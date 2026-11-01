"""Read-only provenance audit of channel r1 review and unexecuted r2 WIP.

This program never imports/runs another checker, compiler, fixture or simulator.
Its only writes are new Integration-owned snapshots and receipts beside itself.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    out = Path(__file__).resolve().parent
    root = out.parents[3]
    ws = root / "docs/research/ws31"
    m, ind = ws / "main", ws / "independent"
    impl = root.parent / "ws31-candidates-implementation"
    parent = "8cd1ba69469bf80143d5c89edc17fa72611018e8"
    pre = "endpoint-channel-local-review-r1"
    git = lambda *args: subprocess.check_output(["git", "-C", str(impl), *args])
    manifest = {}

    def owned_path(path):
        # JSON may contain escaped historical workspace prefixes. Anchor only
        # a known suffix, and validate containment before opening the file.
        text = str(path).replace("\\", "/")
        if "/docs/research/ws31/" in text:
            p = ws / text.split("/docs/research/ws31/", 1)[1]
            assert p.resolve().is_relative_to(ws.resolve())
            return p
        p = Path(path)
        assert p.resolve().is_relative_to(root.parent.parent.resolve())
        return p

    def capture(path, dest, expected=None):
        path = Path(path)
        data = path.read_bytes()
        if expected:
            assert sha(data) == expected, str(path)
        snapshot = out / "snapshots" / dest
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        if snapshot.exists():
            assert snapshot.read_bytes() == data, str(snapshot)
        else:
            snapshot.write_bytes(data)
        manifest[dest] = {"source_path": str(path.resolve()), "snapshot": "snapshots/" + dest,
                          "bytes": len(data), "sha256": sha(data)}
        return data

    def blob(path):
        return git("show", parent + ":" + path)

    review_path = ind / (pre + "-final-review.json")
    qa_path = ind / (pre + "-final-qa.json")
    review, qa = read(review_path), read(qa_path)
    accepted = read(m / "evidence/endpoint-channel-local-review-main-acceptance-r1.json")
    assert review["review_complete"] and not review["implementation_or_scientific_validation_complete"]
    assert review["finding_counts"] == accepted["counts"] == {"P1": 4, "P2": 1}
    assert [x["id"] for x in review["findings"]] == ["C1", "C2", "C3", "C4", "C5"]
    assert review["parent_head"] == review["observed_head"] == accepted["parent_head"] == parent
    assert all(v == 0 for v in review["execution_counts"].values())
    assert qa["execution_counts"] == review["execution_counts"]
    assert not review["new_execution_authority"] and not qa["new_execution_authority"]
    assert sha(review_path.read_bytes()) == accepted["review_sha256"] == "85b22cc6a3393d2f4d07d597d32128864aa2e95eb06e6c20481b01c208e7f1f9"
    assert sha(qa_path.read_bytes()) == accepted["QA_sha256"] == "9e96f3f9480a0f88feb76f94fd0d9299985afc9db9cfa8750bd97b7e825141fe"
    capture(qa_path, "independent/" + qa_path.name)
    for path, expected in qa["artifacts"].items():
        p = owned_path(path)
        capture(p, "independent/" + p.name, expected)
    for key, suffix in [("report_sha256", "-final-report.md"), ("evidence_index_sha256", "-final-evidence-index.json")]:
        assert sha((ind / (pre + suffix)).read_bytes()) == accepted[key]
    r1plan = m / (pre + ".json")
    capture(r1plan, "main/" + r1plan.name, review["plan"]["sha256"])

    index = read(ind / (pre + "-final-evidence-index.json"))
    assert len(index["items"]) == accepted["evidence_items_verified"] == qa["total_evidence_items_verified"] == 36
    fixed_paths = []
    for n, item in enumerate(index["items"]):
        p = owned_path(item["path"])
        data = capture(p, "indexed/%02d-%s" % (n, p.name), item["sha256"])
        if item.get("git_blob"):
            rel = p.as_posix().split("/fixed-parent/", 1)[1]
            assert data == blob(rel)
            assert git("rev-parse", parent + ":" + rel).decode().strip() == item["git_blob"]
            fixed_paths.append(rel)
    assert len(fixed_paths) == len(set(fixed_paths)) == accepted["fixed_parent_file_copies_verified"] == 22
    for rel, expected in review["additional_inspected_fixed_parent_fingerprints"].items():
        assert sha(blob(rel)) == expected
        dest = out / "snapshots/fixed-extra" / Path(rel).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            assert dest.read_bytes() == blob(rel)
        else:
            dest.write_bytes(blob(rel))
        manifest["fixed-extra/" + Path(rel).name] = {
            "source_git": parent + ":" + rel, "snapshot": "snapshots/fixed-extra/" + Path(rel).name,
            "bytes": len(blob(rel)), "sha256": expected}

    old_wip = {}
    for rel, expected in review["five_WIP_working_sha256"].items():
        data = capture(m / "evidence/endpoint-channel-wip-r1-preserved" / rel,
                       "r1-wip/" + Path(rel).name, expected)
        copy = ind / (pre + "-checkpoint-evidence/WIP") / rel
        assert copy.read_bytes() == data
        old_wip[rel] = data
    assert len(old_wip) == accepted["WIP_unchanged"] == 5
    for anchor in review["exact_source_anchors"]:
        rel = anchor["path"]
        data = old_wip[rel] if rel in old_wip else blob(rel)
        assert anchor["contains"] in data.decode("utf-8-sig").splitlines()[anchor["line"] - 1], anchor
    assert len(review["exact_source_anchors"]) == qa["source_anchor_count_verified"] == accepted["exact_source_anchors_verified"] == 55
    release = read(ind / (pre + "-final-guards-released.json"))
    assert release["verified_working_sha256"] == review["five_WIP_working_sha256"]
    assert release["no_broader_guard_held"] and not release["new_execution_authority"]
    for suffix in ["-checkpoint.json", "-checkpoint-qa.json", "-checkpoint-handoff.md", "-guards-released.json"]:
        p = ind / (pre + suffix)
        capture(p, "original/" + p.name)
    assert sha((ind / (pre + "-checkpoint-qa.json")).read_bytes()) == qa["old_checkpoint_qa_sha256_observed"]

    plan_path = m / "endpoint-channel-local-review-r2.json"
    plan = read(plan_path)
    audit_path = m / "evidence/endpoint-channel-wip-source-audit-r2.json"
    source_audit = read(audit_path)
    assert sha(plan_path.read_bytes()) == "6562ce1cb84f6b1b942b0d2e61982d86203371fc7f977e85e459bbb767b975e0"
    assert plan["parent_head"] == source_audit["parent_head"] == parent
    assert plan["files_working_sha256"] == source_audit["files_working_sha256"]
    new_wip = {}
    for rel, expected in plan["files_working_sha256"].items():
        data = capture(impl / rel, "r2-wip/" + Path(rel).name, expected)
        assert (m / "evidence/endpoint-channel-wip-r2-preserved" / rel).read_bytes() == data
        new_wip[rel] = data
    assert len(new_wip) == 5 and set(new_wip) == set(old_wip)
    assert source_audit["local_CPP_build_run_remote_network_calls"] == 0
    assert not source_audit["default_network_or_cost_acceptance"]
    node_qa = read(m / "evidence/endpoint-channel-node18-main-QA-r1.json")
    for item in node_qa["files"]:
        p = owned_path(item["path"])
        data = capture(p, "main/" + p.relative_to(m).as_posix(), item["sha256"])
        assert len(data) == item["bytes"]
    capture(m / "evidence/endpoint-channel-node18-main-QA-r1.json", "main/evidence/endpoint-channel-node18-main-QA-r1.json")
    for name in ["endpoint-channel-repair-design-r1.md", "endpoint-channel-integration-design-r1.md", "endpoint-channel-contract-r1.md"]:
        capture(m / name, "main/" + name)

    def restore(files, revised):
        p = "src/point-to-point/model/qbb-channel.cc"
        w = files[p].replace(b"\r\n", b"\n")
        w = w.replace(b"#include <limits>\n#include <stdexcept>\n", b"", 1)
        a, b = w.index(b"  if (!m_ws31Enter)\n"), w.index(b"\n  // Call the tx anim callback")
        original = w[a:b].split(b"    {\n", 1)[1].split(b"\n    }\n  else", 1)[0]
        if revised:
            original = original.replace(b"      m_ws31EverTransmitted = true;\n", b"", 1)
        original = original.replace(b"      Simulator::ScheduleWithContext", b"  Simulator::ScheduleWithContext", 1)
        w = w[:a] + original + b"\n" + w[b:]
        a, b = w.index(b"void\nQbbChannel::DeliverWs31"), w.index(b"uint32_t \nQbbChannel::GetNDevices")
        w = w[:a] + w[b:]
        assert w == blob(p), p
        p = "src/point-to-point/model/qbb-channel.h"
        w = files[p].replace(b"\r\n", b"\n").replace(b"#include <functional>\n", b"", 1)
        if revised:
            w = w.replace(b"#include <exception>\n", b"", 1)
        w = w.replace(b"class Ws31EndpointChannel;\n", b"", 1)
        a, b = w.index(b"  // Empty for ordinary simulations."), w.index(b"  // Each point to point link")
        assert w[:a] + w[b:] == blob(p), p
        p = "src/network/model/flow-id-num-tag.h"
        w = files[p].replace(b"\r\n", b"\n")
        w = w.replace(b"#ifndef NS3_FLOW_ID_NUM_TAG_H\n#define NS3_FLOW_ID_NUM_TAG_H\n\n", b"", 1)
        w = w.replace(b"#endif // NS3_FLOW_ID_NUM_TAG_H\n\n", b"", 1)
        assert w == blob(p), p

    restore(old_wip, False)
    restore(new_wip, True)
    # These are presence/order checks of written repairs, not semantic or runtime approval.
    h = new_wip["src/point-to-point/model/ws31-endpoint-channel.h"].decode()
    cc = new_wip["src/point-to-point/model/qbb-channel.cc"].decode()
    fixture = new_wip["scratch/ws31-endpoint-channel-test.cc"].decode()
    needles = ["typeid(*PeekPointer(channel))==typeid(QbbChannel)", "id>=0 && id<=65535",
               "tag.SetId(id); tag.SetFlowSize(flowBytes);", "std::current_exception()",
               "!channel->m_ws31EverTransmitted", "channel->m_ws31Enter.swap(enter)", "void RethrowFailure() const"]
    assert all(x in h for x in needles)
    bind = h[h.index("    void Bind("):h.index("    uint64_t Pending()")]
    assert bind.index("channels.push_back(channel)") < bind.index("m_ws31Enter.swap") < bind.index("m_ws31Owner=state.get()")
    delivery = cc[cc.index("QbbChannel::DeliverWs31 ("):cc.index("QbbChannel::GetNDevices")]
    assert "Simulator::Stop ();" in delivery and "throw;" not in delivery
    assert delivery.index("destination->Receive (packet)") < delivery.index("leave (serial)") < delivery.index("--channel->m_ws31Pending")
    assert all(x in fixture for x in ["UnregisteredOverride", "negative-id-before-encoding", "high-id-before-encoding",
        "bind-after-default-scheduled", "owner-lost-inflight", "animation-after-schedule", "partial-enter-finish"])
    assert new_wip["src/network/model/flow-id-num-tag.h"] == old_wip["src/network/model/flow-id-num-tag.h"]
    assert (impl / "src/network/model/flow-id-num-tag.cc").read_bytes().replace(b"\r\n", b"\n") == blob("src/network/model/flow-id-num-tag.cc")

    refs = read(m / "evidence/endpoint-channel-node18-reference-review-r1.json")
    for n, item in enumerate(refs["sources"]):
        p = owned_path(item["path"])
        capture(p, "literature/%02d-%s" % (n, p.name), item["sha256"])
    assert len(refs["sources"]) == 6 and "unresolved" in refs["baseline_admission"]
    status = git("status", "--porcelain", "-uall").decode().splitlines()
    assert status == review["git_status"]
    assert git("rev-parse", "HEAD").decode().strip() == parent
    assert git("rev-parse", "refs/remotes/origin/feature/ws31-candidates").decode().strip() == parent
    assert git("branch", "--show-current").decode().strip() == "feature/ws31-candidates"
    assert git("remote", "get-url", "--push", "origin").decode().strip() == "https://github.com/LarryBUPT/conweave-ns3.git"
    changed = [p for p in new_wip if new_wip[p] != old_wip[p]]
    receipt = {
        "at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_PROVENANCE_R1_REVIEW_ACCEPTED_R2_WRITTEN_NOT_RUNTIME_APPROVED",
        "parent_head": parent, "r1_review_sha256": sha(review_path.read_bytes()),
        "r1_QA_sha256": sha(qa_path.read_bytes()), "indexed_evidence": 36,
        "fixed_parent_copies": 22, "additional_fixed_parent_fingerprints": 1,
        "source_anchors": 55, "r1_frozen_WIP": 5, "r2_current_and_frozen_WIP": 5,
        "r1_to_r2_changed_files": changed, "tag_class_and_serialization_body_unchanged": True,
        "deletion_restoration_checks": {"r1": 3, "r2": 3},
        "finding_counts": review["finding_counts"],
        "findings": [{"id": x["id"], "severity": x["severity"], "title": x["title"]} for x in review["findings"]],
        "r1_review_guard_released": release["at_utc"],
        "r2_plan_sha256": sha(plan_path.read_bytes()), "r2_working_hashes": plan["files_working_sha256"],
        "r2_guard": "Five frozen files under sole independent read-only review; no execution authority",
        "repair_check_scope": "Written source anchors and mutation order only; not a complete new semantic review or compilation",
        "G1_and_all_production_identity_producers_integrated": False,
        "already_truncated_external_identity_aliases_detectable": False,
        "fault_injections": "Controlled transaction-boundary throws; actual animation trace; all unexecuted",
        "runtime_or_default_compatibility_or_cost_accepted": False,
        "literature_records_verified": 6, "new_baseline_admission": False,
        "Flowcut_current_title_CCF_qualification": "UNRESOLVED_REFERENCE_ONLY",
        "implementation_git_status": status, "new_frozen_commit": False,
        "network_total_unchanged": 43, "nonnetwork_adapter_conditions_unchanged": 17,
        "integration_execution_counts": {"remote": 0, "compile": 0, "cpp_test": 0, "network": 0, "old_raw_recomputation": 0},
        "remaining_mandatory": review["remaining_mandatory"],
        "main_observed_cursor": "30516c1d-6c65-4481-bd73-77602ce15c3a:1",
        "independent_main_reported_cursor": "e48b2fab-5538-4004-8e5d-575b33e8e994:4",
        "independent_directly_polled_or_redispatched": False,
    }
    for name, obj in [("source-manifest.json", manifest), ("verification.json", receipt)]:
        p = out / name
        assert not p.exists(), "Refuse to overwrite a successful receipt: " + str(p)
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "snapshots": len(manifest), "evidence": 36,
                      "parent_copies": 22, "anchors": 55, "r2_WIP": 5}, ensure_ascii=False))


if __name__ == "__main__":
    main()
