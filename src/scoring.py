"""
Scores and verdicts for the bloom-warning study (PREREG section 7). Pure functions; no file access.

Every method scores the same examples. A "year table" holds, for each test year, the number of events and each
method's average precision (scikit-learn's `average_precision_score`) in that year.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

BARS = ("B1", "B2")
MIN_EVENTS_PER_YEAR = 5
YEARS_SHARE_REQUIRED = 0.75
LARGE_MARGIN = 0.25
NO_DIFFERENCE_BAND = 0.10
BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 20261117
FAMILY_ALPHA = 0.05
N_TRIES = 4

HELPS_LARGE = "BEATS BY A LARGE MARGIN"
HELPS = "BEATS"
NO_DIFFERENCE = "NO MEANINGFUL DIFFERENCE"
NOT_SHOWN = "NOT SHOWN"


def year_table(frame: pd.DataFrame, methods: list[str]) -> pd.DataFrame:
    """One row per test year: events, examples, and each method's average precision in that year.

    `frame` has columns year, onset (bool) and one score column per method. A year with no event or no
    non-event gets NaN scores. Raises if any score is missing: every method must score every example.
    """
    for method in methods:
        if frame[method].isna().any():
            raise ValueError(f"{method} left {int(frame[method].isna().sum())} examples unscored")
    rows = []
    for year, part in frame.groupby("year", sort=True):
        y = part["onset"].to_numpy(dtype=bool)
        row = {"year": int(year), "examples": len(part), "events": int(y.sum())}
        for method in methods:
            both_classes = 0 < y.sum() < len(y)
            row[method] = float(average_precision_score(y, part[method].to_numpy())) if both_classes else math.nan
        rows.append(row)
    return pd.DataFrame(rows)


def counted(table: pd.DataFrame) -> pd.DataFrame:
    """The years that count toward verdicts: at least MIN_EVENTS_PER_YEAR events."""
    return table.loc[table["events"] >= MIN_EVENTS_PER_YEAR].reset_index(drop=True)


def primary_score(table: pd.DataFrame, method: str, multiplicity: np.ndarray | None = None) -> float:
    """Event-weighted mean of per-year average precision over counted years."""
    part = counted(table)
    weights = part["events"].to_numpy(dtype=float)
    if multiplicity is not None:
        weights = weights * multiplicity
    return float(np.sum(weights * part[method].to_numpy()) / np.sum(weights))


def bar_method(table: pd.DataFrame) -> str:
    """The bar for a place: whichever of B1 and B2 has the higher primary score. A tie goes to B1."""
    scores = {bar: primary_score(table, bar) for bar in BARS}
    return "B2" if scores["B2"] > scores["B1"] else "B1"


def margin(table: pd.DataFrame, method: str) -> float:
    best_bar = max(primary_score(table, bar) for bar in BARS)
    return primary_score(table, method) / best_bar - 1.0


def bootstrap_margins(table: pd.DataFrame, method: str, draws: int = BOOTSTRAP_DRAWS,
                      seed: int = BOOTSTRAP_SEED) -> np.ndarray:
    """Margins from resampling counted years with replacement. The bar is re-picked in each draw."""
    part = counted(table)
    n = len(part)
    rng = np.random.default_rng(seed)
    picks = rng.integers(0, n, size=(draws, n))
    multiplicity = np.zeros((draws, n))
    np.add.at(multiplicity, (np.arange(draws)[:, None], picks), 1.0)
    weights = multiplicity * part["events"].to_numpy(dtype=float)
    total = weights.sum(axis=1)

    def score(name: str) -> np.ndarray:
        return (weights * part[name].to_numpy()).sum(axis=1) / total

    best_bar = np.maximum(score("B1"), score("B2"))
    return score(method) / best_bar - 1.0


def years_won(table: pd.DataFrame, method: str) -> tuple[int, int, int]:
    """(years won against the place's one bar method, counted years, years required). A tie is not a win."""
    part = counted(table)
    bar = bar_method(table)
    won = int((part[method].to_numpy() > part[bar].to_numpy()).sum())
    required = math.ceil(YEARS_SHARE_REQUIRED * len(part))
    return won, len(part), required


def verdict(table: pd.DataFrame, method: str, draws: int = BOOTSTRAP_DRAWS, seed: int = BOOTSTRAP_SEED) -> dict:
    """The pre-registered verdict for one try at one place."""
    point = margin(table, method)
    samples = bootstrap_margins(table, method, draws=draws, seed=seed)
    tail = FAMILY_ALPHA / N_TRIES / 2.0                      # 0.625% each side: the 98.75% interval
    low, high = np.quantile(samples, [tail, 1.0 - tail])
    tost_tail = FAMILY_ALPHA / N_TRIES                       # 1.25% each side: the 97.5% interval
    tost_low, tost_high = np.quantile(samples, [tost_tail, 1.0 - tost_tail])
    won, n_years, required = years_won(table, method)
    years_ok = won >= required
    if low > 0 and years_ok:
        name = HELPS_LARGE if point >= LARGE_MARGIN else HELPS
    elif tost_low > -NO_DIFFERENCE_BAND and tost_high < NO_DIFFERENCE_BAND:
        name = NO_DIFFERENCE
    else:
        name = NOT_SHOWN
    return {
        "method": method, "bar_method": bar_method(table), "primary_score": primary_score(table, method),
        "margin": point, "interval_low": float(low), "interval_high": float(high),
        "low_end_reaches_10pct": bool(low >= 0.10),
        "years_won": won, "years_counted": n_years, "years_required": required, "verdict": name,
    }


# --------------------------------------------------------------------------------------------------------------
# Added for the study run (PREREG section 7): TOO FEW EVENTS, the place-level verdict table, pooled and
# fresh-onset scores, the decision check, episodes, scores by station, the credit check and the win bar.
# Everything below is descriptive except `place_verdicts` and `win_bar_summary`, which apply the rules above.
# --------------------------------------------------------------------------------------------------------------

TOO_FEW_EVENTS = "TOO FEW EVENTS"
NOT_RUN = "NOT RUN"
MIN_COUNTED_YEARS = 5
MIN_COUNTED_EVENTS = 150
TRIES = ("T1", "T2", "T3", "T4")
BLIND_TRIES = ("T1", "T2", "T3")


def counted_events(table: pd.DataFrame) -> int:
    return int(counted(table)["events"].sum())


def too_few_events(table: pd.DataFrame) -> bool:
    """True if the place has fewer than 5 counted years or fewer than 150 events in counted years."""
    return len(counted(table)) < MIN_COUNTED_YEARS or counted_events(table) < MIN_COUNTED_EVENTS


def safe_primary_score(table: pd.DataFrame, method: str) -> float:
    return primary_score(table, method) if len(counted(table)) else math.nan


def place_verdicts(table: pd.DataFrame, tries=TRIES, draws: int = BOOTSTRAP_DRAWS,
                   seed: int = BOOTSTRAP_SEED) -> pd.DataFrame:
    """One row per try. `table` must hold verdict years only. A try absent from the table is NOT RUN."""
    few = too_few_events(table)
    rows = []
    for method in tries:
        if method not in table.columns:
            rows.append({"method": method, "verdict": NOT_RUN})
            continue
        if few:
            usable = len(counted(table)) > 0
            rows.append({
                "method": method, "bar_method": bar_method(table) if usable else "",
                "primary_score": safe_primary_score(table, method),
                "margin": margin(table, method) if usable else math.nan,
                "years_counted": len(counted(table)), "verdict": TOO_FEW_EVENTS,
            })
            continue
        rows.append(verdict(table, method, draws=draws, seed=seed))
    out = pd.DataFrame(rows)
    out.insert(1, "counted_years", len(counted(table)))
    out.insert(2, "counted_events", counted_events(table))
    return out


def win_bar_summary(verdicts: pd.DataFrame) -> dict:
    """Jayden's win bar: at least one try at BEATS BY A LARGE MARGIN, for blind tries and for any try."""
    if (verdicts["verdict"] == TOO_FEW_EVENTS).any():
        return {"blind_tries": TOO_FEW_EVENTS, "any_try": TOO_FEW_EVENTS}
    by_method = dict(zip(verdicts["method"], verdicts["verdict"]))

    def met(names) -> str:
        return "MET" if any(by_method.get(n) == HELPS_LARGE for n in names) else "NOT MET"

    return {"blind_tries": met(BLIND_TRIES), "any_try": met(TRIES)}


def credit_check(table: pd.DataFrame) -> dict:
    """Credit to new inputs only if T3 beats T3-twin, or T2 beats B2, on the primary score (descriptive)."""
    out = {}
    for name, a, b in (("T3_over_T3_twin", "T3", "T3_twin"), ("T2_over_B2", "T2", "B2")):
        if a in table.columns and b in table.columns and len(counted(table)):
            out[name] = bool(primary_score(table, a) > primary_score(table, b))
        else:
            out[name] = None
    out["credit_allowed"] = bool(out["T3_over_T3_twin"] or out["T2_over_B2"])
    return out


def pooled_scores(frame: pd.DataFrame, methods: list[str]) -> dict[str, float]:
    """Average precision on all the examples given, pooled together (pass verdict-year examples only)."""
    y = frame["onset"].to_numpy(dtype=bool)
    if not 0 < y.sum() < len(y):
        return {m: math.nan for m in methods}
    return {m: float(average_precision_score(y, frame[m].to_numpy())) for m in methods}


def fresh_onset_summary(frame: pd.DataFrame, methods: list[str], bar: str) -> pd.DataFrame:
    """Primary score on examples flagged fresh_onset (no high day in t-14..t-1), and whether each try beats the
    place's bar method on that subset (strictly higher primary score). `frame` holds verdict-year examples."""
    subset = frame.loc[frame["fresh_onset"].to_numpy(dtype=bool)]
    table = year_table(subset, methods) if len(subset) else pd.DataFrame(columns=["year", "examples", "events"])
    bar_score = safe_primary_score(table, bar) if len(table) else math.nan
    rows = []
    for m in methods:
        score = safe_primary_score(table, m) if len(table) else math.nan
        rows.append({"method": m, "fresh_primary_score": score,
                     "fresh_counted_years": len(counted(table)) if len(table) else 0,
                     "fresh_counted_events": counted_events(table) if len(table) else 0,
                     "bar_method": bar, "beats_bar_on_fresh": bool(score > bar_score)
                     if not (math.isnan(score) or math.isnan(bar_score)) else False})
    return pd.DataFrame(rows)


def decision_check(frame: pd.DataFrame, method: str, threshold: float) -> pd.DataFrame:
    """Alarm when the score exceeds `threshold` (the model's own training 90th percentile); per year counts."""
    alarm = frame[method].to_numpy() > threshold
    onset = frame["onset"].to_numpy(dtype=bool)
    work = pd.DataFrame({"year": frame["year"].to_numpy(), "alarm": alarm, "caught": alarm & onset,
                         "false_alarm": alarm & ~onset, "event": onset})
    out = work.groupby("year", sort=True).agg(alarms=("alarm", "sum"), events=("event", "sum"),
                                              events_caught=("caught", "sum"),
                                              false_alarms=("false_alarm", "sum")).reset_index()
    out.insert(1, "method", method)
    out.insert(2, "alarm_threshold", threshold)
    return out


def training_threshold(train_scores: np.ndarray, percentile: float = 0.90) -> float:
    """The 90th percentile of a model's scores on its own training examples (numpy's default method)."""
    return float(np.quantile(np.asarray(train_scores, dtype=float), percentile))


def episodes(events: pd.DataFrame, gap_days: int = 7) -> pd.DataFrame:
    """Number events into episodes: events at one station less than `gap_days` apart share an episode.
    `events` has station and date; returns it sorted, with an `episode` id per station (0, 1, ...)."""
    out = events.sort_values(["station", "date"]).reset_index(drop=True).copy()
    gaps = out.groupby("station")["date"].diff().dt.days
    new = gaps.isna() | (gaps >= gap_days)
    out["episode"] = new.astype(int).groupby(out["station"]).cumsum() - 1
    return out


def station_scores(frame: pd.DataFrame, methods: list[str]) -> pd.DataFrame:
    """Average precision by station (pooled over the examples given), with examples and events."""
    rows = []
    for station, part in frame.groupby("station", sort=True):
        y = part["onset"].to_numpy(dtype=bool)
        row = {"station": station, "examples": len(part), "events": int(y.sum())}
        for m in methods:
            row[m] = float(average_precision_score(y, part[m].to_numpy())) if 0 < y.sum() < len(y) else math.nan
        rows.append(row)
    return pd.DataFrame(rows)
