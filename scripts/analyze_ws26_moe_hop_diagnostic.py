#!/usr/bin/env python3
"""Summarize the frozen WS-26 MoE hop diagnostic from verified raw data."""

import collections
import hashlib
import json
import statistics
from pathlib import Path

import analyze_result
import verify_ws26_moe_hop_diagnostic as verifier


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/research/evidence/ws26-moe-hop-diagnostic-analysis.json"
TAGS = {1: "background", 2: "moe"}
REGIONS = ("source_tor", "transit", "destination_tor")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def quantiles(values):
    ordered = sorted(values)
    if not ordered:
        return {"count": 0, "p50": None, "p95": None, "p99": None, "max": None}
    return {"count": len(ordered),
            "p50": analyze_result.percentile(ordered, 50),
            "p95": analyze_result.percentile(ordered, 95),
            "p99": analyze_result.percentile(ordered, 99),
            "max": ordered[-1]}


def read_cell(cell, plan):
    verified = verifier.check(cell, plan)
    folder = ROOT / "results" / cell["id"]
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    trace = verifier.trace_qps(folder / "config/traffic_trace.txt")
    fct_path = verifier.raw_fct(folder, metadata)
    fct = {}
    with fct_path.open(encoding="ascii") as source:
        for line in source:
            values = list(map(int, line.split()))
            key = tuple(values[:4])
            fct[key] = {"tag": trace[key]["tag"], "fct_ns": values[6],
                        "end_ns": values[5] + values[6], "size": values[4]}

    _, _, host_tors, port_to_neighbor = verifier.topology_maps(
        folder / "config/topology.txt")
    hop_rows = collections.defaultdict(list)
    log = folder / "logs/config.log"
    with log.open(encoding="utf-8", errors="replace") as source:
        for line in source:
            if line.startswith("WS26_MOE_HOP "):
                tag = 2
            elif line.startswith("WS13_HOP "):
                tag = 1
            else:
                continue
            row = verifier.fields(line)
            row["tag"] = tag
            hop_rows[(row["src"], row["dst"], row["sport"], row["dport"])].append(row)

    raw = folder / "raw" / str(metadata["raw_directory"])
    cnp_path = verifier.unique_file(raw, "*_out_cnp.txt")
    pfc_path = verifier.unique_file(raw, "*_out_pfc.txt")
    cnp_by_host = collections.defaultdict(lambda: {"ecn": 0, "ooo": 0, "total": 0})
    with cnp_path.open(encoding="ascii") as source:
        for line in source:
            row = list(map(int, line.split()))
            if len(row) != 5:
                raise RuntimeError("Malformed CNP row in " + cell["id"])
            host = row[1]
            cnp_by_host[host]["ecn"] += row[2]
            cnp_by_host[host]["ooo"] += row[3]
            cnp_by_host[host]["total"] += row[4]
    with pfc_path.open(encoding="ascii") as source:
        pfc_events = sum(bool(line.strip()) for line in source)
    resource_samples = [json.loads(line) for line in
                       (folder / "logs/resource-samples.jsonl").read_text(
                           encoding="utf-8").splitlines() if line.strip()]

    rows_by_key = {}
    for key, flow in fct.items():
        rows = hop_rows[key]
        ordered = verifier.path_for(rows, key[0], key[1], len(host_tors),
                                    host_tors, port_to_neighbor)
        hops = []
        for row in ordered:
            neighbor = port_to_neighbor[row["switch"]][row["port"] - 1]
            hops.append({"switch": row["switch"], "port": row["port"],
                         "neighbor": neighbor, "wait_ns_max": row["wait_ns_max"],
                         "queued_bytes_max": row["queued_bytes_max"],
                         "packets": row["packets"], "bytes": row["bytes"]})
        src_tor, dst_tor = host_tors[key[0]], host_tors[key[1]]
        source_region = [hops[0]] if hops and hops[0]["switch"] == src_tor and src_tor != dst_tor else []
        destination_region = [hops[-1]] if hops and hops[-1]["switch"] == dst_tor else []
        transit_region = hops[1:-1] if src_tor != dst_tor else []
        regions = {"source_tor": source_region, "transit": transit_region,
                   "destination_tor": destination_region}
        region_max = {}
        for name, region_hops in regions.items():
            region_max[name] = ({"wait_ns": max(h["wait_ns_max"] for h in region_hops),
                                 "queued_bytes": max(h["queued_bytes_max"] for h in region_hops)}
                                if region_hops else None)
        cnp = cnp_by_host[key[1]]
        rows_by_key[key] = {"tag": flow["tag"], "fct_us": flow["fct_ns"] / 1000,
                            "end_ns": flow["end_ns"], "size_bytes": flow["size"],
                            "source": key[0], "destination": key[1],
                            "sport": key[2], "dport": key[3], "source_tor": src_tor,
                            "destination_tor": dst_tor, "path": hops,
                            "regions": region_max,
                            "destination_host_cnp_aggregate": cnp}

    trace_start = min(row["start_ns"] for row in trace.values())
    class_stats = {}
    region_stats = {}
    tails = {}
    for tag, name in TAGS.items():
        class_rows = [row for row in rows_by_key.values() if row["tag"] == tag]
        fcts = [row["fct_us"] for row in class_rows]
        class_stats[name] = {"flow_count": len(class_rows), "mean_fct_us": statistics.mean(fcts),
                             "p50_fct_us": analyze_result.percentile(sorted(fcts), 50),
                             "p95_fct_us": analyze_result.percentile(sorted(fcts), 95),
                             "p99_fct_us": analyze_result.percentile(sorted(fcts), 99),
                             "batch_completion_us": (max(row["end_ns"] for row in class_rows) -
                                                     trace_start) / 1000}
        region_stats[name] = {}
        for region in REGIONS:
            candidates = [row for row in class_rows if row["regions"][region] is not None]
            region_stats[name][region] = {
                "wait_ns_max_per_qp": quantiles([row["regions"][region]["wait_ns"]
                                                   for row in candidates]),
                "queued_bytes_max_per_qp": quantiles([row["regions"][region]["queued_bytes"]
                                                        for row in candidates])}
        ordered = sorted(class_rows, key=lambda row: (-row["fct_us"], row["source"],
                                                       row["destination"], row["sport"], row["dport"]))
        tails[name] = ordered[:3]

    cnp_totals = {"ecn": sum(row["ecn"] for row in cnp_by_host.values()),
                  "ooo": sum(row["ooo"] for row in cnp_by_host.values()),
                  "total": sum(row["total"] for row in cnp_by_host.values()),
                  "hosts_with_feedback": sum(row["total"] > 0 for row in cnp_by_host.values())}
    return {"id": cell["id"], "seed": cell["seed"], "mode": cell["mode"],
            "stage": cell["stage"], "trace_sha256": cell["trace_sha256"],
            "fct_sha256": verified["fct_file_sha256"],
            "config_log_sha256": verified["config_log_sha256"],
            "paired_plain_id": cell["paired_plain_id"],
            "flow_count": verified["flow_count"], "tag_counts": verified["tag_counts"],
            "hop_qp_count": verified["hop_qp_count"],
            "inflight_unpaired": verified["inflight_unpaired"],
            "resource": verified["resource"], "resource_sample_count": verified["resource_sample_count"],
            "max_load_1m": max(row["load_1m"] for row in resource_samples),
            "pfc_events": pfc_events, "cnp_host_aggregate": cnp_totals,
            "classes": class_stats, "regions": region_stats, "slowest_qps": tails}


