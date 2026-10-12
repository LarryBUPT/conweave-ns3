#!/usr/bin/env python3
"""Verify WS-27 single-class fallback and diagnostic non-interference."""
import argparse
import json
import re
import time
from pathlib import Path

import analyze_moe_tags
import run_ws25_preflight as remote
import run_ws25_resource_pilot as resources

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "592211afe90dcc056051941a924480c1b4a876a2"
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
PLAN = ROOT / "docs/research/evidence/ws27-correctness-plan.json"
RESULT = ROOT / "docs/research/evidence/ws27-correctness-results.json"
TRACES = {
    "moe4": ("ws25_v1fix_moe4.txt", "8acfe14d19d7ef7822bfd9a78334b830ce581456003e132d6557a44d1e41ea60", {"2": 4}),
    "background4": ("ws25_v1fix_background4.txt", "e1259a4dbb17fe70e15a72881cbc3faaeac637123ba18ac29596b4f4f2743015", {"1": 4}),
    "diag_mixed8": ("ws25_v1fix_mixed8.txt", "29ebe2dcf38c0e4d29326947c4bc4e111f6b56fe378c020c30ee788fbaa5effb", {"1": 4, "2": 4}),
}
REFERENCE = {
    "guardhash-v2": "20261013-012000-ws27-guard-v2-preflight",
    "harmgate-v2": "20261013-004744-ws27-harm-v2-preflight",
}


def cells():
    entries = []
    for scenario, modes in (("moe4", ("guardhash-v2", "harmgate-v2")),
                            ("background4", ("fecmp", "guardhash-v2", "harmgate-v2")),
                            ("diag_mixed8", ("guardhash-v2", "harmgate-v2"))):
        trace, digest, tags = TRACES[scenario]
        for mode in modes:
            entries.append({"id": "20261013-023000-ws27-%s-%s" % (scenario, mode),
                            "scenario": scenario, "mode": mode,
                            "trace": trace, "trace_sha256": digest,
                            "expected_tags": tags, "ws25_diag": int(scenario == "diag_mixed8")})
    return entries


def frozen_plan():
    for trace, digest, unused in TRACES.values():
        if analyze_moe_tags.sha256(ROOT / "config" / trace) != digest:
            raise RuntimeError("Correctness trace changed: " + trace)
    plan = {"source_sha": SOURCE_SHA, "topology_sha256": TOPO_SHA,
            "cells": cells(), "max_concurrent": 1}
    encoded = json.dumps(plan, indent=2, sort_keys=True) + "\n"
    if PLAN.exists() and PLAN.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("Frozen correctness plan changed")
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    PLAN.write_text(encoded, encoding="utf-8")
    return plan


def verify(cell):
    folder = ROOT / "results" / cell["id"]
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = meta["parameters"]
    if not (meta["status"] == "SUCCEEDED" and meta["git_commit"] == SOURCE_SHA and
            meta["algorithm"] == cell["mode"] and meta["seed"] == 1 and
            meta["input_flow_sha256"] == cell["trace_sha256"] and
            meta["topology_sha256"] == TOPO_SHA and
            meta["concurrency_cap"] == 1 and
            params["flow_file"] == cell["trace"] and
            params["ws25_diag"] == cell["ws25_diag"] and
            params["pfc"] == 0 and params["irn"] == 1 and
            params["bw"] == 400 and params["buffer"] == 9 and
            params["topo"] == "topo_1280_400G_400G_OS1"):
        raise RuntimeError("Correctness metadata mismatch: " + cell["id"])
    if (analyze_moe_tags.sha256(folder / "config/traffic_trace.txt") != cell["trace_sha256"] or
            analyze_moe_tags.sha256(folder / "config/topology.txt") != TOPO_SHA):
        raise RuntimeError("Correctness input snapshot mismatch: " + cell["id"])
    stats = analyze_moe_tags.summarize(cell["id"])
    tags = stats["tags"]
    if {tag: row["input_flows"] for tag, row in tags.items()} != cell["expected_tags"]:
        raise RuntimeError("Incorrect tag count: " + cell["id"])
    if any(row["completed_flows"] != row["input_flows"] for row in tags.values()):
        raise RuntimeError("Unfinished correctness flow: " + cell["id"])
    log = (folder / "logs/config.log").read_text(encoding="utf-8", errors="replace")
    counter = None
    if cell["mode"] != "fecmp":
        lines = [line for line in log.splitlines() if line.startswith("WS27_GUARD ")]
        if len(lines) != 1:
            raise RuntimeError("Missing new-mode receipt: " + cell["id"])
        counter = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", lines[0])}
        if counter.get("mode") != (23 if cell["mode"] == "guardhash-v2" else 24):
            raise RuntimeError("Incorrect new mode: " + cell["id"])
        if counter.get("queue_violations") != 0:
            raise RuntimeError("Queue conservation failed: " + cell["id"])
        if cell["scenario"] == "background4":
            if counter.get("moe_packets") != 0 or counter.get("fallback_packets", 0) <= 0:
                raise RuntimeError("Background ECMP fallback absent: " + cell["id"])
        elif not (counter.get("new_flows", 0) > 0 and
                  counter.get("reused_packets", 0) > 0 and
                  counter["moe_packets"] == counter["new_flows"] + counter["reused_packets"]):
            raise RuntimeError("New-mode QP cache invariant failed: " + cell["id"])
    resources = json.loads((folder / "logs/resource-summary.json").read_text(encoding="utf-8"))
    samples = [json.loads(line) for line in
               (folder / "logs/resource-samples.jsonl").read_text(encoding="utf-8").splitlines()
               if line]
    if not (resources["final_status"] == "SUCCEEDED" and
            resources["samples"] == len(samples) > 0 and
            resources["peak_tree_rss_mib"] <= 32768 and
            resources["minimum_mem_available_gib"] >= 32 and
            resources["minimum_free_gib"] >= 100 and
            max(row["load_1m"] for row in samples) <= 20):
        raise RuntimeError("Correctness resource gate failed: " + cell["id"])
    return {"id": cell["id"], "scenario": cell["scenario"], "mode": cell["mode"],
            "fct_sha256": stats["fct_sha256"], "tags": tags,
            "ws27_guard": counter, "resource": resources}


