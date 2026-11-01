"""Local Integration source/provenance/default-network regression audit.

The two new logs and their frozen references are streamed once for this new
regression. No main verifier, build, fixture, simulator or remote tool is run.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import subprocess


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


EVENTS = ["WS30_CHOICE", "WS30_ROUTE", "WS31_C2_DEMAND", "WS31_C2_LAUNCH",
          "WS31_C2_FINISH", "WS31_C2_STATE"]


def wait_for(sip, dip, sport, dport, tag):
    if tag != 2:
        return 0
    h = 2166136261 ^ 0x43c2a517
    for word in [sip, dip, sport | (dport << 16)]:
        for j in range(4):
            h = ((h ^ ((word >> (8*j)) & 255)) * 16777619) & 0xffffffff
    h ^= h >> 16
    h = (h * 0x85ebca6b) & 0xffffffff
    h ^= h >> 13
    return h % 501


def verify(root, out):
    ind = root / "docs/research/ws31/independent"
    main = ind.parent / "main"
    pre = "adapter-default-validation-r1"
    idxpath, qapath = ind / (pre + "-index.json"), ind / (pre + "-qa.json")
    idx, qa = read(idxpath), read(qapath)
    reportpath = main / "evidence/adapter-default-pilot-main-acceptance-r1.json"
    report = read(reportpath)
    planpath = main / (pre + ".json")
    plan = read(planpath)
    source = "1f917f44fcfb88e61f3ad22c5cc75fa3a06b6c0e"
    assert sha(idxpath) == qa["index_sha256"] == report["index_sha256"] == "0708039efabeabc4f06c9b42871ac96e9162b514f3e59b6b2026ee61d3d9caef"
    assert sha(qapath) == report["QA_sha256"] == "b119d3c636388b057a30a96060fc5deaf535f8ada0f27f76c64cbdfad9b9f1b9"
    assert sha(planpath) == idx["plan_sha256"] == report["plan_sha256"] == "01665606c32d7422b92f4202d23e8e571500321631ca376b5924ed67f5e7eb68"
    assert idx["source_sha"] == report["source_sha"] == plan["source_sha"] == source
    assert qa["status"] == "PASS_TWO_DEFAULT_COMPATIBILITY_EXECUTOR_DELIVERY"
    assert report["status"] == "MAIN_ACCEPTED_TWO_DEFAULT_DISPATCH_NETWORK_CELLS_AND_FINAL_DELIVERY"
    assert [c["id"] for c in idx["cells"]] == [c["id"] for c in plan["cells"]]
    manifest, files = {}, Counter()

    def capture(path, name, expected=None):
        h, size = sha(path), path.stat().st_size
        if expected is not None:
            assert h == (expected["sha256"] if isinstance(expected, dict) else expected), str(path)
            if isinstance(expected, dict):
                assert size == expected["bytes"], str(path)
        # Keep bulk packet/connection/uplink logs in the original result store.
        freeze = size <= 500000
        relative = "snapshots/" + name if freeze else None
        if freeze:
            dest = out / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                assert sha(dest) == h
            else:
                dest.write_bytes(path.read_bytes())
        manifest[name] = {"source_path": str(path.resolve()), "bytes": size,
                          "sha256": h, "snapshot": relative}

    for group in ["documents", "dependencies", "immutable_reference_files"]:
        for n, (rel, info) in enumerate(idx[group].items()):
            path = Path(rel) if group == "immutable_reference_files" else ind / rel
            name = "references/" + str(n+1) + "-" + path.name if group == "immutable_reference_files" else "independent/" + rel
            capture(path, name, info)
        files[group] = len(idx[group])
    assert idx["immutable_reference_files"] == read(ind / (pre + "-reference-integrity-before.json")) == read(ind / (pre + "-reference-integrity-after.json"))
    capture(idxpath, "independent/" + idxpath.name)
    capture(qapath, "independent/" + qapath.name)
    refs = read(ind / (pre + "-reference-review.json"))
    for n, (path, h) in enumerate(refs["sources"].items()):
        capture(Path(path), "literature/" + str(n+1) + "-" + Path(path).name, h)
    files["literature_sources"] = len(refs["sources"])
    main_files = ["adapter-default-node13-handoff.md", "adapter-default-validation-r1.json",
                  "adapter-default-validation-r1.md", "evidence/adapter-default-pilot-main-acceptance-r1.json",
                  "evidence/adapter-default-q12-main-acceptance-r1.json", "evidence/adapter-default-c2-main-acceptance-r1.json",
                  "evidence/adapter-default-verifier-preparation-r1.json", "scripts/verify_adapter_default_raw_r1.py",
                  "scripts/verify_adapter_default_delivery_r1.py", "endpoint-ledger-local-review-r1.json",
                  "evidence/endpoint-ledger-wip-source-audit-r1.json"]
    for rel in main_files:
        capture(main / rel, "main/" + rel)
    prep = read(main / "evidence/adapter-default-verifier-preparation-r1.json")
    assert sha(main / "scripts/verify_adapter_default_raw_r1.py") == prep["script_sha256"]
    assert sha(planpath) == prep["plan_sha256"]
    output, maps, blobs, build_times, run_times = [], 0, {}, [], []
    for cell, planned, accepted in zip(idx["cells"], plan["cells"], report["cells"]):
        label = "q12" if cell["lb"] == "ws30v13-q12" else "c2"
        base = Path(cell["results_path"])
        assert cell["id"] == planned["id"] == accepted["id"]
        folder = ind / (pre + "-evidence") / cell["id"]
        assert base.resolve() == (folder / "results").resolve()
        for rel, info in cell["supporting_files"].items():
            capture(folder / rel, label + "/support/" + rel, info)
            files["support_files"] += 1
        for rel, info in cell["result_files"].items():
            capture(base / rel, label + "/results/" + rel, info)
            files["result_files"] += 1
        remote = read(folder / "remote-manifest.json")
        assert remote["source_head"] == source and remote["source_hashes"] == cell["source_hashes"]
        assert remote["files"] == cell["result_files"] and remote["binary_sha256"] == cell["binary_sha256"]
        for rel, h in cell["source_hashes"].items():
            assert rel not in blobs or blobs[rel] == h
            blobs[rel] = h
            maps += 1
        meta = read(base / "metadata.json")
        assert meta["status"] == "SUCCEEDED" and meta["git_commit"] == source and meta["experiment_id"] == cell["id"]
        assert meta["algorithm"] == cell["lb"] and meta["cpu_jobs"] == 2 and meta["build_mode"] == "optimized"
        assert meta["git_repository"] == "https://github.com/LarryBUPT/conweave-ns3.git" and meta["concurrency_cap"] == 1
        for k, v in plan["common"].items():
            if k != "max_concurrent":
                assert meta["parameters"][k] == v
        assert all(meta["parameters"].get(k, 0) == 0 for k in ["ws30_tag_transform", "ws30_composition", "ws30_lifecycle", "ws30_life_profile", "ws31_label_profile"])
        config = {s.split()[0]: s.split()[1:] for s in (base / "config/config.txt").read_text(encoding="ascii").splitlines() if s.strip()}
        for k, v in {"LB_MODE": [str(planned["lb_mode"])], "CC_MODE": ["1"], "ENABLE_PFC": ["0"], "ENABLE_IRN": ["1"], "RANDOM_SEED": ["1"], "PACKET_PAYLOAD_SIZE": ["1000"], "BUFFER_SIZE": ["9"], "LINK_DOWN": ["0", "0", "0"]}.items():
            assert config[k] == v
        assert float(config["ERROR_RATE_PER_LINK"][0]) == 0
        assert sha(base / "config/traffic_trace.txt") == plan["inputs"]["config/ws31_correctness_r1.txt"]
        assert sha(base / "config/topology.txt") == plan["inputs"]["config/leaf_spine_128_100G_OS2.txt"]
        trace = (base / "config/traffic_trace.txt").read_text().splitlines()
        expected, ids = {}, {}
        sports, dports = defaultdict(lambda: 10000), defaultdict(lambda: 100)
        for i, line in enumerate(trace[1:]):
            src, dst, pg, size, origin, tag = line.split()
            src, dst = int(src), int(dst)
            key = src, dst, sports[src], dports[dst]
            expected[key] = int(size), int(Fraction.from_float(float(origin)) * 10**9), int(tag)
            ids[i] = key
            sports[src] += 1
            dports[dst] += 1
        assert len(expected) == int(trace[0]) == 104
        fct = next((base / "raw").glob("*/*_out_fct.txt"))
        log = next((base / "raw").glob("*/config.log"))
        complete = {}
        for line in fct.read_text().splitlines():
            row = tuple(map(int, line.split()))
            assert len(row) == 8 and row[:4] in expected and row[:4] not in complete
            assert row[4:6] == expected[row[:4]][:2] and row[6] >= 0 and row[7] > 0
            complete[row[:4]] = row
        assert set(complete) == set(expected) and sum(v[4] for v in complete.values()) == 201981952
        assert sha(fct) == cell["fct_sha256"] == accepted["fct_sha256"] == planned["reference_fct_sha256"]
        assert sha(log) == cell["log_sha256"] == accepted["log_sha256"]
        hashes = {p: hashlib.sha256() for p in EVENTS}
        counts, summaries, ports, c2, qps = Counter(), {}, {}, {p: {} for p in ["DEMAND", "LAUNCH", "FINISH"]}, {}
        with log.open(encoding="utf-8") as stream:
            for line in stream:
                assert "WS30_OBSERVATION_OVERFLOW" not in line
                assert not line.startswith(("WS31_LABEL_", "WS31_SWITCH_BOUNDARY", "WS31_C2_BOUNDARY", "WS31_C1_", "WS31_C3_"))
                if not line.startswith(("WS30_", "WS31_")):
                    continue
                tokens = line.split()
                prefix = tokens[0]
                counts[prefix] += 1
                fields = dict(t.split("=", 1) for t in tokens[1:] if "=" in t)
                if prefix in hashes:
                    hashes[prefix].update((" ".join(t for t in tokens if not t.startswith("uid=")) + "\n").encode())
                v = {k: int(x) for k, x in fields.items()}
                if prefix in ["WS30_ROUTE", "WS30_CHOICE"]:
                    key = ((v["sip"] >> 8) & 65535, (v["dip"] >> 8) & 65535, v["sport"], v["dport"])
                    assert key in expected
                    if prefix == "WS30_ROUTE":
                        assert v["tag"] == expected[key][2]
                        assert ports.setdefault((v["switch"], key), v["port"]) == v["port"]
                    else:
                        assert v["tag"] == 0 and v["chosen"] == (v["first"] if v["q1"] <= v["q2"] else v["second"])
                if prefix.startswith("WS31_C2_"):
                    assert label == "c2"
                    suffix = prefix[len("WS31_C2_"):]
                    if suffix in c2:
                        assert v["flow_id"] not in c2[suffix]
                        c2[suffix][v["flow_id"]] = v
                if prefix == "WS30_QP":
                    assert v["flow_id"] not in qps and v["tag"] == expected[ids[v["flow_id"]]][2]
                    qps[v["flow_id"]] = v
                if prefix in ["WS30_QUEUE", "WS30_PATH", "WS31_C2_STATE"]:
                    assert prefix not in summaries
                    summaries[prefix] = v
        assert set(qps) == set(ids) and counts["WS30_CHOICE"] == 312 and counts["WS30_ROUTE"] == 606168
        assert len(ports) == summaries["WS30_PATH"]["switch_qps"] == 312
        assert all(summaries["WS30_PATH"][k] == 0 for k in ["changed_qps", "port_changes", "rejected"])
        assert summaries["WS30_QUEUE"]["enqueued"] == summaries["WS30_QUEUE"]["dequeued"] == 671412000
        assert all(summaries["WS30_QUEUE"][k] == 0 for k in ["current", "dropped", "admission_dropped_bytes", "queue_rejected_bytes", "violations"])
        waits = []
        if label == "c2":
            assert all(set(rows) == set(ids) for rows in c2.values())
            for i, key in ids.items():
                size, origin, tag = expected[key]
                sip, dip = (11 << 24) | (key[0] << 8) | 1, (11 << 24) | (key[1] << 8) | 1
                wait = wait_for(sip, dip, key[2], key[3], tag)
                demand, launch, finish = [c2[p][i] for p in ["DEMAND", "LAUNCH", "FINISH"]]
                assert demand["demand_ns"] == origin and demand["size"] == size and demand["tag"] == demand["policy_tag"] == tag
                assert demand["delay_ns"] == wait and demand["tag_transform"] == 0
                assert launch["demand_ns"] == origin and launch["launch_ns"] == origin + wait and launch["wait_ns"] == wait and launch["size"] == size
                row = complete[key]
                assert finish["demand_ns"] == origin and finish["launch_ns"] == origin + wait and finish["wait_ns"] == wait
                assert finish["finish_ns"] == origin + row[6] and finish["fct_ns"] == row[6] and finish["size"] == size
                waits.append(wait)
            assert sum(x > 0 for x in waits) == 80 and sum(waits) == 18002 and max(waits) == 497
            assert summaries["WS31_C2_STATE"] == {k: int(v) for k, v in accepted["summaries"]["WS31_C2_STATE"].items()}
        else:
            assert not any(counts[p] for p in EVENTS if p.startswith("WS31_C2_"))
        ref = Path(cell["reference_results"])
        rmeta = read(ref / "metadata.json")
        assert rmeta["git_commit"] == cell["reference_sha"] == planned["reference_sha"] and rmeta["experiment_id"] == planned["reference_id"]
        assert rmeta["status"] == "SUCCEEDED" and rmeta["algorithm"] == cell["lb"]
        rlog, rfct = next((ref / "raw").glob("*/config.log")), next((ref / "raw").glob("*/*_out_fct.txt"))
        assert sha(rfct) == sha(fct) and sha(rlog) == planned["reference_log_sha256"]
        reference_hashes, reference_counts = {p: hashlib.sha256() for p in EVENTS}, Counter()
        with rlog.open(encoding="utf-8") as stream:
            for line in stream:
                prefix = line.split(" ", 1)[0]
                if prefix in reference_hashes:
                    reference_hashes[prefix].update((" ".join(t for t in line.split() if not t.startswith("uid=")) + "\n").encode())
                    reference_counts[prefix] += 1
        assert all(hashes[p].hexdigest() == reference_hashes[p].hexdigest() and counts[p] == reference_counts[p] for p in EVENTS)
        for p, h in accepted["ordered_normalized_hashes"].items():
            assert hashes[p].hexdigest() == h
        build_times.append(meta["build_finished_utc"])
        run_times.append((meta["started_utc"], meta["finished_utc"]))
        build = (base / "logs/build.log").read_text(encoding="utf-8")
        assert max(int(y) for x, y in re.findall(r"\[\s*(\d+)\s*/\s*(\d+)\s*\]", build)) == 1468
        assert len(re.findall(r"'build' finished successfully", build)) == 1
        output.append({"id": cell["id"], "lb": cell["lb"], "reference_id": cell["reference_id"], "reference_source": cell["reference_sha"], "flows": 104, "payload_bytes": 201981952,
                       "fct_sha256": sha(fct), "whole_FCT_equal": True, "ordered_events_remove_uid_only_equal": EVENTS,
                       "ordered_event_counts": {p: counts[p] for p in EVENTS}, "ordered_event_hashes": {p: h.hexdigest() for p, h in hashes.items()},
                       "exact_C2_waits_recomputed": 104 if label == "c2" else 0,
                       "C2_wait_summary": {"positive": 80, "sum_ns": 18002, "max_ns": 497} if waits else None})
    assert maps == 84 and len(blobs) == 42
    impl = root.parent / "ws31-candidates-implementation"
    git = lambda *args: subprocess.check_output(["git", "-C", str(impl), *args])
    prior = read(root / "docs/research/evidence/ws31-adapter-boundary-integration-20261101-r1/snapshots/independent/adapter-boundary-preflight-r2-index.json")
    assert blobs == prior["source_hashes"]
    for rel, h in blobs.items():
        assert hashlib.sha256(git("show", source + ":" + rel)).hexdigest() == h
    tree = git("ls-tree", "-r", source)
    assert len(tree.splitlines()) == 4843 and tree == (ind / (pre + "-source-git-tree.txt")).read_bytes()
    assert git("rev-parse", "HEAD").decode().strip() == source
    assert git("rev-parse", "refs/remotes/origin/feature/ws31-candidates").decode().strip() == source
    worktree = git("status", "--porcelain", "-uall").decode().splitlines()
    wip = {}
    for line in worktree:
        assert line.startswith("?? "), line
        path = line[3:]
        wip[path] = sha(impl / path)
    assert set(wip) == {"src/point-to-point/model/ws31-endpoint-ledger.h", "tests/ws31_endpoint_ledger_test.cc"}
    frozen_wip = read(main / "evidence/endpoint-ledger-wip-source-audit-r1.json")
    # The implementation owner may revise this untracked WIP after its snapshot.
    wip_matches = wip == frozen_wip["files_working_bytes_sha256"]
    receipt = read(ind / (pre + "-receipt.json"))
    assert receipt["status"] == "COMPLETE_FOR_TWO_DEFAULT_DISPATCH_NETWORK_COMPATIBILITY_CELLS_ONLY"
    assert receipt["build_commands"] == receipt["network_runs_started"] == 2
    for k in ["sync_commands", "deploy_commands", "core_commands", "fixture_commands", "reference_runs"]:
        assert receipt[k] == 0
    builds = [c for c in receipt["commands"] if c["operation"] == "guarded-build"]
    runs = [c for c in receipt["commands"] if c["operation"] == "guarded-run"]
    assert len(builds) == len(runs) == 2 and all(c["exit_code"] == 0 for c in builds + runs)
    assert [c["cell"] for c in runs] == [c["id"] for c in plan["cells"]]
    assert max(c["end_utc"] for c in builds) <= runs[0]["start_utc"] and runs[0]["end_utc"] <= runs[1]["start_utc"]
    assert max(build_times) <= min(t[0] for t in run_times) and run_times[0][1] <= run_times[1][0]
    release = read(ind / (pre + "-guards-released.json"))
    assert release["status"] == "RELEASED" and release["network_calls_terminal"] == release["fixed_source_copies"] == 2
    sample_path = next(Path(idx["cells"][0]["results_path"]).glob("logs/resource-build-batch-samples.jsonl"))
    samples = [json.loads(line) for line in sample_path.read_text(encoding="utf-8").splitlines()]
    assert len(samples) == 79
    assert max(x["cc1plus_count_sample"] for x in samples) == 4 and max(x["loadavg"][0] for x in samples) == 4.07
    assert min(x["available_gib"] for x in samples) == idx["resources"]["min_sampled_available_gib"]
    assert not any(x["unknown_project_pids"] or x["other_user_pids"] for x in samples)
    assert files == {"documents": 26, "dependencies": 5, "immutable_reference_files": 12, "literature_sources": 4, "support_files": 22, "result_files": 52}
    assert sha(idxpath) == report["index_sha256"] and sha(qapath) == report["QA_sha256"]
    (out / "source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {"at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS_NEW_DEFAULT_FCT_EVENTS_ORIGINAL_TIMING_EXACT_WAITS_AND_PROVENANCE", "source_sha": source,
              "index_sha256": sha(idxpath), "QA_sha256": sha(qapath), "main_acceptance_sha256": sha(reportpath), "files_hashed": dict(files),
              "source_map_entries": 84, "unique_git_objects": 42, "fixed_tree_entries": 4843, "source_objects_match_node12": True,
              "completed_records": 208, "completed_payload_bytes": 403963904, "cells": output,
              "two_builds_before_serial_Q12_C2": True, "each_build_tasks": 1468, "resources": idx["resources"],
              "sync_deploy_old_core_fixture_reference_repeats": [0, 0, 0, 0, 0], "all_default_guards_explicitly_released": release,
              "worktree_untracked_WIP_observed": wip, "WIP_matches_main_earlier_snapshot": wip_matches,
              "WIP_inherits_1f_acceptance": False, "endpoint_execution_or_generation_proof": False,
              "main_packet_payload_reconstruction_owner": "WS31 main; Integration checks complete FCT identity/bytes/timing, actual labels/pinning/direct queue choices and whole ordered reference equality",
              "new_network_technical_cells": 2, "cumulative_network_technical_cells": 43, "nonnetwork_adapter_conditions_separate": 17,
              "new_independent_efficacy_or_combined_baseline": False, "Integration_remote_build_fixture_simulator_or_main_verifier_execution": 0,
              "large_raw_store_policy": "All indexed files hashed; files over500000B remain at original local paths, with hashes in source-manifest",
              "remaining": ["Actual endpoint retirement/drain/generation/tuple reuse implementation and validation", "Independent C1 V0", "Three candidates business/background effects and state/runtime costs"]}
    (out / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    out = Path(__file__).resolve().parent
    if (out / "verification.json").exists() or (out / "source-manifest.json").exists():
        raise RuntimeError("Refusing to overwrite Integration acceptance")
    result = verify(Path.cwd(), out)
    print(json.dumps({k: result[k] for k in ["status", "files_hashed", "completed_records", "completed_payload_bytes", "cumulative_network_technical_cells", "WIP_matches_main_earlier_snapshot"]}))
