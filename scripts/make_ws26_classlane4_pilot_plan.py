#!/usr/bin/env python3
"""Freeze the independent ClassLane v4 pilot cells and demand hashes."""

import hashlib
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/research/evidence/ws26-classlane4-pilot-plan-r2.json"
SOURCE_SHA = "41384701c865082655cdea9a9e64daae74f51327"
TOPOLOGY = "topo_1280_400G_400G_OS1"
TOPOLOGY_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
ID_PREFIX = "20261009-031000-ws26v4p1r2"
SEEDS = [20262694, 20262695, 20262696, 20262697]
HIGH_ARMS = ["fecmp", "drill", "conga", "letflow", "conweave", "classlane4"]
LOW_ARMS = ["fecmp", "classlane4"]
RANDOMIZATION_SEED = 2026100901


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main():
    if digest(ROOT / "config" / (TOPOLOGY + ".txt")) != TOPOLOGY_SHA:
        raise RuntimeError("Frozen topology hash changed")

    inputs = {}
    for seed in SEEDS:
        for background in (0, 64, 128, 192):
            name = "ws26_seed%d_b%d.txt" % (seed, background)
            path = ROOT / "config" / name
            lines = path.read_text(encoding="ascii").splitlines()
            expected = 16384 + background
            if int(lines[0]) != expected or len(lines) - 1 != expected:
                raise RuntimeError("Unexpected flow count in " + name)
            inputs[seed, background] = {
                "trace": name,
                "trace_sha256": digest(path),
                "expected_flows": expected,
            }

    rng = random.Random(RANDOMIZATION_SEED)
    high_seeds = list(SEEDS)
    rng.shuffle(high_seeds)
    cells = []

    def add(stage, seed, background, mode, diag=0):
        suffix = "s%d-b%d-%s%s" % (
            seed % 100, background, mode, "-diag" if diag else "")
        cell = {
            "id": ID_PREFIX + "-" + suffix,
            "stage": stage,
            "order": len(cells) + 1,
            "seed": seed,
            "background": background,
            "mode": mode,
            "ws25_diag": diag,
            "pfc": 1,
            "irn": 1,
            "ns3_seed": 1,
            "netload": 10,
            "simul_time": "0.01",
            "topology": TOPOLOGY,
            "bw_gbps": 400,
            "buffer_mib": 9,
        }
        cell.update(inputs[seed, background])
        cells.append(cell)

    for seed in high_seeds:
        arms = list(HIGH_ARMS)
        rng.shuffle(arms)
        for mode in arms:
            add("high", seed, 192, mode)
            if mode == "classlane4":
                add("high", seed, 192, mode, 1)

    low_seeds = list(SEEDS)
    rng.shuffle(low_seeds)
    for seed in low_seeds:
        backgrounds = [0, 64, 128]
        rng.shuffle(backgrounds)
        for background in backgrounds:
            arms = list(LOW_ARMS)
            rng.shuffle(arms)
            for mode in arms:
                add("conditional_low", seed, background, mode)

    high_count = sum(cell["stage"] == "high" for cell in cells)
    low_count = sum(cell["stage"] == "conditional_low" for cell in cells)
    if (len(cells) != 52 or len({cell["id"] for cell in cells}) != 52 or
            high_count != 28 or low_count != 24):
        raise RuntimeError("Expected 28 high and 24 conditional low cells")

    plan = {
        "design": "four independent demand seeds; paired arms within seed",
        "purpose": "candidate screening only; not formal efficacy evidence",
        "revision": "r2",
        "supersedes_plan": "docs/research/evidence/ws26-classlane4-pilot-plan.json",
        "revision_reason": "Remove the ClassReserve v3-only with_background gate; use the ClassLane v4 dual effect screen.",
        "source_sha": SOURCE_SHA,
        "topology": TOPOLOGY,
        "topology_sha256": TOPOLOGY_SHA,
        "seeds": SEEDS,
        "randomization_seed": RANDOMIZATION_SEED,
        "high_stage_gate": {
            "metrics": ["moe_batch_completion_time", "background_fct_p99"],
            "paired_change_percent": "100 * (classlane4 / fecmp - 1)",
            "median_each_metric_max_percent": -3.0,
            "strict_improvement_min_seeds_each_metric": 3,
            "seed_count": 4,
            "both_metrics_required": True,
            "zero_is_strict_improvement": False,
        },
        "mechanism_diagnostics": {
            "report_counters": ["background_packets", "moe_packets",
                                "background_qp_new", "moe_qp_new",
                                "background_qp_reused", "moe_qp_reused",
                                "background_diverted", "moe_diverted",
                                "fallback", "missing_destination", "inconsistent",
                                "queue_violations"],
            "report": ["per_qp_paths", "per_switch_destination_tor_class_ports",
                       "queue_conservation"],
            "additional_seed_threshold": None,
        },
        "conditional_low_stage_gate": {
            "start_only_after_high_stage_effect_gate_pass": True,
            "background_levels": [0, 64, 128],
            "arms": LOW_ARMS,
            "paired_median_max_deterioration_percent": 5.0,
            "deterioration_over_10_percent_max_seeds": 1,
            "seed_count": 4,
            "background_p99_at_zero_background": "not_applicable",
        },
        "resource_limits": {
            "cap": 1,
            "peak_tree_rss_mib_max": 32768,
            "minimum_mem_available_gib": 32,
            "minimum_free_disk_gib": 100,
            "sample_load_1m_max": 20,
            "watcher_sample_required_before_each_run": True,
        },
        "acceptance": [
            "Audit every ID and remote result directory before build; never overwrite raw data.",
            "Use fixed source SHA and verify trace, topology, parameters, and complete flow identity.",
            "Require every input QP to complete exactly once before calculating a performance value.",
            "For ClassLane, verify QP path stability, per-tag packet counts, route counters, and queue byte conservation.",
            "Require a terminal resource receipt and watcher sample for each run.",
            "Keep conditional low-stage IDs unstarted unless both high-stage effect gates pass.",
            "Stop new runs on any correctness, identity, or resource failure; preserve the run and raw data.",
        ],
        "cells": cells,
    }
    rendered = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text(encoding="utf-8") != rendered:
            raise RuntimeError("Frozen plan exists and differs; refusing to replace it")
    else:
        OUTPUT.write_text(rendered, encoding="utf-8")
    print(json.dumps({"plan": str(OUTPUT), "cells": len(cells),
                      "high": high_count, "conditional_low": low_count,
                      "source_sha": SOURCE_SHA}, sort_keys=True))


if __name__ == "__main__":
    main()
