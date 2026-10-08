#!/usr/bin/env python3
"""Verify WS-26 ClassLane v4 pilot cells from frozen inputs and raw results."""

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

import analyze_moe_tags


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs/research/evidence/ws26-classlane4-pilot-plan-r2.json"
PLAN = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
SOURCE_SHA = "41384701c865082655cdea9a9e64daae74f51327"
TOPOLOGY = "topo_1280_400G_400G_OS1"
TOPOLOGY_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
SEEDS = (20262694, 20262695, 20262696, 20262697)
MODE_NUMBERS = {"fecmp": 0, "drill": 2, "conga": 3, "letflow": 6,
                "conweave": 9, "classlane4": 24}


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def fields(line):
    return {key: int(value) for key, value in re.findall(r"(\w+)=(-?\d+)", line)}


def unique_file(folder, pattern):
    paths = list(folder.glob(pattern))
    if len(paths) != 1 or paths[0].is_symlink() or not paths[0].is_file():
        raise RuntimeError("Missing or ambiguous file: " + str(folder / pattern))
    return paths[0]


def check_plan():
    cells = PLAN["cells"]
    if (PLAN.get("revision") != "r2" or PLAN.get("source_sha") != SOURCE_SHA or
            PLAN.get("topology_sha256") != TOPOLOGY_SHA or len(cells) != 52 or
            len({row["id"] for row in cells}) != 52 or
            [row["order"] for row in cells] != list(range(1, 53)) or
            sum(row["stage"] == "high" for row in cells) != 28 or
            sum(row["stage"] == "conditional_low" for row in cells) != 24):
        raise RuntimeError("ClassLane v4 r2 pilot layout changed")
    if digest(ROOT / "config" / (TOPOLOGY + ".txt")) != TOPOLOGY_SHA:
        raise RuntimeError("Frozen topology hash changed")

    trace_hashes = {}
    id_prefix = "20261009-031000-ws26v4p1r2-"
    for row in cells:
        if (not row["id"].startswith(id_prefix) or row["seed"] not in SEEDS or
                row["background"] not in (0, 64, 128, 192) or
                row["mode"] not in MODE_NUMBERS or row["pfc"] != 1 or row["irn"] != 1 or
                row["ns3_seed"] != 1 or row["netload"] != 10 or
                row["simul_time"] != "0.01" or row["topology"] != TOPOLOGY or
                row["bw_gbps"] != 400 or row["buffer_mib"] != 9 or
                row["ws25_diag"] not in (0, 1) or
                row["expected_flows"] != 16384 + row["background"] or
                ((row["stage"] == "high") != (row["background"] == 192)) or
                (row["stage"] == "conditional_low" and row["ws25_diag"] != 0)):
            raise RuntimeError("Frozen cell identity mismatch: " + row["id"])
        if row["mode"] != "classlane4" and row["ws25_diag"] != 0:
            raise RuntimeError("Diagnostic flag on a non-candidate cell: " + row["id"])
        trace_hashes[row["trace"]] = row["trace_sha256"]
    if len(trace_hashes) != 16:
        raise RuntimeError("Expected 16 unique frozen traces")
    for name, expected in trace_hashes.items():
        if digest(ROOT / "config" / name) != expected:
            raise RuntimeError("Frozen trace hash changed: " + name)

    for seed in SEEDS:
        high = {(row["mode"], row["ws25_diag"]) for row in cells
                if row["seed"] == seed and row["stage"] == "high"}
        expected_high = {(mode, 0) for mode in
                         ("fecmp", "drill", "conga", "letflow", "conweave", "classlane4")}
        expected_high.add(("classlane4", 1))
        if high != expected_high:
            raise RuntimeError("High stage arms changed for seed " + str(seed))
        for background in (0, 64, 128):
            low = {(row["mode"], row["ws25_diag"]) for row in cells
                   if row["seed"] == seed and row["background"] == background}
            if low != {("fecmp", 0), ("classlane4", 0)}:
                raise RuntimeError("Conditional low stage changed for seed " + str(seed))
    return cells


