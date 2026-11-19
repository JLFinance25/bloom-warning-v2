# EXTRACT for the public copy. This is not the team's whole file.
# Source: the team's `model3/data/raw/model3_hab/code/labels.py` at commit c7a2c32 (the team's repository is private).
# SHA-256 of the source file: 07bc8cee452addd4281a00bb4aaef5a02f594ace8e5d64ae43abec38e5ea8c71
# Kept: only the parts the Long Island run uses (in some files, nothing), copied line for line. Left out:
# everything else, because the team's full files describe the restricted San Francisco Bay sensor data. Text
# marked "[Public copy: ...]" was changed or added by this project. See team_code/README.md.

from __future__ import annotations
import pandas as pd


TRAIN_CUTOFF = "2024-08-16"  # [Public copy: the team's trailing note is left out]


THRESHOLD_PERCENTILE = 0.90


ONSET_HORIZON_DAYS = (1, 2, 3)


EMBARGO_DAYS = 7  # [Public copy: the team's trailing note is left out]


TARGET = "chla_mean"


def train_thresholds(df: pd.DataFrame, cutoff=TRAIN_CUTOFF,
                     percentile=THRESHOLD_PERCENTILE) -> dict[str, float]:
    """
    Per-station threshold, fitted on TRAINING ROWS ONLY.

    Uses the sorted-index convention `sorted(v)[int(p * len(v))]`, matching verify_onset_lift.py.

    [Public copy: part of the team's note is left out here. It describes the restricted San Francisco Bay sensor data.]
    """
    thresholds = {}
    train = df[(df["date"] <= pd.Timestamp(cutoff)) & df[TARGET].notna()]
    for station, group in train.groupby("station"):
        values = sorted(group[TARGET])
        thresholds[station] = values[int(percentile * len(values))]
    return thresholds


def build_onset_examples(df: pd.DataFrame, thresholds: dict[str, float] | None = None,
                         cutoff=TRAIN_CUTOFF, horizon=ONSET_HORIZON_DAYS,
                         split="test", embargo=0) -> pd.DataFrame:
    """
    Build the onset-warning task: on days a station is BELOW its threshold, does it cross within
    `horizon` days?

    Returns one row per (station, date) with columns: station, date, chla_mean, threshold, ratio,
    onset, split.

    `ratio` = **TODAY's** chla_mean / threshold. Because every row is a currently-below-threshold day,
    using the same day's reading predicts a TRANSITION rather than restating a level, so this is not
    the persistence tautology.

    `embargo`: days to exclude immediately before the cutoff from the TRAIN split. Pass
    embargo=EMBARGO_DAYS for a clean split when you build the actual model. Both docs mandate >=7.

    `split` must be "train" or "test" — anything else used to be accepted silently, returning rows
    from the whole record stamped with whatever string was passed, with no cutoff/embargo filter
    applied at all. That's the exact failure this being "the single source of truth" exists to
    prevent, so it's now a ValueError instead.

    A row whose horizon window is only PARTIALLY observed (1 or 2 of the 3 future days missing, not
    all 3) used to be labelled False whenever the observed subset stayed below threshold — a
    censored outcome recorded as a hard negative, since the missing day(s) could have crossed.
    Fixed 2026-08-07: a partial-horizon row is now kept only if it's already a confirmed True (a
    crossing found in the observed subset is real evidence regardless of what's missing); a
    partial-horizon row that would otherwise be False is dropped instead of mislabelled.

    [Public copy: part of the team's note is left out here. It describes the restricted San Francisco Bay sensor data.]
    """
    if split not in ("train", "test"):
        raise ValueError(f"split must be 'train' or 'test', got {split!r}")

    if thresholds is None:
        thresholds = train_thresholds(df, cutoff=cutoff)

    cutoff_ts = pd.Timestamp(cutoff)
    rows = []

    for station, group in df.groupby("station", sort=True):
        threshold = thresholds[station]
        group = group.sort_values("date").set_index("date")
        series = group[TARGET]

        for day, value in series.items():
            if pd.isna(value) or value >= threshold:
                continue

            if split == "test" and day <= cutoff_ts:
                continue
            if split == "train":
                if day > cutoff_ts:
                    continue
                if embargo and day > cutoff_ts - pd.Timedelta(days=embargo):
                    continue

            future_raw = [series.get(day + pd.Timedelta(days=k)) for k in horizon]
            future = [f for f in future_raw if f is not None and not pd.isna(f)]
            if not future:
                continue

            onset = any(f >= threshold for f in future)
            # A confirmed crossing is valid evidence even from a partial horizon — missing days
            # afterward can't retract it. But a NEGATIVE label from a partial horizon is censored,
            # not observed: the missing day(s) could have crossed. Only a False built from every
            # horizon day observed is safe to keep; drop the rest rather than mislabel them.
            if not onset and len(future) < len(horizon):
                continue

            rows.append({
                "station": station,
                "date": day,
                TARGET: value,
                "threshold": threshold,
                "ratio": value / threshold,
                "onset": onset,
                "split": split,
            })

    return pd.DataFrame(rows)
