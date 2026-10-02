#!/usr/bin/env python3
"""Run and verify only the frozen WS-25 192-background cal02-04 pilot."""
import concurrent.futures
import datetime
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import analyze_moe_tags
import run_ws25_preflight as base_runner
import verify_ws25_preflight as preflight

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "04a5277e8ed464229ef88d28a5d810271ae378fb"
TOPO_SHA = preflight.TOPO_SHA
HASHES = {
    20262502: "568046ba32f28d9cf74cdb72fcb0df64d6b37191bac07eed506eed35ddad799d",
    20262503: "2163f9f3c7de0755c908373044b0fd3d397ce1f8c19b36e81241817808801d27",
    20262504: "92404882b0abeba3abca5f41baf3af34b5ed6a362ad87603af87c98580feb3e6",
}
PLAN_PATH = ROOT / "results" / "ws25-calibration-v3-plan.json"
RECEIPTS = ROOT / "results" / "ws25-calibration-v3-receipts.jsonl"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cells():
    output = []
    for seed in sorted(HASHES):
        trace = "ws25_seed%d_b192.txt" % seed
        if sha(ROOT / "config" / trace) != HASHES[seed]:
            raise RuntimeError("Local trace hash changed: " + trace)
        for i, mode in enumerate(preflight.MODES):
            output.append({
                "id": "20261003-03%02d0%d-ws25-v3-cal%02d-%s" %
                      (seed - 20262500, i, seed - 20262500, mode),
                "seed": seed, "mode": mode, "trace": trace,
                "trace_sha256": HASHES[seed],
            })
    return output


def write_plan(selected):
    data = {"kind": "independent calibration pilot, not efficacy matrix",
            "source_sha": SOURCE_SHA, "topology_sha256": TOPO_SHA,
            "ns3_seed": 1, "pfc": 0, "irn": 1, "bw_gbps": 400,
            "buffer_mib": 9, "cells": selected}
    encoded = json.dumps(data, sort_keys=True, indent=2) + "\n"
    if PLAN_PATH.exists():
        if PLAN_PATH.read_text(encoding="utf-8") != encoded:
            raise RuntimeError("Frozen plan changed")
    else:
        PLAN_PATH.write_text(encoded, encoding="utf-8")
    return data


def receipt(event, cell, **details):
    item = {"event": event, "id": cell["id"], "seed": cell["seed"],
            "mode": cell["mode"], "utc": datetime.datetime.utcnow().isoformat() + "Z"}
    item.update(details)
    with RECEIPTS.open("a", encoding="utf-8") as output:
        output.write(json.dumps(item, sort_keys=True) + "\n")
        output.flush()


def verify(cell):
    experiment_id = cell["id"]
    folder = ROOT / "results" / experiment_id
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    if not (meta["status"] == "SUCCEEDED" and meta["git_commit"] == SOURCE_SHA and
            meta["algorithm"] == cell["mode"] and meta["seed"] == 1 and
            meta["input_flow_sha256"] == cell["trace_sha256"] and
            meta["topology_sha256"] == TOPO_SHA and
            meta["parameters"]["flow_file"] == cell["trace"] and
            meta["parameters"]["pfc"] == 0 and meta["parameters"]["irn"] == 1):
        raise RuntimeError("Metadata mismatch: " + experiment_id)
    if sha(folder / "config" / "traffic_trace.txt") != cell["trace_sha256"]:
        raise RuntimeError("Fetched trace hash mismatch")
    if sha(folder / "config" / "topology.txt") != TOPO_SHA:
        raise RuntimeError("Fetched topology hash mismatch")
    summary = analyze_moe_tags.summarize(experiment_id)
    tags = summary["tags"]
    if (tags["1"]["input_flows"] != 192 or tags["1"]["completed_flows"] != 192 or
            tags["2"]["input_flows"] != 16384 or tags["2"]["completed_flows"] != 16384):
        raise RuntimeError("Missing completed flows")
    log = (folder / "logs" / "config.log").read_text(encoding="utf-8", errors="replace")
    if ("LB_MODE\t\t\t%d" % preflight.MODE_CODE[cell["mode"]]) not in log:
        raise RuntimeError("LB mode not recorded")
    if cell["mode"] == "classreserve" and "queue_violations=0" not in log:
        raise RuntimeError("ClassReserve queue conservation failed")
    raw = folder / "raw" / str(meta["raw_directory"])
    for suffix in ("_out_cnp.txt", "_out_pfc.txt", "_out_uplink.txt"):
        paths = list(raw.glob("*" + suffix))
        if len(paths) != 1 or paths[0].is_symlink():
            raise RuntimeError("Missing raw file: " + suffix)
    resources = json.loads((folder / "logs" / "resource-summary.json").read_text())
    samples = [json.loads(x) for x in (folder / "logs" / "resource-samples.jsonl").read_text().splitlines() if x]
    if not (resources["final_status"] == "SUCCEEDED" and resources["samples"] == len(samples) > 0
            and resources["peak_tree_rss_mib"] <= 32768
            and resources["minimum_mem_available_gib"] >= 32
            and resources["minimum_free_gib"] >= 100
            and max(x["load_1m"] for x in samples) <= 20):
        raise RuntimeError("Resource gate failed")
    return {"fct_sha256": summary["fct_sha256"], "resource": resources,
            "moe_batch_us": tags["2"]["synthetic_batch_completion_us"],
            "background_p99_us": tags["1"]["p99_fct_us"]}


