#!/usr/bin/env python3
"""Summarize the frozen seed-97 packet timeline from verified raw results."""

import argparse
import collections
import json
from pathlib import Path

import analyze_moe_tags
import verify_ws26_seed97_time_aligned as verify
from verify_ws26_moe_hop_diagnostic import (
    fields, path_for, raw_fct, topology_maps, trace_qps,
)
from verify_ws26_seed97_probe_preflight import HEADER, HEADER_QUAD, ROOT


PLAN_SHA = "01c9acb0cbc98b3af14c0b1c4d02b861a6842438a9e12d0906278222da7b7f4c"
OUTPUT = ROOT / "docs/research/evidence/ws26-seed97-time-aligned-analysis.json"
TARGETS = (
    (268, 628, 10001, 105), (340, 628, 10000, 101),
    (544, 628, 10000, 103), (692, 628, 10005, 104),
    (896, 628, 10000, 100), (1124, 628, 10000, 102),
    (964, 1148, 10059, 136), (980, 1128, 10059, 156),
    (988, 1120, 10056, 151), (1076, 1120, 10060, 154),
    (1080, 1148, 10058, 139), (1116, 1128, 10058, 165),
)


def label(key):
    return "%d->%d:%d/%d" % key


def percentile(values, proportion):
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * proportion
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def distribution(values):
    return {"count": len(values), "p50_ns": percentile(values, 0.5),
            "p95_ns": percentile(values, 0.95), "p99_ns": percentile(values, 0.99),
            "max_ns": max(values) if values else None}


def parse_fct(folder, metadata, expected, selected):
    result = {}
    with raw_fct(folder, metadata).open(encoding="ascii") as stream:
        for line in stream:
            values = list(map(int, line.split()))
            key = tuple(values[:4])
            if key in selected:
                if key in result:
                    raise RuntimeError("Duplicate selected FCT: " + label(key))
                if (values[4] != expected[key]["size"] or
                        abs(values[5] - expected[key]["start_ns"]) > 2):
                    raise RuntimeError("Selected FCT differs from trace: " + label(key))
                result[key] = {"size_bytes": values[4], "start_ns": values[5],
                               "fct_ns": values[6], "standalone_ns": values[7],
                               "tag": expected[key]["tag"]}
    if set(result) != selected:
        raise RuntimeError("Selected FCT identity mismatch")
    return result


def parse_log(folder, selected):
    events = {key: collections.defaultdict(list) for key in selected}
    hops = {key: collections.defaultdict(list) for key in selected}
    hop_summary = collections.defaultdict(list)
    log = folder / "logs/config.log"
    with log.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if line.startswith("WS26_S97_QP event="):
                row = fields(line)
                key = tuple(row[name] for name in ("src", "dst", "sport", "dport"))
                if key in selected:
                    event = line.split("event=", 1)[1].split()[0]
                    events[key][event].append(row)
            elif line.startswith("WS26_S97_HOP "):
                row = fields(line)
                key = tuple(row[name] for name in ("src", "dst", "sport", "dport"))
                if key in selected:
                    hops[key][row["uid"]].append(row)
            elif line.startswith(("WS13_HOP ", "WS26_MOE_HOP ")):
                row = fields(line)
                key = tuple(row[name] for name in ("src", "dst", "sport", "dport"))
                if key in selected:
                    hop_summary[key].append(row)
    if set(hop_summary) != selected:
        raise RuntimeError("Selected summary hop identities missing")
    return events, hops, hop_summary


def time_us(time_ns, start_ns):
    return round((time_ns - start_ns) / 1000, 3) if time_ns is not None else None


