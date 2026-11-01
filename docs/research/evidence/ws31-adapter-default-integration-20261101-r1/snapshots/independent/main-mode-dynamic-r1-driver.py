import sys
sys.dont_write_bytecode = True
import pathlib, json, hashlib, importlib.util, subprocess, re, threading, traceback, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

OUT = pathlib.Path(__file__).resolve().parent
PREFIX = "main-mode-dynamic-r1"
spec = importlib.util.spec_from_file_location("pilot_engine", str(OUT / "zero-control-pilot-r1-driver.py"))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
b.PREFIX = PREFIX
b.PLAN = json.loads((OUT / (PREFIX + "-frozen-plan.json")).read_text(encoding="utf-8"))
b.RECEIPT = OUT / (PREFIX + "-receipt.json")
b.EVIDENCE = OUT / (PREFIX + "-evidence")
b.EVIDENCE.mkdir(exist_ok=True)
b.state = {"scope": b.PLAN["scope"], "source_sha": b.PLAN["source_sha"], "status": "STARTING",
           "cells": [dict(c, status="NOT_STARTED") for c in b.PLAN["cells"]],
           "network_runs_started": 0, "commands": [],
           "resource_scope": "5-second build-batch samples, 2-second run samples and snapshots; not exact peaks",
           "plan_sha256": hashlib.sha256((OUT / (PREFIX + "-frozen-plan.json")).read_bytes()).hexdigest()}
LOCK = threading.RLock()
old_save = b.save
def save():
    with LOCK:
        old_save()
b.save = save

def checkpoint(cell, status):
    with LOCK:
        if (OUT / (PREFIX + "-stop-request.json")).exists():
            raise RuntimeError("Explicit stop request; no next stage")
        cell["status"] = status
        b.state["status"] = "ACTIVE"
        save()
        print(cell["id"] + " " + status, flush=True)
b.checkpoint = checkpoint

def command(cell, name, argv, timeout=1900):
    log = b.EVIDENCE / cell["id"] / (name + ".log")
    assert not log.exists()
    rec = {"cell": cell["id"], "operation": name, "argv": argv,
           "start_utc": b.stamp(), "log": str(log)}
    with LOCK:
        b.state["commands"].append(rec)
        save()
    with log.open("wb") as stream:
        v = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
    with LOCK:
        rec.update(exit_code=v.returncode, end_utc=b.stamp())
        save()
    if v.returncode:
        raise RuntimeError(name + " exit=" + str(v.returncode))
b.command = command

class CoverageGap(RuntimeError):
    pass

def fields(line):
    values = dict(token.split("=", 1) for token in line.split()[1:])
    return {k: int(v) if re.fullmatch(r"[0-9]+", v) else v for k, v in values.items()}

EXTRA_RESOURCE = b.RESOURCE.replace(
    "r['gate_pass']=", """unknown=[]
for n in os.listdir('/proc'):
 if not n.isdigit() or int(n)==os.getpid():continue
 try:
  s=open('/proc/'+n+'/status').read()
  uid=int(re.search(r'^Uid:\\s+(\\d+)',s,re.M).group(1))
  cwd=os.readlink('/proc/'+n+'/cwd')
  if uid==os.getuid() and (cwd==root or cwd.startswith(root+'/')):
   unknown.append({'pid':int(n),'cwd':cwd,'comm':open('/proc/'+n+'/comm').read().strip()})
 except (IOError,OSError,AttributeError):pass
r['unknown_project_jobs']=unknown
r['gate_pass']=""").replace("not other and not compute and", "not other and not compute and not unknown and")

def fresh(cell, name):
    d = b.remote(EXTRA_RESOURCE)
    (b.EVIDENCE / cell["id"] / (name + ".json")).write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
    if not d["gate_pass"]:
        raise RuntimeError("Other-user/unknown-job/resource gate failed: " + name)
    return d

