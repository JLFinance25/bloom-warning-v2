# How this public copy differs from the private working repo

Built by script from private commit `c81dc24`. The private repo's history is not published, because
it holds private notes and names.

## Reworded for privacy
Passages that named a person, a private folder or a private notes file were reworded to a role
(for example "the data owner"). Apart from the redactions listed in the next section, no number,
method or result was changed. The table counts the passages the build replaced in each copied file:
rewordings, redactions, and the header added to `PREREG.md`. One replaced passage can hold several
redaction marks. The cut in `research/06-power-check.txt` is described in the next section.

| File | Passages replaced |
|---|---|
| `DEVIATIONS.md` | 1 |
| `PREREG-draft.md` | 5 |
| `PREREG.md` | 13 |
| `WORKLOG.md` | 10 |
| `research/01-prior-work.md` | 2 |
| `research/03-second-estuary.md` | 2 |
| `research/04-short-list.md` | 1 |
| `research/07-code-review-opus.md` | 5 |
| `research/08-tester-gate-opus.md` | 28 |
| `src/anchor.py` | 2 |
| `src/config.py` | 7 |
| `src/outside_sentinel2.py` | 1 |
| `src/power_check.py` | 1 |

## Long Island only
The plan covered two places: Long Island and San Francisco Bay. The Bay half was run on a restricted
sensor file. This copy holds no result, number or station-level fact from that file, and none from
this study's Bay run. It still says that the plan covered the Bay, and it keeps the Bay methods and
the Bay code, with no value from that file in them.
Where such a value stood in a copied file, it is replaced by the mark `[redacted: from the restricted Bay file]`.

| File | Redaction marks |
|---|---|
| `DEVIATIONS.md` | 1 |
| `PREREG-draft.md` | 8 |
| `PREREG.md` | 11 |
| `WORKLOG.md` | 6 |
| `research/01-prior-work.md` | 2 |
| `research/03-second-estuary.md` | 2 |
| `research/07-code-review-opus.md` | 4 |
| `research/08-tester-gate-opus.md` | 45 |

- The Bay station codes are replaced by placeholders in one line of `src/config.py` and in one comment
  in `src/outside_sentinel2.py`.
- The anchor's expected Bay counts and scores are left out of `src/config.py` and `src/anchor.py`.
- The two "SF Bay-like" scenarios are left out of `src/power_check.py` and
  `research/06-power-check.txt`.
- So these parts of the code cannot be run from this copy: the Bay run, the anchor check and the
  Bay-like power scenarios.
- The build script scans every file for Bay station codes, restricted numbers and numbers taken from
  this study's Bay output files. It reads them at run time, so the script does not hold them.

## The locked plan
`PREREG.md` was locked before any Long Island value was downloaded and before any new input or
method was fitted or scored on San Francisco Bay data (its header and section 2 say what was already
known). This copy differs from the locked file in
12 passages: 11 are redacted values from the restricted Bay file (each redaction is
marked `[redacted: from the restricted Bay file]` in the file), and one is a private folder path that is reworded.
A two-line header was added at the top. So this copy's hash differs from the locked file's.
- SHA-256 of the locked file (private): `7ca4b0855beabc98eb54111983d84417f43db9e05ffabcc36887a2b11a9dec42`
- SHA-256 of this copy: `a93c73ba3267f3fae7e1a879129ad807f7d1168d1ce18e5d98ad654ff992db7f`

## Left out
- the private repo's writeup/REPORT.md and writeup/README.md (they cover two places; the San Francisco Bay half is not published). The public README.md and writeup/REPORT.md are the Long Island only versions.
- writeup/LI-only-trace.md (a working check file)
- research notes 00, 02 and 05 (they describe the restricted Bay file station by station). Where `PREREG.md`, `PREREG-draft.md` or `WORKLOG.md` name them, they point to notes kept in the private repo.
- writeup/README-draft.md and writeup/REPORT-draft.md (drafts before the final writing pass)
- research/09-privacy-scan-2026-11-17.md (a scan of the private repo)
- tools/ (this build script)
- every San Francisco Bay output file (restricted source data)
- all raw data (see data/raw/SOURCES.md for how to download the public part)

## Added
- `results/`: copies of the Long Island output files (39 files from li_run1, li_t4_run1).
  The report's source tags such as `li_run1/verdicts.csv` point at these.
- `team_code/`: extracts of the team's earlier code, with credit. See `team_code/README.md`.
- `LICENSE` and `LICENSE-TEXT.md`: the two license files named in the README.
