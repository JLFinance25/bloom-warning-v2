# Test plan (pre-registration) — DRAFT, not locked

Drafted by Claude (AI) on 2026-11-17 for Jayden Ling. Lock date: (not locked). Seen or approved by Jayden: (not yet).
Once this file is locked (committed alone as `PREREG.md`), any change is a deviation and is written in
`DEVIATIONS.md` and in the report. Every try listed here is reported, whatever it shows.

## 1. Question
On a day when a station's chlorophyll is below its own "high" line, can we say whether it will cross that line
in the next 1 to 3 days, better than (a) a one-input rule and (b) the old team model? And does the same recipe
work in a second place, on fully public data?

Not claimed, whatever the result: that this predicts harmful algal blooms, toxins, or causes. The target is
chlorophyll that is high for that station.

## 2. What has already been seen (honesty about blindness)
- **San Francisco Bay: not blind.** The team's old model and its scores on one split (training to 2024-08-16) are
  known (`research/00-old-model3-facts.md`). Claude has also counted examples per station and year with a
  simpler threshold (same file, point 7). No new input and no new method has been fitted or scored.
- **Long Island: blind.** Only the public catalogue has been read (which measurements exist, for which dates).
  No data value has been downloaded or seen.

## 3. Places and data
- **SF Bay.** The team's daily file of SFEI moored-sensor data, `MSP_combined_daily_all_stations.csv`, at the
  team repo commit `c7a2c32`. Private; findings only. Stations: the old model's nine ([redacted: from the restricted Bay file]). Record: from the first day in the file (2013-07-24).
- **Long Island.** USGS daily values for stations 01311143, 01310740, 01304562, 01304650, 01303152: chlorophyll
  (parameter 32316), water temperature (00010), salinity (90860), dissolved oxygen (00300), turbidity (63680),
  each as daily mean, maximum and minimum (statistic codes 00003, 00001, 00002). Record: from each station's
  first day to 2025-12-31 for the verdict. Days flagged provisional by USGS are kept and their share is reported.
- The daily mean is used only when the source gives one. No gap is filled. Turbidity below zero is set to zero.

## 4. The task (same rule in both places)
- **High line.** For each station and each test year: the 90th percentile of that station's daily-mean
  chlorophyll over its training days only.
- **Example.** A station-day *t* with chlorophyll measured and below the high line, and with chlorophyll measured
  on all three of *t*+1, *t*+2, *t*+3. (A day with part of that window missing is dropped, not counted as "no".)
- **Event.** The example's label is 1 if chlorophyll is at or above the high line on any of those three days.
- **Issue time.** End of day *t*. Inputs may use anything measured on or before day *t*, and anything known in
  advance from the calendar (season, moon phase). Nothing measured after day *t*.
- For SF Bay the team's `labels.py` builds examples (imported, not rewritten). For Long Island Claude writes the
  same rule, and a test on made-up data must show both codes give the same examples and labels.

## 5. Test design: one test year at a time
- For test year *Y*: train on examples dated on or before 10 days before 1 January *Y* (a 7-day gap plus the
  3-day label window), score every example dated in year *Y*. High lines, scaling and fill-in values come from the
  training days only.
- A station is scored in year *Y* only if it has at least 300 training days with chlorophyll.
- **Verdict years.** SF Bay: 2017 to 2024 (eight years; SFEI calls 2025-26 provisional). Long Island: 2015 to
  2025 (eleven years).
- **Reported but outside the verdict:** SF Bay 2025 and 2026 (to 2026-06-14) as "provisional years"; Long Island
  2026 to date.
- **Anchor.** Before any new number is trusted, the code must reproduce the old single-split scores from the
  team's files: ratio-only [redacted: from the restricted Bay file] and logistic [redacted: from the restricted Bay file] on [redacted: from the restricted Bay file] examples and [redacted: from the restricted Bay file] events, to four decimals.

## 6. Methods
All fitted methods use fixed settings. Nothing is tuned on test years.

**Bars (what must be beaten)**
- **B1, one-input rule.** Score = today's chlorophyll divided by the high line. Nothing is fitted.
- **B2, old model.** SF Bay: the team's logistic model, same inputs (`BASE_FEATURE_COLUMNS`: ratio, 7-day slope,
  dissolved oxygen, temperature, turbidity, salinity, sunlight, wind speed, gusts, wind direction, tide range and
  its 7-day mean, season) and same settings (standardised inputs, `LogisticRegression(class_weight="balanced",
  random_state=42, max_iter=5000)`, missing values filled with training medians), refit for each test year.
  Long Island: the same model on the inputs that exist there without outside data: ratio, 7-day slope, dissolved
  oxygen, temperature, turbidity, salinity, season.
