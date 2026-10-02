#!/usr/bin/env python3
"""Verify the frozen ClassReserve v1-correction correctness preflight."""
import collections
import hashlib
import json
import re
from pathlib import Path

import analyze_moe_tags

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "c84108b24c94a5068861e5bb090c5aa387245ee1"
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
TRACE_HASHES = {
    "ws25_v1fix_mixed8.txt": "29ebe2dcf38c0e4d29326947c4bc4e111f6b56fe378c020c30ee788fbaa5effb",
    "ws25_v1fix_background4.txt": "e1259a4dbb17fe70e15a72881cbc3faaeac637123ba18ac29596b4f4f2743015",
    "ws25_v1fix_moe4.txt": "8acfe14d19d7ef7822bfd9a78334b830ce581456003e132d6557a44d1e41ea60",
    "ws25_v1fix_unclassified8.txt": "73704cadbdb95708c5ba26126af43b2758af688e332a80fdad46e7bc42c66dd3",
    "ws25_v1fix_legacy5.txt": "cc80f3a1eb23dcf936a8b371bf5b63763acac283923361efe9bcd3ebb1ae6c94",
    "ws25_seed20262501_b192.txt": "9791006f71843ea74b044396f6ae112ea8340aa9781cf0d267876e0940b02f48",
}
MODES = ("fecmp", "drill", "conga", "letflow", "conweave", "classreserve")
CELLS = []
for i, mode in enumerate(MODES):
    CELLS.append(("20261003-18000%d-ws25-v1fix-pre-%s" % (i, mode), mode,
                  "ws25_v1fix_mixed8.txt", 0))
for offset, trace in enumerate(("ws25_v1fix_background4.txt", "ws25_v1fix_moe4.txt",
                               "ws25_v1fix_unclassified8.txt", "ws25_v1fix_legacy5.txt")):
    CELLS.append(("20261003-18001%d-ws25-v1fix-pre-%s" %
                  (offset, ("background", "moe", "unclassified", "legacy5")[offset]),
                  "classreserve", trace, 0))
CELLS.append(("20261003-180014-ws25-v1fix-pre-b192", "classreserve",
              "ws25_seed20262501_b192.txt", 0))
EXPECTED_TAGS = {
    "ws25_v1fix_mixed8.txt": {"1": 4, "2": 4},
    "ws25_v1fix_background4.txt": {"1": 4},
    "ws25_v1fix_moe4.txt": {"2": 4},
    "ws25_v1fix_unclassified8.txt": {"0": 8},
    "ws25_v1fix_legacy5.txt": {"0": 8},
    "ws25_seed20262501_b192.txt": {"1": 192, "2": 16384},
}


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def one_file(folder, suffix):
    matches = list(folder.glob("*" + suffix))
    if len(matches) != 1 or matches[0].is_symlink():
        raise RuntimeError("Missing or ambiguous " + suffix + " in " + str(folder))
    return matches[0]


