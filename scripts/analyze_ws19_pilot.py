#!/usr/bin/env python3
"""Analyze WS-19 paired pilot cells from their downloaded raw results."""
import collections
import hashlib
import json
import math
import re
import statistics
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from verify_ws19_cell import verify

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SCHEDULE = ROOT / "docs/research/evidence/ws19-pilot-schedule-v1.json"
RUN_MAP = ROOT / "docs/research/evidence/ws19-pilot-run-map-v1.json"
RECEIPTS = RESULTS / "ws19-pilot-receipts.jsonl"
OUT = ROOT / "docs/research/evidence/ws19-pilot-analysis.json"
FIGURE = ROOT / "docs/research/evidence/ws19-pilot-tradeoff.svg"
SOURCE_SHA = "b52e66f0fbf786fb57672b12a5633cf45b9311c1"
PROTOCOL_SHA = "ade47b2c7c3f427a4756eb8e48634d329a7818280ca017ba8b28831057386dfc"
SCHEDULE_SHA = "6dda53c30ebaf7b5c537f50452e06376e938fe96de33c3b4f8d57aec769c7769"
ARMS = ("ecmp", "admission", "path", "joint")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values, percent):
    values = sorted(values)
    if not values:
        return None
    pos = (len(values) - 1) * percent / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def us(ns):
    return None if ns is None else round(ns / 1000, 6)


def fields(line):
    return dict(token.split("=", 1) for token in line.split()[1:] if "=" in token)


def host_tors():
    result = {}
    neighbors = collections.defaultdict(list)
    with (ROOT / "config/topo_1280_400G_400G_OS1.txt").open() as source:
        next(source)
        next(source)
        for line in source:
            left, right = map(int, line.split()[:2])
            neighbors[left].append(right)
            neighbors[right].append(left)
            if left < 1280:
                assert left not in result
                result[left] = right
            if right < 1280:
                assert right not in result
                result[right] = left
    assert len(result) == 1280
    # ns-3 device ports are one-based in WS13_HOP; links are installed in
    # topology-file order.
    return result, {host: neighbors[tor].index(host) + 1 for host, tor in result.items()}


def diagnostic(raw, raw_id, background, bg_keys, tors, host_ports):
    log = raw / "config.log"
    route = None
    with log.open(encoding="utf-8", errors="replace") as source:
        for line in source:
            if line.startswith("WS18_PATH "):
                route = {k: int(v) for k, v in fields(line).items()}
    assert route is not None
    result = {"path": route}
    if not background:
        return result
    # rg filters the large diagnostic log before Python parses the small
    # collection of background-hop summaries and non-ACK feedback events.
    matched = subprocess.run(
        ["rg", "^WS13_HOP |^WS13_QP event=(cnp|sack|timeout|irn_timeout) ", str(log)],
        capture_output=True, text=True, check=True, encoding="utf-8", errors="replace")
    hops = collections.defaultdict(list)
    events = collections.defaultdict(collections.Counter)
    for line in matched.stdout.splitlines():
        item = fields(line)
        key = tuple(int(item[k]) for k in ("src", "dst", "sport", "dport"))
        if line.startswith("WS13_HOP "):
            hops[key].append({k: int(item[k]) for k in
                              ("switch", "port", "packets", "bytes",
                               "queued_bytes_sum", "queued_bytes_max",
                               "wait_ns_sum", "wait_ns_max")})
        else:
            events[key][item["event"]] += 1
    assert set(hops) == set(bg_keys)
    source_hops, final_hops = [], []
    for key, rows in hops.items():
        src, dst = key[:2]
        source_rows = [h for h in rows if h["switch"] == tors[src] and h["port"] > 8]
        final_rows = [h for h in rows if h["switch"] == tors[dst] and h["port"] == host_ports[dst]]
        assert final_rows and (source_rows or tors[src] == tors[dst]), key
        source_hops.extend(source_rows)
        final_hops.extend(final_rows)
    assert source_hops and final_hops

    def hop_summary(rows):
        return {"rows": len(rows), "wait_ns_sum": sum(x["wait_ns_sum"] for x in rows),
                "wait_ns_max": max(x["wait_ns_max"] for x in rows),
                "queued_bytes_sum": sum(x["queued_bytes_sum"] for x in rows),
                "queued_bytes_max": max(x["queued_bytes_max"] for x in rows)}

    cnp_rows = [list(map(int, line.split())) for line in
                (raw / f"{raw_id}_out_cnp.txt").read_text().splitlines()]
    assert all(len(row) == 5 for row in cnp_rows)
    result.update({"source_tor_uplink_background_hops": hop_summary(source_hops),
                   "destination_tor_to_host_background_hops": hop_summary(final_hops),
                   "qp_event_counts": dict(sum(events.values(), collections.Counter())),
                   "qp_events": {str(k): dict(v) for k, v in events.items()},
                   "cnp_host_aggregate": {"ecn": sum(x[2] for x in cnp_rows),
                                          "ooo": sum(x[3] for x in cnp_rows),
                                          "total": sum(x[4] for x in cnp_rows)}})
    return result


