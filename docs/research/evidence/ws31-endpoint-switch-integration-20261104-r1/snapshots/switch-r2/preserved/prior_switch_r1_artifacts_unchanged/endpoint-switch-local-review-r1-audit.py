"""Local static source and artifact audit; never builds or executes scientific code."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import subprocess

ROOT = Path(r"E:\研\毕业论文\workspace\ws31-candidates-implementation")
OUT = Path(r"E:\研\毕业论文\workspace\LarryBUPT-conweave-ns3\docs\research\ws31\independent")
MAIN = OUT.parent / "main"
PRE = "endpoint-switch-local-review-r1"
R2 = "endpoint-channel-local-review-r2"
PARENT = "8cd1ba69469bf80143d5c89edc17fa72611018e8"
PLAN_HASH = "728a26f076559fd10165798a6d934994ad3c538a2a1a1f5692a19c3f1d485a2c"
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


plan_path = MAIN / (PRE + ".json")
assert sha(plan_path) == PLAN_HASH
plan = get(plan_path)
assert git("rev-parse", "HEAD").strip() == PARENT
status = git("status", "--short").splitlines()
assert len(status) == 9
working = {f: sha(ROOT / f) for f in plan["files_working_sha256"]}
assert working == plan["files_working_sha256"]
for f, h in working.items():
    assert sha(MAIN / plan["preserved_WIP"] / f) == h
main_files = [plan_path, MAIN / "endpoint-switch-contract-r1.md", MAIN / "evidence/endpoint-switch-wip-source-audit-r1.json", MAIN / "evidence/endpoint-channel-r2-requested-repair-r1.patch", MAIN / "evidence/endpoint-channel-local-review-main-acceptance-r2.json"]
main_hashes = {str(p): sha(p) for p in main_files}
source_audit = get(main_files[2])
assert source_audit["files_working_sha256"] == working
assert sha(main_files[3]) == source_audit["channel_patch_sha256"]
for f, h in source_audit["fixed_parent_Git_LF_source_links"].items():
    assert hashlib.sha256(blob(f)).hexdigest() == h

# Reuse the accepted R2 analysis. Check only its five-file delta here.
prior_qa_path = OUT / (R2 + "-qa.json")
prior_review_path = OUT / (R2 + "-review.json")
assert sha(prior_qa_path) == "5f7c160612ee3ec3fc43458a56bfc2c897201051dbe1613ca523da0aeb919662"
assert sha(prior_review_path) == "cf9deb2b6207231a707953b76d182beabe2de2c3d40e9b0bf29ec4c2889d2536"
prior_qa = get(prior_qa_path)
prior_hashes = dict(prior_qa["artifacts"])
prior_hashes[str(prior_qa_path)] = sha(prior_qa_path)
for p, h in prior_hashes.items():
    assert sha(p) == h
old_wip = OUT / (R2 + "-evidence") / "WIP"
HH = "src/point-to-point/model/qbb-channel.h"
CC = "src/point-to-point/model/qbb-channel.cc"
CH = "src/point-to-point/model/ws31-endpoint-channel.h"
TAG = "src/network/model/flow-id-num-tag.h"
FIX = "scratch/ws31-endpoint-channel-test.cc"
for f in [HH, CC]:
    old = (old_wip / f).read_text(encoding="utf-8")
    assert old.count("Ws31Leave leave") == 1
    assert (ROOT / f).read_text(encoding="utf-8") == old.replace("Ws31Leave leave", "const Ws31Leave &leave", 1)
for f in [CH, TAG]:
    assert (ROOT / f).read_bytes() == (old_wip / f).read_bytes()
old = (old_wip / FIX).read_text(encoding="utf-8")
helper = '''template<class F> void FailureMessage(const char *name,const char *expected,F operation) {
    bool caught=false;
    try { operation(); } catch (const std::exception &error) {
        caught=true; Require(std::string(error.what())==expected,"Original failure message was replaced");
    }
    Require(caught,"Expected original saved failure was not observed");
    std::cout << "WS31_ENDPOINT_CHANNEL_FAILURE case=" << name << " original_message=\\\"" << expected << "\\\"\\n";
}
'''
expected = old.replace("void FailAnimation(", helper + "void FailAnimation(", 1)
replacements = [
    ('Refuse("receive-failure-after-run",[&](){ session.RethrowFailure(); });', 'FailureMessage("receive-failure-after-run","controlled Receive failure",[&](){ session.RethrowFailure(); });'),
    ('Fail("animation-original-failure-retained",[&](){ session.RethrowFailure(); });', 'FailureMessage("animation-original-failure-retained","Controlled WS31 animation trace failure",\n                           [&](){ session.RethrowFailure(); });'),
    ('Fail("leave-failure-after-run",[&](){ session.RethrowFailure(); });', 'FailureMessage("leave-failure-after-run","Controlled WS31 observer boundary failure",\n                           [&](){ session.RethrowFailure(); });'),
]
for old_call, new_call in replacements:
    assert expected.count(old_call) == 1
    expected = expected.replace(old_call, new_call, 1)
assert (ROOT / FIX).read_text(encoding="utf-8") == expected

BUD = "src/point-to-point/model/ws31-budget.h"
QUOTA = "src/point-to-point/model/ws31-quota.h"
SW = "src/point-to-point/model/switch-node.h"
PROBE = "src/point-to-point/model/ws31-endpoint-switch-probe.h"
EP = "src/point-to-point/model/ws31-endpoint-probe.h"
restored = {}
w = (ROOT / BUD).read_bytes().replace(b"\r\n", b"\n")
w = w.replace(b"    bool Contains(const Key &key) const { return entries.count(key)!=0; }\n", b"", 1)
w = w.replace(b"    size_t PortCount() const { return ports.size(); }\n", b"", 1)
assert w == blob(BUD)
restored[BUD] = {"exact_parent_git_LF": True, "sha256": hashlib.sha256(w).hexdigest()}
w = (ROOT / QUOTA).read_bytes().replace(b"\r\n", b"\n")
a = w.index(b"    bool Contains(const QuotaKey &key)")
b = w.index(b"    bool Conserved() const", a)
w = w[:a] + w[b:]
assert w == blob(QUOTA)
restored[QUOTA] = {"exact_parent_git_LF": True, "sha256": hashlib.sha256(w).hexdigest()}
w = (ROOT / SW).read_bytes().replace(b"\r\n", b"\n").replace(b"    friend class Ws31EndpointSwitchProbe;\n", b"", 1)
assert w == blob(SW)
restored[SW] = {"exact_parent_git_LF": True, "sha256": hashlib.sha256(w).hexdigest()}
probe_text = (ROOT / PROBE).read_text(encoding="utf-8")
assert not re.search(r"\b(?:GetObject|Expire|Pressure|Value|Erase|Reset)\s*\(", probe_text)
macro_files = subprocess.check_output(["rg", "-l", "WS31_ENDPOINT_SWITCH_PROBE_H", "src", "scratch"], cwd=ROOT).decode().splitlines()
assert [p.replace("\\", "/") for p in macro_files] == [PROBE]

items = []
evidence = OUT / (PRE + "-evidence")
for f, h in working.items():
    p = evidence / "WIP" / f
    put(p, (ROOT / f).read_bytes())
    items.append({"path": str(p), "source": f, "sha256": h, "role": "nine frozen WIP working bytes"})
for source in main_files:
    p = evidence / "main-materials" / source.relative_to(MAIN)
    put(p, source.read_bytes())
    items.append({"path": str(p), "source": str(source), "sha256": sha(p), "role": "main plan/contract/audit/repair/acceptance source copy"})
fixed_sources = ["src/network/model/node.cc", "src/network/model/node.h", "src/network/model/node-list.h", "src/network/model/node-list.cc", "src/point-to-point/model/switch-node.cc", SW, BUD, QUOTA, EP, "src/point-to-point/model/ws31-endpoint-ledger.h", "src/core/model/make-event.h", "src/core/model/simulator.h", "src/core/model/type-traits.h", "src/point-to-point/model/point-to-point-net-device.cc", "src/point-to-point/model/point-to-point-net-device.h", "src/point-to-point/model/qbb-net-device.h"]
for f in fixed_sources:
    data = blob(f)
    if f not in working:
        assert (ROOT / f).read_bytes().replace(b"\r\n", b"\n") == data
    p = evidence / "fixed-parent" / f
    put(p, data)
    items.append({"path": str(p), "source": f, "sha256": sha(p), "role": "fixed parent Git blob", "git_blob": git("rev-parse", PARENT + ":" + f).strip()})
for f in [HH, CC, CH, TAG, FIX]:
    p = old_wip / f
    items.append({"path": str(p), "source": f, "sha256": sha(p), "role": "accepted R2 WIP for minimal-delta check", "reused_without_overwrite": True})
for p in [prior_review_path, prior_qa_path]:
    items.append({"path": str(p), "sha256": sha(p), "role": "accepted R2 analysis", "reused_without_overwrite": True})
literature = [x for x in get(OUT / (R2 + "-evidence-index.json"))["items"] if x["role"] == "literature recheck record snapshot"]
assert len(literature) == 6
for x in literature:
    assert sha(x["source"]) == x["sha256"]
    items.append(dict(x))
assert len(items) == 43
for x in items:
    assert sha(x["path"]) == x["sha256"]
    if x.get("git_blob"):
        data = Path(x["path"]).read_bytes()
        assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == x["git_blob"]
index_path = emit("-evidence-index.json", {"at_utc": UTC, "parent_head": PARENT, "new_byte_copies": 30, "reused_items": 13, "total_items": 43, "items": items, "old_evidence_not_overwritten": True})

specs = [
    (PROBE, 51, "scope.captured && scope.mode==Settings::lb_mode"),
    (PROBE, 57, "node==binding.node"), (PROBE, 58, "GetNDevices()==binding.devices.size()"),
    (PROBE, 60, "GetDevice(i)==binding.devices[i]"), (PROBE, 63, "typeid"),
    (PROBE, 70, "lb_mode>=33 && Settings::lb_mode<=50"), (PROBE, 76, "binding.type==0 || binding.type==1"),
    (PROBE, 78, "binding.type==1"), (PROBE, 80, "typeid"),
    (PROBE, 84, "binding.devices.push_back(node->GetDevice(i))"),
    (PROBE, 87, "switches>0"), (PROBE, 95, "base.observedNs==uint64_t(now)"),
    (PROBE, 96, "base.tuple==entry.tuple && base.generation==entry.generation"),
    (PROBE, 97, "EndpointSnapshot::ALL ^"), (PROBE, 98, "base.pinnedEntries==0"),
    (PROBE, 99, "endpoint.nodes==scope.nodes.size()"),
    (PROBE, 101, "const ws31::Key key"), (PROBE, 103, "result.snapshot=base"),
    (PROBE, 109, "m_ws30V13Pairs.count(key)"), (PROBE, 110, "m_ws31Pairs.count(key)"),
    (PROBE, 111, "m_ws31Budget.Contains(key)"), (PROBE, 112, "m_ws31Quota.Contains(key)"),
    (PROBE, 114, "allQ12Pins="), (PROBE, 115, "allBudget="),
    (PROBE, 116, "PortCount()"), (PROBE, 117, "SharedActivity()"),
    (PROBE, 118, "liveBorrowed"), (PROBE, 119, "snapshot.pinnedEntries"),
    (PROBE, 120, "snapshot.budgetEntries"), (PROBE, 123, "!result.switches.empty()"),
    (PROBE, 124, "observedFields|=ws31::EndpointSnapshot::SWITCH_STATE"),
    (BUD, 131, "Contains(const Key &key) const"), (BUD, 146, "PortCount() const"),
    (QUOTA, 112, "Contains(const QuotaKey &key) const"),
    (QUOTA, 118, "ActivitySnapshot SharedActivity() const"), (QUOTA, 120, "snapshot.seen[i]=seen[i]"),
    (QUOTA, 45, "void Expire"), (QUOTA, 49, "--liveBorrowed"), (QUOTA, 103, "void Erase"),
    (EP, 61, "struct Observation"), (EP, 67, "uint32_t nodes=0"),
    (EP, 90, "static void ValidateScope"), (EP, 99, "record.devices.size()"),
    (EP, 100, "record.node->GetDevice(i)==record.devices[i]"),
    (EP, 118, "nic.device->GetNode()==host.node"), (EP, 246, "ValidateScope(scope)"),
    (EP, 275, "observedNs=Simulator::Now()"), (EP, 307, "++result.nodes"),
    ("src/network/model/node.cc", 112, "device->SetNode (this)"),
    ("src/network/model/node.cc", 113, "device->SetIfIndex (index)"),
    ("src/network/model/node.cc", 125, "return m_devices[index]"),
    ("src/network/model/node.cc", 130, "return m_devices.size"),
    ("src/network/model/node.cc", 338, "return m_node_type"),
    ("src/point-to-point/model/point-to-point-net-device.cc", 370, "m_ifIndex = index"),
    ("src/point-to-point/model/point-to-point-net-device.cc", 543, "m_node = node"),
    ("src/point-to-point/model/switch-node.cc", 1344, "ch.sip, ch.dip, ch.udp.sport, ch.udp.dport"),
    ("src/point-to-point/model/switch-node.cc", 1390, "m_ws30V13Pairs.erase"),
    ("src/point-to-point/model/switch-node.cc", 1392, "m_ws31Pairs.erase"),
    ("src/point-to-point/model/switch-node.cc", 1393, "m_ws31Budget.Erase"),
    ("src/point-to-point/model/switch-node.cc", 1394, "m_ws31Quota.Erase"),
    ("src/point-to-point/model/switch-node.cc", 1459, "ws31::Key key(ch.sip,ch.dip,ch.udp.sport,ch.udp.dport)"),
    ("src/point-to-point/model/switch-node.cc", 1538, "ws31::QuotaKey(ch.sip,ch.dip,ch.udp.sport,ch.udp.dport)"),
    (HH, 143, "const Ws31Leave &leave"), (CC, 153, "const Ws31Leave &leave"),
    (FIX, 33, "std::string(error.what())==expected"),
    (FIX, 182, '"controlled Receive failure"'),
    (FIX, 245, '"Controlled WS31 animation trace failure"'),
    (FIX, 258, '"Controlled WS31 observer boundary failure"'),
]
anchors = []
for f, line, needle in specs:
    actual = (ROOT / f).read_text(encoding="utf-8").splitlines()[line - 1]
    assert needle in actual, (f, line, needle, actual)
    anchors.append({"path": f, "line": line, "contains": needle})

counts = {key: 0 for key in ["ssh_remote", "sync_deploy", "compile", "cpp_test_fixture", "network", "old_accepted_test_rerun", "scientific_source_edits", "main_edits", "commit", "push", "subagents"]}
findings = [
    {"id": "S1", "priority": 1, "severity": "P1", "status": "OPEN_MUST_FIX", "title": "Endpoint observation is not bound to the same switch scope and mutation-free read step", "anchors": [{"path": PROBE, "line": n} for n in [95, 99, 103, 124]] + [{"path": EP, "line": 61}], "counterexamples": ["Real endpoint Read E, add an interface without advancing time, Capture fresh switch scope B with same node count, then Read(E,B): existing checks accept stale endpoint coverage", "Real endpoint Read E then enqueue at same nanosecond before switch Read: old queue values are copied because time equality is not a state freshness proof"], "minimum_action": "Share and validate complete scope provenance and enforce one mutation-free combined actual endpoint/switch read. Prefer a combined entry that performs actual endpoint Read immediately with switch read; alternatively use enforced provenance/state versions. Timestamp/context alone is insufficient.", "claim_boundary": "Static conditional counterexamples only; no false drain or mask255 execution claimed"},
    {"id": "S2", "priority": 2, "severity": "P2", "status": "OPEN_MUST_FIX", "title": "Captured interface pointer slots omit actual owner/index/non-null/unique binding validation", "anchors": [{"path": PROBE, "line": 60}, {"path": PROBE, "line": 84}, {"path": "src/point-to-point/model/point-to-point-net-device.cc", "line": 370}, {"path": "src/point-to-point/model/point-to-point-net-device.cc", "line": 543}], "counterexample": "Capture, change a switch device's public ifIndex without changing Node device vector; current Validate still accepts. A reparented/shared device is not independently excluded either.", "minimum_action": "At Capture and Validate require non-null device, GetNode()==captured node and GetIfIndex()==slot; deduplicate over the full scope at Capture and preserve unique binding. Align allowed interface types with endpoint scope; do not repair bad objects during read.", "claim_boundary": "Upstream endpoint validation may reject some bad shapes, but it does not establish this new scope's own binding contract"},
]
fixture_requirements = [
    {"id": "F1", "topic": "actual objects/key coverage", "required": "Real drivers, savedTX/RX and EndpointProbe::Read127; at least one switch and a two-switch sum case; exact fourtuple excluding PG"},
    {"id": "F2", "topic": "purity", "required": "Capture before purity fingerprint; before/after successful and rejected reads fingerprint pin contents, budget entries/deadlines/totals/counters, quota entries/deadlines/activity/liveBorrowed, observed bytes/time and bindings, not only Size/Contains"},
    {"id": "F3", "topic": "miss/expiry", "required": "Missing key does not insert; overdue entries and stored liveBorrowed stay until production mutation; no Pressure/Value/WriteWs30V13State as a supposedly pure diagnostic"},
    {"id": "F4", "topic": "targeted cleanup", "required": "K plus unrelated K2 and shared history; after valid drain gate call original tuple cleanup and show K removed, K2/shared observed/seen/last retained, liveBorrowed changes only per original Erase"},
    {"id": "F5", "topic": "scope refusal", "required": "Default scope, no switch, unknown/false role, subclass, unsupported/changed mode, changed node/device shape, owner/index/shared-device failures"},
    {"id": "F6", "topic": "provenance/freshness refusal", "required": "Wrong identity/time/mask/prepopulated counts/node count; same-count recaptured scope with stale endpoint and same-nanosecond queue/interface changes"},
    {"id": "F7", "topic": "coverage versus lifecycle", "required": "Mask supplement does not override outstanding channel/held tokens, actual queues/events/history or endpoint state; no complete certificate merely from 255"},
]
review = {
    "at_utc": UTC, "client_date": "2026-11-01", "timezone": "Asia/Shanghai", "target": PRE,
    "source_chat": "01a19323-2201-7b23-a0f1-905c71496d38", "parent_chat": "01a19322-95a5-76e3-a4f5-1f1e9dde81ce",
    "status": "COMPLETE_FOR_LOCAL_STATIC_REVIEW_FIX_REQUIRED", "review_complete": True, "implementation_or_dynamic_validation_complete": False,
    "verdict": "FIX_REQUIRED_SCOPE_PROVENANCE_AND_INTERFACE_BINDING", "finding_counts": {"P1": 1, "P2": 1},
    "parent_head": PARENT, "observed_head": PARENT, "source_root": str(ROOT), "branch": git("branch", "--show-current").strip(), "git_status": status,
    "plan": {"path": str(plan_path), "sha256": PLAN_HASH}, "nine_WIP_working_sha256": working, "main_preserved_WIP_match": True,
    "channel_delta_review": {"prior_review_sha256": sha(prior_review_path), "prior_QA_sha256": sha(prior_qa_path), "prior_analysis_reused_not_repeated": True, "qbb_two_signature_changes_only": True, "channel_adapter_and_tag_header_unchanged": True, "fixture_changes_only_new_helper_and_three_exact_messages": True, "R2_01_status": "ADDRESSED_IN_SOURCE_NOT_BUILT_OR_RUN", "template_argument_proof": "U5 const-reference invocation, T5 event-owned function value retained", "C2_actual_G1_all_producers_shared_protocol_status": "INCOMPLETE"},
    "findings": findings,
    "plan_question_coverage": [{"question": q, "analysis_complete": True, "report_sections": sections} for q, sections in zip(plan["questions"], [["2"], ["3"], ["1:S1,S2", "3"], ["1:S1", "3"], ["3", "4"], ["4", "5"]])],
    "static_positive_findings": {"new_queries_const_no_expiry_insertion_cleanup": True, "three_header_restorations": restored, "no_new_data_members_or_virtual_functions_in_three_modified_switch_headers": True, "new_probe_forbidden_mutating_call_tokens_absent": True, "guard_macro_collision": False, "exact_SwitchNode_and_role_check": True, "at_least_one_switch": True, "current_mode_bound_to_setup": True, "mode_coverage": {"Q12": [33,34,35,43,44,45,46], "C1": [36,37,38,39,40,41,42], "C3": [47,48,49,50]}, "key": ["sip", "dip", "sport", "dport"], "endpoint_PG_excluded_from_switch_key": True, "target_and_global_shared_counts_separate": True, "mask_precondition": 127, "supplement_bit": 128, "nonempty_switch_rows_required": True, "mask255_measured": False, "liveBorrowed_semantics": "copied stored count without expiry, not recomputed active lease count"},
    "minimal_actual_switch_fixture_requirements": [{**x, "implemented_or_executed_in_this_review": False} for x in fixture_requirements],
    "important_node_literature_recheck": {"complete": True, "entry_records": "candidate README and reading-log", "unchanged_record_snapshots_reused": 6, "versions": [{"paper": "DiffFlow", "version": "arXiv:1604.05107v1", "specific_lesson": "state activation order and retirement proof are distinct; no complete reclaim protocol in read version", "scope_boundary": "simplified Java/no-full-TCP/separate queues do not prove RDMA state/effects"}, {"paper": "Flowcut", "version": "arXiv:2506.21406v2", "specific_lesson": "explicit in-flight/state ownership and protocol closure; retain shared history beyond one tuple", "scope_boundary": "ACK byte accounting and SST/Slingshot assumptions differ from map presence and do not prove generation reuse/effects"}], "new_mechanism_or_baseline_admission": False},
    "remaining_mandatory": ["S1/S2 repairs and new frozen source", "actual switch purity/refusal/cleanup fixture", "actual parsed G1 and every identity producer", "shared PFC/ACK/NACK/CNP/retransmit coverage", "completion callback and savedRX", "history release", "channel/held copy and real two-generation positive/negative cases", "independent C1 V0", "three-candidate matched ablation", "business/background two-sided effects", "state/runtime costs"],
    "exact_source_anchors": anchors, "evidence_index": str(index_path), "evidence_items": 43,
    "execution_counts": counts, "owned_background_execution": False, "new_execution_authority": False, "nine_file_read_only_guard": "EXPLICITLY_RELEASED_AT_DELIVERY", "old_deliveries_preserved": True,
}
review_path = emit("-review.json", review)

assert git("rev-parse", "HEAD").strip() == PARENT
assert git("status", "--short").splitlines() == status
assert {f: sha(ROOT / f) for f in working} == working
for p, h in main_hashes.items():
    assert sha(p) == h
for p, h in prior_hashes.items():
    assert sha(p) == h
release_path = emit("-guards-released.json", {"at_utc": UTC, "target": PRE, "status": "EXPLICITLY_RELEASED_AFTER_COMPLETED_LOCAL_STATIC_REVIEW", "source_root": str(ROOT), "head": PARENT, "scope": list(working), "working_sha256": working, "reason": "Static review delivered; S1 P1 and S2 P2 remain for main repair", "no_broader_guard_held": True, "owned_background_execution": False, "execution_counts": counts, "new_execution_authority": False})

links = 0
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
        links += 1
    assert not re.search(r"[０-９]", text)
    assert not re.search(r"^#{4,}", text, re.MULTILINE)
    assert not re.search(r"\n#{1,3} [^\n]+\n[^\n]", text)
assert len(re.findall(r"^## [1-9]\. ", (OUT / (PRE + "-handoff.md")).read_text(encoding="utf-8"), re.MULTILINE)) == 9
assert len(review["plan_question_coverage"]) == 6
artifact_paths = [OUT / (PRE + s) for s in ["-report.md", "-handoff.md", "-review.json", "-evidence-index.json", "-guards-released.json", "-audit.py"]]
qa_path = emit("-qa.json", {
    "at_utc": UTC, "status": "PASS_STATIC_REVIEW_ARTIFACT_QA_FIX_REQUIRED", "review_complete": True, "implementation_or_dynamic_validation_complete": False,
    "scope": "source/delta identities, exact source anchors, deletion restoration, evidence hashes and document QA; no scientific execution",
    "plan_sha256": PLAN_HASH, "head_unchanged": True, "git_status_unchanged": True, "nine_WIP_unchanged": True, "nine_main_preserved_copies_match": True,
    "main_materials_unchanged": main_hashes, "accepted_R2_artifacts_unchanged": prior_hashes,
    "minimal_channel_delta_verified": True, "unchanged_R2_cases_not_reanalyzed_or_rerun": True,
    "evidence_items_verified": 43, "new_byte_copies": 30, "reused_items": 13, "fixed_parent_blobs_verified": 16,
    "source_anchors_verified": len(anchors), "plan_questions_answered": 6, "restoration_checks": restored,
    "mutating_query_tokens_absent": True, "new_probe_guard_collision": False,
    "finding_counts": review["finding_counts"], "no_measured_mask255_or_network_certificate": True,
    "important_node_literature_recheck_complete": True, "nine_handoff_sections": True, "local_links_verified": links,
    "chinese_style_recheck": ["original ruanyf README and six chapters read earlier in this conversation", "heading hierarchy", "spacing", "sentences/paragraphs", "numbers/units", "punctuation", "document structure"],
    "artifacts": {str(p): sha(p) for p in artifact_paths}, "QA_self_hash": "not embedded",
    "only_allowed_prefix_written": all(Path(p).relative_to(OUT).parts[0].startswith(PRE) for p in WRITTEN),
    "nine_file_read_only_guard_explicitly_released": True, "no_broader_guard_held": True, "owned_background_execution": False, "new_execution_authority": False, "execution_counts": counts,
})
assert qa_path.is_file()
print(json.dumps({"status": "PASS_STATIC_REVIEW_ARTIFACT_QA_FIX_REQUIRED", "finding_counts": review["finding_counts"], "evidence_items": 43, "fixed_parent_blobs": 16, "source_anchors": len(anchors), "questions": 6, "review_sha256": sha(review_path), "QA_sha256": sha(qa_path), "guard": "EXPLICITLY_RELEASED", "execution_counts": counts}, ensure_ascii=False))
