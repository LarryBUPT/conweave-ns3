#!/usr/bin/env python3
"""Freeze four non-perturbing ECMP diagnostics for the ClassLane v4 pilot."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/research/evidence/ws26-classlane4-pilot-plan-r2.json"
OUTPUT = ROOT / "docs/research/evidence/ws26-v4-ecmp-diagnostic-plan.json"
SEEDS = (20262694, 20262695, 20262696, 20262697)


def main():
    source_bytes = SOURCE.read_bytes()
    pilot = json.loads(source_bytes)
    controls = {
        cell["seed"]: cell for cell in pilot["cells"]
        if cell["stage"] == "high" and cell["background"] == 192
        and cell["mode"] == "fecmp" and cell["ws25_diag"] == 0
    }
    if set(controls) != set(SEEDS):
        raise RuntimeError("Pilot plan has an unexpected ECMP control set")

    cells = []
    for order, seed in enumerate(SEEDS, 1):
        plain = controls[seed]
        cell = dict(plain)
        cell["id"] = "20261009-230000-ws26v4-ecmpdiag-s%d-b192" % (seed % 100)
        cell["stage"] = "paired_background_hop_diagnostic"
        cell["order"] = order
        cell["ws25_diag"] = 1
        cell["paired_plain_id"] = plain["id"]
        cells.append(cell)

    plan = {
        "purpose": "Read-only mechanism diagnosis; no candidate effect screening",
        "source_sha": pilot["source_sha"],
        "source_plan_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "topology": pilot["topology"],
        "topology_sha256": pilot["topology_sha256"],
        "seeds": list(SEEDS),
        "cells": cells,
        "resource_limits": pilot["resource_limits"],
        "acceptance": {
            "expected_flows_per_cell": 16576,
            "fct_sha256_must_equal_paired_plain": True,
            "background_qps_per_cell": 192,
            "ws13_inflight_unpaired": 0,
            "resource_terminal_receipt_required": True,
            "watcher_first_sample_required": True,
            "max_concurrent": 1,
            "stop_on_first_failure": True,
        },
        "limits": [
            "WS13_HOP observes background data packets only.",
            "Per-hop queue and waiting observations are not MMU occupancy.",
            "The four already completed ECMP controls have no paired hop log.",
            "These new diagnostic cells do not add independent demand seeds.",
            "No performance gate is re-evaluated using this plan.",
        ],
    }
    encoded = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("Refusing to replace an existing frozen plan")
    OUTPUT.write_text(encoded, encoding="utf-8")
    print("frozen_cells=%d plan_sha256=%s" % (
        len(cells), hashlib.sha256(encoded.encode("utf-8")).hexdigest()))


if __name__ == "__main__":
    main()
