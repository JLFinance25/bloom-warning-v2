GATE PASSED: my own code re-derived every score, interval and verdict in both places, and rebuilt the label and five inputs for 200 random examples per place, with no mismatch (123 checks, 0 FAIL).

# Independent tester gate (PREREG section 8)

Tester: Claude (Opus), independent of the builder. Date: 2026-11-17.
Inputs checked: `data/processed/sf_run1/` and `data/processed/li_run1/` (one real run each).
Spec used: `PREREG.md` sections 3 to 8, `DEVIATIONS.md` (D1, readings 1 to 18).
Drafted with Claude (AI); directed, checked and approved by Jayden Ling (true only once he has done so).

## How the checks work
- **Part A** reads only `predictions.csv` and uses only pandas, numpy and `sklearn.metrics.average_precision_score`. Nothing from `src/` is imported.
- **Part B** rebuilds the label and five inputs with my own code, from raw daily chlorophyll.
  - Long Island: I parse the five USGS RDB files myself.
  - SF Bay: I take the cleaned daily frame from `data_sf.load_sf_frame` (as allowed), then do the rest myself.
  - I call `run_study.year_data` only to get the pipeline's own input values to compare against.
- Numbers match if within 1e-9. Labels and flags must match exactly. Missing must match missing.
- "Pipe" = the pipeline's value in the output files. "Mine" = my re-derived value.

## Part A: SF Bay (verdict years 2017 to 2024)

| Quantity | Pipe | Mine | Diff | Result |
|---|---|---|---|---|
| Per-year AP, 9 methods x 10 years; examples, events, counted flags per year | year_table.csv | same | max 5.0e-13 | PASS |
| Counted years / events in counted years | [redacted: from the restricted Bay file] | [redacted: from the restricted Bay file] | 0 | PASS |
| Primary B1 | [redacted: from the restricted Bay file] | [redacted: from the restricted Bay file] | <1e-12 | PASS |
| Primary B2 | [redacted: from the restricted Bay file] | [redacted: from the restricted Bay file] | <1e-12 | PASS |
| Primary T1 / T2 / T3 | [redacted: from the restricted Bay file] | same | <1e-12 | PASS |
| Primary T3-twin, base rate, month-only, station-only | [redacted: from the restricted Bay file] | same | <1e-12 | PASS |
| Bar method | [redacted: from the restricted Bay file] | [redacted: from the restricted Bay file] | - | PASS |
| Margin T1 / T2 / T3 | [redacted: from the restricted Bay file] | same | <1e-12 | PASS |
| Years won / counted / required T1, T2, T3 | [redacted: from the restricted Bay file] | same | 0 | PASS |
| Interval T1 (0.625%, 99.375%) | [redacted: from the restricted Bay file] | [redacted: from the restricted Bay file] | 2.5e-13 / 4.3e-13 | PASS |
| Interval T2 | [redacted: from the restricted Bay file] | [redacted: from the restricted Bay file] | 4.4e-13 / 1.3e-14 | PASS |
| Interval T3 | [redacted: from the restricted Bay file] | [redacted: from the restricted Bay file] | 3.7e-14 / 2.8e-13 | PASS |
| 1.25% / 98.75% points (for NO MEANINGFUL DIFFERENCE) T1, T2, T3 | not written | [redacted: from the restricted Bay file] | - | [redacted: from the restricted Bay file] |
| Low end reaches +10% | [redacted: from the restricted Bay file] | [redacted: from the restricted Bay file] | - | PASS |
| Verdict T1 / T2 / T3 | [redacted: from the restricted Bay file] | [redacted: from the restricted Bay file] | - | PASS |
| TOO FEW EVENTS | [redacted: from the restricted Bay file] | [redacted: from the restricted Bay file] | - | PASS |
| Win bar, blind tries / any try | [redacted: from the restricted Bay file] | [redacted: from the restricted Bay file] | - | PASS |
| Credit allowed (T3 > twin; T2 > B2) | [redacted: from the restricted Bay file] | [redacted: from the restricted Bay file] | - | PASS |
| Part-window events, all test years | [redacted: from the restricted Bay file] | [redacted: from the restricted Bay file] | 0 | PASS |
| Pooled AP, 9 methods | pooled.csv | same | max 3.4e-13 | PASS |
| Fresh-onset primary, 9 methods; [redacted: from the restricted Bay file]; beats-bar flags | fresh_onset.csv | same | max 4.2e-13 | PASS |
| Sanity: no duplicate (station, date); all 9 scores finite; dates in their year; verdict_year and counted_in_verdict columns | - | [redacted: from the restricted Bay file] | - | PASS |
| Sanity: stations, examples, events, part-window events and base rate per year vs audit_years.csv | - | all 10 years | - | PASS |

