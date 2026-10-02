#!/usr/bin/env python3
"""Audit the fixed C2 WS-25 seed-01 calibration from fetched raw data."""
import collections
import json
import re
from pathlib import Path

from analyze_moe_tags import summarize
from verify_ws25_preflight import MODES, verify

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "20261002-22400"


def cnp_totals(path):
    totals = collections.Counter()
    for line in path.read_text(encoding="ascii").splitlines():
        fields = line.split()
        if len(fields) != 5:
            raise ValueError("Malformed CNP row in %s" % path)
        totals["ecn"] += int(fields[2])
        totals["ooo"] += int(fields[3])
        totals["total"] += int(fields[4])
    # A CNP can be attributed to both ECN and out-of-order in the same bucket.
    totals["ecn_ooo_overlap"] = totals["ecn"] + totals["ooo"] - totals["total"]
    if totals["ecn_ooo_overlap"] < 0:
        raise ValueError("CNP total exceeds its sources")
    return dict(totals)


def uplink_summary(path):
    first, last = {}, {}
    previous = {}
    peak_bucket_bytes = 0
    timestamps = set()
    for line in path.read_text(encoding="ascii").splitlines():
        fields = line.split(",")
        if len(fields) != 4:
            raise ValueError("Malformed uplink row in %s" % path)
        time, tor, port, count = map(int, fields)
        key = (tor, port)
        timestamps.add(time)
        if key not in first:
            first[key] = count
        if key in previous:
            prior_time, prior_count = previous[key]
            if time <= prior_time or count < prior_count:
                raise ValueError("Nonmonotone uplink counter")
            peak_bucket_bytes = max(peak_bucket_bytes, count - prior_count)
        previous[key] = (time, count)
        last[key] = count
    if not first or len(timestamps) < 2:
        raise ValueError("Missing uplink monitoring samples")
    totals = [last[key] - first[key] for key in first]
    per_tor = collections.defaultdict(list)
    for key in first:
        per_tor[key[0]].append(last[key] - first[key])
    imbalance = []
    for ports in per_tor.values():
        mean = sum(ports) / len(ports)
        if mean:
            imbalance.append((max(ports) - min(ports)) / mean)
    # The sample interval is taken from raw timestamps, not assumed from config.
    sorted_times = sorted(timestamps)
    intervals = {b - a for a, b in zip(sorted_times, sorted_times[1:])}
    return {
        "ports": len(totals), "tors": len(per_tor),
        "sample_intervals_ns": sorted(intervals),
        "transmitted_uplink_bytes": sum(totals),
        "peak_single_port_bucket_bytes": peak_bucket_bytes,
        "mean_active_tor_port_imbalance": sum(imbalance) / len(imbalance),
        "max_active_tor_port_imbalance": max(imbalance),
    }


def diagnostics(mode, log):
    result = {}
    if mode == "classreserve":
        line = next(x for x in log.splitlines() if x.startswith("WS25_CLASSRESERVE "))
        result["classreserve"] = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", line)}
        line = next(x for x in log.splitlines() if x.startswith("WS25_QUEUE "))
        result["queue"] = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", line)}
        ports = [re.findall(r"(\w+)=(\d+)", x) for x in log.splitlines()
                 if x.startswith("WS25_PORT ")]
        by_tag = collections.Counter()
        for row in ports:
            values = {k: int(v) for k, v in row}
            by_tag[str(values["tag"])] += values["packets"]
        result["source_tor_packets_by_tag"] = dict(by_tag)
    if mode in ("conga", "letflow"):
        match = re.search(r"Number of flowlet's timeout:(\d+)", log)
        if not match:
            raise ValueError("Missing flowlet diagnostic")
        result["flowlet_timeouts"] = int(match.group(1))
    if mode == "conweave":
        for name, pattern in (
            ("init_replies", r"Number of INIT's Reply sent \(RTT_REPLY\):(\d+)"),
            ("notifies", r"Number of NOTIFY Sent:(\d+)"),
            ("reroutings", r"Number of Rerouting:(\d+)"),
            ("ooo_voq_packets", r"Number of OoO enqueued pkts:(\d+)"),
            ("voq_flushes", r"Number of VOQ Flush Total:(\d+)"),
        ):
            match = re.search(pattern, log)
            if not match:
                raise ValueError("Missing ConWeave diagnostic: " + name)
            result[name] = int(match.group(1))
    return result


def main():
    cells = []
    for i, mode in enumerate(MODES):
        experiment_id = "%s%d-ws25-v2-cal01-%s" % (PREFIX, i, mode)
        verified = verify(experiment_id, "pilot", mode)
        stats = summarize(experiment_id)
        base = ROOT / "results" / experiment_id
        raw_id = json.loads((base / "metadata.json").read_text(encoding="utf-8"))["raw_directory"]
        raw = base / "raw" / str(raw_id)
        log = (base / "logs" / "config.log").read_text(encoding="utf-8", errors="replace")
        if stats["tags"]["1"]["completed_flows"] != 192 or stats["tags"]["2"]["completed_flows"] != 16384:
            raise ValueError("Incomplete cell")
        cells.append({
            "id": experiment_id, "mode": mode,
            "fct_sha256": verified["fct_sha256"],
            "moe_batch_us": stats["tags"]["2"]["synthetic_batch_completion_us"],
            "moe_p99_fct_us": stats["tags"]["2"]["p99_fct_us"],
            "background_p99_fct_us": stats["tags"]["1"]["p99_fct_us"],
            "background_batch_us": stats["tags"]["1"]["synthetic_batch_completion_us"],
            "cnp": cnp_totals(next(raw.glob("*_out_cnp.txt"))),
            "pfc_events": len(next(raw.glob("*_out_pfc.txt")).read_text().splitlines()),
            "uplink": uplink_summary(next(raw.glob("*_out_uplink.txt"))),
            "diagnostics": diagnostics(mode, log),
            "resource": verified["resource"],
        })
    candidate = cells[-1]
    for cell in cells[:-1]:
        cell["classreserve_vs_baseline_moe_change_pct"] = 100 * (
            candidate["moe_batch_us"] / cell["moe_batch_us"] - 1)
        cell["classreserve_vs_baseline_bg_p99_change_pct"] = 100 * (
            candidate["background_p99_fct_us"] / cell["background_p99_fct_us"] - 1)
    output = {
        "evidence_level": "single independent demand seed calibration; not formal efficacy",
        "demand_seed": 20262501,
        "source_sha": verified["source_sha"],
        "trace_sha256": verified["trace_sha256"],
        "topology_sha256": verified["topology_sha256"],
        "cells": cells,
    }
    path = ROOT / "docs" / "research" / "evidence" / "ws25-calibration-seed01.json"
    path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"cells": len(cells), "output": str(path)}, sort_keys=True))


if __name__ == "__main__":
    main()
