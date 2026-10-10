#!/usr/bin/env python3
"""Read-only path concentration audit of the verified WS-26 MoE hop cells."""

import collections
import hashlib
import json
from pathlib import Path

import verify_ws26_moe_hop_diagnostic as verifier


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/research/evidence/ws26-failure-path-concentration.json"
MIN_PAIR_QPS = 8


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distribution(port_bytes):
    total = sum(port_bytes.values())
    if total == 0:
        raise RuntimeError("Empty port distribution")
    shares = [value / total for value in port_bytes.values()]
    return {"bytes": total, "ports_used": len(port_bytes),
            "hhi": sum(share * share for share in shares),
            "largest_port_share": max(shares)}


def summarize(groups, minimum_qps=1):
    selected = [group for group in groups.values() if group["qps"] >= minimum_qps]
    bytes_total = sum(sum(group["port_bytes"].values()) for group in selected)
    if not bytes_total:
        return {"groups": 0, "qps": 0, "bytes": 0,
                "weighted_hhi": None, "weighted_largest_port_share": None}
    weighted_hhi = 0
    weighted_largest = 0
    for group in selected:
        dist = distribution(group["port_bytes"])
        weighted_hhi += dist["hhi"] * dist["bytes"]
        weighted_largest += dist["largest_port_share"] * dist["bytes"]
    return {"groups": len(selected), "qps": sum(group["qps"] for group in selected),
            "bytes": bytes_total, "weighted_hhi": weighted_hhi / bytes_total,
            "weighted_largest_port_share": weighted_largest / bytes_total}


def new_group():
    return {"qps": 0, "port_bytes": collections.Counter()}


def add(groups, key, port, bytes_count):
    group = groups[key]
    group["qps"] += 1
    group["port_bytes"][port] += bytes_count


def read_cell(cell, plan):
    verified = verifier.check(cell, plan)
    folder = ROOT / "results" / cell["id"]
    trace = verifier.trace_qps(folder / "config/traffic_trace.txt")
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    finish_ns = {}
    with verifier.raw_fct(folder, metadata).open(encoding="ascii") as source:
        for line in source:
            values = list(map(int, line.split()))
            finish_ns[tuple(values[:4])] = values[5] + values[6]
    hosts, _, host_tors, neighbors = verifier.topology_maps(folder / "config/topology.txt")
    hop_rows = collections.defaultdict(list)
    log = folder / "logs/config.log"
    with log.open(encoding="utf-8", errors="replace") as source:
        for line in source:
            if line.startswith(("WS13_HOP ", "WS26_MOE_HOP ")):
                row = verifier.fields(line)
                key = row["src"], row["dst"], row["sport"], row["dport"]
                hop_rows[key].append(row)
    if set(hop_rows) != set(trace) or set(finish_ns) != set(trace):
        raise RuntimeError("Hop, FCT and trace identities differ: " + cell["id"])

    source_all = collections.defaultdict(new_group)
    source_destination = collections.defaultdict(new_group)
    destination_all = collections.defaultdict(new_group)
    destination_source = collections.defaultdict(new_group)
    classes = collections.Counter()
    start_range = collections.defaultdict(list)
    finish_range = collections.defaultdict(list)
    mismatched_hop_bytes = 0
    for key, item in trace.items():
        path = verifier.path_for(hop_rows[key], key[0], key[1], hosts,
                                 host_tors, neighbors)
        cls = "moe" if item["tag"] == 2 else "background"
        classes[cls] += 1
        start_range[cls].append(item["start_ns"])
        finish_range[cls].append(finish_ns[key])
        if len({row["bytes"] for row in path}) != 1:
            mismatched_hop_bytes += 1
        src_tor, dst_tor = host_tors[key[0]], host_tors[key[1]]
        if src_tor == dst_tor:
            continue
        source_port = path[0]["port"]
        source_bytes = path[0]["bytes"]
        if path[-2]["port"] - 1 not in neighbors[path[-2]["switch"]]:
            raise RuntimeError("Missing destination ingress edge")
        if neighbors[path[-2]["switch"]][path[-2]["port"] - 1] != dst_tor:
            raise RuntimeError("Penultimate hop does not reach destination ToR")
        incoming_switch = path[-2]["switch"]
        incoming_bytes = path[-2]["bytes"]
        add(source_all, (cls, src_tor), source_port, source_bytes)
        add(source_destination, (cls, src_tor, dst_tor), source_port, source_bytes)
        add(destination_all, (cls, dst_tor), incoming_switch, incoming_bytes)
        add(destination_source, (cls, dst_tor, src_tor), incoming_switch, incoming_bytes)

    metrics = {}
    group_details = {}
    for cls in ("moe", "background"):
        by_class = lambda groups: {key: value for key, value in groups.items()
                                   if key[0] == cls}
        pair_source = by_class(source_destination)
        pair_destination = by_class(destination_source)
        metrics[cls] = {
            "total_source_uplink_by_source_tor": summarize(by_class(source_all)),
            "source_uplink_by_destination_tor_min_8_qps": summarize(pair_source, MIN_PAIR_QPS),
            "total_destination_ingress_by_destination_tor": summarize(by_class(destination_all)),
            "destination_ingress_by_source_tor_min_8_qps": summarize(pair_destination, MIN_PAIR_QPS),
            "source_destination_groups_all": len(pair_source),
            "source_destination_groups_min_8_qps": sum(
                group["qps"] >= MIN_PAIR_QPS for group in pair_source.values()),
            "cross_tor_qps": sum(group["qps"] for group in pair_source.values()),
            "all_qps": classes[cls],
            "trace_start_ns_min": min(start_range[cls]),
            "trace_start_ns_max": max(start_range[cls]),
            "observed_finish_ns_min": min(finish_range[cls]),
            "observed_finish_ns_max": max(finish_range[cls]),
        }
        group_details[cls] = {
            "%s:%s" % (key[1], key[2]): {
                "qps": value["qps"],
                "source_uplink": distribution(value["port_bytes"]),
                "destination_ingress": distribution(
                    pair_destination[(cls, key[2], key[1])]["port_bytes"]),
            }
            for key, value in pair_source.items() if value["qps"] >= MIN_PAIR_QPS
        }
    return {"id": cell["id"], "seed": cell["seed"], "mode": cell["mode"],
            "source_sha": verifier.SOURCE_SHA,
            "trace_sha256": cell["trace_sha256"],
            "fct_sha256": verified["fct_sha256"],
            "config_log_sha256": sha256(log),
            "mismatched_hop_bytes_qps": mismatched_hop_bytes,
            "metrics": metrics, "qualified_groups": group_details}


