"""PREREG section 6 inputs, each against its written definition, on made-up data, including missing cases."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

import test_pipeline_helpers as h
import config
import features

N = np.nan


def one(values: dict, station="AAA", start="2020-01-01"):
    return h.daily_frame(station, values, start)


def col(frame, column):
    return frame[column].to_numpy(dtype=float)


def same(a, b):
    np.testing.assert_allclose(np.asarray(a, dtype=float), np.asarray(b, dtype=float), rtol=0, atol=1e-12,
                               equal_nan=True)


def test_ratio_ratio_max_and_slope7():
    chla = [2, 4, N, 6, 8, 10, 12, 14, 16]
    frame = one({"chla_mean": chla, "chla_max": [x * 2 if x == x else N for x in chla]})
    out = features.chlorophyll_state(frame, {"AAA": 2.0})
    same(col(out, "ratio"), [1, 2, N, 3, 4, 5, 6, 7, 8])
    same(col(out, "ratio_max"), [2, 4, N, 6, 8, 10, 12, 14, 16])
    same(col(out, "slope7"), [N] * 7 + [(14 - 2) / 7, (16 - 4) / 7])


def test_d1_and_d3_ratio_missing_if_earlier_day_missing():
    frame = one({"chla_mean": [2, N, 4, 6, 8, 10], "chla_max": [1] * 6})
    out = features.chlorophyll_state(frame, {"AAA": 2.0})
    # ratio: 1, nan, 2, 3, 4, 5
    same(col(out, "d1_ratio"), [N, N, N, 1, 1, 1])
    same(col(out, "d3_ratio"), [N, N, N, 3 - 1, 4 - N, 5 - 2])


def test_max7_ratio_uses_measured_days_of_last_seven():
    chla = [20, 2, N, 2, 2, 2, 2, 2, 2, N]
    frame = one({"chla_mean": chla, "chla_max": [1] * 10})
    out = features.chlorophyll_state(frame, {"AAA": 2.0})
    # ratio: 10,1,nan,1,1,1,1,1,1,nan; window t-6..t
    same(col(out, "max7_ratio"), [10, 10, 10, 10, 10, 10, 10, 1, 1, 1])


def test_days_since_high_definition():
    L = 10.0
    chla = [N] * 70
    chla[0] = 15            # a high on day 0
    chla[1] = 5
    chla[3] = 10            # exactly at the line counts as high
    chla[65] = 12           # high on day 65
    frame = one({"chla_mean": chla, "chla_max": [1] * 70})
    out = col(features.days_since_high(frame, {"AAA": L}), "days_since_high")
    assert out[0] == 60          # nothing on or before t-1 (record starts) -> 60
    assert out[1] == 1           # high yesterday
    assert out[3] == 3           # today's own high is not counted (t-1 rule): last high day 0
    assert out[4] == 1
    assert out[62] == 59         # day 3 high, 59 days ago, across a gap of missing days
    assert out[63] == 60         # 60 days ago -> 60
    assert out[64] == 60         # 61 days ago -> capped at 60
    assert out[65] == 60         # high today is not yet counted
    assert out[66] == 1


def test_days_since_high_does_not_cross_stations():
    a = one({"chla_mean": [15, 5, 5], "chla_max": [1] * 3}, station="AAA")
    b = one({"chla_mean": [5, 5, 5], "chla_max": [1] * 3}, station="BBB")
    out = features.days_since_high(pd.concat([a, b]), {"AAA": 10.0, "BBB": 10.0})
    same(out.loc[out["station"] == "BBB", "days_since_high"], [60, 60, 60])


def test_fresh_onset_flag_uses_t_minus_14_to_t_minus_1():
    chla = [5.0] * 40
    chla[5] = 12
    frame = one({"chla_mean": chla, "chla_max": [1] * 40})
    fresh = features.fresh_onset_flag(frame, {"AAA": 10.0})["fresh_onset"].to_numpy()
    assert fresh[5]              # its own high is not in t-14..t-1
    assert not fresh[6] and not fresh[19]     # day 5 is 1 and 14 days back
    assert fresh[20]             # 15 days back -> fresh
    assert fresh[0]


def test_water_changes_and_missing_ends():
    frame = one({"chla_mean": [1] * 6, "chla_max": [1] * 6,
                 "do_mgl_max": [9, 9, N, 9, 9, 9], "do_mgl_min": [7, 6, 6, N, 5, 4],
                 "temp_c_mean": [10, 11, 12, 13, N, 15], "turbidity_mean": [1, 2, 3, 4, 5, 6],
                 "salinity_psu_mean": [N, 20, 20, 20, 21, 22]})
    out = features.water_changes(frame)
    same(col(out, "do_swing"), [2, 3, N, N, 4, 5])
    same(col(out, "d3_temp"), [N, N, N, 3, N, 3])
    same(col(out, "d3_turb"), [N, N, N, 3, 3, 3])
    same(col(out, "d3_sal"), [N, N, N, N, 1, 2])


def test_moon_phase_definition():
    epoch_days_sf = (pd.Timestamp("2000-01-06 20:00") - pd.Timestamp("2000-01-06 18:14")) / pd.Timedelta(days=1)
    dates = pd.Series(pd.to_datetime(["2000-01-06", "2026-07-01"]))
    sf = features.moon_phase(dates, -8)
    angle = 2 * math.pi * epoch_days_sf / 14.7652944
    assert sf["moon_sin"].iloc[0] == pytest.approx(math.sin(angle), abs=1e-12)
    assert sf["moon_cos"].iloc[0] == pytest.approx(math.cos(angle), abs=1e-12)
    # Long Island noon (UTC-5) is 17:00 UTC: before the epoch on 2000-01-06, so the phase wraps
    li = features.moon_phase(dates, -5)
    phase = (pd.Timestamp("2000-01-06 17:00") - pd.Timestamp("2000-01-06 18:14")) / pd.Timedelta(days=1)
    phase = phase % 14.7652944
    assert 14 < phase < 14.7652944
    assert li["moon_sin"].iloc[0] == pytest.approx(math.sin(2 * math.pi * phase / 14.7652944), abs=1e-12)
    later = (pd.Timestamp("2026-07-01 20:00") - pd.Timestamp("2000-01-06 18:14")) / pd.Timedelta(days=1)
    expect = 2 * math.pi * (later % 14.7652944) / 14.7652944
    assert sf["moon_cos"].iloc[1] == pytest.approx(math.cos(expect), abs=1e-9)


def test_season_is_team_day_of_year_over_365_25():
    dates = pd.Series(pd.to_datetime(["2021-01-01", "2020-12-31"]))
    out = features.season(dates)
    assert out["doy_sin"].iloc[0] == pytest.approx(math.sin(2 * math.pi / 365.25))
    assert out["doy_cos"].iloc[1] == pytest.approx(math.cos(2 * math.pi * 366 / 365.25))


def test_neighbours_each_against_own_line_and_only_taking_part():
    a = one({"chla_mean": [10, 10, N, 30], "chla_max": [1] * 4}, station="AAA")
    b = one({"chla_mean": [20, N, N, 4], "chla_max": [1] * 4}, station="BBB")
    c = one({"chla_mean": [N, N, N, 5], "chla_max": [1] * 4}, station="CCC")
    d = one({"chla_mean": [999, 999, 999, 999], "chla_max": [1] * 4}, station="DDD")   # not taking part
    lines = {"AAA": 10.0, "BBB": 40.0, "CCC": 5.0}
    out = features.neighbours(pd.concat([a, b, c, d]), lines).set_index(["station", "date"])
    day = lambda i: pd.Timestamp("2020-01-01") + pd.Timedelta(days=i)  # noqa: E731
    # day 0, station AAA: only BBB reports (ratio 0.5, below its own line 40)
    r = out.loc[("AAA", day(0))]
    assert r["nb_n_reporting"] == 1 and r["nb_mean_ratio"] == 0.5 and r["nb_max_ratio"] == 0.5 and r["nb_n_high"] == 0
    # day 0, station BBB: AAA reports ratio 1.0, at its own line (high) though below BBB's line
    r = out.loc[("BBB", day(0))]
    assert r["nb_n_reporting"] == 1 and r["nb_n_high"] == 1 and r["nb_mean_ratio"] == 1.0
    # day 1, station AAA: no other station reports -> missing mean/max, zero counts
    r = out.loc[("AAA", day(1))]
    assert r["nb_n_reporting"] == 0 and r["nb_n_high"] == 0
    assert np.isnan(r["nb_mean_ratio"]) and np.isnan(r["nb_max_ratio"])
    # day 2: nobody measured, station CCC (own value missing too)
    r = out.loc[("CCC", day(2))]
    assert r["nb_n_reporting"] == 0 and np.isnan(r["nb_max_ratio"])
    # day 3, station CCC: AAA 3.0 (high), BBB 0.1; DDD is excluded
    r = out.loc[("CCC", day(3))]
    assert r["nb_n_reporting"] == 2 and r["nb_n_high"] == 1
    assert r["nb_mean_ratio"] == pytest.approx(1.55) and r["nb_max_ratio"] == 3.0
    # DDD's own row still gets neighbours from the taking-part stations, but is itself never a neighbour
    assert out.loc[("AAA", day(3)), "nb_n_reporting"] == 2


def test_inputs_need_reindexed_frame():
    frame = one({"chla_mean": [1, 2, 3], "chla_max": [1] * 3})
    gappy = frame.drop(index=1)
    with pytest.raises(ValueError, match="calendar day"):
        features.chlorophyll_state(gappy, {"AAA": 1.0})


def test_year_inputs_require_date_level_inputs_for_sf_like_place():
    frame = h.synthetic_frame(stations=("AAA", "BBB"), end="2015-12-31")
    with pytest.raises(ValueError, match="date-level"):
        features.year_inputs(frame, {"AAA": 1.0, "BBB": 1.0}, h.SYN_SF, None)
    out = features.year_inputs(frame, {"AAA": 1.0, "BBB": 1.0}, h.SYN_LI, None)
    for c in (*config.LI_BASE_COLUMNS, *config.STATION_STATE_COLUMNS, *config.NEIGHBOUR_COLUMNS):
        assert c in out.columns
    assert len(out) == len(frame)


def test_inputs_never_look_past_day_t():
    """Changing every value after day t leaves every input on days <= t unchanged."""
    frame = h.synthetic_frame(stations=("AAA", "BBB", "CCC"), end="2016-12-31")
    lines = {"AAA": 9.0, "BBB": 14.0, "CCC": 20.0}
    t = pd.Timestamp("2016-06-15")
    base = features.year_inputs(frame, lines, h.SYN_SF, h.synthetic_date_inputs())
    changed = frame.copy()
    later = changed["date"] > t
    for c in config.MEASURED_COLUMNS:
        changed.loc[later, c] = changed.loc[later, c] * 3 + 1
    changed.loc[later & (changed.index % 7 == 0), "chla_mean"] = np.nan
    after = features.year_inputs(changed, lines, h.SYN_SF, h.synthetic_date_inputs())
    keep = base["date"] <= t
    pd.testing.assert_frame_equal(base.loc[keep].reset_index(drop=True), after.loc[keep].reset_index(drop=True))
