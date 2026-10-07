"""Generate independent WS-26 demand traces using the WS-25 sampling law.

The 20262601..20262624 seed pool is reserved for formal validation. Pilot
seeds use 20262690..20262699, keeping old WS-25 demands and formal demands
separate. Generating a trace does not freeze it or admit it to a matrix.
"""

import argparse
import json
from pathlib import Path

from make_ws25_demand import make

ROOT = Path(__file__).resolve().parents[1]
FORMAL_SEEDS = tuple(range(20262601, 20262625))
PILOT_SEEDS = tuple(range(20262690, 20262700))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("seed", type=int)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "config")
    args = parser.parse_args()
    if args.seed not in FORMAL_SEEDS + PILOT_SEEDS:
        parser.error("WS-26 seed is outside reserved formal/pilot pools")
    print(json.dumps(make(args.seed, args.out_dir, prefix="ws26"),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
