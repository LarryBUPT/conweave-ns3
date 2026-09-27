#!/usr/bin/env python3
"""Verify local experiment snapshots and build the WS-16 provenance index."""

import argparse
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/research/evidence/ws16-experiment-index.csv"
FIELDS = ("stage", "evidence_role", "experiment_id", "source_sha", "seed",
          "mode", "trace_sha256", "topology_sha256", "metadata",
          "trace_snapshot", "topology_snapshot", "fct_raw", "fct_sha256",
          "analysis_script")


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition, experiment_id, field):
    if not condition:
        raise ValueError("{}: {} mismatch".format(experiment_id, field))


def add(rows, stage, role, experiment_id, expected_sha, expected_fct,
        expected_trace, analysis_script, expected_topology=None):
    base = Path("results") / experiment_id
    meta_path = base / "metadata.json"
    metadata = read_json(meta_path)
    require(metadata["experiment_id"] == experiment_id, experiment_id, "ID")
    require(metadata["git_commit"] == expected_sha, experiment_id, "source SHA")
    require(metadata["input_flow_sha256"] == expected_trace, experiment_id, "trace metadata SHA")
    if expected_topology is not None:
        require(metadata["topology_sha256"] == expected_topology, experiment_id, "topology metadata SHA")
    trace = base / "config/traffic_trace.txt"
    topology = base / "config/topology.txt"
    raw_id = str(metadata["raw_directory"])
    fct = base / "raw" / raw_id / (raw_id + "_out_fct.txt")
    require(sha256(ROOT / trace) == expected_trace, experiment_id, "trace snapshot SHA")
    require(sha256(ROOT / topology) == metadata["topology_sha256"], experiment_id, "topology snapshot SHA")
    require(sha256(ROOT / fct) == expected_fct, experiment_id, "raw FCT SHA")
    rows.append(dict(stage=stage, evidence_role=role, experiment_id=experiment_id,
                     source_sha=expected_sha, seed=metadata["seed"],
                     mode=metadata["algorithm"], trace_sha256=expected_trace,
                     topology_sha256=metadata["topology_sha256"],
                     metadata=meta_path.as_posix(), trace_snapshot=trace.as_posix(),
                     topology_snapshot=topology.as_posix(), fct_raw=fct.as_posix(),
                     fct_sha256=expected_fct, analysis_script=analysis_script))


def build():
    rows = []
    ws10 = read_json("docs/research/ws10-fixed-load-formal-summary.json")
    for cell in ws10["cells"].values():
        add(rows, "WS-10", "preregistered_formal", cell["experiment_id"],
            ws10["source_sha"], cell["fct_sha256"], cell["trace_sha256"],
            "scripts/verify_ws10_formal.py", ws10["topology_sha256"])
    for stage, name, script in (
        ("WS-11", "ws11-full-moe-formal-summary.json", "scripts/verify_ws11_formal.py"),
        ("WS-12", "ws12-packet-strategies-formal-summary.json", "scripts/verify_ws12_formal.py"),
    ):
        summary = read_json("docs/research/" + name)
        for cell in summary["cells"]:
            add(rows, stage, "preregistered_formal", cell["id"],
                summary["simulation_git_commit"], cell["raw_files"]["fct"]["sha256"],
                cell["trace_sha256"], script, summary["topology_sha256"])
    feedback = read_json("docs/research/evidence/ws13-feedback-probe-analysis.json")
    for cell in feedback["cells"]:
        add(rows, "WS-13", "feedback_diagnostic", cell["id"], cell["git_commit"],
            cell["fct_sha256"], cell["trace_sha256"],
            "scripts/analyze_ws13_feedback_probe.py", feedback["topology_sha256"])
    calibration = read_json("docs/research/evidence/ws13-calibration-summary.json")
    for cell in calibration["cells"]:
        meta = read_json(Path("results") / cell["id"] / "metadata.json")
        add(rows, "WS-13", "calibration_only", cell["id"], meta["git_commit"],
            cell["fct_sha256"], cell["trace_sha256"],
            "scripts/analyze_ws13_calibration.py")
    for name, role in (("ws13-irn-pfc-factorial-pilot.json", "ordinary_technical_pilot"),
                       ("ws13-irn-pfc-factorial-stress.json", "stress_technical_pilot")):
        summary = read_json("docs/research/evidence/" + name)
        for cell in summary["cells"].values():
            add(rows, "WS-13", role, cell["experiment_id"], cell["git_commit"],
                cell["fct_sha256"], cell["trace_sha256"],
                "scripts/analyze_irn_pfc_factorial.py", cell["topology_sha256"])
    drop = read_json("docs/research/evidence/ws13-irn-pfc-drop-probe.json")
    add(rows, "WS-13", "drop_diagnostic_incomplete_13_of_16", drop["probe_id"],
        drop["probe_sha"], drop["fct_sha256"], drop["trace_sha256"],
        "scripts/analyze_irn_pfc_drop_probe.py")
    ws14 = read_json("docs/research/evidence/ws14-small-analysis.json")
    for cell in ws14["cells"]:
        add(rows, "WS-14", "single_input_stop_pilot", cell["id"], cell["git_commit"],
            cell["fct_sha256"], cell["trace_sha256"],
            "scripts/run_ws14_small.py; scripts/analyze_ws14_small.py",
            ws14["topology_sha256"])
    require(len(rows) == 216, "index", "row count")
    require(len({row["experiment_id"] for row in rows}) == len(rows), "index", "unique IDs")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare with committed CSV")
    args = parser.parse_args()
    rows = build()
    if args.check:
        with OUT.open(encoding="utf-8", newline="") as stream:
            require(list(csv.DictReader(stream)) == [
                {key: str(row[key]) for key in FIELDS} for row in rows], "index", "committed CSV")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    print("Verified {} experiment IDs; {}".format(len(rows), "index matches" if args.check else OUT))


if __name__ == "__main__":
    main()
