#!/usr/bin/env python3
"""Verify generated WS-24 graph, NIC, placement and flow input contracts."""

import hashlib
import json
from collections import Counter, deque
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def graph(name):
    rows = (CONFIG / name).read_text(encoding='ascii').splitlines()
    nodes, switches, links = map(int, rows[0].split())
    switch_ids = set(map(int, rows[1].split()))
    assert len(switch_ids) == switches
    assert len(rows) - 2 == links
    adjacent = [set() for _ in range(nodes)]
    link_rows = []
    for row in rows[2:]:
        a, b, *_ = row.split()
        a, b = int(a), int(b)
        assert a != b and 0 <= a < nodes and 0 <= b < nodes
        assert b not in adjacent[a]
        adjacent[a].add(b)
        adjacent[b].add(a)
        link_rows.append((a, b))
    components = {}
    for start in sorted(switch_ids):
        if start in components:
            continue
        component = len(set(components.values()))
        pending = deque([start])
        components[start] = component
        while pending:
            now = pending.popleft()
            for peer in adjacent[now] & switch_ids:
                if peer not in components:
                    components[peer] = component
                    pending.append(peer)
    assert len(set(components.values())) == 4
    return nodes, switch_ids, adjacent, link_rows, components


def topology_contract(name, expected_nodes, expected_switches, expected_links,
                      fast_delay_ns, expected_max_rtt_ns):
    rows = (CONFIG / name).read_text(encoding='ascii').splitlines()
    nodes, switches, links = map(int, rows[0].split())
    assert (nodes, switches, links) == (expected_nodes, expected_switches, expected_links)
    host_count = nodes - switches
    switch_ids = set(map(int, rows[1].split()))
    assert switch_ids == set(range(host_count, nodes))
    assert len(rows) == links + 2
    adjacency = [[] for _ in range(nodes)]
    seen = set()
    for row in rows[2:]:
        src_text, dst_text, rate, delay_text, error_text = row.split()
        src, dst = int(src_text), int(dst_text)
        assert 0 <= src < nodes and 0 <= dst < nodes and src != dst
        edge = tuple(sorted((src, dst)))
        assert edge not in seen
        seen.add(edge)
        low, high = edge
        if expected_links == 8:
            assert low < 2 and high >= 2
            expected_delay = 100
        else:
            fast_edge = ((low < 320 and 320 <= high < 480) or
                         (320 <= low < 480 and 480 <= high < 640))
            slow_edge = 480 <= low < 640 and high >= 640
            assert fast_edge or slow_edge
            expected_delay = fast_delay_ns if fast_edge else 100
        assert rate == '400Gbps' and delay_text == '%dns' % expected_delay
        assert float(error_text) == 0.0
        adjacency[src].append((dst, expected_delay))
        adjacency[dst].append((src, expected_delay))
    max_rtt_ns = 0
    for source in range(host_count):
        pending = deque([(source, 0, 0)])
        visited = {source}
        while pending:
            current, hops, delay_ns = pending.popleft()
            if current < host_count and current != source:
                max_rtt_ns = max(max_rtt_ns, 2 * delay_ns + 20 * hops)
                continue  # hosts cannot be fabric transit vertices
            for peer, edge_delay in adjacency[current]:
                if peer not in visited:
                    visited.add(peer)
                    pending.append((peer, hops + 1, delay_ns + edge_delay))
    assert max_rtt_ns == expected_max_rtt_ns
    return max_rtt_ns, max_rtt_ns * 50  # 400 Gbps / 8 in bytes/ns


def nics(name, host_count, adjacent, links, components):
    rows = (CONFIG / name).read_text(encoding='ascii').splitlines()
    assert int(rows[0]) == host_count * 4 and len(rows) - 1 == host_count * 4
    expected_order = Counter()
    for a, b in links:
        if a < host_count:
            expected_order[a] += 1
        elif b < host_count:
            expected_order[b] += 1
    assert all(expected_order[h] == 4 for h in range(host_count))
    result = {}
    ips = set()
    for row in rows[1:]:
        host, rail, ip, peer, interface, legacy = row.split()
        host, rail, peer, interface, legacy = map(int, (host, rail, peer, interface, legacy))
        assert host < host_count and rail in range(4)
        assert interface == rail + 1 and legacy == 4 * host + rail
        assert peer in adjacent[host] and peer in components
        assert (host, rail) not in result and ip not in ips
        result[host, rail] = (ip, peer, interface, legacy)
        ips.add(ip)
    assert len(result) == host_count * 4
    for host in range(host_count):
        assert len({components[result[host, rail][1]] for rail in range(4)}) == 4
    return result


