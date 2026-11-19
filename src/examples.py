"""
The yearly design (PREREG sections 4 and 5), for any place frame.

For test year Y, cut-off C = 31 December of Y-1:
- a station takes part only if it has at least 300 non-missing `chla_mean` days dated on or before C;
- high lines L(Y) = the team's `labels.train_thresholds(frame, cutoff=C)` over the stations taking part;
- training examples = the team's `build_onset_examples(..., split="train", embargo=10)` (dates <= 21 Dec Y-1);
- test examples = `split="test"` with the same C and L(Y), keeping only dates in year Y.
The label rule itself is the team's, called unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import config

EXAMPLE_COLUMNS = ["station", "date", "chla_mean", "threshold", "ratio", "onset", "split"]


@dataclass
class YearExamples:
    year: int | None
    cutoff: pd.Timestamp
    chla_days_before_cutoff: dict[str, int]
    taking_part: list[str]
    lines: dict[str, float]
    train: pd.DataFrame
    test: pd.DataFrame
    notes: list[str] = field(default_factory=list)


def cutoff_for(year: int) -> pd.Timestamp:
    return pd.Timestamp(year=year - 1, month=12, day=31)


def chla_days_before(frame: pd.DataFrame, cutoff: pd.Timestamp) -> dict[str, int]:
    """Non-missing daily-mean chlorophyll days dated on or before the cut-off, per station (0 if none)."""
    known = frame.loc[(frame["date"] <= cutoff) & frame[config.TARGET].notna()]
    counts = known.groupby("station").size()
    return {station: int(counts.get(station, 0)) for station in sorted(frame["station"].unique())}


def stations_taking_part(counts: dict[str, int], min_days: int = config.MIN_CHLA_DAYS_TO_TAKE_PART) -> list[str]:
    return sorted(station for station, n in counts.items() if n >= min_days)


def _as_examples(rows: pd.DataFrame) -> pd.DataFrame:
    """The team's builder returns a column-less frame when there are no rows; give it the columns."""
    if rows.empty and not len(rows.columns):
        return pd.DataFrame({c: pd.Series(dtype=t) for c, t in
                             [("station", object), ("date", "datetime64[ns]"), ("chla_mean", float),
                              ("threshold", float), ("ratio", float), ("onset", bool), ("split", object)]})
    return rows[EXAMPLE_COLUMNS].copy()


def future_measured_days(frame: pd.DataFrame, examples: pd.DataFrame) -> np.ndarray:
    """How many of t+1..t+3 have measured chlorophyll, for each example (for the part-window count)."""
    measured = frame.loc[frame[config.TARGET].notna(), ["station", "date"]]
    keys = pd.MultiIndex.from_frame(measured)
    total = np.zeros(len(examples), dtype=int)
    for k in config.HORIZON_DAYS:
        probe = pd.MultiIndex.from_arrays([examples["station"], examples["date"] + pd.Timedelta(days=k)])
        total += probe.isin(keys).astype(int)
    return total


def build_examples(frame: pd.DataFrame, cutoff, embargo: int, test_year: int | None = None,
                   min_days: int = config.MIN_CHLA_DAYS_TO_TAKE_PART) -> YearExamples:
    labels = config.team().labels
    cutoff = pd.Timestamp(cutoff)
    counts = chla_days_before(frame, cutoff)
    part = stations_taking_part(counts, min_days)
    notes = []
    sub = frame.loc[frame["station"].isin(part)]
    if not part:
        notes.append("no station takes part")
        empty = _as_examples(pd.DataFrame())
        return YearExamples(test_year, cutoff, counts, part, {}, empty, empty.copy(), notes)
    lines = labels.train_thresholds(sub, cutoff=cutoff, percentile=config.LINE_PERCENTILE)
    if set(lines) != set(part):
        raise ValueError(f"High lines cover {sorted(lines)} but stations taking part are {part}.")
    train = _as_examples(labels.build_onset_examples(sub, lines, cutoff=cutoff, horizon=config.HORIZON_DAYS,
                                                     split="train", embargo=embargo))
    test = _as_examples(labels.build_onset_examples(sub, lines, cutoff=cutoff, horizon=config.HORIZON_DAYS,
                                                    split="test"))
    if test_year is not None:
        test = test.loc[test["date"].dt.year == test_year]
    for name, part_frame in (("train", train), ("test", test)):
        part_frame["n_future_measured"] = future_measured_days(frame, part_frame)
        part_frame["part_window"] = part_frame["n_future_measured"] < len(config.HORIZON_DAYS)
    train = train.sort_values(["station", "date"]).reset_index(drop=True)
    test = test.sort_values(["station", "date"]).reset_index(drop=True)
    train["onset"] = train["onset"].astype(bool)
    test["onset"] = test["onset"].astype(bool)
    return YearExamples(test_year, cutoff, counts, part, dict(lines), train, test, notes)


def year_examples(frame: pd.DataFrame, year: int) -> YearExamples:
    """Section 5's design for test year `year`."""
    return build_examples(frame, cutoff_for(year), embargo=config.EMBARGO_DAYS, test_year=year)
