#!/usr/bin/env python3
"""Run only the frozen WS-25 DestSpread correctness IDs with safe recovery."""
import concurrent.futures
import datetime
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import remote_experiment as remote
import run_ws25_preflight as base
import verify_ws25_v2_correctness as verifier

ROOT = Path(__file__).resolve().parents[1]
RECEIPTS = ROOT / "results" / "ws25-v2-correctness-receipts.jsonl"
LOCK = threading.Lock()
ADMISSION_LOCK = threading.Lock()
TRANSPORT_LOCK = threading.Lock()


def receipt(event, cell, **details):
    item = {"event": event, "id": cell[0], "mode": cell[1], "trace": cell[2],
            "utc": datetime.datetime.utcnow().isoformat() + "Z"}
    item.update(details)
    with LOCK:
        RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
        with RECEIPTS.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(item, sort_keys=True) + "\n")
            stream.flush()


def host_gate(reject_active=False):
    with TRANSPORT_LOCK:
        values = base.audit(reject_active=reject_active)
        if float(values["mem_available_gib"]) - 4 * 5 < 32:
            raise RuntimeError("Projected memory below 32 GiB for cap=4")
        cfg = remote.config()
        process = subprocess.run(remote.ssh_base(cfg) + ["ps -eo user=,stat=,comm="],
                                 capture_output=True, text=True, timeout=45, check=True)
    others = []
    for line in process.stdout.splitlines():
        fields = line.split()
        if len(fields) < 3 or fields[0] in ("root", "fnl", "USER", "user"):
            continue
        if fields[0] in ("_chrony", "daemon", "messagebus", "syslog"):
            continue
        if fields[1].startswith("Z"):
            continue
        others.append(line)
    if others:
        raise RuntimeError("Other user processes; no new cell: " + repr(others[:8]))
    return values


def status(experiment_id):
    # The older status SSH has occasionally printed metadata and then waited
    # for channel closure. A short stdin script gives one bounded, read-only
    # metadata/PID observation and never converts an observation timeout into
    # permission to build or rerun the same ID.
    script = ("import json,os\n"
              "i=%r\n"
              "base='/home/fnl/lzy/results/'+i\n"
              "path=base+'/metadata.json'\n"
              "if not os.path.isfile(path):\n"
              " print('REMOTE_METADATA_MISSING:'+i)\n"
              " raise SystemExit(3)\n"
              "assert not os.path.islink(base) and not os.path.islink(path)\n"
              "data=json.load(open(path))\n"
              "if data.get('status')=='RUNNING':\n"
              " pid=data.get('pid')\n"
              " try: os.kill(pid,0)\n"
              " except OSError: raise RuntimeError('RUNNING worker PID missing')\n"
              "print('STATUS_JSON:'+json.dumps(data,sort_keys=True))\n") % experiment_id
    with TRANSPORT_LOCK:
        cfg = remote.config()
        observed = subprocess.run(remote.ssh_base(cfg) + ["python3", "-"],
                                  input=script, capture_output=True, text=True, timeout=45)
    lines = observed.stdout.splitlines()
    if observed.returncode == 3 and any("REMOTE_METADATA_MISSING:" + experiment_id in line
                                        for line in lines):
        raise RuntimeError("REMOTE_METADATA_MISSING: " + experiment_id)
    if observed.returncode:
        raise RuntimeError("Read-only status failed for %s: %s" %
                           (experiment_id, (observed.stdout + observed.stderr)[-1200:]))
    records = [line[len("STATUS_JSON:"):] for line in lines if line.startswith("STATUS_JSON:")]
    if len(records) != 1:
        raise RuntimeError("Read-only status marker absent: " + experiment_id)
    return json.loads(records[0])


def run_cell(cell, cap):
    experiment_id, mode, trace = cell
    local = ROOT / "results" / experiment_id
    if local.is_dir():
        result = verifier.verify(*cell)
        receipt("verified_existing", cell, fct_sha256=result["fct_sha256"])
        return result
    try:
        state = status(experiment_id)
    except RuntimeError as error:
        if "REMOTE_METADATA_MISSING" not in str(error):
            raise
        base.command("build", "--repo-local", str(ROOT), "--id", experiment_id,
                     "--source-sha", verifier.SHA)
        state = status(experiment_id)
        receipt("built", cell, status=state["status"])
    if state["git_commit"] != verifier.SHA:
        raise RuntimeError("Wrong fixed source SHA: " + experiment_id)
    if state["status"] == "BUILT":
        # Build requests may run in parallel, but admission uses serial SSH
        # checks. Concurrent read probes have previously left SSH clients
        # waiting after the server had already returned its response.
        with ADMISSION_LOCK:
            host_gate()
            with TRANSPORT_LOCK:
                base.start_watch(experiment_id)
                base.command("run", experiment_id, "--lb", mode, "--pfc", "0", "--irn", "1",
                             "--bw", "400", "--buffer", "9", "--topo",
                             "topo_1280_400G_400G_OS1", "--flow-file", trace,
                             "--simul-time", "0.01", "--netload", "10", "--max-concurrent",
                             str(cap), "--ws25-diag", "0")
            receipt("started", cell, cap=cap)
            state = status(experiment_id)
    elif state["status"] not in ("RUNNING", "SUCCEEDED"):
        raise RuntimeError("Unexpected state for %s: %s" % (experiment_id, state["status"]))
    while state["status"] == "RUNNING":
        time.sleep(90)
        state = status(experiment_id)
        with TRANSPORT_LOCK:
            base.audit()
    if state["status"] != "SUCCEEDED":
        raise RuntimeError("Terminal failure; preserve ID %s: %s" %
                           (experiment_id, state["status"]))
    with TRANSPORT_LOCK:
        base.wait_watch(experiment_id)
        base.command("fetch", experiment_id)
    meta = json.loads((local / "metadata.json").read_text(encoding="utf-8"))
    with TRANSPORT_LOCK:
        base.fetch_config_log({"id": experiment_id}, meta)
    result = verifier.verify(*cell)
    receipt("verified", cell, cap=cap, fct_sha256=result["fct_sha256"],
            resource=result["resource"])
    print(json.dumps({"verified": experiment_id, "mode": mode}, sort_keys=True), flush=True)
    return result


def group(cells, cap):
    host_gate(reject_active=True)
    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(cells)) as pool:
        futures = {pool.submit(run_cell, cell, cap): cell for cell in cells}
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as error:
                errors.append((futures[future][0], str(error)))
    if errors:
        raise RuntimeError("Stop before expanding; preserve IDs: " + repr(errors))
    host_gate(reject_active=True)


def main():
    if len(sys.argv) != 1:
        raise SystemExit("Frozen protocol has no runtime overrides")
    first = verifier.CELLS[0]
    if not (ROOT / "results" / first[0]).is_dir():
        raise RuntimeError("First candidate cell must be separately verified before expansion")
    verifier.verify(*first)
    receipt("verified_existing", first)
    pending = verifier.CELLS[1:]
    for start in range(0, len(pending), 4):
        group(pending[start:start + 4], 4)
    verifier.main()
    print(json.dumps({"correctness_complete": True, "verified_cells": len(verifier.CELLS)}),
          flush=True)


if __name__ == "__main__":
    main()
