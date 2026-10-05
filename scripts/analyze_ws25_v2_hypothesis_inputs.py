#!/usr/bin/env python3
"""Reproduce descriptive v1/baseline observations used to propose WS-25 v2."""
import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "docs/research/evidence/ws25-v1fix-formal-cell-metrics.csv"
DIAG = ROOT / "docs/research/evidence/ws25-v1-formal-tail-diagnostic-analysis.json"
OUT = ROOT / "docs/research/evidence/ws25-v2-hypothesis-inputs.json"
MODES = ("drill", "conga", "letflow", "conweave", "classreserve")


def main():
    with TABLE.open("r", encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if len(rows) != 576:
        raise RuntimeError("Missing formal cell metrics")
    cells = {(int(row["seed"]), int(row["background_flows"]), row["mode"]): row
             for row in rows}
    if len(cells) != 576:
        raise RuntimeError("Formal cell key duplicate")
    by_mode = {}
    for mode in MODES:
        metrics = {}
        for metric in ("moe_batch_us", "background_p99_fct_us"):
            changes = [100 * (float(cells[seed, 192, mode][metric]) /
                              float(cells[seed, 192, "fecmp"][metric]) - 1)
                       for seed in range(20262521, 20262545)]
            metrics[metric] = {"median_change_pct": statistics.median(changes),
                               "strictly_improved_seeds": sum(value < 0 for value in changes),
                               "n": len(changes)}
        by_mode[mode] = metrics
    oracle = [100 * (min(float(cells[seed, 192, mode]["background_p99_fct_us"])
                         for mode in MODES) /
                     float(cells[seed, 192, "fecmp"]["background_p99_fct_us"]) - 1)
              for seed in range(20262521, 20262545)]
    diagnostic = json.loads(DIAG.read_text(encoding="utf-8"))
    if len(diagnostic["cells"]) != 2 or not all(
            cell["matches_formal_fct"] for cell in diagnostic["cells"]):
        raise RuntimeError("Tail diagnostic is incomplete")
    empty = {}
    for cell in diagnostic["cells"]:
        choice = cell["choice"]["1"]
        empty[str(cell["background"])] = {
            "id": cell["id"], "both_queues_empty": choice["both_queues_empty"],
            "events": choice["events"],
            "fraction": choice["both_queues_empty"] / choice["events"]}
    output = {"role": "posthoc_hypothesis_generation_only",
              "source_sha": rows[0]["source_sha"],
              "formal_192_vs_ecmp": by_mode,
              "best_existing_whole_arm_per_seed_background_p99": {
                  "median_change_pct": statistics.median(oracle),
                  "strictly_improved_seeds": sum(value < 0 for value in oracle),
                  "at_least_5pct_faster_seeds": sum(value <= -5 for value in oracle),
                  "n": len(oracle), "not_a_new_mechanism_upper_bound": True},
              "background_empty_queue_first_choices": empty,
              "formal_efficacy_rejudged": False}
    OUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"modes": len(by_mode), "diagnostic_cells": len(empty),
                      "output": str(OUT)}))


if __name__ == "__main__":
    main()
