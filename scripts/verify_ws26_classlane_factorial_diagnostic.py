#!/usr/bin/env python3
"""Verify one frozen WS-26 class-rule factorial diagnostic cell from raw."""

import argparse
import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path

import analyze_moe_tags
import analyze_ws26_seed97_time_aligned as timeline
import verify_ws26_seed97_time_aligned as previous
from verify_ws26_moe_hop_diagnostic import fields, raw_fct, topology_maps, trace_qps, unique_file
from verify_ws26_seed97_probe_preflight import HEADER, HEADER_QUAD, ROOT


PLAN_COMMIT = "f4477d43282a0e381c9269d9d69f62a0c0853480"
PLAN_PATH = "docs/research/evidence/ws26-classlane-factorial-diagnostic-plan.json"
PLAN_SHA256 = "4a08ce8746e984c301ffdcfdbf18336e408d1b17391aeb967c3abb5a11d5f77b"
SOURCE_SHA = "9877303a6be2e63836373d94f315283dc5bea453"
RECEIPTS = ROOT / "results/ws26-classlane-factorial-diagnostic/receipts.jsonl"
MODE_NUMBERS = {"fecmp": 0, "classlane4": 24,
                "classlane4-moe-only": 25, "classlane4-background-only": 26}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_plan():
    data = subprocess.check_output(["git", "show", PLAN_COMMIT + ":" + PLAN_PATH], cwd=ROOT)
    if hashlib.sha256(data).hexdigest() != PLAN_SHA256:
        raise RuntimeError("Committed factorial plan SHA differs from frozen value")
    plan = json.loads(data.decode("utf-8"))
    cells = plan.get("cells", [])
    if (plan.get("source_sha") != SOURCE_SHA or len(cells) != 10 or
            [cell["order"] for cell in cells] != list(range(1, 11)) or
            len({cell["id"] for cell in cells}) != 10):
        raise RuntimeError("Frozen factorial plan layout or source SHA changed")
    if (digest(HEADER) != plan["target_header_sha256"] or
            digest(ROOT / "docs/research/ws26-classlane-factorial-diagnostic-design.md") !=
            plan["design_sha256"] or
            digest(ROOT / "config" / (plan["topology"] + ".txt")) !=
            plan["topology_sha256"]):
        raise RuntimeError("Frozen header, design, or topology changed")
    for cell in cells:
        if (MODE_NUMBERS.get(cell["mode"]) != cell["mode_number"] or
                digest(ROOT / "config" / cell["trace"]) != cell["trace_sha256"]):
            raise RuntimeError("Frozen mode or trace differs from plan: " + cell["id"])
    return plan


