"""Integration audit of local adapter artifacts and explicit raw-log boundaries.

No remote commands, builds, fixtures or main-owned verifiers are executed.
The complete C1/C3 model replay remains attributed to the WS-31 main chat.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def records(text, prefix):
    return [dict(re.findall(r"(\w+)=([^ ]+)", line))
            for line in text.splitlines() if line.startswith(prefix)]


def values(row, **expected):
    for key, value in expected.items():
        assert row[key] == str(value), (key, row[key], value)


def audit(repo, out):
    ind = repo / "docs/research/ws31/independent"
    main = ind.parent / "main"
    pre = "adapter-boundary-preflight-r2"
    index_path = ind / (pre + "-index.json")
    idx = read(index_path)
    qa_path = ind / (pre + "-qa.json")
    qa = read(qa_path)
    accepted_path = main / "evidence/adapter-boundary-preflight-main-acceptance-r2.json"
    accepted = read(accepted_path)
    plan_path = main / (pre + ".json")
    plan = read(plan_path)
    source = "1f917f44fcfb88e61f3ad22c5cc75fa3a06b6c0e"
    assert digest(index_path.read_bytes()) == qa["index_sha256"] == accepted["index_sha256"] == "9b103d83c461e4c93138e1a0d7650b1d21150b85503949168ae81064a3bd4f8b"
    assert digest(qa_path.read_bytes()) == accepted["QA_sha256"] == "513898a3ae98b08013ddf385b81a9400586c9852cbb6f7fbc174a4607f68c8fa"
    assert digest(plan_path.read_bytes()) == idx["plan_sha256"] == accepted["plan_sha256"]
    assert idx["source_sha"] == accepted["source_sha"] == plan["source_sha"] == source
    assert qa["status"] == "PASS_17_ADAPTER_EXECUTOR_DELIVERY"
    assert accepted["status"] == "MAIN_ACCEPTED_ONE_FULL_BUILD_AND_17_ADAPTER_CASES_AND_DELIVERY"
    target = Path(idx["results_path"])
    folder = target.parent
    assert target.resolve() == (ind / (pre + "-evidence") / plan["id"] / "results").resolve()
    manifest = {}

    def capture(path, name, expected=None, freeze=True):
        data = path.read_bytes()
        h = digest(data)
        if expected is not None:
            assert h == (expected["sha256"] if isinstance(expected, dict) else expected), str(path)
            if isinstance(expected, dict):
                assert len(data) == expected["bytes"], str(path)
        entry = {"source_path": str(path.resolve()), "bytes": len(data), "sha256": h,
                 "snapshot": "snapshots/" + name if freeze else None}
        if freeze:
            dest = out / entry["snapshot"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                assert dest.read_bytes() == data, str(dest)
            else:
                dest.write_bytes(data)
        manifest[name] = entry
        return data

    counts = {}
    for group in ["documents", "dependencies", "original_r1_files"]:
        for rel, info in idx[group].items():
            capture(ind / rel, "independent/" + rel, info)
        counts[group] = len(idx[group])
    assert read(ind / (pre + "-original-r1-integrity-before.json")) == read(ind / (pre + "-original-r1-integrity-after.json")) == idx["original_r1_files"]
    for group, base in [("support_files", folder), ("result_files", target)]:
        for rel, info in idx[group].items():
            binary = group == "result_files" and rel.startswith("technical/adapter-boundary/artifacts/")
            capture(base / rel, ("results/" if base == target else "support/") + rel, info, not binary)
        counts[group] = len(idx[group])
    refs = read(ind / (pre + "-reference-review.json"))
    for n, (path, h) in enumerate(refs["sources"].items()):
        capture(Path(path), "references/" + str(n + 1) + "-" + Path(path).name, h)
    counts["reference_files"] = len(refs["sources"])
    assert counts == {"documents": 33, "dependencies": 4, "original_r1_files": 28,
                      "support_files": 15, "result_files": 47, "reference_files": 4}
    extra_main = [
        "adapter-boundary-node12-handoff.md", "adapter-boundary-preflight-r2.json", "adapter-boundary-preflight-r2.md",
        "adapter-default-validation-r1.json", "adapter-default-validation-r1.md",
        "endpoint-lifecycle-design-r1.md", "endpoint-lifecycle-source-audit-r1.md",
        "evidence/adapter-default-execution-authorization-r1.json",
        "evidence/adapter-default-verifier-preparation-r1.json",
        "evidence/endpoint-lifecycle-source-audit-r1.json", "evidence/endpoint-lifecycle-design-source-links-r1.json",
        "evidence/adapter-boundary-preflight-main-acceptance-r2.json",
        "evidence/adapter-boundary-preflight-stop-main-review-r1.json",
        "evidence/adapter-boundary-main-verifier-preparation-r1.json",
        "evidence/adapter-boundary-main-real-log-negative-checks-r1.json",
        "evidence/adapter-boundary-c1-main-acceptance-r1.json",
        "evidence/adapter-boundary-c2-main-acceptance-r1.json",
        "evidence/adapter-boundary-c3-main-acceptance-r1.json",
        "scripts/verify_adapter_boundary_raw_r1.py", "scripts/check_adapter_c2_verifier_r1.py",
        "scripts/verify_adapter_boundary_delivery_r2.py", "scripts/verify_adapter_default_raw_r1.py",
    ]
    prep = read(main / "evidence/adapter-boundary-main-verifier-preparation-r1.json")
    for rel, h in prep["sha256"].items():
        capture(main / rel, "main/" + rel, h)
    for rel in extra_main:
        capture(main / rel, "main/" + rel)
    capture(index_path, "independent/" + index_path.name)
    capture(qa_path, "independent/" + qa_path.name)
    impl = repo.parent / "ws31-candidates-implementation"
    git = lambda *args: subprocess.check_output(["git", "-C", str(impl), *args])
    for path, h in idx["source_hashes"].items():
        data = git("show", source + ":" + path)
        assert digest(data) == h, path
        dest = out / "snapshots/git-source" / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        manifest["git-source/" + path] = {"source_git": source + ":" + path, "bytes": len(data),
                                              "sha256": h, "snapshot": "snapshots/git-source/" + path}
    assert len(idx["source_hashes"]) == 42
    tree = git("ls-tree", "-r", source)
    assert len(tree.splitlines()) == 4843 and tree == (ind / (pre + "-source-git-tree.txt")).read_bytes()
    assert git("rev-parse", "HEAD").decode().strip() == source
    assert git("rev-parse", "refs/remotes/origin/feature/ws31-candidates").decode().strip() == source
    assert git("branch", "--show-current").decode().strip() == "feature/ws31-candidates"
    assert not git("status", "--porcelain").strip()
    assert git("remote", "get-url", "--push", "origin").decode().strip() == "https://github.com/LarryBUPT/conweave-ns3.git"
    old_root = repo / "docs/research/evidence/ws31-adapter-gate-integration-20261101-r1/snapshots"
    old_compared = 0
    for rel, info in idx["original_r1_files"].items():
        frozen = old_root / "independent" / rel
        if frozen.exists():
            assert frozen.read_bytes() == (ind / rel).read_bytes()
            old_compared += 1
    assert old_compared == 28
    meta = read(target / "metadata.json")
    assert meta["experiment_id"] == plan["id"] and meta["git_commit"] == source
    assert meta["status"] == "BUILT" and meta["build_mode"] == "optimized" and meta["cpu_jobs"] == 2
    assert meta["git_repository"] == "https://github.com/LarryBUPT/conweave-ns3.git"
    assert not any((target / "raw").rglob("*"))
    tech = read(target / "technical/adapter-boundary/receipt.json")
    assert tech == idx["binary_library_artifacts"]
    assert tech["source_sha"] == source and len(tech["binaries"]) == 2 and len(tech["libraries"]) == 36
    for item in list(tech["binaries"].values()) + list(tech["libraries"].values()):
        data = (target / item["artifact"]).read_bytes()
        assert data.startswith(b"\x7fELF") and digest(data) == item["sha256"]
    remote = "/home/fnl/lzy/runs/" + plan["id"] + "/source"
    env = {**plan["environment"], "LD_LIBRARY_PATH": remote + "/build", "PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"}
    assert tech["env_whitelist"] == env
    for name, text in tech["ldd"].items():
        assert name in tech["binaries"] and "not found" not in text
        found = set()
        for line in text.splitlines():
            f = line.split()
            if f and f[0].startswith("libns3."):
                assert f[1] == "=>" and f[2] == remote + "/build/" + f[0]
                found.add(f[0])
        assert found == set(tech["libraries"])
    assert [s["candidate"] for s in tech["steps"]] == ["C1", "C2", "C3"]
    last_end = ""
    logs = {}
    for step, configured in zip(tech["steps"], plan["ordered_executions"]):
        name = step["candidate"]
        assert step["exit_code"] == 0 and step["status"] == "PASS" and step["coverage_pass"]
        assert step["argv"] == [remote + "/" + configured["relative_binary"]] + configured["args"]
        assert step["cwd"] == remote and step["env_whitelist"] == env
        assert step["start_utc"] >= last_end
        last_end = step["end_utc"]
        data = (target / "logs" / ("adapter-" + name + ".log")).read_bytes()
        assert data == (folder / ("adapter-" + name + ".log")).read_bytes()
        assert digest(data) == step["log_sha256"]
        m = read(main / ("evidence/adapter-boundary-" + name.lower() + "-main-acceptance-r1.json"))
        assert m["log_sha256"] == step["log_sha256"] and m["cases"] == configured["case_count"]
        logs[name] = data.decode("utf-8")
    build = (target / "logs/build.log").read_text(encoding="utf-8")
    tasks = max(int(y) for x, y in re.findall(r"\[\s*(\d+)\s*/\s*(\d+)\s*\]", build))
    assert tasks == 1468 and re.findall(r"'build' finished successfully \(([^)]+)\)", build) == ["5m59.118s"]
    samples = [json.loads(s) for s in (target / "logs/resource-build-batch-samples.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(samples) == 74 and not any(s["unknown_project_pids"] or s["other_user_pids"] for s in samples)
    assert max(s["cc1plus_count_sample"] for s in samples) == 2
    assert max(s["loadavg"][0] for s in samples) == 2.0
    assert min(s["available_gib"] for s in samples) == idx["resources"]["min_sampled_available_gib"]
    ctl = read(ind / (pre + "-receipt.json"))
    assert ctl["build_commands"] == 1 and ctl["fixture_commands"] == 3
    for k in ["network_runs_started", "core_commands", "sync_commands", "deploy_commands"]:
        assert ctl[k] == 0
    assert len(ctl["commands"]) == 1 and ctl["commands"][0]["operation"] == "guarded-build"
    release = read(ind / (pre + "-guards-released.json"))
    assert release["status"] == "RELEASED" and release["fixture_calls_terminal"] == 3 and release["network_calls"] == 0

    # Direct checks against fixed test actions, not the main's complete model.
    c1 = records(logs["C1"], "WS31_SWITCH_BOUNDARY_PACKET ")
    c3 = records(logs["C3"], "WS31_SWITCH_BOUNDARY_PACKET ")
    assert len(c1) == 20 and len(c3) == 9
    assert Counter(x["case"] for x in c1) == {"c1-ranges": 5, "c1-expiry-reset": 5, "c1-capacity": 4, "c1-range-limit": 3, "c1-wrap": 3}
    assert Counter(x["case"] for x in c3) == {"c3-borrow-expiry-reset": 6, "c3-unknown-reset": 3}
    for x in c1 + c3:
        values(x, conserved=1)
        assert int(x["wire"]) - int(x["payload"]) == 56
    ranges = [x for x in c1 if x["case"] == "c1-ranges"]
    for x, unique in zip(ranges, [100, 100, 200, 400, 500]):
        values(x, unique=unique, chosen=3, budget_entries=1)
        remain = 8192 - unique
        assert int(x["pressure"]) == remain + ((remain + 999) // 1000) * 56
        values(x, queue_bytes=0 if int(x["time_ns"]) == 0 else 5000)
    expiry = [x for x in c1 if x["case"] == "c1-expiry-reset"]
    for x in expiry:
        t = int(x["time_ns"])
        values(x, budget_entries=int(t < 20000 or t == 20002), expired=int(t >= 20000))
        if 20000 <= t < 20002:
            values(x, pressure=0, unique=1000)
    for case in ["c1-range-limit", "c1-wrap"]:
        for x in [x for x in c1 if x["case"] == case][1:]:
            values(x, chosen=3, budget_entries=0, unique=100, range_fallback=1)
    capacity = [x for x in c1 if x["case"] == "c1-capacity"]
    values(capacity[1], capacity_fallback=1, budget_entries=1, pairs=2, chosen=7)
    values(capacity[2], capacity_fallback=1, budget_entries=0, unique=100, chosen=7)
    values(capacity[3], capacity_fallback=1, budget_entries=1, unique=200, chosen=7)
    assert len(records(logs["C1"], "WS31_C1_CHOICE ")) == 8
    resets = {n: records(logs[n], "WS31_SWITCH_BOUNDARY_RESET ") for n in ["C1", "C3"]}
    assert all(len(x) == 3 for x in resets.values())
    for rows in resets.values():
        for x in rows:
            values(x, conserved=1)
    for x in resets["C1"]:
        assert int(x["pairs_before"]) - int(x["pairs_after"]) == 1
    for x in resets["C3"]:
        assert int(x["quota_before"]) - int(x["quota_after"]) == 1
    borrower = [x for x in c3 if x["case"] == "c3-borrow-expiry-reset"]
    for x in borrower[:2]:
        values(x, chosen=1, live_owner2=1, activation2=0)
    values(borrower[2], fresh=2, restricted=1, activation2=1, live_owner2=1)
    values(borrower[3], residual=1, residual_bytes=156, tag=0, present=0, chosen=1)
    values(borrower[4], time_ns=20202, fresh=2, hits=3, activation1=2, activation2=1, live_owner2=1, residual=1, chosen=1)
    values(borrower[5], fresh=3, live_owner2=0, activation2=2, restricted=2, borrowed=1)
    idle = records(logs["C3"], "WS31_SWITCH_BOUNDARY_IDLE ")
    assert len(idle) == 3
    for x, t, a, b in zip(idle, [20199, 20200, 20201], [1, 1, 0], [1, 0, 0]):
        values(x, time_ns=t, active1=a, active2=b, quota_entries=2, live_owner2=1, observer_expires=0)
    unknown = [x for x in c3 if x["case"] == "c3-unknown-reset"]
    values(unknown[0], activation1=0, activation2=0, fresh=1)
    values(unknown[1], activation1=0, activation2=0, fresh=1, hits=1)
    values(unknown[2], activation1=1, activation2=0, fresh=2)
    c2 = records(logs["C2"], "WS31_C2_BOUNDARY PASS ")
    assert len(c2) == 10
    assert {(x["kind"], x["phase"]) for x in c2} == {(a, b) for a in ["stop", "dispose"] for b in ["before", "same-control-first", "same-launch-first", "after", "zero"]}
    # Independent FNV-style tuple wait calculation from the fixed source.
    h = 2166136261 ^ 0x43c2a517
    for word in [184549377, 184549633, 1 | (100 << 16)]:
        for j in range(4):
            h = ((h ^ ((word >> (8 * j)) & 255)) * 16777619) & 0xffffffff
    h ^= h >> 16
    h = (h * 0x85ebca6b) & 0xffffffff
    h ^= h >> 13
    assert h % 501 == 376
    for x in c2:
        phase = x["phase"]
        cancelled = int(phase in ["before", "same-control-first"])
        launched = 1 - cancelled
        wait = 0 if phase == "zero" else 376
        control_ns = 10 + wait + (-1 if phase == "before" else 1 if phase == "after" else 0)
        values(x, demand_ns=10, wait_ns=wait, sport=1, size=8192, demanded=1, demand_bytes=8192,
               launched=launched, calls=launched, cancelled=cancelled, control_ns=control_ns,
               launch_ns=(10 + wait) if launched else 0, dispatch_demand_ns=10 if launched else 0,
               launch_bytes=8192 * launched, cancel_bytes=8192 * cancelled,
               waited=int(launched and wait > 0), delay_sum_ns=wait * launched,
               delay_max_ns=wait * launched, finished=0, pending=0, transport="fixture")
        if phase.startswith("same-"):
            assert (int(x["control_uid"]) < int(x["launch_uid"])) == bool(cancelled)
    assert sum(int(x["cancelled"]) for x in c2) == 4
    assert sum(int(x["calls"]) for x in c2) == 6
    assert len(records(logs["C2"], "WS31_C2_DEMAND ")) == 10
    assert len(records(logs["C2"], "WS31_C2_CANCEL ")) == 4
    assert len(records(logs["C2"], "WS31_C2_LAUNCH ")) == 6
    neg = read(main / "evidence/adapter-boundary-main-real-log-negative-checks-r1.json")
    assert neg["status"] == "PASS_REAL_LOG_CORRUPTION_REJECTION" and len(neg["corrupt_examples_rejected"]) == 8
    assert neg["new_simulator_or_fixture_executions"] == 0
    for k in ["c1", "c3"]:
        assert digest(logs[k.upper()].encode("utf-8")) == neg["original_raw_unchanged"][k]
    next_plan_path = main / "adapter-default-validation-r1.json"
    nxt = read(next_plan_path)
    auth = read(main / "evidence/adapter-default-execution-authorization-r1.json")
    assert digest(next_plan_path.read_bytes()) == auth["plan_sha256"] == "01665606c32d7422b92f4202d23e8e571500321631ca376b5924ed67f5e7eb68"
    assert auth["main_preflight_acceptance_sha256"] == digest(accepted_path.read_bytes())
    assert nxt["source_sha"] == auth["source_sha"] == source
    assert auth["status"] == "CONDITIONAL_PLAN_PREREQUISITES_MET_MAIN_DISPATCH_AUTHORIZED"
    assert auth["sole_executor_idle_cursor"].endswith(":90")
    assert release["at_utc"] < auth["at_utc"]
    assert [x["lb"] for x in nxt["cells"]] == ["ws30v13-q12", "ws31-c2"]
    assert [x["id"] for x in nxt["cells"]] == ["20261101-153000-ws31-adapterdef-r1-q12", "20261101-153000-ws31-adapterdef-r1-c2"]
    assert nxt["build_resources"]["max_parallel_builds"] == 2 and nxt["build_resources"]["max_total_compile_jobs"] == 4
    assert "未编写端点代码" in (main / "endpoint-lifecycle-design-r1.md").read_text(encoding="utf-8")
    # Recheck identities after snapshots; accepted files are never rewritten.
    for info in manifest.values():
        if "source_path" in info:
            assert digest(Path(info["source_path"]).read_bytes()) == info["sha256"]
    (out / "source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {
        "at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_LOCAL_PROVENANCE_ARTIFACTS_EXPLICIT_RAW_BOUNDARIES_AND_NEXT_GATE",
        "source_sha": source, "last_network_accepted_source": plan["parent_sha"],
        "id": plan["id"], "index_sha256": digest(index_path.read_bytes()), "QA_sha256": digest(qa_path.read_bytes()),
        "main_acceptance_sha256": digest(accepted_path.read_bytes()), "files_hashed": counts,
        "fixed_git_objects": 42, "fixed_tree_entries": 4843, "original_r1_compared_with_root_snapshots": old_compared,
        "build_tasks": tasks, "build_duration": "5m59.118s", "build_count": 1,
        "ELF_binaries_hashed": 2, "resolved_ns3_libraries_hashed": 36,
        "library_mapping_scope": "Recorded ldd with whitelisted LD_LIBRARY_PATH, not kernel runtime mapping capture",
        "large_artifacts_git_policy": "38 ELF files hashed in original local result store; not duplicated into Git",
        "resource_samples": 74, "raw_boundary_checks": {
            "C1_packets": 20, "C1_first_choices": 8, "C1_resets": 3, "real_queue_fill_B": 5000,
            "C2_conditions": 10, "C2_demand_B": 81920, "C2_cancels": 4, "C2_dispatch_substitutes": 6,
            "C2_wait_ns_independently_calculated": 376, "C2_equal_time_uid_orders": 4,
            "C3_packets": 9, "C3_resets": 3, "C3_idle_boundaries": 3,
            "C3_residual_packets": 1, "C3_residual_wire_B": 156, "framing_overhead_B": 56,
            "packet_QP_and_endpoint_generation_scope": "Switch test packets plus C2 transport substitute; no real QP/generation acceptance"
        },
        "full_C1_C3_model_replay_owner": "WS31 main, with unchanged preflight verifier hashes; not rerun by Integration",
        "eight_corruption_rejections_owner": "WS31 main; raw-copy tests, receipts/identities verified by Integration",
        "r2_sync_deploy_old_core_network": [0, 0, 0, 0],
        "r1_failure_and_unknown_PID_kept": True,
        "preflight_guard_released": True, "next_default_plan_sha256": digest(next_plan_path.read_bytes()),
        "next_default_ids": [x["id"] for x in nxt["cells"]], "next_execution_outcomes_accepted": False,
        "next_source_entry_env_guard": "Hold per separate main dispatch until explicit release",
        "network_technical_cells_accepted_cumulative": 41, "new_combined_baseline": False,
        "Integration_remote_actions_builds_fixtures": 0, "manifest_entries": len(manifest),
        "frozen_snapshots": sum(x["snapshot"] is not None for x in manifest.values()),
        "remaining": ["New-source Q12/C2 default compatibility", "Real endpoint exit/drain/generation/tuple reuse",
                      "Independent C1 V0", "All three candidates' business/background effects and state/runtime costs"]
    }
    (out / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    output = Path(__file__).resolve().parent
    if (output / "verification.json").exists() or (output / "source-manifest.json").exists():
        raise RuntimeError("Refusing to overwrite completed Integration evidence")
    result = audit(Path.cwd(), output)
    print(json.dumps({k: result[k] for k in ["status", "files_hashed", "fixed_git_objects", "build_tasks", "manifest_entries", "frozen_snapshots"]}))
