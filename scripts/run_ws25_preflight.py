#!/usr/bin/env python3
"""Run only the frozen 12-cell WS-25 correctness/resource preflight."""
import concurrent.futures
import datetime
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import verify_ws25_preflight as verifier
import remote_experiment as remote

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "scripts" / "remote_experiment.py"
COMMIT = verifier.COMMIT
MODES = verifier.MODES
MODE_CODES = verifier.MODE_CODE
PLAN_PATH = ROOT / "results" / "ws25-preflight-plan-v2.json"
RECEIPTS = ROOT / "results" / "ws25-preflight-receipts-v2.jsonl"
LOCK = threading.Lock()


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def command_output(value):
    # Keep subprocess pipes binary on Windows: a decoder failure in
    # communicate()'s reader thread can otherwise leave stdout as None.
    if value is None:
        return b""
    return value.encode("utf-8", errors="replace") if isinstance(value, str) else value


def preserve_command_error(args, output, **details):
    folder = ROOT / "results" / "controller-command-errors"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S") +
                     "-" + uuid.uuid4().hex + ".log")
    with path.open("xb") as stream:
        stream.write(command_output(output))
    receipt = dict(args=list(args), output=str(path.relative_to(ROOT)),
                   output_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), **details)
    with path.with_suffix(".json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
    return path


def command(*args):
    operation = args[0] if args else ""
    # Keep this wrapper longer than remote_experiment.worker_call's 1800 s
    # build/sync timeout. A shorter parent timeout kills only the controller
    # process on Windows and can leave its SSH child running in the background.
    timeout = 1900 if operation in ("build", "sync", "sync-bundle", "fetch") else 120
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    try:
        result = subprocess.run([sys.executable, str(CONTROLLER)] + list(args), cwd=str(ROOT),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                env=env, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        path = preserve_command_error(args, error.output, timeout_seconds=timeout)
        raise RuntimeError("controller timed out after %s seconds: %s; output retained: %s" %
                           (timeout, " ".join(args[:3]), path)) from error
    output = command_output(result.stdout)
    message = output.decode("utf-8", errors="replace")
    if result.returncode:
        path = preserve_command_error(args, output, returncode=result.returncode,
                                      output_missing=result.stdout is None)
        raise RuntimeError("controller failed (%s), exit %s; output retained: %s: %s" %
                           (" ".join(args[:3]), result.returncode, path, message[-1600:]))
    # Native SSH/SCP diagnostics may use a local code page. Preserve those
    # bytes, while only the diagnostic text receives replacement decoding.
    try:
        output.decode("utf-8")
    except UnicodeDecodeError:
        preserve_command_error(args, output, returncode=0, decoding="utf-8 replacement")
    return message


def status(experiment_id):
    message = command("status", experiment_id)
    start = message.index("{")
    return json.JSONDecoder().raw_decode(message[start:])[0]


def audit(reject_active=False):
    lines = command("check").splitlines()
    values = dict(line.split("=", 1) for line in lines if "=" in line)
    if (float(values["load_1m"]) > 20 or float(values["mem_available_gib"]) < 32 or
            float(values["free_gib"]) < 100 or
            (reject_active and values["active_simulation_pids"].strip())):
        raise RuntimeError("Host/worker resource gate failed: " + repr(values))
    return values


def append_receipt(event, cell, **details):
    item = {"event": event, "id": cell["id"], "phase": cell["phase"],
            "mode": cell["mode"], "utc": datetime.datetime.utcnow().isoformat() + "Z"}
    item.update(details)
    with LOCK:
        RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
        with RECEIPTS.open("a", encoding="utf-8") as output:
            output.write(json.dumps(item, sort_keys=True) + "\n")
            output.flush()


def plan():
    cells = []
    for i, mode in enumerate(MODES):
        cells.append({"id": "20261002-22300%d-ws25-v2-pre-%s" % (i, mode),
                      "phase": "pre", "mode": mode,
                      "trace": "ws25_preflight_seed20262501.txt",
                      "trace_sha256": verifier.PRE_TRACE_SHA})
    for i, mode in enumerate(MODES):
        cells.append({"id": "20261002-22400%d-ws25-v2-cal01-%s" % (i, mode),
                      "phase": "pilot", "mode": mode,
                      "trace": "ws25_seed20262501_b192.txt",
                      "trace_sha256": verifier.CAL192_SHA})
    result = {"source_sha": COMMIT, "topology_sha256": verifier.TOPO_SHA,
              "pfc": 0, "irn": 1, "bw_gbps": 400, "buffer_mib": 9,
              "ns3_seed": 1, "cells": cells}
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if PLAN_PATH.exists():
        assert PLAN_PATH.read_text(encoding="utf-8") == encoded, "Frozen plan differs"
    else:
        PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
        PLAN_PATH.write_text(encoded, encoding="utf-8")
    return cells


def start_watch(experiment_id):
    cfg = remote.config()
    base = "/home/fnl/lzy/results/" + experiment_id
    watch = "/home/fnl/lzy/.research-workflow/ws11_resource_watch.py"
    log = base + "/logs/resource-watch.log"
    path = base + "/logs/resource-samples.jsonl"
    code = ("import os,subprocess,time; base=%r; watch=%r; log=%r; sample=%r; "
            "assert os.path.realpath(base)==base and os.path.isdir(base); "
            "assert not os.path.islink(base) and os.path.isfile(watch) and not os.path.islink(watch); "
            "assert not os.path.lexists(sample); "
            "out=open(log,'ab'); p=subprocess.Popen(['nohup','python3',watch,%r], "
            "stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,start_new_session=True); "
            "time.sleep(1); assert os.path.isfile(sample) and not os.path.islink(sample); "
            "print('watcher_pid='+str(p.pid))") % (base, watch, log, path, experiment_id)
    subprocess.check_call(remote.ssh_base(cfg) + ["python3 -c " + shlex.quote(code)],
                          timeout=45)


def wait_watch(experiment_id):
    cfg = remote.config()
    path = "/home/fnl/lzy/results/%s/logs/resource-summary.json" % experiment_id
    code = ("import os,time; p=%r; "
            "[time.sleep(2) for _ in range(30) if not os.path.isfile(p)]; "
            "assert os.path.isfile(p) and not os.path.islink(p)") % path
    subprocess.check_call(remote.ssh_base(cfg) + ["python3 -c " + shlex.quote(code)],
                          timeout=120)


def fetch_config_log(cell, metadata):
    assert remote.ID_RE.fullmatch(cell["id"])
    raw_id = str(metadata["raw_directory"])
    assert raw_id.isdigit()
    folder = ROOT / "results" / cell["id"]
    destination = folder / "logs" / "config.log"
    source = folder / "raw" / raw_id / "config.log"
    assert destination.parent.resolve() == destination.parent and not destination.is_symlink()
    assert source.parent.resolve() == source.parent and not source.is_symlink()
    # Normal fetch already includes this immutable raw log. Recover the derived
    # logs/ copy locally, including after interruption between fetch and verify.
    if source.is_file():
        digest = file_sha256(source)
        if destination.exists():
            assert file_sha256(destination) == digest, "Existing config.log differs; retained"
            return
    else:
        cfg = remote.config()
        remote_path = "/home/fnl/lzy/results/%s/raw/%s/config.log" % (cell["id"], raw_id)
        code = ("import hashlib,os; p=%r; assert os.path.isfile(p) and os.path.realpath(p)==p; "
                "print(hashlib.sha256(open(p,'rb').read()).hexdigest())") % remote_path
        digest = subprocess.check_output(remote.ssh_base(cfg) + ["python3 -c " + shlex.quote(code)],
                                         encoding="utf-8", errors="replace", timeout=45).strip()
        assert len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)
        if destination.exists():
            assert file_sha256(destination) == digest, "Existing config.log differs; retained"
            return
    staging = destination.with_name(".incoming-config-" + uuid.uuid4().hex + ".log")
    if source.is_file():
        with source.open("rb") as origin, staging.open("xb") as target:
            shutil.copyfileobj(origin, target)
    else:
        args = ["scp", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=15",
                "-o", "ServerAliveCountMax=2", "-o", "ClearAllForwardings=yes",
                cfg["REMOTE_USER"] + "@" + cfg["REMOTE_HOST"] + ":" + remote_path, str(staging)]
        try:
            result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
        except subprocess.TimeoutExpired as error:
            path = preserve_command_error(args, error.output, timeout_seconds=600, staging=str(staging))
            raise RuntimeError("config.log transfer timed out; staging and output retained: " + str(path)) from error
        if result.returncode:
            path = preserve_command_error(args, result.stdout, returncode=result.returncode, staging=str(staging))
            raise RuntimeError("config.log transfer failed; staging and output retained: " + str(path))
    assert file_sha256(staging) == digest, "Transferred config.log hash mismatch; staging retained"
    # Hard-link publication is atomic and refuses an existing destination on
    # both Windows and POSIX. Remove only this call's new temporary name.
    os.link(staging, destination)
    staging.unlink()


def run_cell(cell, cap, poll_seconds):
    experiment_id, mode = cell["id"], cell["mode"]
    local = ROOT / "results" / experiment_id
    if local.is_dir():
        result = verifier.verify(experiment_id, cell["phase"], mode)
        existing = []
        if RECEIPTS.exists():
            existing = [json.loads(line) for line in RECEIPTS.read_text(encoding="utf-8").splitlines()
                        if line]
        if not any(item.get("event") == "verified" and item.get("id") == experiment_id
                   for item in existing):
            append_receipt("verified", cell, fct_sha256=result["fct_sha256"],
                           config_log_sha256=result["config_log_sha256"],
                           resource=result["resource"])
        return result
    audit()
    try:
        state = status(experiment_id)
    except RuntimeError as error:
        if "metadata.json" not in str(error) and "No such file" not in str(error):
            raise
        started = time.monotonic()
        audit()
        output = command("build", "--repo-local", str(ROOT), "--id", experiment_id,
                         "--source-sha", COMMIT, "--label", "ws25-" + cell["phase"] + "-" + mode)
        state = status(experiment_id)
        append_receipt("built", cell, status=state["status"],
                       build_wall_seconds=round(time.monotonic() - started, 2),
                       build_output=output.strip()[-300:])
    if state.get("git_commit") != COMMIT:
        raise RuntimeError("Source SHA mismatch for " + experiment_id)
    if state.get("status") == "BUILT":
        audit()
        start_watch(experiment_id)
        args = ["run", experiment_id, "--lb", mode, "--pfc", "0", "--irn", "1",
                "--bw", "400", "--buffer", "9", "--topo", "topo_1280_400G_400G_OS1",
                "--flow-file", cell["trace"], "--simul-time", "0.01", "--netload", "10",
                "--max-concurrent", str(cap)]
        command(*args)
        append_receipt("started", cell, cap=cap)
        state = status(experiment_id)
    elif state.get("status") == "RUNNING":
        state = status(experiment_id)
    while state.get("status") == "RUNNING":
        time.sleep(poll_seconds)
        state = status(experiment_id)
        try:
            audit()
        except RuntimeError as error:
            append_receipt("resource_stop", cell, error=str(error))
            # Keep the current isolated run intact; the caller stops new cells.
            raise
    if state.get("status") != "SUCCEEDED":
        raise RuntimeError("Experiment did not succeed: %s %s" % (experiment_id, state))
    wait_watch(experiment_id)
    command("fetch", experiment_id)
    with (local / "metadata.json").open(encoding="utf-8") as source:
        metadata = json.load(source)
    fetch_config_log(cell, metadata)
    result = verifier.verify(experiment_id, cell["phase"], mode)
    append_receipt("verified", cell, fct_sha256=result["fct_sha256"],
                   config_log_sha256=result["config_log_sha256"], resource=result["resource"])
    return result


def execute_phase(cells, phase, parallel_after=0):
    selected = [c for c in cells if c["phase"] == phase]
    existing = []
    if RECEIPTS.exists():
        existing = [json.loads(x) for x in RECEIPTS.read_text(encoding="utf-8").splitlines() if x]
    done = {x["id"] for x in existing if x["event"] == "verified"}
    selected = [c for c in selected if c["id"] not in done]
    done_in_phase = {x["id"] for x in existing
                     if x["event"] == "verified" and x["phase"] == phase}
    # Resource escalation: two cells at cap=1, then pairs at cap=2.
    if phase == "pre":
        for c in selected:
            result = run_cell(c, 1 if len(done_in_phase) < 2 else 2, 180)
            done.add(c["id"])
            done_in_phase.add(c["id"])
            print(json.dumps({"verified": c["id"], "phase": phase,
                              "completion_rate": "all flows", "resource": result["resource"]},
                             sort_keys=True), flush=True)
        return
    serial = selected[:max(0, 2 - len(done_in_phase))]
    for c in serial:
        result = run_cell(c, 1, 600)
        done.add(c["id"])
        done_in_phase.add(c["id"])
        print(json.dumps({"verified": c["id"], "phase": phase, "cap": 1,
                          "resource": result["resource"]}, sort_keys=True), flush=True)
    rest = [c for c in selected if c["id"] not in done]
    for offset in range(0, len(rest), 2):
        group = rest[offset:offset + 2]
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(group)) as pool:
            futures = [pool.submit(run_cell, c, 2, 600) for c in group]
            errors = []
            for c, future in zip(group, futures):
                try:
                    result = future.result()
                    done.add(c["id"])
                    print(json.dumps({"verified": c["id"], "phase": phase, "cap": 2,
                                      "resource": result["resource"]}, sort_keys=True), flush=True)
                except Exception as error:
                    errors.append((c["id"], str(error)))
        if errors:
            raise RuntimeError("Pilot group stopped; preserve current IDs: " + repr(errors))


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("plan", "pre", "pilot"))
    args = parser.parse_args()
    cells = plan()
    if args.phase == "plan":
        print(json.dumps({"source_sha": COMMIT, "cells": cells}, indent=2, sort_keys=True))
        return
    audit(reject_active=True)
    if args.phase == "pre":
        execute_phase(cells, "pre")
    else:
        # Correctness must be fully verified before any 192-cell launch.
        pre_ids = [c["id"] for c in cells if c["phase"] == "pre"]
        verified = set()
        if RECEIPTS.exists():
            verified = {x["id"] for x in
                        (json.loads(line) for line in RECEIPTS.read_text(encoding="utf-8").splitlines() if line)
                        if x["event"] == "verified"}
        if not set(pre_ids).issubset(verified):
            raise RuntimeError("All six correctness cells must pass before the calibration pilot")
        execute_phase(cells, "pilot")


if __name__ == "__main__":
    main()
