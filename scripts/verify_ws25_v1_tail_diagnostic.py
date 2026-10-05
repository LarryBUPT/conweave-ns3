#!/usr/bin/env python3
"""Verify two posthoc WS-25 v1 diagnostic replays without treating them as efficacy samples."""
import argparse
import hashlib
import json
import re
from pathlib import Path

import analyze_moe_tags
import analyze_ws25_calibration as diagnostic_parser

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/research/evidence/ws25-v1-formal-tail-diagnostic-plan.json"
RECOVERY = ROOT / "docs/research/evidence/ws25-v1-tail-diagnostic-recovery-plan.json"
EXECUTION = ROOT / "docs/research/evidence/ws25-v1fix-formal-execution.json"
OUTPUT = ROOT / "docs/research/evidence/ws25-v1-formal-tail-diagnostic-analysis.json"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fields(line):
    return {key: int(value) for key, value in re.findall(r"(\w+)=(-?\d+)", line)}


def fct_rows(path, background):
    rows = {}
    with path.open("r", encoding="ascii") as source:
        for line in source:
            data = list(map(int, line.split()))
            if len(data) != 8:
                raise RuntimeError("Malformed FCT row in " + str(path))
            if data[4] != 8 * 1024 * 1024:
                continue
            key = tuple(data[:6])
            if key in rows:
                raise RuntimeError("Duplicate background FCT key in " + str(path))
            rows[key] = data[6] / 1000
    if len(rows) != background:
        raise RuntimeError("Background FCT count mismatch in " + str(path))
    return rows


def raw_fct(folder):
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    raw = folder / "raw" / str(meta["raw_directory"])
    files = list(raw.glob("*_out_fct.txt"))
    if len(files) != 1 or files[0].is_symlink():
        raise RuntimeError("Ambiguous FCT raw for " + str(folder))
    return files[0]


def host_tors(path):
    result = {}
    with path.open("r", encoding="ascii") as source:
        next(source)
        next(source)
        for line in source:
            values = line.split()
            if len(values) < 2:
                continue
            a, b = map(int, values[:2])
            if a < 1280 and b >= 1280:
                result[a] = b
    return result


