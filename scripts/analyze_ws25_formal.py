#!/usr/bin/env python3
"""Verify and analyze the frozen WS-25 formal matrix from fetched raw data."""
import hashlib
import json
import math
import random
import statistics
from pathlib import Path

import analyze_ws25_calibration as diagnostics
import run_ws25_formal as formal

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/research/evidence/ws25-v1fix-formal-analysis.json"
MODE_BASELINES = formal.MODES[:-1]


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sign_p(values):
    """Conservative one-sided exact sign test; zero changes count as failures."""
    n = len(values)
    wins = sum(value < 0 for value in values)
    return wins, sum(math.comb(n, k) for k in range(wins, n + 1)) / (2 ** n)


def median_ci(values, seed, iterations=20000):
    rng = random.Random(seed)
    n = len(values)
    medians = sorted(statistics.median(rng.choices(values, k=n))
                     for _ in range(iterations))
    return [medians[int(.025 * iterations)], medians[min(iterations - 1,
                                                         int(.975 * iterations))]]


def holm(pvalues):
    ordered = sorted(pvalues.items(), key=lambda item: item[1])
    adjusted, running = {}, 0.0
    count = len(ordered)
    for index, (name, value) in enumerate(ordered):
        running = max(running, min(1.0, (count - index) * value))
        adjusted[name] = running
    return adjusted


def analyze():
    plan = formal.frozen_plan()
    if len(plan["cells"]) != 576:
        raise RuntimeError("Formal plan must contain 576 cells")
    rows = []
    for index, cell in enumerate(plan["cells"], 1):
        verified = formal.verify(cell)
        folder = ROOT / "results" / cell["id"]
        metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
        raw = folder / "raw" / str(metadata["raw_directory"])
        log_path = folder / "logs/config.log"
        log = log_path.read_text(encoding="utf-8", errors="replace")
        cnp_path = next(raw.glob("*_out_cnp.txt"))
        pfc_path = next(raw.glob("*_out_pfc.txt"))
        uplink_path = next(raw.glob("*_out_uplink.txt"))
        row = {
            "id": cell["id"], "run_order": cell["run_order"], "batch": cell["batch"],
            "seed": cell["seed"], "background": cell["background"],
            "mode": cell["mode"], "source_sha": metadata["git_commit"],
            "trace_sha256": metadata["input_flow_sha256"],
            "topology_sha256": metadata["topology_sha256"],
            "fct_sha256": verified["fct_sha256"],
            "config_log_sha256": sha(log_path),
            "moe_batch_us": verified["moe_batch_us"],
            "background_p99_us": verified["background_p99_us"],
            "cnp": diagnostics.cnp_totals(cnp_path),
            "pfc_events": sum(bool(line.strip()) for line in
                               pfc_path.read_text(encoding="ascii").splitlines()),
            "uplink": diagnostics.uplink_summary(uplink_path),
            "mode_diagnostics": diagnostics.diagnostics(cell["mode"], log),
            "resource": verified["resource"],
        }
        rows.append(row)
        if index % 24 == 0:
            print(json.dumps({"verified": index, "total": 576}), flush=True)
    return plan, rows


def compare(rows, baseline, level):
    by_seed = {(row["seed"], row["mode"]): row for row in rows}
    output = {}
    metrics = ("moe_batch_us",) if level == 0 else (
        "moe_batch_us", "background_p99_us")
    for mode in ("classreserve",) if baseline == "ecmp" else ("classreserve",):
        pairs = []
        for seed in sorted({row["seed"] for row in rows}):
            candidate, control = by_seed[(seed, mode)], by_seed[(seed, baseline)]
            item = {"seed": seed}
            for metric in metrics:
                item[metric + "_change_pct"] = (
                    100 * (candidate[metric] / control[metric] - 1))
            pairs.append(item)
        output[mode] = pairs
    return output["classreserve"]


