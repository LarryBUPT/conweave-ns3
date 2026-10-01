#!/usr/bin/env python3
"""Deterministic, explicitly synthetic independent WS-24 job-demand blocks."""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config'
MASTER_SEED = 20261002
JOBS = tuple(range(1, 13))
ARMS = ('fixed_single', 'fixed_multi', 'variable_single', 'variable_multi')
HOST_POOL = (0, 8, 16, 24, 64, 72, 80, 88, 128, 136, 144, 152,
             192, 200, 208, 216)
SIZES = (8192, 8192, 65536, 131072, 262144, 1048576)
TOPOLOGY = 'ws24_synthetic_320host_4nic_topology.txt'
NICS = 'ws24_synthetic_320host_4nic_nics.txt'
MANIFEST = CONFIG / 'ws24_independent_manifest.json'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def draw(job, label, index, modulo):
    key = '{}|{}|{}|{}'.format(MASTER_SEED, job, label, index).encode('ascii')
    return int.from_bytes(hashlib.sha256(key).digest()[:8], 'big') % modulo


def hosts_for(job):
    ordered = sorted(HOST_POOL, key=lambda host: draw(job, 'host', host, 1 << 64))
    fixed = tuple(ordered[:4])
    return fixed, (fixed[0], fixed[2], fixed[1], fixed[3])


def demands_for(job):
    pairs = [(src, dst) for src in range(4) for dst in range(4) if src != dst]
    ordered = sorted(pairs, key=lambda pair: draw(job, 'pair', pair[0] * 4 + pair[1], 1 << 64))
    hot = draw(job, 'hot', 0, 4)
    demands = []
    for flow_id in range(30):
        if flow_id < 12:
            src, dst = ordered[flow_id]
        elif flow_id < 24:
            src, dst = pairs[draw(job, 'extra_pair', flow_id, len(pairs))]
        else:
            dst = hot
            src = [rank for rank in range(4) if rank != hot][draw(job, 'incast_src', flow_id, 3)]
        size = SIZES[draw(job, 'size', flow_id, len(SIZES))]
        demand_ns = 2000000000 + (flow_id // 10) * 30000 + draw(job, 'jitter', flow_id, 5000)
        tag = 1 if size >= 1048576 else 2
        demands.append((flow_id, job, src, dst, size, demand_ns, tag))
    return sorted(demands, key=lambda row: (row[5], row[0]))


def flow_name(job, arm):
    return 'ws24_synthetic_independent_j{:02d}_{}_flows.txt'.format(job, arm)


def experiment_id(job, arm):
    if job == 1 and arm == 'fixed_single':
        # First attempt met the flow contract but lacked the required resource watcher.
        return '20261002-180000-ws24-ind-j01-fs-r2'
    short = {'fixed_single': 'fs', 'fixed_multi': 'fm',
             'variable_single': 'vs', 'variable_multi': 'vm'}[arm]
    return '20261002-180000-ws24-ind-j{:02d}-{}'.format(job, short)


def build():
    topology_sha = sha((CONFIG / TOPOLOGY).read_bytes())
    nic_sha = sha((CONFIG / NICS).read_bytes())
    assert topology_sha == 'e82f742a1f07749de63706c94c29b3275ec908c61a967f6336988526213bf6fa'
    assert nic_sha == '4a4bc61466efd15983bf6a6e7a3e69e153cb00760f909a98311d1f9c17481202'
    files = {}
    jobs = {}
    ids = {}
    for job in JOBS:
        fixed, variable = hosts_for(job)
        demands = demands_for(job)
        logical = '\n'.join(' '.join(map(str, row)) for row in demands) + '\n'
        totals = sum(row[4] for row in demands)
        jobs['j{:02d}'.format(job)] = {
            'generation_seed': '{}|{}'.format(MASTER_SEED, job),
            'fixed_hosts_by_rank': list(fixed),
            'variable_hosts_by_rank': list(variable),
            'logical_sha256': sha(logical.encode('ascii')),
            'flows': len(demands), 'bytes': totals,
        }
        for arm in ARMS:
            placement, policy = arm.split('_')
            hosts = fixed if placement == 'fixed' else variable
            rows = []
            for flow_id, _, src_rank, dst_rank, size, demand_ns, tag in demands:
                rail = 0 if policy == 'single' else flow_id % 4
                rows.append((flow_id, job, src_rank, dst_rank,
                             hosts[src_rank], hosts[dst_rank], rail, rail,
                             3, size, demand_ns, tag))
            name = flow_name(job, arm)
            data = (str(len(rows)) + '\n' +
                    ''.join(' '.join(map(str, row)) + '\n' for row in rows)).encode('ascii')
            files[name] = data
            ids['j{:02d}_{}'.format(job, arm)] = experiment_id(job, arm)
    assert len({record['logical_sha256'] for record in jobs.values()}) == len(JOBS)
    assert len({tuple(record['fixed_hosts_by_rank']) for record in jobs.values()}) == len(JOBS)
    order = sorted(ids, key=lambda key: draw(0, 'run_order_' + key, 0, 1 << 64))
    manifest = {
        'schema_version': 1,
        'provenance': 'independent seeded ns-3 synthetic job demands; no deployment observations',
        'master_seed': MASTER_SEED,
        'ns3_seed': 1,
        'job_count': len(JOBS), 'arms_per_job': list(ARMS),
        'topology_file': TOPOLOGY, 'topology_sha256': topology_sha,
        'nic_file': NICS, 'nic_sha256': nic_sha,
        'flow_files_sha256': {name: sha(data) for name, data in sorted(files.items())},
        'jobs': jobs, 'experiment_ids': ids, 'run_order': order,
        'superseded_attempts': {
            '20261002-180000-ws24-ind-j01-fs': {
                'replacement': ids['j01_fixed_single'],
                'reason': 'resource watcher was not started before run; raw retained as correctness-only preflight',
            }
        },
    }
    manifest_data = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode('utf-8')
    return files, manifest_data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='compare generated bytes without writing')
    args = parser.parse_args()
    files, manifest_data = build()
    for name, data in files.items():
        path = CONFIG / name
        if args.check:
            assert path.read_bytes() == data, name
        else:
            path.write_bytes(data)
    if args.check:
        assert MANIFEST.read_bytes() == manifest_data
    else:
        MANIFEST.write_bytes(manifest_data)
    print(json.dumps({'status': 'verified' if args.check else 'generated',
                      'job_blocks': len(JOBS), 'arm_files': len(files),
                      'manifest_sha256': sha(manifest_data)}, sort_keys=True))


if __name__ == '__main__':
    main()
