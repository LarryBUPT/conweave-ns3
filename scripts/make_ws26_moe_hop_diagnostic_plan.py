#!/usr/bin/env python3
"""Freeze the paired, non-perturbing WS-26 MoE hop diagnostic cells."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "docs/research/evidence/ws26-classlane4-pilot-plan-r2.json"
PREFLIGHT = ROOT / "docs/research/evidence/ws26-classlane4-preflight-plan-r2.json"
OUTPUT = ROOT / "docs/research/evidence/ws26-moe-hop-diagnostic-plan.json"
SOURCE_SHA = "3bdb6c520a079a79f915300c7540fe1828f4445a"
SEEDS = (20262694, 20262695, 20262696, 20262697)


def one(cells, predicate, label):
    matched = [cell for cell in cells if predicate(cell)]
    if len(matched) != 1:
        raise RuntimeError("Expected exactly one " + label)
    return matched[0]


def main():
    pilot_bytes = PILOT.read_bytes()
    preflight_bytes = PREFLIGHT.read_bytes()
    pilot = json.loads(pilot_bytes)
    preflight = json.loads(preflight_bytes)
    if pilot["source_sha"] == SOURCE_SHA:
        raise RuntimeError("Diagnostic source must differ from the old pilot")
    if pilot["topology_sha256"] != preflight["topology_sha256"]:
        raise RuntimeError("Pilot and preflight topology differ")

    cells = []
    for mode in ("fecmp", "classlane4"):
        old = one(preflight["cells"], lambda c: c["trace_key"] == "mixed8"
                  and c["mode"] == mode and c["pfc"] == 1 and c["irn"] == 1
                  and c["ws25_diag"] == 0, "mixed8 " + mode)
        cells.append({
            "order": len(cells) + 1,
            "stage": "smoke",
            "id": "20261010-040000-ws26moehop-smoke-" + mode,
            "mode": mode,
            "seed": None,
            "trace": old["trace"],
            "trace_sha256": old["trace_sha256"],
            "expected_flows": 8,
            "expected_moe_qps": 4,
            "expected_background_qps": 4,
            "paired_plain_id": old["id"],
            "pfc": 1,
            "irn": 1,
            "ws25_diag": 1,
            "ws26_moe_hop_diag": 1,
        })

    for seed in SEEDS:
        for mode in ("fecmp", "classlane4"):
            old = one(pilot["cells"], lambda c: c["stage"] == "high"
                      and c["seed"] == seed and c["background"] == 192
                      and c["mode"] == mode and c["ws25_diag"] == 0,
                      "high %d %s" % (seed, mode))
            diagnostic = None
            if mode == "classlane4":
                diagnostic = one(pilot["cells"], lambda c: c["stage"] == "high"
                                 and c["seed"] == seed and c["background"] == 192
                                 and c["mode"] == mode and c["ws25_diag"] == 1,
                                 "old ClassLane diagnostic %d" % seed)["id"]
            cells.append({
                "order": len(cells) + 1,
                "stage": "paired_high_diagnostic",
                "id": "20261010-040000-ws26moehop-s%d-%s" % (seed % 100, mode),
                "mode": mode,
                "seed": seed,
                "trace": old["trace"],
                "trace_sha256": old["trace_sha256"],
                "expected_flows": 16576,
                "expected_moe_qps": 16384,
                "expected_background_qps": 192,
                "paired_plain_id": old["id"],
                "paired_old_candidate_diagnostic_id": diagnostic,
                "pfc": 1,
                "irn": 1,
                "ws25_diag": 1,
                "ws26_moe_hop_diag": 1,
            })

    if len({cell["id"] for cell in cells}) != 10:
        raise RuntimeError("Duplicate diagnostic ID")
    plan = {
        "purpose": "Mechanism diagnosis on disclosed pilot seeds, never an effect screen",
        "source_sha": SOURCE_SHA,
        "pilot_plan_sha256": hashlib.sha256(pilot_bytes).hexdigest(),
        "preflight_plan_sha256": hashlib.sha256(preflight_bytes).hexdigest(),
        "topology": pilot["topology"],
        "topology_sha256": pilot["topology_sha256"],
        "seeds": list(SEEDS),
        "cells": cells,
        "resource_limits": pilot["resource_limits"],
        "acceptance": {
            "all_input_flows_complete_once": True,
            "all_flow_identity_size_start_match": True,
            "fct_sha256_must_equal_paired_plain": True,
            "all_moe_qps_have_hop_rows": True,
            "all_background_qps_have_hop_rows": True,
            "qp_path_continuity_and_stability": True,
            "ws13_inflight_unpaired": 0,
            "resource_terminal_receipt_required": True,
            "watcher_first_sample_required": True,
            "max_concurrent": 1,
            "stop_on_first_failure": True,
        },
        "limits": [
            "The 4 pilot seeds are disclosed and do not add independent repetitions.",
            "MoE and background hop rows are egress-device observations, not MMU occupancy.",
            "Per-QP hop maxima cannot be added to explain whole-flow FCT.",
            "No pilot or formal effect gate is re-evaluated using these cells.",
        ],
    }
    encoded = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("Refusing to replace an existing frozen plan")
    OUTPUT.write_text(encoded, encoding="utf-8")
    print("cells=%d plan_sha256=%s" % (
        len(cells), hashlib.sha256(encoded.encode("utf-8")).hexdigest()))


if __name__ == "__main__":
    main()
