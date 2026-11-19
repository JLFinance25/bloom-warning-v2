"""PREREG section 7 rules on made-up year tables: per-year score, counted years, primary score, margin, bootstrap,
bar method, years rule with ties, every verdict branch, TOO FEW EVENTS, and the descriptive extras."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score

import test_pipeline_helpers as h  # noqa: F401
import scoring


def table(events, **methods) -> pd.DataFrame:
    out = pd.DataFrame({"year": range(2017, 2017 + len(events)), "examples": [1000] * len(events), "events": events})
    for name, values in methods.items():
        out[name] = values if np.ndim(values) else [values] * len(events)
    return out


# --- per-year score -------------------------------------------------------------------------------------------

def test_year_table_is_sklearn_average_precision_per_year():
    rng = np.random.default_rng(0)
    frame = pd.DataFrame({"year": np.repeat([2017, 2018], 200), "onset": rng.random(400) < 0.1,
                          "B1": rng.random(400)})
    t = scoring.year_table(frame, ["B1"])
    for year in (2017, 2018):
        part = frame.loc[frame["year"] == year]
        assert t.loc[t["year"] == year, "B1"].item() == average_precision_score(part["onset"], part["B1"])
    assert t["events"].tolist() == [int(frame.loc[frame.year == y, "onset"].sum()) for y in (2017, 2018)]


def test_year_table_refuses_unscored_examples():
    frame = pd.DataFrame({"year": [2017] * 3, "onset": [True, False, False], "B1": [0.1, np.nan, 0.3]})
    with pytest.raises(ValueError, match="unscored"):
        scoring.year_table(frame, ["B1"])


def test_counted_years_need_five_events():
    t = table([4, 5, 30], B1=0.2, B2=0.2)
    assert scoring.counted(t)["year"].tolist() == [2018, 2019]


# --- primary score, margin, bar --------------------------------------------------------------------------------

def test_primary_score_is_event_weighted_over_counted_years():
    t = table([10, 30, 3], B1=[0.2, 0.6, 0.99], B2=0.1)
    assert scoring.primary_score(t, "B1") == pytest.approx((10 * 0.2 + 30 * 0.6) / 40)


def test_margin_is_against_the_better_bar():
    t = table([10, 10], B1=0.2, B2=0.25, T1=0.30)
    assert scoring.margin(t, "T1") == pytest.approx(0.30 / 0.25 - 1)
    t2 = table([10, 10], B1=0.3, B2=0.25, T1=0.30)
    assert scoring.margin(t2, "T1") == pytest.approx(0.0)


def test_bar_method_tie_goes_to_b1():
    assert scoring.bar_method(table([10, 10], B1=0.2, B2=0.2)) == "B1"
    assert scoring.bar_method(table([10, 10], B1=0.2, B2=0.2000001)) == "B2"


# --- bootstrap -------------------------------------------------------------------------------------------------

def test_bootstrap_is_deterministic_and_seeded():
    t = table([10, 20, 30, 15, 12, 8], B1=[.2, .3, .25, .3, .2, .1], B2=[.25, .2, .3, .2, .2, .15],
              T1=[.3, .35, .3, .33, .25, .2])
    a = scoring.bootstrap_margins(t, "T1")
    b = scoring.bootstrap_margins(t, "T1")
    c = scoring.bootstrap_margins(t, "T1", seed=1)
    assert np.array_equal(a, b) and not np.array_equal(a, c) and len(a) == 10_000


def test_bootstrap_redraws_years_and_repicks_the_bar_each_draw():
    t = table([10, 20, 30], B1=[.5, .1, .1], B2=[.1, .5, .1], T1=[.3, .3, .3])
    got = scoring.bootstrap_margins(t, "T1", draws=50, seed=5)
    rng = np.random.default_rng(5)
    picks = rng.integers(0, 3, size=(50, 3))
    events = t["events"].to_numpy(float)
    for i in range(50):
        w = np.bincount(picks[i], minlength=3) * events
        s = lambda m: (w * t[m].to_numpy()).sum() / w.sum()  # noqa: E731
        assert got[i] == pytest.approx(s("T1") / max(s("B1"), s("B2")) - 1)


# --- years rule ------------------------------------------------------------------------------------------------

def test_years_rule_ties_are_not_wins_and_required_rounds_up():
    t = table([10] * 8, B1=0.2, B2=0.1, T1=[0.3] * 5 + [0.2] * 3)      # 3 ties
    assert scoring.years_won(t, "T1") == (5, 8, 6)
    assert scoring.years_won(table([10] * 11, B1=.2, B2=.1, T1=.3), "T1")[2] == 9
    assert scoring.years_won(table([10] * 6, B1=.2, B2=.1, T1=.3), "T1")[2] == 5


def test_years_rule_uses_the_single_bar_method_not_the_best_each_year():
    # B2 is the bar method (higher primary); in year 1 B1 is higher than T1 but that does not matter
    t = table([10] * 4, B1=[0.8, 0.1, 0.1, 0.1], B2=[0.3, 0.3, 0.3, 0.3], T1=[0.35] * 4)
    assert scoring.bar_method(t) == "B2"
    assert scoring.years_won(t, "T1")[0] == 4


# --- verdict branches ------------------------------------------------------------------------------------------

def _verdict(t, method="T1"):
    return scoring.verdict(t, method, draws=2000)["verdict"]


def test_verdict_beats_by_a_large_margin():
    t = table([30] * 8, B1=[.30, .28, .31, .29, .30, .32, .27, .30], B2=.25, T1=[.42, .40, .41, .39, .43, .44, .38, .40])
    assert _verdict(t) == scoring.HELPS_LARGE


def test_verdict_beats_but_not_large():
    t = table([30] * 8, B1=[.30, .28, .31, .29, .30, .32, .27, .30], B2=.25, T1=[.34, .32, .35, .33, .34, .36, .31, .34])
    v = scoring.verdict(t, "T1", draws=2000)
    assert v["verdict"] == scoring.HELPS and v["interval_low"] > 0 and v["margin"] < 0.25


def test_verdict_years_rule_blocks_beats():
    t = table([30] * 8, B1=.30, B2=.25, T1=[.60, .60, .60, .60, .60, .29, .29, .29])   # 5 of 8 won, need 6
    v = scoring.verdict(t, "T1", draws=2000)
    assert v["interval_low"] > 0 and v["years_won"] == 5 and v["verdict"] == scoring.NOT_SHOWN


def test_verdict_no_meaningful_difference():
    t = table([30] * 8, B1=[.30, .28, .31, .29, .30, .32, .27, .30], B2=.25,
              T1=[.301, .279, .309, .291, .299, .321, .271, .299])
    assert _verdict(t) == scoring.NO_DIFFERENCE


def test_verdict_not_shown():
    t = table([30] * 8, B1=.30, B2=.25, T1=[.20, .40, .15, .45, .30, .10, .50, .30])
    assert _verdict(t) == scoring.NOT_SHOWN


def test_too_few_events_branches():
    ok = table([30] * 5, B1=.3, B2=.25, T1=.4, T2=.4, T3=.4, T4=.4)
    assert not scoring.too_few_events(ok)                      # 5 years, 150 events
    four_years = table([40] * 4 + [4], B1=.3, B2=.25, T1=.4)
    assert scoring.too_few_events(four_years)
    few_events = table([30] * 4 + [29], B1=.3, B2=.25, T1=.4)  # 149 events
    assert scoring.too_few_events(few_events)
    v = scoring.place_verdicts(few_events, draws=200)
    assert v.set_index("method").loc["T1", "verdict"] == scoring.TOO_FEW_EVENTS
    assert v.set_index("method").loc["T2", "verdict"] == scoring.NOT_RUN
    assert scoring.win_bar_summary(v) == {"blind_tries": scoring.TOO_FEW_EVENTS, "any_try": scoring.TOO_FEW_EVENTS}


def test_place_verdicts_and_win_bar():
    t = table([30] * 8, B1=[.30, .28, .31, .29, .30, .32, .27, .30], B2=.25,
              T1=[.42, .40, .41, .39, .43, .44, .38, .40], T2=.30, T3=.10)
    v = scoring.place_verdicts(t, draws=2000).set_index("method")
    assert v.loc["T1", "verdict"] == scoring.HELPS_LARGE and v.loc["T4", "verdict"] == scoring.NOT_RUN
    assert v.loc["T1", "counted_events"] == 240
    assert scoring.win_bar_summary(v.reset_index()) == {"blind_tries": "MET", "any_try": "MET"}
    only_t4 = pd.DataFrame({"method": ["T1", "T2", "T3", "T4"],
                            "verdict": [scoring.NOT_SHOWN, scoring.HELPS, scoring.NOT_SHOWN, scoring.HELPS_LARGE]})
    assert scoring.win_bar_summary(only_t4) == {"blind_tries": "NOT MET", "any_try": "MET"}


# --- descriptive extras ----------------------------------------------------------------------------------------

def test_credit_check():
    t = table([10, 10], B1=.2, B2=.3, T2=.29, T3=.4, T3_twin=.39)
    c = scoring.credit_check(t)
    assert c == {"T3_over_T3_twin": True, "T2_over_B2": False, "credit_allowed": True}
    t2 = table([10, 10], B1=.2, B2=.3, T2=.3, T3=.39, T3_twin=.39)
    assert scoring.credit_check(t2)["credit_allowed"] is False


def test_pooled_score_is_average_precision_on_all_examples():
    rng = np.random.default_rng(3)
    frame = pd.DataFrame({"onset": rng.random(300) < 0.2, "B1": rng.random(300)})
    assert scoring.pooled_scores(frame, ["B1"])["B1"] == average_precision_score(frame["onset"], frame["B1"])


def test_fresh_onset_summary_uses_only_fresh_examples():
    rng = np.random.default_rng(4)
    n = 2000
    frame = pd.DataFrame({"year": np.repeat(range(2017, 2022), n // 5), "onset": rng.random(n) < 0.1,
                          "fresh_onset": rng.random(n) < 0.5})
    frame["B1"] = rng.random(n) + frame["onset"] * 0.3
    frame["B2"] = rng.random(n)
    frame["T1"] = np.where(frame["fresh_onset"], frame["B1"] + 0.0, rng.random(n))
    out = scoring.fresh_onset_summary(frame, ["B1", "B2", "T1"], "B1").set_index("method")
    sub = frame.loc[frame["fresh_onset"]]
    expect = scoring.primary_score(scoring.year_table(sub, ["B1"]), "B1")
    assert out.loc["B1", "fresh_primary_score"] == pytest.approx(expect)
    assert out.loc["T1", "fresh_primary_score"] == pytest.approx(expect)    # same as B1 on the fresh subset
    assert not out.loc["T1", "beats_bar_on_fresh"]                          # equal is not beating


def test_decision_check_counts():
    frame = pd.DataFrame({"year": [2017] * 5 + [2018] * 3, "onset": [1, 0, 1, 0, 0, 1, 0, 0],
                          "B1": [0.9, 0.95, 0.2, 0.5, 0.8, 0.85, 0.1, 0.8]})
    out = scoring.decision_check(frame, "B1", 0.8).set_index("year")
    assert out.loc[2017, ["alarms", "events", "events_caught", "false_alarms"]].tolist() == [2, 2, 1, 1]
    assert out.loc[2018, ["alarms", "events_caught", "false_alarms"]].tolist() == [1, 1, 0]   # 0.8 is not > 0.8
    assert scoring.training_threshold(np.arange(11.0)) == pytest.approx(9.0)


def test_episodes_split_at_seven_days():
    events = pd.DataFrame({"station": ["A"] * 4 + ["B"], "date": pd.to_datetime(
        ["2020-01-01", "2020-01-07", "2020-01-14", "2020-01-30", "2020-01-02"])})
    out = scoring.episodes(events, 7)
    a = out.loc[out["station"] == "A", "episode"].tolist()
    assert a == [0, 0, 1, 2]           # 6 days apart: same; 7 days apart: new
    assert out.loc[out["station"] == "B", "episode"].tolist() == [0]


def test_station_scores():
    frame = pd.DataFrame({"station": ["A"] * 4 + ["B"] * 3, "onset": [1, 0, 0, 1, 0, 0, 0],
                          "B1": [.9, .1, .2, .5, .3, .2, .1]})
    out = scoring.station_scores(frame, ["B1"]).set_index("station")
    assert out.loc["A", "B1"] == average_precision_score([1, 0, 0, 1], [.9, .1, .2, .5])
    assert math.isnan(out.loc["B", "B1"])
