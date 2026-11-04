"""Independent acceptance of new finite-screen artifacts from local old raw.

Reads two fixed old logs once each, verifies their bytes while checking the new
rows. No imported analysis entry, simulator, compiler or remote operation runs.
All writes belong to this new Integration receipt directory.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import tomllib


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def rows(p):
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def audit():
    out = Path(__file__).resolve().parent
    root = out.parents[3]
    m = root / "docs/research/ws31/main"
    impl = root.parent / "ws31-candidates-implementation"
    fixed = "c4b6039beb47e667e6954b56ec770cb6038082fa"
    git = lambda *args: subprocess.check_output(["git", "-C", str(impl), *args])
    manifest = {}

    def capture(p, name, expected=None):
        p = Path(p)
        assert p.resolve().is_relative_to(root.parent.parent.resolve())
        data = p.read_bytes()
        if expected:
            assert sha(data) == expected, str(p)
        dest = out / "snapshots" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            assert dest.read_bytes() == data
        else:
            dest.write_bytes(data)
        manifest[name] = {"source_path": str(p), "snapshot": "snapshots/" + name,
                          "bytes": len(data), "sha256": sha(data)}
        return data

    q = read(m / "evidence/review-finite-screen-main-qa-r1.json")
    c1 = read(m / "evidence/full-score-reference-screen-r1.json")
    c3 = read(m / "evidence/c3-source-interval-screen-r1.json")
    opportunity = read(m / "evidence/review-opportunity-screen-r1.json")
    assert q["fixed_source"] == c1["source_sha"] == c3["source_sha"] == opportunity["source_sha"] == fixed
    report = m / "review-finite-screen-and-demand-design-r1.md"
    capture(report, "main/" + report.name, q["report_sha256"])
    for name in ["review-opportunity-screen-r1.md", "current-status.json", "evidence/review-finite-screen-main-qa-r1.json",
                 "evidence/review-finite-screen-writing-audit-r1.json"]:
        capture(m / name, "main/" + name)
    input_hashes = {}
    for result, stem, script in [(c1, "full-score-reference-screen-r1", "audit_full_score_reference_r1.py"),
                                 (c3, "c3-source-interval-screen-r1", "audit_c3_source_intervals_r1.py")]:
        capture(m / "evidence" / (stem + ".json"), "main/evidence/" + stem + ".json")
        capture(m / "evidence" / (stem + ".csv"), "main/evidence/" + stem + ".csv", result["rows_csv_sha256"])
        capture(m / "scripts" / script, "main/scripts/" + script, result["script_sha256"])
        input_hashes.update(result.get("input_sha256", result.get("inputs_sha256", {})))
    input_hashes.update(opportunity["input_hashes"])
    capture(m / "evidence/review-opportunity-screen-r1.json", "main/evidence/review-opportunity-screen-r1.json")
    capture(m / "evidence/review-opportunity-screen-r1.csv", "main/evidence/review-opportunity-screen-r1.csv", opportunity["rows_csv_sha256"])
    raw_paths = [Path(p) for p in input_hashes if p.endswith("config.log")]
    assert len(raw_paths) == 2
    for value, expected in input_hashes.items():
        p = Path(value)
        if p not in raw_paths:
            capture(p, "support/" + expected[:16] + "-" + p.name, expected)
    for rel, expected in q["source_blob_sha256"].items():
        data = git("show", fixed + ":" + rel)
        assert sha(data) == expected
        p = out / "snapshots/fixed-source" / Path(rel).name
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            assert p.read_bytes() == data
        else:
            p.write_bytes(data)
        manifest["fixed-source/" + p.name] = {"source_git": fixed + ":" + rel,
            "snapshot": "snapshots/fixed-source/" + p.name, "sha256": expected, "bytes": len(data)}
    trace_path = next(Path(p) for p in c1["input_sha256"] if p.endswith("traffic_trace.txt"))
    flows, source_ports, dest_ports = {}, defaultdict(lambda: 10000), defaultdict(lambda: 100)
    for line in trace_path.read_text().splitlines()[1:]:
        src, dst, pg, size, time, tag = line.split()
        src, dst = int(src), int(dst)
        key = (src, dst, source_ports[src], dest_ports[dst])
        source_ports[src] += 1
        dest_ports[dst] += 1
        flows[key] = (int(size), int(tag))
    samples = [{k: int(v) if k in ["line", "time_ns", "switch", "src", "dst", "sport", "dport", "tag", "first", "second", "q1_wire", "q2_wire", "baseline_chosen"] else v for k, v in x.items()}
               for x in rows(m / "evidence/review-opportunity-screen-r1.csv")]
    by_line = {d["line"]: d for d in samples}
    by_key = {(d["src"], d["dst"], d["sport"], d["dport"]): d for d in samples}
    assert len(samples) == len(by_key) == len(flows) == 104
    actual_rows = {(int(d["line"]), d["variant"]): d for d in rows(m / "evidence/full-score-reference-screen-r1.csv")}
    old_rows = {(int(d["line"]), d["variant"]): d for d in rows(m / "evidence/v0-technical-replay-r1.csv")}
    assert len(actual_rows) == len(old_rows) == 416
    variants = ["class_progress", "class_count", "unified_progress", "unified_count"]
    observed_payload, next_seq = defaultdict(int), defaultdict(int)
    previous, selections, totals = [], {}, defaultdict(Counter)
    assignment_counts = Counter()
    ccb = ccpb = 0
    c1_route_count = 0
    raw_manifest = []
    c1log = next(p for p in raw_paths if "zero-control" in str(p))

    def fields(line):
        return {k: int(v) for k, v in (part.split("=", 1) for part in line.split()[1:])}

    def request(v):
        return ((v["sip"] >> 8) & 65535, (v["dip"] >> 8) & 65535, v["sport"], v["dport"])

    digest = hashlib.sha256()
    with c1log.open("rb") as f:
        for number, raw in enumerate(f):
            digest.update(raw)
            if number in by_line:
                assert raw.startswith(b"WS30_CHOICE ")
                v, d = fields(raw.decode()), by_line[number]
                key = request(v)
                assert by_key[key] is d and d["tag"] == flows[key][1]
                assert (v["time_ns"], v["switch"], v["first"], v["second"], v["q1"], v["q2"], v["chosen"]) == tuple(d[k] for k in ["time_ns", "switch", "first", "second", "q1_wire", "q2_wire", "baseline_chosen"])
                p1, p2, now = v["first"], v["second"], v["time_ns"]
                assert v["chosen"] == (p2 if v["q2"] < v["q1"] else p1)
                choices = {}
                for variant in variants:
                    pressures, payloads = defaultdict(int), defaultdict(int)
                    for prior_key, port, start, sw in previous:
                        if sw != v["switch"] or start + 20000 <= now:
                            continue
                        budget = 65536 if variant.startswith("class_") and flows[prior_key][1] == 1 else 8192
                        remain = max(0, budget - observed_payload[prior_key]) if variant.endswith("_progress") else budget
                        payloads[port] += remain
                        pressures[port] += remain + ((remain + 999) // 1000) * 48
                    a = actual_rows[(number, variant)]
                    old = old_rows[(number, variant)]
                    assert (payloads[p1], payloads[p2]) == (int(old["pred1_payload"]), int(old["pred2_payload"]))
                    score1, score2 = v["q1"] + pressures[p1], v["q2"] + pressures[p2]
                    chosen = p2 if score2 < score1 else p1
                    assert (pressures[p1], pressures[p2], score1, score2, chosen) == tuple(int(a[k]) for k in ["r1", "r2", "score1", "score2", "chosen"])
                    choices[variant] = chosen
                    totals[variant].update(decisions=1, nonzero_pressure=bool(pressures[p1] or pressures[p2]), different_from_reference=chosen != v["chosen"])
                selections[number] = choices
                before1 = assignment_counts[(v["switch"], d["tag"], p1)]
                before2 = assignment_counts[(v["switch"], d["tag"], p2)]
                assert (before1, before2) == (int(d["prior_same_class_assignments_first"]), int(d["prior_same_class_assignments_second"]))
                ccb += d["tag"] == 2 and p1 != p2 and 0 < v["q1"] - v["q2"] <= 8192
                ccpb += d["tag"] == 2 and p1 != p2 and v["q1"] == v["q2"] and before2 < before1
                assignment_counts[(v["switch"], d["tag"], v["chosen"])] += 1
                previous.append((key, v["chosen"], now, v["switch"]))
            if raw.startswith(b"WS30_ROUTE "):
                v = fields(raw.decode()); key = request(v)
                if v["switch"] != by_key[key]["switch"]:
                    continue
                assert v["tag"] == flows[key][1] and v["port"] == by_key[key]["baseline_chosen"]
                assert v["seq"] == next_seq[key], "Specific old trace must have contiguous first-seen source segments"
                length = min(1000, flows[key][0] - v["seq"])
                assert length > 0
                next_seq[key] += length
                observed_payload[key] += length
                c1_route_count += 1
    assert digest.hexdigest() == input_hashes[str(c1log)]
    raw_manifest.append({"path": str(c1log), "sha256": digest.hexdigest(), "bytes": c1log.stat().st_size})
    assert len(previous) == 104 and c1_route_count == 202056
    assert all(observed_payload[k] == size for k, (size, tag) in flows.items())
    assert {k: dict(v) for k, v in totals.items()} == c1["totals"]
    for name, expected in c1["contrasts"].items():
        a, b = name.split("_vs_")
        lines = [n for n, x in selections.items() if x[a] != x[b]]
        assert lines == expected["reference_lines"] and len(lines) == expected["different_decisions"]
    assert (ccb, ccpb) == (9, 3)

    c3log = next(p for p in raw_paths if "main-mode-dynamic" in str(p))
    topo = next(Path(p) for p in c3["inputs_sha256"] if p.endswith("topology.txt"))
    content = topo.read_text().splitlines(); switches = set(map(int, content[1].split())); host_to_tor = {}
    for line in content[2:2 + int(content[0].split()[2])]:
        u, v = map(int, line.split()[:2])
        if u not in switches and v in switches: host_to_tor[u] = v
        if v not in switches and u in switches: host_to_tor[v] = u
    assignments, pending_sides, last, serial, epochs = {}, {}, {}, Counter(), {}
    groups = {}; route_count = 0; digest = hashlib.sha256()
    with c3log.open("rb") as f:
        for raw in f:
            digest.update(raw)
            if not raw.startswith((b"WS31_C3_ROUTE ", b"WS30_ROUTE ")):
                continue
            v = fields(raw.decode()); key = request(v)
            if v["switch"] != host_to_tor[key[0]]: continue
            side_key = (key, v["time_ns"], v["seq"])
            if raw.startswith(b"WS31_C3_ROUTE "):
                assert side_key not in pending_sides
                pending_sides[side_key] = v
                if v["fresh"]:
                    assert key not in assignments
                    assignments[key] = v
                continue
            route_count += 1
            assignment = assignments[key]
            category, owner, sw, now = assignment["category"], assignment["owner"], v["switch"], v["time_ns"]
            assert category == flows[key][1] == v["tag"] and assignment["chosen"] == v["port"]
            if category:
                cat = (sw, category)
                if cat not in last or now - last[cat] >= 20000:
                    serial[cat] += 1
                    epochs[(sw, category, serial[cat])] = {"switch": sw, "owner": category, "activation_id": serial[cat], "activation_ns": now, "last_owner_arrival_ns": now}
                last[cat] = now
                epochs[(sw, category, serial[cat])]["last_owner_arrival_ns"] = now
            active = bool(assignment["borrowed"] and (sw, owner) in last and now - last[(sw, owner)] < 20000)
            side = pending_sides.pop(side_key, None)
            if side is not None: assert bool(side["residual"]) == active
            if not active: continue
            assert side is not None
            wire = min(1000, flows[key][0] - v["seq"]) + 48
            assert wire == side["wire_bytes"]
            epoch = (sw, owner, serial[(sw, owner)])
            group_key = (*epoch, key)
            if group_key not in groups:
                groups[group_key] = {"switch": sw, "port": assignment["chosen"], "owner": owner, "activation_id": epoch[2],
                    "activation_ns": epochs[epoch]["activation_ns"], "borrower_src": key[0], "borrower_dst": key[1], "borrower_sport": key[2], "borrower_dport": key[3],
                    "first_residual_source_arrival_ns": now, "last_residual_source_arrival_ns": now, "residual_packets": 0, "residual_wire_bytes": 0}
            g = groups[group_key]; g["last_residual_source_arrival_ns"] = now; g["residual_packets"] += 1; g["residual_wire_bytes"] += wire
    assert not pending_sides and len(assignments) == 104 and route_count == 202056
    assert digest.hexdigest() == input_hashes[str(c3log)]
    raw_manifest.append({"path": str(c3log), "sha256": digest.hexdigest(), "bytes": c3log.stat().st_size})
    for group_key, g in groups.items():
        g["observed_span_ns"] = g["last_residual_source_arrival_ns"] - g["first_residual_source_arrival_ns"]
        g["last_residual_minus_activation_ns"] = g["last_residual_source_arrival_ns"] - g["activation_ns"]
        g["owner_activity_lease_end_ns"] = epochs[group_key[:3]]["last_owner_arrival_ns"] + 20000
    parsed = [{k: int(v) for k, v in row.items()} for row in rows(m / "evidence/c3-source-interval-screen-r1.csv")]
    sort_key = lambda d: (d["switch"], d["owner"], d["activation_id"], d["port"], d["borrower_sport"])
    assert sorted(groups.values(), key=sort_key) == sorted(parsed, key=sort_key)
    assert list(epochs.values()) == c3["owner_activation_episodes"]
    assert len(groups) == 7 and sum(x["borrowed"] for x in assignments.values()) == 4
    assert sum(x["residual_packets"] for x in parsed) == c3["residual_packets"] == 546
    assert sum(x["residual_wire_bytes"] for x in parsed) == c3["residual_wire_bytes"] == 572208
    assert max(x["observed_span_ns"] for x in parsed) == c3["max_observed_span_ns"] == 24507
    assert not c3["physical_recovery_duration_observable"]
    wip = read(root / "docs/research/evidence/ws31-review-rescope-integration-20261104-r1/verification.json")["current_WIP_hashes"]
    assert len(wip) == 19 and {line[3:] for line in git("status", "--porcelain", "-uall").decode().splitlines()} == set(wip)
    assert all(sha((impl / p).read_bytes()) == expected for p, expected in wip.items())
    assert git("rev-parse", "HEAD").decode().strip() == "8cd1ba69469bf80143d5c89edc17fa72611018e8"
    state = read(m / "current-status.json")
    assert state["planned_next_goal"]["status"] == "HOLD_CURRENT_SCOPE_FINITE_SCREEN_COMPLETE_NO_AUTOMATIC_CONTINUATION"
    live = Path("C:/Users/Administrator/.codex/automations/ws-31/automation.toml").read_bytes()
    (out / "automation-after.toml").write_bytes(live)
    before = tomllib.loads((out / "automation-before.toml").read_text(encoding="utf-8")); after = tomllib.loads(live.decode())
    assert all(after[k] == before[k] for k in before if k not in ["prompt", "updated_at"])
    assert after["prompt"].endswith(before["prompt"]) and after["prompt"].startswith("当前优先状态为 HOLD_CURRENT_SCOPE_FINITE_SCREEN_COMPLETE_NO_AUTOMATIC_CONTINUATION")
    result = {"at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS_NEW_FINITE_SCREEN_RAW_ACCEPTANCE_AND_HOLD_SCOPE",
        "fixed_analysis_source": fixed, "fixed_source_blobs_hashed": 4, "raw_logs_streamed_once_each": raw_manifest,
        "C1": {"decisions": 104, "rows_verified": 416, "prior_payload_rows_verified": 416, "source_arrivals": c1_route_count,
               "totals": c1["totals"], "contrasts": c1["contrasts"], "prior_CCB_changes": ccb, "prior_CCPB_changes": ccpb,
               "trajectory": "All old Q, arrivals and assignments unchanged; no candidate feedback or dynamic counterfactual"},
        "C3": {"source_arrivals": route_count, "borrowers": 4, "groups": 7, "packets": 546, "wire_bytes": 572208,
               "max_source_arrival_span_ns": 24507, "activity": "Rolling last-arrival lease", "physical_recovery_duration_observable": False},
        "D1_D2": "Design only, no config/input/scientific code generation, run or future group information supplied online",
        "scientific_implementation_HEAD": "8cd1ba69469bf80143d5c89edc17fa72611018e8", "nineteen_science_WIP_unchanged": True,
        "main_observed_cursor": "f13c4cd1-6458-4d58-888a-76f78e636578:3", "sole_independent_last_reported_cursor": "d0b9dd1a-3dbb-4cea-9a35-6aefe1b3ed0d:14",
        "HOLD": "Finite screen complete; no automatic repetition or engineering continuation without new evidence/scope update",
        "heartbeat": {"status": after["status"], "rrule_unchanged": after["rrule"], "prompt_sha256": sha(after["prompt"].encode()), "live_saved_file_reloaded": True},
        "new_cpp_build_test_fixture_network_SSH_source_config": 0, "new_independent_V0_or_effect_or_combined_baseline": False,
        "unfinished_correctness_V0_ablations_dual_effects_costs": "Retained incomplete; engineering and remote paused",
        "acceptance_scope": "One necessary independent verification of newly delivered analysis, not a repeated main analysis entry or new simulator run"}
    for name, obj in [("source-manifest.json", manifest), ("verification.json", result)]:
        p = out / name; assert not p.exists(), "Do not overwrite successful receipts"
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "C1_rows": 416, "C3_groups": 7, "hold": True}))


if __name__ == "__main__":
    audit()
