#!/usr/bin/env python3
"""WS-25 throughput pilot on frozen calibration inputs; never efficacy evidence."""
import concurrent.futures
import datetime
import json
import shlex
import subprocess
import time
from pathlib import Path

import run_ws25_preflight as base
import run_ws25_v1fix_calibration as calibration

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/research/evidence/ws25-resource-pilot-plan.json"
RECEIPTS = ROOT / "results/ws25-resource-pilot-receipts.jsonl"
SUMMARY = ROOT / "results/ws25-resource-pilot-summary.json"
STAGES = (4, 8, 12)
POLL_SECONDS = 20


def planned_cells():
    original = [c for c in calibration.cells() if c["role"] == "primary"]
    if len(original) != sum(STAGES):
        raise RuntimeError("Expected exactly 24 calibration primary cells")
    cells = []
    for i, old in enumerate(original):
        cell = dict(old)
        cell["id"] = "20261003-210000-ws25-rpilot-%02d-%s" % (i + 1, old["mode"])
        cell["original_id"] = old["id"]
        cell["stage_cap"] = 4 if i < 4 else 8 if i < 12 else 12
        cells.append(cell)
    return cells


def frozen_plan():
    expected = {"purpose": "resource throughput and deterministic replay only",
                "source_sha": calibration.SOURCE_SHA,
                "topology_sha256": calibration.TOPO_SHA,
                "stages": list(STAGES), "cells": planned_cells(),
                "minimum_mem_available_gib": 32,
                "minimum_free_gib": 100, "maximum_load_1m": 20}
    encoded = json.dumps(expected, indent=2, sort_keys=True) + "\n"
    if PLAN.exists():
        if PLAN.read_text(encoding="utf-8") != encoded:
            raise RuntimeError("Frozen resource pilot plan changed")
    else:
        PLAN.parent.mkdir(parents=True, exist_ok=True)
        PLAN.write_text(encoded, encoding="utf-8")
    return expected


def receipt(event, **fields):
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    with RECEIPTS.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"event": event,
                                 "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                 **fields}, sort_keys=True) + "\n")
        stream.flush()


def host_gate(reject_active=False):
    audit = base.audit(reject_active=reject_active)
    remote_code = ("import os,subprocess; uid=os.getuid(); "
                   "lines=subprocess.check_output(['ps','-eo','uid,pid,stat,comm']).decode().splitlines()[1:]; "
                   "print('\\n'.join(x for x in lines if x.split() and int(x.split()[0])>=1000 "
                   "and int(x.split()[0])!=uid))")
    other_users = subprocess.check_output(base.remote.ssh_base(base.remote.config()) +
                                          ["python3 -c " + shlex.quote(remote_code)],
                                          universal_newlines=True, timeout=45).strip()
    if other_users:
        raise RuntimeError("Other user processes appeared; stop pilot admission: " + other_users[:500])
    if (float(audit["load_1m"]) > 20 or
            float(audit["mem_available_gib"]) < 32 or
            float(audit["free_gib"]) < 100):
        raise RuntimeError("Resource pilot safety gate failed: " + repr(audit))
    return audit


def build_one(cell):
    try:
        state = base.status(cell["id"])
    except RuntimeError as error:
        if "metadata.json" not in str(error) and "No such file" not in str(error):
            raise
        base.command("build", "--repo-local", str(ROOT), "--id", cell["id"],
                     "--source-sha", calibration.SOURCE_SHA, "--label", "ws25-resource-pilot")
        state = base.status(cell["id"])
        receipt("built", id=cell["id"], stage_cap=cell["stage_cap"])
    if state.get("git_commit") != calibration.SOURCE_SHA or state.get("status") not in ("BUILT", "SUCCEEDED"):
        raise RuntimeError("Unexpected pilot build identity/status: " + cell["id"])
    calibration.verify_remote_trace(cell)


def prebuild(cells):
    host_gate(reject_active=True)
    # Building uses -j2 per cell; keep at most eight build jobs total.
    for index in range(0, len(cells), 4):
        group = cells[index:index + 4]
        host_gate(reject_active=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(group)) as pool:
            futures = [pool.submit(build_one, cell) for cell in group]
            for cell, future in zip(group, futures):
                future.result()
                print(json.dumps({"built": cell["id"]}), flush=True)
        host_gate(reject_active=True)


