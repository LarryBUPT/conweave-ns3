#!/usr/bin/env python3
"""Describe the four independent WS-25 v1-fix calibration seeds from raw data."""
import hashlib
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

import analyze_ws25_calibration as old
import run_ws25_v1fix_calibration as calibration

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/research/evidence/ws25-v1fix-four-seed-calibration.json"
SEEDS = tuple(sorted(calibration.SEEDS))
MODES = ("fecmp", "drill", "conga", "letflow", "conweave", "classreserve")
QP_COUNTERS = ("rx_ooo_packets", "sack_feedback", "cnp_feedback",
               "repeated_sends", "timeout_recovery")


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fields(line):
    return {key: int(value) for key, value in re.findall(r"(\w+)=(-?\d+)", line)}


def parse_diagnostic(path):
    by_tag = defaultdict(lambda: {"qp_count": 0, "flow_ids": set(),
                                 **{key: 0 for key in QP_COUNTERS}})
    choices = {}
    hop = {"flow_hop_rows": 0, "packets_across_hops": 0,
           "bytes_across_hops": 0, "queued_bytes_sum_across_packets": 0,
           "queued_bytes_max": 0, "wait_ns_sum_across_packets": 0,
           "wait_ns_max": 0, "nonzero_queue_flow_hop_rows": 0}
    inflight = None
    with path.open("r", encoding="utf-8", errors="replace") as source:
        for line in source:
            if line.startswith("WS25_QP "):
                row = fields(line)
                bucket = by_tag[row["tag"]]
                bucket["qp_count"] += 1
                bucket["flow_ids"].add(row["flow_id"])
                for name in QP_COUNTERS:
                    bucket[name] += row[name]
            elif line.startswith("WS25_CHOICE "):
                row = fields(line)
                if row["tag"] in choices:
                    raise RuntimeError("Duplicate choice tag in " + str(path))
                choices[row["tag"]] = row
            elif line.startswith("WS13_HOP "):
                row = fields(line)
                hop["flow_hop_rows"] += 1
                hop["packets_across_hops"] += row["packets"]
                hop["bytes_across_hops"] += row["bytes"]
                hop["queued_bytes_sum_across_packets"] += row["queued_bytes_sum"]
                hop["queued_bytes_max"] = max(hop["queued_bytes_max"], row["queued_bytes_max"])
                hop["wait_ns_sum_across_packets"] += row["wait_ns_sum"]
                hop["wait_ns_max"] = max(hop["wait_ns_max"], row["wait_ns_max"])
                hop["nonzero_queue_flow_hop_rows"] += row["queued_bytes_max"] > 0
            elif line.startswith("WS13_INFLIGHT "):
                if inflight is not None:
                    raise RuntimeError("Duplicate inflight row in " + str(path))
                inflight = fields(line)["unpaired"]
    for bucket in by_tag.values():
        bucket["unique_flow_ids"] = len(bucket.pop("flow_ids"))
    if {tag: bucket["qp_count"] for tag, bucket in by_tag.items()} != {1: 192, 2: 16384}:
        raise RuntimeError("Diagnostic QP coverage mismatch: " + str(path))
    if set(choices) != {1, 2} or inflight != 0:
        raise RuntimeError("Choice/hop diagnostic incomplete: " + str(path))
    packets = hop["packets_across_hops"]
    hop["mean_enqueue_queue_bytes_per_packet"] = (
        hop["queued_bytes_sum_across_packets"] / packets if packets else None)
    hop["mean_enqueue_to_dequeue_wait_ns"] = (
        hop["wait_ns_sum_across_packets"] / packets if packets else None)
    hop["unpaired_inflight_packets"] = inflight
    return {"qp_by_tag": {str(tag): value for tag, value in sorted(by_tag.items())},
            "choice_by_tag": {str(tag): value for tag, value in sorted(choices.items())},
            "background_hops": hop, "config_log_sha256": sha(path)}


def main_cell(cell, verified):
    folder = ROOT / "results" / cell["id"]
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    raw = folder / "raw" / str(meta["raw_directory"])
    logpath = folder / "logs/config.log"
    log = logpath.read_text(encoding="utf-8", errors="replace")
    return {"id": cell["id"], "seed": cell["seed"], "mode": cell["mode"],
            "source_sha": meta["git_commit"], "trace_sha256": meta["input_flow_sha256"],
            "topology_sha256": meta["topology_sha256"],
            "fct_sha256": verified["fct_sha256"], "config_log_sha256": sha(logpath),
            "moe_batch_us": verified["moe_batch_us"],
            "background_p99_us": verified["background_p99_us"],
            "cnp": old.cnp_totals(next(raw.glob("*_out_cnp.txt"))),
            "uplink": old.uplink_summary(next(raw.glob("*_out_uplink.txt"))),
            "pfc_events": sum(1 for line in next(raw.glob("*_out_pfc.txt")).open("r") if line.strip()),
            "mode_diagnostics": old.diagnostics(cell["mode"], log),
            "resource": verified["resource"]}


