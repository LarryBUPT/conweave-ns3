#!/usr/bin/env python3
"""Verify the WS-21 same-SHA long-tail feedback engineering pair."""

import argparse
import hashlib
import json
import math
import re
import statistics
from pathlib import Path

from verify_ws21_identity import verify as verify_identity


EXPECTED_FLOWS = 16576
EXPECTED_BYTES = 1744830464
TRACE_SHA = "9996372ea22158ca995937c727b6fef20559e0ce910b22e77529d9a8061b0cc3"
TOPOLOGY_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
FEEDBACK_RE = re.compile(r"^WS21_FEEDBACK\s+(.*)$", re.M)
COMMON_PARAMETERS = (
    "lb", "pfc", "irn", "bw", "buffer", "topo", "cdf", "simul_time",
    "netload", "flow_file", "ws18_admission", "ws18_path",
    "ws18_admission_rate_gbps", "ws21_identity", "ws21_port_events",
    "ws21_port_max_bytes", "ws13_diag",
)
LOG_FILES = ("config.log", "simulation.log", "worker.log")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def feedback_summary(path):
    matches = FEEDBACK_RE.findall(path.read_text(encoding="utf-8", errors="replace"))
    if len(matches) != 1:
        raise ValueError("expected exactly one WS21_FEEDBACK summary in {}".format(path))
    values = {}
    for item in matches[0].split():
        key, value = item.split("=", 1)
        values[key] = int(value)
    return values


def fct_deltas(off_path, on_path):
    def read(path):
        result = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            columns = line.split()
            if columns:
                result[tuple(columns[:6])] = int(columns[6])
        return result

    off, on = read(off_path), read(on_path)
    if set(off) != set(on):
        return {"same_flow_keys": False, "changed_flows": None}
    deltas = [on[key] - off[key] for key in off]
    ordered_off = sorted(off.values())
    ordered_on = sorted(on.values())

    def nearest_rank(values, percentile):
        return values[min(len(values) - 1, int(math.ceil(len(values) * percentile)) - 1)]

    return {
        "same_flow_keys": True,
        "flow_count": len(deltas),
        "changed_flows": sum(delta != 0 for delta in deltas),
        "fct_decreased_flows": sum(delta < 0 for delta in deltas),
        "fct_increased_flows": sum(delta > 0 for delta in deltas),
        "delta_ns_sum": sum(deltas),
        "delta_ns_mean": sum(deltas) / float(len(deltas)),
        "delta_ns_median": statistics.median(deltas),
        "delta_ns_min": min(deltas),
        "delta_ns_max": max(deltas),
        "off_fct_ns_p50_p90_p99": [nearest_rank(ordered_off, p) for p in (0.5, 0.9, 0.99)],
        "on_fct_ns_p50_p90_p99": [nearest_rank(ordered_on, p) for p in (0.5, 0.9, 0.99)],
    }


