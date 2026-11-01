"""Integration checks saved core evidence and Git blobs without running C++."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit(root, out):
    ws = root / "docs/research/ws31"
    main, ind = ws / "main", ws / "independent"
    impl = root.parent / "ws31-candidates-implementation"
    git = lambda *args: subprocess.check_output(["git", "-C", str(impl), *args])
    pre = "endpoint-ledger-core-preflight-r2"
    idxpath, qapath = ind / (pre + "-index.json"), ind / (pre + "-qa.json")
    idx, qa = read(idxpath), read(qapath)
    acceptedpath = main / "evidence/endpoint-ledger-core-preflight-main-acceptance-r2.json"
    accepted = read(acceptedpath)
    planpath = main / (pre + ".json")
    plan = read(planpath)
    source = "20bc2d9f7c7c435bf832ba2fcaf0e07df00cf5da"
    assert sha(idxpath) == qa["index"]["sha256"] == accepted["index_sha256"] == "5c8fd34433da0d8d5d317f5c2d4b545e8e2a6657834af67b856a7d778a194b68"
    assert sha(qapath) == accepted["QA_sha256"] == "16a64faf700cfecdd14e6a10a4cfd90698cc7b3c2094f2af1394f76ce81e7ce4"
    assert sha(planpath) == idx["plan"]["sha256"] == accepted["plan_sha256"] == "57ee56f60e6406dfaeab8e317910423e53fdb87e46982be6bf730dd4823fae47"
    assert idx["source_sha"] == plan["source_sha"] == accepted["source_sha"] == source
    assert idx["status"] == "PASS_FOR_PORTABLE_CORE_PREFLIGHT_ONLY" and qa["status"] == "PASS_PORTABLE_CORE_PREFLIGHT_DELIVERY"
    assert accepted["status"] == "MAIN_ACCEPTED_PORTABLE_ENDPOINT_CORE_SINGLE_COMPILE_RUN_AND_DELIVERY"
    manifest = {}

    def capture(path, name, expected=None):
        h, size = sha(path), path.stat().st_size
        if expected is not None:
            assert h == (expected["sha256"] if isinstance(expected, dict) else expected), str(path)
            if isinstance(expected, dict):
                assert size == expected["bytes"], str(path)
        dest = out / "snapshots" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            assert sha(dest) == h
        else:
            dest.write_bytes(path.read_bytes())
        manifest[name] = {"source_path": str(path.resolve()), "bytes": size, "sha256": h,
                          "snapshot": "snapshots/" + name}

    def evidence_path(value):
        suffix = value.replace("\\", "/").split("/docs/research/ws31/", 1)[1]
        path = (ws / suffix).resolve()
        assert path.is_relative_to(ws.resolve())
        return path

    def short_name(path):
        rel = path.relative_to(ws).as_posix()
        return rel.replace("independent/" + pre + "-raw/", "raw/", 1)

    assert len(idx["artifacts"]) == 90
    for item in idx["artifacts"]:
        p = evidence_path(item["path"])
        capture(p, short_name(p), item)
    for raw, h in idx["old_artifacts_preserved"].items():
        p = evidence_path(raw)
        capture(p, "original/" + p.name, h)
    assert len(idx["old_artifacts_preserved"]) == 5
    result = ind / (pre + "-raw/remote-results")
    raw_manifest = read(result / "receipt-manifest.json")
    assert len(raw_manifest) == idx["raw_fetch"]["verified_files"] == 41
    assert sha(result / "receipt-manifest.json") == idx["raw_fetch"]["manifest_sha256"]
    for item in raw_manifest:
        p = result / item["path"]
        capture(p, short_name(p), item)
    capture(result / "receipt-manifest.json", "raw/receipt-manifest.json")
    tree = git("ls-tree", "-r", source)
    assert tree == (result / "provenance/source-tree.txt").read_bytes()
    assert len(tree.splitlines()) == 4845 and hashlib.sha256(tree).hexdigest() == plan["tree_sha256"]
    entries = {}
    for row in tree.decode("utf-8").splitlines():
        fields, path = row.split("\t", 1)
        mode, kind, blob = fields.split()
        assert kind == "blob" and path not in entries
        entries[path] = (mode, blob)
    filespath = result / "provenance/source-files.json"
    sources = read(filespath)
    assert len(sources) == len({x["path"] for x in sources}) == len(entries) == 4845
    assert sha(filespath) == idx["source"]["source_files_manifest_sha256"]
    process = subprocess.Popen(["git", "-C", str(impl), "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    total = 0
    try:
        for item in sources:
            assert entries[item["path"]] == (item["mode"], item["git_blob"])
            process.stdin.write((item["git_blob"] + "\n").encode("ascii"))
            process.stdin.flush()
            oid, kind, size = process.stdout.readline().split()
            assert oid.decode("ascii") == item["git_blob"] and kind == b"blob" and int(size) == item["bytes"]
            remain = int(size)
            total += remain
            h = hashlib.sha256()
            while remain:
                block = process.stdout.read(min(remain, 1048576))
                assert block
                h.update(block)
                remain -= len(block)
            assert process.stdout.read(1) == b"\n" and h.hexdigest() == item["sha256"], item["path"]
    finally:
        process.stdin.close()
        process.stdout.close()
        assert process.wait() == 0
    assert total == idx["source"]["verified_source_bytes"] == accepted["git_bytes_verified"] == 284683832
    for rel, h in plan["source_changes_sha256"].items():
        p = ind / (pre + "-raw/frozen-source") / rel
        capture(p, "inputs/" + p.name, h)
        assert hashlib.sha256(git("show", source + ":" + rel)).hexdigest() == h
        assert (impl / rel).read_bytes().replace(b"\r\n", b"\n") == p.read_bytes().replace(b"\r\n", b"\n")
    compiled = read(result / "provenance/compile-result.json")
    run = read(result / "provenance/run-result.json")
    binary_path = "/home/fnl/lzy/results/" + plan["id"] + "/artifacts/ws31_endpoint_ledger_test"
    argv = [binary_path if s.startswith("<new-ID-results>") else s for s in plan["compile"]["argv"]]
    assert compiled["argv"] == argv == accepted["compile_argv"] and run["argv"] == [binary_path]
    assert compiled["exit"] == run["exit"] == compiled["wait_status"] == run["wait_status"] == 0
    assert compiled["end_utc"] <= run["start_utc"]
    assert compiled["environment"] == run["environment"] == read(result / "provenance/exact-compile-run-environment.json")
    for r in [compiled, run]:
        assert r["cwd"] == "/home/fnl/lzy/runs/" + plan["id"] + "/source"
        for s in ["stdout", "stderr"]:
            assert sha(result / r[s]) == r[s + "_sha256"]
        for s in ["resources_before", "resources_after"]:
            assert r[s]["load"][0] <= 4 and r[s]["mem_available_gib"] >= 64 and r[s]["disk_available_gib"] >= 100
    assert (result / "logs/run.stdout").read_bytes() == plan["run"]["expected_stdout"].encode("ascii")
    assert all((result / f).stat().st_size == 0 for f in ["logs/run.stderr", "logs/compile.stdout", "logs/compile.stderr"])
    binary = result / "artifacts/ws31_endpoint_ledger_test"
    assert binary.read_bytes()[:4] == b"\x7fELF" and binary.stat().st_size == 50520
    assert sha(binary) == accepted["binary_sha256"] == idx["binary"]["sha256"] == "15ed3dd0a023e59da058535e29797d7c67787912a619203ad2ee96e108dac86b"
    counts = {"sync": 1, "deploy": 0, "full_ns3_build": 0, "new_core_compile": 1, "new_core_run": 1, "network_run": 0, "old_core_or_fixture_rerun": 0}
    assert idx["counts"] == accepted["counts"] == counts
    assert idx["commands"]["compile"] == compiled and idx["commands"]["run"] == run
    assert idx["commands"]["sync"]["exit"] == 0 and idx["commands"]["sync"]["authorized_sync_command_number"] == 1
    assert idx["runtime_libraries"] == read(result / "provenance/runtime-libraries.json") and len(idx["runtime_libraries"]) == 5
    ldd = (result / "logs/binary-ldd.stdout").read_text(encoding="utf-8")
    assert "not found" not in ldd and all(x["invocation_path"] in ldd for x in idx["runtime_libraries"])
    release = read(ind / (pre + "-guards-released.json"))
    assert release["status"] == "EXPLICITLY_RELEASED_AFTER_TERMINAL_CALLS_AND_FETCH_INTEGRITY"
    assert release["no_persistent_driver"] and not release["future_execution_authorized"]
    assert all(release[k] == "released" for k in ["source_guard", "entry_guard", "environment_guard"])
    refs = read(ind / (pre + "-reference-review.json"))
    paper = root.parent.parent / "参考文献/候选"
    for item in refs["source_records"]:
        name = item["path"].replace("\\", "/").split("/")[-1]
        p = paper / name if name in ["README.md", "reading-log.md"] else paper / "papers/diffflow-2016" / name
        capture(p, "literature/" + name, item["sha256"])
    capture(idxpath, "independent/" + idxpath.name)
    capture(qapath, "independent/" + qapath.name)
    main_files = ["endpoint-core-node15-handoff.md", pre + ".json", "evidence/endpoint-ledger-core-preflight-main-acceptance-r2.json",
                  "scripts/verify_endpoint_core_preflight_r2.py", "evidence/endpoint-ledger-main-checker-initial-r1.py",
                  "evidence/endpoint-ledger-main-checker-path-repair-r1.json", "evidence/endpoint-probe-wip-source-audit-r1.json",
                  "endpoint-probe-local-review-r1.json"]
    for rel in main_files:
        capture(main / rel, "main/" + rel)
    repair = read(main / "evidence/endpoint-ledger-main-checker-path-repair-r1.json")
    old_checker = main / "evidence/endpoint-ledger-main-checker-initial-r1.py"
    assert sha(old_checker) == repair["preserved_script_sha256"]
    old_text = old_checker.read_text(encoding="utf-8")
    corrected = old_text.replace("def verify(repo, source):\n", "def verify(repo, source):\n    repo, source = repo.resolve(), source.resolve()\n")
    corrected = corrected.replace("prefix.replace('core-preflight', 'core-preflight')", "prefix")
    assert corrected == (main / "scripts/verify_endpoint_core_preflight_r2.py").read_text(encoding="utf-8")
    nxtpath = main / "endpoint-probe-local-review-r1.json"
    nxt = read(nxtpath)
    wip_audit = read(main / "evidence/endpoint-probe-wip-source-audit-r1.json")
    assert sha(nxtpath) == "fd8e63b3692967d6f938d409945ee9dad12b5401772c2a07e9b56062c51482ee"
    assert nxt["files_working_sha256"] == wip_audit["files_working_sha256"] and nxt["parent_head"] == source
    for rel, h in nxt["files_working_sha256"].items():
        capture(impl / rel, "probe-wip/" + Path(rel).name, h)
    header = "src/point-to-point/model/qbb-net-device.h"
    probe = "src/point-to-point/model/ws31-endpoint-probe.h"
    base_header = git("show", source + ":" + header).decode()
    actual_header = (impl / header).read_text(encoding="utf-8")
    added = "  // Read-only WS-31 endpoint evidence adapter; never called by normal routing.\n  friend class Ws31EndpointProbe;\n"
    assert actual_header.count(added) == 1 and actual_header.replace(added, "") == base_header
    assert git("status", "--porcelain", "-uall").decode().splitlines() == [" M " + header, "?? " + probe]
    assert git("rev-parse", "HEAD").decode().strip() == source == git("rev-parse", "refs/remotes/origin/feature/ws31-candidates").decode().strip()
    qp = git("show", source + ":src/point-to-point/model/rdma-queue-pair.cc").decode()
    section = qp[qp.index("uint64_t RdmaQueuePair::GetBytesLeft()"):qp.index("uint32_t RdmaQueuePair::GetHash(")]
    assert "snd_nxt += sack_sz;" in section and "irn.m_sack.discardUpTo(snd_nxt);" in section
    dev = git("show", source + ":src/point-to-point/model/qbb-net-device.cc").decode()
    assert "return m_qpGrp->Get(qIndex)->GetBytesLeft();" in dev
    code = re.sub(r"//[^\n]*", "", (impl / probe).read_text(encoding="utf-8"))
    assert "->GetBytesLeft(" not in code and "->GetNextQindex(" not in code and "->IsFinished()" not in code
    mask = code.split("s.observedFields=", 1)[1].split(";", 1)[0]
    assert "SWITCH_STATE" not in mask and "::ALL" not in mask
    assert nxt["pre_dispatch_idle_cursor"].endswith(":98")
    assert sha(idxpath) == accepted["index_sha256"]
    (out / "source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verified = {"at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS_CORE_COMPILE_RUN_ARTIFACTS_FULL_GIT_PATH_CONTENTS_AND_PROBE_WIP_BOUNDARY",
                "source_sha": source, "id": plan["id"], "index_sha256": sha(idxpath), "QA_sha256": sha(qapath),
                "main_acceptance_sha256": sha(acceptedpath), "indexed_artifacts_hashed": 90, "raw_files_hashed": 41, "old_artifacts_preserved": 5,
                "literature_sources_hashed": 4, "git_file_paths_hashed": 4845, "git_path_payload_bytes_hashed": total,
                "git_count_scope": "File paths, not unique Git objects; per-path blob ID, mode, length and SHA256 verified",
                "binary_bytes": 50520, "binary_sha256": sha(binary), "binary_executed_by_Integration": False,
                "exact_compile_argv": compiled["argv"], "exact_stdout": plan["run"]["expected_stdout"], "counts": counts,
                "real_endpoint_snapshots": 0, "manual_completed_generations": 2, "manual_closed_tokens": 6,
                "library_evidence": "Five saved ldd resolution/remote hash receipts; local library bytes and proc maps not independently sampled",
                "compile_max_rss_kib": compiled["rusage"]["max_rss_kib"], "run_max_rss_kib": run["rusage"]["max_rss_kib"],
                "guards_released": release["at_utc"], "no_persistent_driver_recorded": release["no_persistent_driver"],
                "checker_repair_only_absolute_roots_and_noop_expression": True, "raw_source_or_experiment_repeated_for_checker_repair": False,
                "next_probe_review_plan_sha256": sha(nxtpath), "probe_WIP_hashes": nxt["files_working_sha256"],
                "tracked_WIP_change": "qbb-net-device.h adds narrow friend/comment only", "untracked_probe": probe,
                "old_two_core_inputs_unchanged": True, "probe_runtime_compile_or_measurement_accepted": False,
                "GetBytesLeft_IRN_state_mutation_source_confirmed": True, "probe_missing_SWITCH_STATE_deliberately_cannot_certify_ALL": True,
                "next_scope": "Sole independent local read-only review after idle98; no remote or execution authority; two WIP files held unchanged",
                "network_technical_total": 43, "nonnetwork_adapter_conditions": 17, "new_combined_baseline": False,
                "Integration_remote_actions_CXX_builds_or_tests": 0, "manifest_entries": len(manifest),
                "remaining": idx["remaining_required"]}
    (out / "verification.json").write_text(json.dumps(verified, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return verified


if __name__ == "__main__":
    out = Path(__file__).resolve().parent
    if (out / "verification.json").exists() or (out / "source-manifest.json").exists():
        raise RuntimeError("Refusing to overwrite Integration receipt")
    result = audit(Path.cwd(), out)
    print(json.dumps({k: result[k] for k in ["status", "indexed_artifacts_hashed", "raw_files_hashed", "git_file_paths_hashed", "git_path_payload_bytes_hashed", "binary_bytes"]}))