def start_one(cell, cap):
    if (ROOT / "results" / cell["id"]).is_dir():
        raise RuntimeError("Pilot result already fetched; refusing new start: " + cell["id"])
    state = base.status(cell["id"])
    if state.get("status") != "BUILT":
        raise RuntimeError("Pilot cell is not freshly built: " + cell["id"])
    calibration.verify_remote_trace(cell)
    base.start_watch(cell["id"])
    base.command("run", cell["id"], "--lb", cell["mode"], "--pfc", "0", "--irn", "1",
                 "--bw", "400", "--buffer", "9", "--topo", "topo_1280_400G_400G_OS1",
                 "--flow-file", cell["trace"], "--simul-time", "0.01", "--netload", "10",
                 "--max-concurrent", str(cap))
    receipt("started", id=cell["id"], stage_cap=cap)


def finish_one(cell):
    base.wait_watch(cell["id"])
    base.command("fetch", cell["id"])
    local = ROOT / "results" / cell["id"]
    meta = json.loads((local / "metadata.json").read_text(encoding="utf-8"))
    base.fetch_config_log(cell, meta)
    result = calibration.verify(cell)
    original = calibration.verify(next(c for c in calibration.cells() if c["id"] == cell["original_id"]))
    if result["fct_sha256"] != original["fct_sha256"]:
        raise RuntimeError("Concurrent replay changed FCT fingerprint: " + cell["id"])
    receipt("verified", id=cell["id"], stage_cap=cell["stage_cap"],
            fct_sha256=result["fct_sha256"],
            peak_tree_rss_mib=result["resource"]["peak_tree_rss_mib"])
    return result


def run_stage(cells, cap):
    before = host_gate(reject_active=True)
    receipt("stage_start", cap=cap, ids=[c["id"] for c in cells], audit=before)
    start = time.monotonic()
    for cell in cells:
        host_gate()
        start_one(cell, cap)
    while True:
        time.sleep(POLL_SECONDS)
        audit = host_gate()
        states = {c["id"]: base.status(c["id"])["status"] for c in cells}
        if any(s not in ("RUNNING", "SUCCEEDED") for s in states.values()):
            raise RuntimeError("Pilot cell failed; preserve IDs: " + repr(states))
        if all(s == "SUCCEEDED" for s in states.values()):
            break
    elapsed = time.monotonic() - start
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(finish_one, cells))
    rss = [r["resource"]["peak_tree_rss_mib"] for r in results]
    row = {"cap": cap, "cells": len(cells), "wall_seconds": elapsed,
           "throughput_cells_per_hour": len(cells) * 3600 / elapsed,
           "maximum_tree_rss_mib": max(rss),
           "minimum_mem_available_gib": min(r["resource"]["minimum_mem_available_gib"] for r in results),
           "minimum_free_gib": min(r["resource"]["minimum_free_gib"] for r in results),
           "peak_load_1m": max(json.loads(line)["load_1m"]
                               for c in cells for line in
                               (ROOT / "results" / c["id"] / "logs/resource-samples.jsonl").read_text(encoding="utf-8").splitlines()
                               if line)}
    receipt("stage_verified", **row)
    print(json.dumps(row, sort_keys=True), flush=True)
    host_gate(reject_active=True)
    return row


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("plan", "prebuild", "run", "verify"))
    args = parser.parse_args()
    plan = frozen_plan()
    cells = plan["cells"]
    if args.phase == "plan":
        print(json.dumps({"cells": len(cells), "stages": STAGES, "source_sha": calibration.SOURCE_SHA}))
    elif args.phase == "prebuild":
        prebuild(cells)
    elif args.phase == "run":
        groups = {cap: [c for c in cells if c["stage_cap"] == cap] for cap in STAGES}
        rows = []
        for cap in STAGES:
            if (len(rows) >= 2 and
                    rows[-1]["throughput_cells_per_hour"] <=
                    rows[-2]["throughput_cells_per_hour"] * 1.05):
                receipt("pilot_stopped", reason="throughput_plateau", next_cap=cap)
                break
            rows.append(run_stage(groups[cap], cap))
        SUMMARY.write_text(json.dumps({"purpose": plan["purpose"], "stages": rows},
                                      indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        rows = [finish_one(c) if not (ROOT / "results" / c["id"]).is_dir()
                else calibration.verify(c) for c in cells]
        print(json.dumps({"verified_cells": len(rows)}))


if __name__ == "__main__":
    main()
