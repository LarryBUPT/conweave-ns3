import sys
sys.dont_write_bytecode = True
import pathlib, json, hashlib, importlib.util, subprocess, re, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from fractions import Fraction

OUT = pathlib.Path(__file__).resolve().parent
PREFIX = "c2-label-validation-r1-attempt2"
spec = importlib.util.spec_from_file_location("dynamic_engine", str(OUT / "main-mode-dynamic-r1-driver.py"))
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
b = d.b
d.PREFIX = b.PREFIX = PREFIX
b.PLAN = json.loads((OUT / (PREFIX + "-frozen-plan.json")).read_text(encoding="utf-8"))
b.RECEIPT = OUT / (PREFIX + "-receipt.json")
b.EVIDENCE = OUT / "c2-label-validation-r1-evidence" / "attempt2"
b.EVIDENCE.mkdir(exist_ok=True)
b.state = {"scope": b.PLAN["scope"], "source_sha": b.PLAN["source_sha"], "status": "STARTING",
           "cells": [dict(c, status="NOT_STARTED") for c in b.PLAN["cells"]],
           "network_runs_started": 0, "commands": [], "core_status": "NOT_STARTED",
           "resource_scope": "5-second samples for one five-build batch; 2-second run samples; snapshots, not exact peaks",
           "plan_sha256": hashlib.sha256((OUT / (PREFIX + "-frozen-plan.json")).read_bytes()).hexdigest()}
assert b.state["plan_sha256"] == "96f81afe9eca873ab79faca540a14416c2421a420fc9eb81c96d1a0d0fbc3e46"
REF_ROOT = OUT / "main-mode-dynamic-r1-evidence"
ZERO_ROOT = OUT / "zero-control-pilot-r1-evidence"

def policy(tag, transform):
    return 0 if transform == 1 else 3-tag if transform == 2 and tag in (1, 2) else tag

def tuple_hash_wait(key):
    src, dst, sport, dport = key
    h = 2166136261 ^ 0x43c2a517
    for word in [(11 << 24) | (src << 8) | 1, (11 << 24) | (dst << 8) | 1, sport | (dport << 16)]:
        for j in range(4):
            h = ((h ^ ((word >> (8*j)) & 255)) * 16777619) & 0xffffffff
    h ^= h >> 16
    h = (h * 0x85ebca6b) & 0xffffffff
    h ^= h >> 13
    return h % 501

def trace_rows(path):
    lines = path.read_text(encoding="ascii").splitlines()
    sports, dports = defaultdict(lambda: 10000), defaultdict(lambda: 100)
    expected = {}
    for index, line in enumerate(lines[1:]):
        src, dst, pg, size, demand, tag = line.split()
        src, dst, pg, size, tag = map(int, (src, dst, pg, size, tag))
        key = (src, dst, sports[src], dports[dst])
        assert key not in expected
        expected[key] = {"index": index, "size": size, "tag": tag, "pg": pg,
                         "demand_ns": int(Fraction.from_float(float(demand)) * 10**9)}
        sports[src] += 1
        dports[dst] += 1
    assert len(expected) == int(lines[0])
    return expected

