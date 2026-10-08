#!/usr/bin/env python3
"""Freeze and verify the 19-cell WS-26 ClassLane v4 correctness preflight."""

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

import analyze_moe_tags


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "41384701c865082655cdea9a9e64daae74f51327"
TOPOLOGY = "topo_1280_400G_400G_OS1"
TOPOLOGY_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
PLAN_PATH = ROOT / "docs/research/evidence/ws26-classlane4-preflight-plan-r1.json"
RECEIPTS_PATH = ROOT / "results/ws26-classlane4-preflight-r1-receipts.jsonl"
TRACES = {
    "mixed8": ("ws25_v1fix_mixed8.txt",
               "29ebe2dcf38c0e4d29326947c4bc4e111f6b56fe378c020c30ee788fbaa5effb",
               {"1": 4, "2": 4}),
    "background4": ("ws25_v1fix_background4.txt",
                    "e1259a4dbb17fe70e15a72881cbc3faaeac637123ba18ac29596b4f4f2743015",
                    {"1": 4}),
    "moe4": ("ws25_v1fix_moe4.txt",
             "8acfe14d19d7ef7822bfd9a78334b830ce581456003e132d6557a44d1e41ea60",
             {"2": 4}),
    "unclassified8": ("ws25_v1fix_unclassified8.txt",
                      "73704cadbdb95708c5ba26126af43b2758af688e332a80fdad46e7bc42c66dd3",
                      {"0": 8}),
    "legacy5": ("ws25_v1fix_legacy5.txt",
                "cc80f3a1eb23dcf936a8b371bf5b63763acac283923361efe9bcd3ebb1ae6c94",
                {"0": 8}),
    "shared_tor4": ("ws26_classlane4_shared_tor4.txt",
                    "513b85e3c2e2422df2bb8f3c9b3812408fd02f7ee4aaba2ee11fd6cfbf16db2a",
                    {"1": 2, "2": 2}),
}
ROWS = [
    ("231000", "mixed8-p1i1", "classlane4", "mixed8", 1, 1, 0),
    ("231001", "background4-p1i1", "classlane4", "background4", 1, 1, 0),
    ("231002", "moe4-p1i1", "classlane4", "moe4", 1, 1, 0),
    ("231003", "unclassified8-p1i1", "classlane4", "unclassified8", 1, 1, 0),
    ("231004", "legacy5-p1i1", "classlane4", "legacy5", 1, 1, 0),
    ("231005", "unclassified8-ecmp-p1i1", "fecmp", "unclassified8", 1, 1, 0),
    ("231006", "legacy5-ecmp-p1i1", "fecmp", "legacy5", 1, 1, 0),
    ("231007", "mixed8-ecmp-p1i1", "fecmp", "mixed8", 1, 1, 0),
    ("231008", "mixed8-p0i0", "classlane4", "mixed8", 0, 0, 0),
    ("231009", "mixed8-p0i1", "classlane4", "mixed8", 0, 1, 0),
    ("231010", "mixed8-p1i0", "classlane4", "mixed8", 1, 0, 0),
    ("231011", "fecmp-mixed8-p0i1", "fecmp", "mixed8", 0, 1, 0),
    ("231012", "drill-mixed8-p0i1", "drill", "mixed8", 0, 1, 0),
    ("231013", "conga-mixed8-p0i1", "conga", "mixed8", 0, 1, 0),
    ("231014", "letflow-mixed8-p0i1", "letflow", "mixed8", 0, 1, 0),
    ("231015", "conweave-mixed8-p0i1", "conweave", "mixed8", 0, 1, 0),
    ("231016", "shared-tor4-p1i1", "classlane4", "shared_tor4", 1, 1, 1),
    ("231017", "mixed8-diag-p1i1", "classlane4", "mixed8", 1, 1, 1),
    ("231018", "shared-tor4-ecmp-p1i1", "fecmp", "shared_tor4", 1, 1, 0),
]
CELLS = []
for clock, suffix, mode, trace_key, pfc, irn, diag in ROWS:
    filename, trace_sha, tag_counts = TRACES[trace_key]
    CELLS.append({
        "order": len(CELLS) + 1,
        "id": "20261008-" + clock + "-ws26-v4r1-pre-" + suffix,
        "mode": mode,
        "trace": filename,
        "trace_key": trace_key,
        "trace_sha256": trace_sha,
        "expected_tag_flows": tag_counts,
        "pfc": pfc,
        "irn": irn,
        "ws25_diag": diag,
    })


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def fields(line):
    return {key: int(value) for key, value in re.findall(r"(\w+)=(-?\d+)", line)}


