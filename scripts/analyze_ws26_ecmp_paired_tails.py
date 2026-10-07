#!/usr/bin/env python3
"""Pair the non-perturbing ECMP and ClassReserve WS-25 tail diagnostics.

This is a posthoc mechanism comparison on two disclosed demands, not a new
efficacy sample. Run only after the separate per-cell raw/resource verifiers.
"""

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path


PAIRS = (
    ("20261007-170000-ws26-ecmpdiag-s43-b064",
     "20261006-180002-ws25-v1diag-s43-b064-classreserve-r1",
     64, "2447c24415711a30e025a04df23319ad36871061ea40d312775a92617e793cb8"),
    ("20261007-170001-ws26-ecmpdiag-s24-b192",
     "20261006-180001-ws25-v1diag-s24-b192-classreserve",
     192, "48453a24b8c32fdd0d44bea7bfefbf40fcfb4cf96ac05a1c5e9cba544e70b834"),
)
SOURCE_SHA = "ce699dffe2845dc83e2171a1c309c6d96b96d2b3"
TOPO_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fields(line):
    return {key: int(value) for key, value in re.findall(r"(\w+)=(-?\d+)", line)}


def load_cell(root, experiment_id, mode, background, expected_fct=None):
    folder = root / "results" / experiment_id
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    params = meta["parameters"]
    if not (meta["status"] == "SUCCEEDED" and meta["git_commit"] == SOURCE_SHA
            and meta["algorithm"] == mode and meta["topology_sha256"] == TOPO_SHA
            and params["lb"] == mode and params["ws25_diag"] == 1
            and params["pfc"] == 0 and params["irn"] == 1):
        raise RuntimeError("Diagnostic identity mismatch: " + experiment_id)
    if sha(folder / "config" / "topology.txt") != TOPO_SHA:
        raise RuntimeError("Topology snapshot changed: " + experiment_id)
    if sha(folder / "config" / "traffic_trace.txt") != meta["input_flow_sha256"]:
        raise RuntimeError("Trace snapshot changed: " + experiment_id)
    raw = folder / "raw" / str(meta["raw_directory"])
    files = list(raw.glob("*_out_fct.txt"))
    if len(files) != 1:
        raise RuntimeError("Ambiguous FCT raw: " + experiment_id)
    fct_path = files[0]
    fct_sha = sha(fct_path)
    if expected_fct and fct_sha != expected_fct:
        raise RuntimeError("Diagnostic perturbed formal FCT: " + experiment_id)
    fct = {}
    completed = set()
    rows = 0
    with fct_path.open(encoding="ascii") as source:
        for line in source:
            values = list(map(int, line.split()))
            if len(values) != 8:
                raise RuntimeError("Malformed FCT row: " + experiment_id)
            rows += 1
            identity = tuple(values[:5])
            if identity in completed:
                raise RuntimeError("Duplicate completed QP: " + experiment_id)
            completed.add(identity)
            if values[4] == 8388608:
                key = tuple(values[:4])
                if key in fct:
                    raise RuntimeError("Duplicate background QP: " + experiment_id)
                fct[key] = values[6]
    if rows != 16384 + background or len(fct) != background:
        raise RuntimeError("Incomplete FCT: " + experiment_id)
    log_path = raw / "config.log"
    log = log_path.read_text(encoding="utf-8", errors="replace")
    qps, hops = {}, {}
    inflight = None
    for line in log.splitlines():
        if line.startswith("WS25_QP "):
            row = fields(line)
            flow_id = row["flow_id"]
            if flow_id in qps:
                raise RuntimeError("Duplicate QP diagnostic: " + experiment_id)
            qps[flow_id] = row
        elif line.startswith("WS13_HOP "):
            row = fields(line)
            key = tuple(row[item] for item in ("src", "dst", "sport", "dport"))
            hops.setdefault(key, []).append(row)
        elif line.startswith("WS13_INFLIGHT "):
            inflight = fields(line)["unpaired"]
    if (set(qps) != set(range(rows)) or
            sum(row["tag"] == 1 for row in qps.values()) != background or
            inflight != 0):
        raise RuntimeError("Incomplete diagnostic rows: " + experiment_id)
    trace = (folder / "config" / "traffic_trace.txt").read_text(encoding="ascii").splitlines()
    source_ports = collections.defaultdict(lambda: 10000)
    destination_ports = collections.defaultdict(lambda: 100)
    intended = set()
    for line in trace[1:]:
        tokens = line.split()
        src, dst, size = int(tokens[0]), int(tokens[1]), int(tokens[3])
        identity = (src, dst, source_ports[src], destination_ports[dst], size)
        if identity in intended:
            raise RuntimeError("Duplicate input QP: " + experiment_id)
        intended.add(identity)
        source_ports[src] += 1
        destination_ports[dst] += 1
    if completed != intended:
        raise RuntimeError("Unmatched or incomplete input QPs: " + experiment_id)
    trace_ids = {}
    for index, line in enumerate(trace[1:background + 1]):
        src, dst = map(int, line.split()[:2])
        trace_ids[src, dst] = index
    if len(trace_ids) != background or len(trace) != rows + 1:
        raise RuntimeError("Unexpected trace identity: " + experiment_id)
    resource_path = folder / "logs" / "resource-summary.json"
    sample_path = folder / "logs" / "resource-samples.jsonl"
    resource = json.loads(resource_path.read_text(encoding="utf-8"))
    samples = [json.loads(line) for line in sample_path.read_text(encoding="utf-8").splitlines()
               if line]
    if not (resource["final_status"] == "SUCCEEDED" and
            resource["samples"] == len(samples) > 0 and
            resource["peak_tree_rss_mib"] <= 32768 and
            resource["minimum_mem_available_gib"] >= 32 and
            resource["minimum_free_gib"] >= 100 and
            max(sample["load_1m"] for sample in samples) <= 20):
        raise RuntimeError("Resource receipt gate failed: " + experiment_id)
    for key in fct:
        if key[:2] not in trace_ids or key not in hops:
            raise RuntimeError("Missing background trace/hops: " + experiment_id)
    return {"id": experiment_id, "mode": mode, "fct_sha256": fct_sha,
            "trace_sha256": meta["input_flow_sha256"], "fct": fct, "qps": qps,
            "hops": hops, "trace_ids": trace_ids, "resource": resource}


