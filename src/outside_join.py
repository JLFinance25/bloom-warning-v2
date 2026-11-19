"""
Attach the nine T4 "outside data" columns of PREREG.md section 6 to (station, date t) rows.

    .venv/bin/python -I src/outside_join.py                  # writes data/processed/outside_li.csv
    .venv/bin/python -I src/outside_join.py S2.csv OUT.csv   # same from another per-image table

`attach_outside(examples, s2_images, wx_daily)` is a pure function (no file or network access):

Satellite (T4 a): the newest image dated t-1 or earlier (local standard date), at most 30 days old, with at least
10 clear water pixels. If two such images share a date, the one with more clear water pixels; a tie goes to the
image ID that sorts first. Columns: s2_ndci, s2_red, s2_green_blue (that image's medians), s2_n_water (its clear
water pixel count), s2_age (t minus image date, days). All five missing if there is no such image.

Weather (T4 b): wx_sun and wx_wind on day t; wx_sun_3d and wx_wind_3d = mean over t-2, t-1, t, missing if any of
the three days is missing (the literal reading; no partial means).

outside_li.csv has one row per station and calendar date from 2013-01-01 to 2026-11-16, station = USGS site number
as text, date = YYYY-MM-DD, so it can be joined by (station, date).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MIN_CLEAR = 10
MAX_AGE_DAYS = 30
S2_COLS = ["s2_ndci", "s2_red", "s2_green_blue", "s2_n_water", "s2_age"]
WX_COLS = ["wx_sun", "wx_wind", "wx_sun_3d", "wx_wind_3d"]
T4_COLS = S2_COLS + WX_COLS
GRID_START, GRID_END = "2013-01-01", "2026-11-16"


def _dates(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s).dt.normalize().astype("datetime64[ns]")


def best_image_per_date(s2_images: pd.DataFrame) -> pd.DataFrame:
    """Usable images (>= MIN_CLEAR clear water pixels), one per station and local date by the tie rule."""
    needed = ["station", "image_id", "local_date", "n_clear_water", "s2_ndci_median", "s2_red_median",
              "s2_green_blue_median"]
    img = s2_images.reindex(columns=list(dict.fromkeys(list(s2_images.columns) + needed))).copy()
    img["station"] = img["station"].astype(str)
    img["img_date"] = _dates(img["local_date"])
    img["n"] = pd.to_numeric(img["n_clear_water"], errors="coerce")
    img = img[img["n"] >= MIN_CLEAR]
    # more clear water pixels first; equal counts -> image ID that sorts first
    img = img.sort_values(["station", "img_date", "n", "image_id"], ascending=[True, True, False, True])
    img = img.drop_duplicates(["station", "img_date"], keep="first")
    return img[["station", "img_date", "image_id", "n", "s2_ndci_median", "s2_red_median", "s2_green_blue_median"]]


def attach_outside(examples: pd.DataFrame, s2_images: pd.DataFrame, wx_daily: pd.DataFrame,
                   keep_image_id: bool = False) -> pd.DataFrame:
    """
    examples: columns `station` and `date` (date t). s2_images: rows of s2_images_*.csv. wx_daily: rows of
    wx_daily_*.csv. Returns examples (same row order) with the nine T4 columns added.
    """
    ex = examples.copy()
    ex["station"] = ex["station"].astype(str)
    ex["_t"] = _dates(ex["date"])
    ex["_row"] = np.arange(len(ex))

    # --- satellite ---------------------------------------------------------------------------------------------
    best = best_image_per_date(s2_images)
    left = ex[["_row", "station", "_t"]].sort_values("_t")
    right = best.rename(columns={"img_date": "_img_t"}).copy()
    right["_key"] = right["_img_t"]
    right = right.sort_values("_key")
    m = pd.merge_asof(left, right, left_on="_t", right_on="_key", by="station", direction="backward",
                      allow_exact_matches=False,  # image dated t itself is never used: only t-1 or earlier
                      tolerance=pd.Timedelta(days=MAX_AGE_DAYS))
    m = m.set_index("_row").reindex(ex["_row"])
    age = (m["_t"] - m["_img_t"]).dt.days
    ok = age.notna() & (age >= 1) & (age <= MAX_AGE_DAYS)
    ex["s2_ndci"] = m["s2_ndci_median"].where(ok).to_numpy()
    ex["s2_red"] = m["s2_red_median"].where(ok).to_numpy()
    ex["s2_green_blue"] = m["s2_green_blue_median"].where(ok).to_numpy()
    ex["s2_n_water"] = pd.array(m["n"].where(ok).to_numpy(), dtype="Float64").astype("Int64")
    ex["s2_age"] = pd.array(age.where(ok).to_numpy(), dtype="Float64").astype("Int64")
    if keep_image_id:
        ex["s2_image_id"] = m["image_id"].where(ok).to_numpy()

    # --- weather -----------------------------------------------------------------------------------------------
    wx = wx_daily.copy()
    wx["station"] = wx["station"].astype(str)
    wx["_t"] = _dates(wx["local_date"])
    parts = []
    for sid, g in wx.groupby("station", sort=True):
        g = g.set_index("_t").sort_index()
        if g.index.has_duplicates:
            raise ValueError(f"duplicate weather dates for station {sid}")
        full = pd.date_range(g.index.min(), g.index.max(), freq="D")
        g = g.reindex(full)  # a date absent from the table is a missing day
        out = pd.DataFrame({"station": sid, "_t": full})
        for col in ("wx_sun", "wx_wind"):
            v = pd.to_numeric(g[col], errors="coerce")
            out[col] = v.to_numpy()
            out[f"{col}_3d"] = v.rolling(3, min_periods=3).mean().to_numpy()  # missing if any of t-2..t missing
        parts.append(out)
    wxd = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["station", "_t"] + WX_COLS)
    ex = ex.merge(wxd, on=["station", "_t"], how="left", sort=False)
    ex = ex.sort_values("_row").drop(columns=["_t", "_row"]).reset_index(drop=True)
    return ex


def build_grid(stations: list[str], start: str = GRID_START, end: str = GRID_END) -> pd.DataFrame:
    dates = pd.date_range(start, end, freq="D")
    return pd.DataFrame([(s, d) for s in stations for d in dates], columns=["station", "date"])


def main(s2_csv: Path | None = None, out_csv: Path | None = None, place_key: str = "long_island") -> None:
    """Default: read the place's official s2/wx tables and write its outside_*.csv. Paths can be overridden."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from outside_sentinel2 import PLACES

    place = PLACES[place_key]
    s2_csv = s2_csv or place["s2_csv"]
    out_csv = out_csv or place["outside_csv"]
    s2 = pd.read_csv(s2_csv, dtype={"station": str, "image_id": str})
    wx = pd.read_csv(place["wx_csv"], dtype={"station": str})
    out = attach_outside(build_grid(list(place["stations"])), s2, wx)
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    out = out[["station", "date"] + T4_COLS]
    out.to_csv(out_csv, index=False, float_format="%.6g")
    print(f"wrote {out_csv}: {len(out)} rows")


if __name__ == "__main__":
    args = [Path(a) for a in sys.argv[1:3]]
    main(*args)