def summarize_qp(key, fct, events, hops, summary_hops, maps):
    size = fct["size_bytes"]
    start = fct["start_ns"]
    host_tors = maps[2]
    source_tor, destination_tor = host_tors[key[0]], host_tors[key[1]]
    ordered = path_for(summary_hops, key[0], key[1], maps[0], host_tors, maps[3])
    region_by_switch = {row["switch"]: ("source_tor" if row["switch"] == source_tor else
                                        "destination_tor" if row["switch"] == destination_tor else
                                        "transit") for row in ordered}
    sends = sorted(events["send"], key=lambda row: (row["time_ns"], row["seq"], row["uid"]))
    acks = sorted(events["ack"], key=lambda row: row["time_ns"])
    completes = events["complete"]
    if not sends or not acks or len(completes) != 1:
        raise RuntimeError("Required QP events missing: " + label(key))
    if completes[0]["time_ns"] - start != fct["fct_ns"]:
        raise RuntimeError("Complete event differs from raw FCT: " + label(key))
    waits = collections.defaultdict(list)
    ecn = collections.Counter()
    packet_totals = {}
    for uid, rows in hops.items():
        if len(rows) != len(ordered):
            raise RuntimeError("Selected packet has incomplete hop chain: " + label(key))
        chain = sorted(rows, key=lambda row: row["enqueue_ns"])
        if [row["switch"] for row in chain] != [row["switch"] for row in ordered]:
            raise RuntimeError("Selected packet hop chain differs from QP path: " + label(key))
        total_wait = 0
        for row in chain:
            region = region_by_switch[row["switch"]]
            wait = row["dequeue_ns"] - row["enqueue_ns"]
            if wait < 0:
                raise RuntimeError("Negative queue wait")
            waits[region].append(wait)
            ecn[region] += row["ecn"]
            total_wait += wait
        packet_totals[uid] = {"seq": chain[0]["seq"],
                              "first_enqueue_ns": chain[0]["enqueue_ns"],
                              "last_dequeue_ns": chain[-1]["dequeue_ns"],
                              "sum_hop_wait_ns": total_wait,
                              "max_hop_wait_ns": max(row["dequeue_ns"] - row["enqueue_ns"]
                                                     for row in chain)}
    send_uids = {row["uid"] for row in sends}
    if (len(send_uids) != len(sends) or send_uids != set(packet_totals) or
            any(packet_totals[row["uid"]]["seq"] != row["seq"] for row in sends)):
        raise RuntimeError("Send and selected packet hop chains differ: " + label(key))
    final_seq = max(row["seq"] for row in sends)
    final_send = max((row for row in sends if row["seq"] == final_seq),
                     key=lambda row: row["time_ns"])
    final_packet = packet_totals[final_send["uid"]]
    final_chain = sorted(hops[final_send["uid"]], key=lambda row: row["enqueue_ns"])
    send_times = [row["time_ns"] for row in sends]
    send_gaps = [right - left for left, right in zip(send_times, send_times[1:])]
    progress = {}
    for fraction in (0.25, 0.5, 0.75):
        threshold = size * fraction
        sent = next((row["time_ns"] for row in sends if row["seq"] >= threshold), None)
        acked = next((row["time_ns"] for row in acks if row["seq"] >= threshold), None)
        progress[str(fraction)] = {"send_us": time_us(sent, start),
                                   "ack_us": time_us(acked, start)}
    feedback = sorted(events.get("cnp", []), key=lambda row: row["time_ns"])
    rate_events = sorted((row for name, rows in events.items() if name.startswith("rate_")
                          for row in rows), key=lambda row: row["time_ns"])
    all_rates = [row["rate_bps"] for row in sends + rate_events]
    return {
        "identity": label(key), "tag": fct["tag"],
        "role": "target" if key in TARGETS else "control",
        "size_bytes": size, "start_ns": start, "fct_us": round(fct["fct_ns"] / 1000, 3),
        "complete_us": time_us(completes[0]["time_ns"], start),
        "path": [{"switch": row["switch"], "port": row["port"],
                  "region": region_by_switch[row["switch"]]} for row in ordered],
        "send": {"count": len(sends), "first_us": time_us(sends[0]["time_ns"], start),
                 "last_us": time_us(sends[-1]["time_ns"], start),
                 "max_gap_us": round(max(send_gaps, default=0) / 1000, 3),
                 "p99_gap_us": round(percentile(send_gaps, 0.99) / 1000, 3),
                 "progress": progress},
        "ack": {"count": len(acks), "last_us": time_us(acks[-1]["time_ns"], start),
                "max_seq": max(row["seq"] for row in acks)},
        "feedback": {"cnp_count": len(feedback),
                     "first_cnp_us": time_us(feedback[0]["time_ns"], start) if feedback else None,
                     "last_cnp_us": time_us(feedback[-1]["time_ns"], start) if feedback else None,
                     "rate_events": {name: len(rows) for name, rows in sorted(events.items())
                                     if name.startswith("rate_")},
                     "first_rate_event_us": time_us(rate_events[0]["time_ns"], start)
                                            if rate_events else None,
                     "min_rate_gbps": round(min(all_rates) / 1e9, 6)},
        "hop": {"packet_count": len(packet_totals),
                "regions": {name: {"wait": distribution(waits[name]),
                                   "ecn_decisions": ecn[name]}
                            for name in ("source_tor", "transit", "destination_tor")},
                "packet_total_wait": distribution(
                    [item["sum_hop_wait_ns"] for item in packet_totals.values()])},
        "final_seq_packet": {"seq": final_seq, "uid": final_send["uid"],
                             "send_us": time_us(final_send["time_ns"], start),
                             "first_enqueue_us": time_us(final_packet["first_enqueue_ns"], start),
                             "last_dequeue_us": time_us(final_packet["last_dequeue_ns"], start),
                             "sum_hop_wait_us": round(final_packet["sum_hop_wait_ns"] / 1000, 3),
                             "max_hop_wait_us": round(final_packet["max_hop_wait_ns"] / 1000, 3),
                             "hops": [{"switch": row["switch"], "port": row["port"],
                                       "region": region_by_switch[row["switch"]],
                                       "enqueue_us": time_us(row["enqueue_ns"], start),
                                       "dequeue_us": time_us(row["dequeue_ns"], start),
                                       "wait_us": round((row["dequeue_ns"] - row["enqueue_ns"]) / 1000, 3),
                                       "ecn_decision": row["ecn"]}
                                      for row in final_chain]},
    }


