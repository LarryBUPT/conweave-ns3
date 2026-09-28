#!/usr/bin/env python3
"""Recompute a conservative WS-21 feedback/logging budget from WS-19 raw.

This is read-only with respect to experimental results. No simulation is run.
"""
import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RUN_MAP = ROOT / "docs/research/evidence/ws19-pilot-run-map-v1.json"
OUTPUT = ROOT / "docs/research/evidence/ws21-static-budget.json"
TOPOLOGY = ROOT / "config/topo_1280_400G_400G_OS1.txt"
SOURCE_SHA = "b52e66f0fbf786fb57672b12a5633cf45b9311c1"
REPORT_PERIOD_NS = 10_000
SAMPLE_PERIOD_NS = 1_000
REPORT_LOGICAL_BYTES = 16
SAMPLE_RECORD_BYTES = 32


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def topology():
    lines = TOPOLOGY.read_text(encoding="utf-8").splitlines()
    count = tuple(map(int, lines[0].split()))
    assert count == (1856, 576, 3840)
    result = {}
    neighbors = defaultdict(list)
    for line in lines[2:]:
        a, b = map(int, line.split()[:2])
        neighbors[a].append(b)
        neighbors[b].append(a)
        if a < 1280:
            assert a not in result
            result[a] = b
        if b < 1280:
            assert b not in result
            result[b] = a
    assert len(result) == 1280
    return result, neighbors


def last_ingress_sets(destination, neighbors):
    """Topology-only shortest-path ingress possibilities for each first hop."""
    distance = {destination: 0}
    pending = deque([destination])
    while pending:
        node = pending.popleft()
        for adjacent in neighbors[node]:
            if adjacent not in distance:
                distance[adjacent] = distance[node] + 1
                pending.append(adjacent)
    last = {destination: set()}
    for node in sorted(distance, key=lambda n: distance[n]):
        if node == destination:
            continue
        if distance[node] == 1:
            last[node] = {node}
        else:
            last[node] = set().union(*(
                last[n] for n in neighbors[node] if distance[n] == distance[node] - 1
            ))
    return distance, last


