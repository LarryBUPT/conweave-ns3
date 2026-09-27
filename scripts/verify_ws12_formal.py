#!/usr/bin/env python3
"""Recompute WS-12 completeness, two-sided metrics, and frozen strategy gates."""
import json
import re
import statistics

from audit_ws11_inputs import ROOT, TOPO_SHA
from run_ws12_matrix import MODES, SIMULATION_COMMIT
from verify_ws11_formal import one, sha

PLAN = ROOT / 'results' / 'ws12-formal-plan.json'
OUTPUT = ROOT / 'docs' / 'research' / 'ws12-packet-strategies-formal-summary.json'
WS11_SUMMARY = ROOT / 'docs' / 'research' / 'ws11-full-moe-formal-summary.json'
GROUPS = ('original', 20261101, 20261102, 20261103, 20261104)
LEVELS = (0, 64, 128, 192)


def route_counters(cell):
    if cell['mode'] not in ('packet-rr', 'packet-random', 'packet-adaptive', 'packet-drill'):
        return None
    raw = ROOT / 'results' / cell['id'] / 'raw' / str(cell['raw_directory'])
    with (raw / 'config.log').open(encoding='utf-8') as source:
        log = source.read()
    route = re.search(r'WS12_ROUTE mode=(\d+) moe_packets=(\d+) background_packets=(\d+) moe_multipath=(\d+)', log)
    assert route is not None
    mode, moe, background, multipath = map(int, route.groups())
    assert mode == {'packet-rr': 16, 'packet-random': 17,
                    'packet-adaptive': 18, 'packet-drill': 19}[cell['mode']]
    assert moe > 0 and multipath > 0
    if cell['background']:
        assert background > 0
    ports = re.findall(r'WS12_PORT switch=(\d+) port=(\d+) packets=(\d+)', log)
    assert sum(int(packets) for _, _, packets in ports) == moe
    counts = [int(packets) for _, _, packets in ports]
    return {'moe_source_packets': moe, 'background_source_packets': background,
            'moe_source_multipath_packets': multipath,
            'source_ports_used': len(ports), 'source_port_packets_min': min(counts),
            'source_port_packets_max': max(counts),
            'config_log_sha256': sha(raw / 'config.log')}


def main():
    with PLAN.open(encoding='utf-8') as source:
        plan = json.load(source)
    assert plan['git_commit'] == SIMULATION_COMMIT
    assert plan['topology_sha256'] == TOPO_SHA and len(plan['cells']) == 120
    assert len({c['id'] for c in plan['cells']}) == 120
    assert {(str(c['group']), c['background'], c['mode']) for c in plan['cells']} == {
        (str(group), bg, mode) for group in GROUPS for bg in LEVELS for mode in MODES}
    cells = []
    for spec in plan['cells']:
        cell = one(spec, SIMULATION_COMMIT)
        cell['route_counters'] = route_counters(cell)
        cells.append(cell)
    lookup = {(str(c['group']), c['background'], c['mode']): c for c in cells}
    with WS11_SUMMARY.open(encoding='utf-8') as source:
        previous = json.load(source)
    legacy_matches = 0
    for old in previous['cells']:
        assert old['mode'] in ('fecmp', 'dualtrack')
        new = lookup[(str(old['group']), old['background'], old['mode'])]
        assert new['trace_sha256'] == old['trace_sha256']
        assert new['raw_files']['fct']['sha256'] == old['raw_files']['fct']['sha256']
        legacy_matches += 1
    assert legacy_matches == 40
    contrasts = []
    for group in GROUPS:
        key = str(group)
        for mode in MODES:
            baseline0 = lookup[(key, 0, 'fecmp')]['moe']['synthetic_batch_completion_us']
            mode0 = lookup[(key, 0, mode)]['moe']['synthetic_batch_completion_us']
            assert baseline0 > 0 and mode0 > 0
            for bg in LEVELS:
                current = lookup[(key, bg, mode)]
                flow = lookup[(key, bg, 'fecmp')]
                packet_hash = lookup[(key, bg, 'dualtrack')]
                t = current['moe']['synthetic_batch_completion_us']
                f = flow['moe']['synthetic_batch_completion_us']
                h = packet_hash['moe']['synthetic_batch_completion_us']
                interaction = (t - mode0) - (f - baseline0)
                row = {'group': group, 'background': bg, 'mode': mode,
                       'moe_batch_us': t, 'fecmp_batch_us': f, 'hash_batch_us': h,
                       'moe_minus_fecmp_us': t - f, 'moe_minus_hash_us': t - h,
                       'background_interaction_us': interaction,
                       'normalized_interaction_pct': 100 * interaction / mode0}
                if bg:
                    p99 = current['background_flows']['p99_fct_us']
                    fp99 = flow['background_flows']['p99_fct_us']
                    hp99 = packet_hash['background_flows']['p99_fct_us']
                    assert fp99 > 0
                    row.update({'background_p99_us': p99,
                                'background_p99_vs_fecmp_pct': 100 * (p99 - fp99) / fp99,
                                'background_p99_vs_hash_pct': 100 * (p99 - hp99) / hp99})
                contrasts.append(row)
    gates = {}
    for mode in MODES[2:]:
        main_rows = [r for r in contrasts if r['mode'] == mode and r['background'] == 192]
        wins = sum(r['moe_minus_hash_us'] <= 0 for r in main_rows)
        reductions = [-100 * r['moe_minus_hash_us'] / r['hash_batch_us'] for r in main_rows]
        safety = all(r['background_p99_vs_fecmp_pct'] <= 5 for r in contrasts
                     if r['mode'] == mode and r['background'] > 0)
        gates[mode] = {'main_192_not_slower_groups': wins,
                       'main_192_median_reduction_vs_hash_pct': statistics.median(reductions),
                       'background_safety_all_pass': safety,
                       'two_sided_acceptable': wins >= 4 and statistics.median(reductions) >= 5 and safety}
    result = {'prereg': plan['prereg'], 'simulation_git_commit': SIMULATION_COMMIT,
              'topology_sha256': TOPO_SHA, 'formal_cell_count': len(cells),
              'complete': True, 'legacy_fct_hash_matches': legacy_matches,
              'cells': cells, 'contrasts': contrasts, 'strategy_gates': gates,
              'resource': {'max_tree_rss_mib': max(c['resource']['peak_tree_rss_mib'] for c in cells),
                           'max_sampled_load_1m': max(c['sampled_max_load_1m'] for c in cells),
                           'min_mem_available_gib': min(c['resource']['minimum_mem_available_gib'] for c in cells),
                           'min_free_gib': min(c['resource']['minimum_free_gib'] for c in cells),
                           'sum_simulation_seconds': sum(c['simulation_seconds'] for c in cells)}}
    if OUTPUT.exists():
        with OUTPUT.open(encoding='utf-8') as source:
            assert json.load(source) == result
    else:
        with OUTPUT.open('x', encoding='utf-8') as target:
            json.dump(result, target, indent=2, sort_keys=True)
            target.write('\n')
    print(json.dumps({'complete': True, 'formal_cell_count': len(cells),
                      'legacy_fct_hash_matches': legacy_matches,
                      'strategy_gates': gates, 'resource': result['resource']}, sort_keys=True))


if __name__ == '__main__':
    main()
