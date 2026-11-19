# Independent code review before the one real run (Opus, 2026-11-17)

Reviewer: Claude (Opus), not the builder. Spec: `PREREG.md` (locked `09d16c4`) and `DEVIATIONS.md` (D1 and the
nine "readings"). Code: `src/config.py`, `data_sf.py`, `data_li.py`, `examples.py`, `features.py`, `models.py`,
`scoring.py`, `run_study.py`, `anchor.py`, the builder's tests, and the team's `labels.py`, `onset_dataset.py`,
`onset_model.py` (read only).

What I ran: the builder's tests (79 passed); my own tests `tests/test_review_opus.py` on made-up data (14 passed;
full suite together 93 passed); `src/anchor.py` (PASS, 16 of 16). I read the existing `data/processed/*_audit/`
count files and listed the Long Island RDB qualifier codes and series date ranges (no measured value printed).
I did not run the study, and did not fit or score T1, T2, T3, the twin, or yearly B1/B2 on real data.

**Bottom line.** I found no leak and no place where the code computes a different label, input, score or verdict
from what the PREREG says. One spec rule is unmet: section 8's "planted bugs to show the tests catch them". There
are no such tests, and I show four builder tests that would pass with a planted bug. My rule tests now cover those
four gaps, and the current code passes them. So the BLOCKER is about the checking, not about any number.

## Findings (most serious first)

### 1. BLOCKER (spec rule, section 8; changes no number): no planted-bug tests, and four builder tests cannot fail
- **Spec:** "Tests on made-up data for every rule in sections 4 to 7, with planted bugs to show the tests catch
  them."
- **Code:** no test plants a bug (grep finds no mutation tests). I planted four bugs with `monkeypatch`, ran the
  builder's own test against each, and every one still passed (`test_demo_*` in `tests/test_review_opus.py`):
  - `LI_STATISTICS` with mean and min swapped (`00002`→mean, `00003`→min): `test_reindexed_daily_columns_...` passes.
  - `LI_PARAMETERS` with temperature and dissolved oxygen swapped: the same test passes.
  - `scoring.N_TRIES = 1` (a 95% interval in place of 98.75%): all six verdict-branch tests in `test_scoring.py`
    pass.
  - The station-times-moon "sin" products built from `moon_cos`: `test_station_moon_products_are_onehot_times_moon`
    passes, because it checks only column names.
  - Also, no builder test pins `BOOTSTRAP_SEED = 20261117`, so a wrong seed would pass every builder test.
- **Current code is right on all five.** My rule tests check them directly and pass:
  `test_li_column_mapping_with_distinct_values`, `test_verdict_interval_points_are_0_625_and_99_375_percent`,
  `test_no_difference_branch_uses_the_1_25_percent_points`, `test_t1_scores_equal_a_hand_built_t1_with_moon_product_values`
  (rebuilds T1 by hand, product values included, to 1e-9), and `test_prereg_constants_are_the_locked_values`.
- **Smallest fix:** keep my rule tests. Add at least one planted-bug test per section 4 to 7 rule family that
  asserts the builder's test fails (`pytest.raises(AssertionError)`). My demos can be flipped into that form.

### 2. SHOULD FIX: a Long Island run never checks the anchor
- **File:** `run_study.py:255-269`, `config.py:154-162` (`LI.requires_anchor` is False).
- **Spec (section 5):** "Anchor (must pass before any new score is computed)." It names no place, so it covers Long
  Island's new scores too.
- **Code:** `main()` runs the anchor only for `--place sf`. `--place li` fits and scores with no anchor.
- **Made-up case:** if someone ran `--place li` first, Long Island scores would exist before any anchor pass.
- **Today:** the anchor passes (I ran it: [redacted: from the restricted Bay file]). So the
  practical risk is the order of steps only.
- **Fix:** call `anchor.run_anchor()` in `main()` for both places, or set `requires_anchor=True` on `LI`.

### 3. SHOULD FIX: the bars' primary scores and the credit-check numbers are not written to any file
- **File:** `run_study.py:147-185`, `scoring.place_verdicts`, `scoring.credit_check`.
- **Spec (section 7):** the primary score of each method; the margin over "the higher of B1's and B2's primary
  scores"; credit "only if T3 beats T3-twin, or T2 beats B2, on the primary score".
