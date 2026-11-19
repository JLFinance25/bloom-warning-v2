"""Tests added after the independent code review (research/07-code-review-opus.md). MADE-UP data only."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import test_pipeline_helpers as h
import anchor
import config
import models
import run_study


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory):
    frame = h.synthetic_frame()
    d = tmp_path_factory.mktemp("after_review")
    run_study.run_place(frame, h.SYN_SF, d, date_inputs=h.synthetic_date_inputs(), outside=h.synthetic_outside(frame),
                        verbose=False)
    return d


def test_primary_scores_file_is_the_event_weighted_mean_of_counted_verdict_years(run_dir):
    table = pd.read_csv(run_dir / "year_table.csv")
    primary = pd.read_csv(run_dir / "primary_scores.csv").set_index("method")
    part = table.loc[table["year"].isin(h.SYN_SF.verdict_years) & (table["events"] >= 5)]
    assert len(part) > 0
    for method in (*config.MAIN_METHODS, *config.READING_METHODS):
        by_hand = float((part[method] * part["events"]).sum() / part["events"].sum())
        assert primary.loc[method, "primary_score"] == pytest.approx(by_hand, abs=1e-10)
        assert primary.loc[method, "counted_years"] == len(part)
        assert primary.loc[method, "counted_events"] == part["events"].sum()
    summary = (run_dir / "summary.txt").read_text()
    assert "Primary score of every method" in summary and "Warnings raised while fitting" in summary


def test_warnings_file_is_written_with_its_columns(run_dir):
    table = pd.read_csv(run_dir / "audit_warnings.csv")
    assert list(table.columns) == ["year", "category", "message", "count"]


def test_fitting_warnings_are_logged_per_year(tmp_path, monkeypatch):
    import warnings
    real = models.score_year

    def noisy(train, test, spec, **kwargs):
        warnings.warn("made-up warning", UserWarning)
        warnings.warn("made-up warning", UserWarning)
        return real(train, test, spec, **kwargs)

    monkeypatch.setattr(models, "score_year", noisy)
    run_study.run_place(h.synthetic_frame(), h.SYN_SF, tmp_path, date_inputs=h.synthetic_date_inputs(), verbose=False)
    table = pd.read_csv(tmp_path / "audit_warnings.csv")
    made_up = table.loc[table["message"] == "made-up warning"]
    assert len(made_up) > 0 and (made_up["count"] == 2).all() and (made_up["category"] == "UserWarning").all()


@pytest.mark.parametrize("place", ["sf", "li"])
def test_command_line_run_stops_for_either_place_when_the_anchor_fails(place, tmp_path, monkeypatch):
    monkeypatch.setattr(anchor, "run_anchor", lambda *a, **k: False)

    def must_not_run(*a, **k):
        raise AssertionError("the study ran although the anchor failed")

    monkeypatch.setattr(run_study, "run_place", must_not_run)
    assert run_study.main(["--place", place, "--out", str(tmp_path / "out")]) == 2


def test_tree_drops_and_logs_an_all_missing_input_without_changing_scores():
    """D1: a column missing on every training example is left out of the tree fit, logged, and changes no score."""
    frame = h.synthetic_frame(end="2017-01-10")
    _, train, test = run_study.year_data(frame, h.SYN_SF, 2016, h.synthetic_date_inputs(), None)
    columns = models.tree_columns(h.SYN_SF, "T3_twin")
    base_test, base_train, base_final, base_left = models.fit_tree(train, test, columns, "T3_twin")
    train2, test2 = train.assign(empty_input=np.nan), test.assign(empty_input=1.0)
    te, tr, final, left = models.fit_tree(train2, test2, [*columns, "empty_input"], "T3_twin")
    assert left == [*base_left, "empty_input"] and "empty_input" not in final and final == base_final
    np.testing.assert_array_equal(te, base_test)
    np.testing.assert_array_equal(tr, base_train)


def test_no_difference_uses_the_1_25_percent_points_on_a_case_where_the_0_625_points_disagree():
    """Made-up table chosen so the 1.25% / 98.75% points sit inside +-10% while a 0.625% / 99.375% point does not.
    The plan's rule (section 7) uses the 1.25% points, so the verdict must be NO MEANINGFUL DIFFERENCE."""
    import scoring
    rng = np.random.default_rng(102)
    t = pd.DataFrame({"year": range(2017, 2025), "examples": 1000, "events": 30,
                      "B1": .30 + rng.normal(0, .01, 8), "B2": .2})
    t["T1"] = t["B1"] * (1 + rng.normal(0, .08, 8))
    s = scoring.bootstrap_margins(t, "T1", draws=3000)
    wide_low, low, high, wide_high = np.quantile(s, [0.00625, 0.0125, 0.9875, 0.99375])
    assert -0.10 < low and high < 0.10                     # the plan's points are inside the band
    assert wide_high > 0.10 and wide_low < 0               # the wider points are not, and the try does not BEAT
    assert scoring.verdict(t, "T1", draws=3000)["verdict"] == scoring.NO_DIFFERENCE


