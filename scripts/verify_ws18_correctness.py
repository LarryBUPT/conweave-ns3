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


def config_values(path):
    return dict(line.split(None, 1) for line in path.read_text().splitlines()
                if len(line.split(None, 1)) == 2)


def common_config(base, mode, admission=0, path=0):
    config = config_values(base / "config" / "config.txt")
    assert config["CC_MODE"] == "1"
    assert config["LB_MODE"] == str(mode)
    assert config["ENABLE_PFC"] == "0" and config["ENABLE_IRN"] == "1"
    assert config["RANDOM_SEED"] == "1"
    if mode == 20:
        assert config["WS18_ADMISSION"] == str(admission)
        assert config["WS18_PATH"] == str(path)
        assert config["WS18_ADMISSION_RATE_GBPS"] == "400"


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
    common_config(base, 20, admission, path)
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
        assert (src, dst, size, demand, tag) == expected["rows"][fid], (experiment_id, fid)
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
    log = (raw / "config.log").read_text(errors="replace")
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
    parser.add_argument("--legacy-reference", required=True,
                        help="earlier same-trace fecmp result for exact old-mode regression")
    for name, _, _ in ARMS:
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    expected = {"trace": args.trace, "topology": args.topology,
                "rows": trace_rows(args.trace)}
    topo_lines = args.topology.read_text().splitlines()
    host_count = int(topo_lines[0].split()[0]) - int(topo_lines[0].split()[1])
    host_tor = {int(fields[0]): int(fields[1]) for fields in
                (line.split() for line in topo_lines[2:]) if int(fields[0]) < host_count}
    assert len(host_tor) == host_count
    assert all((host_tor[src] - host_count) // 8 ==
               (host_tor[dst] - host_count) // 8
               for src, dst, _, _, _ in expected["rows"]), "Cross-rail flow in correctness trace"
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
    assert meta["status"] == "SUCCEEDED" and meta["git_commit"] in shas
    legacy_params = meta["parameters"]
    assert legacy_params["lb"] == "fecmp"
    assert int(legacy_params["pfc"]) == 0 and int(legacy_params["irn"]) == 1
    assert legacy_params["topo"] == "topo_1280_400G_400G_OS1"
    assert legacy_params["flow_file"] == args.trace.name
    common_config(legacy_base, 0)
    assert digest(legacy_base / "config" / "traffic_trace.txt") == digest(args.trace)
    assert digest(legacy_base / "config" / "topology.txt") == digest(args.topology)
    legacy_raw_id = str(meta["raw_directory"])
    legacy = legacy_base / "raw" / legacy_raw_id / (legacy_raw_id + "_out_fct.txt")
    reference_base = args.results / args.legacy_reference
    reference_meta = json.loads((reference_base / "metadata.json").read_text())
    assert reference_meta["status"] == "SUCCEEDED"
    assert reference_meta["parameters"]["lb"] == "fecmp"
    assert reference_meta["parameters"]["flow_file"] == args.trace.name
    common_config(reference_base, 0)
    assert digest(reference_base / "config" / "traffic_trace.txt") == digest(args.trace)
    assert digest(reference_base / "config" / "topology.txt") == digest(args.topology)
    reference_raw_id = str(reference_meta["raw_directory"])
    reference = (reference_base / "raw" / reference_raw_id /
                 (reference_raw_id + "_out_fct.txt"))
    assert digest(legacy) == digest(reference)
    summary = {name: {k: v for k, v in value.items() if k != "rows"}
               for name, value in arms.items()}
    summary["legacy"] = {"experiment_id": args.legacy,
                         "source_sha": meta["git_commit"],
                         "fct_sha256": digest(legacy),
                         "reference_id": args.legacy_reference,
                         "reference_source_sha": reference_meta["git_commit"],
                         "reference_fct_sha256": digest(reference)}
    summary["trace_sha256"] = digest(args.trace)
    summary["topology_sha256"] = digest(args.topology)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
