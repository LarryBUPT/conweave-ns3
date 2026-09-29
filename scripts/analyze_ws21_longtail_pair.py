#!/usr/bin/env python3
"""Verify and summarize the WS-21 long-tail diagnostic-only pair."""

import argparse
import collections
import datetime
import hashlib
import json
import math
from pathlib import Path

from verify_ws21_identity import verify as verify_identity
from verify_ws21_pair import verify_pair
from verify_ws21_port_events import verify as verify_port_events


TRACE_SHA = "9996372ea22158ca995937c727b6fef20559e0ce910b22e77529d9a8061b0cc3"
TOPOLOGY_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
SOURCE_SHA = "478eca21b626113aa9dc58a33085b0d0a287f740"
EXPECTED_FLOWS = 16576
EXPECTED_BYTES = 1744830464
TEXT_LOG_LIMIT_BYTES = 50 * 1024 * 1024
PORT_RAW_LIMIT_BYTES = 268435456


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def ws18_rows(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        values = [int(value) for value in line.split()]
        if len(values) != 12:
            raise ValueError("WS18 row must have 12 columns")
        flow_id, src, dst, sport, dport, tag, size, demand, release, finish, wait, total = values
        if finish - demand != total or release - demand != wait:
            raise ValueError("WS18 timing fields do not reconcile")
        rows.append({"id": flow_id, "src": src, "dst": dst, "sport": sport,
                     "dport": dport, "tag": tag, "size": size,
                     "demand": demand, "release": release, "finish": finish,
                     "wait": wait, "total": total})
    return rows


def summarize_cell(results, experiment_id, side):
    base = results / experiment_id
    meta = json.loads((base / "metadata.json").read_text(encoding="utf-8"))
    raw_id = str(meta["raw_directory"])
    raw = base / "raw" / raw_id
    ws18 = raw / (raw_id + "_out_ws18.txt")
    fct = raw / (raw_id + "_out_fct.txt")
    log = raw / "config.log"
    rows = ws18_rows(ws18)
    if len(rows) != EXPECTED_FLOWS:
        raise ValueError("%s has %d WS18 rows" % (experiment_id, len(rows)))
    event_counts = collections.Counter()
    event_times = []
    event_qps = set()
    unpaired = None
    for line in log.open(encoding="utf-8", errors="replace"):
        if line.startswith("WS13_QP "):
            fields = dict(part.split("=", 1) for part in line.split()[1:] if "=" in part)
            event_counts[fields["event"]] += 1
            event_qps.add(int(fields["flow_id"]))
            event_times.append(int(fields["time_ns"]))
        elif line.startswith("WS13_INFLIGHT "):
            unpaired = int(line.split("unpaired=", 1)[1].split()[0])
    if unpaired != 0:
        raise ValueError("%s WS13 in-flight packet accounting is incomplete" % experiment_id)
    hops = []
    for line in log.open(encoding="utf-8", errors="replace"):
        if line.startswith("WS13_HOP "):
            hops.append(dict(part.split("=", 1) for part in line.split()[1:] if "=" in part))
    size_groups = {"moe_8k": [row["total"] for row in rows if row["size"] == 8192],
                   "background_8m": [row["total"] for row in rows if row["size"] == 8388608]}
    fct_summary = {}
    for name, values in size_groups.items():
        if not values:
            fct_summary[name] = {"count": 0}
            continue
        fct_summary[name] = {
            "count": len(values),
            "p50_us": round(percentile(values, 0.50) / 1000.0, 3),
            "p95_us": round(percentile(values, 0.95) / 1000.0, 3),
            "p99_us": round(percentile(values, 0.99) / 1000.0, 3),
            "max_us": round(max(values) / 1000.0, 3),
            "percentile_method": "nearest-rank",
        }
    identity_path = raw / (raw_id + "_out_ws21_identity.txt")
    port_path = raw / (raw_id + "_out_ws21_port.txt")
    cell = {"experiment_id": experiment_id, "side": side,
            "status": meta["status"], "source_sha": meta["git_commit"],
            "trace_sha256": meta["input_flow_sha256"],
            "topology_sha256": meta["topology_sha256"],
            "parameters": meta["parameters"],
            "started_utc": meta["started_utc"], "finished_utc": meta["finished_utc"],
            "runtime_seconds": int((datetime.datetime.strptime(meta["finished_utc"],
                "%Y-%m-%dT%H:%M:%SZ") - datetime.datetime.strptime(meta["started_utc"],
                "%Y-%m-%dT%H:%M:%SZ")).total_seconds()),
            "raw_directory": raw_id, "completed_qps": len(rows),
            "completed_bytes": sum(row["size"] for row in rows),
            "fct_sha256": sha256(fct), "ws18_sha256": sha256(ws18),
            "fct_rows": len(fct.read_text(encoding="utf-8").splitlines()),
            "ws18_rows": len(rows), "ws18_fct_by_size": fct_summary,
            "ws13_log_bytes": log.stat().st_size,
            "ws13_qp_events": dict(sorted(event_counts.items())),
            "ws13_qp_count_with_events": len(event_qps),
            "ws13_event_time_ns_min": min(event_times) if event_times else None,
            "ws13_event_time_ns_max": max(event_times) if event_times else None,
            "ws13_hop_records": len(hops),
            "ws13_hop_max_queued_bytes": max((int(row["queued_bytes_max"]) for row in hops), default=0),
            "ws13_hop_max_cumulative_wait_ns": max((int(row["wait_ns_sum"]) for row in hops), default=0),
            "ws13_hop_max_single_wait_ns": max((int(row["wait_ns_max"]) for row in hops), default=0)}
    if side == "on":
        cell["identity"] = verify_identity(ws18, identity_path,
            base / "config" / "topology.txt")
        cell["port_events"] = verify_port_events(port_path, ws18)
        cell["port_event_raw_bytes"] = port_path.stat().st_size
        identity_rows = identity_path.read_text(encoding="utf-8").splitlines()[1:]
        ce_rows = [line.split() for line in identity_rows if line.startswith("destination ")]
        ce_counts = [int(row[8]) for row in ce_rows]
        cell["destination_ce"] = {"packets": sum(ce_counts),
                                  "qps_with_ce": sum(value > 0 for value in ce_counts),
                                  "qps_observed": len(ce_counts)}
    resource_path = base / "logs" / "resource_summary.json"
    cell["resources"] = json.loads(resource_path.read_text(encoding="utf-8"))
    return cell


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--off", required=True)
    parser.add_argument("--on", required=True)
    parser.add_argument("--source-sha", default=SOURCE_SHA)
    parser.add_argument("--trace-sha", default=TRACE_SHA)
    parser.add_argument("--topology-sha", default=TOPOLOGY_SHA)
    parser.add_argument("--expected-flows", type=int, default=EXPECTED_FLOWS)
    parser.add_argument("--expected-bytes", type=int, default=EXPECTED_BYTES)
    parser.add_argument("--ws13-diag", type=int, choices=(0, 1), default=1)
    parser.add_argument("--out", type=Path,
                        default=Path("docs/research/evidence/ws21-longtail-pair.json"))
    args = parser.parse_args()
    verified = verify_pair(args.results, args.off, args.on, args.source_sha,
                           args.trace_sha, args.topology_sha, args.expected_flows,
                           args.expected_bytes, args.ws13_diag)
    cells = [summarize_cell(args.results, args.off, "off"),
             summarize_cell(args.results, args.on, "on")]
    max_text_log = max(cell["resources"]["peaks_and_floors"]["max_largest_log_bytes"]
                       for cell in cells)
    port_bytes = cells[1]["port_event_raw_bytes"]
    port_overflow = cells[1]["port_events"]["overflow"]
    result = {"evidence_level": "long_tail_diagnostic_technical_pair",
              "effect_matrix": "NO-GO; not an efficacy comparison",
              "pair_verification": verified,
              "artifact_size_gates": {
                  "text_log_limit_bytes": TEXT_LOG_LIMIT_BYTES,
                  "largest_text_log_bytes": max_text_log,
                  "text_log_pass": max_text_log <= TEXT_LOG_LIMIT_BYTES,
                  "port_raw_limit_bytes": PORT_RAW_LIMIT_BYTES,
                  "port_raw_bytes": port_bytes,
                  "port_raw_overflow": port_overflow,
                  "port_raw_pass": port_bytes <= PORT_RAW_LIMIT_BYTES and port_overflow == 0,
              },
              "superseded_over_limit_attempt": {
                  "experiment_id": "20260929-130119-ws21-longtail-diagnostic",
                  "source_sha": "fdedcd770f22491a612e76372973538b16ca31b6",
                  "runtime_seconds": 303,
                  "config_log_bytes": 260177114,
                  "ws13_qp_log_lines": 1623113,
                  "ordinary_irn_ack_lines": 1610688,
                  "reason_excluded": "exceeded the 50 MiB text-log limit; kept as a diagnostic of probe overhead",
              },
              "cells": cells,
              "limits": [
                  "Pair validates diagnostic non-perturbation, QP/hop observations, path identity, and port-event completeness only.",
                  "CE observations are recorded on the selected route; no alternate-candidate comparison or real feedback packet was implemented.",
                  "No feedback delivery cost, age, loss, or stale-feedback fallback was measured.",
                  "Percentiles describe this single fixed trace and are not a performance or safety claim.",
                  "The stock analyzer's 2.005-2.060 s completion window excludes this trace, which starts at 2.000000-2.000350 s; summaries use all WS18 QP timings instead.",
              ]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print("Wrote %s" % args.out)


if __name__ == "__main__":
    main()
