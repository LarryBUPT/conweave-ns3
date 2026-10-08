#!/usr/bin/env python3
"""Apply the frozen exploratory gates to verified ClassLane v4 pilot rows."""

import argparse
import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = json.loads((ROOT / "docs/research/evidence/ws26-classlane4-pilot-plan-r2.json")
                  .read_text(encoding="utf-8"))
SEEDS = tuple(PLAN["seeds"])


def change(candidate, baseline):
    if candidate is None or baseline is None or baseline <= 0:
        raise RuntimeError("Undefined paired metric")
    return 100.0 * (candidate / baseline - 1.0)


def compare_metric(pairs, key, stage):
    rows = []
    for seed, background, candidate, baseline in pairs:
        delta = change(candidate[key], baseline[key])
        rows.append({
            "seed": seed,
            "background": background,
            "classlane4": candidate[key],
            "fecmp": baseline[key],
            "change_percent": delta,
            "strict_improvement": delta < 0,
        })
    deltas = [row["change_percent"] for row in rows]
    median = statistics.median(deltas)
    improved = sum(row["strict_improvement"] for row in rows)
    if stage == "high":
        passed = median <= -3.0 and improved >= 3
        over_ten = None
    else:
        over_ten = sum(delta > 10.0 for delta in deltas)
        passed = median <= 5.0 and over_ten <= 1
    return {
        "median_change_percent": median,
        "strict_improvements": improved,
        "over_ten_percent_harms": over_ten,
        "passed": passed,
        "pairs": rows,
    }


def indexed_rows(rows):
    indexed = {}
    plan_by_id = {cell["id"]: cell for cell in PLAN["cells"]}
    for row in rows:
        cell = plan_by_id.get(row.get("id"))
        if cell is None:
            raise RuntimeError("Unexpected pilot ID: " + str(row.get("id")))
        for key in ("stage", "seed", "background", "mode", "ws25_diag"):
            if row.get(key) != cell[key]:
                raise RuntimeError("Verified row identity mismatch: " + cell["id"])
        index = (cell["seed"], cell["background"], cell["mode"], cell["ws25_diag"])
        if index in indexed:
            raise RuntimeError("Duplicate verified pilot row: " + cell["id"])
        indexed[index] = row
    return indexed


def check_diagnostic_identity(indexed):
    for seed in SEEDS:
        plain = indexed.get((seed, 192, "classlane4", 0))
        diagnostic = indexed.get((seed, 192, "classlane4", 1))
        if plain and diagnostic and plain["fct_sha256"] != diagnostic["fct_sha256"]:
            raise RuntimeError("Diagnostic switch changed FCT for seed " + str(seed))


def mechanism_rows(indexed):
    rows = []
    for seed in SEEDS:
        cell = indexed.get((seed, 192, "classlane4", 0))
        diagnostic = indexed.get((seed, 192, "classlane4", 1))
        if cell is None or diagnostic is None:
            raise RuntimeError("Missing ClassLane candidate or diagnostic row for seed " + str(seed))
        route = cell.get("route")
        if route is None:
            raise RuntimeError("Missing ClassLane route counters for seed " + str(seed))
        rows.append({
            "seed": seed,
            "background_packets": route["background_packets"],
            "moe_packets": route["moe_packets"],
            "background_qp_new": route["background_qp_new"],
            "moe_qp_new": route["moe_qp_new"],
            "background_qp_reused": route["background_qp_reused"],
            "moe_qp_reused": route["moe_qp_reused"],
            "background_diverted": route["background_diverted"],
            "moe_diverted": route["moe_diverted"],
            "background_diversion_ratio": (
                route["background_diverted"] / route["background_packets"]
                if route["background_packets"] else None),
            "moe_diversion_ratio": (
                route["moe_diverted"] / route["moe_packets"]
                if route["moe_packets"] else None),
            "fallback": route["fallback"],
            "missing_destination": route["missing_destination"],
            "inconsistent": route["inconsistent"],
            "queue_violations": route["queue_violations"],
            "diagnostic_qp_path_rows": len(diagnostic["diagnostic_qp_paths"]),
            "diagnostic_port_rows": len(diagnostic["port_rows"]),
        })
    return rows


def analyze(rows):
    indexed = indexed_rows(rows)
    check_diagnostic_identity(indexed)
    high_ids = {cell["id"] for cell in PLAN["cells"] if cell["stage"] == "high"}
    received_ids = {row["id"] for row in rows}
    if not high_ids <= received_ids:
        raise RuntimeError("High stage is incomplete")

    high_pairs = [(seed, 192,
                   indexed[(seed, 192, "classlane4", 0)],
                   indexed[(seed, 192, "fecmp", 0)]) for seed in SEEDS]
    moe = compare_metric(high_pairs, "moe_batch_us", "high")
    background = compare_metric(high_pairs, "background_p99_us", "high")
    high_effect_gate = moe["passed"] and background["passed"]
    mechanisms = mechanism_rows(indexed)

    low_ids = {cell["id"] for cell in PLAN["cells"]
               if cell["stage"] == "conditional_low"}
    started_low = low_ids & received_ids
    low_result = None
    if started_low:
        if not high_effect_gate:
            raise RuntimeError("Conditional low stage exists despite a failed high dual gate")
        if not low_ids <= received_ids:
            raise RuntimeError("Conditional low stage is incomplete")
        low_result = {}
        for background_count in (0, 64, 128):
            pairs = [(seed, background_count,
                      indexed[(seed, background_count, "classlane4", 0)],
                      indexed[(seed, background_count, "fecmp", 0)])
                     for seed in SEEDS]
            checks = {"moe_batch": compare_metric(pairs, "moe_batch_us", "low")}
            if background_count:
                checks["background_p99"] = compare_metric(
                    pairs, "background_p99_us", "low")
            low_result[str(background_count)] = checks
    low_pass = (low_result is not None and
                all(metric["passed"] for checks in low_result.values()
                    for metric in checks.values()))

    if not high_effect_gate:
        decision = "high_stage_no_go_analyze_counterexamples"
    elif low_result is None:
        decision = "run_conditional_low_stage"
    elif not low_pass:
        decision = "low_stage_constraint_failed_do_not_freeze_formal"
    else:
        decision = "eligible_for_formal_protocol_freeze"

    return {
        "decision": decision,
        "high_stage": {
            "moe_batch_completion": moe,
            "background_fct_p99": background,
            "dual_effect_gate_passed": high_effect_gate,
            "seed_count": len(SEEDS),
        },
        "mechanism_diagnostics": mechanisms,
        "conditional_low_stage": low_result,
        "conditional_low_stage_passed": low_pass if low_result is not None else None,
        "verified_cells": len(rows),
        "pilot_seed_count": len(SEEDS),
        "evidence_level": "exploratory candidate screening only",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("verified_summary", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = json.loads(args.verified_summary.read_text(encoding="utf-8"))
    result = analyze(source["cells"])
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as target:
            target.write(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