## Part A: Long Island (verdict years 2015 to 2025)

| Quantity | Pipe | Mine | Diff | Result |
|---|---|---|---|---|
| Per-year AP, 9 methods x 12 years; examples, events, counted flags | year_table.csv | same | max 4.9e-13 | PASS |
| Counted years / events | 11 / 458 | 11 / 458 | 0 | PASS |
| Primary B1 / B2 | 0.483999 / 0.440427 | same | <1e-12 | PASS |
| Primary T1 / T2 / T3 | 0.432773 / 0.421824 / 0.473949 | same | <1e-12 | PASS |
| Primary T3-twin, base rate, month-only, station-only | 0.438922, 0.087187, 0.181799, 0.105591 | same | <1e-12 | PASS |
| Bar method | B1 | B1 | - | PASS |
| Margin T1 / T2 / T3 | -10.58% / -12.85% / -2.08% | same | <1e-12 | PASS |
| Years won T1, T2, T3 | 2/11, 1/11, 6/11; need 9 | same | 0 | PASS |
| Interval T1 | [-0.2125, -0.0174] | same | 4.1e-13 / 6.3e-15 | PASS |
| Interval T2 | [-0.2470, -0.0255] | same | 1.3e-13 / 3.0e-14 | PASS |
| Interval T3 | [-0.1506, +0.1224] | same | 2.5e-13 / 2.2e-13 | PASS |
| 1.25% / 98.75% points T1, T2, T3 | not written | [-0.200, -0.027], [-0.236, -0.037], [-0.132, +0.103] | - | none inside ±10% on both ends, so not NMD |
| Verdict T1 / T2 / T3 | NOT SHOWN x3 | NOT SHOWN x3 | - | PASS |
| TOO FEW EVENTS | no | no (11 years, 458 events) | - | PASS |
| Win bar, blind / any | NOT MET / NOT MET | NOT MET / NOT MET | - | PASS |
| Credit allowed (T3 > twin; T2 > B2) | True (True; False) | True (True; False) | - | PASS |
| Part-window events | 28 | 28 | 0 | PASS |
| Pooled AP | pooled.csv | same | max 4.2e-13 | PASS |
| Fresh-onset primary; 11 years, 201 events; beats-bar flags | fresh_onset.csv | same | max 4.5e-13 | PASS |
| Sanity checks (as for SF Bay) | - | 8,229 rows, 12 years | - | PASS |

**Bootstrap.** I read PREREG section 7 as: each draw picks n counted years with replacement, and the draw's primary score is the event-weighted mean of per-year scores, with a year's weight multiplied by how often it was drawn. I drew with `numpy.random.default_rng(20261117).integers(0, n, size=(10000, n))` and took numpy's default (linear) percentiles. My intervals match the pipeline's to about 1e-13. So the pipeline uses the same reading and, it seems, the same draws. No difference could flip a verdict.

## Part B: labels and five inputs, 200 random test examples per place

**How drawn.** `rng = numpy.random.default_rng(20261117)`; `rng.choice(len(predictions), 200, replace=False)`, positions taken against `predictions.csv` in file order, then sorted. Same seed, separately, for each place.

Each example was rebuilt from raw daily chlorophyll: taking part (at least 300 measured days on or before 31 Dec of Y-1), high line (`sorted(values)[int(0.9 n)]`), whether the day is a valid example, `onset`, `part_window`, and the five inputs. I also checked `fresh_onset`, and that B1 equals the ratio.

| Item | SF Bay matches | SF largest diff | LI matches | LI largest diff | Result |
|---|---|---|---|---|---|
| Valid example (measured, below the line, window rule) | 200/200 | - | 200/200 | - | PASS |
| Station takes part (>=300 days before cut-off) | 200/200 | - | 200/200 | - | PASS |
| High line | 200/200 | 0 | 200/200 | 0 | PASS |
| onset | 200/200 | - | 200/200 | - | PASS |
| part_window | 200/200 | - | 200/200 | - | PASS |
| fresh_onset (extra) | 200/200 | - | 200/200 | - | PASS |
| ratio | 200/200 | 0 | 200/200 | 0 | PASS |
| d1_ratio | 200/200 | 0 | 200/200 | 0 | PASS |
| max7_ratio | 200/200 | 0 | 200/200 | 0 | PASS |
| days_since_high | 200/200 | 0 | 200/200 | 0 | PASS |
| moon_sin | 200/200 | 0 | 200/200 | 0 | PASS |
| B1 in predictions.csv equals my ratio | 200/200 | 5.0e-13 (CSV rounding) | 200/200 | 5.0e-13 | PASS |

