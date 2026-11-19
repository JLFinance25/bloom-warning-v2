Public copy of the locked plan PREREG.md (commit 09d16c4). Values from the restricted San Francisco Bay sensor file are redacted, and one private folder path is reworded. Every other character is unchanged.

# Test plan (pre-registration): bloom warning v2

Drafted by Claude (AI) for Jayden Ling. **Locked by Claude on 2026-11-17**, before any Long Island data value was
downloaded and before any new input or method was fitted or scored on San Francisco Bay data.
Seen or approved by Jayden: not yet (he saw the first draft's win bar in chat on 2026-11-17; this locked version
changes it as section 7 says). An independent Opus review of the draft (`research/05-prereg-review-opus.md`, 28
findings) was applied before the lock; Claude's decision on each finding is at the end of that file.

After the lock, any change is a deviation: it goes in `DEVIATIONS.md` and in the report. Every try listed here is
reported, whatever it shows.

## 1. Question
On a day when a station's chlorophyll is below its own "high" line, can we say whether it will cross that line
in the next 1 to 3 days, better than (a) a one-input rule and (b) the old team model refit the same way? Does
the same recipe work in a second place, on fully public data?

"Better than the old team model" applies to San Francisco Bay only. Long Island never had the old model; its
second bar is the old recipe on local sensor inputs (section 6).

Not claimed, whatever the result: that this predicts harmful algal blooms, toxins or causes; that any score is a
probability; that it would work with readings that arrive late.

## 2. What has already been seen
- **San Francisco Bay: not blind.** Known before the lock: the old model's scores on one split (training to
  2024-08-16), including [redacted: from the restricted Bay file]
  (`research/00-old-model3-facts.md`); Claude's count of examples per station and year under a simpler line
  (same file, point 7); and the shelf-life study on the same sensor file (in the team's private workspace,
  a different target: next-day water quality). No new input and no new method has been fitted or scored.
- **Long Island: blind.** Only the public catalogue was read (which series exist, for which dates). No value seen.
- **Satellite and weather: blind.** Only catalogue listings and file headers were read.

## 3. Places and data
- **SF Bay.** The team's daily file of SFEI moored-sensor data, `MSP_combined_daily_all_stations.csv`, team repo
  commit `c7a2c32`. Private; findings only. Stations: the old model's nine ([redacted: from the restricted Bay file]
  [redacted: from the restricted Bay file]). Loaded with the team's `labels.load_msp(start="2013-07-24", reindex=True)`, then the team's hygiene
  steps (turbidity floored at 0, the `ph`, `bga` and `fdom` columns dropped). The team's weather and tide files
  supply B2's date-level inputs, as in the old model.
- **Long Island.** USGS daily values for stations 01311143, 01310740, 01304562, 01304650, 01303152: chlorophyll
  (parameter 32316), water temperature (00010), salinity (90860), dissolved oxygen (00300), turbidity (63680),
  each as daily mean (statistic 00003), maximum (00001) and minimum (00002). If a station has more than one
  series for a parameter and statistic, the series with the most non-missing days is used and the choice is
  logged. Values USGS marks estimated ("e") are dropped and counted. Days USGS marks provisional are kept and
  their share is reported. The run reads only the saved raw download. The frame is reindexed to every calendar
  day per station, and the daily-mean chlorophyll column is named `chla_mean`.
- No gap in a measured series is interpolated. Missing model inputs are handled as section 6 says.

## 4. The task (the team's rule, used unchanged in both places)
Examples and labels are built by the team's `labels.build_onset_examples`, called on each place's frame.
- **High line.** `labels.train_thresholds`: per station, the value at sorted position `int(0.9 × n)` of every
  non-missing daily-mean chlorophyll value dated on or before the cut-off (section 5).
- **Example.** A station-day *t* with chlorophyll measured and strictly below the high line, and with at least
  one of *t*+1, *t*+2, *t*+3 measured.
- **Event.** Label 1 if any measured day of *t*+1 to *t*+3 is at or above the high line. If any of the three days
  is missing and no measured day crosses, the example is dropped (it is not counted as a "no").
- **Issue time.** End of day *t*. Inputs may use anything measured on or before day *t* and anything fixed by the
  calendar (season, moon phase). Satellite images must be from day *t*−1 or earlier.
- The report states how many events in each place come from a partly measured window.

## 5. Test design: one test year at a time
For test year *Y*, cut-off *C* = 31 December of *Y*−1.
- **Taking part.** A station takes part in year *Y* (training examples, test examples, neighbour inputs) only if
  it has at least 300 non-missing chlorophyll days dated on or before *C*. Otherwise it is absent from that year.
