#!/usr/bin/env python3
"""Resource and deterministic-replay pilot for four native WS-28 modes."""
import argparse
import datetime
import json
import time
from pathlib import Path

import run_ws28_native as native


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/research/evidence/ws28-native-resource-plan.json"
SUMMARY = ROOT / "results/ws28-native-resource-summary.json"
RECEIPTS = ROOT / "results/ws28-native-resource-receipts.jsonl"
STAGES = (4, 8, 12)
TRACE = "ws25_seed20262501_b192.txt"
TRACE_SHA = "9791006f71843ea74b044396f6ae112ea8340aa9781cf0d267876e0940b02f48"


def stage_config(engine, cap):
    engine.MAX_CONCURRENT = cap
    engine.RECEIPTS = RECEIPTS
    engine.pilot.RECEIPTS = RECEIPTS
    engine.pilot.POLL_SECONDS = 120


def frozen_plan(engine):
    if engine.sha(ROOT / "config" / TRACE) != TRACE_SHA:
        raise RuntimeError("Resource calibration trace changed")
    cells = []
    for cap in STAGES:
        for repeat in range(1, cap // len(native.MODES) + 1):
            for mode in native.MODES:
                cells.append({"id": f"20261014-000000-ws28-nr-c{cap:02d}-r{repeat}-{mode}",
                              "seed": 20262501, "background": 192, "mode": mode,
                              "trace": TRACE, "trace_sha256": TRACE_SHA,
                              "input_flows": 16576, "expected_tags": {"1": 192, "2": 16384},
                              "role": "resource_only", "run_order": len(cells) + 1,
                              "batch": STAGES.index(cap) + 1, "stage_cap": cap})
    plan = {"kind": "WS-28 native resource and deterministic replay",
            "source_sha": native.SOURCE_SHA, "trace_sha256": TRACE_SHA,
            "topology_sha256": native.prior.TOPO_SHA,
            "stages": list(STAGES), "minimum_mem_available_gib": 32,
            "minimum_free_gib": 100, "maximum_load_1m": 20,
            "maximum_tree_rss_mib": 32768, "cells": cells}
    encoded = json.dumps(plan, indent=2, sort_keys=True) + "\n"
    if PLAN.exists() and PLAN.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("Frozen WS-28 resource plan changed")
    PLAN.write_text(encoded, encoding="utf-8")
    return plan


def verified_stage(engine, cells, cap):
    stage_config(engine, cap)
    rows = [engine.verify(cell) for cell in cells]
    if len(rows) != cap:
        raise RuntimeError("Resource stage incomplete")
    return rows


def run(engine, plan):
    empty = {"kind": plan["kind"], "source_sha": native.SOURCE_SHA, "stages": []}
    saved = (json.loads(SUMMARY.read_text(encoding="utf-8")) if SUMMARY.exists() else empty)
    if saved.get("kind") != empty["kind"] or saved.get("source_sha") != native.SOURCE_SHA:
        raise RuntimeError("Resource summary header changed")
    if [row["cap"] for row in saved["stages"]] != list(STAGES[:len(saved["stages"])]):
        raise RuntimeError("Resource summary is not a stage prefix")
    if "selected_cap" in saved:
        return saved
    for index, cap in enumerate(STAGES):
        cells = [cell for cell in plan["cells"] if cell["stage_cap"] == cap]
        if index < len(saved["stages"]):
            rows = verified_stage(engine, cells, cap)
            hashes = {mode: sorted({r["fct_sha256"] for r in rows if r["mode"] == mode})
                      for mode in native.MODES}
            if hashes != saved["stages"][index]["fct_sha256_by_mode"]:
                raise RuntimeError("Saved resource raw changed")
            continue
        stage_config(engine, cap)
        started = time.monotonic()
        resource, rows = engine.run_batch(cells, index + 1, len(STAGES))
        metadata = [json.loads((ROOT / "results" / cell["id"] / "metadata.json")
                               .read_text(encoding="utf-8")) for cell in cells]
        first = min(datetime.datetime.fromisoformat(m["started_utc"].replace("Z", "+00:00"))
                    for m in metadata)
        last = max(datetime.datetime.fromisoformat(m["finished_utc"].replace("Z", "+00:00"))
                   for m in metadata)
        simulation_wall = (last - first).total_seconds()
        if simulation_wall <= 0:
            raise RuntimeError("Invalid simulation wall time")
        hashes = {mode: sorted({r["fct_sha256"] for r in rows if r["mode"] == mode})
                  for mode in native.MODES}
        if any(len(items) != 1 for items in hashes.values()):
            raise RuntimeError("Nondeterministic native mode within stage")
        if saved["stages"] and hashes != saved["stages"][0]["fct_sha256_by_mode"]:
            raise RuntimeError("Native FCT fingerprint changed with concurrency")
        row = {"cap": cap, "cells": len(rows), "resource": resource,
               "controller_wall_seconds": round(time.monotonic() - started, 3),
               "simulation_wall_seconds": simulation_wall,
               "throughput_cells_per_hour": cap * 3600 / simulation_wall,
               "fct_sha256_by_mode": hashes}
        saved["stages"].append(row)
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(json.dumps(saved, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"verified_cap": cap, "throughput_cells_per_hour":
                          row["throughput_cells_per_hour"], "resource": resource}), flush=True)
        if len(saved["stages"]) >= 2:
            previous = saved["stages"][-2]["throughput_cells_per_hour"]
            if row["throughput_cells_per_hour"] <= previous * 1.05:
                saved["selected_cap"] = saved["stages"][-2]["cap"]
                saved["plateau_at_cap"] = cap
                SUMMARY.write_text(json.dumps(saved, indent=2, sort_keys=True) + "\n",
                                   encoding="utf-8")
                break
    if "selected_cap" not in saved and len(saved["stages"]) == len(STAGES):
        saved["selected_cap"] = STAGES[-1]
        SUMMARY.write_text(json.dumps(saved, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    return saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("plan", "run", "verify"))
    args = parser.parse_args()
    engine = native.configure()
    plan = frozen_plan(engine)
    if args.phase == "plan":
        print(json.dumps({"cells": len(plan["cells"]), "stages": STAGES,
                          "source_sha": native.SOURCE_SHA}))
    elif args.phase == "run":
        run(engine, plan)
    else:
        rows = [row for cap in STAGES for row in verified_stage(
            engine, [cell for cell in plan["cells"] if cell["stage_cap"] == cap], cap)]
        print(json.dumps({"verified_cells": len(rows)}))


if __name__ == "__main__":
    main()