def flow_rows(name, nic_map):
    rows = (CONFIG / name).read_text(encoding='ascii').splitlines()
    assert int(rows[0]) == len(rows) - 1
    flows = []
    previous_ns = -1
    seen_ids = set()
    ranks = {}
    for row in rows[1:]:
        values = tuple(map(int, row.split()))
        assert len(values) == 12
        (flow_id, job, srank, drank, src, dst, src_rail, dst_rail,
         pg, size, demand_ns, tag) = values
        assert src_rail == dst_rail
        assert flow_id not in seen_ids and (src, src_rail) in nic_map and (dst, dst_rail) in nic_map
        assert src != dst and srank != drank and 0 <= pg < 8 and size > 0
        assert demand_ns >= previous_ns
        for rank, host in ((srank, src), (drank, dst)):
            key = (job, rank)
            assert key not in ranks or ranks[key] == host
            ranks[key] = host
        previous_ns = demand_ns
        seen_ids.add(flow_id)
        flows.append(values)
    return flows


def main():
    manifest_path = CONFIG / 'ws24_synthetic_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for filename, digest in manifest['files_sha256'].items():
        assert sha(CONFIG / filename) == digest, filename
    assert sha(CONFIG / 'topo_1280_400G_400G_OS1.txt') == manifest['source_topology_sha256']
    target_rtt, target_bdp = topology_contract(
        'ws24_synthetic_320host_4nic_topology.txt', 896, 576, 3840, 10, 600)
    minimal_rtt, minimal_bdp = topology_contract(
        'ws24_synthetic_2host_4nic_topology.txt', 6, 4, 8, 100, 440)
    _, _, target_adj, target_links, target_components = graph(
        'ws24_synthetic_320host_4nic_topology.txt')
    target_nics = nics('ws24_synthetic_320host_4nic_nics.txt', 320,
                       target_adj, target_links, target_components)
    _, _, min_adj, min_links, min_components = graph('ws24_synthetic_2host_4nic_topology.txt')
    min_nics = nics('ws24_synthetic_2host_4nic_nics.txt', 2,
                    min_adj, min_links, min_components)
    minimal = flow_rows('ws24_synthetic_2host_4nic_flows.txt', min_nics)
    assert len(minimal) == 4 and {row[6] for row in minimal} == {0, 1, 2, 3}
    invalid = (CONFIG / 'ws24_synthetic_2host_crossrail_reject.txt').read_text(
        encoding='ascii').splitlines()
    assert invalid[0] == '1' and len(invalid) == 2
    rejected = tuple(map(int, invalid[1].split()))
    assert len(rejected) == 12 and rejected[6] != rejected[7]
    demands = None
    totals = {}
    for placement in ('fixed', 'variable'):
        for policy in ('single', 'multi'):
            name = placement + '_' + policy
            flows = flow_rows('ws24_synthetic_' + name + '_flows.txt', target_nics)
            assert len(flows) == 10
            logical = {row[0]: (row[1], row[2], row[3], row[8], row[9], row[10], row[11])
                       for row in flows}
            assert len(logical) == 10
            if demands is None:
                demands = logical
            assert logical == demands
            assert {row[6] for row in flows} == ({0} if policy == 'single' else {0, 1, 2, 3})
            totals[name] = sum(row[9] for row in flows)
    assert set(totals.values()) == {manifest['logical_bytes_per_arm']} == {2408448}
    print(json.dumps({'status': 'offline_input_verified', 'manifest_sha256': sha(manifest_path),
                      'target_nics': len(target_nics), 'minimal_nics': len(min_nics),
                      'minimal_flows': len(minimal), 'arm_bytes': totals,
                      'minimal_max_rtt_ns': minimal_rtt, 'minimal_max_bdp_bytes': minimal_bdp,
                      'target_max_rtt_ns': target_rtt, 'target_max_bdp_bytes': target_bdp},
                     sort_keys=True))


if __name__ == '__main__':
    main()
