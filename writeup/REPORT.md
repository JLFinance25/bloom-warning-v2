# Can a richer model warn of high chlorophyll better than a one-input rule? A pre-registered test at Long Island, NY (negative result)

Status of the study: tries T1 to T3 are finished; try T4 was run after T1 to T3 were scored, so it is not a blind test.

The plan (`PREREG.md`) also covered San Francisco Bay, using a sensor file whose owner has not agreed to publication. That half was run, but its results are not reported here, and values from that file are redacted in this copy of the plan [PUBLIC-COPY-NOTES.md; WORKLOG.md].

Source tags in square brackets are file paths inside this project. Tags that start with `li_run1/` or `li_t4_run1/` point to the run output files, which this copy keeps in `results/`. Two tags name files that are not in this copy, because the satellite and weather downloads and other built files are not committed: `data/processed/outside_li.csv` (made by `src/outside_join.py`) and the weather files in `data/raw/openmeteo_li/` (how to download them: `data/raw/SOURCES.md`). "Plan" means `PREREG.md`.

## 1. Answer in brief
No. Neither a richer logistic model (T1, T2; a standard statistical model that weighs several inputs into one score) nor a tree model (T3) was shown to beat the simple rule "today's chlorophyll as a share of the station's own high line" at Long Island, so the pre-set win bar was NOT MET [li_run1/summary.txt]. The best result was T3: -2.1% against the simple rule, with a range from -15.1% to +12.2% that includes zero [li_run1/verdicts.csv]. T1 and T2 scored below the simple rule in 9 (T1) and 10 (T2) of the 11 years, and both ranges lie below zero. The ranges are probably too narrow, so read this as likely worse, not proven [li_run1/verdicts.csv]. Adding satellite and weather inputs to the tree model (T4, not blind) made almost no change in the primary score: 0.4738 against 0.4739 for T3. Whether T4 and T3 are equivalent was not tested, and single years moved both ways [li_t4_run1/primary_scores.csv; li_t4_run1/year_table.csv].

## 2. The question
The question: on a day when a station's chlorophyll is below its own "high" line, can we say whether it will cross that line in the next 1 to 3 days? And does a model with richer inputs do this better than (a) a one-input rule and (b) the earlier model's recipe, rebuilt here on local sensor inputs? The earlier model and its code were written by the Bay Protectors team in the BeSMART 2026 summer program. Jayden Ling, who directs this project, was one of the team's four members. The team's repository is private, so there is no link to it; the source is its commit `c7a2c32` [PREREG.md section 3; WORKLOG.md].

The "high" line is each station's own 90th-percentile chlorophyll value from its training years. The target is chlorophyll that is high for that station. It says nothing about toxins or harm [PREREG.md sections 1 and 4].

## 3. What was fixed in advance
- **Pre-registration.** The plan (data, labels, methods, scores, verdict rules) was written and locked before any Long Island value was downloaded [PREREG.md header; WORKLOG.md]. It was locked in a private git commit and was not filed with an outside registry, so the lock time is the project's own record [DEVIATIONS.md; WORKLOG.md]. Long Island was blind [PREREG.md section 2].
- **The bars.** B1 is the one-input rule: score = today's chlorophyll divided by the station's high line; nothing is fitted. B2 is the earlier model's recipe, refit each test year. At Long Island, B2 is called B2-LI and has only local sensor inputs: no tide, sun or wind. That is fewer inputs than the earlier model's full recipe. B2-LI scored lower than B1 (0.4404 against 0.4840), so B1 was the bar for every margin [PREREG.md section 6; li_run1/primary_scores.csv; li_run1/verdicts.csv].
- **The tries.** T1: B2 plus richer station inputs (peak chlorophyll, recent change, days since the last high day, daily swing in dissolved oxygen, moon phase). T2: T1 plus the readings of neighbouring stations. T3: a tree model (many small yes/no decision charts, each one built to correct the errors of those before it; the method is called gradient boosting) on the same inputs. T4: T3 plus satellite and weather inputs, run after T1 to T3 were scored. T3-twin is the same tree model with only the old inputs; it is a reference, not a try [PREREG.md section 6].
- **Scoring.** Each test year is scored with average precision, a 0-to-1 score for how near the top of the warning list the real events sit. The guessing baseline gives every example in a test year one constant value (the event share of the training years), so it cannot rank examples. Its score for that year is that year's base rate, the share of that year's examples that are events [src/models.py]. The primary score is the mean of the yearly scores, weighted by events, over years with at least 5 events [PREREG.md section 7]. No score is a probability.
- **The win bar, as a number.** A try "wins" at a place only if all three rules hold. (1) Its range of margins stays above zero. (2) It is ahead of the place's bar method (here B1) in at least three-quarters of the counted years. (3) Its margin is at least +25%. The bar is the better of B1 and B2 by primary score. The margin is the try's primary score divided by the bar's primary score, minus 1. The range comes from 10,000 resamples of the years. It is a 98.75% range, because four tries share the 5% error budget [PREREG.md section 7]. A first draft of the plan also required the low end of the range to reach +10%. The locked plan only reports whether it does [PREREG-draft.md; PREREG.md header and section 7].
- **What "NOT SHOWN" means.** The try was neither shown better nor shown equal. It is the plan's catch-all word. It does not mean "close", and it does not mean "worse". Section 5 shows a case where it hides "worse".

