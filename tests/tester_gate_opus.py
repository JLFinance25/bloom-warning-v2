"""
Independent tester gate (PREREG section 8): re-derive scores and verdicts from predictions.csv with my own code
(Part A), and rebuild labels and five inputs for 200 random examples per place from the raw daily data (Part B).

    OMP_NUM_THREADS=1 .venv/bin/python tests/tester_gate_opus.py

Part A uses only pandas, numpy and sklearn.metrics.average_precision_score. Part B builds everything from the raw
daily data with its own code; it calls the pipeline only (a) to get the cleaned SF Bay daily frame
(data_sf.load_sf_frame) and (b) to get the pipeline's own input values for comparison (run_study.year_data).
Prints PASS/FAIL per check. Prints no SF Bay measured value (only counts, flags, differences and scores already
in the outputs). Writes no file.
"""

from __future__ import annotations

import math
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
RAW_LI = ROOT / "data" / "raw" / "usgs_long_island"

TOL = 1e-9
SEED = 20261117
N_DRAWS = 10_000
TRIES = ["T1", "T2", "T3"]
METHODS = ["B1", "B2", "T1", "T2", "T3", "T3_twin", "base_rate", "month_only", "station_only"]
PLACES = {
    "sf": dict(out=PROC / "sf_run1", verdict=range(2017, 2025), utc_offset=-8),
    "li": dict(out=PROC / "li_run1", verdict=range(2015, 2026), utc_offset=-5),
}
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    ok = bool(ok)
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    return ok


def close(a, b, tol=TOL) -> bool:
    if a is None or b is None:
        return a is None and b is None
    a, b = float(a), float(b)
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    return abs(a - b) <= tol


def read_predictions(place: str) -> pd.DataFrame:
    p = pd.read_csv(PLACES[place]["out"] / "predictions.csv", dtype={"station": str}, parse_dates=["date"])
    for c in ("onset", "verdict_year", "counted_in_verdict", "fresh_onset", "part_window"):
        p[c] = p[c].astype(str).str.lower().map({"true": True, "false": False})
    return p


# =============================================================================================================
# Part A
# =============================================================================================================
def per_year_table(pred: pd.DataFrame, verdict_years) -> pd.DataFrame:
    rows = []
    for year, g in pred.groupby("year", sort=True):
        y = g["onset"].to_numpy(dtype=int)
        row = {"year": year, "verdict_year": year in verdict_years, "examples": len(g), "events": int(y.sum())}
        row["counted"] = row["verdict_year"] and row["events"] >= 5
        for m in METHODS:
            row[m] = average_precision_score(y, g[m].to_numpy()) if y.sum() > 0 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def weighted(ap: np.ndarray, w: np.ndarray) -> np.ndarray:
    return (w @ ap) / w.sum(axis=-1, keepdims=True) if w.ndim == 2 else (w @ ap) / w.sum()


