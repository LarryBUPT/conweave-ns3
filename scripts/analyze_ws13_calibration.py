#!/usr/bin/env python3
"""Recompute descriptive WS-13 calibration dispersion from six raw cells."""
import json
import statistics
from pathlib import Path

from analyze_ws11_full import full_summary
from run_ws12_matrix import sha, TOPO_SHA


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'results/ws13-calibration-plan.json'
OUTPUT = ROOT / 'docs/research/evidence/ws13-calibration-summary.json'


def main():
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    assert plan['role'] == 'calibration-only' and len(plan['cells']) == 6
    groups = {}
    cells = []
    for cell in plan['cells']:
        base = ROOT / 'results' / cell['id']
        meta = json.loads((base / 'metadata.json').read_text(encoding='utf-8'))
        assert meta['status'] == 'SUCCEEDED' and meta['git_commit'] == plan['git_commit']
        assert meta['input_flow_sha256'] == cell['flow_sha256']
        assert meta['topology_sha256'] == TOPO_SHA and meta['seed'] == 1
        assert meta['parameters']['pfc'] == 0 and meta['parameters']['irn'] == 1
        assert sha(str(base / 'config/traffic_trace.txt')) == cell['flow_sha256']
        result = full_summary(cell['id'])
        assert result['tags']['2']['completed_flows'] == 16384
        assert result['tags']['1']['completed_flows'] == 192
        resource = json.loads((base / 'logs/resource-summary.json').read_text(encoding='utf-8'))
        assert resource['final_status'] == 'SUCCEEDED' and resource['samples'] > 0
        raw = base / 'raw' / str(meta['raw_directory'])
        fct = raw / (str(meta['raw_directory']) + '_out_fct.txt')
        assert sha(str(fct)) == result['fct_sha256']
        row = {'id': cell['id'], 'trace_seed': int(cell['group']), 'mode': cell['mode'],
               'trace_sha256': cell['flow_sha256'], 'fct_sha256': result['fct_sha256'],
               'moe_batch_us': result['tags']['2']['synthetic_batch_completion_us'],
               'moe_p99_fct_us': result['tags']['2']['p99_fct_us'],
               'background_p99_fct_us': result['tags']['1']['p99_fct_us'],
               'background_mean_fct_us': result['tags']['1']['mean_fct_us'],
               'peak_tree_rss_mib': resource['peak_tree_rss_mib'],
               'minimum_mem_available_gib': resource['minimum_mem_available_gib']}
        cells.append(row)
        groups.setdefault(row['trace_seed'], {})[row['mode']] = row
    contrasts = []
    for seed, pair in sorted(groups.items()):
        assert set(pair) == {'fecmp', 'packet-drill'}
        f, d = pair['fecmp'], pair['packet-drill']
        assert f['trace_sha256'] == d['trace_sha256']
        contrasts.append({'trace_seed': seed, 'trace_sha256': f['trace_sha256'],
                          'moe_batch_drill_minus_ecmp_us': d['moe_batch_us'] - f['moe_batch_us'],
                          'background_p99_drill_minus_ecmp_us': d['background_p99_fct_us'] - f['background_p99_fct_us'],
                          'background_p99_drill_vs_ecmp_pct':
                          100 * (d['background_p99_fct_us'] - f['background_p99_fct_us']) / f['background_p99_fct_us']})
    def span(values):
        return {'min': min(values), 'median': statistics.median(values), 'max': max(values)}
    result = {'role': 'calibration-only; not formal validation', 'complete': True,
              'independent_demand_traces': len(groups), 'cells': cells, 'paired_contrasts': contrasts,
              'descriptive_spans': {
                  'ecmp_background_p99_us': span([g['fecmp']['background_p99_fct_us'] for g in groups.values()]),
                  'ecmp_moe_batch_us': span([g['fecmp']['moe_batch_us'] for g in groups.values()]),
                  'drill_background_p99_minus_ecmp_us': span([r['background_p99_drill_minus_ecmp_us'] for r in contrasts]),
                  'drill_moe_batch_minus_ecmp_us': span([r['moe_batch_drill_minus_ecmp_us'] for r in contrasts])},
              'interpretation_limit': 'Three independent traces give descriptive dispersion only; no threshold or confidence bound.'}
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'independent_traces': len(groups), 'complete': True,
                      'contrasts': contrasts}, ensure_ascii=False))


if __name__ == '__main__':
    main()
