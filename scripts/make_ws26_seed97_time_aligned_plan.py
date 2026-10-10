#!/usr/bin/env python3
"""Freeze a disclosed, paired seed 97 time-line diagnosis."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from verify_ws26_seed97_probe_preflight import (
    DESIGN, HEADER, ROOT, SMOKE, SMOKE_SHA256, TOPOLOGY,
    TOPOLOGY_SHA256, TRACE, TRACE_SHA256, digest, main as preflight,
)


PILOT = ROOT / "docs/research/evidence/ws26-classlane4-pilot-plan-r2.json"
OUTPUT = ROOT / "docs/research/evidence/ws26-seed97-time-aligned-plan.json"
PLAIN_FCT = {
    "fecmp": "5782262613100533dd04fbcca515feda56beed12a3db0c27b32b02f16d5c3c68",
    "classlane4": "537dad823db4de5cf1b2b09ae711f0cd5976a2638024adc685e5317f029bb30e",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--id-prefix", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
        parser.error("--source-sha needs a complete Git SHA")
    if not re.fullmatch(r"[0-9]{8}-[0-9]{6}-ws26s97time", args.id_prefix):
        parser.error("--id-prefix must be YYYYMMDD-HHMMSS-ws26s97time")
    preflight()
    pilot = json.loads(PILOT.read_text(encoding="utf-8"))
    plain = {}
    for mode in PLAIN_FCT:
        cells = [row for row in pilot["cells"] if row.get("stage") == "high"
                 and row.get("seed") == 20262697 and row.get("background") == 192
                 and row.get("mode") == mode and row.get("ws25_diag") == 0]
        if len(cells) != 1 or cells[0]["trace_sha256"] != TRACE_SHA256:
            raise RuntimeError("Seed 97 pilot pair is missing or ambiguous: " + mode)
        plain[mode] = cells[0]["id"]

    cells = []
    for stage, suffix, mode, trace, trace_sha, flows, background, moe, probe in (
            ("smoke_plain", "smoke-plain-fecmp", "fecmp", SMOKE.name,
             SMOKE_SHA256, 61, 1, 60, 0),
            ("smoke_probe", "smoke-probe-fecmp", "fecmp", SMOKE.name,
             SMOKE_SHA256, 61, 1, 60, 1),
            ("paired_high", "high-fecmp", "fecmp", TRACE.name,
             TRACE_SHA256, 16576, 192, 16384, 1),
            ("paired_high", "high-classlane4", "classlane4", TRACE.name,
             TRACE_SHA256, 16576, 192, 16384, 1)):
        experiment_id = args.id_prefix + "-" + suffix
        if (ROOT / "results" / experiment_id).exists():
            raise RuntimeError("Experiment ID already exists locally: " + experiment_id)
        cells.append({
            "order": len(cells) + 1, "stage": stage, "id": experiment_id,
            "mode": mode, "seed": 20262697 if stage == "paired_high" else None,
            "trace": trace, "trace_sha256": trace_sha,
            "expected_flows": flows, "expected_background_qps": background,
            "expected_moe_qps": moe, "pfc": 1, "irn": 1,
            "ws25_diag": 1, "ws26_moe_hop_diag": 1,
            "ws26_seed97_time_diag": probe,
            "paired_plain_id": plain[mode] if stage == "paired_high" else None,
            "paired_plain_fct_sha256": PLAIN_FCT[mode] if stage == "paired_high" else None,
        })
    plan = {
        "purpose": "Disclosed seed 97 mechanism diagnosis; no new effect estimate",
        "source_sha": args.source_sha,
        "pilot_plan_sha256": digest(PILOT),
        "design_sha256": digest(DESIGN),
        "target_header_sha256": digest(HEADER),
        "topology": TOPOLOGY.stem, "topology_sha256": TOPOLOGY_SHA256,
        "smoke_trace_sha256": SMOKE_SHA256,
        "high_trace_sha256": TRACE_SHA256,
        "cells": cells,
        "log_limits": {"switch_rows": 500000, "switch_bytes": 134217728,
                       "qp_rows": 300000, "qp_bytes": 67108864,
                       "total_rows": 800000, "total_bytes": 201326592},
        "resource_limits": {"peak_tree_rss_mib": 32768,
                            "min_mem_available_gib": 32,
                            "min_free_gib": 100, "max_load_1m": 20,
                            "max_concurrent": 1},
        "acceptance": {
            "fixed_source_and_input": True, "all_flows_complete_once": True,
            "all_trace_qp_identity_size_start_match": True,
            "background_and_moe_hop_coverage": True,
            "stable_continuous_paths": True, "ws13_inflight_unpaired": 0,
            "selected_packet_enqueue_dequeue_paired": True,
            "selected_qp_send_and_ack_present": True,
            "new_log_overflow": 0,
            "smoke_probe_fct_equals_smoke_plain": True,
            "high_probe_fct_equals_frozen_plain": True,
            "watcher_first_sample_and_terminal_receipt": True,
            "stop_on_first_failure": True,
        },
        "limits": [
            "The seed is disclosed; the QPs are nested observations, not independent trials.",
            "The sixth background comparison reuses one control QP.",
            "Time ordering alone does not identify a causal mechanism.",
            "No pilot or formal effect gate is re-evaluated with these cells.",
        ],
    }
    encoded = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("Refusing to replace an existing plan")
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(encoded)
    print("cells=4 plan_sha256=" + hashlib.sha256(encoded.encode("utf-8")).hexdigest())


if __name__ == "__main__":
    main()
