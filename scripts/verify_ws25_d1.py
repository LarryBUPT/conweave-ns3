#!/usr/bin/env python3
"""Verify WS-25 D1 diagnostic identity and on/off FCT fingerprints."""
import hashlib
import json
import re
from pathlib import Path

import analyze_moe_tags

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "b13369d3f086189b693a1c8d875cfe7e3171181e"
TRACE = "ws25_seed20262501_b192.txt"
TRACE_SHA = "9791006f71843ea74b044396f6ae112ea8340aa9781cf0d267876e0940b02f48"
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
CELLS = (
    ("20261003-160000-ws25-d1-classreserve-off", "classreserve", 0),
    ("20261003-160001-ws25-d1-classreserve-on", "classreserve", 1),
    ("20261003-160002-ws25-d1-drill-off", "drill", 0),
    ("20261003-160003-ws25-d1-drill-on", "drill", 1),
)


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


def verify_cell(experiment_id, mode, diag):
    folder = ROOT / "results" / experiment_id
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = meta["parameters"]
    if not (meta["status"] == "SUCCEEDED" and meta["git_commit"] == SOURCE_SHA and
            meta["algorithm"] == mode and meta["seed"] == 1 and
            meta["input_flow_sha256"] == TRACE_SHA and meta["topology_sha256"] == TOPO_SHA and
            params["flow_file"] == TRACE and params["lb"] == mode and
            params["topo"] == "topo_1280_400G_400G_OS1" and
            params["bw"] == 400 and params["buffer"] == 9 and
            params["simul_time"] == "0.01" and params["netload"] == 10 and
            params["pfc"] == 0 and params["irn"] == 1 and params["ws25_diag"] == diag):
        raise RuntimeError("D1 metadata mismatch: " + experiment_id)
    if (sha(folder / "config" / "traffic_trace.txt") != TRACE_SHA or
            sha(folder / "config" / "topology.txt") != TOPO_SHA):
        raise RuntimeError("D1 input hash mismatch: " + experiment_id)
    raw = folder / "raw" / str(meta["raw_directory"])
    for suffix in ("_out_fct.txt", "_out_cnp.txt", "_out_pfc.txt", "_out_uplink.txt"):
        one_file(raw, suffix)
    tags = analyze_moe_tags.summarize(experiment_id)["tags"]
    if (tags["1"]["input_flows"], tags["1"]["completed_flows"],
            tags["2"]["input_flows"], tags["2"]["completed_flows"]) != (192, 192, 16384, 16384):
        raise RuntimeError("D1 flow completion mismatch: " + experiment_id)
    log = (folder / "logs" / "config.log").read_text(encoding="utf-8", errors="replace")
    qp_rows = [line for line in log.splitlines() if line.startswith("WS25_QP ")]
    choice_rows = [line for line in log.splitlines() if line.startswith("WS25_CHOICE ")]
    hop_rows = [line for line in log.splitlines() if line.startswith("WS13_HOP ")]
    if diag:
        flow_ids = [int(re.search(r"\bflow_id=(-?\d+)", line).group(1)) for line in qp_rows]
        if len(flow_ids) != 16576 or len(set(flow_ids)) != 16576 or min(flow_ids) < 0:
            raise RuntimeError("D1 per-QP diagnostic incomplete: " + experiment_id)
        if not hop_rows:
            raise RuntimeError("D1 background-hop diagnostic absent: " + experiment_id)
        if mode == "classreserve" and len(choice_rows) != 2:
            raise RuntimeError("D1 choice summary incomplete: " + experiment_id)
        if mode == "drill" and choice_rows:
            raise RuntimeError("D1 choice summary leaked into DRILL")
    elif qp_rows or choice_rows or hop_rows:
        raise RuntimeError("D1 default-off diagnostic produced rows: " + experiment_id)
    if mode == "classreserve" and "queue_violations=0" not in log:
        raise RuntimeError("D1 ClassReserve queue conservation failed")
    resources = json.loads((folder / "logs" / "resource-summary.json").read_text(encoding="utf-8"))
    samples = [json.loads(line) for line in
               (folder / "logs" / "resource-samples.jsonl").read_text().splitlines() if line]
    if not (resources["final_status"] == "SUCCEEDED" and
            resources["samples"] == len(samples) > 0 and
            resources["peak_tree_rss_mib"] <= 32768 and
            resources["minimum_mem_available_gib"] >= 32 and
            resources["minimum_free_gib"] >= 100 and
            max(row["load_1m"] for row in samples) <= 20):
        raise RuntimeError("D1 resource gate failed: " + experiment_id)
    return {"id": experiment_id, "mode": mode, "diag": diag,
            "fct_sha256": sha(one_file(raw, "_out_fct.txt")),
            "moe_batch_us": tags["2"]["synthetic_batch_completion_us"],
            "background_p99_us": tags["1"]["p99_fct_us"],
            "qp_rows": len(qp_rows), "hop_rows": len(hop_rows),
            "choice_rows": len(choice_rows), "resource": resources}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", choices=[cell[0] for cell in CELLS])
    args = parser.parse_args()
    selected = [cell for cell in CELLS if not args.id or cell[0] == args.id]
    if sha(ROOT / "config" / TRACE) != TRACE_SHA:
        raise RuntimeError("Local D1 trace changed")
    rows = [verify_cell(*cell) for cell in selected]
    if not args.id:
        for mode in ("classreserve", "drill"):
            pair = [row for row in rows if row["mode"] == mode]
            if len(pair) != 2 or pair[0]["fct_sha256"] != pair[1]["fct_sha256"]:
                raise RuntimeError("D1 on/off FCT fingerprint differs: " + mode)
    print(json.dumps({"verified": len(rows), "cells": rows}, sort_keys=True))


if __name__ == "__main__":
    main()
