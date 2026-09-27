"""Check WS-18 four-arm identity, timing, bytes, and legacy ECMP regression."""
import argparse
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path


ARMS = (("ecmp", 0, 0), ("admission", 1, 0),
        ("path", 0, 1), ("joint", 1, 1))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace_rows(path):
    lines = path.read_text().splitlines()
    assert int(lines[0]) == len(lines) - 1
    rows = []
    for line in lines[1:]:
        src, dst, pg, size, start, tag = line.split()
        rows.append((int(src), int(dst), int(size),
                     int(Decimal(start) * 1000000000), int(tag)))
    return rows


def read_arm(root, experiment_id, expected, admission, path):
    base = root / experiment_id
    meta = json.loads((base / "metadata.json").read_text())
    assert meta["status"] == "SUCCEEDED", experiment_id
    assert meta["parameters"]["lb"] == "ws18"
    assert int(meta["parameters"]["ws18_admission"]) == admission
    assert int(meta["parameters"]["ws18_path"]) == path
    assert int(meta["parameters"]["pfc"]) == 0
    assert int(meta["parameters"]["irn"]) == 1
    assert int(meta["seed"]) == 1
    raw_id = str(meta["raw_directory"])
    raw = base / "raw" / raw_id
    timing = raw / (raw_id + "_out_ws18.txt")
    fct = raw / (raw_id + "_out_fct.txt")
    assert digest(base / "config" / "traffic_trace.txt") == digest(expected["trace"])
    assert digest(base / "config" / "topology.txt") == digest(expected["topology"])
    rows = {}
    for line in timing.read_text().splitlines():
        values = [int(x) for x in line.split()]
        assert len(values) == 12
        fid, src, dst, sport, dport, tag, size, demand, release, finish, wait, total = values
        assert fid not in rows and 0 <= fid < len(expected["rows"])
        assert (src, dst, size, demand, tag) == expected["rows"][fid]
        assert demand <= release <= finish
        assert wait == release - demand and total == finish - demand
        if not admission or tag != 2:
            assert wait == 0
        rows[fid] = values
    assert len(rows) == len(expected["rows"])
    fct_rows = {}
    for line in fct.read_text().splitlines():
        values = [int(x) for x in line.split()]
        assert len(values) == 8
        key = tuple(values[:4])
        assert key not in fct_rows
        fct_rows[key] = values
    assert len(fct_rows) == len(rows)
    for values in rows.values():
        _, src, dst, sport, dport, _, size, _, release, finish, _, _ = values
        old = fct_rows[(src, dst, sport, dport)]
        assert old[4] == size and old[5] == release and old[5] + old[6] == finish
    log = (base / "logs" / "simulation.log").read_text(errors="replace")
    match = re.search(r"WS18_PATH flows=(\d+) alternate=(\d+) packets=(\d+) multipath_packets=(\d+)", log)
    assert match, experiment_id
    flows, alternate, packets, multipath = map(int, match.groups())
    if path:
        assert flows > 0 and multipath > 0
    else:
        assert (flows, alternate, packets, multipath) == (0, 0, 0, 0)
    conserve = re.search(r"WS18_CONSERVATION input=(\d+) released=(\d+) finished=(\d+) input_bytes=(\d+) finished_bytes=(\d+)", log)
    assert conserve
    n, released, finished, input_bytes, finished_bytes = map(int, conserve.groups())
    assert n == released == finished == len(rows)
    assert input_bytes == finished_bytes == sum(row[2] for row in expected["rows"])
    return {"experiment_id": experiment_id, "source_sha": meta["git_commit"],
            "fct_sha256": digest(fct), "timing_sha256": digest(timing),
            "flows": n, "bytes": input_bytes,
            "wait_positive": sum(v[10] > 0 for v in rows.values()),
            "path_flows": flows, "path_alternate": alternate,
            "path_multipath_packets": multipath,
            "background": [{"id": fid, "finish_ns": v[9], "total_ns": v[11]}
                           for fid, v in sorted(rows.items()) if v[5] == 1],
            "rows": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--trace", type=Path, default=Path("config/ws18_1280_correctness.txt"))
    parser.add_argument("--topology", type=Path,
                        default=Path("config/topo_1280_400G_400G_OS1.txt"))
    parser.add_argument("--legacy", required=True)
    for name, _, _ in ARMS:
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    expected = {"trace": args.trace, "topology": args.topology,
                "rows": trace_rows(args.trace)}
    arms = {name: read_arm(args.results, getattr(args, name), expected, a, p)
            for name, a, p in ARMS}
    shas = {value["source_sha"] for value in arms.values()}
    assert len(shas) == 1
    assert arms["admission"]["wait_positive"] > 0
    assert arms["joint"]["wait_positive"] > 0
    assert arms["ecmp"]["wait_positive"] == arms["path"]["wait_positive"] == 0
    for name in ("admission", "path", "joint"):
        for fid, row in arms[name]["rows"].items():
            base = arms["ecmp"]["rows"][fid]
            assert (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]) == base[:8]
            if name == "path":
                assert row[8] == base[8]
    legacy_base = args.results / args.legacy
    meta = json.loads((legacy_base / "metadata.json").read_text())
    assert meta["parameters"]["lb"] == "fecmp" and meta["git_commit"] in shas
    legacy_raw_id = str(meta["raw_directory"])
    legacy = legacy_base / "raw" / legacy_raw_id / (legacy_raw_id + "_out_fct.txt")
    assert digest(legacy) == arms["ecmp"]["fct_sha256"]
    summary = {name: {k: v for k, v in value.items() if k != "rows"}
               for name, value in arms.items()}
    summary["legacy"] = {"experiment_id": args.legacy, "fct_sha256": digest(legacy)}
    summary["trace_sha256"] = digest(args.trace)
    summary["topology_sha256"] = digest(args.topology)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
