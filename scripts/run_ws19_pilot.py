#!/usr/bin/env python3
"""Build and run the frozen WS-19 cells with ordered starts and receipts."""
import argparse
import concurrent.futures
import datetime
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from verify_ws19_cell import verify

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/research/evidence/ws19-pilot-schedule-v1.json"
RESULTS = ROOT / "results"
RUN_MAP = ROOT / "docs/research/evidence/ws19-pilot-run-map-v1.json"
RECEIPTS = RESULTS / "ws19-pilot-receipts.jsonl"
SOURCE_SHA = "b52e66f0fbf786fb57672b12a5633cf45b9311c1"
REPO = "https://github.com/LarryBUPT/conweave-ns3.git"
TOPO = "topo_1280_400G_400G_OS1"
TOPOLOGY = ROOT / "config" / (TOPO + ".txt")
LOCK = threading.Lock()
ID_PREFIX = "20260928-163500"


def call(argv, timeout=None):
    done = subprocess.run(argv, cwd=str(ROOT), stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True,
                          timeout=timeout)
    if done.returncode:
        raise RuntimeError("command failed %r: %s" % (argv[1:4], done.stdout[-1800:]))
    return done.stdout


def controller(*args):
    return call([sys.executable, str(ROOT / "scripts/remote_experiment.py")] + list(args))


def parse_json_output(output):
    return json.JSONDecoder().raw_decode(output[output.index("{"):])[0]


def status(experiment_id):
    return parse_json_output(controller("status", experiment_id))


def get_plan():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    assert plan["planned_runs"] == 48 and len(plan["runs"]) == 48
    ids = []
    for row in plan["runs"]:
        suffix = {"host_hotspot": "h", "tor_hotspot": "t"}[row["hotspot"]]
        bg = "b0" if row["background"] == 0 else "b192"
        seed = str(row["seed"])[-2:]
        arm = {"ecmp": "e", "admission": "a", "path": "p", "joint": "j"}[row["arm"]]
        row["experiment_id"] = ("%s-ws19-%s%d-%s-%s-%s" %
                                 (ID_PREFIX, suffix, row["block"], bg, seed, arm))
        ids.append(row["experiment_id"])
    assert len(set(ids)) == 48
    mapping = {"source_sha": SOURCE_SHA, "schedule_sha256": plan["schedule_sha256"]
               if "schedule_sha256" in plan else "6dda53c30ebaf7b5c537f50452e06376e938fe96de33c3b4f8d57aec769c7769",
               "id_prefix": ID_PREFIX,
               "runs": [{"index": i, "id": row["experiment_id"], "block": row["block"],
                         "position": row["position"], "arm": row["arm"],
                         "seed": row["seed"], "hotspot": row["hotspot"],
                         "background": row["background"], "trace_sha256": row["trace_sha256"]}
                        for i, row in enumerate(plan["runs"])]}
    data = (json.dumps(mapping, indent=2, sort_keys=True) + "\n").encode()
    if RUN_MAP.exists():
        assert RUN_MAP.read_bytes() == data
    else:
        RUN_MAP.write_bytes(data)
    return plan


def receipt(event, row, **fields):
    item = {"event": event, "id": row["experiment_id"], "index": row["block"] * 4 + row["position"] - 5,
            "arm": row["arm"], "seed": row["seed"], "hotspot": row["hotspot"],
            "background": row["background"], "utc": datetime.datetime.utcnow().isoformat() + "Z"}
    item.update(fields)
    RESULTS.mkdir(exist_ok=True)
    with LOCK:
        with RECEIPTS.open("a", encoding="utf-8") as out:
            out.write(json.dumps(item, sort_keys=True) + "\n")
            out.flush()


def state_or_none(experiment_id):
    try:
        return status(experiment_id)
    except RuntimeError as error:
        message = str(error)
        if "metadata.json" in message or "No such file" in message or "not found" in message:
            return None
        raise


def build_one(row):
    state = state_or_none(row["experiment_id"])
    if state and state["status"] in ("BUILT", "RUNNING", "SUCCEEDED"):
        assert state["git_commit"] == SOURCE_SHA
        return
    started = time.monotonic()
    controller("build", "--repo-local", str(ROOT), "--source-sha", SOURCE_SHA,
               "--id", row["experiment_id"], "--label", "ws19-pilot")
    state = status(row["experiment_id"])
    assert state["status"] == "BUILT" and state["git_commit"] == SOURCE_SHA
    receipt("built", row, build_seconds=round(time.monotonic() - started, 2))


def resource_audit():
    lines = controller("check").splitlines()
    values = dict(line.split("=", 1) for line in lines if "=" in line)
    if (float(values["load_1m"]) > 20 or float(values["mem_available_gib"]) < 32 or
            float(values["free_gib"]) < 100 or values["active_simulation_pids"]):
        # Existing WS-19 experiment processes are allowed; unknown processes are not.
        active = values["active_simulation_pids"]
        if float(values["load_1m"]) > 20 or float(values["mem_available_gib"]) < 32 or float(values["free_gib"]) < 100:
            raise RuntimeError("Resource stop line reached: " + str(values))
    return values


