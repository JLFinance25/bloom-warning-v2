"""PREREG section 6 methods on made-up data: the B2 recipe, T1-T4 columns, the all-missing rule, every method scores
every example, and no leakage from the future or the test year into anything fitted."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

import test_pipeline_helpers as h
import config
import features
import models
import run_study

YEAR = 2016


def year(frame, spec=h.SYN_SF, outside=None, year=YEAR):
    return run_study.year_data(frame, spec, year, h.synthetic_date_inputs(), outside)


@pytest.fixture(scope="module")
def base_frame():
    return h.synthetic_frame(end="2017-01-10")


@pytest.fixture(scope="module")
def fitted(base_frame):
    outside = h.synthetic_outside(base_frame)
    ye, train, test = year(base_frame, outside=outside)
    return ye, train, test, models.score_year(train, test, h.SYN_SF, outside_available=True)


def test_every_method_scores_every_example(fitted):
    _, _, test, scores = fitted
    for name in (*config.MAIN_METHODS, *config.READING_METHODS):
        assert len(scores.test[name]) == len(test)
        assert np.isfinite(scores.test[name]).all()
    assert test[list(config.SF_BASE_COLUMNS)].isna().any().any()     # inputs really were missing somewhere


def test_b1_is_ratio(fitted):
    _, _, test, scores = fitted
    assert np.array_equal(scores.test["B1"], test["ratio"].to_numpy())


def test_b2_is_the_old_recipe_rebuilt_by_hand(fitted):
    _, train, test, scores = fitted
    columns = list(config.SF_BASE_COLUMNS)
    stations = sorted(train["station"].unique())
    marked = [c for c in columns if train[c].isna().any()]
    medians = {c: train[c].median() for c in columns}

    def matrix(frame):
        parts = [frame[c].fillna(medians[c]).to_numpy() for c in columns]
        parts += [(frame["station"] == s).astype(float).to_numpy() for s in stations]
        parts += [frame[c].isna().astype(float).to_numpy() for c in marked]
        return np.column_stack(parts)

    scaler = StandardScaler().fit(matrix(train))
    model = LogisticRegression(class_weight="balanced", random_state=42, max_iter=5000)
    model.fit(scaler.transform(matrix(train)), train["onset"].astype(int))
    expected = model.predict_proba(scaler.transform(matrix(test)))[:, 1]
    np.testing.assert_allclose(scores.test["B2"], expected, rtol=0, atol=1e-10)
    assert len(marked) > 0
    assert scores.columns["B2"] == columns + [f"station_{s}" for s in stations] + [f"{c}_missing" for c in marked]


def test_t1_t2_columns(fitted):
    _, train, _, scores = fitted
    stations = sorted(train["station"].unique())
    t1 = scores.columns["T1"]
    for c in (*config.SF_BASE_COLUMNS, *config.STATION_STATE_COLUMNS):
        assert c in t1
    for s in stations:
        assert f"station_{s}" in t1 and t1.count(f"station_{s}") == 1          # one-hots once
        assert f"station_{s}_x_moon_sin" in t1 and f"station_{s}_x_moon_cos" in t1
    assert not any(c in t1 for c in config.NEIGHBOUR_COLUMNS)
    t2 = scores.columns["T2"]
    assert set(t1) <= set(t2) and all(c in t2 for c in config.NEIGHBOUR_COLUMNS)


def test_station_moon_products_are_onehot_times_moon(fitted):
    _, train, test, _ = fitted
    stations = sorted(train["station"].unique())
    _, _, _, final = models.fit_logistic(train, test, models.logistic_columns(h.SYN_SF, "T1"), "T1", moon_products=True)
    assert final[-2 * len(stations):] == [f"station_{s}_x_moon_{m}" for s in stations for m in ("sin", "cos")]


def test_tree_columns_and_settings(fitted):
    _, train, test, scores = fitted
    t3 = scores.columns["T3"]
    assert t3 == [*config.SF_BASE_COLUMNS, *config.STATION_STATE_COLUMNS, *config.NEIGHBOUR_COLUMNS, "station_code"]
    assert not any(c.startswith("station_") and c != "station_code" for c in t3)
    assert not any(c.endswith("_missing") for c in t3)
    assert scores.columns["T3_twin"] == [*config.SF_BASE_COLUMNS, "station_code"]
    t4_expected = [c for c in (*config.SF_BASE_COLUMNS, *config.STATION_STATE_COLUMNS, *config.NEIGHBOUR_COLUMNS,
                               *config.OUTSIDE_COLUMNS) if not train[c].isna().all()] + ["station_code"]
    assert scores.columns["T4"] == t4_expected
    # T3 by hand: same settings, station as a categorical integer code, missing values left missing
    codes = {s: i for i, s in enumerate(sorted(train["station"].unique()))}
    cols = t3[:-1]
    X = lambda f: np.column_stack([f[cols].to_numpy(float), f["station"].map(codes).to_numpy(float)])  # noqa: E731
    m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=40,
                                       l2_regularization=1.0, early_stopping=False, random_state=42,
                                       categorical_features=[len(cols)]).fit(X(train), train["onset"].astype(int))
    np.testing.assert_array_equal(scores.test["T3"], m.predict_proba(X(test))[:, 1])


def test_t4_skipped_without_outside_table(base_frame):
    _, train, test = year(base_frame)
    scores = models.score_year(train, test, h.SYN_SF, outside_available=False)
    assert "T4" not in scores.test and "no outside" in scores.skipped["T4"]


def test_input_missing_on_every_training_example_is_left_out_of_logistic_models(base_frame):
    frame = base_frame.copy()
    frame.loc[frame["date"] <= pd.Timestamp("2015-12-31"), "salinity_psu_mean"] = np.nan
    _, train, test = year(frame)
    assert train["salinity_psu_mean"].isna().all() and test["salinity_psu_mean"].notna().any()
    scores = models.score_year(train, test, h.SYN_SF, outside_available=False)
    for method in ("B2", "T1", "T2"):
        assert "salinity_psu_mean" in scores.left_out[method]
        assert "salinity_psu_mean" not in scores.columns[method]
        assert "salinity_psu_mean_missing" not in scores.columns[method]
    for method in ("T1", "T2"):
        assert "d3_sal" in scores.left_out[method]
    # the tree models log it too (scikit-learn 1.9.1 cannot bin an all-missing column)
    assert "salinity_psu_mean" in scores.left_out["T3"] and "salinity_psu_mean" in scores.left_out["T3_twin"]
    for name in config.MAIN_METHODS[:-1]:
        assert np.isfinite(scores.test[name]).all()


def test_leaving_an_unsplittable_column_out_of_a_tree_changes_nothing(fitted):
    """Why the tree rule is safe: a column with no split point cannot change a tree's scores."""
    _, train, test, _ = fitted
    cols = list(config.SF_BASE_COLUMNS)
    a_te, _, _, _ = models.fit_tree(train, test, cols, "check")
    train2, test2 = train.assign(constant=1.0), test.assign(constant=np.random.default_rng(0).normal(size=len(test)))
    b_te, _, _, _ = models.fit_tree(train2, test2, cols + ["constant"], "check")
    np.testing.assert_array_equal(a_te, b_te)


