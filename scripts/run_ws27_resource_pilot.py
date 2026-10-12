#!/usr/bin/env python3
"""Measure WS-27 four-arm throughput at concurrency 4, 8, and 12."""
import argparse
import datetime
import json
import time
from pathlib import Path

import run_ws25_formal as engine
import run_ws27_matrix as matrix

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/research/evidence/ws27-resource-pilot-plan.json"
SUMMARY = ROOT / "results/ws27-resource-pilot-summary.json"
STAGES = (4, 8, 12)
MODES = ("fecmp", "classreserve", "guardhash-v2", "harmgate-v2")
SOURCE_SHA = "ee236f27920aa56b3dd562ed971e5abee9e1e659"
TRACE = "ws25_seed20262501_b192.txt"
TRACE_SHA = "9791006f71843ea74b044396f6ae112ea8340aa9781cf0d267876e0940b02f48"
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"


def configure(cap):
    engine.SOURCE_SHA = SOURCE_SHA
    engine.TOPO_SHA = TOPO_SHA
    engine.MAX_CONCURRENT = cap
    engine.RECEIPTS = ROOT / "results/ws27-resource-pilot-receipts.jsonl"
    engine.pilot.POLL_SECONDS = 120


def frozen_plan():
    if engine.sha(ROOT / "config" / TRACE) != TRACE_SHA:
        raise RuntimeError("Resource pilot trace changed")
    cells = []
    order = 0
    for cap in STAGES:
        for repeat in range(cap // len(MODES)):
            for mode in MODES:
                order += 1
                cells.append({
                    "id": "20261013-020000-ws27-rpilot-c%02d-r%d-%s" %
                          (cap, repeat + 1, mode),
                    "seed": 20262501, "background": 192, "mode": mode,
                    "trace": TRACE, "trace_sha256": TRACE_SHA,
                    "input_flows": 16576,
                    "expected_tags": {"1": 192, "2": 16384},
                    "role": "resource_only", "run_order": order,
                    "batch": STAGES.index(cap) + 1, "stage_cap": cap,
                })
    plan = {"purpose": "resource and deterministic replay; not efficacy evidence",
            "source_sha": SOURCE_SHA, "trace_sha256": TRACE_SHA,
            "topology_sha256": TOPO_SHA, "stages": list(STAGES),
            "minimum_mem_available_gib": 32, "minimum_free_gib": 100,
            "maximum_load_1m": 20, "maximum_tree_rss_mib": 32768,
            "cells": cells}
    encoded = json.dumps(plan, indent=2, sort_keys=True) + "\n"
    if PLAN.exists() and PLAN.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("Frozen WS-27 resource plan changed")
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    PLAN.write_text(encoded, encoding="utf-8")
    return plan


def verify_stage(cells, cap):
    configure(cap)
    rows = [engine.verify(cell) for cell in cells]
    if len(rows) != cap:
        raise RuntimeError("Incomplete resource stage")
    return rows


def run():
    plan = frozen_plan()
    saved = ({"purpose": plan["purpose"], "source_sha": SOURCE_SHA,
              "stages": []} if not SUMMARY.exists() else
             json.loads(SUMMARY.read_text(encoding="utf-8")))
    if saved.get("source_sha") != SOURCE_SHA or saved.get("purpose") != plan["purpose"]:
        raise RuntimeError("Resource pilot summary identity changed")
    completed = saved["stages"]
    if [row["cap"] for row in completed] != list(STAGES[:len(completed)]):
        raise RuntimeError("Resource pilot summary is not a stage prefix")
    for index, cap in enumerate(STAGES):
        cells = [cell for cell in plan["cells"] if cell["stage_cap"] == cap]
        if index < len(completed):
            previous = verify_stage(cells, cap)
            hashes = {mode: sorted({r["fct_sha256"] for r in previous
                                   if r["mode"] == mode}) for mode in MODES}
            if hashes != completed[index].get("fct_sha256_by_mode"):
                raise RuntimeError("Saved resource stage differs from raw results")
            continue
        configure(cap)
        started = time.monotonic()
        batch, rows = engine.run_batch(cells, index + 1, len(STAGES))
        elapsed = time.monotonic() - started
        metadata = [json.loads((ROOT / "results" / cell["id"] / "metadata.json")
                               .read_text(encoding="utf-8")) for cell in cells]
        first_start = min(datetime.datetime.fromisoformat(meta["started_utc"].replace("Z", "+00:00"))
                          for meta in metadata)
        last_finish = max(datetime.datetime.fromisoformat(meta["finished_utc"].replace("Z", "+00:00"))
                          for meta in metadata)
        simulation_wall = (last_finish - first_start).total_seconds()
        if simulation_wall <= 0:
            raise RuntimeError("Invalid resource pilot run timestamps")
        row = {"cap": cap, "cells": len(rows),
               "controller_wall_seconds": round(elapsed, 3),
               "simulation_wall_seconds": simulation_wall,
               "throughput_cells_per_hour": len(rows) * 3600 / simulation_wall,
               "resource": batch,
               "fct_sha256_by_mode": {mode: sorted({r["fct_sha256"] for r in rows
                                                   if r["mode"] == mode})
                                     for mode in MODES}}
        if any(len(hashes) != 1 for hashes in row["fct_sha256_by_mode"].values()):
            raise RuntimeError("Nondeterministic replay within resource stage")
        if completed and row["fct_sha256_by_mode"] != completed[0]["fct_sha256_by_mode"]:
            raise RuntimeError("Concurrency changed FCT fingerprints")
        completed.append(row)
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(json.dumps(saved, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
        print(json.dumps({"verified_cap": cap, "cells": len(rows),
                          "throughput_cells_per_hour": row["throughput_cells_per_hour"],
                          "resource": batch}, sort_keys=True), flush=True)
    return saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("plan", "run", "verify"))
    args = parser.parse_args()
    matrix.configure("screen")
    plan = frozen_plan()
    if args.phase == "plan":
        print(json.dumps({"cells": len(plan["cells"]), "stages": STAGES,
                          "source_sha": SOURCE_SHA}, sort_keys=True))
    elif args.phase == "run":
        run()
    else:
        for cap in STAGES:
            cells = [cell for cell in plan["cells"] if cell["stage_cap"] == cap]
            verify_stage(cells, cap)
        print(json.dumps({"verified_cells": len(plan["cells"])}, sort_keys=True))


if __name__ == "__main__":
    main()