def part_a(place: str) -> dict:
    print(f"\n=== Part A: {place}")
    spec = PLACES[place]
    out = spec["out"]
    pred = read_predictions(place)
    mine = per_year_table(pred, set(spec["verdict"]))
    theirs = pd.read_csv(out / "year_table.csv")
    for c in ("verdict_year", "counted"):
        theirs[c] = theirs[c].astype(str).str.lower() == "true"
    res = {"place": place, "rows": []}

    # 1. per-year table
    merged = mine.merge(theirs, on="year", suffixes=("_mine", "_pipe"), how="outer", indicator=True)
    check(f"{place} A1 same years in year_table", (merged["_merge"] == "both").all(),
          f"{len(mine)} years")
    for c in ("examples", "events", "verdict_year", "counted"):
        ok = (merged[f"{c}_mine"] == merged[f"{c}_pipe"]).all()
        check(f"{place} A1 per-year {c}", ok)
    worst = 0.0
    for m in METHODS:
        d = (merged[f"{m}_mine"] - merged[f"{m}_pipe"]).abs().max()
        worst = max(worst, d)
    check(f"{place} A1 per-year AP, all methods and years", worst <= TOL, f"max |diff| {worst:.2e}")
    res["year_ap_maxdiff"] = worst
    res["year_table"] = mine

    # 2. counted years and primary scores
    cnt = mine.loc[mine["counted"]].reset_index(drop=True)
    E = cnt["events"].to_numpy(dtype=float)
    AP = cnt[METHODS].to_numpy(dtype=float)
    primary = dict(zip(METHODS, weighted(AP, E)))
    ps = pd.read_csv(out / "primary_scores.csv").set_index("method")
    check(f"{place} A2 counted years / events", int(ps.loc["B1", "counted_years"]) == len(cnt)
          and int(ps.loc["B1", "counted_events"]) == int(E.sum()), f"{len(cnt)} years, {int(E.sum())} events")
    for m in METHODS:
        d = abs(primary[m] - ps.loc[m, "primary_score"])
        res["rows"].append(("primary " + m, ps.loc[m, "primary_score"], primary[m], d, d <= TOL))
        check(f"{place} A2 primary score {m}", d <= TOL, f"pipe {ps.loc[m, 'primary_score']:.6f} mine {primary[m]:.6f}")

    # 3. bar, margins, years rule
    bar = "B1" if primary["B1"] >= primary["B2"] else "B2"
    bar_score = max(primary["B1"], primary["B2"])
    n = len(cnt)
    need = math.ceil(0.75 * n)
    ver = pd.read_csv(out / "verdicts.csv").set_index("method")
    verdict_mine = {}
    # 4. bootstrap
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, n, size=(N_DRAWS, n))
    mult = np.stack([np.bincount(r, minlength=n) for r in idx]).astype(float)
    W = mult * E
    draw_primary = (W @ AP) / W.sum(axis=1, keepdims=True)
    col = {m: i for i, m in enumerate(METHODS)}
    draw_bar = np.maximum(draw_primary[:, col["B1"]], draw_primary[:, col["B2"]])
    too_few = n < 5 or E.sum() < 150
    blind_large = False
    for t in TRIES:
        margin = primary[t] / bar_score - 1
        won = int((cnt[t] > cnt[bar]).sum())
        dm = draw_primary[:, col[t]] / draw_bar - 1
        lo, hi = np.percentile(dm, [0.625, 99.375])
        lo2, hi2 = np.percentile(dm, [1.25, 98.75])
        beats = lo > 0 and won >= need
        large = beats and margin >= 0.25
        nmd = (not beats) and (-0.10 <= lo2 <= 0.10) and (-0.10 <= hi2 <= 0.10)
        v = "BEATS BY A LARGE MARGIN" if large else "BEATS" if beats else "NO MEANINGFUL DIFFERENCE" if nmd \
            else "NOT SHOWN"
        if too_few:
            v = "TOO FEW EVENTS"
        verdict_mine[t] = v
        blind_large = blind_large or (large and not too_few)
        r = ver.loc[t]
        check(f"{place} A3 {t} bar method", r["bar_method"] == bar, f"{bar}")
        d = abs(margin - r["margin"])
        res["rows"].append((f"margin {t}", r["margin"], margin, d, d <= TOL))
        check(f"{place} A3 {t} margin", d <= TOL, f"pipe {r['margin']:+.6f} mine {margin:+.6f}")
        ok = int(r["years_won"]) == won and int(r["years_counted"]) == n and int(r["years_required"]) == need
        res["rows"].append((f"years won {t}", f"{int(r['years_won'])}/{int(r['years_counted'])} need "
                            f"{int(r['years_required'])}", f"{won}/{n} need {need}", 0, ok))
        check(f"{place} A3 {t} years won/counted/required", ok, f"{won}/{n} need {need}")
        dlo, dhi = abs(lo - r["interval_low"]), abs(hi - r["interval_high"])
        # could the difference flip the verdict? the low end must not cross 0 or +10% between the two runs
        flip = (np.sign(lo) != np.sign(r["interval_low"])) or ((lo >= 0.10) != (r["interval_low"] >= 0.10))
        res["rows"].append((f"interval low {t}", r["interval_low"], lo, dlo, not flip))
        res["rows"].append((f"interval high {t}", r["interval_high"], hi, dhi, True))
        res["rows"].append((f"NMD 1.25/98.75% points {t}", "not written", f"[{lo2:+.4f}, {hi2:+.4f}]", "", True))
        check(f"{place} A4 {t} bootstrap interval (verdict-relevant side unchanged)", not flip,
              f"pipe [{r['interval_low']:+.4f}, {r['interval_high']:+.4f}] mine [{lo:+.4f}, {hi:+.4f}] "
              f"|diff| {dlo:.2e}/{dhi:.2e}; NMD points [{lo2:+.4f}, {hi2:+.4f}]")
        check(f"{place} A5 {t} low end reaches +10%", (lo >= 0.10) == bool(str(r["low_end_reaches_10pct"]) == "True"))
        check(f"{place} A5 {t} verdict", r["verdict"] == v, f"pipe {r['verdict']} mine {v}")
        res["rows"].append((f"verdict {t}", r["verdict"], v, "", r["verdict"] == v))
    check(f"{place} A5 TOO FEW EVENTS rule", not too_few if all(ver.loc[t, "verdict"] != "TOO FEW EVENTS"
                                                                for t in TRIES) else too_few,
          f"{n} counted years, {int(E.sum())} events")
    summary = (out / "summary.txt").read_text()
    m = re.search(r"Win bar \(blind tries T1-T3\): (\w+(?: \w+)?)\. Win bar \(any try\): (\w+(?: \w+)?)\.", summary)
    wb = "MET" if blind_large else "NOT MET"
    check(f"{place} A5 win bar (blind tries, any try; T4 not run)", m and m.group(1) == wb and m.group(2) == wb,
          f"mine {wb}/{wb}")
    res["rows"].append(("win bar blind / any", f"{m.group(1)} / {m.group(2)}", f"{wb} / {wb}", "", m.group(1) == wb))
    c3 = primary["T3"] > primary["T3_twin"]
    c2 = primary["T2"] > primary["B2"]
    m = re.search(r"Credit to new inputs allowed: (\w+) \(T3 over T3-twin: (\w+); T2 over B2: (\w+)\)", summary)
    ok = m and m.group(1) == str(c3 or c2) and m.group(2) == str(c3) and m.group(3) == str(c2)
    check(f"{place} A5 credit check", ok, f"mine allowed {c3 or c2} (T3>twin {c3}, T2>B2 {c2})")
    res["rows"].append(("credit allowed (T3>twin; T2>B2)", f"{m.group(1)} ({m.group(2)}; {m.group(3)})",
                        f"{c3 or c2} ({c3}; {c2})", "", bool(ok)))
    m = re.search(r"Counted years: (\d+); events in counted years: (\d+); part-window events \(all test years\): (\d+)",
                  summary)
    pw = int((pred["onset"] & pred["part_window"]).sum())
    check(f"{place} A5 summary counts line", m and int(m.group(1)) == n and int(m.group(2)) == int(E.sum())
          and int(m.group(3)) == pw, f"{n} / {int(E.sum())} / part-window events {pw}")

    # 6. pooled and fresh onset
    vy = pred.loc[pred["verdict_year"]]
    pooled_mine = {mm: average_precision_score(vy["onset"].astype(int), vy[mm]) for mm in METHODS}
    pooled = pd.read_csv(out / "pooled.csv").set_index("method")["pooled_average_precision"]
    d = max(abs(pooled_mine[mm] - pooled[mm]) for mm in METHODS)
    check(f"{place} A6 pooled AP, all methods", d <= TOL, f"max |diff| {d:.2e}")
    res["rows"].append(("pooled AP (max over methods)", "", "", d, d <= TOL))
    fr = pred.loc[pred["fresh_onset"]]
    ft = per_year_table(fr, set(spec["verdict"]))
    fc = ft.loc[ft["counted"]]
    fresh = pd.read_csv(out / "fresh_onset.csv").set_index("method")
    worst = 0.0
    okc = True
    for mm in METHODS:
        fp = float(np.average(fc[mm], weights=fc["events"]))
        worst = max(worst, abs(fp - fresh.loc[mm, "fresh_primary_score"]))
        okc &= int(fresh.loc[mm, "fresh_counted_years"]) == len(fc) and \
            int(fresh.loc[mm, "fresh_counted_events"]) == int(fc["events"].sum())
        beats = fp > float(np.average(fc[bar], weights=fc["events"])) if mm != bar else False
        okc &= str(fresh.loc[mm, "beats_bar_on_fresh"]) == str(beats)
    check(f"{place} A6 fresh-onset primary, counted years/events, beats-bar flags", worst <= TOL and okc,
          f"max |diff| {worst:.2e}; {len(fc)} years, {int(fc['events'].sum())} events")
    res["rows"].append(("fresh-onset primary (max over methods)", "", "", worst, worst <= TOL and okc))

    # 7. sanity on predictions.csv
    check(f"{place} A7 no duplicate (station, date)", not pred.duplicated(["station", "date"]).any())
    check(f"{place} A7 every score finite", np.isfinite(pred[METHODS].to_numpy(dtype=float)).all())
    check(f"{place} A7 test dates fall in their year", (pred["date"].dt.year == pred["year"]).all())
    check(f"{place} A7 verdict_year column", (pred["verdict_year"] == pred["year"].isin(list(spec["verdict"]))).all())
    cy = set(cnt["year"])
    check(f"{place} A7 counted_in_verdict column", (pred["counted_in_verdict"] == pred["year"].isin(cy)).all())
    aud = pd.read_csv(out / "audit_years.csv", dtype={"stations_taking_part": str})
    ok_st, ok_n = True, True
    notes = []
    for _, r in aud.iterrows():
        part = set(str(r["stations_taking_part"]).split(";"))
        g = pred.loc[pred["year"] == r["year"]]
        seen = set(g["station"])
        if seen != part:
            ok_st = False
            notes.append(f"{r['year']}: preds {sorted(seen)} vs audit {sorted(part)}")
        if len(g) != r["test_examples"] or int(g["onset"].sum()) != r["test_events"] or \
                int((g["onset"] & g["part_window"]).sum()) != r["test_part_window_events"]:
            ok_n = False
        base = g["base_rate"].unique()
        if len(base) != 1 or abs(base[0] - r["train_events"] / r["train_examples"]) > TOL:
            ok_n = False
            notes.append(f"{r['year']}: base_rate")
    check(f"{place} A7 stations per year match audit_years", ok_st, "; ".join(notes))
    check(f"{place} A7 examples/events/part-window per year and base_rate match audit_years", ok_n)
    res.update(primary=primary, bar=bar, verdicts=verdict_mine, pred=pred)
    return res