def ordered(path):
    hashes = {k: hashlib.sha256() for k in ["choice", "route", "combined", "choice_without_tag", "route_without_tag", "combined_without_tag"]}
    counts = {"choice": 0, "route": 0}
    routes = {}
    changes = 0
    tags = defaultdict(set)
    tables = {k: {} for k in ["DEMAND", "LAUNCH", "FINISH"]}
    states, queue, paths = [], [], []
    with path.open("rb") as stream:
        for line in stream:
            assert b"WS30_OBSERVATION_OVERFLOW" not in line
            if line.startswith((b"WS30_CHOICE ", b"WS30_ROUTE ")):
                kind = "choice" if line.startswith(b"WS30_CHOICE ") else "route"
                clean = re.sub(rb" uid=[^ \r\n]+", b"", line)
                hashes[kind].update(clean)
                hashes["combined"].update(clean)
                no_tag = re.sub(rb" tag=[^ \r\n]+", b"", clean)
                hashes[kind+"_without_tag"].update(no_tag)
                hashes["combined_without_tag"].update(no_tag)
                counts[kind] += 1
                if kind == "route":
                    v = d.fields(line.decode("ascii"))
                    key = ((v["sip"] >> 8) & 65535, (v["dip"] >> 8) & 65535, v["sport"], v["dport"])
                    assert v["sip"] == (11 << 24) | (key[0] << 8) | 1
                    assert v["dip"] == (11 << 24) | (key[1] << 8) | 1
                    tags[key].add(v["tag"])
                    hop = (v["switch"],) + key
                    if hop in routes and routes[hop] != v["port"]:
                        changes += 1
                    routes[hop] = v["port"]
            elif line.startswith(b"WS31_C2_"):
                prefix = line.split(b" ", 1)[0].decode("ascii")
                v = d.fields(line.decode("ascii"))
                if prefix == "WS31_C2_STATE":
                    states.append(v)
                else:
                    suffix = prefix[len("WS31_C2_"):]
                    assert suffix in tables, prefix
                    i = v["flow_id"]
                    assert i not in tables[suffix]
                    tables[suffix][i] = v
            elif line.startswith(b"WS30_QUEUE "):
                queue.append(d.fields(line.decode("ascii")))
            elif line.startswith(b"WS30_PATH "):
                paths.append(d.fields(line.decode("ascii")))
    assert changes == 0 and len(paths) == 1 and len(queue) == 1
    assert 0 < counts["route"] <= 1000000 and counts["choice"] > 0
    assert paths[0]["full_rows"] == paths[0]["data_hops"] == counts["route"]
    assert paths[0]["changed_qps"] == paths[0]["port_changes"] == paths[0]["rejected"] == 0
    q = queue[0]
    assert q["enqueued"] == q["dequeued"]
    for name in ["dropped", "current", "admission_dropped_bytes", "queue_rejected_bytes", "violations"]:
        assert q[name] == 0, (name, q[name])
    return {"hashes": {k: v.hexdigest() for k, v in hashes.items()}, "counts": counts,
            "within_qp_port_changes": changes, "path": paths[0], "queue": q,
            "packet_tags": tags, "tables": tables, "states": states}

def reference(results):
    fct = next((results / "raw").glob("*/*_out_fct.txt"))
    log = next((results / "raw").glob("*/config.log"))
    result = ordered(log)
    return {"fct": fct, "hashes": result["hashes"], "counts": result["counts"]}

def core():
    first = b.state["cells"][0]
    source = "/home/fnl/lzy/runs/" + first["id"] + "/source"
    base = "/home/fnl/lzy/results/" + first["id"]
    code = r'''
import os,json,subprocess,hashlib,datetime
source=SOURCE
base=BASE
assert subprocess.check_output(['git','-C',source,'rev-parse','HEAD']).decode().strip()==SHA
folder=base+'/technical/c2-core';assert not os.path.lexists(folder);os.makedirs(folder)
exe=folder+'/ws31-start-test';steps=[]
def run(name,args):
 path=base+'/logs/'+name+'.log';assert not os.path.lexists(path)
 with open(path,'wb') as f:code=subprocess.call(args,cwd=source,stdout=f,stderr=subprocess.STDOUT,timeout=180)
 steps.append({'name':name,'argv':args,'cwd':source,'exit_code':code,'log':path})
 if code:
  result={'status':'FAIL','steps':steps}
  with open(folder+'/receipt.json','w') as f:json.dump(result,f,indent=2)
  print(json.dumps(result));raise SystemExit(1)
run('c2-core-compile',['g++','-std=c++11','-O2','-Wall','-Wextra','-pedantic','tests/ws31_start_test.cc','-o',exe])
run('c2-core-run',[exe])
text=open(base+'/logs/c2-core-run.log').read()
symbols=subprocess.check_output(['nm','-C',exe]).decode()
assert '__assert_fail' in symbols
assert 'WS31_START_TEST PASS bounds/determinism/controls/fallback/demand-time/policy-tag' in text
assert '-DNDEBUG' not in steps[0]['argv']
result={'status':'PASS','steps':steps,'assertions_enabled_symbol':'__assert_fail','binary':exe,
 'binary_sha256':hashlib.sha256(open(exe,'rb').read()).hexdigest(),
 'source_hashes':{p:hashlib.sha256(open(source+'/'+p,'rb').read()).hexdigest() for p in ['tests/ws31_start_test.cc','src/point-to-point/model/ws31-start.h']},
 'compiler_version':subprocess.check_output(['g++','--version']).decode().splitlines()[0]}
with open(folder+'/receipt.json','w') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
'''.replace("SOURCE", repr(source)).replace("BASE", repr(base)).replace("SHA", repr(b.PLAN["source_sha"]))
    result = b.remote(code, timeout=400)
    (OUT / (PREFIX + "-core-receipt.json")).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    assert result["status"] == "PASS"
    for path, h in result["source_hashes"].items():
        blob = subprocess.check_output(["git", "-C", str(b.REPO), "show", b.PLAN["source_sha"]+":"+path])
        assert hashlib.sha256(blob).hexdigest() == h
    b.state["core_status"] = "PASS"
    d.save()