def check(cell, plan, execution):
    folder = ROOT / "results" / cell["id"]
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = meta["parameters"]
    if not (meta["status"] == "SUCCEEDED" and
            meta["git_commit"] == plan["source_sha"] and
            meta["input_flow_sha256"] == cell["trace_sha256"] and
            meta["topology_sha256"] == plan["topology_sha256"] and
            meta["algorithm"] == "classreserve" and
            params["lb"] == "classreserve" and
            params["flow_file"] == cell["trace"] and
            params["topo"] == "topo_1280_400G_400G_OS1" and
            params["pfc"] == 0 and params["irn"] == 1 and
            params["bw"] == 400 and params["buffer"] == 9 and
            params["netload"] == 10 and params["simul_time"] == "0.01" and
            params["ws25_diag"] == 1):
        raise RuntimeError("Diagnostic identity or parameters mismatch: " + cell["id"])
    if (sha(ROOT / "config" / cell["trace"]) != cell["trace_sha256"] or
            sha(folder / "config/traffic_trace.txt") != cell["trace_sha256"] or
            sha(folder / "config/topology.txt") != plan["topology_sha256"]):
        raise RuntimeError("Diagnostic input snapshot mismatch: " + cell["id"])
    summarized = analyze_moe_tags.summarize(cell["id"])
    tags = summarized["tags"]
    if ({tag: x["input_flows"] for tag, x in tags.items()} !=
            {"1": cell["background"], "2": 16384} or
            any(x["completed_flows"] != x["input_flows"] for x in tags.values())):
        raise RuntimeError("Diagnostic flows incomplete: " + cell["id"])

    # fetch keeps the simulator's config.log alongside the raw FCT. Earlier
    # matrix runners copied it to logs/ separately, but this replay did not.
    log_path = folder / "raw" / str(meta["raw_directory"]) / "config.log"
    if not log_path.is_file():
        raise RuntimeError("Diagnostic config.log missing: " + cell["id"])
    log = log_path.read_text(encoding="utf-8", errors="replace")
    mode = diagnostic_parser.diagnostics("classreserve", log)["classreserve"]
    queue = diagnostic_parser.diagnostics("classreserve", log)["queue"]
    if not (mode["queue_violations"] == 0 and queue["enqueued"] == queue["dequeued"]
            and queue["queued_drop"] == 0 and queue["current"] == 0):
        raise RuntimeError("Diagnostic queue invariant failed: " + cell["id"])
    qp = {}
    hops = {}
    choice = {}
    inflight = None
    for line in log.splitlines():
        if line.startswith("WS25_QP "):
            row = fields(line)
            if row["flow_id"] in qp:
                raise RuntimeError("Duplicate QP diagnostic row")
            qp[row["flow_id"]] = row
        elif line.startswith("WS13_HOP "):
            row = fields(line)
            key = (row["src"], row["dst"], row["sport"], row["dport"])
            hops.setdefault(key, []).append(row)
        elif line.startswith("WS25_CHOICE "):
            row = fields(line)
            choice[row["tag"]] = row
        elif line.startswith("WS13_INFLIGHT "):
            inflight = fields(line)["unpaired"]
    if (set(qp) != set(range(cell["input_flows"])) or
            sum(row["tag"] == 1 for row in qp.values()) != cell["background"] or
            set(choice) != {1, 2} or inflight != 0 or not hops):
        raise RuntimeError("Diagnostic coverage failed: " + cell["id"])

    resource_summary = folder / "logs/resource-summary.json"
    resource_samples = folder / "logs/resource-samples.jsonl"
    if not resource_summary.is_file() or not resource_samples.is_file():
        raise RuntimeError("Diagnostic resource receipts missing: " + cell["id"])
    resources = json.loads(resource_summary.read_text(encoding="utf-8"))
    samples = [json.loads(line) for line in
               resource_samples.read_text(encoding="utf-8").splitlines()
               if line]
    if not (resources["final_status"] == "SUCCEEDED" and
            resources["samples"] == len(samples) > 0 and
            resources["peak_tree_rss_mib"] <= 32768 and
            resources["minimum_mem_available_gib"] >= 32 and
            resources["minimum_free_gib"] >= 100 and
            max(x["load_1m"] for x in samples) <= 20):
        raise RuntimeError("Diagnostic resource gate failed: " + cell["id"])

    fct = raw_fct(folder)
    same_fct = sha(fct) == cell["formal_control_fct_sha256"]
    ecmp_id = cell["formal_control_id"].replace("-classreserve", "-fecmp")
    ecmp = next(x for x in execution["verified_cells"] if x["id"] == ecmp_id)
    ecmp_fct = raw_fct(ROOT / "results" / ecmp_id)
    if sha(ecmp_fct) != ecmp["fct_sha256"]:
        raise RuntimeError("Formal ECMP FCT changed: " + ecmp_id)
    compared = fct_rows(fct, cell["background"])
    control = fct_rows(ecmp_fct, cell["background"])
    if compared.keys() != control.keys():
        raise RuntimeError("Formal and diagnostic background identities differ")
    trace_lines = (folder / "config/traffic_trace.txt").read_text(encoding="ascii").splitlines()
    trace_by_pair = {}
    for index, line in enumerate(trace_lines[1:cell["background"] + 1]):
        src, dst = map(int, line.split()[:2])
        if (src, dst) in trace_by_pair:
            raise RuntimeError("Duplicate background src/dst in input trace")
        trace_by_pair[src, dst] = index
    tors = host_tors(folder / "config/topology.txt")
    background_flows = []
    if same_fct:
        for key in sorted(compared, key=lambda key: compared[key] - control[key], reverse=True):
            src, dst, sport, dport = key[:4]
            flow_id = trace_by_pair[src, dst]
            matched = hops.get((src, dst, sport, dport), [])
            dest_hops = [row for row in matched if row["switch"] == tors[dst]]
            background_flows.append({"src": src, "dst": dst, "flow_id": flow_id,
                                     "destination_tor": tors[dst],
                                     "ecmp_fct_us": control[key],
                                     "classreserve_fct_us": compared[key],
                                     "change_us": compared[key] - control[key],
                                     "qp": qp[flow_id], "destination_hops": dest_hops,
                                     "all_hop_rows": len(matched)})
    return {"id": cell["id"], "seed": cell["seed"], "background": cell["background"],
            "fct_sha256": sha(fct), "matches_formal_fct": same_fct,
            "fct_control_sha256": cell["formal_control_fct_sha256"],
            "qp_rows": len(qp), "background_hop_flows": len(hops),
            "inflight_unpaired": inflight, "choice": choice,
            "classreserve": mode, "queue": queue, "resource": resources,
            "config_log_sha256": sha(log_path),
            "tail_flows": background_flows[:5],
            "background_flows": background_flows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", help="verify one diagnostic ID before opening the next")
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    recovery = json.loads(RECOVERY.read_text(encoding="utf-8"))
    if (recovery["original_plan_sha256"] != sha(PLAN) or
            recovery["source_sha"] != plan["source_sha"] or
            recovery["replaced_id"] != plan["cells"][0]["id"] or
            recovery["accepted_ids_in_order"] !=
            [recovery["replacement_id"], plan["cells"][1]["id"]]):
        raise RuntimeError("Diagnostic recovery plan does not match frozen original")
    execution = json.loads(EXECUTION.read_text(encoding="utf-8"))
    replacement = dict(plan["cells"][0], id=recovery["replacement_id"])
    all_cells = plan["cells"] + [replacement]
    accepted = [replacement, plan["cells"][1]]
    cells = [cell for cell in all_cells if cell["id"] == args.id] if args.id else accepted
    if not cells or (not args.id and len(cells) != 2):
        raise RuntimeError("Diagnostic plan selection is incomplete")
    checked = [check(cell, plan, execution) for cell in cells]
    if not all(row["matches_formal_fct"] for row in checked):
        raise RuntimeError("Diagnostic changed formal FCT fingerprint: " +
                           repr([(row["id"], row["fct_sha256"]) for row in checked]))
    if args.id:
        print(json.dumps({"id": checked[0]["id"], "matches_formal_fct": True,
                          "qp_rows": checked[0]["qp_rows"],
                          "background_hop_flows": checked[0]["background_hop_flows"],
                          "resource": checked[0]["resource"]}, sort_keys=True))
    else:
        output = {"role": plan["kind"], "source_sha": plan["source_sha"],
                  "plan_sha256": sha(PLAN), "recovery_plan_sha256": sha(RECOVERY),
                  "replaced_id": recovery["replaced_id"], "cells": checked,
                  "formal_efficacy_rejudged": False}
        OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
        print(json.dumps({"verified": len(checked), "formal_efficacy_rejudged": False,
                          "output": str(OUTPUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
