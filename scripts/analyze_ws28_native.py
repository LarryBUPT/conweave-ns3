#!/usr/bin/env python3
"""Recompute the WS-28 native comparison from 144 fixed raw cells."""
import argparse
import json
import random
import statistics
from pathlib import Path

from analyze_ws28_existing import change, digest, read_cell
from analyze_ws28_existing import percentile
import run_ws28_native as native


ROOT = Path(__file__).resolve().parents[1]
NATIVE_PLAN = ROOT / "docs/research/evidence/ws28-native-plan.json"
NATIVE_RECEIPT = ROOT / "docs/research/evidence/ws28-native-execution.json"
CONTROL_PLAN = ROOT / "docs/research/evidence/ws27-confirm-plan.json"
EXISTING = ROOT / "docs/research/evidence/ws28-existing-raw-analysis.json"
OUTPUT = ROOT / "docs/research/evidence/ws28-native-analysis.json"
SOURCE_SHA = "ee236f27920aa56b3dd562ed971e5abee9e1e659"
PLAN_SHA = "cce19b0bf30a05b94f56332165dd9aaedde5f202686bbc35a325cd20d4c417a5"
MODES = ("fecmp", "drill", "conga", "letflow", "conweave", "classreserve")
NATIVE = ("fecmp", "drill", "conga", "letflow", "conweave")
BOOTSTRAP_DRAWS = 10000
BOOTSTRAP_SEED = 20262828


def interval(values, seed):
    rng = random.Random(seed)
    draws = sorted(statistics.median(rng.choices(values, k=len(values)))
                   for _ in range(BOOTSTRAP_DRAWS))
    return [draws[int(.025 * BOOTSTRAP_DRAWS)],
            draws[int(.975 * BOOTSTRAP_DRAWS)]]


