#!/usr/bin/env python3
"""Freeze the ten-cell, disclosed seed 97 class-rule diagnosis."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from verify_ws26_seed97_probe_preflight import (
    HEADER, ROOT, SMOKE, SMOKE_SHA256, TOPOLOGY, TOPOLOGY_SHA256,
    TRACE, TRACE_SHA256, digest, main as probe_preflight,
)


DESIGN = ROOT / "docs/research/ws26-classlane-factorial-diagnostic-design.md"
OUTPUT = ROOT / "docs/research/evidence/ws26-classlane-factorial-diagnostic-plan.json"
OLD_FCT = {
    "fecmp": "5782262613100533dd04fbcca515feda56beed12a3db0c27b32b02f16d5c3c68",
    "classlane4": "537dad823db4de5cf1b2b09ae711f0cd5976a2638024adc685e5317f029bb30e",
}
ARMS = {
    "fecmp": {"mode_number": 0, "moe_rule": 0, "background_rule": 0},
    "classlane4-moe-only": {"mode_number": 25, "moe_rule": 1, "background_rule": 0},
    "classlane4-background-only": {"mode_number": 26, "moe_rule": 0, "background_rule": 1},
    "classlane4": {"mode_number": 24, "moe_rule": 1, "background_rule": 1},
}
STAGE_CODES = {
    "smoke_plain": "splain", "smoke_probe": "sprobe",
    "high_reference_probe": "href", "high_mixed_plain": "hplain",
    "high_mixed_probe": "hprobe",
}
MODE_CODES = {
    "fecmp": "ecmp", "classlane4": "v4",
    "classlane4-moe-only": "moe", "classlane4-background-only": "bg",
}
SCHEDULE = [
    ("smoke_plain", "classlane4-moe-only", 0),
    ("smoke_probe", "classlane4-moe-only", 1),
    ("smoke_plain", "classlane4-background-only", 0),
    ("smoke_probe", "classlane4-background-only", 1),
    ("high_reference_probe", "fecmp", 1),
    ("high_reference_probe", "classlane4", 1),
    ("high_mixed_plain", "classlane4-moe-only", 0),
    ("high_mixed_probe", "classlane4-moe-only", 1),
    ("high_mixed_plain", "classlane4-background-only", 0),
    ("high_mixed_probe", "classlane4-background-only", 1),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--id-prefix", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
        parser.error("--source-sha needs a full Git SHA")
    if not re.fullmatch(r"[0-9]{8}-[0-9]{6}-ws26factor", args.id_prefix):
        parser.error("--id-prefix must be YYYYMMDD-HHMMSS-ws26factor")
    probe_preflight()
    if digest(TRACE) != TRACE_SHA256 or digest(SMOKE) != SMOKE_SHA256:
        raise RuntimeError("Fixed input changed")
    if digest(TOPOLOGY) != TOPOLOGY_SHA256:
        raise RuntimeError("Fixed topology changed")

    cells = []
    for order, (stage, mode, probe) in enumerate(SCHEDULE, 1):
        smoke = stage.startswith("smoke_")
        experiment_id = "%s-%02d-%s-%s" % (
            args.id_prefix, order, STAGE_CODES[stage], MODE_CODES[mode])
        if not re.fullmatch(r"[0-9]{8}-[0-9]{6}-[a-z0-9][a-z0-9-]{0,40}", experiment_id):
            raise RuntimeError("Experiment ID violates remote runner format: " + experiment_id)
        if (ROOT / "results" / experiment_id).exists():
            raise RuntimeError("Experiment ID already exists locally: " + experiment_id)
        cells.append({
            "order": order, "stage": stage, "id": experiment_id,
            "mode": mode, **ARMS[mode],
            "trace": SMOKE.name if smoke else TRACE.name,
            "trace_sha256": SMOKE_SHA256 if smoke else TRACE_SHA256,
            "trace_seed": None if smoke else 20262697,
            "ns3_seed": 1,
            "expected_flows": 61 if smoke else 16576,
            "expected_background_qps": 1 if smoke else 192,
            "expected_moe_qps": 60 if smoke else 16384,
            "pfc": 1, "irn": 1, "ws25_diag": 1,
            "ws26_moe_hop_diag": 1, "ws26_seed97_time_diag": probe,
            "expected_fct_sha256": OLD_FCT.get(mode) if not smoke else None,
            "plain_pair_order": (
                1 if order == 2 else 3 if order == 4 else
                7 if order == 8 else 9 if order == 10 else None
            ),
        })

    plan = {
        "purpose": "Disclosed seed 97 two-factor mechanism diagnosis; no effect estimate",
        "source_sha": args.source_sha,
        "design_sha256": digest(DESIGN),
        "target_header_sha256": digest(HEADER),
        "topology": TOPOLOGY.stem,
        "topology_sha256": TOPOLOGY_SHA256,
        "smoke_trace_sha256": SMOKE_SHA256,
        "high_trace_sha256": TRACE_SHA256,
        "cells": cells,
        "log_limits_per_probe_cell": {
            "switch_rows": 500000, "switch_bytes": 134217728,
            "qp_rows": 300000, "qp_bytes": 67108864,
            "total_rows": 800000, "total_bytes": 201326592,
            "overflow": 0,
        },
        "resource_limits_per_cell": {
            "max_concurrent": 1, "peak_tree_rss_mib": 32768,
            "min_mem_available_gib": 32, "min_free_gib": 100,
            "max_load_1m": 20,
        },
        "acceptance_order": [
            "fixed_source_and_input", "all_flows_complete_once",
            "all_trace_qp_identity_size_start_match",
            "background_and_moe_generic_hop_coverage",
            "stable_continuous_paths", "ws13_inflight_unpaired_zero",
            "selected_packet_enqueue_dequeue_paired",
            "selected_qp_send_ack_complete_and_zero_overflow",
            "classlane_active_and_bypassed_counters_match_factors",
            "plain_probe_fct_sha256_parity",
            "reference_probe_matches_old_plain_fct_sha256",
            "watcher_first_sample_and_terminal_resource_receipt",
        ],
        "stop_rule": "Stop on first failed gate, retain raw and ID, never overwrite; repair at new SHA and IDs.",
        "resource_pilot": "First high reference probe at cap=1; review full resource receipt before further high cells.",
        "limits": [
            "Disclosed seed and nested QPs are not independent effect replicates.",
            "The diagnosis separates class rules, not DCQCN, shared egress, or other reroutes.",
            "Diagnostic cells do not count toward formal or pilot performance gates.",
        ],
    }
    encoded = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("Refusing to replace an existing plan")
    OUTPUT.write_text(encoded, encoding="utf-8", newline="\n")
    print("cells=10 plan_sha256=" + hashlib.sha256(encoded.encode("utf-8")).hexdigest())


if __name__ == "__main__":
    main()
