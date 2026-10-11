#!/usr/bin/env python3
"""Recompute the disclosed seed-97 two-factor diagnostic from verified raw cells."""

import argparse
import json
from pathlib import Path

import analyze_moe_tags
import analyze_ws26_seed97_time_aligned as timeline
import verify_ws26_classlane_factorial_diagnostic as verify
from verify_ws26_moe_hop_diagnostic import topology_maps, trace_qps
from verify_ws26_seed97_probe_preflight import HEADER, HEADER_QUAD, ROOT


OUTPUT = ROOT / "docs/research/evidence/ws26-classlane-factorial-diagnostic-analysis.json"
METRICS = {"moe_batch_us": ("2", "synthetic_batch_completion_us"),
           "background_p99_fct_us": ("1", "p99_fct_us")}
ARM_ORDERS = {"00": 5, "11": 6, "10": 8, "01": 10}


def signed_difference(right, left):
    return round(right - left, 6)


def analyze_cell(cell, plan, selected):
    checked = verify.check(cell, plan)
    classes = analyze_moe_tags.summarize(cell["id"])["tags"]
    result = {"id": cell["id"], "order": cell["order"], "mode": cell["mode"],
              "trace_sha256": cell["trace_sha256"], "verification": checked,
              "class_metrics": classes}
    if cell["order"] not in ARM_ORDERS.values():
        return result
    folder = ROOT / "results" / cell["id"]
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    expected = trace_qps(folder / "config/traffic_trace.txt")
    fct = timeline.parse_fct(folder, metadata, expected, selected)
    events, hops, summaries = timeline.parse_log(folder, selected)
    maps = topology_maps(folder / "config/topology.txt")
    result["qps"] = {timeline.label(key): timeline.summarize_qp(
        key, fct[key], events[key], hops[key], summaries[key], maps)
        for key in sorted(selected)}
    return result


def contrast(values):
    a, b, c, d = (values[arm] for arm in ("00", "10", "01", "11"))
    return {"10_minus_00": signed_difference(b, a),
            "01_minus_00": signed_difference(c, a),
            "11_minus_10": signed_difference(d, b),
            "11_minus_01": signed_difference(d, c),
            "interaction_11_minus_10_minus_01_plus_00": round(d - b - c + a, 6)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    plan = verify.load_plan()
    selected = {tuple(map(int, match)) for match in
                HEADER_QUAD.findall(HEADER.read_text(encoding="utf-8"))}
    if len(selected) != 23 or not set(timeline.TARGETS) <= selected:
        raise RuntimeError("Selected QPs differ from frozen header")
    cells = [analyze_cell(cell, plan, selected) for cell in plan["cells"]]
    arms = {arm: cells[order - 1] for arm, order in ARM_ORDERS.items()}
    if any(arms[arm]["verification"]["completed_flows"] != 16576 for arm in arms):
        raise RuntimeError("High cell is incomplete")
    metrics = {}
    for name, (tag, field) in METRICS.items():
        values = {arm: arms[arm]["class_metrics"][tag][field] for arm in arms}
        metrics[name] = {"arms": values, "contrasts_us": contrast(values)}
    qps = {}
    for key in sorted(arms["00"]["qps"]):
        entries = {arm: arms[arm]["qps"][key] for arm in arms}
        if len({(row["tag"], row["size_bytes"], row["start_ns"])
                for row in entries.values()}) != 1:
            raise RuntimeError("Selected QP identity differs by arm: " + key)
        values = {arm: row["fct_us"] for arm, row in entries.items()}
        qps[key] = {"tag": entries["00"]["tag"], "role": entries["00"]["role"],
                    "fct_us": values, "fct_contrasts_us": contrast(values),
                    "last_send_us": {arm: row["send"]["last_us"]
                                     for arm, row in entries.items()},
                    "cnp_count": {arm: row["feedback"]["cnp_count"]
                                  for arm, row in entries.items()},
                    "min_rate_gbps": {arm: row["feedback"]["min_rate_gbps"]
                                      for arm, row in entries.items()},
                    "last_packet_wait_us": {arm: row["final_seq_packet"]["sum_hop_wait_us"]
                                            for arm, row in entries.items()},
                    "path": {arm: row["path"] for arm, row in entries.items()}}
    result = {"scope": "disclosed seed 20262697, diagnostic intervention only",
              "plan_sha256": verify.PLAN_SHA256, "source_sha": verify.SOURCE_SHA,
              "trace_sha256": plan["high_trace_sha256"],
              "selected_qp_count": len(selected), "cells": cells,
              "arms": {arm: arms[arm]["id"] for arm in ("00", "10", "01", "11")},
              "metrics": metrics, "selected_qps": qps}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("wrote %s; verified %d cells and %d selected QPs across four arms" %
          (args.output, len(cells), len(qps)))


if __name__ == "__main__":
    main()
