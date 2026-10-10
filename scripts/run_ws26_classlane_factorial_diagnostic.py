#!/usr/bin/env python3
"""Run frozen WS-26 class-rule diagnostic cells serially with durable receipts."""

import argparse
import datetime
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import run_ws26_moe_hop_diagnostic as base
import verify_ws26_classlane_factorial_diagnostic as verifier


ROOT = verifier.ROOT
SCRIPTS = ROOT / "scripts"
OUT = ROOT / "results/ws26-classlane-factorial-diagnostic"
RECEIPTS = OUT / "receipts.jsonl"
LOCK = OUT / "controller.lock"
WATCHER_RELATIVE = "scripts/ws11_resource_watch.py"


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def record(event, **values):
    row = {"event": event, "utc": utc()}
    row.update(values)
    with RECEIPTS.open("a", encoding="utf-8") as target:
        target.write(json.dumps(row, sort_keys=True) + "\n")
        target.flush()
        os.fsync(target.fileno())


def watcher_first_sample(experiment_id):
    base_path = "/home/fnl/lzy/results/" + experiment_id + "/logs"
    source = "/home/fnl/lzy/runs/" + experiment_id + "/source/" + WATCHER_RELATIVE
    samples = base_path + "/resource-samples.jsonl"
    log = base_path + "/resource-watch.log"
    command = ("set -eu; test -d " + shlex.quote(base_path) + "; test ! -L " +
               shlex.quote(base_path) + "; test -f " + shlex.quote(source) +
               "; test ! -L " + shlex.quote(source) + "; test ! -e " +
               shlex.quote(samples) + "; nohup python3 " + shlex.quote(source) +
               " " + shlex.quote(experiment_id) + " --interval 5 > " +
               shlex.quote(log) + " 2>&1 < /dev/null & " +
               "for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do " +
               "test -s " + shlex.quote(samples) + " && break; sleep 1; done; head -n 1 " +
               shlex.quote(samples))
    output = base.ssh(command, timeout=30).strip()
    if not output:
        raise RuntimeError("Watcher failed to write first sample: " + experiment_id)
    record("watcher_first_sample", id=experiment_id, sample=output)
    return output


def verify_local(cell, plan):
    folder = ROOT / "results" / cell["id"]
    if not folder.exists():
        base.call("fetch", cell["id"], timeout=1800)
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    raw_log = folder / "raw" / str(metadata.get("raw_directory", "")) / "config.log"
    target_log = folder / "logs/config.log"
    if raw_log.is_symlink() or not raw_log.is_file():
        raise RuntimeError("Fetched raw config.log missing: " + cell["id"])
    if target_log.exists() or target_log.is_symlink():
        if (target_log.is_symlink() or not target_log.is_file() or
                verifier.digest(target_log) != verifier.digest(raw_log)):
            raise RuntimeError("Existing config.log differs from fetched raw")
    else:
        with raw_log.open("rb") as source, target_log.open("xb") as target:
            shutil.copyfileobj(source, target, 1024 * 1024)
    summary = verifier.check(cell, plan)
    return summary


def terminal_resource(experiment_id):
    path = "/home/fnl/lzy/results/" + experiment_id + "/logs/resource-summary.json"
    output = base.remote_python(
        "import os; p=%r; print(open(p).read() if os.path.isfile(p) else '')" % path)
    if not output:
        raise RuntimeError("Watcher terminal resource summary missing: " + experiment_id)
    resource = json.loads(output)
    record("resource_terminal", id=experiment_id, summary=resource)
    return resource


