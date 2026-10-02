#!/usr/bin/env python3
"""Describe WS-25 C2/C3 independent calibration without treating it as efficacy."""
import hashlib
import json
import statistics
from pathlib import Path

import analyze_moe_tags
import analyze_ws25_calibration as raw_analysis
import run_ws25_calibration_v3 as v3
import verify_ws25_preflight as c2

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (20262501, 20262502, 20262503, 20262504)


def hash_file(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def identity(seed, mode):
    i = c2.MODES.index(mode)
    if seed == 20262501:
        return {"id": "20261002-22400%d-ws25-v2-cal01-%s" % (i, mode),
                "source_sha": c2.COMMIT, "trace_sha256": c2.CAL192_SHA}
    entry = next(x for x in v3.cells() if x["seed"] == seed and x["mode"] == mode)
    return {"id": entry["id"], "source_sha": v3.SOURCE_SHA,
            "trace_sha256": entry["trace_sha256"]}


def cell(seed, mode):
    expected = identity(seed, mode)
    experiment_id = expected["id"]
    if seed == 20262501:
        verification = c2.verify(experiment_id, "pilot", mode)
        resource = verification["resource"]
    else:
        verification = v3.verify(next(x for x in v3.cells() if x["id"] == experiment_id))
        resource = verification["resource"]
    folder = ROOT / "results" / experiment_id
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    if meta["git_commit"] != expected["source_sha"] or meta["input_flow_sha256"] != expected["trace_sha256"]:
        raise ValueError("Source/input identity mismatch: " + experiment_id)
    raw = folder / "raw" / str(meta["raw_directory"])
    stats = analyze_moe_tags.summarize(experiment_id)
    if (stats["tags"]["1"]["input_flows"], stats["tags"]["1"]["completed_flows"],
            stats["tags"]["2"]["input_flows"], stats["tags"]["2"]["completed_flows"]) != (192, 192, 16384, 16384):
        raise ValueError("Incomplete calibration cell")
    log_path = folder / "logs" / "config.log"
    log = log_path.read_text(encoding="utf-8", errors="replace")
    fct = next(raw.glob("*_out_fct.txt"))
    cnp = raw_analysis.cnp_totals(next(raw.glob("*_out_cnp.txt")))
    uplink = raw_analysis.uplink_summary(next(raw.glob("*_out_uplink.txt")))
    diagnostics = raw_analysis.diagnostics(mode, log)
    return {
        "seed": seed, "mode": mode, "experiment_id": experiment_id,
        "source_sha": expected["source_sha"],
        "trace_sha256": expected["trace_sha256"],
        "topology_sha256": meta["topology_sha256"],
        "fct_sha256": hash_file(fct),
        "config_log_sha256": hash_file(log_path),
        "moe_batch_us": stats["tags"]["2"]["synthetic_batch_completion_us"],
        "moe_mean_fct_us": stats["tags"]["2"]["mean_fct_us"],
        "moe_p99_fct_us": stats["tags"]["2"]["p99_fct_us"],
        "background_p99_fct_us": stats["tags"]["1"]["p99_fct_us"],
        "background_mean_fct_us": stats["tags"]["1"]["mean_fct_us"],
        "background_batch_us": stats["tags"]["1"]["synthetic_batch_completion_us"],
        "cnp": cnp, "uplink": uplink, "diagnostics": diagnostics,
        "pfc_events": len(next(raw.glob("*_out_pfc.txt")).read_text().splitlines()),
        "resource": resource,
    }


def paired_summary(cells):
    lookup = {(x["seed"], x["mode"]): x for x in cells}
    output = {}
    for mode in c2.MODES[:-1]:
        pairs = []
        for seed in SEEDS:
            baseline = lookup[(seed, mode)]
            candidate = lookup[(seed, "classreserve")]
            moe_change = 100.0 * (candidate["moe_batch_us"] / baseline["moe_batch_us"] - 1.0)
            background_change = 100.0 * (
                candidate["background_p99_fct_us"] / baseline["background_p99_fct_us"] - 1.0)
            pairs.append({"seed": seed, "moe_change_pct": moe_change,
                          "background_p99_change_pct": background_change,
                          "both_improved": moe_change < 0 and background_change < 0})
        output[mode] = {
            "pairs": pairs,
            "moe_change_pct_median": statistics.median(x["moe_change_pct"] for x in pairs),
            "moe_change_pct_range": [min(x["moe_change_pct"] for x in pairs),
                                     max(x["moe_change_pct"] for x in pairs)],
            "background_p99_change_pct_median": statistics.median(
                x["background_p99_change_pct"] for x in pairs),
            "background_p99_change_pct_range": [
                min(x["background_p99_change_pct"] for x in pairs),
                max(x["background_p99_change_pct"] for x in pairs)],
            "moe_faster_count": sum(x["moe_change_pct"] < 0 for x in pairs),
            "background_better_count": sum(x["background_p99_change_pct"] < 0 for x in pairs),
            "both_improved_count": sum(x["both_improved"] for x in pairs),
        }
    return output


def main():
    cells = [cell(seed, mode) for seed in SEEDS for mode in c2.MODES]
    if len(cells) != 24 or len({x["experiment_id"] for x in cells}) != 24:
        raise ValueError("Missing or duplicated calibration cell")
    output = {
        "evidence_level": "four independent demand seeds for calibration only; no final efficacy claim",
        "seeds": list(SEEDS), "modes": list(c2.MODES), "cells": cells,
        "candidate_vs_baselines": paired_summary(cells),
        "note": "Positive percent change means ClassReserve is slower/worse. Each seed is one independent demand; six arms are paired within seed.",
    }
    path = ROOT / "docs" / "research" / "evidence" / "ws25-four-seed-calibration.json"
    path.write_text(json.dumps(output, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(path), "verified_cells": len(cells),
                      "pairs_per_baseline": len(SEEDS)}, sort_keys=True))


if __name__ == "__main__":
    main()
