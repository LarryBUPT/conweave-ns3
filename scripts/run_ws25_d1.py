#!/usr/bin/env python3
"""Serial controller for the frozen WS-25 D1 on/off diagnostic pilot."""
import json
import subprocess
import sys
import time
from pathlib import Path

import run_ws25_preflight as base
import verify_ws25_d1 as verifier

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = verifier.SOURCE_SHA


def status(experiment_id):
    return base.status(experiment_id)


def finish_cell(experiment_id, mode, diag):
    base.wait_watch(experiment_id)
    base.command("fetch", experiment_id)
    meta = json.loads((ROOT / "results" / experiment_id / "metadata.json").read_text(
        encoding="utf-8"))
    base.fetch_config_log({"id": experiment_id, "trace": verifier.TRACE}, meta)
    row = verifier.verify_cell(experiment_id, mode, diag)
    print(json.dumps({"verified": row}, sort_keys=True), flush=True)
    return row


def await_running(experiment_id):
    state = status(experiment_id)
    while state["status"] == "RUNNING":
        time.sleep(300)
        state = status(experiment_id)
        base.audit()
    if state["status"] != "SUCCEEDED":
        raise RuntimeError("D1 terminal failure; preserve ID: %s status=%s" %
                           (experiment_id, state["status"]))
    return state


def launch_cell(experiment_id, mode, diag, already_started=False):
    folder = ROOT / "results" / experiment_id
    if folder.exists():
        raise RuntimeError("Refuse to overwrite existing local result: " + experiment_id)
    base.audit()
    try:
        state = status(experiment_id)
    except RuntimeError as error:
        if "metadata.json" not in str(error) and "No such file" not in str(error):
            raise
        base.command("build", "--repo-local", str(ROOT), "--id", experiment_id,
                     "--source-sha", SOURCE_SHA, "--label", "ws25-d1-diagnostic")
        state = status(experiment_id)
    if state["git_commit"] != SOURCE_SHA:
        raise RuntimeError("D1 source SHA mismatch: " + experiment_id)
    if state["status"] == "SUCCEEDED":
        raise RuntimeError("Unexpected already-succeeded ID without local result: " + experiment_id)
    if state["status"] == "BUILT":
        base.start_watch(experiment_id)
        base.command("run", experiment_id, "--lb", mode, "--pfc", "0", "--irn", "1",
                     "--bw", "400", "--buffer", "9", "--topo",
                     "topo_1280_400G_400G_OS1", "--flow-file", verifier.TRACE,
                     "--simul-time", "0.01", "--netload", "10", "--max-concurrent", "1",
                     "--ws25-diag", str(diag))
        state = status(experiment_id)
    elif state["status"] == "RUNNING" and not already_started:
        raise RuntimeError("Refuse unexpected in-flight D1 ID: " + experiment_id)
    elif state["status"] != "RUNNING":
        raise RuntimeError("Unexpected D1 state %s for %s" %
                           (state["status"], experiment_id))
    await_running(experiment_id)
    return finish_cell(experiment_id, mode, diag)


def main():
    first = verifier.CELLS[0]
    second = verifier.CELLS[1]
    third, fourth = verifier.CELLS[2:]
    # Resume the already-started on cell only after its off counterpart passes.
    if (ROOT / "results" / first[0]).exists():
        off = verifier.verify_cell(*first)
    else:
        off = launch_cell(*first, already_started=False)
    old_fct = next(x["fct_sha256"] for x in json.load(open(
        ROOT / "docs" / "research" / "evidence" / "ws25-four-seed-calibration.json",
        encoding="utf-8"))["cells"] if x["seed"] == 20262501 and
        x["mode"] == "classreserve")
    if off["fct_sha256"] != old_fct:
        raise RuntimeError("ClassReserve off FCT differs from calibration; stop D1")

    # This cell was launched before the controller was created; do not restart it.
    if not (ROOT / "results" / second[0]).exists():
        state = status(second[0])
        if state["git_commit"] != SOURCE_SHA or state["status"] not in ("RUNNING", "SUCCEEDED"):
            raise RuntimeError("Unexpected resumed D1 state: " + repr(state))
        await_running(second[0])
        on = finish_cell(second[0], second[1], second[2])
    else:
        on = verifier.verify_cell(*second)
    if off["fct_sha256"] != on["fct_sha256"]:
        raise RuntimeError("ClassReserve on/off FCT fingerprints differ; stop before DRILL")

    drill_off = launch_cell(*third)
    drill_on = launch_cell(*fourth)
    if drill_off["fct_sha256"] != drill_on["fct_sha256"]:
        raise RuntimeError("DRILL on/off FCT fingerprints differ")
    print(json.dumps({"d1_complete": True, "classreserve_fct_sha256": off["fct_sha256"],
                      "drill_fct_sha256": drill_off["fct_sha256"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
