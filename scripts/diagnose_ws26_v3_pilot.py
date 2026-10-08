#!/usr/bin/env python3
"""Compare receiver-side ECN feedback summaries with WS-26 pilot tail flows."""

import argparse
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "results/ws26-v3-independent-pilot-r2"
VERIFIED = PILOT / "high-verified.json"
ANALYSIS = PILOT / "high-analysis.json"
SEEDS = (20262690, 20262691, 20262692, 20262693)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def raw_for(cell):
    folder = ROOT / "results" / cell["id"]
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    raw = folder / "raw" / str(meta["raw_directory"])
    if meta["git_commit"] != "593038416fa16f4982b600d256b563260f9106a8":
        raise RuntimeError("Unexpected source SHA: " + cell["id"])
    return raw


def read_cnp(path):
    totals = [0, 0, 0]
    by_node = defaultdict(lambda: [0, 0, 0])
    rows = 0
    for line in path.read_text(encoding="ascii").splitlines():
        time_ns, node, ecn, ooo, total = map(int, line.split())
        if total < max(ecn, ooo):
            raise RuntimeError("Malformed CNP counter row")
        rows += 1
        for i, value in enumerate((ecn, ooo, total)):
            totals[i] += value
            by_node[node][i] += value
    return {"rows": rows, "ecn": totals[0], "ooo": totals[1],
            "total": totals[2], "by_receiver_node": by_node}


def read_background_fct(path):
    rows = []
    for line in path.read_text(encoding="ascii").splitlines():
        src, dst, sport, dport, size, start_ns, fct_ns, standalone_ns = map(int, line.split())
        if size == 8 * 1024 * 1024:
            rows.append({"src": src, "dst": dst, "sport": sport,
                         "dport": dport, "start_ns": start_ns,
                         "fct_ns": fct_ns, "standalone_ns": standalone_ns})
    if len(rows) != 192:
        raise RuntimeError("Expected 192 background QPs")
    return rows


def cnp_by_destination(path):
    # network-load-balance.cc writes RdmaHw::m_node->GetId(); the counter is
    # incremented at the receiver while generating an ACK/NACK with CNP flag.
    totals = defaultdict(lambda: [0, 0, 0])
    for line in path.read_text(encoding="ascii").splitlines():
        _, node, ecn, ooo, total = map(int, line.split())
        for i, value in enumerate((ecn, ooo, total)):
            totals[node][i] += value
    return totals


def one_cell(rows, seed, mode):
    matches = [row for row in rows if row["seed"] == seed and row["mode"] == mode
               and row["ws25_diag"] == 0]
    if len(matches) != 1:
        raise RuntimeError("Expected one cell for %d %s" % (seed, mode))
    return matches[0]