def run_cell(cell):
    folder = ROOT / "results" / cell["id"]
    if folder.exists():
        return verify(cell)
    try:
        state = remote.status(cell["id"])
    except RuntimeError as error:
        if "REMOTE_METADATA_MISSING:" not in str(error):
            raise
        resources.host_gate(reject_active=True)
        remote.command("build", "--repo-local", str(ROOT), "--id", cell["id"],
                       "--source-sha", SOURCE_SHA, "--label", "ws27-correctness")
        state = remote.status(cell["id"])
    if state.get("git_commit") != SOURCE_SHA:
        raise RuntimeError("Correctness source SHA changed: " + cell["id"])
    if state["status"] == "BUILT":
        resources.host_gate(reject_active=True)
        remote.start_watch(cell["id"])
        remote.command("run", cell["id"], "--lb", cell["mode"], "--pfc", "0",
                       "--irn", "1", "--bw", "400", "--buffer", "9",
                       "--topo", "topo_1280_400G_400G_OS1",
                       "--flow-file", cell["trace"], "--simul-time", "0.01",
                       "--netload", "10", "--max-concurrent", "1",
                       "--ws25-diag", str(cell["ws25_diag"]))
        state = remote.status(cell["id"])
    while state["status"] == "RUNNING":
        time.sleep(30)
        state = remote.status(cell["id"])
    if state["status"] != "SUCCEEDED":
        raise RuntimeError("Preserve failed correctness ID: " + cell["id"])
    remote.wait_watch(cell["id"])
    remote.command("fetch", cell["id"])
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    remote.fetch_config_log(cell, meta)
    return verify(cell)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("plan", "run", "verify"))
    args = parser.parse_args()
    plan = frozen_plan()
    if args.phase == "plan":
        print(json.dumps({"cells": len(plan["cells"]), "source_sha": SOURCE_SHA}))
        return
    if args.phase == "run":
        resources.host_gate()
        rows = []
        for cell in plan["cells"]:
            rows.append(run_cell(cell))
            print(json.dumps({"verified": cell["id"]}), flush=True)
        resources.host_gate(reject_active=True)
    else:
        rows = [verify(cell) for cell in plan["cells"]]
    by_id = {row["id"]: row for row in rows}
    for mode, reference in REFERENCE.items():
        expected = analyze_moe_tags.summarize(reference)["fct_sha256"]
        actual = by_id["20261013-023000-ws27-diag_mixed8-" + mode]["fct_sha256"]
        if actual != expected:
            raise RuntimeError("Diagnostic changed FCT for " + mode)
    background_hashes = {row["fct_sha256"] for row in rows
                         if row["scenario"] == "background4"}
    if len(background_hashes) != 1:
        raise RuntimeError("Background-only routing differs from ECMP")
    encoded = json.dumps({"source_sha": SOURCE_SHA, "verified_cells": rows},
                         indent=2, sort_keys=True) + "\n"
    if RESULT.exists() and RESULT.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("Existing correctness evidence differs")
    RESULT.write_text(encoded, encoding="utf-8")
    print(json.dumps({"verified_cells": len(rows)}, sort_keys=True))


if __name__ == "__main__":
    main()
