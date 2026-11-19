"""
Sentinel-2 inputs for try T4(a) of PREREG.md (section 6), built exactly as the PREREG words them.

    .venv/bin/python -I src/outside_sentinel2.py search    # list catalogue items per station (saves raw JSON)
    .venv/bin/python -I src/outside_sentinel2.py fetch     # read small pixel windows per item and station (raw)
    .venv/bin/python -I src/outside_sentinel2.py process   # raw windows -> data/processed/s2_images_li.csv
    .venv/bin/python -I src/outside_sentinel2.py process OTHER.csv   # partial table while the fetch is unfinished
    .venv/bin/python -I src/outside_sentinel2.py offsetcheck ITEM_ID [ITEM_ID ...]   # darkest-1% water check

Source: Earth Search STAC API (Element 84), collection `sentinel-2-l2a`, anonymous public COG files.
Raw files are saved untouched and never overwritten; every fetch skips what is already saved.
Processing reads only the saved raw files.

Places live in the PLACES table. A second place (San Francisco Bay, UTC-8) is one more entry there once its
station coordinates have a citable source; none are invented here.
"""

from __future__ import annotations

import json
import logging
import math
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------------------------------------------
# Places and stations. Coordinates are the public USGS site-service values (read 2026-11-17), used as WGS 84.
# ---------------------------------------------------------------------------------------------------------------
PLACES = {
    "long_island": {
        "utc_offset_hours": -5,  # fixed local standard clock (PREREG section 6), never daylight-saving time
        "coord_source": "USGS site service (waterservices.usgs.gov/nwis/site), read 2026-11-17",
        "s2_raw_dir": ROOT / "data" / "raw" / "sentinel2_li",
        "s2_csv": ROOT / "data" / "processed" / "s2_images_li.csv",
        "wx_raw_dir": ROOT / "data" / "raw" / "openmeteo_li",
        "wx_csv": ROOT / "data" / "processed" / "wx_daily_li.csv",
        "outside_csv": ROOT / "data" / "processed" / "outside_li.csv",
        "stations": {
            "01311143": {"name": "Hog Island Channel", "lat": 40.60865278, "lon": -73.65617222},
            "01310740": {"name": "Reynolds Channel", "lat": 40.59361111, "lon": -73.58388889},
            "01304562": {"name": "Peconic River at Riverhead", "lat": 40.91777778, "lon": -72.63866667},
            "01304650": {"name": "Shelter Island Sound", "lat": 41.04430556, "lon": -72.3169722},
            "01303152": {"name": "West Harbor at Oyster Bay", "lat": 40.90355556, "lon": -73.5433611},
        },
    },
    # San Francisco Bay goes here once its station coordinates have a citable source (none are invented):
    # "sf_bay": {"utc_offset_hours": -8, "coord_source": "...", "s2_raw_dir": ..., "s2_csv": ..., "wx_raw_dir": ...,
    #            "wx_csv": ..., "outside_csv": ..., "stations": {"<station code>": {"name": ..., "lat": ..., "lon": ...}, ...}},
}

STAC = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"
SEARCH_START_UTC = "2015-06-01T00:00:00Z"  # before the collection's first item (2015-06-27)
END_LOCAL_DATE = "2026-11-16"  # last local date searched (inclusive)
USER_AGENT = "research-client/1.0"
RADIUS_M = 150.0
WATER_CLASS = 6
MIN_CLEAR = 10  # used by outside_join, kept here for reference
# PREREG band names -> Earth Search asset keys (checked in the collection's item_assets on 2026-11-17)
ASSETS = {"B02": "blue", "B03": "green", "B04": "red", "B05": "rededge1", "SCL": "scl"}
REFL_BANDS = ("B02", "B03", "B04", "B05")
WINDOW_MARGIN_PX = 1  # one extra 20 m pixel on each side of the 150 m disc, for safety
# Read the four reflectance bands only when the SCL window has at least one class-6 pixel centred within 150 m.
# Without one, no pixel can be a clear water pixel, so every output is identical; this keeps the transfer small.
GATE_ON_SCL = True
GDAL_ENV = {
    "AWS_NO_SIGN_REQUEST": "YES",
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_HTTP_MAX_RETRY": "4",
    "GDAL_HTTP_RETRY_DELAY": "3",
    "GDAL_HTTP_USERAGENT": USER_AGENT,
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
    "VSI_CACHE": "TRUE",
}


