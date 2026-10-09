#!/usr/bin/env python3
"""Execute the frozen WS-26 MoE hop diagnostic serially with receipts."""

import datetime
import hashlib
import json
import os
import shlex
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
import verify_ws26_moe_hop_diagnostic as verifier

OUT = ROOT / "results" / "ws26-moe-hop-diagnostic"
RECEIPTS = OUT / "receipts.jsonl"
LOCK = OUT / "controller.lock"
SOURCE_SHA = verifier.SOURCE_SHA
PLAN_SHA256 = verifier.PLAN_SHA256
WATCHER_RELATIVE = "scripts/ws11_resource_watch.py"


class ControllerLock:
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
    result = subprocess.run([sys.executable, str(SCRIPTS / "remote_experiment.py"), *args],
                            cwd=str(ROOT), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError("remote command failed: " + " ".join(args[:3]) +
                           "\n" + result.stdout[-2500:])
    return result.stdout


def ssh(command, timeout=60):
    return subprocess.check_output(remote.ssh_base(remote.config()) + [command],
                                   stderr=subprocess.STDOUT, timeout=timeout).decode("utf-8")


def remote_python(source, timeout=60):
    return ssh("python3 -c " + shlex.quote("exec(" + repr(source) + ")"), timeout).strip()


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


def remote_preflight(ids):
    code = r'''import fcntl,json,os,subprocess
ids=json.loads(%r); root='/home/fnl/lzy'
ps=subprocess.check_output(['ps','-eo','uid,stat,comm,args','--no-headers']).decode('utf-8','replace')
own=os.getuid(); other=[]
for line in ps.splitlines():
 c=line.split(None,3)
 if len(c)==4 and int(c[0])>=1000 and int(c[0])!=own and not c[1].startswith('Z'): other.append(line)
lock=root+'/.research-workflow/simulation-start.lock'; held=False
if os.path.lexists(lock):
 if os.path.islink(lock): raise RuntimeError('simulation lock is a symlink')
 fd=os.open(lock,os.O_RDWR)
 try:
  try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError: held=True
  else: fcntl.flock(fd,fcntl.LOCK_UN)
 finally: os.close(fd)
collisions=[]
for i in ids:
 paths=[os.path.join(root,'results',i),os.path.join(root,'runs',i)]
 if any(os.path.lexists(p) for p in paths): collisions.append(i)
print(json.dumps({'other_user_processes':other,'simulation_lock_held':held,'collisions':collisions}))''' % json.dumps(ids)
    return json.loads(remote_python(code))


def resource_gate():
    output = call("check", timeout=60)
    values = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    result = {"load_1m": float(values["load_1m"]),
              "mem_available_gib": float(values["mem_available_gib"]),
              "free_gib": float(values["free_gib"]),
              "active_simulation_pids": values["active_simulation_pids"].strip()}
    extra = remote_preflight([])
    result.update({"other_user_processes": extra["other_user_processes"],
                   "simulation_lock_held": extra["simulation_lock_held"]})
    if (result["load_1m"] > 20 or result["mem_available_gib"] < 32 or
            result["free_gib"] < 100 or result["active_simulation_pids"] or
            result["other_user_processes"] or result["simulation_lock_held"]):
        raise RuntimeError("Resource admission failed: " + json.dumps(result, sort_keys=True))
    return result


def audit_paired_plain(cell):
    folder = ROOT / "results" / cell["paired_plain_id"]
    if folder.is_symlink() or not folder.is_dir():
        raise RuntimeError("Paired plain result missing: " + cell["paired_plain_id"])
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = metadata.get("parameters", {})
    if not (metadata.get("status") == "SUCCEEDED" and
            metadata.get("experiment_id") == cell["paired_plain_id"] and
            metadata.get("algorithm") == cell["mode"] and
            metadata.get("input_flow_sha256") == cell["trace_sha256"] and
            metadata.get("topology_sha256") == verifier.TOPOLOGY_SHA256 and
            params.get("lb") == cell["mode"] and params.get("flow_file") == cell["trace"] and
            params.get("topo") == "topo_1280_400G_400G_OS1" and
            params.get("pfc") == 1 and params.get("irn") == 1 and
            params.get("ws25_diag") == 0):
        raise RuntimeError("Paired plain metadata mismatch: " + cell["paired_plain_id"])
    trace = folder / "config" / "traffic_trace.txt"
    topology = folder / "config" / "topology.txt"
    if (digest_script(trace) != cell["trace_sha256"] or
            digest_script(topology) != verifier.TOPOLOGY_SHA256):
        raise RuntimeError("Paired plain input snapshot mismatch: " + cell["paired_plain_id"])
    fct = verifier.raw_fct(folder, metadata)
    sha = digest_script(fct)
    row = {"event": "paired_plain_fct_audit", "utc": utc(), "id": cell["id"],
           "paired_plain_id": cell["paired_plain_id"], "fct_sha256": sha,
           "trace_sha256": cell["trace_sha256"]}
    existing = []
    if RECEIPTS.is_file():
        existing = [json.loads(line) for line in RECEIPTS.read_text(encoding="utf-8").splitlines()]
    matches = [item for item in existing if item.get("event") == "paired_plain_fct_audit"
               and item.get("id") == cell["id"]]
    if matches and (len(matches) != 1 or matches[0].get("fct_sha256") != sha):
        raise RuntimeError("Frozen paired FCT audit changed: " + cell["id"])
    if not matches:
        record("paired_plain_fct_audit", id=cell["id"],
               paired_plain_id=cell["paired_plain_id"], fct_sha256=sha,
               trace_sha256=cell["trace_sha256"])
    return row


def remote_paths(ids):
    code = ("import json,os; ids=json.loads(" + repr(json.dumps(ids)) + "); "
            "root='/home/fnl/lzy'; "
            "[print(i+' '+str(os.path.lexists(os.path.join(root,'results',i)))+' '+"
            "str(os.path.lexists(os.path.join(root,'runs',i)))) for i in ids]")
    rows = {}
    for line in remote_python(code).splitlines():
        parts = line.split()
        if len(parts) == 3:
            rows[parts[0]] = (parts[1] == "True", parts[2] == "True")
    if len(rows) != len(ids):
        raise RuntimeError("Remote ID audit returned incomplete results")
    return rows


def wait_for_state(experiment_id, target, interval, timeout_hours=8):
    deadline = time.time() + timeout_hours * 3600
    while time.time() < deadline:
        time.sleep(interval)
        state = status(experiment_id)
        if state is None:
            raise RuntimeError("Remote metadata disappeared: " + experiment_id)
        if state.get("status") in target or state.get("status") in (
                "FAILED", "BUILD_FAILED", "INTERRUPTED"):
            return state
        if state.get("status") == "RUNNING" and state.get("process_alive") is False:
            raise RuntimeError("Remote worker stopped without terminal metadata: " + experiment_id)
    raise RuntimeError("Timed out waiting for remote state: " + experiment_id)


def copy_trace(cell):
    cfg = remote.config()
    remote_path = "/home/fnl/lzy/runs/" + cell["id"] + "/source/config/" + cell["trace"]
    result = remote_python("import os; p=%r; print('present' if os.path.lexists(p) else 'absent')" %
                           remote_path)
    local_trace = ROOT / "config" / cell["trace"]
    if hashlib.sha256(local_trace.read_bytes()).hexdigest() != cell["trace_sha256"]:
        raise RuntimeError("Local trace hash changed: " + cell["id"])
    if result == "absent":
        target = cfg["REMOTE_USER"] + "@" + cfg["REMOTE_HOST"] + ":" + remote_path
        subprocess.check_call(["scp", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                               "-o", "ConnectTimeout=10", "--", str(local_trace), target],
                              cwd=str(ROOT), timeout=180)
    elif result != "present":
        raise RuntimeError("Remote trace state unclear: " + cell["id"])
    verify = r'''import hashlib,os,subprocess,sys
repo,relative,want=sys.argv[1:]; p=os.path.join(repo,relative)
if os.path.islink(p) or not os.path.isfile(p): raise RuntimeError('trace is not regular')
got=hashlib.sha256(open(p,'rb').read()).hexdigest()
if got!=want: raise RuntimeError('trace hash mismatch')
exclude=os.path.join(repo,'.git','info','exclude')
text=open(exclude).read() if os.path.isfile(exclude) else ''
if relative not in text.splitlines():
 with open(exclude,'a') as f:
  if text and not text.endswith('\\n'): f.write('\\n')
  f.write(relative+'\\n')
status=subprocess.check_output(['git','-C',repo,'status','--porcelain']).decode().strip()
if status: raise RuntimeError('source became dirty: '+status)
print(json.dumps({'sha256':got,'clean':True}))'''
    relative = "config/" + cell["trace"]
    bootstrap = ("import sys; sys.argv=['',%r,%r,%r]; exec(%s)" %
                 ("/home/fnl/lzy/runs/" + cell["id"] + "/source",
                  relative, cell["trace_sha256"], repr(verify)))
    result = remote_python(bootstrap)
    receipt = json.loads(result)
    if receipt.get("sha256") != cell["trace_sha256"] or not receipt.get("clean"):
        raise RuntimeError("Remote trace overlay verification failed: " + cell["id"])


def watcher_first_sample(experiment_id):
    base = "/home/fnl/lzy/results/" + experiment_id + "/logs"
    source = "/home/fnl/lzy/runs/" + experiment_id + "/source/" + WATCHER_RELATIVE
    samples = base + "/resource-samples.jsonl"
    log = base + "/resource-watch.log"
    command = ("set -eu; test -d " + shlex.quote(base) + "; test ! -L " + shlex.quote(base) +
               "; test -f " + shlex.quote(source) + "; test ! -L " + shlex.quote(source) + "; "
               "test ! -e " + shlex.quote(samples) + "; nohup python3 " + shlex.quote(source) +
               " " + shlex.quote(experiment_id) + " --interval 5 > " + shlex.quote(log) +
               " 2>&1 < /dev/null & for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do "
               "test -s " + shlex.quote(samples) + " && break; sleep 1; done; head -n 1 " +
               shlex.quote(samples))
    output = ssh(command, timeout=30).strip()
    if not output:
        raise RuntimeError("Watcher failed to write its first sample: " + experiment_id)
    record("watcher_first_sample", id=experiment_id, sample=output)
    return output


def parse_status(output):
    start = output.find("{")
    return json.JSONDecoder().raw_decode(output[start:])[0]


def process(cell, plan):
    experiment_id = cell["id"]
    state = status(experiment_id)
    paths = remote_paths([experiment_id])[experiment_id]
    local = ROOT / "results" / experiment_id
    if state is None and any(paths):
        raise RuntimeError("Remote ID path exists without metadata: " + experiment_id)
    if state is None and (local.exists() or local.is_symlink()):
        raise RuntimeError("Local result exists without remote state: " + experiment_id)
    if state is None:
        gate = resource_gate()
        record("resource_gate_before_build", id=experiment_id, resources=gate)
        built = call("build", "--repo-local", str(ROOT), "--source-sha", SOURCE_SHA,
                     "--id", experiment_id, "--label", "ws26-moe-hop-diagnostic",
                     timeout=6 * 60 * 60)
        state = status(experiment_id)
        if not state or state.get("status") != "BUILT" or state.get("git_commit") != SOURCE_SHA:
            raise RuntimeError("Build identity mismatch: " + experiment_id + "\n" + built[-1500:])
        record("built", id=experiment_id, source_sha=SOURCE_SHA)
    elif state.get("status") == "BUILDING":
        state = wait_for_state(experiment_id, ("BUILT",), 60)
    if state.get("git_commit") != SOURCE_SHA:
        raise RuntimeError("Remote source SHA mismatch: " + experiment_id)
    if state.get("status") in ("FAILED", "BUILD_FAILED", "INTERRUPTED"):
        raise RuntimeError("Existing terminal failure preserved: " + experiment_id)
    if state.get("status") == "SUCCEEDED":
        summary = verify_local(cell, plan)
        record("verified_reused", id=experiment_id, fct_sha256=summary["fct_sha256"])
        return summary
    if state.get("status") == "BUILT":
        copy_trace(cell)
        gate = resource_gate()
        record("resource_gate_before_run", id=experiment_id, resources=gate)
        first = watcher_first_sample(experiment_id)
        args = ["run", experiment_id, "--lb", cell["mode"], "--simul-time", "0.01",
                "--netload", "10", "--max-concurrent", "1", "--bw", "400", "--buffer", "9",
                "--topo", plan["topology"], "--cdf", "AliStorage2019", "--flow-file",
                "config/" + cell["trace"], "--pfc", "1", "--irn", "1", "--factorial-pilot",
                "--ws25-diag", "1", "--ws26-moe-hop-diag", "1"]
        output = call(*args, timeout=120)
        state = status(experiment_id)
        if (not state or state.get("status") not in ("RUNNING", "SUCCEEDED") or
                state.get("git_commit") != SOURCE_SHA or state.get("concurrency_cap") != 1 or
                state.get("parameters", {}).get("ws25_diag") != 1 or
                state.get("parameters", {}).get("ws26_moe_hop_diag") != 1 or
                state.get("parameters", {}).get("flow_file") != cell["trace"]):
            raise RuntimeError("Run metadata mismatch: " + experiment_id + "\n" + output[-1500:])
        record("run_started", id=experiment_id, source_sha=SOURCE_SHA,
               trace_sha256=cell["trace_sha256"], pid=state.get("pid"), cap=1,
               watcher_first_sample=first)
        if state.get("status") == "RUNNING":
            interval = 30 if cell["stage"] == "smoke" else 1800
            state = wait_for_state(experiment_id, ("SUCCEEDED",), interval)
    elif state.get("status") == "RUNNING":
        interval = 30 if cell["stage"] == "smoke" else 1800
        state = wait_for_state(experiment_id, ("SUCCEEDED",), interval)
    if state.get("status") != "SUCCEEDED":
        raise RuntimeError("Run ended in " + str(state.get("status")) + ": " + experiment_id)
    resource_path = "/home/fnl/lzy/results/" + experiment_id + "/logs/resource-summary.json"
    resource_text = remote_python("import os; p=%r; print(open(p).read() if os.path.isfile(p) else '')" %
                                  resource_path)
    if not resource_text:
        raise RuntimeError("Watcher terminal receipt missing: " + experiment_id)
    resource = json.loads(resource_text)
    record("resource_terminal", id=experiment_id, summary=resource)
    call("fetch", experiment_id, timeout=1800)
    summary = verify_local(cell, plan)
    record("verified", id=experiment_id, source_sha=SOURCE_SHA,
           trace_sha256=cell["trace_sha256"], fct_sha256=summary["fct_sha256"],
           qp_count=summary["hop_qp_count"], peak_tree_rss_mib=resource["peak_tree_rss_mib"])
    print("verified " + experiment_id, flush=True)
    return summary


def verify_local(cell, plan):
    if not (ROOT / "results" / cell["id"]).exists():
        call("fetch", cell["id"], timeout=1800)
    folder = ROOT / "results" / cell["id"]
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    raw_log = folder / "raw" / str(metadata.get("raw_directory", "")) / "config.log"
    target_log = folder / "logs" / "config.log"
    if raw_log.is_symlink() or not raw_log.is_file():
        raise RuntimeError("Fetched raw config.log missing: " + cell["id"])
    if target_log.exists() or target_log.is_symlink():
        if target_log.is_symlink() or not target_log.is_file() or digest_script(target_log) != digest_script(raw_log):
            raise RuntimeError("Refusing to replace different config.log: " + cell["id"])
    else:
        with raw_log.open("rb") as source, target_log.open("xb") as destination:
            destination.write(source.read())
    output = subprocess.run([sys.executable, str(SCRIPTS / "verify_ws26_moe_hop_diagnostic.py"),
                             "--id", cell["id"]], cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    if output.returncode:
        raise RuntimeError("Cell verification failed: " + cell["id"] + "\n" + output.stdout[-2500:])
    return json.loads(output.stdout)


def main():
    plan = verifier.load_plan()
    if len(plan["cells"]) != 10 or SOURCE_SHA != plan["source_sha"]:
        raise RuntimeError("Frozen diagnostic plan mismatch")
    OUT.mkdir(parents=True, exist_ok=True)
    lock = ControllerLock(LOCK)
    try:
        lock.acquire()
    except OSError:
        lock.release()
        raise RuntimeError("Another WS-26 MoE hop diagnostic controller is active")
    try:
        ids = [cell["id"] for cell in plan["cells"]]
        collision_report = remote_preflight(ids)
        if (collision_report["collisions"] or collision_report["other_user_processes"] or
                collision_report["simulation_lock_held"]):
            raise RuntimeError("Remote preflight failed: " + json.dumps(collision_report))
        for cell in plan["cells"]:
            path = ROOT / "results" / cell["id"]
            if path.exists() or path.is_symlink():
                raise RuntimeError("Local ID collision; preserving existing path: " + cell["id"])
        gate = resource_gate()
        paired_audits = [audit_paired_plain(cell) for cell in plan["cells"]]
        record("controller_started", plan_sha256=PLAN_SHA256, source_sha=SOURCE_SHA,
               planned_cells=10, cap=1, remote_preflight=collision_report,
               resources=gate, paired_plain_audits=paired_audits,
               runner_sha256=digest_script(__file__))
        call("deploy", timeout=120)
        call("sync", "--repo-local", str(ROOT), timeout=1800)
        verified = set()
        if RECEIPTS.is_file():
            for line in RECEIPTS.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                if row.get("event") in ("verified", "verified_reused"):
                    verified.add(row["id"])
        for cell in plan["cells"]:
            if cell["id"] in verified:
                raise RuntimeError("Receipt says verified but initial audit found ID collision")
            try:
                process(cell, plan)
            except Exception as error:
                record("stopped", id=cell["id"], error=str(error),
                       completed_before=len(verified), planned_cells=10,
                       next_cell_started=False)
                raise
        record("controller_complete", verified_cells=10, plan_sha256=PLAN_SHA256,
               source_sha=SOURCE_SHA)
        print("all ten diagnostic cells verified", flush=True)
    finally:
        lock.release()


def digest_script(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if __name__ == "__main__":
    main()
