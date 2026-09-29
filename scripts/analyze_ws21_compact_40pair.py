#!/usr/bin/env python3
"""Recheck the frozen WS-21 v2 40-flow pair and summarize its transport cost.

All 40 completed QPs are included. The stock FCT analyzer's 2.005 s start
filter would discard part of this deliberately early correctness trace.
"""

import argparse
import datetime
import json
import math
from pathlib import Path

from verify_ws21_feedback_pair import feedback_summary, inspect_experiment, sha256
from verify_ws21_identity import read_ws18


SOURCE_SHA = "91f43c70bbb515ae35b3161d4d1e40d30ff90992"
OLD_SOURCE_SHA = "23e002e13aed71a05d6b098feb5fdab4ce7ac9f4"
TRACE_SHA = "4e7d0e6a68e3230e8960a174e570a0a788c191fa0b44922408867b02c25782cc"
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
EXPECTED_BYTES = 33849344
EXPECTED_FLOWS = 40
LOG_LIMIT = 50 * 1024 * 1024


def percentile_us(values_ns, percent):
    values = sorted(values_ns)
    position = (len(values) - 1) * percent / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    return (values[lower] + (values[upper] - values[lower]) * (position - lower)) / 1000.0


def summarize_fct(fct):
    values = [row[6] for row in fct.values()]
    groups = {}
    for size in sorted({row[4] for row in fct.values()}):
        group = [row[6] for row in fct.values() if row[4] == size]
        groups[str(size)] = {
            "flows": len(group),
            "p50_us": percentile_us(group, 50),
            "p90_us": percentile_us(group, 90),
            "p99_us": percentile_us(group, 99),
            "max_us": max(group) / 1000.0,
        }
    return {
        "flows": len(values),
        "mean_us": sum(values) / len(values) / 1000.0,
        "p50_us": percentile_us(values, 50),
        "p90_us": percentile_us(values, 90),
        "p99_us": percentile_us(values, 99),
        "max_us": max(values) / 1000.0,
        "by_flow_size_bytes": groups,
        "percentile_method": "linear interpolation on all completed QPs",
    }


def load_cell(experiment_id, enabled):
    checked = inspect_experiment(experiment_id, int(enabled))
    base = Path("results") / experiment_id
    metadata = json.loads((base / "metadata.json").read_text(encoding="utf-8"))
    raw_id = metadata["raw_directory"]
    raw = base / "raw" / raw_id
    if checked["git_commit"] != SOURCE_SHA or metadata["seed"] != 1:
        raise ValueError("source SHA or simulator seed differs")
    if checked["input_flow_sha256"] != TRACE_SHA or checked["topology_sha256"] != TOPO_SHA:
        raise ValueError("frozen input hash differs")
    if sha256(base / "config" / "traffic_trace.txt") != TRACE_SHA:
        raise ValueError("traffic snapshot differs")
    if sha256(base / "config" / "topology.txt") != TOPO_SHA:
        raise ValueError("topology snapshot differs")
    if metadata["parameters"]["ws21_feedback_interval_ns"] != 10000:
        raise ValueError("unexpected feedback interval")

    fct_path = raw / (raw_id + "_out_fct.txt")
    ws18_path = raw / (raw_id + "_out_ws18.txt")
    fct = {}
    for line in fct_path.read_text(encoding="utf-8").splitlines():
        row = tuple(map(int, line.split()))
        if len(row) != 8 or row[:4] in fct or row[6] <= 0 or row[7] <= 0:
            raise ValueError("invalid or duplicate FCT row")
        fct[row[:4]] = row
    ws18 = read_ws18(ws18_path)
    if set(fct) != set(ws18) or len(fct) != EXPECTED_FLOWS:
        raise ValueError("FCT and WS18 QP identities differ")
    if sum(flow["size"] for flow in ws18.values()) != EXPECTED_BYTES:
        raise ValueError("business byte conservation failed")
    for key, row in fct.items():
        flow = ws18[key]
        if (row[4] != flow["size"] or row[5] != flow["release"] or
                row[6] != flow["finish"] - flow["release"]):
            raise ValueError("FCT/WS18 size or timing mismatch for QP %s" % (key,))

    resource = json.loads((base / "logs" / "resource-summary.json").read_text(encoding="utf-8"))
    samples = [json.loads(line) for line in
               (base / "logs" / "resource-samples.jsonl").read_text(encoding="utf-8").splitlines()]
    if (resource["final_status"] != "SUCCEEDED" or resource["samples"] != len(samples) or
            not samples or resource["peak_tree_rss_mib"] !=
            max(point["process_tree_rss_mib"] for point in samples)):
        raise ValueError("resource receipt is incomplete")
    if resource["peak_tree_rss_mib"] > 8192 or resource["minimum_mem_available_gib"] < 16:
        raise ValueError("resource stop condition exceeded")
    log_sizes = {path.name: path.stat().st_size for path in (base / "logs").glob("*.log")}
    log_sizes["config.log"] = (raw / "config.log").stat().st_size
    if max(log_sizes.values()) > LOG_LIMIT:
        raise ValueError("text log size stop condition exceeded")
    start = datetime.datetime.fromisoformat(metadata["started_utc"].replace("Z", "+00:00"))
    finish = datetime.datetime.fromisoformat(metadata["finished_utc"].replace("Z", "+00:00"))
    result = {
        "experiment_id": experiment_id,
        "raw_directory": raw_id,
        "status": metadata["status"],
        "parameters": metadata["parameters"],
        "wall_seconds": int((finish - start).total_seconds()),
        "completed_flows": len(fct),
        "completed_business_bytes": sum(flow["size"] for flow in ws18.values()),
        "path_identity": checked["identity"],
        "fct_sha256": checked["fct_sha256"],
        "ws18_sha256": checked["ws18_sha256"],
        "fct": summarize_fct(fct),
        "resources": resource,
        "largest_text_log_bytes": max(log_sizes.values()),
        "max_observed_load_1m": max(point["load_1m"] for point in samples),
    }
    if enabled:
        report = feedback_summary(raw / "config.log")
        if (report["generated"] != report["delivered"] or report["delivered"] == 0 or
                any(report[key] for key in ("rejected", "expired", "hop_rejects", "sequence_gaps")) or
                report["hop_enqueues"] != report["hop_dequeues"] or
                report["hop_bytes"] < report["delivered_bytes"] or
                report["sample_age_max_ns"] < report["age_max_ns"] or
                report["cache_peak"] > 16384):
            raise ValueError("feedback transport gate failed")
        result["feedback"] = report
    return result, fct


