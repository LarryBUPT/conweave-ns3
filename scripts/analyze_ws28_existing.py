#!/usr/bin/env python3
"""Read-only WS-28 analysis of the fixed WS-27 ECMP/ClassReserve raw cells."""
import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/research/evidence/ws27-confirm-plan.json"
SOURCE_SHA = "ee236f27920aa56b3dd562ed971e5abee9e1e659"
BAD_SEEDS = (20262725, 20262729, 20262739)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def percentile(values, pct):
    values = sorted(values)
    pos = (len(values) - 1) * pct / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def change(candidate, control):
    return 100 * (candidate / control - 1)


def read_cell(base, cell):
    folder = base / cell["id"]
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    if (meta["status"] != "SUCCEEDED" or meta["git_commit"] != SOURCE_SHA or
            meta["algorithm"] != cell["mode"] or
            meta["input_flow_sha256"] != cell["trace_sha256"]):
        raise ValueError("Metadata mismatch: " + cell["id"])
    trace_path = folder / "config/traffic_trace.txt"
    if digest(trace_path) != cell["trace_sha256"]:
        raise ValueError("Trace hash mismatch: " + cell["id"])
    raw_id = str(meta["raw_directory"])
    if not raw_id.isdecimal():
        raise ValueError("Invalid raw ID")
    fct_path = folder / "raw" / raw_id / (raw_id + "_out_fct.txt")
    src_ports, dst_ports = {}, {}
    trace = {}
    with trace_path.open(encoding="utf-8") as source:
        declared = int(next(source))
        for line in source:
            fields = line.split()
            if len(fields) != 6:
                raise ValueError("Untagged trace")
            src, dst, _, size = map(int, fields[:4])
            start = round(float(fields[4]) * 1e9)
            tag = int(fields[5])
            sport, dport = src_ports.get(src, 10000), dst_ports.get(dst, 100)
            src_ports[src], dst_ports[dst] = sport + 1, dport + 1
            key = (src, dst, sport, dport, size)
            if key in trace:
                raise ValueError("Duplicate trace identity")
            trace[key] = (start, tag)
    if len(trace) != declared or declared != cell["input_flows"]:
        raise ValueError("Trace flow count mismatch")
    flows = {}
    with fct_path.open(encoding="utf-8") as source:
        for line in source:
            fields = list(map(int, line.split()))
            if len(fields) != 8:
                raise ValueError("Malformed FCT")
            key = tuple(fields[:5])
            if key not in trace or key in flows or abs(fields[5] - trace[key][0]) > 2:
                raise ValueError("FCT identity or timing mismatch")
            flows[key] = {"tag": trace[key][1], "fct_ns": fields[6],
                          "end_ns": fields[5] + fields[6], "ideal_ns": fields[7]}
    if len(flows) != declared:
        raise ValueError("Incomplete FCT: " + cell["id"])
    moe = {key: value for key, value in flows.items() if value["tag"] == 2}
    bg = {key: value for key, value in flows.items() if value["tag"] == 1}
    if len(moe) != 16384 or len(bg) != cell["background"]:
        raise ValueError("Class count mismatch")
    start = min(value[0] for value in trace.values())
    return {"id": cell["id"], "trace_sha256": digest(trace_path),
            "fct_sha256": digest(fct_path), "moe": moe, "background": bg,
            "batch_us": (max(x["end_ns"] for x in moe.values()) - start) / 1000,
            "moe_fct_p95_us": percentile([x["fct_ns"] / 1000 for x in moe.values()], 95),
            "background_p99_us": percentile([x["fct_ns"] / 1000 for x in bg.values()], 99)}


