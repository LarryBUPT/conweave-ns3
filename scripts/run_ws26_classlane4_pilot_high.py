#!/usr/bin/env python3
"""Run the frozen ClassLane v4 r2 high stage serially with recovery receipts."""

import datetime
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import remote_experiment as remote
import verify_ws26_classlane4_pilot as verifier


PLAN = verifier.PLAN
SOURCE_SHA = verifier.SOURCE_SHA
TOPOLOGY = verifier.TOPOLOGY
OUT = ROOT / "results" / "ws26-classlane4-independent-pilot-r2"
RECEIPTS = OUT / "receipts.jsonl"
LOCK = OUT / "controller.lock"
WATCHER_RELATIVE = "scripts/ws11_resource_watch.py"


class ControllerLock:
    """Hold one byte on Windows or an advisory flock on POSIX."""

    def __init__(self, path):
        self.stream = path.open("a+b")
        self.locked = False

    def acquire(self):
        if os.name == "nt":
            self.stream.seek(0, os.SEEK_END)
            if self.stream.tell() == 0:
                self.stream.write(b"0")
                self.stream.flush()
            self.stream.seek(0)
            msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.locked = True

    def release(self):
        if self.locked:
            if os.name == "nt":
                self.stream.seek(0)
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
            self.locked = False
        self.stream.close()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def record(event, **values):
    row = {"event": event, "utc": utc()}
    row.update(values)
    with RECEIPTS.open("a", encoding="utf-8") as target:
        target.write(json.dumps(row, sort_keys=True) + "\n")
        target.flush()
        os.fsync(target.fileno())


