#!/usr/bin/env python3
"""Run the frozen WS-25 formal matrix without replacing existing result IDs."""
import concurrent.futures
import datetime
import hashlib
import json
import re
import time
from pathlib import Path

import analyze_moe_tags
import run_ws25_preflight as base
import run_ws25_v1fix_calibration as calibration
import run_ws25_resource_pilot as pilot

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/research/evidence/ws25-v1fix-formal-inputs.json"
PLAN = ROOT / "docs/research/evidence/ws25-v1fix-formal-plan.json"
RESULT = ROOT / "docs/research/evidence/ws25-v1fix-formal-execution.json"
LOCAL_PLAN = ROOT / "results/ws25-v1fix-formal-plan.json"
SUMMARY = ROOT / "results/ws25-v1fix-formal-summary.json"
RECEIPTS = ROOT / "results/ws25-v1fix-formal-receipts.jsonl"
pilot.RECEIPTS = RECEIPTS
pilot.POLL_SECONDS = 300

SEED_ORDER = tuple(range(20262521, 20262545))
LEVELS = (0, 64, 128, 192)
MODES = ("fecmp", "drill", "conga", "letflow", "conweave", "classreserve")
MAX_CONCURRENT = 16
RANDOMIZATION_SEED = 20261005
ID_PREFIX = "20261004-070000-ws25-formal"
SOURCE_SHA = "ce699dffe2845dc83e2171a1c309c6d96b96d2b3"
TOPO_SHA = calibration.TOPO_SHA
LOCK = __import__("threading").Lock()


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def frozen_plan():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if set(manifest["seeds"]) != {str(seed) for seed in SEED_ORDER}:
        raise RuntimeError("Demand manifest is missing a frozen seed")
    cells = []
    for seed in SEED_ORDER:
        for background in LEVELS:
            item = manifest["seeds"][str(seed)]["levels"][str(background)]
            trace = item["file"]
            if sha(ROOT / "config" / trace) != item["sha256"]:
                raise RuntimeError("Frozen demand trace changed: " + trace)
            if item["flows"] != 16384 + background:
                raise RuntimeError("Frozen flow count differs: " + trace)
            for mode in MODES:
                cells.append({
                    "id": "%s-s%02d-b%03d-%s" %
                          (ID_PREFIX, seed - 20262500, background, mode),
                    "seed": seed,
                    "background": background,
                    "mode": mode,
                    "trace": trace,
                    "trace_sha256": item["sha256"],
                    "input_flows": item["flows"],
                    "expected_tags": ({"2": 16384} if background == 0 else
                                      {"1": background, "2": 16384}),
                    "role": "formal_validation",
                })
    import random
    rng = random.Random(RANDOMIZATION_SEED)
    blocks = [[cell for cell in cells if cell["seed"] == seed and
               cell["background"] == background]
              for seed in SEED_ORDER for background in LEVELS]
    rng.shuffle(blocks)
    cells = []
    for block in blocks:
        rng.shuffle(block)
        cells.extend(block)
    for run_order, cell in enumerate(cells, 1):
        cell["run_order"] = run_order
        cell["batch"] = (run_order - 1) // MAX_CONCURRENT + 1
    data = {
        "kind": "WS-25 formal independent-demand validation",
        "source_sha": SOURCE_SHA,
        "topology_sha256": TOPO_SHA,
        "demand_seed_order": list(SEED_ORDER),
        "background_levels": list(LEVELS),
        "modes": list(MODES),
        "ns3_seed": 1,
        "pfc": 0,
        "irn": 1,
        "bw_gbps": 400,
        "buffer_mib": 9,
        "netload": 10,
        "simul_time": "0.01",
        "max_concurrent": MAX_CONCURRENT,
        "randomization_seed": RANDOMIZATION_SEED,
        "independent_unit": "demand seed, paired by mode within seed and background level",
        "cells": cells,
    }
    encoded = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if PLAN.exists():
        if PLAN.read_text(encoding="utf-8") != encoded:
            raise RuntimeError("Versioned formal calibration plan differs")
    else:
        PLAN.parent.mkdir(parents=True, exist_ok=True)
        PLAN.write_text(encoded, encoding="utf-8")
    if LOCAL_PLAN.exists():
        if LOCAL_PLAN.read_text(encoding="utf-8") != encoded:
            raise RuntimeError("Execution formal calibration plan differs")
    else:
        LOCAL_PLAN.parent.mkdir(parents=True, exist_ok=True)
        LOCAL_PLAN.write_text(encoded, encoding="utf-8")
    return data


