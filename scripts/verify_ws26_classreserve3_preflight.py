#!/usr/bin/env python3
"""Verify the frozen ClassReserve v3 correctness cells, without efficacy claims."""

import argparse
import hashlib
import json
import re
from pathlib import Path

import analyze_moe_tags


ROOT = Path(__file__).resolve().parents[1]
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
TRACES = {
    "mixed8": ("ws25_v1fix_mixed8.txt", "29ebe2dcf38c0e4d29326947c4bc4e111f6b56fe378c020c30ee788fbaa5effb", {"1": 4, "2": 4}),
    "background4": ("ws25_v1fix_background4.txt", "e1259a4dbb17fe70e15a72881cbc3faaeac637123ba18ac29596b4f4f2743015", {"1": 4}),
    "moe4": ("ws25_v1fix_moe4.txt", "8acfe14d19d7ef7822bfd9a78334b830ce581456003e132d6557a44d1e41ea60", {"2": 4}),
    "unclassified8": ("ws25_v1fix_unclassified8.txt", "73704cadbdb95708c5ba26126af43b2758af688e332a80fdad46e7bc42c66dd3", {"0": 8}),
    "legacy5": ("ws25_v1fix_legacy5.txt", "cc80f3a1eb23dcf936a8b371bf5b63763acac283923361efe9bcd3ebb1ae6c94", {"0": 8}),
}
PREFIX = "20261008-0300"
CELLS = [
    ("00", "mixed8-p1i1", "classreserve3", "mixed8", 1, 1, 0),
    ("01", "background4-p1i1", "classreserve3", "background4", 1, 1, 0),
    ("02", "moe4-p1i1", "classreserve3", "moe4", 1, 1, 0),
    ("03", "unclassified8-p1i1", "classreserve3", "unclassified8", 1, 1, 0),
    ("04", "legacy5-p1i1", "classreserve3", "legacy5", 1, 1, 0),
    ("05", "unclassified8-ecmp-p1i1", "fecmp", "unclassified8", 1, 1, 0),
    ("06", "legacy5-ecmp-p1i1", "fecmp", "legacy5", 1, 1, 0),
    ("07", "mixed8-ecmp-p1i1", "fecmp", "mixed8", 1, 1, 0),
    ("08", "mixed8-p0i0", "classreserve3", "mixed8", 0, 0, 0),
    ("09", "mixed8-p0i1", "classreserve3", "mixed8", 0, 1, 0),
    ("10", "mixed8-p1i0", "classreserve3", "mixed8", 1, 0, 0),
    ("11", "fecmp-mixed8-p0i1", "fecmp", "mixed8", 0, 1, 0),
    ("12", "drill-mixed8-p0i1", "drill", "mixed8", 0, 1, 0),
    ("13", "conga-mixed8-p0i1", "conga", "mixed8", 0, 1, 0),
    ("14", "letflow-mixed8-p0i1", "letflow", "mixed8", 0, 1, 0),
    ("15", "conweave-mixed8-p0i1", "conweave", "mixed8", 0, 1, 0),
    ("16", "background4-ecmp-p1i1", "fecmp", "background4", 1, 1, 0),
    ("17", "mixed8-diag-p1i1", "classreserve3", "mixed8", 1, 1, 1),
]
CELLS = [(PREFIX + number + "-ws26-v3-pre-" + suffix, mode, trace, pfc, irn, diag)
         for number, suffix, mode, trace, pfc, irn, diag in CELLS]
OLD_MIXED8_IDS = {
    mode: "20261003-18000%d-ws25-v1fix-pre-%s" % (i, mode)
    for i, mode in enumerate(("fecmp", "drill", "conga", "letflow", "conweave"))
}


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def one_file(folder, suffix):
    files = list(folder.glob("*" + suffix))
    if len(files) != 1 or files[0].is_symlink():
        raise RuntimeError("Missing or ambiguous raw " + suffix + " in " + str(folder))
    return files[0]


def fields(line):
    return {key: int(value) for key, value in re.findall(r"(\w+)=(-?\d+)", line)}