## 4. Data
**Long Island, New York.** Public daily values from five USGS stations: chlorophyll fluorescence, water temperature, salinity, dissolved oxygen and turbidity, each as daily mean, maximum and minimum. 18,799 daily rows were pulled on 2026-11-17. Station 01304650 has no salinity series [data/raw/SOURCES.md]. License: public domain (U.S. Government work); credit USGS [data/raw/SOURCES.md]. Verdict years are 2015 to 2025: 11 counted years, 458 events [li_run1/primary_scores.csv]. 2026 is reported outside the verdict [li_run1/summary.txt].

The team's rule for examples and labels is used unchanged. An example is a station-day below the high line. The label looks at the next three calendar days. It is 1 if any day that was measured is at or above the line. It is 0 only if all three days were measured and none is at or above the line. Any other example is dropped [PREREG.md section 4; team_code/model3/data/raw/model3_hab/code/labels.py].

## 5. Results
Each cell is a primary score (average precision). Base rate (guessing): 0.0872 at Long Island. That figure is the yearly base rates combined the same way as every primary score (weighted by events), so it is higher than the plain share of all examples that are events, 458 of 7,060, or 0.0649. The plan also reports two other simple rules for reading only, never as the bar: they score 0.1818 (month only) and 0.1056 (station only) [li_run1/primary_scores.csv; li_run1/year_table.csv; PREREG.md section 6].

**Long Island, 11 counted years, 458 events. Bar method: B1.** B2-LI has fewer inputs than the earlier model's full recipe, but it scored lower than B1, so B1 was the bar for every margin.

| Method | Primary score | Margin over the bar | Range (98.75%) | Years ahead of the bar | Verdict |
|---|---|---|---|---|---|
| B1, one-input rule (the bar) | 0.4840 | n/a | n/a | n/a | n/a |
| B2-LI | 0.4404 | not a try | n/a | n/a | n/a |
| T1 | 0.4328 | -10.6% | -21.2% to -1.7% | 2 of 11 (9 needed) | NOT SHOWN |
| T2 | 0.4218 | -12.8% | -24.7% to -2.5% | 1 of 11 (9 needed) | NOT SHOWN |
| T3 | 0.4739 | -2.1% | -15.1% to +12.2% | 6 of 11 (9 needed) | NOT SHOWN |
| T3-twin (reference) | 0.4389 | not a try | n/a | n/a | n/a |
| T4 (not blind) | 0.4738 | -2.1% | -13.4% to +10.2% | 6 of 11 (9 needed) | NOT SHOWN |

[li_run1/primary_scores.csv; li_run1/verdicts.csv; T4 row: li_t4_run1/primary_scores.csv; li_t4_run1/verdicts.csv]

Win bar: NOT MET, both for the blind tries (T1 to T3) and for any try, T4 included [li_run1/summary.txt; li_t4_run1/summary.txt].

**Plainly: T1 and T2 scored below the one-input rule B1 in 9 (T1) and 10 (T2) of the 11 years, and both ranges lie below zero.** The ranges are probably too narrow, so read this as likely worse, not proven [li_run1/verdicts.csv]. T1 and T2 are the same model in the four one-station years (2015 to 2018) [li_run1/year_table.csv; li_run1/audit_years.csv]. The plan's word for this is "NOT SHOWN", because the plan has no label for "shown worse". The word hides the finding.

**Scores by year (average precision, rounded to 4 places).** Verdict years are 2015 to 2025. The row marked "outside" is reported but does not count [li_run1/year_table.csv; T4 column: li_t4_run1/year_table.csv]. Section 10 has every method.

