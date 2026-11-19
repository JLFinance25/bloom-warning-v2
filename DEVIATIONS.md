# Deviations from the locked plan

Every place where what was done differs from `PREREG.md` (locked 2026-11-17, commit `09d16c4`). Newest last.
Each entry says whether any score had been seen when the choice was made.

## D1. Tree models cannot "keep" an input that is missing on every training example (2026-11-17)
- **Plan (section 6):** "An input that is missing on every training example of a year is left out of that year's
  logistic models and logged; the tree models keep it."
- **Done:** scikit-learn 1.9.1's `HistGradientBoostingClassifier` raises an error on such a column. So the column is
  left out of that year's tree fit as well, and logged in the audit file (`audit_left_out.csv`).
- **Why it cannot change a score:** a column with one value (or none) offers no split point, so a tree never uses
  it. The builder's test shows a constant column gives byte-identical scores.
- **Where it applies:** Long Island neighbour inputs in 2015 to 2018 (one station, so no neighbours); satellite
  inputs in training years before 2017 (try T4).
- **Scores seen when this was decided:** none. Found while building, on made-up data.

## D2. T4 was not run at San Francisco Bay (2026-11-17; written down as a deviation on 2026-11-19)
- **Plan (section 6):** "If a station has none, or its satellite windows cannot be read, T4 is still run with those
  inputs missing there, and that is reported."
- **Done:** no sourced coordinates were found for any Bay station, so T4 was not run at the Bay at all. T4 was run
  at Long Island only.
- **What had been seen:** the T1 to T3 results at both places.
- **Why it is listed late:** the private report called this "a gap, not a result" and did not list it here. An independent
  read on 2026-11-19 pointed out that it differs from the plan's wording, so it is a deviation.

## D3. The public copy does not report the San Francisco Bay half (2026-11-18; written down on 2026-11-19)
- **Plan (header):** "Every try listed here is reported, whatever it shows."
- **Done:** the Bay tries were run and are reported in the private report. The public copy reports Long Island
  only, because the owner of the Bay sensor file has not agreed to publication.
- **What had been seen:** every result at both places.
- **What a reader should take from it:** the public report cannot be used to judge the Bay half either way.

## Readings of the plan where it was silent (not changes; listed so a reader can disagree)
Chosen by the builder before any score was seen, and accepted by Claude (Fable):
1. USGS series choice: non-missing days are counted before estimated values are dropped; a tie goes to the lower
   series number. Chosen per parameter and statistic.
2. USGS qualifiers other than "e": values marked `<`, `>` or partial-day are kept; non-numeric entries such as
   "Eqp" (equipment fault) are missing.
3. Decision check: the 90th percentile uses numpy's default method; "exceeds" is strictly greater; for the
   one-input rule, "its own training scores" are the training ratios.
4. Fresh-onset wording rule: "beats the bar" on that subset means a strictly higher fresh-onset primary score.
5. Pooled score uses all verdict-year examples; per-station scores are pooled over verdict years.
6. TOO FEW EVENTS replaces the verdict, but the primary score and margin are still printed.
7. Episodes are counted in the year of their first event.
8. SF Bay neighbours come only from stations taking part that year ([redacted: from the restricted Bay file]).
9. Long Island turbidity is not floored at zero (the plan floors SF Bay's only); the files hold no negative value.

### Added 2026-11-17 for the satellite and weather inputs (try T4), before any T4 value was joined to a label
Chosen by the satellite builder, checked and accepted by Claude (Fable). No score of any kind existed.
10. "Within 150 m" means 150 m or less, measured to the pixel centre. USGS station coordinates (listed as NAD83)
    are used as WGS 84; the two differ by under 2 m here.
11. A 20 m pixel is missing if any of the four 10 m pixels inside it has no data (stored value 0).
12. When the scene-class layer has no water pixel within 150 m, the other four bands are not read. The outputs are
    the same (no pixel could count), but that window is saved with the scene-class layer only.
13. Two catalogue items of the same satellite pass (overlapping map tiles, or an original and a reprocessed copy)
    count as two images; the plan's same-date tie rule picks between them.
14. Six items that exist only in a requester-pays store are never usable (reading them needs an account).
15. Weather: the nearest ERA5 grid cell to the station (the service's default would shift to a land cell); the API's
    default units; a 3-day mean is missing if any of its three days is missing.

### Added 2026-11-17 after the independent code review, before any score existed
16. Long Island turbidity at 01310740 and 01304562: USGS holds two turbidity series that are one record split at a
    2017 sensor change, with no overlap. The plan's rule (the series with the most days) keeps the newer one, so
    turbidity is missing at those two stations before 2017 (dates from the reviewer's reading of date ranges only).
    Joining the two would be a change to the plan and was not done. Every method sees the same loss.
17. Fresh-onset score: the 5-events-a-year rule is applied again to the fresh-onset examples, so a year can drop out
    of that score. It is descriptive and feeds no verdict.
18. From the command line, the anchor runs before a Long Island run as well as an SF Bay run (the plan says the
    anchor "must pass before any new score is computed" and names no place). The anchor needs the private SF Bay
    file, so a reader without that file cannot run this entry point as it stands.

### Added 2026-11-17 after every run (T1 to T4) was done and logged
19. `run_study.py --place li --no-anchor` skips the anchor and writes "ANCHOR NOT RUN" as the first line of
    `summary.txt`. It is refused for SF Bay. It exists only so a reader without the private SF Bay file can rerun
    Long Island. No score in the report comes from such a run: every reported run had the anchor pass first.
    Checked with only the team's code files on disk and no Bay data: all 19 output files of the T1 to T3 run and
    all 20 of the T4 run match the reported runs byte for byte, apart from that first line. The run still imports
    the team's `model3/code` (label rule and the earlier model's recipe), and the team's repo is private, so an
    outside reader cannot complete it until that code is available.
    Update 2026-11-17 (later): the last sentence of reading 19 is no longer true. The public copy now has a folder
    `team_code/` with extracts of four of the team's files: only the functions and settings the Long Island run
    uses, copied line for line apart from a few marked cuts to the notes inside the code, with the team's
    permission [team_code/README.md].
    The check above was made with
    the team's whole files. Repeated from a copy that held only the extracts and no Bay data, all 19 output
    files of the T1 to T3 run and all 20 of the T4 run again matched the reported runs byte for byte, apart from
    that first line [WORKLOG.md]. The T4 rerun used the satellite and weather table as already built; building
    it again from the raw downloads was not repeated [WORKLOG.md]. The San Francisco Bay half and the anchor still cannot be rerun by an outside
    reader: they need the team's full files and the restricted data.
    Update 2026-11-18: the limit about the T4 table is closed. The satellite and weather table was rebuilt from the
    raw downloads alone, and it is byte-identical to the one the runs used [WORKLOG.md].
