# team_code: parts of the team's earlier code

This study reuses the label rule and the earlier model's recipe from an earlier team project. That way the comparison is with the team's real code, not a rewrite of it. The code was written by the Bay Protectors team in the BeSMART 2026 summer program. Jayden Ling, who directs this project, was one of the team's four members. The code is included here with the team's permission. No license in this repository covers it.

These files are extracts, not the team's whole files. The team's repository is private. The source is its commit `c7a2c32`.

## What is kept
| File | Kept (functions and settings) |
|---|---|
| `model3/__init__.py` | nothing (header only) |
| `shared/__init__.py` | nothing (header only) |
| `model3/code/__init__.py` | nothing (header only) |
| `shared/config.py` | `PROJECT_ROOT`, `MODEL3_HAB_DIR`, `MODEL3_HAB_CODE_DIR` |
| `model3/data/raw/model3_hab/code/labels.py` | `TRAIN_CUTOFF`, `THRESHOLD_PERCENTILE`, `ONSET_HORIZON_DAYS`, `EMBARGO_DAYS`, `TARGET`, `train_thresholds`, `build_onset_examples` |
| `model3/code/onset_dataset.py` | `_import_canonical_labels_module`, `_labels`, `SAME_DAY_WQ_COLUMNS`, `BASE_FEATURE_COLUMNS`, `station_indicator_columns`, `encode_station_indicators`, `fit_fold_medians`, `apply_fold_imputation`, `_finalize_run` |
| `model3/code/onset_model.py` | `RANDOM_SEED`, `station_rate_scores`, `month_rate_scores`, `fit_logistic_headline`, `positive_class_scores` |

Kept code is copied as whole lines, apart from the changes listed below. Each time this copy is built, a build script checks every kept function and setting: its code, as Python reads it, must be the same as in the team's file, with docstrings (the notes written inside the code) and comments set aside. Any difference stops the build. The build script is not part of this public copy.

## What is left out, and why
Everything the Long Island run does not use. The full files load and describe the San Francisco Bay sensor file, which is restricted, and their notes quote numbers from it.

## What was changed
- 2 docstrings shortened (whole sentences cut, kept sentences unchanged): `train_thresholds` in `labels.py`, `build_onset_examples` in `labels.py`
- 1 comment sentence cut in `_finalize_run` in `onset_dataset.py`
- 2 trailing comments dropped in `labels.py`
- 1 import line in `onset_dataset.py` narrowed to the one name the file uses
- a header added to every file; `model3/code/__init__.py` reduced to its header

Every change inside the kept code is marked "[Public copy: ...]" in the file.

## Source files (SHA-256 at team commit c7a2c32)
A SHA-256 is a fingerprint of a file: any change to the file gives a different one.

| File | SHA-256 |
|---|---|
| `model3/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `shared/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `model3/code/__init__.py` | `b02eadceb4097755752868a8c57dff58b51240da8f36f75cc7b3257e82f04441` |
| `shared/config.py` | `23828c939f37653bc0c1bf1bb8f0dd6f021ec116b93d61a429397b2d70745bf1` |
| `model3/data/raw/model3_hab/code/labels.py` | `07bc8cee452addd4281a00bb4aaef5a02f594ace8e5d64ae43abec38e5ea8c71` |
| `model3/code/onset_dataset.py` | `f5a29dad1cf87434f370e927a0983389b2c0ef19ca8f22e422fcce06b8dd388f` |
| `model3/code/onset_model.py` | `3a45ac8b406902a97a615b019c6fc106fa452b6f58fb22966973722aae80d718` |

## What this copy can run
The Long Island run with `--no-anchor`. It cannot run the San Francisco Bay half or the anchor check. Those need the team's full files and the restricted data.
