#!/usr/bin/env python3
"""Run the frozen ClassReserve correction correctness matrix with gated concurrency."""
import concurrent.futures
import datetime
import json
import sys
import threading
import time
from pathlib import Path

import run_ws25_preflight as base
import verify_ws25_v1fix_correctness as verifier

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = verifier.SOURCE_SHA
RECEIPTS = ROOT / "results" / "ws25-v1fix-correctness-receipts.jsonl"
LOCK = threading.Lock()


def receipt(event, cell, **details):
    item = {"event": event, "id": cell[0], "mode": cell[1], "trace": cell[2],
            "utc": datetime.datetime.utcnow().isoformat() + "Z"}
    item.update(details)
    with LOCK:
        RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
        with RECEIPTS.open("a", encoding="utf-8") as output:
            output.write(json.dumps(item, sort_keys=True) + "\n")
            output.flush()


def run_cell(cell, cap):
    experiment_id, mode, trace, diag = cell
    local = ROOT / "results" / experiment_id
    if local.exists():
        result = verifier.verify_cell(*cell)
        receipt("verified_existing", cell, **result)
        return result
    try:
        state = base.status(experiment_id)
    except RuntimeError as error:
        message = str(error)
        if "metadata.json" not in message and "No such file" not in message:
            raise
        base.command("build", "--repo-local", str(ROOT), "--id", experiment_id,
                     "--source-sha", SOURCE_SHA, "--label", "ws25-v1fix-correctness")
        state = base.status(experiment_id)
        receipt("built", cell, status=state["status"])
    if state["git_commit"] != SOURCE_SHA:
        raise RuntimeError("Correctness source SHA mismatch: " + experiment_id)
    if state["status"] == "BUILT":
        base.start_watch(experiment_id)
        base.command("run", experiment_id, "--lb", mode, "--pfc", "0", "--irn", "1",
                     "--bw", "400", "--buffer", "9", "--topo",
                     "topo_1280_400G_400G_OS1", "--flow-file", trace,
                     "--simul-time", "0.01", "--netload", "10", "--max-concurrent",
                     str(cap), "--ws25-diag", str(diag))
        state = base.status(experiment_id)
        receipt("started", cell, cap=cap)
    elif state["status"] not in ("RUNNING", "SUCCEEDED"):
        raise RuntimeError("Unexpected correctness state %s for %s" %
                           (state["status"], experiment_id))
    while state["status"] == "RUNNING":
        time.sleep(300)
        state = base.status(experiment_id)
        base.audit()
    if state["status"] != "SUCCEEDED":
        raise RuntimeError("Correctness failure; preserve ID: %s (%s)" %
                           (experiment_id, state["status"]))
    base.wait_watch(experiment_id)
    base.command("fetch", experiment_id)
    meta = json.loads((local / "metadata.json").read_text(encoding="utf-8"))
    base.fetch_config_log({"id": experiment_id, "trace": trace}, meta)
    result = verifier.verify_cell(*cell)
    receipt("verified", cell, cap=cap, **result)
    print(json.dumps({"verified": result}, sort_keys=True), flush=True)
    return result


def run_group(cells, cap):
    base.audit(reject_active=True)
    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(cells)) as pool:
        futures = {pool.submit(run_cell, cell, cap): cell for cell in cells}
        for future in concurrent.futures.as_completed(futures):
            cell = futures[future]
            try:
                future.result()
            except Exception as error:
                errors.append((cell[0], str(error)))
    if errors:
        raise RuntimeError("Stop before next batch; preserve failed cells: " + repr(errors))
    base.audit(reject_active=True)


def main():
    if len(sys.argv) != 1:
        raise SystemExit("This controller accepts no runtime overrides; see frozen protocol.")
    pilot = next(cell for cell in verifier.CELLS
                 if cell[0] == "20261003-180005-ws25-v1fix-pre-classreserve")
    run_group([pilot], 1)
    pending = [cell for cell in verifier.CELLS if cell != pilot]
    for start in range(0, len(pending), 2):
        run_group(pending[start:start + 2], 2)
    print(json.dumps({"correctness_matrix_complete": True,
                      "verified_cells": len(verifier.CELLS)}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