| Long Island year | Events | B1 | B2-LI | T3 | T4 (not blind) |
|---|---|---|---|---|---|
| 2015 | 45 | 0.5810 | 0.5175 | 0.5955 | 0.6112 |
| 2016 | 23 | 0.5748 | 0.6082 | 0.4161 | 0.3836 |
| 2017 | 17 | 0.4974 | 0.3718 | 0.6118 | 0.5452 |
| 2018 | 29 | 0.4764 | 0.4086 | 0.6311 | 0.6300 |
| 2019 | 36 | 0.5257 | 0.4608 | 0.4397 | 0.4137 |
| 2020 | 55 | 0.3875 | 0.4063 | 0.4770 | 0.4479 |
| 2021 | 42 | 0.5141 | 0.3373 | 0.4324 | 0.4627 |
| 2022 | 24 | 0.4870 | 0.3860 | 0.2774 | 0.4159 |
| 2023 | 10 | 0.3916 | 0.2510 | 0.4955 | 0.4821 |
| 2024 | 91 | 0.4139 | 0.4021 | 0.4141 | 0.3684 |
| 2025 | 86 | 0.5225 | 0.5210 | 0.4939 | 0.5330 |
| 2026 (outside) | 79 | 0.4527 | 0.5108 | 0.5379 | 0.5110 |

The scores swing a lot from year to year. T3 is ahead of B1 in some years and behind in others. In one of T3's 6 years ahead, the lead was only 0.0003 (2024: 0.4141 against 0.4139) [li_run1/year_table.csv].

**Descriptive only (no verdict, no range).**
- Credit check: T3 scored above T3-twin (0.4739 vs 0.4389); this gap was not tested. T2 did not score above B2-LI (0.4218 vs 0.4404) [li_run1/summary.txt]. This is not a win. It suggests the new station inputs helped the tree model compared with the same tree on the old inputs, but with no range the gap is not shown to be real. No try was shown better than B1.
- Fresh onsets (examples with no high day in the previous 14 days): T3 scored 0.5732 vs B1 0.5311 [li_run1/fresh_onset.csv]. This gap is small and has no range, and T3 was not shown better overall. So this report does not say any try "warns of new onsets".

## 6. What the result does and does not show
**Known (from the files).** Under this plan and these settings, no try was shown better than the one-input rule. T1 and T2 were worse than it. The bar that mattered was B1, not the earlier model: B1 scored higher than B2-LI [li_run1/primary_scores.csv].

**Author's reading (not a verdict).** Most of what a model can use here is already in today's chlorophyll relative to the high line. In the logistic models, the extra inputs did not lift the score above B2-LI, the same model without them [li_run1/primary_scores.csv]; these results do not show why. Every try used settings fixed in advance, with nothing tuned, and the early training sets are small (the 2015 fits used 334 training examples, 25 of them events) [PREREG.md section 6; li_run1/audit_years.csv]. The tree model was the only try near the bar. A T3 result speaks only for the fixed T3 settings, not for tree models in general [PREREG.md section 7].

**What it does not show.** It does not show that richer inputs can never help. It does not show that T3 is no better than B1: its range, -15.1% to +12.2%, includes possible gains as well as losses [li_run1/verdicts.csv]. In made-up Long Island-like worlds (event counts guessed, not real), a true margin of about +20% reached the win bar in 19% of runs, about +42% in 67%, and about +9% in 2% [research/06-power-check.txt]. So this test could miss a true gain of about 20% or less most of the time. It says nothing about toxins, harm or causes. It does not test readings that arrive late.