def paired(cells):
    lookup = {(x["seed"], x["mode"]): x for x in cells}
    output = {}
    for mode in MODES[:-1]:
        rows = []
        for seed in SEEDS:
            baseline = lookup[(seed, mode)]
            candidate = lookup[(seed, "classreserve")]
            moe = 100 * (candidate["moe_batch_us"] / baseline["moe_batch_us"] - 1)
            bg = 100 * (candidate["background_p99_us"] / baseline["background_p99_us"] - 1)
            rows.append({"seed": seed, "moe_change_pct": moe,
                         "background_p99_change_pct": bg,
                         "both_improved": moe < 0 and bg < 0})
        output[mode] = {"pairs": rows,
                        "moe_change_pct_median": statistics.median(x["moe_change_pct"] for x in rows),
                        "moe_change_pct_range": [min(x["moe_change_pct"] for x in rows),
                                                 max(x["moe_change_pct"] for x in rows)],
                        "background_p99_change_pct_median": statistics.median(
                            x["background_p99_change_pct"] for x in rows),
                        "background_p99_change_pct_range": [
                            min(x["background_p99_change_pct"] for x in rows),
                            max(x["background_p99_change_pct"] for x in rows)],
                        "moe_faster_count": sum(x["moe_change_pct"] < 0 for x in rows),
                        "background_better_count": sum(x["background_p99_change_pct"] < 0 for x in rows),
                        "both_improved_count": sum(x["both_improved"] for x in rows)}
    return output


def main():
    all_cells = calibration.cells()
    verification = calibration.verify_matrix(all_cells)
    by_id = {row["id"]: row for row in verification["cells"]}
    primary = [main_cell(cell, by_id[cell["id"]]) for cell in all_cells if cell["role"] == "primary"]
    if len(primary) != 24:
        raise RuntimeError("Expected 24 primary calibration cells")
    diagnostics = []
    for cell in all_cells:
        if cell["role"] != "diagnostic_control":
            continue
        control = parse_diagnostic(ROOT / "results" / cell["id"] / "logs/config.log")
        paired_main = next(row for row in primary if row["seed"] == cell["seed"] and
                           row["mode"] == "classreserve")
        if by_id[cell["id"]]["fct_sha256"] != paired_main["fct_sha256"]:
            raise RuntimeError("Diagnostic perturbed FCT: " + cell["id"])
        diagnostics.append({"id": cell["id"], "seed": cell["seed"],
                            "fct_sha256": by_id[cell["id"]]["fct_sha256"], **control})
    candidate = [row for row in primary if row["mode"] == "classreserve"]
    variation = {}
    for metric in ("moe_batch_us", "background_p99_us"):
        values = [row[metric] for row in candidate]
        variation[metric] = {"minimum": min(values), "median": statistics.median(values),
                             "maximum": max(values), "range": max(values) - min(values)}
    output = {"evidence_level": "four independent demand seeds for calibration; no formal efficacy",
              "source_sha": calibration.SOURCE_SHA, "topology_sha256": calibration.TOPO_SHA,
              "seeds": list(SEEDS), "modes": list(MODES),
              "verified_primary_cells": len(primary), "verified_diagnostic_cells": len(diagnostics),
              "all_diagnostic_fct_matches_primary": True,
              "candidate_variation": variation,
              "candidate_vs_baselines": paired(primary),
              "primary_cells": primary, "diagnostic_cells": diagnostics,
              "counter_limits": {
                  "cnp": "ECN and OoO reasons may overlap; neither equals retransmissions",
                  "qp": "per-QP rows are nested within each demand seed; not independent repeats",
                  "uplink": "cumulative switch uplink bytes; imbalance is not service throughput",
                  "hops": "one packet can occur on multiple flow-hop rows"}}
    OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verified_primary_cells": len(primary),
                      "verified_diagnostic_cells": len(diagnostics),
                      "paired": {mode: {key: value for key, value in row.items() if key != "pairs"}
                                 for mode, row in output["candidate_vs_baselines"].items()}},
                     sort_keys=True))


if __name__ == "__main__":
    main()