def cell(row, tors, neighbors, topology_cache):
    base = RESULTS / row["id"]
    meta = json.loads((base / "metadata.json").read_text(encoding="utf-8"))
    assert meta["status"] == "SUCCEEDED" and meta["git_commit"] == SOURCE_SHA
    assert meta["input_flow_sha256"] == row["trace_sha256"]
    trace = base / "config/traffic_trace.txt"
    assert sha(trace) == row["trace_sha256"]
    assert sha(base / "config/topology.txt") == sha(TOPOLOGY)
    lines = trace.read_text(encoding="utf-8").splitlines()
    assert int(lines[0]) == len(lines) - 1 == 16576
    pairs = set()
    pair_by_id = {}
    pair_counts = Counter()
    source_tors, destination_tors, background_hosts = set(), set(), set()
    tags = Counter()
    for flow_id, line in enumerate(lines[1:]):
        src, dst, _, _, _, tag = line.split()
        src, dst, tag = int(src), int(dst), int(tag)
        tags[tag] += 1
        if tag == 1:
            background_hosts.add(dst)
        if tag == 2 and tors[src] != tors[dst]:
            pair = (tors[src], tors[dst])
            pairs.add(pair)
            pair_by_id[flow_id] = pair
            pair_counts[pair] += 1
            source_tors.add(pair[0])
            destination_tors.add(pair[1])
    assert tags == {1: 192, 2: 16384}
    raw_id = str(meta["raw_directory"])
    timing = base / "raw" / raw_id / (raw_id + "_out_ws18.txt")
    demands, finishes, background_totals, moe_finishes = [], [], [], []
    pair_spans = {}
    ids = set()
    for line in timing.read_text(encoding="utf-8").splitlines():
        v = list(map(int, line.split()))
        assert len(v) == 12 and v[0] not in ids
        ids.add(v[0])
        demands.append(v[7])
        finishes.append(v[9])
        if v[0] in pair_by_id:
            pair = pair_by_id[v[0]]
            if pair not in pair_spans:
                pair_spans[pair] = [v[7], v[9]]
            else:
                pair_spans[pair][0] = min(pair_spans[pair][0], v[7])
                pair_spans[pair][1] = max(pair_spans[pair][1], v[9])
        if v[5] == 1:
            background_totals.append(v[11])
        elif v[5] == 2:
            moe_finishes.append(v[9])
    assert len(ids) == len(lines) - 1 and len(background_totals) == 192
    assert len(moe_finishes) == 16384
    assert set(pair_spans) == pairs
    ambiguous_ingress_pairs = 0
    first_hop_counts = {}
    for source, destination in pairs:
        if destination not in topology_cache:
            topology_cache[destination] = last_ingress_sets(destination, neighbors)
        distance, ingress = topology_cache[destination]
        first_neighbors = [n for n in neighbors[source]
                           if distance[n] == distance[source] - 1]
        first_hop_counts[(source, destination)] = len(first_neighbors)
        assert len(first_neighbors) == 8
        seen = set()
        ambiguous = False
        for first in first_neighbors:
            if seen.intersection(ingress[first]):
                ambiguous = True
            seen.update(ingress[first])
        ambiguous_ingress_pairs += ambiguous
    window_ns = max(finishes) - min(demands)
    report_slots = math.ceil(window_ns / REPORT_PERIOD_NS)
    sample_slots = math.ceil(window_ns / SAMPLE_PERIOD_NS)
    # Candidates are selected from the four-tuple for EACH flow, so a ToR
    # pair can use more than two distinct ports across its flows. Without
    # reproducing C++ hashing and dynamic routing, two is a lower bound and
    # min(8, 2*flow_count) is a safe topology/input upper bound.
    keys_lower = 2 * len(pairs)
    keys_upper = sum(min(first_hop_counts[pair], 2 * n)
                     for pair, n in pair_counts.items())
    pair_window_report_slots = {
        pair: math.ceil((last - first) / REPORT_PERIOD_NS)
        for pair, (first, last) in pair_spans.items()
    }
    pair_window_reports_lower = 2 * sum(pair_window_report_slots.values())
    pair_window_reports_upper = sum(
        pair_window_report_slots[pair] * min(first_hop_counts[pair], 2 * n)
        for pair, n in pair_counts.items()
    )
    return {
        "experiment_id": row["id"],
        "seed": row["seed"],
        "hotspot": row["hotspot"],
        "trace_sha256": row["trace_sha256"],
        "source_tors_with_moe": len(source_tors),
        "destination_tors_with_moe": len(destination_tors),
        "cross_tor_source_destination_pairs": len(pairs),
        "topology_only_destination_ingress_ambiguous_pairs": ambiguous_ingress_pairs,
        "cross_tor_moe_flows": len(pair_by_id),
        "singleton_source_destination_pairs": sum(n == 1 for n in pair_counts.values()),
        "moe_flows_in_singleton_pairs": sum(n for n in pair_counts.values() if n == 1),
        "feedback_keys_lower_bound": keys_lower,
        "feedback_keys_upper_bound": keys_upper,
        "background_destination_hosts": len(background_hosts),
        "background_max_total_ns": max(background_totals),
        "moe_last_finish_minus_first_demand_ns": max(moe_finishes) - min(demands),
        "whole_cell_window_ns": window_ns,
        "conservative_periodic_report_slots": report_slots,
        "whole_window_periodic_reports_lower_bound": keys_lower * report_slots,
        "whole_window_periodic_reports_upper_bound": keys_upper * report_slots,
        "whole_window_logical_payload_bytes_lower_bound": (
            keys_lower * report_slots * REPORT_LOGICAL_BYTES
        ),
        "whole_window_logical_payload_bytes_upper_bound": (
            keys_upper * report_slots * REPORT_LOGICAL_BYTES
        ),
        "pair_window_reports_lower_bound": pair_window_reports_lower,
        "pair_window_reports_upper_bound": pair_window_reports_upper,
        "pair_window_logical_payload_bytes_lower_bound": (
            pair_window_reports_lower * REPORT_LOGICAL_BYTES
        ),
        "pair_window_logical_payload_bytes_upper_bound": (
            pair_window_reports_upper * REPORT_LOGICAL_BYTES
        ),
        "conservative_dense_egress_sample_slots": sample_slots,
        "conservative_dense_egress_sample_bytes": (
            len(background_hosts) * sample_slots * SAMPLE_RECORD_BYTES
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    mapping = json.loads(RUN_MAP.read_text(encoding="utf-8"))
    rows = [r for r in mapping["runs"] if r["arm"] == "ecmp" and r["background"] == 192]
    assert len(rows) == 6
    tors, neighbors = topology()
    topology_cache = {}
    cells = [cell(row, tors, neighbors, topology_cache)
             for row in sorted(rows, key=lambda r: (r["hotspot"], r["seed"]))]
    result = {
        "role": "static conservative budget using six existing WS-19 ECMP raw cells; no new simulation",
        "source_sha": SOURCE_SHA,
        "topology_sha256": sha(TOPOLOGY),
        "report_period_ns": REPORT_PERIOD_NS,
        "report_logical_bytes": REPORT_LOGICAL_BYTES,
        "egress_sample_period_ns": SAMPLE_PERIOD_NS,
        "egress_sample_record_bytes": SAMPLE_RECORD_BYTES,
        "assumptions": [
            "Each flow hashes two candidates; distinct ports per source/destination ToR pair are bounded below by two and above by min(8, 2*pair flow count). Actual hashing was not replayed.",
            "All bounded candidate keys report for the full cell from earliest demand to latest finish; this is a hypothetical worst-duration schedule, not measured traffic.",
            "Each background destination host egress has one fixed-size sample every microsecond for the full cell; this is a dense upper budget, not a measured log.",
            "No actual packet/header/transport cost or feedback arrival delay is known; logical payload bytes are not wire bytes.",
            "Destination ingress ambiguity is tested on topology-only shortest paths; zero ambiguity is not a runtime observation or implemented mapping.",
        ],
        "cells": cells,
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.verify:
        assert OUTPUT.read_text(encoding="utf-8") == rendered
    else:
        OUTPUT.write_text(rendered, encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