- **High line** *L(Y)* = `train_thresholds(frame, cutoff=C)` for the stations taking part.
- **Training examples** = `build_onset_examples(frame, L(Y), cutoff=C, split="train", embargo=10)`: example dates
  on or before 21 December of *Y*−1, every one labelled against *L(Y)*.
- **Test examples** = `split="test"` with the same *C* and *L(Y)*, keeping only dates in year *Y*.
- The ratio, B1 and every "at or above the line" input use *L(Y)*, in training and in test. Scaling, fill-in
  values, station lists and category codes come from that year's training examples only.
- **Every method scores every test example.** No example is dropped because an input is missing.
- **Verdict years.** SF Bay: 2017 to 2024. Long Island: 2015 to 2025.
- **Reported outside the verdict:** SF Bay 2025 and 2026 (to 2026-06-14), which SFEI treats as provisional;
  Long Island 2026 to the download date.
- **Anchor (must pass before any new score is computed).** The new code, run with `start="2021-01-01"`, one
  cut-off 2024-08-16, `embargo=7`, test = all examples after the cut-off, must give: [redacted: from the restricted Bay file] test examples and [redacted: from the restricted Bay file]
  events; [redacted: from the restricted Bay file] training examples and [redacted: from the restricted Bay file] events; the nine high lines in the team's
  `onset_dataset.CANONICAL_THRESHOLDS` to 2 decimals; and scikit-learn `average_precision_score` of [redacted: from the restricted Bay file] for
  B1 and [redacted: from the restricted Bay file] for B2, to 4 decimals. If any figure differs, no new score is computed until the cause is found
  and logged in `DEVIATIONS.md`, and the anchor then passes.

## 6. Methods
All settings are fixed here. Nothing is tuned on test years. Environment: Python 3.14.4, pandas 3.0.6, numpy
2.5.4, scikit-learn 1.9.1, scipy 1.18.1, rasterio 1.5.2, `OMP_NUM_THREADS=1`.

**Bars**
- **B1, one-input rule.** Score = today's chlorophyll divided by *L(Y)*. Nothing is fitted.
- **B2 (SF Bay), the old model's headline recipe ("Run A") refit each year.** The 15 columns of the team's
  `BASE_FEATURE_COLUMNS` (ratio; 7-day slope; dissolved oxygen, temperature, turbidity and salinity daily means;
  sunlight; wind speed; gusts; wind direction as sine and cosine; tide range; its 7-day mean; season as sine and
  cosine of day of year over 365.25), plus station one-hot columns (station list from that year's training
  examples), plus a missing-marker column for each input with any missing value in that year's training
  examples; missing values filled with that year's training medians; `StandardScaler`, then
  `LogisticRegression(class_weight="balanced", random_state=42, max_iter=5000)`, other settings default.
  No Delta outflow.
- **B2-LI (Long Island), the old recipe on local sensor inputs.** The same pipeline on: ratio, 7-day slope,
  dissolved oxygen, temperature, turbidity and salinity daily means, season sine and cosine. It has no tide, sun
  or wind, so it is a weaker bar than SF Bay's B2; the report says so wherever Long Island margins appear.
- An input that is missing on every training example of a year is left out of that year's logistic models and
  logged; the tree models keep it.
- Reported for reading, never as the bar: base rate, month-only rule, station-only rule.

**New inputs, defined once.** All on the daily-reindexed series of the same station; *v*(*t*) is the value on day
*t*.
- `ratio_max` = daily maximum chlorophyll on *t* divided by *L(Y)*.
- `d1_ratio`, `d3_ratio` = ratio(*t*) − ratio(*t*−1), ratio(*t*) − ratio(*t*−3); missing if the earlier day is missing.
- `max7_ratio` = highest ratio over the measured days of *t*−6 to *t*.
- `days_since_high` = days from the most recent measured day on or before *t*−1 with chlorophyll at or above
  *L(Y)*; 60 if there is none within 60 days (including before the record starts, or across gaps).
- `do_swing` = dissolved-oxygen daily maximum minus minimum on *t*, in mg/L.
- `d3_temp`, `d3_turb`, `d3_sal` = *v*(*t*) − *v*(*t*−3) for the daily means; missing if either end is missing.
- `moon_sin`, `moon_cos` = sine and cosine of 2π × phase / 14.7652944, where phase = (days from 2000-01-06 18:14
  UTC to 12:00 local standard time on day *t*) mod 14.7652944. Local standard time is UTC−8 (SF Bay) and UTC−5
  (Long Island). In SF Bay, B2 already has tide range, so these mostly add whether tides are strengthening or
  weakening.
