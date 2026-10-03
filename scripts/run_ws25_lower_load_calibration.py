#!/usr/bin/env python3
"""Run the frozen 0/64/128-background WS-25 calibration matrix."""
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
MANIFEST = ROOT / "docs/research/evidence/ws25-v1fix-calibration-inputs.json"
PLAN = ROOT / "docs/research/evidence/ws25-v1fix-lower-load-calibration-plan-r3.json"
RESULT = ROOT / "docs/research/evidence/ws25-v1fix-lower-load-calibration.json"
LOCAL_PLAN = ROOT / "results/ws25-v1fix-lower-load-calibration-plan-r3.json"
SUMMARY = ROOT / "results/ws25-v1fix-lower-load-calibration-summary.json"
RECEIPTS = ROOT / "results/ws25-v1fix-lower-load-calibration-receipts.jsonl"
pilot.RECEIPTS = RECEIPTS
pilot.POLL_SECONDS = 300

SEED_ORDER = (20262507, 20262508, 20262505, 20262506)
LEVELS = (0, 64, 128)
MODES = ("fecmp", "drill", "conga", "letflow", "conweave", "classreserve")
MAX_CONCURRENT = 16
RANDOMIZATION_SEED = 20261004
ID_PREFIX = "20261004-030000-ws25-lower"
LOCK = __import__("threading").Lock()


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def frozen_plan():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["seeds"].keys() < {str(seed) for seed in SEED_ORDER}:
        raise RuntimeError("Demand manifest is missing a frozen seed")
    cells = []
    for seed in SEED_ORDER:
        for background in LEVELS:
            item = manifest["seeds"][str(seed)]["inputs"][str(background)]
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
                    "role": "constraint_calibration",
                })
    import random
    from collections import Counter
    rng = random.Random(RANDOMIZATION_SEED)
    remaining = cells[:]
    cells = []
    final_size = len(remaining) % MAX_CONCURRENT
    final_batch = []
    final_mode_count, final_background_count, final_seed_count = Counter(), Counter(), Counter()
    while len(final_batch) < final_size:
        scores = {
            id(cell): (final_mode_count[cell["mode"]],
                       final_background_count[cell["background"]],
                       final_seed_count[cell["seed"]])
            for cell in remaining
        }
        best = min(scores.values())
        choices = [cell for cell in remaining
                   if scores[id(cell)] == best and final_seed_count[cell["seed"]] < 2]
        if not choices:
            raise RuntimeError("Could not balance the final partial batch")
        cell = rng.choice(choices)
        remaining.remove(cell)
        final_batch.append(cell)
        final_mode_count[cell["mode"]] += 1
        final_background_count[cell["background"]] += 1
        final_seed_count[cell["seed"]] += 1
    if (set(final_mode_count) != set(MODES) or set(final_background_count) != set(LEVELS) or
            any(final_background_count[level] < 2 for level in LEVELS) or
            any(final_seed_count[seed] != 2 for seed in SEED_ORDER)):
        raise RuntimeError("Final partial batch is not balanced across modes/levels/seeds")
    rng.shuffle(final_batch)
    batch_sizes = [MAX_CONCURRENT] * (len(remaining) // MAX_CONCURRENT)
    for batch_number, batch_size in enumerate(batch_sizes, 1):
        selected = []
        mode_count, background_count, seed_count = Counter(), Counter(), Counter()
        while len(selected) < batch_size:
            scores = {
                id(cell): (mode_count[cell["mode"]],
                           background_count[cell["background"]],
                           seed_count[cell["seed"]])
                for cell in remaining
            }
            best = min(scores.values())
            choices = [cell for cell in remaining if scores[id(cell)] == best]
            cell = rng.choice(choices)
            remaining.remove(cell)
            cell["batch"] = batch_number
            selected.append(cell)
            mode_count[cell["mode"]] += 1
            background_count[cell["background"]] += 1
            seed_count[cell["seed"]] += 1
        rng.shuffle(selected)
        cells.extend(selected)
    final_batch_number = len(batch_sizes) + 1
    for cell in final_batch:
        cell["batch"] = final_batch_number
    cells.extend(final_batch)
    for run_order, cell in enumerate(cells, 1):
        cell["run_order"] = run_order
    data = {
        "kind": "WS-25 lower-load constraint calibration; exploratory, not efficacy",
        "source_sha": calibration.SOURCE_SHA,
        "topology_sha256": calibration.TOPO_SHA,
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
            raise RuntimeError("Versioned lower-load calibration plan differs")
    else:
        PLAN.parent.mkdir(parents=True, exist_ok=True)
        PLAN.write_text(encoded, encoding="utf-8")
    if LOCAL_PLAN.exists():
        if LOCAL_PLAN.read_text(encoding="utf-8") != encoded:
            raise RuntimeError("Execution lower-load calibration plan differs")
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
            meta["git_commit"] == calibration.SOURCE_SHA and
            meta["algorithm"] == cell["mode"] and meta["seed"] == 1 and
            meta["input_flow_sha256"] == cell["trace_sha256"] and
            meta["topology_sha256"] == calibration.TOPO_SHA and
            params["flow_file"] == cell["trace"] and params["lb"] == cell["mode"] and
            params["topo"] == "topo_1280_400G_400G_OS1" and params["bw"] == 400 and
            params["buffer"] == 9 and params["simul_time"] == "0.01" and
            params["netload"] == 10 and params["pfc"] == 0 and params["irn"] == 1 and
            params["ws25_diag"] == 0 and meta["concurrency_cap"] == MAX_CONCURRENT):
        raise RuntimeError("Lower-load calibration metadata mismatch: " + cell["id"])
    if sha(folder / "config" / "traffic_trace.txt") != cell["trace_sha256"]:
        raise RuntimeError("Lower-load input snapshot mismatch: " + cell["id"])
    if sha(folder / "config" / "topology.txt") != calibration.TOPO_SHA:
        raise RuntimeError("Lower-load topology snapshot mismatch: " + cell["id"])

    summary = analyze_moe_tags.summarize(cell["id"])
    tags = summary["tags"]
    actual_tags = {key: value["input_flows"] for key, value in tags.items()
                   if value["input_flows"]}
    if actual_tags != cell["expected_tags"]:
        raise RuntimeError("Lower-load tag counts mismatch: " + cell["id"])
    if any(value["completed_flows"] != value["input_flows"]
           for value in tags.values() if value["input_flows"]):
        raise RuntimeError("Lower-load unfinished flow: " + cell["id"])

    log_path = folder / "logs" / "config.log"
    log = log_path.read_text(encoding="utf-8", errors="replace")
    raw = folder / "raw" / str(meta["raw_directory"])
    for suffix in ("_out_fct.txt", "_out_cnp.txt", "_out_pfc.txt", "_out_uplink.txt"):
        files = list(raw.glob("*" + suffix))
        if len(files) != 1 or files[0].is_symlink():
            raise RuntimeError("Lower-load raw missing/ambiguous " + suffix + ": " + cell["id"])

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
        raise RuntimeError("Lower-load resource gate failed: " + cell["id"])
    resources["peak_load_1m"] = max(row["load_1m"] for row in samples)
    result["resource"] = resources
    return result


def build_one(cell):
    local = ROOT / "results" / cell["id"]
    if local.exists():
        raise RuntimeError("Refusing to overwrite an existing local ID: " + cell["id"])
    try:
        state = base.status(cell["id"])
    except RuntimeError as error:
        if "metadata.json" not in str(error) and "No such file" not in str(error):
            raise
        base.command("build", "--repo-local", str(ROOT), "--id", cell["id"],
                     "--source-sha", calibration.SOURCE_SHA,
                     "--label", "ws25-lower-load-calibration")
        state = base.status(cell["id"])
        receipt("built", cell, remote_status=state["status"])
    if state.get("git_commit") != calibration.SOURCE_SHA or state.get("status") != "BUILT":
        raise RuntimeError("Lower-load ID is not a fresh build: " + cell["id"])
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
    if state.get("status") != "BUILT" or state.get("git_commit") != calibration.SOURCE_SHA:
        raise RuntimeError("Lower-load ID is not BUILT at the frozen SHA: " + cell["id"])
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
    pilot.host_gate()
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
        if state.get("git_commit") != calibration.SOURCE_SHA:
            raise RuntimeError("Lower-load ID has the wrong frozen SHA: " + cell["id"])
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
            print(json.dumps({"batch": batch_number, "completed": done,
                              "cells": len(cells), "load_1m": audit["load_1m"],
                              "mem_available_gib": audit["mem_available_gib"]},
                             sort_keys=True), flush=True)
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
    if SUMMARY.exists() or RESULT.exists():
        raise RuntimeError("Calibration summary already exists; refusing overwrite")
    pilot.host_gate(reject_active=True)
    batches = [cells[i:i + MAX_CONCURRENT] for i in range(0, len(cells), MAX_CONCURRENT)]
    summary = {"kind": "exploratory 0/64/128 constraints; not efficacy",
               "source_sha": calibration.SOURCE_SHA,
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
        raise RuntimeError("Lower-load matrix incomplete")
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
                          "source_sha": calibration.SOURCE_SHA,
                          "randomization_seed": RANDOMIZATION_SEED}, sort_keys=True))
    elif args.phase == "prebuild":
        prebuild(cells)
    elif args.phase == "run":
        if not all(base.status(cell["id"]).get("status") == "BUILT" for cell in cells):
            raise RuntimeError("All 72 cells must be prebuilt before starting the matrix")
        execute(cells)
    else:
        rows = [verify(cell) for cell in cells]
        if len(rows) != 72 or len({row["id"] for row in rows}) != 72:
            raise RuntimeError("Lower-load verifier did not validate 72 unique cells")
        print(json.dumps({"verified_cells": len(rows), "complete": True}, sort_keys=True))


if __name__ == "__main__":
    main()