def read_cell(run, tors, host_ports):
    base = RESULTS / run["id"]
    meta = json.loads((base / "metadata.json").read_text())
    raw_id = str(meta["raw_directory"])
    raw = base / "raw" / raw_id
    timing = {}
    with (raw / f"{raw_id}_out_ws18.txt").open() as source:
        for line in source:
            row = list(map(int, line.split()))
            timing[row[0]] = row
    expected = 16384 + run["background"]
    assert len(timing) == expected
    moe = [row for row in timing.values() if row[5] == 2]
    bg = {row[0]: row for row in timing.values() if row[5] == 1}
    assert len(moe) == 16384 and len(bg) == run["background"]
    round_origin = min(row[7] for row in moe)
    rounds = collections.defaultdict(list)
    for row in moe:
        round_id, offset = divmod(row[7] - round_origin, 50000)
        assert offset == 0 and 0 <= round_id < 8
        rounds[round_id].append(row)
    assert len(rounds) == 8 and all(len(x) == 2048 for x in rounds.values())
    round_ns = [max(row[9] for row in rounds[i]) - min(row[7] for row in rounds[i])
                for i in range(8)]
    waits = [row[10] for row in moe]
    networks = [row[9] - row[8] for row in moe]
    totals = [row[11] for row in moe]
    result = {"id": run["id"], "raw_id": raw_id, "seed": run["seed"],
              "hotspot": run["hotspot"], "background": run["background"],
              "arm": run["arm"], "index": run["index"],
              "moe": {"completed": len(moe), "bytes": sum(row[6] for row in moe),
                      "round_completion_us": [us(x) for x in round_ns],
                      "round_sum_ns": sum(round_ns),
                      "round_mean_us": us(sum(round_ns) / 8),
                      "round_max_us": us(max(round_ns)),
                      "synthetic_batch_us": us(max(row[9] for row in moe) - round_origin),
                      "wait_positive": sum(x > 0 for x in waits),
                      "wait_p50_us": us(percentile(waits, 50)),
                      "wait_p99_us": us(percentile(waits, 99)),
                      "wait_max_us": us(max(waits)),
                      "wait_sum_us": us(sum(waits)),
                      "network_p50_us": us(percentile(networks, 50)),
                      "network_p99_us": us(percentile(networks, 99)),
                      "network_mean_us": us(statistics.mean(networks)),
                      "total_mean_us": us(statistics.mean(totals))},
              "background_metrics": None}
    bg_keys = {}
    if bg:
        fct = {fid: row[11] for fid, row in bg.items()}
        for fid, row in bg.items():
            bg_keys[(row[1], row[2], row[3], row[4])] = fid
        slowest_id = max(fct, key=lambda fid: (fct[fid], -fid))
        first, last = min(row[7] for row in bg.values()), max(row[9] for row in bg.values())
        result["background_metrics"] = {
            "completed": len(bg), "bytes": sum(row[6] for row in bg.values()),
            "fct_p50_us": us(percentile(fct.values(), 50)),
            "fct_p95_us": us(percentile(fct.values(), 95)),
            "fct_p99_us": us(percentile(fct.values(), 99)),
            "fct_max_us": us(max(fct.values())),
            "fct_p99_ns": percentile(fct.values(), 99),
            "fct_max_ns": max(fct.values()),
            "effective_flow_throughput_p50_gbps": round(percentile(
                [row[6] * 8 / row[11] for row in bg.values()], 50), 6),
            "aggregate_effective_throughput_gbps": round(
                sum(row[6] for row in bg.values()) * 8 / (last - first), 6),
            "slowest": {"flow_id": slowest_id, "qp": list(next(k for k, v in
                        bg_keys.items() if v == slowest_id)), "fct_us": us(fct[slowest_id])}}
    result["diagnostic"] = diagnostic(raw, raw_id, run["background"], bg_keys, tors, host_ports)
    return result, timing


