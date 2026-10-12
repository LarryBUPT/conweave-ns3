#!/usr/bin/env python3
"""Freeze independent WS-27 demands using the unchanged WS-25 distribution."""
import hashlib
import json
from pathlib import Path

from make_ws25_demand import make

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/research/evidence/ws27-demand-manifest.json"
SCREEN_MANIFEST = ROOT / "docs/research/evidence/ws27-screen-inputs.json"
CONFIRM_MANIFEST = ROOT / "docs/research/evidence/ws27-confirm-inputs.json"
SCREEN = tuple(range(20262701, 20262709))
CONFIRM = tuple(range(20262721, 20262745))


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    generator = ROOT / "scripts/make_ws25_demand.py"
    output = {
        "kind": "independent synthetic demand for WS-27 paired comparison",
        "generator": "scripts/make_ws25_demand.py",
        "generator_sha256": sha(generator),
        "screening_seeds": list(SCREEN),
        "confirmation_seeds": list(CONFIRM),
        "levels": [0, 64, 128, 192],
        "seeds": {},
    }
    for seed in SCREEN + CONFIRM:
        output["seeds"][str(seed)] = make(seed, ROOT / "config")
    for path, data in (
            (MANIFEST, output),
            (SCREEN_MANIFEST, {**output, "seeds": {str(seed): output["seeds"][str(seed)]
                                                 for seed in SCREEN}}),
            (CONFIRM_MANIFEST, {**output, "seeds": {str(seed): output["seeds"][str(seed)]
                                                  for seed in CONFIRM}})):
        encoded = json.dumps(data, indent=2, sort_keys=True) + "\n"
        if path.exists() and path.read_text(encoding="utf-8") != encoded:
            raise RuntimeError("Existing WS-27 demand manifest differs: " + str(path))
        path.write_text(encoded, encoding="utf-8")
    print(json.dumps({"seeds": len(output["seeds"]), "traces": len(output["seeds"]) * 4,
                      "manifest_sha256": sha(MANIFEST)}, sort_keys=True))


if __name__ == "__main__":
    main()
