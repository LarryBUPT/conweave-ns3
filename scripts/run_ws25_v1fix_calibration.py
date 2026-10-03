#!/usr/bin/env python3
"""Run the frozen four-seed ClassReserve v1-fix calibration and diagnostic controls."""
import concurrent.futures
import datetime
import hashlib
import json
import re
import shlex
import subprocess
import threading
import time
from pathlib import Path

import analyze_moe_tags
import run_ws25_preflight as base

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "a656104d05c681f9b3a998b5ef4ce3e644558d02"
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
SEEDS = {
    20262505: "038d7cf09f21a56ae8e1d13164cc57e816bd14cf62631d7ff9efa59b8c1d9272",
    20262506: "fe94e381938538ab7c2376614f6d8c27600b2e351c2d5e10a2b62fd14d2a8ed5",
    20262507: "01b24bc1bd76d4932dd6c6e4e7ce159ff9d73824de2540ba4b09cd62e6ff83b7",
    20262508: "e68616fd2de70e466f6193d7584ae77a1eb1a437efbf90c8619930dd814ded4a",
}
SEED_ORDER = (20262507, 20262508, 20262505, 20262506)
MODE_ORDER = {
    20262507: ("fecmp", "conweave", "letflow", "drill", "conga", "classreserve", "classreserve_diag"),
    20262508: ("conga", "conweave", "letflow", "fecmp", "classreserve", "drill", "classreserve_diag"),
    20262505: ("letflow", "conweave", "classreserve", "classreserve_diag", "conga", "drill", "fecmp"),
    20262506: ("conga", "fecmp", "letflow", "drill", "classreserve", "conweave", "classreserve_diag"),
}
ID_PREFIX = {
    20262505: "20261003-102000",
    20262506: "20261003-103000",
    20262507: "20261003-100000",
    20262508: "20261003-101000",
}
DIAG_ID = {20262507: "20261003-110000-ws25-v1fix-cal07-classreserve-diag"}
MODES = ("fecmp", "drill", "conga", "letflow", "conweave", "classreserve")
EXPECTED_TAGS = {"1": 192, "2": 16384}
PLAN_PATH = ROOT / "results" / "ws25-v1fix-calibration-plan-r4.json"
RECEIPTS = ROOT / "results" / "ws25-v1fix-calibration-receipts-r4.jsonl"
LOCK = threading.Lock()


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cells():
    output = []
    for seed in SEED_ORDER:
        trace = "ws25_seed%d_b192.txt" % seed
        trace_path = ROOT / "config" / trace
        if sha(trace_path) != SEEDS[seed]:
            raise RuntimeError("Frozen calibration input changed: " + trace)
        for index, item in enumerate(MODE_ORDER[seed]):
            diagnostic = item == "classreserve_diag"
            mode = "classreserve" if diagnostic else item
            suffix = "classreserve-diag" if diagnostic else mode
            experiment_id = (DIAG_ID.get(seed) if diagnostic else None) or (
                "%s-ws25-v1fix-cal%02d-%s" %
                (ID_PREFIX[seed], seed - 20262500, suffix))
            output.append({
                "id": experiment_id,
                "seed": seed, "mode": mode, "trace": trace,
                "trace_sha256": SEEDS[seed], "diag": int(diagnostic),
                "role": "diagnostic_control" if diagnostic else "primary",
                "block_order": index,
            })
    return output


def write_plan(selected):
    data = {
        "kind": "independent corrected-candidate calibration; not efficacy",
        "source_sha": SOURCE_SHA, "topology_sha256": TOPO_SHA,
        "seed_order": list(SEED_ORDER), "ns3_seed": 1,
        "pfc": 0, "irn": 1, "bw_gbps": 400, "buffer_mib": 9,
        "netload": 10, "simul_time": "0.01", "max_concurrent": 2,
        "calibration_seed_unit": "independent demand seed; six modes paired within seed",
        "cells": selected,
    }
    encoded = json.dumps(data, sort_keys=True, indent=2) + "\n"
    if PLAN_PATH.exists():
        if PLAN_PATH.read_text(encoding="utf-8") != encoded:
            raise RuntimeError("Frozen v1-fix calibration plan differs")
    else:
        PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
        PLAN_PATH.write_text(encoded, encoding="utf-8")
    return data


def receipt(event, cell, **details):
    item = {"event": event, "id": cell["id"], "seed": cell["seed"],
            "mode": cell["mode"], "role": cell["role"],
            "utc": datetime.datetime.utcnow().isoformat() + "Z"}
    item.update(details)
    with LOCK:
        RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
        with RECEIPTS.open("a", encoding="utf-8") as target:
            target.write(json.dumps(item, sort_keys=True) + "\n")
            target.flush()


