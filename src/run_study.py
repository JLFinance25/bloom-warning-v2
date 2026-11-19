"""
The study run (PREREG sections 5 to 7), one place at a time.

    OMP_NUM_THREADS=1 .venv/bin/python src/run_study.py --place sf --out data/processed/sf_run1
    OMP_NUM_THREADS=1 .venv/bin/python src/run_study.py --place li --out data/processed/li_run1 [--outside t4.csv]
    ... --audit-only    loads data, builds examples and inputs, writes the audit files; fits and scores nothing.

Run from the command line, either place refuses to start unless the anchor (section 5) passes in the same
process (the anchor needs the private SF Bay file). SF writes only under data/processed/. Every run prints the environment and fails if it differs from section 6. Output CSVs use the
float format %.12g, sorted rows, and "\n" line ends, so two runs give byte-identical files.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
import examples as examples_mod  # noqa: E402
import features  # noqa: E402
import models  # noqa: E402
import scoring  # noqa: E402

ALL_INPUTS = sorted(set(config.SF_BASE_COLUMNS) | set(config.STATION_STATE_COLUMNS) | set(config.NEIGHBOUR_COLUMNS))


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, float_format=config.CSV_FLOAT_FORMAT, date_format="%Y-%m-%d",
                 lineterminator="\n")


def check_output_dir(spec: config.PlaceSpec, out_dir: Path) -> Path:
    out_dir = Path(out_dir).resolve()
    if spec.outputs_under_processed_only and not out_dir.is_relative_to(config.PROCESSED_DIR.resolve()):
        raise ValueError(f"{spec.name} outputs must go under {config.PROCESSED_DIR}; got {out_dir}.")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def year_data(frame: pd.DataFrame, spec: config.PlaceSpec, year: int, date_inputs: pd.DataFrame | None,
              outside: pd.DataFrame | None):
    """Examples and every input for one test year."""
    ye = examples_mod.year_examples(frame, year)
    if not ye.taking_part:
        return ye, ye.train, ye.test
    inputs = features.year_inputs(frame, ye.lines, spec, date_inputs)
    train = features.attach(ye.train, inputs)
    test = features.attach(ye.test, inputs)
    if outside is not None:
        train = features.attach_outside(train, outside)
        test = features.attach_outside(test, outside)
    return ye, train, test


def _audit_rows(spec, year, ye, train, test):
    year_row = {
        "year": year, "verdict_year": year in spec.verdict_years, "cutoff": ye.cutoff.date().isoformat(),
        "stations_taking_part": ";".join(ye.taking_part), "n_stations": len(ye.taking_part),
        "train_examples": len(train), "train_events": int(train["onset"].sum()) if len(train) else 0,
        "train_part_window_events": int((train["onset"] & train["part_window"]).sum()) if len(train) else 0,
        "test_examples": len(test), "test_events": int(test["onset"].sum()) if len(test) else 0,
        "test_part_window_events": int((test["onset"] & test["part_window"]).sum()) if len(test) else 0,
        "notes": "; ".join(ye.notes),
    }
    line_rows = [{"year": year, "station": s, "chla_days_before_cutoff": n, "taking_part": s in ye.taking_part,
                  "high_line": ye.lines.get(s, np.nan)} for s, n in ye.chla_days_before_cutoff.items()]
    missing_rows = []
    columns = [c for c in ALL_INPUTS + list(config.OUTSIDE_COLUMNS) if c in train.columns or c in test.columns]
    for split, part in (("train", train), ("test", test)):
        for c in columns:
            if c in part.columns:
                missing_rows.append({"year": year, "split": split, "input": c, "missing": int(part[c].isna().sum()),
                                     "examples": len(part)})
    return year_row, line_rows, missing_rows


def run_place(frame: pd.DataFrame, spec: config.PlaceSpec, out_dir: Path, date_inputs: pd.DataFrame | None = None,
              outside: pd.DataFrame | None = None, audit_only: bool = False, extra_audit: dict | None = None,
              draws: int = scoring.BOOTSTRAP_DRAWS, verbose: bool = True) -> dict:
    if spec.requires_anchor:
        import anchor
        if not anchor.passed_in_this_process():
            raise RuntimeError(f"Refusing to run {spec.name}: the anchor has not passed in this process.")
    out_dir = check_output_dir(spec, out_dir)
    missing_stations = sorted(set(spec.stations) - set(frame["station"].unique()))
    if missing_stations:
        raise ValueError(f"Stations {missing_stations} are absent from the {spec.name} frame.")
    frame = frame.loc[frame["station"].isin(spec.stations)].sort_values(["station", "date"]).reset_index(drop=True)

    year_rows, line_rows, missing_rows, left_out_rows, decision_rows, predictions = [], [], [], [], [], []
    warning_rows = []
    for year in spec.years:
        ye, train, test = year_data(frame, spec, year, date_inputs, outside)
        y_row, l_rows, m_rows = _audit_rows(spec, year, ye, train, test)
        year_rows.append(y_row)
        line_rows += l_rows
        missing_rows += m_rows
        if verbose:
            print(f"[{spec.name}] {year}: {y_row['n_stations']} stations take part; training {len(train)} examples, "
                  f"{y_row['train_events']} events; test {len(test)} examples, {y_row['test_events']} events.")
        if audit_only or len(test) == 0:
            continue
        with warnings.catch_warnings(record=True) as caught:  # e.g. a logistic fit that did not converge
            warnings.simplefilter("always")
            scores = models.score_year(train, test, spec, outside_available=outside is not None)
        for w in caught:
            warning_rows.append({"year": year, "category": w.category.__name__,
                                 "message": " ".join(str(w.message).split())[:200]})
        for method, columns in scores.left_out.items():
            for c in columns:
                left_out_rows.append({"year": year, "method": method, "input_left_out": c})
        pred = test[["station", "date", "onset", "fresh_onset", "part_window"]].copy()
        pred.insert(0, "year", year)
        pred.insert(0, "place", spec.name)
        for name, values in scores.test.items():
            pred[name] = values
        predictions.append(pred)
        for method in config.MAIN_METHODS:
            if method in scores.train:
                thr = scoring.training_threshold(scores.train[method], config.DECISION_PERCENTILE)
                decision_rows.append(scoring.decision_check(pred, method, thr))

    audit_years = pd.DataFrame(year_rows)
    write_csv(audit_years, out_dir / "audit_years.csv")
    write_csv(pd.DataFrame(line_rows), out_dir / "audit_lines.csv")
    write_csv(pd.DataFrame(missing_rows), out_dir / "audit_missing.csv")
    for key, value in sorted((extra_audit or {}).items()):
        if isinstance(value, pd.DataFrame):
            write_csv(value, out_dir / f"audit_{key}.csv")
    scalars = {k: v for k, v in (extra_audit or {}).items() if not isinstance(v, pd.DataFrame)}
    if scalars:
        write_csv(pd.DataFrame([{"item": k, "value": v} for k, v in sorted(scalars.items())]),
                  out_dir / "audit_counts.csv")
    if audit_only:
        return {"audit_years": audit_years}

    pred = pd.concat(predictions, ignore_index=True).sort_values(["year", "station", "date"]).reset_index(drop=True)
    methods = [m for m in (*config.MAIN_METHODS, *config.READING_METHODS) if m in pred.columns]
    table = scoring.year_table(pred, methods)
    table.insert(1, "verdict_year", table["year"].isin(spec.verdict_years))
    table.insert(2, "counted", table["verdict_year"] & (table["events"] >= scoring.MIN_EVENTS_PER_YEAR))
    counted_years = set(table.loc[table["counted"], "year"])
    pred.insert(pred.columns.get_loc("onset") + 1, "verdict_year", pred["year"].isin(spec.verdict_years))
    pred.insert(pred.columns.get_loc("verdict_year") + 1, "counted_in_verdict", pred["year"].isin(counted_years))

    verdict_table = table.loc[table["verdict_year"]].drop(columns=["verdict_year", "counted"]).reset_index(drop=True)
    verdicts = scoring.place_verdicts(verdict_table, draws=draws)
    win = scoring.win_bar_summary(verdicts)
    credit = scoring.credit_check(verdict_table)
    verdict_pred = pred.loc[pred["verdict_year"]]
    pooled = scoring.pooled_scores(verdict_pred, methods)
    bar = scoring.bar_method(verdict_table) if len(scoring.counted(verdict_table)) else "B1"
    fresh = scoring.fresh_onset_summary(verdict_pred, methods, bar)
    by_station = scoring.station_scores(verdict_pred, methods)
    by_station_year = pd.concat([scoring.station_scores(p, methods).assign(year=y)
                                 for y, p in pred.groupby("year", sort=True)], ignore_index=True)
    decisions = pd.concat(decision_rows, ignore_index=True).sort_values(["method", "year"]).reset_index(drop=True)
    ep = scoring.episodes(pred.loc[pred["onset"], ["station", "date", "year", "part_window"]], config.EPISODE_GAP_DAYS)
    episodes_by_year = episode_counts(ep)

    write_csv(pred, out_dir / "predictions.csv")
    write_csv(table, out_dir / "year_table.csv")
    write_csv(verdicts, out_dir / "verdicts.csv")
    write_csv(by_station, out_dir / "station_scores.csv")
    write_csv(by_station_year, out_dir / "station_year_scores.csv")
    write_csv(decisions, out_dir / "decision_check.csv")
    write_csv(episodes_by_year, out_dir / "episodes.csv")
    write_csv(fresh, out_dir / "fresh_onset.csv")
    write_csv(pd.DataFrame(left_out_rows, columns=["year", "method", "input_left_out"]),
              out_dir / "audit_left_out.csv")
    write_csv(pd.DataFrame([{"method": m, "pooled_average_precision": v} for m, v in pooled.items()]),
              out_dir / "pooled.csv")
    primary = pd.DataFrame([{"method": m, "primary_score": scoring.safe_primary_score(verdict_table, m),
                             "counted_years": len(scoring.counted(verdict_table)),
                             "counted_events": scoring.counted_events(verdict_table)} for m in methods])
    write_csv(primary, out_dir / "primary_scores.csv")
    warnings_table = (pd.DataFrame(warning_rows, columns=["year", "category", "message"])
                      .value_counts(sort=False).rename("count").reset_index()
                      .sort_values(["year", "category", "message"]).reset_index(drop=True))
    write_csv(warnings_table, out_dir / "audit_warnings.csv")
    if outside is not None:
        sat = (pred.assign(has_image=pred.merge(outside[["station", "date", "s2_ndci"]], on=["station", "date"],
                                                how="left")["s2_ndci"].notna().to_numpy())
               .groupby(["year", "station"]).agg(examples=("has_image", "size"), with_image=("has_image", "sum"))
               .reset_index())
        write_csv(sat, out_dir / "audit_satellite.csv")

    summary = summary_text(spec, table, verdicts, win, credit, pooled, fresh, outside is not None, audit_years,
                           primary=primary, n_warnings=len(warning_rows))
    (out_dir / "summary.txt").write_text(summary)
    if verbose:
        print(summary)
    return {"predictions": pred, "year_table": table, "verdicts": verdicts, "win_bar": win, "credit": credit}


def episode_counts(ep: pd.DataFrame) -> pd.DataFrame:
    """Per year: events, part-window events, and episodes counted in the year of their first event."""
    columns = ["year", "events", "part_window_events", "episodes_starting"]
    if not len(ep):
        return pd.DataFrame(columns=columns)
    first = ep.groupby(["station", "episode"], sort=True).first().reset_index()
    by_year = ep.groupby("year", sort=True).agg(events=("date", "size"), part_window_events=("part_window", "sum"))
    starts = first.groupby("year").size().rename("episodes_starting")
    return by_year.join(starts).fillna(0).astype(int).reset_index()[columns]


def summary_text(spec, table, verdicts, win, credit, pooled, fresh, t4_run, audit_years, primary=None,
                 n_warnings=None) -> str:
    lines = [f"Place: {spec.name}. Verdict years {spec.verdict_years[0]}-{spec.verdict_years[-1]}; "
             f"outside the verdict: {', '.join(map(str, spec.outside_years))}."]
    vt = table.loc[table["verdict_year"]]
    lines.append(f"Counted years: {int(vt['counted'].sum())}; events in counted years: "
                 f"{int(vt.loc[vt['counted'], 'events'].sum())}; "
                 f"part-window events (all test years): {int(audit_years['test_part_window_events'].sum())}.")
    if spec.name == "li":
        lines.append("B2 at Long Island is B2-LI (no tide, sun or wind): a weaker bar than SF Bay's B2. "
                     "Every Long Island margin below is against that weaker bar.")
    if not t4_run:
        lines.append("T4 skipped: no outside-inputs table supplied.")
    else:
        lines.append("T4 was run after T1 to T3 were scored, so it is NOT blind to their results.")
    lines.append("Verdicts (family = T1 to T4 at this place):")
    for row in verdicts.itertuples():
        if row.verdict in (scoring.NOT_RUN,):
            lines.append(f"  {row.method}: {row.verdict}")
            continue
        extra = ""
        if row.verdict != scoring.TOO_FEW_EVENTS:
            extra = (f"; interval [{row.interval_low:+.4f}, {row.interval_high:+.4f}]; years won "
                     f"{row.years_won}/{row.years_counted} (need {row.years_required}); low end reaches +10%: "
                     f"{row.low_end_reaches_10pct}")
        lines.append(f"  {row.method}: {row.verdict}; primary {row.primary_score:.4f}; margin {row.margin:+.4f}{extra}")
    lines.append(f"Win bar (blind tries T1-T3): {win['blind_tries']}. Win bar (any try): {win['any_try']}.")
    lines.append(f"Credit to new inputs allowed: {credit['credit_allowed']} "
                 f"(T3 over T3-twin: {credit['T3_over_T3_twin']}; T2 over B2: {credit['T2_over_B2']}).")
    if primary is not None:
        lines.append("Primary score of every method (primary_scores.csv): "
                     + ", ".join(f"{r.method} {r.primary_score:.4f}" for r in primary.itertuples()))
    if n_warnings is not None:
        lines.append(f"Warnings raised while fitting (audit_warnings.csv): {n_warnings}.")
    lines.append("Pooled average precision over verdict-year examples (no verdict): "
                 + ", ".join(f"{m} {v:.4f}" for m, v in pooled.items()))
    lines.append("Fresh-onset primary score (no verdict): "
                 + ", ".join(f"{r.method} {r.fresh_primary_score:.4f}" for r in fresh.itertuples()))
    lines.append("No score here is a probability. Nothing here predicts harmful algal blooms or toxins.")
    return "\n".join(lines) + "\n"


def load_outside(path: str | None) -> pd.DataFrame | None:
    if not path:
        return None
    table = pd.read_csv(path, dtype={"station": str}, parse_dates=["date"])
    missing = [c for c in ("station", "date", *config.OUTSIDE_COLUMNS) if c not in table.columns]
    if missing:
        raise ValueError(f"Outside-inputs table {path} lacks {missing}.")
    return table


NO_ANCHOR_NOTE = ("ANCHOR NOT RUN: --no-anchor was given. The anchor (PREREG section 5) needs the private SF Bay file, "
                  "so this run did not check that the code still reproduces the earlier model's published numbers.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--place", choices=["sf", "li"], required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--outside", default=None)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--no-anchor", action="store_true",
                        help="Long Island only: skip the anchor, for a reader without the private SF Bay file.")
    args = parser.parse_args(argv)
    if args.no_anchor and args.place != "li":
        parser.error("--no-anchor is allowed only with --place li.")
    config.check_environment()
    outside = load_outside(args.outside)
    log: dict = {}
    import anchor
    if args.no_anchor:
        print(NO_ANCHOR_NOTE, file=sys.stderr)
    elif not anchor.run_anchor():                            # both places: section 5 names no place
        print("Anchor FAILED: no new score is computed.", file=sys.stderr)
        return 2
    if args.place == "sf":
        import data_sf
        spec = config.SF
        check_output_dir(spec, Path(args.out))
        frame = data_sf.load_sf_frame(log=log)
        date_inputs = data_sf.load_sf_date_inputs()
    else:
        import data_li
        spec = config.LI
        frame = data_li.load_li_frame(log=log)
        date_inputs = None
    run_place(frame, spec, Path(args.out), date_inputs=date_inputs, outside=outside, audit_only=args.audit_only,
              extra_audit=log)
    summary_path = Path(args.out) / "summary.txt"
    if args.no_anchor and summary_path.exists():
        summary_path.write_text(NO_ANCHOR_NOTE + "\n" + summary_path.read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
