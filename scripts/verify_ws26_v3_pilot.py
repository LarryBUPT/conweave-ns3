#!/usr/bin/env python3
"""Verify frozen WS-26 v3 pilot cells against original raw and resource receipts."""

import argparse
import hashlib
import json
import re
from pathlib import Path

import analyze_moe_tags


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs/research/evidence/ws26-v3-pilot-plan.json"
PLAN = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
TOPO_NAME = "topo_1280_400G_400G_OS1"


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def fields(line):
    return {key: int(value) for key, value in re.findall(r"(\w+)=(-?\d+)", line)}


def unique_raw(raw, suffix):
    paths = list(raw.glob("*" + suffix))
    if len(paths) != 1 or paths[0].is_symlink() or not paths[0].is_file():
        raise RuntimeError("Missing or ambiguous raw " + suffix + " in " + str(raw))
    return paths[0]


def one_counter(log, prefix, experiment_id):
    rows = [fields(line) for line in log.splitlines() if line.startswith(prefix + " ")]
    if len(rows) != 1:
        raise RuntimeError("Missing or duplicated " + prefix + " in " + experiment_id)
    return rows[0]


def check_plan():
    cells = PLAN["cells"]
    if (len(cells) != 52 or len({row["id"] for row in cells}) != 52 or
            [row["order"] for row in cells] != list(range(1, 53)) or
            sum(row["stage"] == "high" for row in cells) != 28 or
            sum(row["stage"] == "low" for row in cells) != 24):
        raise RuntimeError("Pilot layout changed")
    if digest(ROOT / "config" / (TOPO_NAME + ".txt")) != PLAN["topology_sha256"]:
        raise RuntimeError("Local topology changed")
    for row in cells:
        if (row["seed"] not in range(20262690, 20262694) or
                row["background"] not in (0, 64, 128, 192) or
                row["pfc"] != 1 or row["irn"] != 1 or
                row["expected_flows"] != 16384 + row["background"] or
                (row["stage"] == "high") != (row["background"] == 192) or
                digest(ROOT / "config" / row["trace"]) != row["trace_sha256"]):
            raise RuntimeError("Pilot input or plan mismatch: " + row["id"])
    for seed in range(20262690, 20262694):
        high = {(row["mode"], row["ws25_diag"]) for row in cells
                if row["seed"] == seed and row["background"] == 192}
        expected_high = {(mode, 0) for mode in
                         ("fecmp", "drill", "conga", "letflow", "conweave",
                          "classreserve3")}
        expected_high.add(("classreserve3", 1))
        if high != expected_high:
            raise RuntimeError("High stage arms changed for seed " + str(seed))
        for background in (0, 64, 128):
            low = {(row["mode"], row["ws25_diag"]) for row in cells
                   if row["seed"] == seed and row["background"] == background}
            if low != {("fecmp", 0), ("classreserve3", 0)}:
                raise RuntimeError("Low stage arms changed for seed " + str(seed))
    return cells


