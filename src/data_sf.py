"""
San Francisco Bay daily frame (PREREG section 3). Private data: this module returns frames in memory only.

`load_sf_frame` is a thin version of the team's `onset_dataset.load_hygienic_msp`, which hard-codes the 2021
start. It calls the same steps: `labels.load_msp(stations, start, reindex=True)`, the hazard columns dropped,
`turbidity_mean` clipped below at 0. (`slope7` is built in `features.py`, by the team's formula, for both places.)
`load_sf_date_inputs` joins the team's own weather and tide loaders, unchanged.
"""

from __future__ import annotations

import pandas as pd

import config


def load_sf_frame(start: str = config.SF.extra["start"], stations=config.SF.stations,
                  log: dict | None = None) -> pd.DataFrame:
    team = config.team()
    labels = team.labels
    frame = labels.load_msp(stations=frozenset(stations), start=start, reindex=True)
    found = set(frame["station"].unique())
    missing_stations = sorted(set(stations) - found)
    if missing_stations:
        raise ValueError(f"SF stations {missing_stations} have no rows from {start}.")

    hazards = list(labels.HAZARD_COLUMNS)
    missing_hazards = [c for c in hazards if c not in frame.columns]
    if missing_hazards:
        raise ValueError(f"Hazard columns {missing_hazards} are not in the SF file; the hygiene rule must be re-read.")
    frame = frame.drop(columns=hazards)

    missing_columns = [c for c in config.MEASURED_COLUMNS if c not in frame.columns]
    if missing_columns:
        raise ValueError(f"The SF file lacks columns the study needs: {missing_columns}")

    negative = int((frame["turbidity_mean"] < 0).sum())
    frame["turbidity_mean"] = frame["turbidity_mean"].clip(lower=0)
    if log is not None:
        log["sf_turbidity_clipped_to_zero"] = negative
    return frame.sort_values(["station", "date"]).reset_index(drop=True)


def load_sf_date_inputs() -> pd.DataFrame:
    """Date-level B2 inputs from the team's weather and tide loaders (one row per date)."""
    od = config.team().onset_dataset
    weather = od.load_weather_features()
    tide = od.load_tide_features()
    out = weather.merge(tide, on="date", how="outer").sort_values("date").reset_index(drop=True)
    if out["date"].duplicated().any():
        raise ValueError("The SF date-level inputs have duplicate dates.")
    missing = [c for c in config.SF_DATE_LEVEL_COLUMNS if c not in out.columns]
    if missing:
        raise ValueError(f"The team's weather/tide loaders no longer give {missing}.")
    return out[["date", *config.SF_DATE_LEVEL_COLUMNS]]