def verify(cell):
    folder = ROOT / "results" / cell["id"]
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = meta["parameters"]
    if not (meta["status"] == "SUCCEEDED" and meta["git_commit"] == SOURCE_SHA and
            meta["algorithm"] == cell["mode"] and meta["seed"] == 1 and
            meta["input_flow_sha256"] == cell["trace_sha256"] and
            meta["topology_sha256"] == TOPO_SHA and
            params["flow_file"] == cell["trace"] and params["lb"] == cell["mode"] and
            params["topo"] == "topo_1280_400G_400G_OS1" and params["bw"] == 400 and
            params["buffer"] == 9 and params["simul_time"] == "0.01" and
            params["netload"] == 10 and params["pfc"] == 0 and params["irn"] == 1 and
            params["ws25_diag"] == cell["diag"]):
        raise RuntimeError("Calibration metadata mismatch: " + cell["id"])
    if sha(folder / "config" / "traffic_trace.txt") != cell["trace_sha256"]:
        raise RuntimeError("Calibration input snapshot mismatch: " + cell["id"])
    if sha(folder / "config" / "topology.txt") != TOPO_SHA:
        raise RuntimeError("Calibration topology snapshot mismatch: " + cell["id"])
    summary = analyze_moe_tags.summarize(cell["id"])
    tags = summary["tags"]
    if {tag: item["input_flows"] for tag, item in tags.items()} != EXPECTED_TAGS:
        raise RuntimeError("Calibration tag counts mismatch: " + cell["id"])
    if any(item["completed_flows"] != item["input_flows"] for item in tags.values()):
        raise RuntimeError("Calibration unfinished flows: " + cell["id"])
    log = (folder / "logs" / "config.log").read_text(encoding="utf-8", errors="replace")
    raw = folder / "raw" / str(meta["raw_directory"])
    for suffix in ("_out_fct.txt", "_out_cnp.txt", "_out_pfc.txt", "_out_uplink.txt"):
        files = list(raw.glob("*" + suffix))
        if len(files) != 1 or files[0].is_symlink():
            raise RuntimeError("Calibration raw missing/ambiguous " + suffix)
    result = {"id": cell["id"], "seed": cell["seed"], "mode": cell["mode"],
              "role": cell["role"], "trace_sha256": cell["trace_sha256"],
              "fct_sha256": summary["fct_sha256"], "tags": tags,
              "moe_batch_us": tags["2"]["synthetic_batch_completion_us"],
              "background_p99_us": tags["1"]["p99_fct_us"]}
    if cell["mode"] == "classreserve":
        line = next((row for row in log.splitlines()
                     if row.startswith("WS25_CLASSRESERVE ")), None)
        queue = next((row for row in log.splitlines() if row.startswith("WS25_QUEUE ")), None)
        if not line or not queue:
            raise RuntimeError("ClassReserve counters absent: " + cell["id"])
        counters = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", line)}
        queued = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", queue)}
        if counters.get("queue_violations") != 0 or not (
                counters.get("moe_flow_new", 0) > 0 and
                counters.get("moe_flow_reused", 0) > 0 and
                counters.get("background_new_flows", 0) > 0 and
                counters.get("background_reused", 0) > 0):
            raise RuntimeError("ClassReserve selection/cache invariant failed: " + cell["id"])
        if not (queued.get("enqueued") == queued.get("dequeued") and
                queued.get("queued_drop") == 0 and queued.get("current") == 0):
            raise RuntimeError("ClassReserve queue conservation failed: " + cell["id"])
        result["classreserve"] = counters
        result["queue"] = queued
        if cell["diag"]:
            qp_rows = [row for row in log.splitlines() if row.startswith("WS25_QP ")]
            choices = [row for row in log.splitlines() if row.startswith("WS25_CHOICE ")]
            qp_tags = {}
            for row in qp_rows:
                fields = dict(item.split("=", 1) for item in row.split()[1:])
                qp_tags[fields["tag"]] = qp_tags.get(fields["tag"], 0) + 1
            if qp_tags != {"1": 192, "2": 16384} or not choices:
                raise RuntimeError("Diagnostic coverage incomplete: " + cell["id"])
            result["diagnostic_qp_rows"] = len(qp_rows)
            result["diagnostic_choice_rows"] = len(choices)
    resources = json.loads((folder / "logs" / "resource-summary.json").read_text(encoding="utf-8"))
    samples = [json.loads(row) for row in
               (folder / "logs" / "resource-samples.jsonl").read_text(encoding="utf-8").splitlines()
               if row]
    if not (resources["final_status"] == "SUCCEEDED" and resources["samples"] == len(samples) > 0 and
            resources["peak_tree_rss_mib"] <= 32768 and
            resources["minimum_mem_available_gib"] >= 32 and
            resources["minimum_free_gib"] >= 100 and
            max(row["load_1m"] for row in samples) <= 20):
        raise RuntimeError("Calibration resource gate failed: " + cell["id"])
    result["resource"] = resources
    return result


def verify_remote_trace(cell):
    cfg = base.remote.config()
    path = "/home/fnl/lzy/runs/%s/source/config/%s" % (cell["id"], cell["trace"])
    code = ("import hashlib,os; p=%r; assert os.path.isfile(p) and not os.path.islink(p); "
            "assert os.path.realpath(p)==p; print(hashlib.sha256(open(p,'rb').read()).hexdigest())") % path
    output = subprocess.check_output(base.remote.ssh_base(cfg) +
                                     ["python3 -c " + shlex.quote(code)],
                                     universal_newlines=True).strip()
    if output != cell["trace_sha256"]:
        raise RuntimeError("Remote trace missing or hash mismatch: " + cell["id"])


