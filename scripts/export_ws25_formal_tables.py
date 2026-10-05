#!/usr/bin/env python3
"""Export every verified WS-25 formal cell and paired seed comparison from raw."""
import csv
import json
import sys
from pathlib import Path

import analyze_moe_tags
from analyze_result import percentile

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "docs/research/evidence/ws25-v1fix-formal-analysis.json"
CELL_CSV = ROOT / "docs/research/evidence/ws25-v1fix-formal-cell-metrics.csv"
PAIR_CSV = ROOT / "docs/research/evidence/ws25-v1fix-formal-seed-pairs.csv"
MODES = ("fecmp", "drill", "conga", "letflow", "conweave", "classreserve")


def raw_file(folder, metadata):
    raw_id = str(metadata["raw_directory"])
    if not raw_id.isdigit():
        raise RuntimeError("Invalid raw directory: " + str(folder))
    path = folder / "raw" / raw_id / (raw_id + "_out_fct.txt")
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("Missing or linked FCT: " + str(path))
    return path, raw_id


def extra_percentiles(path, background):
    grouped = {"moe": {"fct": [], "slowdown": []},
               "background": {"fct": [], "slowdown": []}}
    with path.open("r", encoding="ascii") as source:
        for line in source:
            values = list(map(int, line.split()))
            if len(values) != 8 or values[6] < 0 or values[7] <= 0:
                raise RuntimeError("Malformed FCT row: " + str(path))
            kind = {8192: "moe", 8388608: "background"}.get(values[4])
            if kind is None:
                raise RuntimeError("Unexpected flow size: " + str(path))
            grouped[kind]["fct"].append(values[6] / 1000)
            grouped[kind]["slowdown"].append(max(1.0, values[6] / values[7]))
    if len(grouped["moe"]["fct"]) != 16384 or len(grouped["background"]["fct"]) != background:
        raise RuntimeError("FCT class counts differ from frozen input: " + str(path))
    for values in grouped.values():
        for key in values:
            values[key].sort()
    return grouped


