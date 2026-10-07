#!/usr/bin/env python3
"""Freeze the independent ClassReserve v3 pilot layout and input hashes."""

import hashlib
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/research/evidence/ws26-v3-pilot-plan.json"
SOURCE_SHA = "d6fdc5efe9a9aa77a90d24ab3aee931f721b607f"
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
SEEDS = [20262690, 20262691, 20262692, 20262693]
HIGH_ARMS = ["fecmp", "drill", "conga", "letflow", "conweave", "classreserve3"]
LOW_ARMS = ["fecmp", "classreserve3"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if digest(ROOT / "config/topo_1280_400G_400G_OS1.txt") != TOPO_SHA:
        raise RuntimeError("Topology hash changed")
    inputs = {}
    for seed in SEEDS:
        for background in (0, 64, 128, 192):
            name = "ws26_seed%d_b%d.txt" % (seed, background)
            path = ROOT / "config" / name
            lines = path.read_text(encoding="ascii").splitlines()
            expected = 16384 + background
            if int(lines[0]) != expected or len(lines) - 1 != expected:
                raise RuntimeError("Unexpected flow count in " + name)
            inputs[seed, background] = {"trace": name, "trace_sha256": digest(path),
                                        "expected_flows": expected}

    rng = random.Random(2026100801)
    high_seeds = list(SEEDS)
    rng.shuffle(high_seeds)
    cells = []

    def add(stage, seed, background, mode, diag=0):
        suffix = "ws26v3-p%d-b%d-%s%s" % (seed % 100, background, mode,
                                          "-d" if diag else "")
        cell = {"id": "20261008-070000-" + suffix, "stage": stage,
                "order": len(cells) + 1, "seed": seed, "background": background,
                "mode": mode, "ws25_diag": diag, "pfc": 1, "irn": 1}
        cell.update(inputs[seed, background])
        cells.append(cell)

    for seed in high_seeds:
        arms = list(HIGH_ARMS)
        rng.shuffle(arms)
        for mode in arms:
            add("high", seed, 192, mode)
            if mode == "classreserve3":
                add("high", seed, 192, mode, 1)

    low_seeds = list(SEEDS)
    rng.shuffle(low_seeds)
    for seed in low_seeds:
        backgrounds = [0, 64, 128]
        rng.shuffle(backgrounds)
        for background in backgrounds:
            arms = list(LOW_ARMS)
            rng.shuffle(arms)
            for mode in arms:
                add("low", seed, background, mode)

    if (len(cells) != 52 or len({cell["id"] for cell in cells}) != 52 or
            sum(cell["stage"] == "high" for cell in cells) != 28 or
            sum(cell["stage"] == "low" for cell in cells) != 24):
        raise RuntimeError("Pilot layout is not 28 high plus 24 low cells")
    output = {"design": "four independent demand seeds; paired arms within each seed",
              "purpose": "exploratory selection and resource sizing, not formal efficacy",
              "source_sha": SOURCE_SHA, "topology_sha256": TOPO_SHA,
              "randomization_seed": 2026100801, "cells": cells}
    OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print("Wrote %d frozen pilot cells to %s" % (len(cells), OUTPUT))


if __name__ == "__main__":
    main()
