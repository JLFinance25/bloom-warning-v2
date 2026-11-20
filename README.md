# Bloom warning v2: a pre-registered test (negative result)

**Answer.** No. A richer model was not shown to warn of high chlorophyll better than a one-input rule at Long Island, NY. The pre-set win bar was NOT MET [li_run1/summary.txt]. The bar that mattered was the one-input rule (B1): today's chlorophyll as a share of the station's own "high" line. It scored 0.4840. The earlier model's recipe, rebuilt on local inputs (B2-LI), scored 0.4404 [li_run1/primary_scores.csv]. The plan was locked in a private git commit before the Long Island download. It was not filed with an outside registry, so the lock time is the project's own record [DEVIATIONS.md; WORKLOG.md]. The earlier model and its code come from the Bay Protectors team in the BeSMART 2026 summer program. Jayden Ling, who directs this project, was one of the team's four members. The team's repository is private, so there is no link; the source is its commit `c7a2c32` [PREREG.md section 3; WORKLOG.md].

The plan (`PREREG.md`) also covered San Francisco Bay, using a sensor file whose owner has not agreed to publication. That half was run, but its results are not reported here, and values from that file are redacted in this copy of the plan [PUBLIC-COPY-NOTES.md; WORKLOG.md]. Nothing in this copy says what the Bay half showed, in either direction (see D3 in `DEVIATIONS.md`).

The target is chlorophyll that is high for that station, 1 to 3 days ahead. It is not about toxins or harm. No score is a probability.

## Results
Score = average precision, a 0-to-1 score for how high the real events rank in the warning list (higher is better). Margin = the try's score divided by the one-input rule's score, minus 1; zero means a tie. Range = the span that holds 98.75% of the margins when the counted years are re-drawn at random 10,000 times. In each re-draw the bar is whichever of the one-input rule and B2-LI scores higher in that draw [src/scoring.py].

Long Island (11 counted test years, 2015 to 2025; 458 events) [li_run1/verdicts.csv; li_run1/primary_scores.csv]

| Method | Score | Margin | Range | Verdict |
|---|---|---|---|---|
| One-input rule | 0.4840 | the bar | n/a | n/a |
| T1 | 0.4328 | -10.6% | -21.2% to -1.7% | NOT SHOWN |
| T2 | 0.4218 | -12.8% | -24.7% to -2.5% | NOT SHOWN |
| T3 (trees) | 0.4739 | -2.1% | -15.1% to +12.2% | NOT SHOWN |

T1 and T2 scored below the one-input rule in 9 (T1) and 10 (T2) of the 11 years. Both ranges lie below zero, but the ranges are probably too narrow, so read this as likely worse, not proven [li_run1/verdicts.csv; li_run1/year_table.csv]. "NOT SHOWN" is the plan's catch-all word for a missed win bar, and here it hides that. B2-LI has fewer inputs (no tide, sun or wind) than the earlier model's full recipe. That does not affect the margins: the one-input rule B1 scored higher (0.4840 against 0.4404), so B1 was the bar for every margin [li_run1/primary_scores.csv; li_run1/verdicts.csv]. A try with satellite and weather inputs (T4) was run after the others, so it is not a blind test. Its primary score was almost unchanged: 0.4738 against 0.4739 for the same model without those inputs. Whether the two are equivalent was not tested, and single years moved both ways [li_t4_run1/primary_scores.csv; li_t4_run1/year_table.csv].