# =============================================================================================================
# Part B: my own label and input rebuild
# =============================================================================================================
def parse_rdb_chla(path: Path) -> tuple[dict, dict]:
    """Daily-mean chlorophyll (32316/00003) from one RDB file: {date: value}, with PREREG section 3 rules and
    readings 1-2: pick the series with most numeric days (counted before dropping 'e'; tie -> lower TS_ID), drop
    values whose qualifier has an 'e' component, non-numeric entries are missing, '<' '>' '[4]' kept."""
    with open(path) as fh:
        lines = [ln.rstrip("\n") for ln in fh if not ln.startswith("#")]
    header = lines[0].split("\t")
    body = [ln.split("\t") for ln in lines[2:] if ln]
    cands = []
    for j, h in enumerate(header):
        mm = re.fullmatch(r"(\d+)_32316_00003", h)
        if mm:
            vals = []
            for row in body:
                x = row[j] if j < len(row) else ""
                try:
                    vals.append(float(x))
                except ValueError:
                    vals.append(None)
            cands.append((sum(v is not None for v in vals), -int(mm.group(1)), j, vals))
    cands.sort(reverse=True)
    n_numeric, neg_id, j, vals = cands[0]
    jc = header.index(header[j] + "_cd")
    out, info = {}, {"ts_id": -neg_id, "n_candidates": len(cands), "estimated_dropped": 0, "non_numeric": 0}
    di = header.index("datetime")
    for row, v in zip(body, vals):
        raw = row[j] if j < len(row) else ""
        if v is None:
            if raw.strip():
                info["non_numeric"] += 1
            continue
        code = row[jc] if jc < len(row) else ""
        if "e" in code.split(":"):
            info["estimated_dropped"] += 1
            continue
        d = datetime.strptime(row[di], "%Y-%m-%d").date()
        out[d] = v
    return out, info