def expected_plan():
    return {
        "source_sha": SOURCE_SHA,
        "topology": TOPOLOGY,
        "topology_sha256": TOPOLOGY_SHA,
        "bw_gbps": 400,
        "buffer_mib": 9,
        "cc": "dcqcn",
        "ns3_seed": 1,
        "simul_time": "0.01",
        "netload": 10,
        "cap": 1,
        "evidence_level": "correctness and path isolation only; no efficacy claim",
        "acceptance": [
            "Audit all 19 remote IDs before build; never overwrite an existing result.",
            "Run in listed order at cap=1; start and confirm the resource watcher before each run.",
            "Verify frozen source, trace, topology, parameters, full flow identity, and raw files.",
            "Verify QP path stability, per-tag packet counts, and queue byte conservation.",
            "Verify shared ToR category port sets are disjoint in cell 17.",
            "Verify diagnostic mode leaves the cell 1 FCT SHA unchanged.",
            "Verify tag-zero and legacy baseline FCT parity; stop on any failure.",
        ],
        "cells": CELLS,
    }


def write_plan():
    plan = expected_plan()
    rendered = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    if PLAN_PATH.exists():
        if PLAN_PATH.read_text(encoding="utf-8") != rendered:
            raise RuntimeError("Frozen ClassLane plan already exists and differs")
    else:
        PLAN_PATH.write_text(rendered, encoding="utf-8")
    print(json.dumps({"plan": str(PLAN_PATH), "cells": len(CELLS),
                      "source_sha": SOURCE_SHA}, sort_keys=True))


def validate_plan_and_inputs():
    if not PLAN_PATH.is_file() or PLAN_PATH.is_symlink():
        raise RuntimeError("Frozen ClassLane plan is missing or redirected")
    if json.loads(PLAN_PATH.read_text(encoding="utf-8")) != expected_plan():
        raise RuntimeError("Frozen ClassLane plan does not match verifier constants")
    if len(CELLS) != 19 or len({cell["id"] for cell in CELLS}) != 19:
        raise RuntimeError("Expected 19 unique correctness IDs")
    if digest(ROOT / "config" / (TOPOLOGY + ".txt")) != TOPOLOGY_SHA:
        raise RuntimeError("Frozen OS1 topology changed")
    for trace_name, trace_sha, _ in TRACES.values():
        if digest(ROOT / "config" / trace_name) != trace_sha:
            raise RuntimeError("Frozen trace changed: " + trace_name)


def result_file(folder, pattern):
    files = list(folder.glob(pattern))
    if len(files) != 1 or files[0].is_symlink() or not files[0].is_file():
        raise RuntimeError("Missing or ambiguous result file: " + str(folder / pattern))
    return files[0]


def prior_result(experiment_id):
    candidates = (ROOT / "results" / experiment_id,
                  ROOT.parent / "ws25-first-paper" / "results" / experiment_id)
    for folder in candidates:
        if folder.is_dir() and not folder.is_symlink():
            return folder
    raise RuntimeError("Prior baseline result missing: " + experiment_id)


