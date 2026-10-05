#!/usr/bin/env python3
"""Convert formal uplink cumulative-byte samples using their actual timestamps."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "docs/research/evidence/ws25-v1fix-formal-analysis.json"
OUT = ROOT / "docs/research/evidence/ws25-v1fix-formal-uplink-metrics.csv"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def summarize(cell):
    folder = ROOT / "results" / cell["id"]
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    raw_id = str(meta["raw_directory"])
    if not raw_id.isdigit():
        raise RuntimeError("Invalid raw directory: " + cell["id"])
    path = folder / "raw" / raw_id / (raw_id + "_out_uplink.txt")
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("Missing uplink raw: " + cell["id"])
    first = {}
    previous = {}
    last = {}
    interval_ns = set()
    first_time = None
    last_time = None
    peak_bucket_util_pct = 0.0
    row_count = 0
    with path.open("r", encoding="ascii") as source:
        for line in source:
            pieces = line.rstrip().split(",")
            if len(pieces) != 4:
                raise RuntimeError("Malformed uplink row: " + cell["id"])
            timestamp, tor, port, count = map(int, pieces)
            if count < 0:
                raise RuntimeError("Negative uplink bytes: " + cell["id"])
            key = (tor, port)
            first_time = timestamp if first_time is None else min(first_time, timestamp)
            last_time = timestamp if last_time is None else max(last_time, timestamp)
            if key not in first:
                first[key] = (timestamp, count)
            else:
                prior_time, prior_count = previous[key]
                dt = timestamp - prior_time
                delta = count - prior_count
                if dt <= 0 or delta < 0:
                    raise RuntimeError("Nonmonotone uplink counter: " + cell["id"])
                interval_ns.add(dt)
                # 1 bit/ns = 1 Gbps; each uplink is configured at 400 Gbps.
                peak_bucket_util_pct = max(peak_bucket_util_pct,
                                           100 * (8 * delta / dt) / 400)
            previous[key] = (timestamp, count)
            last[key] = (timestamp, count)
            row_count += 1
    if len(first) != 1280 or not interval_ns or last_time <= first_time:
        raise RuntimeError("Incomplete uplink samples: " + cell["id"])
    if any(first[key][0] != first_time or last[key][0] != last_time for key in first):
        raise RuntimeError("Port sampling windows differ: " + cell["id"])
    bytes_by_port = {key: last[key][1] - first[key][1] for key in first}
    total = sum(bytes_by_port.values())
    if (total != cell["uplink"]["transmitted_uplink_bytes"] or
            sorted(interval_ns) != cell["uplink"]["sample_intervals_ns"] or
            max((last[key][1] - first[key][1] for key in first), default=0) < 0):
        raise RuntimeError("Uplink raw disagrees with formal analysis: " + cell["id"])
    active = [value for value in bytes_by_port.values() if value > 0]
    if not active:
        raise RuntimeError("No active uplink ports: " + cell["id"])
    span = last_time - first_time
    percent = lambda bytes_, count: 100 * (8 * bytes_ / span) / (400 * count)
    return {
        "id": cell["id"], "seed": cell["seed"], "background_flows": cell["background"],
        "mode": cell["mode"], "source_sha": cell["source_sha"],
        "raw_uplink_path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "uplink_sha256": sha(path), "sample_rows": row_count,
        "observed_start_ns": first_time, "observed_end_ns": last_time,
        "observed_span_ns": span, "sample_interval_ns_values": ";".join(map(str, sorted(interval_ns))),
        "uplink_port_count": len(first), "active_uplink_port_count": len(active),
        "transmitted_uplink_bytes": total,
        "mean_all_port_utilization_pct": percent(total, len(first)),
        "mean_active_port_utilization_pct": percent(total, len(active)),
        "max_port_mean_utilization_pct": percent(max(bytes_by_port.values()), 1),
        "peak_single_port_sample_utilization_pct": peak_bucket_util_pct,
        "mean_active_tor_port_imbalance": cell["uplink"]["mean_active_tor_port_imbalance"],
    }


def main():
    analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    if len(analysis["cells"]) != 576:
        raise RuntimeError("Formal analysis is incomplete")
    rows = [summarize(cell) for cell in analysis["cells"]]
    rows.sort(key=lambda row: (row["seed"], row["background_flows"], row["mode"]))
    with OUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("uplink_cells=%d" % len(rows))


if __name__ == "__main__":
    main()
