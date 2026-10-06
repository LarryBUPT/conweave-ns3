#!/usr/bin/env python3
"""Reverify the frozen v2 screen and summarize paired, exploratory effects."""
import json
import statistics
from collections import defaultdict

from verify_ws25_v2_screen import PLAN, ROOT, fields, unique_raw, verify


def change(candidate, baseline):
    return 100.0 * (candidate / baseline - 1.0)


def qp_affected(cell):
    log = (ROOT / "results" / cell["id"] / "logs" / "config.log").read_text(
        encoding="utf-8", errors="replace")
    qps = [fields(line) for line in log.splitlines() if line.startswith("WS25_QP ")]
    counters = ("rx_ooo_packets", "sack_feedback", "cnp_feedback",
                "repeated_sends", "timeout_recovery")
    return {str(tag): {name: sum(row[name] > 0 for row in qps if row["tag"] == tag)
                       for name in counters} for tag in (1, 2)}


def background_flows(cell):
    base = ROOT / "results" / cell["id"]
    meta = json.loads((base / "metadata.json").read_text(encoding="utf-8"))
    raw = base / "raw" / str(meta["raw_directory"])
    flows = {}
    for line in unique_raw(raw, "_out_fct.txt").read_text(encoding="utf-8").splitlines():
        fields_ = tuple(map(int, line.split()))
        if fields_[4] == 8388608:
            key = fields_[:5]
            if key in flows:
                raise RuntimeError("Duplicate background FCT key")
            flows[key] = fields_[6] / 1000.0
    if len(flows) != 192:
        raise RuntimeError("Background flow count is not 192")
    return flows


def trace_flow_ids(cell):
    trace = ROOT / "results" / cell["id"] / "config" / "traffic_trace.txt"
    source_ports = defaultdict(lambda: 10000)
    destination_ports = defaultdict(lambda: 100)
    flow_ids = {}
    with trace.open(encoding="utf-8") as stream:
        declared = int(stream.readline())
        for flow_id, line in enumerate(stream):
            src, dst, _pg, size = map(int, line.split()[:4])
            key = (src, dst, source_ports[src], destination_ports[dst], size)
            if key in flow_ids:
                raise RuntimeError("Repeated trace identity")
            flow_ids[key] = flow_id
            source_ports[src] += 1
            destination_ports[dst] += 1
    if len(flow_ids) != declared:
        raise RuntimeError("Trace count mismatch")
    return flow_ids


def diagnostic_qps(cell):
    log = (ROOT / "results" / cell["id"] / "logs" / "config.log").read_text(
        encoding="utf-8", errors="replace")
    return {row["flow_id"]: row for row in
            (fields(line) for line in log.splitlines() if line.startswith("WS25_QP "))}


def main():
    cells = [verify(cell) for cell in PLAN["cells"]]
    if len(cells) != 28 or len({cell["id"] for cell in cells}) != 28:
        raise RuntimeError("Frozen 28-cell screen is incomplete")
    baseline_modes = ("fecmp", "drill", "conga", "letflow", "conweave")
    seeds = sorted({cell["seed"] for cell in cells})
    if len(seeds) != 4:
        raise RuntimeError("Expected four independent demand seeds")
    by_seed = {}
    diag = {}
    for seed in seeds:
        rows = {cell["mode"]: cell for cell in cells
                if cell["seed"] == seed and cell["ws25_diag"] == 0}
        if set(rows) != set(baseline_modes) | {"destspread"}:
            raise RuntimeError("Missing six-mode paired block: " + str(seed))
        diagnostic = [cell for cell in cells if cell["seed"] == seed and cell["ws25_diag"] == 1]
        if len(diagnostic) != 1 or diagnostic[0]["mode"] != "destspread":
            raise RuntimeError("Missing diagnostic control: " + str(seed))
        candidate = rows["destspread"]
        candidate_flows = background_flows(candidate)
        ecmp_flows = background_flows(rows["fecmp"])
        if set(candidate_flows) != set(ecmp_flows):
            raise RuntimeError("Background identities differ within paired block")
        worst = sorted(candidate_flows,
                       key=lambda key: candidate_flows[key] - ecmp_flows[key], reverse=True)[:3]
        flow_ids = trace_flow_ids(diagnostic[0])
        qps = diagnostic_qps(diagnostic[0])
        if len(qps) != 16576 or any(key not in flow_ids or flow_ids[key] not in qps for key in worst):
            raise RuntimeError("Tail flow cannot be joined to diagnostic QP")
        diag[str(seed)] = {
            "route": candidate["route"],
            "qp_counter_totals": diagnostic[0]["qp_by_tag"],
            "qp_nonzero_counts": qp_affected(diagnostic[0]),
            "fct_identical_with_control": candidate["fct_sha256"] == diagnostic[0]["fct_sha256"],
            "background_paired_flow_delta_median_us": statistics.median(
                candidate_flows[key] - ecmp_flows[key] for key in candidate_flows),
            "worst_background_flow_regressions": [
                {"flow_key": list(key), "ecmp_fct_us": ecmp_flows[key],
                 "candidate_fct_us": candidate_flows[key],
                 "delta_us": candidate_flows[key] - ecmp_flows[key],
                 "flow_id": flow_ids[key],
                 "candidate_qp": {name: qps[flow_ids[key]][name] for name in
                                  ("rx_ooo_packets", "sack_feedback", "cnp_feedback",
                                   "repeated_sends", "timeout_recovery")}}
                for key in worst],
        }
        by_seed[str(seed)] = {
            "absolute_us": {mode: {"moe_batch": row["moe_batch_us"],
                                    "background_p99": row["background_p99_us"]}
                            for mode, row in rows.items()},
            "paired_change_pct": {
                mode: {"moe_batch": change(candidate["moe_batch_us"], rows[mode]["moe_batch_us"]),
                       "background_p99": change(candidate["background_p99_us"],
                                                rows[mode]["background_p99_us"])}
                for mode in baseline_modes},
        }
    aggregate = {}
    for mode in baseline_modes:
        aggregate[mode] = {}
        for metric in ("moe_batch", "background_p99"):
            values = [by_seed[str(seed)]["paired_change_pct"][mode][metric] for seed in seeds]
            aggregate[mode][metric] = {
                "median_change_pct": statistics.median(values),
                "strict_improvement_seeds": sum(value < 0 for value in values),
                "range_pct": [min(values), max(values)],
            }
    gate = all(aggregate["fecmp"][metric]["median_change_pct"] <= -5 and
               aggregate["fecmp"][metric]["strict_improvement_seeds"] >= 3
               for metric in ("moe_batch", "background_p99"))
    if not all(item["fct_identical_with_control"] for item in diag.values()):
        raise RuntimeError("Diagnostic control changed FCT")
    output = {"source_sha": PLAN["source_sha"], "cell_count": len(cells),
              "seeds": seeds, "by_seed": by_seed, "aggregate": aggregate,
              "diagnostic": diag, "exploratory_gate_pass": gate,
              "formal_effect_claim_allowed": False}
    target = ROOT / "docs/research/evidence/ws25-v2-screen-analysis.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(json.dumps({"cells": len(cells), "gate": gate, "vs_ecmp": aggregate["fecmp"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
