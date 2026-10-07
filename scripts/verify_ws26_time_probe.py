#!/usr/bin/env python3
"""Verify raw, resources, and bounded time logs for four disclosed WS-25 replays."""

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

import analyze_moe_tags


ROOT = Path(__file__).resolve().parents[1]
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
CELLS = (
    ("20261007-230000-ws26-time-s43-b064-ecmp", "fecmp", 64,
     "ws25_seed20262543_b64.txt", "035228c6e0e5c235e31200d70ab413c1a587f8301437d8e6f180756a264d12aa",
     "2447c24415711a30e025a04df23319ad36871061ea40d312775a92617e793cb8"),
    ("20261007-230001-ws26-time-s43-b064-classreserve", "classreserve", 64,
     "ws25_seed20262543_b64.txt", "035228c6e0e5c235e31200d70ab413c1a587f8301437d8e6f180756a264d12aa",
     "02bbd3324a22a9a1cb128efb0bf4f8a9319bb068f7f21ed2797902ed35a2980c"),
    ("20261007-230002-ws26-time-s24-b192-ecmp", "fecmp", 192,
     "ws25_seed20262524_b192.txt", "d72f0f360d89dd3504c4cba730d903e1d939400ff2abd3566cf0428f4e59e2e3",
     "48453a24b8c32fdd0d44bea7bfefbf40fcfb4cf96ac05a1c5e9cba544e70b834"),
    ("20261007-230003-ws26-time-s24-b192-classreserve", "classreserve", 192,
     "ws25_seed20262524_b192.txt", "d72f0f360d89dd3504c4cba730d903e1d939400ff2abd3566cf0428f4e59e2e3",
     "aadffa71291fbaf6fab0fce7635b54bad0f3729fdb59c5841c817c3ba99acb8e"),
)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fields(line):
    return {key: int(value) for key, value in re.findall(r"(\w+)=(-?\d+)", line)}