- Neighbours, from the other stations of the same place that take part in year *Y* and have chlorophyll measured
  on day *t*, each against its own *L(Y)*: `nb_mean_ratio`, `nb_max_ratio` (missing when none reported),
  `nb_n_high` (how many are at or above their line), `nb_n_reporting`. For SF Bay "other stations" means the
  other eight of the nine.

**Tries (four per place; all reported)**
- **T1, richer station state.** B2's pipeline and columns (station one-hots once), plus `ratio_max`, `d1_ratio`,
  `d3_ratio`, `max7_ratio`, `days_since_high`, `do_swing`, `d3_temp`, `d3_turb`, `d3_sal`, `moon_sin`, `moon_cos`,
  and each station one-hot multiplied by `moon_sin` and by `moon_cos`.
- **T2, T1 plus the four neighbour inputs.**
- **T3, trees.** `HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
  min_samples_leaf=40, l2_regularization=1.0, early_stopping=False, random_state=42)`, no class weights. Inputs:
  B2's base columns (no one-hots, no missing-markers), T1's new columns without the station-times-moon products,
  the four neighbour inputs, and the station as an integer code fitted on training examples and passed through
  `categorical_features`. Missing values stay missing.
- **T3-twin (not a try).** The same tree model on B2's base columns plus the station code.
- **T4, T3 plus outside data at each station's coordinates.** Run after T1 to T3 are scored, so **not blind to
  their results**; inputs and settings are fixed here.
  - (a) Sentinel-2 level 2A from the open AWS catalogue (Earth Search, collection `sentinel-2-l2a`). Image date =
    acquisition date on the local standard clock. Use the newest image dated *t*−1 or earlier, and at most 30
    days old, that has at least 10 clear water pixels. Clear water pixel = scene-classification class 6 (water),
    pixel centre within 150 m of the station in the image's own projection, on the 20 m grid of band B05, with
    B02, B03, B04 (averaged to that grid) and B05 all above zero reflectance. If two images share a date, use the
    one with more clear water pixels; a tie goes to the image ID that sorts first. Inputs: `s2_ndci` = median of
    (B05 − B04)/(B05 + B04); `s2_red` = median B04 reflectance; `s2_green_blue` = median of B03/B02;
    `s2_n_water` = number of clear water pixels; `s2_age` = *t* minus image date in days. All missing if no such
    image. Reflectance = digital number × scale + offset. Whether the catalogue's files already have the offset
    applied is settled before T4 is built, by reading the catalogue's documentation and by checking that the
    darkest 1% of water pixels sit near zero reflectance in one image before and one after 25 January 2022; the
    rule chosen is logged in `WORKLOG.md` before any T4 score exists.
  - (b) Weather from Open-Meteo's historical archive (free for non-commercial use, CC BY 4.0, no key), ERA5
    reanalysis only, daily values on the place's fixed local standard clock: `wx_sun` (shortwave radiation sum)
    and `wx_wind` (maximum 10 m wind speed) on day *t*, and their means over *t*−2 to *t*. If one reanalysis
    cannot be fixed for all years, (b) is dropped and logged. The report states how many distinct weather grid
    cells the stations fall in.
  - Station coordinates must come from a citable source. If a station has none, or its satellite windows cannot
    be read, T4 is still run with those inputs missing there, and that is reported.

## 7. Scoring and verdicts
- **Per-year score.** scikit-learn `average_precision_score` (also called PR-AUC) on one test year's examples.
  Higher is better; guessing scores the base rate.
- **Counted years.** Verdict years with at least 5 events. Other years are reported, not counted.
- **Primary score** of a method at a place = the event-weighted mean of its per-year scores over counted years.
  The score on all verdict-year examples pooled together is reported beside it, with no verdict.
- **Margin** of a try = its primary score divided by the higher of B1's and B2's primary scores, minus 1.
- **Uncertainty.** 10,000 draws, seed 20261117. Each draw picks as many years as there are counted years, with
  replacement; a year's examples count as often as it is drawn; the bar is re-picked in each draw. Interval =
  the 0.625% and 99.375% points of the drawn margins (98.75%; 0.05 split across four tries).
