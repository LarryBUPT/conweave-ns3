#!/usr/bin/env python3
"""Generate the fixed six-cell WS-26 queue-front diagnosis plan locally."""

import hashlib
import json
import re
from pathlib import Path

from verify_ws26_seed97_probe_preflight import (
    ROOT, SMOKE, SMOKE_SHA256, TOPOLOGY, TOPOLOGY_SHA256,
    TRACE, TRACE_SHA256, digest, main as probe_preflight,
)


SOURCE_SHA = "f60c8002057a4ca65b5b31f8610acbb8549aa316"
PREFIX = "20261012-230000-ws26qfront"
DESIGN = ROOT / "docs/research/ws26-queue-front-seed97-design.md"
OUTPUT = ROOT / "docs/research/evidence/ws26-queue-front-seed97-plan.json"
SCHEDULE = [
    ("01-s10-off", "smoke", "classlane4-moe-only", 0),
    ("02-s10-on", "smoke", "classlane4-moe-only", 1),
    ("03-s11-off", "smoke", "classlane4", 0),
    ("04-s11-on", "smoke", "classlane4", 1),
    ("05-h10-on", "high_resource_pilot_and_diagnosis", "classlane4-moe-only", 1),
    ("06-h11-on", "high_diagnosis", "classlane4", 1),
]
OLD_FCT = {
    "classlane4-moe-only": "6a74b903f6142bfe04a0f6472647d4d4c179a097ba043d727548d8e03ed03b0f",
    "classlane4": "dc06ed85f7d70740fb32983822fd5bfb463dd991147145c7970e209831a0c08a",
}


def cli(cell):
    return ["python", "scripts/remote_experiment.py", "run", cell["id"],
            "--lb", cell["lb"], "--flow-file", cell["trace"],
            "--topo", "topo_1280_400G_400G_OS1", "--cdf", "AliStorage2019",
            "--simul-time", "0.01", "--netload", "10", "--bw", "400",
            "--buffer", "9", "--pfc", "1", "--irn", "1",
            "--max-concurrent", "1", "--factorial-pilot",
            "--ws25-diag", "1", "--ws26-moe-hop-diag", "1",
            "--ws26-seed97-time-diag", "1", "--ws26-queue-front-diag",
            str(cell["ws26_queue_front_diag"])]


