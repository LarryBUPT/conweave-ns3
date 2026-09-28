#!/usr/bin/env python3
"""Check a single WS-19 cell's identity, completion, accounting and receipts."""
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PLAN = ROOT / "docs/research/evidence/ws19-pilot-schedule-v1.json"
SOURCE_SHA = "b52e66f0fbf786fb57672b12a5633cf45b9311c1"
TOPO_NAME = "topo_1280_400G_400G_OS1"
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
FLAGS = {"ecmp": (0, 0), "admission": (1, 0), "path": (0, 1), "joint": (1, 1)}


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for part in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def verify(experiment_id, scheduled):
    base = RESULTS / experiment_id
    meta = json.loads((base / "metadata.json").read_text(encoding="utf-8"))
    assert meta["status"] == "SUCCEEDED" and meta["git_commit"] == SOURCE_SHA
    assert meta["topology_sha256"] == TOPO_SHA and int(meta["seed"]) == 1
    assert meta["input_flow_sha256"] == scheduled["trace_sha256"]
    params = meta["parameters"]
    admission, path = FLAGS[scheduled["arm"]]
    assert (params["lb"], params["ws18_admission"], params["ws18_path"],
            params["pfc"], params["irn"], params["bw"], params["buffer"],
            params["topo"], params["ws13_diag"]) == (
                "ws18", admission, path, 0, 1, 400, 9, TOPO_NAME,
                1 if scheduled["background"] else 0)
    raw = base / "raw" / str(meta["raw_directory"])
    trace_path = base / "config" / "traffic_trace.txt"
    assert sha(trace_path) == scheduled["trace_sha256"]
    assert sha(base / "config" / "topology.txt") == TOPO_SHA
    trace_lines = trace_path.read_text(encoding="utf-8").splitlines()
    n = int(trace_lines[0])
    assert n == scheduled["flows"] == len(trace_lines) - 1
    inputs, expected_bytes = [], {1: 0, 2: 0}
    for line in trace_lines[1:]:
        src, dst, pg, size, start, tag = line.split()
        row = (int(src), int(dst), int(size), int(Decimal(start) * 1_000_000_000), int(tag))
        inputs.append(row)
        expected_bytes[row[4]] += row[2]
    assert sum(expected_bytes.values()) == scheduled["offered_bytes"]
    timing_path = raw / (str(meta["raw_directory"]) + "_out_ws18.txt")
    timing = {}
    for line in timing_path.read_text(encoding="utf-8").splitlines():
        v = [int(x) for x in line.split()]
        assert len(v) == 12
        fid, src, dst, sport, dport, tag, size, demand, release, finish, wait, total = v
        assert fid not in timing and 0 <= fid < n
        assert (src, dst, size, demand, tag) == inputs[fid]
        assert demand <= release <= finish
        assert wait == release - demand and total == finish - demand
        if not admission or tag != 2:
            assert wait == 0
        timing[fid] = v
    assert len(timing) == n
    assert sum(v[6] for v in timing.values()) == scheduled["offered_bytes"]
    finished_by_tag = {1: 0, 2: 0}
    for v in timing.values():
        finished_by_tag[v[5]] += v[6]
    assert finished_by_tag == expected_bytes
    fct_path = raw / (str(meta["raw_directory"]) + "_out_fct.txt")
    fct_rows = {}
    for line in fct_path.read_text(encoding="utf-8").splitlines():
        v = [int(x) for x in line.split()]
        assert len(v) == 8
        key = tuple(v[:4])
        assert key not in fct_rows
        fct_rows[key] = v
    assert len(fct_rows) == n
    for v in timing.values():
        fct = fct_rows[(v[1], v[2], v[3], v[4])]
        assert fct[4] == v[6] and fct[5] == v[8] and fct[5] + fct[6] == v[9]
    log = (raw / "config.log").read_text(encoding="utf-8", errors="replace")
    conservation = re.search(r"WS18_CONSERVATION input=(\d+) released=(\d+) finished=(\d+) input_bytes=(\d+) finished_bytes=(\d+)", log)
    assert conservation and tuple(map(int, conservation.groups())) == (
        n, n, n, scheduled["offered_bytes"], scheduled["offered_bytes"])
    route = re.search(r"WS18_PATH flows=(\d+) alternate=(\d+) packets=(\d+) multipath_packets=(\d+)", log)
    assert route
    route_values = tuple(map(int, route.groups()))
    if not path:
        assert route_values == (0, 0, 0, 0)
    else:
        assert route_values[0] > 0 and route_values[3] > 0
    if scheduled["background"]:
        assert "WS13_INFLIGHT unpaired=0" in log
        expected_destinations = {r[1] for r in inputs if r[4] == 1}
        observed_destinations, observed_qps = set(), set()
        for line in log.splitlines():
            if line.startswith("WS13_HOP "):
                fields = dict(x.split("=", 1) for x in line.split()[1:])
                observed_destinations.add(int(fields["dst"]))
            elif line.startswith("WS13_QP "):
                fields = dict(x.split("=", 1) for x in line.split()[1:])
                observed_qps.add((int(fields["src"]), int(fields["dst"]),
                                  int(fields["sport"]), int(fields["dport"])))
                assert "irn_nack_size" in fields
        expected_qps = {(r[0], r[1], timing[i][3], timing[i][4])
                        for i, r in enumerate(inputs) if r[4] == 1}
        assert observed_destinations == expected_destinations
        assert observed_qps == expected_qps
    pfc_path = raw / (str(meta["raw_directory"]) + "_out_pfc.txt")
    assert pfc_path.stat().st_size == 0
    resources = json.loads((base / "logs/resource-summary.json").read_text())
    assert resources["final_status"] == "SUCCEEDED" and resources["samples"] > 0
    assert resources["peak_tree_rss_mib"] < 32768
    assert resources["minimum_mem_available_gib"] > 32
    assert resources["minimum_free_gib"] > 100
    return {"experiment_id": experiment_id, "status": "VERIFIED",
            "arm": scheduled["arm"], "block": scheduled["block"],
            "seed": scheduled["seed"], "hotspot": scheduled["hotspot"],
            "background": scheduled["background"], "flows": n,
            "offered_bytes": scheduled["offered_bytes"],
            "trace_sha256": sha(trace_path), "fct_sha256": sha(fct_path),
            "timing_sha256": sha(timing_path), "resources": resources}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment_id")
    parser.add_argument("schedule_index", type=int)
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    print(json.dumps(verify(args.experiment_id, plan["runs"][args.schedule_index]),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
