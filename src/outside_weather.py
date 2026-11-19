"""
Weather inputs for try T4(b) of PREREG.md (section 6): Open-Meteo historical archive, ERA5 reanalysis only.

    .venv/bin/python -I src/outside_weather.py fetch     # one API call per station, raw JSON saved untouched
    .venv/bin/python -I src/outside_weather.py process   # raw JSON -> data/processed/wx_daily_li.csv

Request settings (checked against https://open-meteo.com/en/docs/historical-weather-api on 2026-11-17):
- `models=era5`: pins the ERA5 reanalysis (0.25 degree grid, 1940 to present, about 5 days behind). The default
  "best match" mixes ERA5, ERA5-Land and ECMWF IFS, so it is never used.
- `daily=shortwave_radiation_sum,wind_speed_10m_max`: MJ/m2 per day and km/h (the API's default units).
- `timezone=Etc/GMT+5` (Long Island; SF Bay would be Etc/GMT+8): a fixed UTC-5 clock from the time zone database (POSIX sign: "GMT+5" is five hours behind
  UTC), so every daily value covers 00:00 to 23:59 local standard time with no daylight-saving shift. Each reply's
  `utc_offset_seconds` is checked to be -18000.
- `cell_selection=nearest`: the ERA5 grid cell nearest the station (the API default, "land", would move to a land
  cell). The cell centre the API used is kept so shared cells can be counted.

Licence: Open-Meteo data CC BY 4.0, free for non-commercial use, no key (under 600 calls a minute, 10,000 a day).
ERA5: Copernicus Climate Change Service (C3S). Nothing personal is sent; a generic User-Agent is used.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from outside_sentinel2 import PLACES  # noqa: E402  (one station table for both outside sources)

API = "https://archive-api.open-meteo.com/v1/archive"
USER_AGENT = "research-client/1.0"
DAILY = ["shortwave_radiation_sum", "wind_speed_10m_max"]
START_DATE = "2012-12-30"  # two days before 2013-01-01, so the 3-day mean exists from the first date
END_DATE = "2026-11-16"
PAUSE_S = 65  # one call per station, spaced more than a minute apart


def wx_settings(place_key: str) -> dict:
    """Weather settings for one entry of PLACES (outside_sentinel2.py): fixed-offset zone, raw folder, output CSV."""
    place = PLACES[place_key]
    return {"timezone": tz_name(place["utc_offset_hours"]), "raw_dir": place["wx_raw_dir"], "csv": place["wx_csv"]}


class Blocked(RuntimeError):
    pass


def tz_name(utc_offset_hours: int) -> str:
    """Fixed-offset tz database name. POSIX sign is inverted: UTC-5 is 'Etc/GMT+5'."""
    if utc_offset_hours == 0:
        return "Etc/GMT"
    return f"Etc/GMT{'+' if utc_offset_hours < 0 else '-'}{abs(int(utc_offset_hours))}"


def request_url(lat: float, lon: float, tz: str, start: str = START_DATE, end: str = END_DATE) -> str:
    q = {
        "latitude": f"{lat}", "longitude": f"{lon}", "start_date": start, "end_date": end,
        "daily": ",".join(DAILY), "models": "era5", "timezone": tz, "cell_selection": "nearest",
    }
    return API + "?" + urllib.parse.urlencode(q)


def get(url: str, tries: int = 5) -> bytes:
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 429):
                raise Blocked(f"HTTP {e.code} from Open-Meteo: stop, do not work around it") from e
            if e.code == 400 or attempt == tries - 1:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == tries - 1:
                raise
        time.sleep(15 * (attempt + 1))
    raise RuntimeError("unreachable")


def cmd_fetch(place_key: str = "long_island") -> None:
    place, wx = PLACES[place_key], wx_settings(place_key)
    raw = wx["raw_dir"]
    raw.mkdir(parents=True, exist_ok=True)
    log_path = raw / "requests.jsonl"
    first = True
    for sid, st in place["stations"].items():
        out = raw / f"{sid}.json"
        if out.exists():
            print(f"{sid}: already saved, skipped")
            continue
        if not first:
            time.sleep(PAUSE_S)
        first = False
        url = request_url(st["lat"], st["lon"], wx["timezone"])
        body = get(url)
        pulled = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        tmp = out.with_suffix(".tmp")
        tmp.write_bytes(body)
        tmp.rename(out)
        with open(log_path, "a") as f:
            f.write(json.dumps({"station": sid, "url": url, "pulled_utc": pulled, "bytes": len(body)}) + "\n")
        print(f"{sid}: {len(body)} bytes")
    write_manifest(place_key)


def write_manifest(place_key: str = "long_island") -> None:
    wx = wx_settings(place_key)
    raw = wx["raw_dir"]
    reqs = [json.loads(ln) for ln in (raw / "requests.jsonl").read_text().splitlines() if ln.strip()]
    files = sorted(raw.glob("*.json"))
    files = [p for p in files if p.name != "MANIFEST.json"]
    days = {}
    for p in files:
        d = json.loads(p.read_text())
        days[p.stem] = {"n_days": len(d["daily"]["time"]), "first": d["daily"]["time"][0],
                        "last": d["daily"]["time"][-1],
                        "last_non_missing": max((t for t, v in zip(d["daily"]["time"],
                                                                   d["daily"]["shortwave_radiation_sum"])
                                                 if v is not None), default=None),
                        "grid_cell": [d["latitude"], d["longitude"]], "utc_offset_seconds": d["utc_offset_seconds"]}
    manifest = {
        "what": "Open-Meteo historical archive, ERA5 only, daily shortwave radiation sum and max 10 m wind speed, "
                "fixed UTC-5 day, nearest grid cell, one JSON reply per station",
        "api": API, "terms": "CC BY 4.0, free non-commercial use, no key (open-meteo.com/en/terms, /en/licence); "
                             "ERA5 from Copernicus Climate Change Service",
        "requests": reqs, "files": len(files), "per_station": days,
        "total_bytes": sum(p.stat().st_size for p in files),
        "manifest_written_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (raw / "MANIFEST.json").write_text(json.dumps(manifest, indent=1))


def parse_reply(sid: str, d: dict, expected_offset_s: int) -> list[dict]:
    if d.get("utc_offset_seconds") != expected_offset_s:
        raise ValueError(f"{sid}: utc_offset_seconds {d.get('utc_offset_seconds')} != {expected_offset_s}")
    daily = d["daily"]
    rows = []
    for t, sun, wind in zip(daily["time"], daily["shortwave_radiation_sum"], daily["wind_speed_10m_max"]):
        rows.append({"station": sid, "local_date": t, "wx_sun": sun, "wx_wind": wind,
                     "grid_lat": d["latitude"], "grid_lon": d["longitude"]})
    return rows


def cmd_process(place_key: str = "long_island") -> None:
    import pandas as pd

    place, wx = PLACES[place_key], wx_settings(place_key)
    rows = []
    for sid in place["stations"]:
        d = json.loads((wx["raw_dir"] / f"{sid}.json").read_text())
        rows += parse_reply(sid, d, int(place["utc_offset_hours"] * 3600))
    df = pd.DataFrame(rows)
    df["station"] = df["station"].astype(str)
    wx["csv"].parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(wx["csv"], index=False)
    cells = df[["grid_lat", "grid_lon"]].drop_duplicates()
    print(f"wrote {wx['csv']}: {len(df)} rows, {len(cells)} distinct grid cells")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "fetch":
        cmd_fetch()
    elif cmd == "process":
        cmd_process()
    elif cmd == "manifest":
        write_manifest()
    else:
        print(__doc__)
        sys.exit(2)
