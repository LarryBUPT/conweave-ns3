#!/usr/bin/env python3
"""Run the frozen v2 sole-correction correctness cells with original-ID recovery."""
import concurrent.futures
import datetime
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import run_ws25_preflight as base
import run_ws25_v1fix_calibration as calibration
import run_ws25_v2_correctness as safe
import verify_ws25_v2r1_correctness as verifier
import ws25_v2r1_controller_lock as controller_lock

ROOT = Path(__file__).resolve().parents[1]
RECEIPTS = ROOT / "results/ws25-v2r1-correctness-receipts.jsonl"
SUMMARY = ROOT / "results/ws25-v2r1-correctness-summary.json"


def receipt(event, cell, **extra):
    row = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "event": event, "id": cell[0]}
    row.update(extra)
    with RECEIPTS.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
        stream.flush()


def state_or_missing(cell):
    try:
        return safe.status(cell[0])
    except RuntimeError as error:
        if str(error).startswith("REMOTE_METADATA_MISSING: "):
            return None
        raise


def build_one(cell):
    if (ROOT / "results" / cell[0]).is_dir():
        return
    state = state_or_missing(cell)
    if state is None:
        try:
            base.command("build", "--repo-local", str(ROOT), "--id", cell[0],
                         "--source-sha", verifier.SHA)
        except RuntimeError:
            state = state_or_missing(cell)
            if state is None or state.get("status") != "BUILT" or state.get(
                    "git_commit") != verifier.SHA:
                raise
            receipt("built_recovered_transport", cell)
        else:
            state = state_or_missing(cell)
            receipt("built", cell)
    if state is None or state.get("git_commit") != verifier.SHA or state.get(
            "status") not in ("BUILT", "RUNNING", "SUCCEEDED"):
        raise RuntimeError("Unsafe original ID state: " + cell[0])
    if state["status"] == "BUILT":
        trace = {"id": cell[0], "trace": cell[2],
                 "trace_sha256": verifier.old.TRACES[cell[2]][0]}
        with safe.TRANSPORT_LOCK:
            calibration.verify_remote_trace(trace)


def start_one(cell, cap):
    if (ROOT / "results" / cell[0]).is_dir():
        return
    state = state_or_missing(cell)
    if state is None or state.get("git_commit") != verifier.SHA:
        raise RuntimeError("Missing/wrong built source: " + cell[0])
    if state["status"] == "BUILT":
        safe.host_gate(reject_active=(cap == 1))
        with safe.TRANSPORT_LOCK:
            base.start_watch(cell[0])
            message = base.command("run", cell[0], "--lb", cell[1],
                                   "--pfc", "0", "--irn", "1", "--bw", "400",
                                   "--buffer", "9", "--topo", "topo_1280_400G_400G_OS1",
                                   "--flow-file", cell[2], "--simul-time", "0.01",
                                   "--netload", "10", "--max-concurrent", str(cap),
                                   "--ws25-diag", str(cell[3]))
        match = re.search(r"started experiment=" + re.escape(cell[0]) +
                          r" pid=(\d+) cap=" + str(cap), message)
        if match is None:
            raise RuntimeError("Start marker missing; inspect original ID: " + cell[0])
        receipt("started", cell, cap=cap, pid=int(match.group(1)))
    elif state["status"] not in ("RUNNING", "SUCCEEDED"):
        raise RuntimeError("Unsafe launch state: " + cell[0])


def finish_one(cell):
    local = ROOT / "results" / cell[0]
    if local.is_dir():
        return verifier.verify(cell)
    state = state_or_missing(cell)
    if state is None or state.get("git_commit") != verifier.SHA:
        raise RuntimeError("Original ID missing after launch: " + cell[0])
    if state["status"] == "RUNNING":
        return None
    if state["status"] != "SUCCEEDED":
        raise RuntimeError("Terminal failure, preserve ID %s %s" % (cell[0], state["status"]))
    with safe.TRANSPORT_LOCK:
        base.wait_watch(cell[0])
        base.command("fetch", cell[0])
        meta = json.loads((local / "metadata.json").read_text(encoding="utf-8"))
        base.fetch_config_log({"id": cell[0]}, meta)
    result = verifier.verify(cell)
    receipt("verified", cell, cap=meta["concurrency_cap"],
            fct_sha256=result["fct_sha256"], resource=result["resource"])
    return result


def wait_group(cells):
    pending = {cell[0]: cell for cell in cells}
    while pending:
        for cell in list(pending.values()):
            if finish_one(cell) is not None:
                del pending[cell[0]]
        if pending:
            base.audit()
            time.sleep(90)


def group(cells, cap):
    observed = [state_or_missing(cell) for cell in cells]
    recovering = [cell for cell, state in zip(cells, observed) if state is not None and
                  state.get("status") == "RUNNING"]
    safe.host_gate(reject_active=not recovering)
    if recovering:
        wait_group(recovering)
        safe.host_gate(reject_active=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(cells)) as pool:
        futures = [pool.submit(build_one, cell) for cell in cells]
        for future in futures:
            future.result()
    safe.host_gate(reject_active=True)
    for cell in cells:
        start_one(cell, cap)
    wait_group(cells)
    safe.host_gate(reject_active=True)


def run():
    if len(sys.argv) != 1:
        raise SystemExit("Frozen correctness plan has no runtime overrides")
    if len(verifier.CELLS) != 13 or len({cell[0] for cell in verifier.CELLS}) != 13:
        raise RuntimeError("Frozen correctness identities malformed")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=str(ROOT)).strip():
        raise RuntimeError("Commit controller changes before running")
    groups = [verifier.CELLS[:1]]
    groups.extend(verifier.CELLS[start:start + 4]
                  for start in range(1, len(verifier.CELLS), 4))
    for index, cells in enumerate(groups):
        group(cells, 1 if index == 0 else 4)
        print(json.dumps({"verified_group": index + 1,
                          "verified_cells": sum((ROOT / "results" / cell[0]).is_dir()
                                                for cell in verifier.CELLS)}), flush=True)
    verifier.main()
    results = [verifier.verify(cell) for cell in verifier.CELLS]
    SUMMARY.write_text(json.dumps({"verified": True, "source_sha": verifier.SHA,
                                   "cells": results}, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")
    print(json.dumps({"correctness_complete": True, "verified": len(results)}), flush=True)


def main():
    with controller_lock.exclusive():
        run()


if __name__ == "__main__":
    main()
