#!/usr/bin/env python3
"""Freeze independent demand inputs for the sole DestSpread v2 correction screen."""
import json
from pathlib import Path

from make_ws25_demand import make

ROOT = Path(__file__).resolve().parents[1]
SEEDS = tuple(range(20262577, 20262581))
TARGET = ROOT / "docs/research/evidence/ws25-v2r1-screen-inputs.json"


def main():
    manifest = {
        "role": "v2 sole diagnostic correction exploratory screening; not formal efficacy",
        "generator": "scripts/make_ws25_demand.py",
        "screening_seeds": list(SEEDS),
        "calibration_pilot_reserved": list(range(20262549, 20262553)),
        "final_reserved": [20262553, 20262576],
        "seeds": {str(seed): make(seed, ROOT / "config") for seed in SEEDS},
    }
    encoded = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if TARGET.exists() and TARGET.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("Refusing to replace frozen v2r1 input manifest")
    TARGET.write_text(encoded, encoding="utf-8")
    print("v2r1_screen_seeds={} traces={}".format(len(SEEDS), len(SEEDS) * 4))


if __name__ == "__main__":
    main()
