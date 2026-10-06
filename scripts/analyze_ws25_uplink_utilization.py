"""Supplementary 192-background uplink utilization from verified WS-25 raw counters.

The fixed 1 ms window is common to all 144 main-load cells. This script does
not change the frozen efficacy analysis or its primary outcomes.
"""

import hashlib
import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/research/evidence/ws25-v1fix-formal-plan.json"
ANALYSIS = ROOT / "docs/research/evidence/ws25-v1fix-formal-analysis.json"
OUTPUT = ROOT / "docs/research/evidence/ws25-v1fix-uplink-utilization.json"
START_NS = 2_000_000_000
END_NS = 2_001_000_000
INTERVAL_NS = 10_000
CAPACITY_GBPS = 400
WINDOW_CAPACITY_BYTES = CAPACITY_GBPS * (END_NS - START_NS) / 8


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def median(values):
    return statistics.median(values)


def verify_topology(path):
    with path.open(encoding="ascii") as stream:
        nodes, switches, edges = map(int, stream.readline().split())
        stream.readline()  # switch IDs
        links = [stream.readline().split() for _ in range(edges)]
    if nodes != 1856 or switches != 576 or edges != 3840:
        raise ValueError("Unexpected formal topology dimensions")
    uplinks = [row for row in links if 1280 <= int(row[0]) < 1440
               and int(row[1]) >= 1440]
    if len(uplinks) != 1280 or any(row[2] != "400Gbps" for row in uplinks):
        raise ValueError("Formal ToR uplink capacity is not 400 Gbps")


def read_window(path):
    first, last, previous, counts = {}, {}, {}, {}
    timestamps = set()
    last_stamp = START_NS
    with path.open(encoding="ascii") as stream:
        for line in stream:
            stamp, tor, port, count = map(int, line.split(","))
            if stamp < last_stamp:
                raise ValueError("Out-of-order uplink timestamps: " + str(path))
            last_stamp = stamp
            if stamp > END_NS:
                break
            key = (tor, port)
            if key in previous:
                old_stamp, old_count = previous[key]
                if stamp - old_stamp != INTERVAL_NS or count < old_count:
                    raise ValueError("Nonmonotone uplink raw: " + str(path))
            previous[key] = (stamp, count)
            counts[key] = counts.get(key, 0) + 1
            timestamps.add(stamp)
            if stamp == START_NS:
                first[key] = count
            elif stamp == END_NS:
                last[key] = count
    expected = set(range(START_NS, END_NS + 1, INTERVAL_NS))
    if (timestamps != expected or len(first) != 1280 or len(last) != 1280
            or first.keys() != last.keys()
            or any(value != len(expected) for value in counts.values())):
        raise ValueError("Incomplete common uplink window: " + str(path))
    deltas = [last[key] - first[key] for key in first]
    active = [value for value in deltas if value > 0]
    if not active or max(deltas) > WINDOW_CAPACITY_BYTES * 1.01:
        raise ValueError("Invalid uplink utilization: " + str(path))
    return {
        "ports": len(deltas),
        "active_ports": len(active),
        "transmitted_bytes": sum(deltas),
        "mean_all_port_utilization_pct": 100 * sum(deltas) / len(deltas) / WINDOW_CAPACITY_BYTES,
        "mean_active_port_utilization_pct": 100 * sum(active) / len(active) / WINDOW_CAPACITY_BYTES,
        "max_port_utilization_pct": 100 * max(deltas) / WINDOW_CAPACITY_BYTES,
    }


def main():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    if len(plan["cells"]) != analysis["verified_cells"] != 576:
        raise ValueError("Formal analysis is not complete")
    planned_ids = {row["id"] for row in plan["cells"]}
    analyzed_ids = {row["id"] for row in analysis["cells"]}
    if planned_ids != analyzed_ids or analysis["primary_ecmp_192"]["passes"]:
        raise ValueError("Formal plan/analysis identity or gate changed")
    topology = ROOT / "results" / plan["cells"][0]["id"] / "config/topology.txt"
    verify_topology(topology)
    cells = []
    for cell in plan["cells"]:
        if cell["background"] != 192:
            continue
        raw = ROOT / "results" / cell["id"] / "raw"
        uplinks = list(raw.glob("*/*_out_uplink.txt"))
        if len(uplinks) != 1:
            raise ValueError("Missing or duplicate uplink raw: " + cell["id"])
        cells.append({"id": cell["id"], "seed": cell["seed"], "mode": cell["mode"],
                      **read_window(uplinks[0])})
    if len(cells) != 144:
        raise ValueError("Incomplete 192-background utilization comparison")
    by_key = {(row["seed"], row["mode"]): row for row in cells}
    if len(by_key) != 144:
        raise ValueError("Duplicate utilization seed/mode")
    fields = ("mean_all_port_utilization_pct", "mean_active_port_utilization_pct",
              "max_port_utilization_pct")
    by_mode = {}
    for mode in plan["modes"]:
        rows = [row for row in cells if row["mode"] == mode]
        by_mode[mode] = {name + "_median": median([row[name] for row in rows])
                         for name in fields}
        by_mode[mode]["active_ports_median"] = median([row["active_ports"] for row in rows])
    paired = {}
    for name in fields:
        diffs = [by_key[seed, "classreserve"][name] - by_key[seed, "fecmp"][name]
                 for seed in plan["demand_seed_order"]]
        paired[name] = {"median_difference_percentage_points": median(diffs),
                        "lower_than_ecmp_seeds": sum(value < 0 for value in diffs),
                        "range_difference_percentage_points": [min(diffs), max(diffs)]}
    output = {
        "kind": "ws25_v1fix_supplementary_192_uplink_utilization",
        "formal_plan_sha256": sha256(PLAN), "formal_analysis_sha256": sha256(ANALYSIS),
        "topology_sha256": sha256(topology), "window_start_ns": START_NS,
        "window_end_ns": END_NS, "sample_interval_ns": INTERVAL_NS,
        "capacity_gbps_per_uplink": CAPACITY_GBPS,
        "scope": "ToR uplinks; per-port byte-counter difference divided by 400 Gbps x 1 ms",
        "cells": cells, "by_mode": by_mode, "classreserve_vs_ecmp": paired,
        "formal_efficacy_rejudged": False,
    }
    OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"cells": len(cells), "classreserve_vs_ecmp": paired,
                      "output": str(OUTPUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
