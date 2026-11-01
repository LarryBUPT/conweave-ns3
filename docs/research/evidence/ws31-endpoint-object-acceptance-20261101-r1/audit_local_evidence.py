"""Independent local Integration of object-fixture output and build provenance.

No main verifiers, executable artifacts, compilers, simulator or remote command
are run. Large ELF artifacts remain in the original local result store.
"""
from collections import defaultdict
from datetime import datetime, timezone
import ast
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def raw_checks(path, plan):
    rows = defaultdict(list)
    data = path.read_bytes()
    assert data.endswith(b"\n") and len(data.splitlines()) == 62
    for line in data.decode("utf-8").splitlines():
        tokens = shlex.split(line)
        prefix = tokens.pop(0)
        if prefix == "WS31_ENDPOINT_OBJECT_SUMMARY":
            assert tokens.pop(0) == "PASS"
        fields = {}
        for token in tokens:
            k, sep, value = token.partition("=")
            assert sep and k not in fields
            fields[k] = value if k in ["case", "state", "reason"] else int(value)
        rows[prefix].append(fields)
    P = "WS31_ENDPOINT_OBJECT"
    assert {p: len(v) for p, v in rows.items()} == {P: 8, P+"_DEVICE": 16, P+"_SLOT": 13, P+"_SACK": 8, P+"_REFUSE": 16, P+"_SUMMARY": 1}
    assert [r["case"] for r in rows[P]] == plan["fixture"]["normal_cases"]
    assert [r["case"] for r in rows[P+"_SACK"]] == plan["fixture"]["normal_cases"]
    denial_names = {r["case"] for r in rows[P+"_REFUSE"]}
    assert denial_names == set(plan["fixture"]["read_refusal_cases"] + plan["fixture"]["other_refusals"])
    assert rows[P+"_SUMMARY"] == [{"reads": 31, "refusals": 16, "network_runs": 0, "event_calls": 0, "actual_network_completions": 0}]
    bound = None
    saved = None
    new_object = None
    for i, r in enumerate(rows[P]):
        name = r["case"]
        assert r["mask"] == 127 and r["nodes"] == r["devices"] == 2
        assert r["before"] == r["after"] and r["full_protocol_bytes_equal"] == 1
        assert r["finished"] == int(i < 2)
        assert r["pending"] == (0 if i < 2 else 8192 if i == 2 else 4096)
        active = int(i == 7)
        assert r["tx_timers"] == r["rx_timers"] == r["transmitting"] == active
        assert r["device_timers"] == 2*active
        assert r["data"] == 32*int(i >= 6) and r["ack"] == 48*int(i >= 6)
        assert r["history_released"] == int(i < 4)
        if saved is None:
            saved = r["saved_tx"], r["saved_rx"]
            assert min(saved) > 0 and len(set(saved)) == 2
        assert (r["saved_tx"], r["saved_rx"]) == saved and r["live_tx"] == 0
        assert r["live_rx"] == (saved[1] if i == 5 else 0)
        devices = [{k: v for k, v in d.items() if k != "case"} for d in rows[P+"_DEVICE"] if d["case"] == name]
        assert len(devices) == 2
        assert len({(d["node"], d["interface"]) for d in devices}) == 2
        for k in ["object", "physical", "egress", "ack", "group"]:
            assert min(d[k] for d in devices) > 0 and len({d[k] for d in devices}) == 2
        if bound is None:
            bound = devices
        assert devices == bound
        slots = [d for d in rows[P+"_SLOT"] if d["case"] == name]
        assert len(slots) == (1 if i < 3 else 2)
        old = slots[0]
        assert old["slot"] == old["flow_id"] == 0 and old["object"] == saved[0]
        assert old["finished_bit"] == int(i != 0) and old["completed"] == int(i != 2)
        assert old["next"] == old["acknowledged"] == (0 if i == 2 else 8192)
        assert old["size"] == 8192 and old["pending"] == (8192 if i == 2 else 0) and old["timers"] == active
        if i >= 3:
            new = slots[1]
            assert (new["node"], new["interface"]) == (old["node"], old["interface"])
            assert new["slot"] == new["flow_id"] == 1 and new["size"] == new["pending"] == 4096
            if new_object is None:
                new_object = new["object"]
                assert new_object > 0 and new_object not in saved
            assert new["object"] == new_object
            assert all(new[k] == 0 for k in ["finished_bit", "completed", "next", "acknowledged", "timers"])
        sack = next(d for d in rows[P+"_SACK"] if d["case"] == name)
        assert sack["next"] == sack["acknowledged"] == old["next"]
        assert sack["state"] == ("" if i < 2 else "[0-1024] [2048-3072] ")
    for r in rows[P+"_REFUSE"]:
        assert r["reason"]
        if r["case"] in plan["fixture"]["read_refusal_cases"]:
            assert r["full_protocol_bytes_equal"] == 1
    return {"rows": 62, "normal_pairs": 8, "device_rows": 16, "slot_rows": 13, "SACK_rows": 8,
            "Read_calls": 31, "Read_refusals": 14, "successful_returns": 17, "other_refusals": 2,
            "mask": 127, "event_calls": 0, "natural_network_completions": 0,
            "object_bindings_slots_SACK_queues_and_timers_checked": True,
            "full_protocol_string_comparison_scope": "Runtime check is inside fixed C++; raw display hashes/flags are linked through source/build/binary, not a whole-memory comparison"}


