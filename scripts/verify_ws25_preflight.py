#!/usr/bin/env python3
"""Verify WS-25 preflight correctness cells from fetched raw and receipts."""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "bb10309261b7c5be350fcaab75b4fdb8db95ddca"
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
PRE_TRACE_SHA = "29ebe2dcf38c0e4d29326947c4bc4e111f6b56fe378c020c30ee788fbaa5effb"
CAL192_SHA = "9791006f71843ea74b044396f6ae112ea8340aa9781cf0d267876e0940b02f48"
MODES = ("fecmp", "drill", "conga", "letflow", "conweave", "classreserve")
MODE_CODE = {"fecmp": 0, "drill": 2, "conga": 3, "letflow": 6,
             "conweave": 9, "classreserve": 21}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify(experiment_id, phase, mode):
    base = ROOT / "results" / experiment_id
    with (base / "metadata.json").open(encoding="utf-8") as source:
        meta = json.load(source)
    expected_trace = PRE_TRACE_SHA if phase == "pre" else CAL192_SHA
    expected_count = 8 if phase == "pre" else 16576
    expected_tags = {1: 4, 2: 4} if phase == "pre" else {1: 192, 2: 16384}
    assert meta["status"] == "SUCCEEDED" and meta["git_commit"] == COMMIT
    assert meta["algorithm"] == mode and meta["seed"] == 1
    assert meta["parameters"]["lb"] == mode
    assert meta["parameters"]["pfc"] == 0 and meta["parameters"]["irn"] == 1
    assert meta["parameters"]["bw"] == 400 and meta["parameters"]["buffer"] == 9
    assert meta["input_flow_sha256"] == expected_trace
    assert meta["topology_sha256"] == TOPO_SHA
    trace = base / "config" / "traffic_trace.txt"
    topology = base / "config" / "topology.txt"
    assert sha(trace) == expected_trace and sha(topology) == TOPO_SHA
    declared, inputs, pending, expected_bytes = None, [], {}, collections.Counter()
    source_ports, destination_ports = {}, {}
    with trace.open(encoding="ascii") as source:
        declared = int(source.readline().strip())
        for line_number, line in enumerate(source, 2):
            row = line.split()
            assert len(row) == 6, (line_number, row)
            src, dst, pg, size = map(int, row[:4])
            start_ns, tag = round(float(row[4]) * 1e9), int(row[5])
            assert tag in (1, 2) and start_ns == 2000000000
            sport = source_ports.get(src, 10000)
            dport = destination_ports.get(dst, 100)
            source_ports[src], destination_ports[dst] = sport + 1, dport + 1
            key = (src, dst, sport, dport, size, start_ns)
            assert key not in pending
            pending[key] = tag
            expected_bytes[tag] += size
            inputs.append((src, dst, pg, size, start_ns, tag))
    assert declared == len(inputs) == expected_count
    assert dict(collections.Counter(row[5] for row in inputs)) == expected_tags

    raw_id = str(meta["raw_directory"])
    assert raw_id.isdigit()
    raw = base / "raw" / raw_id
    fct_files = list(raw.glob("*_out_fct.txt"))
    assert len(fct_files) == 1 and not fct_files[0].is_symlink()
    completed, completed_bytes = {}, collections.Counter()
    for line_number, line in enumerate(fct_files[0].read_text().splitlines(), 1):
        fields = tuple(map(int, line.split()))
        assert len(fields) == 8
        key, size = tuple(fields[:6]), fields[4]
        assert key in pending and key not in completed, (line_number, key)
        assert fields[6] >= 0 and fields[7] > 0
        completed[key] = pending[key]
        completed_bytes[pending[key]] += size
    assert len(completed) == expected_count
    assert completed_bytes == expected_bytes

    pfc = list(raw.glob("*_out_pfc.txt"))
    assert len(pfc) == 1 and pfc[0].stat().st_size == 0
    config_log = base / "logs" / "config.log"
    assert config_log.is_file() and not config_log.is_symlink()
    log = config_log.read_text(encoding="utf-8", errors="replace")
    assert "LB_MODE\t\t\t%d" % MODE_CODE[mode] in log
    assert "RANDOM_SEED\t\t\t1" in log
    for tag, count in expected_tags.items():
        assert "WS06_INPUT_TAG tag=%d flows=%d" % (tag, count) in log
        marker = "WS06_ROUTING_TAG tag=%d packets=" % tag
        assert marker in log and int(log.split(marker, 1)[1].split()[0]) > 0
    assert "WS06_ROUTING_TAG missing=0" in log
    mode_extra = None
    if mode == "classreserve":
        line = next((x for x in log.splitlines() if x.startswith("WS25_CLASSRESERVE ")), None)
        assert line and "queue_violations=0" in line
        values = dict(item.split("=", 1) for item in line.split()[1:])
        assert int(values["background_new_flows"]) > 0
        assert int(values["moe_two_choices"]) > 0
        mode_extra = values

    samples_path = base / "logs" / "resource-samples.jsonl"
    summary_path = base / "logs" / "resource-summary.json"
    assert samples_path.is_file() and summary_path.is_file()
    samples = [json.loads(x) for x in samples_path.read_text().splitlines() if x.strip()]
    resources = json.loads(summary_path.read_text(encoding="utf-8"))
    assert resources["final_status"] == "SUCCEEDED" and resources["samples"] == len(samples) > 0
    assert resources["peak_tree_rss_mib"] <= 32768
    assert resources["minimum_mem_available_gib"] >= 32
    assert resources["minimum_free_gib"] >= 100
    assert max(x["load_1m"] for x in samples) <= 20
    summary = {"experiment_id": experiment_id, "phase": phase, "mode": mode,
               "status": meta["status"], "source_sha": meta["git_commit"],
               "trace_sha256": expected_trace, "topology_sha256": TOPO_SHA,
               "fct_sha256": sha(fct_files[0]), "config_log_sha256": sha(config_log),
               "input_flows": expected_count, "completed_flows": len(completed),
               "bytes_by_tag": {str(k): v for k, v in sorted(expected_bytes.items())},
               "resource": resources, "mode_diagnostics": mode_extra}
    summary_path_local = base / "processed" / "ws25_preflight_verification.json"
    if summary_path_local.exists():
        assert json.loads(summary_path_local.read_text(encoding="utf-8")) == summary
    else:
        summary_path_local.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                                      encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("pre", "pilot"))
    parser.add_argument("--ids", nargs="+")
    args = parser.parse_args()
    if args.phase == "pre":
        ids = ["20261002-22300%d-ws25-v2-pre-%s" % (i, mode) for i, mode in enumerate(MODES)]
    else:
        ids = ["20261002-22400%d-ws25-v2-cal01-%s" % (i, mode) for i, mode in enumerate(MODES)]
    selected = args.ids if args.ids else ids
    mode_by_id = dict(zip(ids, MODES))
    unknown = [experiment_id for experiment_id in selected if experiment_id not in mode_by_id]
    if unknown:
        parser.error("IDs do not belong to phase %s: %s" % (args.phase, ", ".join(unknown)))
    results = [verify(experiment_id, args.phase, mode_by_id[experiment_id])
               for experiment_id in selected]
    assert results and (args.ids or len(results) == 6)
    print(json.dumps({"phase": args.phase, "verified": len(results), "cells": results},
                     sort_keys=True))


if __name__ == "__main__":
    main()
