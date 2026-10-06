#!/usr/bin/env python3
"""Verify the frozen independent screen of the sole DestSpread v2 correction."""
import argparse
import json

import verify_ws25_v2_screen as old

ROOT = old.ROOT
PLAN = json.loads((ROOT / "docs/research/evidence/ws25-v2r1-screen-plan.json")
                  .read_text(encoding="utf-8"))


def verify(cell):
    # The v2 screen verifier checks the raw trace, all completed QPs, resource
    # receipts, queue conservation, and non-perturbation of diagnostic FCT.
    # Its frozen v2 identities are replaced only during this call.
    original = old.PLAN
    try:
        old.PLAN = PLAN
        old.SHA = PLAN["source_sha"]
        old.TOPO = PLAN["topology_sha256"]
        result = old.verify(cell)
    finally:
        old.PLAN = original
        old.SHA = original["source_sha"]
        old.TOPO = original["topology_sha256"]
    if cell["mode"] == "destspread":
        route = result["route"]
        if (route.get("moe_new", 0) <= 0 or route.get("moe_reused", 0) <= 0 or
                route.get("moe_new", 0) + route.get("moe_reused", 0) !=
                route.get("moe_packets") or route.get("fallback_packets") != 0):
            raise RuntimeError("Corrected MoE cache/fallback failed: " + cell["id"])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", choices=[cell["id"] for cell in PLAN["cells"]])
    args = parser.parse_args()
    cells = [cell for cell in PLAN["cells"] if not args.id or cell["id"] == args.id]
    results = [verify(cell) for cell in cells]
    print(json.dumps({"verified": len(results), "ids": [row["id"] for row in results]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
