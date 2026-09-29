#!/usr/bin/env python3
"""Recompute WS-21 compact-feedback interval costs and paired disturbances."""

import argparse
import datetime
import hashlib
import json
import math
import re
from pathlib import Path

from verify_ws21_feedback_longtail import feedback_summary
from verify_ws21_identity import verify as verify_identity


SOURCE_SHA = "2c14d3b4c952a9cece89a9de14216709b604706f"
TRACE_SHA = "9996372ea22158ca995937c727b6fef20559e0ce910b22e77529d9a8061b0cc3"
TOPOLOGY_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
EXPECTED_FLOWS = 16576
EXPECTED_BYTES = 1744830464
CELLS = {
    5: "20260929-221400-ws21c-v2-tail-5us",
    10: "20260929-221100-ws21c-v2-tail-10us",
    20: "20260929-221200-ws21c-v2-tail-20us",
    40: "20260929-221300-ws21c-v2-tail-40us",
}
OFF_ID = "20260929-221000-ws21c-v2-tail-off"
OLD_ON_ID = "20260929-171900-ws21-feedback-longtail-on"
FEEDBACK_RE = re.compile(r"^WS21_FEEDBACK\s+(.*)$", re.M)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values, p):
    values = sorted(values)
    return values[max(0, math.ceil(len(values) * p) - 1)]


def read_fct(path):
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if not fields:
            continue
        if len(fields) < 8:
            raise ValueError("duplicate or malformed FCT row")
        key = tuple(fields[:6])
        if key in rows:
            raise ValueError("duplicate FCT input tuple")
        rows[key] = int(fields[6])
    return rows


def read_ws18(path):
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        values = [int(value) for value in line.split()]
        if len(values) != 12:
            raise ValueError("WS18 row must contain 12 fields")
        flow_id, src, dst, sport, dport, tag, size, demand, release, finish, wait, total = values
        key = (src, dst, sport, dport)
        if key in rows or release - demand != wait or finish - demand != total:
            raise ValueError("duplicate QP or inconsistent WS18 timing")
        rows[key] = {"id": flow_id, "tag": tag, "size": size, "demand": demand,
                     "release": release, "finish": finish, "wait": wait, "total": total}
    return rows


def fct_stats(rows):
    return {"count": len(rows), "p50_us": round(percentile(rows, .50) / 1000, 3),
            "p90_us": round(percentile(rows, .90) / 1000, 3),
            "p99_us": round(percentile(rows, .99) / 1000, 3),
            "max_us": round(max(rows) / 1000, 3),
            "percentile_method": "nearest-rank"}