def main():
    probe_preflight()
    if (digest(TRACE), digest(SMOKE), digest(TOPOLOGY)) != (
            TRACE_SHA256, SMOKE_SHA256, TOPOLOGY_SHA256):
        raise RuntimeError("Fixed trace/topology bytes changed")
    cells = []
    for order, (suffix, stage, lb, probe) in enumerate(SCHEDULE, 1):
        experiment_id = PREFIX + "-" + suffix
        if (not re.fullmatch(r"[0-9]{8}-[0-9]{6}-[a-z0-9][a-z0-9-]{0,40}", experiment_id)
                or (ROOT / "results" / experiment_id).exists()):
            raise RuntimeError("Invalid or locally occupied ID: " + experiment_id)
        smoke = stage == "smoke"
        cell = {
            "order": order, "id": experiment_id, "stage": stage, "lb": lb,
            "mode_number": 25 if lb == "classlane4-moe-only" else 24,
            "factors": "10" if lb == "classlane4-moe-only" else "11",
            "trace": SMOKE.name if smoke else TRACE.name,
            "trace_sha256": SMOKE_SHA256 if smoke else TRACE_SHA256,
            "expected_flows": 61 if smoke else 16576,
            "expected_background_qps": 1 if smoke else 192,
            "expected_moe_qps": 60 if smoke else 16384,
            "ns3_seed": 1, "pfc": 1, "irn": 1, "factorial_pilot": True,
            "bw_gbps": 400, "buffer_mib": 9, "netload": 10,
            "simul_time": "0.01", "max_concurrent": 1,
            "ws25_diag": 1, "ws26_moe_hop_diag": 1,
            "ws26_seed97_time_diag": 1, "ws26_time_probe": 0,
            "ws26_queue_front_diag": probe,
            "old_high_fct_sha256": OLD_FCT[lb] if not smoke else None,
        }
        cell["run_cli"] = cli(cell)
        cells.append(cell)
    for off, on in ((0, 1), (2, 3)):
        left = dict(cells[off]); right = dict(cells[on])
        for row in (left, right):
            for key in ("id", "order", "run_cli", "ws26_queue_front_diag"):
                row.pop(key)
        if left != right:
            raise RuntimeError("Smoke pair differs beyond the new diagnostic flag")
    plan = {
        "status": "proposed_freeze_pending_main_review",
        "purpose": "Observe queue composition on disclosed seed 97; no effect estimate",
        "source_sha": SOURCE_SHA,
        "design_sha256": digest(DESIGN),
        "topology": TOPOLOGY.name, "topology_sha256": TOPOLOGY_SHA256,
        "smoke_trace_sha256": SMOKE_SHA256,
        "high_trace_sha256": TRACE_SHA256,
        "cells": cells,
        "smoke_pairs": [
            {"off_id": cells[0]["id"], "on_id": cells[1]["id"],
             "gate": "raw FCT SHA-256 exactly equal"},
            {"off_id": cells[2]["id"], "on_id": cells[3]["id"],
             "gate": "raw FCT SHA-256 exactly equal"},
        ],
        "high_resource_pilot_id": cells[4]["id"],
        "high_resource_pilot_reuse": "If all gates pass, retain this original ID as 10-on diagnosis; do not rerun it as independent evidence.",
        "log_budget": {
            "queue_front_max_rows_per_on_cell": 400000,
            "queue_front_max_bytes_per_on_cell": 100663296,
            "old_10_raw_config_log_bytes": 135216060,
            "old_11_raw_config_log_bytes": 131808838,
            "old_10_local_logs_copy_bytes": 135216060,
            "old_11_local_logs_copy_bytes": 131808838,
            "estimated_10_raw_plus_probe_bytes": 235879356,
            "estimated_11_raw_plus_probe_bytes": 232472134,
            "estimated_10_with_local_duplicate_bytes": 471758712,
            "estimated_11_with_local_duplicate_bytes": 464944268,
            "pilot_must_measure_actual_peak": True,
        },
        "resource_gate": {
            "max_concurrent": 1, "peak_tree_rss_mib": 32768,
            "min_mem_available_gib": 32, "min_free_gib": 100,
            "max_load_1m": 20, "first_and_terminal_receipts_required": True,
        },
        "acceptance_order": [
            "source_sha_and_fixed_input_hashes", "isolated_unique_ids",
            "four_smoke_cells_all_61_flows_complete_once",
            "smoke_off_on_raw_fct_sha256_equal_per_arm",
            "queue_front_terminal_summary_and_budget", "queue_front_subqueue_fifo_replay",
            "high_10_on_all_16576_flows_complete_once",
            "high_10_on_old_fct_sha256_parity", "high_10_on_resource_receipts_and_limits",
            "reuse_high_10_on_original_id", "high_11_on_all_16576_flows_complete_once",
            "high_11_on_old_fct_sha256_parity", "high_11_on_replay_and_resources",
            "pair_with_existing_00_01_raw_without_rerun",
        ],
        "stop_rule": "Stop on first failure; preserve original ID/raw/logs; fix under a new SHA and IDs.",
        "remote_id_check": "Pending until remote access is authorized; abort if any planned ID already exists.",
        "interpretation_limits": [
            "Queue membership is observational and does not identify causal shares.",
            "Disclosed seed 97 is not a new mechanism effect pilot.",
            "Formal two-sided criteria and all outstanding WS-26 acceptance items remain unchanged.",
        ],
    }
    encoded = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("Refusing to overwrite a different frozen plan")
    OUTPUT.write_text(encoded, encoding="utf-8", newline="\n")
    print("cells=6 plan_sha256=" + hashlib.sha256(encoded.encode("utf-8")).hexdigest())


if __name__ == "__main__":
    main()
