#!/usr/bin/env python3
"""Read-only, paired WS-19 counterexample audit for the WS-20 gate review."""
import collections
import hashlib
import json
import subprocess
from pathlib import Path

from analyze_ws19_pilot import host_tors, percentile


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SUMMARY = ROOT / "docs/research/evidence/ws19-pilot-analysis.json"
OUTPUT = ROOT / "docs/research/evidence/ws20-counterexample-audit.json"
SOURCE_SHA = "b52e66f0fbf786fb57672b12a5633cf45b9311c1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(cell):
    base = RESULTS / cell["id"]
    meta = json.loads((base / "metadata.json").read_text(encoding="utf-8"))
    assert meta["status"] == "SUCCEEDED" and meta["git_commit"] == SOURCE_SHA
    assert str(meta["raw_directory"]) == str(cell["raw_id"])
    raw = base / "raw" / str(cell["raw_id"])
    timing_file = raw / (str(cell["raw_id"]) + "_out_ws18.txt")
    assert digest(timing_file) == cell["raw_sha256"]["timing"]
    rows = {}
    for line in timing_file.read_text(encoding="utf-8").splitlines():
        values = list(map(int, line.split()))
        assert len(values) == 12 and values[0] not in rows
        assert values[7] <= values[8] <= values[9]
        rows[values[0]] = values
    assert len(rows) == 16576
    return raw, rows


def round_tails(rows):
    moe = [row for row in rows.values() if row[5] == 2]
    origin = min(row[7] for row in moe)
    rounds = collections.defaultdict(list)
    for row in moe:
        number, offset = divmod(row[7] - origin, 50000)
        assert offset == 0 and 0 <= number < 8
        rounds[number].append(row)
    assert len(rounds) == 8 and all(len(rows) == 2048 for rows in rounds.values())
    return [{"round": number, "flow_id": max(rounds[number], key=lambda row: (row[9], -row[0]))[0],
             "round_us": (max(row[9] for row in rounds[number]) - origin - number * 50000) / 1000}
            for number in range(8)]


def hops(raw):
    matched = subprocess.run(["rg", "^WS13_HOP ", str(raw / "config.log")],
                             capture_output=True, text=True, check=True,
                             encoding="utf-8", errors="replace")
    by_qp = collections.defaultdict(list)
    for line in matched.stdout.splitlines():
        fields = dict(token.split("=", 1) for token in line.split()[1:])
        item = {key: int(value) for key, value in fields.items()}
        key = tuple(item[k] for k in ("src", "dst", "sport", "dport"))
        by_qp[key].append(item)
    assert len(by_qp) == 192
    return by_qp


def row_data(row):
    return {"flow_id": row[0], "total_us": row[11] / 1000,
            "wait_us": row[10] / 1000, "network_us": (row[9] - row[8]) / 1000,
            "demand_ns": row[7], "release_ns": row[8], "finish_ns": row[9]}


def main():
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["source_sha"] == SOURCE_SHA
    cells = {(c["seed"], c["hotspot"], c["background"], c["arm"]): c
             for c in summary["cells"]}
    tors, host_ports = host_tors()
    output = {"role": "read-only post-WS19 descriptive audit; no new simulation",
              "source_sha": SOURCE_SHA, "source_summary_sha256": digest(SUMMARY),
              "independent_demand_seeds": [20261701, 20261702, 20261703],
              "hotspot": "tor_hotspot", "background_flows": 192, "seeds": []}
    for seed in output["independent_demand_seeds"]:
        cell = {arm: cells[(seed, "tor_hotspot", 192, arm)]
                for arm in ("ecmp", "admission", "path", "joint")}
        loaded = {arm: load(c) for arm, c in cell.items()}
        rows = {arm: item[1] for arm, item in loaded.items()}
        e, j = rows["ecmp"], rows["joint"]
        tail = {arm: round_tails(rows[arm]) for arm in rows}
        round_pairs = []
        for number in range(8):
            e_id = tail["ecmp"][number]["flow_id"]
            j_id = tail["joint"][number]["flow_id"]
            round_pairs.append({"round": number, "ecmp_tail_id": e_id,
                                "joint_tail_id": j_id, "same_tail": e_id == j_id,
                                "ecmp_round_us": tail["ecmp"][number]["round_us"],
                                "joint_round_us": tail["joint"][number]["round_us"],
                                "joint_tail": row_data(j[j_id]),
                                "same_joint_tail_in_ecmp": row_data(e[j_id]),
                                "same_ecmp_tail_in_joint": row_data(j[e_id])})
        e_bg = {fid: row for fid, row in e.items() if row[5] == 1}
        j_bg = {fid: row for fid, row in j.items() if row[5] == 1}
        assert set(e_bg) == set(j_bg) and len(e_bg) == 192
        e_hops, j_hops = hops(loaded["ecmp"][0]), hops(loaded["joint"][0])
        top_ids = (set(sorted(e_bg, key=lambda fid: (-e_bg[fid][11], fid))[:4]) |
                   set(sorted(j_bg, key=lambda fid: (-j_bg[fid][11], fid))[:4]))
        bg_tail = []
        for fid in sorted(top_ids):
            erow, jrow = e_bg[fid], j_bg[fid]
            qp = tuple(erow[k] for k in (1, 2, 3, 4))
            assert qp == tuple(jrow[k] for k in (1, 2, 3, 4))
            position = {}
            for arm, all_hops in (("ecmp", e_hops), ("joint", j_hops)):
                selected = all_hops[qp]
                source = [h for h in selected if h["switch"] == tors[qp[0]] and h["port"] > 8]
                final = [h for h in selected if h["switch"] == tors[qp[1]] and h["port"] == host_ports[qp[1]]]
                assert source and len(final) == 1
                position[arm] = {"source_uplink_wait_max_us": max(h["wait_ns_max"] for h in source) / 1000,
                                 "final_egress_wait_max_us": final[0]["wait_ns_max"] / 1000,
                                 "final_egress_queued_bytes_max": final[0]["queued_bytes_max"]}
            bg_tail.append({"flow_id": fid, "qp": qp, "ecmp_total_us": erow[11] / 1000,
                            "joint_total_us": jrow[11] / 1000,
                            "joint_minus_ecmp_us": (jrow[11] - erow[11]) / 1000,
                            "background_wait_us": jrow[10] / 1000, "position": position})
        output["seeds"].append({"seed": seed, "experiment_ids": {a: c["id"] for a, c in cell.items()},
                                "rounds": round_pairs,
                                "round_tail_identity_same_count": sum(r["same_tail"] for r in round_pairs),
                                "background_p99_us": {a: cell[a]["background_metrics"]["fct_p99_us"] for a in cell},
                                "background_p99_order_ecmp": sorted(e_bg, key=lambda fid: (-e_bg[fid][11], fid))[:4],
                                "background_p99_order_joint": sorted(j_bg, key=lambda fid: (-j_bg[fid][11], fid))[:4],
                                "background_top_union": bg_tail,
                                "background_joint_worse_count": sum(j_bg[fid][11] > e_bg[fid][11] for fid in e_bg),
                                "background_joint_better_count": sum(j_bg[fid][11] < e_bg[fid][11] for fid in e_bg),
                                "background_joint_equal_count": sum(j_bg[fid][11] == e_bg[fid][11] for fid in e_bg),
                                "background_p99_recomputed_us": {
                                    "ecmp": percentile([r[11] for r in e_bg.values()], 99) / 1000,
                                    "joint": percentile([r[11] for r in j_bg.values()], 99) / 1000}})
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(str(OUTPUT))


if __name__ == "__main__":
    main()
