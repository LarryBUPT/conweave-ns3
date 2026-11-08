import hashlib,json,re,subprocess,sys,tarfile,tomllib
from datetime import datetime,timezone,timedelta
from pathlib import Path,PurePosixPath
sys.stdout.reconfigure(encoding="utf-8")
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
BASE=ROOT/"docs/research/ws31"
ledger={}
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def local(p):
    p=Path(p).resolve()
    assert p.is_relative_to(Path("E:/研/毕业论文").resolve()),str(p)
    return p
def capture(p,bucket="documents"):
    p=local(p); key=p.as_posix(); digest=sha(p)
    ledger[key]={"bytes":p.stat().st_size,"sha256":digest}
    if bucket:
        target=OUT/"snapshots"/bucket/(digest[:16]+"-"+p.name)
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            with target.open("xb") as f:f.write(p.read_bytes())
        assert sha(target)==digest
        ledger[key]["snapshot"]=target.relative_to(ROOT).as_posix()
    return digest
def bound(item,bucket="documents"):
    p=local(item["path"]);assert sha(p)==item["sha256"],str(p)
    if "bytes" in item:assert p.stat().st_size==item["bytes"]
    capture(p,bucket);return p
def fresh_json(name,value):
    with (OUT/name).open("x",encoding="utf-8",newline="\n") as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write("\n")
def utc(s):return datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(timezone.utc)
RUN="20261108-152638-ws31-native-entry-r2"
COMMIT="21b440985f90d2081438e435ef640adc9f43a42d"
BEIJING=timezone(timedelta(hours=8))
# Direct human instruction in the authentic current main turn, rather than an old retained user message.
session=Path("C:/Users/Administrator/.codex/sessions/2026/11/01/rollout-2026-11-01T02-04-39-01a19322-95a5-76e3-a4f5-1f1e9dde81ce.jsonl")
found=[];active=False
for n,line in enumerate(session.open(encoding="utf-8"),1):
    r=json.loads(line);p=r.get("payload",{})
    if r.get("type")=="turn_context":active=p.get("turn_id")=="01a1ba03-e440-7853-a726-eb9f829b6a2d"
    if active and r.get("type")=="response_item" and p.get("role")=="user":
        text="\n".join(x.get("text","") for x in p.get("content",[]) if isinstance(x,dict))
        if text.startswith("请读取 E:/研/毕业论文/dev-group/state/ws31-supervision/native-recovery-r2.json"):
            found.append({"source":str(session),"line":n,"event_time_utc":r["timestamp"],"record_sha256":hashlib.sha256(line.encode()).hexdigest(),"text":text,"turn_id":"01a1ba03-e440-7853-a726-eb9f829b6a2d"})
assert len(found)==1
fresh_json("user-instruction.json",found[0])
capture(Path("E:/研/毕业论文/dev-group/state/ws31-supervision/native-recovery-r2.json"))
native_dir=BASE/"main/evidence/native-supervision-r2"
native=read(native_dir/"native-acceptance.json");capture(native_dir/"native-acceptance.json")
bound({"path":native["activation_readback"],"sha256":native["activation_sha256"]})
timers=[]
for t in native["verified_timers"]:
    for field,hkey in [("tool_receipt","tool_receipt_sha256"),("creation_receipt","creation_receipt_sha256"),("configuration_snapshot","configuration_sha256")]:
        bound({"path":t[field],"sha256":t[hkey]},"supervision")
    p=Path("C:/Users/Administrator/.codex/automations")/t["automation_id"]/"automation.toml"
    actual=tomllib.loads(p.read_text(encoding="utf-8"))
    assert actual["kind"]=="heartbeat" and actual["status"]=="ACTIVE"
    assert actual["target_thread_id"]==t["target_thread_id"]
    assert actual["rrule"]=="FREQ=MINUTELY;INTERVAL=30"
    assert actual["created_at"]==t["created_at_epoch_ms"] and actual["updated_at"]==t["updated_at_epoch_ms"]
    # Persisted snapshots are byte-checked against the original native-operation snapshots.
    assert sha(p)==t["configuration_sha256"]
    dest=OUT/"snapshots/supervision"/(t["automation_id"]+"-observed.toml")
    with dest.open("xb") as f:f.write(p.read_bytes())
    timers.append({"automation_id":t["automation_id"],"target_thread_id":t["target_thread_id"],"status":"ACTIVE","interval_minutes":30,"created_at_utc":datetime.fromtimestamp(actual["created_at"]/1000,timezone.utc).isoformat(),"configuration_sha256":sha(p),"creation_receipt":t["creation_receipt"],"native_view_limit":"Rendered card only; persisted configuration separately verified","scheduler_firing_observed_by_Integration":False})