def paired_deltas(cells):
    by_seed = collections.defaultdict(dict)
    for cell in cells:
        by_seed[cell["seed"]][cell["mode"]] = cell
    output = []
    for seed in sorted(by_seed):
        left, right = by_seed[seed]["fecmp"], by_seed[seed]["classlane4"]
        if left["trace_sha256"] != right["trace_sha256"]:
            raise RuntimeError("Paired trace differs: " + str(seed))
        classes = {}
        for cls in ("moe", "background"):
            a, b = left["metrics"][cls], right["metrics"][cls]
            keys = ("total_source_uplink_by_source_tor",
                    "source_uplink_by_destination_tor_min_8_qps",
                    "total_destination_ingress_by_destination_tor",
                    "destination_ingress_by_source_tor_min_8_qps")
            classes[cls] = {}
            for key in keys:
                first, second = a[key], b[key]
                if (first["groups"], first["qps"], first["bytes"]) != (
                        second["groups"], second["qps"], second["bytes"]):
                    raise RuntimeError("Paired distribution denominator differs")
                classes[cls][key] = {"ecmp": first, "classlane4": second,
                                     "hhi_difference": (second["weighted_hhi"] -
                                                        first["weighted_hhi"])
                                     if first["weighted_hhi"] is not None else None}
            groups_a, groups_b = left["qualified_groups"][cls], right["qualified_groups"][cls]
            if set(groups_a) != set(groups_b):
                raise RuntimeError("Qualified group identities differ")
            changes = []
            for group_id in groups_a:
                before, after = groups_a[group_id], groups_b[group_id]
                if before["qps"] != after["qps"]:
                    raise RuntimeError("Paired group QP count differs")
                changes.append({"source_destination_tor": group_id,
                                "qps": before["qps"],
                                "bytes": before["source_uplink"]["bytes"],
                                "source_uplink_hhi_difference":
                                    after["source_uplink"]["hhi"] - before["source_uplink"]["hhi"],
                                "destination_ingress_hhi_difference":
                                    after["destination_ingress"]["hhi"] - before["destination_ingress"]["hhi"]})
            classes[cls]["largest_absolute_group_changes"] = sorted(
                changes, key=lambda row: (-abs(row["source_uplink_hhi_difference"]),
                                          row["source_destination_tor"]))[:5]
        output.append({"seed": seed, "classes": classes})
    return output


def main():
    plan = verifier.load_plan()
    cells = [read_cell(cell, plan) for cell in plan["cells"]
             if cell["stage"] == "paired_high_diagnostic"]
    if len(cells) != 8:
        raise RuntimeError("Expected eight high diagnostic cells")
    pairs = paired_deltas(cells)
    for cell in cells:
        cell.pop("qualified_groups")
    output = {
        "purpose": "Ofan-inspired read-only destination-conditioned path audit",
        "source_sha": verifier.SOURCE_SHA,
        "plan_sha256": verifier.PLAN_SHA256,
        "topology_sha256": verifier.TOPOLOGY_SHA256,
        "minimum_qps_per_source_destination_tor_group": MIN_PAIR_QPS,
        "metrics_definition": {
            "weight": "observed data bytes at each hop, summed over entire cell",
            "hhi": "sum of squared port byte shares; larger means more concentration",
            "total_source": "per source ToR, combine all destination ToRs within one class",
            "conditional_source": "per source ToR and destination ToR, minimum eight QPs",
            "total_destination": "per destination ToR, combine all source ToRs within one class",
            "conditional_destination": "per destination ToR and source ToR, minimum eight QPs",
            "downward_port": "penultimate switch sending into destination ToR",
        },
        "limits": [
            "Whole-cell byte shares do not measure simultaneous link load or queue causality",
            "MoE and background finish windows differ; classes are not pooled",
            "At least eight QPs per source/destination ToR is descriptive, not a significance threshold",
            "Conditional source and destination HHI can coincide through deterministic path mapping; they are not independent measurements",
            "Results reuse four revealed seeds and are not new efficacy samples",
        ],
        "cells": cells, "pairs": pairs,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    print(json.dumps({"file": str(OUT), "sha256": sha256(OUT),
                      "verified_high_cells": len(cells)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
