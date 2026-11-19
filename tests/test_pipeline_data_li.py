"""PREREG section 3, Long Island rules, on a made-up RDB file: series choice, "e" dropped, provisional share,
known-absent salinity, daily reindex, station as text."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import test_pipeline_helpers as h  # noqa: F401
import config
import data_li


def rdb(site: str, rows: list[dict], series: list[str]) -> str:
    """series: column names like '100_32316_00003'; rows: {'date': ..., col: (value, code)}."""
    header = ["agency_cd", "site_no", "datetime"]
    for s in series:
        header += [s, f"{s}_cd"]
    lines = ["# comment line", "#", "\t".join(header), "\t".join(["5s", "15s", "20d"] + ["14n", "10s"] * len(series))]
    for r in rows:
        cells = ["USGS", site, r["date"]]
        for s in series:
            value, code = r.get(s, ("", ""))
            cells += [str(value), code]
        lines.append("\t".join(cells))
    return "\n".join(lines) + "\n"


def full_series(ts_for: dict | None = None) -> list[str]:
    out = []
    for p in config.LI_PARAMETERS:
        for s in config.LI_STATISTICS:
            out.append(f"{(ts_for or {}).get((p, s), 900)}{p[-2:]}{s[-1]}_{p}_{s}")
    return out


def write_station(tmp_path, site, text):
    (tmp_path / f"usgs_dv_{site}.rdb").write_text(text)


def base_rows(series, dates, value=1.0, code="A"):
    return [{"date": d, **{s: (value, code) for s in series}} for d in dates]


def test_series_with_most_days_is_chosen_and_logged(tmp_path):
    series = full_series()
    extra_short, extra_long = "100_32316_00003", "200_32316_00003"
    series2 = [s for s in series if not s.endswith("_32316_00003")] + [extra_short, extra_long]
    rows = base_rows(series2, ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"])
    for r in rows:
        r[extra_short] = (5.0, "A")
        r[extra_long] = (7.0, "A")
    rows[0][extra_long] = ("", "")              # long series: 3 days; short: 4 days -> short wins
    write_station(tmp_path, "01310740", rdb("01310740", rows, series2))
    log = {}
    frame = data_li.load_li_frame(tmp_path, stations=("01310740",), log=log)
    assert (frame["chla_mean"] == 5.0).all()
    chosen = log["li_series"].set_index("column").loc["chla_mean"]
    assert chosen["chosen_ts_id"] == "100" and chosen["candidates"] == "100:4;200:3"


def test_series_tie_goes_to_lower_ts_id(tmp_path):
    series = [s for s in full_series() if not s.endswith("_32316_00003")] + ["300_32316_00003", "250_32316_00003"]
    rows = base_rows(series, ["2020-01-01", "2020-01-02"])
    for r in rows:
        r["300_32316_00003"] = (3.0, "A")
        r["250_32316_00003"] = (2.5, "A")
    write_station(tmp_path, "01310740", rdb("01310740", rows, series))
    frame = data_li.load_li_frame(tmp_path, stations=("01310740",))
    assert (frame["chla_mean"] == 2.5).all()


def test_estimated_dropped_provisional_kept_non_numeric_missing(tmp_path):
    series = full_series()
    chla = [s for s in series if s.endswith("_32316_00003")][0]
    rows = base_rows(series, [f"2020-01-0{i}" for i in range(1, 7)])
    rows[0][chla] = (4.0, "A:e")       # estimated -> dropped
    rows[1][chla] = (4.0, "P")         # provisional -> kept
    rows[2][chla] = (4.0, "P:[4]")     # provisional, partial aggregation -> kept
    rows[3][chla] = ("Eqp", "P")       # non-numeric -> missing
    rows[4][chla] = (4.0, "A:<")       # censored qualifier -> kept as is
    rows[5][chla] = (4.0, "P:e")       # provisional estimate -> dropped
    write_station(tmp_path, "01311143", rdb("01311143", rows, series))
    log = {}
    frame = data_li.load_li_frame(tmp_path, stations=("01311143",), log=log)
    assert frame["chla_mean"].isna().tolist() == [True, False, False, True, False, True]
    row = log["li_series"].set_index("column").loc["chla_mean"]
    assert row["estimated_dropped"] == 2 and row["non_numeric_dropped"] == 1
    assert row["values_kept"] == 3 and row["provisional_kept"] == 2
    share = log["li_provisional_chla"].set_index("station").loc["01311143"]
    assert share["provisional_share"] == pytest.approx(2 / 3)
    assert log["li_estimated_dropped"] == 2


def test_known_absent_salinity_is_all_missing_other_absences_raise(tmp_path):
    series = [s for s in full_series() if "_90860_" not in s]
    rows = base_rows(series, ["2020-01-01", "2020-01-02"])
    write_station(tmp_path, "01304650", rdb("01304650", rows, series))
    frame = data_li.load_li_frame(tmp_path, stations=("01304650",))
    assert frame["salinity_psu_mean"].isna().all() and frame["chla_mean"].notna().all()
    write_station(tmp_path, "01303152", rdb("01303152", rows, series))
    with pytest.raises(ValueError, match="no series for parameter 90860"):
        data_li.load_li_frame(tmp_path, stations=("01303152",))


def test_reindexed_daily_columns_named_like_sf_and_station_text(tmp_path):
    series = full_series()
    rows = base_rows(series, ["2020-01-01", "2020-01-05"])
    rows[1][[s for s in series if s.endswith("_32316_00001")][0]] = (9.0, "A")
    write_station(tmp_path, "01304562", rdb("01304562", rows, series))
    frame = data_li.load_li_frame(tmp_path, stations=("01304562",))
    assert len(frame) == 5 and frame["date"].diff().dropna().dt.days.eq(1).all()
    assert frame["station"].iloc[0] == "01304562"
    for c in config.MEASURED_COLUMNS:
        assert c in frame.columns
    assert frame["chla_max"].tolist()[4] == 9.0 and frame["chla_mean"].isna().sum() == 3


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        data_li.load_li_frame(tmp_path, stations=("01304562",))