def check_metadata(base, cell, topology_sha):
    folder = base / cell["id"]
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = meta["parameters"]
    if not (meta["status"] == "SUCCEEDED" and meta["git_commit"] == SOURCE_SHA and
            meta["algorithm"] == cell["mode"] and meta["seed"] == 1 and
            meta["input_flow_sha256"] == cell["trace_sha256"] and
            meta["topology_sha256"] == topology_sha and
            params["flow_file"] == cell["trace"] and params["lb"] == cell["mode"] and
            params["topo"] == "topo_1280_400G_400G_OS1" and
            params["bw"] == 400 and params["buffer"] == 9 and
            params["simul_time"] == "0.01" and params["netload"] == 10 and
            params["pfc"] == 0 and params["irn"] == 1 and
            params["ws25_diag"] == 0 and meta["concurrency_cap"] == 12):
        raise ValueError("Metadata mismatch: " + cell["id"])
    if digest(folder / "config/topology.txt") != topology_sha:
        raise ValueError("Topology snapshot mismatch: " + cell["id"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-results", "--old-results", type=Path,
                        default=ROOT.parent / "ws27-guardhash-compare/results")
    parser.add_argument("--plan", type=Path, default=NATIVE_PLAN)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    native_plan = json.loads(args.plan.read_text(encoding="utf-8"))
    control_plan = json.loads(CONTROL_PLAN.read_text(encoding="utf-8"))
    receipt = json.loads(NATIVE_RECEIPT.read_text(encoding="utf-8"))
    existing = json.loads(EXISTING.read_text(encoding="utf-8"))
    existing_by_seed = {r["seed"]: r for r in existing["paired_seeds"]}
    if digest(args.plan) != PLAN_SHA:
        raise ValueError("Native plan hash changed")
    if (native_plan["source_sha"] != SOURCE_SHA or control_plan["source_sha"] != SOURCE_SHA or
            receipt["source_sha"] != SOURCE_SHA or not receipt["verified"] or
            native_plan["topology_sha256"] != control_plan["topology_sha256"]):
        raise ValueError("Frozen source, topology, or receipt mismatch")
    native_cells = {(c["seed"], c["mode"]): c for c in native_plan["cells"]}
    controls = {(c["seed"], c["mode"]): c for c in control_plan["cells"]
                if c["background"] == 192 and c["mode"] in ("fecmp", "classreserve")}
    receipts = {r["id"]: r for r in receipt["verified_cells"]}
    seeds = list(range(20262721, 20262745))
    if (len(native_cells) != 96 or len(controls) != 48 or len(receipts) != 96 or
            sorted(set(seed for seed, _ in native_cells)) != seeds or
            sorted(set(seed for seed, _ in controls)) != seeds):
        raise ValueError("Incomplete or duplicate plan/receipt rows")

    paired = []
    dynamic = {mode: [] for mode in ("conga", "letflow", "conweave")}
    native_engine = native.configure()
    for seed in seeds:
        cells = {}
        for mode in MODES:
            planned = controls[(seed, mode)] if mode in ("fecmp", "classreserve") else native_cells[(seed, mode)]
            base = args.control_results if mode in ("fecmp", "classreserve") else ROOT / "results"
            check_metadata(base, planned, native_plan["topology_sha256"])
            cell = read_cell(base, planned)
            if mode in ("fecmp", "classreserve"):
                cell["source"] = "ws27-confirm"
            else:
                row = receipts[planned["id"]]
                if native_engine.verify(planned) != row:
                    raise ValueError("Native branch/raw/resource verification changed: " + planned["id"])
                if (row["seed"] != seed or row["mode"] != mode or
                        row["trace_sha256"] != cell["trace_sha256"] or
                        row["fct_sha256"] != cell["fct_sha256"] or
                        abs(row["moe_batch_us"] - cell["batch_us"]) > 1e-6 or
                        abs(row["background_p99_us"] - cell["background_p99_us"]) > 1e-6 or
                        row["input_flows"] != 16576 or
                        row["resource"]["final_status"] != "SUCCEEDED"):
                    raise ValueError("Raw and native receipt disagree: " + planned["id"])
                cell["source"] = "ws28-native"
                if mode in dynamic:
                    dynamic[mode].append(row["native_dynamic"])
            cells[mode] = cell
        control = cells["fecmp"]
        prior = existing_by_seed[seed]
        if (prior["fct_sha256"]["ecmp"] != control["fct_sha256"] or
                prior["fct_sha256"]["classreserve"] != cells["classreserve"]["fct_sha256"] or
                abs(prior["moe_batch_us"]["ecmp"] - control["batch_us"]) > 1e-6 or
                abs(prior["moe_batch_us"]["classreserve"] -
                    cells["classreserve"]["batch_us"]) > 1e-6):
            raise ValueError("WS-27 raw differs from prior WS-28 diagnosis: " + str(seed))
        for mode, cell in cells.items():
            if (cell["trace_sha256"] != control["trace_sha256"] or
                    cell["moe"].keys() != control["moe"].keys() or
                    cell["background"].keys() != control["background"].keys()):
                raise ValueError("Unpaired input or flow identities: " + cell["id"])
        fastest_native = min(NATIVE, key=lambda mode: (cells[mode]["batch_us"], mode))
        for mode in MODES:
            cell = cells[mode]
            paired.append({
                "seed": seed, "mode": mode, "id": cell["id"],
                "source": cell["source"], "ecmp_id": control["id"],
                "trace_sha256": cell["trace_sha256"], "fct_sha256": cell["fct_sha256"],
                "moe_batch_us": cell["batch_us"],
                "moe_batch_change_vs_ecmp_pct": change(cell["batch_us"], control["batch_us"]),
                "moe_single_flow_p95_us": cell["moe_fct_p95_us"],
                "moe_single_flow_p95_change_vs_ecmp_pct":
                    change(cell["moe_fct_p95_us"], control["moe_fct_p95_us"]),
                "background_p99_us": cell["background_p99_us"],
                "background_p99_change_vs_ecmp_pct":
                    change(cell["background_p99_us"], control["background_p99_us"]),
                "fastest_native_mode": fastest_native,
            })

    effects = []
    for index, mode in enumerate(MODES):
        rows = [r for r in paired if r["mode"] == mode]
        batch = [r["moe_batch_change_vs_ecmp_pct"] for r in rows]
        bg = [r["background_p99_change_vs_ecmp_pct"] for r in rows]
        effects.append({
            "mode": mode, "demand_seeds": len(rows),
            "moe_batch_median_change_vs_ecmp_pct": statistics.median(batch),
            "moe_batch_bootstrap_95pct": interval(batch, BOOTSTRAP_SEED + index),
            "moe_batch_improved_seeds": sum(x < 0 for x in batch),
            "moe_batch_worsened_seeds": sum(x > 0 for x in batch),
            "moe_batch_change_range_pct": [min(batch), max(batch)],
            "moe_batch_p95_us": percentile([r["moe_batch_us"] for r in rows], 95),
            "moe_batch_p95_change_vs_ecmp_pct": change(
                percentile([r["moe_batch_us"] for r in rows], 95),
                percentile([r["moe_batch_us"] for r in paired if r["mode"] == "fecmp"], 95)),
            "moe_single_flow_p95_median_change_vs_ecmp_pct": statistics.median(
                r["moe_single_flow_p95_change_vs_ecmp_pct"] for r in rows),
            "background_p99_median_change_vs_ecmp_pct": statistics.median(bg),
            "background_p99_bootstrap_95pct": interval(bg, BOOTSTRAP_SEED + 100 + index),
            "background_p99_over_3pct_seeds": sum(x > 3 for x in bg),
            "background_constraint_pass": statistics.median(bg) < 3,
            "fastest_native_seeds": sum(r["fastest_native_mode"] == mode for r in rows),
            "fct_digest_distinct_from_ecmp_seeds": sum(
                r["fct_sha256"] != next(x["fct_sha256"] for x in paired
                                              if x["seed"] == r["seed"] and x["mode"] == "fecmp")
                for r in rows),
        })
    by_key = {(r["seed"], r["mode"]): r for r in paired}
    direct = []
    for index, mode in enumerate(NATIVE):
        batch = [change(by_key[(seed, "classreserve")]["moe_batch_us"],
                        by_key[(seed, mode)]["moe_batch_us"]) for seed in seeds]
        direct.append({"native_mode": mode,
                       "classreserve_moe_batch_median_change_pct": statistics.median(batch),
                       "bootstrap_95pct": interval(batch, BOOTSTRAP_SEED + 200 + index),
                       "classreserve_faster_seeds": sum(x < 0 for x in batch)})
    native_best = min((e for e in effects if e["mode"] in NATIVE),
                      key=lambda row: row["moe_batch_median_change_vs_ecmp_pct"])["mode"]
    gate_pass_best = min((e for e in effects if e["mode"] in NATIVE and
                          e["background_constraint_pass"]),
                         key=lambda row: row["moe_batch_median_change_vs_ecmp_pct"])["mode"]
    output = {
        "source_sha": SOURCE_SHA, "native_plan_sha256": PLAN_SHA,
        "control_plan_sha256": digest(CONTROL_PLAN),
        "native_execution_sha256": digest(NATIVE_RECEIPT),
        "topology_sha256": native_plan["topology_sha256"],
        "verified_raw_cells": len(paired), "native_cells": 96,
        "ecmp_control_cells": 24, "classreserve_cells": 24,
        "independent_unit": "synthetic demand seed; flows nested within seed",
        "bootstrap": {"draws": BOOTSTRAP_DRAWS, "seed": BOOTSTRAP_SEED,
                      "method": "resample demand seeds with replacement; percentile interval"},
        "background_gate": "median paired P99 FCT change versus same-input ECMP < +3%",
        "native_dynamic": dynamic,
        "ecmp_moe_batch_p95_us": percentile(
            [r["moe_batch_us"] for r in paired if r["mode"] == "fecmp"], 95),
        "fastest_native_by_median_paired_change": native_best,
        "fastest_gate_passing_native_by_median_paired_change": gate_pass_best,
        "effects": effects, "classreserve_vs_native": direct,
        "paired_seeds": paired,
    }
    encoded = json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and args.output.read_text(encoding="utf-8") != encoded:
        raise ValueError("Existing analysis differs: " + str(args.output))
    args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps({"verified_raw_cells": len(paired), "effects": effects,
                      "classreserve_vs_native": direct}, ensure_ascii=False))


if __name__ == "__main__":
    main()