# ---------------------------------------------------------------------------------------------------------------
# Pure rules (tested in tests/test_outside_sentinel2.py)
# ---------------------------------------------------------------------------------------------------------------
def local_date(dt_utc: datetime, utc_offset_hours: float) -> str:
    """Date on the fixed local standard clock (UTC + offset, no daylight-saving time), as YYYY-MM-DD."""
    if dt_utc.tzinfo is None:
        raise ValueError("datetime must be timezone-aware (UTC)")
    return (dt_utc.astimezone(timezone.utc) + timedelta(hours=utc_offset_hours)).date().isoformat()


def parse_utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def baseline_tuple(b: str | None) -> tuple[int, int]:
    if not b:
        return (-1, -1)
    major, minor = b.split(".")
    return (int(major), int(minor))


RAW_OFFSET_MIN_DN = 800  # below this, a pixel still carrying +1000 would mean reflectance under -0.02: implausible


def reflectance_rule(props: dict, raster_band: dict, item_min_dn: float | None) -> tuple[float, float, str]:
    """
    Scale and offset turning a stored digital number (DN) into reflectance, for one asset of one item:
    reflectance = DN x scale + offset.

    Settled 2026-11-17 from the catalogue's documentation plus the darkest-water check (final report, WORKLOG):
    - Baseline before 04.00: the data never had the offset. Offset 0 (the asset also lists 0).
    - Baseline 04.00 or later: the asset lists offset -0.1, and the documentation says to add it. But in the COG
      files of most such items the offset has already been taken out of the pixels (darkest clear water sits near
      DN 0, not near DN 1000), so adding -0.1 again would put clear water near -0.1. The catalogue flag
      `earthsearch:boa_offset_applied` is right when true, but false is not reliable (some false items have the
      offset already out, shown by darker-than-possible pixels and by the same acquisition in an overlapping tile).
      So the listed offset is added only when the flag is false AND no valid pixel of B02-B05 in the item's saved
      windows is below DN 800 (`item_min_dn`, the smallest nonzero DN). Otherwise offset 0.
    """
    scale = float(raster_band.get("scale", 0.0001))
    listed_offset = float(raster_band.get("offset", 0.0))
    applied = props.get("earthsearch:boa_offset_applied")
    base = baseline_tuple(props.get("s2:processing_baseline"))
    if base < (4, 0):
        return scale, 0.0, "pre-04.00: dn*scale"
    if applied is True:
        return scale, 0.0, "04.00+, flag true: dn*scale (offset already out of pixels)"
    if item_min_dn is not None and item_min_dn < RAW_OFFSET_MIN_DN:
        return scale, 0.0, "04.00+, flag false, pixels below DN 800: dn*scale (offset already out of pixels)"
    if listed_offset == 0.0:
        raise ValueError(f"baseline {props.get('s2:processing_baseline')} lists no offset but pixels look raw")
    return scale, listed_offset, "04.00+, flag false, no pixel below DN 800: dn*scale+offset"


def window_20m(x: float, y: float, transform20, radius: float = RADIUS_M, margin: int = WINDOW_MARGIN_PX):
    """
    (col_off, row_off, width, height) on the 20 m grid holding every pixel whose centre is within `radius` of (x, y),
    plus `margin` pixels on each side. transform20 = (a, b, c, d, e, f) of a north-up grid.
    """
    a, b, c, d, e, f = transform20[:6]
    if b != 0 or d != 0 or e != -a:
        raise ValueError("grid must be north-up with square pixels")
    res = a
    col_min = math.ceil((x - radius - c) / res - 0.5) - margin
    col_max = math.floor((x + radius - c) / res - 0.5) + margin
    row_min = math.ceil((f - y - radius) / res - 0.5) - margin
    row_max = math.floor((f - y + radius) / res - 0.5) + margin
    return col_min, row_min, col_max - col_min + 1, row_max - row_min + 1


