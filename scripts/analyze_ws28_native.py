#!/usr/bin/env python3
"""Compare verified WS-28 native raw cells with the same-input WS-27 ECMP."""
import argparse
import json
import statistics
from pathlib import Path

import analyze_ws28_existing as raw
import run_ws28_native as native


ROOT = Path(__file__).resolve().parents[1]
OLD_RESULTS = ROOT.parent / "ws27-guardhash-compare" / "results"
OUTPUT = ROOT / "docs/research/evidence/ws28-native-analysis.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=native.PLAN)
    parser.add_argument("--old-results", type=Path, default=OLD_RESULTS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    engine = native.configure()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    if (plan["source_sha"] != native.SOURCE_SHA or
            set(plan["modes"]) != set(native.MODES) or
            plan["demand_seed_order"] != list(native.SEEDS)):
        raise RuntimeError("Native plan identity mismatch")
    if len(plan["cells"]) != 96:
        raise RuntimeError("Native matrix incomplete")
    old_plan = json.loads(raw.PLAN.read_text(encoding="utf-8"))
    controls = {c["seed"]: c for c in old_plan["cells"]
                if c["background"] == 192 and c["mode"] == "fecmp"}
    cells = {(c["seed"], c["mode"]): c for c in plan["cells"]}
    if len(controls) != 24 or len(cells) != 96:
        raise RuntimeError("Duplicate or absent seed-mode pair")
    by_mode = {mode: [] for mode in native.MODES}
    dynamic = {mode: [] for mode in native.MODES}
    for seed in native.SEEDS:
        baseline = raw.read_cell(args.old_results, controls[seed])
        for mode in native.MODES:
            cell = cells[(seed, mode)]
            receipt = engine.verify(cell)
            candidate = raw.read_cell(ROOT / "results", cell)
            if baseline["trace_sha256"] != candidate["trace_sha256"]:
                raise RuntimeError("Unpaired trace: " + cell["id"])
            if baseline["moe"].keys() != candidate["moe"].keys():
                raise RuntimeError("Unpaired flow identities: " + cell["id"])
            row = {"seed": seed, "baseline_id": baseline["id"],
                   "candidate_id": candidate["id"], "trace_sha256": baseline["trace_sha256"],
                   "baseline_fct_sha256": baseline["fct_sha256"],
                   "candidate_fct_sha256": candidate["fct_sha256"],
                   "moe_batch_us": candidate["batch_us"],
                   "ecmp_moe_batch_us": baseline["batch_us"],
                   "moe_batch_change_pct": raw.change(candidate["batch_us"], baseline["batch_us"]),
                   "moe_single_flow_p95_change_pct": raw.change(
                       candidate["moe_fct_p95_us"], baseline["moe_fct_p95_us"]),
                   "background_p99_change_pct": raw.change(
                       candidate["background_p99_us"], baseline["background_p99_us"]),
                   "dynamic_receipt": receipt["native_dynamic"]}
            by_mode[mode].append(row)
            dynamic[mode].append(receipt["native_dynamic"])
    summary = []
    for mode in native.MODES:
        rows = by_mode[mode]
        moe = [r["moe_batch_change_pct"] for r in rows]
        bg = [r["background_p99_change_pct"] for r in rows]
        ecmp_p95 = raw.percentile([r["ecmp_moe_batch_us"] for r in rows], 95)
        mode_p95 = raw.percentile([r["moe_batch_us"] for r in rows], 95)
        summary.append({"mode": mode, "demand_seeds": len(rows),
                        "moe_batch_median_change_pct": statistics.median(moe),
                        "moe_batch_improved_seeds": sum(x < 0 for x in moe),
                        "moe_batch_worsened_seeds": sum(x > 0 for x in moe),
                        "moe_batch_p95_us": mode_p95,
                        "moe_batch_p95_change_pct": raw.change(mode_p95, ecmp_p95),
                        "moe_single_flow_p95_median_change_pct": statistics.median(
                            r["moe_single_flow_p95_change_pct"] for r in rows),
                        "background_p99_median_change_pct": statistics.median(bg),
                        "background_constraint_pass": statistics.median(bg) < 3,
                        "background_seed_over_3pct": sum(x > 3 for x in bg),
                        "dynamic_receipts": dynamic[mode]})
    output = {"source_sha": native.SOURCE_SHA,
              "plan_sha256": raw.digest(args.plan), "verified_new_cells": 96,
              "verified_paired_ecmp_cells": 24,
              "independent_unit": "one synthetic demand seed; flows are nested",
              "background_constraint": "median paired P99 change < +3% at 192 background",
              "ecmp_moe_batch_p95_us": raw.percentile(
                  [r["ecmp_moe_batch_us"] for r in by_mode[native.MODES[0]]], 95),
              "summary": summary, "paired_changes": by_mode}
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"verified_new_cells": 96, "summary":
                      [{k: v for k, v in row.items() if k != "dynamic_receipts"}
                       for row in summary]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
