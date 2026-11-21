# Series-choice check (exploratory, run after the results were seen)

Written 2026-11-20 by Claude (Fable), on Jayden's go-ahead. Drafted with Claude (AI); directed by Jayden Ling.
**This is not a registered result.** It changes no score, verdict or file of the study.

## The question
An outside review (Codex, 2026-11-19) pointed out that `src/data_li.py` picks between competing sensor series by
counting values over the whole record, test years included. Does that choice move the Long Island scores?

## What the data shows
Only turbidity at two stations has competing series (01310740 and 01304562; three statistics each)
[results/li_run1/audit_li_series.csv]. At both, the two series never share a day: one runs to 2017
(01310740: 2010-01-01 to 2017-05-18, 2,217 mean values; 01304562: 2012-08-15 to 2017-10-01, 792 mean values) and the other starts in 2017
(2017-05-25 and 2017-10-03, to 2026-11-16). Keeping one series dropped every value of the other; the registered rule
kept the newer, longer one. [counted from the files in `data/raw/usgs_long_island/`]

## What was run
A scratch copy of the public repository (commit `a6184af`), with a switch added to `src/data_li.py`
(`data_li.patch` here; the project's own `src/` was not touched). Four runs of the Long Island study, same command:
- **registered**: the rule as run. Control: 18 of 19 output files byte-identical to `results/li_run1/`
  (the other, `summary.txt`, differs only in a first line the run adds).
- **splice**: on each day use whichever series has a value. Uses no future information and drops nothing.
  Not checked: whether the two series are the same instrument and scale.
- **before2020** and **before2024**: count values only before that date. Together with the registered run they give
  the choice a "count only days before each test year" rule would make: older series at both stations for test
  years 2015 to 2020; newer at 01304562 and older at 01310740 for 2021 to 2024; newer at both for 2025.

To rerun: in a copy of the repository, from its root, run
`git apply research/10-series-choice-check-2026-11-20/data_li.patch`, then run the README's study command with the
environment variable `SERIES_MODE` unset, `splice`, `before:2020-01-01` or `before:2024-01-01`, each with its own
`--out` folder.

## Result
Primary scores [runs/*/primary_scores.csv]:

| Method | registered | splice | per-test-year choice (point score only) |
|---|---|---|---|
| One-input rule (B1) | 0.4840 | 0.4840 | 0.4840 |
| B2-LI | 0.4404 | 0.4404 | 0.4390 |
| T1 | 0.4328 | 0.4326 | 0.4304 |
| T2 | 0.4218 | 0.4218 | 0.4230 |
| T3 | 0.4739 | 0.4788 | 0.4765 |

- **Splice: no verdict changes.** T1 -10.6% (range -21.3% to -1.8%), T2 -12.8% (-24.7% to -2.5%),
  T3 -1.1% (-15.7% to +13.4%), all NOT SHOWN, bar B1 [runs/splice/verdicts.csv].
- The per-test-year column is an event-weighted mean of yearly scores taken from the three runs
  (2015 to 2020 from before2020, 2021 to 2024 from before2024, 2025 from registered). The same formula reproduces
  the registered primary scores to six places. T3 margin against B1: -1.6%. T3 was ahead of the
  one-input rule in 6 of 11 counted years; the plan's win rule needs 9 [runs/*/year_table.csv; runs/registered/verdicts.csv].
  No range and no verdict were computed for it.
- Events and examples per year are identical in all four runs (labels use chlorophyll only).
- The largest move is T3: 0.4739 to 0.4788 with splice. No variant puts any try above the one-input rule.

## Limits
- Exploratory, chosen after the results were known. One reviewer-suggested check, two variants; no other variant was tried.
- The per-test-year rule is a literal reading; for some test years it picks a series with no values in that year.
- The two series may differ in instrument or scale; not checked.
- No range or verdict was computed for the per-test-year column.
- The runs were not repeated by a second agent. One AI reviewer recomputed the numbers above from the saved tables.
