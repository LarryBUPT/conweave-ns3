#!/usr/bin/env python3
"""Verify and pair the frozen WS-26 v3 per-QP/per-hop tail diagnostics."""

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs/research/evidence/ws26-v3-tail-diagnostic-plan.json"
PLAN = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
COUNTERS = ("rx_ooo_packets", "sack_feedback", "cnp_feedback",
            "repeated_sends", "timeout_recovery")


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fields(line):
    return {key: int(value) for key, value in re.findall(r"(\w+)=(-?\d+)", line)}


def topology_host_to_tor():
    path = ROOT / "config" / (PLAN["topology"] + ".txt")
    lines = path.read_text(encoding="ascii").splitlines()
    node_count, switch_count = map(int, lines[0].split()[:2])
    host_count = node_count - switch_count
    result = {}
    for line in lines[2:]:
        parts = line.split()
        if len(parts) < 5 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        left, right = int(parts[0]), int(parts[1])
        if left < host_count <= right:
            result[left] = right
        elif right < host_count <= left:
            result[right] = left
    if set(result) != set(range(host_count)):
        raise RuntimeError("Could not map every host to its directly connected switch")
    return result


def check_plan():
    cells = PLAN["cells"]
    if (PLAN["source_sha"] != "593038416fa16f4982b600d256b563260f9106a8"
            or len(cells) != 8 or [row["run_order"] for row in cells] != list(range(1, 9))
            or len({row["id"] for row in cells}) != 8 or PLAN["parameters"]["cap"] != 1):
        raise RuntimeError("Frozen diagnostic plan identity or shape changed")
    topo = ROOT / "config/topo_1280_400G_400G_OS1.txt"
    if sha(topo) != PLAN["topology_sha256"]:
        raise RuntimeError("Frozen diagnostic topology changed")
    topology_host_to_tor()
    pilot = json.loads((ROOT / "docs/research/evidence/ws26-v3-pilot-plan.json").read_text(
        encoding="utf-8"))
    pilot_cells = pilot["cells"]
    high_verified = json.loads((ROOT / "results/ws26-v3-independent-pilot-r2/high-verified.json").read_text(
        encoding="utf-8"))
    for row in cells:
        key = (row["seed"], row["background"], row["mode"], 0)
        original = next((cell for cell in pilot_cells if
                         (cell["seed"], cell["background"], cell["mode"], cell["ws25_diag"]) == key), None)
        verified = next((cell for cell in high_verified["cells"] if
                         (cell["seed"], cell["background"], cell["mode"], cell["ws25_diag"]) == key), None)
        if (row["background"] != 192 or row["ws25_diag"] != 1 or
                row["ws26_time_probe"] != 0 or row["mode"] not in ("fecmp", "classreserve3") or
                row["expected_flows"] != 16576 or original is None or
                verified is None or row["expected_fct_sha256"] != verified["fct_sha256"] or
                row["trace"] != original["trace"] or row["trace_sha256"] != original["trace_sha256"] or
                sha(ROOT / "config" / row["trace"]) != row["trace_sha256"]):
            raise RuntimeError("Diagnostic cell diverged from the frozen pilot: " + row["id"])
    return cells


