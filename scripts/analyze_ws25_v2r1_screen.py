#!/usr/bin/env python3
"""Reverify v2r1 frozen raw and summarize its exploratory paired effects."""
import json
import statistics

from analyze_ws25_v2_screen import (background_flows, diagnostic_qps,
                                     qp_affected, trace_flow_ids)
from verify_ws25_v2r1_screen import PLAN, ROOT, verify


def pct(candidate, baseline):
    return 100.0 * (candidate / baseline - 1.0)


def main():
    cells = [verify(cell) for cell in PLAN["cells"]]
    if len(cells) != 28 or len({cell["id"] for cell in cells}) != 28:
        raise RuntimeError("Frozen 28-cell plan incomplete")
    seeds = sorted({cell["seed"] for cell in cells})
    if seeds != list(range(20262577, 20262581)):
        raise RuntimeError("Unexpected demand seeds")
    modes = ("fecmp", "drill", "conga", "letflow", "conweave")
    result = {"source_sha": PLAN["source_sha"], "verified_cells": 28,
              "seeds": {}, "comparisons": {}, "resource": {}}
    for seed in seeds:
        main_rows = {cell["mode"]: cell for cell in cells
                     if cell["seed"] == seed and cell["ws25_diag"] == 0}
        diag_rows = [cell for cell in cells if cell["seed"] == seed and cell["ws25_diag"] == 1]
        if set(main_rows) != set(modes) | {"destspread"} or len(diag_rows) != 1:
            raise RuntimeError("Incomplete six-mode block: " + str(seed))
        candidate = main_rows["destspread"]
        diag = diag_rows[0]
        if diag["mode"] != "destspread" or candidate["fct_sha256"] != diag["fct_sha256"]:
            raise RuntimeError("Diagnostic perturbation: " + str(seed))
        candidate_flows = background_flows(candidate)
        ecmp_flows = background_flows(main_rows["fecmp"])
        if candidate_flows.keys() != ecmp_flows.keys():
            raise RuntimeError("Background flow identities differ")
        flow_ids = trace_flow_ids(diag)
        qps = diagnostic_qps(diag)
        if len(qps) != 16576:
            raise RuntimeError("Diagnostic QP count mismatch")
        worst = sorted(candidate_flows,
                       key=lambda key: candidate_flows[key] - ecmp_flows[key],
                       reverse=True)[:3]
        result["seeds"][str(seed)] = {
            "metrics": {mode: {"moe_batch_us": row["moe_batch_us"],
                               "background_p99_us": row["background_p99_us"],
                               "id": row["id"]}
                        for mode, row in main_rows.items()},
            "route": candidate["route"],
            "qp_totals": diag["qp_by_tag"],
            "qp_affected": qp_affected(diag),
            "background_flow_median_delta_us": statistics.median(
                candidate_flows[key] - ecmp_flows[key] for key in candidate_flows),
            "worst_background_flows": [
                {"dst": key[1], "ecmp_fct_us": ecmp_flows[key],
                 "candidate_fct_us": candidate_flows[key],
                 "delta_us": candidate_flows[key] - ecmp_flows[key],
                 "qp": qps[flow_ids[key]]} for key in worst],
        }
    for baseline in modes:
        effects = {}
        for metric in ("moe_batch_us", "background_p99_us"):
            values = [pct(result["seeds"][str(seed)]["metrics"]["destspread"][metric],
                          result["seeds"][str(seed)]["metrics"][baseline][metric])
                      for seed in seeds]
            effects[metric] = {"by_seed_pct": dict(zip(map(str, seeds), values)),
                               "median_pct": statistics.median(values),
                               "improved_seeds": sum(value < 0 for value in values)}
        result["comparisons"][baseline] = effects
    resources = [cell["resource"] for cell in cells]
    result["resource"] = {
        "peak_tree_rss_mib": max(row["peak_tree_rss_mib"] for row in resources),
        "minimum_mem_available_gib": min(row["minimum_mem_available_gib"] for row in resources),
        "minimum_free_gib": min(row["minimum_free_gib"] for row in resources),
    }
    decision = result["comparisons"]["fecmp"]
    result["screen_gate_pass"] = all(
        decision[metric]["median_pct"] <= -5 and decision[metric]["improved_seeds"] >= 3
        for metric in ("moe_batch_us", "background_p99_us"))
    path = ROOT / "docs/research/evidence/ws25-v2r1-screen-analysis.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    print(json.dumps({"verified_cells": len(cells),
                      "screen_gate_pass": result["screen_gate_pass"],
                      "output": str(path)}, sort_keys=True))


if __name__ == "__main__":
    main()
