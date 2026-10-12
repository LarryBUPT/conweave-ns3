#!/usr/bin/env python3
"""Replay the frozen WS-26 queue-front windows from a simulation log."""

import argparse
import collections
import json
from pathlib import Path


PORTS = {(1382, 16): 25000, (1543, 10): 25000,
         (1657, 5): 25000, (1575, 4): 25000, (1347, 6): 50000}
START_NS = 2000000000
MAX_ROWS = 400000
MAX_BYTES = 96 * 1024 * 1024
FIELDS = ("event", "time_ns", "switch", "port", "qindex", "uid",
          "packet_bytes", "queue_bytes_after", "subqueue_bytes_after", "tag", "dst_tor",
          "qp_hash", "seq", "l3", "service_done_ns")


def parse(line):
    values = dict(part.split("=", 1) for part in line.split()[1:])
    if set(values) != set(FIELDS):
        raise ValueError("missing or unexpected queue-front fields")
    event = values.pop("event")
    if event not in ("E", "D", "T", "X"):
        raise ValueError("unknown event")
    return {"event": event, **{key: int(value) for key, value in values.items()}}


def replay(path, target_uids):
    queues = collections.defaultdict(collections.deque)
    occupancy = {}
    suboccupancy = {}
    initial_remaining = {}
    last_time = {}
    in_flight = {}
    service = {}
    counts = collections.Counter()
    leading_unknown = collections.Counter()
    boundary = collections.Counter()
    targets = []
    summary = None
    summaries = 0
    summary_seen = False
    row_bytes = 0
    with path.open(encoding="utf-8", errors="replace") as stream:
        for number, line in enumerate(stream, 1):
            if line.startswith("WS26_QFRONT_SUMMARY "):
                summaries += 1
                summary_seen = True
                summary = dict(part.split("=", 1) for part in line.split()[1:])
                continue
            if not line.startswith("WS26_QFRONT "):
                continue
            if summary_seen:
                raise ValueError("queue-front row after terminal summary")
            row_bytes += len(line.encode("utf-8"))
            row = parse(line)
            event = row["event"]
            port = row["switch"], row["port"]
            qkey = port + (row["qindex"],)
            uid = row["uid"]
            size = row["packet_bytes"]
            now = row["time_ns"]
            if port not in PORTS or not START_NS <= now <= START_NS + PORTS[port]:
                raise ValueError("event outside frozen port/window at line %d" % number)
            if now < last_time.get(port, START_NS):
                raise ValueError("port event time regressed at line %d" % number)
            last_time[port] = now
            if size <= 0 or row["queue_bytes_after"] < 0 or row["subqueue_bytes_after"] < 0:
                raise ValueError("invalid packet/queue bytes at line %d" % number)
            delta = size if event == "E" else -size if event in ("D", "X") else 0
            if port in occupancy:
                if occupancy[port] + delta != row["queue_bytes_after"]:
                    raise ValueError("queue byte conservation failed at line %d" % number)
            else:
                initial_total = row["queue_bytes_after"] - delta
                if initial_total < 0:
                    raise ValueError("negative initial queue at line %d" % number)
                boundary[str(port)] = initial_total
            occupancy[port] = row["queue_bytes_after"]
            if qkey in suboccupancy:
                if suboccupancy[qkey] + delta != row["subqueue_bytes_after"]:
                    raise ValueError("subqueue byte conservation failed at line %d" % number)
            else:
                initial_sub = row["subqueue_bytes_after"] - delta
                if initial_sub < 0:
                    raise ValueError("negative initial subqueue at line %d" % number)
                initial_remaining[qkey] = initial_sub
            suboccupancy[qkey] = row["subqueue_bytes_after"]
            counts[event] += 1
            queue = queues[qkey]
            if event == "E":
                queue.append(row)
            elif event in ("D", "X"):
                if initial_remaining[qkey] and queue and queue[0]["uid"] == uid:
                    raise ValueError("observed packet bypassed unknown queue prefix at line %d" % number)
                if queue and queue[0]["uid"] == uid:
                    enrolled = queue.popleft()
                    identity = ("qindex", "packet_bytes", "tag", "dst_tor", "qp_hash", "seq", "l3")
                    if any(enrolled[key] != row[key] for key in identity):
                        raise ValueError("enqueue/dequeue identity mismatch at line %d" % number)
                elif initial_remaining[qkey] >= size:
                    initial_remaining[qkey] -= size
                    leading_unknown[str(qkey)] += 1
                else:
                    raise ValueError("FIFO/initial-boundary mismatch at line %d" % number)
                if event == "D":
                    active = service.get(port)
                    if active and active["service_done_ns"] > now:
                        raise ValueError("dequeue before prior service ended at line %d" % number)
                    if port in in_flight:
                        raise ValueError("second dequeue before transmit at line %d" % number)
                    in_flight[port] = row
                    for target in targets:
                        if target["uid"] == uid and target["port"] == port:
                            target["dequeue_seen"] = True
            elif event == "T":
                last = in_flight.get(port)
                identity = ("uid", "qindex", "packet_bytes", "tag", "dst_tor", "qp_hash", "seq", "l3")
                if last is None or any(last[key] != row[key] for key in identity):
                    raise ValueError("dequeue/transmit mismatch at line %d" % number)
                if row["service_done_ns"] <= now:
                    raise ValueError("invalid service end at line %d" % number)
                service[port] = row
                del in_flight[port]
            if uid in target_uids and event == "E":
                active = service.get(port)
                targets.append({"line": number, "event": event, "port": port,
                                "uid": uid, "ahead_same_queue": [
                                    {"uid": item["uid"], "tag": item["tag"],
                                     "dst_tor": item["dst_tor"], "qp_hash": item["qp_hash"],
                                     "bytes": item["packet_bytes"]} for item in list(queue)[:-1]],
                                "unknown_ahead_bytes": initial_remaining[qkey],
                                "front_complete": initial_remaining[qkey] == 0,
                                "transmitting": ({"uid": active["uid"], "tag": active["tag"],
                                                  "dst_tor": active["dst_tor"],
                                                  "qp_hash": active["qp_hash"],
                                                  "service_done_ns": active["service_done_ns"]}
                                                 if active and active["service_done_ns"] > now else None),
                                "dequeue_seen": False})
    if summaries != 1 or summary is None:
        raise ValueError("missing or duplicate summary; run may be incomplete")
    if int(summary["rows"]) != sum(counts.values()) or int(summary["bytes"]) != row_bytes:
        raise ValueError("summary count/byte mismatch")
    if not counts or sum(counts.values()) > MAX_ROWS or row_bytes > MAX_BYTES or in_flight:
        raise ValueError("budget exceeded or unmatched transmit")
    return {"status": "PASS_WITH_BOUNDARIES", "rows": dict(counts),
            "bytes": row_bytes, "initial_queue_bytes": dict(boundary),
            "leading_unobserved_dequeues": dict(leading_unknown),
            "unobserved_subqueue_bytes_remaining": {str(key): value for key, value in initial_remaining.items() if value},
            "remaining_observed_packets": {str(key): len(value) for key, value in queues.items() if value},
            "last_queue_bytes": {str(key): value for key, value in occupancy.items()},
            "targets": targets}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--target-uid", type=int, action="append", default=[])
    args = parser.parse_args()
    print(json.dumps(replay(args.log, set(args.target_uid)), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
