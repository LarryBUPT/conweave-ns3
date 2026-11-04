"""Integrate the human-authorized review-driven scope change without execution.

Verifies documents, preserved sources and automation bytes only. It does not
rerun old analyses, validate new engineering semantics, or implement proposals.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tomllib


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def audit():
    out = Path(__file__).resolve().parent
    root = out.parents[3]
    main = root / "docs/research/ws31/main"
    ind = root / "docs/research/ws31/independent"
    impl = root.parent / "ws31-candidates-implementation"
    fixed = "8cd1ba69469bf80143d5c89edc17fa72611018e8"
    git = lambda *args: subprocess.check_output(["git", "-C", str(impl), *args])
    manifest = {}

    def capture(path, name, expected=None):
        path = Path(path)
        assert path.resolve().is_relative_to(root.parent.parent.resolve())
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

    authority = read(out / "user-instruction.json")
    assert authority["source_turn"] == "01a1a5ef-431a-7e63-92f7-3173dde91e74"
    assert "暂缓对应工作或者优化对应工作" in authority["exact_user_text"]
    qa_path = main / "evidence/external-review-synthesis-main-qa-r1.json"
    qa = read(qa_path)
    transition_path = main / "evidence/external-review-scope-transition-r1.json"
    transition = read(transition_path)
    capture(qa_path, "main/evidence/" + qa_path.name)
    capture(transition_path, "main/evidence/" + transition_path.name)
    # Recover the exact prior JSON serialization from the embedded full state.
    # Its reported raw digest matches CRLF bytes, not the LF representation.
    prior_bytes = (json.dumps(transition["prior_status"], ensure_ascii=False, indent=2) + "\n").replace("\n", "\r\n").encode()
    assert sha(prior_bytes) == transition["prior_status_sha256"]
    prior = out / "snapshots/prior/current-status-before-scope.json"
    prior.parent.mkdir(parents=True, exist_ok=True)
    assert not prior.exists()
    prior.write_bytes(prior_bytes)
    manifest["prior/current-status-before-scope.json"] = {
        "source": "Reconstructed full embedded pre-transition JSON as CRLF; reported original SHA-256 independently matched",
        "snapshot": "snapshots/prior/current-status-before-scope.json", "bytes": len(prior_bytes), "sha256": sha(prior_bytes)}
    expected_reviews = {x["path"]: x["sha256"] for x in transition["review_sources"]}
    assert expected_reviews == {x["path"]: x["sha256"] for x in qa["reviews"]}
    for n, row in enumerate(transition["review_sources"]):
        data = capture(row["path"], "reviews/%d-c123-review.md" % (n + 1), row["sha256"])
        assert len(data) == row["bytes"] and len(data.decode("utf-8-sig").splitlines()) == row["lines"]
    for row in qa["outputs"]:
        p = Path(row["path"])
        rel = p.relative_to(main).as_posix() if p.is_relative_to(main) else "report/" + p.name
        capture(p, "main/" + rel, row["sha256"])
    for row in qa["sole_independent_artifacts"]:
        p = Path(row["path"])
        capture(p, "independent/" + p.name, row["sha256"])
    sources = read(ind / "external-c123-review-audit-r1-source-hashes.json")
    for label, row in sources["sources"].items():
        assert sha(Path(row["snapshot"]).read_bytes()) == row["sha256"] == expected_reviews[row["path"]]
        assert Path(row["snapshot"]).read_bytes() == Path(row["path"]).read_bytes()
    extraction = read(ind / "external-c123-review-audit-r1-extraction.json")
    assert extraction["source_manifest_sha256"] == sha((ind / "external-c123-review-audit-r1-source-hashes.json").read_bytes())
    names = {x["name"] for x in extraction["mechanism_inventory"]}
    assert names == set(qa["nine_mechanisms_covered"]) == {"CCB", "CGQ", "CCPB", "MACA", "CQT", "CLC", "CDLC", "BCS", "CCL"}

    identity_path = main / "evidence/endpoint-identity-wip-source-audit-r1.json"
    entry_path = main / "evidence/endpoint-entry-input-wip-source-audit-r1.json"
    completion_path = main / "evidence/endpoint-completion-wip-source-audit-r1.json"
    identity, entry, completion = read(identity_path), read(entry_path), read(completion_path)
    expected_wip = {**identity["all14_working_sha256"], **entry["new5_working_sha256"]}
    assert len(expected_wip) == 19
    assert expected_wip == {x["path"]: x["expected"] for x in qa["nineteen_existing_WIP_match_pre_review_audits"]}
    for rel, expected in expected_wip.items():
        data = capture(impl / rel, "WIP/" + rel, expected)
        preserved = Path(identity["preserved_WIP"]) / rel if rel in identity["all14_working_sha256"] else main / entry["preserved"] / rel
        assert preserved.read_bytes() == data
    assert expected_wip[completion["source"]] == completion["working_sha256"]
    assert sha(Path(completion["preserved"]).read_bytes()) == completion["working_sha256"]
    old = read(root / "docs/research/evidence/ws31-endpoint-switch-integration-20261104-r1/verification.json")
    assert all(expected_wip[rel] == h for rel, h in old["r3_working_hashes"].items())
    for p in [identity_path, entry_path, completion_path]:
        capture(p, "main/evidence/" + p.name)
    prior_main_acceptances = []
    for name in ["endpoint-switch-local-review-main-acceptance-r3.json", "endpoint-identity-local-review-main-acceptance-r1.json"]:
        p = main / "evidence" / name
        data = capture(p, "main/evidence/" + name)
        receipt = read(p)
        assert not receipt["new_execution_authority"] and not receipt["runtime_network_or_measured_mask255_accepted"]
        prior_main_acceptances.append({"path": str(p), "sha256": sha(data), "status": receipt["status"],
                                       "terminal_cursor": receipt["terminal_cursor"], "explicit_release": receipt["explicit_release"],
                                       "scope": "Main acceptance receipt identity only; full independent static review not repeated by Integration in this rescope"})
    assert qa["new_compile_test_network_SSH"] == transition["new_build_test_network"] == 0
    assert not qa["new_formal_baseline"] and not qa["canonical_registry_mutated_by_main"]
    assert transition["scientific_source_mutations"] == 0
    current = read(main / "current-status.json")
    assert current["status"] == "ACTIVE_REVIEW_INFORMED_RESCOPING_CANDIDATE_ENGINEERING_PAUSED"
    assert current["independent_cursor"] == qa["independent_cursor"] == "d0b9dd1a-3dbb-4cea-9a35-6aefe1b3ed0d:14"
    assert git("rev-parse", "HEAD").decode().strip() == qa["source_head"] == fixed
    assert git("rev-parse", "refs/remotes/origin/feature/ws31-candidates").decode().strip() == fixed
    assert git("branch", "--show-current").decode().strip() == "feature/ws31-candidates"
    gitstatus = git("status", "--porcelain", "-uall").decode().splitlines()
    assert {line[3:] for line in gitstatus} == set(expected_wip)
    before = tomllib.loads((out / "automation-before.toml").read_text(encoding="utf-8"))
    after = tomllib.loads((out / "automation-after.toml").read_text(encoding="utf-8"))
    live = Path("C:/Users/Administrator/.codex/automations/ws-31/automation.toml").read_bytes()
    assert live == (out / "automation-after.toml").read_bytes()
    for key in before:
        if key not in ["prompt", "updated_at"]:
            assert after[key] == before[key]
    assert after["status"] == "ACTIVE" and after["rrule"] == "FREQ=MINUTELY;INTERVAL=30"
    assert all(word in after["prompt"] for word in ["不 SSH", "不重复派发", "19 个现有 WIP", "暂缓", "不提供恢复授权"])
    result = {
        "at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS_USER_AUTHORITY_REVIEW_PROVENANCE_WIP_PRESERVATION_AND_RESCOPE",
        "direct_user_turn": authority["source_turn"], "direct_user_message": authority["source_message"],
        "three_original_reviews_unchanged_and_independent_copies_match": True,
        "main_output_hashes_matched": 5, "independent_artifact_hashes_matched": 3,
        "nine_proposals_covered": sorted(names), "review_assessments_are_not_experiments_or_independent_replications": True,
        "full_pre_transition_status_CRLF_sha256_verified": transition["prior_status_sha256"],
        "preserved_WIP_paths": 19, "prior_root_accepted_ten_WIP_unchanged": True,
        "current_WIP_hashes": expected_wip, "implementation_HEAD": fixed, "implementation_git_status": gitstatus,
        "main_prior_acceptance_receipts": prior_main_acceptances,
        "engineering_build_test_network_and_effect_matrices": "PAUSED_BY_REVIEW_INFORMED_USER_SCOPE_CHANGE",
        "permitted_work": ["Bounded local read-only evidence/logic inventory", "Business-grounded category/size-decoupled demand design", "Evidence and design documents"],
        "unfinished_correctness_V0_ablations_dual_effects_costs": "RETAINED_NOT_COMPLETE_NOT_CANCELLED",
        "independent_main_reported_cursor": qa["independent_cursor"], "independent_main_reported_state": "completed/idle document review",
        "main_observed_cursor": "f13c4cd1-6458-4d58-888a-76f78e636578:2", "main_observed_state": "idle",
        "sole_independent_redispatched_or_directly_polled": False,
        "heartbeat": {"id": "ws-31", "status": "ACTIVE", "schedule_unchanged": after["rrule"],
                      "target_thread_unchanged": after["target_thread_id"], "prompt_sha256": sha(after["prompt"].encode()),
                      "tool_updated_then_saved_file_reloaded": True, "only_prompt_and_update_timestamp_changed": True},
        "new_Integration_scientific_source_build_test_network_SSH": 0, "new_formal_baseline": False,
        "Ofan": "PAUSED", "WS29": "DEFERRED_UNREAD_UNWOKEN_UNARCHIVED",
        "Integration_scope": "Authority and provenance verification plus state/scheduler alignment, not a fresh full literature or raw-result audit",
    }
    for name, value in [("source-manifest.json", manifest), ("verification.json", result)]:
        p = out / name
        assert not p.exists(), "Do not overwrite successful evidence"
        p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "reviews": 3, "WIP": 19, "proposals": 9, "heartbeat": "scope updated; schedule unchanged"}))


if __name__ == "__main__":
    audit()