def analyze():
    verified = json.loads(VERIFIED.read_text(encoding="utf-8"))
    analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    cells = verified["cells"]
    if verified["verified"] != 28 or verified["requested"] != 28:
        raise RuntimeError("High pilot is not verified 28/28")
    output = {"source_sha": "593038416fa16f4982b600d256b563260f9106a8",
              "evidence_level": "exploratory pilot diagnostic",
              "verified_cells": 28, "seeds": []}
    analysis_pairs = {"moe_batch": {p["seed"]: p for p in
                       analysis["high"]["moe_batch"]["pairs"]},
                      "background_p99": {p["seed"]: p for p in
                       analysis["high"]["background_p99"]["pairs"]}}
    ecn_changes, p99_changes = [], []
    for seed in SEEDS:
        rows = {}
        counters = {}
        flow_sets = {}
        for mode in ("fecmp", "classreserve3"):
            cell = one_cell(cells, seed, mode)
            raw = raw_for(cell)
            cnp_path = next(raw.glob("*_out_cnp.txt"))
            pfc_path = next(raw.glob("*_out_pfc.txt"))
            fct_path = next(raw.glob("*_out_fct.txt"))
            if digest(fct_path) != cell["fct_sha256"]:
                raise RuntimeError("FCT hash changed: " + cell["id"])
            counters[mode] = read_cnp(cnp_path)
            counters[mode]["by_receiver_node"] = cnp_by_destination(cnp_path)
            counters[mode]["pfc_pause_events"] = sum(
                bool(line.strip()) and line.split()[-1] == "1"
                for line in pfc_path.read_text(encoding="ascii").splitlines())
            counters[mode]["pfc_resume_events"] = sum(
                bool(line.strip()) and line.split()[-1] == "0"
                for line in pfc_path.read_text(encoding="ascii").splitlines())
            flow_sets[mode] = read_background_fct(fct_path)
        if len(flow_sets["fecmp"]) != len(flow_sets["classreserve3"]):
            raise RuntimeError("Paired background count mismatch")
        summary = {}
        for mode in ("fecmp", "classreserve3"):
            flows = sorted(flow_sets[mode], key=lambda row: (row["fct_ns"], row["src"], row["dst"]))
            pos = (len(flows) - 1) * 0.99
            lo = int(pos)
            hi = min(lo + 1, len(flows) - 1)
            p99 = flows[lo]["fct_ns"] + (flows[hi]["fct_ns"] - flows[lo]["fct_ns"]) * (pos - lo)
            worst = sorted(flows, key=lambda row: row["fct_ns"], reverse=True)[:5]
            per_node = counters[mode]["by_receiver_node"]
            summary[mode] = {
                "fct_sha256": digest(next((ROOT / "results" / one_cell(cells, seed, mode)["id"] /
                                           "raw").glob("*/*_out_fct.txt"))),
                "background_qps": len(flows), "background_p99_us": p99 / 1000.0,
                "worst_five_background_qps": [
                    {**row, "fct_us": row["fct_ns"] / 1000.0,
                     "receiver_cnp_total": per_node[row["dst"]][2],
                     "receiver_cnp_ecn": per_node[row["dst"]][0],
                     "receiver_cnp_ooo": per_node[row["dst"]][1]}
                    for row in worst],
                "ecn_counter_total": counters[mode]["ecn"],
                "ooo_counter_total": counters[mode]["ooo"],
                "feedback_counter_total": counters[mode]["total"],
                "cnp_rows": counters[mode]["rows"],
                "pfc_pause_events": counters[mode]["pfc_pause_events"],
                "pfc_resume_events": counters[mode]["pfc_resume_events"],
                "highest_feedback_receivers": [
                    {"receiver_node": node, "ecn": values[0], "ooo": values[1],
                     "total": values[2]}
                    for node, values in sorted(per_node.items(), key=lambda item: item[1][2],
                                               reverse=True)[:5]]}
        p99_change = 100.0 * (summary["classreserve3"]["background_p99_us"] /
                              summary["fecmp"]["background_p99_us"] - 1.0)
        ecn_change = 100.0 * (summary["classreserve3"]["ecn_counter_total"] /
                              summary["fecmp"]["ecn_counter_total"] - 1.0)
        ecn_changes.append(ecn_change)
        p99_changes.append(p99_change)
        pair = {"seed": seed, "background_p99_change_percent": p99_change,
                "receiver_ecn_total_change_percent": ecn_change,
                "receiver_ecn_total_change": (summary["classreserve3"]["ecn_counter_total"] -
                                               summary["fecmp"]["ecn_counter_total"]),
                "moe_batch_change_percent": analysis_pairs["moe_batch"][seed]["change_percent"],
                "worst_flow_destination_ecmp": summary["fecmp"]["worst_five_background_qps"][0]["dst"],
                "worst_flow_destination_candidate": summary["classreserve3"]["worst_five_background_qps"][0]["dst"],
                "worst_destination_cnp_ecmp": summary["fecmp"]["worst_five_background_qps"][0]["receiver_cnp_total"],
                "worst_destination_cnp_candidate": summary["classreserve3"]["worst_five_background_qps"][0]["receiver_cnp_total"],
                "summary": summary}
        output["seeds"].append(pair)
    output["aggregate"] = {
        "ecn_total_change_percent_by_seed": ecn_changes,
        "ecn_total_change_median_percent": statistics.median(ecn_changes),
        "background_p99_change_percent_by_seed": p99_changes,
        "background_p99_change_median_percent": statistics.median(p99_changes),
        "interpretation_limits": [
            "CNP counters are generated at the receiver and aggregated by host, not by QP.",
            "ECN and OoO reasons may overlap; these raw counters are not retransmission counts.",
            "The PFC raw file counts pause/resume events; empty files show no PFC event in these cells.",
            "Receiver-level totals do not identify the marking switch, queue, or causal path for a tail QP.",
            "The diagnostic compares four pilot seeds and does not estimate population effects."
        ]}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=PILOT / "high-diagnostic.json")
    args = parser.parse_args()
    result = analyze()
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.output.write_text(rendered, encoding="utf-8")
    print(json.dumps({"output": str(args.output), "seeds": len(result["seeds"]),
                      "verified_cells": result["verified_cells"],
                      "ecn_median_change_percent": result["aggregate"][
                          "ecn_total_change_median_percent"]}, indent=2))


if __name__ == "__main__":
    main()
