#!/usr/bin/env python3
"""Run and verify the frozen WS-27 paired demand matrices."""
import argparse
import json
import random
import re
from pathlib import Path

import run_ws25_formal as engine

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "ee236f27920aa56b3dd562ed971e5abee9e1e659"
MODES = ("fecmp", "classreserve", "guardhash-v2", "harmgate-v2")
LEVELS = (0, 64, 128, 192)
SCREEN = tuple(range(20262701, 20262709))
CONFIRM = tuple(range(20262721, 20262745))
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
CAPS = {"screen": 4, "confirm": 12}


def configure(stage):
    seeds = SCREEN if stage == "screen" else CONFIRM
    levels = (192,) if stage == "screen" else LEVELS
    cap = CAPS[stage]
    stem = "ws27-" + stage
    engine.MANIFEST = ROOT / ("docs/research/evidence/" + stem + "-inputs.json")
    engine.PLAN = ROOT / ("docs/research/evidence/" + stem + "-plan.json")
    engine.LOCAL_PLAN = ROOT / ("results/" + stem + "-plan.json")
    engine.RESULT = ROOT / ("docs/research/evidence/" + stem + "-execution.json")
    engine.SUMMARY = ROOT / ("results/" + stem + "-summary.json")
    engine.RECEIPTS = ROOT / ("results/" + stem + "-receipts.jsonl")
    engine.SEED_ORDER = seeds
    engine.LEVELS = levels
    engine.MODES = MODES
    engine.MAX_CONCURRENT = cap
    engine.RANDOMIZATION_SEED = 20262710 if stage == "screen" else 20262745
    engine.ID_PREFIX = "20261013-030000-" + stem
    engine.SOURCE_SHA = SOURCE_SHA
    engine.TOPO_SHA = TOPO_SHA
    engine.pilot.POLL_SECONDS = 1800

    original_verify = engine.verify

    def verify(cell):
        result = original_verify(cell)
        if cell["mode"] in ("guardhash-v2", "harmgate-v2"):
            folder = ROOT / "results" / cell["id"]
            log = (folder / "logs/config.log").read_text(encoding="utf-8", errors="replace")
            rows = [row for row in log.splitlines() if row.startswith("WS27_GUARD ")]
            if len(rows) != 1:
                raise RuntimeError("WS-27 mechanism receipt missing: " + cell["id"])
            counters = {key: int(value) for key, value in
                        re.findall(r"(\w+)=(\d+)", rows[0])}
            code = 23 if cell["mode"] == "guardhash-v2" else 24
            if not (counters.get("mode") == code and
                    counters.get("queue_violations") == 0 and
                    counters.get("moe_packets", 0) > 0 and
                    counters.get("new_flows", 0) > 0 and
                    counters.get("reused_packets", 0) > 0 and
                    counters.get("moe_packets") == counters.get("new_flows") +
                    counters.get("reused_packets")):
                raise RuntimeError("WS-27 cache or queue invariant failed: " + cell["id"])
            result["ws27_guard"] = counters
        return result

    engine.verify = verify

    def frozen_plan():
        manifest = json.loads(engine.MANIFEST.read_text(encoding="utf-8"))
        if set(manifest["seeds"]) != {str(seed) for seed in seeds}:
            raise RuntimeError("WS-27 stage seed set differs from frozen manifest")
        blocks = []
        for seed in seeds:
            for background in levels:
                item = manifest["seeds"][str(seed)]["levels"][str(background)]
                if engine.sha(ROOT / "config" / item["file"]) != item["sha256"]:
                    raise RuntimeError("WS-27 trace hash changed: " + item["file"])
                block = []
                for mode in MODES:
                    block.append({"id": "%s-s%d-b%03d-%s" %
                                  (engine.ID_PREFIX, seed, background, mode),
                                  "seed": seed, "background": background,
                                  "mode": mode, "trace": item["file"],
                                  "trace_sha256": item["sha256"],
                                  "input_flows": item["flows"],
                                  "expected_tags": ({"2": 16384} if background == 0 else
                                                    {"1": background, "2": 16384}),
                                  "role": stage})
                blocks.append(block)
        rng = random.Random(engine.RANDOMIZATION_SEED)
        rng.shuffle(blocks)
        cells = []
        for block in blocks:
            rng.shuffle(block)
            cells.extend(block)
        for order, cell in enumerate(cells, 1):
            cell["run_order"] = order
            cell["batch"] = (order - 1) // cap + 1
        plan = {"kind": "WS-27 independent-demand " + stage,
                "source_sha": SOURCE_SHA, "topology_sha256": TOPO_SHA,
                "demand_seed_order": list(seeds), "background_levels": list(levels),
                "modes": list(MODES), "ns3_seed": 1, "pfc": 0, "irn": 1,
                "bw_gbps": 400, "buffer_mib": 9, "netload": 10,
                "simul_time": "0.01", "max_concurrent": cap,
                "randomization_seed": engine.RANDOMIZATION_SEED,
                "cells": cells}
        encoded = json.dumps(plan, indent=2, sort_keys=True) + "\n"
        for path in (engine.PLAN, engine.LOCAL_PLAN):
            if path.exists() and path.read_text(encoding="utf-8") != encoded:
                raise RuntimeError("Frozen WS-27 plan changed: " + str(path))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(encoded, encoding="utf-8")
        return plan

    engine.frozen_plan = frozen_plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("screen", "confirm"))
    parser.add_argument("phase", choices=("plan", "run", "verify"))
    args = parser.parse_args()
    configure(args.stage)
    plan = engine.frozen_plan()
    cells = plan["cells"]
    if args.phase == "plan":
        print(json.dumps({"stage": args.stage, "cells": len(cells),
                          "source_sha": SOURCE_SHA, "cap": CAPS[args.stage]}, sort_keys=True))
    elif args.phase == "run":
        engine.execute(cells)
    else:
        rows = [engine.verify(cell) for cell in cells]
        if len(rows) != len(cells):
            raise RuntimeError("WS-27 matrix is incomplete")
        print(json.dumps({"stage": args.stage, "verified_cells": len(rows)}, sort_keys=True))


if __name__ == "__main__":
    main()