def summarize_cell(cell, plan, selected):
    checked = verify.check(cell, plan)
    classes = analyze_moe_tags.summarize(cell["id"])["tags"]
    folder = ROOT / "results" / cell["id"]
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    expected = trace_qps(folder / "config/traffic_trace.txt")
    fct = parse_fct(folder, metadata, expected, selected)
    events, hops, summary_hops = parse_log(folder, selected)
    maps = topology_maps(folder / "config/topology.txt")
    qps = {label(key): summarize_qp(key, fct[key], events[key], hops[key],
                                   summary_hops[key], maps) for key in sorted(selected)}
    return {"id": cell["id"], "mode": cell["mode"],
            "raw_directory": metadata["raw_directory"],
            "metadata_sha256": verify.digest(folder / "metadata.json"),
            "resource_summary_sha256": verify.digest(folder / "logs/resource-summary.json"),
            "verification": checked,
            "class_metrics": classes, "qps": qps}


def compare(left, right):
    result = {}
    for name in sorted(left["qps"]):
        e, v = left["qps"][name], right["qps"][name]
        if (e["size_bytes"], e["start_ns"], e["tag"], e["role"]) != (
                v["size_bytes"], v["start_ns"], v["tag"], v["role"]):
            raise RuntimeError("Paired QP identity changed: " + name)
        result[name] = {"tag": e["tag"], "role": e["role"],
                        "fct_delta_us": round(v["fct_us"] - e["fct_us"], 3),
                        "last_send_delta_us": round(v["send"]["last_us"] - e["send"]["last_us"], 3),
                        "final_packet_last_dequeue_delta_us": round(
                            v["final_seq_packet"]["last_dequeue_us"] -
                            e["final_seq_packet"]["last_dequeue_us"], 3),
                        "final_packet_sum_hop_wait_delta_us": round(
                            v["final_seq_packet"]["sum_hop_wait_us"] -
                            e["final_seq_packet"]["sum_hop_wait_us"], 3),
                        "cnp_delta": v["feedback"]["cnp_count"] - e["feedback"]["cnp_count"],
                        "ecn_decision_delta": {region: (
                            v["hop"]["regions"][region]["ecn_decisions"] -
                            e["hop"]["regions"][region]["ecn_decisions"])
                            for region in ("source_tor", "transit", "destination_tor")},
                        "path_changed": v["path"] != e["path"]}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    plan = verify.load_plan(PLAN_SHA)
    selected = {tuple(map(int, match)) for match in
                HEADER_QUAD.findall(HEADER.read_text(encoding="utf-8"))}
    if len(selected) != 23 or not set(TARGETS) <= selected:
        raise RuntimeError("Target set differs from frozen header")
    high = plan["cells"][2:]
    left, right = [summarize_cell(cell, plan, selected) for cell in high]
    result = {"scope": "disclosed seed 20262697 mechanism diagnostic; no new effect estimate",
              "plan_sha256": PLAN_SHA, "source_sha": plan["source_sha"],
              "trace_sha256": plan["high_trace_sha256"],
              "selected_qps": len(selected), "targets": [label(key) for key in TARGETS],
              "cells": [left, right], "paired_qps": compare(left, right)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("wrote %s with %d paired QPs" % (args.output, len(result["paired_qps"])))


if __name__ == "__main__":
    main()
