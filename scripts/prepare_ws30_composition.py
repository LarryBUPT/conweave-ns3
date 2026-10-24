"""Freeze actual-RDMA composition inputs; no remote calls or experiment launch."""
import collections
import json
from pathlib import Path

import run_ws30_stage2 as stage


def murmur(words, seed):
    mask = 0xffffffff
    rotate = lambda x, n: ((x << n) | (x >> (32 - n))) & mask
    for value in words:
        value = rotate(value * 0xcc9e2d51 & mask, 15) * 0x1b873593 & mask
        seed = (rotate(seed ^ value, 13) * 5 + 0xe6546b64) & mask
    seed ^= len(words) * 4
    seed ^= seed >> 16
    seed = seed * 0x85ebca6b & mask
    seed ^= seed >> 13
    seed = seed * 0xc2b2ae35 & mask
    return seed ^ (seed >> 16)


def generate():
    topology = '8 4 8\n4 5 6 7\n' + ''.join(
        '%d %d %dGbps 1000ns 0\n' % (a, b, rate)
        for a, b, rate in [(0,4,400),(1,5,400),(2,6,400),(3,7,400),
                           (4,5,40),(4,6,40),(5,7,40),(6,7,40)])
    topo = stage.ROOT / 'config/ws30_composition8.txt'
    if topo.exists(): assert topo.read_text() == topology
    else: topo.write_text(topology)
    # Four identical 32-KiB wire QPs precede the probe; this also fixes its
    # identity at sport=10004 without changing candidate salts or scores.
    words = [0x0b000001, 0x0b000301, 10004 | (100 << 16), 0]
    indices = [murmur(words, 4 ^ salt) % 2 for salt in [0, 0x9e3779b9]]
    assert indices == [0, 1]
    rows = []
    for continuing in [0, 1]:
        for swap in [0, 1]:
            flows = [(0, dst, 3, 31616, 2000000000, (1 if dst == 1 else 2) if not swap
                      else (2 if dst == 1 else 1)) for repeat in range(2) for dst in [1, 2]]
            flows.append((0, 3, 3, 16000, 2000020000, 2))
            if continuing:
                flows.extend((0, dst, 3, 8000, 2000022000 + repeat * 1000, 1)
                             for repeat in range(16) for dst in [1, 2])
            flows.sort(key=lambda row: row[4])
            text = str(len(flows)) + '\n' + ''.join(
                '%d %d %d %d %d.%09d %d\n' % (*f[:4], f[4]//10**9, f[4]%10**9, f[5])
                for f in flows)
            name = 'ws30_composition_swap%d_cont%d.txt' % (swap, continuing)
            path = stage.ROOT / 'config' / name
            if path.exists(): assert path.read_text() == text
            else: path.write_text(text)
            rows.append({'trace': name, 'trace_sha256': stage.sha(path),
                         'input_flows': len(flows), 'swap': swap, 'continuing': continuing,
                         'expected_tags': dict(collections.Counter(str(f[5]) for f in flows)),
                         'expected_background_by_port': {'2': 0 if swap else 65536,
                                                        '3': 65536 if swap else 0}})
    design = {
        'kind': 'WS-30 actual-enqueue composition fixture r1',
        'execution_enabled': False, 'topology': 'ws30_composition8',
        'topology_sha256': stage.sha(topo), 'traces': rows,
        'probe': {'src': 0, 'dst': 3, 'sport': 10004, 'dport': 100, 'bytes': 16000,
                  'start_ns': 2000020000, 'tag': 2, 'first': 2, 'second': 3},
        'hold_ns': 1999999000, 'release_ns': 2000022000,
        'wire_header_bytes': 36, 'payload_mtu': 1000,
        'prefill_qps_per_port': 2, 'prefill_payload_per_qp': 31616,
        'prefill_packets_per_qp': 32, 'wire_bytes_per_port': 65536,
        'output_bps': 40000000000, 'host_bps': 400000000000,
        'continuing_arrivals': {'qps_per_port': 16, 'payload_per_qp': 8000,
                                'start_ns': 2000022000, 'interval_ns': 1000},
        'arms': ['E', 'Q16', 'C16'], 'required_cells': 12,
        'interpretation': 'controlled scheduler hold; real RDMA QPs and real shared queues; no queue/score writes',
    }
    stage.frozen(stage.EV / 'ws30-composition-design-r1.json', design)
    return design


if __name__ == '__main__':
    data = generate()
    print(json.dumps({'traces': len(data['traces']), 'cells': data['required_cells'],
                      'wire_bytes_each_port': 65536, 'probe_candidates': [2, 3],
                      'execution_enabled': False}))
