#!/usr/bin/env python3
"""Recompute WS-27 paired effects from every verified raw experiment cell."""
import argparse
import json
import random
import statistics
from pathlib import Path

import run_ws27_matrix as matrix

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_SEED = 20262799
BOOTSTRAP_DRAWS = 10000


def change(candidate, control):
    if control <= 0:
        raise RuntimeError("Nonpositive ECMP control value")
    return 100.0 * (candidate / control - 1.0)


def median_interval(values, seed):
    rng = random.Random(seed)
    draws = [statistics.median(rng.choices(values, k=len(values)))
             for _ in range(BOOTSTRAP_DRAWS)]
    draws.sort()
    return [draws[int(0.025 * BOOTSTRAP_DRAWS)],
            draws[int(0.975 * BOOTSTRAP_DRAWS)]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("screen", "confirm"))
    args = parser.parse_args()
    matrix.configure(args.stage)
    plan = matrix.engine.frozen_plan()
    rows = [matrix.engine.verify(cell) for cell in plan["cells"]]
    by_key = {(row["seed"], row["background"], row["mode"]): row for row in rows}
    if len(by_key) != len(plan["cells"]):
        raise RuntimeError("Duplicate or missing WS-27 matrix cell")
    paired = []
    for seed in plan["demand_seed_order"]:
        for background in plan["background_levels"]:
            control = by_key[(seed, background, "fecmp")]
            for mode in plan["modes"]:
                if mode == "fecmp":
                    continue
                candidate = by_key[(seed, background, mode)]
                paired.append({
                    "seed": seed, "background": background, "mode": mode,
                    "baseline_id": control["id"], "candidate_id": candidate["id"],
                    "moe_batch_change_pct": change(candidate["moe_batch_us"],
                                                   control["moe_batch_us"]),
                    "moe_fct_p50_change_pct": change(candidate["tags"]["2"]["p50_fct_us"],
                                                     control["tags"]["2"]["p50_fct_us"]),
                    "moe_fct_p99_change_pct": change(candidate["tags"]["2"]["p99_fct_us"],
                                                     control["tags"]["2"]["p99_fct_us"]),
                    "background_p99_change_pct":
                        (change(candidate["background_p99_us"], control["background_p99_us"])
                         if background else None),
                })
    effects = []
    for background in plan["background_levels"]:
        for mode in plan["modes"]:
            if mode == "fecmp":
                continue
            subset = [row for row in paired if row["background"] == background and
                      row["mode"] == mode]
            primary = [row["moe_batch_change_pct"] for row in subset]
            result = {
                "background": background, "mode": mode, "demand_seeds": len(subset),
                "moe_batch_median_change_pct": statistics.median(primary),
                "moe_batch_median_bootstrap_95pct":
                    median_interval(primary, BOOTSTRAP_SEED + background + len(mode)),
                "moe_batch_improved_seeds": sum(value < 0 for value in primary),
                "moe_batch_worsened_seeds": sum(value > 0 for value in primary),
                "moe_fct_p50_median_change_pct": statistics.median(
                    row["moe_fct_p50_change_pct"] for row in subset),
                "moe_fct_p99_median_change_pct": statistics.median(
                    row["moe_fct_p99_change_pct"] for row in subset),
            }
            if background:
                safety = [row["background_p99_change_pct"] for row in subset]
                result["background_p99_median_change_pct"] = statistics.median(safety)
                result["background_p99_median_bootstrap_95pct"] = median_interval(
                    safety, BOOTSTRAP_SEED + background + len(mode) + 1000)
                if background == 192:
                    result["background_constraint_pass"] = statistics.median(safety) < 3.0
            effects.append(result)
    output = {
        "stage": args.stage,
        "source_sha": matrix.SOURCE_SHA,
        "independent_unit": "one synthetic demand seed; flows are nested observations",
        "bootstrap": {"seed": BOOTSTRAP_SEED, "draws": BOOTSTRAP_DRAWS,
                      "method": "resample demand seeds with replacement; percentile interval"},
        "decision": "Report effects and uncertainty to user; no automatic business-effect winner",
        "verified_cells": len(rows), "effects": effects, "paired_changes": paired,
    }
    path = ROOT / ("docs/research/evidence/ws27-" + args.stage + "-analysis.json")
    encoded = json.dumps(output, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("Existing WS-27 analysis differs: " + str(path))
    path.write_text(encoded, encoding="utf-8")
    print(json.dumps({"stage": args.stage, "verified_cells": len(rows),
                      "effects": effects}, sort_keys=True))


if __name__ == "__main__":
    main()
