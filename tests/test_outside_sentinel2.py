"""
Tests for src/outside_sentinel2.py on made-up data only (PREREG T4(a)). No network, no real files.
"""

from __future__ import annotations

import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.dont_write_bytecode = True
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import outside_sentinel2 as s2  # noqa: E402

# A made-up 20 m grid: origin (600000, 4600020), like an MGRS tile in UTM zone 18N.
T20 = (20.0, 0.0, 600000.0, 0.0, -20.0, 4600020.0)
NO_OFFSET = {b: (0.0001, 0.0) for b in s2.REFL_BANDS}


def make_scene(h=17, w=17, dn=500, scl=6):
    """DN windows: 10 m bands are (2h, 2w), 20 m bands (h, w); all water, all DN `dn`."""
    return {
        "B02": np.full((2 * h, 2 * w), dn, dtype="uint16"),
        "B03": np.full((2 * h, 2 * w), dn, dtype="uint16"),
        "B04": np.full((2 * h, 2 * w), dn, dtype="uint16"),
        "B05": np.full((h, w), dn, dtype="uint16"),
        "SCL": np.full((h, w), scl, dtype="uint8"),
    }


def centred_window(x, y):
    c0, r0, w, h = s2.window_20m(x, y, T20)
    wt = (T20[0], 0.0, T20[2] + c0 * T20[0], 0.0, T20[4], T20[5] + r0 * T20[4])
    return c0, r0, w, h, wt


# ----------------------------------------------------------------------------------------------- geometry
def test_pixel_centres_are_half_a_pixel_in():
    wt = (20.0, 0.0, 1000.0, 0.0, -20.0, 5000.0)
    xs, ys = s2.pixel_centres(wt, 2, 3)
    assert xs[0, 0] == 1010.0 and ys[0, 0] == 4990.0
    assert xs[1, 2] == 1050.0 and ys[1, 2] == 4970.0


@pytest.mark.parametrize("x,y", [(612345.6, 4512345.6), (612340.0, 4512340.0), (612350.0, 4512350.0),
                                 (600151.0, 4599869.0), (612333.3, 4512366.6)])
def test_window_holds_every_pixel_centred_within_150m(x, y):
    c0, r0, w, h, wt = centred_window(x, y)
    # brute force over a wide area of the full grid
    cols = np.arange(c0 - 30, c0 + w + 30)
    rows = np.arange(r0 - 30, r0 + h + 30)
    cc, rr = np.meshgrid(cols, rows)
    xc = T20[2] + (cc + 0.5) * 20
    yc = T20[5] - (rr + 0.5) * 20
    inside = np.hypot(xc - x, yc - y) <= 150
    assert inside.any()
    assert (cc[inside] >= c0).all() and (cc[inside] < c0 + w).all()
    assert (rr[inside] >= r0).all() and (rr[inside] < r0 + h).all()
    # and the window is tight: the margin plus at most one column/row the disc only grazes
    m = s2.WINDOW_MARGIN_PX
    assert m <= cc[inside].min() - c0 <= m + 1 and m <= c0 + w - 1 - cc[inside].max() <= m + 1
    assert m <= rr[inside].min() - r0 <= m + 1 and m <= r0 + h - 1 - rr[inside].max() <= m + 1


def test_150m_rule_counts_exactly_the_pixels_whose_centre_is_within_150m():
    x, y = 612345.0, 4512345.0
    c0, r0, w, h, wt = centred_window(x, y)
    dn = make_scene(h, w)
    xs, ys = s2.pixel_centres(wt, h, w)
    expected = int((np.hypot(xs - x, ys - y) <= 150).sum())
    out = s2.clear_water_stats(dn, wt, x, y, NO_OFFSET)
    assert out["n_clear"] == expected
    # a disc of radius 150 m holds about pi*150^2/400 = 177 pixels
    assert abs(expected - math.pi * 150 ** 2 / 400) < 12


