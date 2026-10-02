#!/usr/bin/env python3
"""Analyze verified WS-25 D1 per-QP and background egress diagnostics."""
import collections
import json
import re
from pathlib import Path

import analyze_moe_tags
import verify_ws25_d1 as verifier

ROOT = Path(__file__).resolve().parents[1]
QP_COUNTERS = ("rx_ooo_packets", "sack_feedback", "cnp_feedback",
               "repeated_sends", "timeout_recovery")


def fields(line):
    return {key: int(value) for key, value in re.findall(r"(\w+)=(-?\d+)", line)}


def summarize_hops(rows):
    packets = sum(row["packets"] for row in rows)
    return {
        "flow_hop_rows": len(rows),
        "packets_across_hops": packets,
        "bytes_across_hops": sum(row["bytes"] for row in rows),
        "queued_bytes_sum_across_packets": sum(row["queued_bytes_sum"] for row in rows),
        "queued_bytes_max": max((row["queued_bytes_max"] for row in rows), default=0),
        "mean_enqueue_queue_bytes_per_packet": (
            sum(row["queued_bytes_sum"] for row in rows) / packets if packets else 0),
        "wait_ns_sum_across_packets": sum(row["wait_ns_sum"] for row in rows),
        "wait_ns_max": max((row["wait_ns_max"] for row in rows), default=0),
        "mean_enqueue_to_dequeue_wait_ns": (
            sum(row["wait_ns_sum"] for row in rows) / packets if packets else 0),
        "unpaired_inflight_packets": None,
    }


def cell(experiment_id, mode, diag):
    checked = verifier.verify_cell(experiment_id, mode, diag)
    log_path = ROOT / "results" / experiment_id / "logs" / "config.log"
    log = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    qp_rows = [fields(line) for line in log if line.startswith("WS25_QP ")]
    by_tag = collections.defaultdict(lambda: {
        "qp_count": 0, "unique_flow_ids": set(), **{key: 0 for key in QP_COUNTERS}})
    for row in qp_rows:
        bucket = by_tag[row["tag"]]
        bucket["qp_count"] += 1
        bucket["unique_flow_ids"].add(row["flow_id"])
        for key in QP_COUNTERS:
            bucket[key] += row[key]
    for bucket in by_tag.values():
        bucket["unique_flow_ids"] = len(bucket["unique_flow_ids"])
    choices = {row["tag"]: row for row in
               (fields(line) for line in log if line.startswith("WS25_CHOICE "))}
    hop_rows = [fields(line) for line in log if line.startswith("WS13_HOP ")]
    if diag:
        unpaired = next(int(fields(line)["unpaired"]) for line in log
                        if line.startswith("WS13_INFLIGHT "))
        hops = summarize_hops(hop_rows)
        hops["unpaired_inflight_packets"] = unpaired
    else:
        hops = summarize_hops([])
    classreserve = None
    queue_check = None
    if mode == "classreserve":
        route = next(fields(line) for line in log if line.startswith("WS25_CLASSRESERVE "))
        queue_check = next(fields(line) for line in log if line.startswith("WS25_QUEUE "))
        classreserve = {"route_counters": route, "choice_diagnostics_by_tag": choices}
    stats = analyze_moe_tags.summarize(experiment_id)["tags"]
    return {
        **checked,
        "fct_sha256": checked["fct_sha256"],
        "moe_batch_us": stats["2"]["synthetic_batch_completion_us"],
        "background_p99_us": stats["1"]["p99_fct_us"],
        "qp_diagnostics_by_tag": {str(tag): bucket for tag, bucket in sorted(by_tag.items())},
        "background_hop_diagnostics": hops,
        "classreserve_diagnostics": classreserve,
        "classreserve_queue_check": queue_check,
    }


def main():
    rows = [cell(*entry) for entry in verifier.CELLS]
    for mode in ("classreserve", "drill"):
        pair = [row for row in rows if row["mode"] == mode]
        if len(pair) != 2 or pair[0]["fct_sha256"] != pair[1]["fct_sha256"]:
            raise RuntimeError("D1 mode on/off fingerprint mismatch: " + mode)
    output = {
        "evidence_level": "single-demand diagnostic and non-perturbation check; not efficacy",
        "source_sha": verifier.SOURCE_SHA,
        "demand_seed": 20262501,
        "trace_sha256": verifier.TRACE_SHA,
        "topology_sha256": verifier.TOPO_SHA,
        "counter_semantics": {
            "rx_ooo_packets": "received UDP packets whose sequence starts above ReceiverNextExpectedSeq",
            "sack_feedback": "sender-side ACK/NACK messages carrying nonzero IRN NACK size; not unique loss events",
            "cnp_feedback": "sender-side ACK/NACK messages carrying CNP flag; may overlap SACK feedback",
            "repeated_sends": "transmitted UDP packets whose sequence starts below the highest previously sent end sequence; not a direct loss counter",
            "timeout_recovery": "HandleTimeout invocations that proceeded into recovery",
            "background_hops": "background packet records aggregated by flow-hop; the same input bytes appear on multiple switches",
        },
        "cells": rows,
        "interpretation_limits": [
            "One diagnostic demand seed cannot establish a general performance effect.",
            "Packet OoO, feedback messages, repeated sends, and timeout recovery are distinct counters.",
            "Background hop totals count the same packet at multiple switches and are explanatory only.",
            "D1 does not exercise or validate CONGA/LetFlow flowlet transitions or ConWeave reroute/VOQ branches.",
        ],
    }
    destination = ROOT / "docs" / "research" / "evidence" / "ws25-d1-diagnostic.json"
    destination.write_text(json.dumps(output, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(destination), "verified_cells": len(rows)}, sort_keys=True))


if __name__ == "__main__":
    main()