def run_cell(cell, cap):
    experiment_id = cell["id"]
    local = ROOT / "results" / experiment_id
    if local.is_dir():
        result = verify(cell)
        receipt("verified_existing", cell, **result)
        return result
    base_runner.audit()
    try:
        state = base_runner.status(experiment_id)
    except RuntimeError as error:
        if "metadata.json" not in str(error) and "No such file" not in str(error):
            raise
        base_runner.command("build", "--repo-local", str(ROOT), "--id", experiment_id,
                            "--source-sha", SOURCE_SHA, "--label", "ws25-v3-calibration")
        state = base_runner.status(experiment_id)
        receipt("built", cell, status=state["status"])
    if state["git_commit"] != SOURCE_SHA:
        raise RuntimeError("Remote source SHA mismatch")
    if state["status"] == "BUILT":
        base_runner.audit()
        base_runner.start_watch(experiment_id)
        base_runner.command("run", experiment_id, "--lb", cell["mode"],
                            "--pfc", "0", "--irn", "1", "--bw", "400", "--buffer", "9",
                            "--topo", "topo_1280_400G_400G_OS1", "--flow-file", cell["trace"],
                            "--simul-time", "0.01", "--netload", "10",
                            "--max-concurrent", str(cap))
        receipt("started", cell, cap=cap)
        state = base_runner.status(experiment_id)
    while state["status"] == "RUNNING":
        time.sleep(300)
        state = base_runner.status(experiment_id)
        base_runner.audit()
    if state["status"] != "SUCCEEDED":
        raise RuntimeError("Terminal experiment failed: %s %s" % (experiment_id, state["status"]))
    base_runner.wait_watch(experiment_id)
    base_runner.command("fetch", experiment_id)
    meta = json.loads((local / "metadata.json").read_text(encoding="utf-8"))
    base_runner.fetch_config_log(cell, meta)
    result = verify(cell)
    receipt("verified", cell, **result)
    return result


def execute(selected):
    # C2 pilot already supported cap=2. Observe three pairs before trying cap=4.
    batches = [(selected[i:i + 2], 2) for i in range(0, 6, 2)]
    batches += [(selected[i:i + 4], 4) for i in range(6, len(selected), 4)]
    for group, cap in batches:
        base_runner.audit()
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(group)) as pool:
            futures = {pool.submit(run_cell, cell, cap): cell for cell in group}
            errors = []
            for future in concurrent.futures.as_completed(futures):
                cell = futures[future]
                try:
                    result = future.result()
                    print(json.dumps({"verified": cell["id"], "cap": cap,
                                      "peak_rss_mib": result["resource"]["peak_tree_rss_mib"]}),
                          flush=True)
                except Exception as error:
                    errors.append((cell["id"], str(error)))
        if errors:
            raise RuntimeError("Stop new cells; preserve failed IDs: " + repr(errors))


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("plan", "run", "verify"))
    args = parser.parse_args()
    selected = cells()
    write_plan(selected)
    if args.phase == "plan":
        print(json.dumps({"source_sha": SOURCE_SHA, "cells": len(selected)}, sort_keys=True))
    elif args.phase == "verify":
        print(json.dumps({"verified": len([verify(cell) for cell in selected])}, sort_keys=True))
    else:
        base_runner.audit(reject_active=True)
        execute(selected)


if __name__ == "__main__":
    main()
