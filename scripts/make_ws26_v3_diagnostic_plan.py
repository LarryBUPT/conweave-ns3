#!/usr/bin/env python3
"""Freeze bounded non-perturbing diagnostics for the WS-26 v3 pilot tails."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "results/ws26-v3-independent-pilot-r2"
VERIFIED = PILOT / "high-verified.json"
OUTPUT = ROOT / "docs/research/evidence/ws26-v3-tail-diagnostic-plan.json"
SOURCE_SHA = "593038416fa16f4982b600d256b563260f9106a8"
TOPOLOGY_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
SEEDS = (20262690, 20262691, 20262692, 20262693)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    verified = json.loads(VERIFIED.read_text(encoding="utf-8"))
    rows = verified["cells"]
    if verified["verified"] != 28 or verified["requested"] != 28:
        raise RuntimeError("The high pilot must be verified 28/28 first")
    cells = []
    for seed in SEEDS:
        for mode in ("fecmp", "classreserve3"):
            matches = [r for r in rows if r["seed"] == seed and r["mode"] == mode
                       and r["ws25_diag"] == 0]
            if len(matches) != 1:
                raise RuntimeError("Missing paired high cell: %d %s" % (seed, mode))
            row = matches[0]
            cell = {"id": "20261008-200000-ws26v3diag-p%02d-b192-%s" %
                          (seed % 100, mode),
                    "seed": seed, "mode": mode, "stage": "tail_diagnostic",
                    "background": 192, "expected_flows": 16576,
                    "trace_sha256": None, "expected_fct_sha256": row["fct_sha256"],
                    "pfc": 1, "irn": 1, "ns3_seed": 1, "ws25_diag": 1,
                    "ws26_time_probe": 0}
            plan = json.loads((ROOT / "docs/research/evidence/ws26-v3-pilot-plan.json")
                              .read_text(encoding="utf-8"))
            trace_rows = [x for x in plan["cells"] if x["seed"] == seed and
                          x["background"] == 192 and x["mode"] == mode and
                          x["ws25_diag"] == 0]
            if len(trace_rows) != 1:
                raise RuntimeError("Cannot resolve frozen trace: %d %s" % (seed, mode))
            cell["trace"] = trace_rows[0]["trace"]
            cell["trace_sha256"] = trace_rows[0]["trace_sha256"]
            cell["run_order"] = len(cells) + 1
            cells.append(cell)
    if len({cell["id"] for cell in cells}) != 8:
        raise RuntimeError("Diagnostic IDs are not unique")
    for cell in cells:
        if (ROOT / "results" / cell["id"]).exists():
            raise RuntimeError("Diagnostic ID already exists: " + cell["id"])
    result = {
        "purpose": "Per-QP CNP and per-hop queue/wait diagnosis of the four v3 high-pilot pairs",
        "evidence_level": "exploratory diagnosis only; not a new efficacy sample",
        "source_sha": SOURCE_SHA,
        "topology_sha256": TOPOLOGY_SHA,
        "topology": "topo_1280_400G_400G_OS1",
        "parameters": {"bw": 400, "buffer": 9, "pfc": 1, "irn": 1,
                        "netload": 10, "simul_time": "0.01", "ws25_diag": 1,
                        "ws26_time_probe": 0, "cap": 1},
        "cells": cells,
        "acceptance": [
            "Before build, query every ID and confirm no existing metadata, PID, or raw.",
            "Confirm no other user job, active ns-3 process, held lock, or resource stop-line breach.",
            "Start the resource watcher before each run and require its first sample.",
            "Require exact source, trace, topology, parameter, full-QP completion, raw, and resource receipts.",
            "Require each diagnostic FCT SHA-256 to equal expected_fct_sha256 from the v2 high pilot.",
            "Parse every WS25_QP and WS13_HOP row; report per-flow CNP/recovery and per-hop queue/wait for all 192 background QPs.",
            "Stop on any identity, completion, resource, or FCT non-perturbation failure; retain the failed ID and do not start later cells."
        ]}
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print("Wrote %d diagnostic cells to %s" % (len(cells), OUTPUT))


if __name__ == "__main__":
    main()
