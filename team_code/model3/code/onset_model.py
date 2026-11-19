# EXTRACT for the public copy. This is not the team's whole file.
# Source: the team's `model3/code/onset_model.py` at commit c7a2c32 (the team's repository is private).
# SHA-256 of the source file: 3a45ac8b406902a97a615b019c6fc106fa452b6f58fb22966973722aae80d718
# Kept: only the parts the Long Island run uses (in some files, nothing), copied line for line. Left out:
# everything else, because the team's full files describe the restricted San Francisco Bay sensor data. Text
# marked "[Public copy: ...]" was changed or added by this project. See team_code/README.md.

from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


RANDOM_SEED = 42


def station_rate_scores(train: pd.DataFrame, frame: pd.DataFrame) -> np.ndarray:
    """Each row scored with its station's training onset rate (train global rate if unseen)."""

    rates = train.groupby("station")["onset"].mean()
    fallback = float(train["onset"].mean())
    return frame["station"].map(rates).fillna(fallback).to_numpy(dtype=float)


def month_rate_scores(train: pd.DataFrame, frame: pd.DataFrame) -> np.ndarray:
    """Each row scored with its calendar month's training onset rate (train global if unseen)."""

    monthly = train.groupby(train["date"].dt.month)["onset"].mean()
    fallback = float(train["onset"].mean())
    return frame["date"].dt.month.map(monthly).fillna(fallback).to_numpy(dtype=float)


def fit_logistic_headline(train: pd.DataFrame, feature_columns: list[str]) -> Pipeline:
    """The headline: standardized logistic regression, class-balanced, seeded, deterministic."""

    model = Pipeline([
        ("scale", StandardScaler()),
        ("logit", LogisticRegression(
            class_weight="balanced", random_state=RANDOM_SEED, max_iter=5000,
        )),
    ])
    model.fit(train[feature_columns], train["onset"].to_numpy(dtype=int))
    return model


def positive_class_scores(model: Pipeline, frame: pd.DataFrame,
                          feature_columns: list[str]) -> np.ndarray:
    """Probability of the positive class, used as the ranking score everywhere."""

    return model.predict_proba(frame[feature_columns])[:, 1]
