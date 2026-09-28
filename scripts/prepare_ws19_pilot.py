#!/usr/bin/env python3
"""Freeze WS-17 demand traces and a seeded WS-19 four-arm block schedule."""
import argparse
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results/ws17-demand"
MANIFEST = ROOT / "docs/research/evidence/ws17-demand-manifest.json"
SCHEDULE = ROOT / "docs/research/evidence/ws19-pilot-schedule-v1.json"
TOPOLOGY = ROOT / "config/topo_1280_400G_400G_OS1.txt"
RNG_SEED = 20261901
ARMS = ["ecmp", "admission", "path", "joint"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert sha(TOPOLOGY) == manifest["topology_sha256"]
    blocks = []
    for seed in manifest["seeds"]:
        for record in seed["records"]:
            src = SOURCE / record["trace"]
            dst = ROOT / "config" / ("ws19_" + record["trace"])
            assert sha(src) == record["trace_sha256"]
            if not dst.exists():
                if args.verify:
                    raise RuntimeError("Missing frozen trace: " + str(dst))
                dst.write_bytes(src.read_bytes())
            assert sha(dst) == record["trace_sha256"]
            blocks.append({"seed": seed["seed"], "hotspot": record["treatment"],
                           "background": record["background_flows"],
                           "trace": dst.name, "trace_sha256": record["trace_sha256"],
                           "demand_sha256": record["demand_sha256"],
                           "flows": record["flows"], "moe_flows": record["moe_flows"],
                           "background_flows": record["background_flows"],
                           "offered_bytes": record["moe_bytes"] + record["background_bytes"]})
    rng = random.Random(RNG_SEED)
    rng.shuffle(blocks)
    runs = []
    for index, block in enumerate(blocks, 1):
        order = ARMS.copy()
        rng.shuffle(order)
        for position, arm in enumerate(order, 1):
            runs.append({"block": index, "position": position, "arm": arm, **block})
    output = {"version": 1, "purpose": "WS-19 exploratory pilot; not WS-20 confirmation",
              "parent_manifest_sha256": sha(MANIFEST), "topology_sha256": sha(TOPOLOGY),
              "randomization_seed": RNG_SEED, "independent_demand_seeds": 3,
              "paired_blocks": len(blocks), "planned_runs": len(runs), "runs": runs}
    data = (json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    if SCHEDULE.exists():
        assert SCHEDULE.read_bytes() == data, "Frozen schedule differs"
    elif args.verify:
        raise RuntimeError("Missing frozen schedule")
    else:
        SCHEDULE.write_bytes(data)
    print(json.dumps({"verified": True, "runs": len(runs), "blocks": len(blocks),
                      "schedule_sha256": sha(SCHEDULE)}, sort_keys=True))


if __name__ == "__main__":
    main()
