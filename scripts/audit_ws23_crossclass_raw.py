#!/usr/bin/env python3
"""Independently audit the four frozen WS-23 cross-class raw results.

This intentionally reads raw files directly and does not import the preflight
verifier or its FCT/tag analysis helpers.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "154f537ec345df75fbb404a1674436535f92735b"
TOPOLOGY = "dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad"
TRACES = {
    "background": (
        "8b11ba4bbc5fac248b1983e4070e818cb3ad3658ebaae6d9eb878b3999b76b83",
        [(0, 24, 3, 8388608, "2.006000000", 1)],
    ),
    "mixed": (
        "379e0c87cb0c26690d438287468dbc9159054f82445e6be46d0324165d639863",
        [(0, 24, 3, 8388608, "2.006000000", 1),
         (1, 25, 3, 4194304, "2.006000000", 2),
         (2, 26, 3, 4194304, "2.006000000", 2),
         (3, 27, 3, 4194304, "2.006000000", 2)],
    ),
}
CELLS = (
    ("20261001-091000-ws23-bg-off", "background", False),
    ("20261001-091100-ws23-bg-on", "background", True),
    ("20261001-091200-ws23-mix-off", "mixed", False),
    ("20261001-091300-ws23-mix-on", "mixed", True),
)
COMMON = {"lb": "fecmp", "pfc": 0, "irn": 1, "buffer": 9, "bw": 100,
          "simul_time": "0.01", "netload": 10, "topo": "fat_k4_100G_OS2",
          "cdf": "AliStorage2019", "factorial_pilot": True,
          "factorial_drop_diag": True}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_hops(lines):
    hops = []
    unpaired = []
    for line in lines:
        if line.startswith("WS23_CROSSCLASS_HOP "):
            parts = line.split()[1:]
            row = dict(part.split("=", 1) for part in parts)
            require(len(row) == 15, "Malformed hop receipt")
            hops.append({key: int(value) for key, value in row.items()})
        elif line.startswith("WS23_CROSSCLASS_INFLIGHT "):
            unpaired.append(int(line.split("unpaired=", 1)[1]))
    return hops, unpaired


def audit_cell(experiment_id, scenario, diagnostic):
    folder = ROOT / "results" / experiment_id
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    expected_hash, expected_rows = TRACES[scenario]
    require(meta["experiment_id"] == experiment_id and meta["status"] == "SUCCEEDED",
            experiment_id + ": metadata identity or status")
    require(meta["git_commit"] == SOURCE and meta["seed"] == 1 and
            meta["algorithm"] == "fecmp" and meta["build_mode"] == "optimized" and
            meta["cpu_jobs"] == 2 and meta["concurrency_cap"] == 1,
            experiment_id + ": source, seed, or execution settings")
    require(meta["input_flow_sha256"] == expected_hash and
            meta["topology_sha256"] == TOPOLOGY,
            experiment_id + ": metadata input hashes")
    require(meta["input_flows"] == len(expected_rows) and
            meta["completed_flows"] == len(expected_rows) and
            meta["unfinished_flows"] == 0,
            experiment_id + ": flow counts")
    params = meta["parameters"]
    for key, value in COMMON.items():
        require(params[key] == value, experiment_id + ": parameter " + key)
    require(params["ws13_diag"] == int(diagnostic), experiment_id + ": diagnostic setting")
    require(params["flow_file"] == ("ws23_crossclass_bg_1x8MiB.txt" if scenario == "background"
                                      else "ws23_crossclass_bg_plus_3x4MiB.txt"),
            experiment_id + ": traffic file setting")

    trace = folder / "config" / "traffic_trace.txt"
    topology = folder / "config" / "topology.txt"
    require(sha(trace) == expected_hash and sha(topology) == TOPOLOGY,
            experiment_id + ": snapshot hashes")
    lines = trace.read_text(encoding="utf-8").splitlines()
    parsed = [(int(a), int(b), int(c), int(d), e, int(f))
              for a, b, c, d, e, f in (line.split() for line in lines[1:])]
    require(int(lines[0]) == len(expected_rows) and parsed == expected_rows,
            experiment_id + ": traffic records")

    raw = folder / "raw" / str(meta["raw_directory"])
    fct_file = raw / (str(meta["raw_directory"]) + "_out_fct.txt")
    fct = [tuple(int(value) for value in line.split())
           for line in fct_file.read_text(encoding="utf-8").splitlines()]
    require(len(fct) == len(expected_rows) and all(len(row) == 8 for row in fct),
            experiment_id + ": FCT format or count")
    for flow in expected_rows:
        matching = [row for row in fct if (row[0], row[1], row[4]) ==
                    (flow[0], flow[1], flow[3])]
        require(len(matching) == 1 and matching[0][5] == 2005999999 and
                matching[0][6] > 0,
                experiment_id + ": completion identity or timing")
    require(sum(row[4] for row in fct) == sum(row[3] for row in expected_rows),
            experiment_id + ": total payload")
    pfc_file = raw / (str(meta["raw_directory"]) + "_out_pfc.txt")
    require(pfc_file.stat().st_size == 0, experiment_id + ": unexpected PFC event")

    log_path = raw / "config.log"
    log_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    forbidden = ("FACTORIAL_ADMISSION_DROP ", "FACTORIAL_QUEUE_REJECT ",
                 "WARNING - Drop occurs in SendToDevContinue()", "WS08_TX_TIMEOUT ")
    require(not any(line.startswith(forbidden) for line in log_lines),
            experiment_id + ": drop, queue reject, or timeout")
    hops, unpaired = load_hops(log_lines)
    if diagnostic:
        require(hops and unpaired == [0], experiment_id + ": diagnostic receipts")
        for hop in hops:
            require(hop["packets"] > 0 and hop["bytes"] > 0 and
                    hop["first_enqueue_ns"] < hop["last_dequeue_ns"],
                    experiment_id + ": invalid hop counters")
    else:
        require(not hops and not unpaired, experiment_id + ": unexpected diagnostic output")

    receipt = json.loads((folder / "logs" / "resource-fast-summary.json").read_text())
    samples = [json.loads(line) for line in
               (folder / "logs" / "resource-fast-samples.jsonl").read_text().splitlines()]
    running = [sample for sample in samples if sample["status"] == "RUNNING"]
    to_epoch = lambda field: datetime.fromisoformat(meta[field].replace("Z", "+00:00")).timestamp()
    require(samples[0]["status"] == "READY" and
            samples[0]["time_utc_epoch"] <= to_epoch("started_utc") and
            to_epoch("build_finished_utc") - to_epoch("created_utc") <= 20 * 60 and
            to_epoch("finished_utc") - to_epoch("started_utc") <= 10 * 60,
            experiment_id + ": observer order or duration stop line")
    require(receipt["final_status"] == "SUCCEEDED" and receipt["running_seen"] and
            receipt["root_pid"] == meta["pid"] and receipt["samples"] == len(running) and
            running and all(sample["root_pid"] == meta["pid"] and
                            sample["process_tree_rss_mib"] > 0 for sample in running),
            experiment_id + ": process resource samples")
    require(abs(receipt["peak_tree_rss_mib"] -
                max(sample["process_tree_rss_mib"] for sample in running)) < 1e-8 and
            abs(receipt["minimum_mem_available_gib"] -
                min(sample["mem_available_gib"] for sample in running)) < 1e-8 and
            abs(receipt["minimum_free_gib"] -
                min(sample["free_gib"] for sample in running)) < 1e-8,
            experiment_id + ": resource summary disagrees with samples")
    require(receipt["peak_tree_rss_mib"] < 8192 and
            receipt["minimum_mem_available_gib"] >= 16 and
            receipt["minimum_free_gib"] >= 100 and
            max(sample["load_1m"] for sample in running) <= 20,
            experiment_id + ": resource stop threshold")
    max_text_log_bytes = max((path.stat().st_size for path in folder.rglob("*.log")), default=0)
    require(max_text_log_bytes <= 50 * 1024 * 1024, experiment_id + ": log stop threshold")
    return {
        "id": experiment_id, "scenario": scenario, "diagnostic": diagnostic,
        "fct_sha256": sha(fct_file), "config_log_sha256": sha(log_path),
        "fct_rows": len(fct), "payload_bytes": sum(row[4] for row in fct),
        "fct_ns_by_source": {str(row[0]): row[6] for row in fct},
        "hops": hops, "hop_rows": len(hops), "unpaired": unpaired,
        "resource_samples": len(running), "peak_tree_rss_mib": receipt["peak_tree_rss_mib"],
        "minimum_mem_available_gib": receipt["minimum_mem_available_gib"],
        "minimum_free_gib": receipt["minimum_free_gib"],
        "maximum_sampled_load_1m": max(sample["load_1m"] for sample in running),
        "maximum_text_log_bytes": max_text_log_bytes,
    }


def one(hops, tag, source, switch):
    rows = [hop for hop in hops if hop["tag"] == tag and hop["src"] == source and
            hop["switch"] == switch]
    require(len(rows) == 1, "Expected one flow at requested switch")
    return rows[0]


def main():
    cells = [audit_cell(*cell) for cell in CELLS]
    require(cells[0]["fct_sha256"] == cells[1]["fct_sha256"] and
            cells[2]["fct_sha256"] == cells[3]["fct_sha256"],
            "Diagnostic off/on changed FCT bytes")
    background_base = one(cells[1]["hops"], 1, 0, 32)
    background_mixed = one(cells[3]["hops"], 1, 0, 32)
    base_path = sorted((hop["switch"], hop["port"]) for hop in cells[1]["hops"])
    mixed_path = sorted((hop["switch"], hop["port"]) for hop in cells[3]["hops"]
                        if hop["tag"] == 1)
    require(base_path == mixed_path and background_base["port"] ==
            background_mixed["port"], "Background route changed")
    contenders = [hop for hop in cells[3]["hops"] if hop["tag"] == 2 and
                  hop["switch"] == 32 and hop["port"] == background_mixed["port"]]
    overlapping = [hop for hop in contenders if
                   max(hop["first_enqueue_ns"], background_mixed["first_enqueue_ns"]) <
                   min(hop["last_dequeue_ns"], background_mixed["last_dequeue_ns"])]
    require(len(overlapping) == 1 and overlapping[0]["src"] == 3,
            "Expected competing flow did not overlap")
    base_fct = cells[1]["fct_ns_by_source"]["0"]
    mixed_fct = cells[3]["fct_ns_by_source"]["0"]
    base_wait = background_base["wait_ns_sum"] / background_base["packets"]
    mixed_wait = background_mixed["wait_ns_sum"] / background_mixed["packets"]
    require(mixed_fct > base_fct and mixed_wait > base_wait and
            background_mixed["mmu_egress_bytes_max"] >
            background_base["mmu_egress_bytes_max"],
            "Predeclared background direction did not hold")
    output = {
        "source_sha": SOURCE,
        "cell_raw_audit": [{key: value for key, value in cell.items() if key != "hops"}
                           for cell in cells],
        "background_path_unchanged": base_path,
        "shared_source_tor": 32,
        "shared_port": background_mixed["port"],
        "overlapping_contender_src_dst": [overlapping[0]["src"], overlapping[0]["dst"]],
        "overlap_envelope_ns": min(overlapping[0]["last_dequeue_ns"],
                                    background_mixed["last_dequeue_ns"]) -
                               max(overlapping[0]["first_enqueue_ns"],
                                   background_mixed["first_enqueue_ns"]),
        "background_fct_us_base": base_fct / 1000,
        "background_fct_us_mixed": mixed_fct / 1000,
        "background_fct_increase_us": (mixed_fct - base_fct) / 1000,
        "background_fct_increase_percent": 100 * (mixed_fct - base_fct) / base_fct,
        "background_mean_wait_ns_base": base_wait,
        "background_mean_wait_ns_mixed": mixed_wait,
        "background_device_queue_bytes_max_base": background_base["device_queue_bytes_max"],
        "background_device_queue_bytes_max_mixed": background_mixed["device_queue_bytes_max"],
        "background_mmu_egress_bytes_max_base": background_base["mmu_egress_bytes_max"],
        "background_mmu_egress_bytes_max_mixed": background_mixed["mmu_egress_bytes_max"],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