def process(cell, plan):
    experiment_id = cell["id"]
    state = base.status(experiment_id)
    paths = base.remote_paths([experiment_id])[experiment_id]
    local = ROOT / "results" / experiment_id
    if state is None and any(paths):
        raise RuntimeError("Remote ID path exists without metadata: " + experiment_id)
    if state is None and (local.exists() or local.is_symlink()):
        raise RuntimeError("Local result exists without remote state: " + experiment_id)
    if state is None:
        gate = base.resource_gate()
        record("resource_gate_before_build", id=experiment_id, resources=gate)
        base.call("build", "--repo-local", str(ROOT), "--source-sha", verifier.SOURCE_SHA,
                  "--id", experiment_id, "--label", "ws26-factorial-diagnostic",
                  timeout=6 * 60 * 60)
        state = base.status(experiment_id)
        if not state or state.get("status") != "BUILT":
            raise RuntimeError("Build did not reach BUILT: " + experiment_id)
        record("built", id=experiment_id, source_sha=verifier.SOURCE_SHA)
    elif state.get("status") == "BUILDING":
        state = base.wait_for_state(experiment_id, ("BUILT",), 60)
    if state.get("git_commit") != verifier.SOURCE_SHA:
        raise RuntimeError("Remote source SHA differs from frozen plan: " + experiment_id)
    if state.get("status") in ("FAILED", "BUILD_FAILED", "INTERRUPTED"):
        raise RuntimeError("Existing failed ID preserved: " + experiment_id)
    if state.get("status") == "SUCCEEDED":
        summary = verify_local(cell, plan)
        record("verified_reused", id=experiment_id, fct_sha256=summary["fct_sha256"])
        return summary
    if state.get("status") == "BUILT":
        base.copy_trace(cell)
        gate = base.resource_gate()
        record("resource_gate_before_run", id=experiment_id, resources=gate)
        first = watcher_first_sample(experiment_id)
        args = ["run", experiment_id, "--lb", cell["mode"], "--simul-time", "0.01",
                "--netload", "10", "--max-concurrent", "1", "--bw", "400",
                "--buffer", "9", "--topo", plan["topology"], "--cdf", "AliStorage2019",
                "--flow-file", "config/" + cell["trace"], "--pfc", "1", "--irn", "1",
                "--factorial-pilot", "--ws25-diag", "1", "--ws26-moe-hop-diag", "1",
                "--ws26-seed97-time-diag", str(cell["ws26_seed97_time_diag"])]
        base.call(*args, timeout=120)
        state = base.status(experiment_id)
        params = (state or {}).get("parameters", {})
        if (not state or state.get("status") not in ("RUNNING", "SUCCEEDED") or
                state.get("git_commit") != verifier.SOURCE_SHA or
                state.get("concurrency_cap") != 1 or
                params.get("lb") != cell["mode"] or
                params.get("flow_file") != cell["trace"] or
                params.get("ws26_seed97_time_diag") != cell["ws26_seed97_time_diag"]):
            raise RuntimeError("Run metadata differs from frozen cell: " + experiment_id)
        record("run_started", id=experiment_id, source_sha=verifier.SOURCE_SHA,
               trace_sha256=cell["trace_sha256"], pid=state.get("pid"), cap=1,
               watcher_first_sample=first)
    if state.get("status") == "RUNNING":
        interval = 30 if cell["stage"].startswith("smoke_") else 1800
        state = base.wait_for_state(experiment_id, ("SUCCEEDED",), interval)
    if state.get("status") != "SUCCEEDED":
        raise RuntimeError("Run ended in " + str(state.get("status")) + ": " + experiment_id)
    resource = terminal_resource(experiment_id)
    base.call("fetch", experiment_id, timeout=1800)
    summary = verify_local(cell, plan)
    record("verified", id=experiment_id, source_sha=verifier.SOURCE_SHA,
           trace_sha256=cell["trace_sha256"], fct_sha256=summary["fct_sha256"],
           completed_flows=summary["completed_flows"],
           peak_tree_rss_mib=resource["peak_tree_rss_mib"])
    print("verified " + experiment_id, flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-order", type=int, default=1)
    parser.add_argument("--through-order", type=int, default=10)
    args = parser.parse_args()
    if not (1 <= args.start_order <= args.through_order <= 10):
        parser.error("Order range must remain within the frozen ten cells")
    plan = verifier.load_plan()
    OUT.mkdir(parents=True, exist_ok=True)
    lock = base.ControllerLock(LOCK)
    try:
        lock.acquire()
    except OSError:
        lock.release()
        raise RuntimeError("Another WS-26 factorial controller is active")
    try:
        cells = plan["cells"]
        ids = [cell["id"] for cell in cells]
        remote = base.remote_preflight(ids)
        if remote["other_user_processes"] or remote["simulation_lock_held"]:
            raise RuntimeError("Remote preflight failed: " + json.dumps(remote))
        for experiment_id in remote["collisions"]:
            state = base.status(experiment_id)
            paths = base.remote_paths([experiment_id])[experiment_id]
            if (not state or state.get("git_commit") != verifier.SOURCE_SHA or
                    paths != (True, True) or state.get("status") not in
                    ("BUILT", "BUILDING", "RUNNING", "SUCCEEDED")):
                raise RuntimeError("Remote ID collision is not resumable: " + experiment_id)
        for cell in cells:
            path = ROOT / "results" / cell["id"]
            if (path.exists() or path.is_symlink()) and cell["id"] not in remote["collisions"]:
                raise RuntimeError("Local ID collision: " + cell["id"])
        gate = base.resource_gate()
        record("controller_started", plan_sha256=verifier.PLAN_SHA256,
               source_sha=verifier.SOURCE_SHA, start_order=args.start_order,
               through_order=args.through_order, cap=1, remote_preflight=remote,
               resources=gate, controller_sha256=verifier.digest(Path(__file__)))
        base.call("deploy", timeout=120)
        try:
            base.call("sync", "--repo-local", str(ROOT), timeout=1800)
        except RuntimeError:
            base.call("sync-bundle", "--repo-local", str(ROOT), timeout=1800)
        for cell in cells[args.start_order - 1:args.through_order]:
            try:
                process(cell, plan)
            except Exception as error:
                record("stopped", id=cell["id"], error=str(error),
                       next_cell_started=False)
                raise
        record("controller_stage_complete", through_order=args.through_order,
               plan_sha256=verifier.PLAN_SHA256, source_sha=verifier.SOURCE_SHA)
        print("factorial diagnostic verified through order " + str(args.through_order),
              flush=True)
    finally:
        lock.release()


if __name__ == "__main__":
    main()
