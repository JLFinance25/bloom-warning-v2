"""
Tests for src/outside_join.py (PREREG T4: which image and which weather days feed day t). Made-up data only.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.dont_write_bytecode = True
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import outside_join as oj  # noqa: E402

ST = "01311143"


def img(image_id, date, n, ndci=0.1, red=0.02, gb=1.5, station=ST):
    return {"station": station, "image_id": image_id, "local_date": date, "n_clear_water": n,
            "s2_ndci_median": ndci, "s2_red_median": red, "s2_green_blue_median": gb}


def ex(*dates, station=ST):
    return pd.DataFrame({"station": [station] * len(dates), "date": list(dates)})


def wx_days(start, values_sun, values_wind=None, station=ST):
    dates = pd.date_range(start, periods=len(values_sun), freq="D").strftime("%Y-%m-%d")
    values_wind = values_wind if values_wind is not None else [10.0] * len(values_sun)
    return pd.DataFrame({"station": station, "local_date": dates, "wx_sun": values_sun, "wx_wind": values_wind,
                         "grid_lat": 40.5, "grid_lon": -73.75})


EMPTY_WX = wx_days("2000-01-01", [1.0])


def attach(examples, images, wx=EMPTY_WX):
    return oj.attach_outside(examples, pd.DataFrame(images), wx)


# ------------------------------------------------------------------------------------------- satellite
def test_image_dated_t_is_not_used_but_t_minus_1_is():
    out = attach(ex("2020-06-10"), [img("A", "2020-06-10", 50, ndci=0.9)])
    assert out[oj.S2_COLS].isna().all(axis=None)
    out = attach(ex("2020-06-10"), [img("A", "2020-06-10", 50, ndci=0.9), img("B", "2020-06-09", 50, ndci=0.3)])
    assert out.loc[0, "s2_ndci"] == pytest.approx(0.3)
    assert out.loc[0, "s2_age"] == 1


def test_newest_usable_image_wins():
    out = attach(ex("2020-06-10"), [img("A", "2020-06-01", 50, ndci=0.1), img("B", "2020-06-05", 50, ndci=0.5)])
    assert out.loc[0, "s2_ndci"] == pytest.approx(0.5) and out.loc[0, "s2_age"] == 5


def test_30_day_limit():
    imgs = [img("A", "2020-06-01", 50)]
    out = attach(ex("2020-07-01", "2020-07-02"), imgs)
    assert out.loc[0, "s2_age"] == 30 and out.loc[0, "s2_n_water"] == 50
    assert out.loc[1, oj.S2_COLS].isna().all()


def test_10_pixel_minimum_and_fall_back_to_older_image():
    imgs = [img("A", "2020-06-01", 10, ndci=0.1), img("B", "2020-06-05", 9, ndci=0.9)]
    out = attach(ex("2020-06-10"), imgs)
    assert out.loc[0, "s2_ndci"] == pytest.approx(0.1)
    assert out.loc[0, "s2_n_water"] == 10 and out.loc[0, "s2_age"] == 9


def test_too_few_pixels_everywhere_gives_all_five_missing():
    out = attach(ex("2020-06-10"), [img("A", "2020-06-05", 9), img("B", "2020-06-04", np.nan)])
    assert out[oj.S2_COLS].isna().all(axis=None)


def test_same_date_tie_more_pixels_wins():
    imgs = [img("S2B_X", "2020-06-05", 40, ndci=0.4), img("S2A_X", "2020-06-05", 60, ndci=0.6)]
    out = attach(ex("2020-06-10"), imgs)
    assert out.loc[0, "s2_ndci"] == pytest.approx(0.6) and out.loc[0, "s2_n_water"] == 60


def test_same_date_equal_pixels_id_that_sorts_first_wins():
    imgs = [img("S2B_18TXL_20200605_0_L2A", "2020-06-05", 50, ndci=0.2),
            img("S2A_18TXK_20200605_1_L2A", "2020-06-05", 50, ndci=0.7),
            img("S2A_18TXL_20200605_0_L2A", "2020-06-05", 50, ndci=0.9)]
    out = oj.attach_outside(ex("2020-06-10"), pd.DataFrame(imgs), EMPTY_WX, keep_image_id=True)
    assert out.loc[0, "s2_image_id"] == "S2A_18TXK_20200605_1_L2A"
    assert out.loc[0, "s2_ndci"] == pytest.approx(0.7)


def test_tie_rule_does_not_reach_back_past_a_newer_usable_date():
    imgs = [img("A", "2020-06-08", 12, ndci=0.1), img("B", "2020-06-07", 150, ndci=0.9)]
    out = attach(ex("2020-06-10"), imgs)
    assert out.loc[0, "s2_ndci"] == pytest.approx(0.1)


def test_stations_do_not_share_images_and_row_order_is_kept():
    imgs = [img("A", "2020-06-05", 50, ndci=0.5, station="01310740")]
    e = pd.DataFrame({"station": [ST, "01310740", ST], "date": ["2020-06-10", "2020-06-10", "2020-06-06"]})
    out = attach(e, imgs)
    assert list(out["station"]) == [ST, "01310740", ST]
    assert out.loc[0, oj.S2_COLS].isna().all() and out.loc[2, oj.S2_COLS].isna().all()
    assert out.loc[1, "s2_ndci"] == pytest.approx(0.5)


def test_all_five_columns_come_from_the_chosen_image():
    out = attach(ex("2020-06-10"), [img("A", "2020-06-03", 77, ndci=0.25, red=0.031, gb=1.7)])
    r = out.loc[0]
    assert (r.s2_ndci, r.s2_red, r.s2_green_blue, r.s2_n_water, r.s2_age) == (0.25, 0.031, 1.7, 77, 7)


# ------------------------------------------------------------------------------------------- weather
def test_weather_on_day_t_and_three_day_mean():
    wx = wx_days("2020-06-01", [1.0, 2.0, 6.0, 10.0], [5.0, 7.0, 9.0, 11.0])
    out = attach(ex("2020-06-03", "2020-06-04"), [], wx)
    assert out.loc[0, "wx_sun"] == 6.0 and out.loc[0, "wx_wind"] == 9.0
    assert out.loc[0, "wx_sun_3d"] == pytest.approx(3.0) and out.loc[0, "wx_wind_3d"] == pytest.approx(7.0)
    assert out.loc[1, "wx_sun_3d"] == pytest.approx(6.0)


def test_three_day_mean_missing_if_any_day_missing():
    wx = wx_days("2020-06-01", [1.0, np.nan, 6.0, 10.0, 12.0, 14.0])
    out = attach(ex("2020-06-03", "2020-06-04", "2020-06-05", "2020-06-06"), [], wx)
    assert np.isnan(out.loc[0, "wx_sun_3d"]) and np.isnan(out.loc[1, "wx_sun_3d"])
    assert out.loc[2, "wx_sun_3d"] == pytest.approx((6 + 10 + 12) / 3)
    assert out.loc[0, "wx_sun"] == 6.0  # the day-t value itself is still there


def test_absent_weather_date_counts_as_missing_day():
    wx = wx_days("2020-06-01", [1.0, 2.0, 3.0, 4.0]).drop(index=1)  # 2020-06-02 absent from the table
    out = attach(ex("2020-06-02", "2020-06-03", "2020-06-04"), [], wx)
    assert np.isnan(out.loc[0, "wx_sun"])
    assert np.isnan(out.loc[1, "wx_sun_3d"]) and np.isnan(out.loc[0, "wx_sun_3d"])
    assert np.isnan(out.loc[2, "wx_sun_3d"])  # window 06-02..06-04 still holds the absent day


def test_first_two_days_of_record_have_no_three_day_mean():
    wx = wx_days("2020-06-01", [1.0, 2.0, 3.0])
    out = attach(ex("2020-06-01", "2020-06-02", "2020-06-03"), [], wx)
    assert out["wx_sun_3d"].isna().tolist() == [True, True, False]


def test_build_grid_covers_every_station_and_date():
    g = oj.build_grid(["a", "b"], "2020-01-01", "2020-01-31")
    assert len(g) == 62 and g.groupby("station").size().tolist() == [31, 31]