def hop_view(rows, destination_tor):
    def view(selected):
        packets = sum(row["packets"] for row in selected)
        return {"hop_rows": len(selected),
                "ports": [[row["switch"], row["port"]] for row in selected],
                "max_wait_ns": max((row["wait_ns_max"] for row in selected), default=0),
                "max_queued_bytes": max((row["queued_bytes_max"] for row in selected), default=0),
                "mean_wait_ns_per_hop_packet":
                    sum(row["wait_ns_sum"] for row in selected) / packets if packets else None}
    return {"destination": view([r for r in rows if r["switch"] == destination_tor]),
            "upstream": view([r for r in rows if r["switch"] != destination_tor])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parent = Path(__file__).resolve().parents[2]
    parser.add_argument("--ws26-root", type=Path, default=parent / "ws26-classmix-validation")
    parser.add_argument("--ws25-root", type=Path, default=parent / "ws25-first-paper")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ecmp-id", help="analyze one accepted ECMP replay")
    args = parser.parse_args()
    output = {"role": "disclosed-demand paired mechanism diagnostic, not efficacy",
              "source_sha": SOURCE_SHA, "pairs": []}
    for ecmp_id, candidate_id, background, expected_fct in PAIRS:
        if args.ecmp_id and ecmp_id != args.ecmp_id:
            continue
        ecmp = load_cell(args.ws26_root, ecmp_id, "fecmp", background, expected_fct)
        candidate = load_cell(args.ws25_root, candidate_id, "classreserve", background)
        if ecmp["trace_sha256"] != candidate["trace_sha256"] or ecmp["fct"].keys() != candidate["fct"].keys():
            raise RuntimeError("Paired identities differ: " + ecmp_id)
        old_summary = json.loads((args.ws25_root / "docs/research/evidence/ws25-v1-formal-tail-diagnostic-analysis.json").read_text(encoding="utf-8"))
        old_cell = next(c for c in old_summary["cells"] if c["id"] == candidate_id)
        if old_cell["fct_sha256"] != candidate["fct_sha256"] or not old_cell["matches_formal_fct"]:
            raise RuntimeError("ClassReserve diagnostic is not non-perturbing")
        tors = {tuple((r["src"], r["dst"])): r["destination_tor"]
                for r in old_cell["background_flows"]}
        details = []
        for key in ecmp["fct"]:
            flow_id = ecmp["trace_ids"][key[:2]]
            if candidate["trace_ids"][key[:2]] != flow_id:
                raise RuntimeError("Paired flow IDs differ")
            tor = tors[key[:2]]
            details.append({"src": key[0], "dst": key[1], "sport": key[2],
                            "dport": key[3], "flow_id": flow_id,
                            "ecmp_fct_us": ecmp["fct"][key] / 1000,
                            "classreserve_fct_us": candidate["fct"][key] / 1000,
                            "change_us": (candidate["fct"][key] - ecmp["fct"][key]) / 1000,
                            "ecmp_qp": ecmp["qps"][flow_id],
                            "classreserve_qp": candidate["qps"][flow_id],
                            "ecmp_hops": hop_view(ecmp["hops"][key], tor),
                            "classreserve_hops": hop_view(candidate["hops"][key], tor)})
        details.sort(key=lambda row: row["change_us"], reverse=True)
        output["pairs"].append({"ecmp_id": ecmp_id, "classreserve_id": candidate_id,
                                "background": background,
                                "trace_sha256": ecmp["trace_sha256"],
                                "ecmp_fct_sha256": ecmp["fct_sha256"],
                                "classreserve_fct_sha256": candidate["fct_sha256"],
                                "ecmp_resource": ecmp["resource"],
                                "classreserve_resource": candidate["resource"],
                                "flows_by_descending_regression": details})
    if not output["pairs"]:
        raise RuntimeError("No accepted diagnostic ID selected")
    target = args.output or (args.ws26_root / "docs/research/evidence/ws26-ecmp-paired-tail-diagnostic.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"pairs": len(output["pairs"]), "output": str(target)}, sort_keys=True))


if __name__ == "__main__":
    main()
