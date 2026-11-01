import sys
sys.dont_write_bytecode = True
import pathlib, subprocess, json, hashlib, importlib.util, shlex, datetime, time, re, traceback

OUT = pathlib.Path(__file__).resolve().parent
PREFIX = "zero-control-pilot-r1"
REPO = pathlib.Path("E:/研/毕业论文/workspace/ws31-candidates-implementation")
PLAN = json.loads((OUT / (PREFIX + "-frozen-plan.json")).read_text(encoding="utf-8"))
RECEIPT = OUT / (PREFIX + "-receipt.json")
EVIDENCE = OUT / (PREFIX + "-evidence")
EVIDENCE.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location("controller", str(REPO / "scripts/remote_experiment.py"))
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)
CFG = controller.config()
state = {
    "scope": PLAN["scope"], "source_sha": PLAN["source_sha"],
    "status": "STARTING", "cells": [dict(c, status="NOT_STARTED") for c in PLAN["cells"]],
    "network_runs_started": 0, "commands": [],
    "resource_scope": "Before/after snapshots and 2-second run samples; sampled maxima are not exact peaks",
    "plan_sha256": hashlib.sha256((OUT / (PREFIX + "-frozen-plan.json")).read_bytes()).hexdigest(),
}

def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def save():
    state["updated_utc"] = stamp()
    temp = RECEIPT.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(RECEIPT)

def checkpoint(cell, status):
    if (OUT / (PREFIX + "-stop-request.json")).exists():
        raise RuntimeError("Explicit stop request present; no further stage started")
    cell["status"] = status
    state["status"] = "ACTIVE"
    save()
    print(cell["id"] + " " + status, flush=True)