def run_cell(cell):
    local = ROOT / "results" / cell["id"]
    if local.is_dir():
        result = verify(cell)
        receipt("verified_existing", cell, **result)
        return result
    try:
        state = base.status(cell["id"])
    except RuntimeError as error:
        if "metadata.json" not in str(error) and "No such file" not in str(error):
            raise
        output = base.command("build", "--repo-local", str(ROOT), "--id", cell["id"],
                              "--source-sha", SOURCE_SHA, "--label", "ws25-v1fix-calibration")
        state = base.status(cell["id"])
        receipt("built", cell, status=state["status"], build_output=output.strip()[-300:])
    if state.get("git_commit") != SOURCE_SHA:
        raise RuntimeError("Calibration source SHA mismatch: " + cell["id"])
    if state["status"] == "BUILT":
        verify_remote_trace(cell)
        base.start_watch(cell["id"])
        args = ["run", cell["id"], "--lb", cell["mode"], "--pfc", "0", "--irn", "1",
                "--bw", "400", "--buffer", "9", "--topo", "topo_1280_400G_400G_OS1",
                "--flow-file", cell["trace"], "--simul-time", "0.01", "--netload", "10",
                "--max-concurrent", "2"]
        if cell["diag"]:
            args.extend(["--ws25-diag", "1"])
        base.command(*args)
        receipt("started", cell, cap=2)
        state = base.status(cell["id"])
    elif state["status"] not in ("RUNNING", "SUCCEEDED"):
        raise RuntimeError("Unexpected calibration state %s: %s" % (state["status"], cell["id"]))
    while state["status"] == "RUNNING":
        time.sleep(1800)
        state = base.status(cell["id"])
    if state["status"] != "SUCCEEDED":
        raise RuntimeError("Calibration simulation failed; preserve ID: " + cell["id"])
    base.wait_watch(cell["id"])
    base.command("fetch", cell["id"])
    meta = json.loads((local / "metadata.json").read_text(encoding="utf-8"))
    base.fetch_config_log(cell, meta)
    result = verify(cell)
    receipt("verified", cell, cap=2, **result)
    return result


def verify_matrix(selected):
    rows = [verify(cell) for cell in selected]
    if len(rows) != 28:
        raise RuntimeError("Expected 28 calibration and diagnostic cells")
    by_key = {(row["seed"], row["mode"], row["role"]): row for row in rows}
    fingerprints = {}
    for seed in SEED_ORDER:
        primary = by_key[(seed, "classreserve", "primary")]
        diagnostic = by_key[(seed, "classreserve", "diagnostic_control")]
        fingerprints[str(seed)] = primary["fct_sha256"] == diagnostic["fct_sha256"]
    return {"verified_cells": len(rows), "independent_demand_seeds": len(SEED_ORDER),
            "diagnostic_fct_matches_primary_by_seed": fingerprints,
            "diagnostics_nonperturbing_for_all_seeds": all(fingerprints.values()),
            "cells": rows}


def execute(selected):
    by_seed = {seed: [cell for cell in selected if cell["seed"] == seed]
               for seed in SEED_ORDER}
    for seed in SEED_ORDER:
        block = by_seed[seed]
        for start in range(0, len(block), 2):
            group = block[start:start + 2]
            base.audit(reject_active=True)
            errors = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(group)) as pool:
                futures = {pool.submit(run_cell, cell): cell for cell in group}
                for future, cell in futures.items():
                    try:
                        result = future.result()
                        print(json.dumps({"verified": cell["id"], "seed": seed,
                                          "peak_rss_mib": result["resource"]["peak_tree_rss_mib"]},
                                         sort_keys=True), flush=True)
                    except Exception as error:
                        errors.append((cell["id"], str(error)))
            if errors:
                raise RuntimeError("Stop before new calibration cells; preserve IDs: " + repr(errors))
            base.audit(reject_active=True)
    result = verify_matrix(selected)
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    with (RECEIPTS.parent / "ws25-v1fix-calibration-verification-r4.json").open("x", encoding="utf-8") as target:
        json.dump(result, target, indent=2, sort_keys=True)
        target.write("\n")
    print(json.dumps({"calibration_matrix_complete": True,
                      "verified_cells": result["verified_cells"],
                      "diagnostics_nonperturbing_for_all_seeds":
                          result["diagnostics_nonperturbing_for_all_seeds"]}, sort_keys=True), flush=True)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("plan", "run", "verify"))
    args = parser.parse_args()
    selected = cells()
    write_plan(selected)
    if args.phase == "plan":
        print(json.dumps({"source_sha": SOURCE_SHA, "cells": len(selected),
                          "seeds": list(SEED_ORDER)}, sort_keys=True))
    elif args.phase == "verify":
        print(json.dumps(verify_matrix(selected), sort_keys=True))
    else:
        base.audit(reject_active=True)
        execute(selected)


if __name__ == "__main__":
    main()