assert {x["automation_id"] for x in timers}=={"ws-31","ws-31-2"}
qa=read(native_dir/"supervision-acceptance-qa.json");assert qa["status"].startswith("PASS_SUPERVISION_N1_N2_N3_N4")
capture(native_dir/"supervision-acceptance-qa.json")
checks=read(native_dir/"final-checks.json");capture(native_dir/"final-checks.json")
for c in checks["checks"]:
    for stream in ["stdout","stderr"]:bound({"path":c[stream],"sha256":c[stream+"_sha256"]})
assert checks["checks"][0]["actual_exit"]==1 and checks["checks"][1]["actual_exit"]==0
assert "CC_SESSION_KEY" in Path(checks["checks"][0]["stderr"]).read_text(encoding="utf-8")
# Both old failed R1 and new terminal R2 are checked locally; no command in either plan is executed.
counts={}
for version,expected_count,expected_members in [("r1",65,25),("r2",202,147)]:
    evpath=BASE/("independent/native-entry-execution-"+version+"-evidence.json")
    ev=read(evpath);capture(evpath)
    raw=BASE/("independent/native-entry-execution-"+version+"-raw")
    mpath=bound(ev["raw_manifest"]);manifest=read(mpath)
    members=manifest["files"];assert isinstance(members,list)
    seen=set()
    for item in members:
        rel=PurePosixPath(item["relative_path"]);assert not rel.is_absolute() and ".." not in rel.parts
        p=(raw/rel.as_posix()).resolve();assert p.is_relative_to(raw.resolve()) and rel.as_posix() not in seen
        seen.add(rel.as_posix());assert p.stat().st_size==item["bytes"] and sha(p)==item["sha256"],str(p)
    assert len(members)+1==expected_count
    archive=local(ev["transfer"]["local_archive"])
    assert sha(archive)==ev["transfer"]["local_archive_sha256"]
    count=0; names=set()
    with tarfile.open(archive,"r|gz") as tf:
        for member in tf:
            if member.isdir():continue
            assert member.isfile()
            rel=PurePosixPath(member.name);assert not rel.is_absolute() and ".." not in rel.parts
            assert rel.as_posix() not in names;names.add(rel.as_posix())
            p=raw/"remote-result"/rel.as_posix()
            data=tf.extractfile(member).read()
            assert len(data)==member.size==p.stat().st_size and hashlib.sha256(data).hexdigest()==sha(p),str(p)
            count+=1
    assert count==expected_members
    capture(BASE/("independent/native-entry-execution-"+version+"-report.md"))
    counts[version]={"raw_files_with_manifest":len(members)+1,"transfer_archive_members":count,"archive_sha256":sha(archive)}
ev=read(BASE/"independent/native-entry-execution-r2-evidence.json")
plan=read(bound(ev["plan"]));pub=read(bound(ev["publication"]))
bound(ev["tree_manifest"]);bound(ev["source_archive"],None)
source_repo=local(pub["source_root"])
assert subprocess.check_output(["git","rev-parse",COMMIT],cwd=source_repo,text=True).strip()==COMMIT
assert subprocess.check_output(["git","rev-parse",COMMIT+"^"],cwd=source_repo,text=True).strip()==pub["parent"]
assert subprocess.check_output(["git","diff","--name-only",pub["parent"],COMMIT],cwd=source_repo,text=True).splitlines()==["src/point-to-point/wscript"]
diff=subprocess.check_output(["git","diff","--unified=0",pub["parent"],COMMIT,"--","src/point-to-point/wscript"],cwd=source_repo,text=True)
added=[x for x in diff.splitlines() if x.startswith("+") and not x.startswith("+++")]
deleted=[x for x in diff.splitlines() if x.startswith("-") and not x.startswith("---")]
assert len(added)==1 and not deleted and "ws31-v2-native-declarations.h" in added[0]
tree=read(Path(ev["tree_manifest"]["path"]))
assert len(tree)==4870
actual_tree={}
for item in subprocess.check_output(["git","ls-tree","-rz","--full-tree",COMMIT],cwd=source_repo).split(b"\0"):
    if not item:continue
    meta,path=item.split(b"\t",1);mode,kind,oid=meta.decode().split()
    actual_tree[path.decode()]={"mode":mode,"git_blob":oid}
