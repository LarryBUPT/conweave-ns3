#!/usr/bin/env python3
"""Freeze, run and verify the same-input WS-28 native-mode comparison."""
import argparse
import json
import random
import re
from pathlib import Path

import run_ws27_matrix as prior


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = prior.SOURCE_SHA  # Exact WS-27 simulator source for paired fidelity.
MODES = ("drill", "conga", "letflow", "conweave")
SEEDS = tuple(range(20262721, 20262745))
PLAN = ROOT / "docs/research/evidence/ws28-native-plan.json"
RESULT = ROOT / "docs/research/evidence/ws28-native-execution.json"
RANDOMIZATION_SEED = 20262801
ID_PREFIX = "20261014-010000-ws28-native"


def configure():
    prior.configure("confirm")
    engine = prior.engine
    engine.PLAN = PLAN
    engine.LOCAL_PLAN = ROOT / "results/ws28-native-plan.json"
    engine.RESULT = RESULT
    engine.SUMMARY = ROOT / "results/ws28-native-summary.json"
    engine.RECEIPTS = ROOT / "results/ws28-native-receipts.jsonl"
    engine.pilot.RECEIPTS = engine.RECEIPTS
    engine.ID_PREFIX = ID_PREFIX
    engine.RANDOMIZATION_SEED = RANDOMIZATION_SEED
    engine.SOURCE_SHA = SOURCE_SHA
    engine.MAX_CONCURRENT = 12
    engine.BUILD_GROUP_SIZE = 6

    original_verify = engine.verify

    def verify(cell):
        row = original_verify(cell)
        log = (ROOT / "results" / cell["id"] / "logs/config.log").read_text(
            encoding="utf-8", errors="replace")
        if cell["mode"] == "conga":
            if "CONGA History" not in log or "Number of flowlet's timeout:" not in log:
                raise RuntimeError("CONGA branch receipt missing: " + cell["id"])
            match = re.search(r"Number of flowlet's timeout:(\d+)", log)
            row["native_dynamic"] = {"flowlet_timeouts": int(match.group(1))}
        elif cell["mode"] == "letflow":
            if "Letflow History" not in log:
                raise RuntimeError("LetFlow branch receipt missing: " + cell["id"])
            match = re.search(r"Number of flowlet's timeout:(\d+)", log)
            if not match:
                raise RuntimeError("LetFlow timeout receipt missing: " + cell["id"])
            row["native_dynamic"] = {"flowlet_timeouts": int(match.group(1))}
        elif cell["mode"] == "conweave":
            fields = {key: int(value) for key, value in
                      re.findall(r"Number of ([\w '()]+):\s*(\d+)", log)}
            if "ConWeave History" not in log or "Rerouting" not in fields or not any(
                    "INIT" in key and "Reply" in key for key in fields):
                raise RuntimeError("ConWeave branch receipt missing: " + cell["id"])
            row["native_dynamic"] = fields
        else:
            # DRILL executes its local queue decision per data packet. The
            # fixed source has no dedicated DRILL counter; code-path plus
            # output fingerprint are audited separately before interpretation.
            row["native_dynamic"] = {"dedicated_counter_available": False}
        return row

    engine.verify = verify

    def resume_summary(cells, batches):
        empty = {"kind": "WS-28 native-mode same-input comparison",
                 "source_sha": SOURCE_SHA, "randomization_seed": RANDOMIZATION_SEED,
                 "max_concurrent": 12, "batches": [], "verified_cells": []}
        if not engine.SUMMARY.exists():
            return empty, 0
        saved = json.loads(engine.SUMMARY.read_text(encoding="utf-8"))
        if any(saved.get(k) != empty[k] for k in
               ("kind", "source_sha", "randomization_seed", "max_concurrent")):
            raise RuntimeError("WS-28 native resume header mismatch")
        done = len(saved["batches"])
        if done > len(batches) or len(saved["verified_cells"]) != 12 * done:
            raise RuntimeError("WS-28 native resume is not a complete batch prefix")
        for number, batch in enumerate(saved["batches"], 1):
            if batch["batch"] != number or batch["cells"] != 12:
                raise RuntimeError("WS-28 native batch receipt mismatch")
        for cell, row in zip(cells[:12 * done], saved["verified_cells"]):
            if cell["id"] != row["id"] or verify(cell) != row:
                raise RuntimeError("WS-28 native raw changed: " + cell["id"])
        return saved, done

    engine.resume_summary = resume_summary
    return engine


def frozen_plan(engine):
    manifest = json.loads(engine.MANIFEST.read_text(encoding="utf-8"))
    if set(manifest["seeds"]) != {str(x) for x in SEEDS}:
        raise RuntimeError("Demand seed set changed")
    blocks = []
    for seed in SEEDS:
        item = manifest["seeds"][str(seed)]["levels"]["192"]
        trace = ROOT / "config" / item["file"]
        if item["flows"] != 16576 or engine.sha(trace) != item["sha256"]:
            raise RuntimeError("WS-28 input changed: " + str(trace))
        blocks.append([{"id": f"{ID_PREFIX}-s{seed}-b192-{mode}",
                        "seed": seed, "background": 192, "mode": mode,
                        "trace": item["file"], "trace_sha256": item["sha256"],
                        "input_flows": 16576, "expected_tags": {"1": 192, "2": 16384},
                        "role": "native_same_input"} for mode in MODES])
    rng = random.Random(RANDOMIZATION_SEED)
    rng.shuffle(blocks)
    cells = []
    for block in blocks:
        rng.shuffle(block)
        cells.extend(block)
    for order, cell in enumerate(cells, 1):
        cell["run_order"], cell["batch"] = order, (order - 1) // 12 + 1
    plan = {"kind": "WS-28 native-mode same-input comparison",
            "source_sha": SOURCE_SHA, "topology_sha256": prior.TOPO_SHA,
            "demand_seed_order": list(SEEDS), "background_levels": [192],
            "modes": list(MODES), "ns3_seed": 1, "pfc": 0, "irn": 1,
            "bw_gbps": 400, "buffer_mib": 9, "netload": 10,
            "simul_time": "0.01", "max_concurrent": 12,
            "randomization_seed": RANDOMIZATION_SEED,
            "paired_control": "WS-27 confirm ECMP, same simulator SHA and trace per seed",
            "cells": cells}
    encoded = json.dumps(plan, indent=2, sort_keys=True) + "\n"
    for path in (engine.PLAN, engine.LOCAL_PLAN):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_text(encoding="utf-8") != encoded:
            raise RuntimeError("Frozen WS-28 native plan changed: " + str(path))
        path.write_text(encoded, encoding="utf-8")
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("plan", "run", "verify"))
    args = parser.parse_args()
    engine = configure()
    plan = frozen_plan(engine)
    if args.phase == "plan":
        print(json.dumps({"cells": len(plan["cells"]), "source_sha": SOURCE_SHA,
                          "modes": MODES, "seeds": len(SEEDS)}))
    elif args.phase == "run":
        engine.execute(plan["cells"])
    else:
        rows = [engine.verify(cell) for cell in plan["cells"]]
        if len(rows) != 96:
            raise RuntimeError("Incomplete WS-28 native matrix")
        print(json.dumps({"verified_cells": len(rows)}))


if __name__ == "__main__":
    main()
