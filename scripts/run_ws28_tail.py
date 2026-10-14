#!/usr/bin/env python3
"""Run and verify the frozen WS-28 nonperturbing tail probe one cell at a time."""
import argparse
import datetime
import json
import re
import time
from pathlib import Path

import analyze_moe_tags
import run_ws25_preflight as base
import run_ws25_resource_pilot as pilot
import run_ws25_v1fix_calibration as calibration


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/research/evidence/ws28-tail-plan-v2.json"
SUMMARY = ROOT / "results/ws28-tail-summary.json"
RECEIPTS = ROOT / "results/ws28-tail-receipts.jsonl"
pilot.RECEIPTS = RECEIPTS


def receipt(event, cell, **fields):
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    row = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "event": event, "id": cell["id"], **fields}
    with RECEIPTS.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")


def verify(cell, plan):
    folder = ROOT / "results" / cell["id"]
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = meta["parameters"]
    if not (meta["status"] == "SUCCEEDED" and
            meta["git_commit"] == plan["source_sha"] and
            meta["algorithm"] == cell["mode"] and meta["seed"] == 1 and
            meta["input_flow_sha256"] == cell["trace_sha256"] and
            meta["topology_sha256"] == plan["topology_sha256"] and
            meta["concurrency_cap"] == 1 and
            params["flow_file"] == cell["trace"] and
            params["ws28_tail_diag"] == cell["diag"] and
            params["pfc"] == 0 and params["irn"] == 1 and
            params["bw"] == 400 and params["buffer"] == 9):
        raise RuntimeError("tail metadata mismatch: " + cell["id"])
    if (analyze_moe_tags.sha256(folder / "config/traffic_trace.txt") != cell["trace_sha256"] or
            analyze_moe_tags.sha256(folder / "config/topology.txt") != plan["topology_sha256"]):
        raise RuntimeError("tail input snapshot changed: " + cell["id"])
    stats = analyze_moe_tags.summarize(cell["id"])
    tags = stats["tags"]
    if ({tag: row["input_flows"] for tag, row in tags.items()} != cell["expected_tags"] or
            any(row["completed_flows"] != row["input_flows"] for row in tags.values()) or
            stats["fct_sha256"] != cell["expected_fct_sha256"]):
        raise RuntimeError("tail completion or nonperturbation failed: " + cell["id"])
    log = (folder / "logs/config.log").read_text(encoding="utf-8", errors="replace")
    kinds = {key: len(re.findall(r"^WS28_TAIL_" + key + r"\b", log, re.M))
             for key in ("CHOICE", "OFFER", "ENQUEUE", "DEQUEUE",
                         "REJECT", "DROP", "ADMISSION_DROP")}
    if cell["diag"]:
        if ("WS28_TAIL_OVERFLOW" in log or not all(kinds[key] > 0 for key in
                                                 ("CHOICE", "OFFER", "ENQUEUE", "DEQUEUE"))):
            raise RuntimeError("tail probe missing events or overflowed: " + cell["id"])
        if sum(kinds.values()) > plan["row_limit"]:
            raise RuntimeError("tail probe row limit exceeded: " + cell["id"])
    elif any(kinds.values()):
        raise RuntimeError("tail probe leaked into disabled cell: " + cell["id"])
    resource = json.loads((folder / "logs/resource-summary.json").read_text(encoding="utf-8"))
    if not (resource["final_status"] == "SUCCEEDED" and
            resource["peak_tree_rss_mib"] <= 32768 and
            resource["minimum_mem_available_gib"] >= 32 and
            resource["minimum_free_gib"] >= 100):
        raise RuntimeError("tail resource gate failed: " + cell["id"])
    return {"id": cell["id"], "seed": cell["seed"], "mode": cell["mode"],
            "diag": cell["diag"], "fct_sha256": stats["fct_sha256"],
            "events": kinds, "resource": resource}


def run_cell(cell, plan):
    local = ROOT / "results" / cell["id"]
    if local.exists():
        return verify(cell, plan)
    try:
        state = base.status(cell["id"])
    except RuntimeError as error:
        if "REMOTE_METADATA_MISSING:" not in str(error):
            raise
        pilot.host_gate(reject_active=True)
        base.command("build", "--repo-local", str(ROOT), "--id", cell["id"],
                     "--source-sha", plan["source_sha"], "--label", "ws28-tail")
        state = base.status(cell["id"])
        receipt("built", cell, status=state["status"])
    if state.get("git_commit") != plan["source_sha"]:
        raise RuntimeError("tail source SHA differs: " + cell["id"])
    if state["status"] == "BUILT":
        calibration.verify_remote_trace(cell)
        pilot.host_gate(reject_active=True)
        base.start_watch(cell["id"])
        base.command("run", cell["id"], "--lb", cell["mode"],
                     "--pfc", "0", "--irn", "1", "--bw", "400", "--buffer", "9",
                     "--topo", "topo_1280_400G_400G_OS1", "--flow-file", cell["trace"],
                     "--simul-time", "0.01", "--netload", "10", "--max-concurrent", "1",
                     "--ws28-tail-diag", str(cell["diag"]))
        receipt("started", cell, diag=cell["diag"])
        state = base.status(cell["id"])
    while state["status"] == "RUNNING":
        time.sleep(180)
        pilot.host_gate()
        state = base.status(cell["id"])
    if state["status"] != "SUCCEEDED":
        raise RuntimeError("tail cell failed; preserve ID: " + cell["id"])
    base.wait_watch(cell["id"])
    base.command("fetch", cell["id"])
    meta = json.loads((local / "metadata.json").read_text(encoding="utf-8"))
    base.fetch_config_log(cell, meta)
    row = verify(cell, plan)
    receipt("verified", cell, fct_sha256=row["fct_sha256"], events=row["events"])
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("verify", "run"))
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    cells = plan["cells"][:args.limit]
    rows = []
    for cell in cells:
        rows.append(verify(cell, plan) if args.phase == "verify" else run_cell(cell, plan))
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(json.dumps({"source_sha": plan["source_sha"],
                                       "plan_sha256": analyze_moe_tags.sha256(PLAN),
                                       "verified_cells": rows}, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
        print(json.dumps({"verified": len(rows), "of": len(cells), "id": cell["id"]}),
              flush=True)


if __name__ == "__main__":
    main()