def verify(cell):
    experiment_id = cell["id"]
    folder = ROOT / "results" / experiment_id
    if not folder.is_dir() or folder.is_symlink():
        raise RuntimeError("Local result directory missing or linked: " + experiment_id)
    metadata = json.loads(result_file(folder, "metadata.json").read_text(encoding="utf-8"))
    params = metadata["parameters"]
    if not (metadata.get("status") == "SUCCEEDED" and
            metadata.get("git_commit") == SOURCE_SHA and
            metadata.get("algorithm") == cell["mode"] and metadata.get("seed") == 1 and
            metadata.get("input_flow_sha256") == cell["trace_sha256"] and
            metadata.get("topology_sha256") == TOPOLOGY_SHA and
            params.get("lb") == cell["mode"] and params.get("flow_file") == cell["trace"] and
            params.get("topo") == TOPOLOGY and params.get("bw") == 400 and
            params.get("buffer") == 9 and params.get("pfc") == cell["pfc"] and
            params.get("irn") == cell["irn"] and
            params.get("ws25_diag") == cell["ws25_diag"] and
            params.get("ws26_time_probe") == 0 and params.get("netload") == 10 and
            params.get("simul_time") == "0.01"):
        raise RuntimeError("Metadata identity or parameters mismatch: " + experiment_id)
    if (digest(folder / "config" / "topology.txt") != TOPOLOGY_SHA or
            digest(folder / "config" / "traffic_trace.txt") != cell["trace_sha256"]):
        raise RuntimeError("Fetched input snapshot mismatch: " + experiment_id)
    summary = analyze_moe_tags.summarize(experiment_id)
    tags = summary["tags"]
    expected_tags = cell["expected_tag_flows"]
    if ({tag: item["input_flows"] for tag, item in tags.items()} != expected_tags or
            any(item["input_flows"] != item["completed_flows"] for item in tags.values())):
        raise RuntimeError("Flow identity, tag, or completion mismatch: " + experiment_id)
    raw_id = str(metadata.get("raw_directory", ""))
    if not raw_id.isdigit():
        raise RuntimeError("Invalid raw directory ID: " + experiment_id)
    raw = folder / "raw" / raw_id
    required_raw = {}
    for suffix in ("_out_fct.txt", "_out_cnp.txt", "_out_pfc.txt", "_out_uplink.txt"):
        required_raw[suffix] = result_file(raw, "*" + suffix)
    fct_sha = digest(required_raw["_out_fct.txt"])
    fct_rows = sum(1 for _ in required_raw["_out_fct.txt"].open(encoding="ascii"))
    if fct_rows != sum(expected_tags.values()):
        raise RuntimeError("FCT completion count mismatch: " + experiment_id)

    route = None
    qp_paths = []
    if cell["mode"] == "classlane4":
        log = result_file(folder / "logs", "config.log").read_text(
            encoding="utf-8", errors="replace").splitlines()
        route_lines = [line for line in log if line.startswith("WS26_CLASSLANE4 ")]
        queue_lines = [line for line in log if line.startswith("WS26_QUEUE ")]
        if len(route_lines) != 1 or len(queue_lines) != 1:
            raise RuntimeError("ClassLane summary or queue receipt missing: " + experiment_id)
        route, queue = fields(route_lines[0]), fields(queue_lines[0])
        if (route.get("inconsistent") != 0 or route.get("missing_destination") != 0 or
                route.get("queue_violations") != 0 or
                queue.get("enqueued") != queue.get("dequeued", 0) +
                queue.get("queued_drop", 0) + queue.get("current", 0)):
            raise RuntimeError("ClassLane queue or routing conservation failed: " + experiment_id)
        for tag, name in ((1, "background"), (2, "moe")):
            if (route.get(name + "_packets", 0) < 0 or
                    route.get(name + "_qp_new", 0) < 0 or
                    route.get(name + "_qp_reused", 0) < 0 or
                    route.get(name + "_diverted", 0) < 0):
                raise RuntimeError("Invalid per-tag ClassLane counters: " + experiment_id)
        if cell["trace_key"] == "mixed8" and not all(route.get(key, 0) > 0 for key in
                ("background_packets", "moe_packets", "background_qp_new", "moe_qp_new")):
            raise RuntimeError("Mixed trace did not exercise both classes: " + experiment_id)
        if cell["trace_key"] == "background4" and route.get("moe_packets") != 0:
            raise RuntimeError("Unexpected MoE packets in background-only trace")
        if cell["trace_key"] == "moe4" and route.get("background_packets") != 0:
            raise RuntimeError("Unexpected background packets in MoE-only trace")
        if cell["trace_key"] in ("unclassified8", "legacy5") and route.get("fallback", 0) <= 0:
            raise RuntimeError("ECMP fallback was not exercised: " + experiment_id)
        port_rows = [fields(line) for line in log if line.startswith("WS26_CLASSLANE4_PORT ")]
        if sum(row.get("packets", 0) for row in port_rows if row.get("tag") == 1) != route.get("background_packets") or \
                sum(row.get("packets", 0) for row in port_rows if row.get("tag") == 2) != route.get("moe_packets"):
            raise RuntimeError("Per-tag port packet sums differ from route totals: " + experiment_id)
        if cell["ws25_diag"]:
            qp_paths = [fields(line) for line in log if line.startswith("WS26_CLASSLANE4_QP ")]
            route_by_tag = {1: "background_packets", 2: "moe_packets"}
            if sum(row.get("packets", 0) for row in qp_paths if row.get("tag") == 1) != route.get(route_by_tag[1]) or \
                    sum(row.get("packets", 0) for row in qp_paths if row.get("tag") == 2) != route.get(route_by_tag[2]):
                raise RuntimeError("Per-QP path packet sums differ from route totals: " + experiment_id)
            path_map = {}
            disjoint = collections.defaultdict(lambda: {1: set(), 2: set()})
            for row in qp_paths:
                key = (row.get("switch"), row.get("sip"), row.get("dip"),
                       row.get("sport"), row.get("dport"))
                signature = (row.get("tag"), row.get("dst_tor"), row.get("port"))
                if row.get("tag") not in (1, 2) or row.get("packets", 0) <= 0:
                    raise RuntimeError("Invalid ClassLane QP path row: " + experiment_id)
                if key in path_map and path_map[key] != signature:
                    raise RuntimeError("A QP changed class, destination ToR, or port")
                path_map[key] = signature
                disjoint[(row["switch"], row["dst_tor"])][row["tag"]].add(row["port"])
            if any(groups[1] & groups[2] for groups in disjoint.values()):
                raise RuntimeError("Class port sets overlap at a switch/destination ToR")
            if cell["trace_key"] == "shared_tor4":
                target_rows = [row for row in qp_paths
                               if row.get("switch") == 1280 and row.get("dst_tor") == 1281]
                source_hosts = {((row["sip"] >> 8) & 0xFFFF) for row in target_rows}
                destination_hosts = {((row["dip"] >> 8) & 0xFFFF) for row in target_rows}
                class_ports = {tag: {row["port"] for row in target_rows if row["tag"] == tag}
                               for tag in (1, 2)}
                if (len(target_rows) != 4 or sum(row["tag"] == 1 for row in target_rows) != 2 or
                        sum(row["tag"] == 2 for row in target_rows) != 2 or
                        source_hosts != {0, 4, 8, 12} or
                        destination_hosts != {32, 36, 40, 44} or
                        class_ports[1] & class_ports[2]):
                    raise RuntimeError("Shared source/destination ToR path isolation failed")
    resource = json.loads(result_file(folder / "logs", "resource-summary.json").read_text(
        encoding="utf-8"))
    samples_path = result_file(folder / "logs", "resource-samples.jsonl")
    samples = [json.loads(line) for line in samples_path.read_text(encoding="utf-8").splitlines()
               if line]
    if not (resource.get("id") == experiment_id and resource.get("final_status") == "SUCCEEDED" and
            resource.get("samples") == len(samples) > 0 and
            resource.get("peak_tree_rss_mib", 10**12) <= 32768 and
            resource.get("minimum_mem_available_gib", 0) >= 32 and
            resource.get("minimum_free_gib", 0) >= 100 and
            max(row.get("load_1m", 10**12) for row in samples) <= 20):
        raise RuntimeError("Resource receipt failed: " + experiment_id)
    return {"id": experiment_id, "trace_key": cell["trace_key"], "mode": cell["mode"],
            "pfc": cell["pfc"], "irn": cell["irn"], "fct_sha256": fct_sha,
            "flow_count": sum(expected_tags.values()), "route": route,
            "path_row_count": len(qp_paths), "resource": resource}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-plan", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--id", choices=[cell["id"] for cell in CELLS])
    parser.add_argument("--source-sha", default=SOURCE_SHA)
    args = parser.parse_args()
    if args.write_plan:
        write_plan()
        return
    if args.source_sha != SOURCE_SHA:
        parser.error("This preflight is frozen to source SHA " + SOURCE_SHA)
    validate_plan_and_inputs()
    if args.plan_only:
        print(json.dumps({"plan_valid": True, "cells": len(CELLS),
                          "source_sha": SOURCE_SHA}, sort_keys=True))
        return
    selected = [cell for cell in CELLS if args.id is None or cell["id"] == args.id]
    results = [verify(cell) for cell in selected]
    by_key = {(row["mode"], row["trace_key"], row["pfc"], row["irn"]): row
              for row in results}
    parity_pairs = (("classlane4", "unclassified8", 1, 1),
                    ("classlane4", "legacy5", 1, 1))
    for mode, trace_key, pfc, irn in parity_pairs:
        a = by_key.get((mode, trace_key, pfc, irn))
        b = by_key.get(("fecmp", trace_key, pfc, irn))
        if a and b and a["fct_sha256"] != b["fct_sha256"]:
            raise RuntimeError("ECMP fallback FCT parity failed: " + trace_key)
    plain = by_key.get(("classlane4", "mixed8", 1, 1))
    diagnostic = next((row for row in results if row["id"] == CELLS[17]["id"]), None)
    if plain and diagnostic and plain["fct_sha256"] != diagnostic["fct_sha256"]:
        raise RuntimeError("Diagnostic switch changed FCT")
    for mode in ("fecmp", "drill", "conga", "letflow", "conweave"):
        current = by_key.get((mode, "mixed8", 0, 1))
        if not current:
            continue
        old_id = "20261003-18000%d-ws25-v1fix-pre-%s" % (
            ("fecmp", "drill", "conga", "letflow", "conweave").index(mode), mode)
        old = prior_result(old_id)
        old_meta = json.loads(result_file(old, "metadata.json").read_text(encoding="utf-8"))
        old_params = old_meta.get("parameters", {})
        if (old_meta.get("status") != "SUCCEEDED" or old_meta.get("algorithm") != mode or
                old_meta.get("input_flow_sha256") != TRACES["mixed8"][1] or
                old_meta.get("topology_sha256") != TOPOLOGY_SHA or old_meta.get("seed") != 1 or
                old_params.get("lb") != mode or old_params.get("pfc") != 0 or
                old_params.get("irn") != 1 or old_params.get("bw") != 400 or
                old_params.get("buffer") != 9 or old_params.get("topo") != TOPOLOGY or
                old_params.get("simul_time") != "0.01" or old_params.get("netload") != 10):
            raise RuntimeError("Prior baseline metadata mismatch: " + old_id)
        old_fct = result_file(old / "raw" / str(old_meta["raw_directory"]), "*_out_fct.txt")
        if current["fct_sha256"] != digest(old_fct):
            raise RuntimeError("Original baseline FCT changed: " + mode)
    print(json.dumps({"verified": len(results), "expected": len(CELLS),
                      "cells": results}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