def series_from_frame(frame: pd.DataFrame) -> dict:
    s = {}
    for st, g in frame.groupby("station"):
        g = g.loc[g["chla_mean"].notna()]
        s[st] = dict(zip(g["date"].dt.date, g["chla_mean"].astype(float)))
    return s


def line_for(values_upto: list[float]) -> float:
    v = sorted(values_upto)
    return v[int(0.9 * len(v))]


def year_lines(series: dict, year: int) -> tuple[dict, int]:
    cut = datetime(year - 1, 12, 31).date()
    lines, odd = {}, 0
    for st, d in series.items():
        vals = [v for day, v in d.items() if day <= cut]
        if len(vals) >= 300:
            lines[st] = line_for(vals)
            if int(0.9 * len(vals)) != (9 * len(vals)) // 10:
                odd += 1
    return lines, odd


def moon_sin(day, utc_offset: int) -> float:
    noon_utc = datetime(day.year, day.month, day.day, 12) - timedelta(hours=utc_offset)
    elapsed = (noon_utc - datetime(2000, 1, 6, 18, 14)).total_seconds() / 86400.0
    phase = elapsed % 14.7652944
    return math.sin(2 * math.pi * phase / 14.7652944)


def rebuild(series_st: dict, line: float, t, utc_offset: int) -> dict:
    get = series_st.get
    v = get(t)
    fut = [get(t + timedelta(days=k)) for k in (1, 2, 3)]
    meas = [f for f in fut if f is not None]
    onset = any(f >= line for f in meas)
    valid = v is not None and v < line and len(meas) > 0 and (onset or len(meas) == 3)
    out = {"valid": valid, "onset": onset, "part_window": len(meas) < 3}
    if v is None:
        return out
    ratio = v / line
    prev = get(t - timedelta(days=1))
    out["ratio"] = ratio
    out["d1_ratio"] = ratio - prev / line if prev is not None else np.nan
    out["max7_ratio"] = max(get(t - timedelta(days=k)) / line for k in range(7) if get(t - timedelta(days=k)) is not None)
    dsh = 60.0
    for k in range(1, 61):
        x = get(t - timedelta(days=k))
        if x is not None and x >= line:
            dsh = float(k)
            break
    out["days_since_high"] = dsh
    out["moon_sin"] = moon_sin(t, utc_offset)
    recent = [get(t - timedelta(days=k)) for k in range(1, 15)]
    out["fresh_onset"] = not any(x is not None and x >= line for x in recent)
    return out


