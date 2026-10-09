#!/usr/bin/env python3
"""Verify frozen WS-26 MoE and background hop diagnostic cells."""

import argparse
import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path

import analyze_moe_tags

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = "docs/research/evidence/ws26-moe-hop-diagnostic-plan.json"
PLAN_SHA256 = "ea17bce8eda8441d16139acafd9849bc3c3de615be6b9b797f4e46f65db7f5ea"
SOURCE_SHA = "3bdb6c520a079a79f915300c7540fe1828f4445a"
TOPOLOGY_SHA256 = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
MODE_NUMBERS = {"fecmp": 0, "classlane4": 24}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan_bytes():
    return subprocess.check_output(["git", "show", "HEAD:" + PLAN_PATH], cwd=ROOT)


def load_plan():
    data = plan_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != PLAN_SHA256:
        raise RuntimeError("Committed frozen plan SHA mismatch: " + actual)
    plan = json.loads(data.decode("utf-8"))
    if (plan.get("source_sha") != SOURCE_SHA or len(plan.get("cells", [])) != 10 or
            [cell["order"] for cell in plan["cells"]] != list(range(1, 11))):
        raise RuntimeError("Frozen plan layout or source SHA changed")
    if digest(ROOT / "config" / (plan["topology"] + ".txt")) != TOPOLOGY_SHA256:
        raise RuntimeError("Frozen topology hash changed")
    for cell in plan["cells"]:
        if digest(ROOT / "config" / cell["trace"]) != cell["trace_sha256"]:
            raise RuntimeError("Frozen trace hash changed: " + cell["trace"])
    return plan


def unique_file(folder, pattern):
    matches = list(folder.glob(pattern))
    if len(matches) != 1 or matches[0].is_symlink() or not matches[0].is_file():
        raise RuntimeError("Missing or ambiguous file: " + str(folder / pattern))
    return matches[0]


def fields(line):
    return {key: int(value) for key, value in re.findall(r"(\w+)=(-?\d+)", line)}


def trace_qps(path):
    source_ports = collections.defaultdict(lambda: 10000)
    destination_ports = collections.defaultdict(lambda: 100)
    expected = {}
    with path.open(encoding="ascii") as stream:
        declared = int(stream.readline().strip())
        for line_number, line in enumerate(stream, 2):
            values = line.split()
            if len(values) != 6:
                raise RuntimeError("Expected six-column tagged trace at line %d" % line_number)
            src, dst, unused_pg, size = map(int, values[:4])
            start_ns = round(float(values[4]) * 1e9)
            tag = int(values[5])
            key = (src, dst, source_ports[src], destination_ports[dst])
            source_ports[src] += 1
            destination_ports[dst] += 1
            if key in expected:
                raise RuntimeError("Duplicate QP identity in trace")
            expected[key] = {"tag": tag, "size": size, "start_ns": start_ns}
    if declared != len(expected):
        raise RuntimeError("Trace declared count mismatch")
    return expected


def topology_maps(path):
    lines = path.read_text(encoding="ascii").splitlines()
    node_count, switches, links = map(int, lines[0].split()[:3])
    hosts = node_count - switches
    host_tors = {}
    port_to_neighbor = collections.defaultdict(dict)
    for line in lines[2:]:
        values = line.split()
        if len(values) < 2:
            continue
        left, right = map(int, values[:2])
        if left < hosts <= right:
            host_tors[left] = right
        elif right < hosts <= left:
            host_tors[right] = left
        port_to_neighbor[left][len(port_to_neighbor[left])] = right
        port_to_neighbor[right][len(port_to_neighbor[right])] = left
    if len(host_tors) != hosts or sum(map(len, port_to_neighbor.values())) != links * 2:
        raise RuntimeError("Topology edge or host mapping parse mismatch")
    return hosts, switches, host_tors, port_to_neighbor


def path_for(rows, src, dst, hosts, host_tors, port_to_neighbor):
    if len({row["switch"] for row in rows}) != len(rows):
        raise RuntimeError("QP has more than one observed port on a switch")
    by_switch = {row["switch"]: row for row in rows}
    current = host_tors[src]
    destination_tor = host_tors[dst]
    ordered = []
    visited = set()
    while current >= hosts:
        if current in visited or current not in by_switch:
            raise RuntimeError("QP hop path is discontinuous")
        visited.add(current)
        row = by_switch[current]
        neighbor = port_to_neighbor.get(current, {}).get(row["outDev"])
        if neighbor is None:
            raise RuntimeError("QP outDev is absent from topology")
        ordered.append(row)
        current = neighbor
    if current != dst or not ordered or ordered[-1]["switch"] != destination_tor:
        raise RuntimeError("QP path does not reach its destination host via destination ToR")
    if visited != set(by_switch):
        raise RuntimeError("QP has unconnected extra hop records")
    return ordered