def old_version_cost(experiment_id, current_cell):
    base = Path("results") / experiment_id
    metadata = json.loads((base / "metadata.json").read_text(encoding="utf-8"))
    raw_id = metadata["raw_directory"]
    raw = base / "raw" / raw_id
    report = feedback_summary(raw / "config.log")
    old_params = dict(metadata["parameters"])
    old_params["ws21_feedback_interval_ns"] = 10000  # fixed by the old source
    current = current_cell["feedback"]
    if (metadata["status"] != "SUCCEEDED" or metadata["git_commit"] != OLD_SOURCE_SHA or
            metadata["seed"] != 1 or old_params != current_cell["parameters"] or
            metadata["input_flow_sha256"] != TRACE_SHA or
            metadata["topology_sha256"] != TOPO_SHA or
            metadata["parameters"]["ws21_feedback"] != 1 or
            report["generated"] != current["generated"] or
            report["hop_enqueues"] != current["hop_enqueues"] or
            sha256(raw / (raw_id + "_out_fct.txt")) !=
            current_cell["fct_sha256"] or
            sha256(raw / (raw_id + "_out_ws18.txt")) != current_cell["ws18_sha256"]):
        raise ValueError("old-version 40-flow cost is not comparable")
    return {
        "experiment_id": experiment_id,
        "source_sha": metadata["git_commit"],
        "same_trace_topology_seed_flow_completion_report_count_and_hops": True,
        "old_report_bytes": report["delivered_bytes"] / report["delivered"],
        "new_report_bytes": current["delivered_bytes"] / current["delivered"],
        "old_hop_bytes": report["hop_bytes"],
        "new_hop_bytes": current["hop_bytes"],
        "observed_hop_byte_reduction_percent":
            100.0 * (report["hop_bytes"] - current["hop_bytes"]) / report["hop_bytes"],
        "limit": "Different source SHAs; this is a protocol-size pilot, not a same-SHA effect comparison.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--off", required=True)
    parser.add_argument("--on", required=True)
    parser.add_argument("--old-on", help="optional 51-byte-header 40-flow reference ID")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    off, off_fct = load_cell(args.off, False)
    on, on_fct = load_cell(args.on, True)
    off_params = dict(off["parameters"])
    on_params = dict(on["parameters"])
    off_params.pop("ws21_feedback")
    on_params.pop("ws21_feedback")
    if off_params != on_params or set(off_fct) != set(on_fct):
        raise ValueError("pair parameters or QP identities differ")
    deltas = [on_fct[key][6] - off_fct[key][6] for key in off_fct]
    feedback = on["feedback"]
    result = {
        "evidence_level": "same-SHA 40-flow technical transport pair, one trace/seed",
        "source_sha": SOURCE_SHA,
        "trace_sha256": TRACE_SHA,
        "topology_sha256": TOPO_SHA,
        "off": off,
        "on": on,
        "pair": {
            "fct_improved_flows": sum(delta < 0 for delta in deltas),
            "fct_worsened_flows": sum(delta > 0 for delta in deltas),
            "fct_unchanged_flows": sum(delta == 0 for delta in deltas),
            "fct_delta_ns_min": min(deltas),
            "fct_delta_ns_max": max(deltas),
            "fct_raw_identical": off["fct_sha256"] == on["fct_sha256"],
            "ws18_raw_identical": off["ws18_sha256"] == on["ws18_sha256"],
            "control_hop_bytes_over_business_input_percent":
                100.0 * feedback["hop_bytes"] / EXPECTED_BYTES,
            "control_delivered_bytes_over_business_input_percent":
                100.0 * feedback["delivered_bytes"] / EXPECTED_BYTES,
            "mean_transport_age_ns": feedback["age_sum_ns"] / feedback["delivered"],
            "mean_sample_age_ns": feedback["sample_age_sum_ns"] / feedback["delivered"],
            "report_bytes": feedback["delivered_bytes"] / feedback["delivered"],
        },
        "limits": [
            "Ratios divide summed per-hop control bytes by application input bytes; they are not link-utilization percentages.",
            "No upstream CE differentiation or feedback-based routing decision occurred in this input.",
            "One fixed trace/seed and one 10-us interval cannot establish an optimal interval, a safety SLO, or efficacy.",
            "The stock FCT analyzer time window would exclude early QPs; all 40 completed QPs are used here.",
        ],
    }
    if args.old_on:
        result["cross_version_packet_size"] = old_version_cost(args.old_on, on)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print("Wrote %s" % args.out)


if __name__ == "__main__":
    main()
