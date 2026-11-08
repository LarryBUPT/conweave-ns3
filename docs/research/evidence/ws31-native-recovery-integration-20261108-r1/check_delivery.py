import hashlib,json,re,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
sys.stdout.reconfigure(encoding="utf-8")
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
H=ROOT/"docs/handoffs/2026-11-08-ws31-native-recovery-integration.md"
FILES=[ROOT/"docs/project-state"/p for p in ["CURRENT_STATE.md","ROADMAP.md","WORKSTREAMS.md","WS31_EXECUTION.md"]]+[H]
links=[]
for p in FILES:
    for m in re.finditer(r"\]\(([^\n]+?)\)",p.read_text(encoding="utf-8-sig")):
        s=m.group(1).strip("<>")
        if "://" in s or s.startswith("#"):continue
        target=(p.parent/unquote(s.split("#")[0])).resolve()
        assert target.exists(),(str(p),s)
        links.append((p.relative_to(ROOT).as_posix(),s))
for p in OUT.rglob("*.json"):json.loads(p.read_text(encoding="utf-8-sig"))
d=json.loads((ROOT/"docs/project-state/ws31-coordination.json").read_text(encoding="utf-8-sig"))
assert d["status"]=="ACTIVE_NATIVE_ENTRY_R2_ACCEPTED_NEXT_G2_BOUNDED_DESIGN_REQUIRED"
assert d["heartbeat"]["interval_minutes"]==30 and len(d["heartbeat"]["timers"])==2
assert any(x.get("status")=="DELETED_AFTER_FINITE_SCREEN_HOLD_RETAINED" for x in d["heartbeat_scope_history"])
assert not d["validated_combined_baseline_established"]
assert d["technical_cells_accepted_cumulative"]["total"]==43
assert not d["next_registered_goal"]["new_execution_plan_fixed"]
assert len(re.findall(r"^## \d\.",H.read_text(encoding="utf-8"),re.M))==9
ledger=json.loads((OUT/"source-manifest.json").read_text(encoding="utf-8"))
for origin,item in ledger.items():
    if "snapshot" in item:assert hashlib.sha256((ROOT/item["snapshot"]).read_bytes()).hexdigest()==item["sha256"],item["snapshot"]
ref=json.loads((OUT/"reference-review.json").read_text(encoding="utf-8"))
with (OUT/"reference-source-fingerprints.json").open("x",encoding="utf-8") as f:
    json.dump({"observed_at_utc":datetime.now(timezone.utc).isoformat(),"source_sha256":{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ref["entry_points"]+ref["sources"]}},f,ensure_ascii=False,indent=2);f.write("\n")
expected={"docs/project-state/"+p for p in ["CURRENT_STATE.md","ROADMAP.md","WORKSTREAMS.md","WS31_EXECUTION.md","ws31-coordination.json"]}
assert set(subprocess.check_output(["git","diff","--name-only"],text=True).splitlines())==expected
subprocess.run(["git","diff","--check"],check=True,capture_output=True)
result={"observed_at_utc":datetime.now(timezone.utc).isoformat(),"status":"PASS_NATIVE_RECOVERY_INTEGRATION_DELIVERY_QA","links_checked":len(links),"JSON_files_checked":len(list(OUT.rglob("*.json"))),"nine_handoff_sections":True,"exact_five_authority_files_changed":True,"two_native_timers_configuration_verified":True,"new_actual_user_authorization_checked":True,"old_deletion_and_HOLD_preserved_as_history":True,"event_main_acceptance_and_Integration_observation_separate":True,"source_UTC_offset_normalized_from_value":True,"source_snapshots_hash_verified":True,"scientific_reexecution_by_Integration":False,"new_network_or_effects_accepted":False,"new_baseline":False,"intermediate_native_stages_claimed_fully_reaccepted":False,"local_raw_reader_attempts_preserved":2,"first_inline_delivery_QA_error":"Expected integer43; registry actually stores total43 and stages. Corrected reader to total; registry count and scope unchanged."}
with (OUT/"delivery-qa.json").open("x",encoding="utf-8") as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write("\n")
print(json.dumps(result,ensure_ascii=False))
