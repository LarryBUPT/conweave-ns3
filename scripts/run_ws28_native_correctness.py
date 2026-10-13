#!/usr/bin/env python3
"""Five-arm mixed-eight technical check before WS-28 native resource runs."""
import argparse
import json
import re
import time
from pathlib import Path

import analyze_moe_tags
import run_ws25_preflight as remote
import run_ws25_resource_pilot as resources
import run_ws28_native as native


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/research/evidence/ws28-native-correctness-plan.json"
RESULT = ROOT / "docs/research/evidence/ws28-native-correctness-results.json"
TRACE = "ws25_v1fix_mixed8.txt"
TRACE_SHA = "29ebe2dcf38c0e4d29326947c4bc4e111f6b56fe378c020c30ee788fbaa5effb"
MODES = ("fecmp",) + native.MODES


def frozen_plan():
    if analyze_moe_tags.sha256(ROOT / "config" / TRACE) != TRACE_SHA:
        raise RuntimeError("Technical trace changed")
    cells = [{"id": f"20261014-000001-ws28-ncheck-{mode}", "mode": mode,
              "trace": TRACE, "trace_sha256": TRACE_SHA,
              "expected_tags": {"1": 4, "2": 4}} for mode in MODES]
    plan = {"kind": "WS-28 native mixed-eight technical check",
            "source_sha": native.SOURCE_SHA, "topology_sha256": native.prior.TOPO_SHA,
            "max_concurrent": 1, "pfc": 0, "irn": 1, "cells": cells}
    encoded = json.dumps(plan, indent=2, sort_keys=True) + "\n"
    if PLAN.exists() and PLAN.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("Frozen WS-28 technical plan changed")
    PLAN.write_text(encoded, encoding="utf-8")
    return plan


def verify(cell):
    folder = ROOT / "results" / cell["id"]
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = meta["parameters"]
    if not (meta["status"] == "SUCCEEDED" and meta["git_commit"] == native.SOURCE_SHA and
            meta["algorithm"] == cell["mode"] and meta["seed"] == 1 and
            meta["input_flow_sha256"] == TRACE_SHA and
            meta["topology_sha256"] == native.prior.TOPO_SHA and
            meta["concurrency_cap"] == 1 and params["flow_file"] == TRACE and
            params["pfc"] == 0 and params["irn"] == 1 and params["bw"] == 400 and
            params["buffer"] == 9 and params["ws25_diag"] == 0):
        raise RuntimeError("Technical metadata mismatch: " + cell["id"])
    if (analyze_moe_tags.sha256(folder / "config/traffic_trace.txt") != TRACE_SHA or
            analyze_moe_tags.sha256(folder / "config/topology.txt") != native.prior.TOPO_SHA):
        raise RuntimeError("Technical input mismatch: " + cell["id"])
    stats = analyze_moe_tags.summarize(cell["id"])
    tags = stats["tags"]
    if ({tag: row["input_flows"] for tag, row in tags.items()} != cell["expected_tags"] or
            any(row["completed_flows"] != row["input_flows"] for row in tags.values())):
        raise RuntimeError("Technical flow completion failed: " + cell["id"])
    log = (folder / "logs/config.log").read_text(encoding="utf-8", errors="replace")
    dynamic = {}
    if cell["mode"] in ("conga", "letflow"):
        name = "CONGA History" if cell["mode"] == "conga" else "Letflow History"
        match = re.search(r"Number of flowlet's timeout:(\d+)", log)
        if name not in log or not match:
            raise RuntimeError("Technical flowlet receipt absent: " + cell["id"])
        dynamic["flowlet_timeouts"] = int(match.group(1))
    elif cell["mode"] == "conweave":
        match = re.search(r"Number of INIT's Reply sent \(RTT_REPLY\):(\d+)", log)
        if "ConWeave History" not in log or not match:
            raise RuntimeError("Technical ConWeave receipt absent: " + cell["id"])
        dynamic["rtt_replies"] = int(match.group(1))
    resource = json.loads((folder / "logs/resource-summary.json").read_text(encoding="utf-8"))
    samples = [json.loads(line) for line in
               (folder / "logs/resource-samples.jsonl").read_text(encoding="utf-8").splitlines()
               if line]
    if not (resource["final_status"] == "SUCCEEDED" and
            resource["samples"] == len(samples) > 0 and
            resource["peak_tree_rss_mib"] <= 32768 and
            resource["minimum_mem_available_gib"] >= 32 and
            resource["minimum_free_gib"] >= 100 and
            max(row["load_1m"] for row in samples) <= 20):
        raise RuntimeError("Technical resource gate failed: " + cell["id"])
    return {"id": cell["id"], "mode": cell["mode"],
            "fct_sha256": stats["fct_sha256"], "tags": tags,
            "dynamic_receipt": dynamic, "resource": resource}


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
                       "--source-sha", native.SOURCE_SHA, "--label", "ws28-native-check")
        state = remote.status(cell["id"])
    if state.get("git_commit") != native.SOURCE_SHA:
        raise RuntimeError("Technical source changed: " + cell["id"])
    if state["status"] == "BUILT":
        resources.host_gate(reject_active=True)
        remote.start_watch(cell["id"])
        remote.command("run", cell["id"], "--lb", cell["mode"], "--pfc", "0",
                       "--irn", "1", "--bw", "400", "--buffer", "9",
                       "--topo", "topo_1280_400G_400G_OS1", "--flow-file", TRACE,
                       "--simul-time", "0.01", "--netload", "10",
                       "--max-concurrent", "1", "--ws25-diag", "0")
        state = remote.status(cell["id"])
    while state["status"] == "RUNNING":
        time.sleep(30)
        state = remote.status(cell["id"])
    if state["status"] != "SUCCEEDED":
        raise RuntimeError("Preserve failed technical ID: " + cell["id"])
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
        print(json.dumps({"cells": len(plan["cells"]), "source_sha": native.SOURCE_SHA}))
        return
    if args.phase == "run":
        if RESULT.exists():
            raise RuntimeError("Technical results already finalized")
        rows = [run_cell(cell) for cell in plan["cells"]]
        RESULT.write_text(json.dumps({"source_sha": native.SOURCE_SHA,
                                      "verified_cells": len(rows), "rows": rows},
                                     indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        rows = [verify(cell) for cell in plan["cells"]]
        if RESULT.exists() and rows != json.loads(RESULT.read_text(encoding="utf-8"))["rows"]:
            raise RuntimeError("Saved technical result differs from raw")
        print(json.dumps({"verified_cells": len(rows)}))


if __name__ == "__main__":
    main()