Edge cases the sample actually hit:
- **SF Bay:** [redacted: from the restricted Bay file]
- **Long Island:** 17 events, 2 missing `d1_ratio`, 16 with a gap in t-6..t, 80 with a high within 60 days, 2 partly measured windows.

Extra checks beyond the sample (all PASS):
- **Full recount, both places, every test year.** My rule gives exactly the same set of (station, date) test examples as `predictions.csv`. It also gives the same `onset`, `part_window` and `fresh_onset` on every one, and the same B1 within 1e-9. That is [redacted: from the restricted Bay file] SF Bay and 8,229 Long Island examples. This covers the partly measured windows in the SF Bay sample: [redacted: from the restricted Bay file].
- **Long Island raw parse.** My RDB parse of daily-mean chlorophyll equals the pipeline's frame on every day at every station.
  - Each station has one chlorophyll-mean series, so the "most days" rule (reading 1) never had to choose.
  - No chlorophyll-mean value carries "e", so none were dropped.
  - One non-numeric entry (station 01304650) becomes missing (reading 2).
  - The "<", ">" and "[4]" codes are kept.
- **High-line position.** `int(0.9 n)` never differs from the exact integer `(9 n) // 10` for any line used, so floating-point error does not move a line.

## Could not check (UNVERIFIED)
- **Model scores.** B2, T1, T2, T3, T3-twin and the reading rules' scores were taken as given. I re-fitted no model, as instructed. Part A shows the arithmetic on those scores is right, not that the models were fitted as the plan says.
- **Other inputs.** These were not rebuilt: `slope7`, `ratio_max`, `d3_ratio`, `do_swing`, `d3_temp/turb/sal`, `moon_cos`, season, the four neighbour inputs, and SF Bay's weather and tide columns.
- **Training data.** Training examples, training labels and the 21 December embargo were not checked. I checked test examples only, apart from the base rate, which matches the audit's training counts.
- **SF Bay cleaning.** The team's `load_msp`, the hygiene steps and the start date are not checked independently. My SF Bay rebuild starts from the pipeline's cleaned frame, so an error inside `load_sf_frame` would not show up here.
- **Readings 9 and 16** (Long Island turbidity) do not touch the five inputs, so they were not exercised.
- **Not re-checked by me:** the anchor, the byte-for-byte second run, `decision_check.csv`, `episodes.csv`, and the station scores. (`sf_run2/` and `li_run2/` exist; I did not compare them.) T4 was not run by the pipeline.

## Things in the outputs that could mislead a reader
1. **"NOT SHOWN" hides "shown worse" at Long Island.** T1's interval is [-21.2%, -1.7%] and T2's is [-24.7%, -2.5%]. Both lie wholly below zero. By the plan's own resampling, T1 and T2 did worse than B1 there. The plan's word list has no label for this, so a reader of the verdicts alone would miss it. The write-up should say it.
2. **"Credit to new inputs allowed: True" (at Long Island; [redacted: from the restricted Bay file] at SF Bay) reads like a win.** It only means T3 out-scored T3-twin at Long Island. No try beat the bar at Long Island; [redacted: from the restricted Bay file] at SF Bay. There is no gain over the bar to credit.
3. **Fresh-onset "beats bar" is True for T3 at Long Island ([redacted: from the restricted Bay file] at SF Bay).** The edges are small and come with no interval:
   - SF Bay: [redacted: from the restricted Bay file].
   - Long Island: 0.5732 vs 0.5311, about +7.9%.

   PREREG lets a try "warn of new onsets" only if it *also* beats the bar on this subset. With T3 NOT SHOWN overall, that wording should not be used.
4. **The bar is B1, not the old model.** B1 (the one-input rule) beat B2 at Long Island ([redacted: from the restricted Bay file] at SF Bay), so every Long Island margin is against the simple rule. At SF Bay, [redacted: from the restricted Bay file]. That is not a verdict comparison and should not be quoted as one.
5. **Cosmetic:** `summary.txt` prints years won as "[redacted: from the restricted Bay file]". `verdicts.csv` has the integers.
6. **Fewer SF Bay stations in early years.** [redacted: from the restricted Bay file], and Long Island has a single station in 2015 to 2018. That is why T1 equals T2 there. Both follow the plan, but a reader may assume all stations count in every year.

## What I ran
```
cd bloom-warning-v2
OMP_NUM_THREADS=1 .venv/bin/python tests/tester_gate_opus.py
```
Result: `123 PASS, 0 FAIL`, `GATE PASSED`, exit code 0, about 9 seconds.
- The script prints no SF Bay measured value: only counts, flags, differences and scores already in the outputs.
- It writes no file.
- Nothing in `src/`, `data/`, the existing tests, `PREREG.md`, `DEVIATIONS.md` or `WORKLOG.md` was changed.
- No commit was made.
