#!/usr/bin/env python3
"""Run only the frozen 18-cell stage after the corrected 16-cell gate."""
import argparse
import json
from pathlib import Path

import run_ws25_resource_capacity as capacity
import run_ws25_resource_pilot as pilot
import run_ws25_v1fix_calibration as calibration

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/research/evidence/ws25-resource-capacity-analysis.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true", help="Validate identities and host without launching")
    args = parser.parse_args()
    plan = capacity.frozen_plan()
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    if not (audit["go_18"] and audit["source_sha"] == calibration.SOURCE_SHA and
            audit["metadata_throughput_ratio_16_over_12"] > 1.05):
        raise RuntimeError("Corrected 16-cell capacity gate is not open")
    stage18 = [cell for cell in plan["cells"] if cell["stage_cap"] == 18]
    if [cell["id"] for cell in stage18] != audit["cap18_planned_ids"]:
        raise RuntimeError("18-cell frozen IDs changed")
    summary = json.loads(capacity.SUMMARY.read_text(encoding="utf-8"))
    if len(summary["stages"]) != 1 or summary["stages"][0]["cap"] != 16:
        raise RuntimeError("Expected one verified 16-cell stage before 18-cell run")
    receipts = [json.loads(line) for line in pilot.RECEIPTS.read_text(encoding="utf-8").splitlines()
                if line]
    if any(row.get("event") == "started" and row.get("id") in audit["cap18_planned_ids"]
           for row in receipts):
        raise RuntimeError("An 18-cell ID has already started; inspect it before recovery")
    pilot.host_gate(reject_active=True)
    for cell in stage18:
        if (ROOT / "results" / cell["id"]).exists():
            raise RuntimeError("18-cell local results already exist: " + cell["id"])
        state = pilot.base.status(cell["id"])
        if state.get("status") != "BUILT" or state.get("git_commit") != calibration.SOURCE_SHA:
            raise RuntimeError("18-cell ID is not freshly built: " + cell["id"])
    if args.preflight:
        print(json.dumps({"ready_stage": 18, "built_ids": len(stage18),
                          "source_sha": calibration.SOURCE_SHA}, sort_keys=True))
        return
    pilot.POLL_SECONDS = 300
    result = pilot.run_stage(stage18, 18)
    summary["stages"].append(result)
    capacity.SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                                encoding="utf-8")
    print(json.dumps({"completed_stage": 18, "cells": result["cells"],
                      "resource_gate_passed": True}, sort_keys=True))


if __name__ == "__main__":
    main()
