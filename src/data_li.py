"""
Long Island daily frame from the five saved USGS RDB files (PREREG section 3). Reads only the saved download.

Columns in each file are `<TS_ID>_<parameter>_<statistic>`, each with a `<...>_cd` qualifier column. Rules:
- If a station has more than one series for a parameter and statistic, the one with the most non-missing
  (numeric) days in the file is used; a tie goes to the lower TS_ID. Every choice is logged.
- Values whose qualifier carries "e" (estimated) are dropped and counted. Qualifiers are split on ":"
  (e.g. "A:e", "P:[4]"); a component equal to "e" marks an estimate.
- Values whose qualifier carries "P" (provisional) are kept; their share is reported.
- A non-numeric value (e.g. "Eqp", equipment malfunction) is missing; it is counted.
- Output: one row per station and calendar day from the station's first to last file date, columns named as in
  the SF frame (`chla_mean`, `chla_max`, `do_mgl_min`, ...), station = USGS site number as text.
- A missing series raises, except those listed in `config.LI_KNOWN_ABSENT` (Shelter Island salinity), which
  become all-missing columns.
"""

from __future__ import annotations

import re
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

import config

SERIES_PATTERN = re.compile(r"^(\d+)_(\d{5})_(\d{5})$")


def read_rdb_text(text: str) -> pd.DataFrame:
    """The data table of one RDB file, every cell as text (comment and format lines removed)."""
    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    if len(lines) < 2:
        raise ValueError("RDB text has no header and format lines.")
    header, body = lines[0], lines[2:]   # lines[1] is the column-format line (5s 15s 20d ...)
    return pd.read_csv(StringIO("\n".join([header, *body])), sep="\t", dtype=str, keep_default_na=False,
                       na_values=[""])


def _qualifier_has(codes: pd.Series, flag: str) -> np.ndarray:
    return codes.fillna("").map(lambda c: flag in c.split(":")).to_numpy(dtype=bool)


def station_frame(table: pd.DataFrame, station: str, log_rows: list[dict]) -> pd.DataFrame:
    """Turn one station's RDB table into the daily frame for that station."""
    sites = set(table["site_no"].dropna().unique())
    if sites != {station}:
        raise ValueError(f"RDB for {station} holds site numbers {sorted(sites)}.")
    dates = pd.to_datetime(table["datetime"], format="%Y-%m-%d")
    if dates.duplicated().any():
        raise ValueError(f"RDB for {station} has duplicate dates.")
    series_columns = {}
    for column in table.columns:
        match = SERIES_PATTERN.match(column)
        if match:
            series_columns.setdefault((match.group(2), match.group(3)), []).append((int(match.group(1)), column))

    out = pd.DataFrame({"date": dates.to_numpy()})
    for parameter, name in config.LI_PARAMETERS.items():
        for statistic, stat_name in config.LI_STATISTICS.items():
            column_name = f"{name}_{stat_name}"
            candidates = sorted(series_columns.get((parameter, statistic), []))
            if not candidates:
                if (station, parameter) in config.LI_KNOWN_ABSENT:
                    out[column_name] = np.nan
                    log_rows.append({"station": station, "column": column_name, "parameter": parameter,
                                     "statistic": statistic, "chosen_ts_id": "", "candidates": "",
                                     "values_in_file": 0, "non_numeric_dropped": 0, "estimated_dropped": 0,
                                     "values_kept": 0, "provisional_kept": 0, "note": "no series (known absent)"})
                    continue
                raise ValueError(f"Station {station} has no series for parameter {parameter} statistic {statistic}.")
            counts = []
            for ts_id, column in candidates:
                if f"{column}_cd" not in table.columns:
                    raise ValueError(f"Station {station}: column {column} has no qualifier column.")
                numeric = pd.to_numeric(table[column], errors="coerce")
                counts.append((int(numeric.notna().sum()), ts_id, column))
            # most non-missing days; tie -> lower TS_ID (candidates are sorted by TS_ID, max keeps the first)
            best = max(counts, key=lambda item: (item[0], -item[1]))
            n_valid, ts_id, column = best
            raw = table[column]
            numeric = pd.to_numeric(raw, errors="coerce")
            non_numeric = int((raw.notna() & numeric.isna()).sum())
            codes = table[f"{column}_cd"]
            estimated = _qualifier_has(codes, "e") & numeric.notna().to_numpy()
            provisional = _qualifier_has(codes, "P")
            values = numeric.to_numpy(dtype=float).copy()
            values[estimated] = np.nan
            kept = ~np.isnan(values)
            out[column_name] = values
            if column_name == "chla_mean":
                out["_chla_mean_provisional"] = provisional & kept
            log_rows.append({
                "station": station, "column": column_name, "parameter": parameter, "statistic": statistic,
                "chosen_ts_id": str(ts_id),
                "candidates": ";".join(f"{c[1]}:{c[0]}" for c in sorted(counts, key=lambda c: c[1])),
                "values_in_file": n_valid, "non_numeric_dropped": non_numeric,
                "estimated_dropped": int(estimated.sum()), "values_kept": int(kept.sum()),
                "provisional_kept": int((provisional & kept).sum()),
                "note": "chosen of several" if len(candidates) > 1 else "",
            })

    out = out.sort_values("date").set_index("date")
    full = pd.date_range(out.index.min(), out.index.max(), freq="D")
    out = out.reindex(full)
    out.index.name = "date"
    out["_chla_mean_provisional"] = out["_chla_mean_provisional"].astype("boolean").fillna(False).astype(bool)
    out["station"] = station
    return out.reset_index()


def load_li_frame(raw_dir: Path = config.LI_RAW_DIR, stations=config.LI.stations,
                  log: dict | None = None) -> pd.DataFrame:
    """The Long Island daily frame for every station; `log` receives the series choices and counts."""
    log_rows: list[dict] = []
    parts = []
    for station in stations:
        path = Path(raw_dir) / f"usgs_dv_{station}.rdb"
        if not path.is_file():
            raise FileNotFoundError(f"Missing saved USGS file {path}")
        table = read_rdb_text(path.read_text())
        parts.append(station_frame(table, station, log_rows))
    frame = pd.concat(parts, ignore_index=True)
    columns = ["date", "station", *[f"{n}_{s}" for n in config.LI_PARAMETERS.values()
                                    for s in config.LI_STATISTICS.values()]]
    provisional = frame.pop("_chla_mean_provisional")
    if log is not None:
        series_log = pd.DataFrame(log_rows)
        log["li_series"] = series_log
        share = (frame.assign(p=provisional, m=frame["chla_mean"].notna())
                 .groupby("station").agg(chla_days=("m", "sum"), provisional_chla_days=("p", "sum")))
        share["provisional_share"] = share["provisional_chla_days"] / share["chla_days"]
        log["li_provisional_chla"] = share.reset_index()
        kept = series_log["values_kept"].sum()
        log["li_provisional_share_all_values"] = float(series_log["provisional_kept"].sum() / kept) if kept else np.nan
        log["li_estimated_dropped"] = int(series_log["estimated_dropped"].sum())
        log["li_non_numeric_dropped"] = int(series_log["non_numeric_dropped"].sum())
        log["li_negative_turbidity_mean"] = int((frame["turbidity_mean"] < 0).sum())
    return frame[columns].sort_values(["station", "date"]).reset_index(drop=True)