## Rerun the Long Island half
The Long Island half uses the extracts in `team_code/`, which the code finds by default [src/config.py; team_code/README.md]. It needs Python 3.14.4 and the exact package versions in `requirements.txt`; every run checks Python and the main packages and stops if they differ [PREREG.md section 6; src/config.py]. The commands below expect them in a virtual environment (a private Python install for this project) in a folder named `.venv`, for example made with `python3.14 -m venv .venv` and then `.venv/bin/pip install -r requirements.txt`. The five USGS station files the study used are in `data/raw/usgs_long_island/`, with a manifest that lists each file's request address, size and SHA-256 [data/raw/usgs_long_island/MANIFEST.json]. The command below runs the study on them.
```
OMP_NUM_THREADS=1 .venv/bin/python src/run_study.py --place li --out data/processed/li_run1 --no-anchor
```
[src/run_study.py]. Compare the new folder with `results/li_run1/`. Expect every file to match except the first line of `summary.txt` [WORKLOG.md]. `--no-anchor` skips a start-up check (the "anchor") that needs the restricted Bay file [PREREG.md section 5; DEVIATIONS.md reading 18]. Every score in the report came from runs where that check passed [WORKLOG.md]. A run made with this option says "ANCHOR NOT RUN" at the top of `summary.txt` [DEVIATIONS.md reading 19].

To start from a fresh download instead, move the five `.rdb` files and `MANIFEST.json` out of `data/raw/usgs_long_island/`. The script does not replace a station file that is already there, and it rewrites the manifest [src/download_usgs.py]. Then run `.venv/bin/python -I src/download_usgs.py`, and run the study command above with another `--out` folder. USGS may revise recent provisional values, so a fresh download may not match the study's files [data/raw/SOURCES.md]. A download on 2026-11-18 differed in all five files. A run on it gave the same three verdicts and the same scores to four places for the one-input rule, T1 and T2; T3 was 0.4781 against the reported 0.4739 [WORKLOG.md].

T4 also needs the satellite and weather table. The commands to build it are at the top of `src/outside_sentinel2.py` (search, fetch, process), `src/outside_weather.py` (fetch, process) and `src/outside_join.py`; the satellite step reads about 14.6 GB over the network [data/raw/SOURCES.md]. Then run `run_study.py` as above with `--outside data/processed/outside_li.csv` and another `--out` folder.

The run uses code from the earlier team project. The folder `team_code/` holds extracts of four of the team's files, included with credit and with the team's permission: only the functions and settings this run uses, copied line for line apart from a few marked cuts to the notes inside the code and one narrowed import line [team_code/README.md]. Run from a copy that held only these extracts and no restricted data, every Long Island output file matched the reported runs byte for byte, apart from the first line of `summary.txt` [WORKLOG.md]. For T4, that rerun used the satellite and weather table as already built. In a separate check, the table was rebuilt from the raw downloads alone, and it was byte-identical to the one the runs used [WORKLOG.md].

## Where things are
- `PREREG.md`: the locked plan; in this copy, values from the restricted Bay file are redacted and marked. `DEVIATIONS.md`: the three deviations, 19 readings and one known error in two generated result files. `WORKLOG.md`: what happened, in order.
- `research/`: notes, the independent code check and the independent tester gate [research/08-tester-gate-opus.md].
- `writeup/REPORT.md`: the full report, with limits.
- `team_code/`: extracts of four of the team's code files, plus three package files that hold only a header, with credit. Its README says what was kept, left out and changed.
- Data: USGS public domain, pulled 2026-11-17; the five files are in `data/raw/usgs_long_island/` [data/raw/SOURCES.md]. T4 also used Sentinel-2 images and Open-Meteo/ERA5 weather; their credit lines are in `writeup/REPORT.md` section 11.

## License
- Code in `src/` and `tests/`: MIT License [LICENSE].
- Text and result tables (this README, `PUBLIC-COPY-NOTES.md`, `PREREG.md`, `PREREG-draft.md`, `DEVIATIONS.md`, `WORKLOG.md`, `data/raw/SOURCES.md`, `writeup/`, `research/` and `results/`): Creative Commons Attribution 4.0 [LICENSE-TEXT.md].
- The five USGS station files (`.rdb`) in `data/raw/usgs_long_island/` are U.S. Government data in the public domain [data/raw/SOURCES.md]. Neither license covers them.
- `team_code/` is the team's code. It is included with the team's permission and is not covered by either license [team_code/README.md].

Drafted with Claude (AI); directed, checked and approved by Jayden Ling.
