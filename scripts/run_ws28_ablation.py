#!/usr/bin/env python3
"""Execute and verify the frozen WS-28 two-factor matrix."""
import argparse
import json
import re
from pathlib import Path

import run_ws25_formal as engine


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/research/evidence/ws28-ablation-plan.json"
RESULT = ROOT / "docs/research/evidence/ws28-ablation-execution.json"
SUMMARY = ROOT / "results/ws28-ablation-summary.json"
RECEIPTS = ROOT / "results/ws28-ablation-receipts.jsonl"
FACTORS = {"cr-a0-b0": (25, 0, 0), "cr-a1-b0": (26, 1, 0),
           "cr-a0-b1": (27, 0, 1), "cr-a1-b1": (21, 1, 1)}


def configure(plan):
    engine.MANIFEST = ROOT / "docs/research/evidence/ws28-ablation-inputs.json"
    engine.PLAN = PLAN
    engine.RESULT = RESULT
    engine.SUMMARY = SUMMARY
    engine.RECEIPTS = RECEIPTS
    engine.pilot.RECEIPTS = RECEIPTS
    engine.pilot.POLL_SECONDS = 180
    engine.SOURCE_SHA = plan["source_sha"]
    engine.TOPO_SHA = plan["topology_sha256"]
    engine.MAX_CONCURRENT = plan["max_concurrent"]
    engine.BUILD_GROUP_SIZE = min(4, engine.MAX_CONCURRENT)
    engine.RANDOMIZATION_SEED = plan["randomization_seed"]

    original_verify = engine.verify

    def verify(cell):
        row = original_verify(cell)
        log = (ROOT / "results" / cell["id"] / "logs/config.log").read_text(
            encoding="utf-8", errors="replace")
        if cell["mode"] in FACTORS:
            expected = FACTORS[cell["mode"]]
            lines = [line for line in log.splitlines() if line.startswith("WS28_FACTOR ")]
            if len(lines) != 1:
                raise RuntimeError("WS-28 factor receipt missing: " + cell["id"])
            values = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", lines[0])}
            if tuple(values.get(key) for key in ("mode", "background_weight",
                                                  "background_routing")) != expected:
                raise RuntimeError("WS-28 factor branch mismatch: " + cell["id"])
            matches = [line for line in log.splitlines()
                       if line.startswith("WS25_CLASSRESERVE ")]
            if len(matches) != 1:
                raise RuntimeError("ClassReserve branch receipt missing: " + cell["id"])
            counts = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", matches[0])}
            if (counts.get("queue_violations") != 0 or
                    counts.get("moe_flow_new", 0) <= 0 or
                    counts.get("background_new_flows", 0) <= 0):
                raise RuntimeError("ClassReserve branch or queue invariant failed: " + cell["id"])
            row["factors"] = values
            row["classreserve"] = counts
        return row

    engine.verify = verify

    def resume_summary(cells, batches):
        empty = {"kind": "WS-28 independent-demand two-factor ablation",
                 "source_sha": engine.SOURCE_SHA,
                 "randomization_seed": engine.RANDOMIZATION_SEED,
                 "max_concurrent": engine.MAX_CONCURRENT,
                 "batches": [], "verified_cells": []}
        if not SUMMARY.exists():
            return empty, 0
        saved = json.loads(SUMMARY.read_text(encoding="utf-8"))
        for key in ("kind", "source_sha", "randomization_seed", "max_concurrent"):
            if saved.get(key) != empty[key]:
                raise RuntimeError("WS-28 ablation resume header mismatch: " + key)
        done = len(saved["batches"])
        if done > len(batches):
            raise RuntimeError("WS-28 ablation has too many completed batches")
        offset = 0
        for index, row in enumerate(saved["batches"]):
            if row["batch"] != index + 1 or row["cells"] != len(batches[index]):
                raise RuntimeError("WS-28 ablation batch receipt mismatch")
            offset += len(batches[index])
        if len(saved["verified_cells"]) != offset:
            raise RuntimeError("WS-28 ablation verified-cell count mismatch")
        for cell, row in zip(cells[:offset], saved["verified_cells"]):
            if cell["id"] != row["id"] or verify(cell) != row:
                raise RuntimeError("WS-28 ablation raw changed: " + cell["id"])
        return saved, done

    engine.resume_summary = resume_summary


def validate_plan(plan):
    if (plan["kind"] != "WS-28 independent-demand two-factor ablation" or
            len(plan["cells"]) != 120 or len(plan["demand_seeds"]) != 24):
        raise RuntimeError("WS-28 ablation plan is incomplete")
    ids = set()
    pairs = set()
    for cell in plan["cells"]:
        if cell["id"] in ids or (cell["seed"], cell["mode"]) in pairs:
            raise RuntimeError("WS-28 ablation plan has duplicate cells")
        ids.add(cell["id"])
        pairs.add((cell["seed"], cell["mode"]))
        if engine.sha(ROOT / "config" / cell["trace"]) != cell["trace_sha256"]:
            raise RuntimeError("WS-28 ablation trace changed: " + cell["trace"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("audit", "prebuild", "run", "verify"))
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    validate_plan(plan)
    configure(plan)
    cells = plan["cells"]
    if args.phase == "audit":
        print(json.dumps({"cells": len(cells), "source_sha": plan["source_sha"],
                          "cap": plan["max_concurrent"]}, sort_keys=True))
    elif args.phase == "prebuild":
        engine.prebuild(cells)
    elif args.phase == "run":
        engine.execute(cells)
    else:
        rows = [engine.verify(cell) for cell in cells]
        print(json.dumps({"verified_cells": len(rows)}, sort_keys=True))


if __name__ == "__main__":
    main()