def start_watcher(experiment_id):
    remote = "/home/fnl/lzy/results/%s/logs" % experiment_id
    command = ("if test ! -e {0}/resource-samples.jsonl; then "
               "nohup python3 /home/fnl/lzy/.research-workflow/ws11_resource_watch.py "
               "{1} > {0}/resource-watch.log 2>&1 < /dev/null & fi; "
               "sleep 1; test -e {0}/resource-samples.jsonl").format(remote, experiment_id)
    call(["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
          "fnl@10.112.14.167", command], timeout=20)


def wait_watcher(experiment_id):
    remote = "/home/fnl/lzy/results/%s/logs/resource-summary.json" % experiment_id
    for _ in range(12):
        done = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                               "fnl@10.112.14.167", "test -s " + remote],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if done.returncode == 0:
            return
        time.sleep(5)
    raise RuntimeError("Resource watcher did not finish for " + experiment_id)


def run_args(row, cap):
    admission, path = {"ecmp": (0, 0), "admission": (1, 0),
                       "path": (0, 1), "joint": (1, 1)}[row["arm"]]
    args = ["run", row["experiment_id"], "--lb", "ws18", "--simul-time", "0.01",
            "--netload", "10", "--bw", "400", "--buffer", "9", "--topo", TOPO,
            "--cdf", "AliStorage2019", "--pfc", "0", "--irn", "1",
            "--flow-file", row["trace"], "--ws18-admission", str(admission),
            "--ws18-path", str(path), "--ws18-admission-rate-gbps", "400",
            "--max-concurrent", str(cap)]
    if row["background"]:
        args.extend(["--ws13-diag", "1"])
    return args


def launch(row, cap):
    resource_audit()
    state = status(row["experiment_id"])
    assert state["status"] == "BUILT" and state["git_commit"] == SOURCE_SHA
    controller(*run_args(row, cap))
    start_watcher(row["experiment_id"])
    receipt("started", row, concurrency_cap=cap)


def finish(row, index):
    experiment_id = row["experiment_id"]
    wait_watcher(experiment_id)
    controller("fetch", experiment_id)
    summary = verify(experiment_id, row)
    receipt("verified", row, schedule_index=index, fct_sha256=summary["fct_sha256"],
            timing_sha256=summary["timing_sha256"], trace_sha256=summary["trace_sha256"],
            peak_tree_rss_mib=summary["resources"]["peak_tree_rss_mib"],
            min_mem_gib=summary["resources"]["minimum_mem_available_gib"],
            min_disk_gib=summary["resources"]["minimum_free_gib"])


def run_rows(rows, cap, poll_seconds=90):
    rows = list(rows)
    done_ids = set()
    if RECEIPTS.exists():
        for line in RECEIPTS.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            if item["event"] == "verified":
                done_ids.add(item["id"])
    rows = [r for r in rows if r["experiment_id"] not in done_ids]
    active = {}
    next_index = 0
    failure = None
    while next_index < len(rows) or active:
        while failure is None and next_index < len(rows) and len(active) < cap:
            row = rows[next_index]
            launch(row, cap)
            active[row["experiment_id"]] = (next_index, row)
            next_index += 1
        if not active:
            break
        time.sleep(poll_seconds)
        for experiment_id, (local_index, row) in list(active.items()):
            state = status(experiment_id)
            if state["status"] == "SUCCEEDED":
                del active[experiment_id]
                try:
                    finish(row, row["schedule_index"])
                except Exception as error:
                    failure = error
                    receipt("verification_failed", row, error=str(error))
            elif state["status"] in ("FAILED", "BUILD_FAILED", "INTERRUPTED"):
                failure = RuntimeError("Experiment failed: %s (%s)" % (experiment_id, state["status"]))
                receipt("failed", row, state=state["status"])
                del active[experiment_id]
        try:
            resource_audit()
        except Exception as error:
            failure = failure or error
            receipt("resource_stop", rows[min(next_index, len(rows) - 1)], error=str(error))
    if failure:
        raise RuntimeError("WS-19 stopped after preserving in-flight runs: " + str(failure))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("map", "build", "run"))
    parser.add_argument("--build-workers", type=int, choices=(1, 2, 4, 8), default=8)
    parser.add_argument("--concurrency", type=int, choices=(1, 2, 4, 8), default=2)
    parser.add_argument("--subset", choices=("first2", "rest", "all"), default="all")
    args = parser.parse_args()
    plan = get_plan()
    rows = plan["runs"]
    for index, row in enumerate(rows):
        row["schedule_index"] = index
    if args.phase == "map":
        print(str(RUN_MAP))
        return
    if args.subset == "first2":
        rows = rows[:2]
    elif args.subset == "rest":
        rows = rows[2:]
    if args.phase == "build":
        resource_audit()
        failures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.build_workers) as pool:
            futures = {pool.submit(build_one, row): row for row in rows}
            for future, row in [(f, r) for f, r in futures.items()]:
                try:
                    future.result()
                except Exception as error:
                    failures.append((row["experiment_id"], str(error)))
        if failures:
            raise RuntimeError("Build failures: " + repr(failures[:3]))
        print("Built %d WS-19 cells" % len(rows))
        return
    resource_audit()
    run_rows(rows, args.concurrency)
    print("Verified %d WS-19 cells in selected sequence" % len(rows))


if __name__ == "__main__":
    main()
