#!/usr/bin/env python3
"""Recompute descriptive WS-25 lower-load comparisons from fetched raw cells."""
import hashlib
import json
import statistics
from pathlib import Path

import analyze_ws25_calibration as diagnostics
import run_ws25_lower_load_calibration as calibration

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/research/evidence/ws25-v1fix-lower-load-analysis.json"
EXECUTION = ROOT / "docs/research/evidence/ws25-v1fix-lower-load-calibration.json"
MODES = ("fecmp", "drill", "conga", "letflow", "conweave", "classreserve")
LEVELS = (0, 64, 128)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def raw_cell(cell, verified):
    folder = ROOT / "results" / cell["id"]
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    raw = folder / "raw" / str(meta["raw_directory"])
    logpath = folder / "logs/config.log"
    log = logpath.read_text(encoding="utf-8", errors="replace")
    cnp = diagnostics.cnp_totals(next(raw.glob("*_out_cnp.txt")))
    uplink = diagnostics.uplink_summary(next(raw.glob("*_out_uplink.txt")))
    pfc = sum(bool(line.strip()) for line in next(raw.glob("*_out_pfc.txt")).open("r"))
    return {
        "id": cell["id"], "seed": cell["seed"], "background": cell["background"],
        "mode": cell["mode"], "source_sha": meta["git_commit"],
        "trace_sha256": meta["input_flow_sha256"],
        "topology_sha256": meta["topology_sha256"],
        "fct_sha256": verified["fct_sha256"],
        "config_log_sha256": sha(logpath),
        "moe_batch_us": verified["moe_batch_us"],
        "background_p99_us": verified["background_p99_us"],
        "cnp": cnp, "uplink": uplink, "pfc_events": pfc,
        "mode_diagnostics": diagnostics.diagnostics(cell["mode"], log),
        "resource": verified["resource"],
    }


def paired(rows):
    by_key = {(row["seed"], row["background"], row["mode"]): row for row in rows}
    seeds = sorted({row["seed"] for row in rows})
    result = {}
    for level in LEVELS:
        comparisons = {}
        for mode in MODES[:-1]:
            pairs = []
            for seed in seeds:
                baseline = by_key[(seed, level, mode)]
                candidate = by_key[(seed, level, "classreserve")]
                moe = 100 * (candidate["moe_batch_us"] / baseline["moe_batch_us"] - 1)
                bg = (100 * (candidate["background_p99_us"] /
                              baseline["background_p99_us"] - 1) if level else None)
                pairs.append({"seed": seed, "moe_change_pct": moe,
                              "background_p99_change_pct": bg,
                              "both_improved": moe < 0 and bg < 0 if bg is not None else None})
            moe = [item["moe_change_pct"] for item in pairs]
            bg = [item["background_p99_change_pct"] for item in pairs if level]
            comparisons[mode] = {
                "pairs": pairs,
                "moe_median_change_pct": statistics.median(moe),
                "moe_range_change_pct": [min(moe), max(moe)],
                "moe_faster_count": sum(value < 0 for value in moe),
                "background_median_change_pct": statistics.median(bg) if bg else None,
                "background_range_change_pct": [min(bg), max(bg)] if bg else None,
                "background_better_count": sum(value < 0 for value in bg) if bg else None,
                "both_improved_count": sum(item["both_improved"] for item in pairs)
                                       if bg else None,
            }
        result[str(level)] = comparisons
    return result


def main():
    cells = calibration.frozen_plan()["cells"]
    verified = {cell["id"]: calibration.verify(cell) for cell in cells}
    execution = json.loads(EXECUTION.read_text(encoding="utf-8"))
    old = {cell["id"]: cell for cell in execution["verified_cells"]}
    if not len(cells) == len(verified) == len(old):
        raise RuntimeError("Incomplete or duplicate cell set")
    for cell in cells:
        now, before = verified[cell["id"]], old[cell["id"]]
        for key in ("fct_sha256", "trace_sha256", "moe_batch_us", "background_p99_us"):
            if now[key] != before[key]:
                raise RuntimeError("Execution summary differs from raw: %s %s" % (cell["id"], key))
    rows = [raw_cell(cell, verified[cell["id"]]) for cell in cells]
    if len(rows) != 72:
        raise RuntimeError("Expected 72 calibration cells")
    if any(row["pfc_events"] for row in rows):
        raise RuntimeError("Unexpected PFC events")
    output = {
        "evidence_level": "four demand seeds, exploratory lower-load calibration; no formal efficacy",
        "source_sha": calibration.calibration.SOURCE_SHA,
        "topology_sha256": calibration.calibration.TOPO_SHA,
        "execution_summary_sha256": sha(EXECUTION), "verified_cells": len(rows),
        "seeds": sorted({row["seed"] for row in rows}),
        "background_levels": list(LEVELS), "modes": list(MODES),
        "paired": paired(rows), "cells": rows,
        "limits": {
            "replication": "Demand seed is the independent unit; levels and flows within seed are repeated observations",
            "zero_background": "Background P99 and joint improvement are undefined at background=0",
            "cnp": "ECN and OoO reasons may overlap; CNP is not a retransmission count",
            "uplink": "Cumulative uplink bytes show distribution, not end-to-end throughput or MMU occupancy",
            "dynamic_branches": "A zero diagnostic counter means that branch was not covered in this input",
        },
    }
    OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verified_cells": len(rows), "output": str(OUTPUT),
                      "comparison_counts": {level: {mode: {
                          "moe_faster": item["moe_faster_count"],
                          "background_better": item["background_better_count"],
                          "both_improved": item["both_improved_count"]}
                          for mode, item in modes.items()}
                          for level, modes in output["paired"].items()}}, sort_keys=True))


if __name__ == "__main__":
    main()
