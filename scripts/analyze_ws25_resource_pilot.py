#!/usr/bin/env python3
"""Recompute WS-25 resource pilot evidence from fetched per-ID raw receipts."""
import datetime
import json
from collections import Counter
from pathlib import Path

import run_ws25_resource_pilot as pilot
import run_ws25_v1fix_calibration as calibration

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/research/evidence/ws25-resource-pilot-analysis.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def utc(value):
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


def main():
    plan = pilot.frozen_plan()
    cells = plan["cells"]
    saved = load(pilot.SUMMARY)
    receipts = [json.loads(line) for line in pilot.RECEIPTS.read_text(encoding="utf-8").splitlines() if line]
    events = Counter(row["event"] for row in receipts)
    if events != {"built": 24, "started": 24, "verified": 24,
                  "stage_start": 3, "stage_verified": 3}:
        raise RuntimeError("Pilot event counts differ from frozen 24-cell plan: " + repr(events))
    originals = {row["id"]: row for row in calibration.verify_matrix(calibration.cells())["cells"]}
    by_cap = {cap: [] for cap in pilot.STAGES}
    rows = []
    for cell in cells:
        result = calibration.verify(cell)
        original = originals[cell["original_id"]]
        if result["fct_sha256"] != original["fct_sha256"]:
            raise RuntimeError("FCT replay differs: " + cell["id"])
        folder = ROOT / "results" / cell["id"]
        meta = load(folder / "metadata.json")
        if meta["status"] != "SUCCEEDED" or meta["concurrency_cap"] != cell["stage_cap"]:
            raise RuntimeError("Pilot metadata status/cap mismatch: " + cell["id"])
        samples = [json.loads(line) for line in
                   (folder / "logs/resource-samples.jsonl").read_text(encoding="utf-8").splitlines() if line]
        row = {"id": cell["id"], "original_id": cell["original_id"],
               "cap": cell["stage_cap"], "mode": cell["mode"], "seed": cell["seed"],
               "source_sha": meta["git_commit"], "trace_sha256": meta["input_flow_sha256"],
               "fct_sha256": result["fct_sha256"], "start_utc": meta["started_utc"],
               "finish_utc": meta["finished_utc"],
               "peak_tree_rss_mib": max(point["process_tree_rss_mib"] for point in samples),
               "minimum_mem_available_gib": min(point["mem_available_gib"] for point in samples),
               "minimum_free_gib": min(point["free_gib"] for point in samples),
               "peak_load_1m": max(point["load_1m"] for point in samples),
               "samples": len(samples)}
        rows.append(row)
        by_cap[cell["stage_cap"]].append(row)
    stages = []
    for stored in saved["stages"]:
        cap = stored["cap"]
        group = by_cap[cap]
        if len(group) != cap:
            raise RuntimeError("Pilot stage cell count mismatch: " + str(cap))
        metrics = {"maximum_tree_rss_mib": max(r["peak_tree_rss_mib"] for r in group),
                   "minimum_mem_available_gib": min(r["minimum_mem_available_gib"] for r in group),
                   "minimum_free_gib": min(r["minimum_free_gib"] for r in group),
                   "peak_load_1m": max(r["peak_load_1m"] for r in group)}
        for key, value in metrics.items():
            if abs(value - stored[key]) > 0.000001:
                raise RuntimeError("Stored pilot stage metric differs: %s cap=%d" % (key, cap))
        if abs(stored["throughput_cells_per_hour"] - cap * 3600 / stored["wall_seconds"]) > 0.000001:
            raise RuntimeError("Stored pilot throughput arithmetic differs: " + str(cap))
        raw_wall = (max(utc(r["finish_utc"]) for r in group) -
                    min(utc(r["start_utc"]) for r in group)).total_seconds()
        # The runner starts its wall clock before the first remote launch and
        # detects the last terminal state after its polling interval.
        if not raw_wall <= stored["wall_seconds"] <= raw_wall + 60:
            raise RuntimeError("Stage wall time incompatible with metadata: " + str(cap))
        stages.append({**stored, "metadata_first_start_to_last_finish_seconds": raw_wall,
                       "margin_above_32_gib": stored["minimum_mem_available_gib"] - 32})
    output = {"source_sha": plan["source_sha"], "topology_sha256": plan["topology_sha256"],
              "verified_cells": len(rows), "all_replays_identical": True,
              "receipt_event_counts": dict(events), "stages": stages, "cells": rows}
    OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verified_cells": len(rows), "stages": stages}, sort_keys=True))


if __name__ == "__main__":
    main()