def build_sampler():
    ids = [c["id"] for c in b.state["cells"]]
    code = r'''
import os,time,json,re,subprocess,datetime
ids=IDS
base='/home/fnl/lzy/results/'+ids[0]
for unused in range(90):
 if os.path.isdir(base+'/logs'):break
 time.sleep(1)
else:raise RuntimeError('First build result directory not established')
path=base+'/logs/resource-build-batch-samples.jsonl';assert not os.path.lexists(path)
samples=[];deadline=time.time()+1900
with open(path,'w') as stream:
 while time.time()<deadline:
  metas=[]
  for i in ids:
   p='/home/fnl/lzy/results/'+i+'/metadata.json'
   if os.path.isfile(p):metas.append(json.load(open(p)))
  roots={m['pid'] for m in metas};parents={};procs={};other=[];unknown=[];cc=0
  for n in os.listdir('/proc'):
   if not n.isdigit():continue
   try:
    s=open('/proc/'+n+'/status').read()
    uid=int(re.search(r'^Uid:\s+(\d+)',s,re.M).group(1))
    stat=re.search(r'^State:\s+(\S+)',s,re.M).group(1)
    if uid>=1000 and uid!=os.getuid() and stat!='Z':other.append(int(n))
    parents[int(n)]=int(re.search(r'^PPid:\s+(\d+)',s,re.M).group(1));procs[int(n)]=s
    if open('/proc/'+n+'/comm').read().strip()=='cc1plus':cc+=1
   except (IOError,OSError,AttributeError):pass
  rss=0
  for pid,s in procs.items():
   q=pid;seen=set()
   while q and q not in roots and q not in seen:seen.add(q);q=parents.get(q,0)
   if q in roots:
    m=re.search(r'^VmRSS:\s+(\d+)',s,re.M);rss+=int(m.group(1)) if m else 0
   elif pid!=os.getpid():
    try:
     uid=int(re.search(r'^Uid:\s+(\d+)',s,re.M).group(1));cwd=os.readlink('/proc/%d/cwd'%pid)
     if uid==os.getuid() and (cwd=='/home/fnl/lzy' or cwd.startswith('/home/fnl/lzy/')):unknown.append(pid)
    except (IOError,OSError,AttributeError):pass
  mem=open('/proc/meminfo').read();v=os.statvfs('/home/fnl/lzy')
  d={'utc':datetime.datetime.utcnow().isoformat()+'Z','loadavg':os.getloadavg(),
   'available_gib':int(re.search(r'^MemAvailable:\s+(\d+)',mem,re.M).group(1))/1024**2,
   'free_gib':v.f_bavail*v.f_frsize/1024**3,'build_tree_rss_kib_sample':rss,'cc1plus_count_sample':cc,
   'building_metadata_count':sum(m['status']=='BUILDING' for m in metas),
   'other_user_pids':other,'unknown_project_pids':unknown}
  samples.append(d);stream.write(json.dumps(d)+'\n');stream.flush()
  if os.path.exists(base+'/logs/build-batch-monitor-stop.json'):break
  if len(metas)==len(ids) and all(m['status'] in ('BUILT','BUILD_FAILED') for m in metas):break
  time.sleep(5)
 else:raise RuntimeError('Build resource monitor timeout')
r={'sample_count':len(samples),'interval_seconds':5,
 'max_sampled_load_1m':max(s['loadavg'][0] for s in samples),
 'min_sampled_available_gib':min(s['available_gib'] for s in samples),
 'min_sampled_free_gib':min(s['free_gib'] for s in samples),
 'max_sampled_build_tree_rss_kib':max(s['build_tree_rss_kib_sample'] for s in samples),
 'max_sampled_cc1plus_count':max(s['cc1plus_count_sample'] for s in samples),
 'max_sampled_building_metadata_count':max(s['building_metadata_count'] for s in samples),
 'other_user_seen':any(s['other_user_pids'] for s in samples),
 'unknown_project_seen':any(s['unknown_project_pids'] for s in samples),
 'claim':'sampled maxima/minima, not exact peaks'}
with open(base+'/logs/resource-build-batch-summary.json','w') as f:json.dump(r,f,indent=2)
print(json.dumps(r))
'''.replace("IDS", repr(ids))
    result = b.remote(code, timeout=2000)
    (OUT / (PREFIX + "-build-resources.json")).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result

def do_build(cell):
    checkpoint(cell, "BUILDING")
    try:
        command(cell, "guarded-build", [sys.executable, "-B", str(b.REPO / "scripts/remote_experiment.py"),
                "build", "--repo-local", str(b.REPO), "--id", cell["id"], "--source-sha", b.PLAN["source_sha"]])
    except BaseException:
        with LOCK:
            cell["status"] = "BUILD_FAILED"
            save()
        raise
    with LOCK:
        cell["status"] = "BUILT"
        save()
    print(cell["id"] + " BUILT", flush=True)

