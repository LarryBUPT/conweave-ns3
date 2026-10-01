#!/usr/bin/env python3
"""Audit frozen synthetic job blocks, four-arm pairing and rail reachability."""

import hashlib
import json
from pathlib import Path

from verify_ws24_inputs import CONFIG, flow_rows, graph, nics, sha


MANIFEST = CONFIG / 'ws24_independent_manifest.json'


def main():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    assert manifest['schema_version'] == 1 and manifest['job_count'] == 12
    assert manifest['provenance'].startswith('independent seeded ns-3 synthetic')
    assert manifest['master_seed'] == 20261002 and manifest['ns3_seed'] == 1
    assert sha(CONFIG / manifest['topology_file']) == manifest['topology_sha256']
    assert sha(CONFIG / manifest['nic_file']) == manifest['nic_sha256']
    _, _, adjacent, links, components = graph(manifest['topology_file'])
    nic_map = nics(manifest['nic_file'], 320, adjacent, links, components)
    assert len(nic_map) == 1280
    assert len(manifest['flow_files_sha256']) == 48
    assert len(manifest['experiment_ids']) == len(set(manifest['experiment_ids'].values())) == 48
    assert set(manifest['run_order']) == set(manifest['experiment_ids'])
    assert len(manifest['run_order']) == 48
    all_logical = set()
    all_placements = set()
    bytes_by_job = {}
    for number in range(1, 13):
        job = 'j{:02d}'.format(number)
        info = manifest['jobs'][job]
        fixed = tuple(info['fixed_hosts_by_rank'])
        variable = tuple(info['variable_hosts_by_rank'])
        assert info['generation_seed'] == '{}|{}'.format(manifest['master_seed'], number)
        assert len(set(fixed)) == 4 and variable == (fixed[0], fixed[2], fixed[1], fixed[3])
        assert fixed not in all_placements
        all_placements.add(fixed)
        logical_ref = None
        for placement in ('fixed', 'variable'):
            hosts = fixed if placement == 'fixed' else variable
            for policy in ('single', 'multi'):
                arm = placement + '_' + policy
                name = 'ws24_synthetic_independent_{}_{}_flows.txt'.format(job, arm)
                assert sha(CONFIG / name) == manifest['flow_files_sha256'][name]
                flows = flow_rows(name, nic_map)
                assert len(flows) == info['flows'] == 30
                logical = [(r[0], r[1], r[2], r[3], r[9], r[10], r[11]) for r in flows]
                assert logical_ref is None or logical == logical_ref
                logical_ref = logical
                assert sum(r[9] for r in flows) == info['bytes']
                assert {r[6] for r in flows} == ({0} if policy == 'single' else {0, 1, 2, 3})
                for row in flows:
                    fid, row_job, src_rank, dst_rank, src, dst, sr, dr = row[:8]
                    assert row_job == number and src == hosts[src_rank] and dst == hosts[dst_rank]
                    assert sr == dr == (0 if policy == 'single' else fid % 4)
                    assert components[nic_map[src, sr][1]] == components[nic_map[dst, dr][1]]
                key = '{}_{}'.format(job, arm)
                if key == 'j01_fixed_single':
                    superseded = manifest['superseded_attempts'][
                        '20261002-180000-ws24-ind-j01-fs']
                    assert manifest['experiment_ids'][key] == superseded['replacement']
                else:
                    assert manifest['experiment_ids'][key].endswith('-ws24-ind-{}-{}'.format(
                        job, {'fixed_single': 'fs', 'fixed_multi': 'fm',
                              'variable_single': 'vs', 'variable_multi': 'vm'}[arm]))
        payload = ('\n'.join(' '.join(map(str, row)) for row in logical_ref) + '\n').encode('ascii')
        digest = hashlib.sha256(payload).hexdigest()
        assert digest == info['logical_sha256'] and digest not in all_logical
        all_logical.add(digest)
        bytes_by_job[job] = info['bytes']
    print(json.dumps({'status': 'independent_inputs_verified',
                      'jobs': len(all_logical), 'paired_arms': 48,
                      'manifest_sha256': sha(MANIFEST),
                      'bytes_range': [min(bytes_by_job.values()), max(bytes_by_job.values())]},
                     sort_keys=True))


if __name__ == '__main__':
    main()