def main():
    plan, rows = analyze()
    if len(rows) != 576 or len({row["id"] for row in rows}) != 576:
        raise RuntimeError("Raw verifier did not validate all formal IDs")
    seeds = sorted({row["seed"] for row in rows})
    changes, primary = {}, {}
    for level in (0, 64, 128, 192):
        changes[str(level)] = {}
        for baseline in MODE_BASELINES:
            pairs = compare([row for row in rows if row["background"] == level],
                            baseline, level)
            metrics = ("moe_batch_us",) if level == 0 else (
                "moe_batch_us", "background_p99_us")
            summary = {}
            for metric in metrics:
                values = [pair[metric + "_change_pct"] for pair in pairs]
                wins, pvalue = sign_p(values)
                summary[metric] = {
                    "median_change_pct": statistics.median(values),
                    "range_change_pct": [min(values), max(values)],
                    "bootstrap_95pct_median_ci": median_ci(
                        values, 20261006 + level + len(baseline) + len(metric)),
                    "improved_seed_count": wins,
                    "one_sided_exact_sign_p": pvalue,
                    "per_seed": values,
                }
            if level == 192:
                summary["both_directions"] = all(
                    pair["moe_batch_us_change_pct"] < 0 and
                    pair["background_p99_us_change_pct"] < 0 for pair in pairs)
            changes[str(level)][baseline] = summary
            if level == 192 and baseline == "ecmp":
                primary = summary

    primary_pass = all(
        primary[metric]["median_change_pct"] <= -5 and
        primary[metric]["improved_seed_count"] >= 17 and
        primary[metric]["one_sided_exact_sign_p"] <= .05
        for metric in ("moe_batch_us", "background_p99_us"))
    secondary_p = {}
    for baseline in MODE_BASELINES[1:]:
        endpoint_p = [changes["192"][baseline][metric]["one_sided_exact_sign_p"]
                      for metric in ("moe_batch_us", "background_p99_us")]
        secondary_p[baseline] = max(endpoint_p)
    secondary_adjusted = holm(secondary_p)
    secondary_pass = {
        baseline: bool(primary_pass and
                       secondary_adjusted[baseline] <= .05 and
                       all(changes["192"][baseline][metric]["median_change_pct"] <= -5
                           for metric in ("moe_batch_us", "background_p99_us")))
        for baseline in MODE_BASELINES[1:]
    }

    constraints = {}
    for level in (0, 64, 128):
        comparisons = {}
        pairs = compare([row for row in rows if row["background"] == level], "fecmp", level)
        metrics = ("moe_batch_us",) if level == 0 else (
            "moe_batch_us", "background_p99_us")
        for metric in metrics:
            values = [pair[metric + "_change_pct"] for pair in pairs]
            comparisons[metric] = {
                "median_change_pct": statistics.median(values),
                "range_change_pct": [min(values), max(values)],
                "seed_count_worse_than_plus_10pct": sum(value > 10 for value in values),
                "passes": statistics.median(values) <= 5 and sum(value > 10 for value in values) <= 4,
            }
        constraints[str(level)] = {"comparisons_vs_ecmp": comparisons,
                                  "passes": all(x["passes"] for x in comparisons.values())}

    output = {
        "evidence_level": "formal 24 independent demand seeds; inference applies to the frozen synthetic demand generator and ns-3 model",
        "protocol_sha256": sha(ROOT / "docs/research/ws25-v1fix-formal-protocol.md"),
        "plan_sha256": sha(ROOT / "docs/research/evidence/ws25-v1fix-formal-plan.json"),
        "source_sha": formal.SOURCE_SHA, "topology_sha256": formal.TOPO_SHA,
        "verified_cells": len(rows), "seeds": seeds, "paired_changes": changes,
        "primary_ecmp_192": {"metrics": primary, "passes": primary_pass},
        "secondary_holm_joint_p": secondary_p,
        "secondary_holm_adjusted_p": secondary_adjusted,
        "secondary_pass": secondary_pass,
        "lower_load_constraints": constraints,
        "overall_efficacy_gate": bool(primary_pass and all(constraint["passes"]
                                                          for constraint in constraints.values())),
        "cells": rows,
        "limits": {
            "independent_unit": "demand seed; within-seed levels and flows are not independent",
            "background_zero": "background P99 is not applicable at level 0",
            "cnp": "ECN/OoO source counters may overlap and do not count retransmissions",
            "uplink": "cumulative port bytes and imbalance are not business throughput or physical queue occupancy",
            "dynamic_baselines": "zero branch counter means the dynamic branch was not exercised",
        },
    }
    OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(json.dumps({"verified_cells": len(rows), "primary_pass": primary_pass,
                      "secondary_pass": secondary_pass,
                      "lower_load_constraints": constraints,
                      "output": str(OUTPUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