def test_long_island_usgs_codes_map_to_the_right_measures(tmp_path):
    """The USGS codes are written out here, not read from the code under test: 32316 chlorophyll, 00010 water
    temperature, 90860 salinity, 00300 dissolved oxygen, 63680 turbidity; 00001 max, 00002 min, 00003 mean."""
    import data_li
    from test_pipeline_data_li import full_series, rdb, write_station
    parameter_name = {"32316": "chla", "00010": "temp_c", "90860": "salinity_psu", "00300": "do_mgl",
                      "63680": "turbidity"}
    statistic_name = {"00001": "max", "00002": "min", "00003": "mean"}
    series, value, expect = full_series(), {}, {}
    for k, s in enumerate(series):
        _, parameter, statistic = s.split("_")
        value[s] = float(1000 + k)
        expect[f"{parameter_name[parameter]}_{statistic_name[statistic]}"] = value[s]
    assert len(expect) == 15
    rows = [{"date": d, **{s: (value[s], "A") for s in series}} for d in ("2020-01-01", "2020-01-02")]
    write_station(tmp_path, "01311143", rdb("01311143", rows, series))
    f = data_li.load_li_frame(tmp_path, stations=("01311143",))
    for column, v in expect.items():
        assert (f[column] == v).all(), column


# ---- reading 18 follow-up: a Long Island rerun without the private SF Bay file (added after all runs were done) ----
def test_no_anchor_option_is_refused_for_sf_bay(tmp_path, monkeypatch):
    def must_not_run(*a, **k):
        raise AssertionError("the SF Bay study ran without its anchor")

    monkeypatch.setattr(run_study, "run_place", must_not_run)
    with pytest.raises(SystemExit):
        run_study.main(["--place", "sf", "--out", str(tmp_path / "out"), "--no-anchor"])


def test_no_anchor_option_skips_the_anchor_for_long_island_and_marks_the_summary(tmp_path, monkeypatch):
    import data_li

    def anchor_must_not_run(*a, **k):
        raise AssertionError("the anchor ran although --no-anchor was given")

    seen = []

    def fake_run_place(frame, spec, out_dir, **k):
        out_dir.mkdir(parents=True)
        (out_dir / "summary.txt").write_text("Place: li.\n")
        seen.append((frame, spec.name))

    monkeypatch.setattr(anchor, "run_anchor", anchor_must_not_run)
    monkeypatch.setattr(data_li, "load_li_frame", lambda log=None: "FRAME")
    monkeypatch.setattr(run_study, "run_place", fake_run_place)
    out = tmp_path / "out"
    assert run_study.main(["--place", "li", "--out", str(out), "--no-anchor"]) == 0
    assert seen == [("FRAME", "li")]
    text = (out / "summary.txt").read_text()
    assert text == run_study.NO_ANCHOR_NOTE + "\nPlace: li.\n"
    assert "ANCHOR NOT RUN" in run_study.NO_ANCHOR_NOTE