- Also reported for reading, never as the bar: the base rate, a month-only rule and a station-only rule.

**Tries (four, all reported)**
- **T1, richer station state (logistic, B2's settings).** B2's inputs plus, all from the same station up to day
  *t*: peak chlorophyll today over the high line; change in the ratio over 1 and 3 days; highest ratio in the
  last 7 days; days since the last day at or above the line (capped at 60); dissolved-oxygen daily swing (max
  minus min); 3-day changes in temperature, turbidity and salinity; moon phase as two numbers (sine and cosine of
  the 14.765-day spring-neap cycle); and station indicators, alone and multiplied by the two moon-phase numbers.
- **T2, T1 plus neighbours.** Adds, from the other stations of the same place on day *t*: their mean ratio,
  their highest ratio, how many are at or above their own line, and how many reported.
- **T3, trees.** `HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
  min_samples_leaf=40, l2_regularization=1.0, early_stopping=False, random_state=42)` on T2's inputs, with the
  station as one category input and missing values left missing. No class weights.
- **T3-twin (not a try; for reading).** The same tree model on B2's inputs only. It separates "a better model"
  from "better inputs".
- **T4, T3 plus outside data at each station's own location.**
  (a) Sentinel-2 (level 2A, from the open AWS catalogue): from the newest image taken on or before day *t* that
  has at least 10 clear water pixels within 150 m of the station (water and cloud taken from the image's own
  scene-classification layer): the median of (B05 − B04)/(B05 + B04), a red-edge index used for chlorophyll;
  the median red reflectance (B04), a stand-in for muddiness; the median of B03/B02; the number of water pixels;
  and the image's age in days. Missing if no such image within 30 days. Reflectance is put on one scale using the
  offset the catalogue states for each image.
  (b) Weather at the station's coordinates (Open-Meteo historical archive, if its terms allow; otherwise dropped
  and logged): sunlight total and maximum wind speed on day *t*, and their 3-day means ending on day *t*.
  **T4 is run after T1 to T3 have been scored, so it is not blind to their results.** Its inputs and settings
  are fixed here. If a station's coordinates cannot be sourced, T4 is not run for that place and that is
  reported.

## 7. Scoring and verdicts
- **Score.** Average precision (also called PR-AUC), computed on all verdict-year examples of a place pooled
  together, each scored by the model trained for its year. Higher is better; guessing scores the base rate.
- **Margin** of a try = its score divided by the bar's score, minus 1. The bar is the better of B1 and B2.
- **Uncertainty.** Resample whole test years with replacement, 10,000 times, seed 20261117; in each draw re-pick
  the bar and recompute the margin. Interval: the middle 98.75% (0.05 split across four tries).
- **Years won.** A try wins a year if its score in that year beats the better of B1 and B2 in that year. Only
  years with at least 5 events count. Required: at least three-quarters of counted years, rounded up (6 of 8).
- **Verdict per try and place:**
  - **BEATS BY A LARGE MARGIN:** margin at least +25%, interval's low end at least +10%, and the years rule met.
  - **BEATS:** interval's low end above 0, and the years rule met.
  - **NO MEANINGFUL DIFFERENCE:** the whole interval lies between −10% and +10%.
  - **NOT SHOWN:** anything else.
- **Jayden's win bar** ("a pretty large margin") is met for a place only if at least one try gets BEATS BY A
  LARGE MARGIN there. Every try's verdict is printed next to it, so one lucky try cannot hide three misses.
- Also reported, no verdict: the share of events caught and the share of warnings that were right in the top
  tenth of scores; scores by station and by year; the count of separate bloom episodes (events at one station
  less than 7 days apart count as one); how often satellite inputs were present.

## 8. Checks before any result is believed
- Tests on made-up data for every rule in sections 4 to 7, with planted bugs to show the tests catch them.
- The anchor in section 5.
- The full run is done twice and the output files must match byte for byte.
- An independent Opus agent re-derives the scores and verdicts with its own code from the saved predictions.
- Library versions are pinned and written in the report.

## 9. Known limits, stated now
- "End of day *t*" assumes the sensor reading is in hand that evening. The shelf-life study showed readings may
  be [redacted: from the restricted Bay file]. This plan does not fix that; it compares methods under the old model's own assumption.
- Eight to eleven test years is few for the resampling above, so intervals are rough.
- Events cluster into episodes, so there are fewer independent blooms than events.
- Chlorophyll [redacted: from the restricted Bay file] (team's figure) and the cause is unknown. [redacted: from the restricted Bay file]
- Sensor fluorescence stands in for chlorophyll, and sensor swaps can shift it.
- The second-place search was cut short by a search cap; a better place may exist.

Drafted with Claude (AI); directed, checked and approved by Jayden Ling. (True only once he has done so.)
