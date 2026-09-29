#!/usr/bin/env python3
"""Verify the fixed WS-21 local-heartbeat pilot from fetched raw results."""

import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUTPUT = ROOT / "docs/research/evidence/ws21-local-heartbeat-pilot.json"
SOURCE_SHA = "770b6b5617657832393bd721e0d634c6639405fb"
TOPOLOGY_SHA = "dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad"
TRACE_SHA = "032b6baaf3b1a6b4507a7699ef3a148eeadd1f343a13c61a12b79c65f1d49ff5"
FLOW_BYTES = 67108864
FLOW_START_NS = 2006000000
FAULT_START_NS = 2006100000
FAULT_END_NS = 2010000000
TEXT_LOG_LIMIT_BYTES = 50 * 1024 * 1024

CELLS = (
    ("off", "20260930-020100-ws21hb-k4-off", 0, 200000, 0),
    ("normal_200us", "20260930-020200-ws21hb-k4-200us", 1, 200000, 0),
    ("drop_hello", "20260930-020300-ws21hb-k4-drophello", 1, 200000, 1),
    ("drop_ack", "20260930-020400-ws21hb-k4-dropack", 1, 200000, 2),
    ("normal_50us", "20260930-020500-ws21hb-k4-50us", 1, 50000, 0),
    ("normal_1000us", "20260930-020600-ws21hb-k4-1000us", 1, 1000000, 0),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def only_line(lines, prefix):
    found = [line for line in lines if line.startswith(prefix)]
    require(len(found) == 1, "expected one {!r}, got {}".format(prefix, len(found)))
    return found[0]


def fields(line):
    return {key: int(value) for key, value in re.findall(r"([a-z_]+)=([0-9]+)", line)}


def wall_seconds(start, end):
    return int((datetime.strptime(end, "%Y-%m-%dT%H:%M:%SZ") -
                datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ")).total_seconds())


def max_text_log_bytes(folder):
    files = list(folder.rglob("*.log")) + list(folder.rglob("*.jsonl"))
    largest = max((path.stat().st_size for path in files), default=0)
    require(largest <= TEXT_LOG_LIMIT_BYTES,
            "{} text log exceeded 50 MiB".format(folder.name))
    return largest


def verify_unit():
    experiment_id = "20260930-020000-ws21hb-k4-unit"
    folder = RESULTS / experiment_id
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    resource = json.loads((folder / "logs/resource-summary.json").read_text(encoding="utf-8"))
    test_log = (folder / "logs/unit-test.log").read_text(encoding="utf-8")
    require(metadata["git_commit"] == SOURCE_SHA and metadata["status"] == "BUILT",
            "unit build provenance/status mismatch")
    require(resource["final_status"] == "TESTED" and resource["id"] == experiment_id,
            "unit resource receipt mismatch")
    require("PASS devices-point-to-point" in test_log and
            "PASS WS-21 heartbeat header serialization and validation" in test_log and
            "PASS WS-21 feedback header serialization and validation" in test_log,
            "point-to-point suite did not pass")
    require(len((folder / "logs/resource-samples.jsonl").read_text(encoding="utf-8").splitlines())
            == resource["samples"], "unit resource sample count mismatch")
    return {"experiment_id": experiment_id, "metadata_status": metadata["status"],
            "test_status": resource["final_status"], "suite": "devices-point-to-point",
            "peak_tree_rss_mib": resource["peak_tree_rss_mib"],
            "resource_samples": resource["samples"],
            "max_text_log_bytes": max_text_log_bytes(folder)}


def verify_cell(label, experiment_id, enabled, interval_ns, fault_mode):
    folder = RESULTS / experiment_id
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    resource = json.loads((folder / "logs/resource-summary.json").read_text(encoding="utf-8"))
    require(metadata["status"] == "SUCCEEDED" and metadata["git_commit"] == SOURCE_SHA,
            "{} status/source mismatch".format(label))
    require(metadata["seed"] == 1 and metadata["build_mode"] == "optimized",
            "{} seed/build mismatch".format(label))
    require(metadata["topology_sha256"] == TOPOLOGY_SHA and
            metadata["input_flow_sha256"] == TRACE_SHA,
            "{} metadata input hash mismatch".format(label))
    require(digest((folder / "config/topology.txt").read_bytes()) == TOPOLOGY_SHA and
            digest((folder / "config/traffic_trace.txt").read_bytes()) == TRACE_SHA,
            "{} input snapshot hash mismatch".format(label))
    params = metadata["parameters"]
    fixed = {"lb": "ws18", "ws18_path": 1, "ws18_admission": 0,
             "ws21_feedback": 0, "ws21_identity": 0, "ws21_port_events": 0,
             "pfc": 0, "irn": 1, "bw": 100, "buffer": 9,
             "flow_file": "ws21_heartbeat_fat_k4_long_flow.txt",
             "topo": "fat_k4_100G_OS2", "ws21_heartbeat": enabled,
             "ws21_heartbeat_interval_ns": interval_ns,
             "ws21_heartbeat_fault_mode": fault_mode}
    for key, expected in fixed.items():
        require(params.get(key) == expected,
                "{} parameter {} mismatch".format(label, key))
    if fault_mode:
        require((params["ws21_heartbeat_fault_tor"], params["ws21_heartbeat_fault_port"],
                 params["ws21_heartbeat_fault_start_ns"], params["ws21_heartbeat_fault_end_ns"])
                == (32, 0, FAULT_START_NS, FAULT_END_NS),
                "{} fault window mismatch".format(label))
    raw = folder / "raw" / metadata["raw_directory"]
    log_lines = (raw / "config.log").read_text(encoding="utf-8").splitlines()
    conservation = fields(only_line(log_lines, "WS18_CONSERVATION "))
    require(conservation == {"input": 1, "released": 1, "finished": 1,
                             "input_bytes": FLOW_BYTES, "finished_bytes": FLOW_BYTES},
            "{} business conservation mismatch".format(label))
    require(fields(only_line(log_lines, "WS06_INPUT_TAG ")) == {"tag": 2, "flows": 1},
            "{} flow tag mismatch".format(label))
    require(fields(only_line(log_lines, "WS06_ROUTING_TAG missing="))["missing"] == 0,
            "{} missing routing tags".format(label))
    fct_path = raw / (metadata["raw_directory"] + "_out_fct.txt")
    fct_lines = [line for line in fct_path.read_text(encoding="utf-8").splitlines()
                 if line.strip() and not line.startswith("#")]
    require(len(fct_lines) == 1, "{} FCT row count mismatch".format(label))
    fct = [int(x) for x in fct_lines[0].split()]
    require(len(fct) == 8 and fct[0:2] == [0, 8] and
            fct[4] == FLOW_BYTES and fct[5] == FLOW_START_NS,
            "{} FCT identity/input mismatch".format(label))
    require(resource["id"] == experiment_id and resource["final_status"] == "SUCCEEDED",
            "{} resource receipt mismatch".format(label))
    sample_count = len((folder / "logs/resource-samples.jsonl").read_text(encoding="utf-8").splitlines())
    require(sample_count == resource["samples"] and resource["peak_tree_rss_mib"] < 8192 and
            resource["minimum_mem_available_gib"] > 16 and resource["minimum_free_gib"] > 100,
            "{} resource safety mismatch".format(label))
    events = []
    for line in log_lines:
        if line.startswith("WS21_HEARTBEAT_EVENT "):
            data = fields(line)
            match = re.search(r"event=([a-z_]+)", line)
            require(match is not None, "{} malformed heartbeat event".format(label))
            data["event"] = match.group(1)
            events.append(data)
    heartbeat_lines = [line for line in log_lines if line.startswith("WS21_HEARTBEAT ")]
    heartbeat = None
    if enabled:
        require(len(heartbeat_lines) == 1, "{} heartbeat summary missing".format(label))
        heartbeat = fields(heartbeat_lines[0])
        require(heartbeat["hop_enqueues"] == heartbeat["hop_dequeues"] and
                heartbeat["hop_rejects"] == 0 and heartbeat["event_overflow"] == 0 and
                heartbeat["rejected"] == 0 and
                heartbeat["hop_bytes"] == heartbeat["hello_hop_bytes"] + heartbeat["ack_hop_bytes"] and
                heartbeat["hop_bytes"] == 44 * heartbeat["hop_enqueues"] and
                heartbeat["active_peak"] == 1 and heartbeat["activations"] == 1 and
                heartbeat["event_rows"] == len(events),
                "{} heartbeat accounting mismatch".format(label))
        if fault_mode == 0:
            require(heartbeat["hello_generated"] == heartbeat["hello_received"] ==
                    heartbeat["ack_generated"] == heartbeat["ack_received"] and
                    heartbeat["injected_drops"] == heartbeat["timeouts"] ==
                    heartbeat["unknown"] == heartbeat["recovered"] == 0,
                    "{} normal heartbeat mismatch".format(label))
        else:
            dropped = [e for e in events if e["event"] ==
                       ("drop_hello" if fault_mode == 1 else "drop_ack")]
            unknown = [e for e in events if e["event"] == "unknown_timeout"]
            recovered = [e for e in events if e["event"] == "recovered"]
            require(len(dropped) == heartbeat["injected_drops"] == heartbeat["timeouts"] == 19 and
                    len(unknown) == heartbeat["unknown"] == 1 and
                    len(recovered) == heartbeat["recovered"] == 1 and
                    FAULT_START_NS <= dropped[0]["time_ns"] < dropped[-1]["time_ns"] < FAULT_END_NS and
                    dropped[2]["time_ns"] < unknown[0]["time_ns"] < recovered[0]["time_ns"] and
                    recovered[0]["time_ns"] > FAULT_END_NS and
                    all(e["tor"] == 32 and e["port"] == 6 for e in dropped + unknown + recovered),
                    "{} fault transition mismatch".format(label))
            if fault_mode == 1:
                require(heartbeat["hello_generated"] - heartbeat["hello_received"] == 19 and
                        heartbeat["ack_generated"] == heartbeat["ack_received"] == heartbeat["hello_received"],
                        "{} dropped HELLO accounting mismatch".format(label))
            else:
                require(heartbeat["ack_generated"] - heartbeat["ack_received"] == 19 and
                        heartbeat["hello_generated"] == heartbeat["hello_received"] == heartbeat["ack_generated"],
                        "{} dropped ACK accounting mismatch".format(label))
    else:
        require(not heartbeat_lines and not events, "off cell sent heartbeat traffic")
    row = {"label": label, "experiment_id": experiment_id,
           "raw_id": metadata["raw_directory"], "fct_ns": fct[6],
           "input_flows": conservation["input"], "finished_flows": conservation["finished"],
           "input_bytes": conservation["input_bytes"], "finished_bytes": conservation["finished_bytes"],
           "heartbeat": heartbeat, "resource": resource,
           "max_text_log_bytes": max_text_log_bytes(folder),
           "build_wall_seconds": wall_seconds(metadata["created_utc"], metadata["build_finished_utc"]),
           "simulation_wall_seconds": wall_seconds(metadata["started_utc"], metadata["finished_utc"])}
    if fault_mode:
        row["fault_events"] = {
            "first_drop_ns": dropped[0]["time_ns"], "third_drop_ns": dropped[2]["time_ns"],
            "unknown_ns": unknown[0]["time_ns"], "recovered_ns": recovered[0]["time_ns"],
            "unknown_from_fault_start_ns": unknown[0]["time_ns"] - FAULT_START_NS,
            "unknown_from_first_drop_ns": unknown[0]["time_ns"] - dropped[0]["time_ns"],
            "recovered_after_fault_end_ns": recovered[0]["time_ns"] - FAULT_END_NS}
    return row


def main():
    git_blob = subprocess.check_output(
        ["git", "show", SOURCE_SHA + ":config/fat_k4_100G_OS2.txt"], cwd=str(ROOT))
    checkout = (ROOT / "config/fat_k4_100G_OS2.txt").read_bytes()
    require(digest(git_blob) == TOPOLOGY_SHA and
            digest(checkout.replace(b"\r\n", b"\n")) == TOPOLOGY_SHA,
            "topology Git blob / checkout canonical content mismatch")
    unit = verify_unit()
    rows = [verify_cell(*cell) for cell in CELLS]
    baseline_fct = rows[0]["fct_ns"]
    for row in rows:
        row["fct_delta_vs_off_ns"] = row["fct_ns"] - baseline_fct
        hb = row["heartbeat"]
        if hb:
            row["hop_bytes_per_application_byte_percent"] = round(
                hb["hop_bytes"] * 100.0 / FLOW_BYTES, 9)
    result = {
        "schema_version": 1, "evidence_level": "single-flow technical pilot",
        "source_sha": SOURCE_SHA, "seed": 1,
        "topology_git_blob_sha256": TOPOLOGY_SHA,
        "topology_windows_checkout_sha256": digest(checkout),
        "trace_sha256": TRACE_SHA, "application_bytes_per_cell": FLOW_BYTES,
        "unit": unit, "cells": rows,
        "limits": ["one fixed flow and one ns-3 seed", "UNKNOWN does not change routing",
                   "50/1000 us cells have no fault injection",
                   "single lost probe, stale/duplicate/wrong-port ACK, restart and link-up remain untested"]}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("verified unit + {} simulation cells; wrote {}".format(len(rows), OUTPUT))


if __name__ == "__main__":
    main()
