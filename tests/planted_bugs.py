"""
Planted-bug check (PREREG section 8): plant one bug at a time in src/, run the test that should catch it, and put
the file back byte for byte. A bug the test does not catch is a hole in the tests.

    OMP_NUM_THREADS=1 .venv/bin/python tests/planted_bugs.py

Refuses to start unless src/ has no uncommitted change (so git can always restore it). Exit code 0 only if every
planted bug is caught and every file is restored. Made-up data only: the tests it runs read no real file.
The first 26 bugs are the pipeline builder's; the rest were added after the independent code review.
"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = str(ROOT / ".venv/bin/python")
BUGS = [
    ("examples.py", "embargo=embargo))", "embargo=embargo - 1))",
     "tests/test_pipeline_examples.py::test_training_examples_end_21_december_and_test_examples_stay_in_year",
     "embargo 10 -> 9"),
    ("examples.py", "if n >= min_days)", "if n > min_days)",
     "tests/test_pipeline_examples.py::test_station_takes_part_only_with_300_days_on_or_before_cutoff",
     "taking part needs >300 days instead of >=300"),
    ("examples.py", 'test["date"].dt.year == test_year]', 'test["date"].dt.year >= test_year]',
     "tests/test_pipeline_examples.py::test_training_examples_end_21_december_and_test_examples_stay_in_year",
     "test examples not limited to year Y"),
    ("examples.py", "lines = labels.train_thresholds(sub, cutoff=cutoff,",
     "lines = labels.train_thresholds(sub, cutoff=cutoff + pd.Timedelta(days=30),",
     "tests/test_pipeline_examples.py::test_high_line_is_sorted_position_of_values_on_or_before_cutoff",
     "high line uses 30 days past the cut-off"),
    ("examples.py", '["part_window"] = part_frame["n_future_measured"] < len(config.HORIZON_DAYS)',
     '["part_window"] = part_frame["n_future_measured"] < 2',
     "tests/test_pipeline_examples.py::test_part_window_count_matches_rule",
     "part-window flag misses windows with 2 of 3 days"),
    ("features.py", 'out["d1_ratio"] = ratio - _lag(frame, ratio, 1)', 'out["d1_ratio"] = ratio - _lag(frame, ratio, 2)',
     "tests/test_pipeline_features.py::test_d1_and_d3_ratio_missing_if_earlier_day_missing", "d1_ratio lag 2"),
    ("features.py", 'last_high_before_t = last_high.groupby(frame["station"]).shift(1)',
     'last_high_before_t = last_high', "tests/test_pipeline_features.py::test_days_since_high_definition",
     "days_since_high counts day t itself"),
    ("features.py", "np.minimum(days, config.DAYS_SINCE_HIGH_CAP)", "days",
     "tests/test_pipeline_features.py::test_days_since_high_definition", "days_since_high not capped at 60"),
    ("features.py", ".rolling(config.MAX7_WINDOW_DAYS, min_periods=1)", ".rolling(config.MAX7_WINDOW_DAYS - 1, min_periods=1)",
     "tests/test_pipeline_features.py::test_max7_ratio_uses_measured_days_of_last_seven", "max7 window 6 days"),
    ("features.py", ".rolling(config.FRESH_ONSET_WINDOW_DAYS, min_periods=1)",
     ".rolling(config.FRESH_ONSET_WINDOW_DAYS - 1, min_periods=1)",
     "tests/test_pipeline_features.py::test_fresh_onset_flag_uses_t_minus_14_to_t_minus_1", "fresh window 13 days"),
    ("features.py", "- pd.Timedelta(hours=utc_offset_hours)", "+ pd.Timedelta(hours=utc_offset_hours)",
     "tests/test_pipeline_features.py::test_moon_phase_definition", "moon phase clock offset sign flipped"),
    ("features.py", "others = [s for s in chla.columns if s != station]", "others = list(chla.columns)",
     "tests/test_pipeline_features.py::test_neighbours_each_against_own_line_and_only_taking_part",
     "neighbours include the station itself"),
    ("features.py", "high = chla.ge(line_row, axis=1)", "high = chla.gt(line_row, axis=1)",
     "tests/test_pipeline_features.py::test_neighbours_each_against_own_line_and_only_taking_part",
     "nb_n_high uses > instead of >="),
    ("features.py", 'out[name] = frame[column] - _lag(frame, column, 3)', 'out[name] = frame[column] - _lag(frame, column, -3)',
     "tests/test_pipeline_features.py::test_inputs_never_look_past_day_t", "d3 inputs look 3 days into the future"),
    ("models.py", "left_out = [c for c in columns if train[c].isna().all()]", "left_out = []",
     "tests/test_pipeline_models.py::test_input_missing_on_every_training_example_is_left_out_of_logistic_models",
     "all-missing rule not applied (logistic)"),
    ("models.py", '_finalize_run(method, train, {"test": test}, kept)',
     '_finalize_run(method, pd.concat([train, test]), {"test": test}, kept)',
     "tests/test_pipeline_models.py::test_changing_test_year_values_changes_nothing_on_the_training_side",
     "logistic fitted (medians, scaling, coefficients) on train plus test"),
    ("models.py", "for moon in (\"moon_sin\", \"moon_cos\"):", "for moon in (\"moon_sin\",):",
     "tests/test_pipeline_models.py::test_t1_t2_columns", "station-times-moon_cos products missing"),
    ("scoring.py", "won = int((part[method].to_numpy() > part[bar].to_numpy()).sum())",
     "won = int((part[method].to_numpy() >= part[bar].to_numpy()).sum())",
     "tests/test_scoring.py::test_years_rule_ties_are_not_wins_and_required_rounds_up", "years rule counts ties as wins"),
    ("scoring.py", "MIN_COUNTED_EVENTS = 150", "MIN_COUNTED_EVENTS = 149",
     "tests/test_scoring.py::test_too_few_events_branches", "TOO FEW EVENTS at 149 instead of 150"),
    ("scoring.py", 'best_bar = np.maximum(score("B1"), score("B2"))', 'best_bar = score("B1")',
     "tests/test_scoring.py::test_bootstrap_redraws_years_and_repicks_the_bar_each_draw", "bar not re-picked per draw"),
    ("scoring.py", '    weights = part["events"].to_numpy(dtype=float)\n    if multiplicity',
     '    weights = np.ones(len(part))\n    if multiplicity',
     "tests/test_scoring.py::test_primary_score_is_event_weighted_over_counted_years", "primary score not event-weighted"),
    ("scoring.py", "return table.loc[table[\"events\"] >= MIN_EVENTS_PER_YEAR]", "return table.loc[table[\"events\"] > MIN_EVENTS_PER_YEAR]",
     "tests/test_scoring.py::test_counted_years_need_five_events", "counted years need >5 events"),
    ("scoring.py", "new = gaps.isna() | (gaps >= gap_days)", "new = gaps.isna() | (gaps > gap_days)",
     "tests/test_scoring.py::test_episodes_split_at_seven_days", "episodes: 7 days apart merged"),
    ("scoring.py", 'return "B2" if scores["B2"] > scores["B1"] else "B1"', 'return "B2" if scores["B2"] >= scores["B1"] else "B1"',
     "tests/test_scoring.py::test_bar_method_tie_goes_to_b1", "bar-method tie goes to B2"),
    ("data_li.py", "values[estimated] = np.nan", "pass",
     "tests/test_pipeline_data_li.py::test_estimated_dropped_provisional_kept_non_numeric_missing", "estimated values kept"),
    ("data_li.py", "best = max(counts, key=lambda item: (item[0], -item[1]))",
     "best = min(counts, key=lambda item: (item[0], -item[1]))",
     "tests/test_pipeline_data_li.py::test_series_with_most_days_is_chosen_and_logged", "series with FEWEST days chosen"),

    # ---- added after the independent code review (research/07-code-review-opus.md) ----
    ("config.py", 'LI_STATISTICS = {"00003": "mean", "00001": "max", "00002": "min"}',
     'LI_STATISTICS = {"00002": "mean", "00001": "max", "00003": "min"}',
     "tests/test_review_opus.py::test_li_column_mapping_with_distinct_values", "Long Island daily mean and minimum swapped"),
    ("config.py", '"00010": "temp_c", "90860": "salinity_psu", "00300": "do_mgl"',
     '"00300": "temp_c", "90860": "salinity_psu", "00010": "do_mgl"',
     "tests/test_after_review.py::test_long_island_usgs_codes_map_to_the_right_measures",
     "temperature and dissolved oxygen swapped"),
    ("scoring.py", "N_TRIES = 4", "N_TRIES = 1",
     "tests/test_review_opus.py::test_verdict_interval_points_are_0_625_and_99_375_percent", "95% interval instead of 98.75%"),
    ("scoring.py", "tost_tail = FAMILY_ALPHA / N_TRIES  ", "tost_tail = FAMILY_ALPHA / N_TRIES / 2.0  ",
     "tests/test_after_review.py::test_no_difference_uses_the_1_25_percent_points_on_a_case_where_the_0_625_points_disagree",
     "no-difference check uses the 0.625% points"),
    ("scoring.py", "BOOTSTRAP_SEED = 20261117", "BOOTSTRAP_SEED = 20261118",
     "tests/test_review_opus.py::test_prereg_constants_are_the_locked_values", "wrong bootstrap seed"),
    ("scoring.py", "LARGE_MARGIN = 0.25", "LARGE_MARGIN = 0.20",
     "tests/test_review_opus.py::test_prereg_constants_are_the_locked_values", "large margin at +20% instead of +25%"),
    ("models.py", "frame[product] = frame[name] * frame[moon]", 'frame[product] = frame[name] * frame["moon_cos"]',
     "tests/test_review_opus.py::test_t1_scores_equal_a_hand_built_t1_with_moon_product_values",
     "station-times-moon_sin products built from moon_cos"),
    ("models.py", "unbinnable = [c for c in columns if train[c].isna().all()]", "unbinnable = []",
     "tests/test_after_review.py::test_tree_drops_and_logs_an_all_missing_input_without_changing_scores",
     "all-missing input not dropped from the tree fit (deviation D1)"),
    ("run_study.py", "scoring.safe_primary_score(verdict_table, m)", "scoring.safe_primary_score(table, m)",
     "tests/test_after_review.py::test_primary_scores_file_is_the_event_weighted_mean_of_counted_verdict_years",
     "primary-score file includes years outside the verdict"),
    ("run_study.py", "    elif not anchor.run_anchor():  ", '    elif args.place == "sf" and not anchor.run_anchor():  ',
     "tests/test_after_review.py::test_command_line_run_stops_for_either_place_when_the_anchor_fails",
     "Long Island run does not need the anchor"),
    ("run_study.py", 'if args.no_anchor and args.place != "li":', "if False:",
     "tests/test_after_review.py::test_no_anchor_option_is_refused_for_sf_bay",
     "SF Bay run allowed to skip the anchor"),
    ("run_study.py", "if args.no_anchor and summary_path.exists():", "if False:",
     "tests/test_after_review.py::test_no_anchor_option_skips_the_anchor_for_long_island_and_marks_the_summary",
     "a run without the anchor is not marked in the summary"),
]

if subprocess.run(["git", "status", "--porcelain", "src"], cwd=ROOT, capture_output=True, text=True).stdout.strip():
    sys.exit("src/ has uncommitted changes: commit them first, so a planted bug can never be left behind.")
env = dict(os.environ, OMP_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / "src").glob("*.py")}
rows, bad = [], 0
for i, (fname, old, new, test, what) in enumerate(BUGS, 1):
    path = ROOT / "src" / fname
    original = path.read_bytes()
    text = original.decode()
    n = text.count(old)
    if n != 1:
        rows.append((i, fname, what, f"SETUP ERROR: pattern found {n} times"))
        bad += 1
        continue
    try:
        path.write_text(text.replace(old, new))
        r = subprocess.run([PY, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", test], cwd=ROOT, env=env,
                           capture_output=True, text=True, timeout=900)
        caught = r.returncode == 1                       # 1 = a test failed; other codes mean the run itself broke
        last = ([l for l in r.stdout.splitlines() if l.strip()] or ["(no output)"])[-1]
    finally:
        path.write_bytes(original)
    restored = hashlib.sha256(path.read_bytes()).hexdigest() == before[fname]
    bad += (not caught) or (not restored)
    rows.append((i, fname, what, ("CAUGHT" if caught else f"NOT CAUGHT (exit {r.returncode})") + f" | {last}"
                 + ("" if restored else " | NOT RESTORED")))
after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / "src").glob("*.py")}
for row in rows:
    print(" | ".join(map(str, row)))
print(f"{len(rows) - bad} of {len(rows)} planted bugs caught. All src files identical to before: {before == after}")
sys.exit(0 if bad == 0 and before == after else 1)