def pixel_centres(win_transform, height: int, width: int) -> tuple[np.ndarray, np.ndarray]:
    """Projected x, y of every pixel centre of a window, given the window's own (a, b, c, d, e, f) transform."""
    a, b, c, d, e, f = win_transform[:6]
    cols = np.arange(width) + 0.5
    rows = np.arange(height) + 0.5
    cc, rr = np.meshgrid(cols, rows)
    xs = c + cc * a + rr * b
    ys = f + cc * d + rr * e
    return xs, ys


def average_2x2(dn10: np.ndarray, nodata: int = 0) -> np.ndarray:
    """Average a 10 m digital-number array onto the 20 m grid (2 x 2 blocks). Any nodata member -> NaN."""
    h, w = dn10.shape
    if h % 2 or w % 2:
        raise ValueError("10 m window must have even height and width")
    blocks = dn10.astype("float64").reshape(h // 2, 2, w // 2, 2)
    out = blocks.mean(axis=(1, 3))
    bad = (dn10 == nodata).reshape(h // 2, 2, w // 2, 2).any(axis=(1, 3))
    out[bad] = np.nan
    return out


def clear_water_stats(dn: dict, win20_transform, x: float, y: float, rules: dict, radius: float = RADIUS_M) -> dict:
    """
    PREREG T4(a) for one image and station. dn: B02, B03, B04 (10 m windows, exactly twice the 20 m window) and
    B05, SCL (20 m windows). rules: band -> (scale, offset). Returns the count of clear water pixels and the medians.
    """
    scl = dn["SCL"]
    h, w = scl.shape
    xs, ys = pixel_centres(win20_transform, h, w)
    within = np.hypot(xs - x, ys - y) <= radius
    water = scl == WATER_CLASS
    out = {"n_class6_within": int((within & water).sum())}
    if "B05" not in dn:  # reflectance bands were not read (no class-6 pixel within the radius)
        out.update(n_clear=0, ndci=np.nan, red=np.nan, green_blue=np.nan)
        return out
    refl = {}
    for band in REFL_BANDS:
        arr = dn[band]
        if band == "B05":
            v = arr.astype("float64")
            v[arr == 0] = np.nan
        else:
            v = average_2x2(arr)
        scale, offset = rules[band]
        refl[band] = v * scale + offset
    positive = np.ones_like(within)
    for band in REFL_BANDS:
        positive &= np.isfinite(refl[band]) & (refl[band] > 0)
    clear = within & water & positive
    n = int(clear.sum())
    out["n_clear"] = n
    if n == 0:
        out.update(ndci=np.nan, red=np.nan, green_blue=np.nan)
        return out
    b2, b3, b4, b5 = (refl[b][clear] for b in REFL_BANDS)
    out["ndci"] = float(np.median((b5 - b4) / (b5 + b4)))
    out["red"] = float(np.median(b4))
    out["green_blue"] = float(np.median(b3 / b2))
    return out


# ---------------------------------------------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------------------------------------------
class Blocked(RuntimeError):
    """The service refused or rate-limited us: stop, never work around it."""


def http_json(url: str, body: dict | None = None, tries: int = 5) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 429):
                raise Blocked(f"HTTP {e.code} from {url}") from e
            if attempt == tries - 1:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == tries - 1:
                raise
        time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def search_end_utc(place: dict) -> str:
    """Last UTC instant whose local standard date is END_LOCAL_DATE."""
    end_local = datetime.fromisoformat(END_LOCAL_DATE).replace(tzinfo=timezone.utc) + timedelta(days=1)
    end_utc = end_local - timedelta(hours=place["utc_offset_hours"]) - timedelta(milliseconds=1)
    return end_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# ---------------------------------------------------------------------------------------------------------------
# Step 1: search
# ---------------------------------------------------------------------------------------------------------------
def cmd_search(place_key: str = "long_island") -> None:
    place = PLACES[place_key]
    raw = place["s2_raw_dir"]
    (raw / "items").mkdir(parents=True, exist_ok=True)
    (raw / "search").mkdir(parents=True, exist_ok=True)
    for sid, st in place["stations"].items():
        sdir = raw / "search" / sid
        if (sdir / "COMPLETE").exists():
            print(f"{sid}: search already saved, skipped")
            continue
        sdir.mkdir(parents=True, exist_ok=True)
        body = {
            "collections": [COLLECTION],
            "intersects": {"type": "Point", "coordinates": [st["lon"], st["lat"]]},
            "datetime": f"{SEARCH_START_UTC}/{search_end_utc(place)}",
            "limit": 100,
            "sortby": [{"field": "properties.datetime", "direction": "asc"}],
        }
        page, ids, log = 1, [], []
        while body is not None:
            out = sdir / f"page_{page:04d}.json"
            if out.exists():
                resp = json.loads(out.read_text())
            else:
                resp = http_json(f"{STAC}/search", body)
                out.write_text(json.dumps(resp))
                log.append({"url": f"{STAC}/search", "method": "POST", "body": body, "pulled_utc": utc_now(),
                            "returned": len(resp.get("features", []))})
            for feat in resp.get("features", []):
                ids.append(feat["id"])
                ipath = raw / "items" / f"{feat['id']}.json"
                if not ipath.exists():
                    ipath.write_text(json.dumps(feat))
            nxt = [ln for ln in resp.get("links", []) if ln.get("rel") == "next"]
            body = nxt[0]["body"] if nxt else None
            page += 1
        (sdir / "requests.json").write_text(json.dumps(log, indent=1))
        (sdir / "COMPLETE").write_text(json.dumps({"n_items": len(ids), "n_unique": len(set(ids)),
                                                   "finished_utc": utc_now()}))
        print(f"{sid}: {len(ids)} items ({len(set(ids))} unique)")


def station_items(place_key: str = "long_island") -> dict[str, list[str]]:
    raw = PLACES[place_key]["s2_raw_dir"]
    out = {}
    for sid in PLACES[place_key]["stations"]:
        sdir = raw / "search" / sid
        if not (sdir / "COMPLETE").exists():
            raise RuntimeError(f"search for {sid} not complete; run `search` first")
        ids = []
        for p in sorted(sdir.glob("page_*.json")):
            ids += [f["id"] for f in json.loads(p.read_text()).get("features", [])]
        out[sid] = sorted(set(ids))
    return out


# ---------------------------------------------------------------------------------------------------------------
# Step 2: fetch windows
# ---------------------------------------------------------------------------------------------------------------
_bytes_lock = threading.Lock()
_net = {"bytes": 0, "ranges": 0}
_RANGE_RE = re.compile(r"Downloading (\d+)-(\d+)")


class _ByteCounter(logging.Handler):
    """Adds up the HTTP byte ranges GDAL reports in its debug log (the real network transfer for pixel data)."""

    def emit(self, record):
        msg = record.getMessage()
        for a, b in _RANGE_RE.findall(msg):
            with _bytes_lock:
                _net["bytes"] += int(b) - int(a) + 1
                _net["ranges"] += 1


def _read_window(ds, col_off, row_off, width, height):
    from rasterio.windows import Window

    win = Window(col_off, row_off, width, height)
    inside = col_off >= 0 and row_off >= 0 and col_off + width <= ds.width and row_off + height <= ds.height
    arr = ds.read(1, window=win, boundless=not inside, fill_value=0)
    wt = ds.window_transform(win)
    return arr, tuple(wt)[:6]


def _saved(raw: Path, item_id: str, sid: str) -> bool:
    d = raw / "windows" / item_id
    return (d / f"{sid}.npz").exists() or (d / f"{sid}.unreadable.json").exists()


def fetch_item(item_id: str, stations: list[str], place_key: str) -> list[dict]:
    """Read and save the raw windows of one item for the given stations. Returns manifest entries."""
    import rasterio
    from rasterio.warp import transform as warp

    place = PLACES[place_key]
    raw = place["s2_raw_dir"]
    item = json.loads((raw / "items" / f"{item_id}.json").read_text())
    todo = [s for s in stations if not _saved(raw, item_id, s)]
    if not todo:
        return []
    epsg = item["properties"]["proj:epsg"]
    hrefs = {b: item["assets"][k]["href"] for b, k in ASSETS.items()}
    entries = []
    if not all(h.startswith("https://") for h in hrefs.values()):
        # Assets only in a requester-pays bucket (s3://...): reading them needs an AWS account, which is not allowed.
        for sid in todo:
            out = raw / "windows" / item_id / f"{sid}.unreadable.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({"item_id": item_id, "station": sid, "hrefs": hrefs, "checked_utc": utc_now(),
                                       "reason": "no public COG asset (requester-pays s3:// only); not read"}))
            entries.append({"item": item_id, "station": sid, "bands": [], "bytes": 0, "status": "no_public_cog"})
        return entries
    with rasterio.Env(**GDAL_ENV):
        handles = {}
        try:
            handles["SCL"] = rasterio.open(hrefs["SCL"])
            scl_ds = handles["SCL"]
            if scl_ds.crs.to_epsg() != epsg:
                raise RuntimeError(f"{item_id}: SCL CRS {scl_ds.crs} differs from proj:epsg {epsg}")
            t20 = tuple(scl_ds.transform)[:6]
            for sid in todo:
                st = place["stations"][sid]
                xs, ys = warp("EPSG:4326", f"EPSG:{epsg}", [st["lon"]], [st["lat"]])
                x, y = xs[0], ys[0]
                c0, r0, w, h = window_20m(x, y, t20)
                scl, wt20 = _read_window(scl_ds, c0, r0, w, h)
                cx, cy = pixel_centres(wt20, h, w)
                n6 = int(((np.hypot(cx - x, cy - y) <= RADIUS_M) & (scl == WATER_CLASS)).sum())
                arrays = {"SCL": scl}
                meta = {"item_id": item_id, "station": sid, "epsg": epsg, "station_x": x, "station_y": y,
                        "lon": st["lon"], "lat": st["lat"], "win20": [c0, r0, w, h], "transform20": list(wt20),
                        "hrefs": {"SCL": hrefs["SCL"]}, "n_class6_within": n6}
                if n6 > 0 or not GATE_ON_SCL:
                    for band in ("B05", "B02", "B03", "B04"):
                        if band not in handles:
                            handles[band] = rasterio.open(hrefs[band])
                        ds = handles[band]
                        if ds.crs.to_epsg() != epsg:
                            raise RuntimeError(f"{item_id}: {band} CRS differs")
                        if band == "B05":
                            if tuple(ds.transform)[:6] != t20:
                                raise RuntimeError(f"{item_id}: B05 grid differs from SCL grid")
                            arr, wt = _read_window(ds, c0, r0, w, h)
                        else:
                            t10 = tuple(ds.transform)[:6]
                            if (t10[2], t10[5]) != (t20[2], t20[5]) or t10[0] * 2 != t20[0]:
                                raise RuntimeError(f"{item_id}: {band} 10 m grid not aligned with 20 m grid")
                            arr, wt = _read_window(ds, 2 * c0, 2 * r0, 2 * w, 2 * h)
                        arrays[band] = arr
                        meta["hrefs"][band] = hrefs[band]
                        meta[f"transform_{band}"] = list(wt)
                    meta["bands_saved"] = ["B02", "B03", "B04", "B05", "SCL"]
                else:
                    meta["bands_saved"] = ["SCL"]
                    meta["gate"] = "no SCL class-6 pixel centred within 150 m: reflectance bands not read"
                meta["crs_wkt"] = scl_ds.crs.to_wkt()
                meta["pulled_utc"] = utc_now()
                out = raw / "windows" / item_id / f"{sid}.npz"
                out.parent.mkdir(parents=True, exist_ok=True)
                tmp = out.with_suffix(".tmp.npz")
                np.savez_compressed(tmp, meta=np.array(json.dumps(meta)), **arrays)
                tmp.rename(out)
                entries.append({"item": item_id, "station": sid, "bands": meta["bands_saved"],
                                "bytes": out.stat().st_size, "pulled_utc": meta["pulled_utc"]})
        finally:
            for ds in handles.values():
                ds.close()
    return entries