def verify_builds():
    ids = [c["id"] for c in b.state["cells"]]
    code = r'''
import os,json,subprocess,hashlib
ids=IDS
result=[]
for i in ids:
 source='/home/fnl/lzy/runs/'+i+'/source';base='/home/fnl/lzy/results/'+i
 meta=json.load(open(base+'/metadata.json'))
 assert meta['status']=='BUILT' and meta['cpu_jobs']==2 and meta['build_mode']=='optimized'
 assert subprocess.check_output(['git','-C',source,'rev-parse','HEAD']).decode().strip()==SHA
 assert not subprocess.check_output(['git','-C',source,'status','--porcelain']).strip()
 paths=subprocess.check_output(['git','-C',source,'diff','--name-only','21faeb2d986b0a4d9d59edd9bf11a0d0de934007',SHA]).decode().splitlines()
 paths+=['src/point-to-point/model/ws30-observer.h','config/leaf_spine_128_100G_OS2.txt','config/ws31_correctness_r1.txt','scripts/verify_ws31_fct.py']
 hashes={p:hashlib.sha256(open(source+'/'+p,'rb').read()).hexdigest() for p in sorted(set(paths))}
 binary=source+'/build/scratch/network-load-balance'
 result.append({'id':i,'metadata':meta,'source_hashes':hashes,'binary_sha256':hashlib.sha256(open(binary,'rb').read()).hexdigest()})
print(json.dumps(result))
'''.replace("IDS", repr(ids)).replace("SHA", repr(b.PLAN["source_sha"]))
    result = b.remote(code, timeout=180)
    for item in result:
        assert item["metadata"]["git_commit"] == b.PLAN["source_sha"]
        for path, h in item["source_hashes"].items():
            blob = subprocess.check_output(["git", "-C", str(b.REPO), "show", b.PLAN["source_sha"] + ":" + path])
            assert hashlib.sha256(blob).hexdigest() == h
    (OUT / (PREFIX + "-all-builds-verified.json")).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result

