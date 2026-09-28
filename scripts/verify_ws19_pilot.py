#!/usr/bin/env python3
"""Verify WS-19 pilot raw identity, completion, timing and optional diagnostics."""
import argparse
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SOURCE_SHA = "b52e66f0fbf786fb57672b12a5633cf45b9311c1"
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
TRACE_NAME = "ws19_ws17_seed20261701_tor_hotspot_b192.txt"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(experiment_id, diagnostic):
    base = RESULTS / experiment_id
    meta = json.loads((base / "metadata.json").read_text(encoding="utf-8"))
    assert meta["status"] == "SUCCEEDED"
    assert meta["git_commit"] == SOURCE_SHA
    assert meta["input_flow_sha256"] == sha(ROOT / "config" / TRACE_NAME)
    assert meta["topology_sha256"] == TOPO_SHA
    params = meta["parameters"]
    assert (params["lb"], params["ws18_admission"], params["ws18_path"],
            params["pfc"], params["irn"], params["bw"], params["topo"]) == (
                "ws18", 0, 0, 0, 1, 400, "topo_1280_400G_400G_OS1")
    assert int(meta["seed"]) == 1
    raw = base / "raw" / str(meta["raw_directory"])
    trace_snapshot = base / "config" / "traffic_trace.txt"
    topology_snapshot = base / "config" / "topology.txt"
    assert sha(trace_snapshot) == sha(ROOT / "config" / TRACE_NAME)
    assert sha(topology_snapshot) == TOPO_SHA
    rows = (trace_snapshot.read_text(encoding="utf-8").splitlines())
    assert int(rows[0]) == len(rows) - 1 == 16576
    expected = []
    for line in rows[1:]:
        src, dst, pg, size, start, tag = line.split()
        expected.append((int(src), int(dst), int(size),
                         int(Decimal(start) * 1_000_000_000), int(tag)))
    timing_path = raw / (str(meta["raw_directory"]) + "_out_ws18.txt")
    timing = {}
    for line in timing_path.read_text(encoding="utf-8").splitlines():
        values = [int(x) for x in line.split()]
        assert len(values) == 12
        fid, src, dst, sport, dport, tag, size, demand, release, finish, wait, total = values
        assert fid not in timing and 0 <= fid < len(expected)
        assert (src, dst, size, demand, tag) == expected[fid]
        assert demand <= release <= finish
        assert wait == release - demand and total == finish - demand
        assert wait == 0
        timing[fid] = values
    assert len(timing) == 16576
    assert sum(row[6] for row in timing.values()) == 1_744_830_464
    fct_path = raw / (str(meta["raw_directory"]) + "_out_fct.txt")
    fct = fct_path.read_text(encoding="utf-8").splitlines()
    assert len(fct) == 16576 and fct_path.stat().st_size > 0
    fct_keys = set()
    for line in fct:
        values = [int(x) for x in line.split()]
        assert len(values) == 8
        key = tuple(values[:4])
        assert key not in fct_keys
        fct_keys.add(key)
    assert len(fct_keys) == len(timing)
    log = (raw / "config.log").read_text(encoding="utf-8", errors="replace")
    conservation = re.search(r"WS18_CONSERVATION input=(\d+) released=(\d+) finished=(\d+) input_bytes=(\d+) finished_bytes=(\d+)", log)
    assert conservation and tuple(map(int, conservation.groups())) == (
        16576, 16576, 16576, 1744830464, 1744830464)
    assert "WS18_PATH flows=0 alternate=0 packets=0 multipath_packets=0" in log
    if diagnostic:
        assert "WS13_INFLIGHT unpaired=0" in log
        trace_destinations = {row[1] for row in expected if row[4] == 1}
        observed_destinations = set()
        observed_qps = set()
        for line in log.splitlines():
            if line.startswith("WS13_HOP "):
                fields = dict(part.split("=", 1) for part in line.split()[1:])
                observed_destinations.add(int(fields["dst"]))
            elif line.startswith("WS13_QP "):
                fields = dict(part.split("=", 1) for part in line.split()[1:])
                observed_qps.add((int(fields["src"]), int(fields["dst"]),
                                  int(fields["sport"]), int(fields["dport"])))
                assert "irn_nack_size" in fields
        expected_qps = {(row[0], row[1], timing[fid][3], timing[fid][4])
                        for fid, row in enumerate(expected) if row[4] == 1}
        assert observed_destinations == trace_destinations
        assert observed_qps == expected_qps
    resource = json.loads((base / "logs/resource-summary.json").read_text())
    assert resource["final_status"] == "SUCCEEDED" and resource["samples"] > 0
    pfc_path = raw / (str(meta["raw_directory"]) + "_out_pfc.txt")
    assert pfc_path.stat().st_size == 0
    return {"experiment_id": experiment_id, "diagnostic": diagnostic,
            "status": meta["status"], "source_sha": meta["git_commit"],
            "trace_sha256": meta["input_flow_sha256"],
            "fct_sha256": sha(fct_path), "timing_sha256": sha(timing_path),
            "flows": len(timing), "completed_bytes": 1_744_830_464,
            "background_destinations": len({row[1] for row in expected if row[4] == 1}),
            "diagnostic_qps": len(observed_qps) if diagnostic else 0,
            "resource": resource}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--off", required=True)
    parser.add_argument("--on")
    args = parser.parse_args()
    off = run(args.off, False)
    result = {"off": off}
    if args.on:
        on = run(args.on, True)
        assert off["fct_sha256"] == on["fct_sha256"], "Diagnostic changed FCT fingerprint"
        result["on"] = on
        result["fct_identical"] = True
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