def cmd_fetch(place_key: str = "long_island", workers: int = 8, limit: int | None = None) -> None:
    from rasterio.errors import RasterioIOError

    place = PLACES[place_key]
    raw = place["s2_raw_dir"]
    per_station = station_items(place_key)
    by_item: dict[str, list[str]] = {}
    for sid, ids in per_station.items():
        for i in ids:
            by_item.setdefault(i, []).append(sid)
    todo = [i for i in sorted(by_item) if any(not _saved(raw, i, s) for s in by_item[i])]
    if limit:
        todo = todo[:limit]
    print(f"{len(by_item)} items, {len(todo)} with windows still to fetch")
    handler = _ByteCounter()
    rlog = logging.getLogger("rasterio")
    rlog.addHandler(handler)
    rlog.setLevel(logging.DEBUG)
    GDAL_ENV["CPL_DEBUG"] = "ON"
    errors_path = raw / "fetch_errors.jsonl"
    entries_path = raw / "fetch_log.jsonl"
    t0, done, n_err, consecutive_err = time.time(), 0, 0, 0
    stop = threading.Event()

    def task(item_id):
        if stop.is_set():
            return item_id, None, "stopped"
        for attempt in range(4):
            try:
                return item_id, fetch_item(item_id, by_item[item_id], place_key), None
            except RasterioIOError as e:
                msg = str(e)
                if re.search(r"\b(403|429|503)\b|SlowDown|Throttl", msg):
                    if attempt == 3:
                        return item_id, None, f"blocked-or-throttled: {msg}"
                if attempt == 3:
                    return item_id, None, msg
                time.sleep(10 * (attempt + 1))
            except Exception as e:  # noqa: BLE001
                return item_id, None, f"{type(e).__name__}: {e}"
        return item_id, None, "unreachable"

    with ThreadPoolExecutor(max_workers=workers) as pool, open(entries_path, "a") as flog, \
            open(errors_path, "a") as ferr:
        futs = [pool.submit(task, i) for i in todo]
        for fut in as_completed(futs):
            item_id, entries, err = fut.result()
            done += 1
            if err:
                if err == "stopped":
                    continue
                n_err += 1
                consecutive_err += 1
                ferr.write(json.dumps({"item": item_id, "error": err, "time_utc": utc_now()}) + "\n")
                ferr.flush()
                if err.startswith("blocked") or consecutive_err >= 25:
                    stop.set()
                    print(f"STOPPING: {err}", flush=True)
            else:
                consecutive_err = 0
                for e in entries:
                    flog.write(json.dumps(e) + "\n")
                flog.flush()
            if done % 100 == 0:
                el = time.time() - t0
                print(f"{done}/{len(todo)} items, {n_err} errors, {_net['bytes'] / 1e9:.2f} GB transferred, "
                      f"{el / 60:.1f} min", flush=True)
    rlog.removeHandler(handler)
    with open(raw / "transfer_log.jsonl", "a") as f:
        f.write(json.dumps({"run_finished_utc": utc_now(), "items_attempted": len(todo), "errors": n_err,
                            "pixel_bytes_transferred": _net["bytes"], "http_ranges": _net["ranges"],
                            "stopped_early": stop.is_set()}) + "\n")
    print(f"done: {len(todo)} items, {n_err} errors, {_net['bytes'] / 1e9:.3f} GB transferred")
    write_manifest(place_key)


