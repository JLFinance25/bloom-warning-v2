"""
Tests for src/outside_weather.py request settings and reply parsing (made-up replies, no network).
"""

from __future__ import annotations

import sys
import urllib.parse
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.dont_write_bytecode = True
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import outside_weather as ow  # noqa: E402


def test_fixed_offset_zone_names_use_posix_sign():
    assert ow.tz_name(-5) == "Etc/GMT+5"
    assert ow.tz_name(-8) == "Etc/GMT+8"
    assert ow.tz_name(0) == "Etc/GMT"


def test_request_pins_era5_fixed_clock_and_variables():
    q = urllib.parse.parse_qs(urllib.parse.urlparse(ow.request_url(40.6, -73.6, "Etc/GMT+5")).query)
    assert q["models"] == ["era5"]
    assert q["timezone"] == ["Etc/GMT+5"]
    assert q["daily"] == ["shortwave_radiation_sum,wind_speed_10m_max"]
    assert q["start_date"] == ["2012-12-30"] and q["end_date"] == ["2026-11-16"]
    assert q["cell_selection"] == ["nearest"]


def test_parse_reply_keeps_grid_cell_and_rejects_wrong_offset():
    reply = {"latitude": 40.5, "longitude": -73.75, "utc_offset_seconds": -18000,
             "daily": {"time": ["2020-01-01", "2020-01-02"], "shortwave_radiation_sum": [5.0, None],
                       "wind_speed_10m_max": [20.0, 21.0]}}
    rows = ow.parse_reply("01311143", reply, -18000)
    assert rows[0] == {"station": "01311143", "local_date": "2020-01-01", "wx_sun": 5.0, "wx_wind": 20.0,
                       "grid_lat": 40.5, "grid_lon": -73.75}
    assert rows[1]["wx_sun"] is None
    reply["utc_offset_seconds"] = -14400  # a daylight-saving reply must be refused
    with pytest.raises(ValueError):
        ow.parse_reply("01311143", reply, -18000)