def raw_fct(folder, metadata):
    raw = folder / "raw" / str(metadata.get("raw_directory", ""))
    if raw.is_symlink() or not raw.is_dir():
        raise RuntimeError("Raw result directory missing or linked")
    return unique_file(raw, "*_out_fct.txt")


def paired_fct_hash(cell):
    receipt_file = ROOT / "results" / "ws26-moe-hop-diagnostic" / "receipts.jsonl"
    if not receipt_file.is_file() or receipt_file.is_symlink():
        raise RuntimeError("Paired FCT audit receipt is missing")
    matches = []
    for line in receipt_file.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("event") == "paired_plain_fct_audit" and row.get("id") == cell["id"]:
            matches.append(row)
    if len(matches) != 1:
        raise RuntimeError("Expected one frozen paired FCT audit receipt")
    return matches[0]["fct_sha256"]


def check(cell, plan):
    folder = ROOT / "results" / cell["id"]
    if folder.is_symlink() or not folder.is_dir():
        raise RuntimeError("Result directory missing or linked: " + cell["id"])
    meta = json.loads(unique_file(folder, "metadata.json").read_text(encoding="utf-8"))
    params = meta.get("parameters", {})
    if not (meta.get("experiment_id") == cell["id"] and
            meta.get("status") == "SUCCEEDED" and meta.get("git_commit") == SOURCE_SHA and
            meta.get("algorithm") == cell["mode"] and meta.get("seed") == 1 and
            meta.get("concurrency_cap") == 1 and
            meta.get("input_flow_sha256") == cell["trace_sha256"] and
            meta.get("topology_sha256") == TOPOLOGY_SHA256 and
            params.get("lb") == cell["mode"] and params.get("flow_file") == cell["trace"] and
            params.get("topo") == plan["topology"] and params.get("bw") == 400 and
            params.get("buffer") == 9 and params.get("pfc") == 1 and params.get("irn") == 1 and
            params.get("ws25_diag") == 1 and params.get("ws26_moe_hop_diag") == 1 and
            params.get("netload") == 10 and params.get("simul_time") == "0.01" and
            params.get("factorial_pilot") is True):
        raise RuntimeError("Metadata identity or parameter mismatch: " + cell["id"])

    trace = unique_file(folder / "config", "traffic_trace.txt")
    topology = unique_file(folder / "config", "topology.txt")
    config = unique_file(folder / "config", "config.txt")
    if digest(trace) != cell["trace_sha256"] or digest(topology) != TOPOLOGY_SHA256:
        raise RuntimeError("Fetched input snapshot mismatch: " + cell["id"])
    values = {parts[0]: parts[1] for line in config.read_text(encoding="utf-8").splitlines()
              if len(parts := line.split()) > 1}
    if (values.get("LB_MODE") != str(MODE_NUMBERS[cell["mode"]]) or
            values.get("ENABLE_PFC") != "1" or values.get("ENABLE_IRN") != "1" or
            values.get("BUFFER_SIZE") != "9" or
            values.get("TOPOLOGY_FILE") != "config/" + plan["topology"] + ".txt" or
            values.get("FLOW_FILE") != "config/" + cell["trace"]):
        raise RuntimeError("Simulation config mismatch: " + cell["id"])

    summary = analyze_moe_tags.summarize(cell["id"])
    tags = {"1": cell["expected_background_qps"], "2": cell["expected_moe_qps"]}
    if ({tag: row["input_flows"] for tag, row in summary["tags"].items()} !=
            {tag: count for tag, count in tags.items() if count} or
            any(row["completed_flows"] != row["input_flows"] or row["unfinished_flows"]
                for row in summary["tags"].values()) or
            sum(row["completed_flows"] for row in summary["tags"].values()) != cell["expected_flows"]):
        raise RuntimeError("Input flows did not complete exactly once: " + cell["id"])

    expected = trace_qps(trace)
    actual_fct = raw_fct(folder, meta)
    fct_data = {}
    with actual_fct.open(encoding="ascii") as stream:
        for line in stream:
            values = list(map(int, line.split()))
            if len(values) != 8:
                raise RuntimeError("Malformed FCT row")
            key = tuple(values[:4])
            if key in fct_data or key not in expected:
                raise RuntimeError("Duplicate or unexpected FCT identity")
            wanted = expected[key]
            if values[4] != wanted["size"] or abs(values[5] - wanted["start_ns"]) > 2:
                raise RuntimeError("FCT size/start differs from input")
            fct_data[key] = {"tag": wanted["tag"], "fct_ns": values[6], "size": values[4]}
    if set(fct_data) != set(expected):
        raise RuntimeError("FCT identity set differs from input")
    fct_sha = digest(actual_fct)
    paired = ROOT / "results" / cell["paired_plain_id"]
    paired_meta = json.loads(unique_file(paired, "metadata.json").read_text(encoding="utf-8"))
    paired_fct = raw_fct(paired, paired_meta)
    paired_sha = digest(paired_fct)
    frozen_paired_sha = paired_fct_hash(cell)
    if paired_sha != frozen_paired_sha or fct_sha != frozen_paired_sha:
        raise RuntimeError("Diagnostic FCT differs from paired plain cell: " + cell["id"])

    logs = folder / "logs"
    log = unique_file(logs, "config.log")
    hop_rows = collections.defaultdict(list)
    inflight = None
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("WS26_MOE_HOP "):
            row = fields(line)
            row["tag"] = 2
        elif line.startswith("WS13_HOP "):
            row = fields(line)
            row["tag"] = 1
        elif line.startswith("WS13_INFLIGHT "):
            inflight = fields(line).get("unpaired")
            continue
        else:
            continue
        key = (row["src"], row["dst"], row["sport"], row["dport"])
        hop_rows[key].append(row)
    if inflight != 0 or len(hop_rows) != cell["expected_flows"]:
        raise RuntimeError("Hop coverage or WS13_INFLIGHT invariant failed: " + cell["id"])
    topology_index = topology_maps(topology)
    for key, flow in fct_data.items():
        qpk = key[:4]
        rows = hop_rows.get(qpk, [])
        if not rows or any(row["tag"] != flow["tag"] for row in rows):
            raise RuntimeError("QP lacks matching-tag hop rows: " + repr(qpk))
        ordered = path_for(rows, key[0], key[1], topology_index[0],
                           topology_index[2], topology_index[3])
        if any(row["packets"] <= 0 or row["bytes"] <= 0 for row in ordered):
            raise RuntimeError("Invalid hop packet or byte counters")

    samples_path = unique_file(logs, "resource-samples.jsonl")
    resource_path = unique_file(logs, "resource-summary.json")
    samples = [json.loads(line) for line in samples_path.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    resource = json.loads(resource_path.read_text(encoding="utf-8"))
    receipt_file = ROOT / "results" / "ws26-moe-hop-diagnostic" / "receipts.jsonl"
    first_sample_remote = False
    if receipt_file.is_file() and not receipt_file.is_symlink():
        for line in receipt_file.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row.get("event") == "watcher_first_sample" and row.get("id") == cell["id"]:
                first_sample_remote = bool(row.get("sample"))
    if not (samples and resource.get("id") == cell["id"] and
            resource.get("final_status") == "SUCCEEDED" and
            resource.get("samples") == len(samples) and
            resource.get("peak_tree_rss_mib", 10**12) <= 32768 and
            resource.get("minimum_mem_available_gib", 0) >= 32 and
            resource.get("minimum_free_gib", 0) >= 100 and
            max(row.get("load_1m", 10**12) for row in samples) <= 20 and
            first_sample_remote):
        raise RuntimeError("Resource terminal receipt invalid: " + cell["id"])
    return {"id": cell["id"], "stage": cell["stage"], "order": cell["order"],
            "seed": cell["seed"], "mode": cell["mode"], "trace_sha256": cell["trace_sha256"],
            "fct_sha256": fct_sha, "paired_plain_id": cell["paired_plain_id"],
            "paired_plain_fct_sha256": paired_sha, "flow_count": len(fct_data),
            "tag_counts": {tag: count for tag, count in tags.items() if count},
            "hop_qp_count": len(hop_rows), "inflight_unpaired": inflight,
            "resource": resource, "resource_sample_count": len(samples),
            "config_log_sha256": digest(log), "fct_file_sha256": fct_sha,
            "moe_tag_summary": summary["tags"].get("2"),
            "background_tag_summary": summary["tags"].get("1")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True)
    args = parser.parse_args()
    plan = load_plan()
    cell = next((row for row in plan["cells"] if row["id"] == args.id), None)
    if cell is None:
        raise RuntimeError("ID is not in the committed frozen plan")
    print(json.dumps(check(cell, plan), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
