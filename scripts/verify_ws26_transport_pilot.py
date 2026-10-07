#!/usr/bin/env python3
"""Verify the three disclosed-demand WS-26 transport correctness pilot cells."""

import hashlib
import json
from pathlib import Path

import analyze_moe_tags


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "ce699dffe2845dc83e2171a1c309c6d96b96d2b3"
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
TRACE_SHA = "d72f0f360d89dd3504c4cba730d903e1d939400ff2abd3566cf0428f4e59e2e3"
TRACE_NAME = "ws25_seed20262524_b192.txt"
CELLS = (
    ("20261007-171000-ws26-transport-s24-b192-p1i1", 1, 1),
    ("20261007-171001-ws26-transport-s24-b192-p1i0", 1, 0),
    ("20261007-171002-ws26-transport-s24-b192-p0i0", 0, 0),
)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def unique_raw(raw, suffix):
    paths = list(raw.glob("*" + suffix))
    if len(paths) != 1 or paths[0].is_symlink():
        raise RuntimeError("Missing or ambiguous raw " + suffix)
    return paths[0]


def verify(experiment_id, pfc, irn):
    folder = ROOT / "results" / experiment_id
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = meta["parameters"]
    expected = {"lb": "fecmp", "pfc": pfc, "irn": irn, "bw": 400,
                "buffer": 9, "netload": 10, "simul_time": "0.01",
                "topo": "topo_1280_400G_400G_OS1", "cdf": "AliStorage2019",
                "flow_file": TRACE_NAME, "factorial_pilot": True,
                "ws25_diag": 0}
    if not (meta["status"] == "SUCCEEDED" and meta["git_commit"] == SOURCE_SHA
            and meta["algorithm"] == "fecmp" and meta["seed"] == 1
            and meta["input_flow_sha256"] == TRACE_SHA
            and meta["topology_sha256"] == TOPO_SHA
            and all(params.get(key) == value for key, value in expected.items())):
        raise RuntimeError("Pilot identity or parameters differ: " + experiment_id)
    if (sha(folder / "config" / "traffic_trace.txt") != TRACE_SHA or
            sha(folder / "config" / "topology.txt") != TOPO_SHA):
        raise RuntimeError("Pilot input snapshot changed: " + experiment_id)
    summary = analyze_moe_tags.summarize(experiment_id)
    tags = summary["tags"]
    if ({tag: value["input_flows"] for tag, value in tags.items()} !=
            {"1": 192, "2": 16384} or
            any(value["completed_flows"] != value["input_flows"] for value in tags.values())):
        raise RuntimeError("Pilot QP identity or completion failed: " + experiment_id)
    raw = folder / "raw" / str(meta["raw_directory"])
    pfc_path = unique_raw(raw, "_out_pfc.txt")
    cnp_path = unique_raw(raw, "_out_cnp.txt")
    uplink_path = unique_raw(raw, "_out_uplink.txt")
    unique_raw(raw, "_out_fct.txt")
    pfc_events = {"pause": 0, "resume": 0}
    for line in pfc_path.read_text(encoding="ascii").splitlines():
        parts = line.split()
        if len(parts) != 5 or parts[-1] not in ("0", "1"):
            raise RuntimeError("Malformed PFC event: " + experiment_id)
        pfc_events["pause" if parts[-1] == "1" else "resume"] += 1
    for suffix, path, width in (("CNP", cnp_path, 5), ("uplink", uplink_path, 4)):
        with path.open(encoding="ascii") as source:
            for line in source:
                parts = line.split(",") if suffix == "uplink" else line.split()
                parts = [value.strip() for value in parts]
                if len(parts) != width or any(not value.isdigit() for value in parts):
                    raise RuntimeError("Malformed " + suffix + " row: " + experiment_id)
    resource = json.loads((folder / "logs" / "resource-summary.json").read_text(encoding="utf-8"))
    samples = [json.loads(line) for line in
               (folder / "logs" / "resource-samples.jsonl").read_text(encoding="utf-8").splitlines()
               if line]
    if not (resource["final_status"] == "SUCCEEDED" and
            resource["samples"] == len(samples) > 0 and
            resource["peak_tree_rss_mib"] <= 32768 and
            resource["minimum_mem_available_gib"] >= 32 and
            resource["minimum_free_gib"] >= 100 and
            max(row["load_1m"] for row in samples) <= 20):
        raise RuntimeError("Pilot resource gate failed: " + experiment_id)
    if not pfc and pfc_events != {"pause": 0, "resume": 0}:
        raise RuntimeError("PFC-disabled pilot emitted PFC events: " + experiment_id)
    diagnostics = {"timeout_recovery": 0, "nack_recovery": 0,
                   "irn_pfc_deferred": 0, "irn_pfc_recovery": 0}
    prefixes = (("WS08_TX_TIMEOUT ", "timeout_recovery"),
                ("WS08_TX_NACK ", "nack_recovery"),
                ("WS23_IRN_PFC_TIMEOUT_DEFERRED ", "irn_pfc_deferred"),
                ("WS23_IRN_PFC_TIMEOUT_RECOVERY ", "irn_pfc_recovery"))
    with (raw / "config.log").open(encoding="utf-8", errors="replace") as source:
        for line in source:
            for prefix, name in prefixes:
                if line.startswith(prefix):
                    diagnostics[name] += 1
    return {"id": experiment_id, "pfc": pfc, "irn": irn,
            "fct_sha256": summary["fct_sha256"],
            "input_flows": 16576, "completed_flows": 16576,
            "moe_batch_us": tags["2"]["synthetic_batch_completion_us"],
            "background_p99_us": tags["1"]["p99_fct_us"],
            "pfc_events": pfc_events, "recovery_diagnostics": diagnostics,
            "resource": resource}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", help="verify one cell before starting the next")
    args = parser.parse_args()
    selected = [cell for cell in CELLS if not args.id or cell[0] == args.id]
    if not selected:
        parser.error("Unknown transport pilot ID")
    result = {"role": "technical correctness pilot, not efficacy",
              "source_sha": SOURCE_SHA, "trace_sha256": TRACE_SHA,
              "cells": [verify(*cell) for cell in selected]}
    if args.id:
        print(json.dumps(result["cells"][0], sort_keys=True))
    else:
        target = ROOT / "docs/research/evidence/ws26-transport-correctness-pilot.json"
        target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"cells": len(result["cells"]), "output": str(target)}, sort_keys=True))


if __name__ == "__main__":
    main()