def load_cell(cell):
    folder = ROOT / "results" / cell["id"]
    if folder.is_symlink() or not folder.is_dir():
        raise RuntimeError("Missing or linked result directory: " + cell["id"])
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = meta["parameters"]
    identity = (meta.get("status") == "SUCCEEDED" and
                meta.get("git_commit") == PLAN["source_sha"] and
                meta.get("algorithm") == cell["mode"] and
                meta.get("input_flow_sha256") == cell["trace_sha256"] and
                meta.get("topology_sha256") == PLAN["topology_sha256"] and
                params.get("lb") == cell["mode"] and params.get("flow_file") == cell["trace"] and
                params.get("topo") == PLAN["topology"] and params.get("bw") == 400 and
                params.get("buffer") == 9 and params.get("pfc") == 1 and
                params.get("irn") == 1 and params.get("ws25_diag") == 1 and
                params.get("ws26_time_probe") == 0 and params.get("netload") == 10 and
                params.get("simul_time") == "0.01")
    if not identity:
        raise RuntimeError("Diagnostic metadata mismatch: " + cell["id"])
    if sha(folder / "config/traffic_trace.txt") != cell["trace_sha256"] or \
            sha(folder / "config/topology.txt") != PLAN["topology_sha256"]:
        raise RuntimeError("Diagnostic input snapshot mismatch: " + cell["id"])
    raw_id = str(meta.get("raw_directory", ""))
    if not raw_id.isdigit():
        raise RuntimeError("Invalid raw directory ID: " + cell["id"])
    raw = folder / "raw" / raw_id
    fcts = list(raw.glob("*_out_fct.txt"))
    if raw.is_symlink() or not raw.is_dir() or len(fcts) != 1 or not fcts[0].is_file():
        raise RuntimeError("Missing or ambiguous diagnostic raw: " + cell["id"])
    fct_sha = sha(fcts[0])
    if fct_sha != cell["expected_fct_sha256"]:
        raise RuntimeError("Diagnostic perturbed FCT: " + cell["id"])
    log_path = folder / "logs/config.log"
    if not log_path.is_file() or log_path.is_symlink():
        raise RuntimeError("Fetched diagnostic config.log missing: " + cell["id"])
    log = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    fct_by_tuple = {}
    fct_rows = 0
    with fcts[0].open(encoding="ascii") as stream:
        for line in stream:
            values = [int(value) for value in line.split()]
            if len(values) != 8:
                raise RuntimeError("Malformed FCT row: " + cell["id"])
            key = tuple(values[:4])
            if key in fct_by_tuple:
                raise RuntimeError("Duplicate FCT flow tuple: " + cell["id"])
            fct_by_tuple[key] = values[6] / 1000.0
            fct_rows += 1
    if fct_rows != 16576:
        raise RuntimeError("FCT completion count mismatch: " + cell["id"])
    qp_rows = [fields(line) for line in log if line.startswith("WS25_QP ")]
    if (len(qp_rows) != 16576 or
            {row.get("flow_id") for row in qp_rows} != set(range(16576))):
        raise RuntimeError("Per-QP diagnostic rows missing or duplicated: " + cell["id"])
    if any(any(row.get(key, -1) < 0 for key in COUNTERS) for row in qp_rows):
        raise RuntimeError("Invalid per-QP counters: " + cell["id"])
    background_qps = {row["flow_id"]: row for row in qp_rows if row.get("tag") == 1}
    if len(background_qps) != 192 or sum(row.get("tag") == 2 for row in qp_rows) != 16384:
        raise RuntimeError("Expected 192 background QP rows: " + cell["id"])
    hops = collections.defaultdict(list)
    for line in log:
        if line.startswith("WS13_HOP "):
            row = fields(line)
            if any(row.get(key, -1) < 0 for key in
                   ("switch", "port", "packets", "bytes", "queued_bytes_max", "wait_ns_max")):
                raise RuntimeError("Invalid per-hop counters: " + cell["id"])
            key = tuple(row.get(k) for k in ("src", "dst", "sport", "dport"))
            hops[key].append(row)
    choice_rows = [fields(line) for line in log
                   if line.startswith("WS26_CLASSRESERVE3_QP ")]
    chosen_paths = {}
    candidate_moe_by_tor_port = collections.defaultdict(lambda: {"qp_count": 0, "packets": 0})
    if cell["mode"] == "classreserve3":
        route_summary_rows = [fields(line) for line in log
                              if line.startswith("WS26_CLASSRESERVE3 ")]
        if len(route_summary_rows) != 1:
            raise RuntimeError("ClassReserve summary missing or duplicated: " + cell["id"])
        route_summary = route_summary_rows[0]
        if (len(choice_rows) != route_summary["background_new"] + route_summary["moe_new"] or
                sum(row.get("tag") == 1 for row in choice_rows) != route_summary["background_new"] or
                sum(row.get("tag") == 2 for row in choice_rows) != route_summary["moe_new"]):
            raise RuntimeError("ClassReserve path-choice rows are incomplete: " + cell["id"])
        for row in choice_rows:
            key = (((row["sip"] >> 8) & 0xffff), ((row["dip"] >> 8) & 0xffff),
                   row["sport"], row["dport"])
            if key in chosen_paths or row.get("inconsistent") != 0:
                raise RuntimeError("Duplicate or unstable ClassReserve path choice: " + cell["id"])
            chosen_paths[key] = {"source_tor": row["switch"], "port": row["port"],
                                 "packets": row["packets"], "tag": row["tag"]}
    inflight = [fields(line) for line in log if line.startswith("WS13_INFLIGHT ")]
    if len(inflight) != 1 or inflight[0].get("unpaired") != 0:
        raise RuntimeError("Flow-hop diagnostic did not close: " + cell["id"])

    trace_lines = (folder / "config/traffic_trace.txt").read_text(encoding="ascii").splitlines()
    if len(trace_lines) != 16577:
        raise RuntimeError("Trace row count mismatch: " + cell["id"])
    source_ports = collections.defaultdict(lambda: 10000)
    destination_ports = collections.defaultdict(lambda: 100)
    input_ids = {}
    for index, line in enumerate(trace_lines[1:]):
        src, dst = map(int, line.split()[:2])
        key = (src, dst, source_ports[src], destination_ports[dst])
        input_ids[key] = index
        source_ports[src] += 1
        destination_ports[dst] += 1
    host_to_tor = topology_host_to_tor()
    for key, choice in chosen_paths.items():
        if key not in input_ids or choice["source_tor"] != host_to_tor[key[0]]:
            raise RuntimeError("ClassReserve source-ToR choice identity mismatch: " + cell["id"])
        if choice["tag"] == 2:
            target = candidate_moe_by_tor_port[(choice["source_tor"], choice["port"])]
            target["qp_count"] += 1
            target["packets"] += choice["packets"]
    detail = []
    for flow_key, flow_id in input_ids.items():
        if flow_id not in background_qps:
            continue
        if flow_key not in hops:
            raise RuntimeError("Background QP missing hop rows: " + cell["id"])
        selected = hops[flow_key]
        record = {"flow_id": flow_id, "src": flow_key[0], "dst": flow_key[1],
                       "sport": flow_key[2], "dport": flow_key[3],
                       "fct_us": fct_by_tuple.get(flow_key),
                       "counters": {key: background_qps[flow_id][key] for key in COUNTERS},
                       "hops": [{"switch": row["switch"], "port": row["port"],
                                 "packets": row["packets"],
                                 "queued_bytes_max": row["queued_bytes_max"],
                                 "wait_ns_max": row["wait_ns_max"],
                                 "queued_bytes_sum": row["queued_bytes_sum"],
                                 "wait_ns_sum": row["wait_ns_sum"]}
                                for row in selected]}
        if record["fct_us"] is None:
            raise RuntimeError("Background FCT tuple missing: " + cell["id"])
        source_tor = host_to_tor[flow_key[0]]
        source_hops = [row for row in selected if row["switch"] == source_tor]
        if len(source_hops) != 1:
            raise RuntimeError("Background source-ToR hop missing or duplicated: " + cell["id"])
        record["source_tor_path"] = {"switch": source_tor,
            "selected_port": source_hops[0]["port"],
            "queued_bytes_max": source_hops[0]["queued_bytes_max"],
            "wait_ns_max": source_hops[0]["wait_ns_max"],
            "queued_bytes_sum": source_hops[0]["queued_bytes_sum"],
            "wait_ns_sum": source_hops[0]["wait_ns_sum"]}
        record["classreserve3_moe_choices_at_source_tor"] = [
            {"port": port, **counts} for (switch, port), counts in
            sorted(candidate_moe_by_tor_port.items()) if switch == source_tor]
        if cell["mode"] == "classreserve3":
            choice = chosen_paths.get(flow_key)
            if choice is not None and (choice["tag"] != 1 or
                                       source_hops[0]["port"] != choice["port"]):
                raise RuntimeError("ClassReserve choice disagrees with source-ToR hop: " + cell["id"])
        detail.append(record)
    if len(detail) != 192:
        raise RuntimeError("Could not map all 192 background QPs to diagnostics: " + cell["id"])
    resource = json.loads((folder / "logs/resource-summary.json").read_text(encoding="utf-8"))
    samples = [json.loads(line) for line in
               (folder / "logs/resource-samples.jsonl").read_text(encoding="utf-8").splitlines()
               if line]
    if not (resource.get("final_status") == "SUCCEEDED" and
            resource.get("samples") == len(samples) > 0 and
            resource.get("peak_tree_rss_mib", 10**12) <= 32768 and
            resource.get("minimum_mem_available_gib", 0) >= 32 and
            resource.get("minimum_free_gib", 0) >= 100 and
            max(row["load_1m"] for row in samples) <= 20):
        raise RuntimeError("Resource receipt failed: " + cell["id"])
    return {"id": cell["id"], "seed": cell["seed"], "mode": cell["mode"],
            "fct_sha256": fct_sha, "resource": resource,
            "background_qps": detail}


