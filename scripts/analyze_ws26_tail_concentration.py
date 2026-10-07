"""Describe destination concentration among WS-25 formal background tail flows.

This is post-hoc WS-26 mechanism diagnosis, never a formal efficacy test.
"""

import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/research/evidence/ws25-v1fix-formal-plan.json"
OUTPUT = ROOT / "docs/research/evidence/ws26-tail-concentration.json"
MODES = ("fecmp", "classreserve")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values, fraction):
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[min(lower + 1, len(ordered) - 1)] * weight


def trace_background(path, expected_sha):
    if sha256(path) != expected_sha:
        raise ValueError("trace hash mismatch: {}".format(path))
    lines = path.read_text(encoding="ascii").splitlines()
    if int(lines[0]) != len(lines) - 1:
        raise ValueError("trace count mismatch: {}".format(path))
    background = []
    for line in lines[1:]:
        src, dst, _, size, _, tag = line.split()
        if tag == "1":
            if int(size) != 8388608:
                raise ValueError("unexpected background size")
            background.append((int(src), int(dst)))
    if len(background) != 192 or len(set(background)) != 192:
        raise ValueError("background identity mismatch: {}".format(path))
    return background


def fct_background(results_root, cell, background):
    files = list((results_root / cell["id"] / "raw").glob("*/*_out_fct.txt"))
    if len(files) != 1:
        raise ValueError("expected one FCT raw: {}".format(cell["id"]))
    result = {}
    total = 0
    with files[0].open(encoding="ascii") as handle:
        for line in handle:
            parts = line.split()
            if len(parts) < 8:
                raise ValueError("malformed FCT: {}".format(files[0]))
            src, dst, _, _, size, start, fct = map(int, parts[:7])
            total += 1
            if start != 2000000000:
                raise ValueError("unexpected flow start: {}".format(files[0]))
            if size == 8388608:
                key = (src, dst)
                if key in result:
                    raise ValueError("duplicate background FCT: {}".format(key))
                result[key] = fct
    if total != 16576 or set(result) != set(background):
        raise ValueError("incomplete FCT: {}".format(cell["id"]))
    return result, sha256(files[0])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", type=Path, default=ROOT / "results")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    cells = {(cell["seed"], cell["background"], cell["mode"]): cell
             for cell in plan["cells"]}
    seeds = sorted({seed for seed, level, mode in cells
                    if level == 192 and mode == "fecmp"})
    if len(seeds) != 24:
        raise ValueError("expected 24 independent demand seeds")
    rows = []
    for seed in seeds:
        anchor = cells[seed, 192, "fecmp"]
        background = trace_background(ROOT / "config" / anchor["trace"],
                                      anchor["trace_sha256"])
        dst_count = Counter(dst for _, dst in background)
        src_count = Counter(src for src, _ in background)
        for mode in MODES:
            cell = cells[seed, 192, mode]
            if cell["trace_sha256"] != anchor["trace_sha256"]:
                raise ValueError("arm input mismatch: {}".format(seed))
            fct, fct_sha = fct_background(args.results_root, cell, background)
            tail = sorted(fct, key=lambda key: fct[key], reverse=True)[:3]
            rows.append({
                "seed": seed, "mode": mode, "id": cell["id"],
                "trace_sha256": cell["trace_sha256"], "fct_sha256": fct_sha,
                "background_p99_fct_ns": percentile(list(fct.values()), 0.99),
                "all_destination_multiplicity_median": statistics.median(dst_count.values()),
                "tail3": [{"src": src, "dst": dst, "fct_ns": fct[src, dst],
                           "destination_multiplicity": dst_count[dst],
                           "source_multiplicity": src_count[src]}
                          for src, dst in tail],
            })
    summary = {}
    for mode in MODES:
        chosen = [row for row in rows if row["mode"] == mode]
        tail_counts = [item["destination_multiplicity"]
                       for row in chosen for item in row["tail3"]]
        all_counts = []
        for row in chosen:
            trace = ROOT / "config" / cells[row["seed"], 192, mode]["trace"]
            background = trace_background(trace, row["trace_sha256"])
            counts = Counter(dst for _, dst in background)
            all_counts.extend(counts[dst] for _, dst in background)
        summary[mode] = {
            "tail3_destination_multiplicity_median": statistics.median(tail_counts),
            "tail3_destination_multiplicity_ge5": sum(x >= 5 for x in tail_counts),
            "tail3_flows": len(tail_counts),
            "all_background_destination_multiplicity_median": statistics.median(all_counts),
            "all_background_destination_multiplicity_ge5": sum(x >= 5 for x in all_counts),
            "all_background_flows": len(all_counts),
            "seeds_with_shared_destination_in_tail3": sum(
                len({item["dst"] for item in row["tail3"]}) < 3 for row in chosen),
        }
    by_key = {(row["seed"], row["mode"]): row for row in rows}
    summary["paired_tail_overlap"] = {
        "same_flow_entries_in_top3": sum(
            len({(x["src"], x["dst"]) for x in by_key[seed, "fecmp"]["tail3"]} &
                {(x["src"], x["dst"]) for x in by_key[seed, "classreserve"]["tail3"]})
            for seed in seeds),
        "same_destination_entries_in_top3": sum(
            len({x["dst"] for x in by_key[seed, "fecmp"]["tail3"]} &
                {x["dst"] for x in by_key[seed, "classreserve"]["tail3"]})
            for seed in seeds),
    }
    output = {"kind": "posthoc_ws25_formal_tail_concentration",
              "independent_seeds": len(seeds), "background_level": 192,
              "plan_sha256": sha256(PLAN), "summary": summary, "rows": rows,
              "limits": "Tail selection is post-hoc; destination multiplicity is demand, not a path or queue measurement."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