def export():
    data = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    if len(data["cells"]) != 576 or data["verified_cells"] != 576:
        raise RuntimeError("Formal analysis is not a complete 576-cell matrix")
    fields = ["id", "seed", "background_flows", "mode", "source_sha", "trace_sha256",
              "topology_sha256", "fct_sha256", "raw_directory", "raw_fct_path",
              "moe_completed", "moe_mean_fct_us", "moe_p50_fct_us", "moe_p90_fct_us",
              "moe_p95_fct_us", "moe_p99_fct_us", "moe_p50_slowdown", "moe_p90_slowdown",
              "moe_p99_slowdown", "moe_batch_us", "background_completed",
              "background_mean_fct_us", "background_p50_fct_us", "background_p90_fct_us",
              "background_p95_fct_us", "background_p99_fct_us", "background_p50_slowdown",
              "background_p90_slowdown", "background_p99_slowdown", "background_batch_us"]
    rows = []
    by_key = {}
    for cell in data["cells"]:
        folder = ROOT / "results" / cell["id"]
        metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
        fct, raw_id = raw_file(folder, metadata)
        if (metadata["status"] != "SUCCEEDED" or metadata["git_commit"] != data["source_sha"] or
                metadata["input_flow_sha256"] != cell["trace_sha256"] or
                metadata["topology_sha256"] != data["topology_sha256"]):
            raise RuntimeError("Cell identity mismatch: " + cell["id"])
        summary = analyze_moe_tags.summarize(cell["id"])
        if summary["fct_sha256"] != cell["fct_sha256"]:
            raise RuntimeError("FCT hash mismatch: " + cell["id"])
        moe = summary["tags"]["2"]
        bg = summary["tags"].get("1")
        if (moe["input_flows"] != moe["completed_flows"] or
                moe["synthetic_batch_completion_us"] != cell["moe_batch_us"] or
                (cell["background"] and (bg is None or bg["completed_flows"] != cell["background"] or
                                           abs(bg["p99_fct_us"] - cell["background_p99_us"]) > 1e-9))):
            raise RuntimeError("Class metric mismatch: " + cell["id"])
        extra = extra_percentiles(fct, cell["background"])
        row = {"id": cell["id"], "seed": cell["seed"], "background_flows": cell["background"],
               "mode": cell["mode"], "source_sha": data["source_sha"],
               "trace_sha256": cell["trace_sha256"], "topology_sha256": data["topology_sha256"],
               "fct_sha256": cell["fct_sha256"], "raw_directory": raw_id,
               "raw_fct_path": str(fct.relative_to(ROOT)).replace("\\", "/"),
               "moe_completed": moe["completed_flows"], "moe_mean_fct_us": moe["mean_fct_us"],
               "moe_p50_fct_us": moe["p50_fct_us"], "moe_p90_fct_us": percentile(extra["moe"]["fct"], 90),
               "moe_p95_fct_us": moe["p95_fct_us"], "moe_p99_fct_us": moe["p99_fct_us"],
               "moe_p50_slowdown": percentile(extra["moe"]["slowdown"], 50),
               "moe_p90_slowdown": percentile(extra["moe"]["slowdown"], 90),
               "moe_p99_slowdown": percentile(extra["moe"]["slowdown"], 99),
               "moe_batch_us": cell["moe_batch_us"],
               "background_completed": bg["completed_flows"] if bg else 0,
               "background_mean_fct_us": bg["mean_fct_us"] if bg else "",
               "background_p50_fct_us": bg["p50_fct_us"] if bg else "",
               "background_p90_fct_us": percentile(extra["background"]["fct"], 90) if bg else "",
               "background_p95_fct_us": bg["p95_fct_us"] if bg else "",
               "background_p99_fct_us": bg["p99_fct_us"] if bg else "",
               "background_p50_slowdown": percentile(extra["background"]["slowdown"], 50) if bg else "",
               "background_p90_slowdown": percentile(extra["background"]["slowdown"], 90) if bg else "",
               "background_p99_slowdown": percentile(extra["background"]["slowdown"], 99) if bg else "",
               "background_batch_us": bg["synthetic_batch_completion_us"] if bg else ""}
        key = (cell["seed"], cell["background"], cell["mode"])
        if key in by_key:
            raise RuntimeError("Duplicate cell identity: " + repr(key))
        by_key[key] = row
        rows.append(row)
    if len(by_key) != 576:
        raise RuntimeError("Missing formal cell")
    rows.sort(key=lambda row: (row["seed"], row["background_flows"], MODES.index(row["mode"])))
    with CELL_CSV.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    pair_fields = ["seed", "background_flows", "metric", "baseline", "baseline_id",
                   "classreserve_id", "baseline_value_us", "classreserve_value_us", "change_pct"]
    pairs = []
    for seed in range(20262521, 20262545):
        for background in (0, 64, 128, 192):
            candidate = by_key[seed, background, "classreserve"]
            for baseline in MODES[:-1]:
                control = by_key[seed, background, baseline]
                for metric in ("moe_batch_us", "background_p99_fct_us"):
                    if metric.startswith("background") and background == 0:
                        continue
                    base_value = float(control[metric])
                    candidate_value = float(candidate[metric])
                    pairs.append({"seed": seed, "background_flows": background,
                                  "metric": metric, "baseline": baseline,
                                  "baseline_id": control["id"], "classreserve_id": candidate["id"],
                                  "baseline_value_us": base_value,
                                  "classreserve_value_us": candidate_value,
                                  "change_pct": 100 * (candidate_value / base_value - 1)})
    if len(pairs) != 24 * (5 + 3 * 10):
        raise RuntimeError("Paired comparison count mismatch")
    with PAIR_CSV.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=pair_fields)
        writer.writeheader()
        writer.writerows(pairs)
    print(json.dumps({"cells": len(rows), "pairs": len(pairs),
                      "cell_csv": str(CELL_CSV), "pair_csv": str(PAIR_CSV)}))


if __name__ == "__main__":
    export()