- **Bar method for the years rule.** Chosen once per place: whichever of B1 and B2 has the higher primary score
  (a tie goes to B1). A try wins a year if its per-year score is strictly above that method's in that year.
  Required: at least three-quarters of counted years, rounded up (6 of 8; 9 of 11).
- **Verdict per try and place:**
  - **BEATS:** the interval's low end is above 0 and the years rule is met.
  - **BEATS BY A LARGE MARGIN:** BEATS, and the margin is at least +25%. The report also says whether the low end
    reaches +10%. Wording allowed: "shown better than the bar, with an estimated margin of X%". Not allowed:
    "shown to be at least 25% better".
  - **NO MEANINGFUL DIFFERENCE:** not BEATS, and the 1.25% and 98.75% points of the drawn margins both lie
    between −10% and +10%.
  - **NOT SHOWN:** anything else.
  - **TOO FEW EVENTS:** printed instead of any verdict if the place has fewer than 5 counted years or fewer than
    150 events in counted years. Such a place does not count toward the win bar.
- **The family** is T1 to T4 within one place. The two places are separate claims. B-rules, T3-twin, pooled
  scores and everything in the next bullet are descriptive.
- **Jayden's win bar** ("a pretty large margin") is met at a place if at least one try gets BEATS BY A LARGE
  MARGIN there. It is reported twice: for the blind tries (T1 to T3), and for any try. Every try's verdict is
  printed next to it.
- **Credit for new inputs.** A gain may be credited to the new inputs only if T3 beats T3-twin, or T2 beats B2,
  on the primary score. A T3 result speaks for these fixed settings, not for tree models in general.
- **Also reported, no verdict:**
  - Fresh-onset score: the primary score on examples with no day at or above *L(Y)* in *t*−14 to *t*−1. The
    report may say a try "warns of new onsets" only if it also beats the place's bar method on this subset.
  - Decision check: alarm when a score exceeds the 90th percentile of that model's scores on its own training
    examples; per year, the alarms, events caught and false alarms.
  - Scores by station and by year; the number of separate episodes (events at one station less than 7 days
    apart count as one); satellite presence by year and station.

## 8. Checks
- Tests on made-up data for every rule in sections 4 to 7, with planted bugs to show the tests catch them.
- The anchor in section 5.
- The full run is done twice and the output files must match byte for byte.
- An independent Opus agent re-derives scores and verdicts with its own code from the saved predictions, and
  rebuilds the label and five inputs from the raw files for 200 randomly chosen examples (fixed seed).
- If a bug is found after scores are seen: it is fixed, everything is rerun, both results are reported, and the
  fix goes in `DEVIATIONS.md`.
- **Power check, done before the lock on made-up data** (`research/06-power-check.txt`; no real data). In a
  made-up Bay-like world, with no true difference the rules gave BEATS 0% of the time; with a true margin near
  +35 to +40% they gave BEATS BY A LARGE MARGIN in 78 to 91% of runs; near +15% they gave BEATS in 52 to 95% and
  LARGE in 1 to 16%. In a made-up Long Island-like world (event counts guessed), a true margin near +42% gave
  LARGE in 67% of runs. These numbers describe the made-up world only; real years may vary more.

## 9. Known limits, stated now
- "End of day *t*" assumes the sensor reading is in hand that evening. Readings may in fact be [redacted: from the restricted Bay file] (the
  shelf-life study). This plan compares methods under the old model's own assumption.
- Eight to eleven years is few for resampling; the intervals are probably too narrow, not just rough.
- Events cluster into episodes, so there are fewer independent blooms than events. Many events may be a
  re-crossing inside an existing bloom; the fresh-onset score is there to show that.
- A first-year high line from 300 to 450 days may cover one bloom season only.
- Chlorophyll [redacted: from the restricted Bay file] (team's figure), cause unknown.
- Sensor fluorescence stands in for chlorophyll; sensor swaps can shift it. Daily maximum chlorophyll is
  sensitive to spikes.
- SFEI and USGS values were revised after the fact and satellite archives reprocessed; a live system would see
  rougher data.
- Long Island's "neighbours" are in different bays up to about 100 km apart: they carry a regional season, not
  the spread of one bloom.
- Satellite: the open catalogue starts in January 2017 for both places (checked in the catalogue), so early
  training years have no satellite inputs; muddy or shallow water may not be labelled as water; ERA5 weather
  cells are about 25 km wide, so nearby stations share values.
- The second-place search was cut short by a search cap; a better place may exist.

Drafted with Claude (AI); directed, checked and approved by Jayden Ling. (True only once he has done so.)
