#!/usr/bin/env python3
"""Verify a same-SHA 40-flow WS-21 feedback off/on engineering pair."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from verify_ws21_identity import verify as verify_identity


EXPECTED_FLOWS = 40
EXPECTED_BYTES = 33849344
FEEDBACK_RE = re.compile(r"^WS21_FEEDBACK\s+(.*)$", re.M)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
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


def inspect_experiment(experiment_id, expected_feedback):
    base = Path("results") / experiment_id
    metadata = json.loads((base / "metadata.json").read_text(encoding="utf-8"))
    if metadata.get("status") != "SUCCEEDED":
        raise ValueError("{} did not succeed".format(experiment_id))
    params = metadata["parameters"]
    if (params.get("lb") != "ws18" or params.get("pfc") != 0 or
            params.get("irn") != 1 or params.get("ws21_identity") != 1 or
            params.get("ws21_feedback") != expected_feedback):
        raise ValueError("{} has unexpected mode/transport/feedback settings".format(experiment_id))

    raw_id = metadata["raw_directory"]
    raw = base / "raw" / raw_id
    fct = raw / (raw_id + "_out_fct.txt")
    ws18 = raw / (raw_id + "_out_ws18.txt")
    identity = raw / (raw_id + "_out_ws21_identity.txt")
    fct_rows = [line for line in fct.read_text(encoding="utf-8").splitlines() if line.strip()]
    ws18_rows = [line.split() for line in ws18.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(fct_rows) != EXPECTED_FLOWS or len(ws18_rows) != EXPECTED_FLOWS:
        raise ValueError("{} completed an unexpected number of flows".format(experiment_id))
    byte_total = sum(int(row[6]) for row in ws18_rows)
    if byte_total != EXPECTED_BYTES:
        raise ValueError("{} WS18 bytes do not match the frozen trace".format(experiment_id))
    identity_result = verify_identity(ws18, identity, base / "config" / "topology.txt")
    if not identity_result.get("complete"):
        raise ValueError("{} path identity check failed: {}".format(experiment_id, identity_result))

    item = {
        "experiment_id": experiment_id,
        "status": metadata["status"],
        "git_commit": metadata["git_commit"],
        "input_flow_sha256": metadata["input_flow_sha256"],
        "topology_sha256": metadata["topology_sha256"],
        "raw_directory": raw_id,
        "feedback_enabled": expected_feedback,
        "fct_rows": len(fct_rows),
        "provided_bytes": byte_total,
        "fct_sha256": sha256(fct),
        "ws18_sha256": sha256(ws18),
        "identity": identity_result,
    }
    if expected_feedback:
        summary = feedback_summary(raw / "config.log")
        if summary.get("generated") != summary.get("delivered"):
            raise ValueError("feedback reports were not all delivered")
        for key in ("rejected", "expired", "hop_rejects", "sequence_gaps"):
            if summary.get(key) != 0:
                raise ValueError("feedback summary reports {}={}".format(key, summary.get(key)))
        if summary.get("hop_enqueues") != summary.get("hop_dequeues"):
            raise ValueError("feedback per-hop queue enqueue/dequeue counts differ")
        if summary.get("hop_bytes", 0) < summary.get("delivered_bytes", 0):
            raise ValueError("per-hop feedback bytes are less than delivered packet bytes")
        item["feedback"] = summary
    return item


def verify(off_id, on_id):
    off = inspect_experiment(off_id, 0)
    on = inspect_experiment(on_id, 1)
    if off["git_commit"] != on["git_commit"]:
        raise ValueError("pair source commits differ")
    for key in ("input_flow_sha256", "topology_sha256", "fct_sha256", "ws18_sha256"):
        if off[key] != on[key]:
            raise ValueError("pair {} differs: {} vs {}".format(key, off[key], on[key]))
    return {
        "complete": True,
        "off": off,
        "on": on,
        "interpretation": "40-flow engineering gate only; no CE differentiation or performance claim",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--off", required=True, help="feedback-disabled experiment ID")
    parser.add_argument("--on", required=True, help="feedback-enabled experiment ID")
    parser.add_argument("--output", type=Path, help="optional JSON receipt path")
    args = parser.parse_args()
    result = verify(args.off, args.on)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
