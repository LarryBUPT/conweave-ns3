#!/usr/bin/env python3
"""Generate an independent explicit-tag MixHash-shaped M1 demand."""

import argparse
import random
from pathlib import Path


def generate(seed, path):
    rng = random.Random(seed)
    aligned = list(range(0, 1280, 4))
    business_nodes = sorted(rng.sample(aligned, 256))
    background_nodes = sorted(set(aligned) - set(business_nodes))

    background = []
    used_pairs = set()
    attempts = 0
    while len(background) < 192 and attempts < 1920:
        src = rng.choice(background_nodes)
        dst = rng.choice(background_nodes)
        if src != dst and (src, dst) not in used_pairs:
            used_pairs.add((src, dst))
            background.append((src, dst))
        attempts += 1
    if len(background) != 192:
        raise RuntimeError("Could not generate the fixed background pool")

    lines = ["16448\n"]
    for src, dst in background[:64]:
        lines.append("%d %d 3 8388608 2.000000000 1\n" % (src, dst))
    for src in business_nodes:
        destinations = sorted(rng.sample([dst for dst in business_nodes if dst != src], 64))
        for dst in destinations:
            lines.append("%d %d 3 8192 2.000000000 2\n" % (src, dst))
    if len(lines) != 16449:
        raise RuntimeError("Incorrect output row count")
    path.write_bytes("".join(lines).encode("ascii"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    generate(args.seed, args.output)


if __name__ == "__main__":
    main()