def test_pixel_centre_exactly_at_150m_is_in_and_just_beyond_is_out():
    # station placed so that one pixel centre is exactly 150 m east of it
    wt = (20.0, 0.0, 0.0, 0.0, -20.0, 400.0)
    h = w = 20
    xs, ys = s2.pixel_centres(wt, h, w)
    x0, y0 = xs[10, 2], ys[10, 2]  # station sits on a pixel centre
    dn = make_scene(h, w)
    dn["SCL"][:] = 0
    dn["SCL"][10, 2 + 7] = 6  # centre 140 m away
    target = (10, 2 + 7)
    xs_t = xs[target]
    # move the station so that the distance to that centre is exactly 150 m
    station_x = xs_t - 150.0
    out = s2.clear_water_stats(dn, wt, station_x, y0, NO_OFFSET)
    assert out["n_clear"] == 1
    out = s2.clear_water_stats(dn, wt, station_x - 0.01, y0, NO_OFFSET)
    assert out["n_clear"] == 0


# ----------------------------------------------------------------------------------------------- classes
@pytest.mark.parametrize("cls,expected_in", [(6, True), (5, False), (7, False), (8, False), (3, False), (0, False)])
def test_only_scene_class_6_counts(cls, expected_in):
    x, y = 612345.0, 4512345.0
    c0, r0, w, h, wt = centred_window(x, y)
    dn = make_scene(h, w)
    full = s2.clear_water_stats(dn, wt, x, y, NO_OFFSET)["n_clear"]
    dn["SCL"][h // 2, w // 2] = cls  # the centre pixel is certainly within 150 m
    n = s2.clear_water_stats(dn, wt, x, y, NO_OFFSET)["n_clear"]
    assert n == (full if expected_in else full - 1)


# ----------------------------------------------------------------------------------------------- above zero
@pytest.mark.parametrize("band", ["B02", "B03", "B04", "B05"])
def test_pixel_is_dropped_when_any_band_is_not_above_zero(band):
    x, y = 612345.0, 4512345.0
    c0, r0, w, h, wt = centred_window(x, y)
    dn = make_scene(h, w, dn=1500)
    rules = {b: (0.0001, -0.1) for b in s2.REFL_BANDS}  # raw-era rule: DN 1000 is reflectance 0
    full = s2.clear_water_stats(dn, wt, x, y, rules)["n_clear"]
    i, j = h // 2, w // 2
    if band == "B05":
        dn[band][i, j] = 1000  # exactly zero reflectance: not above zero
    else:
        dn[band][2 * i:2 * i + 2, 2 * j:2 * j + 2] = 1000
    assert s2.clear_water_stats(dn, wt, x, y, rules)["n_clear"] == full - 1
    if band == "B05":
        dn[band][i, j] = 1001
    else:
        dn[band][2 * i:2 * i + 2, 2 * j:2 * j + 2] = 1001
    assert s2.clear_water_stats(dn, wt, x, y, rules)["n_clear"] == full


def test_nodata_dn_zero_is_never_clear():
    x, y = 612345.0, 4512345.0
    c0, r0, w, h, wt = centred_window(x, y)
    dn = make_scene(h, w)
    full = s2.clear_water_stats(dn, wt, x, y, NO_OFFSET)["n_clear"]
    i, j = h // 2, w // 2
    dn["B03"][2 * i, 2 * j] = 0  # one of four 10 m pixels is nodata
    assert s2.clear_water_stats(dn, wt, x, y, NO_OFFSET)["n_clear"] == full - 1


# ----------------------------------------------------------------------------------------------- 2x2 average
def test_average_2x2_onto_20m_grid():
    a = np.array([[1, 2, 10, 10], [3, 4, 10, 30], [5, 5, 7, 7], [5, 5, 7, 8]], dtype="uint16")
    out = s2.average_2x2(a)
    assert out.shape == (2, 2)
    assert out[0, 0] == 2.5 and out[0, 1] == 15.0 and out[1, 0] == 5.0 and out[1, 1] == 7.25


def test_average_2x2_marks_blocks_with_nodata_missing():
    a = np.array([[1, 2], [0, 4]], dtype="uint16")
    assert np.isnan(s2.average_2x2(a)[0, 0])


def test_10m_bands_are_averaged_not_subsampled_in_the_medians():
    x, y = 612345.0, 4512345.0
    c0, r0, w, h, wt = centred_window(x, y)
    dn = make_scene(h, w, dn=400)
    # B04 10 m pattern: each 2x2 block holds 100, 200, 300, 400 -> average 250 everywhere
    dn["B04"][0::2, 0::2] = 100
    dn["B04"][0::2, 1::2] = 200
    dn["B04"][1::2, 0::2] = 300
    dn["B04"][1::2, 1::2] = 400
    out = s2.clear_water_stats(dn, wt, x, y, NO_OFFSET)
    assert out["red"] == pytest.approx(0.0250)


# ----------------------------------------------------------------------------------------------- medians
def test_each_median_on_known_pixels():
    wt = (20.0, 0.0, 0.0, 0.0, -20.0, 60.0)  # 3 x 3 window, centre pixel centre at (30, 30)
    h = w = 3
    dn = make_scene(h, w)
    dn["SCL"][:] = 0
    dn["SCL"][1, 0] = dn["SCL"][1, 1] = dn["SCL"][1, 2] = 6  # three water pixels in the middle row
    b02 = [100, 200, 400]
    b03 = [300, 300, 300]
    b04 = [100, 300, 500]
    b05 = [300, 300, 300]
    for j in range(3):
        dn["B02"][2:4, 2 * j:2 * j + 2] = b02[j]
        dn["B03"][2:4, 2 * j:2 * j + 2] = b03[j]
        dn["B04"][2:4, 2 * j:2 * j + 2] = b04[j]
        dn["B05"][1, j] = b05[j]
    out = s2.clear_water_stats(dn, wt, 30.0, 30.0, NO_OFFSET)
    assert out["n_clear"] == 3
    ndci = [(b05[j] - b04[j]) / (b05[j] + b04[j]) for j in range(3)]  # 0.5, 0, -0.25
    assert out["ndci"] == pytest.approx(sorted(ndci)[1])
    assert out["red"] == pytest.approx(0.0300)
    assert out["green_blue"] == pytest.approx(sorted(b03[j] / b02[j] for j in range(3))[1])  # 3, 1.5, 0.75


def test_medians_use_reflectance_after_the_offset():
    wt = (20.0, 0.0, 0.0, 0.0, -20.0, 20.0)
    dn = make_scene(1, 1)
    dn["B02"][:] = 1200
    dn["B03"][:] = 1400
    dn["B04"][:] = 1100
    dn["B05"][:] = 1300
    rules = {b: (0.0001, -0.1) for b in s2.REFL_BANDS}
    out = s2.clear_water_stats(dn, wt, 10.0, 10.0, rules)
    assert out["red"] == pytest.approx(0.01)
    assert out["ndci"] == pytest.approx((0.03 - 0.01) / (0.03 + 0.01))
    assert out["green_blue"] == pytest.approx(0.04 / 0.02)


def test_no_reflectance_bands_means_zero_clear_pixels():
    wt = (20.0, 0.0, 0.0, 0.0, -20.0, 20.0)
    out = s2.clear_water_stats({"SCL": np.full((1, 1), 9, dtype="uint8")}, wt, 10.0, 10.0, NO_OFFSET)
    assert out["n_clear"] == 0 and np.isnan(out["ndci"])


# ----------------------------------------------------------------------------------------------- offset rule
RB = {"scale": 0.0001, "offset": -0.1}


@pytest.mark.parametrize("baseline", ["00.01", "02.14", "03.01"])
def test_offset_rule_before_baseline_04_is_dn_times_scale(baseline):
    s, o, _ = s2.reflectance_rule({"s2:processing_baseline": baseline, "earthsearch:boa_offset_applied": False},
                                  {"scale": 0.0001, "offset": 0}, item_min_dn=1500)
    assert (s, o) == (0.0001, 0.0)


@pytest.mark.parametrize("min_dn", [1, 300, 1050, None])
def test_offset_rule_flag_true_never_adds_listed_offset(min_dn):
    s, o, _ = s2.reflectance_rule({"s2:processing_baseline": "05.11", "earthsearch:boa_offset_applied": True},
                                  RB, item_min_dn=min_dn)
    assert (s, o) == (0.0001, 0.0)


def test_offset_rule_flag_false_raw_pixels_add_listed_offset():
    s, o, _ = s2.reflectance_rule({"s2:processing_baseline": "04.00", "earthsearch:boa_offset_applied": False},
                                  RB, item_min_dn=1026)
    assert (s, o) == (0.0001, -0.1)
    s, o, _ = s2.reflectance_rule({"s2:processing_baseline": "04.00", "earthsearch:boa_offset_applied": False},
                                  RB, item_min_dn=800)
    assert o == -0.1


def test_offset_rule_flag_false_but_dark_pixels_means_offset_already_out():
    s, o, _ = s2.reflectance_rule({"s2:processing_baseline": "05.11", "earthsearch:boa_offset_applied": False},
                                  RB, item_min_dn=799)
    assert (s, o) == (0.0001, 0.0)


def test_offset_rule_both_eras_put_dark_water_near_zero():
    """The PREREG check in miniature: darkest water ~0.01 reflectance in both eras under the chosen rule."""
    pre = s2.reflectance_rule({"s2:processing_baseline": "02.14", "earthsearch:boa_offset_applied": False},
                              {"scale": 0.0001, "offset": 0}, item_min_dn=100)
    raw = s2.reflectance_rule({"s2:processing_baseline": "04.00", "earthsearch:boa_offset_applied": False},
                              RB, item_min_dn=1090)
    out = s2.reflectance_rule({"s2:processing_baseline": "04.00", "earthsearch:boa_offset_applied": True},
                              RB, item_min_dn=100)
    assert 100 * pre[0] + pre[1] == pytest.approx(0.01)
    assert 1100 * raw[0] + raw[1] == pytest.approx(0.01)
    assert 100 * out[0] + out[1] == pytest.approx(0.01)


# ----------------------------------------------------------------------------------------------- local date
@pytest.mark.parametrize("utc,offset,expected", [
    ("2020-06-01T04:59:59Z", -5, "2020-05-31"),
    ("2020-06-01T05:00:00Z", -5, "2020-06-01"),
    ("2020-06-01T00:30:00Z", -5, "2020-05-31"),
    ("2020-01-01T03:00:00Z", -5, "2019-12-31"),
    ("2020-07-04T15:52:00Z", -5, "2020-07-04"),  # summer: fixed UTC-5, no daylight-saving hour
    ("2020-07-05T04:30:00Z", -5, "2020-07-04"),  # 00:30 EDT would be 07-05; standard clock keeps 07-04
    ("2020-06-01T07:59:59Z", -8, "2020-05-31"),
    ("2020-06-01T08:00:00Z", -8, "2020-06-01"),
])
def test_local_date_on_fixed_standard_clock(utc, offset, expected):
    assert s2.local_date(s2.parse_utc(utc), offset) == expected


def test_local_date_needs_aware_datetime():
    with pytest.raises(ValueError):
        s2.local_date(datetime(2020, 1, 1), -5)


def test_search_end_is_last_instant_of_local_end_date():
    assert s2.search_end_utc({"utc_offset_hours": -5}) == "2026-11-17T04:59:59.999Z"
    assert s2.local_date(datetime(2026, 11, 17, 4, 59, 59, tzinfo=timezone.utc), -5) == s2.END_LOCAL_DATE


def test_band_to_asset_mapping():
    assert s2.ASSETS == {"B02": "blue", "B03": "green", "B04": "red", "B05": "rededge1", "SCL": "scl"}