def inspect_cell(results, experiment_id, interval_us):
    base = results / experiment_id
    meta = json.loads((base / "metadata.json").read_text(encoding="utf-8"))
    params = meta["parameters"]
    expected = {"lb": "ws18", "pfc": 0, "irn": 1, "ws18_admission": 0,
                "ws18_path": 0, "ws13_diag": 1, "ws21_identity": 1,
                "ws21_feedback": 1, "ws21_feedback_interval_ns": interval_us * 1000,
                "ws21_port_events": 0}
    if meta.get("status") != "SUCCEEDED" or meta.get("git_commit") != SOURCE_SHA:
        raise ValueError("{} status/source mismatch".format(experiment_id))
    if meta.get("input_flow_sha256") != TRACE_SHA or meta.get("topology_sha256") != TOPOLOGY_SHA:
        raise ValueError("{} input fingerprint mismatch".format(experiment_id))
    if (sha256(base / "config" / "traffic_trace.txt") != TRACE_SHA or
            sha256(base / "config" / "topology.txt") != TOPOLOGY_SHA):
        raise ValueError("{} config snapshot fingerprint mismatch".format(experiment_id))
    if meta.get("seed") != 1 or any(params.get(k) != v for k, v in expected.items()):
        raise ValueError("{} parameter/seed mismatch".format(experiment_id))
    raw_id = str(meta["raw_directory"])
    raw = base / "raw" / raw_id
    fct_path = raw / (raw_id + "_out_fct.txt")
    ws18_path = raw / (raw_id + "_out_ws18.txt")
    identity_path = raw / (raw_id + "_out_ws21_identity.txt")
    fct = read_fct(fct_path)
    ws18 = read_ws18(ws18_path)
    if len(fct) != EXPECTED_FLOWS or len(ws18) != EXPECTED_FLOWS:
        raise ValueError("{} flow completion mismatch".format(experiment_id))
    if sum(row["size"] for row in ws18.values()) != EXPECTED_BYTES:
        raise ValueError("{} application byte total mismatch".format(experiment_id))
    if len(fct) != len(ws18):
        raise ValueError("{} FCT and WS18 record counts differ".format(experiment_id))
    for fields, elapsed_ns in fct.items():
        qp_key = tuple(int(value) for value in fields[:4])
        flow = ws18.get(qp_key)
        if (flow is None or int(fields[4]) != flow["size"] or
                int(fields[5]) != flow["release"] or elapsed_ns != flow["finish"] - flow["release"]):
            raise ValueError("{} FCT row does not reconcile with WS18 QP timing".format(experiment_id))
    identity = verify_identity(ws18_path, identity_path, base / "config" / "topology.txt")
    if not identity.get("complete"):
        raise ValueError("{} path identity failure".format(experiment_id))
    feedback = feedback_summary(raw / "config.log")
    if feedback["generated"] <= 0:
        raise ValueError("{} has no generated feedback reports".format(experiment_id))
    if feedback["generated"] != feedback["delivered"] + feedback["expired"]:
        raise ValueError("{} generated reports do not reconcile with delivery/expiry".format(experiment_id))
    age_bin_total = sum(feedback.get(name, 0) for name in
                        ("age_lt_1us", "age_1_2us", "age_2_5us", "age_5_10us", "age_gt_10us"))
    if age_bin_total != feedback["generated"]:
        raise ValueError("{} report-age bins do not reconcile with generated reports".format(experiment_id))
    if feedback["rejected"] or feedback["hop_rejects"] or feedback["sequence_gaps"]:
        raise ValueError("{} has rejected, hop-rejected, or sequence-gap reports".format(experiment_id))
    if feedback["hop_enqueues"] != feedback["hop_dequeues"]:
        raise ValueError("{} per-hop feedback queue does not balance".format(experiment_id))
    if feedback["delivered"] and feedback["delivered_bytes"] != feedback["delivered"] * 60:
        raise ValueError("{} delivered packet bytes do not reconcile at 60 bytes/report".format(experiment_id))
    if feedback["hop_bytes"] != feedback["hop_enqueues"] * 60:
        raise ValueError("{} per-hop packet bytes do not reconcile at 60 bytes/hop".format(experiment_id))
    for filename in ("config.log", "simulation.log", "worker.log"):
        path = base / "logs" / filename
        if not path.exists():
            path = raw / filename
        if not path.exists() or path.stat().st_size > 50 * 1024 * 1024:
            raise ValueError("{} missing/oversized {}".format(experiment_id, filename))
    resources = json.loads((base / "logs" / "resource-summary.json").read_text(encoding="utf-8"))
    if resources.get("final_status") != "SUCCEEDED":
        raise ValueError("{} resource receipt is not terminal-success".format(experiment_id))
    samples = [json.loads(line) for line in
               (base / "logs" / "resource-samples.jsonl").read_text(encoding="utf-8").splitlines()]
    if not samples or len(samples) != resources.get("samples"):
        raise ValueError("{} resource sample count mismatch".format(experiment_id))
    for label, actual in (("peak_tree_rss_mib", max(point["process_tree_rss_mib"] for point in samples)),
                          ("minimum_mem_available_gib", min(point["mem_available_gib"] for point in samples)),
                          ("minimum_free_gib", min(point["free_gib"] for point in samples))):
        if not math.isclose(resources.get(label, float("nan")), actual, rel_tol=0, abs_tol=1e-6):
            raise ValueError("{} resource {} does not match samples".format(experiment_id, label))
    if (resources.get("peak_tree_rss_mib", float("inf")) > 8192 or
            resources.get("minimum_mem_available_gib", 0) < 16 or
            resources.get("minimum_free_gib", 0) < 100):
        raise ValueError("{} exceeded an experiment resource stop limit".format(experiment_id))

    flow_stats = {}
    for name, pred in (("all", lambda row: True), ("moe_8k", lambda row: row["size"] == 8192),
                       ("background_8m", lambda row: row["size"] == 8388608)):
        selected = [row for row in ws18.values() if pred(row)]
        flow_stats[name] = fct_stats([row["total"] for row in selected])
    moe_rounds = {}
    for row in ws18.values():
        if row["size"] == 8192:
            batch = moe_rounds.setdefault(row["demand"], [])
            batch.append(row["finish"])
    round_times = [max(finishes) - demand for demand, finishes in moe_rounds.items()]
    if len(round_times) != 8:
        raise ValueError("{} does not contain eight MoE rounds".format(experiment_id))
    params_runtime = (meta["finished_utc"], meta["started_utc"])
    runtime_seconds = int((datetime.datetime.strptime(params_runtime[0], "%Y-%m-%dT%H:%M:%SZ") -
                           datetime.datetime.strptime(params_runtime[1], "%Y-%m-%dT%H:%M:%SZ")).total_seconds())
    report = feedback["delivered"]
    return {
        "experiment_id": experiment_id,
        "interval_us": interval_us,
        "status": meta["status"],
        "source_sha": meta["git_commit"],
        "trace_sha256": meta["input_flow_sha256"],
        "topology_sha256": meta["topology_sha256"],
        "seed": meta["seed"],
        "raw_directory": raw_id,
        "started_utc": params_runtime[1],
        "finished_utc": params_runtime[0],
        "runtime_seconds": runtime_seconds,
        "fct_sha256": sha256(fct_path),
        "ws18_sha256": sha256(ws18_path),
        "flow_count": len(fct),
        "application_bytes": sum(row["size"] for row in ws18.values()),
        "identity": identity,
        "log_bytes": {name: (base / "logs" / name).stat().st_size
                       if (base / "logs" / name).exists()
                       else (raw / name).stat().st_size for name in ("config.log", "simulation.log", "worker.log")},
        "resource_summary": resources,
        "fct_by_group": flow_stats,
        "moe_round_count": len(round_times),
        "moe_round_mean_us": round(sum(round_times) / float(len(round_times)) / 1000, 3),
        "moe_round_max_us": round(max(round_times) / 1000, 3),
        "feedback": feedback,
        "feedback_expired_fraction_pct": round(feedback["expired"] * 100.0 /
                                                  feedback["generated"], 6),
        "mean_generation_to_arrival_us": round(feedback["age_sum_ns"] /
                                                float(feedback["generated"]) / 1000, 3),
        "mean_window_end_to_arrival_us": round(feedback["sample_age_sum_ns"] /
                                                float(feedback["generated"]) / 1000, 3),
        "feedback_packet_bytes_per_report": (feedback["delivered_bytes"] / float(report)
                                               if report else None),
        "delivered_bytes_per_application_byte": feedback["delivered_bytes"] / float(EXPECTED_BYTES),
        "hop_bytes_per_application_byte": feedback["hop_bytes"] / float(EXPECTED_BYTES),
    }, fct, ws18


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--output", type=Path,
                        default=Path("docs/research/evidence/ws21-compact-longtail-interval-analysis.json"))
    args = parser.parse_args()
    off_base = args.results / OFF_ID
    off_meta = json.loads((off_base / "metadata.json").read_text(encoding="utf-8"))
    off_raw = off_base / "raw" / str(off_meta["raw_directory"])
    off_fct_path = off_raw / (str(off_meta["raw_directory"]) + "_out_fct.txt")
    off_ws18_path = off_raw / (str(off_meta["raw_directory"]) + "_out_ws18.txt")
    if (off_meta.get("status") != "SUCCEEDED" or off_meta.get("git_commit") != SOURCE_SHA or
            off_meta.get("input_flow_sha256") != TRACE_SHA or off_meta.get("topology_sha256") != TOPOLOGY_SHA):
        raise ValueError("off baseline metadata/fingerprint mismatch")
    if (sha256(off_base / "config" / "traffic_trace.txt") != TRACE_SHA or
            sha256(off_base / "config" / "topology.txt") != TOPOLOGY_SHA):
        raise ValueError("off baseline config snapshot fingerprint mismatch")
    if sha256(off_fct_path) != "964b7f757f93397d56f2ab1434aa4647dfc4b23d083ecd08ef6486fac7f0e18f" or \
            sha256(off_ws18_path) != "e12ab3388a27f2ccec9b85acf1d590680816e7b7d91a9e22b90e2a9e58e5fbab":
        raise ValueError("off baseline fingerprints changed")
    off_fct, off_ws18 = read_fct(off_fct_path), read_ws18(off_ws18_path)
    if len(off_fct) != EXPECTED_FLOWS or len(off_ws18) != EXPECTED_FLOWS:
        raise ValueError("off baseline completion mismatch")
    if len(off_fct) != len(off_ws18):
        raise ValueError("off baseline FCT and WS18 record counts differ")
    for fields, elapsed_ns in off_fct.items():
        flow = off_ws18.get(tuple(int(value) for value in fields[:4]))
        if (flow is None or int(fields[4]) != flow["size"] or
                int(fields[5]) != flow["release"] or elapsed_ns != flow["finish"] - flow["release"]):
            raise ValueError("off baseline FCT row does not reconcile with WS18")
    off_group_stats = {}
    for name, pred in (("all", lambda row: True), ("moe_8k", lambda row: row["size"] == 8192),
                       ("background_8m", lambda row: row["size"] == 8388608)):
        selected = [row for row in off_ws18.values() if pred(row)]
        off_group_stats[name] = fct_stats([row["total"] for row in selected])
    off_moe_rounds = {}
    for row in off_ws18.values():
        if row["size"] == 8192:
            off_moe_rounds.setdefault(row["demand"], []).append(row["finish"])
    off_round_times = [max(finishes) - demand for demand, finishes in off_moe_rounds.items()]
    if len(off_round_times) != 8:
        raise ValueError("off baseline does not contain eight MoE rounds")
    cells = []
    for interval, experiment_id in sorted(CELLS.items()):
        cell, fct, ws18 = inspect_cell(args.results, experiment_id, interval)
        if set(fct) != set(off_fct):
            raise ValueError("{} FCT input tuples differ from off".format(experiment_id))
        if set(ws18) != set(off_ws18):
            raise ValueError("{} WS18 QP keys differ from off".format(experiment_id))
        deltas = [fct[key] - off_fct[key] for key in fct]
        cell["paired_vs_off"] = {
            "fct_changed": sum(delta != 0 for delta in deltas),
            "fct_decreased": sum(delta < 0 for delta in deltas),
            "fct_increased": sum(delta > 0 for delta in deltas),
            "fct_unchanged": sum(delta == 0 for delta in deltas),
            "fct_delta_mean_ns": sum(deltas) / float(len(deltas)),
            "fct_delta_median_ns": percentile(deltas, .5),
            "fct_delta_min_ns": min(deltas),
            "fct_delta_max_ns": max(deltas),
            "demand_time_changed": sum(ws18[k]["demand"] != off_ws18[k]["demand"] for k in ws18),
            "release_time_changed": sum(ws18[k]["release"] != off_ws18[k]["release"] for k in ws18),
            "finish_time_changed": sum(ws18[k]["finish"] != off_ws18[k]["finish"] for k in ws18),
            "wait_time_changed": sum(ws18[k]["wait"] != off_ws18[k]["wait"] for k in ws18),
        }
        cells.append(cell)
    old_base = args.results / OLD_ON_ID
    old_meta = json.loads((old_base / "metadata.json").read_text(encoding="utf-8"))
    if (old_meta.get("status") != "SUCCEEDED" or old_meta.get("input_flow_sha256") != TRACE_SHA or
            old_meta.get("topology_sha256") != TOPOLOGY_SHA):
        raise ValueError("old-version on cell input/status mismatch")
    old_raw = old_base / "raw" / str(old_meta["raw_directory"])
    old_feedback = feedback_summary(old_raw / "config.log")
    new_10us = next(cell for cell in cells if cell["interval_us"] == 10)
    new_feedback = new_10us["feedback"]
    old_wire_bytes = old_feedback["delivered_bytes"] / float(old_feedback["delivered"])
    new_wire_bytes = new_feedback["delivered_bytes"] / float(new_feedback["delivered"])
    if old_feedback["hop_bytes"] != old_feedback["hop_enqueues"] * old_wire_bytes:
        raise ValueError("old-version hop-byte accounting mismatch")

    def dominates(left, right):
        a = (left["feedback"]["hop_bytes"], left["feedback"]["sample_age_max_ns"],
             left["feedback"]["expired"])
        b = (right["feedback"]["hop_bytes"], right["feedback"]["sample_age_max_ns"],
             right["feedback"]["expired"])
        return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))

    def frontier(group):
        return [cell["interval_us"] for cell in group
                if not any(dominates(other, cell) for other in group if other is not cell)]

    zero_expiry = [cell for cell in cells if cell["feedback"]["expired"] == 0]
    conditional_choices = []
    for age_cap in (20000, 20500, None):
        feasible = [cell for cell in zero_expiry
                    if age_cap is None or cell["feedback"]["sample_age_max_ns"] <= age_cap]
        minimum = min(feasible, key=lambda cell: cell["feedback"]["hop_bytes"]) if feasible else None
        conditional_choices.append({
            "age_cap_ns": age_cap,
            "requires_zero_expiry": True,
            "selected_interval_us": minimum["interval_us"] if minimum else None,
            "selected_hop_bytes": minimum["feedback"]["hop_bytes"] if minimum else None,
            "interpretation": "illustrative constraint on this trace, not an established business SLO",
        })
    result = {
        "evidence_level": "single_trace_feedback_transport_cost_and_disturbance_matrix",
        "source_sha": SOURCE_SHA,
        "trace_sha256": TRACE_SHA,
        "topology_sha256": TOPOLOGY_SHA,
        "ns3_seed": 1,
        "off_experiment_id": OFF_ID,
        "off_fct_sha256": sha256(off_fct_path),
        "off_ws18_sha256": sha256(off_ws18_path),
        "off_baseline": {
            "flow_count": len(off_fct),
            "application_bytes": sum(row["size"] for row in off_ws18.values()),
            "fct_by_group": off_group_stats,
            "moe_round_count": len(off_round_times),
            "moe_round_mean_us": round(sum(off_round_times) / float(len(off_round_times)) / 1000, 3),
            "moe_round_max_us": round(max(off_round_times) / 1000, 3),
        },
        "sampling_unit": "one fixed demand trace; flows are paired observations, not independent repetitions",
        "percentile_method": "nearest-rank",
        "age_definitions": {
            "age_max_ns": "generation time to report arrival; reports older than 10 us are explicitly counted expired and not cached",
            "sample_age_max_ns": "window end time to report arrival; distinct from generation-to-arrival age",
        },
        "cells": cells,
        "cross_version_10us_packet_cost": {
            "old_experiment_id": OLD_ON_ID,
            "old_source_sha": old_meta["git_commit"],
            "old_reports": old_feedback["delivered"],
            "old_packet_bytes": old_wire_bytes,
            "old_hop_bytes": old_feedback["hop_bytes"],
            "new_experiment_id": new_10us["experiment_id"],
            "new_reports": new_feedback["delivered"],
            "new_packet_bytes": new_wire_bytes,
            "new_hop_bytes": new_feedback["hop_bytes"],
            "packet_byte_reduction_pct": (old_wire_bytes - new_wire_bytes) / old_wire_bytes * 100.0,
            "observed_total_hop_byte_reduction_pct": (
                old_feedback["hop_bytes"] - new_feedback["hop_bytes"]) /
                float(old_feedback["hop_bytes"]) * 100.0,
            "limit": "different source SHAs and report counts; technical packet-size comparison, not a routing-effect or causal total-byte estimate",
        },
        "observed_cost_freshness_expiry_pareto_us": frontier(cells),
        "observed_zero_expiry_cost_freshness_pareto_us": frontier(zero_expiry),
        "conditional_minimum_cost_examples": conditional_choices,
        "limits": [
            "Feedback cache is not consumed by route selection; these data do not measure routing benefit.",
            "FCT changes are communication perturbations observed on one fixed trace, not independent statistical samples.",
            "Expired reports are counted and discarded before cache update; route-level stale fallback is not exercised because route selection does not read this cache.",
            "No local HELLO/ACK heartbeat was implemented or included in communication-cost totals.",
            "No business SLO or cost preference was provided; report a Pareto set rather than a unique optimum.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("Wrote {}".format(args.output))


if __name__ == "__main__":
    main()