assert set(actual_tree)==set(tree)
source_count=0
with tarfile.open(Path(ev["source_archive"]["path"]),"r|gz") as tf:
    for m in tf:
        if m.isdir():continue
        assert m.isfile();rel=PurePosixPath(m.name).as_posix()
        assert rel in tree and ".." not in PurePosixPath(rel).parts
        data=tf.extractfile(m).read();item=tree[rel]
        assert item["bytes"]==len(data) and item["sha256"]==hashlib.sha256(data).hexdigest()
        assert item["git_blob"]==hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
        assert actual_tree[rel]=={"mode":item["mode"],"git_blob":item["git_blob"]}
        source_count+=1
assert source_count==4870
raw=BASE/"independent/native-entry-execution-r2-raw";run=raw/"remote-result/execution"
terminal=read(bound(ev["terminal_verification"]))
assert terminal["source_commit"]==COMMIT and terminal["worker_absent"] and terminal["source_unchanged"]
for path,item in tree.items():
    actual=terminal["actual_source_identities"][path]
    assert actual["bytes"]==item["bytes"] and actual["sha256"]==item["sha256"]
receipt=read(run/"receipt.json");state=read(run/"worker-state.json");commands=read(run/"commands.json")
for p in ["receipt.json","worker-state.json","commands.json","worker-identity.json","case-admission-request.json","case-admission.json","case-admission-accepted.json","post-build-resource-gate.json","elf-manifest.json"]:
    capture(run/p,"raw")
assert receipt["run_id"]==RUN and receipt["source_commit"]==COMMIT and state["status"]=="PASS"
assert receipt["cases"]==state["completed_cases"]==plan["fixture_cases"]
assert len(commands)==24 and len({x["pid"] for x in commands[4:]})==20
assert [x["name"] for x in commands[:4]]==["compiler-version","configure","build","ldd"]
assert commands[2]["argv"]==["./waf","-j2"]
assert all(c["actual_exit"]==0 and not c["timeout"] for c in commands)
assert [c["name"] for c in commands[4:]]==["case-"+n for n in plan["fixture_cases"]]
for c in commands:
    for stream in ["stdout","stderr"]:assert sha(run/(c["name"]+"."+stream))==c[stream+"_sha256"]
request=read(run/"case-admission-request.json");gate=read(run/"case-admission.json");accepted=read(run/"case-admission-accepted.json");resource=read(run/"post-build-resource-gate.json")
assert gate["request_sha256"]==sha(run/"case-admission-request.json")==accepted["request_sha256"]
assert gate["resource_receipt_sha256"]==sha(run/"post-build-resource-gate.json")==accepted["receipt_sha256"]
assert accepted["gate_sha256"]==sha(run/"case-admission.json")
assert request["completed_cases"]==accepted["completed_cases_before_release"]==[]
assert request["requested_epoch_s"]>=commands[2]["started_epoch_s"]+commands[2]["elapsed_s"]
assert commands[4]["started_epoch_s"]>=utc(accepted["accepted_utc"]).timestamp()
assert commands[-1]["started_epoch_s"]-resource["observed_epoch_s"]<=60
assert not (run/"case-admission-revoked.json").exists()
elf=read(run/"elf-manifest.json");binary=run/"elf/ws31-v2-native-entry-check"
assert binary.read_bytes()[:4]==b"\x7fELF" and sha(binary)==elf["binary_sha256"]==ev["binary"]["sha256"]
assert len(elf["libraries"])==36
for name,item in elf["libraries"].items():assert sha(run/"elf"/name)==item["sha256"]
for _,item in terminal["all_built_ns3_libraries"].items():
    p=raw/"remote-result"/item["copy_relative_path"];assert p.stat().st_size==item["bytes"] and sha(p)==item["sha256"]
inputs={}
for family,item in plan["input_files"].items():
    p=local(next(x["path"] for x in plan["input_sources"] if x["family"]==family))
    assert sha(p)==item["sha256"]
    inputs[family]=[list(map(int,l.split())) for l in p.read_text(encoding="ascii").splitlines()[3:]]
    assert len(inputs[family])==1120
    capture(p,"inputs")
def wait(r,mode,policy):
    if mode!=43 or policy!=2:return 0
    h=2166136261^0x43c2a517
    for word in (r[4],r[5],r[12]|r[13]<<16):
        for shift in range(0,32,8):h=((h^((word>>shift)&255))*16777619)&0xffffffff
    h^=h>>16;h=h*0x85ebca6b&0xffffffff;h^=h>>13
    return h%501