def pair_seed(ecmp, candidate):
    delta = {}
    for cls in ("moe", "background"):
        base = ecmp["classes"][cls]
        variant = candidate["classes"][cls]
        delta[cls] = {metric: {"ecmp": base[metric], "classlane4": variant[metric],
                               "change_percent": 100 * (variant[metric] / base[metric] - 1)}
                      for metric in ("mean_fct_us", "p50_fct_us", "p95_fct_us", "p99_fct_us")}
    delta["moe"]["batch_completion_us"] = {
        "ecmp": ecmp["classes"]["moe"]["batch_completion_us"],
        "classlane4": candidate["classes"]["moe"]["batch_completion_us"],
        "change_percent": 100 * (candidate["classes"]["moe"]["batch_completion_us"] /
                                  ecmp["classes"]["moe"]["batch_completion_us"] - 1)}

    # Read per-QP identity data from the verifier's local FCT and log files.
    cell_info = {"fecmp": ecmp, "classlane4": candidate}
    flows = {mode: per_qp_rows(ROOT / "results" / row["id"], row)
             for mode, row in cell_info.items()}
    keys = set(flows["fecmp"])
    if keys != set(flows["classlane4"]):
        raise RuntimeError("Paired QP identities differ for seed " + str(ecmp["seed"]))
    comparisons = {}
    for tag, name in ((2, "moe"), (1, "background")):
        pairs = [(flows["fecmp"][key], flows["classlane4"][key]) for key in keys
                 if flows["fecmp"][key]["tag"] == tag]
        counts = collections.Counter()
        for left, right in pairs:
            if left["tag"] != right["tag"] or left["same_tor"] != right["same_tor"]:
                raise RuntimeError("Paired QP metadata differ for seed " + str(ecmp["seed"]))
            fct_up = right["fct_ns"] > left["fct_ns"]
            counts["fct_up"] += fct_up
            if left["same_tor"]:
                counts["same_tor_qp_pairs"] += 1
                counts["same_tor_fct_up"] += fct_up
            for region in REGIONS:
                if left["regions"][region] is not None and right["regions"][region] is not None:
                    counts[region + "_comparable_qp_pairs"] += 1
                    counts[region + "_fct_up_qp_pairs"] += fct_up
                    wait_up = right["regions"][region]["wait_ns"] > left["regions"][region]["wait_ns"]
                    queue_up = right["regions"][region]["queued_bytes"] > left["regions"][region]["queued_bytes"]
                    counts[region + "_wait_up"] += wait_up
                    counts[region + "_queue_up"] += queue_up
                    counts[region + "_fct_up_and_wait_up"] += fct_up and wait_up
                    counts[region + "_fct_up_without_wait_up"] += fct_up and not wait_up
        comparisons[name] = {"qp_pairs": len(pairs), "counts_with_classlane4_increase": dict(counts)}
    tail_pairs = {}
    for tag, name in ((2, "moe"), (1, "background")):
        candidate_keys = [key for key in keys if flows["classlane4"][key]["tag"] == tag]
        slowest = sorted(candidate_keys, key=lambda key: -flows["classlane4"][key]["fct_ns"])[:3]
        tail_pairs[name] = [{"classlane4": flows["classlane4"][key],
                             "fecmp_same_qp": flows["fecmp"][key],
                             "fct_change_us": (flows["classlane4"][key]["fct_ns"] -
                                               flows["fecmp"][key]["fct_ns"]) / 1000}
                            for key in slowest]
    return {"seed": ecmp["seed"], "metrics": delta, "cnp": {
                "ecn": {"ecmp": ecmp["cnp_host_aggregate"]["ecn"],
                        "classlane4": candidate["cnp_host_aggregate"]["ecn"]},
                "ooo": {"ecmp": ecmp["cnp_host_aggregate"]["ooo"],
                        "classlane4": candidate["cnp_host_aggregate"]["ooo"]},
                "pfc_events": {"ecmp": ecmp["pfc_events"],
                               "classlane4": candidate["pfc_events"]}},
            "regions": compare_regions(ecmp, candidate),
            "paired_qp_sign_counts": comparisons,
            "classlane4_slowest_qp_pairs": tail_pairs,
            "slowest_qps": {"fecmp": ecmp["slowest_qps"],
                            "classlane4": candidate["slowest_qps"]}}