def verify_cell(experiment_id, mode, trace, diag=0):
    folder = ROOT / "results" / experiment_id
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = meta["parameters"]
    expected_trace = TRACE_HASHES[trace]
    if not (meta["status"] == "SUCCEEDED" and meta["git_commit"] == SOURCE_SHA and
            meta["algorithm"] == mode and meta["seed"] == 1 and
            meta["input_flow_sha256"] == expected_trace and meta["topology_sha256"] == TOPO_SHA and
            params["flow_file"] == trace and params["lb"] == mode and
            params["topo"] == "topo_1280_400G_400G_OS1" and
            params["bw"] == 400 and params["buffer"] == 9 and
            params["simul_time"] == "0.01" and params["netload"] == 10 and
            params["pfc"] == 0 and params["irn"] == 1 and params["ws25_diag"] == diag):
        raise RuntimeError("V1 correction metadata mismatch: " + experiment_id)
    if sha(folder / "config" / "traffic_trace.txt") != expected_trace:
        raise RuntimeError("V1 correction trace snapshot mismatch: " + experiment_id)
    if sha(folder / "config" / "topology.txt") != TOPO_SHA:
        raise RuntimeError("V1 correction topology snapshot mismatch: " + experiment_id)
    stats = analyze_moe_tags.summarize(experiment_id)["tags"]
    tag_counts = {tag: row["input_flows"] for tag, row in stats.items()}
    if tag_counts != EXPECTED_TAGS[trace]:
        raise RuntimeError("Workload tag counts mismatch: " + experiment_id)
    if any(row["input_flows"] != row["completed_flows"] for row in stats.values()):
        raise RuntimeError("Unfinished input flow: " + experiment_id)
    log = (folder / "logs" / "config.log").read_text(encoding="utf-8", errors="replace")
    raw = folder / "raw" / str(meta["raw_directory"])
    for suffix in ("_out_fct.txt", "_out_cnp.txt", "_out_pfc.txt", "_out_uplink.txt"):
        one_file(raw, suffix)
    if mode == "classreserve":
        match = next((line for line in log.splitlines()
                      if line.startswith("WS25_CLASSRESERVE ")), None)
        if match is None or "queue_violations=0" not in match:
            # Queue check is reported on the separate WS25_QUEUE line.
            if match is None or "queue_violations=0" not in log:
                raise RuntimeError("ClassReserve counters/queue invariant absent: " + experiment_id)
        counters = {key: int(value) for key, value in
                    re.findall(r"(\w+)=(\d+)", match)}
        if trace == "ws25_v1fix_unclassified8.txt" or trace == "ws25_v1fix_legacy5.txt":
            if counters.get("fallback_packets", 0) <= 0:
                raise RuntimeError("Fallback branch not observed: " + experiment_id)
        if trace == "ws25_v1fix_background4.txt" and counters.get("moe_packets", 0) != 0:
            raise RuntimeError("Unexpected MoE packets in background-only trace")
        if trace == "ws25_v1fix_moe4.txt" and counters.get("background_packets", 0) != 0:
            raise RuntimeError("Unexpected background packets in MoE-only trace")
        if trace in ("ws25_v1fix_mixed8.txt", "ws25_seed20262501_b192.txt") and not (
                counters.get("moe_flow_new", 0) > 0 and
                counters.get("moe_flow_reused", 0) > 0 and
                counters.get("background_new_flows", 0) > 0 and
                counters.get("background_reused", 0) > 0):
            raise RuntimeError("Flow-path cache selection/reuse absent: " + experiment_id)
    resources = json.loads((folder / "logs" / "resource-summary.json").read_text(encoding="utf-8"))
    samples = [json.loads(line) for line in
               (folder / "logs" / "resource-samples.jsonl").read_text().splitlines() if line]
    if not (resources["final_status"] == "SUCCEEDED" and
            resources["samples"] == len(samples) > 0 and
            resources["peak_tree_rss_mib"] <= 32768 and
            resources["minimum_mem_available_gib"] >= 32 and
            resources["minimum_free_gib"] >= 100 and
            max(row["load_1m"] for row in samples) <= 20):
        raise RuntimeError("V1 correction resource gate failed: " + experiment_id)
    return {"id": experiment_id, "mode": mode, "trace": trace,
            "trace_sha256": expected_trace, "fct_sha256": sha(one_file(raw, "_out_fct.txt")),
            "tag_counts": tag_counts,
            "moe_batch_us": stats.get("2", {}).get("synthetic_batch_completion_us"),
            "background_p99_us": stats.get("1", {}).get("p99_fct_us"),
            "resource": resources}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", choices=[cell[0] for cell in CELLS])
    args = parser.parse_args()
    selected = [entry for entry in CELLS if not args.id or entry[0] == args.id]
    for trace, digest in TRACE_HASHES.items():
        if sha(ROOT / "config" / trace) != digest:
            raise RuntimeError("Local input hash mismatch: " + trace)
    rows = [verify_cell(*entry) for entry in selected]
    print(json.dumps({"verified": len(rows), "cells": rows}, sort_keys=True))


if __name__ == "__main__":
    main()
