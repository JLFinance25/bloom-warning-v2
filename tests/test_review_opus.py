"""Independent review tests (Opus, 2026-11-17). MADE-UP data only; nothing here reads a real file.

Two kinds of test:
- "rule" tests: check a PREREG rule the builder's tests do not pin down. They should pass.
- "mutation demo" tests: plant a bug in the code (monkeypatch), run one of the BUILDER'S tests against it, and
  assert that the builder's test still passes. A passing demo means that builder test cannot catch that bug.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

import test_pipeline_helpers as h
import config
import data_li
import examples
import features
import models
import run_study
import scoring

YEAR = 2016


@pytest.fixture(scope="module")
def frame():
    return h.synthetic_frame(end="2017-01-10")


@pytest.fixture(scope="module")
def year16(frame):
    ye, train, test = run_study.year_data(frame, h.SYN_SF, YEAR, h.synthetic_date_inputs(), None)
    return ye, train, test


# ---------------------------------------------------------------------------------------------------------------
# Rule tests
# ---------------------------------------------------------------------------------------------------------------

def test_t1_scores_equal_a_hand_built_t1_with_moon_product_values(year16):
    """T1 = B2 pipeline + new columns + one-hot x moon products. Rebuilt by hand, including product VALUES."""
    _, train, test = year16
    cols = list(config.SF_BASE_COLUMNS) + list(config.STATION_STATE_COLUMNS)
    stations = sorted(train["station"].unique())
    marked = [c for c in cols if train[c].isna().any()]
    med = {c: train[c].median() for c in cols}

    def matrix(f):
        parts = [f[c].fillna(med[c]).to_numpy() for c in cols]
        onehot = [(f["station"] == s).astype(float).to_numpy() for s in stations]
        parts += onehot
        parts += [f[c].isna().astype(float).to_numpy() for c in marked]
        for o in onehot:
            parts += [o * f["moon_sin"].to_numpy(), o * f["moon_cos"].to_numpy()]
        return np.column_stack(parts)

    sc = StandardScaler().fit(matrix(train))
    lr = LogisticRegression(class_weight="balanced", random_state=42, max_iter=5000)
    lr.fit(sc.transform(matrix(train)), train["onset"].astype(int))
    expected = lr.predict_proba(sc.transform(matrix(test)))[:, 1]
    got, _, _, _ = models.fit_logistic(train, test, models.logistic_columns(h.SYN_SF, "T1"), "T1", moon_products=True)
    np.testing.assert_allclose(got, expected, rtol=0, atol=1e-9)


def test_unseen_station_at_test_time_is_scored_by_every_method(year16):
    """A test station absent from training: logistic one-hots all zero, tree code missing; every score finite."""
    _, train, test = year16
    train2 = train.loc[train["station"] != "DDD"].reset_index(drop=True)
    for method in ("B2", "T1", "T2"):
        te, _, _, cols = models.fit_logistic(train2, test, models.logistic_columns(h.SYN_SF, method), method,
                                             moon_products=method != "B2")
        assert np.isfinite(te).all() and "station_DDD" not in cols
    te, _, _, _ = models.fit_tree(train2, test, models.tree_columns(h.SYN_SF, "T3"), "T3")
    assert np.isfinite(te).all()


def test_station_not_taking_part_reaches_nothing_through_the_full_year_path():
    """DDD has < 300 chlorophyll days before the cut-off. Changing all its values changes no other input or label."""
    base = h.synthetic_frame(starts={"AAA": "2012-01-01", "BBB": "2012-01-01", "CCC": "2012-01-01",
                                     "DDD": "2015-06-01"}, end="2017-01-10")
    ye, train, test = run_study.year_data(base, h.SYN_SF, YEAR, h.synthetic_date_inputs(), None)
    assert "DDD" not in ye.taking_part
    changed = base.copy()
    ddd = changed["station"] == "DDD"
    changed.loc[ddd, "chla_mean"] = changed.loc[ddd, "chla_mean"] * 50 + 100
    _, train2, test2 = run_study.year_data(changed, h.SYN_SF, YEAR, h.synthetic_date_inputs(), None)
    pd.testing.assert_frame_equal(train, train2)
    pd.testing.assert_frame_equal(test, test2)
    assert "DDD" not in set(test["station"]) and "DDD" not in set(train["station"])


def test_verdict_interval_points_are_0_625_and_99_375_percent():
    t = pd.DataFrame({"year": range(2017, 2025), "examples": 1000, "events": [30, 12, 25, 40, 9, 18, 22, 15],
                      "B1": [.30, .28, .31, .29, .30, .32, .27, .30], "B2": .25,
                      "T1": [.34, .29, .35, .30, .34, .36, .31, .33]})
    v = scoring.verdict(t, "T1", draws=4000)
    s = scoring.bootstrap_margins(t, "T1", draws=4000)
    assert v["interval_low"] == pytest.approx(np.quantile(s, 0.00625), abs=1e-15)
    assert v["interval_high"] == pytest.approx(np.quantile(s, 0.99375), abs=1e-15)


def test_no_difference_branch_uses_the_1_25_percent_points():
    """When not BEATS, NO MEANINGFUL DIFFERENCE holds exactly when the 1.25%/98.75% points are inside +-10%."""
    rng = np.random.default_rng(1)
    t = pd.DataFrame({"year": range(2017, 2025), "examples": 1000, "events": 30,
                      "B1": .30 + rng.normal(0, .01, 8), "B2": .2})
    t["T1"] = t["B1"] * (1 + rng.normal(0, .04, 8))
    s = scoring.bootstrap_margins(t, "T1", draws=3000)
    lo, hi = np.quantile(s, [0.0125, 0.9875])
    v = scoring.verdict(t, "T1", draws=3000)
    if v["verdict"] != scoring.HELPS and v["verdict"] != scoring.HELPS_LARGE:
        assert (v["verdict"] == scoring.NO_DIFFERENCE) == (lo > -0.1 and hi < 0.1)


def test_prereg_constants_are_the_locked_values():
    """No builder test pins the seed; a wrong BOOTSTRAP_SEED would pass every builder test."""
    assert scoring.BOOTSTRAP_SEED == 20261117 and scoring.BOOTSTRAP_DRAWS == 10_000
    assert scoring.FAMILY_ALPHA / scoring.N_TRIES / 2 == pytest.approx(0.00625)
    assert scoring.MIN_EVENTS_PER_YEAR == 5 and scoring.MIN_COUNTED_YEARS == 5 and scoring.MIN_COUNTED_EVENTS == 150
    assert scoring.LARGE_MARGIN == 0.25 and scoring.NO_DIFFERENCE_BAND == 0.10 and scoring.YEARS_SHARE_REQUIRED == 0.75
    assert config.MIN_CHLA_DAYS_TO_TAKE_PART == 300 and config.EMBARGO_DAYS == 10 and config.LINE_PERCENTILE == 0.90
    assert config.DAYS_SINCE_HIGH_CAP == 60 and config.FRESH_ONSET_WINDOW_DAYS == 14 and config.EPISODE_GAP_DAYS == 7
    assert config.MOON_HALF_CYCLE_DAYS == 14.7652944 and config.MOON_EPOCH_UTC == pd.Timestamp("2000-01-06 18:14")
    assert config.SF.utc_offset_hours == -8 and config.LI.utc_offset_hours == -5
    assert config.SF.verdict_years == tuple(range(2017, 2025)) and config.LI.verdict_years == tuple(range(2015, 2026))
    assert config.LI_STATISTICS == {"00003": "mean", "00001": "max", "00002": "min"}


def test_hgb_on_an_all_missing_column(year16):
    """D1 says scikit-learn 1.9.1 refuses a column that is missing on every training example. Check it."""
    _, train, _ = year16
    X = np.column_stack([train["ratio"].to_numpy(float), np.full(len(train), np.nan)])
    m = HistGradientBoostingClassifier(**config.TREE_SETTINGS)
    try:
        m.fit(X, train["onset"].astype(int))
        raised = False
    except ValueError:
        raised = True
    if not raised:
        # if it fits, the all-missing column must not change scores (so dropping it is still harmless)
        X_test = np.column_stack([train["ratio"].to_numpy(float), np.random.default_rng(0).normal(size=len(train))])
        m2 = HistGradientBoostingClassifier(**config.TREE_SETTINGS).fit(X[:, :1], train["onset"].astype(int))
        np.testing.assert_array_equal(m.predict_proba(X_test)[:, 1], m2.predict_proba(X_test[:, :1])[:, 1])


def test_li_column_mapping_with_distinct_values(tmp_path):
    """Every (parameter, statistic) gets its own value, so any swap in the mapping shows."""
    from test_pipeline_data_li import full_series, rdb, write_station
    series = full_series()
    value = {}
    for k, s in enumerate(series):
        _, p, st = s.split("_")
        value[s] = 100 * list(config.LI_PARAMETERS).index(p) + 10 * ["00003", "00001", "00002"].index(st) + 1
    rows = [{"date": d, **{s: (value[s], "A") for s in series}} for d in ("2020-01-01", "2020-01-02")]
    write_station(tmp_path, "01311143", rdb("01311143", rows, series))
    f = data_li.load_li_frame(tmp_path, stations=("01311143",))
    expect = {"chla_mean": 1, "chla_max": 11, "chla_min": 21, "temp_c_mean": 101, "salinity_psu_mean": 201,
              "do_mgl_mean": 301, "do_mgl_max": 311, "do_mgl_min": 321, "turbidity_mean": 401}
    for c, v in expect.items():
        assert (f[c] == v).all(), c


def test_fresh_onset_counted_years_are_refiltered_on_the_subset():
    """READING CHECK (not a bug): the fresh-onset 'primary score' re-applies '>= 5 events' to the fresh subset, so a
    year counted at the place can drop out of the fresh score. Shown here so the reader can see the choice."""
    rng = np.random.default_rng(2)
    n = 400
    f = pd.DataFrame({"year": np.repeat([2017, 2018], n), "onset": False, "fresh_onset": False})
    f.loc[:9, "onset"] = True                        # 2017: 10 events, 3 fresh
    f.loc[:2, "fresh_onset"] = True
    f.loc[50:250, "fresh_onset"] = True
    f.loc[n:n + 9, "onset"] = True                   # 2018: 10 events, 10 fresh
    f.loc[n:n + 300, "fresh_onset"] = True
    f["B1"] = rng.random(len(f))
    out = scoring.fresh_onset_summary(f, ["B1"], "B1")
    assert out.loc[0, "fresh_counted_years"] == 1   # 2017 dropped: only 3 fresh events


# ---------------------------------------------------------------------------------------------------------------
# Mutation demos: each passes when the builder's test CANNOT catch the planted bug
# ---------------------------------------------------------------------------------------------------------------

def test_demo_builder_li_test_misses_a_mean_min_swap(tmp_path, monkeypatch):
    import test_pipeline_data_li as t
    monkeypatch.setattr(config, "LI_STATISTICS", {"00002": "mean", "00001": "max", "00003": "min"})
    t.test_reindexed_daily_columns_named_like_sf_and_station_text(tmp_path)        # still passes


def test_demo_builder_li_test_misses_a_parameter_swap(tmp_path, monkeypatch):
    import test_pipeline_data_li as t
    monkeypatch.setattr(config, "LI_PARAMETERS",
                        {"32316": "chla", "00300": "temp_c", "90860": "salinity_psu", "00010": "do_mgl",
                         "63680": "turbidity"})
    t.test_reindexed_daily_columns_named_like_sf_and_station_text(tmp_path)        # still passes


def test_demo_builder_scoring_tests_miss_wrong_interval_points(monkeypatch):
    import test_scoring as t
    monkeypatch.setattr(scoring, "N_TRIES", 1)       # 95% interval instead of 98.75%
    for name in ("test_verdict_beats_by_a_large_margin", "test_verdict_beats_but_not_large",
                 "test_verdict_years_rule_blocks_beats", "test_verdict_no_meaningful_difference",
                 "test_verdict_not_shown", "test_place_verdicts_and_win_bar"):
        getattr(t, name)()                           # all still pass


def test_demo_builder_moon_product_test_misses_wrong_product_values(frame, monkeypatch):
    """Plant: every product uses moon_cos. The builder's name-only test still passes."""
    import test_pipeline_models as t
    real = models.fit_logistic

    def planted(train, test, columns, method, moon_products=False):
        if not moon_products:
            return real(train, test, columns, method, moon_products)
        tr = train.assign(moon_sin=train["moon_cos"])
        te = test.assign(moon_sin=test["moon_cos"])
        return real(tr, te, columns, method, moon_products)

    monkeypatch.setattr(models, "fit_logistic", planted)
    outside = h.synthetic_outside(frame)
    ye, train, test = run_study.year_data(frame, h.SYN_SF, YEAR, h.synthetic_date_inputs(), outside)
    t.test_station_moon_products_are_onehot_times_moon((ye, train, test, None))


def test_demo_builder_tree_drop_test_does_not_exercise_the_drop_rule(frame):
    """The builder's 'unsplittable column' test adds a CONSTANT column, which fit_tree does not drop; the
    all-missing branch of fit_tree is exercised only by the left_out bookkeeping test, never for score equality."""
    _, train, test = run_study.year_data(frame, h.SYN_SF, YEAR, h.synthetic_date_inputs(), None)
    cols = list(config.SF_BASE_COLUMNS)
    _, _, final, dropped = models.fit_tree(train.assign(constant=1.0), test.assign(constant=2.0),
                                           cols + ["constant"], "check")
    assert "constant" in final and dropped == []