def summarize_cell(cell):
    flows = cell["background_qps"]
    hop_rows = [{"flow_id": flow["flow_id"], "src": flow["src"], "dst": flow["dst"],
                 "sport": flow["sport"], "dport": flow["dport"], **hop}
                for flow in flows for hop in flow["hops"]]
    counters = {key: {"total": sum(flow["counters"][key] for flow in flows),
                      "flows_nonzero": sum(flow["counters"][key] > 0 for flow in flows)}
                for key in COUNTERS}
    ports = sorted({(row["switch"], row["port"]) for row in hop_rows})
    return {"id": cell["id"], "seed": cell["seed"], "mode": cell["mode"],
            "fct_sha256": cell["fct_sha256"], "flow_count": len(flows),
            "counters": counters, "hop_row_count": len(hop_rows),
            "switch_port_count": len(ports),
            "top_queue_hops": sorted(hop_rows,
                key=lambda row: (row["queued_bytes_max"], row["wait_ns_max"]),
                reverse=True)[:10],
            "top_wait_hops": sorted(hop_rows,
                key=lambda row: (row["wait_ns_max"], row["queued_bytes_max"]),
                reverse=True)[:10]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT /
                        "docs/research/evidence/ws26-v3-tail-diagnostic-analysis.json")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    cells = check_plan()
    rows = [load_cell(cell) for cell in cells]
    by_pair = {(row["seed"], row["mode"]): row for row in rows}
    pairs = []
    for seed in range(20262690, 20262694):
        ecmp, candidate = by_pair[(seed, "fecmp")], by_pair[(seed, "classreserve3")]
        if ecmp["background_qps"] and candidate["background_qps"]:
            paired = []
            for a, b in zip(ecmp["background_qps"], candidate["background_qps"]):
                if (a["src"], a["dst"], a["sport"], a["dport"]) != \
                        (b["src"], b["dst"], b["sport"], b["dport"]):
                    raise RuntimeError("Paired background QP identity mismatch")
                if a["source_tor_path"]["selected_port"] != b["source_tor_path"]["selected_port"]:
                    raise RuntimeError("Background ECMP source-ToR path changed: " + ecmp["id"])
                paired.append({"flow_id": a["flow_id"], "src": a["src"], "dst": a["dst"],
                               "sport": a["sport"], "dport": a["dport"],
                               "ecmp_fct_us": a["fct_us"],
                               "classreserve3_fct_us": b["fct_us"],
                               "fct_change_us": b["fct_us"] - a["fct_us"],
                               "ecmp_counters": a["counters"],
                               "classreserve3_counters": b["counters"],
                               "ecmp_hops": a["hops"], "classreserve3_hops": b["hops"],
                               "controlled_source_tor": {
                                   "switch": b["source_tor_path"]["switch"],
                                   "ecmp_port": a["source_tor_path"]["selected_port"],
                                   "classreserve3_port": b["source_tor_path"]["selected_port"],
                                   "ecmp_queue_hop": a["source_tor_path"],
                                   "classreserve3_queue_hop": b["source_tor_path"]},
                               "classreserve3_moe_choices_at_source_tor":
                                   b["classreserve3_moe_choices_at_source_tor"]})
            pairs.append({"seed": seed, "ecmp_id": ecmp["id"],
                          "classreserve3_id": candidate["id"],
                          "trace_sha256": next(c["trace_sha256"] for c in cells
                              if c["seed"] == seed and c["mode"] == "fecmp"),
                          "flows": paired})
    if len(pairs) != 4 or any(len(pair["flows"]) != 192 for pair in pairs):
        raise RuntimeError("Expected four complete 192-QP paired diagnostics")
    if args.verify_only:
        print(json.dumps({"verified_cells": len(rows), "paired_seeds": len(pairs),
                          "background_qps_per_pair": 192}, sort_keys=True))
        return
    output = {"purpose": PLAN["purpose"], "evidence_level": PLAN["evidence_level"],
              "source_sha": PLAN["source_sha"], "cells": rows, "pairs": pairs,
              "interpretation_limit": "NS-3 diagnostics only; no new efficacy sample"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_path = args.output.with_name("ws26-v3-tail-diagnostic-summary.json")
    summary_pairs = []
    for pair_index, pair in enumerate(pairs):
        ecmp = by_pair[(pair["seed"], "fecmp")]
        candidate = by_pair[(pair["seed"], "classreserve3")]
        flow_index = []
        for index, flow in enumerate(pair["flows"]):
            flow_index.append({"flow_id": flow["flow_id"],
                               "tuple": [flow["src"], flow["dst"], flow["sport"], flow["dport"]],
                               "full_evidence_pointer": "pairs[%d].flows[%d]" % (pair_index, index),
                               "fct_change_us": flow["fct_change_us"],
                               "ecmp_switch_ports": [[hop["switch"], hop["port"]]
                                                     for hop in flow["ecmp_hops"]],
                               "classreserve3_switch_ports": [[hop["switch"], hop["port"]]
                                                               for hop in flow["classreserve3_hops"]],
                               "controlled_source_tor": flow["controlled_source_tor"],
                               "classreserve3_moe_choices_at_source_tor":
                                   flow["classreserve3_moe_choices_at_source_tor"],
                               "ecmp_counters": flow["ecmp_counters"],
                               "classreserve3_counters": flow["classreserve3_counters"]})
        summary_pairs.append({"seed": pair["seed"], "trace_sha256": pair["trace_sha256"],
                              "ecmp": summarize_cell(ecmp),
                              "classreserve3": summarize_cell(candidate),
                              "per_flow_path_evidence_index": flow_index})
    summary = {"purpose": PLAN["purpose"], "evidence_level": PLAN["evidence_level"],
               "source_sha": PLAN["source_sha"], "full_analysis_file": args.output.name,
               "verified_cells": len(rows), "paired_seeds": len(summary_pairs),
               "background_qps_per_pair": 192, "pairs": summary_pairs,
               "interpretation_limit": "NS-3 diagnostics only; no new efficacy sample"}
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verified_cells": len(rows), "analysis": str(args.output),
                      "summary": str(summary_path)}, sort_keys=True))


if __name__ == "__main__":
    main()