def compare(block):
    e, a, p, j = (block[arm] for arm in ARMS)
    times = {arm: block[arm]["moe"]["round_sum_ns"] / 8000 for arm in ARMS}
    result = {"round_mean_delta_us": {
        "A-E": round(times["admission"] - times["ecmp"], 6),
        "P-E": round(times["path"] - times["ecmp"], 6),
        "J-E": round(times["joint"] - times["ecmp"], 6),
        "J-A": round(times["joint"] - times["admission"], 6),
        "J-P": round(times["joint"] - times["path"], 6),
        "interaction": round(times["joint"] - times["admission"] -
                             times["path"] + times["ecmp"], 6)}}
    if e["background_metrics"]:
        result["background"] = {}
        for metric in ("fct_p99_ns", "fct_max_ns"):
            values = {arm: block[arm]["background_metrics"][metric] for arm in ARMS}
            result["background"][metric.replace("_ns", "_delta_us")] = {
                "A-E": us(values["admission"] - values["ecmp"]),
                "P-E": us(values["path"] - values["ecmp"]),
                "J-E": us(values["joint"] - values["ecmp"]),
                "J-A": us(values["joint"] - values["admission"]),
                "J-P": us(values["joint"] - values["path"]),
                "interaction": us(values["joint"] - values["admission"] -
                                  values["path"] + values["ecmp"])}
    return result


