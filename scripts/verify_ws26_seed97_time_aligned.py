#!/usr/bin/env python3
"""Verify each frozen seed 97 time-aligned diagnostic cell from fetched raw."""

import argparse
import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path

import analyze_moe_tags
from verify_ws26_moe_hop_diagnostic import (
    fields, path_for, raw_fct, topology_maps, trace_qps, unique_file,
)
from verify_ws26_seed97_probe_preflight import HEADER_QUAD, HEADER, ROOT


PLAN_PATH = "docs/research/evidence/ws26-seed97-time-aligned-plan.json"
RECEIPTS = ROOT / "results/ws26-seed97-time-aligned/receipts.jsonl"
MODE_NUMBERS = {"fecmp": 0, "classlane4": 24}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_plan(expected_sha):
    data = subprocess.check_output(["git", "show", "HEAD:" + PLAN_PATH], cwd=ROOT)
    if hashlib.sha256(data).hexdigest() != expected_sha:
        raise RuntimeError("Committed plan SHA differs from the frozen value")
    plan = json.loads(data.decode("utf-8"))
    if (len(plan["cells"]) != 4 or
            [row["order"] for row in plan["cells"]] != [1, 2, 3, 4] or
            [row["stage"] for row in plan["cells"]] !=
            ["smoke_plain", "smoke_probe", "paired_high", "paired_high"]):
        raise RuntimeError("Frozen plan layout changed")
    if digest(HEADER) != plan["target_header_sha256"]:
        raise RuntimeError("Selected QP header differs from the frozen plan")
    return plan


