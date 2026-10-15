#!/usr/bin/env python3
"""Recompute WS-28 factorial effects from the frozen 120-cell raw matrix."""
import json
import random
import statistics
from pathlib import Path

import analyze_ws28_existing as existing
import run_ws28_ablation as ablation


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/research/evidence/ws28-ablation-plan.json"
EXECUTION = ROOT / "docs/research/evidence/ws28-ablation-execution.json"
OUTPUT = ROOT / "docs/research/evidence/ws28-ablation-analysis.json"
MODES = ("fecmp", "cr-a0-b0", "cr-a1-b0", "cr-a0-b1", "cr-a1-b1")
CONTRASTS = {
    "A_when_B0": ("cr-a1-b0", "cr-a0-b0"),
    "A_when_B1": ("cr-a1-b1", "cr-a0-b1"),
    "B_when_A0": ("cr-a0-b1", "cr-a0-b0"),
    "B_when_A1": ("cr-a1-b1", "cr-a1-b0"),
}
BOOTSTRAP_DRAWS = 10000


def interval(values, seed):
    rng = random.Random(seed)
    draws = sorted(statistics.median(rng.choices(values, k=len(values)))
                   for _ in range(BOOTSTRAP_DRAWS))
    return [draws[int(0.025 * BOOTSTRAP_DRAWS)],
            draws[int(0.975 * BOOTSTRAP_DRAWS)]]


def summarize(values, seed):
    return {"median_pct": statistics.median(values),
            "bootstrap_95pct": interval(values, seed),
            "improved_seeds": sum(value < 0 for value in values),
            "worsened_seeds": sum(value > 0 for value in values),
            "range_pct": [min(values), max(values)]}


def main():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    receipt = json.loads(EXECUTION.read_text(encoding="utf-8"))
    if (plan["kind"] != "WS-28 independent-demand two-factor ablation" or
            receipt["source_sha"] != plan["source_sha"] or
            not receipt["verified"] or len(receipt["verified_cells"]) != 120):
        raise RuntimeError("WS-28 ablation plan or execution is incomplete")
    ablation.validate_plan(plan)
    ablation.configure(plan)
    existing.SOURCE_SHA = plan["source_sha"]
    receipt_by_id = {row["id"]: row for row in receipt["verified_cells"]}
    if len(receipt_by_id) != 120:
        raise RuntimeError("WS-28 ablation execution has duplicate IDs")
    by_key = {(cell["seed"], cell["mode"]): cell for cell in plan["cells"]}
    if len(by_key) != 120:
        raise RuntimeError("WS-28 ablation plan has duplicate seed/mode pairs")
    seeds = list(range(20262921, 20262945))
    paired = []
    for seed in seeds:
        cells = {}
        for mode in MODES:
            planned = by_key[(seed, mode)]
            verified = ablation.engine.verify(planned)
            if verified != receipt_by_id[planned["id"]]:
                raise RuntimeError("WS-28 ablation raw receipt changed: " + planned["id"])
            item = existing.read_cell(ROOT / "results", planned)
            if (item["fct_sha256"] != verified["fct_sha256"] or
                    abs(item["batch_us"] - verified["moe_batch_us"]) > 1e-6 or
                    abs(item["background_p99_us"] - verified["background_p99_us"]) > 1e-6):
                raise RuntimeError("WS-28 ablation raw metric mismatch: " + planned["id"])
            cells[mode] = item
        control = cells["fecmp"]
        if any(item["trace_sha256"] != control["trace_sha256"] or
               item["moe"].keys() != control["moe"].keys() or
               item["background"].keys() != control["background"].keys()
               for item in cells.values()):
            raise RuntimeError("WS-28 ablation seed is not paired: " + str(seed))
        metrics = {mode: {"id": item["id"], "fct_sha256": item["fct_sha256"],
                          "moe_batch_us": item["batch_us"],
                          "moe_single_flow_p95_us": item["moe_fct_p95_us"],
                          "background_p99_us": item["background_p99_us"],
                          "moe_batch_vs_ecmp_pct": existing.change(item["batch_us"], control["batch_us"]),
                          "background_p99_vs_ecmp_pct": existing.change(
                              item["background_p99_us"], control["background_p99_us"])}
                   for mode, item in cells.items()}
        contrasts = {}
        for name, (treatment, base) in CONTRASTS.items():
            contrasts[name] = {
                "moe_batch_pct": existing.change(cells[treatment]["batch_us"], cells[base]["batch_us"]),
                "background_p99_pct": existing.change(cells[treatment]["background_p99_us"],
                                                      cells[base]["background_p99_us"]),
            }
        contrasts["A_by_B_interaction"] = {
            metric: contrasts["A_when_B1"][metric] - contrasts["A_when_B0"][metric]
            for metric in ("moe_batch_pct", "background_p99_pct")}
        paired.append({"seed": seed, "trace_sha256": control["trace_sha256"],
                       "modes": metrics, "contrasts": contrasts})
    effects = {}
    for index, mode in enumerate(MODES):
        moe = [row["modes"][mode]["moe_batch_vs_ecmp_pct"] for row in paired]
        bg = [row["modes"][mode]["background_p99_vs_ecmp_pct"] for row in paired]
        effects[mode] = {"moe_batch": summarize(moe, 20262950 + index),
                         "background_p99": summarize(bg, 20262960 + index),
                         "background_constraint_pass": statistics.median(bg) < 3,
                         "background_over_3pct_seeds": sum(value > 3 for value in bg)}
    component = {}
    for index, name in enumerate(tuple(CONTRASTS) + ("A_by_B_interaction",)):
        component[name] = {metric: summarize(
            [row["contrasts"][name][metric] for row in paired], 20262970 + 10 * index + offset)
            for offset, metric in enumerate(("moe_batch_pct", "background_p99_pct"))}
    output = {"kind": "WS-28 two-factor paired raw analysis",
              "source_sha": plan["source_sha"],
              "plan_sha256": existing.digest(PLAN),
              "input_manifest_sha256": plan["input_manifest_sha256"],
              "verified_cells": 120, "independent_units": 24,
              "paired_seeds": paired, "mode_effects": effects,
              "component_effects": component}
    encoded = json.dumps(output, indent=2, sort_keys=True) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("WS-28 ablation analysis differs from existing output")
    OUTPUT.write_text(encoded, encoding="utf-8")
    print(json.dumps({"verified_cells": 120, "independent_units": 24,
                      "output": str(OUTPUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