- **Code:** `verdicts.csv` holds only T1 to T4. The primary scores of B1, B2, T3-twin and the reading rules are never
  written, and the credit check prints only True/False. The report writer would have to recompute them by hand
  from `year_table.csv`, which is a second, unchecked code path.
- **Fix:** write `primary_scores.csv` (every method: primary score, counted years, counted events) and print the
  four credit-check numbers in `summary.txt`.

### 4. SHOULD FIX (record it, do not change the code): the series rule drops pre-2017 turbidity at two LI stations
- **File:** `data_li.py:73-81`. **Spec (section 3):** "the series with the most non-missing days is used".
- **Code:** matches the spec. But the two series are not duplicates. They are one record split at a sensor change,
  with no overlap (date ranges only; no values read):
  - 01310740: kept `214195` (2017-05-25 to 2026-11-16, 2,889 days); dropped `332560` (2010-01-01 to 2017-05-18,
    2,217 days).
  - 01304562: kept `214193` (2017-10-03 on, 2,873 days); dropped `332564` (2012-08-15 to 2017-10-01, 792 days).
  The same holds for `_max` and `_min`.
- **Effect:** Long Island turbidity is missing at those stations before 2017. It gets the median fill and a
  missing marker in B2-LI, T1 and T2, and stays missing in the trees. Every method sees the same loss, so the
  comparison stays fair. Joining the two series would be a deviation and is not advised.
- **Fix:** add this to the "readings" list in `DEVIATIONS.md` (reading 1 does not mention disjoint series) and to
  the report's limits.

### 5. NOTE: D1 (trees drop an all-missing input) checked
- The claim is true: with scikit-learn 1.9.1 and an all-missing column, `HistGradientBoostingClassifier.fit` raises
  `ValueError: window shape cannot be larger than input array shape` (my test `test_hgb_on_an_all_missing_column`).
- It cannot change a score. A column with no measured training value has no bin threshold, so no split can use it.
  `max_features` defaults to 1.0 and there are far fewer than 200,000 training rows, so no random column or row
  sampling shifts with the column count. It is logged: `fit_tree` returns it, and `run_study` writes it to
  `audit_left_out.csv`.
- **Weak test:** the builder's proof (`test_leaving_an_unsplittable_column_out_of_a_tree_changes_nothing`) uses a
  CONSTANT column. `fit_tree` keeps constant columns, so that test never runs the drop branch (my
  `test_demo_builder_tree_drop_test_does_not_exercise_the_drop_rule`). The argument above is sound anyway.
- Where it fires on real data (audit counts): LI 2015 to 2018, `nb_mean_ratio` and `nb_max_ratio` (one station
  takes part), in both training and test. The same two columns are left out of T2's logistic fit, as the PREREG
  says. T2 also keeps `nb_n_high` and `nb_n_reporting`, both constant at 0 in those years.

### 6. NOTE: the fresh-onset "primary score" re-applies the 5-event rule to the fresh subset
- **File:** `scoring.fresh_onset_summary`. A year counted at the place drops out of the fresh score if it has fewer
  than 5 fresh events (shown in `test_fresh_onset_counted_years_are_refiltered_on_the_subset`). The other reading
  keeps the place's counted years and weights by fresh events. The PREREG does not settle this, and
  `DEVIATIONS.md` reading 4 covers only "strictly higher". Add a line to the readings list. It is descriptive and
  affects no verdict.

### 7. NOTE: T4 recomputes T1 to T3 in the same call
- `--outside` re-fits B1 to T3 and T4 together. The T1 to T3 numbers will match the blind run (same seed, same
  data, no T4 input in them), but only if nothing else changed. When T4 runs, write to a new output folder and
  diff T1 to T3 columns of `predictions.csv` against the blind run's file.

### 8. NOTE: smaller points
- a. **Convergence warnings** from `LogisticRegression` go to stderr and are not logged per year or method.
  Capture `ConvergenceWarning` into the audit (`models.fit_logistic`).
