#!/usr/bin/env python3
"""Apply the frozen exploratory gates to verified WS-26 v3 pilot rows."""

import argparse
import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = json.loads((ROOT / "docs/research/evidence/ws26-v3-pilot-plan.json")
                  .read_text(encoding="utf-8"))
SEEDS = (20262690, 20262691, 20262692, 20262693)


def change(candidate, baseline):
    if candidate is None or baseline is None or baseline <= 0:
        raise RuntimeError("Undefined paired metric")
    return 100.0 * (candidate / baseline - 1.0)


def summarize_metric(pairs, key, stage):
    rows = []
    for seed, background, candidate, baseline in pairs:
        value = change(candidate[key], baseline[key])
        rows.append({"seed": seed, "background": background,
                     "candidate": candidate[key], "ecmp": baseline[key],
                     "change_percent": value, "strict_improvement": value < 0})
    changes = [row["change_percent"] for row in rows]
    median = statistics.median(changes)
    improved = sum(row["strict_improvement"] for row in rows)
    if stage == "high":
        passed = median <= -3.0 and improved >= 3
    else:
        passed = median <= 5.0 and sum(value > 10.0 for value in changes) <= 1
    return {"median_change_percent": median, "strict_improvements": improved,
            "over_ten_percent_harms": sum(value > 10.0 for value in changes),
            "passed": passed, "pairs": rows}


def analyze(rows):
    indexed = {}
    for row in rows:
        key = (row["seed"], row["background"], row["mode"], row["ws25_diag"])
        if key in indexed:
            raise RuntimeError("Duplicate verified pilot row")
        indexed[key] = row
    planned = {row["id"]: row for row in PLAN["cells"]}
    for row in rows:
        cell = planned.get(row["id"])
        if cell is None or any(row[key] != cell[key] for key in
                               ("stage", "seed", "background", "mode", "ws25_diag")):
            raise RuntimeError("Unexpected pilot identity: " + row["id"])
    high_plan = [row for row in PLAN["cells"] if row["stage"] == "high"]
    high_ids = {row["id"] for row in high_plan}
    received = {row["id"] for row in rows}
    if not high_ids <= received:
        raise RuntimeError("High stage is incomplete")
    high_pairs = [(seed, 192, indexed[(seed, 192, "classreserve3", 0)],
                   indexed[(seed, 192, "fecmp", 0)]) for seed in SEEDS]
    moe = summarize_metric(high_pairs, "moe_batch_us", "high")
    background = summarize_metric(high_pairs, "background_p99_us", "high")
    coverage = {"with_background_seeds": [], "diverted_seeds": [],
                "with_same_destination": {}, "diverted": {}}
    for seed in SEEDS:
        diag = indexed[(seed, 192, "classreserve3", 1)]
        route = diag["route"]
        if route is None:
            raise RuntimeError("Diagnostic route summary missing")
        for key in ("with_background", "diverted", "with_same_destination"):
            if key not in route:
                raise RuntimeError("Diagnostic counter missing: " + key)
        if route["with_background"] > 0:
            coverage["with_background_seeds"].append(seed)
        if route["diverted"] > 0:
            coverage["diverted_seeds"].append(seed)
        coverage["with_same_destination"][str(seed)] = route["with_same_destination"]
        coverage["diverted"][str(seed)] = route["diverted"]
    coverage["passed"] = (len(coverage["with_background_seeds"]) >= 3 and
                          len(coverage["diverted_seeds"]) >= 3)
    high_pass = moe["passed"] and background["passed"] and coverage["passed"]
    low_plan = [row for row in PLAN["cells"] if row["stage"] == "low"]
    low_ids = {row["id"] for row in low_plan}
    low_result = None
    if low_ids & received:
        if not low_ids <= received:
            raise RuntimeError("Low stage was started but is incomplete")
        low_result = {}
        for background_count in (0, 64, 128):
            pairs = [(seed, background_count,
                      indexed[(seed, background_count, "classreserve3", 0)],
                      indexed[(seed, background_count, "fecmp", 0)])
                     for seed in SEEDS]
            metrics = {"moe_batch": summarize_metric(pairs, "moe_batch_us", "low")}
            if background_count:
                metrics["background_p99"] = summarize_metric(
                    pairs, "background_p99_us", "low")
            low_result[str(background_count)] = metrics
    low_pass = (low_result is not None and
                all(metric["passed"] for metrics in low_result.values()
                    for metric in metrics.values()))
    if not high_pass:
        decision = "diagnose_or_revise_before_formal"
    elif low_result is None:
        decision = "run_low_stage"
    elif not low_pass:
        decision = "diagnose_or_revise_before_formal"
    else:
        decision = "eligible_to_freeze_formal_protocol"
    return {"decision": decision, "high": {"moe_batch": moe,
            "background_p99": background, "mechanism_coverage": coverage,
            "passed": high_pass}, "low": low_result,
            "pilot_seed_count": len(SEEDS), "verified_cells": len(rows),
            "evidence_level": "exploratory pilot only"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("verified_summary", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = json.loads(args.verified_summary.read_text(encoding="utf-8"))
    result = analyze(source["cells"])
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
