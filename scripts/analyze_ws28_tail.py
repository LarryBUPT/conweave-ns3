#!/usr/bin/env python3
"""Pair WS-28 target packet queue events and summarize terminal-packet paths."""
import argparse
import json
from collections import defaultdict
from pathlib import Path

import run_ws28_tail as tail


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/research/evidence/ws28-tail-plan-v2.json"
PROGRESS = ROOT / "results/ws28-tail-analysis-progress.json"
FINAL = ROOT / "docs/research/evidence/ws28-tail-analysis.json"
TARGETS = (
    (20262725, 780, 956, 10045, 142), (20262725, 964, 304, 10020, 139),
    (20262729, 1176, 344, 10010, 165), (20262729, 320, 528, 10033, 115),
    (20262739, 860, 1160, 10057, 137), (20262739, 560, 448, 10027, 133),
)


def parse_events(log):
    events = []
    for line in log.splitlines():
        if not line.startswith("WS28_TAIL_"):
            continue
        kind, *parts = line.split()
        values = {}
        for part in parts:
            key, value = part.split("=", 1)
            values[key] = int(value) if value.isdigit() else value
        events.append({"kind": kind[10:], **values})
    return events


def analyze_cell(cell, plan):
    receipt = tail.verify(cell, plan)
    if not cell["diag"]:
        return {"id": cell["id"], "seed": cell["seed"], "mode": cell["mode"],
                "fct_sha256": receipt["fct_sha256"], "diag": 0, "targets": []}
    folder = ROOT / "results" / cell["id"]
    log = (folder / "logs/config.log").read_text(encoding="utf-8", errors="replace")
    events = parse_events(log)
    if any(event["kind"] == "OVERFLOW" for event in events):
        raise RuntimeError("tail event log overflowed: " + cell["id"])
    by_packet = defaultdict(dict)
    choices = defaultdict(list)
    admission = []
    for event in events:
        kind = event["kind"]
        if kind == "CHOICE":
            choices[event["target"]].append(event)
            continue
        if kind == "ADMISSION_DROP":
            admission.append(event)
            continue
        key = (event["target"], event["switch"], event["uid"])
        if kind in by_packet[key]:
            raise RuntimeError("duplicate packet event: {} {}".format(cell["id"], key))
        by_packet[key][kind] = event
    for key, packet in by_packet.items():
        if "OFFER" not in packet:
            raise RuntimeError("target packet has no queue offer: {} {}".format(cell["id"], key))
        if "DEQUEUE" in packet:
            terminal = "DEQUEUE"
        elif "DROP" in packet and packet["DROP"]["was_queued"]:
            terminal = "DROP"
        elif "REJECT" in packet or "DROP" in packet:
            terminal = "REJECT"
        else:
            raise RuntimeError("target packet terminal event missing: {} {}".format(cell["id"], key))
        if (terminal in ("DEQUEUE", "DROP")) != ("ENQUEUE" in packet):
            raise RuntimeError("target packet queue acceptance mismatch: {} {}".format(cell["id"], key))
        if terminal == "DEQUEUE":
            if packet["DEQUEUE"]["wait_ns"] < 0 or (packet["DEQUEUE"]["enqueue_ns"] !=
                                                        packet["OFFER"]["time_ns"]):
                raise RuntimeError("target packet wait time mismatch: {} {}".format(cell["id"], key))
    summaries = []
    for target, identity in enumerate(TARGETS):
        if identity[0] != cell["seed"]:
            continue
        records = [(key, packet) for key, packet in by_packet.items() if key[0] == target]
        if not records or not choices[target]:
            raise RuntimeError("expected target flow absent: {} target={}".format(cell["id"], target))
        highest_seq = max(packet["OFFER"]["seq"] for _, packet in records)
        terminal_uids = sorted({key[2] for key, packet in records
                                if packet["OFFER"]["seq"] == highest_seq})
        paths = []
        for uid in terminal_uids:
            hops = []
            for key, packet in records:
                if key[2] == uid:
                    offer = packet["OFFER"]
                    end = packet.get("DEQUEUE", packet.get("REJECT", packet.get("DROP")))
                    hops.append({"switch": key[1], "port": offer["port"],
                                 "enqueue_ns": offer["time_ns"],
                                 "end_ns": end["time_ns"], "event": end["kind"],
                                 "wait_ns": end.get("wait_ns"),
                                 "queue_before": offer["queue_before"],
                                 "background_before": offer["background_before"],
                                 "background_valid": offer["background_valid"]})
            paths.append({"uid": uid, "hops": sorted(hops, key=lambda row: row["enqueue_ns"]),
                          "total_wait_ns": sum(row["wait_ns"] or 0 for row in hops)})
        summaries.append({"target": target, "flow": identity[1:],
                          "source_choices": sorted(choices[target], key=lambda row: row["time_ns"]),
                          "max_seq": highest_seq, "max_seq_paths": paths,
                          "packet_hops": len(records)})
    return {"id": cell["id"], "seed": cell["seed"], "mode": cell["mode"],
            "diag": 1, "fct_sha256": receipt["fct_sha256"],
            "events": receipt["events"], "admission_drops": admission,
            "targets": summaries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    rows = [analyze_cell(cell, plan) for cell in plan["cells"][:args.limit]]
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source_sha": plan["source_sha"],
               "plan_sha256": tail.analyze_moe_tags.sha256(PLAN),
               "analyzed_cells": rows}
    PROGRESS.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    if len(rows) == 12:
        pairs = defaultdict(dict)
        for row in rows:
            pairs[(row["seed"], row["mode"])][row["diag"]] = row["fct_sha256"]
        if len(pairs) != 6 or any(set(pair) != {0, 1} or
                                  pair[0] != pair[1] for pair in pairs.values()):
            raise RuntimeError("tail probe on/off FCT identity failed")
        FINAL.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    print(json.dumps({"analyzed_cells": len(rows), "target_summaries":
                      sum(len(row["targets"]) for row in rows)}, sort_keys=True))


if __name__ == "__main__":
    main()
