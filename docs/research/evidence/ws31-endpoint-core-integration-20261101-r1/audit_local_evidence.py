"""Local source/static-review integration; no compilation or remote work."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def audit(root, out):
    ind = root / "docs/research/ws31/independent"
    main = ind.parent / "main"
    impl = root.parent / "ws31-candidates-implementation"
    git = lambda *args: subprocess.check_output(["git", "-C", str(impl), *args])
    parent = "1f917f44fcfb88e61f3ad22c5cc75fa3a06b6c0e"
    source = "20bc2d9f7c7c435bf832ba2fcaf0e07df00cf5da"
    pre = "endpoint-ledger-local-review-r1"
    reviewpath, qapath, reportpath = [ind / (pre + suffix) for suffix in ["-review.json", "-qa.json", "-report.md"]]
    review, qa = read(reviewpath), read(qapath)
    acceptedpath = main / "evidence/endpoint-ledger-local-review-main-acceptance-r1.json"
    accepted = read(acceptedpath)
    planpath = main / (pre + ".json")
    assert sha(reviewpath.read_bytes()) == accepted["review_sha256"] == "aa54af2b05c870e356e32e53d855c0a4175d4e00b38a314d39cad35a84cad12c"
    assert sha(reportpath.read_bytes()) == accepted["report_sha256"] == review["report_sha256"]
    assert sha(qapath.read_bytes()) == accepted["QA_sha256"]
    assert sha(planpath.read_bytes()) == accepted["plan_sha256"] == qa["plan_sha256"] == review["plan"]["sha256"]
    assert accepted["status"] == "MAIN_ACCEPTED_STATIC_REVIEW_WITH_REQUIRED_REPAIRS"
    assert qa["status"] == "PASS_DELIVERY_INTEGRITY_ONLY_NO_CODE_TEST_EXECUTED"
    assert review["status"] == "LOCAL_STATIC_REVIEW_COMPLETE_REAL_ENDPOINT_ACCEPTANCE_NOT_READY"
    assert review["before"] == review["after"] == qa["before"] == qa["after"]
    assert review["before"]["head"] == parent
    assert all(x == 0 for x in review["executions"].values()) and qa["execution_counts"] == review["executions"]
    assert [x["id"] for x in review["findings"]] == ["R1", "R2", "R3", "R4"]
    manifest = {}

    def capture(path, name, expected=None):
        data = path.read_bytes()
        if expected is not None:
            assert sha(data) == expected, str(path)
        dest = out / "snapshots" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            assert dest.read_bytes() == data
        else:
            dest.write_bytes(data)
        manifest[name] = {"source_path": str(path.resolve()), "bytes": len(data),
                          "sha256": sha(data), "snapshot": "snapshots/" + name}

    for p in [reviewpath, qapath, reportpath]:
        capture(p, "independent/" + p.name)
    main_files = ["endpoint-ledger-node14-handoff.md", "endpoint-ledger-local-review-r1.json",
                  "endpoint-lifecycle-design-r2.md", "endpoint-ledger-core-preflight-r2.json",
                  "endpoint-snapshot-interface-audit-r1.md", "current-status.json",
                  "evidence/endpoint-ledger-local-review-main-acceptance-r1.json",
                  "evidence/endpoint-ledger-core-source-audit-r2.json",
                  "evidence/endpoint-ledger-wip-source-audit-r1.json",
                  "evidence/endpoint-snapshot-interface-audit-r1.json"]
    for rel in main_files:
        capture(main / rel, "main/" + rel)
    prior = read(root / "docs/research/evidence/ws31-adapter-default-integration-20261101-r1/verification.json")
    for rel, h in accepted["wip_preserved"].items():
        assert h == review["before"]["wip_sha256"][rel] == prior["worktree_untracked_WIP_observed"][rel]
        capture(main / "evidence/endpoint-ledger-wip-r1-preserved" / Path(rel).name,
                "original-wip/" + Path(rel).name, h)
    checked = []
    for entry in review["provenance"]:
        p = Path(entry["path"])
        rel = p.relative_to(impl).as_posix()
        data = git("show", parent + ":" + rel)
        assert sha(data) == entry["head_blob_sha256"]
        assert git("rev-parse", parent + ":" + rel).decode().strip() == entry["git_blob"]
        assert git("show", source + ":" + rel) == data
        working = p.read_bytes()
        assert sha(working) == entry["working_sha256"]
        assert working.replace(b"\r\n", b"\n") == data.replace(b"\r\n", b"\n")
        checked.append({"path": rel, "fixed_git_sha256": sha(data), "working_sha256": sha(working)})
    assert len(checked) == accepted["git_source_objects_checked"] == 11
    auditpath = main / "evidence/endpoint-ledger-core-source-audit-r2.json"
    src_audit = read(auditpath)
    nextpath = main / "endpoint-ledger-core-preflight-r2.json"
    nxt = read(nextpath)
    assert sha(nextpath.read_bytes()) == "57ee56f60e6406dfaeab8e317910423e53fdb87e46982be6bf730dd4823fae47"
    assert src_audit["source_sha"] == nxt["source_sha"] == source
    assert src_audit["parent_sha"] == nxt["parent_sha"] == parent == git("rev-parse", source + "^").decode().strip()
    assert nxt["source_changes_sha256"] == src_audit["source_changes_sha256"]
    diff = git("diff", "--name-status", parent, source).decode().splitlines()
    assert {line.split("\t")[0] for line in diff} == {"A"}
    assert {line.split("\t")[1] for line in diff} == set(nxt["source_changes_sha256"])
    for rel, h in nxt["source_changes_sha256"].items():
        data = git("show", source + ":" + rel)
        assert sha(data) == h
        p = out / "snapshots/new-source" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        manifest["new-source/" + rel] = {"source_git": source + ":" + rel, "bytes": len(data), "sha256": h,
                                       "snapshot": "snapshots/new-source/" + rel}
    tree = git("ls-tree", "-r", source)
    assert len(tree.splitlines()) == 4845 and sha(tree) == nxt["tree_sha256"] == src_audit["tree_sha256"]
    (out / "source-tree.txt").write_bytes(tree)
    assert git("rev-parse", "HEAD").decode().strip() == source
    assert git("rev-parse", "refs/remotes/origin/feature/ws31-candidates").decode().strip() == source
    assert git("branch", "--show-current").decode().strip() == "feature/ws31-candidates"
    assert not git("status", "--porcelain", "-uall").strip()
    assert git("remote", "get-url", "--push", "origin").decode().strip() == "https://github.com/LarryBUPT/conweave-ns3.git"
    include_matches = git("grep", "-l", "ws31-endpoint-ledger.h", source, "--").decode().splitlines()
    assert include_matches == [source + ":tests/ws31_endpoint_ledger_test.cc"]
    assert src_audit["Waf_registration_or_includes"] == src_audit["ns3_runtime_source_changes"] == 0
    # Independent static anchors for the concrete findings; never execute C++.
    qp = git("show", parent + ":src/point-to-point/model/rdma-queue-pair.cc").decode()
    dev = git("show", parent + ":src/point-to-point/model/qbb-net-device.cc").decode()
    hw = git("show", parent + ":src/point-to-point/model/rdma-hw.cc").decode()
    assert "void RdmaQueuePairGroup::Clear(void) { m_qps.clear(); }" in qp
    assert "RdmaQueuePairGroup::RdmaQueuePairGroup(void) { memset(m_qp_finished, 0, sizeof(m_qp_finished)); }" in qp
    assert "void RdmaQueuePairGroup::AddQp(Ptr<RdmaQueuePair> qp) { m_qps.push_back(qp); }" in qp
    scheduler = dev[dev.index("int RdmaEgressQueue::GetNextQindex("):dev.index("uint32_t RdmaEgressQueue::GetNBytes(")]
    assert scheduler.index("if (m_qpGrp->IsQpFinished(") < scheduler.index("Ptr<RdmaQueuePair> qp =")
    assert "if (p->PeekPacketTag(fit)) {\n                newp->AddPacketTag(fit);" in hw
    complete = hw[hw.index("void RdmaHw::QpComplete("):hw.index("void RdmaHw::SetLinkDown(")]
    assert complete.index("m_qpCompleteCallback(qp);") < complete.index("DeleteQueuePair(qp);")
    tx = lambda dip, sport, dport, pg: (dip << 32) | (sport << 16) | dport | pg
    rx = lambda sip, sport, dport, pg: (sip << 32) | (dport << 16) | (pg << 16) | sport
    assert tx(2, 1000, 100, 3) == tx(2, 1000, 103, 3)
    assert rx(1, 1000, 100, 3) == rx(1, 1000, 103, 3)
    core = git("show", source + ":src/point-to-point/model/ws31-endpoint-ledger.h").decode()
    test = git("show", source + ":tests/ws31_endpoint_ledger_test.cc").decode()
    anchors = ["EndpointRouteKey", "txOwners, rxOwners", "actual.observedFields==EndpointSnapshot::ALL",
               "actual.generation==e.generation", "actual.observedNs==now", "prior->Reusable()",
               "t.kind==expectedKind", "reason==RECEIVE_RETURNED", "reason==HELD_DISCARDED",
               "completionHistoryReleased", "Valid false observations also advance the evidence clock"]
    assert all(x in core for x in anchors)
    assert "assert(" not in test and "throw std::runtime_error" in test
    assert all(x in test for x in ["ledger.Launch(1,105)", "ledger.AckComplete(1,8192,110)", "ledger.Retire(1,", "ledger.CertifyDrain(1,", "ledger.SwitchCleared(1,"])
    assert nxt["pre_dispatch_idle_cursor"].endswith(":95")
    assert nxt["authorized_sync_commands"] == nxt["new_core_compile_commands"] == nxt["new_core_run_commands"] == 1
    assert nxt["full_ns3_builds"] == nxt["authorized_deploy_commands"] == nxt["network_runs"] == 0
    assert nxt["compile"]["standard_assert_disabled"] and "-DNDEBUG" in nxt["compile"]["argv"]
    assert nxt["compile"]["test_checks_use_exceptions"] and nxt["compile"]["binary_outside_source"]
    state = read(main / "current-status.json")
    assert state["planned_next_goal"]["plan_sha256"] == sha(nextpath.read_bytes())
    assert state["planned_next_goal"]["status"] == "DISPATCHED_SOLE_STATIC_REVIEW_THEN_GATED_STANDALONE_CORE"
    assert state["independent_cursor"].endswith(":96")
    refs = root.parent.parent / "参考文献/候选"
    for rel in ["README.md", "reading-log.md", "papers/diffflow-2016/analysis-technical.md", "papers/diffflow-2016/verification.md"]:
        capture(refs / rel, "literature/" + rel)
    (out / "source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {"at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS_STATIC_REVIEW_PROVENANCE_PRESERVED_WIP_FIXED_CORE_AND_PREFLIGHT_SCOPE",
              "review_sha256": sha(reviewpath.read_bytes()), "report_sha256": sha(reportpath.read_bytes()), "QA_sha256": sha(qapath.read_bytes()),
              "main_acceptance_sha256": sha(acceptedpath.read_bytes()), "reviewed_source_objects": checked,
              "original_WIP_matches_node13_and_before_after_review": True, "preserved_WIP_files": 2,
              "accepted_findings": [x["id"] for x in review["findings"]], "source_sha": source, "parent_sha": parent,
              "new_source_files": nxt["source_changes_sha256"], "fixed_tree_entries": 4845, "tree_sha256": sha(tree),
              "clean_checkout_and_personal_origin_tracking": True, "production_runtime_changes": 0, "Waf_or_production_inclusion": 0,
              "root_independent_static_findings": {"Clear_only_clears_vector": True, "finished_bitmap_initialized_in_constructor": True,
                  "scheduler_checks_old_finished_bit_before_new_QP": True, "packed_key_alias_vector_verified": True,
                  "ACK_NACK_identity_copy_conditional": True, "completion_callback_precedes_TX_map_delete": True},
              "repair_static_anchor_scope": "New core guard/test anchors inspected; no compiled or runtime behavior accepted",
              "retain_old_finished_QP_and_append_policy": "New contract only; production bitmap branch still needs real NS3 fixture",
              "next_preflight_plan_sha256": sha(nextpath.read_bytes()), "next_id": nxt["id"],
              "next_sync_compile_core_maxima": [1, 1, 1], "next_full_NS3_build_deploy_network": [0, 0, 0],
              "source_entry_guard": "Main holds clean exclusive source and compatible entry until explicit terminal release",
              "next_preflight_outcome_accepted": False, "last_network_accepted_source": parent,
              "network_technical_total": 43, "nonnetwork_adapter_conditions": 17, "new_combined_baseline": False,
              "Integration_compiles_tests_simulation_remote_actions": 0, "manifest_entries": len(manifest),
              "remaining": nxt["remaining_after"]}
    (out / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    out = Path(__file__).resolve().parent
    if (out / "verification.json").exists() or (out / "source-manifest.json").exists():
        raise RuntimeError("Refusing to overwrite Integration acceptance")
    result = audit(Path.cwd(), out)
    print(json.dumps({k: result[k] for k in ["status", "source_sha", "fixed_tree_entries", "production_runtime_changes", "next_preflight_outcome_accepted", "network_technical_total"]}))