def check(cell, source_sha, selected):
    experiment_id, mode, background, trace_name, trace_sha, formal_fct_sha = cell
    folder = ROOT / "results" / experiment_id
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    p = meta["parameters"]
    if not (meta["status"] == "SUCCEEDED" and meta["git_commit"] == source_sha and
            meta["algorithm"] == mode and meta["topology_sha256"] == TOPO_SHA and
            meta["input_flow_sha256"] == trace_sha and p["lb"] == mode and
            p["flow_file"] == trace_name and p["topo"] == "topo_1280_400G_400G_OS1" and
            p["pfc"] == 0 and p["irn"] == 1 and p["bw"] == 400 and p["buffer"] == 9 and
            p["netload"] == 10 and p["simul_time"] == "0.01" and
            p["ws25_diag"] == 1 and p["ws26_time_probe"] == 1):
        raise RuntimeError("Fixed identity or parameters mismatch: " + experiment_id)
    if (sha(folder / "config/topology.txt") != TOPO_SHA or
            sha(folder / "config/traffic_trace.txt") != trace_sha):
        raise RuntimeError("Input snapshot mismatch: " + experiment_id)
    summary = analyze_moe_tags.summarize(experiment_id)
    tags = summary["tags"]
    if ({tag: data["input_flows"] for tag, data in tags.items()} !=
            {"1": background, "2": 16384} or
            any(data["completed_flows"] != data["input_flows"] for data in tags.values())):
        raise RuntimeError("Incomplete or mismatched QP identities: " + experiment_id)
    raw = folder / "raw" / str(meta["raw_directory"])
    fct = list(raw.glob("*_out_fct.txt"))
    if len(fct) != 1 or sha(fct[0]) != formal_fct_sha:
        raise RuntimeError("Time probe perturbed formal FCT: " + experiment_id)

    sample_file = folder / "logs/resource-samples.jsonl"
    receipt_file = folder / "logs/resource-summary.json"
    resources = json.loads(receipt_file.read_text(encoding="utf-8"))
    samples = [json.loads(line) for line in sample_file.read_text(encoding="utf-8").splitlines() if line]
    if not (resources["final_status"] == "SUCCEEDED" and
            resources["samples"] == len(samples) > 0 and
            resources["peak_tree_rss_mib"] <= 32768 and
            resources["minimum_mem_available_gib"] >= 32 and
            resources["minimum_free_gib"] >= 100 and
            max(row["load_1m"] for row in samples) <= 20):
        raise RuntimeError("Resource receipt failed: " + experiment_id)

    events = collections.Counter()
    cnp_events = collections.Counter()
    event_keys = set()
    qp = {}
    event_summary = {}
    bucket_count = 0
    bucket_keys = set()
    ecn_summary = None
    unpaired = None
    for line in (raw / "config.log").read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("WS26_QP_EVENT "):
            row = fields(line)
            key = tuple(row[name] for name in ("src", "dst", "sport", "dport"))
            if key not in selected:
                raise RuntimeError("Unselected flow in QP time probe: " + experiment_id)
            event_keys.add(key)
            events[row["flow_id"]] += 1
            if "event=cnp " in line:
                cnp_events[row["flow_id"]] += 1
        elif line.startswith("WS26_QP_EVENT_SUMMARY "):
            row = fields(line)
            if row["flow_id"] in event_summary:
                raise RuntimeError("Duplicate QP event summary: " + experiment_id)
            event_summary[row["flow_id"]] = row
        elif line.startswith("WS26_ECN_BUCKET "):
            row = fields(line)
            key = tuple(row[name] for name in ("src", "dst", "sport", "dport"))
            if (key not in selected or row["bucket_start_ns"] % 10000 or
                    row["decisions"] <= 0 or row["bytes"] <= 0):
                raise RuntimeError("Invalid ECN bucket: " + experiment_id)
            bucket_key = (key, row["switch"], row["port"], row["bucket_start_ns"])
            if bucket_key in bucket_keys:
                raise RuntimeError("Duplicate ECN bucket: " + experiment_id)
            bucket_keys.add(bucket_key)
            bucket_count += 1
        elif line.startswith("WS26_ECN_SUMMARY "):
            if ecn_summary is not None:
                raise RuntimeError("Duplicate ECN summary: " + experiment_id)
            ecn_summary = fields(line)
        elif line.startswith("WS25_QP "):
            row = fields(line)
            if row["flow_id"] in qp:
                raise RuntimeError("Duplicate QP diagnostic: " + experiment_id)
            qp[row["flow_id"]] = row
        elif line.startswith("WS13_INFLIGHT "):
            unpaired = fields(line)["unpaired"]
    if (unpaired != 0 or len(qp) != 16384 + background or
            ecn_summary is None or ecn_summary["bucket_rows"] != bucket_count or
            ecn_summary["overflow"] != 0):
        raise RuntimeError("Diagnostic coverage or bucket cap failed: " + experiment_id)
    if (set(events) != set(event_summary) or len(event_summary) != 5 or
            event_keys != selected or
            any(qp[flow_id]["tag"] != 1 or qp[flow_id]["cnp_feedback"] != cnp_events[flow_id]
                for flow_id in event_summary) or
            any(row["truncated"] or row["rows"] != events[flow_id]
                for flow_id, row in event_summary.items())):
        raise RuntimeError("QP event coverage or cap failed: " + experiment_id)
    return {"id": experiment_id, "mode": mode, "background": background,
            "source_sha": source_sha, "fct_sha256": formal_fct_sha,
            "qp_event_rows": sum(events.values()), "ecn_bucket_rows": bucket_count,
            "resource_samples": len(samples), "peak_tree_rss_mib": resources["peak_tree_rss_mib"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--id", help="verify one original ID while the remaining cells run")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
        parser.error("--source-sha needs a full Git SHA")
    pairs = json.loads((ROOT / "docs/research/evidence/ws26-ecmp-paired-tail-diagnostic.json").read_text(encoding="utf-8"))["pairs"]
    selected = {p["background"]: {
        tuple(flow[name] for name in ("src", "dst", "sport", "dport"))
        for flow in p["flows_by_descending_regression"][:5]} for p in pairs}
    cells = [cell for cell in CELLS if args.id is None or cell[0] == args.id]
    if not cells:
        parser.error("unknown experiment ID")
    result = {"complete": len(cells) == 4,
              "cells": [check(cell, args.source_sha, selected[cell[2]]) for cell in cells]}
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
