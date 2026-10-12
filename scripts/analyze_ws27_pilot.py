#!/usr/bin/env python3
"""Recompute the four-arm WS-27 192-background engineering pilot from raw data."""
import json
import re
from pathlib import Path

import analyze_moe_tags

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/research/evidence/ws27-b192-pilot-analysis.json"
SOURCE_SHA = "592211afe90dcc056051941a924480c1b4a876a2"
TRACE_SHA = "9791006f71843ea74b044396f6ae112ea8340aa9781cf0d267876e0940b02f48"
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
IDS = {
    "fecmp": "20261013-013000-ws27-fecmp-b192-pilot",
    "classreserve": "20261013-013001-ws27-classreserve-b192-pilot",
    "guardhash-v2": "20261013-013002-ws27-guard-b192-pilot",
    "harmgate-v2": "20261013-011000-ws27-harm-b192-pilot",
}


def counters(log, prefix):
    lines = [line for line in log.splitlines() if line.startswith(prefix)]
    if len(lines) != 1:
        raise RuntimeError("Missing or ambiguous " + prefix)
    return {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", lines[0])}


def verify(mode, experiment_id):
    folder = ROOT / "results" / experiment_id
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = meta["parameters"]
    if not (meta["status"] == "SUCCEEDED" and meta["git_commit"] == SOURCE_SHA and
            meta["algorithm"] == mode and meta["seed"] == 1 and
            meta["input_flow_sha256"] == TRACE_SHA and
            meta["topology_sha256"] == TOPO_SHA and
            params["flow_file"] == "ws25_seed20262501_b192.txt" and
            params["lb"] == mode and params["pfc"] == 0 and params["irn"] == 1 and
            params["bw"] == 400 and params["buffer"] == 9 and
            params["ws25_diag"] == 0):
        raise RuntimeError("Pilot metadata mismatch: " + experiment_id)
    if (analyze_moe_tags.sha256(folder / "config/traffic_trace.txt") != TRACE_SHA or
            analyze_moe_tags.sha256(folder / "config/topology.txt") != TOPO_SHA):
        raise RuntimeError("Pilot input snapshot mismatch: " + experiment_id)
    summary = analyze_moe_tags.summarize(experiment_id)
    tags = summary["tags"]
    if {tag: row["input_flows"] for tag, row in tags.items()} != {"1": 192, "2": 16384}:
        raise RuntimeError("Pilot tag counts differ: " + experiment_id)
    if any(row["completed_flows"] != row["input_flows"] for row in tags.values()):
        raise RuntimeError("Pilot has unfinished flows: " + experiment_id)
    log = (folder / "logs/config.log").read_text(encoding="utf-8", errors="replace")
    diagnostic = None
    if mode in ("guardhash-v2", "harmgate-v2"):
        diagnostic = counters(log, "WS27_GUARD ")
        if not (diagnostic["mode"] == (23 if mode == "guardhash-v2" else 24) and
                diagnostic["queue_violations"] == 0 and
                diagnostic["new_flows"] > 0 and diagnostic["reused_packets"] > 0 and
                diagnostic["moe_packets"] == diagnostic["new_flows"] +
                diagnostic["reused_packets"]):
            raise RuntimeError("Pilot cache/queue invariant failed: " + experiment_id)
    if mode == "classreserve":
        diagnostic = counters(log, "WS25_CLASSRESERVE ")
        queue = counters(log, "WS25_QUEUE ")
        if not (diagnostic["queue_violations"] == 0 and
                queue["enqueued"] == queue["dequeued"] and
                queue["current"] == queue["queued_drop"] == 0):
            raise RuntimeError("ClassReserve queue invariant failed: " + experiment_id)
    raw = folder / "raw" / str(meta["raw_directory"])
    for suffix in ("_out_fct.txt", "_out_cnp.txt", "_out_pfc.txt", "_out_uplink.txt"):
        matches = list(raw.glob("*" + suffix))
        if len(matches) != 1 or matches[0].is_symlink():
            raise RuntimeError("Pilot raw file missing: " + suffix)
    resources = json.loads((folder / "logs/resource-summary.json").read_text(encoding="utf-8"))
    samples = [json.loads(line) for line in
               (folder / "logs/resource-samples.jsonl").read_text(encoding="utf-8").splitlines()
               if line]
    if not (resources["final_status"] == "SUCCEEDED" and
            resources["samples"] == len(samples) > 0 and
            resources["peak_tree_rss_mib"] <= 32768 and
            resources["minimum_mem_available_gib"] >= 32 and
            resources["minimum_free_gib"] >= 100 and
            max(row["load_1m"] for row in samples) <= 20):
        raise RuntimeError("Pilot resource gate failed: " + experiment_id)
    return {"id": experiment_id, "source_sha": SOURCE_SHA,
            "trace_sha256": TRACE_SHA, "fct_sha256": summary["fct_sha256"],
            "moe_batch_us": tags["2"]["synthetic_batch_completion_us"],
            "moe_p50_fct_us": tags["2"]["p50_fct_us"],
            "moe_p99_fct_us": tags["2"]["p99_fct_us"],
            "background_p99_fct_us": tags["1"]["p99_fct_us"],
            "background_max_fct_us": max(
                int(line.split()[6]) / 1000 for line in
                next(raw.glob("*_out_fct.txt")).read_text(encoding="utf-8").splitlines()
                if int(line.split()[4]) == 8388608),
            "tags": tags, "diagnostic": diagnostic, "resource": resources}


def change(value, control):
    return 100 * (value / control - 1)


def main():
    rows = {mode: verify(mode, experiment_id) for mode, experiment_id in IDS.items()}
    control = rows["fecmp"]
    effects = {}
    for mode, row in rows.items():
        if mode == "fecmp":
            continue
        effects[mode] = {
            "moe_batch_change_pct": change(row["moe_batch_us"], control["moe_batch_us"]),
            "moe_p50_fct_change_pct": change(row["moe_p50_fct_us"], control["moe_p50_fct_us"]),
            "moe_p99_fct_change_pct": change(row["moe_p99_fct_us"], control["moe_p99_fct_us"]),
            "background_p99_change_pct": change(row["background_p99_fct_us"],
                                                   control["background_p99_fct_us"]),
        }
    output = {"kind": "same-trace engineering pilot; no independent-seed inference",
              "source_sha": SOURCE_SHA, "trace_sha256": TRACE_SHA,
              "cells": rows, "paired_effects": effects}
    encoded = json.dumps(output, indent=2, sort_keys=True) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("Existing pilot analysis differs")
    OUTPUT.write_text(encoded, encoding="utf-8")
    print(json.dumps({"cells": len(rows), "paired_effects": effects}, sort_keys=True))


if __name__ == "__main__":
    main()
