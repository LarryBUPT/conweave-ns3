#!/usr/bin/env python3
"""Verify 12 independent synthetic WS-24 job blocks and paired four-arm effects."""

import argparse
import json
import math
import statistics
from pathlib import Path

from verify_ws24_inputs import sha
from verify_ws24_matrix import arm_rows
from verify_ws24_result import verify as verify_cell


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'config' / 'ws24_independent_manifest.json'


def exact_sign_p(values):
    nonzero = [value for value in values if value != 0]
    n = len(nonzero)
    if not n:
        return 1.0
    minority = min(sum(value > 0 for value in nonzero), sum(value < 0 for value in nonzero))
    return min(1.0, 2.0 * sum(math.comb(n, index) for index in range(minority + 1)) / (2 ** n))


def median_ci_percent(log_ratios):
    ordered = sorted(log_ratios)
    n = len(ordered)
    best = 1
    for k in range(1, n // 2 + 1):
        coverage = 1 - 2 * sum(math.comb(n, i) for i in range(k)) / (2 ** n)
        if coverage >= .95:
            best = k
    return [100 * (math.exp(ordered[best - 1]) - 1),
            100 * (math.exp(ordered[n - best]) - 1)]


def verify_resource(experiment_id):
    logs = ROOT / 'results' / experiment_id / 'logs'
    summary = json.loads((logs / 'resource-summary.json').read_text(encoding='utf-8'))
    assert summary['id'] == experiment_id and summary['final_status'] == 'SUCCEEDED'
    rows = [json.loads(line) for line in (logs / 'resource-samples.jsonl').read_text(
        encoding='utf-8').splitlines() if line.strip()]
    assert rows and len(rows) == summary['samples']
    assert max(row['process_tree_rss_mib'] for row in rows) <= 8192
    assert max(row['load_1m'] for row in rows) <= 20
    assert min(row['mem_available_gib'] for row in rows) >= 16
    assert min(row['free_gib'] for row in rows) >= 100
    assert all(path.stat().st_size <= 50 * 1024 * 1024 for path in logs.glob('*.log'))
    return {'samples': len(rows),
            'peak_tree_rss_mib': max(row['process_tree_rss_mib'] for row in rows),
            'max_load_1m': max(row['load_1m'] for row in rows)}


def verify_matrix(source_sha):
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    assert manifest['job_count'] == 12 and len(manifest['experiment_ids']) == 48
    assert sha(ROOT / 'config' / manifest['topology_file']) == manifest['topology_sha256']
    assert sha(ROOT / 'config' / manifest['nic_file']) == manifest['nic_sha256']
    cells = {}
    effects = {}
    for job_index in range(1, 13):
        job = 'j{:02d}'.format(job_index)
        info = manifest['jobs'][job]
        receipts = {}
        spans = {}
        logical_ref = None
        for arm in manifest['arms_per_job']:
            key = job + '_' + arm
            experiment_id = manifest['experiment_ids'][key]
            filename = 'ws24_synthetic_independent_{}_{}_flows.txt'.format(job, arm)
            assert sha(ROOT / 'config' / filename) == manifest['flow_files_sha256'][filename]
            resource = verify_resource(experiment_id)
            result = verify_cell(experiment_id, source_sha, 'independent', key)
            assert result['flows'] == info['flows'] and result['unique_bytes'] == info['bytes']
            assert result['input_flow_sha256'] == manifest['flow_files_sha256'][filename]
            assert result['topology_sha256'] == manifest['topology_sha256']
            assert result['nic_sha256'] == manifest['nic_sha256']
            rows = arm_rows(experiment_id)
            assert len(rows) == info['flows']
            logical = {fid: (r[1], r[2], r[3], r[12], r[13]) for fid, r in rows.items()}
            assert logical_ref is None or logical == logical_ref
            logical_ref = logical
            placement, policy = arm.split('_')
            hosts = info[placement + '_hosts_by_rank']
            for fid, row in rows.items():
                assert (row[4], row[5]) == (hosts[row[2]], hosts[row[3]])
                assert row[6] == (0 if policy == 'single' else fid % 4)
            receipts[arm] = rows
            spans[arm] = max(row[15] for row in rows.values()) - min(row[13] for row in rows.values())
            cells[key] = {'result': result, 'resource': resource, 'span_ns': spans[arm]}
        fixed_log = math.log(spans['fixed_multi'] / spans['fixed_single'])
        variable_log = math.log(spans['variable_multi'] / spans['variable_single'])
        effects[job] = {'spans_ns': spans,
                        'fixed_log_ratio': fixed_log,
                        'variable_log_ratio': variable_log,
                        'primary_log_ratio': (fixed_log + variable_log) / 2,
                        'placement_interaction_log_ratio': variable_log - fixed_log}
    primary = [effects[job]['primary_log_ratio'] for job in sorted(effects)]
    median_log = statistics.median(primary)
    return {'source_sha': source_sha, 'manifest_sha256': sha(MANIFEST),
            'cells_verified': len(cells), 'independent_job_blocks': len(effects),
            'cells': cells, 'paired_jobs': effects,
            'primary': {'metric': 'mean of fixed/variable log(multi/single) job-span ratios',
                        'median_percent': 100 * (math.exp(median_log) - 1),
                        'median_95_percent_ci': median_ci_percent(primary),
                        'two_sided_exact_sign_p': exact_sign_p(primary),
                        'negative_blocks': sum(value < 0 for value in primary),
                        'positive_blocks': sum(value > 0 for value in primary),
                        'zero_blocks': sum(value == 0 for value in primary)},
            'evidence_level': 'independent seeded synthetic ns-3 jobs; no real deployment claim'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-sha', required=True)
    args = parser.parse_args()
    print(json.dumps(verify_matrix(args.source_sha), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