- b. `config.SF.extra["last_day"]` ([redacted: from the restricted Bay file]) is never used. The SF frame is not cut at that date. This is
  harmless if the team file ends there (team docs say it does; I did not check the file's last date: UNVERIFIED).
- c. Byte-identical reruns: the run sets `OMP_NUM_THREADS=1`, and the builder's double run matches on made-up data.
  Whether the BLAS library numpy uses on this Mac obeys it is UNVERIFIED. The PREREG's real double run (section 8)
  is the check. `run_study` does not do it by itself; the runner must.
- d. If a year's training examples held one class only, the run would stop with an error, not skip silently. No
  such year exists in the audit counts (fewest: LI 2015, 334 examples and 25 events).
- e. Unseen station at test time: logistic one-hots go all-zero and the tree code is missing. Every score is
  finite (`test_unseen_station_at_test_time_is_scored_by_every_method`). On real data no test station lacks
  training examples.
- f. Long Island qualifier codes in the saved files are exactly `A, A:<, A:>, A:[4], A:e, P, P:<, P:[4]`, and the
  only non-numeric value is `Eqp` (2 cells). The code handles all of these as `DEVIATIONS.md` readings 2 and 9
  say. Audit: 4 estimated values dropped, 0 negative turbidity.

## Leakage hunt: what I checked (no leak found)
| Possible leak | Where | Result |
|---|---|---|
| High line uses data after C | `examples.build_examples` → team `train_thresholds(sub, cutoff=C)` | only dates ≤ C, only stations taking part |
| Taking-part list uses data after C | `examples.chla_days_before` | `date <= C`, non-missing only |
| Training labels use days after C | team builder, `embargo=10` | training dates ≤ 21 Dec, so labels use days ≤ 24 Dec; builder test perturbs post-C values |
| Test examples outside year Y | `examples.py:90-91` | filtered to `dt.year == Y` (labels may use 1 to 3 Jan of Y+1, as the PREREG allows) |
| Non-taking-part station in neighbours or examples | `features.year_inputs`, `neighbours` | frame filtered to `lines`; my test changes the absent station's values: train and test frames byte-equal |
| `shift`/`rolling` across stations or gaps | every function in `features.py` calls `_sorted` → `check_gapless` | always gapless and grouped by station; `days_since_high` uses grouped ffill/shift on a RangeIndex that matches |
| `max7_ratio`, `days_since_high`, fresh flag windows | `features.py:55-86` | t−6..t; on or before t−1; t−14..t−1 (builder tests and my reading agree) |
| Scaler, medians, markers, one-hots, station code | team `_finalize_run`, `fit_tree` | fitted on training examples only |
| Decision-check percentile | `run_study.py:119-122` | each model's training-example scores |
| Merge duplicates/reorders | `features.attach`, `attach_outside`, `year_inputs` | `validate="one_to_one"` / `many_to_one`; left order kept; scores assigned by position from frames reset in that order |
| Outside table | `features.attach_outside` | exact (station, date) key, duplicate keys refused; the table must be keyed by issue date t (it is, per `outside_join.py` header) |
| Reading rules | `models.reading_rules` | training rates only |

## Every PREREG rule checked
| § | Rule | Code | Status |
|---|---|---|---|
| 3 | SF file, nine stations, `load_msp(start=2013-07-24, reindex=True)` | `data_sf.load_sf_frame` | matches |
| 3 | SF hygiene: turbidity floored at 0; ph/bga/fdom dropped | `data_sf.py:27-38` | matches ([redacted: from the restricted Bay file]) |
| 3 | SF date-level inputs from team weather/tide files | `data_sf.load_sf_date_inputs` | matches |
| 3 | LI five stations, five parameters, three statistics, codes | `config.LI_PARAMETERS/STATISTICS` | matches (my distinct-value test) |
| 3 | Most non-missing days series; choice logged | `data_li.py:73-101` | matches (see finding 4) |
| 3 | "e" dropped and counted; provisional kept, share reported | `data_li.py:86-100,131-136` | matches |
| 3 | Reads only saved download; reindexed daily; `chla_mean` | `data_li.load_li_frame` | matches |
| 3 | No interpolation | all | matches |
| 4 | Examples and labels by team `build_onset_examples` | `examples.py:86-89` | matches |
| 4 | High line = sorted position int(0.9n), dates ≤ C | team `train_thresholds` | matches |
| 4 | Example: measured, strictly below; ≥1 future day measured | team | matches |
| 4 | Event / partial window dropped unless it crosses | team | matches |
| 4 | Issue time end of day t | `features.py` | matches (causality test) |
| 4 | Part-window events reported | `examples.future_measured_days`, summary | matches |
| 5 | C = 31 Dec Y−1 | `examples.cutoff_for` | matches |
| 5 | Taking part: ≥300 chla days ≤ C, absent everywhere otherwise | `examples.py`, `features.year_inputs` | matches |
| 5 | L(Y) over taking-part stations | `examples.py:83` | matches |
| 5 | Training: split train, embargo 10 (≤ 21 Dec), labelled vs L(Y) | `examples.py:86` | matches |
| 5 | Test: split test, same C and L(Y), year Y only | `examples.py:88-91` | matches |
| 5 | Ratio, B1, "at or above" inputs use L(Y) | `features.py` | matches |
| 5 | Scaling, fills, station lists, codes from training only | team `_finalize_run`, `fit_tree` | matches |
| 5 | Every method scores every test example | `models.score_year`, `scoring.year_table` | matches |
| 5 | Verdict years SF 2017–2024, LI 2015–2025; outside years reported | `config.SF/LI` | matches |
| 5 | Anchor passes before any new score | `run_study.main`, `anchor.py` | differs for LI (finding 2) |
| 6 | Environment pinned | `config.check_environment` | matches |
| 6 | B1 = ratio | `models.py:140` | matches |
| 6 | B2: 15 base cols + one-hots + markers, medians, scaler, logistic settings, no outflow | team pipeline via `fit_logistic` | matches (builder rebuild test; anchor) |
| 6 | B2-LI columns | `config.LI_BASE_COLUMNS` | matches |
| 6 | All-missing input left out of logistic and logged | `models.py:77` | matches |
| 6 | Trees keep all-missing input | `models.py:113` | differs, logged as D1; no score effect (finding 5) |
| 6 | Reading rules: base rate, month, station | `models.reading_rules` | matches |
| 6 | Each new input definition (ratio_max … moon, neighbours) | `features.py` | matches |
| 6 | T1: B2 + new cols + one-hots once + one-hot×moon products | `models.fit_logistic` | matches (my hand rebuild) |
| 6 | T2 = T1 + four neighbour inputs | `models.logistic_columns` | matches |
| 6 | T3 settings, no class weights, inputs, station code categorical, missing stays missing | `models.fit_tree` | matches |
| 6 | T3-twin | `models.tree_columns` | matches |
| 6 | T4 = T3 + outside columns; skipped if no table | `models.py:148-156` | matches |
| 7 | Per-year score = sklearn AP | `scoring.year_table` | matches |
| 7 | Counted years ≥5 events, verdict years only | `scoring.counted`, `run_study.py:147` | matches |
| 7 | Primary score event-weighted; pooled reported | `scoring.primary_score`, `pooled_scores` | matches |
| 7 | Margin vs higher of B1/B2 | `scoring.margin` | matches |
| 7 | Bootstrap 10,000, seed, years with replacement, bar re-picked | `scoring.bootstrap_margins` | matches |
| 7 | Interval 0.625% / 99.375% | `scoring.verdict` | matches (my test) |
| 7 | One bar method per place, tie to B1; strict year wins; ceil(¾) | `scoring.bar_method`, `years_won` | matches |
| 7 | BEATS, LARGE (≥+25%), +10% low-end reported, NO DIFF (1.25/98.75 in ±10%), NOT SHOWN, order | `scoring.verdict` | matches |
| 7 | TOO FEW EVENTS (<5 counted years or <150 events); no win-bar count | `scoring.place_verdicts`, `win_bar_summary` | matches |
| 7 | Win bar blind and any try; every verdict printed | `scoring.win_bar_summary`, summary | matches |
| 7 | Credit rule | `scoring.credit_check` | matches; numbers not written (finding 3) |
| 7 | Fresh-onset score and "beats bar on subset" | `scoring.fresh_onset_summary` | matches one reading (finding 6) |
| 7 | Decision check (training 90th pct, per year counts) | `scoring.decision_check` | matches |
| 7 | By station, by year, episodes (<7 days), satellite presence | `run_study.py` | matches |
| 8 | Planted-bug tests | none | **missing** (finding 1) |
| 8 | Full run twice, byte-identical | not automated | runner's step (8c) |

## Tests that cannot fail (or cannot catch the bug they are named for)
1. `test_pipeline_data_li.py::test_reindexed_daily_columns_named_like_sf_and_station_text`: every value is 1.0
   except one `chla_max` cell. It misses a mean/min swap and any parameter swap (demonstrated).
2. `test_scoring.py` verdict tests (`..._large_margin`, `..._beats_but_not_large`, `..._years_rule_blocks_beats`,
   `..._no_meaningful_difference`, `..._not_shown`, `test_place_verdicts_and_win_bar`): the cases are so clear that a
   95% interval gives the same verdicts. Nothing pins the 0.625% / 1.25% points (demonstrated).
3. `test_pipeline_models.py::test_station_moon_products_are_onehot_times_moon`: checks names only, not values
   (demonstrated).
4. `test_pipeline_models.py::test_leaving_an_unsplittable_column_out_of_a_tree_changes_nothing`: uses a constant
   column, which `fit_tree` never drops, so it says nothing about the drop branch (demonstrated).
5. `test_scoring.py::test_fresh_onset_summary_uses_only_fresh_examples`: the expected value comes from the same
   `year_table` and `primary_score` functions on the same subset, so it cannot catch a wrong counted-year rule.
6. `test_pipeline_run.py::test_verdicts_use_verdict_years_only`: recomputes with the same `place_verdicts`. It
   checks the year filter only, not any verdict rule.
7. `test_scoring.py::test_bootstrap_is_deterministic_and_seeded`: checks that some seed is used, not that it is
   20261117 (now pinned by my constants test).

## Files
- This report: `research/07-code-review-opus.md`.
- Review tests: `tests/test_review_opus.py` (made-up data only; 14 passed; the full suite of 93 passed together).
- No file in `src/` or any existing test was changed. Nothing committed.

---

## Decisions on each finding (Claude, Fable; 2026-11-17, before any score was computed on real data)
| # | Finding | Decision | What was done |
|---|---|---|---|
| 1 | BLOCKER: no kept planted-bug tests; four builder tests cannot fail | Accepted | Kept the reviewer's rule tests. Added `tests/planted_bugs.py`: 36 planted bugs (the builder's 26 plus 10 for the gaps named here and the fixes below), each run against the test that should catch it. Result logged in `WORKLOG.md`. |
| 2 | Long Island run skips the anchor | Accepted | `run_study.main` runs the anchor for both places; test added. Reading 18 in `DEVIATIONS.md`. |
| 3 | Bar scores and credit numbers not written | Accepted | New output `primary_scores.csv` (every method) and a line in `summary.txt`; test rebuilds the numbers by hand. |
| 4 | Pre-2017 turbidity dropped at two Long Island stations | Accepted as written (no code change) | Reading 16 in `DEVIATIONS.md`; goes in the report's limits. |
| 5 | D1 proof test never runs the drop branch | Accepted | New test fits a tree with and without an all-missing input: same scores, input logged. |
| 6 | Fresh-onset score re-applies the 5-event rule | Accepted as a reading | Reading 17 in `DEVIATIONS.md`. |
| 7 | A T4 run recomputes T1 to T3 | Accepted | T4 will be written to a new folder and its T1 to T3 columns compared with the blind run's file. |
| 8a | Convergence warnings not logged | Accepted | Every warning raised while fitting is written per year to `audit_warnings.csv` and counted in `summary.txt`. |
| 8b | SF `last_day` setting unused | Checked | The SF frame's last date is [redacted: from the restricted Bay file] (Claude read the date only), so the setting changes nothing. |
| 8c | Byte-identical double run not automated | Accepted | Claude runs each place twice and compares file hashes. |
| 8d–f | One-class year, unseen station, qualifier codes | No action needed | As the reviewer says. |