def analyze(cell, target, references):
    meta = json.loads((target / "metadata.json").read_text(encoding="utf-8"))
    assert meta["status"] == "SUCCEEDED" and meta["git_commit"] == b.PLAN["source_sha"]
    assert meta["build_mode"] == "optimized" and meta["cpu_jobs"] == 2 and meta["concurrency_cap"] == 1
    for k, v in b.PLAN["common"].items():
        if k != "max_concurrent":
            assert meta["parameters"][k] == v, k
    assert meta["parameters"]["lb"] == cell["lb"]
    assert meta["parameters"]["flow_file"] == cell["flow_file"]
    assert meta["parameters"]["ws30_tag_transform"] == cell["ws30_tag_transform"]
    for k in ["ws30_composition", "ws30_lifecycle", "ws30_life_profile", "ws13_diag", "ws25_diag",
              "ws28_tail_diag", "ws21_heartbeat", "ws21_feedback", "ws21_identity", "ws18_admission", "ws18_path"]:
        assert not meta["parameters"].get(k, 0), k
    for file, key in [("traffic_trace.txt", "config/"+cell["flow_file"]),
                      ("topology.txt", "config/leaf_spine_128_100G_OS2.txt")]:
        assert hashlib.sha256((target / "config" / file).read_bytes()).hexdigest() == b.PLAN["inputs"][key]
    expected = trace_rows(target / "config/traffic_trace.txt")
    assert len(expected) == cell["flow_count"] and sum(v["size"] for v in expected.values()) == cell["payload_bytes"]
    fct = next((target / "raw").glob("*/*_out_fct.txt"))
    log = next((target / "raw").glob("*/config.log"))
    args = [sys.executable, "-B", str(OUT / (PREFIX+"-verifier.py")),
            str(target / "config/traffic_trace.txt"), str(fct), "--log", str(log)]
    name = cell["id"].split("-r1-", 1)[1]
    paired = references.get("default" if name == "default" else "zero" if name == "remove" else "unknown" if name == "unknown-c2" else "")
    if paired:
        args += ["--equal-fct", str(paired["fct"])]
    d.command(cell, "all-input-verifier", args, 120)
    verified = json.loads((b.EVIDENCE / cell["id"] / "all-input-verifier.log").read_text(encoding="utf-8"))
    assert verified["flows"] == cell["flow_count"] and verified["payload_bytes"] == cell["payload_bytes"]
    obs = ordered(log)
    assert set(obs["packet_tags"]) == set(expected)
    for key, values in obs["packet_tags"].items():
        assert values == {policy(expected[key]["tag"], cell["ws30_tag_transform"])}, (key, values)
    config = dict(row.split(None, 1) for row in (target/"config/config.txt").read_text(encoding="ascii").splitlines() if row.strip())
    assert config["CC_MODE"] == "1" and config["ENABLE_PFC"] == "0" and config["ENABLE_IRN"] == "1"
    assert config["BUFFER_SIZE"] == "9" and config["RANDOM_SEED"] == "1"
    completed = {tuple(v[:4]): v for v in (list(map(int, line.split())) for line in fct.read_text(encoding="ascii").splitlines())}
    timing = []
    if cell["lb"] == "ws31-c2":
        ids = set(range(len(expected)))
        for table in obs["tables"].values():
            assert set(table) == ids
        for key, e in expected.items():
            i = e["index"]
            dem, launch, finish = (obs["tables"][kind][i] for kind in ["DEMAND", "LAUNCH", "FINISH"])
            tag = policy(e["tag"], cell["ws30_tag_transform"])
            wait = tuple_hash_wait(key) if tag == 2 else 0
            assert dem["tag"] == e["tag"] and dem["policy_tag"] == tag
            assert dem["tag_transform"] == cell["ws30_tag_transform"]
            assert dem["size"] == launch["size"] == finish["size"] == e["size"]
            assert dem["delay_ns"] == launch["wait_ns"] == finish["wait_ns"] == wait
            assert dem["demand_ns"] == launch["demand_ns"] == finish["demand_ns"] == completed[key][5] == e["demand_ns"]
            assert launch["launch_ns"] == finish["launch_ns"] == e["demand_ns"] + wait
            assert finish["finish_ns"] >= launch["launch_ns"]
            assert finish["fct_ns"] == completed[key][6] == finish["finish_ns"] - e["demand_ns"]
            timing.append({"key": key, "flow_id": i, "business_tag": e["tag"], "policy_tag": tag,
                           "tag_transform": cell["ws30_tag_transform"], "wait_ns": wait,
                           "demand_ns": e["demand_ns"], "launch_ns": launch["launch_ns"],
                           "finish_ns": finish["finish_ns"], "size": e["size"]})
        assert verified["c2_timing_rows_checked"] == len(expected) and len(obs["states"]) == 1
        s = obs["states"][0]
        for k in ["demanded", "launched", "finished"]:
            assert s[k] == len(expected)
        for k in ["cancelled", "pending", "unfinished", "cancel_bytes"]:
            assert s[k] == 0
        for k in ["demand_bytes", "launch_bytes", "finish_bytes"]:
            assert s[k] == cell["payload_bytes"]
        assert s["waited"] == sum(v["wait_ns"] > 0 for v in timing)
        assert s["delay_sum_ns"] == sum(v["wait_ns"] for v in timing)
        assert s["delay_max_ns"] == max(v["wait_ns"] for v in timing)
        assert s["frozen_max_ns"] == 500
    else:
        assert not obs["states"] and not any(obs["tables"].values())
    if paired:
        keys = ["choice_without_tag", "route_without_tag", "combined_without_tag"] if name == "remove" else ["choice", "route", "combined"]
        assert obs["counts"] == paired["counts"]
        for k in keys:
            assert obs["hashes"][k] == paired["hashes"][k], (name, k)
    if name == "default":
        if not any(v["wait_ns"] > 0 and v["business_tag"] == 2 for v in timing):
            raise d.CoverageGap("Default cell lacks required positive tag2 wait")
        assert all(v["wait_ns"] == 0 for v in timing if v["business_tag"] == 1)
    elif name == "remove":
        assert all(v["wait_ns"] == v["policy_tag"] == 0 for v in timing)
    elif name == "swap":
        if not any(v["wait_ns"] > 0 and v["business_tag"] == 1 for v in timing):
            raise d.CoverageGap("Swap cell lacks required newly eligible positive wait")
        assert all(v["wait_ns"] == 0 for v in timing if v["business_tag"] == 2)
    elif name == "unknown-c2":
        assert {v["business_tag"] for v in timing} == {0, 7, 99}
        assert all(v["policy_tag"] == v["business_tag"] and v["wait_ns"] == 0 for v in timing)
    if name == "unknown-q12":
        references["unknown"] = {"fct": fct, "hashes": obs["hashes"], "counts": obs["counts"]}
    result = {"status": "PASS", "name": name, "all_input_verifier": verified,
              "ordered_hashes": obs["hashes"], "observation_counts": obs["counts"],
              "path": obs["path"], "queue": obs["queue"], "timing": timing,
              "c2_state": obs["states"], "packet_tags_per_input_tuple": [{"key": key, "tags": sorted(v)} for key, v in obs["packet_tags"].items()],
              "original_business_counts": {str(tag): sum(e["tag"] == tag for e in expected.values()) for tag in sorted({e["tag"] for e in expected.values()})},
              "original_business_bytes": {str(tag): sum(e["size"] for e in expected.values() if e["tag"] == tag) for tag in sorted({e["tag"] for e in expected.values()})},
              "pair_reference_fct": str(paired["fct"]) if paired else None,
              "label_normalization": "remove only uid; remove cell additionally removes intentionally changed tag for comparison and independently requires packet tag0"}
    (b.EVIDENCE/cell["id"]/"acceptance.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    cell["acceptance"] = result
    d.save()

def main():
    assert not b.RECEIPT.exists(), "Never overwrite/re-run frozen IDs"
    d.save()
    fork = b.controller.local_fork(str(b.REPO), require_pushed=True)
    assert fork[3] == b.PLAN["source_sha"]
    for c in b.state["cells"]:
        folder = b.EVIDENCE/c["id"]
        assert not folder.exists()
        folder.mkdir()
    ids = [c["id"] for c in b.state["cells"]]
    assert b.remote("import os,json;ids="+repr(ids)+";print(json.dumps({'fresh':all(not os.path.lexists('/home/fnl/lzy/'+p+'/'+i) for i in ids for p in ['runs','results'])}))")["fresh"]
    expected = hashlib.sha256((b.REPO/"scripts/remote_worker.py").read_bytes()).hexdigest()
    assert b.remote("import hashlib,json;print(json.dumps({'h':hashlib.sha256(open('/home/fnl/lzy/.research-workflow/remote_worker.py','rb').read()).hexdigest()}))")["h"] == expected
    b.state["deployed_worker_sha256"] = expected
    initial = d.fresh(b.state["cells"][0], "resources-batch-before")
    cache = json.loads((OUT / (PREFIX + "-cache-prerequisite.json")).read_text(encoding="utf-8"))
    assert cache["ids_uncreated"] and not cache["active_prior_driver_or_monitor"]
    assert cache["cache_realpath"] == "/home/fnl/lzy/code/conweave-ns3"
    assert cache["origin"] == "https://github.com/LarryBUPT/conweave-ns3.git" and not cache["clean_status"]
    assert cache["commit_exists"] and cache["origin_branch_sha"] == b.PLAN["source_sha"]
    b.state["cache_reuse_prerequisite"] = PREFIX + "-cache-prerequisite.json"
    b.state["environment_pause_history"] = "c2-label-validation-r1-evidence/attempt1/manifest.json"
    b.state["network_fetch_repeated"] = False
    print("VERIFIED_CACHE_REUSE no repeated fetch", flush=True)
    cap = 3 if initial["available_gib"] >= 64 and initial["free_gib"] >= 100 and initial["loadavg"][0] <= 4 else 1
    b.state["parallel_builds_admitted"] = cap
    b.state["max_compile_jobs_admitted"] = cap*2
    b.state["build_waves"] = []
    d.save()
    print("BUILD_BATCH cap=%d jobs=%d cells=5"%(cap, cap*2), flush=True)
    errors = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        sampler = pool.submit(d.build_sampler)
        cursor = 0
        while cursor < len(b.state["cells"]):
            fresh = d.fresh(b.state["cells"][cursor], "resources-before-build-wave")
            # One five-build batch: strict <=4 initial-load admission above, worker <=20 ongoing guard.
            width = min(cap if fresh["available_gib"] >= 64 and fresh["free_gib"] >= 100 else 1, len(b.state["cells"])-cursor)
            group = b.state["cells"][cursor:cursor+width]
            b.state["build_waves"].append([c["id"] for c in group])
            d.save()
            futures = [pool.submit(d.do_build, c) for c in group]
            for f in as_completed(futures):
                try:
                    f.result()
                except BaseException as error:
                    errors.append(str(error))
            if errors:
                break
            cursor += width
            if cursor < len(b.state["cells"]):
                first = "/home/fnl/lzy/results/"+ids[0]+"/logs/resource-build-batch-samples.jsonl"
                observed = b.remote("import json;rows=[json.loads(x) for x in open("+repr(first)+")];print(json.dumps({'clean':not any(x['other_user_pids'] or x['unknown_project_pids'] for x in rows)}))")
                if not observed["clean"]:
                    errors.append("Other-user/project work sampled; no next build wave")
                    break
        first = "/home/fnl/lzy/results/"+ids[0]+"/logs"
        b.remote("import os,json;p="+repr(first)+";assert os.path.realpath(p)==p;open(p+'/build-batch-monitor-stop.json','w').write('{}');print(json.dumps({'stopped':True}))")
        sampled = sampler.result()
    b.state["build_batch_samples"] = sampled
    d.save()
    if errors:
        raise RuntimeError("; ".join(errors))
    assert not sampled["other_user_seen"] and not sampled["unknown_project_seen"]
    assert sampled["min_sampled_available_gib"] >= 4 and sampled["min_sampled_free_gib"] >= 20 and sampled["max_sampled_load_1m"] <= 20
    d.verify_builds()
    b.state["all_builds_verified_before_any_run"] = True
    d.fresh(b.state["cells"][0], "resources-before-core")
    core()
    references = {"default": reference(REF_ROOT/"20261101-071042-ws31-dyn-r1-c2/results"),
                  "zero": reference(ZERO_ROOT/"20261101-062753-ws31-zr1-q12/results")}
    d.save()
    for c in b.state["cells"]:
        d.checkpoint(c, "RESOURCE_GATE_BEFORE_RUN")
        d.fresh(c, "resources-before-run")
        args = [sys.executable, "-B", str(b.REPO/"scripts/remote_experiment.py"), "run", c["id"], "--lb", c["lb"],
                "--flow-file", c["flow_file"], "--ws30-tag-transform", str(c["ws30_tag_transform"])]
        for k, v in b.PLAN["common"].items():
            args += ["--"+k.replace("_", "-"), str(v)]
        d.checkpoint(c, "STARTING_GUARDED_RUN")
        d.command(c, "guarded-run", args, 90)
        b.state["network_runs_started"] += 1
        d.checkpoint(c, "RUNNING")
        monitored = b.monitor(c)
        c["resource_samples"] = {k: v for k, v in monitored.items() if k != "metadata"}
        d.checkpoint(c, "TERMINAL_TRANSFERRING")
        target = b.transfer(c)
        assert monitored["metadata"]["status"] == "SUCCEEDED"
        assert monitored["min_sampled_available_gib"] >= 4 and monitored["max_sampled_load_1m"] <= 20
        d.fresh(c, "resources-after-run")
        d.checkpoint(c, "VERIFYING_LABELS_TIMING_AND_REGRESSIONS")
        analyze(c, target, references)
        c["status"] = "PASS"
        d.save()
        print(c["id"]+" PASS", flush=True)
    b.state["status"] = "COMPLETE_FOR_C2_DECISION_LABEL_TECHNICAL_ACCEPTANCE_ONLY"
    d.save()
    print(b.state["status"], flush=True)

if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        reason = "COVERAGE_GAP" if isinstance(error, d.CoverageGap) else "FAILURE"
        b.state["status"] = "STOPPED_ON_"+reason
        b.state["error"] = str(error)
        b.state["traceback"] = traceback.format_exc()
        for c in b.state["cells"]:
            if c["status"] in ("BUILT", "NOT_STARTED"):
                c["status"] += "_NOT_RUN_DUE_TO_"+reason
            elif c["status"] not in ("PASS", "BUILD_FAILED"):
                c["status"] = "STOPPED_ON_"+reason
        d.save()
        print(b.state["status"]+" "+str(error), flush=True)
        (OUT/(PREFIX+"-driver-error.log")).write_text(traceback.format_exc(), encoding="utf-8")
        d.preserve_failure()
        raise
