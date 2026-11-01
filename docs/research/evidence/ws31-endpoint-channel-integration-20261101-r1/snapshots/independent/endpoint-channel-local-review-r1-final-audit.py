"""Local source/document audit only. Never builds, runs C++, or edits source/main."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import subprocess

ROOT = Path(r"E:\研\毕业论文\workspace\ws31-candidates-implementation")
OUT = Path(r"E:\研\毕业论文\workspace\LarryBUPT-conweave-ns3\docs\research\ws31\independent")
MAIN = OUT.parent / "main"
PREFIX = "endpoint-channel-local-review-r1"
PARENT = "8cd1ba69469bf80143d5c89edc17fa72611018e8"
PLAN_HASH = "5e73c6e98844c393dc63f6e2a1d141d6116af2466b8426156d6378da2c85d20d"
UTC = datetime.datetime.now(datetime.timezone.utc).isoformat()


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def emit_json(suffix, value):
    p = OUT / (PREFIX + suffix)
    assert p.parent == OUT and p.name.startswith(PREFIX + "-final-")
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8")


plan_path = MAIN / (PREFIX + ".json")
assert digest(plan_path) == PLAN_HASH
plan = read_json(plan_path)
checkpoint_path = OUT / (PREFIX + "-checkpoint.json")
checkpoint = read_json(checkpoint_path)
old_qa_path = OUT / (PREFIX + "-checkpoint-qa.json")
old_qa = read_json(old_qa_path)
old_qa_initial_hash = digest(old_qa_path)
assert old_qa["review_completed"] is False
assert digest(checkpoint_path) == "a7f03112ac87a43207d8ccd45f116ec6fde1fa55f844f183641f606221aeb7cc"
assert old_qa["status"] == "PASS_CHECKPOINT_INTEGRITY_REVIEW_INCOMPLETE"
for p, expected in old_qa["artifacts"].items():
    assert digest(p) == expected, p
assert git("rev-parse", "HEAD").strip() == PARENT
status = git("status", "--short").splitlines()
assert status == checkpoint["Git_status"], status
working = {p: digest(ROOT / p) for p in plan["files_working_sha256"]}
assert working == plan["files_working_sha256"]

main_hashes = {
    str(plan_path): PLAN_HASH,
    str(MAIN / "endpoint-channel-contract-r1.md"): "267844db96f9cba258bf4e0f9fd44f504bebd0300b238f98dec8cc8c9630bba4",
    str(MAIN / "evidence/endpoint-channel-wip-source-audit-r1.json"): "103c443d1c42ff96357d378571e6dcca821ca1625899a2654b48709c782eff43",
}
for p, expected in main_hashes.items():
    assert digest(p) == expected

index_path = OUT / (PREFIX + "-final-evidence-index.json")
index = read_json(index_path)
assert len(index["items"]) == 36
for item in index["items"]:
    assert digest(item["path"]) == item["sha256"], item["path"]
    if item.get("git_blob"):
        data = Path(item["path"]).read_bytes()
        obj = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        assert obj == item["git_blob"]

# Reproduce the deletion-only restoration, allowing CRLF -> LF in working bytes.
def blob(p):
    return subprocess.check_output(["git", "show", PARENT + ":" + p], cwd=ROOT)


restoration = {}
p = "src/point-to-point/model/qbb-channel.cc"
w = (ROOT / p).read_bytes().replace(b"\r\n", b"\n")
w = w.replace(b"#include <limits>\n#include <stdexcept>\n", b"", 1)
a = w.index(b"  if (!m_ws31Enter)\n")
b = w.index(b"\n  // Call the tx anim callback", a)
original = w[a:b].split(b"    {\n", 1)[1].split(b"\n    }\n  else", 1)[0]
original = original.replace(b"      Simulator::ScheduleWithContext", b"  Simulator::ScheduleWithContext", 1)
w = w[:a] + original + b"\n" + w[b:]
a = w.index(b"void\nQbbChannel::DeliverWs31")
b = w.index(b"uint32_t \nQbbChannel::GetNDevices", a)
w = w[:a] + w[b:]
assert w == blob(p)
restoration[p] = {"exact_parent_git_LF": True, "sha256": hashlib.sha256(w).hexdigest()}
p = "src/point-to-point/model/qbb-channel.h"
w = (ROOT / p).read_bytes().replace(b"\r\n", b"\n")
w = w.replace(b"#include <functional>\n", b"", 1).replace(b"class Ws31EndpointChannel;\n", b"", 1)
a = w.index(b"  // Empty for ordinary simulations.")
b = w.index(b"  // Each point to point link", a)
w = w[:a] + w[b:]
assert w == blob(p)
restoration[p] = {"exact_parent_git_LF": True, "sha256": hashlib.sha256(w).hexdigest()}
p = "src/network/model/flow-id-num-tag.h"
w = (ROOT / p).read_bytes().replace(b"\r\n", b"\n")
w = w.replace(b"#ifndef NS3_FLOW_ID_NUM_TAG_H\n#define NS3_FLOW_ID_NUM_TAG_H\n\n", b"", 1)
w = w.replace(b"#endif // NS3_FLOW_ID_NUM_TAG_H\n\n", b"", 1)
assert w == blob(p)
restoration[p] = {"exact_parent_git_LF": True, "sha256": hashlib.sha256(w).hexdigest()}

guard_matches = subprocess.check_output(
    ["rg", "-l", "NS3_FLOW_ID_NUM_TAG_H|WS31_ENDPOINT_CHANNEL_H", "src", "scratch", "--glob", "*.[hc]*"], cwd=ROOT
).decode().splitlines()
assert sorted(x.replace("\\", "/") for x in guard_matches) == sorted([
    "src/network/model/flow-id-num-tag.h", "src/point-to-point/model/ws31-endpoint-channel.h"
])

CH = "src/point-to-point/model/ws31-endpoint-channel.h"
CC = "src/point-to-point/model/qbb-channel.cc"
TAG = "src/network/model/flow-id-num-tag.cc"
FIX = "scratch/ws31-endpoint-channel-test.cc"
SIM = "src/core/model/default-simulator-impl.cc"
anchors = []


def anchor(path, line, expected):
    actual = (ROOT / path).read_text(encoding="utf-8").splitlines()[line - 1]
    assert expected in actual, (path, line, expected, actual)
    item = {"path": path, "line": line, "contains": expected}
    anchors.append(item)
    return item


findings = [
    {
        "id": "C1", "priority": 1, "severity": "P1", "status": "OPEN_REQUIRES_MAIN_FIX",
        "title": "TypeId equality does not prove exact C++ dynamic channel type",
        "anchors": [anchor(CH, 112, "GetInstanceTypeId()"), anchor("src/core/model/object.h", 417, "T::GetTypeId"), anchor("src/core/model/object.cc", 79, "return m_tid"), anchor("src/point-to-point/model/qbb-channel.h", 76, "virtual bool TransmitStart")],
        "trigger": "CreateObject of a derived QbbChannel inheriting GetTypeId while overriding TransmitStart; attach two devices and Bind",
        "consequence": "Bind may accept a subclass that bypasses the observation wrapper; registered remote-channel rejection does not cover it",
        "minimum_action": "Use exact C++ dynamic-type proof or equally strong enforced provenance across construction paths; add unregistered overriding-subclass refusal. Base dynamic_cast alone is insufficient.",
        "evidence": "static source chain and counterexample; not executed",
    },
    {
        "id": "C2", "priority": 1, "severity": "P1", "status": "OPEN_REQUIRES_IDENTITY_CONTRACT",
        "title": "U16 tag serialization aliases signed and high int32 flow identities",
        "anchors": [anchor(CH, 63, "PeekPacketTag(tag)"), anchor(CH, 103, "void Register"), anchor(TAG, 43, "WriteU16(flow_stat)"), anchor(TAG, 50, "ReadU16()"), anchor("src/network/model/packet.cc", 843, "m_packetTagList.Add"), anchor("src/network/model/packet-tag-list.cc", 147, "tag.Serialize"), anchor("src/network/model/packet-tag-list.cc", 162, "tag.Deserialize"), anchor(FIX, 83, 'Refuse("negative-tag"')],
        "trigger": "SetId(-1) or SetId(65536), AddPacketTag, then Peek; decoded IDs are 65535 and 0 respectively",
        "consequence": "The existing negative test is an unregistered-65535 rejection. If decoded low identity is registered, an invalid original identity may be charged to the wrong request/generation.",
        "minimum_action": "Freeze a representable, unique identity domain and enforce it at actual G1/producers before serialization plus registration; or separately design full-width observation identity. Register range checks alone cannot detect already-truncated aliases. Preserve baseline tag body in current scope.",
        "minimum_cases": ["-1 with registered 65535", "65536 with registered 0", "legal identity boundaries", "unique IDs across generations", "all fixture tag fields initialized"],
        "evidence": "exact Packet/Add/Serialize and Peek/Deserialize source chain; no runtime result",
    },
    {
        "id": "C3", "priority": 1, "severity": "P1", "status": "OPEN_REQUIRES_FIXTURE_FIX",
        "title": "New Tagged helper serializes uninitialized flow_size",
        "anchors": [anchor(FIX, 51, "tag.SetId(id); packet->AddPacketTag(tag)"), anchor(TAG, 14, "flow_stat(0)"), anchor(TAG, 44, "WriteU32(flow_size)"), anchor("src/point-to-point/model/rdma-hw.cc", 1151, "SetFlowSize")],
        "trigger": "Every new Tagged(id) helper call",
        "consequence": "Reading an indeterminate integer during serialization invalidates the fixture's reliable C++ behavior; it is independent of identity truncation",
        "minimum_action": "Initialize SetFlowSize to a defined fixture size before AddPacketTag in the new helper; retain original tag class body/API",
        "evidence": "static constructor/serializer/helper comparison; no execution",
    },
    {
        "id": "C4", "priority": 2, "severity": "P2", "status": "OPEN_REQUIRES_ERROR_PROCESS_CONTRACT",
        "title": "Rethrow through old simulator event loop skips current event Unref",
        "anchors": [anchor(CC, 151, "throw;"), anchor(SIM, 133, "RemoveNext"), anchor(SIM, 142, "Invoke"), anchor(SIM, 143, "Unref"), anchor("src/core/model/scheduler.h", 72, "EventImpl *impl"), anchor("src/core/model/make-event.h", 433, "m_a1"), anchor(SIM, 84, "RemoveNext"), anchor(FIX, 139, 'Refuse("receive-throws"')],
        "trigger": "Receive or leave throws from DeliverWs31 and the fixture catches outside Simulator::Run",
        "consequence": "Already-removed current event retains its reference, channel/destination/packet/leave and State/ledger; Destroy cannot locate this current event. The fixture may still print PASS and exit; crash is not asserted.",
        "minimum_action": "Choose and document either event-local failure capture/Stop with normal event return and reporting outside Run, or an isolated one-shot terminal negative process with no cleanup/reuse claim. Do not patch simulator baseline just for the fixture.",
        "evidence": "local source ownership proof; no execution or measured leak size",
    },
    {
        "id": "C5", "priority": 1, "severity": "P1", "status": "OPEN_REQUIRES_POSTMUTATION_LATCH_OR_ATOMIC_COMMIT",
        "title": "Postmutation failures can leave partial accounting without terminal failure latching",
        "anchors": [anchor(CH, 74, "ledger->Enter"), anchor(CH, 75, "history.push_back"), anchor(CH, 76, "open.insert"), anchor(CH, 148, "Pending()==0"), anchor(CC, 120, "++m_ws31Pending"), anchor(CC, 122, "ScheduleWithContext"), anchor(CC, 129, "m_txrxQbb"), anchor(CH, 126, "channels.push_back"), anchor(CH, 131, "m_ws31Leave="), anchor(CH, 132, "m_ws31Owner=")],
        "trigger": "Allocation failure after ledger Enter, scheduling/function-copy failure after pending increment, animation callback throw after scheduling, or partial Bind assignment failure",
        "consequence": "Enter allocation failure may leave ledger token while Pending/open are zero and Finish succeeds. Animation failure may be followed by normal delivery/Finish with no failure latch. This does not mean the full ledger drain check accepts an outstanding token.",
        "minimum_action": "Keep pre-mutation missing/unknown-tag refusals recoverable; stage setup with no-throw commit or terminally latch any postmutation observer/session/channel failure, covering Enter, schedule and animation. Do not fabricate RECEIVE_RETURNED as rollback when delivery is absent or uncertain.",
        "minimum_cases": ["history/open allocation failure after ledger Enter", "event construction/callback copy/scheduler insertion failure", "animation callback failure", "partial Bind failure", "recoverable invalid inputs stay token-free"],
        "evidence": "source mutation order and conditional failure paths; fault injection not run",
    },
]

# Further exact anchors for successful mechanics and integration obligations.
for values in [
    ("src/core/model/simulator.h", 975, "ScheduleWithContext"),
    ("src/core/model/simulator.h", 977, "MakeEvent (f, a1, a2, a3, a4, a5)"),
    ("src/core/model/type-traits.h", 21, "typedef U ReferencedType"),
    ("src/point-to-point/model/qbb-net-device.h", 101, "virtual void Receive"),
    (CC, 106, "ScheduleWithContext"), (CC, 142, "destination->Receive"),
    (CC, 144, "leave (serial)"), (CC, 145, "--channel->m_ws31Pending"),
    (CH, 89, "ledger->Close"), (CH, 101, "No destructor cleanup"),
    ("src/point-to-point/model/qbb-net-device.cc", 503, "m_channel = ch"),
    ("src/point-to-point/model/qbb-net-device.h", 177, "Ptr<QbbChannel> m_channel"),
    ("src/point-to-point/model/point-to-point-net-device.h", 289, "Ptr<PointToPointChannel> m_channel"),
    ("src/point-to-point/model/point-to-point-net-device.cc", 186, "m_channel = 0"),
    ("src/point-to-point/model/qbb-net-device.cc", 481, "SendPfc"),
    ("src/point-to-point/model/qbb-net-device.cc", 483, "Create<Packet>(0)"),
    ("src/point-to-point/model/qbb-net-device.cc", 382, "!m_linkUp"),
    ("src/point-to-point/model/qbb-net-device.cc", 390, "m_receiveErrorModel"),
    ("src/point-to-point/model/qbb-net-device.cc", 407, "!m_qbbEnabled"),
    ("src/point-to-point/model/qbb-net-device.cc", 433, "SwitchReceiveFromDevice"),
    ("src/point-to-point/model/qbb-net-device.cc", 436, "m_rdmaReceiveCb"),
]:
    anchor(*values)

counts = {name: 0 for name in ["ssh_remote_experiment", "sync_deploy", "compile", "cpp_test_fixture", "network_simulation", "old_accepted_test_rerun", "scientific_source_edits", "main_edits", "commit", "push", "subagents"]}
obligations = [
    {"id": "I1", "required": True, "topic": "Bind before every related transmission; reject/forbid late binding over default scheduled deliveries, including any default traffic between Finish and rebind", "scope": "G1/integration precondition; current fixture uses distinct Pair for default-off"},
    {"id": "I2", "required": True, "topic": "Keep normal session owner until explicit Finish; callbacks retain State safely after owner loss but binding cannot be normally taken over", "scope": "lifecycle contract, no automatic destructor closure"},
    {"id": "I3", "required": True, "topic": "Separate preexisting Qbb device/channel strong references from new callback ownership and exception-retained event roots; no full teardown reclamation claim", "scope": "lifetime and cost verification"},
    {"id": "I4", "required": True, "topic": "Freeze actual data/ACK/NACK/CNP/retransmit/shared-PFC coverage and provenance; shared packets need explicit shared/global accounting rather than arbitrary per-flow tags", "scope": "production protocol integration; untagged PFC is not supported by current fixture-only adapter"},
    {"id": "I5", "required": True, "topic": "Receive return closes this event only; include early-return/drop, actual forwarding, endpoint completion, savedRX, queue/timers and history separately", "scope": "complete endpoint/network proof"},
]
tests = [
    ("T1", "Exact channel and unregistered overriding subclass"),
    ("T2", "Initialized tag round-trip, signed/high aliases, legal boundaries and unique cross-generation identities"),
    ("T3", "Receive/leave failure without fabricated closure under explicit terminal/recoverable event contract"),
    ("T4", "Postmutation allocation/schedule/animation/Bind failure plus recoverable pre-mutation refusal"),
    ("T5", "Idle/inflight owner loss, callback lifetime, no normal takeover, reference retention attribution"),
    ("T6", "G1 setup-before-default-delivery and rebind epoch admission"),
    ("T7", "Original Ptr/context/delay/event count/animation order and nested completion timing"),
    ("T8", "Production Receive early return/drop, PFC, switch, RDMA completion and savedRX"),
    ("T9", "Real switch/history/G1/two-generation positive and negative network cases; independent V0, matched ablation, both workloads and costs"),
]
review = {
    "at_utc": UTC, "client_date": "2026-11-01", "timezone": "Asia/Shanghai",
    "source_chat": "01a19323-2201-7b23-a0f1-905c71496d38", "parent_chat": "01a19322-95a5-76e3-a4f5-1f1e9dde81ce",
    "target": PREFIX, "status": "COMPLETE_FOR_LOCAL_STATIC_REVIEW_FIX_REQUIRED",
    "verdict": "FIX_REQUIRED_NOT_APPROVED_FOR_UNCHANGED_ENGINEERING_EXECUTION",
    "review_complete": True, "implementation_or_scientific_validation_complete": False,
    "scope": plan["scope"], "source_root": str(ROOT), "branch": git("branch", "--show-current").strip(),
    "parent_head": PARENT, "observed_head": PARENT, "git_status": status,
    "plan": {"path": str(plan_path), "sha256": PLAN_HASH}, "five_WIP_working_sha256": working,
    "findings": findings, "finding_counts": {"P1": 4, "P2": 1},
    "plan_question_coverage": [{"question": q, "analysis_complete": True, "report_sections": refs} for q, refs in zip(plan["questions"], [["1", "3"], ["3"], ["2:C4,C5", "4:I1,I2,I3"], ["2:C2", "4:I4,I5"], ["2", "5"], ["5:T9", "7"]])],
    "restoration_checks": restoration, "guard_macro_collision_in_src_scratch": False,
    "normal_path_static_findings": {
        "event_template": "Old five-argument free-function ScheduleWithContext/MakeEvent exists; non-reference argument members store Ptr and function copies by value; no compilation claimed",
        "same_packet_delay_context": True, "one_replacement_delivery_event": True,
        "animation_order": "schedule delivery first, trace second, for default and observed successful paths; trace side effects not executed",
        "closure_order": ["full Receive returns", "leave closes ledger", "decrement channel pending"],
        "serial_identity": "ledger-generated serial carried by each event; same packet UID may have multiple independent serials",
        "normal_fixture_trace": {"evidence_level": "static_not_executed", "return_ns": [13, 13, 16], "receive_visible_pending": [2, 2, 1], "nested_peak_pending": 3, "serials": [1, 2, 3]},
        "no_new_state_to_channel_ownership_cycle": True,
        "no_destructor_fabricated_finish": True,
        "no_full_teardown_reclamation_claim": True,
    },
    "mandatory_integration_obligations": obligations,
    "minimum_next_cases": [{"id": i, "description": d, "status": "NOT_RUN_REQUIRED_IN_NEW_MAIN_PLAN"} for i, d in tests],
    "remaining_mandatory": ["C1-C5 decisions/fixes and new frozen source", "actual parsed G1", "real switch read-only observation", "completion callback and savedRX", "history release", "two-generation production network positive/negative cases", "independent V0", "three-candidate matched ablation", "business/background two-sided effects", "state/runtime costs"],
    "literature_recheck": {
        "complete_for_this_review_node": True, "source_records": str(index_path),
        "versions": [
            {"paper": "DiffFlow", "version": "arXiv:1604.05107v1", "pdf_sha256": "f552fcb75a0cec582286db0032c81660ff161fe475609ae5e79ad7075a0ae164", "lesson": "separate classification, control activation and real transport coverage/cost", "boundary": "Java simplified transport and separate queues; no RDMA/MoE dual-metric or endpoint-certificate inference"},
            {"paper": "Flowcut", "version": "arXiv:2506.21406v2", "pdf_sha256": "1ba1e8cbad41973d3b42112a1a33876629541da814ac56bd06132439704fd1a1", "lesson": "explicit in-flight closure conditions and drain/pause costs", "boundary": "ACK-byte closure differs from Receive-event return; SST/Slingshot/BDP assumptions and reported effects do not prove project drain or generation reuse"},
        ], "new_mechanism_or_baseline_admission": False,
    },
    "exact_source_anchors": anchors,
    "additional_inspected_fixed_parent_fingerprints": {p: hashlib.sha256(blob(p)).hexdigest() for p in ["src/core/model/scheduler.h"]},
    "evidence_index": str(index_path), "evidence_items": 36,
    "execution_counts": counts, "owned_background_execution": False,
    "five_file_read_only_guard": "EXPLICITLY_RELEASED_AT_DELIVERY", "new_execution_authority": False,
    "old_checkpoint_status": "PRESERVED_INCOMPLETE_USER_SHUTDOWN_CHECKPOINT_NOT_OVERWRITTEN",
    "report": str(OUT / (PREFIX + "-final-report.md")), "handoff": str(OUT / (PREFIX + "-final-handoff.md")),
}
review_path = emit_json("-final-review.json", review)
release_path = emit_json("-final-guards-released.json", {
    "at_utc": UTC, "target": PREFIX, "status": "EXPLICITLY_RELEASED_AFTER_FINAL_LOCAL_STATIC_REVIEW",
    "scope": list(working), "source_root": str(ROOT), "head": PARENT, "verified_working_sha256": working,
    "reason": "Final review/report/QA/handoff delivered; 4 P1 and 1 P2 open for main; no source changes by reviewer",
    "no_broader_guard_held": True, "owned_background_execution": False, "new_execution_authority": False,
    "execution_counts": counts, "old_release_receipt_preserved": True,
})

# Check internal links and source line numbers in the generated human artifacts.
links_checked = []
for suffix in ["-final-report.md", "-final-handoff.md"]:
    p = OUT / (PREFIX + suffix)
    text = p.read_text(encoding="utf-8")
    for href in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        if href.startswith("https://"):
            continue
        match = re.match(r"^(.*):(\d+)$", href)
        target = match.group(1) if match else href
        resolved = Path(target) if re.match(r"^[A-Za-z]:[/\\]", target) else p.parent / target
        # QA is emitted below, so its target is intentionally deferred.
        if resolved.name != PREFIX + "-final-qa.json":
            assert resolved.is_file(), (p, href)
            if match:
                assert int(match.group(2)) <= len(resolved.read_text(encoding="utf-8-sig").splitlines())
        links_checked.append({"document": p.name, "target": href})
    assert not re.search(r"[０-９]", text)
    assert not re.search(r"^#{4,}", text, re.MULTILINE)
    assert not re.search(r"^#{1,3} .*[:：。，；]$", text, re.MULTILINE)
    assert not re.search(r"\n#{1,3} [^\n]+\n[^\n]", text)
assert len(re.findall(r"^## [1-9]\. ", (OUT / (PREFIX + "-final-handoff.md")).read_text(encoding="utf-8"), re.MULTILINE)) == 9
assert len(review["plan_question_coverage"]) == 6
assert sum(x["severity"] == "P1" for x in findings) == 4
assert sum(x["severity"] == "P2" for x in findings) == 1

# Final source and old evidence identity check. No source/main or Git mutations.
assert git("rev-parse", "HEAD").strip() == PARENT
assert git("status", "--short").splitlines() == status
assert {p: digest(ROOT / p) for p in working} == working
for p, expected in main_hashes.items():
    assert digest(p) == expected
for p, expected in old_qa["artifacts"].items():
    assert digest(p) == expected
assert digest(old_qa_path) == old_qa_initial_hash
artifact_paths = [
    OUT / (PREFIX + s) for s in ["-final-report.md", "-final-handoff.md", "-final-review.json", "-final-guards-released.json", "-final-evidence-index.json", "-final-audit.py"]
]
qa = {
    "at_utc": UTC, "status": "PASS_LOCAL_STATIC_REVIEW_ARTIFACT_QA_FIXES_REQUIRED",
    "scope": "source identity, static source anchors, deletion-only restoration, artifact hashes/links/sections; not a C++ test or scientific execution",
    "review_completed": True, "implementation_or_validation_completed": False,
    "verdict": review["verdict"], "finding_counts": review["finding_counts"],
    "plan_sha256": PLAN_HASH, "head_unchanged": True, "five_WIP_bytes_unchanged": True, "git_status_unchanged": True,
    "main_materials_unchanged": True, "old_checkpoint_and_release_unchanged": True,
    "old_checkpoint_qa_sha256_observed": digest(old_qa_path),
    "old_checkpoint_evidence_items_verified": 23, "new_evidence_items_verified": 13, "total_evidence_items_verified": 36,
    "fixed_parent_git_blob_ids_verified": True, "source_anchor_count_verified": len(anchors),
    "plan_questions_answered": 6, "restoration_checks": restoration,
    "guard_macro_collision_in_src_scratch": False,
    "nine_handoff_sections": True, "local_links_checked": len(links_checked), "local_links_valid": True,
    "chinese_style": {"original_readme_and_six_chapters_read": True, "original_url": "https://github.com/ruanyf/document-style-guide", "manual_checks": ["heading hierarchy", "spacing", "sentences/paragraphs", "numbers/units", "punctuation", "document structure"], "basic_format_checks": True},
    "important_node_literature_recheck_complete": True,
    "audit_tool_corrections": ["Initial document-audit invocation stopped on a mistyped rdma-hw.cc path (network/model instead of point-to-point/model); corrected only this audit script, then read the same frozen source bytes. No C++ or scientific retry."],
    "execution_counts": counts, "owned_background_execution": False, "five_file_read_only_guard_explicitly_released": True,
    "new_execution_authority": False, "only_allowed_prefix_written": True,
    "artifacts": {str(p): digest(p) for p in artifact_paths}, "QA_self_hash": "not embedded",
}
qa_path = emit_json("-final-qa.json", qa)
assert qa_path.is_file()
for item in links_checked:
    if item["target"] == qa_path.name:
        assert qa_path.exists()
print(json.dumps({"status": qa["status"], "counts": review["finding_counts"], "source_anchors": len(anchors), "evidence_items": 36, "local_links": len(links_checked), "review_sha256": digest(review_path), "QA_sha256": digest(qa_path), "read_only_guard": "EXPLICITLY_RELEASED", "scientific_execution_counts": counts}, ensure_ascii=False))
