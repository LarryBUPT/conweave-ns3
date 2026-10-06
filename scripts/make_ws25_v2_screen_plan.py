#!/usr/bin/env python3
"""Freeze the exploratory, independently seeded WS-25 v2 screening order."""
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "7aa09f5ab8e9cd7ef852db3c3fab6aa551ca8ecb"
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
SEEDS = tuple(range(20262545, 20262549))
MODES = ("fecmp", "drill", "conga", "letflow", "conweave", "destspread")
ORDER_SEED = 2026100614


def main():
    manifest = json.loads((ROOT / "docs/research/evidence/ws25-v2-screen-inputs.json")
                          .read_text(encoding="utf-8"))
    if tuple(int(seed) for seed in sorted(manifest["seeds"])) != SEEDS:
        raise RuntimeError("Screen demand seed pool changed")
    rng = random.Random(ORDER_SEED)
    blocks = list(SEEDS)
    rng.shuffle(blocks)
    cells = []
    for seed in blocks:
        modes = list(MODES)
        rng.shuffle(modes)
        trace = manifest["seeds"][str(seed)]["levels"]["192"]
        name = "ws25_seed{}_b192.txt".format(seed)
        path = ROOT / "config" / name
        if trace["file"] != name or hashlib.sha256(path.read_bytes()).hexdigest() != trace["sha256"]:
            raise RuntimeError("Frozen screen trace mismatch: " + name)
        for mode in modes + ["destspread-diag"]:
            cells.append({"id": "20261006-140000-ws25-v2-screen-s{}-b192-{}".format(
                seed % 100, mode), "seed": seed, "level": 192,
                "mode": "destspread" if mode == "destspread-diag" else mode,
                "ws25_diag": int(mode == "destspread-diag"),
                "trace": name, "trace_sha256": trace["sha256"],
                "run_order": len(cells) + 1})
    if len(cells) != 28 or len({cell["id"] for cell in cells}) != 28:
        raise RuntimeError("Screen identity count mismatch")
    plan = {"role": "exploratory screening; no confirmatory efficacy claims",
            "source_sha": SOURCE_SHA, "simulator_sha":
            "87bb136ba85126c8c6c883814c7fa10cdcd74fda",
            "topology_sha256": TOPO_SHA, "order_seed": ORDER_SEED,
            "seeds": list(SEEDS), "modes": list(MODES), "level": 192,
            "ns3_seed": 1, "pfc": 0, "irn": 1, "bw_gbps": 400,
            "buffer_mib": 9, "cap_first_block": 1, "cap_after_first_block": 4,
            "cells": cells}
    path = ROOT / "docs/research/evidence/ws25-v2-screen-plan.json"
    encoded = json.dumps(plan, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("Refusing to replace frozen screening plan")
    path.write_text(encoded, encoding="utf-8")
    print(json.dumps({"cells": len(cells), "first_seed": blocks[0],
                      "source_sha": SOURCE_SHA}, sort_keys=True))


if __name__ == "__main__":
    main()
