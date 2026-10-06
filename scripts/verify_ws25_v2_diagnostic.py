#!/usr/bin/env python3
"""Check v2 mixed8 diagnostics against the same-input default-off cell."""
import collections
import json
import re
from pathlib import Path

import verify_ws25_v2_correctness as preflight

ROOT = Path(__file__).resolve().parents[1]
OFF = "20261006-070000-ws25-v2-pre-mixed8"
ON = "20261006-123000-ws25-v2-diag-mixed8"
TRACE = "ws25_v1fix_mixed8.txt"
COUNTERS = ("rx_ooo_packets", "sack_feedback", "cnp_feedback",
            "repeated_sends", "timeout_recovery")


def fields(line):
    return {key: int(value) for key, value in re.findall(r"(\w+)=(-?\d+)", line)}


def main():
    off = preflight.verify(OFF, "destspread", TRACE)
    on = preflight.verify(ON, "destspread", TRACE, diag=1)
    if off["fct_sha256"] != on["fct_sha256"]:
        raise RuntimeError("Diagnostic changed the complete FCT raw fingerprint")
    lines = (ROOT / "results" / ON / "logs" / "config.log").read_text(
        encoding="utf-8", errors="replace").splitlines()
    qp = [fields(line) for line in lines if line.startswith("WS25_QP ")]
    if len(qp) != 8 or len({row["flow_id"] for row in qp}) != 8:
        raise RuntimeError("Per-QP diagnostic rows missing or duplicated")
    if collections.Counter(row["tag"] for row in qp) != {1: 4, 2: 4}:
        raise RuntimeError("Per-QP class identity mismatch")
    if any(key not in row or row[key] < 0 for row in qp for key in COUNTERS):
        raise RuntimeError("Per-QP counter missing or invalid")
    hops = [fields(line) for line in lines if line.startswith("WS13_HOP ")]
    if not hops:
        raise RuntimeError("Background flow-hop observations missing")
    inflight = [fields(line) for line in lines if line.startswith("WS13_INFLIGHT ")]
    if len(inflight) != 1 or inflight[0].get("unpaired") != 0:
        raise RuntimeError("Flow-hop observations did not close")
    by_tag = {}
    for tag in (1, 2):
        rows = [row for row in qp if row["tag"] == tag]
        by_tag[str(tag)] = {"qp_count": len(rows), **{
            key: sum(row[key] for row in rows) for key in COUNTERS}}
    output = {"role": "same-input correctness and nonintrusive diagnostic only",
              "source_sha": preflight.SHA, "off_id": OFF, "on_id": ON,
              "fct_sha256": on["fct_sha256"], "qp_by_tag": by_tag,
              "background_hop_rows": len(hops), "unpaired_inflight": 0,
              "resource": on["resource"], "not_independent_efficacy": True}
    destination = ROOT / "docs/research/evidence/ws25-v2-destspread-diagnostic.json"
    destination.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({"verified": True, "on_id": ON,
                      "fct_identical": True, "qp_by_tag": by_tag}, sort_keys=True))


if __name__ == "__main__":
    main()
