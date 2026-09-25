#!/usr/bin/env python3
"""Verify the fixed WS-09 technical experiments from fetched raw results."""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
CASES = {
    "small_dual": "20260926-013834-ws09-compile2",
    "pilot_shortq2": "20260926-014609-ws09-pilot-shortq2",
    "pilot_guardhash": "20260926-015632-ws09-pilot-guardhash",
    "pilot_gate": "20260926-020703-ws09-pilot-gate",
    "small_flow": "20260926-021713-ws09-small-flow",
    "small_packet": "20260926-022334-ws09-small-packet",
    "cross_four": "20260926-022959-ws09-cross-four",
    "regress_fecmp": "20260926-024003-ws09-regress-fecmp",
    "regress_dualtrack": "20260926-024625-ws09-regress-dualtrack",
    "drop_probe": "20260926-025616-ws09-drop-probe",
}
QUEUE = re.compile(r"^WS09_QUEUE switch=(\d+) port=(\d+) tag=(\d+) (.*)$")
KV = re.compile(r"([a-z_]+)=(\d+)")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique(path, glob):
    matches = list(path.glob(glob))
    if len(matches) != 1:
        raise ValueError("Expected one %s under %s; found %d" % (glob, path, len(matches)))
    return matches[0]


def config_values(path):
    values = {}
    for line in path.read_text().splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            values[parts[0]] = parts[1]
    return values


def verify_case(name, experiment_id):
    base = RESULTS / experiment_id
    meta = json.loads((base / "metadata.json").read_text())
    assert meta["status"] == "SUCCEEDED", (name, meta["status"])
    raw = base / "raw" / meta["raw_directory"]
    fct = unique(raw, "*_out_fct.txt")
    cnp = unique(raw, "*_out_cnp.txt")
    trace = base / "config" / "traffic_trace.txt"
    assert sha256(trace) == meta["input_flow_sha256"], name
    assert sha256(base / "config" / "topology.txt") == meta["topology_sha256"], name
    declared_flows = int(trace.read_text().splitlines()[0])
    completed = sum(1 for line in fct.read_text().splitlines() if line.strip())
    log = (raw / "config.log").read_text()
    route = next((line for line in log.splitlines() if line.startswith("WS09_ROUTE ")), None)
    queue_check = next((line for line in log.splitlines() if line.startswith("WS09_QUEUE_CHECK ")), None)
    tag_counts = {}
    queue_rows = 0
    drop = {"admission": 0, "reject": 0, "queued": 0}
    for line in log.splitlines():
        if line.startswith("WS06_ROUTING_TAG tag="):
            found = dict(KV.findall(line))
            tag_counts[found["tag"]] = int(found["packets"])
        matched = QUEUE.match(line)
        if matched:
            queue_rows += 1
            counters = {k: int(v) for k, v in KV.findall(matched.group(4))}
            queued_drop = counters.get("queued_drop", counters.get("queue_drop", 0))
            assert counters["enqueued"] == counters["dequeued"] + queued_drop + counters["current"], (name, line)
            drop["admission"] += counters["admission_drop"]
            drop["reject"] += counters.get("queue_reject", 0)
            drop["queued"] += queued_drop
    if name not in ("regress_fecmp", "regress_dualtrack"):
        assert route and queue_check == "WS09_QUEUE_CHECK violations=0", name
        assert queue_rows > 0, name
    cnp_rows = [list(map(int, line.split())) for line in cnp.read_text().splitlines() if line.strip()]
    assert all(len(row) == 5 for row in cnp_rows), name
    return {
        "experiment_id": experiment_id,
        "algorithm": meta["algorithm"],
        "source_sha": meta["git_commit"],
        "trace_sha256": meta["input_flow_sha256"],
        "topology_sha256": meta["topology_sha256"],
        "seed": meta["seed"],
        "parameters": meta["parameters"],
        "config": config_values(base / "config" / "config.txt"),
        "input_flows": declared_flows,
        "completed_flows": completed,
        "fct_sha256": sha256(fct),
        "tag_packets": tag_counts,
        "route": route,
        "queue_rows": queue_rows,
        "queue_violations": 0 if queue_check else None,
        "drops_bytes": drop,
        "cnp_ecn": sum(row[2] for row in cnp_rows),
        "cnp_ooo": sum(row[3] for row in cnp_rows),
        "tx_timeouts": log.count("WS08_TX_TIMEOUT "),
        "build_seconds": round((datetime.fromisoformat(meta["build_finished_utc"].replace("Z", "+00:00")) - datetime.fromisoformat(meta["created_utc"].replace("Z", "+00:00"))).total_seconds()),
        "run_seconds": round((datetime.fromisoformat(meta["finished_utc"].replace("Z", "+00:00")) - datetime.fromisoformat(meta["started_utc"].replace("Z", "+00:00"))).total_seconds()),
    }


def main():
    cases = {name: verify_case(name, experiment_id) for name, experiment_id in CASES.items()}
    pilots = [cases["pilot_" + name] for name in ("shortq2", "guardhash", "gate")]
    common_keys = ["TOPOLOGY_FILE", "FLOW_FILE", "CC_MODE", "ENABLE_PFC", "ENABLE_IRN",
                   "BUFFER_SIZE", "RANDOM_SEED", "GUARDHASH_LAMBDA", "GUARDHASH_TAU_BYTES",
                   "HARM_GATE_ON_BYTES", "HARM_GATE_OFF_BYTES"]
    assert len({case["source_sha"] for case in pilots}) == 1
    assert len({case["trace_sha256"] for case in pilots}) == 1
    assert len({case["topology_sha256"] for case in pilots}) == 1
    assert len({case["seed"] for case in pilots}) == 1
    assert all(len({case["config"][key] for case in pilots}) == 1 for key in common_keys)
    assert all(case["completed_flows"] == 320 for case in pilots)
    flow_hashes = {cases[name]["fct_sha256"] for name in ("small_flow", "regress_fecmp", "regress_dualtrack")}
    assert len(flow_hashes) == 1
    assert cases["small_dual"]["completed_flows"] == 4
    assert cases["small_packet"]["completed_flows"] == 4
    assert cases["cross_four"]["completed_flows"] == 4
    assert cases["drop_probe"]["completed_flows"] == 16
    assert cases["drop_probe"]["drops_bytes"]["admission"] > 0
    assert cases["drop_probe"]["queue_violations"] == 0
    summary = {
        "purpose": "WS-09 engineering correctness and single-seed technical pilot; no efficacy inference",
        "pairing_passed": True,
        "flow_regression_passed": True,
        "drop_probe_passed": True,
        "cases": cases,
    }
    output = ROOT / "docs" / "research" / "ws09-validation-summary.json"
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print("verified %d experiments; summary=%s" % (len(cases), output))


if __name__ == "__main__":
    main()