def public_flow(key, value):
    return {"flow_key": list(key), "fct_us": value["fct_ns"] / 1000,
            "end_us_after_2s": (value["end_ns"] - 2000000000) / 1000}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True,
                        help="Read-only WS-27 results directory")
    parser.add_argument("--output", type=Path, default=ROOT /
                        "docs/research/evidence/ws28-existing-raw-analysis.json")
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    if plan["source_sha"] != SOURCE_SHA:
        raise ValueError("Frozen source changed")
    selected = {(x["seed"], x["mode"]): x for x in plan["cells"]
                if x["background"] == 192 and x["mode"] in ("fecmp", "classreserve")}
    if len(selected) != 48:
        raise ValueError("Expected 48 paired raw cells")
    rows, examples = [], {}
    for seed in range(20262721, 20262745):
        ec = read_cell(args.results, selected[(seed, "fecmp")])
        cr = read_cell(args.results, selected[(seed, "classreserve")])
        if ec["trace_sha256"] != cr["trace_sha256"] or ec["moe"].keys() != cr["moe"].keys():
            raise ValueError("Unpaired flow identities")
        row = {"seed": seed, "ecmp_id": ec["id"], "classreserve_id": cr["id"],
               "trace_sha256": ec["trace_sha256"],
               "fct_sha256": {"ecmp": ec["fct_sha256"], "classreserve": cr["fct_sha256"]},
               "moe_batch_us": {"ecmp": ec["batch_us"], "classreserve": cr["batch_us"]},
               "moe_batch_change_pct": change(cr["batch_us"], ec["batch_us"]),
               "moe_single_flow_p95_us": {"ecmp": ec["moe_fct_p95_us"],
                                           "classreserve": cr["moe_fct_p95_us"]},
               "moe_single_flow_p95_change_pct": change(cr["moe_fct_p95_us"], ec["moe_fct_p95_us"]),
               "background_p99_change_pct": change(cr["background_p99_us"], ec["background_p99_us"])}
        rows.append(row)
        if seed in BAD_SEEDS:
            tails = {}
            for name, cell in (("ecmp", ec), ("classreserve", cr)):
                ranked = sorted(cell["moe"].items(), key=lambda item: item[1]["end_ns"], reverse=True)
                tails[name] = [public_flow(key, value) for key, value in ranked[:10]]
            tail_keys = {tuple(item["flow_key"]) for group in tails.values() for item in group}
            matched = []
            for key in sorted(tail_keys):
                matched.append({"flow_key": list(key),
                                "ecmp": public_flow(key, ec["moe"][key]),
                                "classreserve": public_flow(key, cr["moe"][key]),
                                "fct_change_us": (cr["moe"][key]["fct_ns"] - ec["moe"][key]["fct_ns"]) / 1000})
            examples[str(seed)] = {"top10_by_completion": tails, "matched_tail_union": matched,
                                   "tail_identity_same": tails["ecmp"][0]["flow_key"] ==
                                   tails["classreserve"][0]["flow_key"]}
    batch_p95 = {name: percentile([r["moe_batch_us"][name] for r in rows], 95)
                 for name in ("ecmp", "classreserve")}
    output = {"source_sha": SOURCE_SHA, "input_plan_sha256": digest(PLAN),
              "independent_unit": "demand seed", "verified_raw_cells": 48,
              "p95_definitions": {"single_flow": "within each seed, 16384 MoE FCT values",
                                  "batch": "across 24 seed-level MoE batch times"},
              "across_seed_batch_p95_us": batch_p95,
              "across_seed_batch_p95_change_pct": change(batch_p95["classreserve"], batch_p95["ecmp"]),
              "median_within_seed_single_flow_p95_change_pct": statistics.median(
                  r["moe_single_flow_p95_change_pct"] for r in rows),
              "paired_seeds": rows, "worsened_seed_tails": examples}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verified_raw_cells": 48,
                      "across_seed_batch_p95_change_pct": output["across_seed_batch_p95_change_pct"],
                      "median_within_seed_single_flow_p95_change_pct":
                      output["median_within_seed_single_flow_p95_change_pct"]}))


if __name__ == "__main__":
    main()