def call(*args, timeout=3600):
    command = [sys.executable, str(SCRIPTS / "remote_experiment.py"), *args]
    result = subprocess.run(command, cwd=str(ROOT), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError("remote command failed: " + " ".join(args[:3]) +
                           "\n" + result.stdout[-2500:])
    return result.stdout


def ssh(command, timeout=60):
    return subprocess.check_output(remote.ssh_base(remote.config()) + [command],
                                   stderr=subprocess.STDOUT, timeout=timeout).decode("utf-8")


def remote_python(source, timeout=60):
    command = "python3 -c " + shlex.quote("exec(" + repr(source) + ")")
    return ssh(command, timeout=timeout).strip()


def status(experiment_id):
    try:
        output = call("status", experiment_id, timeout=60)
    except RuntimeError as error:
        if "REMOTE_METADATA_MISSING:" in str(error):
            return None
        raise
    start = output.find("{")
    if start < 0:
        raise RuntimeError("Remote status has no metadata: " + experiment_id)
    return json.JSONDecoder().raw_decode(output[start:])[0]


def resource_gate():
    output = call("check", timeout=60)
    values = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    code = r'''import fcntl,json,os,subprocess
ps=subprocess.check_output(['ps','-eo','uid,stat,comm','--no-headers']).decode('utf-8','replace')
own=os.getuid(); other=0
for line in ps.splitlines():
 c=line.split(None,2)
 if len(c)==3 and int(c[0])>=1000 and int(c[0])!=own and not c[1].startswith('Z'):
  other+=1
lock='/home/fnl/lzy/.research-workflow/simulation-start.lock'; held=False
if os.path.lexists(lock):
 if os.path.islink(lock): raise RuntimeError('simulation lock is a symlink')
 fd=os.open(lock,os.O_RDWR)
 try:
  try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError: held=True
  else: fcntl.flock(fd,fcntl.LOCK_UN)
 finally: os.close(fd)
print(json.dumps({'other_user_processes':other,'simulation_lock_held':held}))'''
    probe = remote_python(code)
    extra = json.loads(probe)
    gate = {
        "load_1m": float(values["load_1m"]),
        "mem_available_gib": float(values["mem_available_gib"]),
        "free_gib": float(values["free_gib"]),
        "active_simulation_pids": values["active_simulation_pids"].strip(),
        "other_user_processes": extra["other_user_processes"],
        "simulation_lock_held": extra["simulation_lock_held"],
    }
    if (gate["load_1m"] > 20 or gate["mem_available_gib"] < 32 or
            gate["free_gib"] < 100 or gate["active_simulation_pids"] or
            gate["other_user_processes"] or gate["simulation_lock_held"]):
        raise RuntimeError("Resource admission failed: " + json.dumps(gate, sort_keys=True))
    return gate


def remote_paths(ids):
    source = ("import json,os; ids=json.loads(" + repr(json.dumps(ids)) + "); "
              "root='/home/fnl/lzy'; "
              "[print(i+' results='+str(os.path.lexists(os.path.join(root,'results',i)))"
              "+' runs='+str(os.path.lexists(os.path.join(root,'runs',i)))) for i in ids]")
    output = remote_python(source)
    rows = {}
    for line in output.splitlines():
        if " results=" not in line or " runs=" not in line:
            continue
        experiment_id, rest = line.split(" results=", 1)
        results_flag, runs_flag = rest.split(" runs=", 1)
        rows[experiment_id] = (results_flag == "True", runs_flag == "True")
    if len(rows) != len(ids):
        raise RuntimeError("Remote ID audit returned an incomplete result")
    return rows


def audit_plan_ids():
    ids = [cell["id"] for cell in PLAN["cells"]]
    state = remote_paths(ids)
    record("remote_id_audit", revision="r2", checked=len(ids),
           collisions=[key for key, value in state.items() if any(value)])
    return state


def copy_trace_overlay(cell):
    cfg = remote.config()
    destination = ("/home/fnl/lzy/runs/" + cell["id"] + "/source/config/" +
                   cell["trace"])
    remote_id = cfg["REMOTE_USER"] + "@" + cfg["REMOTE_HOST"] + ":" + destination
    source = ROOT / "config" / cell["trace"]
    if hashlib.sha256(source.read_bytes()).hexdigest() != cell["trace_sha256"]:
        raise RuntimeError("Local trace changed before transfer: " + cell["trace"])
    probe = "import os; p=%r; print('present' if os.path.lexists(p) else 'absent')" % destination
    exists = remote_python(probe)
    if exists == "absent":
        subprocess.check_call([
            "scp", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "ConnectTimeout=10", "--", str(source), remote_id,
        ], cwd=str(ROOT), timeout=180)
    elif exists != "present":
        raise RuntimeError("Could not determine remote trace state: " + cell["id"])

    relative = "config/" + cell["trace"]
    verify = r'''import hashlib,json,os,subprocess,sys
repo,relative,expected=sys.argv[1:]
path=os.path.join(repo,relative)
if os.path.islink(path) or not os.path.isfile(path): raise RuntimeError('trace is not regular')
actual=hashlib.sha256(open(path,'rb').read()).hexdigest()
if actual!=expected: raise RuntimeError('trace hash mismatch')
exclude=os.path.join(repo,'.git','info','exclude')
if os.path.islink(exclude): raise RuntimeError('exclude is a symlink')
text=open(exclude,encoding='utf-8').read() if os.path.isfile(exclude) else ''
if relative not in text.splitlines():
 with open(exclude,'a',encoding='utf-8') as f:
  if text and not text.endswith('\n'): f.write('\n')
  f.write(relative+'\n')
status=subprocess.check_output(['git','-C',repo,'status','--porcelain']).decode().strip()
if status: raise RuntimeError('source worktree became dirty: '+status)
print(json.dumps({'path':relative,'sha256':actual,'git_status_clean':True}))'''
    command = "python3 -c " + shlex.quote(verify) + " " + shlex.quote(
        "/home/fnl/lzy/runs/" + cell["id"] + "/source") + " " + shlex.quote(
        relative) + " " + cell["trace_sha256"]
    result = ssh(command, timeout=60)
    receipt = json.loads(result.strip())
    if receipt.get("sha256") != cell["trace_sha256"] or not receipt.get("git_status_clean"):
        raise RuntimeError("Remote trace overlay verification failed: " + cell["id"])
    record("trace_overlay_verified", id=cell["id"], trace=cell["trace"],
           trace_sha256=receipt["sha256"], fixed_source_sha=SOURCE_SHA)
    return receipt


def watcher_sample(experiment_id):
    base = "/home/fnl/lzy/results/" + experiment_id + "/logs"
    source = "/home/fnl/lzy/runs/" + experiment_id + "/source/" + WATCHER_RELATIVE
    samples = base + "/resource-samples.jsonl"
    log = base + "/resource-watch.log"
    command = (
        "set -eu; test -d " + shlex.quote(base) + "; test ! -L " + shlex.quote(base) + "; "
        "test -f " + shlex.quote(source) + "; test ! -L " + shlex.quote(source) + "; "
        "if test -s " + shlex.quote(samples) + "; then echo existing_sample; "
        "else test ! -e " + shlex.quote(samples) + "; nohup python3 " +
        shlex.quote(source) + " " + shlex.quote(experiment_id) +
        " --interval 5 > " + shlex.quote(log) + " 2>&1 < /dev/null & "
        "for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do "
        "test -s " + shlex.quote(samples) + " && { echo first_sample_ready; break; }; sleep 1; done; "
        "test -s " + shlex.quote(samples) + "; fi; head -n 1 " + shlex.quote(samples))
    first = ssh(command, timeout=30).strip()
    if not first:
        raise RuntimeError("Watcher first sample missing: " + experiment_id)
    record("watcher_first_sample", id=experiment_id, sample=first)
    return first


def wait_for_state(experiment_id, target_statuses, interval_seconds=1800, timeout_hours=6):
    deadline = time.time() + timeout_hours * 3600
    while time.time() < deadline:
        time.sleep(interval_seconds)
        state = status(experiment_id)
        if state is None:
            raise RuntimeError("Remote metadata disappeared: " + experiment_id)
        current = state.get("status")
        if current in target_statuses:
            return state
        if current == "RUNNING" and state.get("process_alive") is False:
            raise RuntimeError("Remote worker stopped without terminal metadata: " + experiment_id)
        if current in ("FAILED", "BUILD_FAILED", "INTERRUPTED"):
            return state
    raise RuntimeError("Timed out waiting for remote state: " + experiment_id)


def run_args(cell):
    args = ["run", cell["id"], "--lb", cell["mode"], "--simul-time", "0.01",
            "--netload", "10", "--max-concurrent", "1", "--bw", "400", "--buffer", "9",
            "--topo", TOPOLOGY, "--cdf", "AliStorage2019", "--flow-file",
            "config/" + cell["trace"], "--pfc", "1", "--irn", "1", "--factorial-pilot"]
    if cell["ws25_diag"]:
        args.extend(["--ws25-diag", "1"])
    return args


def ensure_config_log(cell, meta):
    folder = ROOT / "results" / cell["id"]
    raw_id = str(meta.get("raw_directory", ""))
    if not raw_id.isdigit():
        raise RuntimeError("Invalid raw ID: " + cell["id"])
    raw_log = folder / "raw" / raw_id / "config.log"
    target = folder / "logs" / "config.log"
    if raw_log.is_symlink() or not raw_log.is_file():
        raise RuntimeError("Fetched raw config.log missing: " + cell["id"])
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_file() or digest(target) != digest(raw_log):
            raise RuntimeError("Refusing to overwrite mismatched config.log: " + cell["id"])
    else:
        with raw_log.open("rb") as source, target.open("xb") as destination:
            shutil.copyfileobj(source, destination)
    return digest(target)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_local(cell):
    folder = ROOT / "results" / cell["id"]
    if not folder.exists():
        call("fetch", cell["id"], timeout=1800)
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    config_log_sha = ensure_config_log(cell, meta)
    output = subprocess.run([
        sys.executable, str(SCRIPTS / "verify_ws26_classlane4_pilot.py"),
        "--id", cell["id"],
    ], cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if output.returncode:
        raise RuntimeError("Cell verification failed for " + cell["id"] + ": " +
                           output.stdout[-2500:])
    result = json.loads(output.stdout[output.stdout.find("{"):])
    summary = result["cells"][0]
    summary["config_log_sha256"] = config_log_sha
    receipt_path = OUT / (cell["id"] + ".verified.json")
    if receipt_path.exists():
        old = json.loads(receipt_path.read_text(encoding="utf-8"))
        if old != summary:
            raise RuntimeError("Existing verified receipt differs: " + cell["id"])
    else:
        receipt_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                                encoding="utf-8")
    return summary


def process(cell):
    experiment_id = cell["id"]
    state = status(experiment_id)
    paths = remote_paths([experiment_id]).get(experiment_id)
    if paths is None:
        raise RuntimeError("Remote ID audit did not return the cell: " + experiment_id)
    if state is None and any(paths):
        raise RuntimeError("Remote directory exists without usable metadata: " + experiment_id)
    local = ROOT / "results" / experiment_id
    if state is None and (local.exists() or local.is_symlink()):
        raise RuntimeError("Local result exists without remote state; inspect it manually: " + experiment_id)

    if state is None:
        gate = resource_gate()
        record("resource_gate_before_build", id=experiment_id, resources=gate)
        output = call("build", "--repo-local", str(ROOT), "--source-sha", SOURCE_SHA,
                      "--id", experiment_id, "--label", "ws26-classlane4-pilot-r2",
                      timeout=6 * 60 * 60)
        state = status(experiment_id)
        if (not state or state.get("status") != "BUILT" or
                state.get("git_commit") != SOURCE_SHA):
            raise RuntimeError("Build identity mismatch: " + experiment_id + "\n" + output[-1800:])
        record("built", id=experiment_id, source_sha=state.get("git_commit"),
               build_finished_utc=state.get("build_finished_utc"))
    elif state.get("status") == "BUILDING":
        state = wait_for_state(experiment_id, ("BUILT",), interval_seconds=1800)

    if state.get("git_commit") != SOURCE_SHA:
        raise RuntimeError("Remote source SHA mismatch: " + experiment_id)
    if state.get("status") in ("FAILED", "BUILD_FAILED", "INTERRUPTED"):
        raise RuntimeError("Preserving terminal failure: " + experiment_id + " " +
                           str(state.get("status")))

    if state.get("status") == "SUCCEEDED":
        summary = verify_local(cell)
        record("verified_reused", id=experiment_id, fct_sha256=summary["fct_sha256"])
        return summary

    if state.get("status") == "BUILT":
        copy_trace_overlay(cell)
        gate = resource_gate()
        record("resource_gate_before_run", id=experiment_id, resources=gate)
        first_sample = watcher_sample(experiment_id)
        run_output = call(*run_args(cell), timeout=120)
        started = status(experiment_id)
        if (not started or started.get("status") not in ("RUNNING", "SUCCEEDED") or
                started.get("git_commit") != SOURCE_SHA or
                started.get("parameters", {}).get("ws25_diag") != cell["ws25_diag"] or
                started.get("parameters", {}).get("flow_file") != cell["trace"] or
                started.get("concurrency_cap") != 1):
            raise RuntimeError("Run metadata does not match frozen cell: " + experiment_id +
                               "\n" + run_output[-1800:])
        record("run_started", id=experiment_id, source_sha=SOURCE_SHA,
               trace_sha256=cell["trace_sha256"], pid=started.get("pid"), cap=1,
               watcher_first_sample=first_sample)
        print("started %s" % experiment_id, flush=True)
        if started.get("status") == "RUNNING":
            state = wait_for_state(experiment_id, ("SUCCEEDED",), interval_seconds=1800)
        else:
            state = started
    elif state.get("status") == "RUNNING":
        record("resumed_running", id=experiment_id, pid=state.get("pid"))
        state = wait_for_state(experiment_id, ("SUCCEEDED",), interval_seconds=1800)

    if state.get("status") != "SUCCEEDED":
        record("remote_terminal_failure", id=experiment_id, status=state.get("status"))
        raise RuntimeError("Run ended in " + str(state.get("status")) + ": " + experiment_id)

    resource_path = "/home/fnl/lzy/results/" + experiment_id + "/logs/resource-summary.json"
    summary_text = remote_python("import os; p=%r; "
                                 "print(open(p,encoding='utf-8').read() if os.path.isfile(p) else '')" %
                                 resource_path, timeout=60)
    if not summary_text:
        raise RuntimeError("Watcher terminal summary missing: " + experiment_id)
    resource_summary = json.loads(summary_text)
    record("resource_terminal", id=experiment_id, summary=resource_summary)
    call("fetch", experiment_id, timeout=1800)
    summary = verify_local(cell)
    record("verified", id=experiment_id, source_sha=SOURCE_SHA,
           trace_sha256=cell["trace_sha256"], fct_sha256=summary["fct_sha256"],
           route=summary["route"], resource_samples=summary["resource_samples"],
           peak_tree_rss_mib=summary["peak_tree_rss_mib"])
    print("verified %s" % experiment_id, flush=True)
    return summary


def main():
    verifier.check_plan()
    rows = [cell for cell in PLAN["cells"] if cell["stage"] == "high"]
    if len(rows) != 28 or PLAN.get("source_sha") != SOURCE_SHA:
        raise RuntimeError("Frozen high-stage plan changed")
    OUT.mkdir(parents=True, exist_ok=True)
    lock = ControllerLock(LOCK)
    try:
        lock.acquire()
    except OSError:
        lock.release()
        raise RuntimeError("Another ClassLane v4 r2 controller is active")
    try:
        audit = audit_plan_ids()
        collisions = [experiment_id for experiment_id, paths in audit.items()
                      if any(paths) and status(experiment_id) is None]
        if collisions:
            raise RuntimeError("Remote paths lack usable metadata: " + ",".join(collisions))
        record("controller_started", stage="high", planned_cells=28,
               source_sha=SOURCE_SHA, cap=1,
               runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               model_switch_required="GPT-6 Luna High before long-run supervision")
        verified = set()
        if RECEIPTS.exists():
            for line in RECEIPTS.read_text(encoding="utf-8").splitlines():
                event = json.loads(line)
                if event.get("event") in ("verified", "verified_reused"):
                    verified.add(event["id"])
        for index, cell in enumerate(rows, 1):
            if cell["id"] in verified:
                summary = verify_local(cell)
                print("[%d/28] already verified %s" % (index, cell["id"]), flush=True)
                continue
            try:
                process(cell)
            except Exception as error:
                record("stopped", id=cell["id"], error=str(error),
                       verified_before=len(verified), planned_high=28,
                       next_cell_started=False)
                raise
            verified.add(cell["id"])
            progress = {"stage": "high", "verified": len(verified), "planned": 28,
                        "current_id": cell["id"], "updated_utc": utc()}
            (OUT / "progress.json").write_text(
                json.dumps(progress, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print("[%d/28] accepted %s" % (index, cell["id"]), flush=True)
        output = subprocess.run([
            sys.executable, str(SCRIPTS / "verify_ws26_classlane4_pilot.py"),
            "--stage", "high",
        ], cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if output.returncode:
            raise RuntimeError("High stage aggregate verification failed: " + output.stdout[-2500:])
        high_path = OUT / "high-verified.json"
        if high_path.exists():
            previous = json.loads(high_path.read_text(encoding="utf-8"))
            if previous != json.loads(output.stdout[output.stdout.find("{"):]):
                raise RuntimeError("Existing high verification receipt differs")
        else:
            high_path.write_text(output.stdout[output.stdout.find("{"):], encoding="utf-8")
        record("high_stage_verified", count=28, output_sha256=digest(high_path))
        print("HIGH_STAGE_VERIFIED 28/28", flush=True)
    finally:
        lock.release()


if __name__ == "__main__":
    main()