def verify(cell, source_sha):
    experiment_id, mode, trace_key, pfc, irn, diag = cell
    folder = ROOT / "results" / experiment_id
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = metadata["parameters"]
    trace_name, trace_sha, expected_tags = TRACES[trace_key]
    if not (metadata["status"] == "SUCCEEDED" and metadata["git_commit"] == source_sha and
            metadata["algorithm"] == mode and metadata["seed"] == 1 and
            metadata["input_flow_sha256"] == trace_sha and
            metadata["topology_sha256"] == TOPO_SHA and params["lb"] == mode and
            params["flow_file"] == trace_name and
            params["topo"] == "topo_1280_400G_400G_OS1" and
            params["bw"] == 400 and params["buffer"] == 9 and
            params["pfc"] == pfc and params["irn"] == irn and
            params["ws25_diag"] == diag and params["ws26_time_probe"] == 0 and
            params["netload"] == 10 and params["simul_time"] == "0.01"):
        raise RuntimeError("Metadata identity or parameters mismatch: " + experiment_id)
    if (digest(folder / "config/topology.txt") != TOPO_SHA or
            digest(folder / "config/traffic_trace.txt") != trace_sha):
        raise RuntimeError("Input snapshot mismatch: " + experiment_id)
    tags = analyze_moe_tags.summarize(experiment_id)["tags"]
    if ({tag: row["input_flows"] for tag, row in tags.items()} != expected_tags or
            any(row["input_flows"] != row["completed_flows"] for row in tags.values())):
        raise RuntimeError("Flow completion or tag identity mismatch: " + experiment_id)
    raw = folder / "raw" / str(metadata["raw_directory"])
    for suffix in ("_out_fct.txt", "_out_cnp.txt", "_out_pfc.txt", "_out_uplink.txt"):
        one_file(raw, suffix)
    fct_sha = digest(one_file(raw, "_out_fct.txt"))
    log = (folder / "logs/config.log").read_text(encoding="utf-8", errors="replace")
    route = None
    paths = None
    if mode == "classreserve3":
        route_lines = [line for line in log.splitlines()
                       if line.startswith("WS26_CLASSRESERVE3 ")]
        queue_lines = [line for line in log.splitlines() if line.startswith("WS26_QUEUE ")]
        if len(route_lines) != 1 or len(queue_lines) != 1:
            raise RuntimeError("ClassReserve v3 counters missing: " + experiment_id)
        route, queue = fields(route_lines[0]), fields(queue_lines[0])
        if (route.get("queue_violations") != 0 or route.get("missing_destination") != 0 or
                queue.get("enqueued") != queue.get("dequeued", 0) +
                queue.get("queued_drop", 0) + queue.get("current", 0) or
                route.get("background_packets") != route.get("background_new", 0) +
                route.get("background_reused", 0) or
                route.get("moe_packets") != route.get("moe_new", 0) +
                route.get("moe_reused", 0) or
                route.get("choices") != route.get("moe_new")):
            raise RuntimeError("ClassReserve v3 conservation failed: " + experiment_id)
        if trace_key == "mixed8" and not all(route.get(key, 0) > 0 for key in (
                "background_new", "background_reused", "moe_new", "moe_reused")):
            raise RuntimeError("Mixed data paths not exercised: " + experiment_id)
        if trace_key == "background4" and route.get("moe_packets") != 0:
            raise RuntimeError("MoE appeared in background-only cell: " + experiment_id)
        if trace_key == "moe4" and route.get("background_packets") != 0:
            raise RuntimeError("Background appeared in MoE-only cell: " + experiment_id)
        if trace_key in ("unclassified8", "legacy5") and route.get("fallback", 0) <= 0:
            raise RuntimeError("ECMP fallback not exercised: " + experiment_id)
        if diag:
            paths = [fields(line) for line in log.splitlines()
                     if line.startswith("WS26_CLASSRESERVE3_QP ")]
            if (len(paths) != 8 or any(row.get("inconsistent") != 0 or
                                       row.get("packets", 0) <= 0 for row in paths) or
                    {row.get("tag") for row in paths} != {1, 2}):
                raise RuntimeError("Per-QP path identity failed: " + experiment_id)
    resource = json.loads((folder / "logs/resource-summary.json").read_text(encoding="utf-8"))
    samples = [json.loads(line) for line in (folder / "logs/resource-samples.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    if not (resource["final_status"] == "SUCCEEDED" and
            resource["samples"] == len(samples) > 0 and
            resource["peak_tree_rss_mib"] <= 32768 and
            resource["minimum_mem_available_gib"] >= 32 and
            resource["minimum_free_gib"] >= 100 and
            max(row["load_1m"] for row in samples) <= 20):
        raise RuntimeError("Resource receipt failed: " + experiment_id)
    return {"id": experiment_id, "mode": mode, "trace": trace_key,
            "pfc": pfc, "irn": irn, "diag": diag, "fct_sha256": fct_sha,
            "tags": expected_tags, "route": route, "per_qp_paths": paths,
            "resource_samples": len(samples),
            "peak_tree_rss_mib": resource["peak_tree_rss_mib"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--id", choices=[cell[0] for cell in CELLS])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
        parser.error("--source-sha needs a full Git SHA")
    for trace_name, trace_sha, unused_tags in TRACES.values():
        if digest(ROOT / "config" / trace_name) != trace_sha:
            raise RuntimeError("Local trace hash changed: " + trace_name)
    selected = [cell for cell in CELLS if args.id is None or cell[0] == args.id]
    results = [verify(cell, args.source_sha) for cell in selected]
    by_key = {(row["mode"], row["trace"], row["pfc"], row["irn"], row["diag"]): row
              for row in results}
    for trace in ("unclassified8", "legacy5", "background4"):
        a = by_key.get(("classreserve3", trace, 1, 1, 0))
        b = by_key.get(("fecmp", trace, 1, 1, 0))
        if a and b and a["fct_sha256"] != b["fct_sha256"]:
            raise RuntimeError("ECMP parity failed: " + trace)
    plain = by_key.get(("classreserve3", "mixed8", 1, 1, 0))
    diagnostic = by_key.get(("classreserve3", "mixed8", 1, 1, 1))
    if plain and diagnostic and plain["fct_sha256"] != diagnostic["fct_sha256"]:
        raise RuntimeError("Diagnostic mode perturbed FCT")
    for mode, old_id in OLD_MIXED8_IDS.items():
        row = by_key.get((mode, "mixed8", 0, 1, 0))
        if row:
            old_meta = json.loads((ROOT / "results" / old_id / "metadata.json").read_text(
                encoding="utf-8"))
            old_raw = ROOT / "results" / old_id / "raw" / str(old_meta["raw_directory"])
            if row["fct_sha256"] != digest(one_file(old_raw, "_out_fct.txt")):
                raise RuntimeError("Original baseline FCT changed: " + mode)
    result = {"complete": len(results) == len(CELLS), "verified": len(results), "cells": results}
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
