"""PREREG sections 4 and 5 on made-up data: high line, example and label rule, cut-off, embargo, taking part."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import test_pipeline_helpers as h  # noqa: F401  (puts src/ on the path)
import config
import examples


def training_period_frame(station="AAA", start="2020-01-01", end="2020-12-31", seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, end, freq="D")
    values = rng.integers(1, 101, len(dates)).astype(float)
    return pd.DataFrame({"date": dates, "station": station, "chla_mean": values, "chla_max": values * 1.2})


def with_test_year(base: pd.DataFrame, test_values: list) -> pd.DataFrame:
    """Append days from 2021-01-01 with the given chlorophyll values (None = missing)."""
    station = base["station"].iloc[0]
    dates = pd.date_range("2021-01-01", periods=len(test_values), freq="D")
    tail = pd.DataFrame({"date": dates, "station": station,
                         "chla_mean": [np.nan if v is None else v for v in test_values]})
    tail["chla_max"] = tail["chla_mean"]
    return pd.concat([base, tail], ignore_index=True)


def test_cutoff_is_31_december_of_previous_year():
    assert examples.cutoff_for(2021) == pd.Timestamp("2020-12-31")


def test_high_line_is_sorted_position_of_values_on_or_before_cutoff():
    base = training_period_frame()
    frame = with_test_year(base, [500.0] * 40)          # huge test-year values must not move the line
    ye = examples.year_examples(frame, 2021)
    values = sorted(base["chla_mean"])
    assert ye.lines["AAA"] == values[int(0.9 * len(values))]
    frame2 = with_test_year(base, [0.5] * 40)
    assert examples.year_examples(frame2, 2021).lines == ye.lines


def test_example_and_label_rules():
    base = training_period_frame()
    line = examples.year_examples(with_test_year(base, [1.0] * 5), 2021).lines["AAA"]
    low, high = line * 0.5, line * 1.5
    test_values = [
        low, low, low, low,          # Jan 1: example, next three measured and below -> onset False
        line,                        # Jan 5: at the line -> not an example
        low, None, high, None,       # Jan 6: example; window partly measured but crosses -> onset True, part window
        low, low, None, low,         # Jan 10: example? window Jan 11-13 partly measured, no crossing -> dropped
        None,                        # Jan 14: chlorophyll missing on t -> not an example
        low, None, None, None,       # Jan 15: whole window missing -> dropped
        low, low, low, line,         # Jan 19: Jan 22 at the line counts as a crossing ("at or above")
    ]
    ye = examples.year_examples(with_test_year(base, test_values), 2021)
    test = ye.test.set_index("date")
    d = lambda s: pd.Timestamp(s)  # noqa: E731
    assert d("2021-01-01") in test.index and not test.loc[d("2021-01-01"), "onset"]
    assert d("2021-01-05") not in test.index
    assert test.loc[d("2021-01-06"), "onset"] and test.loc[d("2021-01-06"), "part_window"]
    assert test.loc[d("2021-01-06"), "n_future_measured"] == 1
    assert d("2021-01-10") not in test.index
    assert d("2021-01-14") not in test.index
    assert d("2021-01-15") not in test.index
    assert test.loc[d("2021-01-19"), "onset"]
    assert test.loc[d("2021-01-20"), "onset"] and test.loc[d("2021-01-21"), "onset"]
    assert (test["ratio"] == test["chla_mean"] / line).all()


def test_training_examples_end_21_december_and_test_examples_stay_in_year():
    frame = h.synthetic_frame(stations=("AAA",), starts={"AAA": "2019-01-01"}, end="2022-01-10", missing_share=0.0, outage=False)
    frame["chla_mean"] = np.where(frame["date"].dt.day % 5 == 0, 1000.0, 1.0)   # crossings every 5 days
    ye = examples.year_examples(frame, 2021)
    assert ye.train["date"].max() == pd.Timestamp("2020-12-21")
    assert pd.Timestamp("2020-12-22") not in set(ye.train["date"])
    assert ye.test["date"].min() == pd.Timestamp("2021-01-01")
    assert ye.test["date"].max() == pd.Timestamp("2021-12-31")      # labelled from 2022-01-01..03
    assert (ye.test["date"].dt.year == 2021).all()
    # embargo arithmetic: 10 days before 31 Dec
    assert config.EMBARGO_DAYS == 10


def test_training_labels_never_use_days_after_cutoff():
    frame = h.synthetic_frame(stations=("AAA",), starts={"AAA": "2019-01-01"}, end="2021-12-31")
    ye = examples.year_examples(frame, 2021)
    changed = frame.copy()
    after = changed["date"] > pd.Timestamp("2020-12-31")
    changed.loc[after, "chla_mean"] = 1e6
    ye2 = examples.year_examples(changed, 2021)
    pd.testing.assert_frame_equal(ye.train, ye2.train)
    assert ye.lines == ye2.lines


def test_station_takes_part_only_with_300_days_on_or_before_cutoff():
    frame = h.synthetic_frame(stations=("AAA", "BBB", "CCC"),
                              starts={"AAA": "2019-01-01", "BBB": "2020-03-07", "CCC": "2020-03-08"},
                              end="2021-06-30", missing_share=0.0, outage=False)
    frame = frame.loc[~((frame["date"] > "2020-12-31") & (frame["station"] == "AAA"))]   # AAA: no test days
    # 2020-03-07 .. 2020-12-31 is 300 days; from 2020-03-08 it is 299
    counts = examples.chla_days_before(frame, pd.Timestamp("2020-12-31"))
    assert counts["BBB"] == 300 and counts["CCC"] == 299
    ye = examples.year_examples(frame, 2021)
    assert ye.taking_part == ["AAA", "BBB"]
    assert "CCC" not in ye.lines
    assert "CCC" not in set(ye.train["station"]) and "CCC" not in set(ye.test["station"])


def test_missing_days_do_not_count_toward_taking_part():
    frame = h.synthetic_frame(stations=("AAA",), starts={"AAA": "2020-01-01"}, end="2021-03-01", missing_share=0.0, outage=False)
    keep = frame["date"] <= pd.Timestamp("2020-12-31")
    idx = frame.index[keep][:67]                       # 366 days in 2020, blank 67 -> 299 measured
    frame.loc[idx, "chla_mean"] = np.nan
    assert examples.chla_days_before(frame, pd.Timestamp("2020-12-31"))["AAA"] == 299
    assert examples.year_examples(frame, 2021).taking_part == []


def test_no_station_taking_part_gives_empty_year():
    frame = h.synthetic_frame(stations=("AAA",), starts={"AAA": "2020-10-01"}, end="2021-03-01")
    ye = examples.year_examples(frame, 2021)
    assert ye.taking_part == [] and len(ye.train) == 0 and len(ye.test) == 0


def test_part_window_count_matches_rule():
    frame = h.synthetic_frame(stations=("AAA", "BBB"), end="2016-12-31", missing_share=0.2)
    ye = examples.year_examples(frame, 2016)
    measured = frame.loc[frame["chla_mean"].notna(), ["station", "date"]]
    keys = set(zip(measured["station"], measured["date"]))
    for row in ye.test.sample(200, random_state=1).itertuples():
        n = sum((row.station, row.date + pd.Timedelta(days=k)) in keys for k in (1, 2, 3))
        assert row.n_future_measured == n
        assert row.part_window == (n < 3)
        if row.part_window:
            assert row.onset          # a partly measured window is kept only when it crosses
