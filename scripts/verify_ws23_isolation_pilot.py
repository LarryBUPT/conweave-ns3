#!/usr/bin/env python3
"""Verify the frozen WS-23 18-cell synthetic, paired isolation pilot."""

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/research/evidence/ws23-isolation-demand-manifest.json"
MODES = ("fecmp", "shortq2", "guardhash")
TOPO_SHA = "dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def experiment_id(seed, scenario, mode):
    return "20261001-18%04d-ws23-s%d-%s-%s" % (
        (seed - 2301) * 6 + (0 if scenario == "bg" else 3) + MODES.index(mode),
        seed, scenario, mode)


def parse_counter(log, name):
    matches = [line for line in log.splitlines() if line.startswith(name + " ")]
    require(len(matches) == 1, name + " receipt count")
    return {k: int(v) for k, v in re.findall(r"([a-z_]+)=(\d+)", matches[0])}


def inspect(entry, mode, source_sha):
    exp = experiment_id(entry["seed"], entry["scenario"], mode)
    folder = ROOT / "results" / exp
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    require(meta["experiment_id"] == exp and meta["status"] == "SUCCEEDED", exp + " identity/status")
    require(meta["git_commit"] == source_sha and meta["algorithm"] == mode and
            meta["seed"] == 1 and meta["build_mode"] == "optimized" and
            meta["cpu_jobs"] == 2 and meta["concurrency_cap"] == 1, exp + " build/seed")
    require(meta["input_flow_sha256"] == entry["sha256"] and
            meta["topology_sha256"] == TOPO_SHA and
            digest(folder / "config/traffic_trace.txt") == entry["sha256"] and
            digest(folder / "config/topology.txt") == TOPO_SHA, exp + " input hashes")
    require(meta["input_flows"] == entry["flow_count"] and
            meta["completed_flows"] == entry["flow_count"] and
            meta["unfinished_flows"] == 0, exp + " completion")
    p = meta["parameters"]
    expected = {"lb": mode, "pfc": 0, "irn": 1, "buffer": 9, "bw": 100,
                "simul_time": "0.01", "netload": 10, "topo": "fat_k4_100G_OS2",
                "cdf": "AliStorage2019", "factorial_pilot": True,
                "factorial_drop_diag": True, "ws13_diag": 0,
                "flow_file": Path(entry["path"]).name}
    require(all(p.get(k) == v for k, v in expected.items()), exp + " parameters")
    raw_id = str(meta["raw_directory"])
    raw = folder / "raw" / raw_id
    fct_file = raw / (raw_id + "_out_fct.txt")
    fct = [tuple(map(int, line.split())) for line in fct_file.read_text().splitlines()]
    require(len(fct) == entry["flow_count"] and all(len(row) == 8 for row in fct), exp + " FCT rows")
    flows = entry["flows"]
    by_identity = {(row[0], row[1], row[4]): row for row in fct}
    require(len(by_identity) == len(flows) and all(
        (flow["source"], flow["destination"], flow["bytes"]) in by_identity
        for flow in flows), exp + " flow identities")
    require(sum(row[4] for row in fct) == entry["payload_bytes"] and
            all(row[6] > 0 for row in fct), exp + " bytes/FCT")
    require((raw / (raw_id + "_out_pfc.txt")).stat().st_size == 0, exp + " PFC")
    log = (raw / "config.log").read_text(encoding="utf-8", errors="replace")
    forbidden = ("FACTORIAL_ADMISSION_DROP ", "FACTORIAL_QUEUE_REJECT ",
                 "WARNING - Drop occurs in SendToDevContinue()", "WS08_TX_TIMEOUT ")
    require(not any(line.startswith(forbidden) for line in log.splitlines()), exp + " loss/timeout")
    route = check = None
    if mode != "fecmp":
        route = parse_counter(log, "WS09_ROUTE")
        check = parse_counter(log, "WS09_QUEUE_CHECK")
        require(check == {"violations": 0}, exp + " queue conservation")
    receipt = json.loads((folder / "logs/resource-fast-summary.json").read_text())
    require(receipt["final_status"] == "SUCCEEDED" and receipt["running_seen"] and
            receipt["root_pid"] == meta["pid"] and receipt["samples"] > 0 and
            0 < receipt["peak_tree_rss_mib"] < 8192 and
            receipt["minimum_mem_available_gib"] >= 16 and
            receipt["minimum_free_gib"] >= 100, exp + " resource receipt")
    return {"id": exp, "fct_sha256": digest(fct_file),
            "background_fct_ns": by_identity[(flows[0]["source"], flows[0]["destination"],
                                               flows[0]["bytes"])][6],
            "contender_fct_ns": sorted(row[6] for row in fct if row[0] != flows[0]["source"]),
            "route": route, "resource_peak_rss_mib": receipt["peak_tree_rss_mib"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    require(re.fullmatch(r"[0-9a-f]{40}", args.source_sha), "full source SHA required")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = {(e["seed"], e["scenario"]): e for e in manifest["entries"]}
    require(set(entries) == {(s, c) for s in (2301, 2302, 2303) for c in ("bg", "mix")},
            "demand manifest coverage")
    rows = {}
    for seed in (2301, 2302, 2303):
        for scenario in ("bg", "mix"):
            entry = entries[seed, scenario]
            require(digest(ROOT / entry["path"]) == entry["sha256"], "Git demand byte hash")
            for mode in MODES:
                rows[seed, scenario, mode] = inspect(entry, mode, args.source_sha)
        require(len({rows[seed, "bg", mode]["fct_sha256"] for mode in MODES}) == 1,
                "Background-only mode equivalence seed %d" % seed)
    outcomes = []
    for seed in (2301, 2302, 2303):
        row = {mode: rows[seed, "mix", mode] for mode in MODES}
        interference = {mode: row[mode]["background_fct_ns"] -
                        rows[seed, "bg", mode]["background_fct_ns"] for mode in MODES}
        dynamic = row["guardhash"]["route"]
        mechanism = (dynamic["two_candidates"] > 0 and dynamic["scored"] > 0 and
                     dynamic["class_nonzero"] > 0 and dynamic["class_changed_choice"] > 0)
        background_better = all(interference["guardhash"] < interference[m]
                                for m in ("fecmp", "shortq2"))
        contender_safe = all(max(row["guardhash"]["contender_fct_ns"]) <=
                             max(row[m]["contender_fct_ns"])
                             for m in ("fecmp", "shortq2"))
        outcomes.append({"seed": seed, "interference_ns": interference,
                         "contender_max_fct_ns": {m: max(row[m]["contender_fct_ns"])
                                                  for m in MODES},
                         "class_mechanism_triggered": mechanism,
                         "background_better_than_both": background_better,
                         "contender_max_no_worse_than_both": contender_safe})
    print(json.dumps({"source_sha": args.source_sha, "cells": len(rows),
                      "outcomes": outcomes,
                      "exploratory_positive": all(o["class_mechanism_triggered"] and
                                                  o["background_better_than_both"] and
                                                  o["contender_max_no_worse_than_both"]
                                                  for o in outcomes)}, indent=2))


if __name__ == "__main__":
    main()