def render_svg(blocks):
    points = []
    for block in blocks:
        if block["background"] != 192:
            continue
        for arm in ("admission", "path", "joint"):
            points.append((block["hotspot"], block["seed"], arm,
                           block["effects"]["round_mean_delta_us"][{"admission": "A-E", "path": "P-E", "joint": "J-E"}[arm]],
                           block["effects"]["background"]["fct_p99_delta_us"][{"admission": "A-E", "path": "P-E", "joint": "J-E"}[arm]]))
    colors = {"admission": "#3274a1", "path": "#e1812c", "joint": "#4d8f61"}
    def marker(seed, arm, x, y):
        color = colors[arm]
        if seed == 20261701:
            return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{color}" stroke="#333" stroke-width=".6"/>'
        if seed == 20261702:
            return f'<rect x="{x-6:.1f}" y="{y-6:.1f}" width="12" height="12" fill="{color}" stroke="#333" stroke-width=".6"/>'
        return f'<polygon points="{x:.1f},{y-7:.1f} {x-7:.1f},{y+6:.1f} {x+7:.1f},{y+6:.1f}" fill="{color}" stroke="#333" stroke-width=".6"/>'

    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="560" viewBox="0 0 1120 560">',
           '<rect width="1120" height="560" fill="white"/>',
           '<text x="560" y="28" text-anchor="middle" font-family="Arial" font-size="18">WS-19: paired MoE–background tradeoff (b192)</text>',
           '<text x="560" y="50" text-anchor="middle" font-family="Arial" font-size="12">Each mark is one independent demand seed; deltas vs same-trace ECMP. Panels use different scales.</text>']
    for hotspot, title, x0 in (("host_hotspot", "Host hotspot", 90),
                               ("tor_hotspot", "ToR hotspot", 630)):
        selected = [p for p in points if p[0] == hotspot]
        xs = [p[3] for p in selected] + [0]
        ys = [p[4] for p in selected] + [0]
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)
        dx, dy = max(xmax - xmin, .1), max(ymax - ymin, .1)
        xmin, xmax = xmin - dx * .12, xmax + dx * .12
        ymin, ymax = ymin - dy * .12, ymax + dy * .12
        x1, y0, y1 = x0 + 400, 105, 405
        sx = lambda x: x0 + (x - xmin) / (xmax - xmin) * 400
        sy = lambda y: y1 - (y - ymin) / (ymax - ymin) * 300
        svg += [f'<text x="{x0+200}" y="88" text-anchor="middle" font-family="Arial" font-size="16">{title}</text>',
                f'<rect x="{x0}" y="{y0}" width="400" height="300" fill="#fafafa" stroke="#999"/>',
                f'<line x1="{sx(0):.1f}" x2="{sx(0):.1f}" y1="{y0}" y2="{y1}" stroke="#888" stroke-dasharray="4 4"/>',
                f'<line x1="{x0}" x2="{x1}" y1="{sy(0):.1f}" y2="{sy(0):.1f}" stroke="#888" stroke-dasharray="4 4"/>']
        for _, seed, arm, x, y in selected:
            svg.append(marker(seed, arm, sx(x), sy(y)))
        svg += [f'<text x="{x0+200}" y="450" text-anchor="middle" font-family="Arial" font-size="12">MoE round-mean Δ (µs; lower is better)</text>',
                f'<text x="{x0}" y="425" font-family="Arial" font-size="10">{xmin:.1f}</text>',
                f'<text x="{x1}" y="425" text-anchor="end" font-family="Arial" font-size="10">{xmax:.1f}</text>',
                f'<text x="{x0-5}" y="108" text-anchor="end" font-family="Arial" font-size="10">{ymax:.1f}</text>',
                f'<text x="{x0-5}" y="408" text-anchor="end" font-family="Arial" font-size="10">{ymin:.1f}</text>']
    svg += ['<text x="25" y="255" transform="rotate(-90 25 255)" text-anchor="middle" font-family="Arial" font-size="12">Background P99 Δ (µs; lower is better)</text>']
    for i, (arm, label) in enumerate((("admission", "Admission only"), ("path", "Path only"), ("joint", "Joint"))):
        x = 145 + i * 180
        svg += [marker(20261701, arm, x, 488),
                f'<text x="{x+13}" y="492" font-family="Arial" font-size="12">{label}</text>']
    for i, (seed, label) in enumerate(((20261701, "seed 01"), (20261702, "seed 02"), (20261703, "seed 03"))):
        x = 700 + i * 125
        svg += [marker(seed, "joint", x, 488),
                f'<text x="{x+13}" y="492" font-family="Arial" font-size="12">{label}</text>']
    svg += ['<text x="560" y="535" text-anchor="middle" font-family="Arial" font-size="11">Descriptive n=3 only; background P99 is undefined in b0.</text>', '</svg>']
    FIGURE.write_text("\n".join(svg) + "\n", encoding="utf-8")


