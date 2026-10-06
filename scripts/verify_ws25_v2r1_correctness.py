#!/usr/bin/env python3
"""Check the sole DestSpread v2 correction's frozen small-input cells."""
import argparse
import json

import verify_ws25_v2_correctness as old

ROOT = old.ROOT
SHA = "206888df97e2fd5fd37656d51deda5fb6a4e96c1"
PREFIX = "20261006-1700"
CELLS = [
    (PREFIX + "00-ws25-v2r1-pre-mixed8", "destspread", "ws25_v1fix_mixed8.txt", 0),
    (PREFIX + "01-ws25-v2r1-pre-background4", "destspread", "ws25_v1fix_background4.txt", 0),
    (PREFIX + "02-ws25-v2r1-pre-moe4", "destspread", "ws25_v1fix_moe4.txt", 0),
    (PREFIX + "03-ws25-v2r1-pre-unclassified8", "destspread", "ws25_v1fix_unclassified8.txt", 0),
    (PREFIX + "04-ws25-v2r1-pre-legacy5", "destspread", "ws25_v1fix_legacy5.txt", 0),
]
CELLS += [(PREFIX + "%02d-ws25-v2r1-pre-%s" % (i + 5, mode), mode,
           "ws25_v1fix_mixed8.txt", 0)
          for i, mode in enumerate(("fecmp", "drill", "conga", "letflow", "conweave"))]
CELLS += [
    (PREFIX + "10-ws25-v2r1-pre-unclassified-ecmp", "fecmp", "ws25_v1fix_unclassified8.txt", 0),
    (PREFIX + "11-ws25-v2r1-pre-legacy-ecmp", "fecmp", "ws25_v1fix_legacy5.txt", 0),
    (PREFIX + "12-ws25-v2r1-pre-mixed8-diag", "destspread", "ws25_v1fix_mixed8.txt", 1),
]


def verify(cell):
    experiment_id, mode, trace, diagnostic = cell
    result = old.verify(experiment_id, mode, trace, diagnostic, SHA)
    if mode == "destspread":
        route = result["route"]
        if route.get("moe_packets") != route.get("moe_new", 0) + route.get("moe_reused", 0):
            raise RuntimeError("MoE first-packet cache counters do not conserve")
        if trace in ("ws25_v1fix_mixed8.txt", "ws25_v1fix_moe4.txt") and not (
                route.get("moe_new", 0) > 0 and route.get("moe_reused", 0) > 0):
            raise RuntimeError("Corrected MoE cache was not exercised")
    if diagnostic:
        control = verify(CELLS[0])
        if result["fct_sha256"] != control["fct_sha256"]:
            raise RuntimeError("Diagnostic switch perturbed FCT")
        log = (ROOT / "results" / experiment_id / "logs" / "config.log").read_text(
            encoding="utf-8", errors="replace")
        qps = [old.counters(line) for line in log.splitlines()
               if line.startswith("WS25_QP ")]
        names = ("rx_ooo_packets", "sack_feedback", "cnp_feedback",
                 "repeated_sends", "timeout_recovery")
        if len(qps) != 8 or sum(qp.get("tag") == 1 for qp in qps) != 4 or sum(
                qp.get("tag") == 2 for qp in qps) != 4 or any(
                not all(name in qp for name in names) for qp in qps):
            raise RuntimeError("Missing per-QP diagnostic rows")
        result["qp_totals"] = {str(tag): {name: sum(qp.get(name, 0) for qp in qps
                                                  if qp["tag"] == tag)
                                          for name in names}
                               for tag in (1, 2)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", choices=[cell[0] for cell in CELLS])
    args = parser.parse_args()
    selected = [cell for cell in CELLS if not args.id or cell[0] == args.id]
    results = [verify(cell) for cell in selected]
    if not args.id:
        by_key = {(row["mode"], row["trace"]): row for row in results}
        for trace in ("ws25_v1fix_unclassified8.txt", "ws25_v1fix_legacy5.txt"):
            if by_key["destspread", trace]["fct_sha256"] != by_key["fecmp", trace]["fct_sha256"]:
                raise RuntimeError("ECMP fallback FCT changed")
        for mode, old_id in old.OLD_MIXED8_IDS.items():
            meta = json.loads((ROOT / "results" / old_id / "metadata.json").read_text(
                encoding="utf-8"))
            raw = ROOT / "results" / old_id / "raw" / str(meta["raw_directory"])
            if by_key[mode, "ws25_v1fix_mixed8.txt"]["fct_sha256"] != old.digest(
                    old.one_file(raw, "_out_fct.txt")):
                raise RuntimeError("Old baseline FCT regression: " + mode)
    print(json.dumps({"verified": len(results), "ids": [row["id"] for row in results]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
