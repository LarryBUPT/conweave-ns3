#!/usr/bin/env python3
"""Verify one frozen independent WS-25 v2 screening cell from raw evidence."""
import argparse
import hashlib
import json
import re
from pathlib import Path

import analyze_moe_tags

ROOT = Path(__file__).resolve().parents[1]
PLAN = json.loads((ROOT / "docs/research/evidence/ws25-v2-screen-plan.json")
                  .read_text(encoding="utf-8"))
SHA = PLAN["source_sha"]
TOPO = PLAN["topology_sha256"]


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def fields(line):
    return {key: int(value) for key, value in re.findall(r"(\w+)=(-?\d+)", line)}


def unique_raw(raw, suffix):
    paths = list(raw.glob("*" + suffix))
    if len(paths) != 1 or paths[0].is_symlink():
        raise RuntimeError("Raw file missing or ambiguous: " + suffix)
    return paths[0]


def verify(cell):
    folder = ROOT / "results" / cell["id"]
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = meta["parameters"]
    if not (meta["status"] == "SUCCEEDED" and meta["git_commit"] == SHA and
            meta["algorithm"] == cell["mode"] and meta["seed"] == 1 and
            meta["input_flow_sha256"] == cell["trace_sha256"] and
            meta["topology_sha256"] == TOPO and
            params["flow_file"] == cell["trace"] and params["lb"] == cell["mode"] and
            params["topo"] == "topo_1280_400G_400G_OS1" and
            params["bw"] == 400 and params["buffer"] == 9 and
            params["pfc"] == 0 and params["irn"] == 1 and
            params["simul_time"] == "0.01" and params["netload"] == 10 and
            params["ws25_diag"] == cell["ws25_diag"] and
            meta["concurrency_cap"] in (1, 4)):
        raise RuntimeError("Screen metadata identity mismatch: " + cell["id"])
    if digest(folder / "config" / "traffic_trace.txt") != cell["trace_sha256"] or digest(
            folder / "config" / "topology.txt") != TOPO:
        raise RuntimeError("Screen input snapshot mismatch: " + cell["id"])
    summary = analyze_moe_tags.summarize(cell["id"])
    tags = summary["tags"]
    if {tag: row["input_flows"] for tag, row in tags.items() if row["input_flows"]} != {
            "1": 192, "2": 16384} or any(
            row["input_flows"] != row["completed_flows"] for row in tags.values()):
        raise RuntimeError("Screen flow identity/completion mismatch: " + cell["id"])
    raw = folder / "raw" / str(meta["raw_directory"])
    for suffix in ("_out_fct.txt", "_out_cnp.txt", "_out_pfc.txt", "_out_uplink.txt"):
        unique_raw(raw, suffix)
    fct_sha = digest(unique_raw(raw, "_out_fct.txt"))
    if fct_sha != summary["fct_sha256"]:
        raise RuntimeError("Screen FCT fingerprint mismatch: " + cell["id"])
    log = (folder / "logs" / "config.log").read_text(encoding="utf-8", errors="replace")
    route = None
    if cell["mode"] == "destspread":
        matches = [fields(line) for line in log.splitlines()
                   if line.startswith("WS25_DESTSPREAD ")]
        queues = [fields(line) for line in log.splitlines()
                  if line.startswith("WS25_QUEUE ")]
        if len(matches) != 1 or len(queues) != 1:
            raise RuntimeError("Screen candidate counters missing: " + cell["id"])
        route, queue = matches[0], queues[0]
        if (route.get("queue_violations") != 0 or
                queue.get("enqueued") != queue.get("dequeued", 0) +
                queue.get("queued_drop", 0) + queue.get("current", 0) or
                not all(route.get(name, 0) > 0 for name in
                        ("moe_packets", "background_packets", "background_new",
                         "background_reused"))):
            raise RuntimeError("Screen candidate path/conservation failed: " + cell["id"])
    qp_by_tag = None
    if cell["ws25_diag"]:
        rows = [fields(line) for line in log.splitlines() if line.startswith("WS25_QP ")]
        if len(rows) != 16576 or len({row["flow_id"] for row in rows}) != 16576 or {
                tag: sum(row["tag"] == tag for row in rows) for tag in (1, 2)} != {
                1: 192, 2: 16384}:
            raise RuntimeError("Screen per-QP rows missing or duplicated: " + cell["id"])
        counters = ("rx_ooo_packets", "sack_feedback", "cnp_feedback",
                    "repeated_sends", "timeout_recovery")
        if any(name not in row or row[name] < 0 for row in rows for name in counters):
            raise RuntimeError("Screen per-QP field missing: " + cell["id"])
        qp_by_tag = {str(tag): {name: sum(row[name] for row in rows if row["tag"] == tag)
                                for name in counters} for tag in (1, 2)}
        off = next(other for other in PLAN["cells"] if other["seed"] == cell["seed"] and
                   other["mode"] == "destspread" and other["ws25_diag"] == 0)
        off_meta = json.loads((ROOT / "results" / off["id"] / "metadata.json")
                              .read_text(encoding="utf-8"))
        off_raw = ROOT / "results" / off["id"] / "raw" / str(off_meta["raw_directory"])
        if digest(unique_raw(off_raw, "_out_fct.txt")) != fct_sha:
            raise RuntimeError("Screen diagnostic changed FCT: " + cell["id"])
        if not any(line.startswith("WS13_HOP ") for line in log.splitlines()):
            raise RuntimeError("Screen background hop observations missing: " + cell["id"])
        inflight = [fields(line) for line in log.splitlines()
                    if line.startswith("WS13_INFLIGHT ")]
        if len(inflight) != 1 or inflight[0].get("unpaired") != 0:
            raise RuntimeError("Screen background hop observations unpaired: " + cell["id"])
    resource = json.loads((folder / "logs" / "resource-summary.json")
                          .read_text(encoding="utf-8"))
    samples = [json.loads(line) for line in (folder / "logs" / "resource-samples.jsonl")
               .read_text(encoding="utf-8").splitlines() if line]
    if not (resource["final_status"] == "SUCCEEDED" and
            resource["samples"] == len(samples) > 0 and
            resource["peak_tree_rss_mib"] <= 32768 and
            resource["minimum_mem_available_gib"] >= 32 and
            resource["minimum_free_gib"] >= 100 and
            max(row["load_1m"] for row in samples) <= 20):
        raise RuntimeError("Screen resource gate failed: " + cell["id"])
    return {"id": cell["id"], "seed": cell["seed"], "mode": cell["mode"],
            "ws25_diag": cell["ws25_diag"], "fct_sha256": fct_sha,
            "moe_batch_us": tags["2"]["synthetic_batch_completion_us"],
            "background_p99_us": tags["1"]["p99_fct_us"],
            "route": route, "qp_by_tag": qp_by_tag, "resource": resource}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    args = parser.parse_args()
    rows = [row for row in PLAN["cells"] if row["id"] == args.id]
    if len(rows) != 1:
        raise RuntimeError("ID outside frozen screen plan")
    result = verify(rows[0])
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