def dynamic_analyze(cell, target):
    common = b.analyze(cell, target, None)
    log = next((target / "raw").glob("*/config.log"))
    c1states=[];c1choices=[];c3states=[];c2rows=[];queue=[];c3fresh={};residual={};c3counters={}
    with log.open(encoding="utf-8", errors="strict") as stream:
        for line in stream:
            if line.startswith("WS30_QUEUE "):queue.append(fields(line))
            elif line.startswith("WS31_C1_STATE "):c1states.append(fields(line))
            elif line.startswith("WS31_C1_CHOICE "):c1choices.append(fields(line))
            elif line.startswith("WS31_C2_FINISH "):c2rows.append(fields(line))
            elif line.startswith("WS31_C3_STATE "):c3states.append(fields(line))
            elif line.startswith("WS31_C3_ROUTE "):
                v=fields(line);key=tuple(v[k] for k in ["switch","sip","dip","sport","dport"])
                counts=c3counters.setdefault(v["switch"],{"fresh":0,"restricted":0,"borrowed":0,"residual_packets":0,"residual_wire_bytes":0})
                if v["fresh"]:
                    assert key not in c3fresh
                    c3fresh[key]=v["chosen"];counts["fresh"]+=1;counts["restricted"]+=v["restricted"];counts["borrowed"]+=v["borrowed"]
                else:
                    assert key in c3fresh and c3fresh[key]==v["chosen"]
                if v["residual"]:
                    assert v["borrowed"] and not v["fresh"]
                    counts["residual_packets"]+=1;counts["residual_wire_bytes"]+=v["wire_bytes"]
    assert len(queue)==1
    q=queue[0];assert q["violations"]==0 and q["enqueued"]==q["dequeued"]+q["dropped"]+q["current"]
    detail={"mode":cell["lb"],"queue_ledger":q,"common_acceptance":"PASS","coverage":{}}
    if cell["lb"]=="ws31-c1":
        assert c1states and all(s["conserved"]==1 for s in c1states)
        assert all(s["predictor_peak"]<=65536 and s["ttl_ns"]==20000 and s["max_entries"]==65536 and s["max_ranges"]==32 for s in c1states)
        assert all(s["moe_payload"]==8192 and s["bg_payload"]==65536 and s["unified_payload"]==8192 for s in c1states)
        assert sum(s["fresh"] for s in c1states)==104 and sum(s["entries"] for s in c1states)==104 and sum(s["hits"] for s in c1states)>0
        assert len(c1choices)==104 and len({tuple(c[k] for k in ["switch","sip","dip","sport","dport"]) for c in c1choices})==104
        pressure=sum(bool(c["r1"] or c["r2"]) for c in c1choices)
        unique=sum(s["unique_payload"] for s in c1states)
        detail.update(states=c1states,choices=c1choices,nonzero_pressure_choices=pressure,unique_payload_deduction_counter=unique)
        detail["coverage"]={"nonzero_pressure":pressure>0,"unique_payload_deduction":unique>0}
    elif cell["lb"]=="ws31-c2":
        assert len(c2rows)==104 and common["all_input_verifier"]["c2_timing_rows_checked"]==104 and len(common["c2_state"])==1
        tags=[int(row.split()[5]) for row in (target/"config/traffic_trace.txt").read_text(encoding="ascii").splitlines()[1:] if row.strip()]
        positive=0;tagstats={}
        for v in c2rows:
            tag=tags[v["flow_id"]];tagstats[tag]=tagstats.get(tag,0)+1
            assert 0<=v["wait_ns"]<=500
            if tag!=2:assert v["wait_ns"]==0
            if tag==2 and v["wait_ns"]>0:positive+=1
        s=common["c2_state"][0]
        for k in ["demanded","launched","finished"]:assert s[k]==104
        for k in ["cancelled","pending","unfinished","cancel_bytes"]:assert s[k]==0
        for k in ["demand_bytes","launch_bytes","finish_bytes"]:assert s[k]==b.PLAN["payload_bytes"]
        assert s["waited"]==positive and s["delay_sum_ns"]==sum(v["wait_ns"] for v in c2rows)
        assert s["delay_max_ns"]==max(v["wait_ns"] for v in c2rows)
        detail.update(timing_rows=c2rows,state=s,input_tags=tagstats,positive_eligible_waits=positive)
        detail["coverage"]={"positive_eligible_wait":positive>0}
    elif cell["lb"]=="ws31-c3":
        assert c3states and all(s["conserved"]==1 and s["activity_ns"]==20000 and s["pinning"]==1 and s["moe_lane_fraction"]=="1/4" for s in c3states)
        assert sum(s["fresh"] for s in c3states)==104 and sum(s["entries"] for s in c3states)==104 and len(c3fresh)==104
        for s in c3states:
            counts=c3counters.get(s["switch"],{"fresh":0,"restricted":0,"borrowed":0,"residual_packets":0,"residual_wire_bytes":0})
            for k in counts:assert counts[k]==s[k],(s["switch"],k,counts[k],s[k])
        sums={k:sum(s[k] for s in c3states) for k in ["restricted","borrowed","residual_packets","residual_wire_bytes","moe_activations","moe_borrowers_at_activation_sum"]}
        reactivated=max(s["moe_activations"] for s in c3states)>=2
        detail.update(states=c3states,per_switch_logged_counters=c3counters,totals=sums,
                      reactivation_interpretation="At least one source switch records tag2 activation twice; not merely two switches' first activations")
        detail["coverage"]={"restricted_admission":sums["restricted"]>0,"borrowed_admission":sums["borrowed"]>0,
                            "tag2_reactivation":reactivated,
                            "borrower_or_residual_evidence":sums["moe_borrowers_at_activation_sum"]>0 or sums["residual_packets"]>0}
    assert detail["coverage"]
    detail["status"]="PASS" if all(detail["coverage"].values()) else "COVERAGE_GAP"
    (b.EVIDENCE/cell["id"]/"dynamic-acceptance.json").write_text(json.dumps(detail,indent=2)+"\n",encoding="utf-8")
    cell["dynamic_acceptance"]=detail
    save()
    if detail["status"]!="PASS":raise CoverageGap(cell["lb"]+" required branch not covered: "+str(detail["coverage"]))
    return detail

