# EXTRACT for the public copy. This is not the team's whole file.
# Source: the team's `model3/code/onset_dataset.py` at commit c7a2c32 (the team's repository is private).
# SHA-256 of the source file: f5a29dad1cf87434f370e927a0983389b2c0ef19ca8f22e422fcce06b8dd388f
# Kept: only the parts the Long Island run uses (in some files, nothing), copied line for line. Left out:
# everything else, because the team's full files describe the restricted San Francisco Bay sensor data. Text
# marked "[Public copy: ...]" was changed or added by this project. See team_code/README.md.

from __future__ import annotations
import importlib.util
import pandas as pd
from shared.config import MODEL3_HAB_CODE_DIR  # [Public copy: import narrowed to the one name this file uses]


def _import_canonical_labels_module():
    """Load data/external/model3_hab/code/labels.py by its exact file path.

    The canonical label builder is not part of any package, and it used to be imported by
    inserting its directory at the FRONT of the process-global sys.path, then doing a bare
    `import labels`. That made this module's own import order load-bearing: a caller (or a test
    file) that did `import labels` before this module ran would either get a different `labels`
    if one existed elsewhere on the path, or an ImportError, and a caller after it worked only
    because of this module's side effect. Loading by explicit spec avoids sys.path entirely — no
    global state changes, and the identity of what "the canonical labels module" means can never
    depend on what already ran.
    """
    labels_path = MODEL3_HAB_CODE_DIR / "labels.py"
    spec = importlib.util.spec_from_file_location("model3_hab_labels", labels_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_labels = _import_canonical_labels_module()


SAME_DAY_WQ_COLUMNS = ("do_mgl_mean", "temp_c_mean", "turbidity_mean", "salinity_psu_mean")


BASE_FEATURE_COLUMNS = [
    "ratio",                # today's chla_mean / station threshold — SAME-DAY, disclosed
    "slope7",               # (chla_mean[t] - chla_mean[t-7]) / 7 on the reindexed series
    *SAME_DAY_WQ_COLUMNS,   # today's daily means — SAME-DAY, disclosed
    "shortwave_radiation_sum_MJm2",
    "wind_speed_10m_max_kmh",
    "wind_gusts_10m_max_kmh",
    "wind_dir_sin",
    "wind_dir_cos",
    "tidal_range_m",
    "tide_range_7d",
    "doy_sin",
    "doy_cos",
]


def station_indicator_columns(vocabulary: list[str]) -> list[str]:
    """The one-hot column names for a training-fitted station vocabulary."""

    return [f"station_{station}" for station in vocabulary]


def encode_station_indicators(frame: pd.DataFrame, vocabulary: list[str]) -> pd.DataFrame:
    """
    One-hot encode `station` against a vocabulary fitted on TRAINING rows only.

    A station absent from the vocabulary encodes as all-zero rather than gaining a column,
    because which stations exist in the held-out period is a fact the training fold is not
    allowed to know (2B's fold-local station encoding, in its simplest correct form).
    """
    out = frame.copy()
    for station in vocabulary:
        out[f"station_{station}"] = (out["station"] == station).astype(float)
    return out


def fit_fold_medians(train: pd.DataFrame, columns: list[str]) -> dict[str, float]:
    """Fit per-column imputation medians on the TRAINING rows only."""

    medians = {}
    for column in columns:
        median = train[column].median()
        if pd.isna(median):
            raise ValueError(
                f"The training median of {column} is undefined because every training value is "
                f"missing, so this column cannot be imputed and should not be a feature."
            )
        medians[column] = float(median)
    return medians


def apply_fold_imputation(frame: pd.DataFrame, medians: dict[str, float],
                          indicator_features: list[str]) -> pd.DataFrame:
    """
    Fill missing feature values with the training medians and add missingness indicators.

    The indicator columns record WHERE a value was imputed (1.0) versus observed (0.0), so the
    model can weight imputed rows differently instead of mistaking the median for a reading.
    The indicator column set is decided once per run and shared by every frame in it, so train
    and test always carry identical columns.
    """
    out = frame.copy()
    for column in indicator_features:
        out[f"{column}_missing"] = out[column].isna().astype(float)
    for column, median in medians.items():
        out[column] = out[column].fillna(median)
    return out


def _finalize_run(run_name: str, train: pd.DataFrame, tests: dict[str, pd.DataFrame],
                  feature_columns: list[str]):
    """Apply the fold-local steps for one run: one-hots, indicator set, imputation."""

    vocabulary = sorted(train["station"].unique())
    frames = {"train": train, **tests}

    # The indicator-column SET is derived from the TRAINING frame alone, so the narration sentence
    # below ("fitted on its training rows only") is literally true of every fold-local artifact.
    # [Public copy: one sentence about the restricted San Francisco Bay data is left out here.]
    # A feature that is complete on train but missing on a test
    # row is still imputed with the train median below — it just carries no indicator column, which
    # is exactly what "the model never saw test missingness" requires.
    indicator_features = [
        column for column in feature_columns if train[column].isna().any()
    ]
    medians = fit_fold_medians(train, feature_columns)

    finished = {}
    report_rows = []
    for frame_name, frame in frames.items():
        for column in indicator_features:
            report_rows.append({
                "run": run_name,
                "frame": frame_name,
                "feature": column,
                "values_imputed": int(frame[column].isna().sum()),
                "train_median_used": medians[column],
            })
        frame = encode_station_indicators(frame, vocabulary)
        frame = apply_fold_imputation(frame, medians, indicator_features)
        finished[frame_name] = frame.reset_index(drop=True)

    final_columns = (
        feature_columns
        + station_indicator_columns(vocabulary)
        + [f"{column}_missing" for column in indicator_features]
    )
    print(
        f"[MODEL 3] Run {run_name} is finalized fold-locally: the station vocabulary "
        f"({len(vocabulary)} stations), the imputation medians, and the "
        f"{len(indicator_features)} missingness-indicator columns "
        f"({', '.join(indicator_features) if indicator_features else 'none'}) were all fitted "
        f"on its {len(train):,} training rows only."
    )
    return finished, final_columns, report_rows
