"""
The bars, tries and reading rules of PREREG section 6, fitted on one year's training examples and scored on
that year's test examples (and, for the decision check, on the training examples themselves).

Logistic methods (B2 / B2-LI, T1, T2) reuse the team's fold-local machinery unchanged:
`onset_dataset._finalize_run` (station one-hots from the training station list, a missing-marker column for each
input with any missing training value, missing values filled with training medians) and
`onset_model.fit_logistic_headline` (StandardScaler, then LogisticRegression(class_weight="balanced",
random_state=42, max_iter=5000)). An input missing on every training example is left out of that year's logistic
models and logged; the tree models keep it in principle, but see `fit_tree` (scikit-learn 1.9.1 cannot bin an
all-missing column, so it is left out of the tree fit and logged too; it could not change a tree's scores).
"""

from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

import config


@dataclass
class MethodScores:
    test: dict[str, np.ndarray] = field(default_factory=dict)
    train: dict[str, np.ndarray] = field(default_factory=dict)
    left_out: dict[str, list[str]] = field(default_factory=dict)       # logistic inputs left out (all missing)
    columns: dict[str, list[str]] = field(default_factory=dict)        # final model columns
    skipped: dict[str, str] = field(default_factory=dict)


def logistic_columns(spec: config.PlaceSpec, method: str) -> list[str]:
    base = list(spec.base_columns)
    if method == "B2":
        return base
    if method == "T1":
        return base + list(config.STATION_STATE_COLUMNS)
    if method == "T2":
        return base + list(config.STATION_STATE_COLUMNS) + list(config.NEIGHBOUR_COLUMNS)
    raise ValueError(method)


def tree_columns(spec: config.PlaceSpec, method: str) -> list[str]:
    base = list(spec.base_columns)
    if method == "T3_twin":
        return base
    t3 = base + list(config.STATION_STATE_COLUMNS) + list(config.NEIGHBOUR_COLUMNS)
    if method == "T3":
        return t3
    if method == "T4":
        return t3 + list(config.OUTSIDE_COLUMNS)
    raise ValueError(method)


def _require_columns(frame: pd.DataFrame, columns: list[str], what: str) -> None:
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise ValueError(f"{what}: input columns {missing} are absent.")


def _require_both_classes(train: pd.DataFrame, what: str) -> None:
    n_events = int(train["onset"].sum())
    if n_events == 0 or n_events == len(train):
        raise ValueError(f"{what}: the training examples hold {n_events} events in {len(train)}; cannot fit.")


def fit_logistic(train: pd.DataFrame, test: pd.DataFrame, columns: list[str], method: str,
                 moon_products: bool = False) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    """(test scores, train scores, columns left out, final columns) for one logistic method."""
    team = config.team()
    _require_columns(train, columns, method)
    _require_both_classes(train, method)
    left_out = [c for c in columns if train[c].isna().all()]
    kept = [c for c in columns if c not in left_out]
    with contextlib.redirect_stdout(io.StringIO()):          # the team's narration; the audit records the same facts
        finished, final_columns, _ = team.onset_dataset._finalize_run(method, train, {"test": test}, kept)
    final_columns = list(final_columns)
    if moon_products:
        vocabulary = sorted(train["station"].unique())
        for name in team.onset_dataset.station_indicator_columns(vocabulary):
            for moon in ("moon_sin", "moon_cos"):
                if moon not in kept:
                    raise ValueError(f"{method}: {moon} is needed for the station-times-moon products.")
                product = f"{name}_x_{moon}"
                for frame in finished.values():
                    frame[product] = frame[name] * frame[moon]
                final_columns.append(product)
    model = team.onset_model.fit_logistic_headline(finished["train"], final_columns)
    params = model.named_steps["logit"].get_params()
    for key, value in config.LOGISTIC_SETTINGS.items():
        if params[key] != value:
            raise ValueError(f"The team's logistic setting {key}={params[key]} differs from PREREG ({value}).")
    test_scores = team.onset_model.positive_class_scores(model, finished["test"], final_columns)
    train_scores = team.onset_model.positive_class_scores(model, finished["train"], final_columns)
    return test_scores, train_scores, left_out, final_columns


def fit_tree(train: pd.DataFrame, test: pd.DataFrame, columns: list[str], method: str
             ) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    """HistGradientBoosting on `columns` plus the station as an integer code fitted on training examples.

    PREREG says trees keep an input that is missing on every training example. scikit-learn 1.9.1 cannot bin
    such a column (it raises on zero distinct values), and a column with no split point can never change a
    tree's prediction (a constant column gives byte-identical scores to leaving it out; see the tests). So such a
    column is left out of that year's tree fit and LOGGED, never silently: (test, train, final columns, left out).
    """
    _require_columns(train, columns, method)
    _require_both_classes(train, method)
    unbinnable = [c for c in columns if train[c].isna().all()]
    columns = [c for c in columns if c not in unbinnable]
    vocabulary = {s: i for i, s in enumerate(sorted(train["station"].unique()))}

    def matrix(frame: pd.DataFrame) -> np.ndarray:
        code = frame["station"].map(vocabulary).astype(float).to_numpy()   # unseen station -> missing
        return np.column_stack([frame[columns].to_numpy(dtype=float), code])

    model = HistGradientBoostingClassifier(categorical_features=[len(columns)], **config.TREE_SETTINGS)
    model.fit(matrix(train), train["onset"].to_numpy(dtype=int))
    return (model.predict_proba(matrix(test))[:, 1], model.predict_proba(matrix(train))[:, 1],
            [*columns, "station_code"], unbinnable)


def reading_rules(train: pd.DataFrame, frame: pd.DataFrame) -> dict[str, np.ndarray]:
    om = config.team().onset_model
    return {
        "base_rate": np.full(len(frame), float(train["onset"].mean())),
        "month_only": om.month_rate_scores(train, frame),
        "station_only": om.station_rate_scores(train, frame),
    }


def score_year(train: pd.DataFrame, test: pd.DataFrame, spec: config.PlaceSpec,
               outside_available: bool, methods=config.MAIN_METHODS) -> MethodScores:
    out = MethodScores()
    if "B1" in methods:
        out.test["B1"] = test["ratio"].to_numpy(dtype=float)
        out.train["B1"] = train["ratio"].to_numpy(dtype=float)
        out.columns["B1"] = ["ratio"]
    for method in ("B2", "T1", "T2"):
        if method in methods:
            te, tr, left_out, final = fit_logistic(train, test, logistic_columns(spec, method), method,
                                                   moon_products=method in ("T1", "T2"))
            out.test[method], out.train[method], out.left_out[method], out.columns[method] = te, tr, left_out, final
    for method in ("T3", "T3_twin", "T4"):
        if method not in methods:
            continue
        if method == "T4" and not outside_available:
            out.skipped["T4"] = "no outside-inputs table supplied"
            continue
        te, tr, final, unbinnable = fit_tree(train, test, tree_columns(spec, method), method)
        out.test[method], out.train[method], out.columns[method] = te, tr, final
        out.left_out[method] = unbinnable
    for name, values in reading_rules(train, test).items():
        out.test[name] = values
    for name, values in reading_rules(train, train).items():
        out.train[name] = values
    for name, values in out.test.items():
        if len(values) != len(test) or not np.all(np.isfinite(values)):
            raise ValueError(f"{name} did not score every test example with a finite score.")
    return out