def remote(code, timeout=90):
    v = subprocess.run(controller.ssh_base(CFG) + ["python3 -c " + shlex.quote(code)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if v.returncode:
        raise RuntimeError("Read-only remote operation failed: " + v.stderr[-1600:] + v.stdout[-600:])
    return json.loads(v.stdout)

RESOURCE = r'''
import os,re,json,subprocess,datetime
root='/home/fnl/lzy'
assert os.path.realpath(root)==root and os.path.isdir(root)
other=[];compute=[]
for row in subprocess.check_output(['ps','-eo','uid,pid,stat,comm','--no-headers']).decode().splitlines():
 c=row.split(None,3)
 if len(c)!=4:continue
 uid,pid,status,comm=c
 if int(uid)>=1000 and int(uid)!=os.getuid() and not status.startswith('Z'):other.append(row.strip())
 if comm.startswith(('network-load','cc1plus','g++','gcc','waf')):compute.append(row.strip())
mem=open('/proc/meminfo').read();v=os.statvfs(root)
r={'utc':datetime.datetime.utcnow().isoformat()+'Z','logical_cpu':os.cpu_count(),'loadavg':os.getloadavg(),
 'available_gib':int(re.search(r'^MemAvailable:\s+(\d+)',mem,re.M).group(1))/1024**2,
 'free_gib':v.f_bavail*v.f_frsize/1024**3,'other_ordinary_user_processes':other,'compute_processes':compute,
 'logged_in':subprocess.check_output(['who']).decode()}
r['gate_pass']=not other and not compute and r['loadavg'][0]<=20 and r['available_gib']>=4 and r['free_gib']>=20
print(json.dumps(r))
'''

def resource(cell, name):
    d = remote(RESOURCE)
    (EVIDENCE / cell["id"] / (name + ".json")).write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
    if not d["gate_pass"]:
        raise RuntimeError("Fresh resource/other-job gate failed at " + name)
    return d

def command(cell, name, argv, timeout=1900):
    log = EVIDENCE / cell["id"] / (name + ".log")
    assert not log.exists()
    rec = {"cell": cell["id"], "operation": name, "argv": argv, "start_utc": stamp(),
           "log": str(log)}
    state["commands"].append(rec)
    save()
    with log.open("wb") as output:
        v = subprocess.run(argv, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
    rec.update(exit_code=v.returncode, end_utc=stamp())
    save()
    if v.returncode:
        raise RuntimeError(name + " exit=" + str(v.returncode))

def monitor(cell):
    base = "/home/fnl/lzy/results/" + cell["id"]
    code = r'''
import os,json,time,re,datetime
base=BASE
assert os.path.realpath(base)==base and not os.path.islink(base)
path=base+'/logs/resource-run-samples.jsonl';assert not os.path.lexists(path)
samples=[];deadline=time.time()+1800
def snapshot(pid):
 rss=0;cpu_ticks=0;procs={};parents={}
 for n in os.listdir('/proc'):
  if not n.isdigit():continue
  try:
   s=open('/proc/'+n+'/status').read()
   parents[int(n)]=int(re.search(r'^PPid:\s+(\d+)',s,re.M).group(1))
   procs[int(n)]=s
  except (IOError,OSError,AttributeError):pass
 for n,s in procs.items():
  p=n;seen=set()
  while p and p not in seen and p!=pid:seen.add(p);p=parents.get(p,0)
  if p!=pid:continue
  m=re.search(r'^VmRSS:\s+(\d+)',s,re.M)
  rss+=int(m.group(1)) if m else 0
  try:
   stat=open('/proc/%d/stat'%n).read().rsplit(')',1)[1].split()
   cpu_ticks+=int(stat[11])+int(stat[12])
  except (IOError,OSError,IndexError,ValueError):pass
 mem=open('/proc/meminfo').read();v=os.statvfs('/home/fnl/lzy')
 return {'utc':datetime.datetime.utcnow().isoformat()+'Z','pid':pid,'loadavg':os.getloadavg(),
  'available_gib':int(re.search(r'^MemAvailable:\s+(\d+)',mem,re.M).group(1))/1024**2,
  'free_gib':v.f_bavail*v.f_frsize/1024**3,'worker_tree_rss_kib_sample':rss,'worker_tree_cpu_ticks_sample':cpu_ticks}
with open(path,'w') as stream:
 while time.time()<deadline:
  meta=json.load(open(base+'/metadata.json'))
  d=snapshot(meta['pid']);samples.append(d);stream.write(json.dumps(d)+'\n');stream.flush()
  if meta['status']!='RUNNING':break
  time.sleep(2)
 else:raise RuntimeError('Monitoring timeout; retain ID and inspect actual run')
r={'metadata':meta,'sampling_interval_seconds':2,'sample_count':len(samples),
 'max_sampled_worker_tree_rss_kib':max(s['worker_tree_rss_kib_sample'] for s in samples),
 'min_sampled_available_gib':min(s['available_gib'] for s in samples),
 'max_sampled_load_1m':max(s['loadavg'][0] for s in samples),
 'sample_path':path,'claim':'sampled observations only, not exact resource peaks'}
with open(base+'/logs/resource-run-summary.json','w') as f:json.dump(r,f,indent=2)
print(json.dumps(r))
'''.replace("BASE", repr(base))
    d = remote(code, timeout=1860)
    (EVIDENCE / cell["id"] / "run-monitor.json").write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
    return d

def transfer(cell):
    folder = EVIDENCE / cell["id"]
    base = "/home/fnl/lzy/results/" + cell["id"]
    code = r'''
import os,json,hashlib,subprocess
base=BASE
source=SOURCE
assert os.path.realpath(base)==base and os.path.realpath(source)==source
files={}
for parent,dirs,names in os.walk(base):
 for name in dirs+names:
  assert not os.path.islink(parent+'/'+name)
 for name in names:
  p=parent+'/'+name;h=hashlib.sha256()
  with open(p,'rb') as f:
   for b in iter(lambda:f.read(1048576),b''):h.update(b)
  files[os.path.relpath(p,base)]={'bytes':os.path.getsize(p),'sha256':h.hexdigest()}
paths=subprocess.check_output(['git','-C',source,'diff','--name-only','21faeb2d986b0a4d9d59edd9bf11a0d0de934007',SHA]).decode().splitlines()
paths+=['src/point-to-point/model/ws30-observer.h','config/leaf_spine_128_100G_OS2.txt','config/ws31_correctness_r1.txt','scripts/verify_ws31_fct.py']
hashes={p:hashlib.sha256(open(source+'/'+p,'rb').read()).hexdigest() for p in sorted(set(paths))}
binary=source+'/build/scratch/network-load-balance'
print(json.dumps({'files':files,'source_head':subprocess.check_output(['git','-C',source,'rev-parse','HEAD']).decode().strip(),
 'source_hashes':hashes,'binary_sha256':hashlib.sha256(open(binary,'rb').read()).hexdigest()}))
'''.replace("BASE", repr(base)).replace("SOURCE", repr("/home/fnl/lzy/runs/" + cell["id"] + "/source")).replace("SHA", repr(PLAN["source_sha"]))
    manifest = remote(code, timeout=180)
    (folder / "remote-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    target = folder / "results"
    assert not target.exists()
    v = subprocess.run(["scp", "-r", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                        "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=15",
                        "-o", "ServerAliveCountMax=2", CFG["REMOTE_USER"] + "@" + CFG["REMOTE_HOST"] + ":" + base,
                        str(target)], capture_output=True, timeout=900)
    (folder / "transfer.log").write_bytes(v.stdout + v.stderr)
    assert v.returncode == 0, "SCP failed; retained staging/results"
    for rel, info in manifest["files"].items():
        p = target / rel
        assert p.is_file() and p.stat().st_size == info["bytes"], rel
        h = hashlib.sha256()
        with p.open("rb") as f:
            for b in iter(lambda: f.read(1048576), b""):
                h.update(b)
        assert h.hexdigest() == info["sha256"], rel
    assert manifest["source_head"] == PLAN["source_sha"]
    for path, h in manifest["source_hashes"].items():
        b = subprocess.check_output(["git", "-C", str(REPO), "show", PLAN["source_sha"] + ":" + path])
        assert hashlib.sha256(b).hexdigest() == h, path
    cell["source_hashes_verified"] = len(manifest["source_hashes"])
    cell["transferred_files_verified"] = len(manifest["files"])
    cell["binary_sha256"] = manifest["binary_sha256"]
    save()
    return target

def analyze(cell, target, reference):
    meta = json.loads((target / "metadata.json").read_text(encoding="utf-8"))
    assert meta["status"] == "SUCCEEDED", meta
    assert meta["git_commit"] == PLAN["source_sha"] and meta["cpu_jobs"] == 2 and meta["build_mode"] == "optimized"
    for name, value in PLAN["common"].items():
        observed = meta["concurrency_cap"] if name == "max_concurrent" else meta["parameters"].get(name)
        assert observed == value, (name, observed, value)
    assert meta["parameters"]["lb"] == cell["lb"]
    for name in ["ws30_composition", "ws30_lifecycle", "ws30_life_profile", "ws30_tag_transform",
                 "ws13_diag", "ws25_diag", "ws28_tail_diag", "ws21_heartbeat", "ws21_feedback",
                 "ws21_identity", "ws18_admission", "ws18_path"]:
        assert not meta["parameters"].get(name, 0), name
    assert meta["input_flow_sha256"] == PLAN["inputs"]["config/ws31_correctness_r1.txt"]
    assert meta["topology_sha256"] == PLAN["inputs"]["config/leaf_spine_128_100G_OS2.txt"]
    fcts = list((target / "raw").glob("*/*_out_fct.txt"))
    logs = list((target / "raw").glob("*/config.log"))
    assert len(fcts) == len(logs) == 1
    fct, log = fcts[0], logs[0]
    args = [sys.executable, "-B", str(OUT / (PREFIX + "-verifier.py")),
            str(target / "config/traffic_trace.txt"), str(fct), "--log", str(log)]
    if reference:
        args += ["--equal-fct", reference["fct_path"]]
    command(cell, "all-input-verifier", args, 120)
    verified = json.loads((EVIDENCE / cell["id"] / "all-input-verifier.log").read_text(encoding="utf-8"))
    assert verified["flows"] == PLAN["flow_count"] and verified["payload_bytes"] == PLAN["payload_bytes"]
    hashes = {k: hashlib.sha256() for k in ["choice", "route", "combined"]}
    counts = {"choice": 0, "route": 0}
    routes = {}
    changes = 0
    path_summaries = []
    c2_rows = []
    c2_states = []
    config = {}
    for row in (target / "config/config.txt").read_text(encoding="ascii").splitlines():
        fields = row.split(None, 1)
        if len(fields) == 2:
            config[fields[0]] = fields[1]
    assert config["ENABLE_PFC"] == "0" and config["ENABLE_IRN"] == "1" and config["RANDOM_SEED"] == "1"
    assert config["CC_MODE"] == "1" and config["BUFFER_SIZE"] == "9"
    normalized_config = {k: (re.sub(r"mix/output/[0-9]+/[0-9]+", "mix/output/<RAW>/<RAW>", v)
                             if k.endswith("_FILE") or k.startswith("VOQ_MON") or k.endswith("_MON_FILE") else v)
                         for k, v in config.items() if k != "LB_MODE"}
    if reference:
        assert normalized_config == reference["normalized_common_config"], "Common configuration mismatch"
    with log.open("rb") as stream:
        for line in stream:
            assert b"WS30_OBSERVATION_OVERFLOW" not in line
            if line.startswith((b"WS30_CHOICE ", b"WS30_ROUTE ")):
                kind = "choice" if line.startswith(b"WS30_CHOICE ") else "route"
                normalized = re.sub(rb" uid=[^ \r\n]+", b"", line)
                hashes[kind].update(normalized)
                hashes["combined"].update(normalized)
                counts[kind] += 1
                if kind == "route":
                    values = dict(token.split(b"=", 1) for token in line.split()[1:])
                    key = tuple(int(values[k]) for k in [b"switch", b"sip", b"dip", b"sport", b"dport"])
                    port = int(values[b"port"])
                    if key in routes and routes[key] != port:
                        changes += 1
                    routes[key] = port
            elif line.startswith(b"WS30_PATH "):
                path_summaries.append({k.decode(): int(v) for k, v in (t.split(b"=", 1) for t in line.split()[1:])})
            elif line.startswith(b"WS31_C2_FINISH "):
                c2_rows.append({k.decode(): int(v) for k, v in (t.split(b"=", 1) for t in line.split()[1:])})
            elif line.startswith(b"WS31_C2_STATE "):
                c2_states.append({k.decode(): int(v) for k, v in (t.split(b"=", 1) for t in line.split()[1:])})
    assert counts["choice"] > 0 and 0 < counts["route"] <= 1000000
    assert changes == 0 and len(path_summaries) == 1
    assert path_summaries[0]["full_rows"] == counts["route"]
    assert path_summaries[0]["changed_qps"] == path_summaries[0]["port_changes"] == 0
    digest = {k: h.hexdigest() for k, h in hashes.items()}
    if reference:
        assert digest == reference["ordered_normalized_hashes"], "Ordered path/choice mismatch"
        assert counts == reference["observation_rows"]
    if cell["lb"] == "ws31-c2-zero":
        assert verified["c2_timing_rows_checked"] == 104 and len(c2_rows) == 104 and len(c2_states) == 1
        assert all(v["wait_ns"] == 0 and v["launch_ns"] == v["demand_ns"] for v in c2_rows)
        s = c2_states[0]
        for k in ["demanded", "launched", "finished"]:
            assert s[k] == 104, (k, s[k])
        for k in ["cancelled", "pending", "unfinished", "cancel_bytes", "waited", "delay_sum_ns", "delay_max_ns"]:
            assert s[k] == 0, (k, s[k])
        for k in ["demand_bytes", "launch_bytes", "finish_bytes"]:
            assert s[k] == PLAN["payload_bytes"], (k, s[k])
    result = {"all_input_verifier": verified, "fct_path": str(fct),
              "fct_sha256": verified["fct_sha256"], "observation_rows": counts,
              "ordered_normalized_hashes": digest, "within_qp_port_changes": changes,
              "switch_qps_observed": len(routes), "path_summary": path_summaries[0],
              "c2_state": c2_states, "common_config": config,
              "normalized_common_config": normalized_config, "status": "PASS"}
    (EVIDENCE / cell["id"] / "acceptance.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    cell["acceptance"] = result
    return result

def main():
    assert not RECEIPT.exists(), "Refuse to overwrite pilot receipt or re-run frozen IDs"
    save()
    fork = controller.local_fork(str(REPO), require_pushed=True)
    assert fork[3] == PLAN["source_sha"]
    ids = [c["id"] for c in state["cells"]]
    fresh = remote("import json,os;ids=" + repr(ids) +
                   ";print(json.dumps({'fresh':all(not os.path.lexists('/home/fnl/lzy/'+d+'/'+i)"
                   " for i in ids for d in ['results','runs'])}))")
    assert fresh["fresh"], "A frozen ID already exists; stop without reuse"
    expected_worker = hashlib.sha256((REPO / "scripts/remote_worker.py").read_bytes()).hexdigest()
    worker = remote("import hashlib,json;print(json.dumps({'sha256':hashlib.sha256(open('/home/fnl/lzy/.research-workflow/remote_worker.py','rb').read()).hexdigest()}))")
    assert worker["sha256"] == expected_worker
    state["deployed_worker_sha256"] = expected_worker
    reference = None
    for cell in state["cells"]:
        folder = EVIDENCE / cell["id"]
        assert not folder.exists()
        folder.mkdir()
        checkpoint(cell, "RESOURCE_GATE_BEFORE_BUILD")
        resource(cell, "resources-before-build")
        assert controller.local_fork(str(REPO), require_pushed=True)[3] == PLAN["source_sha"]
        checkpoint(cell, "BUILDING")
        command(cell, "guarded-build",
                [sys.executable, "-B", str(REPO / "scripts/remote_experiment.py"), "build",
                 "--repo-local", str(REPO), "--id", cell["id"], "--source-sha", PLAN["source_sha"]])
        checkpoint(cell, "BUILT_RESOURCE_GATE")
        resource(cell, "resources-before-run")
        args = [sys.executable, "-B", str(REPO / "scripts/remote_experiment.py"), "run", cell["id"], "--lb", cell["lb"]]
        for key, value in PLAN["common"].items():
            args += ["--" + key.replace("_", "-"), str(value)]
        checkpoint(cell, "STARTING_GUARDED_RUN")
        command(cell, "guarded-run", args, 90)
        state["network_runs_started"] += 1
        checkpoint(cell, "RUNNING")
        monitored = monitor(cell)
        cell["resource_samples"] = {k: v for k, v in monitored.items() if k != "metadata"}
        checkpoint(cell, "TERMINAL_TRANSFERRING")
        target = transfer(cell)
        assert monitored["metadata"]["status"] == "SUCCEEDED", monitored["metadata"]
        assert monitored["min_sampled_available_gib"] >= 4 and monitored["max_sampled_load_1m"] <= 20
        resource(cell, "resources-after-run")
        checkpoint(cell, "VERIFYING_ALL_REQUESTS_AND_PATHS")
        accepted = analyze(cell, target, reference)
        if reference is None:
            reference = accepted
        cell["status"] = "PASS"
        save()
        print(cell["id"] + " PASS", flush=True)
    state["status"] = "COMPLETE_FOR_FOUR_ZERO_CONTROL_TECHNICAL_PILOT_ONLY"
    save()
    print(state["status"], flush=True)

if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        state["status"] = "STOPPED_ON_FAILURE"
        state["error"] = str(error)
        state["traceback"] = traceback.format_exc()
        state["failure_utc"] = stamp()
        for c in state["cells"]:
            if c["status"] == "NOT_STARTED":
                c["status"] = "NOT_STARTED_DUE_TO_FAILURE"
        save()
        (OUT / (PREFIX + "-driver-failure.log")).write_text(traceback.format_exc(), encoding="utf-8")
        print("STOPPED_ON_FAILURE " + str(error), flush=True)
        raise
