"""Validate a mode-20 host-egress event stream against its WS18 timing raw."""

import argparse
import json
from pathlib import Path

from verify_ws21_identity import read_ws18


def verify(port_path, ws18_path):
    flows = read_ws18(ws18_path)
    earliest = min(flow["demand"] for flow in flows.values())
    latest = max(flow["finish"] for flow in flows.values())
    ports = {}
    errors = []
    count = 0
    byte_count = 0
    summary = None
    with port_path.open("rb") as stream:
        header = stream.readline()
        byte_count += len(header)
        if header != b"time_ns tor port event queue_bytes\n":
            raise ValueError("port-event header mismatch")
        for raw in stream:
            if raw.startswith(b"# "):
                if summary is not None:
                    errors.append("duplicate summary")
                summary = dict(field.split("=", 1) for field in raw.decode().strip()[2:].split())
                continue
            if summary is not None:
                errors.append("event after summary")
                continue
            byte_count += len(raw)
            fields = raw.decode().split()
            if len(fields) != 5:
                errors.append("malformed event row")
                continue
            time, tor, port = map(int, fields[:3])
            event = fields[3]
            queue = int(fields[4])
            key = (tor, port)
            previous = ports.get(key)
            if event not in ("B", "F", "E", "D", "R", "X") or queue < 0:
                errors.append(f"invalid event or queue on {key}")
            if previous is None:
                if event != "B" or time > earliest:
                    errors.append(f"missing start boundary on {key}")
                ports[key] = {"start": time, "end": None, "time": time,
                              "queue": queue, "peak": queue, "events": 1}
            else:
                if time < previous["time"] or previous["end"] is not None:
                    errors.append(f"non-monotone time or event after final boundary on {key}")
                if event == "B":
                    errors.append(f"duplicate start boundary on {key}")
                elif event == "F":
                    previous["end"] = time
                elif event == "E" and queue < previous["queue"]:
                    errors.append(f"enqueue decreased queue on {key}")
                elif event in ("D", "X") and queue > previous["queue"]:
                    errors.append(f"dequeue/drop increased queue on {key}")
                elif event == "R" and queue != previous["queue"]:
                    errors.append(f"rejection changed queue on {key}")
                previous["time"] = time
                previous["queue"] = queue
                previous["peak"] = max(previous["peak"], queue)
                previous["events"] += 1
            count += 1
    if summary is None:
        errors.append("missing summary")
        summary = {}
    else:
        if int(summary.get("events", -1)) != count or int(summary.get("bytes", -1)) != byte_count:
            errors.append("event/byte counters do not match raw")
        if int(summary.get("overflow", -1)) != 0:
            errors.append("port-event stream overflowed")
    for key, row in ports.items():
        if row["end"] is None or row["end"] < latest:
            errors.append(f"missing or early final boundary on {key}")
    return {"complete": not errors, "qp_count": len(flows), "port_count": len(ports),
            "events": count, "raw_bytes_before_summary": byte_count,
            "overflow": int(summary.get("overflow", -1)),
            "peak_queue_bytes": max((row["peak"] for row in ports.values()), default=0),
            "errors": errors[:20]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port-events", type=Path, required=True)
    parser.add_argument("--ws18", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.port_events, args.ws18)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["complete"] else 1)


if __name__ == "__main__":
    main()
