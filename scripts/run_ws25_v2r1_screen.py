#!/usr/bin/env python3
"""Execute the frozen WS-25 v2r1 screen with original-ID recovery."""
import concurrent.futures
import datetime
import json
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import run_ws25_preflight as base
import run_ws25_v1fix_calibration as calibration
import run_ws25_v2_correctness as safe
import verify_ws25_v2r1_screen as verifier
import verify_ws25_v2r1_correctness as correctness
import ws25_v2r1_controller_lock as controller_lock

ROOT = Path(__file__).resolve().parents[1]
PLAN = verifier.PLAN
CELLS = PLAN["cells"]
RECEIPTS = ROOT / "results/ws25-v2r1-screen-receipts.jsonl"
SUMMARY = ROOT / "results/ws25-v2r1-screen-summary.json"
RECEIPT_LOCK = threading.Lock()


def receipt(event, cell, **extra):
    row = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "event": event, "id": cell["id"], "run_order": cell["run_order"]}
    row.update(extra)
    with RECEIPT_LOCK:
        with RECEIPTS.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
            stream.flush()


def state_or_missing(cell):
    try:
        return safe.status(cell["id"])
    except RuntimeError as error:
        if str(error).startswith("REMOTE_METADATA_MISSING: "):
            return None
        raise


def build_one(cell):
    if (ROOT / "results" / cell["id"]).is_dir():
        return
    state = state_or_missing(cell)
    if state is None:
        try:
            base.command("build", "--repo-local", str(ROOT), "--id", cell["id"],
                         "--source-sha", PLAN["source_sha"])
        except RuntimeError:
            # An SSH return-path failure may follow a successful remote build.
            # A second build request is forbidden; only read the original ID.
            state = state_or_missing(cell)
            if state is None or state.get("status") != "BUILT" or state.get(
                    "git_commit") != PLAN["source_sha"]:
                raise
            receipt("built_recovered_transport", cell)
        else:
            state = state_or_missing(cell)
            receipt("built", cell)
    if state is None or state.get("git_commit") != PLAN["source_sha"] or state.get(
            "status") not in ("BUILT", "RUNNING", "SUCCEEDED"):
        raise RuntimeError("Unsafe original ID state: " + cell["id"])
    if state["status"] == "BUILT":
        with safe.TRANSPORT_LOCK:
            calibration.verify_remote_trace(cell)


def start_one(cell, cap):
    if (ROOT / "results" / cell["id"]).is_dir():
        return None
    state = state_or_missing(cell)
    if state is None or state["git_commit"] != PLAN["source_sha"]:
        raise RuntimeError("Missing/wrong built source: " + cell["id"])
    if state["status"] == "BUILT":
        safe.host_gate(reject_active=(cap == 1))
        with safe.TRANSPORT_LOCK:
            base.start_watch(cell["id"])
            message = base.command("run", cell["id"], "--lb", cell["mode"],
                                   "--pfc", "0", "--irn", "1", "--bw", "400",
                                   "--buffer", "9", "--topo",
                                   "topo_1280_400G_400G_OS1", "--flow-file",
                                   cell["trace"], "--simul-time", "0.01",
                                   "--netload", "10", "--max-concurrent", str(cap),
                                   "--ws25-diag", str(cell["ws25_diag"]))
        match = re.search(r"started experiment=" + re.escape(cell["id"]) +
                          r" pid=(\d+) cap=" + str(cap), message)
        if match is None:
            raise RuntimeError("Run receipt marker missing; inspect original ID: " + cell["id"])
        receipt("started", cell, cap=cap, pid=int(match.group(1)))
    elif state["status"] not in ("RUNNING", "SUCCEEDED"):
        raise RuntimeError("Unsafe launch state: " + cell["id"])
    return state["status"]


def finish_one(cell):
    local = ROOT / "results" / cell["id"]
    if local.is_dir():
        result = verifier.verify(cell)
        receipt("verified_existing", cell)
        return result
    state = state_or_missing(cell)
    if state is None or state["git_commit"] != PLAN["source_sha"]:
        raise RuntimeError("Original ID missing after launch: " + cell["id"])
    if state["status"] == "RUNNING":
        return None
    if state["status"] != "SUCCEEDED":
        raise RuntimeError("Terminal failure, preserve ID: %s %s" %
                           (cell["id"], state["status"]))
    with safe.TRANSPORT_LOCK:
        base.wait_watch(cell["id"])
        base.command("fetch", cell["id"])
        meta = json.loads((local / "metadata.json").read_text(encoding="utf-8"))
        base.fetch_config_log(cell, meta)
    result = verifier.verify(cell)
    receipt("verified", cell, cap=meta["concurrency_cap"],
            fct_sha256=result["fct_sha256"], resource=result["resource"])
    return result


def wait_group(cells):
    pending = {cell["id"]: cell for cell in cells}
    while pending:
        for cell in list(pending.values()):
            if finish_one(cell) is not None:
                del pending[cell["id"]]
        if pending:
            base.audit()
            time.sleep(90)


def group(cells, cap):
    # A previous controller may have exited while one of these original IDs
    # was RUNNING. Confirm that state before allowing a recovery observation.
    observed = [state_or_missing(cell) for cell in cells]
    recovering = [cell for cell, state in zip(cells, observed) if state is not None and
                  state.get("status") == "RUNNING"]
    safe.host_gate(reject_active=not recovering)
    if recovering:
        wait_group(recovering)
        safe.host_gate(reject_active=True)
    if cap == 1:
        # The first full-demand cell is the resource pilot. Only after its
        # raw/resource receipt passes may later independent builds overlap.
        first, rest = cells[0], cells[1:]
        build_one(first)
        start_one(first, cap)
        wait_group([first])
        for start in range(0, len(rest), 4):
            batch = rest[start:start + 4]
            safe.host_gate(reject_active=True)
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(batch)) as pool:
                futures = [pool.submit(build_one, cell) for cell in batch]
                for future in futures:
                    future.result()
            safe.host_gate(reject_active=True)
            for cell in batch:
                start_one(cell, cap)
                wait_group([cell])
    else:
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
        raise SystemExit("Frozen screen has no runtime overrides")
    if len(CELLS) != 28 or [cell["run_order"] for cell in CELLS] != list(range(1, 29)):
        raise RuntimeError("Frozen screen plan malformed")
    if PLAN["simulator_sha"] != correctness.SHA:
        raise RuntimeError("Screen simulator SHA differs from correctness gate")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=str(ROOT)).strip():
        raise RuntimeError("Commit controller changes before starting screen runner")
    # Recheck all original small-input raw, fallback equality and old-mode
    # fingerprints before admitting a full-demand screening cell.
    correctness.main()
    groups = [CELLS[:7]]
    for start in range(7, len(CELLS), 7):
        block = CELLS[start:start + 7]
        if len(block) != 7 or any(cell["seed"] != block[0]["seed"] for cell in block):
            raise RuntimeError("Screen paired block malformed")
        groups.extend((block[:4], block[4:6], block[6:]))
    for index, cells in enumerate(groups):
        group(cells, 1 if index == 0 else 4)
        print(json.dumps({"verified_group": index + 1, "verified_cells":
                          sum((ROOT / "results" / cell["id"]).is_dir()
                              for cell in CELLS)}), flush=True)
    results = [verifier.verify(cell) for cell in CELLS]
    SUMMARY.write_text(json.dumps({"verified": True, "source_sha": PLAN["source_sha"],
                                   "cells": results}, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")
    print(json.dumps({"screen_complete": True, "verified": len(results)}), flush=True)


def main():
    with controller_lock.exclusive():
        run()


if __name__ == "__main__":
    main()
