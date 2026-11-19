"""
The anchor of PREREG section 5, through THIS project's code paths: `data_sf.load_sf_frame` with start 2021-01-01,
`examples.build_examples` with one cut-off 2024-08-16 and embargo 7 (test = all examples after the cut-off),
`features.year_inputs`, and `models` for B1 and B2. It must give the expected test and training counts and events, the nine high lines equal to the team's
CANONICAL_THRESHOLDS to 2 decimals, and the two average precision scores (B1 and B2) to 4 decimals
[Public copy: the expected values are left out; they come from the restricted Bay file]. Only figures are printed, never station values
beyond the nine canonical lines in the team's settings.

    OMP_NUM_THREADS=1 .venv/bin/python src/anchor.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sklearn.metrics import average_precision_score  # noqa: E402

import config  # noqa: E402

_PASSED = {"value": False}


def passed_in_this_process() -> bool:
    return _PASSED["value"]


def run_anchor(verbose: bool = True) -> bool:
    import data_sf
    import examples
    import features
    import models

    _PASSED["value"] = False
    a = config.ANCHOR
    od = config.team().onset_dataset
    frame = data_sf.load_sf_frame(start=a["start"])
    date_inputs = data_sf.load_sf_date_inputs()
    ye = examples.build_examples(frame, a["cutoff"], embargo=a["embargo"], test_year=None)
    inputs = features.year_inputs(frame, ye.lines, config.SF, date_inputs)
    train = features.attach(ye.train, inputs)
    test = features.attach(ye.test, inputs)

    checks = []

    def check(name, found, expected, ok):
        checks.append(ok)
        if verbose:
            print(f"ANCHOR {name}: found {found}, expected {expected}: {'PASS' if ok else 'FAIL'}")

    check("stations taking part", len(ye.taking_part), 9, ye.taking_part == sorted(config.SF.stations))
    check("test examples", len(test), a["test_examples"], len(test) == a["test_examples"])
    check("test events", int(test["onset"].sum()), a["test_events"], int(test["onset"].sum()) == a["test_events"])
    check("training examples", len(train), a["train_examples"], len(train) == a["train_examples"])
    check("training events", int(train["onset"].sum()), a["train_events"],
          int(train["onset"].sum()) == a["train_events"])
    canonical = od.CANONICAL_THRESHOLDS
    for station in sorted(canonical):
        found = round(ye.lines.get(station, float("nan")), 2)
        check(f"high line {station}", f"{found:.2f}", f"{canonical[station]:.2f}", found == round(canonical[station], 2))
    scores = models.score_year(train, test, config.SF, outside_available=False, methods=("B1", "B2"))
    y = test["onset"].to_numpy(dtype=bool)
    for method, key in (("B1", "B1_average_precision"), ("B2", "B2_average_precision")):
        ap = float(average_precision_score(y, scores.test[method]))
        check(f"{method} average precision", f"{ap:.4f}", f"{a[key]:.4f}", round(ap, 4) == a[key])
    if verbose and scores.left_out.get("B2"):
        print(f"ANCHOR note: B2 left out all-missing inputs {scores.left_out['B2']}")
    passed = all(checks)
    if verbose:
        print(f"ANCHOR RESULT: {'PASS' if passed else 'FAIL'} ({sum(checks)} of {len(checks)} checks)")
    _PASSED["value"] = passed
    return passed


if __name__ == "__main__":
    config.check_environment()
    sys.exit(0 if run_anchor() else 1)
