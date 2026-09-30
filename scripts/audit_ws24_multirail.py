#!/usr/bin/env python3
"""Audit OS1 rail structure and a deliberately synthetic placement contract.

This does not run ns-3 or establish physical server identity. The synthetic
mapping checks that a proposed sidecar can be validated before simulator work.
"""

import hashlib
import json
from collections import Counter, deque
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = ROOT / "config/topo_1280_400G_400G_OS1.txt"


def load_topology(path):
    raw = path.read_bytes()
    lines = raw.decode("ascii").splitlines()
    node_count, switch_count, link_count = map(int, lines[0].split())
    switches = set(map(int, lines[1].split()))
    assert len(switches) == switch_count
    assert len(lines) == link_count + 2
    neighbors = [set() for _ in range(node_count)]
    for line in lines[2:]:
        a, b, rate, delay, loss = line.split()
        a, b = int(a), int(b)
        assert 0 <= a < node_count and 0 <= b < node_count and a != b
        assert b not in neighbors[a]
        assert rate == "400Gbps" and loss == "0.0"
        assert delay in ("10ns", "100ns")
        neighbors[a].add(b)
        neighbors[b].add(a)
    components = [-1] * node_count
    sizes = []
    for start in range(node_count):
        if components[start] != -1:
            continue
        component = len(sizes)
        pending = deque([start])
        components[start] = component
        size = 0
        while pending:
            node = pending.popleft()
            size += 1
            for other in neighbors[node]:
                if components[other] == -1:
                    components[other] = component
                    pending.append(other)
        sizes.append(size)
    hosts = set(range(node_count)) - switches
    assert hosts == set(range(1280))
    assert all(len(neighbors[host]) == 1 for host in hosts)
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "node_count": node_count,
        "switch_count": switch_count,
        "link_count": link_count,
        "hosts": hosts,
        "components": components,
        "component_sizes": sizes,
    }


def validate_contract(topology, endpoints, placements, flows):
    """Return resolved endpoint pairs; reject unsupported or ambiguous mapping."""
    components = topology["components"]
    hosts = topology["hosts"]
    by_host_rail = {}
    used_endpoints = set()
    for physical_host, rail, endpoint in endpoints:
        key = (physical_host, rail)
        if key in by_host_rail or endpoint in used_endpoints or endpoint not in hosts:
            raise ValueError("duplicate or invalid host/NIC endpoint")
        by_host_rail[key] = endpoint
        used_endpoints.add(endpoint)
    for physical_host in {item[0] for item in endpoints}:
        rails = {rail: by_host_rail[(physical_host, rail)] for rail in range(4)
                 if (physical_host, rail) in by_host_rail}
        if len(rails) != 4 or len({components[node] for node in rails.values()}) != 4:
            raise ValueError("physical host lacks four distinct rail components")
    rank_to_host = {}
    for job, rank, physical_host in placements:
        key = (job, rank)
        if key in rank_to_host:
            raise ValueError("ambiguous rank placement")
        if (physical_host, 0) not in by_host_rail:
            raise ValueError("placement references unknown physical host")
        rank_to_host[key] = physical_host
    resolved = []
    flow_ids = set()
    for job, flow_id, src_rank, dst_rank, src_rail, dst_rail in flows:
        if (job, flow_id) in flow_ids or src_rail != dst_rail:
            raise ValueError("duplicate flow identity or unsupported cross-rail flow")
        flow_ids.add((job, flow_id))
        try:
            src = by_host_rail[(rank_to_host[(job, src_rank)], src_rail)]
            dst = by_host_rail[(rank_to_host[(job, dst_rank)], dst_rail)]
        except KeyError as exc:
            raise ValueError("flow has no rank or rail endpoint") from exc
        if src == dst or components[src] != components[dst]:
            raise ValueError("flow endpoints have no same-rail path")
        resolved.append((src, dst, src_rail))
    return resolved


def expect_rejection(fn):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError("invalid contract was accepted")


def main():
    topology = load_topology(TOPOLOGY)
    components = topology["components"]
    hosts = topology["hosts"]
    counts = Counter(components[node] for node in hosts)
    assert topology["sha256"] == "74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba"
    assert sorted(topology["component_sizes"]) == [464] * 4
    assert sorted(counts.values()) == [320] * 4
    assert all(components[host] == components[host % 4] for host in hosts)

    # Purely hypothetical grouping. No imported topology or workload record
    # says that endpoint IDs 4*h+r belong to one physical server.
    endpoints = [(host, rail, 4 * host + rail)
                 for host in range(320) for rail in range(4)]
    placements = [("fixture-job", 0, 0), ("fixture-job", 1, 4)]
    flows = [("fixture-job", rail, 0, 1, rail, rail) for rail in range(4)]
    resolved = validate_contract(topology, endpoints, placements, flows)
    assert resolved == [(rail, 16 + rail, rail) for rail in range(4)]
    expect_rejection(lambda: validate_contract(
        topology, endpoints + [(0, 0, 32)], placements, flows))
    expect_rejection(lambda: validate_contract(
        topology, endpoints, placements + [("fixture-job", 0, 8)], flows))
    expect_rejection(lambda: validate_contract(
        topology, endpoints, placements, flows + [("fixture-job", 4, 0, 2, 0, 0)]))
    expect_rejection(lambda: validate_contract(
        topology, endpoints, placements, flows + [("fixture-job", 4, 0, 1, 0, 1)]))
    # A cross-rail endpoint pair cannot be made reachable by labelling alone.
    assert components[0] != components[17]

    result = {
        "evidence_level": "local static structure and synthetic contract fixture only",
        "topology_sha256": topology["sha256"],
        "nodes": topology["node_count"],
        "switches": topology["switch_count"],
        "links": topology["link_count"],
        "components": len(topology["component_sizes"]),
        "component_sizes": sorted(topology["component_sizes"]),
        "hosts_per_component": sorted(counts.values()),
        "synthetic_physical_hosts": 320,
        "synthetic_resolved_flows": [list(row) for row in resolved],
        "cross_rail_network_path": False,
        "physical_identity_verified": False,
        "simulator_multinic_verified": False,
        "placement_source_verified": False,
        "remote_simulation_go": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