def receipt(event, cell=None, **fields):
    row = {"event": event,
           "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if cell is not None:
        row.update({"id": cell["id"], "seed": cell["seed"],
                    "background": cell["background"], "mode": cell["mode"],
                    "run_order": cell["run_order"]})
    row.update(fields)
    with LOCK:
        RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
        with RECEIPTS.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
            stream.flush()


def verify(cell):
    folder = ROOT / "results" / cell["id"]
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = meta["parameters"]
    if not (meta["status"] == "SUCCEEDED" and
            meta["git_commit"] == SOURCE_SHA and
            meta["algorithm"] == cell["mode"] and meta["seed"] == 1 and
            meta["input_flow_sha256"] == cell["trace_sha256"] and
            meta["topology_sha256"] == TOPO_SHA and
            params["flow_file"] == cell["trace"] and params["lb"] == cell["mode"] and
            params["topo"] == "topo_1280_400G_400G_OS1" and params["bw"] == 400 and
            params["buffer"] == 9 and params["simul_time"] == "0.01" and
            params["netload"] == 10 and params["pfc"] == 0 and params["irn"] == 1 and
            params["ws25_diag"] == 0 and meta["concurrency_cap"] == MAX_CONCURRENT):
        raise RuntimeError("Formal metadata mismatch: " + cell["id"])
    if sha(folder / "config" / "traffic_trace.txt") != cell["trace_sha256"]:
        raise RuntimeError("Formal input snapshot mismatch: " + cell["id"])
    if sha(folder / "config" / "topology.txt") != TOPO_SHA:
        raise RuntimeError("Formal topology snapshot mismatch: " + cell["id"])

    summary = analyze_moe_tags.summarize(cell["id"])
    tags = summary["tags"]
    actual_tags = {key: value["input_flows"] for key, value in tags.items()
                   if value["input_flows"]}
    if actual_tags != cell["expected_tags"]:
        raise RuntimeError("Formal tag counts mismatch: " + cell["id"])
    if any(value["completed_flows"] != value["input_flows"]
           for value in tags.values() if value["input_flows"]):
        raise RuntimeError("Formal unfinished flow: " + cell["id"])

    log_path = folder / "logs" / "config.log"
    log = log_path.read_text(encoding="utf-8", errors="replace")
    raw = folder / "raw" / str(meta["raw_directory"])
    for suffix in ("_out_fct.txt", "_out_cnp.txt", "_out_pfc.txt", "_out_uplink.txt"):
        files = list(raw.glob("*" + suffix))
        if len(files) != 1 or files[0].is_symlink():
            raise RuntimeError("Formal raw missing/ambiguous " + suffix + ": " + cell["id"])

    result = {"id": cell["id"], "seed": cell["seed"],
              "background": cell["background"], "mode": cell["mode"],
              "trace_sha256": cell["trace_sha256"], "fct_sha256": summary["fct_sha256"],
              "input_flows": cell["input_flows"], "tags": tags,
              "moe_batch_us": tags["2"]["synthetic_batch_completion_us"],
              "background_p99_us": (tags["1"]["p99_fct_us"]
                                    if cell["background"] else None)}
    if cell["mode"] == "classreserve":
        line = next((row for row in log.splitlines()
                     if row.startswith("WS25_CLASSRESERVE ")), None)
        queue_line = next((row for row in log.splitlines()
                           if row.startswith("WS25_QUEUE ")), None)
        if not line or not queue_line:
            raise RuntimeError("ClassReserve counters absent: " + cell["id"])
        counters = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", line)}
        queued = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", queue_line)}
        if counters.get("queue_violations") != 0 or not (
                counters.get("moe_flow_new", 0) > 0 and
                counters.get("moe_flow_reused", 0) > 0):
            raise RuntimeError("ClassReserve MoE cache invariant failed: " + cell["id"])
        if cell["background"] and not (
                counters.get("background_new_flows", 0) > 0 and
                counters.get("background_reused", 0) > 0):
            raise RuntimeError("ClassReserve background cache invariant failed: " + cell["id"])
        if not (queued.get("enqueued") == queued.get("dequeued") and
                queued.get("queued_drop") == 0 and queued.get("current") == 0):
            raise RuntimeError("ClassReserve queue conservation failed: " + cell["id"])
        result["classreserve"] = counters
        result["queue"] = queued

    resources = json.loads((folder / "logs" / "resource-summary.json").read_text(encoding="utf-8"))
    samples = [json.loads(row) for row in
               (folder / "logs" / "resource-samples.jsonl").read_text(encoding="utf-8").splitlines()
               if row]
    if not (resources["final_status"] == "SUCCEEDED" and
            resources["samples"] == len(samples) > 0 and
            resources["peak_tree_rss_mib"] <= 32768 and
            resources["minimum_mem_available_gib"] >= 32 and
            resources["minimum_free_gib"] >= 100 and
            max(row["load_1m"] for row in samples) <= 20):
        raise RuntimeError("Formal resource gate failed: " + cell["id"])
    resources["peak_load_1m"] = max(row["load_1m"] for row in samples)
    result["resource"] = resources
    return result


def build_one(cell):
    local = ROOT / "results" / cell["id"]
    if local.exists():
        verify(cell)
        return
    try:
        state = base.status(cell["id"])
    except RuntimeError as error:
        if "metadata.json" not in str(error) and "No such file" not in str(error):
            raise
        try:
            base.command("build", "--repo-local", str(ROOT), "--id", cell["id"],
                         "--source-sha", SOURCE_SHA,
                         "--label", "ws25-formal-validation")
        except RuntimeError as build_error:
            # SSH may lose its return path after the remote build commits BUILT.
            # Read metadata through a new connection; never issue a second build.
            try:
                state = base.status(cell["id"])
            except RuntimeError:
                raise build_error
            if state.get("git_commit") != SOURCE_SHA or state.get("status") != "BUILT":
                raise build_error
            receipt("built_recovered_transport", cell, remote_status=state["status"],
                    controller_error=str(build_error)[-600:])
        else:
            state = base.status(cell["id"])
            receipt("built", cell, remote_status=state["status"])
    if state.get("git_commit") != SOURCE_SHA or state.get("status") not in (
            "BUILT", "RUNNING", "SUCCEEDED"):
        raise RuntimeError("Formal ID has unexpected source or state: " + cell["id"])
    if state["status"] == "BUILT":
        calibration.verify_remote_trace(cell)


def prebuild(cells):
    pilot.host_gate(reject_active=True)
    for offset in range(0, len(cells), 4):
        group = cells[offset:offset + 4]
        pilot.host_gate(reject_active=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(group)) as pool:
            futures = {pool.submit(build_one, cell): cell for cell in group}
            for future in concurrent.futures.as_completed(futures):
                future.result()
        pilot.host_gate(reject_active=True)
        print(json.dumps({"prebuilt": min(offset + 4, len(cells)),
                          "total": len(cells)}, sort_keys=True), flush=True)


def start_one(cell):
    if (ROOT / "results" / cell["id"]).exists():
        raise RuntimeError("Existing local results; refusing to start: " + cell["id"])
    state = base.status(cell["id"])
    if state.get("status") != "BUILT" or state.get("git_commit") != SOURCE_SHA:
        raise RuntimeError("Formal ID is not BUILT at the frozen SHA: " + cell["id"])
    calibration.verify_remote_trace(cell)
    base.start_watch(cell["id"])
    base.command("run", cell["id"], "--lb", cell["mode"], "--pfc", "0", "--irn", "1",
                 "--bw", "400", "--buffer", "9", "--topo", "topo_1280_400G_400G_OS1",
                 "--flow-file", cell["trace"], "--simul-time", "0.01", "--netload", "10",
                 "--max-concurrent", str(MAX_CONCURRENT), "--ws25-diag", "0")
    receipt("started", cell, concurrency=MAX_CONCURRENT)


def finish_one(cell):
    base.wait_watch(cell["id"])
    base.command("fetch", cell["id"])
    local = ROOT / "results" / cell["id"]
    meta = json.loads((local / "metadata.json").read_text(encoding="utf-8"))
    base.fetch_config_log(cell, meta)
    result = verify(cell)
    receipt("verified", cell, fct_sha256=result["fct_sha256"],
            peak_tree_rss_mib=result["resource"]["peak_tree_rss_mib"])
    return result


def run_batch(cells, batch_number, batch_count):
    pilot.host_gate(reject_active=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for future in concurrent.futures.as_completed(
                [pool.submit(build_one, cell) for cell in cells]):
            future.result()
    pilot.host_gate(reject_active=True)
    receipt("batch_start", cap=MAX_CONCURRENT, batch=batch_number,
            batches=batch_count, ids=[cell["id"] for cell in cells],
            resume=any((ROOT / "results" / cell["id"]).exists() for cell in cells))
    local_results = {}
    for cell in cells:
        local = ROOT / "results" / cell["id"]
        if local.exists():
            local_results[cell["id"]] = verify(cell)
            receipt("verified_resume", cell,
                    fct_sha256=local_results[cell["id"]]["fct_sha256"],
                    peak_tree_rss_mib=local_results[cell["id"]]["resource"]["peak_tree_rss_mib"])
            continue
        state = base.status(cell["id"])
        if state.get("git_commit") != SOURCE_SHA:
            raise RuntimeError("Formal ID has the wrong frozen SHA: " + cell["id"])
        if state.get("status") == "BUILT":
            pilot.host_gate()
            start_one(cell)
        elif state.get("status") not in ("RUNNING", "SUCCEEDED"):
            raise RuntimeError("Stop before next batch; preserve IDs and raw: %s=%s" %
                               (cell["id"], state.get("status")))
    if len(local_results) != len(cells):
        while True:
            time.sleep(pilot.POLL_SECONDS)
            audit = pilot.host_gate()
            states = {cell["id"]: ("SUCCEEDED" if cell["id"] in local_results else
                                    base.status(cell["id"])["status"])
                      for cell in cells}
            if any(state not in ("RUNNING", "SUCCEEDED") for state in states.values()):
                raise RuntimeError("Stop before next batch; preserve IDs and raw: " + repr(states))
            done = sum(state == "SUCCEEDED" for state in states.values())
            if done == len(cells):
                break
            receipt("batch_progress", batch=batch_number, completed=done,
                    cells=len(cells), load_1m=audit["load_1m"],
                    mem_available_gib=audit["mem_available_gib"])
    pending = [cell for cell in cells if cell["id"] not in local_results]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(finish_one, pending))
    local_results.update({result["id"]: result for result in results})
    results = [local_results[cell["id"]] for cell in cells]
    pilot.host_gate(reject_active=True)
    row = {"batch": batch_number, "cells": len(results),
           "minimum_mem_available_gib": min(r["resource"]["minimum_mem_available_gib"] for r in results),
           "minimum_free_gib": min(r["resource"]["minimum_free_gib"] for r in results),
           "peak_load_1m": max(r["resource"]["peak_load_1m"] for r in results),
           "maximum_tree_rss_mib": max(r["resource"]["peak_tree_rss_mib"] for r in results)}
    return row, results


def execute(cells):
    if RESULT.exists():
        raise RuntimeError("Formal final evidence already exists; refusing overwrite")
    pilot.host_gate(reject_active=True)
    batches = [cells[i:i + MAX_CONCURRENT] for i in range(0, len(cells), MAX_CONCURRENT)]
    summary = {"kind": "formal independent-demand validation",
               "source_sha": SOURCE_SHA,
               "randomization_seed": RANDOMIZATION_SEED,
               "max_concurrent": MAX_CONCURRENT,
               "batches": [], "verified_cells": []}
    for index, batch in enumerate(batches, 1):
        batch_summary, rows = run_batch(batch, index, len(batches))
        summary["batches"].append(batch_summary)
        summary["verified_cells"].extend(rows)
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
        print(json.dumps({"batch_verified": index, "batches": len(batches),
                          "verified_total": len(summary["verified_cells"])},
                         sort_keys=True), flush=True)
    if len(summary["verified_cells"]) != len(cells):
        raise RuntimeError("Formal matrix incomplete")
    summary["verified"] = True
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")
    print(json.dumps({"verified_cells": len(cells), "complete": True,
                      "result": str(RESULT)}, sort_keys=True), flush=True)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("plan", "prebuild", "run", "verify"))
    args = parser.parse_args()
    plan = frozen_plan()
    cells = plan["cells"]
    if args.phase == "plan":
        print(json.dumps({"cells": len(cells), "seeds": len(SEED_ORDER),
                          "levels": list(LEVELS), "modes": len(MODES),
                          "source_sha": SOURCE_SHA,
                          "randomization_seed": RANDOMIZATION_SEED}, sort_keys=True))
    elif args.phase == "prebuild":
        prebuild(cells)
    elif args.phase == "run":
        execute(cells)
    else:
        rows = [verify(cell) for cell in cells]
        if len(rows) != 576 or len({row["id"] for row in rows}) != 576:
            raise RuntimeError("Formal verifier did not validate 576 unique cells")
        print(json.dumps({"verified_cells": len(rows), "complete": True}, sort_keys=True))


if __name__ == "__main__":
    main()
