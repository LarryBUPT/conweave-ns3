#!/usr/bin/env python3
"""Verify the frozen DestSpread v2 correctness cells, without efficacy claims."""
import argparse
import hashlib
import json
import re
from pathlib import Path

import analyze_moe_tags

ROOT = Path(__file__).resolve().parents[1]
SHA = "87bb136ba85126c8c6c883814c7fa10cdcd74fda"
TOPO = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
TRACES = {
    "ws25_v1fix_mixed8.txt": ("29ebe2dcf38c0e4d29326947c4bc4e111f6b56fe378c020c30ee788fbaa5effb", {"1": 4, "2": 4}),
    "ws25_v1fix_background4.txt": ("e1259a4dbb17fe70e15a72881cbc3faaeac637123ba18ac29596b4f4f2743015", {"1": 4}),
    "ws25_v1fix_moe4.txt": ("8acfe14d19d7ef7822bfd9a78334b830ce581456003e132d6557a44d1e41ea60", {"2": 4}),
    "ws25_v1fix_unclassified8.txt": ("73704cadbdb95708c5ba26126af43b2758af688e332a80fdad46e7bc42c66dd3", {"0": 8}),
    "ws25_v1fix_legacy5.txt": ("cc80f3a1eb23dcf936a8b371bf5b63763acac283923361efe9bcd3ebb1ae6c94", {"0": 8}),
}
CELLS = [
    ("20261006-070000-ws25-v2-pre-mixed8", "destspread", "ws25_v1fix_mixed8.txt"),
    ("20261006-070001-ws25-v2-pre-background4", "destspread", "ws25_v1fix_background4.txt"),
    ("20261006-070002-ws25-v2-pre-moe4", "destspread", "ws25_v1fix_moe4.txt"),
    ("20261006-070003-ws25-v2-pre-unclassified8", "destspread", "ws25_v1fix_unclassified8.txt"),
    ("20261006-070004-ws25-v2-pre-legacy5", "destspread", "ws25_v1fix_legacy5.txt"),
]
CELLS += [("20261006-0700%02d-ws25-v2-pre-%s" % (i + 5, mode), mode,
           "ws25_v1fix_mixed8.txt")
          for i, mode in enumerate(("fecmp", "drill", "conga", "letflow", "conweave"))]
CELLS += [
    ("20261006-070010-ws25-v2-pre-unclassified-ecmp", "fecmp", "ws25_v1fix_unclassified8.txt"),
    ("20261006-070011-ws25-v2-pre-legacy-ecmp", "fecmp", "ws25_v1fix_legacy5.txt"),
]
OLD_MIXED8_IDS = {
    mode: "20261003-18000%d-ws25-v1fix-pre-%s" % (i, mode)
    for i, mode in enumerate(("fecmp", "drill", "conga", "letflow", "conweave"))
}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def one_file(folder, suffix):
    paths = list(folder.glob("*" + suffix))
    if len(paths) != 1 or paths[0].is_symlink():
        raise RuntimeError("Missing/ambiguous raw " + suffix + " in " + str(folder))
    return paths[0]


def counters(line):
    return {name: int(value) for name, value in re.findall(r"(\w+)=(\d+)", line)}


