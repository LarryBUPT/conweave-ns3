#!/usr/bin/env python3
"""Audit capacity throughput from simulation timestamps, not controller polls."""
import datetime
import json
from collections import Counter
from pathlib import Path

import run_ws25_resource_capacity as capacity
import run_ws25_resource_pilot as pilot
import run_ws25_v1fix_calibration as calibration

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/research/evidence/ws25-resource-capacity-analysis.json"
RECOVERY = ROOT / "docs/research/evidence/ws25-resource-capacity-recovery-plan.json"
PILOT_RECEIPTS = ROOT / "results/ws25-resource-pilot-receipts.jsonl"
CAPACITY_RECEIPTS = ROOT / "results/ws25-resource-capacity-receipts.jsonl"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def utc(value):
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


def receipts(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def cohort(cells, cap, receipt_path, stored, original_cache):
    ids = [cell["id"] for cell in cells]
    events = receipts(receipt_path)
    stage_starts = [item for item in events if item.get("event") == "stage_start"
                    and item.get("cap") == cap and item.get("ids") == ids]
    if len(stage_starts) != 1:
        raise RuntimeError("Expected one exact stage-start receipt for cap %d" % cap)
    if stored["cap"] != cap or stored["cells"] != len(cells):
        raise RuntimeError("Stored stage count/cap mismatch")

    rows = []
    for cell in cells:
        result = calibration.verify(cell)
        original_id = cell["original_id"]
        if original_id not in original_cache:
            original = next(item for item in calibration.cells() if item["id"] == original_id)
            original_cache[original_id] = calibration.verify(original)
        if result["fct_sha256"] != original_cache[original_id]["fct_sha256"]:
            raise RuntimeError("Concurrent FCT replay differs: " + cell["id"])
        folder = ROOT / "results" / cell["id"]
        meta = load(folder / "metadata.json")
        if meta["concurrency_cap"] != cap or meta["status"] != "SUCCEEDED":
            raise RuntimeError("Capacity metadata status/cap differs: " + cell["id"])
        samples = receipts(folder / "logs/resource-samples.jsonl")
        if not samples or samples[-1]["status"] != "SUCCEEDED":
            raise RuntimeError("Capacity watcher did not finish: " + cell["id"])
        start, finish = utc(meta["started_utc"]), utc(meta["finished_utc"])
        if finish <= start:
            raise RuntimeError("Capacity metadata time order differs: " + cell["id"])
        rows.append({"id": cell["id"], "original_id": original_id,
                     "mode": cell["mode"], "seed": cell["seed"],
                     "source_sha": meta["git_commit"],
                     "trace_sha256": meta["input_flow_sha256"],
                     "topology_sha256": meta["topology_sha256"],
                     "fct_sha256": result["fct_sha256"],
                     "started_utc": meta["started_utc"],
                     "finished_utc": meta["finished_utc"],
                     "run_seconds": (finish-start).total_seconds(),
                     "resource_samples": len(samples),
                     "peak_tree_rss_mib": max(x["process_tree_rss_mib"] for x in samples),
                     "minimum_mem_available_gib": min(x["mem_available_gib"] for x in samples),
                     "minimum_free_gib": min(x["free_gib"] for x in samples),
                     "peak_load_1m": max(x["load_1m"] for x in samples)})

    first = min(utc(row["started_utc"]) for row in rows)
    last = max(utc(row["finished_utc"]) for row in rows)
    stage_start = utc(stage_starts[0]["utc"])
    first_to_last = (last-first).total_seconds()
    stage_to_last = (last-stage_start).total_seconds()
    runner_seconds = stored["wall_seconds"]
    if not (0 < first_to_last <= stage_to_last <= runner_seconds):
        raise RuntimeError("Capacity timing receipts are inconsistent")
    safety = {"maximum_tree_rss_mib": max(row["peak_tree_rss_mib"] for row in rows),
              "minimum_mem_available_gib": min(row["minimum_mem_available_gib"] for row in rows),
              "minimum_free_gib": min(row["minimum_free_gib"] for row in rows),
              "peak_load_1m": max(row["peak_load_1m"] for row in rows)}
    for key, value in safety.items():
        if abs(value-stored[key]) > 0.000001:
            raise RuntimeError("Stored resource metric differs for cap %d: %s" % (cap,key))
    if safety["minimum_mem_available_gib"] < 32 or safety["minimum_free_gib"] < 100 or safety["peak_load_1m"] > 20:
        raise RuntimeError("Capacity safety line failed")
    return {"cap": cap, "cells": len(cells), "first_started_utc": first.isoformat(),
            "last_finished_utc": last.isoformat(), "stage_started_utc": stage_start.isoformat(),
            "first_start_to_last_finish_seconds": first_to_last,
            "stage_start_to_last_finish_seconds": stage_to_last,
            "metadata_throughput_cells_per_hour": len(cells)*3600/first_to_last,
            "stage_receipt_throughput_cells_per_hour": len(cells)*3600/stage_to_last,
            "runner_wall_seconds": runner_seconds,
            "runner_throughput_cells_per_hour": stored["throughput_cells_per_hour"],
            "runner_polling_overhang_seconds": runner_seconds-stage_to_last,
            "minimum_full_overlap_seconds": (min(utc(row["finished_utc"]) for row in rows)-
                                             max(utc(row["started_utc"]) for row in rows)).total_seconds(),
            "modes": dict(Counter(row["mode"] for row in rows)),
            "unique_trace_count": len(set(row["trace_sha256"] for row in rows)),
            "safety": safety, "rows": rows}


def main():
    capacity_plan = capacity.frozen_plan()
    recovery = load(RECOVERY)
    local_recovery = load(ROOT / "results/ws25-resource-capacity-recovery-plan.json")
    if recovery != local_recovery:
        raise RuntimeError("Versioned and execution recovery plans differ")
    first = next(item for item in capacity_plan["cells"]
                 if item["id"] == recovery["original_single_cell_id"])
    replacement = dict(first)
    replacement["id"] = recovery["replacement_id"]
    expected16 = [item for item in capacity_plan["cells"]
                  if item["stage_cap"] == 16 and item["id"] != first["id"]] + [replacement]
    if [item["id"] for item in expected16] != recovery["stage16_ids"]:
        raise RuntimeError("Recovery cohort differs from its frozen IDs")

    original_cache = {}
    first_result = calibration.verify(first)
    first_original = next(item for item in calibration.cells() if item["id"] == first["original_id"])
    if first_result["fct_sha256"] != calibration.verify(first_original)["fct_sha256"]:
        raise RuntimeError("Standalone first cell changed FCT fingerprint")
    pilot_plan = pilot.frozen_plan()
    pilot_summary = load(pilot.SUMMARY)
    twelve = cohort([item for item in pilot_plan["cells"] if item["stage_cap"] == 12],
                    12, PILOT_RECEIPTS, pilot_summary["stages"][-1], original_cache)
    capacity_summary = load(capacity.SUMMARY)
    sixteen = cohort(expected16, 16, CAPACITY_RECEIPTS,
                     capacity_summary["stages"][0], original_cache)
    expected18 = [item for item in capacity_plan["cells"] if item["stage_cap"] == 18]
    if len(capacity_summary["stages"]) != 2 or capacity_summary["stages"][1]["cap"] != 18:
        raise RuntimeError("Expected completed 18-cell stage after verified 16-cell stage")
    eighteen = cohort(expected18, 18, CAPACITY_RECEIPTS,
                      capacity_summary["stages"][1], original_cache)
    if not sixteen["minimum_full_overlap_seconds"] > 0:
        raise RuntimeError("16-cell cohort never ran concurrently")
    if not eighteen["minimum_full_overlap_seconds"] > 0:
        raise RuntimeError("18-cell cohort never ran concurrently")
    ratio = (sixteen["metadata_throughput_cells_per_hour"] /
             twelve["metadata_throughput_cells_per_hour"])
    if not ratio > 1.05:
        raise RuntimeError("Corrected 16-cell throughput did not meet 18-cell gate")
    cap18_ids = [item["id"] for item in capacity_plan["cells"] if item["stage_cap"] == 18]
    events = receipts(CAPACITY_RECEIPTS)
    started18 = sorted({item.get("id") for item in events
                        if item.get("event") == "started" and item.get("id") in cap18_ids})
    throughput_ratio_18_over_16 = (eighteen["metadata_throughput_cells_per_hour"] /
                                    sixteen["metadata_throughput_cells_per_hour"])
    selected_cap = 18 if throughput_ratio_18_over_16 > 1.05 else 16
    output = {"purpose": capacity_plan["purpose"], "source_sha": capacity_plan["source_sha"],
              "topology_sha256": capacity_plan["topology_sha256"],
              "standalone_original_first_id": first["id"],
              "standalone_original_first_fct_sha256": first_result["fct_sha256"],
              "stages": {"12": twelve, "16": sixteen, "18": eighteen},
              "metadata_throughput_ratio_16_over_12": ratio,
              "stage_receipt_throughput_ratio_16_over_12":
                  sixteen["stage_receipt_throughput_cells_per_hour"] /
                  twelve["stage_receipt_throughput_cells_per_hour"],
              "go_18_threshold_ratio": 1.05, "go_18": True,
              "metadata_throughput_ratio_18_over_16": throughput_ratio_18_over_16,
              "selected_cap": selected_cap,
              "cap18_planned_ids": cap18_ids, "cap18_started_receipt_ids": started18,
              "recovery_plan": "docs/research/evidence/ws25-resource-capacity-recovery-plan.json"}
    OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"12_metadata_throughput": twelve["metadata_throughput_cells_per_hour"],
                      "16_metadata_throughput": sixteen["metadata_throughput_cells_per_hour"],
                      "18_metadata_throughput": eighteen["metadata_throughput_cells_per_hour"],
                      "18_over_16_ratio": throughput_ratio_18_over_16,
                      "selected_cap": selected_cap,
                      "ratio": ratio, "go_18": True,
                      "cap18_started_receipts": len(started18)}, sort_keys=True))


if __name__ == "__main__":
    main()
