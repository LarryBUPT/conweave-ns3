#!/usr/bin/env python3
"""Frozen 16/18-worker WS-25 capacity replay; never algorithm efficacy data."""
import argparse
import json
from pathlib import Path

import run_ws25_resource_pilot as pilot
import run_ws25_v1fix_calibration as calibration

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/research/evidence/ws25-resource-capacity-plan.json"
SUMMARY = ROOT / "results/ws25-resource-capacity-summary.json"
pilot.RECEIPTS = ROOT / "results/ws25-resource-capacity-receipts.jsonl"


def frozen_plan():
    originals = [cell for cell in calibration.cells() if cell["role"] == "primary"]
    if len(originals) != 24:
        raise RuntimeError("Expected 24 verified calibration cells")
    cells = []
    for cap, selected in ((16, originals[:16]), (18, originals[6:24])):
        for number, original in enumerate(selected, 1):
            cell = dict(original)
            cell["id"] = "20261003-220000-ws25-cap%02d-%02d-%s" % (cap, number, original["mode"])
            cell["original_id"] = original["id"]
            cell["stage_cap"] = cap
            cells.append(cell)
    expected = {
        "purpose": "16/18 capacity and deterministic replay only; no efficacy samples",
        "source_sha": calibration.SOURCE_SHA,
        "topology_sha256": calibration.TOPO_SHA,
        "stages": [16, 18], "cells": cells,
        "minimum_mem_available_gib": 32,
        "minimum_free_gib": 100, "maximum_load_1m": 20,
        "go_18_if": "16 throughput > 12 throughput by 5%, no failure, projected memory admission passes",
    }
    encoded = json.dumps(expected, indent=2, sort_keys=True) + "\n"
    if PLAN.exists():
        if PLAN.read_text(encoding="utf-8") != encoded:
            raise RuntimeError("Frozen capacity plan changed")
    else:
        PLAN.parent.mkdir(parents=True, exist_ok=True)
        PLAN.write_text(encoded, encoding="utf-8")
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("plan", "prebuild", "run", "verify"))
    args = parser.parse_args()
    plan = frozen_plan()
    cells = plan["cells"]
    if args.phase == "plan":
        print(json.dumps({"cells": len(cells), "stages": plan["stages"],
                          "source_sha": plan["source_sha"]}))
        return
    if args.phase == "prebuild":
        pilot.prebuild(cells)
        return
    if args.phase == "verify":
        verified = [pilot.finish_one(cell) if not (ROOT / "results" / cell["id"]).is_dir()
                    else calibration.verify(cell) for cell in cells
                    if pilot.base.status(cell["id"]).get("status") == "SUCCEEDED"]
        print(json.dumps({"verified_cells": len(verified)}))
        return
    baseline = json.loads(pilot.SUMMARY.read_text(encoding="utf-8"))["stages"][-1]
    if baseline["cap"] != 12:
        raise RuntimeError("12-worker throughput baseline missing")
    rows = []
    for cap in (16, 18):
        if cap == 18 and rows[-1]["throughput_cells_per_hour"] <= baseline["throughput_cells_per_hour"] * 1.05:
            pilot.receipt("capacity_stopped", reason="16_throughput_plateau", next_cap=18)
            break
        group = [cell for cell in cells if cell["stage_cap"] == cap]
        rows.append(pilot.run_stage(group, cap))
        SUMMARY.write_text(json.dumps({"purpose": plan["purpose"], "stages": rows},
                                      indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"completed_stages": [row["cap"] for row in rows]}, sort_keys=True))


if __name__ == "__main__":
    main()
