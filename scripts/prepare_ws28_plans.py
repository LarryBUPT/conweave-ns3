#!/usr/bin/env python3
"""Freeze WS-28 tail-diagnostic and independent ablation cell identities."""
import argparse
import hashlib
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/research/evidence"
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path, data):
    encoded = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("frozen plan differs: " + str(path))
    path.write_text(encoded, encoding="utf-8")
    return sha(path)


def tail(source_sha):
    prior = json.loads((EVIDENCE / "ws28-existing-raw-analysis.json").read_text(encoding="utf-8"))
    old = {row["seed"]: row for row in prior["paired_seeds"]}
    seeds = (20262725, 20262729, 20262739)
    cells = []
    for seed in seeds:
        trace = "ws25_seed{}_b192.txt".format(seed)
        trace_sha = sha(ROOT / "config" / trace)
        if trace_sha != old[seed]["trace_sha256"]:
            raise RuntimeError("old demand trace changed: " + trace)
        for mode in ("fecmp", "classreserve"):
            for enabled in (0, 1):
                cells.append({
                    "id": "20261015-010000-ws28-tail-s{}-{}-d{}".format(seed, mode, enabled),
                    "seed": seed, "mode": mode, "diag": enabled,
                    "trace": trace, "trace_sha256": trace_sha,
                    "old_id": old[seed]["ecmp_id" if mode == "fecmp" else "classreserve_id"],
                    "expected_fct_sha256": old[seed]["fct_sha256"]["ecmp" if mode == "fecmp" else mode],
                    "input_flows": 16576, "expected_tags": {"1": 192, "2": 16384},
                    "run_order": len(cells) + 1, "batch": len(cells) + 1,
                })
    return {
        "kind": "WS-28 three-seed nonperturbing tail diagnostic",
        "source_sha": source_sha, "topology_sha256": TOPO_SHA,
        "ns3_seed": 1, "pfc": 0, "irn": 1, "bw_gbps": 400,
        "buffer_mib": 9, "simul_time": "0.01", "max_concurrent": 1,
        "window_ns": [2000000000, 2000025000], "row_limit": 20000,
        "cells": cells,
    }


def ablation(source_sha, cap):
    manifest = json.loads((EVIDENCE / "ws28-ablation-inputs.json").read_text(encoding="utf-8"))
    if manifest["background_levels"] != [192] or len(manifest["seeds"]) != 24:
        raise RuntimeError("ablation input manifest is incomplete")
    rng = random.Random(20262945)
    blocks = []
    modes = ("fecmp", "cr-a0-b0", "cr-a1-b0", "cr-a0-b1", "cr-a1-b1")
    for seed in range(20262921, 20262945):
        item = manifest["seeds"][str(seed)]["levels"]["192"]
        trace = item["file"]
        if item["flows"] != 16576 or sha(ROOT / "config" / trace) != item["sha256"]:
            raise RuntimeError("ablation trace changed: " + trace)
        block = [{
            "id": "20261015-020000-ws28-ablation-s{}-{}".format(seed, mode),
            "seed": seed, "background": 192, "mode": mode,
            "trace": trace, "trace_sha256": item["sha256"],
            "input_flows": 16576, "expected_tags": {"1": 192, "2": 16384},
        } for mode in modes]
        rng.shuffle(block)
        blocks.append(block)
    rng.shuffle(blocks)
    cells = [cell for block in blocks for cell in block]
    for index, cell in enumerate(cells, 1):
        cell["run_order"] = index
        cell["batch"] = (index - 1) // cap + 1
    return {
        "kind": "WS-28 independent-demand two-factor ablation",
        "source_sha": source_sha, "topology_sha256": TOPO_SHA,
        "input_manifest_sha256": sha(EVIDENCE / "ws28-ablation-inputs.json"),
        "demand_seeds": list(range(20262921, 20262945)),
        "modes": list(modes), "background_levels": [192],
        "randomization_seed": 20262945, "ns3_seed": 1,
        "pfc": 0, "irn": 1, "bw_gbps": 400, "buffer_mib": 9,
        "simul_time": "0.01", "max_concurrent": cap,
        "cells": cells,
    }


def technical(source_sha):
    trace = "ws25_v1fix_mixed8.txt"
    trace_sha = sha(ROOT / "config" / trace)
    modes = ("fecmp", "classreserve", "cr-a0-b0", "cr-a1-b0", "cr-a0-b1", "cr-a1-b1")
    return {
        "kind": "WS-28 six-arm technical correctness",
        "source_sha": source_sha, "topology_sha256": TOPO_SHA,
        "trace_sha256": trace_sha, "max_concurrent": 1,
        "ns3_seed": 1, "pfc": 0, "irn": 1,
        "cells": [{"id": "20261015-000010-ws28-technical-" + mode,
                   "mode": mode, "trace": trace, "trace_sha256": trace_sha,
                   "expected_tags": {"1": 4, "2": 4}}
                  for mode in modes],
    }


def resource(source_sha):
    trace = "ws25_seed20262501_b192.txt"
    trace_sha = sha(ROOT / "config" / trace)
    modes = ("cr-a0-b0", "cr-a1-b0", "cr-a0-b1", "cr-a1-b1")
    stages = (4, 8, 12)
    cells = []
    for cap in stages:
        for repeat in range(1, cap // len(modes) + 1):
            for mode in modes:
                cells.append({
                    "id": "20261015-000100-ws28-resource-c{:02d}-r{}-{}".format(cap, repeat, mode),
                    "mode": mode, "trace": trace, "trace_sha256": trace_sha,
                    "stage_cap": cap, "input_flows": 16576,
                    "expected_tags": {"1": 192, "2": 16384},
                })
    return {
        "kind": "WS-28 factorial mode resource pilot",
        "source_sha": source_sha, "topology_sha256": TOPO_SHA,
        "trace_sha256": trace_sha, "stages": list(stages),
        "minimum_mem_available_gib": 32, "minimum_free_gib": 100,
        "maximum_load_1m": 20, "maximum_tree_rss_mib": 32768,
        "cells": cells,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("tail", "technical", "resource", "ablation"))
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--cap", type=int, choices=(1, 2, 4, 8, 12, 16, 18), default=1)
    args = parser.parse_args()
    if len(args.source_sha) != 40 or any(c not in "0123456789abcdef" for c in args.source_sha):
        raise ValueError("source SHA must be a full lowercase Git commit")
    builders = {"tail": lambda: tail(args.source_sha),
                "technical": lambda: technical(args.source_sha),
                "resource": lambda: resource(args.source_sha),
                "ablation": lambda: ablation(args.source_sha, args.cap)}
    data = builders[args.kind]()
    path = EVIDENCE / ("ws28-{}-plan.json".format(args.kind))
    digest = write_once(path, data)
    print(json.dumps({"kind": args.kind, "cells": len(data["cells"]),
                      "source_sha": args.source_sha, "plan_sha256": digest}, sort_keys=True))


if __name__ == "__main__":
    main()