def verify(cell):
    experiment_id = cell["id"]
    folder = ROOT / "results" / experiment_id
    if folder.is_symlink() or not folder.is_dir():
        raise RuntimeError("Result directory missing or linked: " + experiment_id)
    meta = json.loads(unique_file(folder, "metadata.json").read_text(encoding="utf-8"))
    params = meta.get("parameters", {})
    if not (meta.get("experiment_id") == experiment_id and
            meta.get("status") == "SUCCEEDED" and
            meta.get("git_commit") == SOURCE_SHA and
            meta.get("algorithm") == cell["mode"] and meta.get("seed") == 1 and
            meta.get("concurrency_cap") == 1 and
            meta.get("input_flow_sha256") == cell["trace_sha256"] and
            meta.get("topology_sha256") == TOPOLOGY_SHA and
            params.get("lb") == cell["mode"] and
            params.get("flow_file") == cell["trace"] and
            params.get("topo") == TOPOLOGY and params.get("bw") == 400 and
            params.get("buffer") == 9 and params.get("pfc") == 1 and
            params.get("irn") == 1 and params.get("ws25_diag") == cell["ws25_diag"] and
            params.get("ws26_time_probe") == 0 and params.get("netload") == 10 and
            params.get("simul_time") == "0.01" and params.get("factorial_pilot") is True):
        raise RuntimeError("Metadata identity or parameters mismatch: " + experiment_id)

    trace_snapshot = unique_file(folder / "config", "traffic_trace.txt")
    topology_snapshot = unique_file(folder / "config", "topology.txt")
    if digest(trace_snapshot) != cell["trace_sha256"] or digest(topology_snapshot) != TOPOLOGY_SHA:
        raise RuntimeError("Fetched input snapshot mismatch: " + experiment_id)
    config_file = unique_file(folder / "config", "config.txt")
    config_values = {}
    for line in config_file.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            config_values[parts[0]] = parts[1]
    if (config_values.get("LB_MODE") != str(MODE_NUMBERS[cell["mode"]]) or
            config_values.get("TOPOLOGY_FILE") != "config/" + TOPOLOGY + ".txt" or
            config_values.get("FLOW_FILE") != "config/" + cell["trace"] or
            config_values.get("ENABLE_PFC") != "1" or
            config_values.get("ENABLE_IRN") != "1" or
            config_values.get("BUFFER_SIZE") != "9"):
        raise RuntimeError("Simulation config snapshot mismatch: " + experiment_id)

    summary = analyze_moe_tags.summarize(experiment_id)
    tags = summary["tags"]
    expected_tags = {"2": 16384}
    if cell["background"]:
        expected_tags["1"] = cell["background"]
    if ({tag: item["input_flows"] for tag, item in tags.items()} != expected_tags or
            any(item["input_flows"] != item["completed_flows"] or
                item["unfinished_flows"] != 0 for item in tags.values())):
        raise RuntimeError("Input flow identity or completion mismatch: " + experiment_id)

    raw_id = str(meta.get("raw_directory", ""))
    if not re.fullmatch(r"[0-9]+", raw_id):
        raise RuntimeError("Invalid raw directory ID: " + experiment_id)
    raw = folder / "raw" / raw_id
    if raw.is_symlink() or not raw.is_dir():
        raise RuntimeError("Raw directory missing or linked: " + experiment_id)
    raw_files = {suffix: unique_file(raw, "*" + suffix) for suffix in
                 ("_out_fct.txt", "_out_cnp.txt", "_out_pfc.txt", "_out_uplink.txt")}
    if digest(raw_files["_out_fct.txt"]) != summary["fct_sha256"]:
        raise RuntimeError("FCT raw hash mismatch: " + experiment_id)
    fct_rows = sum(1 for line in raw_files["_out_fct.txt"].open(encoding="ascii") if line.strip())
    if fct_rows != cell["expected_flows"]:
        raise RuntimeError("FCT row count mismatch: " + experiment_id)
    pfc_events = {"pause": 0, "resume": 0}
    with raw_files["_out_pfc.txt"].open(encoding="ascii") as source:
        for line in source:
            parts = line.split()
            if len(parts) != 5 or parts[-1] not in ("0", "1"):
                raise RuntimeError("Malformed PFC event: " + experiment_id)
            pfc_events["pause" if parts[-1] == "1" else "resume"] += 1

    route = None
    queue = None
    ports = []
    qp_paths = []
    if cell["mode"] == "classlane4":
        log_file = unique_file(folder / "logs", "config.log")
        log_lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        route_lines = [line for line in log_lines if line.startswith("WS26_CLASSLANE4 ")]
        queue_lines = [line for line in log_lines if line.startswith("WS26_QUEUE ")]
        if len(route_lines) != 1 or len(queue_lines) != 1:
            raise RuntimeError("ClassLane route or queue summary missing: " + experiment_id)
        route, queue = fields(route_lines[0]), fields(queue_lines[0])
        if (route.get("missing_destination") != 0 or route.get("inconsistent") != 0 or
                route.get("queue_violations") != 0 or
                queue.get("enqueued") != queue.get("dequeued", 0) +
                queue.get("queued_drop", 0) + queue.get("current", 0)):
            raise RuntimeError("ClassLane route or queue conservation failed: " + experiment_id)
        for tag, name in ((1, "background"), (2, "moe")):
            packet_key = name + "_packets"
            new_key = name + "_qp_new"
            reused_key = name + "_qp_reused"
            diverted_key = name + "_diverted"
            if (any(key not in route for key in
                    (packet_key, new_key, reused_key, diverted_key)) or
                    route[packet_key] != route[new_key] + route[reused_key] or
                    route[diverted_key] > route[packet_key]):
                raise RuntimeError("ClassLane per-tag route counters mismatch: " + experiment_id)
        port_lines = [line for line in log_lines if line.startswith("WS26_CLASSLANE4_PORT ")]
        ports = [fields(line) for line in port_lines]
        for tag, name in ((1, "background"), (2, "moe")):
            total = sum(row.get("packets", 0) for row in ports if row.get("tag") == tag)
            if total != route[name + "_packets"]:
                raise RuntimeError("ClassLane port packet count mismatch: " + experiment_id)
        if cell["ws25_diag"]:
            qp_paths = [fields(line) for line in log_lines
                        if line.startswith("WS26_CLASSLANE4_QP ")]
            paths_by_qp = {}
            ports_by_switch_dest = collections.defaultdict(lambda: {1: set(), 2: set()})
            for row in qp_paths:
                key = (row.get("switch"), row.get("sip"), row.get("dip"),
                       row.get("sport"), row.get("dport"))
                signature = (row.get("tag"), row.get("dst_tor"), row.get("port"))
                if row.get("tag") not in (1, 2) or row.get("packets", 0) <= 0:
                    raise RuntimeError("Invalid per-QP ClassLane row: " + experiment_id)
                if key in paths_by_qp and paths_by_qp[key] != signature:
                    raise RuntimeError("A QP changed class, destination ToR, or port")
                paths_by_qp[key] = signature
                ports_by_switch_dest[(row["switch"], row["dst_tor"])][row["tag"]].add(
                    row["port"])
            if (sum(row.get("packets", 0) for row in qp_paths if row.get("tag") == 1) !=
                    route["background_packets"] or
                    sum(row.get("packets", 0) for row in qp_paths if row.get("tag") == 2) !=
                    route["moe_packets"] or
                    sum(row.get("tag") == 1 for row in qp_paths) !=
                    route["background_qp_new"] or
                    sum(row.get("tag") == 2 for row in qp_paths) != route["moe_qp_new"] or
                    any(groups[1] & groups[2] for groups in ports_by_switch_dest.values())):
                raise RuntimeError("ClassLane diagnostic path or port isolation failed")

    resource = json.loads(unique_file(folder / "logs", "resource-summary.json")
                          .read_text(encoding="utf-8"))
    sample_file = unique_file(folder / "logs", "resource-samples.jsonl")
    samples = [json.loads(line) for line in sample_file.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    if not (resource.get("id") == experiment_id and
            resource.get("final_status") == "SUCCEEDED" and
            resource.get("samples") == len(samples) > 0 and
            resource.get("peak_tree_rss_mib", 10**12) <= 32768 and
            resource.get("minimum_mem_available_gib", 0) >= 32 and
            resource.get("minimum_free_gib", 0) >= 100 and
            max(row.get("load_1m", 10**12) for row in samples) <= 20):
        raise RuntimeError("Pilot resource gate failed: " + experiment_id)

    return {
        "id": experiment_id,
        "stage": cell["stage"],
        "seed": cell["seed"],
        "background": cell["background"],
        "mode": cell["mode"],
        "ws25_diag": cell["ws25_diag"],
        "trace_sha256": cell["trace_sha256"],
        "fct_sha256": summary["fct_sha256"],
        "flow_count": cell["expected_flows"],
        "moe_batch_us": tags["2"]["synthetic_batch_completion_us"],
        "moe_mean_fct_us": tags["2"]["mean_fct_us"],
        "moe_p99_fct_us": tags["2"]["p99_fct_us"],
        "background_p99_us": tags.get("1", {}).get("p99_fct_us"),
        "background_mean_fct_us": tags.get("1", {}).get("mean_fct_us"),
        "completion_rate": {tag: item["completion_rate"] for tag, item in tags.items()},
        "pfc_events": pfc_events,
        "route": route,
        "queue": queue,
        "port_rows": ports,
        "diagnostic_qp_paths": qp_paths,
        "resource_samples": len(samples),
        "peak_tree_rss_mib": resource["peak_tree_rss_mib"],
    }


def verify_selection(cells, selected):
    rows = [verify(cell) for cell in selected]
    indexed = {(row["seed"], row["background"], row["mode"], row["ws25_diag"]): row
               for row in rows}
    if len(indexed) != len(rows):
        raise RuntimeError("Duplicate verified pilot cell")
    for row in rows:
        if row["mode"] == "classlane4" and row["ws25_diag"]:
            plain = indexed.get((row["seed"], row["background"], "classlane4", 0))
            if plain and plain["fct_sha256"] != row["fct_sha256"]:
                raise RuntimeError("Diagnostic changed FCT: " + row["id"])
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--id", choices=[cell["id"] for cell in PLAN["cells"]])
    group.add_argument("--stage", choices=("high", "conditional_low", "all"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cells = check_plan()
    selected = ([row for row in cells if row["id"] == args.id] if args.id else
                [row for row in cells if args.stage == "all" or row["stage"] == args.stage])
    rows = verify_selection(cells, selected)
    result = {"verified": len(rows), "requested": len(selected), "cells": rows}
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as target:
            target.write(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
