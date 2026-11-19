"""
Power check on MADE-UP data, run before the PREREG is locked. No real data is read.

Question: if a try truly were X% better than the bar, how often would each verdict fire under the rules in
`scoring.py`? The made-up world has stations whose hidden bloom pressure drifts day to day (so events come in
runs, as real blooms do), a bar that sees one signal, and a try that sees that signal plus a second one whose
usefulness varies from year to year.

    .venv/bin/python -I src/power_check.py > research/06-power-check.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scoring  # noqa: E402

SEED = 20261117


def ar1(rng, shape, rho):
    out = np.empty(shape)
    out[..., 0] = rng.standard_normal(shape[:-1])
    noise = rng.standard_normal(shape) * np.sqrt(1 - rho ** 2)
    for t in range(1, shape[-1]):
        out[..., t] = rho * out[..., t - 1] + noise[..., t]
    return out


def simulate_place(rng, events_per_year, stations, days, extra_strength, year_sd):
    """One made-up place: a frame with year, onset, and scores for B1, B2 and TRY."""
    parts = []
    for year, target_events in enumerate(events_per_year):
        z = ar1(rng, (stations, days), 0.9).ravel()          # what the bar sees
        w = ar1(rng, (stations, days), 0.7).ravel()          # what only the try sees
        strength = extra_strength * np.exp(year_sd * rng.standard_normal())
        signal = 1.6 * z + strength * w
        # pick the intercept so the expected number of events matches the target
        lo, hi = -15.0, 5.0
        for _ in range(40):
            mid = (lo + hi) / 2
            if (1 / (1 + np.exp(-(mid + signal)))).sum() > target_events:
                hi = mid
            else:
                lo = mid
        p = 1 / (1 + np.exp(-(lo + signal)))
        onset = rng.random(p.size) < p
        parts.append(pd.DataFrame({
            "year": year, "onset": onset,
            "B1": z,
            "B2": z + 0.15 * rng.standard_normal(z.size),              # the old model: the same signal, noisier
            "TRY": 1.6 * z + extra_strength * w + 0.3 * rng.standard_normal(z.size),
        }))
    return pd.concat(parts, ignore_index=True)


def run_scenario(name, events_per_year, stations, days, strengths, year_sd, sims=300, draws=2000):
    print(f"\n## {name}")
    print(f"years {len(events_per_year)}, target events per year {list(events_per_year)}, "
          f"{stations} stations x {days} eligible days, year-to-year spread of the extra signal {year_sd}")
    print("| extra signal | true margin (median) | LARGE | BEATS | NO DIFFERENCE | NOT SHOWN | median interval |")
    print("|---|---|---|---|---|---|---|")
    for strength in strengths:
        rng = np.random.default_rng(SEED + int(strength * 1000))
        counts = {scoring.HELPS_LARGE: 0, scoring.HELPS: 0, scoring.NO_DIFFERENCE: 0, scoring.NOT_SHOWN: 0}
        margins, lows, highs = [], [], []
        for _ in range(sims):
            frame = simulate_place(rng, events_per_year, stations, days, strength, year_sd)
            table = scoring.year_table(frame, ["B1", "B2", "TRY"])
            result = scoring.verdict(table, "TRY", draws=draws)
            counts[result["verdict"]] += 1
            margins.append(result["margin"]); lows.append(result["interval_low"]); highs.append(result["interval_high"])
        share = {k: f"{100 * v / sims:.0f}%" for k, v in counts.items()}
        print(f"| {strength} | {100 * np.median(margins):+.0f}% | {share[scoring.HELPS_LARGE]} | {share[scoring.HELPS]} | "
              f"{share[scoring.NO_DIFFERENCE]} | {share[scoring.NOT_SHOWN]} | "
              f"[{100 * np.median(lows):+.0f}%, {100 * np.median(highs):+.0f}%] |")


def main():
    print("# Power check on made-up data (no real data read)")
    print("Rules under test: scoring.py as written on 2026-11-17. 300 made-up worlds per row, 2,000 resamples each.")
    print("'True margin' is the median measured margin across the made-up worlds, so it is a property of the "
          "made-up world, not of the Bay.")
    strengths = [0.0, 0.3, 0.5, 0.7, 1.0]
    # [Public copy: the two "SF Bay-like" scenarios are left out; their yearly event counts came from the restricted Bay file]
    # Long Island-like: eleven years, few events early (one station), more later. Counts are a guess.
    run_scenario("Long Island-like (event counts are a guess)", [8, 10, 12, 25, 30, 35, 35, 40, 40, 50, 55],
                 3, 300, strengths, year_sd=0.5)


if __name__ == "__main__":
    main()
