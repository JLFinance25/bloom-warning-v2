"""The whole run on made-up data: byte-identical outputs on two runs, output contents, and the run's gates
(anchor first for SF, outputs under data/processed for SF, environment check)."""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score

import test_pipeline_helpers as h
import config
import models
import run_study
import scoring


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    frame = h.synthetic_frame()
    dates = h.synthetic_date_inputs()
    outside = h.synthetic_outside(frame)
    out = []
    for name in ("first", "second"):
        d = tmp_path_factory.mktemp(name)
        result = run_study.run_place(frame, h.SYN_SF, d, date_inputs=dates, outside=outside, verbose=False)
        out.append((d, result))
    return frame, dates, outside, out


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_two_runs_give_byte_identical_files(runs):
    *_, out = runs
    (a, _), (b, _) = out
    names = sorted(p.name for p in a.iterdir())
    assert names == sorted(p.name for p in b.iterdir())
    for required in ("predictions.csv", "year_table.csv", "verdicts.csv", "station_scores.csv", "decision_check.csv",
                     "episodes.csv", "audit_years.csv", "audit_lines.csv", "audit_missing.csv", "audit_left_out.csv",
                     "fresh_onset.csv", "pooled.csv", "summary.txt", "audit_satellite.csv"):
        assert required in names
    for name in names:
        assert digest(a / name) == digest(b / name), name


def test_predictions_hold_every_method_for_every_example(runs):
    *_, out = runs
    pred = pd.read_csv(out[0][0] / "predictions.csv", dtype={"station": str})
    for m in (*config.MAIN_METHODS, *config.READING_METHODS):
        assert m in pred.columns and pred[m].notna().all()
    assert list(pred.columns[:9]) == ["place", "year", "station", "date", "onset", "verdict_year",
                                      "counted_in_verdict", "fresh_onset", "part_window"]
    events = pred.groupby("year")["onset"].sum()
    expect = pred["year"].map(lambda y: y in h.SYN_SF.verdict_years and events[y] >= 5)
    assert (pred["counted_in_verdict"] == expect).all()
    assert not pred.loc[pred["year"] == 2020, "verdict_year"].any()


def test_year_table_recomputes_from_predictions(runs):
    *_, out = runs
    pred = pd.read_csv(out[0][0] / "predictions.csv")
    yt = pd.read_csv(out[0][0] / "year_table.csv")
    for row in yt.itertuples():
        part = pred.loc[pred["year"] == row.year]
        assert row.T2 == pytest.approx(average_precision_score(part["onset"], part["T2"]), abs=1e-11)
        assert row.events == part["onset"].sum()


def test_verdicts_use_verdict_years_only(runs):
    *_, out = runs
    result = out[0][1]
    vt = result["year_table"].loc[result["year_table"]["verdict_year"]].drop(columns=["verdict_year", "counted"])
    expect = scoring.place_verdicts(vt.reset_index(drop=True))
    got = result["verdicts"]
    assert got["verdict"].tolist() == expect["verdict"].tolist()
    np.testing.assert_allclose(got["margin"], expect["margin"])
    assert (got["counted_events"] == vt.loc[vt["events"] >= 5, "events"].sum()).all()


def test_decision_check_threshold_is_training_90th_percentile(runs):
    frame, dates, outside, out = runs
    ye, train, test = run_study.year_data(frame, h.SYN_SF, 2016, dates, outside)
    dc = pd.read_csv(out[0][0] / "decision_check.csv")
    row = dc.loc[(dc["year"] == 2016) & (dc["method"] == "B1")].iloc[0]
    assert row["alarm_threshold"] == pytest.approx(np.quantile(train["ratio"], 0.9), abs=1e-11)
    assert row["alarms"] == (test["ratio"] > row["alarm_threshold"]).sum()


def test_episodes_file_matches_events(runs):
    *_, out = runs
    pred = pd.read_csv(out[0][0] / "predictions.csv", parse_dates=["date"], dtype={"station": str})
    ep = pd.read_csv(out[0][0] / "episodes.csv")
    assert ep["events"].sum() == pred["onset"].sum()
    assert ep["episodes_starting"].sum() <= ep["events"].sum()
    assert ep["part_window_events"].sum() == (pred["onset"] & pred["part_window"]).sum()


def test_summary_states_t4_not_blind(runs):
    *_, out = runs
    text = (out[0][0] / "summary.txt").read_text()
    assert "NOT blind" in text and "probability" in text