def full_recount(series: dict, pred: pd.DataFrame, years) -> tuple[bool, list[str]]:
    """Every test example of every year: my rule vs predictions.csv. Same key set, and per example the same
    onset, part_window and fresh_onset flags and the same B1 (= my ratio)."""
    ok, notes = True, []
    for y in years:
        lines, _ = year_lines(series, y)
        mine = {}
        for st, line in lines.items():
            for day in series[st]:
                if day.year != y:
                    continue
                r = rebuild(series[st], line, day, 0)
                if r["valid"]:
                    mine[(st, day)] = r
        g = pred.loc[pred["year"] == y]
        pk = dict(zip(zip(g["station"], g["date"].dt.date), g[["onset", "part_window", "fresh_onset", "B1"]]
                      .itertuples(index=False)))
        if set(pk) != set(mine):
            ok = False
            notes.append(f"{y}: mine {len(mine)} vs pipe {len(pk)}; only mine {len(set(mine) - set(pk))}, "
                         f"only pipe {len(set(pk) - set(mine))}")
            continue
        bad = sum(r["onset"] != bool(pk[k].onset) or r["part_window"] != bool(pk[k].part_window)
                  or r["fresh_onset"] != bool(pk[k].fresh_onset) or abs(r["ratio"] - pk[k].B1) > TOL
                  for k, r in mine.items())
        if bad:
            ok = False
            notes.append(f"{y}: {bad} examples differ in onset/part_window/fresh_onset/B1")
    return ok, notes


