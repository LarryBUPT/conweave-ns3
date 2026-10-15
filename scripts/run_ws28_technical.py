#!/usr/bin/env python3
"""Run and verify the frozen six-arm WS-28 technical correctness plan."""
import argparse
import json
import re
from pathlib import Path

import run_ws28_ablation as ablation
import run_ws28_native_correctness as native_check


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/research/evidence/ws28-technical-plan.json"
RESULT = ROOT / "docs/research/evidence/ws28-technical-results.json"
PROGRESS = ROOT / "results/ws28-technical-progress.json"


def verify(cell, source_sha):
    native_check.native.SOURCE_SHA = source_sha
    row = native_check.verify(cell)
    log = (ROOT / "results" / cell["id"] / "logs/config.log").read_text(
        encoding="utf-8", errors="replace")
    if cell["mode"] in ablation.FACTORS:
        lines = [line for line in log.splitlines() if line.startswith("WS28_FACTOR ")]
        if len(lines) != 1:
            raise RuntimeError("WS-28 technical factor receipt missing: " + cell["id"])
        fields = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", lines[0])}
        if tuple(fields.get(key) for key in ("mode", "background_weight",
                                              "background_routing")) != ablation.FACTORS[cell["mode"]]:
            raise RuntimeError("WS-28 technical factor branch mismatch: " + cell["id"])
        row["factors"] = fields
    elif cell["mode"] == "classreserve":
        if "WS28_FACTOR mode=21 background_weight=1 background_routing=1" not in log:
            raise RuntimeError("original ClassReserve factor receipt missing")
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("run", "verify"))
    parser.add_argument("--limit", type=int, default=6)
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    if plan["kind"] != "WS-28 six-arm technical correctness" or len(plan["cells"]) != 6:
        raise RuntimeError("WS-28 technical plan is incomplete")
    native_check.native.SOURCE_SHA = plan["source_sha"]
    rows = []
    for cell in plan["cells"][:args.limit]:
        if ablation.engine.sha(ROOT / "config" / cell["trace"]) != cell["trace_sha256"]:
            raise RuntimeError("WS-28 technical trace changed")
        if args.phase == "run" and not (ROOT / "results" / cell["id"]).exists():
            native_check.run_cell(cell)
        row = verify(cell, plan["source_sha"])
        rows.append(row)
        PROGRESS.parent.mkdir(parents=True, exist_ok=True)
        PROGRESS.write_text(json.dumps({"source_sha": plan["source_sha"],
                                        "verified_cells": rows}, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
        print(json.dumps({"verified": len(rows), "id": cell["id"]}), flush=True)
    if args.limit == 6:
        by_mode = {row["mode"]: row for row in rows}
        if by_mode["classreserve"]["fct_sha256"] != by_mode["cr-a1-b1"]["fct_sha256"]:
            raise RuntimeError("A=1,B=1 differs from original ClassReserve on identical input")
        final = {"source_sha": plan["source_sha"], "verified_cells": len(rows),
                 "original_alias_fct_equal": True, "rows": rows}
        encoded = json.dumps(final, indent=2, sort_keys=True) + "\n"
        if RESULT.exists() and RESULT.read_text(encoding="utf-8") != encoded:
            raise RuntimeError("WS-28 technical result differs from prior verification")
        RESULT.write_text(encoded, encoding="utf-8")


if __name__ == "__main__":
    main()
