#!/usr/bin/env python3
"""Run the frozen WS-28 factorial resource and deterministic-replay pilot."""
import argparse
import json
import re
from pathlib import Path

import run_ws28_ablation as ablation
import run_ws28_native_resource as native_resource


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/research/evidence/ws28-resource-plan-v2.json"
SUMMARY = ROOT / "results/ws28-resource-summary.json"
RECEIPTS = ROOT / "results/ws28-resource-receipts.jsonl"
MODES = tuple(ablation.FACTORS)


def configure(plan):
    native_resource.native.SOURCE_SHA = plan["source_sha"]
    native_resource.native.MODES = MODES
    native_resource.PLAN = PLAN
    native_resource.SUMMARY = SUMMARY
    native_resource.RECEIPTS = RECEIPTS
    engine = native_resource.native.configure()
    original_verify = engine.verify

    def verify(cell):
        row = original_verify(cell)
        log = (ROOT / "results" / cell["id"] / "logs/config.log").read_text(
            encoding="utf-8", errors="replace")
        lines = [line for line in log.splitlines() if line.startswith("WS28_FACTOR ")]
        if len(lines) != 1:
            raise RuntimeError("WS-28 resource factor receipt missing: " + cell["id"])
        fields = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", lines[0])}
        if tuple(fields.get(key) for key in ("mode", "background_weight",
                                              "background_routing")) != ablation.FACTORS[cell["mode"]]:
            raise RuntimeError("WS-28 resource factor branch mismatch: " + cell["id"])
        row["factors"] = fields
        return row

    engine.verify = verify
    return engine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("audit", "run", "verify"))
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    if (plan["kind"] != "WS-28 factorial mode resource pilot" or
            len(plan["cells"]) != sum(plan["stages"])):
        raise RuntimeError("WS-28 resource plan is incomplete")
    for order, cell in enumerate(plan["cells"], 1):
        if (cell["mode"] not in MODES or cell["stage_cap"] not in plan["stages"] or
                cell["seed"] != 20262501 or cell["background"] != 192 or
                cell["role"] != "resource_only" or cell["run_order"] != order or
                cell["batch"] != plan["stages"].index(cell["stage_cap"]) + 1):
            raise RuntimeError("WS-28 resource cell differs from plan")
        if ablation.engine.sha(ROOT / "config" / cell["trace"]) != cell["trace_sha256"]:
            raise RuntimeError("WS-28 resource trace changed")
    engine = configure(plan)
    if args.phase == "audit":
        print(json.dumps({"cells": len(plan["cells"]), "stages": plan["stages"],
                          "source_sha": plan["source_sha"]}, sort_keys=True))
    elif args.phase == "run":
        native_resource.run(engine, plan)
    else:
        rows = [row for cap in plan["stages"] for row in native_resource.verified_stage(
            engine, [cell for cell in plan["cells"] if cell["stage_cap"] == cap], cap)]
        print(json.dumps({"verified_cells": len(rows)}, sort_keys=True))


if __name__ == "__main__":
    main()
