"""
Made-up data for the pipeline tests (no real data anywhere in tests/). Imported by the other test files.
Holds no tests itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent / "src"
sys.dont_write_bytecode = True
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import config  # noqa: E402


def daily_frame(station: str, values: dict, start: str = "2020-01-01") -> pd.DataFrame:
    """A gapless one-station frame from lists of values (missing given as None or nan)."""
    n = max(len(v) for v in values.values())
    out = pd.DataFrame({"date": pd.date_range(start, periods=n, freq="D"), "station": station})
    for column in config.MEASURED_COLUMNS:
        out[column] = np.nan
    for column, v in values.items():
        out[column] = np.array([np.nan if x is None else x for x in v], dtype=float)
    return out


def synthetic_frame(stations=("AAA", "BBB", "CCC", "DDD"), starts=None, end="2020-12-31", seed=7,
                    missing_share=0.03, outage: bool = True) -> pd.DataFrame:
    """A made-up place: seasonal, autocorrelated chlorophyll with bloom bursts, other measures, and gaps."""
    rng = np.random.default_rng(seed)
    starts = starts or {s: "2012-01-01" for s in stations}
    parts = []
    for i, station in enumerate(stations):
        dates = pd.date_range(starts[station], end, freq="D")
        n = len(dates)
        doy = dates.dayofyear.to_numpy()
        season = 1.0 + 0.6 * np.sin(2 * np.pi * (doy - 100) / 365.25)
        ar = np.zeros(n)
        noise = rng.standard_normal(n)
        for t in range(1, n):
            ar[t] = 0.85 * ar[t - 1] + 0.35 * noise[t]
        burst = np.zeros(n)
        for b in rng.choice(n - 6, size=max(1, n // 45), replace=False):
            burst[b:b + rng.integers(2, 6)] += rng.uniform(0.8, 1.6)
        chla = (5 + 3 * i) * season * np.exp(ar + burst)
        frame = pd.DataFrame({"date": dates, "station": station})
        frame["chla_mean"] = chla
        frame["chla_max"] = chla * (1 + np.abs(rng.normal(0.3, 0.1, n)))
        frame["chla_min"] = chla * (1 - np.abs(rng.normal(0.2, 0.05, n)))
        frame["do_mgl_mean"] = 8 - 0.05 * chla + rng.normal(0, 0.3, n)
        frame["do_mgl_max"] = frame["do_mgl_mean"] + np.abs(rng.normal(1, 0.3, n))
        frame["do_mgl_min"] = frame["do_mgl_mean"] - np.abs(rng.normal(1, 0.3, n))
        frame["temp_c_mean"] = 15 + 5 * np.sin(2 * np.pi * (doy - 120) / 365.25) + rng.normal(0, 0.5, n)
        frame["turbidity_mean"] = np.abs(rng.normal(10, 4, n))
        frame["salinity_psu_mean"] = 25 + rng.normal(0, 2, n)
        for column in config.MEASURED_COLUMNS:
            holes = rng.random(n) < missing_share
            frame.loc[holes, column] = np.nan
        block = rng.integers(30, n - 40)
        if outage:
            frame.loc[block:block + 20, list(config.MEASURED_COLUMNS)] = np.nan   # a three-week outage
        parts.append(frame)
    return pd.concat(parts, ignore_index=True).sort_values(["station", "date"]).reset_index(drop=True)


def synthetic_date_inputs(start="2011-01-01", end="2021-12-31", seed=11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, end, freq="D")
    out = pd.DataFrame({"date": dates})
    for column in config.SF_DATE_LEVEL_COLUMNS:
        out[column] = rng.normal(0, 1, len(dates))
    out.loc[rng.random(len(dates)) < 0.02, "shortwave_radiation_sum_MJm2"] = np.nan
    return out


def synthetic_outside(frame: pd.DataFrame, seed=13) -> pd.DataFrame:
    """A made-up outside-inputs table: satellite inputs only from 2017 on, weather every day."""
    rng = np.random.default_rng(seed)
    out = frame[["station", "date"]].copy()
    n = len(out)
    for column in config.OUTSIDE_COLUMNS:
        out[column] = rng.normal(0, 1, n)
    no_image = (out["date"] < pd.Timestamp("2017-01-01")) | (rng.random(n) < 0.6)
    out.loc[no_image, [c for c in config.OUTSIDE_COLUMNS if c.startswith("s2_")]] = np.nan
    return out


SYN_SF = config.PlaceSpec(
    name="syn_sf", stations=("AAA", "BBB", "CCC", "DDD"), verdict_years=(2014, 2015, 2016, 2017, 2018, 2019),
    outside_years=(2020,), utc_offset_hours=-8, base_columns=config.SF_BASE_COLUMNS,
    date_level_columns=config.SF_DATE_LEVEL_COLUMNS,
)
SYN_LI = config.PlaceSpec(
    name="syn_li", stations=("AAA", "BBB", "CCC", "DDD"), verdict_years=(2014, 2015, 2016, 2017, 2018, 2019),
    outside_years=(2020,), utc_offset_hours=-5, base_columns=config.LI_BASE_COLUMNS,
)