def receipt(experiment_id, event):
    if not RECEIPTS.is_file() or RECEIPTS.is_symlink():
        raise RuntimeError("Controller receipts missing")
    rows = [json.loads(line) for line in RECEIPTS.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    matches = [row for row in rows if row.get("id") == experiment_id
               and row.get("event") == event]
    if len(matches) != 1:
        raise RuntimeError("Missing or ambiguous %s receipt: %s" % (event, experiment_id))
    return matches[0]


def fct_identity(fct, expected):
    observed = set()
    with fct.open(encoding="ascii") as stream:
        for line in stream:
            values = list(map(int, line.split()))
            if len(values) != 8:
                raise RuntimeError("Malformed FCT row")
            key = tuple(values[:4])
            if key in observed or key not in expected:
                raise RuntimeError("Duplicate or unexpected FCT QP")
            wanted = expected[key]
            if values[4] != wanted["size"] or abs(values[5] - wanted["start_ns"]) > 2:
                raise RuntimeError("FCT size/start differs from input")
            observed.add(key)
    if observed != set(expected):
        raise RuntimeError("FCT identity set differs from the input")
    return digest(fct)


def check_resources(folder, cell, plan):
    logs = folder / "logs"
    samples = [json.loads(line) for line in unique_file(
        logs, "resource-samples.jsonl").read_text(encoding="utf-8").splitlines()
               if line.strip()]
    final = json.loads(unique_file(logs, "resource-summary.json").read_text(encoding="utf-8"))
    limits = plan["resource_limits"]
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


def check_logs(log, expected, selected, topology, probe, limits):
    hop_qps = collections.defaultdict(list)
    probe_hops = collections.Counter()
    probe_hop_bytes = 0
    qp_events = collections.defaultdict(collections.Counter)
    qp_rows = collections.Counter()
    qp_bytes = collections.Counter()
    qp_summary = {}
    switch_summary = []
    unpaired = []
    topology_index = topology_maps(topology)
    port_to_neighbor = topology_index[3]
    with log.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if line.startswith(("WS13_HOP ", "WS26_MOE_HOP ")):
                row = fields(line)
                row["tag"] = 1 if line.startswith("WS13_HOP ") else 2
                key = tuple(row[name] for name in ("src", "dst", "sport", "dport"))
                hop_qps[key].append(row)
            elif line.startswith("WS13_INFLIGHT "):
                unpaired.append(fields(line)["unpaired"])
            elif line.startswith("WS26_S97_HOP "):
                if not probe:
                    raise RuntimeError("Probe hop line in plain smoke")
                row = fields(line)
                key = tuple(row[name] for name in ("src", "dst", "sport", "dport"))
                if (key not in selected or row["tag"] != expected[key]["tag"] or
                        row["enqueue_ns"] > row["dequeue_ns"] or
                        row["packet_bytes"] <= 0 or row["ecn"] not in (0, 1)):
                    raise RuntimeError("Invalid selected QP hop row")
                neighbor = port_to_neighbor[row["switch"]].get(row["port"] - 1)
                if neighbor is None:
                    raise RuntimeError("Selected hop port absent from topology")
                packet_key = (key, row["uid"], row["switch"])
                probe_hops[packet_key] += 1
                probe_hop_bytes += len(line.encode("utf-8"))
            elif line.startswith("WS26_S97_QP event="):
                if not probe:
                    raise RuntimeError("Probe event line in plain smoke")
                row = fields(line)
                key = tuple(row[name] for name in ("src", "dst", "sport", "dport"))
                if key not in selected or row["tag"] != expected[key]["tag"]:
                    raise RuntimeError("Unselected or mislabelled QP event")
                event = line.split("event=", 1)[1].split()[0]
                qp_events[key][event] += 1
                qp_rows[key] += 1
                qp_bytes[key] += len(line.encode("utf-8"))
            elif line.startswith("WS26_S97_QP_SUMMARY "):
                row = fields(line)
                key = tuple(row[name] for name in ("src", "dst", "sport", "dport"))
                if key in qp_summary:
                    raise RuntimeError("Duplicate selected QP summary")
                qp_summary[key] = row
            elif line.startswith("WS26_S97_SWITCH_SUMMARY "):
                switch_summary.append(fields(line))

    if unpaired != [0] or set(hop_qps) != set(expected):
        raise RuntimeError("All-flow hop coverage or queue pairing failed")
    for key, wanted in expected.items():
        rows = hop_qps[key]
        if any(row["tag"] != wanted["tag"] for row in rows):
            raise RuntimeError("Hop tag differs from input")
        ordered = path_for(rows, key[0], key[1], topology_index[0],
                           topology_index[2], topology_index[3])
        if any(row["packets"] <= 0 or row["bytes"] <= 0 for row in ordered):
            raise RuntimeError("Hop packet/byte counters invalid")
    if not probe:
        if qp_events or qp_summary or switch_summary or probe_hops:
            raise RuntimeError("Plain smoke emitted selected probe records")
        return {"hop_qps": len(hop_qps), "probe_qps": 0, "probe_hops": 0}
    if (set(qp_events) != selected or set(qp_summary) != selected or
            len(switch_summary) != 1 or not probe_hops or
            any(count != 1 for count in probe_hops.values())):
        raise RuntimeError("Selected QP coverage, summary, or packet pairing failed")
    for key in selected:
        events = qp_events[key]
        summary = qp_summary[key]
        if (not events["send"] or not events["ack"] or events["complete"] != 1 or
                summary["rows"] != qp_rows[key] or
                summary["bytes"] != qp_bytes[key] or summary["overflow"] != 0):
            raise RuntimeError("Selected QP events are incomplete or truncated: %r" % (key,))
    sw = switch_summary[0]
    if (sw["rows"] != len(probe_hops) or sw["bytes"] != probe_hop_bytes or
            sw["overflow"] != 0 or sw["rows"] > limits["switch_rows"] or
            sw["bytes"] > limits["switch_bytes"] or
            sum(qp_rows.values()) > limits["qp_rows"] or
            sum(qp_bytes.values()) > limits["qp_bytes"] or
            sw["rows"] + sum(qp_rows.values()) > limits["total_rows"] or
            sw["bytes"] + sum(qp_bytes.values()) > limits["total_bytes"]):
        raise RuntimeError("Probe line or byte budget violated")
    return {"hop_qps": len(hop_qps), "probe_qps": len(qp_summary),
            "probe_hops": len(probe_hops), "probe_rows": sw["rows"] + sum(qp_rows.values()),
            "probe_bytes": sw["bytes"] + sum(qp_bytes.values())}


def check(cell, plan):
    folder = ROOT / "results" / cell["id"]
    if folder.is_symlink() or not folder.is_dir():
        raise RuntimeError("Fetched cell missing: " + cell["id"])
    meta = json.loads(unique_file(folder, "metadata.json").read_text(encoding="utf-8"))
    params = meta.get("parameters", {})
    if not (meta.get("experiment_id") == cell["id"] and meta.get("status") == "SUCCEEDED" and
            meta.get("git_commit") == plan["source_sha"] and
            meta.get("algorithm") == cell["mode"] and meta.get("seed") == 1 and
            meta.get("concurrency_cap") == 1 and
            meta.get("input_flow_sha256") == cell["trace_sha256"] and
            meta.get("topology_sha256") == plan["topology_sha256"] and
            params.get("lb") == cell["mode"] and params.get("flow_file") == cell["trace"] and
            params.get("topo") == plan["topology"] and params.get("bw") == 400 and
            params.get("buffer") == 9 and params.get("pfc") == 1 and
            params.get("irn") == 1 and params.get("ws25_diag") == 1 and
            params.get("ws26_moe_hop_diag") == 1 and
            params.get("ws26_seed97_time_diag") == cell["ws26_seed97_time_diag"] and
            params.get("netload") == 10 and params.get("simul_time") == "0.01" and
            params.get("factorial_pilot") is True):
        raise RuntimeError("Metadata or run parameters differ from plan: " + cell["id"])
    config = folder / "config"
    trace = unique_file(config, "traffic_trace.txt")
    topology = unique_file(config, "topology.txt")
    if digest(trace) != cell["trace_sha256"] or digest(topology) != plan["topology_sha256"]:
        raise RuntimeError("Fetched inputs differ from the plan")
    values = {parts[0]: parts[1] for line in unique_file(config, "config.txt").read_text(
        encoding="utf-8").splitlines() if len(parts := line.split()) > 1}
    if (values.get("LB_MODE") != str(MODE_NUMBERS[cell["mode"]]) or
            values.get("ENABLE_PFC") != "1" or values.get("ENABLE_IRN") != "1" or
            values.get("BUFFER_SIZE") != "9" or
            values.get("TOPOLOGY_FILE") != "config/" + plan["topology"] + ".txt" or
            values.get("FLOW_FILE") != "config/" + cell["trace"]):
        raise RuntimeError("Config snapshot differs from plan")
    summary = analyze_moe_tags.summarize(cell["id"])
    tags = summary["tags"]
    if (tags.get("1", {}).get("input_flows") != cell["expected_background_qps"] or
            tags.get("2", {}).get("input_flows") != cell["expected_moe_qps"] or
            any(row["completed_flows"] != row["input_flows"] or row["unfinished_flows"]
                for row in tags.values()) or
            sum(row["completed_flows"] for row in tags.values()) != cell["expected_flows"]):
        raise RuntimeError("One or more input flows did not complete")
    expected = trace_qps(trace)
    if len(expected) != cell["expected_flows"]:
        raise RuntimeError("Input trace count differs from plan")
    fct = raw_fct(folder, meta)
    fct_sha = fct_identity(fct, expected)
    if cell["stage"] == "smoke_probe":
        old = plan["cells"][0]
        old_folder = ROOT / "results" / old["id"]
        old_meta = json.loads(unique_file(old_folder, "metadata.json").read_text(encoding="utf-8"))
        if fct_sha != digest(raw_fct(old_folder, old_meta)):
            raise RuntimeError("Probe smoke FCT differs from plain smoke")
    elif cell["stage"] == "paired_high":
        old_folder = ROOT / "results" / cell["paired_plain_id"]
        old_meta = json.loads(unique_file(old_folder, "metadata.json").read_text(encoding="utf-8"))
        if (fct_sha != cell["paired_plain_fct_sha256"] or
                digest(raw_fct(old_folder, old_meta)) != fct_sha):
            raise RuntimeError("High diagnostic FCT differs from frozen plain cell")
    selected = set(HEADER_QUAD.findall(HEADER.read_text(encoding="utf-8")))
    selected = {tuple(map(int, key)) for key in selected} & set(expected)
    if len(selected) != (2 if cell["stage"].startswith("smoke_") else 23):
        raise RuntimeError("Selected QP coverage differs from preregistration")
    logs = check_logs(unique_file(folder / "logs", "config.log"), expected, selected,
                      topology, cell["ws26_seed97_time_diag"], plan["log_limits"])
    resources = check_resources(folder, cell, plan)
    return {"id": cell["id"], "order": cell["order"], "source_sha": plan["source_sha"],
            "trace_sha256": cell["trace_sha256"], "fct_sha256": fct_sha,
            "completed_flows": len(expected), **logs, "resource": resources,
            "config_log_sha256": digest(unique_file(folder / "logs", "config.log"))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-sha", required=True)
    parser.add_argument("--id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{64}", args.plan_sha):
        parser.error("--plan-sha needs a SHA-256 digest")
    plan = load_plan(args.plan_sha)
    cell = next((row for row in plan["cells"] if row["id"] == args.id), None)
    if cell is None:
        raise RuntimeError("ID absent from frozen plan")
    print(json.dumps(check(cell, plan), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
