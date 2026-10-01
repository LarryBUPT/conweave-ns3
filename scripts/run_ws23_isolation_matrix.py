#!/usr/bin/env python3
"""Run the remaining frozen WS-23 matrix cells with bounded build parallelism."""

import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from verify_ws23_isolation_pilot import MODES, ROOT, experiment_id


SOURCE_SHA = "3db2685a3540895bf49e25302bd00465bc0921e2"
CONTROLLER = ROOT / "scripts/remote_experiment.py"
WATCHER = ROOT / "scripts/ws23_start_resource_watch.py"
VERIFIER = ROOT / "scripts/verify_ws23_isolation_pilot.py"
GATE_ID = "20261001-200003-ws23-s2301-mix-fecmp"
RECEIPTS = ROOT / "results/ws23-isolation-matrix-r2-progress.jsonl"


def invoke(*args, timeout=60):
    result = subprocess.run([sys.executable, "-u"] + [str(arg) for arg in args], cwd=ROOT,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            universal_newlines=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError("command failed: %s\n%s" %
                           (" ".join(str(x) for x in args), result.stdout[-2500:]))
    return result.stdout


def audit():
    lines = invoke(CONTROLLER, "check").splitlines()
    return {key: value for key, value in (line.split("=", 1) for line in lines if "=" in line)}


def safe_start(snapshot):
    if float(snapshot["load_1m"]) > 10:
        raise RuntimeError("pre-start load1m exceeds 10")
    if float(snapshot["mem_available_gib"]) < 32:
        raise RuntimeError("pre-start available memory below 32 GiB")
    if float(snapshot["free_gib"]) < 100:
        raise RuntimeError("pre-start free disk below 100 GiB")
    if snapshot["active_simulation_pids"]:
        raise RuntimeError("another simulation is active: " + snapshot["active_simulation_pids"])


def record(handle, event, **values):
    item = {"event": event, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **values}
    handle.write(json.dumps(item, sort_keys=True) + "\n")
    handle.flush()
    print(json.dumps(item, sort_keys=True), flush=True)


def build_one(experiment_id_value):
    start = time.monotonic()
    output = invoke(CONTROLLER, "build", "--repo-local", ROOT, "--id", experiment_id_value,
                    "--source-sha", SOURCE_SHA, timeout=1800)
    duration = time.monotonic() - start
    state = json.loads(invoke(CONTROLLER, "status", experiment_id_value))
    if state.get("status") != "BUILT" or state.get("git_commit") != SOURCE_SHA:
        raise RuntimeError("build identity/status failed: " + experiment_id_value)
    if duration > 1200:
        raise RuntimeError("build exceeded 20-minute stop line: " + experiment_id_value)
    return {"id": experiment_id_value, "duration_seconds": round(duration, 2),
            "git_commit": state["git_commit"], "status": state["status"],
            "output": output.strip()}


def batch_build(handle, batch, jobs):
    futures = {}
    breached = None
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for cell in batch:
            futures[pool.submit(build_one, cell[3])] = cell[3]
        pending = set(futures)
        while pending:
            done, pending = wait(pending, timeout=30, return_when=FIRST_COMPLETED)
            if not done:
                current = audit()
                if float(current["load_1m"]) > 20 or \
                        float(current["mem_available_gib"]) < 16 or \
                        float(current["free_gib"]) < 100:
                    breached = {"load_1m": current["load_1m"],
                                "mem_available_gib": current["mem_available_gib"],
                                "free_gib": current["free_gib"]}
                    record(handle, "build_resource_stop", ids=[futures[f] for f in pending],
                           snapshot=breached)
            for future in done:
                result = future.result()
                record(handle, "built", **result)
    if breached:
        raise RuntimeError("resource stop threshold crossed during build batch")


def run_one(handle, experiment_id_value, mode, flow_file):
    safe_start(audit())
    ready = json.loads(invoke(WATCHER, experiment_id_value, "--source-sha", SOURCE_SHA))
    if ready.get("status") != "READY":
        raise RuntimeError("resource observer did not report READY: " + experiment_id_value)
    record(handle, "ready", id=experiment_id_value, observer_pid=ready.get("observer_pid"))
    invoke(CONTROLLER, "run", experiment_id_value, "--lb", mode, "--simul-time", "0.01",
           "--netload", "10", "--bw", "100", "--buffer", "9",
           "--topo", "fat_k4_100G_OS2", "--cdf", "AliStorage2019", "--flow-file",
           "config/" + flow_file, "--pfc", "0", "--irn", "1", "--factorial-pilot",
           "--factorial-drop-diag", "--max-concurrent", "1")
    started = time.monotonic()
    while True:
        state = json.loads(invoke(CONTROLLER, "status", experiment_id_value))
        if state.get("status") != "RUNNING":
            break
        current = audit()
        if float(current["load_1m"]) > 20 or float(current["mem_available_gib"]) < 16 or \
                float(current["free_gib"]) < 100:
            record(handle, "resource_stop", id=experiment_id_value,
                   load_1m=current["load_1m"], mem_available_gib=current["mem_available_gib"],
                   free_gib=current["free_gib"])
            raise RuntimeError("resource stop threshold crossed during " + experiment_id_value)
        if time.monotonic() - started > 600:
            raise RuntimeError("single-cell simulation exceeded 10-minute stop line")
        time.sleep(30)
    invoke(WATCHER, experiment_id_value, "--source-sha", SOURCE_SHA, "--wait")
    if state.get("status") != "SUCCEEDED":
        invoke(CONTROLLER, "fetch", experiment_id_value)
        record(handle, "failed", id=experiment_id_value, state=state)
        raise RuntimeError("simulation did not succeed: " + experiment_id_value)
    invoke(CONTROLLER, "fetch", experiment_id_value)
    verification = json.loads(invoke(VERIFIER, "--source-sha", SOURCE_SHA,
                                     "--revision", "2", "--cell", experiment_id_value))
    result = verification["verified_cell"]
    record(handle, "verified", id=experiment_id_value, duration_seconds=round(
        time.monotonic() - started, 2), result=result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-jobs", type=int, choices=(1, 2, 3, 4), default=4)
    args = parser.parse_args()
    if not (ROOT / "results" / GATE_ID / "metadata.json").is_file():
        raise RuntimeError("new-input parser gate has not been fetched")
    gate = json.loads(invoke(VERIFIER, "--source-sha", SOURCE_SHA, "--revision", "2",
                             "--cell", GATE_ID))["verified_cell"]
    pending = [(seed, scenario, mode,
                experiment_id(seed, scenario, mode, 2),
                "ws23_isolation_s%d_%s.txt" % (seed, scenario))
               for seed in (2301, 2302, 2303) for scenario in ("bg", "mix")
               for mode in MODES]
    pending = [cell for cell in pending if cell[3] != GATE_ID]
    if len(pending) != 17 or len({cell[3] for cell in pending}) != 17:
        raise RuntimeError("revision-2 matrix mapping is not 17 remaining unique cells")
    if RECEIPTS.exists():
        raise RuntimeError("progress receipt already exists; preserve it and resume by audit")
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    with RECEIPTS.open("x", encoding="utf-8") as handle:
        record(handle, "start", source_sha=SOURCE_SHA, build_jobs=args.build_jobs,
               total_cells=18, already_verified=GATE_ID, gate=gate)
        for offset in range(0, len(pending), args.build_jobs):
            batch = pending[offset:offset + args.build_jobs]
            safe_start(audit())
            record(handle, "build_batch_start", ids=[cell[3] for cell in batch])
            try:
                batch_build(handle, batch, args.build_jobs)
            except Exception as error:
                record(handle, "build_batch_failed", ids=[cell[3] for cell in batch],
                       error=str(error))
                raise
            safe_start(audit())
            for seed, scenario, mode, cell_id, flow_file in batch:
                run_one(handle, cell_id, mode, flow_file)
        record(handle, "complete", source_sha=SOURCE_SHA, completed_cells=18)


if __name__ == "__main__":
    main()