def test_t4_skipped_and_too_few_events_end_to_end(tmp_path):
    frame = h.synthetic_frame(end="2016-12-31")
    spec = config.PlaceSpec(name="li", stations=h.SYN_LI.stations, verdict_years=(2015, 2016), outside_years=(),
                            utc_offset_hours=-5, base_columns=config.LI_BASE_COLUMNS)
    result = run_study.run_place(frame, spec, tmp_path, verbose=False)
    v = result["verdicts"].set_index("method")
    assert v.loc["T4", "verdict"] == scoring.NOT_RUN
    assert v.loc["T1", "verdict"] == scoring.TOO_FEW_EVENTS
    text = (tmp_path / "summary.txt").read_text()
    assert "T4 skipped" in text and "B2-LI" in text
    assert "T4" not in pd.read_csv(tmp_path / "predictions.csv").columns


def test_audit_only_fits_nothing(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("audit-only must not fit")
    monkeypatch.setattr(models, "score_year", boom)
    frame = h.synthetic_frame(end="2016-12-31")
    run_study.run_place(frame, h.SYN_LI, tmp_path, audit_only=True, verbose=False)
    assert (tmp_path / "audit_years.csv").exists() and not (tmp_path / "predictions.csv").exists()


def test_missing_station_raises(tmp_path):
    frame = h.synthetic_frame(stations=("AAA", "BBB"), end="2015-12-31")
    with pytest.raises(ValueError, match="absent"):
        run_study.run_place(frame, h.SYN_LI, tmp_path, audit_only=True, verbose=False)


def test_sf_refuses_to_run_without_anchor(tmp_path):
    import anchor
    assert not anchor.passed_in_this_process()
    spec = config.PlaceSpec(name="sf", stations=h.SYN_SF.stations, verdict_years=(2015,), outside_years=(),
                            utc_offset_hours=-8, base_columns=config.SF_BASE_COLUMNS,
                            date_level_columns=config.SF_DATE_LEVEL_COLUMNS, requires_anchor=True)
    with pytest.raises(RuntimeError, match="anchor"):
        run_study.run_place(h.synthetic_frame(end="2015-12-31"), spec, tmp_path, date_inputs=h.synthetic_date_inputs())


def test_sf_outputs_only_under_processed(tmp_path):
    with pytest.raises(ValueError, match="processed"):
        run_study.check_output_dir(config.SF, tmp_path / "elsewhere")
    assert not (tmp_path / "elsewhere").exists()


def test_environment_check(monkeypatch):
    monkeypatch.setenv("OMP_NUM_THREADS", "1")
    config.check_environment(verbose=False)
    monkeypatch.setitem(config.REQUIRED_ENVIRONMENT, "numpy", "0.0.0")
    with pytest.raises(RuntimeError, match="numpy"):
        config.check_environment(verbose=False)
    monkeypatch.setitem(config.REQUIRED_ENVIRONMENT, "numpy", np.__version__)
    monkeypatch.setenv("OMP_NUM_THREADS", "4")
    with pytest.raises(RuntimeError, match="OMP_NUM_THREADS"):
        config.check_environment(verbose=False)


def test_outside_table_loaded_from_csv_joins_by_station_and_date(tmp_path):
    frame = h.synthetic_frame(stations=("AAA", "BBB"), end="2018-12-31")
    outside = h.synthetic_outside(frame)
    outside["station"] = outside["station"].map({"AAA": "001", "BBB": "002"})
    frame["station"] = frame["station"].map({"AAA": "001", "BBB": "002"})
    path = tmp_path / "outside.csv"
    outside.assign(date=outside["date"].dt.strftime("%Y-%m-%d")).to_csv(path, index=False)
    loaded = run_study.load_outside(str(path))
    assert loaded["station"].iloc[0] == "001"
    spec = config.PlaceSpec(name="x", stations=("001", "002"), verdict_years=(2018,), outside_years=(),
                            utc_offset_hours=-5, base_columns=config.LI_BASE_COLUMNS)
    _, train, test = run_study.year_data(frame, spec, 2018, None, loaded)
    merged = test.merge(outside, on=["station", "date"], suffixes=("", "_src"))
    np.testing.assert_allclose(merged["wx_sun"], merged["wx_sun_src"])
    assert test["s2_ndci"].notna().any() and train["wx_wind"].notna().all()
    with pytest.raises(ValueError, match="lacks"):
        bad = tmp_path / "bad.csv"
        outside.drop(columns="s2_age").to_csv(bad, index=False)
        run_study.load_outside(str(bad))