def receipt(experiment_id, event):
    if not RECEIPTS.is_file() or RECEIPTS.is_symlink():
        raise RuntimeError("Controller receipts missing")
    rows = [json.loads(line) for line in RECEIPTS.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    matches = [row for row in rows if row.get("id") == experiment_id and
               row.get("event") == event]
    if len(matches) != 1:
        raise RuntimeError("Missing or ambiguous %s receipt: %s" % (event, experiment_id))
    return matches[0]


def check_resources(folder, cell, plan):
    logs = folder / "logs"
    samples = [json.loads(line) for line in unique_file(
        logs, "resource-samples.jsonl").read_text(encoding="utf-8").splitlines()
               if line.strip()]
    final = json.loads(unique_file(logs, "resource-summary.json").read_text(encoding="utf-8"))
    limits = plan["resource_limits_per_cell"]
    first = receipt(cell["id"], "watcher_first_sample")
    if (not samples or not first.get("sample") or
            final.get("id") != cell["id"] or final.get("final_status") != "SUCCEEDED" or
            final.get("samples") != len(samples) or
            final.get("peak_tree_rss_mib", 10**12) > limits["peak_tree_rss_mib"] or
            final.get("minimum_mem_available_gib", 0) < limits["min_mem_available_gib"] or
            final.get("minimum_free_gib", 0) < limits["min_free_gib"] or
            max(row.get("load_1m", 10**12) for row in samples) > limits["max_load_1m"]):
        raise RuntimeError("Resource or watcher receipt failed: " + cell["id"])
    return {"samples": len(samples), "peak_tree_rss_mib": final["peak_tree_rss_mib"]}


def check_classlane(log, cell, expected):
    route_lines = []
    queue_lines = []
    port_rows = []
    qp_rows = []
    with log.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if line.startswith("WS26_CLASSLANE4 "):
                route_lines.append(fields(line))
            elif line.startswith("WS26_QUEUE "):
                queue_lines.append(fields(line))
            elif line.startswith("WS26_CLASSLANE4_PORT "):
                port_rows.append(fields(line))
            elif line.startswith("WS26_CLASSLANE4_QP "):
                qp_rows.append(fields(line))
    if cell["mode"] == "fecmp":
        if route_lines or queue_lines or port_rows or qp_rows:
            raise RuntimeError("ECMP unexpectedly emitted ClassLane counters")
        return None
    if len(route_lines) != 1 or len(queue_lines) != 1:
        raise RuntimeError("ClassLane route or queue summary missing")
    route, queue = route_lines[0], queue_lines[0]
    if (route.get("mode") != cell["mode_number"] or
            route.get("missing_destination") != 0 or route.get("inconsistent") != 0 or
            route.get("queue_violations") != 0 or
            queue.get("enqueued") != queue.get("dequeued", 0) +
            queue.get("queued_drop", 0) + queue.get("current", 0)):
        raise RuntimeError("ClassLane mode, path, or queue conservation failed")
    for tag, name, enabled in ((1, "background", cell["background_rule"]),
                               (2, "moe", cell["moe_rule"])):
        packets = route.get(name + "_packets", -1)
        bypassed = route.get(name + "_bypassed", -1)
        new = route.get(name + "_qp_new", -1)
        reused = route.get(name + "_qp_reused", -1)
        diverted = route.get(name + "_diverted", -1)
        if min(packets, bypassed, new, reused, diverted) < 0:
            raise RuntimeError("Missing or invalid per-class ClassLane counter")
        if enabled:
            if not (packets > 0 and new > 0 and packets == new + reused and
                    bypassed == 0 and diverted <= packets):
                raise RuntimeError("Active ClassLane class was not exercised")
        elif not (packets == new == reused == diverted == 0 and bypassed > 0):
            raise RuntimeError("Disabled class was not bypassed to ECMP")
        if sum(row.get("packets", 0) for row in port_rows if row.get("tag") == tag) != packets:
            raise RuntimeError("ClassLane port packet count differs from route count")
        matching_qps = [row for row in qp_rows if row.get("tag") == tag]
        if (sum(row.get("packets", 0) for row in matching_qps) != packets or
                len(matching_qps) != new):
            raise RuntimeError("ClassLane QP path counts differ from route count")
        if not enabled and matching_qps:
            raise RuntimeError("Bypassed class emitted ClassLane QP path rows")
        qp_keys = [tuple(row.get(k) for k in ("switch", "sip", "dip", "sport", "dport"))
                   for row in matching_qps]
        if (any(any(value is None for value in key) for key in qp_keys) or
                len(set(qp_keys)) != len(qp_keys) or
                any(row.get("dst_tor", 0) <= 0 or row.get("port", 0) <= 0
                    for row in matching_qps)):
            raise RuntimeError("ClassLane QP path identity is malformed or duplicated")
    return {"route": route, "queue": queue, "qp_path_rows": len(qp_rows)}


def check(cell, plan):
    folder = ROOT / "results" / cell["id"]
    if folder.is_symlink() or not folder.is_dir():
        raise RuntimeError("Fetched result directory missing: " + cell["id"])
    meta = json.loads(unique_file(folder, "metadata.json").read_text(encoding="utf-8"))
    params = meta.get("parameters", {})
    if not (meta.get("experiment_id") == cell["id"] and meta.get("status") == "SUCCEEDED" and
            meta.get("git_commit") == SOURCE_SHA and meta.get("algorithm") == cell["mode"] and
            meta.get("seed") == cell["ns3_seed"] and meta.get("concurrency_cap") == 1 and
            meta.get("input_flow_sha256") == cell["trace_sha256"] and
            meta.get("topology_sha256") == plan["topology_sha256"] and
            params.get("lb") == cell["mode"] and params.get("flow_file") == cell["trace"] and
            params.get("topo") == plan["topology"] and params.get("bw") == 400 and
            params.get("buffer") == 9 and params.get("pfc") == cell["pfc"] and
            params.get("irn") == cell["irn"] and params.get("ws25_diag") == cell["ws25_diag"] and
            params.get("ws26_moe_hop_diag") == cell["ws26_moe_hop_diag"] and
            params.get("ws26_seed97_time_diag") == cell["ws26_seed97_time_diag"] and
            params.get("netload") == 10 and params.get("simul_time") == "0.01" and
            params.get("factorial_pilot") is True):
        raise RuntimeError("Metadata or run parameters differ from frozen plan: " + cell["id"])
    config = folder / "config"
    trace = unique_file(config, "traffic_trace.txt")
    topology = unique_file(config, "topology.txt")
    if digest(trace) != cell["trace_sha256"] or digest(topology) != plan["topology_sha256"]:
        raise RuntimeError("Fetched trace or topology differs from frozen plan")
    values = {parts[0]: parts[1] for line in unique_file(config, "config.txt").read_text(
        encoding="utf-8").splitlines() if len(parts := line.split()) > 1}
    if (values.get("LB_MODE") != str(cell["mode_number"]) or
            values.get("ENABLE_PFC") != "1" or values.get("ENABLE_IRN") != "1" or
            values.get("BUFFER_SIZE") != "9" or
            values.get("TOPOLOGY_FILE") != "config/" + plan["topology"] + ".txt" or
            values.get("FLOW_FILE") != "config/" + cell["trace"]):
        raise RuntimeError("Simulation config snapshot differs from frozen plan")
    classes = analyze_moe_tags.summarize(cell["id"])["tags"]
    if (classes.get("1", {}).get("input_flows") != cell["expected_background_qps"] or
            classes.get("2", {}).get("input_flows") != cell["expected_moe_qps"] or
            any(row["completed_flows"] != row["input_flows"] or row["unfinished_flows"]
                for row in classes.values()) or
            sum(row["completed_flows"] for row in classes.values()) != cell["expected_flows"]):
        raise RuntimeError("One or more input flows did not complete exactly once")
    expected = trace_qps(trace)
    if len(expected) != cell["expected_flows"]:
        raise RuntimeError("Trace QP count differs from frozen plan")
    fct = raw_fct(folder, meta)
    fct_sha = previous.fct_identity(fct, expected)
    if cell["expected_fct_sha256"] and fct_sha != cell["expected_fct_sha256"]:
        raise RuntimeError("Reference diagnostic FCT differs from frozen old plain cell")
    if cell["plain_pair_order"] is not None:
        paired = plan["cells"][cell["plain_pair_order"] - 1]
        paired_folder = ROOT / "results" / paired["id"]
        paired_meta = json.loads(unique_file(paired_folder, "metadata.json").read_text(
            encoding="utf-8"))
        if fct_sha != digest(raw_fct(paired_folder, paired_meta)):
            raise RuntimeError("Probe FCT differs from its paired plain cell")
    selected = {tuple(map(int, match)) for match in
                HEADER_QUAD.findall(HEADER.read_text(encoding="utf-8"))} & set(expected)
    if len(selected) != (2 if cell["stage"].startswith("smoke_") else 23):
        raise RuntimeError("Selected QP identities differ from frozen header")
    log = unique_file(folder / "logs", "config.log")
    logs = previous.check_logs(log, expected, selected, topology,
                               cell["ws26_seed97_time_diag"],
                               plan["log_limits_per_probe_cell"])
    if cell["ws26_seed97_time_diag"]:
        events, hops, summary_hops = timeline.parse_log(folder, selected)
        maps = topology_maps(topology)
        fct_selected = timeline.parse_fct(folder, meta, expected, selected)
        for key in selected:
            timeline.summarize_qp(key, fct_selected[key], events[key], hops[key],
                                  summary_hops[key], maps)
    route = check_classlane(log, cell, expected)
    resources = check_resources(folder, cell, plan)
    raw = folder / "raw" / str(meta["raw_directory"])
    pfc = unique_file(raw, "*_out_pfc.txt")
    pfc_rows = 0
    with pfc.open(encoding="ascii") as stream:
        for line in stream:
            parts = line.split()
            if len(parts) != 5 or parts[-1] not in ("0", "1"):
                raise RuntimeError("Malformed PFC event")
            pfc_rows += 1
    return {"id": cell["id"], "order": cell["order"], "mode": cell["mode"],
            "source_sha": SOURCE_SHA, "trace_sha256": cell["trace_sha256"],
            "fct_sha256": fct_sha, "completed_flows": len(expected),
            "pfc_rows": pfc_rows, "route": route, "resource": resources,
            "config_log_sha256": digest(log), **logs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True)
    args = parser.parse_args()
    plan = load_plan()
    cell = next((row for row in plan["cells"] if row["id"] == args.id), None)
    if cell is None:
        raise RuntimeError("ID absent from frozen factorial plan")
    print(json.dumps(check(cell, plan), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
