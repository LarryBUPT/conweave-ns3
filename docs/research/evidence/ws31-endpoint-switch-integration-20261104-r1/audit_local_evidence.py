"""Read-only Integration audit of nodes 19/20 and the intervening channel review.

Only Git reads and file reads are used. Other checkers, C++, build systems and
simulators are never imported or executed. Original receipts remain untouched.
"""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def audit():
    out = Path(__file__).resolve().parent
    root = out.parents[3]
    ws = root / "docs/research/ws31"
    main, ind = ws / "main", ws / "independent"
    impl = root.parent / "ws31-candidates-implementation"
    fixed = "8cd1ba69469bf80143d5c89edc17fa72611018e8"
    git = lambda *args: subprocess.check_output(["git", "-C", str(impl), *args])
    blob = lambda path: git("show", fixed + ":" + path)
    manifest = {}

    def locate(value):
        text = str(value).replace("\\", "/")
        if "/docs/research/ws31/" in text:
            p = ws / text.split("/docs/research/ws31/", 1)[1]
            assert p.resolve().is_relative_to(ws.resolve())
        else:
            p = Path(value)
            assert p.resolve().is_relative_to(root.parent.parent.resolve())
        return p

    def capture(path, name, expected=None):
        data = path.read_bytes()
        if expected:
            assert sha(data) == expected, str(path)
        target = out / "snapshots" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert target.read_bytes() == data
        else:
            target.write_bytes(data)
        manifest[name] = {"source_path": str(path.resolve()), "snapshot": "snapshots/" + name,
                          "sha256": sha(data), "bytes": len(data)}
        return data

    def preserve_map(mapping, group):
        for value, expected in mapping.items():
            p = locate(value)
            capture(p, group + "/" + p.name, expected)

    def check_review(prefix, wip_key, main_preserved, expected_counts, group):
        review = read(ind / (prefix + "-review.json"))
        qa = read(ind / (prefix + "-qa.json"))
        assert review["review_complete"] and not review["implementation_or_dynamic_validation_complete"]
        assert review["parent_head"] == review["observed_head"] == fixed
        assert all(v == 0 for v in review["execution_counts"].values())
        assert qa["execution_counts"] == review["execution_counts"]
        assert not review["new_execution_authority"] and not qa["new_execution_authority"]
        preserve_map(qa["artifacts"], group + "/artifacts")
        capture(ind / (prefix + "-qa.json"), group + "/artifacts/" + prefix + "-qa.json")
        for key in ["main_materials_unchanged", "old_r1_artifacts_unchanged",
                    "accepted_R2_artifacts_unchanged", "prior_switch_r1_artifacts_unchanged",
                    "incomplete_stage_receipts_unchanged"]:
            if key in qa:
                preserve_map(qa[key], group + "/preserved/" + key)
        plan = locate(review["plan"]["path"])
        capture(plan, "main/" + plan.relative_to(main).as_posix(), review["plan"]["sha256"])
        index = read(locate(review["evidence_index"]))
        count, fixed_count, anchors_count = expected_counts
        assert len(index["items"]) == review["evidence_items"] == count
        parent_sources = []
        for item in index["items"]:
            p = locate(item["path"])
            data = capture(p, "indexed/" + item["sha256"][:16] + "-" + p.name, item["sha256"])
            if item.get("git_blob"):
                rel = item.get("source", "").replace("\\", "/")
                if not rel.startswith(("src/", "waf-tools/")):
                    rel = p.as_posix().split("/fixed-parent/", 1)[1]
                assert ".." not in Path(rel).parts
                assert data == blob(rel)
                assert git("rev-parse", fixed + ":" + rel).decode().strip() == item["git_blob"].strip()
                parent_sources.append(rel)
        assert len(parent_sources) == len(set(parent_sources)) == fixed_count
        wip = {}
        for rel, expected in review[wip_key].items():
            p = main / "evidence" / main_preserved / rel
            data = capture(p, group + "/wip/" + Path(rel).name, expected)
            wip[rel] = data
        for anchor in review["exact_source_anchors"]:
            rel = anchor["path"]
            data = wip[rel] if rel in wip else blob(rel)
            assert anchor["contains"] in data.decode("utf-8-sig").splitlines()[anchor["line"] - 1], anchor
        assert len(review["exact_source_anchors"]) == anchors_count
        release = read(ind / (prefix + "-guards-released.json"))
        assert not release["new_execution_authority"] and release["no_broader_guard_held"]
        assert all(v == 0 for v in release["execution_counts"].values())
        return review, qa, wip

    channel, cq, cw = check_review("endpoint-channel-local-review-r2", "five_WIP_working_sha256",
                                 "endpoint-channel-wip-r2-preserved", (42, 26, 67), "channel-r2")
    s1, q1, w1 = check_review("endpoint-switch-local-review-r1", "nine_WIP_working_sha256",
                            "endpoint-switch-wip-r1-preserved", (43, 16, 68), "switch-r1")
    s2, q2, w2 = check_review("endpoint-switch-local-review-r2", "ten_WIP_working_sha256",
                            "endpoint-switch-wip-r2-preserved", (62, 28, 68), "switch-r2")
    ca = read(main / "evidence/endpoint-channel-local-review-main-acceptance-r2.json")
    a1 = read(main / "evidence/endpoint-switch-local-review-main-acceptance-r1.json")
    a2 = read(main / "evidence/endpoint-switch-local-review-main-acceptance-r2.json")
    for pre, acc in [("endpoint-channel-local-review-r2", ca),
                     ("endpoint-switch-local-review-r1", a1), ("endpoint-switch-local-review-r2", a2)]:
        assert sha((ind / (pre + "-review.json")).read_bytes()) == acc["review_sha256"]
        assert sha((ind / (pre + "-qa.json")).read_bytes()) == acc["QA_sha256"]
    assert a1["verified"] == {"artifacts": 6, "accepted_R2_artifacts_unchanged": 7,
                               "main_materials_unchanged": 5, "fixed_parent": 16, "evidence": 43, "source_anchors": 68}
    assert a2["verified"]["evidence"] == 62 and a2["verified"]["fixed_parent"] == 28
    assert ca["exact_source_anchors_verified"] == 67
    assert channel["new_finding_counts"] == {"P1": 0, "P2": 1}
    assert [x["id"] for x in s1["findings"]] == ["S1", "S2"]
    assert [x["id"] for x in s2["findings"]] == ["R2-F1"]
    assert all(x["status"] == "ADDRESSED_IN_SOURCE_NOT_RUN" for x in s2["prior_resolution"])
    prior = read(root / "docs/research/evidence/ws31-endpoint-channel-integration-20261101-r1/verification.json")
    assert channel["five_WIP_working_sha256"] == prior["r2_working_hashes"]
    for rel in ["src/point-to-point/model/qbb-channel.h", "src/point-to-point/model/qbb-channel.cc"]:
        assert w1[rel].replace(b"\r\n", b"\n") == cw[rel].replace(b"\r\n", b"\n").replace(b"Ws31Leave leave", b"const Ws31Leave &leave", 1)
    for rel in ["src/point-to-point/model/ws31-endpoint-channel.h", "src/network/model/flow-id-num-tag.h"]:
        assert w1[rel] == cw[rel]
    chfix = w1["scratch/ws31-endpoint-channel-test.cc"].decode()
    assert "Original failure message was replaced" in chfix and chfix.count("FailureMessage(") == 4
    for rel in cw:
        assert w1[rel] == w2[rel]

    bud, quota, sw = ["src/point-to-point/model/" + x for x in ["ws31-budget.h", "ws31-quota.h", "switch-node.h"]]
    restored = w1[bud].replace(b"\r\n", b"\n")
    restored = restored.replace(b"    bool Contains(const Key &key) const { return entries.count(key)!=0; }\n", b"", 1)
    restored = restored.replace(b"    size_t PortCount() const { return ports.size(); }\n", b"", 1)
    assert restored == blob(bud)
    restored = w1[quota].replace(b"\r\n", b"\n")
    begin, end = restored.index(b"    bool Contains(const QuotaKey &key)"), restored.index(b"    bool Conserved() const")
    assert restored[:begin] + restored[end:] == blob(quota)
    assert w1[sw].replace(b"\r\n", b"\n").replace(b"    friend class Ws31EndpointSwitchProbe;\n", b"", 1) == blob(sw)
    for rel in [bud, quota, sw]:
        data = w2[rel].decode().replace("\r\n", "\n")
        data = data.replace("namespace ns3 { class Ws31EndpointSwitchFixture; namespace ws31 {", "namespace ns3 { namespace ws31 {")
        data = data.replace("    friend class ::ns3::Ws31EndpointSwitchFixture;\n", "")
        data = data.replace("    friend class Ws31EndpointSwitchFixture;\n", "")
        assert data == w1[rel].decode().replace("\r\n", "\n")
    probe = w2["src/point-to-point/model/ws31-endpoint-switch-probe.h"].decode()
    assert "class Scope {" in probe and "Ws31EndpointProbe::Scope endpoint;" in probe
    assert "result.endpoint=Ws31EndpointProbe::Read" in probe and "scope.endpoint=Ws31EndpointProbe::Capture(drivers)" in probe
    assert "const Ws31EndpointProbe::Observation &endpoint" not in probe
    assert probe.count("DeviceBinding(node,i,") == 2
    assert not re.search(r"\b(?:GetObject|Expire|Pressure|Value|Erase|Reset)\s*\(", probe)
    assert all(x in probe for x in ["device->GetNode()==node", "device->GetIfIndex()==slot", "seen.insert("])

    plan3_path = main / "endpoint-switch-local-review-r3.json"
    p3 = read(plan3_path)
    audit3 = read(main / "evidence/endpoint-switch-wip-source-audit-r3.json")
    assert sha(plan3_path.read_bytes()) == "b508f333802b730fbd8ab98229b7c9a161e4b2ffee276e75c5db9e45af735e04"
    assert p3["files_working_sha256"] == audit3["files_working_sha256"]
    w3 = {}
    for rel, expected in p3["files_working_sha256"].items():
        data = capture(impl / rel, "current-r3/" + Path(rel).name, expected)
        assert (main / "evidence/endpoint-switch-wip-r3-preserved" / rel).read_bytes() == data
        w3[rel] = data
    changed = [rel for rel in w3 if w3[rel] != w2[rel]]
    assert changed == p3["changed_paths"] == audit3["changed_paths"] == ["scratch/ws31-endpoint-switch-test.cc"]
    assert len(w3) == 10 and len(p3["unchanged_paths"]) == audit3["other_WIP_unchanged"] == 9
    fixture_path = changed[0]
    patch = "".join(difflib.unified_diff(w2[fixture_path].decode().splitlines(True), w3[fixture_path].decode().splitlines(True),
                                     fromfile="r2/" + fixture_path, tofile="r3/" + fixture_path))
    patch_path = main / "evidence/endpoint-switch-r2-to-r3-fixture.patch"
    assert patch_path.read_text(encoding="utf-8") == patch
    assert sha(patch_path.read_bytes()) == p3["delta_sha256"] == audit3["patch_sha256"]
    text = w3[fixture_path].decode()
    device = text[text.index("    static void Device("):text.index("class Ws31RoleNode")]
    assert "GetNode()->GetNodeType()" not in device
    assert device.index("if (!eq) return;") < device.index("eq->m_rrlast")
    assert device.index("if (!group) return;") < device.index("group->m_qps.size()")
    assert device.index("if (!qp) continue;") < device.index("qp->m_flow_id")
    assert 'denyReadBecause("switch-owner-changed","WS31 switch scope device owner/index/uniqueness changed")' in text
    assert "Require(before==state()" in text
    counts = s2["static_fixture_chronology"]
    assert (counts["planned_pairs"], counts["planned_composite_Read_calls"], counts["planned_Read_returns"],
            counts["planned_Read_refusals"], counts["planned_total_refusals"]) == (25, 63, 53, 10, 19)
    assert not counts["mask255_measured"] and not counts["natural_network_completion"]
    capture(main / "evidence/endpoint-switch-local-review-r2-interruption-recovery-r1.json", "main/evidence/endpoint-switch-local-review-r2-interruption-recovery-r1.json")
    recovery = read(main / "evidence/endpoint-switch-local-review-r2-interruption-recovery-r1.json")
    assert recovery["failed_turn"] == s2["recovery"]["failed_prior_turn"] == "01a19786-5399-7631-a7c8-c0517ab25c14"
    assert s2["recovery"]["incomplete_receipts_not_overwritten"]
    assert a2["explicit_release"] == "2026-11-04T06:58:12.280951+00:00"

    for node in [19, 20]:
        qa_path = main / ("evidence/endpoint-switch-node%d-main-QA-r1.json" % node)
        qa = read(qa_path)
        for rel, expected in qa["artifacts"].items():
            capture(main / rel, "main/" + rel, expected)
        capture(qa_path, "main/" + qa_path.relative_to(main).as_posix())
    for rel in ["endpoint-switch-local-review-r2.json", "endpoint-switch-local-review-r3.json",
                "endpoint-switch-contract-r1.md", "endpoint-switch-contract-r2.md", "endpoint-switch-fixture-repair-r3.md",
                "evidence/endpoint-switch-wip-source-audit-r1.json", "evidence/endpoint-switch-wip-source-audit-r2.json",
                "evidence/endpoint-channel-local-review-main-acceptance-r2.json"]:
        capture(main / rel, "main/" + rel)
    for node in [19, 20]:
        ref = read(main / ("evidence/endpoint-switch-node%d-reference-review-r1.json" % node))
        for value, expected in ref["local_records"].items():
            p = locate(value)
            if node == 20:
                capture(p, "literature-current/" + expected[:16] + "-" + p.name, expected)
            else:
                # Earlier README/log changed after 1 Nov; use original indexed
                # snapshot, never force historical hashes on the current file.
                matches = [x for x in read(ind / "endpoint-switch-local-review-r1-evidence-index.json")["items"] if x["sha256"] == expected]
                assert matches and locate(matches[0]["path"]).read_bytes()
        assert not ref["new_baseline_admission"]

    brief_qa_path = main / "evidence/ws31-c123-external-review-brief-20261104-r1-qa.json"
    bqa = read(brief_qa_path)
    brief = locate(bqa["candidate"]["path"])
    bdata = capture(brief, "main/" + brief.name, bqa["candidate"]["sha256"])
    assert len(bdata) == bqa["candidate"]["bytes"]
    capture(brief_qa_path, "main/" + brief_qa_path.relative_to(main).as_posix())
    capture(main / "current-status.json", "main/current-status.json")
    status = read(main / "current-status.json")
    assert status["independent_second_goal"] == "ACTIVE_LOCAL_READONLY_R3_SINGLE_FIXTURE_DELTA_REVIEW"
    assert git("rev-parse", "HEAD").decode().strip() == fixed
    assert git("rev-parse", "refs/remotes/origin/feature/ws31-candidates").decode().strip() == fixed
    assert git("branch", "--show-current").decode().strip() == "feature/ws31-candidates"
    assert git("remote", "get-url", "--push", "origin").decode().strip() == "https://github.com/LarryBUPT/conweave-ns3.git"
    gitstatus = git("status", "--porcelain", "-uall").decode().splitlines()
    assert {x[3:] for x in gitstatus} == set(w3)
    assert len([x for x in gitstatus if x.startswith(" M")]) == 6
    assert len([x for x in gitstatus if x.startswith("??")]) == 4
    receipt = {
        "at_utc": datetime.now(timezone.utc).isoformat(), "client_date": "2026-11-04",
        "status": "PASS_NODES19_20_STATIC_PROVENANCE_R3_FIXTURE_DELTA_WRITTEN_NOT_EXECUTED",
        "fixed_parent_head": fixed,
        "channel_r2": {"evidence": 42, "fixed_parent_copies": 26, "exact_anchors": 67,
                       "review_sha256": ca["review_sha256"], "new_finding": "R2-01/P2", "const_reference_repair_source_confirmed": True},
        "switch_r1": {"evidence": 43, "fixed_parent_copies": 16, "exact_anchors": 68, "WIP_preserved": 9,
                      "review_sha256": a1["review_sha256"], "QA_sha256": a1["QA_sha256"], "findings": ["S1/P1", "S2/P2"]},
        "switch_r2": {"evidence": 62, "fixed_parent_copies": 28, "exact_anchors": 68, "WIP_preserved": 10,
                      "review_sha256": a2["review_sha256"], "QA_sha256": a2["QA_sha256"], "finding": "R2-F1/P1",
                      "S1_S2_addressed_in_source_not_run": True},
        "overlapping_index_counts_are_separate_not_unique_union": True,
        "r1_switch_headers_restore_to_fixed_parent": 3,
        "r2_switch_headers_restore_to_r1_after_friend_removal": 3,
        "r3_changed_files": changed, "r3_unchanged_files": 9, "r3_current_and_preserved_files": 10,
        "r3_plan_sha256": sha(plan3_path.read_bytes()), "r3_working_hashes": p3["files_working_sha256"],
        "r3_delta_sha256": sha(patch_path.read_bytes()),
        "r3_source_check_scope": "Frozen byte identities, complete one-file diff and affected null checks/guard message; no C++ approval",
        "r3_independent_review_main_reported_cursor": status["independent_cursor"],
        "main_observed_cursor": "f13c4cd1-6458-4d58-888a-76f78e636578:1",
        "incomplete_review_failure_and_resume_receipts_preserved": True,
        "prior_usage_failure_turn": recovery["failed_turn"],
        "failure_verification_scope": "Preserved main recovery and independent resume/progress/final receipts; no new platform failure inspection",
        "r2_guard_released": a2["explicit_release"],
        "fingerprint_scope": a2["fingerprint_scope"],
        "planned_not_executed_counts": a2["planned_not_executed_counts"],
        "measured_mask255": 0, "new_cpp_build_fixture_or_network_execution": 0,
        "runtime_default_compatibility_cost_or_complete_lifecycle_accepted": False,
        "network_technical_total_unchanged": 43, "nonnetwork_adapter_conditions_unchanged": 17,
        "current_implementation_git_status": gitstatus,
        "external_brief": {"path": str(brief), "sha256": sha(bdata), "bytes": len(bdata),
                           "scope": "Delivered review document identity only; not external review/novelty/efficacy certification or new implementation authority"},
        "literature_current_records_verified": 6, "earlier_literature_records_preserved": True,
        "Flowcut_current_title_CCF_status": "UNRESOLVED_REFERENCE_ONLY", "new_baseline_admission": False,
        "remaining_mandatory": s2["remaining_mandatory"],
        "sole_independent_directly_polled_or_redispatched": False,
        "source_snapshot_files": len(list((out / "snapshots").rglob("*.*"))),
    }
    for name, value in [("source-manifest.json", manifest), ("verification.json", receipt)]:
        p = out / name
        assert not p.exists(), "Do not overwrite a successful receipt"
        p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "source_snapshots": receipt["source_snapshot_files"],
                      "r3_WIP": 10, "changed": 1, "execution": 0}, ensure_ascii=False))


if __name__ == "__main__":
    audit()
