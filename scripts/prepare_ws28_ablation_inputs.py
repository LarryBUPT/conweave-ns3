#!/usr/bin/env python3
"""Freeze WS-28 ablation demands at the 192-background level only."""
import hashlib
import json
from pathlib import Path

from make_ws25_demand import make


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/research/evidence/ws28-ablation-inputs.json"
SEEDS = tuple(range(20262921, 20262945))


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    generator = ROOT / "scripts/make_ws25_demand.py"
    output = {
        "kind": "WS-28 independent ablation demand",
        "generator": "scripts/make_ws25_demand.py",
        "generator_sha256": sha(generator),
        "seeds": {},
        "background_levels": [192],
    }
    for seed in SEEDS:
        output["seeds"][str(seed)] = make(seed, ROOT / "config", levels=(192,))
    encoded = json.dumps(output, indent=2, sort_keys=True) + "\n"
    if MANIFEST.exists() and MANIFEST.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("WS-28 ablation manifest changed")
    MANIFEST.write_text(encoded, encoding="utf-8")
    print(json.dumps({"seeds": len(SEEDS), "traces": len(SEEDS),
                      "manifest_sha256": sha(MANIFEST)}, sort_keys=True))


if __name__ == "__main__":
    main()
