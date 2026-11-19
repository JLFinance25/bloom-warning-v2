"""
Every model input of PREREG section 6, one function per input family, each on the daily-reindexed series of the
same station. v(t) is the value on day t. Nothing here looks past day t.

Year-dependent inputs (anything divided by or compared with L(Y)) take that year's lines; the rest do not.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config


def check_gapless(frame: pd.DataFrame) -> None:
    """Raise unless every station's rows are consecutive calendar days with no duplicates, sorted."""
    for station, group in frame.groupby("station", sort=True):
        dates = group["date"]
        if not dates.is_monotonic_increasing or dates.duplicated().any():
            raise ValueError(f"Station {station} rows are not sorted unique days.")
        if len(dates) and (dates.iloc[-1] - dates.iloc[0]).days + 1 != len(dates):
            raise ValueError(f"Station {station} is not reindexed to every calendar day.")


def _sorted(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.sort_values(["station", "date"]).reset_index(drop=True)
    check_gapless(out)
    return out


def _line_per_row(frame: pd.DataFrame, lines: dict[str, float]) -> pd.Series:
    missing = sorted(set(frame["station"].unique()) - set(lines))
    if missing:
        raise ValueError(f"No high line for stations {missing}.")
    return frame["station"].map(lines).astype(float)


def _lag(frame: pd.DataFrame, column: str | pd.Series, days: int) -> pd.Series:
    values = frame[column] if isinstance(column, str) else column
    return values.groupby(frame["station"]).shift(days)


def chlorophyll_state(frame: pd.DataFrame, lines: dict[str, float]) -> pd.DataFrame:
    """ratio, slope7 (the team's), ratio_max, d1_ratio, d3_ratio, max7_ratio."""
    frame = _sorted(frame)
    line = _line_per_row(frame, lines)
    ratio = frame["chla_mean"] / line
    out = frame[["station", "date"]].copy()
    out["ratio"] = ratio
    out["slope7"] = (frame["chla_mean"] - _lag(frame, "chla_mean", config.SLOPE_LAG_DAYS)) / config.SLOPE_LAG_DAYS
    out["ratio_max"] = frame["chla_max"] / line
    out["d1_ratio"] = ratio - _lag(frame, ratio, 1)
    out["d3_ratio"] = ratio - _lag(frame, ratio, 3)
    out["max7_ratio"] = (ratio.groupby(frame["station"])
                         .rolling(config.MAX7_WINDOW_DAYS, min_periods=1).max()
                         .reset_index(level=0, drop=True).sort_index())
    return out


def days_since_high(frame: pd.DataFrame, lines: dict[str, float]) -> pd.DataFrame:
    """Days from the most recent measured day on or before t-1 with chlorophyll >= L(Y); capped at 60."""
    frame = _sorted(frame)
    line = _line_per_row(frame, lines)
    high = (frame["chla_mean"] >= line).to_numpy()            # missing compares False: not a high
    position = np.arange(len(frame), dtype=float)
    last_high = pd.Series(np.where(high, position, np.nan)).groupby(frame["station"]).ffill()
    last_high_before_t = last_high.groupby(frame["station"]).shift(1)   # on or before t-1
    days = position - last_high_before_t.to_numpy()
    days = np.where(np.isnan(days), config.DAYS_SINCE_HIGH_CAP, np.minimum(days, config.DAYS_SINCE_HIGH_CAP))
    out = frame[["station", "date"]].copy()
    out["days_since_high"] = days.astype(float)
    return out


def fresh_onset_flag(frame: pd.DataFrame, lines: dict[str, float]) -> pd.DataFrame:
    """True when no measured day in t-14..t-1 has chlorophyll at or above L(Y)."""
    frame = _sorted(frame)
    line = _line_per_row(frame, lines)
    high = (frame["chla_mean"] >= line).astype(float)
    earlier = high.groupby(frame["station"]).shift(1, fill_value=0.0)
    recent = (earlier.groupby(frame["station"])
              .rolling(config.FRESH_ONSET_WINDOW_DAYS, min_periods=1).sum()
              .reset_index(level=0, drop=True).sort_index())
    out = frame[["station", "date"]].copy()
    out["fresh_onset"] = (recent == 0).to_numpy()
    return out


def water_changes(frame: pd.DataFrame) -> pd.DataFrame:
    """do_swing, d3_temp, d3_turb, d3_sal; missing if either end is missing."""
    frame = _sorted(frame)
    out = frame[["station", "date"]].copy()
    out["do_swing"] = frame["do_mgl_max"] - frame["do_mgl_min"]
    for name, column in (("d3_temp", "temp_c_mean"), ("d3_turb", "turbidity_mean"), ("d3_sal", "salinity_psu_mean")):
        out[name] = frame[column] - _lag(frame, column, 3)
    return out


def moon_phase(dates: pd.Series, utc_offset_hours: int) -> pd.DataFrame:
    """sin/cos of 2*pi*phase/14.7652944, phase = days from 2000-01-06 18:14 UTC to local-standard noon of t."""
    noon_utc = pd.to_datetime(dates) + pd.Timedelta(hours=12) - pd.Timedelta(hours=utc_offset_hours)
    elapsed = (noon_utc - config.MOON_EPOCH_UTC) / pd.Timedelta(days=1)
    phase = np.mod(elapsed.to_numpy(dtype=float), config.MOON_HALF_CYCLE_DAYS)
    angle = 2 * np.pi * phase / config.MOON_HALF_CYCLE_DAYS
    return pd.DataFrame({"moon_sin": np.sin(angle), "moon_cos": np.cos(angle)}, index=dates.index)


def season(dates: pd.Series) -> pd.DataFrame:
    """The team's doy_sin, doy_cos: day of year over 365.25."""
    angle = 2 * np.pi * pd.to_datetime(dates).dt.dayofyear / config.DAYS_IN_YEAR
    return pd.DataFrame({"doy_sin": np.sin(angle), "doy_cos": np.cos(angle)}, index=dates.index)


def neighbours(frame: pd.DataFrame, lines: dict[str, float]) -> pd.DataFrame:
    """From the OTHER stations in `lines` (those taking part) with chlorophyll measured on day t."""
    frame = _sorted(frame)
    part = frame.loc[frame["station"].isin(list(lines))]
    chla = part.pivot(index="date", columns="station", values="chla_mean")
    line_row = pd.Series({s: lines[s] for s in chla.columns}, dtype=float)
    ratio = chla.divide(line_row, axis=1)
    high = chla.ge(line_row, axis=1)                    # missing compares False
    out = []
    for station, group in frame.groupby("station", sort=True):
        others = [s for s in chla.columns if s != station]
        r = ratio[others].reindex(group["date"])
        h = high[others].reindex(group["date"], fill_value=False)
        piece = group[["station", "date"]].copy()
        piece["nb_mean_ratio"] = r.mean(axis=1, skipna=True).to_numpy()
        piece["nb_max_ratio"] = r.max(axis=1, skipna=True).to_numpy()
        piece["nb_n_high"] = h.sum(axis=1).to_numpy(dtype=float)
        piece["nb_n_reporting"] = r.notna().sum(axis=1).to_numpy(dtype=float)
        out.append(piece)
    return pd.concat(out, ignore_index=True)


def year_inputs(frame: pd.DataFrame, lines: dict[str, float], spec: config.PlaceSpec,
                date_inputs: pd.DataFrame | None = None) -> pd.DataFrame:
    """Every input for every station-day of the stations in `lines`, keyed by (station, date)."""
    frame = _sorted(frame.loc[frame["station"].isin(list(lines))])
    out = frame[["station", "date", "do_mgl_mean", "temp_c_mean", "turbidity_mean", "salinity_psu_mean"]].copy()
    keys = ["station", "date"]
    for piece in (chlorophyll_state(frame, lines), days_since_high(frame, lines), fresh_onset_flag(frame, lines),
                  water_changes(frame), neighbours(frame, lines)):
        out = out.merge(piece, on=keys, how="left", validate="one_to_one")
    out = pd.concat([out, moon_phase(out["date"], spec.utc_offset_hours), season(out["date"])], axis=1)
    if spec.date_level_columns:
        if date_inputs is None:
            raise ValueError(f"Place {spec.name} needs date-level inputs {spec.date_level_columns}.")
        missing = [c for c in spec.date_level_columns if c not in date_inputs.columns]
        if missing:
            raise ValueError(f"Date-level inputs lack {missing}.")
        out = out.merge(date_inputs[["date", *spec.date_level_columns]], on="date", how="left", validate="many_to_one")
    if len(out) != len(frame):
        raise ValueError("Building inputs changed the number of station-days.")
    return out


def attach(examples: pd.DataFrame, inputs: pd.DataFrame) -> pd.DataFrame:
    """Left-join inputs onto examples, row count and order preserved; checks the team's ratio matches ours."""
    merged = examples.merge(inputs.rename(columns={"ratio": "_ratio_check"}), on=["station", "date"],
                            how="left", validate="one_to_one")
    if len(merged) != len(examples):
        raise ValueError("Attaching inputs changed the example count.")
    if len(merged) and not np.allclose(merged["ratio"], merged["_ratio_check"], rtol=0, atol=1e-12):
        raise ValueError("The team's ratio and this module's ratio disagree.")
    return merged.drop(columns="_ratio_check")


def attach_outside(examples: pd.DataFrame, outside: pd.DataFrame) -> pd.DataFrame:
    """Left-join the other builder's outside-inputs table (station, date, OUTSIDE_COLUMNS)."""
    missing = [c for c in ("station", "date", *config.OUTSIDE_COLUMNS) if c not in outside.columns]
    if missing:
        raise ValueError(f"The outside-inputs table lacks columns {missing}.")
    if outside.duplicated(["station", "date"]).any():
        raise ValueError("The outside-inputs table has duplicate (station, date) rows.")
    table = outside[["station", "date", *config.OUTSIDE_COLUMNS]]
    merged = examples.merge(table, on=["station", "date"], how="left", validate="one_to_one")
    if len(merged) != len(examples):
        raise ValueError("Attaching outside inputs changed the example count.")
    return merged
