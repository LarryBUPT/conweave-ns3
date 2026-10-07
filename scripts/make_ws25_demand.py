"""Create independent WS-11-distribution demands without changing its levels.

The sampling rules follow the read-only reference generator at
maplerime/conweave-ns3@470c580: 256 of 320 rail-0 hosts are experts; each
expert selects 64 distinct expert peers; the other 64 hosts supply up to 192
distinct directed 8 MiB background pairs. All flows start at 2 s.
"""

import argparse
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEVELS = (0, 64, 128, 192)


def make(seed, out_dir, prefix="ws25"):
    rng = random.Random(seed)
    aligned = list(range(0, 1280, 4))
    experts = sorted(rng.sample(aligned, 256))
    expert_set = set(experts)
    background_hosts = sorted(set(aligned) - expert_set)
    pairs = []
    used = set()
    while len(pairs) < 192:
        src = rng.choice(background_hosts)
        dst = rng.choice(background_hosts)
        if src != dst and (src, dst) not in used:
            used.add((src, dst))
            pairs.append((src, dst))
    moe = []
    for src in experts:
        peers = sorted(rng.sample([dst for dst in experts if dst != src], 64))
        moe.extend((src, dst) for dst in peers)
    assert len(moe) == 16384 and len(set(moe)) == 16384
    assert not (set(background_hosts) & expert_set)
    manifest = {"seed": seed, "generator": "scripts/make_{}_demand.py".format(prefix),
                "levels": {}, "expert_hosts": len(experts),
                "background_hosts": len(background_hosts)}
    out_dir.mkdir(parents=True, exist_ok=True)
    for level in LEVELS:
        name = "{}_seed{}_b{}.txt".format(prefix, seed, level)
        lines = [str(16384 + level)]
        lines.extend("{} {} 3 8388608 2.000000000 1".format(src, dst)
                     for src, dst in pairs[:level])
        lines.extend("{} {} 3 8192 2.000000000 2".format(src, dst)
                     for src, dst in moe)
        data = ("\n".join(lines) + "\n").encode("ascii")
        path = out_dir / name
        if path.exists() and path.read_bytes() != data:
            raise ValueError("refusing to replace different trace: {}".format(path))
        path.write_bytes(data)
        manifest["levels"][str(level)] = {
            "file": name, "sha256": hashlib.sha256(data).hexdigest(),
            "flows": 16384 + level,
            "offered_bytes": 134217728 + level * 8388608}
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("seed", type=int)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "config")
    args = parser.parse_args()
    print(json.dumps(make(args.seed, args.out_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