def write_manifest(place_key: str = "long_island") -> None:
    place = PLACES[place_key]
    raw = place["s2_raw_dir"]
    per_station = station_items(place_key)
    search_reqs = {}
    for sid in place["stations"]:
        p = raw / "search" / sid / "requests.json"
        search_reqs[sid] = json.loads(p.read_text()) if p.exists() else []
    windows = sorted((raw / "windows").glob("*/*.npz")) if (raw / "windows").exists() else []
    items = sorted((raw / "items").glob("*.json"))
    total = sum(p.stat().st_size for p in raw.rglob("*") if p.is_file() and p.name != "MANIFEST.json")
    transfers = []
    if (raw / "transfer_log.jsonl").exists():
        transfers = [json.loads(ln) for ln in (raw / "transfer_log.jsonl").read_text().splitlines() if ln.strip()]
    n_full = n_scl = 0
    for p in windows:
        with np.load(p) as z:
            if "B05" in z.files:
                n_full += 1
            else:
                n_scl += 1
    manifest = {
        "what": "Sentinel-2 L2A digital-number windows around each station (B02, B03, B04 at 10 m; B05, SCL at 20 m)"
                " plus each STAC item JSON, from Earth Search (Element 84) and the public sentinel-cogs bucket",
        "stac_api": STAC, "collection": COLLECTION,
        "asset_url_pattern": "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/<zone>/<band>/"
                             "<square>/<year>/<month>/<item_id>/<B02|B03|B04|B05|SCL>.tif (exact URL in each .npz meta)",
        "terms": "Copernicus Sentinel data, free and open (Sentinel Data Legal Notice); Earth Search metadata free to"
                 " use; anonymous access, no account or key",
        "search_requests": search_reqs,
        "items_per_station": {s: len(v) for s, v in per_station.items()},
        "unique_items": len({i for v in per_station.values() for i in v}),
        "item_json_files": len(items),
        "window_files": len(windows), "window_files_all_bands": n_full, "window_files_scl_only": n_scl,
        "gate_on_scl": GATE_ON_SCL,
        "fetch_runs": transfers,
        "network_bytes_pixel_reads_total": sum(t.get("pixel_bytes_transferred", 0) for t in transfers),
        "total_bytes_saved": total,
        "manifest_written_utc": utc_now(),
    }
    (raw / "MANIFEST.json").write_text(json.dumps(manifest, indent=1))
    print(f"manifest: {len(windows)} windows, {len(items)} items, {total / 1e6:.1f} MB saved")


