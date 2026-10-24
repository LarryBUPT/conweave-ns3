"""Reverify and combine the immutable WS-30 stage-3 correctness receipts."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_ws30_stage3 as stage3


def main():
    plan = stage3.read(stage3.PLAN)
    cells = stage3.read(stage3.CHECK_PLAN)["cells"]
    cells += stage3.read(stage3.EV / "ws30-stage3-correctness-plan-r6.json")["cells"]
    assert len(cells) == 14
    assert len({c["id"] for c in cells}) == 14
    accepted = stage3.read(stage3.EV / "ws30-technical-results-recovered-r1.json")
    historical_plan = stage3.read(stage3.EV / "ws30-stage2-recovery-plan-r1.json")
    rows = []
    for cell in cells:
        row = stage3.verify(cell)
        metadata = stage3.read(stage3.ROOT / "results" / cell["id"] / "metadata.json")
        assert metadata["status"] == "SUCCEEDED"
        assert metadata["git_commit"] == stage3.COMPOSITION_SOURCE
        assert metadata["started_utc"] < metadata["finished_utc"]
        row["identity"] = {
            key: cell[key]
            for key in ("id", "role", "arm", "swap", "continuing", "trace", "trace_sha256",
                        "topology", "topology_sha256", "source_sha", "expected_fct_sha256")
            if key in cell
        }
        row["execution"] = {
            "created_utc": metadata["created_utc"],
            "started_utc": metadata["started_utc"],
            "finished_utc": metadata["finished_utc"],
            "actual_cap": metadata["concurrency_cap"],
            "status": metadata["status"],
            "input_flow_sha256": metadata["input_flow_sha256"],
            "raw_directory": metadata["raw_directory"],
            "parameters": {
                "pfc": metadata["parameters"]["pfc"],
                "irn": metadata["parameters"]["irn"],
                "bw": metadata["parameters"]["bw"],
                "buffer": metadata["parameters"]["buffer"],
                "simul_time": metadata["parameters"]["simul_time"],
                "netload": metadata["parameters"]["netload"],
                "ws30_observe": metadata["parameters"]["ws30_observe"],
                "ws30_composition": metadata["parameters"]["ws30_composition"],
            },
        }
        if cell["role"] == "composition-check":
            specification = next(
                c for c in plan["composition"]
                if (c["arm"], c["swap"], c["continuing"])
                == (cell["arm"], cell["swap"], cell["continuing"])
            )
            assert row["trace_sha256"] == specification["trace_sha256"]
            composition = row["composition"]
            snapshot = composition["snapshot"]
            assert snapshot["q1"] == snapshot["q2"] == 65536
            assert (snapshot["b1"], snapshot["b2"]) == (
                specification["expected_background_by_port"]["2"],
                specification["expected_background_by_port"]["3"],
            )
            assert composition["all_completed_rows"] == specification["input_flows"]
            expected_after = 134144 if cell["continuing"] else 0
            assert composition["after_probe_background_by_port"] == {
                "2": expected_after, "3": expected_after
            }
            choice = next(c for c in row["observation"]["choices"] if c["tag"] == 2)
            if cell["arm"] == "C16":
                assert composition["chosen_port"] == (2 if cell["swap"] else 3)
                assert choice["composition"] == 1
                assert choice["a_disagrees"] == (0 if cell["swap"] else 1)
            elif cell["arm"] == "Q16":
                assert composition["chosen_port"] == 2
                assert choice["composition"] == 1
            else:
                assert cell["arm"] == "E" and choice["events"] == 0
            queue = row["observation"]["queue"]
            transport = row["observation"]["transport_sums"]
            assert queue["dropped"] == queue["admission_dropped_bytes"] == 0
            assert queue["queue_rejected_bytes"] == queue["violations"] == 0
            assert transport["retransmit_packets"] == transport["retransmit_bytes"] == 0
            assert transport["timeout"] == transport["rx_gap"] == 0
        else:
            assert cell["role"] == "compatibility-check"
            bridge = next(
                c for c in historical_plan["technical"]
                if c["arm"] == cell["arm"] and c["role"] == "bridge-precheck"
            )
            historical = next(r for r in accepted["rows"] if r["id"] == bridge["id"])
            assert row["fct_sha256"] == cell["expected_fct_sha256"] == historical["fct_sha256"]
        rows.append(row)

    composition_cells = [c for c in cells if c["role"] == "composition-check"]
    assert len(composition_cells) == 12
    assert {(c["swap"], c["continuing"]) for c in composition_cells} == {
        (0, 0), (1, 0), (0, 1), (1, 1)
    }
    assert {c["arm"] for c in composition_cells} == {"E", "Q16", "C16"}

    preserved_failures = []
    for name in (
        "ws30-stage3-correctness-summary-r2.json",
        "ws30-stage3-correctness-summary-r3.json",
        "ws30-stage3-correctness-summary-r4.json",
    ):
        summary = json.loads((stage3.ROOT / "results" / name).read_text(encoding="utf-8"))
        preserved_failures.extend(summary["failures"])
    assert len(preserved_failures) == 3
    evidence = {
        "kind": "WS-30 stage-3 fixture correctness audit; technical only",
        "source_sha": stage3.COMPOSITION_SOURCE,
        "formal_plan_sha256": stage3.stage.sha(stage3.PLAN),
        "composition_design_sha256": stage3.stage.sha(stage3.EV / "ws30-composition-design-r3.json"),
        "verified_ids": len(rows),
        "composition_cells": len(composition_cells),
        "compatibility_checks": 2,
        "formal_effect_cells_counted": 0,
        "preserved_failed_ids": preserved_failures,
        "rows": rows,
    }
    stage3.stage.frozen(stage3.EV / "ws30-stage3-correctness-combined-r1.json", evidence)
    print(json.dumps({
        "verified_ids": len(rows),
        "composition_cells": len(composition_cells),
        "compatibility_checks": 2,
        "preserved_failures": len(preserved_failures),
        "result": "PASS",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