def main():
    assert sha(ROOT / "docs/research/ws19-admission-pilot-prereg-v1.md") == PROTOCOL_SHA
    assert sha(SCHEDULE) == SCHEDULE_SHA
    schedule = json.loads(SCHEDULE.read_text())
    mapping = json.loads(RUN_MAP.read_text())
    runs = mapping["runs"]
    assert len(runs) == len(schedule["runs"]) == 48
    assert mapping["source_sha"] == SOURCE_SHA and mapping["schedule_sha256"] == SCHEDULE_SHA
    assert all(r["index"] == i and all(r[k] == schedule["runs"][i][k] for k in
               ("arm", "seed", "hotspot", "background", "trace_sha256", "block", "position"))
               for i, r in enumerate(runs))
    receipt_rows = [json.loads(line) for line in RECEIPTS.read_text().splitlines() if line.strip()]
    receipt_counts = dict(collections.Counter(r["event"] for r in receipt_rows))
    assert receipt_counts == {"built": 48, "started": 48, "verified": 48}
    starts = [r for r in receipt_rows if r["event"] == "started"]
    assert [r["index"] for r in starts] == list(range(48))
    assert max(r["concurrency_cap"] for r in starts) <= 4
    verified = {r["id"]: r for r in receipt_rows if r["event"] == "verified"}
    assert len(verified) == 48 and set(verified) == {r["id"] for r in runs}
    assert all(verified[r["id"]]["schedule_index"] == r["index"] for r in runs)
    with ThreadPoolExecutor(max_workers=4) as pool:
        checked = list(pool.map(lambda r: verify(r["id"], schedule["runs"][r["index"]]), runs))
    assert all(x["status"] == "VERIFIED" for x in checked)
    checked_by_id = {x["experiment_id"]: x for x in checked}
    tors, host_ports = host_tors()
    cells, timing = {}, {}
    for run in runs:
        cell, rows = read_cell(run, tors, host_ports)
        cell["raw_sha256"] = {"trace": checked_by_id[run["id"]]["trace_sha256"],
                              "fct": checked_by_id[run["id"]]["fct_sha256"],
                              "timing": checked_by_id[run["id"]]["timing_sha256"]}
        cells[run["id"]] = cell
        timing[run["id"]] = rows
    block_lookup = collections.defaultdict(dict)
    for run in runs:
        block_lookup[(run["seed"], run["hotspot"], run["background"])][run["arm"]] = run["id"]
    blocks = []
    for (seed, hotspot, background), ids in sorted(block_lookup.items()):
        assert set(ids) == set(ARMS)
        arm_cells = {arm: cells[ids[arm]] for arm in ARMS}
        effects = compare(arm_cells)
        if background:
            baseline = timing[ids["ecmp"]]
            effects["background"]["paired_flow_delta_vs_ecmp"] = {}
            for arm in ARMS:
                slowest = arm_cells[arm]["background_metrics"]["slowest"]
                slowest["qp_event_counts"] = arm_cells[arm]["diagnostic"]["qp_events"].get(
                    str(tuple(slowest["qp"])), {})
            for arm in ("admission", "path", "joint"):
                current = timing[ids[arm]]
                diffs = []
                for fid, ref in baseline.items():
                    if ref[5] != 1:
                        continue
                    now = current[fid]
                    assert (ref[1], ref[2], ref[5], ref[6], ref[7]) == (now[1], now[2], now[5], now[6], now[7])
                    diffs.append(now[11] - ref[11])
                assert len(diffs) == 192
                effects["background"]["paired_flow_delta_vs_ecmp"][arm] = {
                    "worse": sum(x > 0 for x in diffs), "equal": sum(x == 0 for x in diffs),
                    "better": sum(x < 0 for x in diffs), "p50_us": us(percentile(diffs, 50)),
                    "p99_us": us(percentile(diffs, 99)), "min_us": us(min(diffs)),
                    "max_us": us(max(diffs))}
                slowest_id = arm_cells[arm]["background_metrics"]["slowest"]["flow_id"]
                arm_cells[arm]["background_metrics"]["slowest"]["paired_ecmp_delta_us"] = us(
                    current[slowest_id][11] - baseline[slowest_id][11])
        blocks.append({"seed": seed, "hotspot": hotspot, "background": background,
                       "ids": ids, "effects": effects})
    gates = []
    for block in blocks:
        arm = {name: cells[eid] for name, eid in block["ids"].items()}
        j = arm["joint"]
        if block["hotspot"] == "tor_hotspot" and block["background"] == 192:
            for other in ("ecmp", "admission", "path"):
                gates.append({"seed": block["seed"], "scenario": "tor_b192",
                              "criterion": f"J_round_mean_strictly_less_than_{other}",
                              "pass": j["moe"]["round_sum_ns"] < arm[other]["moe"]["round_sum_ns"]})
            for metric in ("fct_p99_ns", "fct_max_ns"):
                gates.append({"seed": block["seed"], "scenario": "tor_b192",
                              "criterion": f"J_{metric}_not_above_E",
                              "pass": j["background_metrics"][metric] <= arm["ecmp"]["background_metrics"][metric]})
        if block["hotspot"] == "host_hotspot" and block["background"] == 192:
            gates.append({"seed": block["seed"], "scenario": "host_b192",
                          "criterion": "J_round_mean_not_above_A",
                          "pass": j["moe"]["round_sum_ns"] <= arm["admission"]["moe"]["round_sum_ns"]})
            for metric in ("fct_p99_ns", "fct_max_ns"):
                gates.append({"seed": block["seed"], "scenario": "host_b192",
                              "criterion": f"J_{metric}_not_above_A",
                              "pass": j["background_metrics"][metric] <= arm["admission"]["background_metrics"][metric]})
        if block["background"] == 0:
            gates.append({"seed": block["seed"], "scenario": block["hotspot"] + "_b0",
                          "criterion": "J_round_mean_not_above_E",
                          "pass": j["moe"]["round_sum_ns"] <= arm["ecmp"]["moe"]["round_sum_ns"]})
    assert all(c["moe"]["completed"] == 16384 for c in cells.values())
    assert all(c["background_metrics"] is None or c["background_metrics"]["completed"] == 192 for c in cells.values())
    assert all(c["diagnostic"]["path"]["alternate"] > 0 for c in cells.values() if c["arm"] in ("path", "joint"))
    strata = []
    for hotspot in ("host_hotspot", "tor_hotspot"):
        for background in (0, 192):
            selected = [b for b in blocks if b["hotspot"] == hotspot and b["background"] == background]
            assert [b["seed"] for b in selected] == [20261701, 20261702, 20261703]
            contrasts = {}
            for name in ("A-E", "P-E", "J-E", "J-A", "J-P", "interaction"):
                values = [b["effects"]["round_mean_delta_us"][name] for b in selected]
                contrasts[name] = {"by_seed_us": values, "median_us": statistics.median(values),
                                   "range_us": [min(values), max(values)]}
            entry = {"hotspot": hotspot, "background": background,
                     "moe_round_mean_deltas": contrasts}
            if background:
                entry["background_p99_deltas"] = {}
                entry["background_max_deltas"] = {}
                for metric, key in (("fct_p99_delta_us", "background_p99_deltas"),
                                    ("fct_max_delta_us", "background_max_deltas")):
                    for name in ("A-E", "P-E", "J-E", "J-A", "J-P", "interaction"):
                        values = [b["effects"]["background"][metric][name] for b in selected]
                        entry[key][name] = {"by_seed_us": values,
                                            "median_us": statistics.median(values),
                                            "range_us": [min(values), max(values)]}
            strata.append(entry)
    output = {"role": "exploratory paired 2x2 pilot; independent demand n=3",
              "source_sha": SOURCE_SHA, "protocol_sha256": PROTOCOL_SHA,
              "schedule_sha256": SCHEDULE_SHA, "run_map_sha256": sha(RUN_MAP),
              "receipts_sha256": sha(RECEIPTS), "receipt_counts": receipt_counts,
              "start_indices_in_frozen_order": True,
              "concurrency_caps_used": sorted({r["concurrency_cap"] for r in starts}),
              "raw_verification_repeated": True,
              "unit_of_independence": "seed; rounds, flows, background levels and hotspots are paired repeated observations",
              "percentile_method": "linear interpolation at (n-1)*p/100",
              "cells": [cells[r["id"]] for r in runs], "blocks": blocks, "strata": strata,
              "gates": gates, "gate_pass_count": sum(g["pass"] for g in gates),
              "gate_fail_count": sum(not g["pass"] for g in gates),
              "all_gates_pass": all(g["pass"] for g in gates),
              "ws20_decision": "design_go_only" if all(g["pass"] for g in gates) else "no_go"}
    # The event map is only needed while deriving spatial summaries; it would
    # bloat the stable artifact and does not add independent measurements.
    for cell in output["cells"]:
        cell["diagnostic"].pop("qp_events", None)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    render_svg(blocks)
    print(f"WS-19: {len(cells)} verified cells, {len(blocks)} blocks, {sum(not g['pass'] for g in gates)} failed gates; {output['ws20_decision']}")
    print(OUT)
    print(FIGURE)


if __name__ == "__main__":
    main()