# ---------------------------------------------------------------------------------------------------------------
# Step 3: process
# ---------------------------------------------------------------------------------------------------------------
def load_window(path: Path) -> tuple[dict, dict]:
    with np.load(path) as z:
        meta = json.loads(str(z["meta"]))
        arrays = {k: z[k] for k in z.files if k != "meta"}
    return meta, arrays


def item_min_dn(item_dir: Path) -> float | None:
    """Smallest nonzero DN of B02-B05 over every saved window of one item (None if no reflectance band was read)."""
    mins = []
    for p in sorted(item_dir.glob("*.npz")):
        _, arr = load_window(p)
        for band in REFL_BANDS:
            if band in arr:
                v = arr[band][arr[band] > 0]
                if v.size:
                    mins.append(int(v.min()))
    return float(min(mins)) if mins else None


def process_one(meta: dict, arrays: dict, item: dict, utc_offset_hours: float, min_dn: float | None) -> dict:
    props = item["properties"]
    rules, names = {}, set()
    for band in REFL_BANDS:
        rb = item["assets"][ASSETS[band]]["raster:bands"][0]
        s, o, name = reflectance_rule(props, rb, min_dn)
        rules[band] = (s, o)
        names.add(name)
    if len(names) != 1:
        raise ValueError(f"{item['id']}: bands got different offset rules {names}")
    stats = clear_water_stats(arrays, meta["transform20"], meta["station_x"], meta["station_y"], rules)
    acq = parse_utc(props["datetime"])
    return {
        "station": meta["station"],
        "image_id": item["id"],
        "acq_time_utc": acq.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "local_date": local_date(acq, utc_offset_hours),
        "n_clear_water": stats["n_clear"],
        "s2_ndci_median": stats["ndci"],
        "s2_red_median": stats["red"],
        "s2_green_blue_median": stats["green_blue"],
        "n_class6_within_150m": stats["n_class6_within"],
        "bands_read": "+".join(meta["bands_saved"]),
        "processing_baseline": props.get("s2:processing_baseline"),
        "boa_offset_applied": props.get("earthsearch:boa_offset_applied"),
        "item_min_dn": min_dn,
        "offset_used": rules["B04"][1],
        "offset_rule": names.pop(),
        "mgrs_tile": props.get("grid:code"),
        "epsg": meta["epsg"],
    }