## 7. Checks that were run
- **Tests and planted bugs.** 165 tests passed. A script plants 36 bugs, one at a time. The tests caught 34 of 36 on the first run; two tests were then sharpened, and the second run caught 36 of 36 [WORKLOG.md]. After every run was done, two tests and two planted bugs were added for the `--no-anchor` option: 167 tests passed and 38 of 38 planted bugs were caught [WORKLOG.md].
- **Independent code check** (a second AI agent, before any score was computed). No label, input, score or verdict differed from the plan, and no leak of future data was found. It found one blocker about the testing (no planted-bug tests) and three should-fix items. All were fixed before the real run [research/07-code-review-opus.md; WORKLOG.md].
- **Byte-identical double run.** The Long Island run was done twice, and every output file matched byte for byte [WORKLOG.md].
- **Independent tester gate** (another agent, with its own code, not using the study's scoring code). It re-derived every yearly score, primary score, margin, range and verdict at Long Island, with differences of at most about 5e-13. It also rebuilt the label, the high line and five inputs for 200 random test examples: 200 of 200 matched [research/08-tester-gate-opus.md]. It did not check the model fits, the other inputs, or the training examples [research/08-tester-gate-opus.md].

## 8. Limits and deviations
**Three deviations (D1 to D3)** [DEVIATIONS.md]. **D1.** The plan said tree models keep an input that is missing on every training example. The software raises an error on such a column, so the column is left out of that year's tree fit and logged. This cannot change a score, because a column with no values offers no split. It applied to Long Island neighbour inputs in 2015 to 2018, and to T4's satellite inputs in test years 2015 to 2017 (section 9) [DEVIATIONS.md; li_run1/audit_left_out.csv; li_t4_run1/audit_left_out.csv]. No score had been seen when this was decided.

**D2.** The plan said T4 is still run where a station has no sourced coordinates, with the satellite inputs missing there. At San Francisco Bay no sourced coordinates were found for any station, so T4 was not run there at all [DEVIATIONS.md; WORKLOG.md]. **D3.** The plan said every try is reported. This public report covers Long Island only, because the owner of the Bay sensor file has not agreed to publication, so it cannot be used to judge the Bay half either way [DEVIATIONS.md]. D2 and D3 were written down as deviations on 2026-11-19, after an independent AI read of the published copy.

**Readings where the plan was silent** (19 of them, listed in `DEVIATIONS.md`; choices made where the plan gave no rule, not changes. Readings 1 to 15 were chosen by the AI agents that built the code and accepted by the AI drafter; readings 16 to 19 were added by the AI drafter itself [DEVIATIONS.md; WORKLOG.md]). The ones that matter to a reader:
- Reading 16: at two Long Island stations, the USGS turbidity record is split at a 2017 sensor change. The plan's rule keeps only the newer part, so turbidity is missing there before 2017. Every method sees the same loss.
- Reading 17: the 5-events rule is applied again for the fresh-onset score, so a year can drop out of that score.
- Reading 19, added after every run was done: a `--no-anchor` option lets a Long Island run skip the anchor check (the plan's first check, in which the new code must reproduce the earlier model's recorded counts and scores on the restricted Bay file [PREREG.md section 5]), and marks the summary "ANCHOR NOT RUN". With no restricted data on disk, every Long Island output file matched the reported runs byte for byte apart from that line [DEVIATIONS.md; WORKLOG.md]. Section 9 gives the same check with the extracts in `team_code/`. No score in this report comes from a run made with `--no-anchor`.
- Reading 9: Long Island turbidity is not floored at zero; no negative value exists [li_run1/audit_counts.csv].
- Readings 1 to 8 and 10 to 15 cover series choice, qualifier codes, the decision-check percentile, a few wording and counting rules, how pooled and per-station scores are built, and the satellite and weather inputs.

**Other limits.**
- B2-LI has no tide, sun or wind, which is fewer inputs than the earlier model's full recipe. It scored lower than B1, so B1 was the bar for every margin. Line 3 of both `summary.txt` files (`li_run1` and `li_t4_run1`) says every Long Island margin is against B2-LI. That sentence is wrong: column `bar_method` in `verdicts.csv` shows B1. The result files are left as generated; see `DEVIATIONS.md` [li_run1/verdicts.csv; li_run1/primary_scores.csv; DEVIATIONS.md].
- Long Island has one station in 2015 to 2018, three in 2019 to 2023, four in 2024 and five in 2025 [li_run1/audit_years.csv]. In the single-station years, T1 and T2 are identical.
- Turbidity gap: see reading 16.
- USGS provisional values are kept: 5.3% of Long Island values [li_run1/audit_counts.csv]. For chlorophyll alone, 1,505 of 12,267 station-days (12.3%) are provisional. At 01303152 the share is 89.8%, and that station's 19 verdict-year events are all in 2025 [li_run1/audit_li_provisional_chla.csv; li_t4_run1/station_scores.csv; li_t4_run1/audit_satellite.csv]. The USGS values are as published on the download date, so they include revisions made after the fact; a live system would see rougher data [PREREG.md section 9].
- Series choice used the whole record. Where a station had two series for one parameter, the series with the most non-missing days over the whole record was kept, so later coverage (test years and 2026) chose the series used in earlier years. This applies only to turbidity at 01310740 and 01304562. The effect on scores was not measured. Choosing on training years only would need a rerun; that has not been done [src/data_li.py; li_run1/audit_li_series.csv; DEVIATIONS.md reading 1].
- Part-window events (events where some of the next three days were not measured): 28 at Long Island, across all test years, including those outside the verdict [li_run1/summary.txt]. 26 of the 458 verdict-year events are part-window [li_t4_run1/episodes.csv]. A part-window day is kept if it is an event and dropped if it is not. This applies to every method alike [team_code/model3/data/raw/model3_hab/code/labels.py].
- Eleven years is few for resampling, so the ranges are probably too narrow. Events cluster in blooms, so there are fewer independent blooms than events [PREREG.md section 9].
- "End of day t" assumes the reading is in hand that evening. Real readings can arrive later; this study does not test that [PREREG.md section 9].
- T4 is a retrospective test. Its weather for day t comes from ERA5, which runs about 5 days behind, and the 2026-11-17 pull was filled only to 2026-11-10. So that weather would not be in hand on the evening of day t [src/outside_weather.py; data/raw/SOURCES.md; src/outside_join.py]. T4 showed almost no change in the primary score, so this did not flatter its result.
- The sensors measure fluorescence (a light signal that stands in for chlorophyll), not chlorophyll itself [PREREG.md section 9; research/04-short-list.md].
- This place was chosen after a search that a search cap cut short; a better place may exist [research/04-short-list.md].
- T4 (satellite and weather) is not blind to the T1 to T3 results, so it can never be a blind test [PREREG.md section 6].
- One branch of the satellite brightness rule covers 37 usable station-images from early 2022, about 1% of the 3,628 usable ones. That branch is reasoned from the pixel values and could not be cross-checked against a second copy of the same pass [WORKLOG.md].

## 9. T4 (satellite and weather), and rerunning the Long Island half
### T4 at Long Island: run, NOT SHOWN, and not a blind test
T4 is the T3 tree model plus nine outside inputs at each station's coordinates [PREREG.md section 6]. Five come from the newest usable Sentinel-2 satellite image of the last 30 days: a chlorophyll colour index (NDCI), red brightness, the green-to-blue ratio, the count of clear water pixels, and the image's age in days. Four come from weather records: the day's sunlight and wind, and their 3-day means [src/outside_join.py]. T4 was run after T1 to T3 were scored, with the study code unchanged since the freeze [WORKLOG.md].

- **Result.** T4 scored 0.4738 and T3 scored 0.4739 (a difference of -0.00015). Against the bar B1 (0.4840), T4's margin is -2.1%, with a range from -13.4% to +10.2%. It was ahead of B1 in 6 of 11 years (9 needed). Verdict: NOT SHOWN. The win bar for any try stays NOT MET [li_t4_run1/primary_scores.csv; li_t4_run1/verdicts.csv; li_t4_run1/summary.txt].
- **Against T3, year by year.** T4 was ahead of T3 in 4 of the 11 counted years and behind in 7 [li_t4_run1/year_table.csv]. The outside inputs moved single years up or down, with almost no net change in the primary score. Whether T4 and T3 are equivalent was not tested.
- **Descriptive only.** Pooled over all verdict-year examples, T4 scored 0.4307 and T3 0.4436. On fresh onsets, T4 scored 0.5336, T3 0.5732 and B1 0.5311 [li_t4_run1/summary.txt]. No range is attached to these.
- **Coverage.** A usable image (10 or more clear water pixels, at most 30 days old) existed for 6,465 of the 7,060 verdict-year test examples (92%), and for 99% in 2018 to 2025 [li_t4_run1/audit_satellite.csv]. The catalogue's first image is from 2017-01-13 [data/raw/SOURCES.md]. So for test years 2015 to 2017, no training example had an image. The five satellite inputs were left out of those fits, and T4 was T3 plus weather only [li_t4_run1/audit_left_out.csv].
- **Checks.** T4 was run twice, and every output file matched byte for byte. The T1 to T3 prediction columns and verdict rows in the T4 run are identical to the first run's [WORKLOG.md]. The independent tester's scoring code, pointed at the T4 outputs, re-derived T4's yearly scores, primary score, margin, range and verdict: 54 checks passed, 0 failed [WORKLOG.md]. That code was written for T1 to T3 and was reused here by the AI drafter, not by an independent agent, so this is a weaker check than the original gate.
- **Data.** 3,672 catalogue items were read around the five stations. They gave 7,327 station-image rows; 3,628 of those rows had at least 10 clear water pixels and were usable [WORKLOG.md; data/raw/SOURCES.md].

**Author's reading (not a verdict).** The image in use is about a week old on average (mean 7.7 days, median 6, over all station-days with an image) [data/processed/outside_li.csv, built by src/outside_join.py]. It shows the water colour that the sensor already measures every day at the same spot. So it is not surprising that it adds little to a one-station, 1-to-3-day question. This says nothing about what satellite images could add where there is no sensor.

### Rerunning the Long Island half
- An outside reader can rerun the Long Island half with `--no-anchor`. Four separate checks stand behind that.
  1. **The extracts match the team's files.** The folder `team_code/` holds extracts of four of the team's files: only the functions and settings the Long Island run uses, copied line for line apart from a few marked cuts to the notes inside the code, with the team's permission. They are extracts, not whole files. Each time the public copy is built, a build script checks that every kept function and setting is the same as in the team's file. The code as Python reads it must be equal, with comments and docstrings (the notes written inside the code) set aside, or the build stops. The script itself is not in the public copy.
  2. **What was cut.** A few notes inside the code were cut, each marked "[Public copy: ...]" in the file: whole sentences from two docstrings, one comment sentence and two end-of-line comments. One import line was narrowed to the one name the file uses [team_code/README.md; WORKLOG.md].
  3. **A rerun from the extracts.** Run from a copy that held only these extracts and no restricted data, every Long Island output file matched the reported runs byte for byte, apart from the first line of `summary.txt` [WORKLOG.md].
  4. **The T4 table.** That rerun used the satellite and weather table as already built. In a separate check, the table was rebuilt from the raw downloads alone, and it was byte-identical to the one the runs used [WORKLOG.md].

## 10. Also reported under the plan (no verdict)

The plan lists items to report with no verdict [PREREG.md section 7]. They are below. A script built each table from the output file named under it. Nothing in this section changes a verdict. T4 is not a blind test.

**Low end of the range.** The plan asks whether the low end of each try's range reaches +10%. No try's low end reaches +10% [li_t4_run1/verdicts.csv].

**Scores by year, every method (average precision).** The row marked "outside" does not count toward a verdict.

| Long Island year | Examples | Events | B1 | B2-LI | T1 | T2 | T3 | T3-twin | T4 |
|---|---|---|---|---|---|---|---|---|---|
| 2015 | 233 | 45 | 0.5810 | 0.5175 | 0.6464 | 0.6464 | 0.5955 | 0.4918 | 0.6112 |
| 2016 | 234 | 23 | 0.5748 | 0.6082 | 0.4838 | 0.4838 | 0.4161 | 0.4995 | 0.3836 |
| 2017 | 232 | 17 | 0.4974 | 0.3718 | 0.3693 | 0.3693 | 0.6118 | 0.5389 | 0.5452 |
| 2018 | 251 | 29 | 0.4764 | 0.4086 | 0.3646 | 0.3646 | 0.6311 | 0.4744 | 0.6300 |
| 2019 | 805 | 36 | 0.5257 | 0.4608 | 0.4381 | 0.4481 | 0.4397 | 0.4604 | 0.4137 |
| 2020 | 664 | 55 | 0.3875 | 0.4063 | 0.3882 | 0.3874 | 0.4770 | 0.4490 | 0.4479 |
| 2021 | 680 | 42 | 0.5141 | 0.3373 | 0.4159 | 0.3821 | 0.4324 | 0.4884 | 0.4627 |
| 2022 | 889 | 24 | 0.4870 | 0.3860 | 0.3222 | 0.2751 | 0.2774 | 0.3177 | 0.4159 |
| 2023 | 947 | 10 | 0.3916 | 0.2510 | 0.2717 | 0.2589 | 0.4955 | 0.3159 | 0.4821 |
| 2024 | 994 | 91 | 0.4139 | 0.4021 | 0.3640 | 0.3414 | 0.4141 | 0.3590 | 0.3684 |
| 2025 | 1131 | 86 | 0.5225 | 0.5210 | 0.4997 | 0.4928 | 0.4939 | 0.4564 | 0.5330 |
| 2026 (outside) | 1169 | 79 | 0.4527 | 0.5108 | 0.4539 | 0.4344 | 0.5379 | 0.5322 | 0.5110 |

[li_t4_run1/year_table.csv]

**Scores by station, pooled over the verdict years (average precision).** Each station's verdict-year examples are scored as one list. Long Island stations are shown by USGS site number.

| Long Island station | Examples | Events | B1 | B2-LI | T1 | T2 | T3 | T3-twin | T4 |
|---|---|---|---|---|---|---|---|---|---|
| 01303152 | 200 | 19 | 0.6047 | 0.6428 | 0.6076 | 0.5983 | 0.6691 | 0.5400 | 0.6706 |
| 01304562 | 1948 | 143 | 0.5079 | 0.4074 | 0.4048 | 0.3876 | 0.4268 | 0.3529 | 0.4272 |
| 01304650 | 353 | 36 | 0.3081 | 0.3329 | 0.2781 | 0.2780 | 0.2894 | 0.2607 | 0.2116 |
| 01310740 | 1895 | 82 | 0.4163 | 0.3326 | 0.3639 | 0.3288 | 0.3527 | 0.3755 | 0.3583 |
| 01311143 | 2664 | 178 | 0.5008 | 0.4167 | 0.4001 | 0.3912 | 0.5290 | 0.4886 | 0.5159 |

[li_t4_run1/station_scores.csv]

**Pooled score over all verdict-year examples (average precision).** Each method gets one score, from all verdict-year examples in a single list instead of year by year.

| B1 | B2-LI | T1 | T2 | T3 | T3-twin | T4 | Base rate |
|---|---|---|---|---|---|---|---|
| 0.4632 | 0.3969 | 0.3845 | 0.3717 | 0.4436 | 0.4088 | 0.4307 | 0.0813 |

Here "Base rate" is the pooled score of the guessing rule. That rule gives every example in a year the same value, but the value differs from year to year, so pooling ranks some years above others. It is not the share of examples that are events.

[li_t4_run1/pooled.csv]

**Fresh-onset score, every method.** This is the primary score on examples with no high day in the previous 14 days. Sections 5 and 9 discuss it.

| Counted years | Events | B1 | B2-LI | T1 | T2 | T3 | T3-twin | T4 | Base rate |
|---|---|---|---|---|---|---|---|---|---|
| 11 | 201 | 0.5311 | 0.4590 | 0.4278 | 0.4234 | 0.5732 | 0.4987 | 0.5336 | 0.0461 |

Here "Base rate" is the guessing rule's score on these examples, combined over years like the others.

[li_t4_run1/fresh_onset.csv]

**Decision check.** A method raises an alarm on a test example when its score is higher than 90% of that method's scores on its own training examples [PREREG.md section 7; DEVIATIONS.md reading 3]. Each cell shows alarms / events caught / false alarms. An alarm is false when the example is not an event. The last row is the total over the verdict years.

| Long Island year | Events | B1 | B2-LI | T1 | T2 | T3 | T4 |
|---|---|---|---|---|---|---|---|
| 2015 | 45 | 79 / 39 / 40 | 63 / 32 / 31 | 62 / 33 / 29 | 62 / 33 / 29 | 64 / 35 / 29 | 72 / 36 / 36 |
| 2016 | 23 | 21 / 12 / 9 | 15 / 11 / 4 | 23 / 13 / 10 | 23 / 13 / 10 | 26 / 12 / 14 | 35 / 14 / 21 |
| 2017 | 17 | 31 / 10 / 21 | 44 / 15 / 29 | 43 / 13 / 30 | 43 / 13 / 30 | 43 / 17 / 26 | 45 / 17 / 28 |
| 2018 | 29 | 28 / 13 / 15 | 43 / 18 / 25 | 52 / 18 / 34 | 52 / 18 / 34 | 71 / 24 / 47 | 65 / 23 / 42 |
| 2019 | 36 | 39 / 21 / 18 | 59 / 21 / 38 | 71 / 21 / 50 | 80 / 22 / 58 | 111 / 27 / 84 | 97 / 27 / 70 |
| 2020 | 55 | 59 / 25 / 34 | 70 / 29 / 41 | 82 / 28 / 54 | 79 / 27 / 52 | 85 / 29 / 56 | 86 / 33 / 53 |
| 2021 | 42 | 51 / 27 / 24 | 41 / 18 / 23 | 55 / 20 / 35 | 49 / 19 / 30 | 61 / 27 / 34 | 65 / 25 / 40 |
| 2022 | 24 | 32 / 15 / 17 | 28 / 10 / 18 | 29 / 11 / 18 | 37 / 12 / 25 | 65 / 13 / 52 | 70 / 16 / 54 |
| 2023 | 10 | 35 / 7 / 28 | 49 / 7 / 42 | 49 / 8 / 41 | 52 / 8 / 44 | 65 / 9 / 56 | 78 / 9 / 69 |
| 2024 | 91 | 180 / 61 / 119 | 159 / 52 / 107 | 173 / 55 / 118 | 169 / 54 / 115 | 224 / 63 / 161 | 231 / 62 / 169 |
| 2025 | 86 | 134 / 61 / 73 | 136 / 59 / 77 | 126 / 52 / 74 | 119 / 51 / 68 | 151 / 68 / 83 | 164 / 72 / 92 |
| 2026 (outside) | 79 | 134 / 48 / 86 | 122 / 49 / 73 | 114 / 47 / 67 | 111 / 46 / 65 | 153 / 59 / 94 | 151 / 59 / 92 |
| Verdict years, total | 458 | 689 / 291 / 398 | 707 / 272 / 435 | 765 / 272 / 493 | 765 / 270 / 495 | 966 / 324 / 642 | 1008 / 334 / 674 |

[li_t4_run1/decision_check.csv]

**Episodes.** Events at one station less than 7 days apart count as one episode. An episode is counted in the year of its first event [PREREG.md section 7; DEVIATIONS.md reading 7]. In the verdict years (2015 to 2025), 135 episodes started.

| Long Island year | Events | Part-window events | Episodes starting |
|---|---|---|---|
| 2015 | 45 | 8 | 13 |
| 2016 | 23 | 2 | 8 |
| 2017 | 17 | 0 | 5 |
| 2018 | 29 | 1 | 9 |
| 2019 | 36 | 0 | 11 |
| 2020 | 55 | 4 | 16 |
| 2021 | 42 | 2 | 11 |
| 2022 | 24 | 2 | 9 |
| 2023 | 10 | 0 | 3 |
| 2024 | 91 | 1 | 25 |
| 2025 | 86 | 6 | 25 |
| 2026 (outside) | 79 | 2 | 20 |

[li_t4_run1/episodes.csv]

**Satellite presence by year and station (Long Island, T4).** Each cell shows how many test examples had a usable image (as defined in section 9), out of all test examples for that station and year. "No examples" means the station did not take part that year.

| Year | 01303152 | 01304562 | 01304650 | 01310740 | 01311143 |
|---|---|---|---|---|---|
| 2015 | no examples | no examples | no examples | no examples | 0 of 233 |
| 2016 | no examples | no examples | no examples | no examples | 0 of 234 |
| 2017 | no examples | no examples | no examples | no examples | 182 of 232 |
| 2018 | no examples | no examples | no examples | no examples | 247 of 251 |
| 2019 | no examples | 333 of 338 | no examples | 301 of 316 | 149 of 151 |
| 2020 | no examples | 201 of 201 | no examples | 255 of 255 | 208 of 208 |
| 2021 | no examples | 272 of 277 | no examples | 146 of 146 | 257 of 257 |
| 2022 | no examples | 274 of 274 | no examples | 301 of 301 | 309 of 314 |
| 2023 | no examples | 284 of 289 | no examples | 363 of 363 | 295 of 295 |
| 2024 | no examples | 276 of 276 | 217 of 217 | 264 of 279 | 212 of 222 |
| 2025 | 200 of 200 | 283 of 293 | 136 of 136 | 233 of 235 | 267 of 267 |
| 2026 | 276 of 278 | 258 of 258 | 195 of 197 | 251 of 253 | 183 of 183 |

[li_t4_run1/audit_satellite.csv]

**Two data notes the plan asks for.** USGS marked 4 Long Island values as estimated; they were dropped. Another 2 entries were not numbers and were treated as missing [li_run1/audit_counts.csv]. The five Long Island stations fall in five different weather grid cells, so no two stations share a cell [data/raw/openmeteo_li/ station files; PREREG.md section 6].

## 11. Sources (all pulled 2026-11-17 unless stated)
- USGS daily values: https://waterservices.usgs.gov/nwis/dv/ (public domain; credit USGS) [data/raw/SOURCES.md].
- Sentinel-2 and Open-Meteo/ERA5 (used by T4 only; no other score uses them): https://earth-search.aws.element84.com/v1 and https://archive-api.open-meteo.com/v1/archive [data/raw/SOURCES.md]. Credit lines the terms ask for: "Contains modified Copernicus Sentinel data"; weather data by Open-Meteo (CC BY 4.0); ERA5 data from the Copernicus Climate Change Service [data/raw/SOURCES.md].
- The team's earlier model comes from the Bay Protectors team in the BeSMART 2026 summer program. The team's repository is private, so there is no link; commit `c7a2c32` [PREREG.md section 3; WORKLOG.md]. Extracts of its code are in `team_code/` [team_code/README.md].
- Plan and logs: `PREREG.md`, `DEVIATIONS.md`, `WORKLOG.md`.

## 12. AI-use line
Drafted with Claude (AI); directed, checked and approved by Jayden Ling.
