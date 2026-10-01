#!/usr/bin/env python3
"""Freeze three independent synthetic demand pairs for WS-23 isolation pilot."""

import argparse
import hashlib
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEEDS = (2301, 2302, 2303)
MANIFEST = ROOT / "docs/research/evidence/ws23-isolation-demand-manifest.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def render(rows):
    lines = [str(len(rows))]
    for src, dst, size, offset, tag in rows:
        seconds = 2 + (6_000_000 + offset) / 1_000_000_000
        lines.append("%d %d 3 %d %.9f %d" % (src, dst, size, seconds, tag))
    return ("\n".join(lines) + "\n").encode("ascii")


def build(seed):
    rng = random.Random(seed)
    sources, destinations = list(range(4)), list(range(24, 28))
    rng.shuffle(sources)
    rng.shuffle(destinations)
    # All four demands remain cross-ToR (32 to 38); source, destination and
    # arrival vary independently by seed. The first flow is the background.
    offsets = [rng.randrange(0, 100_001) for _ in range(4)]
    rows = [(sources[0], destinations[0], 8 * 1024 * 1024, offsets[0], 1)]
    rows += [(sources[i], destinations[i], 4 * 1024 * 1024, offsets[i], 2)
             for i in range(1, 4)]
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    entries = []
    for seed in SEEDS:
        rows = build(seed)
        assert len({row[0] for row in rows}) == 4
        assert len({row[1] for row in rows}) == 4
        for kind, subset in (("bg", rows[:1]), ("mix", rows)):
            path = ROOT / "config" / ("ws23_isolation_s%d_%s.txt" % (seed, kind))
            data = render(subset)
            if args.check:
                assert path.read_bytes() == data, str(path)
            else:
                path.write_bytes(data)
            entries.append({"seed": seed, "scenario": kind,
                            "path": path.relative_to(ROOT).as_posix(),
                            "sha256": sha(data), "flow_count": len(subset),
                            "payload_bytes": sum(row[2] for row in subset),
                            "flows": [dict(source=row[0], destination=row[1],
                                           pg=3, bytes=row[2],
                                           arrival_offset_ns=row[3], tag=row[4])
                                      for row in subset]})
    manifest = {"kind": "synthetic independent demand; not deployment traffic",
                "generator": "scripts/make_ws23_isolation_demands.py",
                "python_random_seeds": list(SEEDS),
                "arrival_origin_seconds": 2.006,
                "topology": "fat_k4_100G_OS2",
                "total_payload_bytes_per_mixed_trace": 20 * 1024 * 1024,
                "entries": entries}
    data = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if args.check:
        assert MANIFEST.read_bytes() == data, str(MANIFEST)
    else:
        MANIFEST.write_bytes(data)
    print(sha(data))


if __name__ == "__main__":
    main()