def unreadable_row(item: dict, sid: str, utc_offset_hours: float) -> dict:
    props = item["properties"]
    acq = parse_utc(props["datetime"])
    return {"station": sid, "image_id": item["id"], "acq_time_utc": acq.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "local_date": local_date(acq, utc_offset_hours), "n_clear_water": np.nan,
            "s2_ndci_median": np.nan, "s2_red_median": np.nan, "s2_green_blue_median": np.nan,
            "n_class6_within_150m": np.nan, "bands_read": "none (no public COG)",
            "processing_baseline": props.get("s2:processing_baseline"),
            "boa_offset_applied": props.get("earthsearch:boa_offset_applied"), "item_min_dn": np.nan,
            "offset_used": np.nan, "offset_rule": "not read", "mgrs_tile": props.get("grid:code"), "epsg": None}


def cmd_process(place_key: str = "long_island", out: Path | None = None) -> None:
    """Write the per-image table. Refuses to write the official CSV unless every station-item has a saved window."""
    import pandas as pd

    place = PLACES[place_key]
    raw = place["s2_raw_dir"]
    per_station = station_items(place_key)
    rows, missing, min_cache = [], [], {}
    for sid, ids in per_station.items():
        for item_id in ids:
            p = raw / "windows" / item_id / f"{sid}.npz"
            item = json.loads((raw / "items" / f"{item_id}.json").read_text())
            if (raw / "windows" / item_id / f"{sid}.unreadable.json").exists():
                rows.append(unreadable_row(item, sid, place["utc_offset_hours"]))
                continue
            if not p.exists():
                missing.append((sid, item_id))
                continue
            if item_id not in min_cache:
                min_cache[item_id] = item_min_dn(raw / "windows" / item_id)
            meta, arrays = load_window(p)
            rows.append(process_one(meta, arrays, item, place["utc_offset_hours"], min_cache[item_id]))
    if missing and out is None:
        raise SystemExit(f"{len(missing)} station-items have no saved window: run `fetch` to finish, or pass an "
                         f"explicit output path for a partial table (never the official CSV)")
    df = pd.DataFrame(rows).sort_values(["station", "acq_time_utc", "image_id"]).reset_index(drop=True)
    target = out or place["s2_csv"]
    target.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(target, index=False, float_format="%.6g")
    print(f"wrote {target}: {len(df)} rows; {len(missing)} station-items without a saved window")


