"""R2 static source/document audit. No compiler, C++ fixture, simulator or SSH calls."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import subprocess

ROOT = Path(r"E:\研\毕业论文\workspace\ws31-candidates-implementation")
OUT = Path(r"E:\研\毕业论文\workspace\LarryBUPT-conweave-ns3\docs\research\ws31\independent")
MAIN = OUT.parent / "main"
PRE = "endpoint-channel-local-review-r2"
OLD = "endpoint-channel-local-review-r1"
PARENT = "8cd1ba69469bf80143d5c89edc17fa72611018e8"
PLAN_HASH = "6562ce1cb84f6b1b942b0d2e61982d86203371fc7f977e85e459bbb767b975e0"
UTC = datetime.datetime.now(datetime.timezone.utc).isoformat()
WRITTEN = []


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def get(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def put(p, data):
    p = Path(p)
    assert p.is_relative_to(OUT)
    assert p.relative_to(OUT).parts[0].startswith(PRE)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    WRITTEN.append(str(p))


def emit(suffix, value):
    p = OUT / (PRE + suffix)
    put(p, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return p


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8")


def blob(f):
    return subprocess.check_output(["git", "show", PARENT + ":" + f], cwd=ROOT)


plan_path = MAIN / (PRE + ".json")
assert sha(plan_path) == PLAN_HASH
plan = get(plan_path)
assert git("rev-parse", "HEAD").strip() == PARENT
status = git("status", "--short").splitlines()
assert status == [" M src/network/model/flow-id-num-tag.h", " M src/point-to-point/model/qbb-channel.cc", " M src/point-to-point/model/qbb-channel.h", "?? scratch/ws31-endpoint-channel-test.cc", "?? src/point-to-point/model/ws31-endpoint-channel.h"]
working = {f: sha(ROOT / f) for f in plan["files_working_sha256"]}
assert working == plan["files_working_sha256"]
for f, h in working.items():
    assert sha(MAIN / plan["preserved_WIP"] / f) == h
main_sources = [plan_path, MAIN / "endpoint-channel-contract-r2.md", MAIN / "evidence/endpoint-channel-wip-source-audit-r2.json"]
main_hashes = {str(p): sha(p) for p in main_sources}
assert get(main_sources[2])["files_working_sha256"] == working
old_qa = get(OUT / (OLD + "-final-qa.json"))
assert sha(OUT / (OLD + "-final-qa.json")) == "9e96f3f9480a0f88feb76f94fd0d9299985afc9db9cfa8750bd97b7e825141fe"
assert sha(OUT / (OLD + "-final-review.json")) == "85b22cc6a3393d2f4d07d597d32128864aa2e95eb06e6c20481b01c208e7f1f9"
old_hashes = dict(old_qa["artifacts"])
old_hashes[str(OUT / (OLD + "-final-qa.json"))] = sha(OUT / (OLD + "-final-qa.json"))
for p, h in old_hashes.items():
    assert sha(p) == h
old_cp = get(OUT / (OLD + "-checkpoint.json"))
for item in old_cp["preserved_files"]:
    assert sha(item["path"]) == item["sha256"]

items = []
evidence_root = OUT / (PRE + "-evidence")
for f, h in working.items():
    p = evidence_root / "WIP" / f
    put(p, (ROOT / f).read_bytes())
    items.append({"path": str(p), "role": "r2 frozen working byte copy", "source": f, "sha256": h})
for original in main_sources:
    relative = original.relative_to(MAIN)
    p = evidence_root / "main-materials" / relative
    put(p, original.read_bytes())
    items.append({"path": str(p), "role": "r2 main material byte copy", "source": str(original), "sha256": sha(p)})
for f in ["waf-tools/cflags.py", "src/core/model/ptr.h", "src/core/model/scheduler.h", "src/core/model/attribute-accessor-helper.h"]:
    data = blob(f)
    assert (ROOT / f).read_bytes().replace(b"\r\n", b"\n") == data
    p = evidence_root / "fixed-parent" / f
    put(p, data)
    items.append({"path": str(p), "role": "additional r2 fixed-parent Git blob", "source": f, "sha256": sha(p), "git_blob": git("rev-parse", PARENT + ":" + f).strip()})
old_index = get(OUT / (OLD + "-final-evidence-index.json"))
fixed = [x for x in old_index["items"] if "fixed parent" in x["role"] or "fixed-parent" in x["role"]]
literature = [x for x in old_index["items"] if x["role"] == "literature recheck record snapshot"]
assert len(fixed) == 22 and len(literature) == 6
for original in fixed + literature:
    assert sha(original["path"]) == original["sha256"]
    entry = dict(original)
    entry["reused_from_r1_without_overwrite"] = True
    items.append(entry)
for suffix in ["-final-review.json", "-final-qa.json"]:
    p = OUT / (OLD + suffix)
    items.append({"path": str(p), "role": "prior accepted r1 review artifact", "sha256": sha(p), "reused_from_r1_without_overwrite": True})
assert len(items) == 42
for x in items:
    assert sha(x["path"]) == x["sha256"]
    if x.get("git_blob"):
        data = Path(x["path"]).read_bytes()
        assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == x["git_blob"]
for x in literature:
    assert sha(x["source"]) == x["sha256"]

# Delete added structure to independently recover the three original Git blobs.
restored = {}
p = "src/point-to-point/model/qbb-channel.cc"
w = (ROOT / p).read_bytes().replace(b"\r\n", b"\n").replace(b"#include <limits>\n#include <stdexcept>\n", b"", 1)
a = w.index(b"  if (!m_ws31Enter)\n")
b = w.index(b"\n  // Call the tx anim callback", a)
direct = w[a:b].split(b"    {\n", 1)[1].split(b"\n    }\n  else", 1)[0]
direct = direct.replace(b"      m_ws31EverTransmitted = true;\n", b"", 1).replace(b"      Simulator::ScheduleWithContext", b"  Simulator::ScheduleWithContext", 1)
w = w[:a] + direct + b"\n" + w[b:]
a = w.index(b"void\nQbbChannel::DeliverWs31")
b = w.index(b"uint32_t \nQbbChannel::GetNDevices", a)
w = w[:a] + w[b:]
assert w == blob(p)
restored[p] = {"exact_parent_git_LF": True, "sha256": hashlib.sha256(w).hexdigest()}
p = "src/point-to-point/model/qbb-channel.h"
w = (ROOT / p).read_bytes().replace(b"\r\n", b"\n").replace(b"#include <functional>\n#include <exception>\n", b"", 1).replace(b"class Ws31EndpointChannel;\n", b"", 1)
a = w.index(b"  // Empty for ordinary simulations.")
b = w.index(b"  // Each point to point link", a)
w = w[:a] + w[b:]
assert w == blob(p)
restored[p] = {"exact_parent_git_LF": True, "sha256": hashlib.sha256(w).hexdigest()}
p = "src/network/model/flow-id-num-tag.h"
w = (ROOT / p).read_bytes().replace(b"\r\n", b"\n").replace(b"#ifndef NS3_FLOW_ID_NUM_TAG_H\n#define NS3_FLOW_ID_NUM_TAG_H\n\n", b"", 1).replace(b"#endif // NS3_FLOW_ID_NUM_TAG_H\n\n", b"", 1)
assert w == blob(p)
restored[p] = {"exact_parent_git_LF": True, "sha256": hashlib.sha256(w).hexdigest()}
guards = subprocess.check_output(["rg", "-l", "NS3_FLOW_ID_NUM_TAG_H|WS31_ENDPOINT_CHANNEL_H", "src", "scratch", "--glob", "*.[hc]*"], cwd=ROOT).decode().splitlines()
assert sorted(x.replace("\\", "/") for x in guards) == sorted(["src/network/model/flow-id-num-tag.h", "src/point-to-point/model/ws31-endpoint-channel.h"])

CH = "src/point-to-point/model/ws31-endpoint-channel.h"
CC = "src/point-to-point/model/qbb-channel.cc"
HH = "src/point-to-point/model/qbb-channel.h"
FIX = "scratch/ws31-endpoint-channel-test.cc"
anchor_specs = [
    (HH, 142, "static void DeliverWs31"), (HH, 143, "Ws31Leave leave"),
    (CC, 153, "Ws31Leave leave"), (CC, 155, "try"),
    ("src/core/model/make-event.h", 430, "(*m_function)(m_a1, m_a2, m_a3, m_a4, m_a5)"),
    ("src/core/model/make-event.h", 437, "ReferencedType m_a5"),
    ("src/core/model/default-simulator-impl.cc", 142, "Invoke"),
    ("src/core/model/default-simulator-impl.cc", 143, "Unref"),
    ("src/core/model/default-simulator-impl.cc", 211, "m_stop = true"),
    ("src/core/model/type-traits.h", 21, "typedef U ReferencedType"),
    (CH, 156, "typeid(*PeekPointer(channel))==typeid(QbbChannel)"),
    (CH, 157, "GetInstanceTypeId"), (FIX, 43, "UnregisteredOverride"),
    (FIX, 94, "Pair overriding"), (FIX, 95, "GetInstanceTypeId"),
    (FIX, 97, "unregistered-overriding-channel"),
    ("waf-tools/cflags.py", 26, "-std=gnu++11"),
    ("src/core/model/ptr.h", 375, "dynamic_cast"),
    (CH, 127, "id>=0 && id<=65535"), (CH, 130, "ValidateIdentity(id)"),
    (CH, 134, "tag.SetId(id); tag.SetFlowSize(flowBytes)"), (CH, 135, "AddPacketTag"),
    (CH, 146, "Healthy(); ValidateIdentity(id)"), (CH, 149, "registered.count"),
    (FIX, 64, "EncodeIdentity(packet,id,8)"), (FIX, 112, "tag.SetFlowSize(8)"),
    (FIX, 114, "decoded.GetId()==(id==-1?65535:0)"),
    (CC, 160, "destination->Receive"), (CC, 162, "leave (serial)"),
    (CC, 163, "--channel->m_ws31Pending"), (CC, 168, "m_ws31Failed = true"),
    (CC, 169, "if (!channel->m_ws31Failure)"), (CC, 172, "Simulator::Stop"),
    (CH, 94, "ledger->Enter"), (CH, 96, "history.push_back"),
    (CH, 98, "open.insert"), (CH, 102, "s->failure=std::current_exception"),
    (CH, 55, "void Healthy"), (CH, 185, "Healthy()"), (CH, 224, "Pending()==0"),
    (CC, 122, "++m_ws31Pending"), (CC, 124, "try"),
    (CC, 131, "ScheduleWithContext"), (CC, 135, "m_txrxQbb"),
    (CC, 140, "if (!m_ws31Failure)"), (CH, 173, "Ws31Enter enter="),
    (CH, 177, "Ws31Leave leave="), (CH, 179, "channels.push_back"),
    (CH, 180, "m_ws31Enter.swap"), (CH, 181, "m_ws31Leave.swap"), (CH, 182, "m_ws31Owner="),
    (CC, 106, "m_ws31EverTransmitted = true"), (CC, 121, "m_ws31EverTransmitted = true"),
    (CH, 162, "!channel->m_ws31EverTransmitted"),
    (FIX, 189, "bind-after-default-scheduled"), (FIX, 191, "bind-after-default-returned"),
    (FIX, 197, "AFTER_LEDGER_ENTER"), (FIX, 209, "BEFORE_BIND_COMMIT"),
    (FIX, 220, "FailNextScheduleForTesting"), (FIX, 231, "TraceConnectWithoutContext"),
    (FIX, 245, "LEAVE_BEFORE_CLOSE"), (FIX, 259, "owner.reset"),
    (FIX, 263, "ledger->Get(8).closed"), (FIX, 20, "catch (const std::logic_error"),
    (FIX, 26, "catch (const std::runtime_error"), (CH, 218, "std::rethrow_exception(state->failure)"),
    (CH, 220, "std::rethrow_exception(channel->m_ws31Failure)"),
]
anchors = []
for f, line, needle in anchor_specs:
    text = (ROOT / f).read_text(encoding="utf-8").splitlines()
    assert needle in text[line - 1], (f, line, needle, text[line - 1])
    anchors.append({"path": f, "line": line, "contains": needle})

counts = {name: 0 for name in ["ssh_remote", "sync_deploy", "compile", "cpp_test_fixture", "network", "old_accepted_test_rerun", "scientific_source_edits", "main_edits", "commit", "push", "subagents"]}
cases = [
    ("default-off", 72, 84, "one original-pointer delivery at 13 ns, correct context; marker adds no event"),
    ("observed-nested-and-refusals", 85, 166, "13/13/16 ns, serials 1/2/3, pending 2/2/1, nested peak 3; pre-mutation refusals token-free; used rebind rejected"),
    ("receive-error", 167, 183, "body-caught logic_error, Stop/normal Run return, open=1 token=1; Finish denied"),
    ("late-bind", 184, 194, "Bind rejected before and after old default delivery; default callback called once"),
    ("after-ledger-enter", 197, 206, "State failed, token=1 history=0 open=0; pending not increased; Finish denied"),
    ("after-history-append", 197, 206, "State failed, token=1 history=1 open=0; pending not increased; Finish denied"),
    ("staged-bind", 207, 217, "fault before vector push, healthy empty session; retry and unused-object next owner allowed"),
    ("pre-schedule-boundary", 218, 226, "channel failed, token=1 open=1, no actual schedule; Finish denied"),
    ("animation", 227, 240, "actual trace throws runtime_error after schedule; delivery guard denies Receive, retains first error, token=1 open=1"),
    ("leave-before-close", 241, 252, "Receive returned, leave throws runtime_error, token=1 open=1, no closure evidence"),
    ("owner-lost-idle", 253, 268, "callbacks retain State, no event or normal Finish, takeover denied"),
    ("owner-lost-inflight", 253, 268, "callbacks avoid session this; one token can close, takeover denied, no normal Finish"),
]
index_path = emit("-evidence-index.json", {"at_utc": UTC, "parent_head": PARENT, "items": items, "new_copies": 12, "reused_items": 30, "total_items": 42, "old_r1_not_overwritten": True})
finding = {
    "id": "R2-01", "priority": 2, "severity": "P2", "status": "OPEN_MUST_FIX_BEFORE_NEW_FROZEN_EXECUTION",
    "title": "By-value leave parameter can throw before DeliverWs31 body enters its catch",
    "anchors": [a for a in anchors if (a["path"], a["line"]) in {(HH, 143), (CC, 153), (CC, 155), ("src/core/model/make-event.h", 430), ("src/core/model/default-simulator-impl.cc", 142), ("src/core/model/default-simulator-impl.cc", 143)}],
    "trigger": "Event Notify passes saved std::function m_a5 lvalue to by-value Ws31Leave; copy construction throws before target function body",
    "consequence": "No channel failure capture/Stop occurs; exception again skips current-event Unref in old simulator. Pending/open stay positive, so fabricated closure is not asserted.",
    "minimum_action": "Use const Ws31Leave & in both declaration and definition, retaining event-owned function value while binding reference at invocation; or move every throwing copy within a protected event boundary. No simulator baseline edit needed.",
    "old_template_reason": "U5 (function signature) and T5 (stored call argument) are separate template parameters. T5 remains function value, while U5 may be const reference.",
    "evidence_level": "conditional static failure path; allocation/copy failure not executed",
}
resolution = [
    {"id": "C1", "status": "ADDRESSED_IN_SOURCE_NOT_BUILT", "reason": "exact dynamic type plus TypeId; complete inherited-TypeId override refusal written; actual build flags remain a gate"},
    {"id": "C2", "prior_priority": 1, "status": "PARTIAL_CONTROLLED_ENCODER_ONLY_PRODUCTION_CONTRACT_OPEN", "reason": "range checking before new encoder serialization and Register; cannot recover already-truncated tags; actual G1 and every producer remain mandatory"},
    {"id": "C3", "status": "ADDRESSED_IN_NEW_FIXTURE_SOURCE_NOT_RUN", "reason": "EncodeIdentity and raw alias examples initialize flow_size; original tag body unchanged"},
    {"id": "C4", "status": "PARTIAL_BODY_EXCEPTION_PATH_ADDRESSED_R2_01_OPEN", "reason": "body-caught Receive/leave exceptions Stop and return to Unref; pre-body argument copy still escapes"},
    {"id": "C5", "status": "ADDRESSED_FOR_INSPECTED_MUTATION_PATHS_NOT_RUN", "reason": "State latch after ledger mutation; channel latch for schedule/animation; staged Bind then swaps/owner. Actual allocator/scheduler failure handling not dynamically proved."},
    {"id": "I1", "status": "ADDRESSED_FOR_LOCAL_CHANNEL_ADMISSION_NOT_RUN", "reason": "EverTransmitted blocks old default events and used rebind; global G1 coverage and default cost remain open"},
]
remaining = ["R2-01 parameter-boundary repair and new frozen source", "actual parsed G1 before all traffic", "all identity producers before serialization and cross-generation uniqueness", "shared PFC/ACK/NACK/CNP/retransmit coverage", "real switch read-only snapshot", "completion callback and savedRX", "history release", "real two-generation positive and negative network cases", "independent C1 V0", "three-candidate matched ablation", "business/background two-sided effects", "state/runtime costs"]
review = {
    "at_utc": UTC, "client_date": "2026-11-01", "timezone": "Asia/Shanghai", "target": PRE,
    "source_chat": "01a19323-2201-7b23-a0f1-905c71496d38", "parent_chat": "01a19322-95a5-76e3-a4f5-1f1e9dde81ce",
    "status": "COMPLETE_FOR_LOCAL_R2_STATIC_REVIEW_FIX_REQUIRED", "review_complete": True, "implementation_or_dynamic_validation_complete": False,
    "verdict": "FIX_REQUIRED_R2_01_OPEN_C2_PRODUCTION_SCOPE_STILL_OPEN", "new_finding_counts": {"P1": 0, "P2": 1},
    "source_root": str(ROOT), "parent_head": PARENT, "observed_head": PARENT, "branch": git("branch", "--show-current").strip(), "git_status": status,
    "plan": {"path": str(plan_path), "sha256": PLAN_HASH}, "five_WIP_working_sha256": working, "main_preserved_WIP_match": True,
    "findings": [finding], "r1_resolution": resolution,
    "plan_question_coverage": [{"question": q, "analysis_complete": True, "report_sections": sections} for q, sections in zip(plan["questions"], [["2:C1"], ["2:C2,C3"], ["1", "2:C4"], ["2:C5", "3"], ["2:I1", "4"], ["3", "4"], ["5"]])],
    "fixture_cases": [{"case": name, "source": FIX, "start": start, "end": end, "static_expectation": result, "executed": False} for name, start, end, result in cases],
    "fixture_boundaries": {"simulator_lifetime_segments_in_source": 12, "all_results_are_static_expectations": True, "production_receive_or_transport_completion": False, "allocation_schedule_bind_faults": "controlled throws at selected transaction boundaries, not actual allocator/scheduler exhaustion", "animation_fault": "actual TxRxQbb callback throws after scheduling", "original_exception_assertions": "helper checks exception class family only; recommend exact message/type marker checks"},
    "restoration_checks": restored, "guard_macro_collision_in_src_scratch": False,
    "nominal_success_path": {"original_packet_context_delay_preserved_in_source": True, "delivery_event_count": "one replacement event", "animation_order": "schedule then animation", "closure_order": ["Receive returns", "leave closes ledger", "pending decreases"], "normal_fixture_return_ns": [13, 13, 16], "normal_receive_visible_pending": [2, 2, 1], "execution_evidence": False},
    "rtti_cpp11": {"source_support": "waf GccTraits gnu++11 and existing dynamic_cast; no disable RTTI/exception option found in inspected configuration sources", "actual_r2_compilation_and_final_flags_verified": False},
    "lifetime": {"callbacks_capture_shared_State_not_session_this": True, "state_has_no_direct_channel_device_members": True, "owner_loss_is_not_normal_finish": True, "preexisting_qbb_device_channel_strong_references_remain": True, "no_whole_teardown_reclamation_claim": True},
    "exact_source_anchors": anchors, "evidence_index": str(index_path), "evidence_items": 42,
    "literature_recheck": {"completed_for_r2_review_node": True, "readme_reading_log_and_four_records_unchanged_from_r1": True, "focused_recheck": ["DiffFlow technical section 8 and verification boundaries", "Flowcut technical section 9 and verification evidence boundaries"], "versions": [{"name": "DiffFlow", "version": "arXiv:1604.05107v1", "pdf_sha256_previously_verified": "f552fcb75a0cec582286db0032c81660ff161fe475609ae5e79ad7075a0ae164", "lesson": "separate classification, activation and actual transport; Java/no-full-TCP/separate-queue evidence is not RDMA G1 proof"}, {"name": "Flowcut", "version": "arXiv:2506.21406v2", "pdf_sha256_previously_verified": "1ba1e8cbad41973d3b42112a1a33876629541da814ac56bd06132439704fd1a1", "lesson": "explicit in-flight closure and state/pause costs; ACK-byte closure is not Receive-return evidence and does not prove project reuse/effects"}], "new_baseline_or_mechanism_admission": False},
    "remaining_mandatory": remaining, "execution_counts": counts, "owned_background_execution": False, "new_execution_authority": False,
    "five_file_read_only_guard": "EXPLICITLY_RELEASED_AT_DELIVERY", "old_r1_artifacts_preserved": True,
}
review_path = emit("-review.json", review)

# Check source/main/old bytes once more before releasing this review's five-file guard.
assert git("rev-parse", "HEAD").strip() == PARENT
assert git("status", "--short").splitlines() == status
assert {f: sha(ROOT / f) for f in working} == working
for p, h in main_hashes.items():
    assert sha(p) == h
for p, h in old_hashes.items():
    assert sha(p) == h
release_path = emit("-guards-released.json", {"at_utc": UTC, "target": PRE, "status": "EXPLICITLY_RELEASED_AFTER_COMPLETED_LOCAL_R2_STATIC_REVIEW", "scope": list(working), "source_root": str(ROOT), "head": PARENT, "working_sha256": working, "reason": "R2 review complete; one new P2 fix and production obligations remain with main", "no_broader_guard_held": True, "owned_background_execution": False, "execution_counts": counts, "new_execution_authority": False, "r1_release_not_overwritten": True})

link_count = 0
for suffix in ["-report.md", "-handoff.md"]:
    p = OUT / (PRE + suffix)
    text = p.read_text(encoding="utf-8")
    for href in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        if href.startswith("https://"):
            continue
        match = re.match(r"^(.*):(\d+)$", href)
        target = match.group(1) if match else href
        resolved = Path(target) if re.match(r"^[A-Za-z]:[/\\]", target) else p.parent / target
        if resolved.name != PRE + "-qa.json":
            assert resolved.is_file(), (p, href)
            if match:
                assert int(match.group(2)) <= len(resolved.read_text(encoding="utf-8-sig").splitlines())
        link_count += 1
    assert not re.search(r"[０-９]", text)
    assert not re.search(r"^#{4,}", text, re.MULTILINE)
    assert not re.search(r"\n#{1,3} [^\n]+\n[^\n]", text)
assert len(re.findall(r"^## [1-9]\. ", (OUT / (PRE + "-handoff.md")).read_text(encoding="utf-8"), re.MULTILINE)) == 9
assert len(review["plan_question_coverage"]) == 7
fixture_line_count = len((ROOT / FIX).read_text(encoding="utf-8").splitlines())
assert all(0 < x["start"] < x["end"] <= fixture_line_count for x in review["fixture_cases"])
artifact_paths = [OUT / (PRE + s) for s in ["-report.md", "-handoff.md", "-review.json", "-evidence-index.json", "-guards-released.json", "-audit.py"]]
qa_path = emit("-qa.json", {
    "at_utc": UTC, "status": "PASS_R2_STATIC_ARTIFACT_QA_ONE_P2_FIX_REQUIRED", "review_completed": True, "implementation_or_dynamic_validation_completed": False,
    "scope": "static source identity/anchors/restoration and document links/hashes; no C++ or scientific execution",
    "plan_sha256": PLAN_HASH, "head_unchanged": True, "git_status_unchanged": True, "five_WIP_unchanged": True, "main_five_WIP_preserved_copies_match": True,
    "main_materials_unchanged": main_hashes, "old_r1_artifacts_unchanged": old_hashes,
    "old_r1_checkpoint_23_snapshots_unchanged": True,
    "evidence_items_verified": 42, "new_evidence_copies": 12, "reused_evidence_items": 30, "fixed_parent_blobs_verified": 26,
    "source_anchors_verified": len(anchors), "plan_questions_answered": 7, "static_fixture_segments": 12, "fixture_segments_executed": 0,
    "restoration_checks": restored, "guard_macro_collision_in_src_scratch": False,
    "new_finding_counts": review["new_finding_counts"], "C2_production_scope_still_open": True, "literature_recheck_complete": True,
    "nine_handoff_sections": True, "local_links_verified": link_count, "chinese_style_manual_recheck": ["original README and six chapters already read in this conversation", "headings", "spacing", "sentences/paragraphs", "numbers/units", "punctuation", "document structure"],
    "artifacts": {str(p): sha(p) for p in artifact_paths}, "QA_self_hash": "not embedded",
    "only_allowed_r2_prefix_written": all(Path(p).relative_to(OUT).parts[0].startswith(PRE) for p in WRITTEN),
    "five_file_read_only_guard_explicitly_released": True, "no_broader_guard_held": True, "owned_background_execution": False, "new_execution_authority": False, "execution_counts": counts,
})
assert qa_path.is_file()
print(json.dumps({"status": "PASS_R2_STATIC_ARTIFACT_QA_ONE_P2_FIX_REQUIRED", "evidence_items": 42, "fixed_parent_blobs": 26, "source_anchors": len(anchors), "plan_questions": 7, "static_fixture_segments": 12, "new_findings": {"P2": 1}, "review_sha256": sha(review_path), "QA_sha256": sha(qa_path), "guard": "EXPLICITLY_RELEASED", "execution_counts": counts}, ensure_ascii=False))