def per_qp_rows(folder, cell):
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    expected = verifier.trace_qps(folder / "config/traffic_trace.txt")
    fct_path = verifier.raw_fct(folder, meta)
    fct = {}
    with fct_path.open(encoding="ascii") as source:
        for line in source:
            values = list(map(int, line.split()))
            key = tuple(values[:4])
            fct[key] = {"tag": expected[key]["tag"], "fct_ns": values[6]}
    _, _, host_tors, port_to_neighbor = verifier.topology_maps(folder / "config/topology.txt")
    hop_rows = collections.defaultdict(list)
    with (folder / "logs/config.log").open(encoding="utf-8", errors="replace") as source:
        for line in source:
            if line.startswith("WS26_MOE_HOP "):
                tag = 2
            elif line.startswith("WS13_HOP "):
                tag = 1
            else:
                continue
            row = verifier.fields(line)
            row["tag"] = tag
            hop_rows[(row["src"], row["dst"], row["sport"], row["dport"])].append(row)
    result = {}
    raw = folder / "raw" / str(meta["raw_directory"])
    cnp_by_host = collections.defaultdict(lambda: {"ecn": 0, "ooo": 0, "total": 0})
    with verifier.unique_file(raw, "*_out_cnp.txt").open(encoding="ascii") as source:
        for line in source:
            values = list(map(int, line.split()))
            cnp_by_host[values[1]]["ecn"] += values[2]
            cnp_by_host[values[1]]["ooo"] += values[3]
            cnp_by_host[values[1]]["total"] += values[4]
    for key in fct:
        path = verifier.path_for(hop_rows[key], key[0], key[1], len(host_tors),
                                 host_tors, port_to_neighbor)
        hops = [{"switch": row["switch"], "port": row["port"],
                 "neighbor": port_to_neighbor[row["switch"]][row["port"] - 1],
                 "wait_ns_max": row["wait_ns_max"],
                 "queued_bytes_max": row["queued_bytes_max"]} for row in path]
        src_tor, dst_tor = host_tors[key[0]], host_tors[key[1]]
        regions = {"source_tor": [], "transit": [], "destination_tor": []}
        for index, row in enumerate(path):
            if index == 0 and src_tor != dst_tor:
                regions["source_tor"].append(row)
            elif index == len(path) - 1:
                regions["destination_tor"].append(row)
            elif index > 0:
                regions["transit"].append(row)
        result[key] = {"tag": fct[key]["tag"], "fct_ns": fct[key]["fct_ns"],
                       "source": key[0], "destination": key[1],
                       "same_tor": src_tor == dst_tor,
                       "sport": key[2], "dport": key[3], "path": hops,
                       "destination_host_cnp_aggregate": cnp_by_host[key[1]],
                       "regions": {region: ({"wait_ns": max(row["wait_ns_max"] for row in rows),
                                             "queued_bytes": max(row["queued_bytes_max"] for row in rows)}
                                            if rows else None)
                                   for region, rows in regions.items()}}
    return result


