#!/usr/bin/env python3
"""Freeze the independent screen of the sole DestSpread v2 correction."""
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "5a4334116bdb38466533204af51f6f12d77d07b4"
SIMULATOR_SHA = "206888df97e2fd5fd37656d51deda5fb6a4e96c1"
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
SEEDS = tuple(range(20262577, 20262581))
MODES = ("fecmp", "drill", "conga", "letflow", "conweave", "destspread")
ORDER_SEED = 2026100617
TARGET = ROOT / "docs/research/evidence/ws25-v2r1-screen-plan.json"


def main():
    manifest = json.loads((ROOT / "docs/research/evidence/ws25-v2r1-screen-inputs.json")
                          .read_text(encoding="utf-8"))
    if tuple(manifest["screening_seeds"]) != SEEDS:
        raise RuntimeError("Independent v2r1 seed pool changed")
    rng = random.Random(ORDER_SEED)
    blocks = list(SEEDS)
    rng.shuffle(blocks)
    cells = []
    for seed in blocks:
        trace = manifest["seeds"][str(seed)]["levels"]["192"]
        path = ROOT / "config" / trace["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != trace["sha256"]:
            raise RuntimeError("Frozen trace mismatch: " + trace["file"])
        modes = list(MODES)
        rng.shuffle(modes)
        for name in modes + ["destspread-diag"]:
            cells.append({
                "id": "20261006-180000-ws25-v2r1-screen-s{}-b192-{}".format(seed % 100, name),
                "seed": seed, "level": 192,
                "mode": "destspread" if name == "destspread-diag" else name,
                "ws25_diag": int(name == "destspread-diag"),
                "trace": trace["file"], "trace_sha256": trace["sha256"],
                "run_order": len(cells) + 1,
            })
    if len(cells) != 28 or len({cell["id"] for cell in cells}) != 28:
        raise RuntimeError("Screen ID count mismatch")
    plan = {"role": "v2 sole correction exploratory screen; no efficacy claim",
            "source_sha": SOURCE_SHA, "simulator_sha": SIMULATOR_SHA,
            "topology_sha256": TOPO_SHA, "order_seed": ORDER_SEED,
            "seeds": list(SEEDS), "modes": list(MODES), "level": 192,
            "ns3_seed": 1, "pfc": 0, "irn": 1, "bw_gbps": 400,
            "buffer_mib": 9, "cap_first_block": 1, "cap_after_first_block": 4,
            "cells": cells}
    encoded = json.dumps(plan, indent=2, sort_keys=True) + "\n"
    if TARGET.exists() and TARGET.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("Refusing to replace frozen v2r1 plan")
    TARGET.write_text(encoded, encoding="utf-8")
    print(json.dumps({"cells": len(cells), "first_seed": blocks[0],
                      "source_sha": SOURCE_SHA}, sort_keys=True))


if __name__ == "__main__":
    main()