cases={};packet_total=0
for name in plan["fixture_cases"]:
    p=run/("case-"+name+".stdout");lines=p.read_text(encoding="utf-8").splitlines()
    passes=[x for x in lines if x.startswith("WS31_V2_NATIVE_ENTRY_PASS ")]
    assert len(passes)==1
    fields=dict(x.split("=",1) for x in passes[0].split()[1:])
    packets=[dict(x.split("=",1) for x in line.split()[1:]) for line in lines if line.startswith("ENTRY_PACKET ")]
    mode=43 if name in plan["object_parameters"]["mode43_cases"] else 12
    for row in packets:
        i=int(row["ordinal"]);r=inputs[plan["case_family"][name]][i];present,policy=r[10],r[11]
        if name=="policy-variants" and i in [0,1,2,16]:present,policy={0:(1,1),1:(0,0),2:(1,99),16:(1,2)}[i]
        values={"id":r[0],"src":r[2],"dst":r[3],"sport":r[12],"dport":r[13],"pg":r[6],"bytes":r[7],"original":r[9],"present":present,"policy":policy,"demand_ns":r[8],"delay_ns":wait(r,mode,policy if present else 0)}
        assert all(int(row[k])==v for k,v in values.items()),(name,i)
    if name in ["entry-d1","entry-d2","nonzero-install","policy-variants"]:assert len(packets)==1120
    elif name in ["postrun-live-map","postrun-context"]:assert len(packets)==1
    else:assert not packets
    assert fields["network"]==fields["completion"]==fields["generation"]=="0"
    packet_total+=len(packets);cases[name]={"fields":fields,"packet_rows":len(packets)}
    capture(p,"cases")
assert packet_total==4482
accept=read(native_dir/"r2-terminal-main-acceptance.json")
assert accept["source_commit"]==COMMIT and not accept["full_G2_complete"] and not accept["new_baseline"]
bound({"path":accept["main_raw_verification"],"sha256":accept["main_raw_verification_sha256"]})
for p in ["r1-failure-main-acceptance-and-release.json","r2-terminal-main-acceptance.json","after-export-audit.json","export-review-main-acceptance.json"]:
    capture(native_dir/p)
capture(BASE/"main/native-supervision-and-entry-recovery-handoff-r2.md")
capture(BASE/"main/current-status.json")
capture(ROOT/"docs/research/evidence/ws31-heartbeat-stop-integration-20261104-r1/verification.json","history")
now=datetime.now(timezone.utc).isoformat()
result={"status":"PASS_INTEGRATION_LOCAL_R1_R2_PROVENANCE_AND_BOUNDED_RAW_CHECK","observed_at_utc":now,"user_authorization":found[0],"timers":timers,"r1":counts["r1"],"r2":counts["r2"],"fixed_source":COMMIT,"source_parent":pub["parent"],"source_archive_and_Git_paths":source_count,"terminal_source_identities_checked":len(terminal["actual_source_identities"]),"actual_commands":len(commands),"actual_cases":len(cases),"case_results":cases,"packet_rows_independently_checked":packet_total,"ELF_and_project_libraries_checked":1+len(elf["libraries"]),"build_elapsed_seconds":commands[2]["elapsed_s"],"completed_event_time_utc":receipt["finished_utc"],"completed_event_time_beijing":utc(receipt["finished_utc"]).astimezone(BEIJING).isoformat(),"main_acceptance_observed_at_utc":accept["observed_at_utc"],"integration_observed_at_utc":now,"native_receipt_observed_at_utc_normalized":utc(native["observed_at_utc"]).isoformat(),"source_time_note":"Native receipt field named observed_at_utc carries +08:00; original bytes retained and normalization uses the supplied offset, never the field name.","old_deletion_history_preserved":True,"WIP_full_preservation_scope":"Main/deputy full 4870+4868 byte audits retained and evidence-bound; Integration independently checked source archive/Git/terminal provenance, not a repeat of every current working-file guard.","network_runs":0,"full_G2_complete":False,"new_baseline":False,"scientific_performance_accepted":False,"no_compilation_fixture_simulation_or_ssh_by_Integration":True,"reference_review":{"version":"arXiv:2407.09808v1","borrowed":"Separate original request identity, actual QP and ultimate completion; account for all children before claiming parent completion.","difference":"Current finite unattached-object entry checks do not implement SeqBalance WQE splitting/CQE aggregation.","no_external_performance_or_hardware_cost_transfer":True}}
fresh_json("verification.json",result)
fresh_json("source-manifest.json",ledger)
print(json.dumps({k:result[k] for k in ["status","r1","r2","source_archive_and_Git_paths","actual_commands","actual_cases","packet_rows_independently_checked","network_runs"]},ensure_ascii=False))