def test_neighbours_all_missing_with_one_station(base_frame):
    one = base_frame.loc[base_frame["station"] == "AAA"]
    spec = config.PlaceSpec(name="one", stations=("AAA",), verdict_years=(YEAR,), outside_years=(),
                            utc_offset_hours=-5, base_columns=config.LI_BASE_COLUMNS)
    _, train, test = run_study.year_data(one, spec, YEAR, None, None)
    scores = models.score_year(train, test, spec, outside_available=False)
    assert set(scores.left_out["T2"]) >= {"nb_mean_ratio", "nb_max_ratio"}
    assert (train["nb_n_reporting"] == 0).all()
    assert np.isfinite(scores.test["T2"]).all() and np.isfinite(scores.test["T3"]).all()


def test_li_like_place_uses_b2_li_columns(base_frame):
    _, train, test = year(base_frame, spec=h.SYN_LI)
    scores = models.score_year(train, test, h.SYN_LI, outside_available=False, methods=("B2", "T3_twin"))
    assert [c for c in scores.columns["B2"] if not c.startswith("station_") and not c.endswith("_missing")] \
        == list(config.LI_BASE_COLUMNS)
    assert scores.columns["T3_twin"] == [*config.LI_BASE_COLUMNS, "station_code"]


def test_reading_rules_use_training_only(fitted):
    _, train, test, scores = fitted
    assert np.all(scores.test["base_rate"] == train["onset"].mean())
    month = test["date"].dt.month.iloc[0]
    assert scores.test["month_only"][0] == pytest.approx(train.loc[train["date"].dt.month == month, "onset"].mean())


# ------------------------------------------------------------------------------------------------------------------
# Leakage
# ------------------------------------------------------------------------------------------------------------------

def _perturb_after(frame, when, outside=None):
    out = frame.copy()
    later = out["date"] > when
    for c in config.MEASURED_COLUMNS:
        out.loc[later, c] = out.loc[later, c] * 1.7 + 3
    if outside is not None:
        outside = outside.copy()
        later_o = outside["date"] > when
        for c in config.OUTSIDE_COLUMNS:
            outside.loc[later_o, c] = outside.loc[later_o, c] + 5
    return out, outside


def test_changing_test_year_values_changes_nothing_on_the_training_side(base_frame, fitted):
    ye, train, test, scores = fitted
    outside = h.synthetic_outside(base_frame)
    changed, outside2 = _perturb_after(base_frame, pd.Timestamp("2015-12-31"), outside)
    ye2, train2, test2 = year(changed, outside=outside2)
    scores2 = models.score_year(train2, test2, h.SYN_SF, outside_available=True)
    assert ye2.lines == ye.lines and ye2.taking_part == ye.taking_part
    pd.testing.assert_frame_equal(train, train2)
    for name in scores.train:
        np.testing.assert_array_equal(scores.train[name], scores2.train[name])


def test_changing_values_after_day_t_leaves_scores_for_day_t_unchanged(base_frame, fitted):
    _, _, test, scores = fitted
    outside = h.synthetic_outside(base_frame)
    t = pd.Timestamp("2016-07-01")
    changed, outside2 = _perturb_after(base_frame, t, outside)
    _, train2, test2 = year(changed, outside=outside2)
    scores2 = models.score_year(train2, test2, h.SYN_SF, outside_available=True)
    key = ["station", "date"]
    a = test[key].assign(row=np.arange(len(test)))
    b = test2[key].assign(row2=np.arange(len(test2)))
    both = a.merge(b, on=key)
    both = both.loc[both["date"] <= t]
    assert len(both) > 0.95 * (a["date"] <= t).sum()       # a few examples near t may change label/existence
    for name in scores.test:
        np.testing.assert_array_equal(scores.test[name][both["row"]], scores2.test[name][both["row2"]])
