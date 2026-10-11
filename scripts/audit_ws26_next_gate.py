#!/usr/bin/env python3
"""Audit the frozen WS-26 v4 low-stage gate without starting experiments."""

import hashlib
import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/research/evidence/ws26-classlane4-pilot-plan-r2.json"
ANALYSIS = ROOT / "docs/research/evidence/ws26-classlane4-pilot-r2-analysis.json"
OUTPUT = ROOT / "docs/research/evidence/ws26-next-gate-local-audit.json"
PLAN_SHA = "b71155816dff1fd7410073913a35ae714c9bc6988c789867eba79829aa58cc02"
ANALYSIS_SHA = "44375a60a5fa3d9a5a411e366ddb938397d27e055437c74314fb8454b42b19d1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if digest(PLAN) != PLAN_SHA or digest(ANALYSIS) != ANALYSIS_SHA:
        raise RuntimeError("Frozen plan or high-stage analysis changed")
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    gate = plan["high_stage_gate"]
    if (plan["revision"] != "r2" or gate["seed_count"] != 4 or
            gate["median_each_metric_max_percent"] != -3 or
            gate["strict_improvement_min_seeds_each_metric"] != 3):
        raise RuntimeError("Unexpected frozen high-stage gate")
    high = [cell for cell in plan["cells"] if cell["stage"] == "high"]
    low = [cell for cell in plan["cells"] if cell["stage"] == "conditional_low"]
    if len(high) != 28 or len(low) != 24 or len({cell["id"] for cell in plan["cells"]}) != 52:
        raise RuntimeError("Frozen cell inventory changed")
    expected = {(seed, background, mode) for seed in plan["seeds"]
                for background in (0, 64, 128) for mode in ("fecmp", "classlane4")}
    if {(cell["seed"], cell["background"], cell["mode"]) for cell in low} != expected:
        raise RuntimeError("Conditional low-stage pairing changed")

    metrics = {}
    for key in ("moe_batch_completion", "background_fct_p99"):
        recorded = analysis["high_stage"][key]
        pairs = recorded["pairs"]
        if len(pairs) != 4 or {row["seed"] for row in pairs} != set(plan["seeds"]):
            raise RuntimeError("High-stage seed pairing changed")
        changes = [100 * (row["classlane4"] / row["fecmp"] - 1) for row in pairs]
        median = statistics.median(changes)
        improved = sum(change < 0 for change in changes)
        passed = (median <= gate["median_each_metric_max_percent"] and
                  improved >= gate["strict_improvement_min_seeds_each_metric"])
        if (abs(median - recorded["median_change_percent"]) > 1e-9 or
                improved != recorded["strict_improvements"] or passed != recorded["passed"]):
            raise RuntimeError("High-stage result differs from recorded analysis")
        metrics[key] = {"median_change_percent": median,
                        "strict_improvements": improved, "passed": passed}

    if any(not (ROOT / "results" / cell["id"]).is_dir() for cell in high):
        raise RuntimeError("A previously verified high-stage result is unavailable locally")
    for cell in low:
        trace = ROOT / "config" / cell["trace"]
        if digest(trace) != cell["trace_sha256"]:
            raise RuntimeError("Conditional low-stage trace changed: " + cell["id"])
        if (ROOT / "results" / cell["id"]).exists():
            raise RuntimeError("A conditional low-stage local result already exists: " + cell["id"])

    passed = all(row["passed"] for row in metrics.values())
    if passed != analysis["high_stage"]["dual_effect_gate_passed"] or passed:
        raise RuntimeError("Unexpected high-stage decision")
    result = {"scope": "local gate audit only; no remote ID inventory or new run",
              "plan_sha256": PLAN_SHA, "analysis_sha256": ANALYSIS_SHA,
              "high_result_directories": len(high), "high_metrics": metrics,
              "high_dual_gate_passed": passed, "conditional_low_ids": len(low),
              "conditional_low_trace_hashes_valid": True,
              "conditional_low_local_result_directories": 0,
              "next_action": "keep low-stage IDs unstarted; define and review a new candidate"}
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print("audited 28 high and 24 low IDs; high dual gate remains closed")


if __name__ == "__main__":
    main()
