"""
Every path, station list, year list and constant the study uses, in one place (PREREG sections 3 to 7).

Nothing here reads data. `team()` loads the team's Model 3 code (read-only) by path; it never writes there:
bytecode writing is switched off for this process before the import, so no `__pycache__` lands in the team
worktree.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

# --------------------------------------------------------------------------------------------------------------
# Paths. The team's code is expected in a folder (or link) named `team_code` inside this project; BLOOM_TEAM_ROOT
# overrides it. In the private working repo `team_code` is a git-ignored link to the team's files; the public copy
# holds extracts of them there (see team_code/README.md).
# --------------------------------------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
LI_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "usgs_long_island"
TEAM_ROOT = Path(os.environ.get(
    "BLOOM_TEAM_ROOT",
    PROJECT_ROOT / "team_code",
)).resolve()

# --------------------------------------------------------------------------------------------------------------
# Environment (PREREG section 6). The run fails if any of these differ.
# --------------------------------------------------------------------------------------------------------------
REQUIRED_ENVIRONMENT = {
    "python": "3.14.4",
    "pandas": "3.0.6",
    "numpy": "2.5.4",
    "scikit-learn": "1.9.1",
    "scipy": "1.18.1",
    "rasterio": "1.5.2",
    "OMP_NUM_THREADS": "1",
}

# --------------------------------------------------------------------------------------------------------------
# The task (section 4) and the yearly design (section 5).
# --------------------------------------------------------------------------------------------------------------
HORIZON_DAYS = (1, 2, 3)
LINE_PERCENTILE = 0.90
MIN_CHLA_DAYS_TO_TAKE_PART = 300
EMBARGO_DAYS = 10                    # training example dates on or before 21 December of Y-1
TARGET = "chla_mean"

ANCHOR = {
    "start": "2021-01-01",
    "cutoff": "2024-08-16",
    "embargo": 7,
    "test_examples": None,  # [Public copy: left out; from the restricted Bay file]
    "test_events": None,  # [Public copy: left out; from the restricted Bay file]
    "train_examples": None,  # [Public copy: left out; from the restricted Bay file]
    "train_events": None,  # [Public copy: left out; from the restricted Bay file]
    "B1_average_precision": None,  # [Public copy: left out; from the restricted Bay file]
    "B2_average_precision": None,  # [Public copy: left out; from the restricted Bay file]
}

# --------------------------------------------------------------------------------------------------------------
# Inputs (section 6).
# --------------------------------------------------------------------------------------------------------------
SF_BASE_COLUMNS = (                  # the team's BASE_FEATURE_COLUMNS, checked against the team's list at run time
    "ratio", "slope7", "do_mgl_mean", "temp_c_mean", "turbidity_mean", "salinity_psu_mean",
    "shortwave_radiation_sum_MJm2", "wind_speed_10m_max_kmh", "wind_gusts_10m_max_kmh",
    "wind_dir_sin", "wind_dir_cos", "tidal_range_m", "tide_range_7d", "doy_sin", "doy_cos",
)
SF_DATE_LEVEL_COLUMNS = (
    "shortwave_radiation_sum_MJm2", "wind_speed_10m_max_kmh", "wind_gusts_10m_max_kmh",
    "wind_dir_sin", "wind_dir_cos", "tidal_range_m", "tide_range_7d",
)
LI_BASE_COLUMNS = (                  # B2-LI
    "ratio", "slope7", "do_mgl_mean", "temp_c_mean", "turbidity_mean", "salinity_psu_mean", "doy_sin", "doy_cos",
)
STATION_STATE_COLUMNS = (            # T1's new inputs (station-times-moon products are added in models.py)
    "ratio_max", "d1_ratio", "d3_ratio", "max7_ratio", "days_since_high", "do_swing",
    "d3_temp", "d3_turb", "d3_sal", "moon_sin", "moon_cos",
)
NEIGHBOUR_COLUMNS = ("nb_mean_ratio", "nb_max_ratio", "nb_n_high", "nb_n_reporting")
OUTSIDE_COLUMNS = (
    "s2_ndci", "s2_red", "s2_green_blue", "s2_n_water", "s2_age",
    "wx_sun", "wx_wind", "wx_sun_3d", "wx_wind_3d",
)
MEASURED_COLUMNS = (                 # the shared measures both places' frames carry
    "chla_mean", "chla_max", "chla_min", "do_mgl_mean", "do_mgl_max", "do_mgl_min",
    "temp_c_mean", "turbidity_mean", "salinity_psu_mean",
)

SLOPE_LAG_DAYS = 7
MAX7_WINDOW_DAYS = 7
DAYS_SINCE_HIGH_CAP = 60
FRESH_ONSET_WINDOW_DAYS = 14
DAYS_IN_YEAR = 365.25
MOON_EPOCH_UTC = pd.Timestamp("2000-01-06 18:14:00")
MOON_HALF_CYCLE_DAYS = 14.7652944

# --------------------------------------------------------------------------------------------------------------
# Methods (section 6).
# --------------------------------------------------------------------------------------------------------------
LOGISTIC_SETTINGS = {"class_weight": "balanced", "random_state": 42, "max_iter": 5000}
TREE_SETTINGS = {
    "max_iter": 300, "learning_rate": 0.05, "max_leaf_nodes": 15, "min_samples_leaf": 40,
    "l2_regularization": 1.0, "early_stopping": False, "random_state": 42,
}
TRIES = ("T1", "T2", "T3", "T4")
BLIND_TRIES = ("T1", "T2", "T3")
MAIN_METHODS = ("B1", "B2", "T1", "T2", "T3", "T3_twin", "T4")
READING_METHODS = ("base_rate", "month_only", "station_only")
DECISION_PERCENTILE = 0.90
EPISODE_GAP_DAYS = 7

CSV_FLOAT_FORMAT = "%.12g"


# --------------------------------------------------------------------------------------------------------------
# Places.
# --------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class PlaceSpec:
    name: str
    stations: tuple[str, ...]
    verdict_years: tuple[int, ...]
    outside_years: tuple[int, ...]
    utc_offset_hours: int                     # local standard time = UTC + this
    base_columns: tuple[str, ...]             # B2's base columns at this place
    date_level_columns: tuple[str, ...] = ()  # joined by date (SF only)
    requires_anchor: bool = False
    outputs_under_processed_only: bool = False
    extra: dict = field(default_factory=dict, compare=False)

    @property
    def years(self) -> tuple[int, ...]:
        return tuple(sorted(set(self.verdict_years) | set(self.outside_years)))


SF = PlaceSpec(
    name="sf",
    stations=("BAY1", "BAY2", "BAY3", "BAY4", "BAY5", "BAY6", "BAY7", "BAY8", "BAY9"),  # [Public copy: the nine Bay station codes are left out; placeholders stand in]
    verdict_years=tuple(range(2017, 2025)),
    outside_years=(2025, 2026),
    utc_offset_hours=-8,
    base_columns=SF_BASE_COLUMNS,
    date_level_columns=SF_DATE_LEVEL_COLUMNS,
    requires_anchor=True,
    outputs_under_processed_only=True,
    extra={"start": "2013-07-24", "last_day": "2026-06-14"},
)

LI = PlaceSpec(
    name="li",
    stations=("01311143", "01310740", "01304562", "01304650", "01303152"),
    verdict_years=tuple(range(2015, 2026)),
    outside_years=(2026,),
    utc_offset_hours=-5,
    base_columns=LI_BASE_COLUMNS,
    extra={"download_date": "2026-11-17"},
)

# USGS parameter and statistic codes -> the SF frame's column names (section 3).
LI_PARAMETERS = {"32316": "chla", "00010": "temp_c", "90860": "salinity_psu", "00300": "do_mgl", "63680": "turbidity"}
LI_STATISTICS = {"00003": "mean", "00001": "max", "00002": "min"}
# Series the PREREG/SOURCES already say do not exist. Any other missing series raises.
LI_KNOWN_ABSENT = frozenset({("01304650", "90860")})


# --------------------------------------------------------------------------------------------------------------
# The team's code, read-only.
# --------------------------------------------------------------------------------------------------------------
_TEAM = None


def team() -> SimpleNamespace:
    """The team's labels, onset_dataset and onset_model modules, imported by path, writing nothing there."""
    global _TEAM
    if _TEAM is not None:
        return _TEAM
    if not (TEAM_ROOT / "model3" / "code" / "onset_dataset.py").is_file():
        raise FileNotFoundError(f"The team's Model 3 code is not at {TEAM_ROOT}; set BLOOM_TEAM_ROOT.")
    sys.dont_write_bytecode = True               # never write __pycache__ into the read-only worktree
    if str(TEAM_ROOT) not in sys.path:
        sys.path.append(str(TEAM_ROOT))
    import model3.code.onset_dataset as onset_dataset  # noqa: E402
    import model3.code.onset_model as onset_model      # noqa: E402
    if list(SF_BASE_COLUMNS) != list(onset_dataset.BASE_FEATURE_COLUMNS):
        raise ValueError("config.SF_BASE_COLUMNS no longer matches the team's BASE_FEATURE_COLUMNS.")
    _TEAM = SimpleNamespace(labels=onset_dataset._labels, onset_dataset=onset_dataset, onset_model=onset_model)
    return _TEAM


def check_environment(verbose: bool = True) -> dict:
    """Print the environment and raise if it differs from PREREG section 6."""
    import platform

    import numpy
    import rasterio
    import scipy
    import sklearn

    found = {
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": numpy.__version__,
        "scikit-learn": sklearn.__version__,
        "scipy": scipy.__version__,
        "rasterio": rasterio.__version__,
        "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", "<unset>"),
    }
    if verbose:
        print("Environment: " + ", ".join(f"{k} {v}" for k, v in found.items()))
    wrong = {k: (found[k], v) for k, v in REQUIRED_ENVIRONMENT.items() if found[k] != v}
    if wrong:
        raise RuntimeError("Environment differs from PREREG section 6 (found, required): "
                           + ", ".join(f"{k} {a} != {b}" for k, (a, b) in wrong.items()))
    return found