def audit(root, out):
    ws = root / "docs/research/ws31"
    main, ind = ws / "main", ws / "independent"
    impl = root.parent / "ws31-candidates-implementation"
    git = lambda *a: subprocess.check_output(["git", "-C", str(impl), *a])
    pre = "endpoint-probe-object-preflight-r1"
    base = ind / (pre + "-raw")
    raw = base / "remote-results"
    ip, qp = ind / (pre + "-index.json"), ind / (pre + "-qa.json")
    idx, qa = read(ip), read(qp)
    acceptedpath = main / "evidence/endpoint-object-delivery-main-acceptance-r1.json"
    accepted = read(acceptedpath)
    planpath = main / (pre + ".json")
    plan = read(planpath)
    source = "8cd1ba69469bf80143d5c89edc17fa72611018e8"
    assert digest(ip) == qa["index"]["sha256"] == accepted["index_sha256"] == "11137470407f9fc587971e8ad6ec2cb0000699a9959cf19166aabd2431751f5f"
    assert digest(qp) == accepted["QA_sha256"] == "98bb162d029300695ac852939d293beea643a90aa054a26fcfc085e9c4e46658"
    assert digest(planpath) == idx["plan"]["sha256"] == accepted["plan_sha256"] == "d91892f73bc6a6b45c0541f2c588ba59ba3fd3694ec75a75e35be5265dd5b255"
    assert idx["source_sha"] == accepted["source_sha"] == plan["source_sha"] == source
    assert idx["status"] == "PASS_ACTUAL_OBJECT_PROBE_PREFLIGHT_ONLY" and qa["status"] == "PASS_ACTUAL_OBJECT_PREFLIGHT_DELIVERY"
    manifest, cache = {}, {}

    def capture(path, name, expected=None):
        key = str(path.resolve())
        if key not in cache:
            with path.open("rb") as stream:
                elf = stream.read(4) == b"\x7fELF"
            cache[key] = digest(path), path.stat().st_size, elf
        h, size, elf = cache[key]
        if expected is not None:
            assert h == (expected["sha256"] if isinstance(expected, dict) else expected), key
            if isinstance(expected, dict):
                assert size == expected["bytes"], key
        snapshot = None if elf else "snapshots/" + name
        if snapshot:
            p = out / snapshot
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.exists():
                assert digest(p) == h
            else:
                p.write_bytes(path.read_bytes())
        manifest[name] = {"source_path": key, "bytes": size, "sha256": h, "snapshot": snapshot,
                          "ELF_retained_original_local_store": elf}

    def evidence_path(value):
        suffix = value.replace("\\", "/").split("/docs/research/ws31/", 1)[1]
        p = (ws / suffix).resolve()
        assert p.is_relative_to(ws.resolve())
        return p

    def name(path):
        return path.relative_to(ws).as_posix().replace("independent/" + pre + "-raw/", "raw/", 1)

    assert len(idx["artifacts"]) == 170
    for item in idx["artifacts"]:
        p = evidence_path(item["path"])
        capture(p, name(p), item)
    for path, h in idx["old_artifacts_preserved"].items():
        p = evidence_path(path)
        capture(p, "prior/" + p.name, h)
    assert len(idx["old_artifacts_preserved"]) == 13
    fetched = read(raw / "receipt-manifest.json")
    assert len(fetched) == len({x["path"] for x in fetched}) == 109
    assert sum(x["bytes"] for x in fetched) == idx["raw_fetch"]["verified_bytes"] == 183766520
    assert digest(raw / "receipt-manifest.json") == idx["raw_fetch"]["manifest_sha256"]
    for item in fetched:
        p = (raw / item["path"]).resolve()
        assert p.is_relative_to(raw.resolve())
        capture(p, name(p), item)
    capture(raw / "receipt-manifest.json", "raw/receipt-manifest.json")
    tree = git("ls-tree", "-r", source)
    assert tree == (raw / "provenance/source-tree.txt").read_bytes()
    assert hashlib.sha256(tree).hexdigest() == plan["tree_sha256"]
    entries = {}
    for line in tree.decode().splitlines():
        fields, path = line.split("\t", 1)
        mode, kind, blob = fields.split()
        assert kind == "blob" and path not in entries
        entries[path] = mode, blob
    sources = read(raw / "provenance/source-files.json")
    assert len(entries) == len(sources) == len({x["path"] for x in sources}) == 4847
    process = subprocess.Popen(["git", "-C", str(impl), "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    total = 0
    try:
        for item in sources:
            assert entries[item["path"]] == (item["mode"], item["git_blob"])
            process.stdin.write((item["git_blob"] + "\n").encode("ascii")); process.stdin.flush()
            oid, kind, size = process.stdout.readline().split()
            assert oid.decode() == item["git_blob"] and kind == b"blob" and int(size) == item["bytes"]
            remaining = int(size); total += remaining; h = hashlib.sha256()
            while remaining:
                chunk = process.stdout.read(min(remaining, 1048576)); assert chunk
                h.update(chunk); remaining -= len(chunk)
            assert process.stdout.read(1) == b"\n" and h.hexdigest() == item["sha256"]
    finally:
        process.stdin.close(); process.stdout.close(); assert process.wait() == 0
    assert total == idx["source"]["source_bytes"] == 284719415
    for rel, h in plan["source_changes_sha256"].items():
        fixed, working = base / "frozen-source" / rel, base / "local-working-bytes" / rel
        assert digest(fixed) == h and hashlib.sha256(git("show", source + ":" + rel)).hexdigest() == h
        assert working.read_bytes().replace(b"\r\n", b"\n") == fixed.read_bytes()
    for rel, h in idx["source"]["accepted_core_inputs_unchanged"].items():
        assert hashlib.sha256(git("show", source + ":" + rel)).hexdigest() == h
    receipts = [read(raw / ("provenance/" + x + "-result.json")) for x in ["configure", "build", "fixture"]]
    cwd = "/home/fnl/lzy/runs/" + plan["id"] + "/source"
    assert [x["argv"] for x in receipts] == [["./waf", "configure", "--build-profile=optimized"], ["./waf", "-j2", "-v"], [cwd + "/build/scratch/ws31-endpoint-object-test"]]
    assert time(receipts[0]["end_utc"]) <= time(receipts[1]["start_utc"]) and time(receipts[1]["end_utc"]) <= time(receipts[2]["start_utc"])
    for i, r in enumerate(receipts):
        assert r["exit"] == r["wait_status"] == 0 and r["cwd"] == cwd
        env = r["environment"]
        assert env == read(raw / ("provenance/" + ("fixture" if i == 2 else "build") + "-environment.json"))
        assert "LD_PRELOAD" not in env
        assert {k for k in env if k.startswith(("WS30_", "WS31_"))} == {"WS30_OBSERVE", "WS31_LABEL_PROFILE", "WS30_TAG_TRANSFORM", "WS30_LIFECYCLE", "WS30_LIFE_PROFILE", "WS30_COMPOSITION"}
        assert all(v == "0" for k, v in env.items() if k.startswith(("WS30_", "WS31_")))
        assert env.get("LD_LIBRARY_PATH") == (cwd + "/build" if i == 2 else None)
        for stream in ["stdout", "stderr"]:
            assert digest(raw / r[stream]) == r[stream + "_sha256"]
        for point in ["resources_before", "resources_after"]:
            s = r[point]
            assert s["load"][0] <= 4 and s["mem_available_gib"] >= 64 and s["disk_available_gib"] >= 100
    commands, buildtext = [], ""
    for stream in ["stdout", "stderr"]:
        text = (raw / ("logs/build." + stream)).read_text(encoding="utf-8")
        buildtext += text
        for line in text.splitlines():
            if " runner [" in line:
                commands.append(ast.literal_eval(line.split(" runner ", 1)[1]))
    compiles = [c for c in commands if "../scratch/ws31-endpoint-object-test.cc" in c]
    links = [c for c in commands if cwd + "/build/scratch/ws31-endpoint-object-test" in c]
    assert len(compiles) == len(links) == 1
    assert all(x in compiles[0] for x in ["-O3", "-g", "-std=gnu++11", "-c"]) and "-DNDEBUG" not in compiles[0]
    assert compiles[0] == accepted["compiler_argv"]
    assert max(tuple(map(int, m)) for m in re.findall(r"\[(\d+)/(\d+)\]", buildtext)) == (1470, 1470)
    waf_duration = re.findall(r"'build' finished successfully \(([^)]+)\)", buildtext)
    assert waf_duration == ["5m57.379s"]
    binary = raw / "artifacts/ws31-endpoint-object-test"
    assert binary.stat().st_size == idx["binary"]["bytes"] == 1709032 and binary.read_bytes()[:4] == b"\x7fELF"
    assert digest(binary) == accepted["binary_sha256"] == "06bbe540d28f35571502e0b4189c1029e2282fae179402443f43dc1258e099ef"
    libraries = read(raw / "provenance/runtime-libraries.json")
    assert libraries == idx["runtime_libraries"] and len(libraries) == 45
    project = [x for x in libraries if x["project_library"]]
    assert len(project) == 36
    for lib in project:
        p = raw / lib["local_artifact"]
        assert p.stat().st_size == lib["bytes"] and digest(p) == lib["sha256"]
        assert lib["realpath"].startswith(cwd + "/build/")
    assert len([x for x in libraries if not x["project_library"]]) == 9
    static, gate = read(base / "local-static-review.json"), read(base / "before-sync-gate-review.json")
    assert static["source_sha"] == source and static["local_status"] == "clean"
    assert time(static["at_utc"]) < time(gate["at_utc"]) <= time(idx["commands"]["sync"]["start_utc"])
    assert not gate["unknown_jobs"] and gate["worker_verified"] and all(gate["id_absent"].values())
    worker = hashlib.sha256(git("show", source + ":scripts/remote_worker.py")).hexdigest()
    for stage in ["before-source-gate", "before-fixture-gate", "after-fixture-gate"]:
        g = read(raw / ("provenance/" + stage + ".json"))
        assert g["decision"] == "PASS_FRESH_GATE" and g["worker"]["LF_sha256"] == worker
        assert not g["worker"]["symlink"] and not any(g["maintenance_markers"].values())
        assert g["load"][0] <= 4 and g["mem_available_gib"] >= 64 and g["disk_available_gib"] >= 100
    release = read(ind / (pre + "-guards-released.json"))
    final = read(base / "after-fetch-gate.stdout.json")
    assert release["status"] == "EXPLICITLY_RELEASED_AFTER_ALL_TERMINAL_CALLS_AND_VERIFIED_RAW"
    assert all(release[k] == "released" for k in ["source_guard", "entry_guard", "environment_guard"])
    assert release["no_persistent_driver"] and not release["future_execution_authority"]
    assert release["remote_task_pids_absent"] == final["previous_task_pids_absent"] and final["all_guarded_calls_terminal"]
    assert not set(release["remote_task_pids_absent"]) & {p["pid"] for p in final["processes"]}
    assert idx["counts"] == accepted["counts"] == {"sync": 1, "deploy": 0, "full_optimized_j2_build": 1, "new_object_fixture": 1, "standalone_core_compile": 0, "old_core_adapter_reference_rerun": 0, "network_run": 0}
    assert len(idx["auxiliary_checker_corrections"]) == 2 and idx["scientific_retries"] == 0
    assert idx["auxiliary_checker_corrections"][0]["status"] == "LOCAL_VERIFIER_ASSUMPTION_FAILED_NOT_SOURCE_CHANGE"
    assert idx["auxiliary_checker_corrections"][1]["status"] == "LOCAL_LOG_EXTRACTOR_STDOUT_ONLY_ASSUMPTION_FAILED"
    transcript = raw_checks(raw / "logs/fixture.stdout", plan)
    assert (raw / "logs/fixture.stderr").stat().st_size == 0
    prep = read(main / "evidence/endpoint-object-main-verifier-preparation-r1.json")
    assert digest(main / prep["raw_verifier"]) == prep["raw_verifier_sha256"] == "cac9e289b7cfbdf5884f20adf65fa38af9a8728c974a9f8c0ba0960be185f147"
    main_raw = read(main / "evidence/endpoint-object-raw-main-acceptance-r1.json")
    assert main_raw["stdout_sha256"] == digest(raw / "logs/fixture.stdout")
    assert git("rev-parse", "HEAD").decode().strip() == source == git("rev-parse", "refs/remotes/origin/feature/ws31-candidates").decode().strip()
    assert not git("status", "--porcelain", "-uall").strip()
    for p in [ip, qp]:
        capture(p, "independent/" + p.name)
    for rel in ["endpoint-object-node17-handoff.md", "endpoint-probe-object-preflight-r1.json", "endpoint-channel-integration-design-r1.md",
                "evidence/endpoint-object-delivery-main-acceptance-r1.json", "evidence/endpoint-object-raw-main-acceptance-r1.json",
                "evidence/endpoint-object-main-verifier-preparation-r1.json", "evidence/endpoint-object-node17-reference-review-r1.json",
                "scripts/verify_endpoint_object_raw_r1.py", "scripts/verify_endpoint_object_delivery_r1.py", "current-status.json"]:
        capture(main / rel, "main/" + rel)
    assert digest(main / "endpoint-channel-integration-design-r1.md") == prep["channel_design_sha256"]
    paper = root.parent.parent / "参考文献/候选"
    for rel in ["README.md", "reading-log.md", "papers/diffflow-2016/analysis-technical.md", "papers/diffflow-2016/verification.md"]:
        capture(paper / rel, "literature/" + Path(rel).name)
    assert digest(ip) == accepted["index_sha256"]
    (out / "source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {"at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS_OBJECT_TRANSCRIPT_BUILD_SOURCE_BINARY_LIBRARIES_AND_RELEASE",
              "source_sha": source, "id": plan["id"], "index_sha256": digest(ip), "QA_sha256": digest(qp), "main_acceptance_sha256": digest(acceptedpath),
              "indexed_artifacts_hashed": 170, "raw_files_hashed": 109, "prior_artifacts_preserved": 13,
              "git_file_path_entries_hashed": 4847, "git_per_path_payload_bytes_hashed": total, "Git_counts_are_unique_objects": False,
              "binary_bytes": 1709032, "binary_sha256": digest(binary), "project_library_copies_locally_hashed": 36,
              "system_library_fingerprints_only": 9, "library_scope": "ldd resolved paths plus saved project ELF bytes; no proc maps runtime capture",
              "build_tasks": 1470, "build_outer_elapsed_seconds": receipts[1]["elapsed_seconds"], "Waf_inner_duration": waf_duration[0],
              "compiler_argv": compiles[0], "compiler_NDEBUG_flag_present": False, "transcript": transcript,
              "build_child_max_rss_kib": receipts[1]["rusage"]["max_rss_kib"], "fixture_child_max_rss_kib": receipts[2]["rusage"]["max_rss_kib"],
              "auxiliary_checker_failures_preserved": 2, "scientific_retries": 0, "main_raw_verifier_unchanged": True,
              "guards_explicitly_released": release["at_utc"], "no_persistent_driver": True, "future_execution_authority": False,
              "current_checkout_clean_fixed8cd": True, "channel_design_only_no_new_implementation_accepted": True,
              "large_ELFs_retained_in_original_local_store": True, "ELF_manifest_paths_not_copied_to_Git": sum(x["snapshot"] is None for x in manifest.values()),
              "network_technical_total": 43, "nonnetwork_adapter_conditions": 17, "new_combined_baseline": False,
              "Integration_remote_build_fixture_or_main_verifier_runs": 0, "manifest_entries": len(manifest), "remaining": idx["remaining_required"]}
    (out / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    out = Path(__file__).resolve().parent
    if (out / "verification.json").exists() or (out / "source-manifest.json").exists():
        raise RuntimeError("Refusing to overwrite Integration acceptance")
    result = audit(Path.cwd(), out)
    print(json.dumps({k: result[k] for k in ["status", "indexed_artifacts_hashed", "raw_files_hashed", "git_file_path_entries_hashed", "git_per_path_payload_bytes_hashed", "project_library_copies_locally_hashed"]}))