def main():
    assert not b.RECEIPT.exists(),"Do not overwrite/re-run fixed IDs"
    save()
    assert b.controller.local_fork(str(b.REPO),require_pushed=True)[3]==b.PLAN["source_sha"]
    for c in b.state["cells"]:
        folder=b.EVIDENCE/c["id"];assert not folder.exists();folder.mkdir()
    ids=[c["id"] for c in b.state["cells"]]
    d=b.remote("import os,json;ids="+repr(ids)+";print(json.dumps({'fresh':all(not os.path.lexists('/home/fnl/lzy/'+p+'/'+i) for i in ids for p in ['runs','results'])}))")
    assert d["fresh"]
    expected=hashlib.sha256((b.REPO/"scripts/remote_worker.py").read_bytes()).hexdigest()
    actual=b.remote("import json,hashlib;print(json.dumps({'sha':hashlib.sha256(open('/home/fnl/lzy/.research-workflow/remote_worker.py','rb').read()).hexdigest()}))")
    assert actual["sha"]==expected;b.state["deployed_worker_sha256"]=expected
    admission=fresh(b.state["cells"][0],"resources-batch-before")
    parallel=3 if admission["available_gib"]>=64 and admission["free_gib"]>=100 and admission["loadavg"][0]<=4 else 1
    b.state["parallel_builds_admitted"]=parallel;b.state["max_compile_jobs_admitted"]=parallel*2;save()
    print("BOUNDED_BUILD_ADMISSION parallel=%d total_jobs=%d"%(parallel,parallel*2),flush=True)
    errors=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        sampler=pool.submit(build_sampler)
        if parallel==3:
            futures={pool.submit(do_build,c):c for c in b.state["cells"]}
            for future in as_completed(futures):
                try:future.result()
                except BaseException as error:errors.append(str(error))
        else:
            for c in b.state["cells"]:
                try:do_build(c)
                except BaseException as error:errors.append(str(error));break
        # Stop only this read-only sampling loop; never signal compiler/simulation jobs.
        first="/home/fnl/lzy/results/"+ids[0]+"/logs"
        b.remote("import os,json;p="+repr(first)+";assert os.path.realpath(p)==p;open(p+'/build-batch-monitor-stop.json','w').write('{}');print(json.dumps({'monitor_stop_written':True}))")
        sampled=sampler.result()
    b.state["build_batch_samples"]=sampled;save()
    if errors:raise RuntimeError("Build batch failed: "+"; ".join(errors))
    assert not sampled["other_user_seen"] and not sampled["unknown_project_seen"]
    assert sampled["min_sampled_available_gib"]>=4 and sampled["min_sampled_free_gib"]>=20 and sampled["max_sampled_load_1m"]<=20
    verify_builds();b.state["all_builds_verified_before_any_run"]=True;save()
    for c in b.state["cells"]:
        checkpoint(c,"RESOURCE_GATE_BEFORE_RUN");fresh(c,"resources-before-run")
        args=[sys.executable,"-B",str(b.REPO/"scripts/remote_experiment.py"),"run",c["id"],"--lb",c["lb"]]
        for k,v in b.PLAN["common"].items():args+=["--"+k.replace("_","-"),str(v)]
        checkpoint(c,"STARTING_GUARDED_RUN");command(c,"guarded-run",args,90)
        b.state["network_runs_started"]+=1;checkpoint(c,"RUNNING")
        monitored=b.monitor(c);c["resource_samples"]={k:v for k,v in monitored.items() if k!="metadata"}
        checkpoint(c,"TERMINAL_TRANSFERRING");target=b.transfer(c)
        assert monitored["metadata"]["status"]=="SUCCEEDED",monitored["metadata"]
        assert monitored["min_sampled_available_gib"]>=4 and monitored["max_sampled_load_1m"]<=20
        fresh(c,"resources-after-run");checkpoint(c,"VERIFYING_DYNAMIC_BEHAVIOR")
        dynamic_analyze(c,target);c["status"]="PASS";save();print(c["id"]+" PASS",flush=True)
    b.state["status"]="COMPLETE_FOR_THREE_MAIN_MODE_DYNAMIC_TECHNICAL_CHECKS_ONLY";save();print(b.state["status"],flush=True)

def preserve_failure():
    for c in b.state["cells"]:
        folder=b.EVIDENCE/c["id"]
        if (folder/"results/metadata.json").exists():continue
        base="/home/fnl/lzy/results/"+c["id"]
        try:
            ok=b.remote("import os,json;p="+repr(base)+";print(json.dumps({'exists':os.path.isdir(p) and os.path.realpath(p)==p}))")
            if not ok["exists"]:continue
            target=folder/"failure-results"
            if target.exists():continue
            v=subprocess.run(["scp","-r","-o","BatchMode=yes","-o","StrictHostKeyChecking=yes",
                              b.CFG["REMOTE_USER"]+"@"+b.CFG["REMOTE_HOST"]+":"+base,str(target)],
                             capture_output=True,timeout=900)
            (folder/"failure-transfer.log").write_bytes(v.stdout+v.stderr)
        except BaseException as error:
            (folder/"failure-transfer-error.txt").write_text(str(error),encoding="utf-8")

if __name__=="__main__":
    try:main()
    except BaseException as error:
        why="COVERAGE_GAP" if isinstance(error,CoverageGap) else "FAILURE"
        b.state["status"]="STOPPED_ON_"+why;b.state["error"]=str(error);b.state["traceback"]=traceback.format_exc()
        for c in b.state["cells"]:
            if c["status"] in ("BUILT","NOT_STARTED"):c["status"]+="_NOT_RUN_DUE_TO_"+why
            elif c["status"] not in ("PASS","BUILD_FAILED"):
                c["status"]="STOPPED_ON_"+why
        save();print(b.state["status"]+" "+str(error),flush=True)
        (OUT/(PREFIX+"-driver-error.log")).write_text(traceback.format_exc(),encoding="utf-8")
        preserve_failure()
        raise
