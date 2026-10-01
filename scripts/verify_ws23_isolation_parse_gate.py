#!/usr/bin/env python3
"""Verify the new-SHA WS-23 mixed-trace parser gate from fetched raw data."""

import argparse
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/research/evidence/ws23-isolation-demand-manifest.json"
EXPERIMENT_ID = "20261001-200003-ws23-s2301-mix-fecmp"
TOPO_SHA = "dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/research/evidence/ws23-isolation-parse-gate.json")
    args = parser.parse_args()
    require(re.fullmatch(r"[0-9a-f]{40}", args.source_sha) is not None,
            "full source SHA required")
    entry = next(item for item in json.loads(MANIFEST.read_text(encoding="utf-8"))["entries"]
                 if item["seed"] == 2301 and item["scenario"] == "mix")
    folder = ROOT / "results" / EXPERIMENT_ID
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    require(meta["experiment_id"] == EXPERIMENT_ID and meta["status"] == "SUCCEEDED",
            "experiment identity/status")
    require(meta["git_commit"] == args.source_sha and meta["algorithm"] == "fecmp" and
            meta["seed"] == 1 and meta["build_mode"] == "optimized" and
            meta["cpu_jobs"] == 2 and meta["concurrency_cap"] == 1,
            "source/build/seed mismatch")
    require(meta["input_flow_sha256"] == entry["sha256"] and
            meta["topology_sha256"] == TOPO_SHA and
            sha(folder / "config/traffic_trace.txt") == entry["sha256"] and
            sha(folder / "config/topology.txt") == TOPO_SHA,
            "config snapshot hashes")
    require(meta["input_flows"] == meta["completed_flows"] == 4 and
            meta["unfinished_flows"] == 0, "flow completion")
    params = meta["parameters"]
    expected = {"lb": "fecmp", "pfc": 0, "irn": 1, "buffer": 9, "bw": 100,
                "simul_time": "0.01", "netload": 10, "topo": "fat_k4_100G_OS2",
                "cdf": "AliStorage2019", "factorial_pilot": True,
                "factorial_drop_diag": True, "ws13_diag": 0,
                "flow_file": "ws23_isolation_s2301_mix.txt"}
    require(all(params.get(key) == value for key, value in expected.items()),
            "frozen parameters")
    trace = (folder / "config/traffic_trace.txt").read_text(encoding="ascii").splitlines()
    rows = [line.split() for line in trace[1:]]
    require(trace[0] == "4" and len(rows) == 4 and all(len(row) == 6 for row in rows),
            "trace flow count/columns")
    times = [float(row[4]) for row in rows]
    require(times == sorted(times) and len(set(times)) == 4, "trace time ordering")
    require("FLOW_INPUT_ERROR" not in (folder / "raw" / str(meta["raw_directory"]) /
                                       "config.log").read_text(encoding="utf-8", errors="replace"),
            "flow parser error")
    raw = folder / "raw" / str(meta["raw_directory"])
    fct_path = raw / (str(meta["raw_directory"]) + "_out_fct.txt")
    fct = [tuple(map(int, line.split())) for line in fct_path.read_text().splitlines()]
    expected_flows = {(flow["source"], flow["destination"], flow["bytes"])
                      for flow in entry["flows"]}
    actual_flows = {(row[0], row[1], row[4]) for row in fct}
    require(len(fct) == 4 and all(len(row) == 8 for row in fct) and
            actual_flows == expected_flows and all(row[6] > 0 for row in fct),
            "FCT identities/completion")
    require(sum(row[4] for row in fct) == entry["payload_bytes"], "payload bytes")
    pfc_path = raw / (str(meta["raw_directory"]) + "_out_pfc.txt")
    require(pfc_path.stat().st_size == 0, "unexpected PFC")
    receipt = json.loads((folder / "logs/resource-fast-summary.json").read_text())
    samples = [json.loads(line) for line in
               (folder / "logs/resource-fast-samples.jsonl").read_text().splitlines()]
    running = [sample for sample in samples if sample["status"] == "RUNNING"]
    require(receipt["final_status"] == "SUCCEEDED" and receipt["running_seen"] and
            receipt["root_pid"] == meta["pid"] and samples[0]["status"] == "READY" and
            running and all(sample["root_pid"] == meta["pid"] and
                            sample["process_tree_rss_mib"] > 0 and
                            sample["load_1m"] <= 20 for sample in running) and
            0 < receipt["peak_tree_rss_mib"] < 8192 and
            receipt["minimum_mem_available_gib"] >= 16 and
            receipt["minimum_free_gib"] >= 100, "resource receipt")
    report = {"experiment_id": EXPERIMENT_ID, "source_sha": args.source_sha,
              "status": meta["status"], "input_sha256": entry["sha256"],
              "topology_sha256": TOPO_SHA, "flow_count": len(fct),
              "payload_bytes": sum(row[4] for row in fct),
              "fct_sha256": sha(fct_path), "peak_tree_rss_mib": receipt["peak_tree_rss_mib"],
              "maximum_sampled_load_1m": max(s["load_1m"] for s in running),
              "parse_error": False, "resource_receipt_valid": True,
              "gate_passed": True}
    rendered = json.dumps(report, indent=2) + "\n"
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")


if __name__ == "__main__":
    main()