def verify(cell):
    experiment_id = cell["id"]
    folder = ROOT / "results" / experiment_id
    if folder.is_symlink() or not folder.is_dir():
        raise RuntimeError("Result directory missing or linked: " + experiment_id)
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = meta["parameters"]
    if not (meta["status"] == "SUCCEEDED" and
            meta["git_commit"] == PLAN["source_sha"] and
            meta["algorithm"] == cell["mode"] and meta["seed"] == 1 and
            meta["input_flow_sha256"] == cell["trace_sha256"] and
            meta["topology_sha256"] == PLAN["topology_sha256"] and
            params["lb"] == cell["mode"] and
            params["flow_file"] == cell["trace"] and
            params["topo"] == TOPO_NAME and params["bw"] == 400 and
            params["buffer"] == 9 and params["pfc"] == 1 and
            params["irn"] == 1 and params["ws25_diag"] == cell["ws25_diag"] and
            params["ws26_time_probe"] == 0 and params["netload"] == 10 and
            params["simul_time"] == "0.01"):
        raise RuntimeError("Pilot metadata identity mismatch: " + experiment_id)
    if (digest(folder / "config/traffic_trace.txt") != cell["trace_sha256"] or
            digest(folder / "config/topology.txt") != PLAN["topology_sha256"]):
        raise RuntimeError("Pilot input snapshot mismatch: " + experiment_id)
    summary = analyze_moe_tags.summarize(experiment_id)
    tags = summary["tags"]
    expected_tags = {"2": 16384}
    if cell["background"]:
        expected_tags["1"] = cell["background"]
    if ({tag: value["input_flows"] for tag, value in tags.items()} != expected_tags or
            any(value["input_flows"] != value["completed_flows"]
                for value in tags.values())):
        raise RuntimeError("Pilot flow identity or completion failed: " + experiment_id)
    raw_id = str(meta["raw_directory"])
    if not re.fullmatch(r"[0-9]+", raw_id):
        raise RuntimeError("Invalid raw ID: " + experiment_id)
    raw = folder / "raw" / raw_id
    if raw.is_symlink() or not raw.is_dir():
        raise RuntimeError("Raw directory missing or linked: " + experiment_id)
    for suffix in ("_out_fct.txt", "_out_cnp.txt", "_out_pfc.txt", "_out_uplink.txt"):
        unique_raw(raw, suffix)
    fct_sha = digest(unique_raw(raw, "_out_fct.txt"))
    if fct_sha != summary["fct_sha256"]:
        raise RuntimeError("Pilot FCT hash mismatch: " + experiment_id)
    pfc_file = unique_raw(raw, "_out_pfc.txt")
    pfc_events = {"pause": 0, "resume": 0}
    with pfc_file.open(encoding="ascii") as source:
        for line in source:
            parts = line.split()
            if len(parts) != 5 or parts[-1] not in ("0", "1"):
                raise RuntimeError("Malformed PFC event: " + experiment_id)
            pfc_events["pause" if parts[-1] == "1" else "resume"] += 1

    route = None
    per_qp = None
    if cell["mode"] == "classreserve3":
        log = (folder / "logs/config.log").read_text(encoding="utf-8", errors="replace")
        route = one_counter(log, "WS26_CLASSRESERVE3", experiment_id)
        queue = one_counter(log, "WS26_QUEUE", experiment_id)
        if (route.get("queue_violations") != 0 or
                route.get("missing_destination") != 0 or
                route.get("background_packets") != route.get("background_new", 0) +
                route.get("background_reused", 0) or
                route.get("moe_packets") != route.get("moe_new", 0) +
                route.get("moe_reused", 0) or
                route.get("choices") != route.get("moe_new") or
                queue.get("enqueued") != queue.get("dequeued", 0) +
                queue.get("queued_drop", 0) + queue.get("current", 0) or
                route.get("moe_new", 0) <= 0 or
                (cell["background"] > 0 and route.get("background_new", 0) <= 0)):
            raise RuntimeError("Pilot ClassReserve v3 conservation failed: " + experiment_id)
        if cell["ws25_diag"]:
            per_qp = [fields(line) for line in log.splitlines()
                      if line.startswith("WS26_CLASSRESERVE3_QP ")]
            identities = {(row.get("switch"), row.get("sip"), row.get("dip"),
                           row.get("sport"), row.get("dport")) for row in per_qp}
            if (len(per_qp) != route["background_new"] + route["moe_new"] or
                    len(identities) != len(per_qp) or
                    sum(row.get("tag") == 1 for row in per_qp) != route["background_new"] or
                    sum(row.get("tag") == 2 for row in per_qp) != route["moe_new"] or
                    sum(row.get("packets", 0) for row in per_qp if row.get("tag") == 1) !=
                    route["background_packets"] or
                    sum(row.get("packets", 0) for row in per_qp if row.get("tag") == 2) !=
                    route["moe_packets"] or
                    any(row.get("inconsistent") != 0 or row.get("packets", 0) <= 0
                        for row in per_qp)):
                raise RuntimeError("Pilot per-QP path check failed: " + experiment_id)

    resource = json.loads((folder / "logs/resource-summary.json").read_text(
        encoding="utf-8"))
    samples = [json.loads(line) for line in (folder / "logs/resource-samples.jsonl")
               .read_text(encoding="utf-8").splitlines() if line]
    if not (resource["final_status"] == "SUCCEEDED" and
            resource["samples"] == len(samples) > 0 and
            resource["peak_tree_rss_mib"] <= 32768 and
            resource["minimum_mem_available_gib"] >= 32 and
            resource["minimum_free_gib"] >= 100 and
            max(row["load_1m"] for row in samples) <= 20):
        raise RuntimeError("Pilot resource gate failed: " + experiment_id)
    return {"id": experiment_id, "stage": cell["stage"], "seed": cell["seed"],
            "background": cell["background"], "mode": cell["mode"],
            "ws25_diag": cell["ws25_diag"], "fct_sha256": fct_sha,
            "moe_batch_us": tags["2"]["synthetic_batch_completion_us"],
            "moe_mean_fct_us": tags["2"]["mean_fct_us"],
            "moe_p99_fct_us": tags["2"]["p99_fct_us"],
            "background_p99_us": tags.get("1", {}).get("p99_fct_us"),
            "background_mean_fct_us": tags.get("1", {}).get("mean_fct_us"),
            "pfc_events": pfc_events, "route": route,
            "diagnostic_path_count": len(per_qp) if per_qp is not None else None,
            "resource_samples": len(samples),
            "peak_tree_rss_mib": resource["peak_tree_rss_mib"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--id")
    group.add_argument("--stage", choices=("high", "low", "all"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cells = check_plan()
    selected = [row for row in cells if row["id"] == args.id] if args.id else [
        row for row in cells if args.stage == "all" or row["stage"] == args.stage]
    if not selected:
        parser.error("ID outside frozen pilot plan")
    rows = [verify(row) for row in selected]
    keyed = {(row["seed"], row["background"], row["mode"], row["ws25_diag"]): row
             for row in rows}
    for row in rows:
        if row["mode"] == "classreserve3" and row["ws25_diag"]:
            plain = keyed.get((row["seed"], row["background"], "classreserve3", 0))
            if plain and plain["fct_sha256"] != row["fct_sha256"]:
                raise RuntimeError("Pilot diagnostic changed FCT: " + row["id"])
    result = {"verified": len(rows), "requested": len(selected), "cells": rows}
    rendered = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
