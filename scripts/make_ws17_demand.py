#!/usr/bin/env python3
"""Rebuild WS-17 independent demand assets; never run a simulation.

Each seed redraws membership, background sources and destinations, and the
hotspot. Two topology treatments share that seed's demand skeleton but are
not independent statistical replicates. Outputs live in ignored results/.
"""
import argparse
import hashlib
import json
import random
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = ROOT / 'config/topo_1280_400G_400G_OS1.txt'
OUT = ROOT / 'results/ws17-demand'
MANIFEST = ROOT / 'docs/research/evidence/ws17-demand-manifest.json'
SEEDS = (20261701, 20261702, 20261703)
HOSTS = tuple(range(0, 1280, 4))  # rail 0, as in the imported workload
ROUND_COUNT = 8
PER_SOURCE_ROUND = 8
ROUND_NS = 50000
START_NS = 2000000000
MOE_BYTES = 8192
BACKGROUND_BYTES = 8 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def render(obj):
    return (json.dumps(obj, indent=2, sort_keys=True) + '\n').encode('utf-8')


def save_exact(path, data, verify):
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError('Existing file differs: ' + str(path))
    elif verify:
        raise ValueError('Missing asset: ' + str(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def topology():
    lines = TOPOLOGY.read_text(encoding='utf-8').splitlines()
    count = tuple(map(int, lines[0].split()))
    assert count == (1856, 576, 3840)
    links = [line.split() for line in lines[2:]]
    assert len(links) == count[2]
    neighbors = {i: [] for i in range(count[0])}
    for a, b, rate, delay, error in links:
        a, b = int(a), int(b)
        assert rate == '400Gbps' and error == '0.0'
        assert delay in ('10ns', '100ns')
        if min(a, b) < 1280:
            assert delay == '10ns'
        neighbors[a].append(b)
        neighbors[b].append(a)
    assert all(len(neighbors[h]) == 1 for h in range(1280))
    return neighbors


def route_audit(src, dst, neighbors):
    distance = {dst: 0}
    pending = deque([dst])
    while pending:
        node = pending.popleft()
        for next_node in neighbors[node]:
            if next_node not in distance:
                distance[next_node] = distance[node] + 1
                if next_node >= 1280:
                    pending.append(next_node)
    source_tor, destination_tor = neighbors[src][0], neighbors[dst][0]
    return {'sample_source': src, 'source_tor': source_tor,
            'destination': dst, 'destination_tor': destination_tor,
            'source_tor_shortest_next_hops': sum(distance.get(n) == distance[source_tor] - 1
                                                  for n in neighbors[source_tor]),
            'destination_tor_shortest_next_hops': sum(distance.get(n) == distance[destination_tor] - 1
                                                       for n in neighbors[destination_tor]),
            'destination_host_degree': len(neighbors[dst])}


def one_seed(seed, neighbors, verify):
    rng = random.Random(seed)
    experts = sorted(rng.sample(HOSTS, 256))
    expert_set = set(experts)
    background_sources = sorted(set(HOSTS) - expert_set)
    eligible_tors = sorted({neighbors[h][0] for h in experts
                            if sum(neighbors[x][0] == neighbors[h][0] for x in experts) >= 4})
    hot_tor = rng.choice(eligible_tors)
    hot_hosts = sorted(h for h in experts if neighbors[h][0] == hot_tor)
    hot_host = rng.choice(hot_hosts)
    sample_source = next(h for h in experts if neighbors[h][0] != hot_tor)

    # Draw one independent demand skeleton per seed; topology treatments
    # reuse it as a paired contrast, so they must not count as two repeats.
    skeleton = []
    for round_id in range(ROUND_COUNT):
        for src in experts:
            ordinary = rng.sample([h for h in experts if h != src], 6)
            for slot in range(PER_SOURCE_ROUND):
                ordinary_dst = ordinary[slot - 2] if slot >= 2 else None
                tor_dst = rng.choice([h for h in hot_hosts if h != src])
                skeleton.append((round_id, src, slot, ordinary_dst, tor_dst))
    bg_sources = [rng.choice(background_sources) for _ in range(192)]
    bg_ordinary = [rng.choice([h for h in experts if h != src])
                   for src in bg_sources]
    bg_tor = [rng.choice(hot_hosts) for _ in range(192)]

    records = []
    for treatment in ('host_hotspot', 'tor_hotspot'):
        items = []
        for i, (src, ordinary_dst, tor_dst) in enumerate(zip(bg_sources, bg_ordinary, bg_tor)):
            dst = (hot_host if treatment == 'host_hotspot' else tor_dst) if i % 4 == 0 else ordinary_dst
            if src == dst:  # different source pool makes this impossible
                raise AssertionError('Background self flow')
            items.append((START_NS, 1, src, dst, BACKGROUND_BYTES, -1, i % 4 == 0))
        for round_id, src, slot, ordinary_dst, tor_dst in skeleton:
            dst = (hot_host if treatment == 'host_hotspot' else tor_dst) if slot < 2 else ordinary_dst
            if src == dst:
                # A source located at the hotspot cannot send to itself.
                dst = rng.choice([h for h in hot_hosts if h != src])
            items.append((START_NS + round_id * ROUND_NS, 2, src, dst, MOE_BYTES,
                          round_id, slot < 2))
        # Stable tie order is part of the trace contract; source/destination
        # ports follow this order in ScheduleFlowInputs.
        items.sort(key=lambda x: x[0])
        moe_reference = None
        for bg_count in (0, 192):
            selected = [x for x in items if x[1] == 2 or (bg_count and x[1] == 1)]
            assert len(selected) == 16384 + bg_count
            assert all(x[2] != x[3] for x in selected)
            lines = [str(len(selected)) + '\n']
            sidecar = []
            sports, dports = {}, {}
            for index, (ns, tag, src, dst, size, round_id, hot) in enumerate(selected):
                lines.append(f'{src} {dst} 3 {size} {ns // 1000000000}.{ns % 1000000000:09d} {tag}\n')
                sport = sports.get(src, 10000)
                dport = dports.get(dst, 100)
                sports[src] = sport + 1
                dports[dst] = dport + 1
                sidecar.append({'flow_index': index, 'demand_ns': ns, 'src': src,
                                'dst': dst, 'sport': sport, 'dport': dport,
                                'bytes': size, 'tag': tag,
                                'round': round_id, 'hotspot': hot})
            moe_lines = [line for line in lines[1:] if line.endswith(' 2\n')]
            if moe_reference is None:
                moe_reference = moe_lines
            else:
                assert moe_lines == moe_reference, 'Background addition changed MoE demand'
            basename = f'ws17_seed{seed}_{treatment}_b{bg_count}'
            trace = ''.join(lines).encode('ascii')
            demand = render({'seed': seed, 'treatment': treatment,
                             'background_flows': bg_count, 'flows': sidecar})
            save_exact(OUT / (basename + '.txt'), trace, verify)
            save_exact(OUT / (basename + '.demand.json'), demand, verify)
            records.append({'seed': seed, 'treatment': treatment, 'background_flows': bg_count,
                            'trace': basename + '.txt', 'trace_sha256': digest(trace),
                            'demand': basename + '.demand.json', 'demand_sha256': digest(demand),
                            'flows': len(selected), 'moe_flows': 16384,
                            'background_bytes': bg_count * BACKGROUND_BYTES,
                            'moe_bytes': 16384 * MOE_BYTES})
    return {'seed': seed, 'expert_membership_sha256': digest(render(experts)),
            'background_sources_sha256': digest(render(bg_sources)),
            'hot_tor': hot_tor, 'hot_host': hot_host, 'hot_hosts': hot_hosts,
            'route_audit': route_audit(sample_source, hot_host, neighbors),
            'records': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    neighbors = topology()
    seeds = [one_seed(seed, neighbors, args.verify) for seed in SEEDS]
    manifest = {'role': 'design-and-static-audit-only; not simulation evidence',
                'generator': 'scripts/make_ws17_demand.py',
                'topology_sha256': digest(TOPOLOGY.read_bytes()),
                'simulator_seed_for_future_pairing': 1,
                'sampling_unit': 'one independently redrawn seed; treatments/background levels are paired within seed',
                'round_count': ROUND_COUNT, 'round_gap_ns': ROUND_NS,
                'first_demand_ns': START_NS, 'seeds': seeds}
    save_exact(MANIFEST, render(manifest), args.verify)
    if args.verify:
        for seed in seeds:
            for record in seed['records']:
                assert digest((OUT / record['trace']).read_bytes()) == record['trace_sha256']
                assert digest((OUT / record['demand']).read_bytes()) == record['demand_sha256']
    print(json.dumps({'verified': args.verify, 'independent_seeds': len(seeds),
                      'paired_trace_assets': sum(len(s['records']) for s in seeds),
                      'manifest_sha256': digest(render(manifest))}))


if __name__ == '__main__':
    main()