def part_b(place: str, pred: pd.DataFrame) -> dict:
    print(f"\n=== Part B: {place}")
    sys.path.insert(0, str(ROOT / "src"))
    import config  # noqa: E402
    import run_study  # noqa: E402
    if place == "li":
        series, infos = {}, {}
        for st in config.LI.stations:
            series[st], infos[st] = parse_rdb_chla(RAW_LI / f"usgs_dv_{st}.rdb")
        import data_li  # noqa: E402
        frame = data_li.load_li_frame()          # pipeline's frame, used ONLY to get pipeline input values
        spec, date_inputs = config.LI, None
        info_txt = "; ".join(f"{s}: TS {i['ts_id']} of {i['n_candidates']}, e-dropped {i['estimated_dropped']}, "
                             f"non-numeric {i['non_numeric']}" for s, i in infos.items())
        print("  LI chlorophyll series: " + info_txt)
        # my parse vs pipeline frame: same set of measured chla days
        pipe_series = series_from_frame(frame)
        same = all(set(series[s]) == set(pipe_series[s]) and
                   all(abs(series[s][d] - pipe_series[s][d]) <= TOL for d in series[s]) for s in series)
        check("li B0 my RDB parse of chla_mean equals pipeline frame (all days, all stations)", same)
    else:
        import data_sf  # noqa: E402
        frame = data_sf.load_sf_frame()
        date_inputs = data_sf.load_sf_date_inputs()
        spec = config.SF
        series = series_from_frame(frame)
    utc = PLACES[place]["utc_offset"]

    rng = np.random.default_rng(SEED)
    pick = np.sort(rng.choice(len(pred), size=200, replace=False))
    sample = pred.iloc[pick].reset_index(drop=True)

    items = ["valid example", "taking part (>=300 days)", "high line", "onset", "part_window", "fresh_onset",
             "ratio", "d1_ratio", "max7_ratio", "days_since_high", "moon_sin", "B1 == my ratio"]
    match = {k: 0 for k in items}
    maxdiff = {k: 0.0 for k in items}
    fails = {k: [] for k in items}
    odd_total = 0
    cov = {k: 0 for k in ("d1 missing", "gap in t-6..t", "days_since_high < 60", "onset true", "part_window true")}
    for year, grp in sample.groupby("year"):
        lines, odd = year_lines(series, int(year))
        odd_total += odd
        _, _, test = run_study.year_data(frame, spec, int(year), date_inputs, None)
        test = test.set_index(["station", "date"])
        for _, row in grp.iterrows():
            st, t = row["station"], row["date"].date()
            key = (st, row["date"])
            p = test.loc[key] if key in test.index else None
            part_ok = st in lines
            match["taking part (>=300 days)"] += part_ok
            if not part_ok:
                fails["taking part (>=300 days)"].append((st, t, "not taking part"))
                continue
            line = lines[st]
            mine = rebuild(series[st], line, t, utc)
            n7 = sum(series[st].get(t - timedelta(days=k)) is not None for k in range(7))
            cov["d1 missing"] += bool(np.isnan(mine.get("d1_ratio", 0.0)))
            cov["gap in t-6..t"] += n7 < 7
            cov["days_since_high < 60"] += mine.get("days_since_high", 60) < 60
            cov["onset true"] += mine["onset"]
            cov["part_window true"] += mine["part_window"]

            def cmp_flag(name, a, b):
                if a == b:
                    match[name] += 1
                else:
                    fails[name].append((st, t, f"mine {a} pipe {b}"))

            def cmp_num(name, a, b):
                a = np.nan if a is None else float(a)
                b = np.nan if b is None else float(b)
                if np.isnan(a) and np.isnan(b):
                    match[name] += 1
                    return
                d = abs(a - b) if not (np.isnan(a) or np.isnan(b)) else np.inf
                maxdiff[name] = max(maxdiff[name], d)
                if d <= TOL:
                    match[name] += 1
                else:
                    fails[name].append((st, t, f"|diff| {d:.3g}"))

            cmp_flag("valid example", mine["valid"], p is not None)
            if p is None:
                continue
            cmp_num("high line", line, p["threshold"])
            cmp_flag("onset", mine["onset"], bool(row["onset"]))
            cmp_flag("part_window", mine["part_window"], bool(row["part_window"]))
            cmp_flag("fresh_onset", mine["fresh_onset"], bool(row["fresh_onset"]))
            for name in ("ratio", "d1_ratio", "max7_ratio", "days_since_high", "moon_sin"):
                cmp_num(name, mine[name], p[name])
            cmp_num("B1 == my ratio", mine["ratio"], row["B1"])
            # the label and part_window stored with the pipeline's test frame must agree with predictions.csv
            if bool(p["onset"]) != bool(row["onset"]) or bool(p["part_window"]) != bool(row["part_window"]):
                fails["onset"].append((st, t, "pipeline test frame disagrees with predictions.csv"))
    # B1 is written at %.12g; allow 12-significant-digit rounding for that one item
    out_rows = []
    for k in items:
        tol_note = ""
        ok = match[k] == 200
        if k == "B1 == my ratio" and not ok:
            tol_note = " (csv rounding)"
        out_rows.append((k, match[k], maxdiff[k], ok))
        check(f"{place} B {k}: {match[k]}/200", ok, f"max |diff| {maxdiff[k]:.2e}{tol_note}"
              + (f"; first fails: {fails[k][:3]}" if fails[k] else ""))
    check(f"{place} B high-line position: int(0.9n) equals (9n)//10 for every line used", odd_total == 0,
          f"{odd_total} lines differ")
    print(f"  {place} edge cases in the sample: {cov}")
    ok, notes = full_recount(series, pred, sorted(pred["year"].unique()))
    check(f"{place} B full recount: every test example of every year (key set, onset, part_window, fresh_onset, B1)", ok,
          "; ".join(notes))
    return {"rows": out_rows, "recount_ok": ok, "sample_years": sample["year"].value_counts().sort_index().to_dict(),
            "sample_events": int(sample["onset"].sum())}


def main() -> int:
    res = {}
    for place in ("sf", "li"):
        res[place] = part_a(place)
    for place in ("sf", "li"):
        res[place]["B"] = part_b(place, res[place]["pred"])
        print(f"  {place} sample: events {res[place]['B']['sample_events']}, by year {res[place]['B']['sample_years']}")
    n_fail = sum(not ok for _, ok, _ in RESULTS)
    print(f"\n{len(RESULTS) - n_fail} PASS, {n_fail} FAIL")
    print("GATE " + ("PASSED" if n_fail == 0 else "FAILED"))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
