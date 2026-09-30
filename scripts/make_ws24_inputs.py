#!/usr/bin/env python3
"""Generate explicitly synthetic WS-24 multi-NIC fixtures from the imported OS1 graph.

The imported topology was matched edge for edge to maplerime/conweave-ns3
config/gen_moe_topology.py at 470c58026ec3933eabb6667bf3124b6b9bd401be.
No physical deployment or job trace is inferred from that source.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
SOURCE = CONFIG / "topo_1280_400G_400G_OS1.txt"
SOURCE_SHA = "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
PLACEMENTS = {
    "fixed": (0, 8, 64, 72),
    "variable": (0, 64, 8, 72),
}
PAIRS = ((0, 1), (0, 2), (1, 3), (2, 3))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_lf(path, content, encoding='ascii'):
    with path.open('w', encoding=encoding, newline='\n') as handle:
        handle.write(content)


def endpoint_ip(endpoint):
    address = 0x0B000001 + (endpoint // 256) * 0x10000 + (endpoint % 256) * 0x100
    return ".".join(str((address >> shift) & 255) for shift in (24, 16, 8, 0))


def write_topology():
    assert sha(SOURCE) == SOURCE_SHA, "imported source topology changed"
    original = SOURCE.read_text(encoding="ascii").splitlines()
    assert tuple(map(int, original[0].split())) == (1856, 576, 3840)
    assert set(map(int, original[1].split())) == set(range(1280, 1856))
    lines = original[2:]
    assert len(lines) == 3840
    output = ["896 576 3840", " ".join(map(str, range(320, 896)))]
    nic_rows = []
    count = Counter()
    for line in lines:
        parts = line.split()
        a, b = map(int, parts[:2])
        new_a = a // 4 if a < 1280 else a - 960
        new_b = b // 4 if b < 1280 else b - 960
        output.append(" ".join((str(new_a), str(new_b)) + tuple(parts[2:])))
        if a < 1280 or b < 1280:
            endpoint = a if a < 1280 else b
            switch = b if a < 1280 else a
            host, rail = divmod(endpoint, 4)
            count[host] += 1
            nic_rows.append((host, rail, endpoint_ip(endpoint), switch - 960,
                             count[host], endpoint))
    assert len(nic_rows) == 1280
    assert all(count[host] == 4 for host in range(320))
    assert len({row[2] for row in nic_rows}) == 1280
    assert all([row[1] for row in nic_rows if row[0] == host] == [0, 1, 2, 3]
               for host in range(320))
    topology = CONFIG / "ws24_synthetic_320host_4nic_topology.txt"
    nic_file = CONFIG / "ws24_synthetic_320host_4nic_nics.txt"
    write_lf(topology, "\n".join(output) + "\n")
    write_lf(nic_file, "1280\n" + "".join("%d %d %s %d %d %d\n" % row for row in nic_rows))
    return topology, nic_file


def write_minimal():
    topo = CONFIG / "ws24_synthetic_2host_4nic_topology.txt"
    nics = CONFIG / "ws24_synthetic_2host_4nic_nics.txt"
    lines = ["6 4 8", "2 3 4 5"]
    rows = []
    for host in range(2):
        for rail in range(4):
            switch = 2 + rail
            lines.append("%d %d 400Gbps 100ns 0" % (host, switch))
            rows.append((host, rail, endpoint_ip(4 * host + rail), switch,
                         1 + rail, 4 * host + rail))
    write_lf(topo, "\n".join(lines) + "\n")
    write_lf(nics, "8\n" + "".join("%d %d %s %d %d %d\n" % row for row in rows))
    minimal_flows = CONFIG / "ws24_synthetic_2host_4nic_flows.txt"
    records = [(rail, 0, 0, 1, 0, 1, rail, rail, 3, 8192, 2000000000, 2)
               for rail in range(4)]
    write_lf(minimal_flows, "4\n" + "".join(" ".join(map(str, row)) + "\n" for row in records))
    invalid = CONFIG / "ws24_synthetic_2host_crossrail_reject.txt"
    write_lf(invalid, "1\n0 0 0 1 0 1 0 1 3 8192 2000000000 2\n")
    return topo, nics, minimal_flows, invalid


def logical_demands():
    rows = []
    for flow_id in range(8):
        source, destination = PAIRS[flow_id % 4]
        rows.append((flow_id, 0, source, destination,
                     131072 if (source, destination) == (0, 1) else 8192,
                     2000000000 + (flow_id // 4) * 50000, 2))
    rows.extend(((8, 0, 1, 2, 1 << 20, 2000000000, 1),
                 (9, 0, 3, 0, 1 << 20, 2000000000, 1)))
    return rows


def write_arms():
    demands = logical_demands()
    assert len({row[0] for row in demands}) == 10
    assert sum(row[4] for row in demands) == 2408448
    files = {}
    for placement_name, hosts in PLACEMENTS.items():
        for rail_policy in ("single", "multi"):
            path = CONFIG / ("ws24_synthetic_%s_%s_flows.txt" % (placement_name, rail_policy))
            records = []
            for flow_id, job, source, destination, size, demand_ns, tag in demands:
                rail = 0 if rail_policy == "single" else flow_id % 4
                records.append((flow_id, job, source, destination, hosts[source],
                                hosts[destination], rail, rail, 3, size, demand_ns, tag))
            records.sort(key=lambda row: (row[10], row[0]))
            write_lf(path, "10\n" + "".join(" ".join(map(str, row)) + "\n" for row in records))
            files[placement_name + "_" + rail_policy] = path
    return files


def main():
    topology, nics = write_topology()
    min_topo, min_nics, min_flows, invalid_flows = write_minimal()
    arms = write_arms()
    manifest = {
        "schema_version": 1,
        "provenance": "synthetic fixture, not observed deployment or job trace",
        "reference_generator_commit": "470c58026ec3933eabb6667bf3124b6b9bd401be",
        "source_topology_sha256": SOURCE_SHA,
        "files_sha256": {path.name: sha(path) for path in
                         (topology, nics, min_topo, min_nics, min_flows,
                          invalid_flows, *arms.values())},
        "logical_flows_per_arm": 10,
        "logical_bytes_per_arm": 2408448,
        "physical_deployment_verified": False,
        "simulator_multinic_verified": False,
    }
    output = CONFIG / "ws24_synthetic_manifest.json"
    write_lf(output, json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding='utf-8')
    print(json.dumps({"manifest": str(output), "files": len(manifest["files_sha256"]),
                      "manifest_sha256": sha(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