# ---------------------------------------------------------------------------------------------------------------
# Offset check (PREREG T4(a)): darkest 1% of water pixels under each rule, for chosen items
# ---------------------------------------------------------------------------------------------------------------
def cmd_offsetcheck(item_ids: list[str], place_key: str = "long_island") -> None:
    place = PLACES[place_key]
    raw = place["s2_raw_dir"]
    for item_id in item_ids:
        item = json.loads((raw / "items" / f"{item_id}.json").read_text())
        props = item["properties"]
        vals = {b: [] for b in REFL_BANDS}
        for p in sorted((raw / "windows" / item_id).glob("*.npz")):
            meta, arr = load_window(p)
            if "B05" not in arr:
                continue
            water = arr["SCL"] == WATER_CLASS
            for b in REFL_BANDS:
                v = arr[b].astype("float64") if b == "B05" else average_2x2(arr[b])
                vals[b].append(v[water & np.isfinite(v)])
        print(f"{item_id} baseline {props.get('s2:processing_baseline')} "
              f"boa_offset_applied {props.get('earthsearch:boa_offset_applied')}")
        for b in REFL_BANDS:
            v = np.concatenate(vals[b]) if vals[b] else np.array([])
            if v.size == 0:
                print(f"  {b}: no water pixels")
                continue
            rb = item["assets"][ASSETS[b]]["raster:bands"][0]
            p1 = float(np.percentile(v, 1))
            dark = v[v <= p1]
            print(f"  {b}: n water px {v.size}, DN p1 {p1:.0f}, mean of darkest 1% DN {dark.mean():.1f} -> "
                  f"DN*scale {dark.mean() * rb.get('scale', 1e-4):+.4f}, "
                  f"DN*scale+listed offset({rb.get('offset', 0)}) "
                  f"{dark.mean() * rb.get('scale', 1e-4) + rb.get('offset', 0):+.4f}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "search":
        cmd_search()
    elif cmd == "fetch":
        lim = int(sys.argv[2]) if len(sys.argv) > 2 else None
        cmd_fetch(limit=lim)
    elif cmd == "manifest":
        write_manifest()
    elif cmd == "process":
        cmd_process(out=Path(sys.argv[2]) if len(sys.argv) > 2 else None)
    elif cmd == "offsetcheck":
        cmd_offsetcheck(sys.argv[2:])
    else:
        print(__doc__)
        sys.exit(2)
