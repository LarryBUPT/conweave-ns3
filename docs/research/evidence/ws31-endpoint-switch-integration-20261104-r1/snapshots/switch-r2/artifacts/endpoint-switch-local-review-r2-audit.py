"""Static source/document evidence audit only. No C++/simulation/SSH execution."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import subprocess

ROOT = Path(r"E:\研\毕业论文\workspace\ws31-candidates-implementation")
OUT = Path(r"E:\研\毕业论文\workspace\LarryBUPT-conweave-ns3\docs\research\ws31\independent")
MAIN = OUT.parent / "main"
PRE = "endpoint-switch-local-review-r2"
OLD = "endpoint-switch-local-review-r1"
PARENT = "8cd1ba69469bf80143d5c89edc17fa72611018e8"
PLAN_HASH = "950104b5c26805437f7dab8a877176a20ae9dd2be15d0ab1a65b75488780b775"
UTC = datetime.datetime.now(datetime.timezone.utc).isoformat()
WRITTEN = []


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def get(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8")


def blob(f):
    return subprocess.check_output(["git", "show", PARENT + ":" + f], cwd=ROOT)


def put(p, data):
    p = Path(p)
    assert p.is_relative_to(OUT) and p.relative_to(OUT).parts[0].startswith(PRE)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    WRITTEN.append(str(p))


def emit(suffix, value):
    p = OUT / (PRE + suffix)
    put(p, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return p


resume_path = OUT / (PRE + "-resume-receipt.json")
progress_path = OUT / (PRE + "-progress-r1.json")
resume, progress = get(resume_path), get(progress_path)
stage_hashes = {str(p): sha(p) for p in [resume_path, progress_path]}
assert resume["review_complete"] is False and progress["review_completed"] is False
plan_path = MAIN / (PRE + ".json")
assert sha(plan_path) == PLAN_HASH
plan = get(plan_path)
assert git("rev-parse", "HEAD").strip() == PARENT
status = git("status", "--short").splitlines()
assert status == resume["git_status"]
working = {f: sha(ROOT / f) for f in plan["files_working_sha256"]}
assert len(working) == 10 and working == plan["files_working_sha256"] == resume["ten_WIP_sha256"]
for f, h in working.items():
    assert sha(MAIN / plan["preserved_WIP"] / f) == h
assert sha(MAIN / plan["contract"]) == plan["contract_sha256"]
main_files = [plan_path, MAIN / plan["contract"], MAIN / plan["source_audit"], MAIN / plan["prior_main_acceptance"], MAIN / "evidence/endpoint-switch-local-review-r2-interruption-recovery-r1.json", MAIN / "evidence/endpoint-switch-r1-to-r2.patch"]
main_hashes = {str(p): sha(p) for p in main_files}
audit = get(main_files[2])
assert audit["files_working_sha256"] == working
assert sha(main_files[3]) == audit["main_review_acceptance_sha256"]
assert sha(main_files[5]) == audit["r1_to_r2_patch_sha256"]
recovery = get(main_files[4])
assert recovery["failed_turn"] == "01a19786-5399-7631-a7c8-c0517ab25c14"
assert recovery["plan_sha256"] == PLAN_HASH
assert recovery["ten_current_and_preserved_WIP_hashes"] == working

old_review_path, old_qa_path = OUT / (OLD + "-review.json"), OUT / (OLD + "-qa.json")
assert sha(old_review_path) == "8ec0ab1523d7340049e51be5f774f32a4eadf13439475c7cbcc7116363a0b029"
assert sha(old_qa_path) == "e7db79776f5c14bd48d3dac02ca47be069f8cc2ebd386125b5a0fb2f1ef01bd4"
old_review, old_qa = get(old_review_path), get(old_qa_path)
old_hashes = dict(old_qa["artifacts"])
old_hashes[str(old_qa_path)] = sha(old_qa_path)
for p, h in old_hashes.items():
    assert sha(p) == h
channels = audit["channel_files_unchanged"]
assert len(channels) == 5
assert all(working[f] == old_review["nine_WIP_working_sha256"][f] for f in channels)

# Three additional-friend deltas only; retain the previously accepted bodies.
old_root = OUT / (OLD + "-evidence") / "WIP"
BUD = "src/point-to-point/model/ws31-budget.h"
QUOTA = "src/point-to-point/model/ws31-quota.h"
SW = "src/point-to-point/model/switch-node.h"
PROBE = "src/point-to-point/model/ws31-endpoint-switch-probe.h"
EP = "src/point-to-point/model/ws31-endpoint-probe.h"
FIX = "scratch/ws31-endpoint-switch-test.cc"
restored = {}
for f in [BUD, QUOTA, SW]:
    w = (ROOT / f).read_bytes().replace(b"\r\n", b"\n")
    if f in [BUD, QUOTA]:
        w = w.replace(b"namespace ns3 { class Ws31EndpointSwitchFixture; namespace ws31 {", b"namespace ns3 { namespace ws31 {", 1)
        w = w.replace(b"    friend class ::ns3::Ws31EndpointSwitchFixture;\n", b"")
    else:
        w = w.replace(b"    friend class Ws31EndpointSwitchFixture;\n", b"", 1)
    assert w == (old_root / f).read_bytes().replace(b"\r\n", b"\n")
    restored[f] = {"exact_reviewed_r1_after_removing_only_new_friends": True, "normalized_r1_sha256": hashlib.sha256(w).hexdigest()}
probe_text = (ROOT / PROBE).read_text(encoding="utf-8")
assert not re.search(r"\b(?:GetObject|Expire|Pressure|Value|Erase|Reset|Run)\s*\(", probe_text)
assert "const Ws31EndpointProbe::Observation &endpoint" not in probe_text
assert "Ws31EndpointProbe::Scope endpoint;" in probe_text

items = []
evidence = OUT / (PRE + "-evidence")


def record(p, role, source=None, git_blob=None):
    x = {"path": str(p), "role": role, "sha256": sha(p)}
    if source is not None:
        x["source"] = str(source)
    if git_blob is not None:
        x["git_blob"] = git_blob
    items.append(x)


for f in working:
    p = evidence / "WIP" / f
    put(p, (ROOT / f).read_bytes())
    record(p, "ten frozen r2 WIP working byte copies", f)
for source in main_files:
    p = evidence / "main-materials" / source.relative_to(MAIN)
    put(p, source.read_bytes())
    record(p, "immutable main plan/contract/audit/acceptance/recovery/patch copy", source)
bootstrap = [
    Path(r"E:\研\毕业论文\docs\REMOTE_EXPERIMENT_WORKFLOW.md"),
    OUT.parents[2] / "project-state/WS31_EXECUTION.md",
    OUT.parents[2] / "project-state/ws31-coordination.json",
    MAIN / "current-status.json",
]
for i, source in enumerate(bootstrap, 1):
    p = evidence / "bootstrap" / (str(i) + "-" + source.name)
    put(p, source.read_bytes())
    record(p, "bootstrap status/instruction snapshot; historical rows may be stale", source)
old_index = get(OUT / (OLD + "-evidence-index.json"))
fixed = [x for x in old_index["items"] if x["role"] == "fixed parent Git blob"]
assert len(fixed) == 16
for x in fixed:
    assert sha(x["path"]) == x["sha256"]
    items.append({**x, "reused_without_overwrite": True})
new_fixed = ["src/point-to-point/model/qbb-net-device.cc", "src/point-to-point/model/rdma-driver.cc", "src/point-to-point/model/rdma-driver.h", "src/point-to-point/model/rdma-hw.cc", "src/point-to-point/model/rdma-hw.h", "src/point-to-point/model/rdma-queue-pair.cc", "src/point-to-point/model/rdma-queue-pair.h", "src/core/model/event-id.h", "src/core/model/ptr.h", "src/network/utils/broadcom-egress-queue.cc", "src/network/utils/broadcom-egress-queue.h", "src/point-to-point/helper/qbb-helper.cc"]
for f in new_fixed:
    data = blob(f)
    assert (ROOT / f).read_bytes().replace(b"\r\n", b"\n") == data
    p = evidence / "fixed-parent" / f
    put(p, data)
    record(p, "additional fixed parent API/initialization/queue source", f, git("rev-parse", PARENT + ":" + f).strip())
for f in [BUD, QUOTA, SW, PROBE]:
    record(old_root / f, "previously reviewed switch r1 WIP retained for delta", f)
for p in [old_review_path, old_qa_path]:
    record(p, "previous accepted switch r1 review/QA")
refs = Path(r"E:\研\毕业论文\参考文献\候选")
for f in ["README.md", "reading-log.md", "papers/diffflow-2016/analysis-technical.md", "papers/diffflow-2016/verification.md", "papers/flowcut-2026/analysis-technical.md", "papers/flowcut-2026/verification.md"]:
    p = evidence / "literature" / f
    put(p, (refs / f).read_bytes())
    record(p, "important-node literature recheck record snapshot", refs / f)
for p in [resume_path, progress_path]:
    record(p, "preserved incomplete-stage receipt; superseded only by separate final review")
for x in items:
    assert sha(x["path"]) == x["sha256"]
    if x.get("git_blob"):
        data = Path(x["path"]).read_bytes()
        assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == x["git_blob"]
assert len(items) == 62
index_path = emit("-evidence-index.json", {"at_utc": UTC, "client_date": "2026-11-04", "parent_head": PARENT, "total_items": len(items), "fixed_parent_blobs": 28, "new_byte_copies": 38, "reused_or_preserved_items": 24, "items": items})

specs = [
    (PROBE, 36, "Ws31EndpointProbe::Scope endpoint;"),
    (PROBE, 55, "device && device->GetNode()==node && device->GetIfIndex()==slot"),
    (PROBE, 56, "seen.insert"), (PROBE, 58, "DynamicCast<QbbNetDevice>"),
    (PROBE, 59, "DynamicCast<LoopbackNetDevice>"), (PROBE, 74, "DeviceBinding"),
    (PROBE, 85, "Settings::lb_mode>=33"), (PROBE, 96, "typeid"),
    (PROBE, 102, "DeviceBinding"), (PROBE, 107, "switches>0"),
    (PROBE, 108, "Ws31EndpointProbe::Capture(drivers)"),
    (PROBE, 115, "Validate(scope)"), (PROBE, 120, "Ws31EndpointProbe::Read"),
    (PROBE, 127, "EndpointSnapshot::ALL ^"), (PROBE, 131, "const ws31::Key key"),
    (PROBE, 139, "m_ws30V13Pairs.count"), (PROBE, 141, "m_ws31Budget.Contains"),
    (PROBE, 145, "allBudget"), (PROBE, 148, "liveBorrowed"),
    (PROBE, 154, "observedFields|="),
    (FIX, 46, "Insert(k,1,1024,512,16,0,1)"),
    (FIX, 47, "Insert(other,4,2048,1024,32,0,1000)"),
    (FIX, 50, "QuotaAdmission(10)"), (FIX, 55, "target.borrowed"),
    (FIX, 76, "static std::string State"), (FIX, 88, "b.entries"),
    (FIX, 89, "b.deadlines"), (FIX, 90, "b.totals"),
    (FIX, 96, "q.entries"), (FIX, 97, "q.deadlines"),
    (FIX, 104, "deadline->first==1"), (FIX, 113, "totals.at(4)==2112"),
    (FIX, 134, "d->GetNode()->GetNodeType()!=0"),
    (FIX, 139, "eq->m_qpGrp->m_qp_finished"),
    (FIX, 163, "static_assert"), (FIX, 196, "i<2"),
    (FIX, 198, "d->Init()"), (FIX, 215, "SetQpFinished(0)"),
    (FIX, 223, "Ws31EndpointSnapshotFixture::Device"),
    (FIX, 247, "before=state()"), (FIX, 248, "before==between"),
    (FIX, 251, "x.snapshot.pinnedEntries==y.snapshot.pinnedEntries"),
    (FIX, 267, "before=state(); Deny"),
    (FIX, 274, "Simulator::Run()"), (FIX, 275, "GetNanoSeconds()==20"),
    (FIX, 277, "pinnedEntries==4"), (FIX, 281, "std::get<4>(pgEntry.tuple)=4"),
    (FIX, 293, "mode<=50"), (FIX, 301, "SetIfIndex(slot+10)"),
    (FIX, 303, "swDevice->SetNode(hosts.Get(0))"),
    (FIX, 316, "auto oldEndpoint=Ws31EndpointProbe::Read"),
    (FIX, 318, "Enqueue(Create<Packet>(32),1)"),
    (FIX, 322, "ledger.AckComplete"), (FIX, 326, "HELD_TEST_COPY"),
    (FIX, 329, "RECEIVE_RETURNED"), (FIX, 331, "HELD_DISCARDED"),
    (FIX, 335, "ResetWs30V13Tuple"), (FIX, 337, "sharedLeft=="),
    (FIX, 343, "liveBorrowed[2]==0"), (FIX, 348, "recaptured-composite-scope"),
    (FIX, 349, "left->AddDevice(swDevice)"), (FIX, 363, "SUMMARY PASS"),
    ("src/point-to-point/model/qbb-net-device.cc", 91, "RdmaEgressQueue::RdmaEgressQueue()"),
    ("src/point-to-point/model/qbb-net-device.cc", 249, "m_rdmaEQ = CreateObject<RdmaEgressQueue>()"),
    ("src/point-to-point/model/rdma-driver.cc", 52, "m_rdma->Setup"),
    ("src/point-to-point/model/rdma-hw.cc", 231, "m_rdmaEQ->m_qpGrp = m_nic[i].qpGrp"),
    ("src/core/model/ptr.h", 416, ": m_ptr (0)"),
    ("src/core/model/event-id.h", 75, "GetContext"),
]
anchors = []
for f, line, needle in specs:
    actual = (ROOT / f).read_text(encoding="utf-8").splitlines()[line - 1]
    assert needle in actual, (f, line, needle, actual)
    anchors.append({"path": f, "line": line, "contains": needle})
fixture = (ROOT / FIX).read_text(encoding="utf-8")
# Derive planned counts from literal call sites and the 18-iteration mode loop.
pair_calls = len(re.findall(r"\bpair\(", fixture))
deny_read_calls = len(re.findall(r'\bdenyRead\("', fixture))
deny_calls = len(re.findall(r'\bDeny\("', fixture))
planned_pairs = pair_calls - 1 + 18
planned_read_refusals = deny_read_calls + 1  # direct wrong-resource composite Read
planned_reads = planned_pairs * 2 + deny_read_calls + 1 + 1 + 2  # wrong resource, PG, final ledger checks
planned_refusals = deny_read_calls + deny_calls
assert (planned_pairs, planned_reads, planned_read_refusals, planned_refusals) == (25, 63, 10, 19)
counts = {k: 0 for k in ["ssh_remote", "sync_deploy", "compile_build", "CXX_test_fixture", "network", "old_accepted_test_rerun", "scientific_source_edits", "main_edits", "commit", "push", "subagents"]}
finding = {"id": "R2-F1", "priority": 1, "severity": "P1", "status": "OPEN_MUST_FIX_BEFORE_NEW_EXECUTABLE_SLICE", "title": "Owner-refusal purity fingerprint dereferences an unbound switch QP group before invoking Read", "anchors": [{"path": FIX, "line": x} for x in [303,267,223,134,139]] + [{"path": "src/point-to-point/model/qbb-net-device.cc", "line": 91}, {"path": "src/point-to-point/model/rdma-hw.cc", "line": 231}], "source_chain": ["middle-link switch device starts with RdmaEgressQueue whose default Ptr qpGrp is null", "only the two host drivers call Init/Setup and bind groups", "SetNode(host) changes the role seen by Device fingerprint", "denyRead invokes state() before observe()", "host branch dereferences qpGrp before the intended owner/index guard"], "consequence": "Undefined behavior/null-group access before expected refusal; later history/queue/manual-token/cleanup/scope cases cannot be accepted as reachable", "minimum_action": "Safely fingerprint malformed ownership without selecting protocol layout from the mutated owner: use captured/iterated role and optional-object presence checks, preserving before/after comparisons. Do not fill groups or repair owner during fingerprint. Assert intended refusal cause.", "evidence_level": "static source finding, not observed crash or runtime failure"}
review = {
    "at_utc": UTC, "client_date": "2026-11-04", "timezone": "Asia/Shanghai", "target": PRE,
    "source_chat": "01a19323-2201-7b23-a0f1-905c71496d38", "parent_chat": "01a19322-95a5-76e3-a4f5-1f1e9dde81ce",
    "status": "COMPLETE_FOR_LOCAL_STATIC_R2_REVIEW_FIX_REQUIRED", "review_complete": True, "implementation_or_dynamic_validation_complete": False,
    "verdict": "FIX_REQUIRED_ONE_P1_IN_NEW_FIXTURE", "finding_counts": {"P1": 1, "P2": 0},
    "plan": {"path": str(plan_path), "sha256": PLAN_HASH}, "source_root": str(ROOT), "parent_head": PARENT, "observed_head": PARENT, "git_status": status,
    "ten_WIP_working_sha256": working, "main_preserved_ten_match": True,
    "recovery": {"same_goal_not_new_dispatch": True, "failed_prior_turn": recovery["failed_turn"], "prior_failure_preserved": True, "terminal_cursor": recovery["observed_terminal_cursor"], "original_guard_held_through_failed_turn": True, "resume_receipt": str(resume_path), "progress_receipt": str(progress_path), "incomplete_receipts_not_overwritten": True},
    "prior_resolution": [{"id": "S1", "status": "ADDRESSED_IN_SOURCE_NOT_RUN", "reason": "private combined endpoint Scope, internal actual synchronous Read, no external Observation upgrade argument"}, {"id": "S2", "status": "ADDRESSED_IN_SOURCE_NOT_RUN", "reason": "nonnull/owner/index/global device uniqueness/type checked both Capture and Validate"}],
    "findings": [finding],
    "plan_question_coverage": [{"question": q, "analysis_complete": True, "report_sections": s} for q,s in zip(plan["questions"], [["2:S1"],["2:S2"],["1","3"],["1","3"],["4"],["4","5"],["2","5"]])],
    "five_channel_files": {"unchanged_from_accepted_prior_switch_r1": True, "files": channels, "prior_review_sha256": sha(old_review_path), "analysis_reused_not_repeated": True, "no_old_test_rerun": True},
    "restoration_checks": restored,
    "CXX11_old_API_static_review": {"new_friend_access_and_forward_declarations_consistent": True, "event_id_getters_declared": True, "savedTX_group_bitmap_and_egress_fields_accessible": True, "no_other_confirmed_compile_blocker_found_by_reading": True, "actual_compilation_verified": False},
    "fingerprint_review": {"switch_pin_budget_quota_observed_core_state_covered": True, "complete_strings_compared_not_only_display_hashes": True, "captures_before_purity_interval": True, "endpoint_scope": "listed protocol fields only, not whole object memory or all queue/QP state", "missing_broader_queue_fields": ["physical queue packet identities", "RR cursor", "all queue statistics", "all QP protocol fields"], "pair_compares_full_observation": False, "pair_compared_result_fields": ["target pin count", "target budget count", "target quota count"], "owner_malformed_state_safety": "FAIL_R2_F1", "duplicate_case_branch_limit": "AddDevice also changes interface count and index; does not independently isolate seen.insert refusal"},
    "static_fixture_chronology": {"evidence_level": "not_executed_conditional_after_R2_F1_repair", "planned_pairs": planned_pairs, "planned_composite_Read_calls": planned_reads, "planned_Read_refusals": planned_read_refusals, "planned_Read_returns": planned_reads-planned_read_refusals, "planned_total_refusals": planned_refusals, "extra_direct_endpoint_Read": 1, "manual_tokens": 2, "protocol_state_assignment_manual": True, "mode_coverage": "18 supported read-admission modes, not production routing executions", "PG_case": "projection-only copy of Entry with actual saved object fields adjusted; not cross-PG ledger admission", "per_switch_seed": {"target_remaining_payload": 896, "target_wire_budget": 928, "K2_wire_budget": 2112, "target_budget_deadline_ns": 1, "quota_deadline_ns": 10, "clock_target_ns": 20, "stored_liveBorrowed2": 1}, "two_switch_target_counts": {"pins": 4, "budget": 2, "quota": 2}, "cleanup_per_switch": {"K_absent": True, "K2_four_table_entries_retained": True, "budget_port1": 0, "budget_port4": 2112, "budget_deadlines": 1, "quota_deadlines": 1, "stored_liveBorrowed2": 0, "shared_history_retained": True}, "mask255_measured": False, "natural_network_completion": False},
    "important_node_literature_recheck": {"complete": True, "entry_points": ["candidate README", "reading-log"], "versions": [{"paper":"DiffFlow","version":"arXiv:1604.05107v1","lesson":"separate activation, actual transport and reclamation evidence","boundary":"simplified Java and class queues do not establish RDMA correctness/effects"},{"paper":"Flowcut","version":"arXiv:2506.21406v2","lesson":"explicit in-flight closure and state/cost accounting","boundary":"ACK byte closure differs from manual token assignments; SST/Slingshot results do not certify this fixture or dual metrics"}], "record_snapshots": 6, "new_baseline_admission": False},
    "remaining_mandatory": ["R2-F1 repair and new fixed source/execution plan", "actual new fixture build/reachability/raw verification", "completion callback and savedRX", "history release", "actual G1 and all identity producers", "shared PFC/ACK/NACK/CNP/retransmit coverage", "actual channel/held-copy and two-generation network positive/negative cases", "independent C1 V0", "three-candidate matched ablation", "business/background two-sided effects", "state/runtime costs"],
    "evidence_index": str(index_path), "evidence_items": len(items), "exact_source_anchors": anchors,
    "execution_counts": counts, "owned_background_execution": False, "new_execution_authority": False, "ten_file_guard": "EXPLICITLY_RELEASED_AT_FINAL_DELIVERY",
}
review_path = emit("-review.json", review)

# Human artifacts: local links, source line bounds and structural/style checks.
links = 0
deferred = {PRE + "-qa.json", PRE + "-guards-released.json"}
for suffix in ["-report.md", "-handoff.md"]:
    p = OUT / (PRE + suffix)
    text = p.read_text(encoding="utf-8")
    for href in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        if href.startswith("https://"):
            continue
        match = re.match(r"^(.*):(\d+)$", href)
        target = match.group(1) if match else href
        resolved = Path(target) if re.match(r"^[A-Za-z]:[/\\]", target) else p.parent / target
        if resolved.name not in deferred:
            assert resolved.is_file(), (p,href)
            if match:
                assert int(match.group(2)) <= len(resolved.read_text(encoding="utf-8-sig").splitlines())
        links += 1
    assert not re.search(r"[０-９]", text)
    assert not re.search(r"^#{4,}", text, re.MULTILINE)
    assert not re.search(r"\n#{1,3} [^\n]+\n[^\n]", text)
assert len(re.findall(r"^## [1-9]\. ", (OUT/(PRE+"-handoff.md")).read_text(encoding="utf-8"), re.MULTILINE)) == 9
assert len(review["plan_question_coverage"]) == 7

# End-of-review identities and preserved failure/progress records.
assert git("rev-parse", "HEAD").strip() == PARENT
assert git("status", "--short").splitlines() == status
assert {f:sha(ROOT/f) for f in working} == working
for p,h in {**main_hashes, **old_hashes, **stage_hashes}.items():
    assert sha(p) == h
release_path = emit("-guards-released.json", {"at_utc": UTC,"client_date":"2026-11-04","target":PRE,"status":"EXPLICITLY_RELEASED_AFTER_COMPLETE_LOCAL_STATIC_REVIEW","source_root":str(ROOT),"head":PARENT,"scope":list(working),"working_sha256":working,"reason":"Static review complete; R2-F1 P1 fixture repair and all dynamic validation remain with main","guard_was_held_continuously_across_prior_usage_failure":True,"old_failure_and_stage_receipts_preserved":True,"no_broader_guard_held":True,"owned_background_execution":False,"new_execution_authority":False,"execution_counts":counts})
artifact_paths = [OUT/(PRE+s) for s in ["-report.md","-handoff.md","-review.json","-evidence-index.json","-guards-released.json","-audit.py","-resume-receipt.json","-progress-r1.json"]]
qa_path = emit("-qa.json", {"at_utc":UTC,"client_date":"2026-11-04","status":"PASS_STATIC_ARTIFACT_QA_ONE_P1_FIX_REQUIRED","review_complete":True,"implementation_or_dynamic_validation_complete":False,"scope":"source/evidence identities, static anchors, delta checks, planned count derivation and document QA; no C++ fixture execution","plan_sha256":PLAN_HASH,"head_unchanged":True,"git_status_unchanged":True,"ten_WIP_unchanged":True,"ten_main_preserved_copies_match":True,"five_channel_files_unchanged_and_prior_analysis_reused":True,"prior_switch_r1_artifacts_unchanged":old_hashes,"incomplete_stage_receipts_unchanged":stage_hashes,"prior_usage_limit_failure_preserved":True,"evidence_items_verified":len(items),"fixed_parent_blobs_verified":28,"source_anchors_verified":len(anchors),"plan_questions_answered":7,"restoration_checks":restored,"planned_counts_are_not_execution_results":True,"no_measured_mask255_or_network_certificate":True,"literature_recheck_complete":True,"nine_handoff_sections":True,"local_links_verified":links,"chinese_style_recheck":["original ruanyf README and six chapters already read in this conversation","headings","spacing","sentences/paragraphs","numbers/units","punctuation","structure"],"artifacts":{str(p):sha(p) for p in artifact_paths},"QA_self_hash":"not embedded","only_allowed_prefix_written":all(Path(p).relative_to(OUT).parts[0].startswith(PRE) for p in WRITTEN),"ten_file_guard_explicitly_released":True,"owned_background_execution":False,"new_execution_authority":False,"execution_counts":counts})
assert qa_path.exists() and release_path.exists()
print(json.dumps({"status":"PASS_STATIC_ARTIFACT_QA_ONE_P1_FIX_REQUIRED","evidence_items":len(items),"fixed_parent_blobs":28,"source_anchors":len(anchors),"review_sha256":sha(review_path),"QA_sha256":sha(qa_path),"guard":"EXPLICITLY_RELEASED","execution_counts":counts},ensure_ascii=False))
