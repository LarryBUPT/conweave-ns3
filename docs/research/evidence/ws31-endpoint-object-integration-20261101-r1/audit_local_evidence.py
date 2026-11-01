"""Integrate probe static review and fixed object-fixture plan, read-only locally."""
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
    ws = root / "docs/research/ws31"
    main, ind = ws / "main", ws / "independent"
    impl = root.parent / "ws31-candidates-implementation"
    git = lambda *args: subprocess.check_output(["git", "-C", str(impl), *args])
    parent = "20bc2d9f7c7c435bf832ba2fcaf0e07df00cf5da"
    source = "8cd1ba69469bf80143d5c89edc17fa72611018e8"
    pre = "endpoint-probe-local-review-r1"
    reviewpath, reportpath, qapath = [ind / (pre + s) for s in ["-review.json", "-report.md", "-qa.json"]]
    review, qa = read(reviewpath), read(qapath)
    acceptedpath = main / "evidence/endpoint-probe-local-review-main-acceptance-r1.json"
    accepted = read(acceptedpath)
    planpath = main / (pre + ".json")
    assert sha(planpath.read_bytes()) == accepted["plan_sha256"] == review["plan"]["sha256"] == "fd8e63b3692967d6f938d409945ee9dad12b5401772c2a07e9b56062c51482ee"
    assert sha(reviewpath.read_bytes()) == accepted["review_sha256"] == "e401fcc8f2c4b2954224d228d4891b07280d4341f03b09ae9e987753d6cb5ff9"
    assert sha(reportpath.read_bytes()) == review["report_sha256"] == accepted["report_sha256"]
    assert sha(qapath.read_bytes()) == accepted["QA_sha256"]
    assert accepted["status"] == "MAIN_ACCEPTED_PROBE_STATIC_REVIEW_REPAIRS_REQUIRED"
    assert review["status"] == "LOCAL_STATIC_REVIEW_COMPLETE_REQUIRED_COVERAGE_REPAIRS"
    assert qa["status"] == "PASS_STATIC_REVIEW_DELIVERY_INTEGRITY_ONLY"
    assert review["before"] == review["after"] == qa["before"] == qa["after"]
    assert review["before"]["head"] == parent
    assert all(v == 0 for v in review["execution_counts"].values()) and qa["execution_counts"] == review["execution_counts"]
    assert [x["id"] for x in review["findings"]] == ["P1", "P2", "P3"]
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
        manifest[name] = {"source_path": str(path.resolve()), "bytes": len(data), "sha256": sha(data),
                          "snapshot": "snapshots/" + name}

    for p in [reviewpath, reportpath, qapath]:
        capture(p, "independent/" + p.name)
    for path, h in review["prior_artifacts_sha256"].items():
        capture(Path(path), "prior/" + Path(path).name, h)
    assert len(review["prior_artifacts_sha256"]) == accepted["prior_artifacts_verified"] == 8
    prior = read(root / "docs/research/evidence/ws31-endpoint-preflight-integration-20261101-r1/verification.json")
    for rel, h in accepted["original_wip_preserved"].items():
        assert h == review["before"]["wip_sha256"][rel] == prior["probe_WIP_hashes"][rel]
        capture(main / "evidence/endpoint-probe-wip-r1-preserved" / Path(rel).name, "original-wip/" + Path(rel).name, h)
    paths = []
    for item in review["source_provenance"]:
        p = Path(item["path"])
        rel = p.relative_to(impl).as_posix()
        data = git("show", parent + ":" + rel)
        assert sha(data) == item["head_blob_sha256"]
        assert git("rev-parse", parent + ":" + rel).decode().strip() == item["git_blob"]
        if rel == "src/point-to-point/model/qbb-net-device.h":
            old = (main / "evidence/endpoint-probe-wip-r1-preserved/qbb-net-device.h").read_bytes()
            assert sha(old) == item["working_sha256"]
            removed = old.decode().replace("\r\n", "\n").replace("  // Read-only WS-31 endpoint evidence adapter; never called by normal routing.\n  friend class Ws31EndpointProbe;\n", "")
            assert removed.replace("\r\n", "\n") == data.decode().replace("\r\n", "\n")
        else:
            assert git("show", source + ":" + rel) == data
            assert sha(p.read_bytes()) == item["working_sha256"]
            assert p.read_bytes().replace(b"\r\n", b"\n") == data.replace(b"\r\n", b"\n")
        paths.append({"path": rel, "fixed_parent_sha256": sha(data), "historical_working_sha256": item["working_sha256"]})
    assert len(paths) == qa["source_provenance_count"] == accepted["fixed_source_paths_verified"] == 25
    for rel, h in review["before"]["accepted_core_sha256"].items():
        assert sha(git("show", source + ":" + rel)) == sha(git("show", parent + ":" + rel)) == h
    nextpath = main / "endpoint-probe-object-preflight-r1.json"
    nxt = read(nextpath)
    sourceaudit = read(main / "evidence/endpoint-probe-object-source-audit-r1.json")
    assert sha(nextpath.read_bytes()) == "d91892f73bc6a6b45c0541f2c588ba59ba3fd3694ec75a75e35be5265dd5b255"
    assert nxt["source_sha"] == sourceaudit["source_sha"] == source
    assert nxt["parent_sha"] == sourceaudit["parent_sha"] == parent == git("rev-parse", source + "^").decode().strip()
    assert nxt["source_changes_sha256"] == sourceaudit["source_changes_sha256"]
    changes = git("diff", "--name-status", parent, source).decode().splitlines()
    assert {tuple(x.split("\t")) for x in changes} == {("A", "scratch/ws31-endpoint-object-test.cc"), ("A", "src/point-to-point/model/ws31-endpoint-probe.h"), ("M", "src/point-to-point/model/qbb-net-device.h")}
    for rel, h in nxt["source_changes_sha256"].items():
        data = git("show", source + ":" + rel)
        assert sha(data) == h
        p = out / "snapshots/new-source" / Path(rel).name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        manifest["new-source/" + rel] = {"source_git": source + ":" + rel, "bytes": len(data), "sha256": h,
                                       "snapshot": "snapshots/new-source/" + Path(rel).name}
    tree = git("ls-tree", "-r", source)
    assert len(tree.splitlines()) == nxt["source_tree_entries"] == sourceaudit["source_tree_entries"] == 4847
    assert sha(tree) == nxt["tree_sha256"] == sourceaudit["tree_sha256"]
    (out / "source-tree.txt").write_bytes(tree)
    assert git("rev-parse", "HEAD").decode().strip() == source
    assert git("rev-parse", "refs/remotes/origin/feature/ws31-candidates").decode().strip() == source
    assert not git("status", "--porcelain", "-uall").strip()
    assert git("remote", "get-url", "--push", "origin").decode().strip() == "https://github.com/LarryBUPT/conweave-ns3.git"
    header = git("show", source + ":src/point-to-point/model/qbb-net-device.h").decode()
    parentheader = git("show", parent + ":src/point-to-point/model/qbb-net-device.h").decode()
    add = "  // Read-only WS-31 endpoint evidence adapter; never called by normal routing.\n  friend class Ws31EndpointProbe;\n  friend class Ws31EndpointSnapshotFixture;\n"
    assert header.count(add) == 1 and header.replace(add, "") == parentheader
    probe = git("show", source + ":src/point-to-point/model/ws31-endpoint-probe.h").decode()
    fixture = git("show", source + ":scratch/ws31-endpoint-object-test.cc").decode()
    code = re.sub(r"//[^\n]*", "", probe)
    reading = code[code.index("static Observation Read("):]
    assert "GetObject<" not in reading and "->GetBytesLeft(" not in reading and "->GetNextQindex(" not in reading
    assert "s.retainedQpsFinished=savedTx->IsFinishedConst();" in reading
    assert "s.pendingPayloadBytes=Pending(savedTx);" in reading and "Need(savedTxOccurrences==1," in reading
    assert reading.index("Need(liveTx->second!=nullptr") < reading.index("result.liveTxFlowId=liveTx->second->m_flow_id")
    assert reading.index("Need(liveRx->second!=nullptr") < reading.index("result.liveRxFlowId=liveRx->second->m_flow_id")
    assert "ValidateScope(scope);" in reading and "Duplicate QP in retained groups or slots" in reading
    mask = reading.split("s.observedFields=", 1)[1].split(";", 1)[0]
    assert "SWITCH_STATE" not in mask and "::ALL" not in mask
    assert "static Scope Capture(" in code and "GetObject<RdmaDriver>" in code
    assert "Simulator::Run(" not in re.sub(r"//[^\n]*", "", fixture)
    assert "Require(before==middle && middle==after," in fixture and "Require(before==state()," in fixture
    assert "full_protocol_bytes_equal=1" in fixture and "irn.m_sack" in fixture
    normal = re.findall(r'pair\("([^\"]+)"\)', fixture)
    denials = re.findall(r'deny\("([^\"]+)"\)', fixture)
    assert normal == nxt["fixture"]["normal_cases"] == sourceaudit["normal_cases"]
    assert denials == nxt["fixture"]["read_refusal_cases"] == sourceaudit["read_refusal_cases"]
    assert len(normal) == 8 and len(denials) == 14 and len(nxt["fixture"]["other_refusals"]) == 2
    assert nxt["fixture"]["expected_read_calls"] == 31 and nxt["fixture"]["expected_refusals"] == 16 and nxt["fixture"]["expected_mask"] == 127
    assert nxt["authorized_sync_commands"] == nxt["full_optimized_builds"] == nxt["new_fixture_commands"] == 1
    assert nxt["authorized_deploy_commands"] == nxt["standalone_old_or_new_core_compiles"] == 0
    assert nxt["resource_gate"]["jobs_per_build"] == 2 and nxt["resource_gate"]["network_simulation_concurrency"] == 0
    assert nxt["pre_dispatch_idle_cursor"].endswith(":102")
    mainfiles = ["endpoint-probe-node16-handoff.md", pre + ".json", "endpoint-probe-object-contract-r1.md",
                 "endpoint-probe-object-preflight-r1.json", "current-status.json",
                 "evidence/endpoint-probe-local-review-main-acceptance-r1.json", "evidence/endpoint-probe-object-source-audit-r1.json"]
    for rel in mainfiles:
        capture(main / rel, "main/" + rel)
    state = read(main / "current-status.json")
    assert state["planned_next_goal"]["plan_sha256"] == sha(nextpath.read_bytes()) and state["independent_cursor"].endswith(":103")
    refs = root.parent.parent / "参考文献/候选"
    for rel in ["README.md", "reading-log.md", "papers/diffflow-2016/analysis-technical.md", "papers/diffflow-2016/verification.md"]:
        capture(refs / rel, "literature/" + Path(rel).name)
    (out / "source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {"at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS_PROBE_STATIC_REVIEW_PRESERVATION_FIXED_SOURCE_AND_GATED_OBJECT_PLAN",
              "review_sha256": sha(reviewpath.read_bytes()), "report_sha256": sha(reportpath.read_bytes()), "QA_sha256": sha(qapath.read_bytes()),
              "main_acceptance_sha256": sha(acceptedpath.read_bytes()), "fixed_parent_source_paths_verified": paths,
              "prior_artifacts_verified": 8, "old_WIP_files_preserved_and_match_node15": 2, "accepted_core_inputs_unchanged": True,
              "findings": [x["id"] for x in review["findings"]], "static_savedTX_coverage_counterexample_not_execution": True,
              "new_source_sha": source, "parent_sha": parent, "source_changes": nxt["source_changes_sha256"], "source_tree_path_entries": 4847,
              "source_tree_sha256": sha(tree), "clean_exclusive_checkout_personal_origin_tracking": True,
              "tracked_header_changes": "Comment and two friend declarations only; no data members/virtual methods/production cc changes",
              "new_guard_and_test_scope": "Static anchor checks only; full source review remains independent, compile/purity outcome pending",
              "object_fixture_planned_normal_pairs": 8, "object_fixture_planned_Read_refusals": 14, "object_fixture_planned_other_refusals": 2,
              "object_fixture_planned_Read_calls_including_failures": 31, "planned_mask": 127,
              "natural_transmission_or_ALL_certificate_or_network_completion_proven": False,
              "next_plan_sha256": sha(nextpath.read_bytes()), "next_id": nxt["id"], "next_sync_fullbuild_fixture_maxima": [1, 1, 1],
              "next_jobs_per_build": 2, "next_deploy_network_or_old_tests_authorized": False,
              "next_source_entry_environment_guard": "Held until fixed-source/calls terminal and explicit release",
              "next_execution_outcomes_accepted": False, "network_technical_total": 43, "nonnetwork_adapter_conditions": 17,
              "new_combined_baseline": False, "Integration_remote_build_fixture_or_model_execution": 0,
              "manifest_entries": len(manifest), "remaining": nxt["remaining_after"]}
    (out / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    out = Path(__file__).resolve().parent
    if (out / "verification.json").exists() or (out / "source-manifest.json").exists():
        raise RuntimeError("Refusing to overwrite Integration evidence")
    result = audit(Path.cwd(), out)
    print(json.dumps({k: result[k] for k in ["status", "prior_artifacts_verified", "new_source_sha", "source_tree_path_entries", "next_execution_outcomes_accepted", "network_technical_total"]}))