def inspect_cell(results, experiment_id, feedback_enabled, source_sha):
    base = results / experiment_id
    metadata = json.loads((base / "metadata.json").read_text(encoding="utf-8"))
    if metadata.get("status") != "SUCCEEDED" or metadata.get("git_commit") != source_sha:
        raise ValueError("{} status/source SHA mismatch".format(experiment_id))
    params = metadata["parameters"]
    expected = {"lb": "ws18", "pfc": 0, "irn": 1, "ws18_admission": 0,
                "ws18_path": 0, "ws13_diag": 1, "ws21_identity": 1,
                "ws21_feedback": feedback_enabled, "ws21_port_events": 0}
    if any(params.get(key) != value for key, value in expected.items()):
        raise ValueError("{} has unexpected parameters: {}".format(experiment_id, params))
    if metadata.get("seed") != 1:
        raise ValueError("{} ns-3 seed is not 1".format(experiment_id))

    for filename, expected_hash in (("traffic_trace.txt", TRACE_SHA),
                                    ("topology.txt", TOPOLOGY_SHA)):
        if sha256(base / "config" / filename) != expected_hash:
            raise ValueError("{} {} hash mismatch".format(experiment_id, filename))

    raw_id = str(metadata["raw_directory"])
    raw = base / "raw" / raw_id
    fct = raw / (raw_id + "_out_fct.txt")
    ws18 = raw / (raw_id + "_out_ws18.txt")
    identity_file = raw / (raw_id + "_out_ws21_identity.txt")
    fct_rows = [line for line in fct.read_text(encoding="utf-8").splitlines() if line.strip()]
    ws18_rows = [line.split() for line in ws18.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(fct_rows) != EXPECTED_FLOWS or len(ws18_rows) != EXPECTED_FLOWS:
        raise ValueError("{} flow completion mismatch".format(experiment_id))
    byte_total = sum(int(row[6]) for row in ws18_rows)
    if byte_total != EXPECTED_BYTES:
        raise ValueError("{} byte conservation mismatch: {}".format(experiment_id, byte_total))
    identity = verify_identity(ws18, identity_file, base / "config" / "topology.txt")
    if not identity.get("complete"):
        raise ValueError("{} identity check failed: {}".format(experiment_id, identity))

    log_sizes = {}
    for filename in LOG_FILES:
        candidates = (base / "logs" / filename, raw / filename)
        path = next((candidate for candidate in candidates if candidate.exists()), None)
        if path is None:
            raise ValueError("{} is missing {}".format(experiment_id, filename))
        size = path.stat().st_size
        if size > 50 * 1024 * 1024:
            raise ValueError("{} {} exceeds 50 MiB".format(experiment_id, filename))
        log_sizes[filename] = size

    return {
        "experiment_id": experiment_id,
        "status": metadata["status"],
        "git_commit": metadata["git_commit"],
        "input_flow_sha256": metadata["input_flow_sha256"],
        "topology_sha256": metadata["topology_sha256"],
        "raw_directory": raw_id,
        "feedback_enabled": feedback_enabled,
        "fct_rows": len(fct_rows),
        "provided_bytes": byte_total,
        "fct_sha256": sha256(fct),
        "ws18_sha256": sha256(ws18),
        "identity": identity,
        "log_bytes": log_sizes,
        "metadata": metadata,
        "raw": raw,
    }


def verify(results, off_id, on_id, source_sha, off_peak_rss_mib=None,
           on_peak_rss_mib=None):
    off = inspect_cell(results, off_id, 0, source_sha)
    on = inspect_cell(results, on_id, 1, source_sha)
    off_params, on_params = off["metadata"]["parameters"], on["metadata"]["parameters"]
    if any(off_params.get(key) != on_params.get(key) for key in COMMON_PARAMETERS):
        raise ValueError("off/on common parameters differ")
    failures = []
    shared_input = all(off[key] == on[key] for key in ("input_flow_sha256", "topology_sha256"))
    same_fct = off["fct_sha256"] == on["fct_sha256"]
    same_ws18 = off["ws18_sha256"] == on["ws18_sha256"]
    if not shared_input:
        failures.append("paired trace/topology hashes differ")
    if not same_fct:
        failures.append("FCT raw differs between feedback-off and feedback-on")
    if not same_ws18:
        failures.append("WS18 timing raw differs between feedback-off and feedback-on")
    if not off["identity"].get("complete") or not on["identity"].get("complete"):
        failures.append("path identity check failed")

    summary = feedback_summary(on["raw"] / "config.log")
    if summary.get("generated") != summary.get("delivered"):
        failures.append("feedback generated/delivered counts differ")
    for key in ("rejected", "expired", "hop_rejects", "sequence_gaps"):
        if summary.get(key) != 0:
            failures.append("feedback {} must be zero, got {}".format(key, summary.get(key)))
    if summary.get("hop_enqueues") != summary.get("hop_dequeues"):
        failures.append("feedback per-hop enqueue/dequeue counts differ")
    if summary.get("hop_bytes", 0) < summary.get("delivered_bytes", 0):
        failures.append("feedback hop bytes are less than delivered packet bytes")
    if summary.get("age_max_ns", 0) > 10000:
        failures.append("feedback maximum age exceeds 10 us")
    if summary.get("cache_peak", 0) > 16384:
        failures.append("feedback cache exceeded its key bound")
    on["feedback"] = summary
    deltas = fct_deltas(off["raw"] / (off["metadata"]["raw_directory"] + "_out_fct.txt"),
                        on["raw"] / (on["metadata"]["raw_directory"] + "_out_fct.txt"))
    resource_receipt = {
        "available": off_peak_rss_mib is not None and on_peak_rss_mib is not None,
        "off_peak_rss_mib": off_peak_rss_mib,
        "on_peak_rss_mib": on_peak_rss_mib,
    }
    if not resource_receipt["available"]:
        resource_receipt["reason"] = (
            "no per-experiment peak RSS sample was recorded while either simulation was active"
        )
        failures.append("per-experiment peak RSS receipt missing")
    off_timing = {key: off["metadata"].get(key) for key in ("started_utc", "finished_utc")}
    on_timing = {key: on["metadata"].get(key) for key in ("started_utc", "finished_utc")}
    del off["metadata"], on["metadata"], off["raw"], on["raw"]
    return {
        "analysis_complete": True,
        "gate_pass": not failures,
        "failures": failures,
        "off": off,
        "on": on,
        "run_times": {"off": off_timing, "on": on_timing},
        "paired_fct_delta": deltas,
        "resource_receipt": resource_receipt,
        "interpretation": "feedback transport may be assessed from aggregate counters; any application timing change fails the non-perturbation gate and is not a routing benefit claim",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--off", required=True)
    parser.add_argument("--on", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--off-peak-rss-mib", type=float)
    parser.add_argument("--on-peak-rss-mib", type=float)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.results, args.off, args.on, args.source_sha,
                    args.off_peak_rss_mib, args.on_peak_rss_mib)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if not result["gate_pass"]:
        return 1


if __name__ == "__main__":
    main()