def verify(experiment_id, mode, trace, diag=0, source_sha=SHA):
    folder = ROOT / "results" / experiment_id
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = meta["parameters"]
    trace_sha, expected_tags = TRACES[trace]
    if not (meta["status"] == "SUCCEEDED" and meta["git_commit"] == source_sha and
            meta["algorithm"] == mode and meta["seed"] == 1 and
            meta["input_flow_sha256"] == trace_sha and meta["topology_sha256"] == TOPO and
            params["lb"] == mode and params["flow_file"] == trace and
            params["topo"] == "topo_1280_400G_400G_OS1" and
            params["bw"] == 400 and params["buffer"] == 9 and
            params["pfc"] == 0 and params["irn"] == 1 and params["ws25_diag"] == diag and
            params["netload"] == 10 and params["simul_time"] == "0.01"):
        raise RuntimeError("Metadata identity mismatch: " + experiment_id)
    if digest(folder / "config" / "traffic_trace.txt") != trace_sha or digest(
            folder / "config" / "topology.txt") != TOPO:
        raise RuntimeError("Input snapshot mismatch: " + experiment_id)
    tags = analyze_moe_tags.summarize(experiment_id)["tags"]
    if {tag: row["input_flows"] for tag, row in tags.items()} != expected_tags or any(
            row["input_flows"] != row["completed_flows"] for row in tags.values()):
        raise RuntimeError("Flow completion or tag mismatch: " + experiment_id)
    raw = folder / "raw" / str(meta["raw_directory"])
    for suffix in ("_out_fct.txt", "_out_cnp.txt", "_out_pfc.txt", "_out_uplink.txt"):
        one_file(raw, suffix)
    fct_sha = digest(one_file(raw, "_out_fct.txt"))
    log = (folder / "logs" / "config.log").read_text(encoding="utf-8", errors="replace")
    route = None
    if mode == "destspread":
        lines = [line for line in log.splitlines() if line.startswith("WS25_DESTSPREAD ")]
        queue = [line for line in log.splitlines() if line.startswith("WS25_QUEUE ")]
        if len(lines) != 1 or len(queue) != 1:
            raise RuntimeError("DestSpread counters missing: " + experiment_id)
        route, q = counters(lines[0]), counters(queue[0])
        if route.get("queue_violations") != 0 or q.get("enqueued") != (
                q.get("dequeued", 0) + q.get("queued_drop", 0) + q.get("current", 0)):
            raise RuntimeError("DestSpread queue conservation failed: " + experiment_id)
        if trace == "ws25_v1fix_mixed8.txt" and not all(route.get(key, 0) > 0 for key in (
                "moe_packets", "background_packets", "background_new", "background_reused")):
            raise RuntimeError("DestSpread mixed path not exercised: " + experiment_id)
        if trace == "ws25_v1fix_mixed8.txt":
            ports = [counters(line) for line in log.splitlines()
                     if line.startswith("WS25_DESTSPREAD_PORT ")]
            if not all(any(row.get("tag") == tag and row.get("packets", 0) > 0 for row in ports)
                       for tag in (1, 2)):
                raise RuntimeError("Source ToR port decisions missing: " + experiment_id)
        if trace in ("ws25_v1fix_unclassified8.txt", "ws25_v1fix_legacy5.txt") and route.get(
                "fallback_packets", 0) <= 0:
            raise RuntimeError("DestSpread fallback not exercised: " + experiment_id)
        if trace == "ws25_v1fix_background4.txt" and route.get("moe_packets") != 0:
            raise RuntimeError("Unexpected MoE packets: " + experiment_id)
        if trace == "ws25_v1fix_moe4.txt" and route.get("background_packets") != 0:
            raise RuntimeError("Unexpected background packets: " + experiment_id)
    resources = json.loads((folder / "logs" / "resource-summary.json").read_text(encoding="utf-8"))
    samples = [json.loads(line) for line in (folder / "logs" / "resource-samples.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    if not (resources["final_status"] == "SUCCEEDED" and
            resources["samples"] == len(samples) > 0 and
            resources["peak_tree_rss_mib"] <= 32768 and
            resources["minimum_mem_available_gib"] >= 32 and
            resources["minimum_free_gib"] >= 100 and
            max(row["load_1m"] for row in samples) <= 20):
        raise RuntimeError("Resource receipt failed: " + experiment_id)
    return {"id": experiment_id, "mode": mode, "trace": trace, "fct_sha256": fct_sha,
            "tag_counts": expected_tags, "route": route, "resource": resources}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", choices=[cell[0] for cell in CELLS])
    args = parser.parse_args()
    for trace, (expected, unused_tags) in TRACES.items():
        if digest(ROOT / "config" / trace) != expected:
            raise RuntimeError("Local trace hash changed: " + trace)
    selected = [cell for cell in CELLS if not args.id or args.id == cell[0]]
    results = [verify(*cell) for cell in selected]
    by_key = {(row["mode"], row["trace"]): row for row in results}
    for trace in ("ws25_v1fix_unclassified8.txt", "ws25_v1fix_legacy5.txt"):
        if ("destspread", trace) in by_key and ("fecmp", trace) in by_key and by_key[
                "destspread", trace]["fct_sha256"] != by_key["fecmp", trace]["fct_sha256"]:
            raise RuntimeError("ECMP fallback FCT differs: " + trace)
    for mode, old_id in OLD_MIXED8_IDS.items():
        key = (mode, "ws25_v1fix_mixed8.txt")
        if key in by_key:
            old_meta = json.loads((ROOT / "results" / old_id / "metadata.json").read_text(
                encoding="utf-8"))
            old_raw = ROOT / "results" / old_id / "raw" / str(old_meta["raw_directory"])
            if by_key[key]["fct_sha256"] != digest(one_file(old_raw, "_out_fct.txt")):
                raise RuntimeError("Old mode FCT regression: " + mode)
    print(json.dumps({"verified": len(results), "cells": results}, sort_keys=True))


if __name__ == "__main__":
    main()