def compare_regions(ecmp, candidate):
    output = {}
    for cls in ("moe", "background"):
        output[cls] = {}
        for region in REGIONS:
            output[cls][region] = {}
            for metric, key in (("wait_ns_max_per_qp", "wait_ns_max_per_qp"),
                                ("queued_bytes_max_per_qp", "queued_bytes_max_per_qp")):
                left = ecmp["regions"][cls][region][key]
                right = candidate["regions"][cls][region][key]
                output[cls][region][metric] = {
                    "ecmp": left, "classlane4": right,
                    "p50_change_percent": 100 * (right["p50"] / left["p50"] - 1)
                    if left["p50"] and right["p50"] else None,
                    "p95_change_percent": 100 * (right["p95"] / left["p95"] - 1)
                    if left["p95"] and right["p95"] else None,
                    "p99_change_percent": 100 * (right["p99"] / left["p99"] - 1)
                    if left["p99"] and right["p99"] else None}
    return output


def aggregate():
    plan = verifier.load_plan()
    high_cells = [cell for cell in plan["cells"] if cell["stage"] == "paired_high_diagnostic"]
    cells = [read_cell(cell, plan) for cell in high_cells]
    by_seed = collections.defaultdict(dict)
    for cell in cells:
        by_seed[cell["seed"]][cell["mode"]] = cell
    seeds = [pair_seed(by_seed[seed]["fecmp"], by_seed[seed]["classlane4"])
             for seed in sorted(by_seed)]
    changes = {name: [row["metrics"]["moe"]["batch_completion_us"]["change_percent"]
                      for row in seeds] for name in ("moe",)}
    changes["background_p99"] = [row["metrics"]["background"]["p99_fct_us"]["change_percent"]
                                  for row in seeds]
    output = {"analysis": "paired mechanism diagnostic only; no pilot rejudgment or causal claim",
              "source_sha": verifier.SOURCE_SHA,
              "plan_sha256": verifier.PLAN_SHA256,
              "topology_sha256": verifier.TOPOLOGY_SHA256,
              "independent_unit": "seed (four seeds; QPs are within-seed observations)",
              "verified_high_cells": len(cells), "cells": cells,
              "seeds": seeds,
              "paired_change_summary": {key: {"values_percent": values,
                  "median_percent": statistics.median(values),
                  "improved_seeds": sum(value < 0 for value in values),
                  "worsened_seeds": sum(value > 0 for value in values)}
                  for key, values in changes.items()},
              "limits": ["four previously revealed seeds are not independent new pilot data",
                         "device egress queue observations are not physical MMU occupancy",
                         "hop maxima are not packet-time aligned and cannot be summed as FCT",
                         "CNP totals are destination-host aggregates, not per-QP feedback attribution",
                         "diagnostic does not establish causal mechanism or performance benefit"]}
    rendered = json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    OUT.write_text(rendered, encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(OUT), "sha256": sha256(OUT),
                      "verified_high_cells": len(cells),
                      "moe_batch_change_percent": changes["moe"],
                      "background_p99_change_percent": changes["background_p99"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    aggregate()
