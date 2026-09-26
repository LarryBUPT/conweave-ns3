#!/usr/bin/env python3
"""Recompute WS-11 gates from all 40 experiment-ID raw artifacts."""
import collections
import datetime
import glob
import hashlib
import json
import os
import statistics

from analyze_ws11_full import full_summary
from audit_ws11_inputs import ROOT, TOPO_SHA
from analyze_result import percentile

RESULTS = ROOT / 'results'
PLAN = RESULTS / 'ws11-formal-plan.json'
OUTPUT = ROOT / 'docs' / 'research' / 'ws11-full-moe-formal-summary.json'
GROUPS = ['original', 20261101, 20261102, 20261103, 20261104]
LEVELS = (0, 64, 128, 192)


def sha(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def uplink_window(path):
    """Use the configured 2.000-2.010 s window, not a selected busy slice."""
    endpoints = {}
    with open(path, encoding='utf-8') as source:
        for line in source:
            fields = line.strip().split(',')
            assert len(fields) == 4
            moment, tor, port, counter = map(int, fields)
            if not 2000000000 <= moment <= 2010000000:
                continue
            key = (tor, port)
            if key not in endpoints:
                endpoints[key] = [moment, counter, moment, counter]
            else:
                assert moment >= endpoints[key][2]
                assert counter >= endpoints[key][3]
                endpoints[key][2:] = [moment, counter]
    by_tor = collections.defaultdict(list)
    max_util = 0.0
    total_bytes = 0
    for (tor, _), (first_t, first_b, last_t, last_b) in endpoints.items():
        assert last_t > first_t
        sent = last_b - first_b
        total_bytes += sent
        by_tor[tor].append(sent)
        max_util = max(max_util, sent * 8.0 / (last_t - first_t) / 400.0)
    imbalance = []
    for values in by_tor.values():
        mean = statistics.mean(values)
        if mean:
            imbalance.append((max(values) - min(values)) / mean)
    imbalance.sort()
    return {'window_start_ns': 2000000000, 'window_end_ns': 2010000000,
            'observed_tors': len(by_tor), 'active_tors': len(imbalance),
            'uplink_ports': len(endpoints), 'total_port_tx_bytes': total_bytes,
            'max_port_mean_utilization_fraction': max_util,
            'tor_imbalance_p50': percentile(imbalance, 50) if imbalance else None,
            'tor_imbalance_p99': percentile(imbalance, 99) if imbalance else None}


def one(cell, commit):
    base = RESULTS / cell['id']
    with (base / 'metadata.json').open(encoding='utf-8') as source:
        metadata = json.load(source)
    assert metadata['status'] == 'SUCCEEDED'
    assert metadata['git_commit'] == commit and metadata['seed'] == 1
    assert metadata['input_flow_sha256'] == cell['flow_sha256']
    assert metadata['topology_sha256'] == TOPO_SHA
    assert metadata['algorithm'] == cell['mode']
    assert metadata['parameters']['pfc'] == 0 and metadata['parameters']['irn'] == 1
    assert sha(base / 'config' / 'traffic_trace.txt') == cell['flow_sha256']
    assert sha(base / 'config' / 'topology.txt') == TOPO_SHA
    summary = full_summary(cell['id'])
    assert summary['trace_sha256'] == cell['flow_sha256']
    expected = {'2': 16384}
    if cell['background']:
        expected['1'] = cell['background']
    assert set(summary['tags']) == set(expected)
    for tag, count in expected.items():
        assert summary['tags'][tag]['input_flows'] == count
        assert summary['tags'][tag]['completed_flows'] == count
        assert summary['tags'][tag]['completion_rate'] == 1
    assert len(summary['hotspot_destinations']) == 8
    assert all(h['input_flows'] == h['completed_flows']
               for h in summary['hotspot_destinations'])
    raw = base / 'raw' / str(metadata['raw_directory'])
    files = {}
    for name in ('fct', 'cnp', 'pfc', 'uplink'):
        found = glob.glob(str(raw / ('*_out_%s.txt' % name)))
        assert len(found) == 1
        files[name] = {'sha256': sha(found[0]), 'bytes': os.path.getsize(found[0])}
    assert files['fct']['sha256'] == summary['fct_sha256']
    assert files['fct']['bytes'] > 0 and files['uplink']['bytes'] > 0
    assert files['pfc']['bytes'] == 0
    uplink = uplink_window(glob.glob(str(raw / '*_out_uplink.txt'))[0])
    with (base / 'logs' / 'resource-summary.json').open(encoding='utf-8') as source:
        resources = json.load(source)
    assert resources['final_status'] == 'SUCCEEDED' and resources['samples'] > 0
    assert resources['peak_tree_rss_mib'] <= 32768
    assert resources['minimum_mem_available_gib'] >= 32
    assert resources['minimum_free_gib'] >= 100
    samples = []
    with (base / 'logs' / 'resource-samples.jsonl').open(encoding='utf-8') as source:
        for line in source:
            samples.append(json.loads(line))
    assert len(samples) == resources['samples']
    started = datetime.datetime.strptime(metadata['started_utc'], '%Y-%m-%dT%H:%M:%SZ')
    finished = datetime.datetime.strptime(metadata['finished_utc'], '%Y-%m-%dT%H:%M:%SZ')
    assert finished >= started
    return {'id': cell['id'], 'group': cell['group'], 'background': cell['background'],
            'mode': cell['mode'], 'trace_sha256': cell['flow_sha256'],
            'topology_sha256': TOPO_SHA, 'seed': 1, 'raw_directory': metadata['raw_directory'],
            'started_utc': metadata['started_utc'], 'finished_utc': metadata['finished_utc'],
            'simulation_seconds': (finished - started).total_seconds(),
            'moe': summary['tags']['2'], 'background_flows': summary['tags'].get('1'),
            'hotspot_destinations': summary['hotspot_destinations'],
            'raw_files': files, 'uplink_window': uplink, 'resource': resources,
            'resource_samples_sha256': sha(base / 'logs' / 'resource-samples.jsonl'),
            'sampled_max_load_1m': max(p['load_1m'] for p in samples)}


def main():
    with PLAN.open(encoding='utf-8') as source:
        plan = json.load(source)
    assert len(plan['cells']) == 40 and len({c['id'] for c in plan['cells']}) == 40
    assert plan['topology_sha256'] == TOPO_SHA
    cells = [one(cell, plan['git_commit']) for cell in plan['cells']]
    lookup = {(str(c['group']), c['background'], c['mode']): c for c in cells}
    assert len(lookup) == 40
    by_group = []
    for group in GROUPS:
        key = str(group)
        p0 = lookup[(key, 0, 'dualtrack')]['moe']['synthetic_batch_completion_us']
        f0 = lookup[(key, 0, 'fecmp')]['moe']['synthetic_batch_completion_us']
        assert p0 > 0 and f0 > 0
        levels = {}
        for bg in LEVELS[1:]:
            p = lookup[(key, bg, 'dualtrack')]
            f = lookup[(key, bg, 'fecmp')]
            pb = p['moe']['synthetic_batch_completion_us']
            fb = f['moe']['synthetic_batch_completion_us']
            interaction = (pb - p0) - (fb - f0)
            baseline_bg_p99 = f['background_flows']['p99_fct_us']
            packet_bg_p99 = p['background_flows']['p99_fct_us']
            safety_pct = 100 * (packet_bg_p99 - baseline_bg_p99) / baseline_bg_p99
            levels[str(bg)] = {'moe_interaction_us': interaction,
                               'normalized_interaction_pct': 100 * interaction / p0,
                               'packet_moe_batch_us': pb, 'flow_moe_batch_us': fb,
                               'flow_load_increment_us': fb - f0,
                               'background_p99_degradation_pct': safety_pct,
                               'background_safety_pass': safety_pct <= 5}
        by_group.append({'group': group, 'packet0_batch_us': p0, 'flow0_batch_us': f0,
                         'levels': levels})
    main_interactions = [r['levels']['192']['moe_interaction_us'] for r in by_group]
    main_percent = [r['levels']['192']['normalized_interaction_pct'] for r in by_group]
    positive = sum(value > 0 for value in main_interactions)
    median_pct = statistics.median(main_percent)
    background_safe = all(r['levels'][str(bg)]['background_safety_pass']
                          for r in by_group for bg in LEVELS[1:])
    go = positive >= 4 and median_pct >= 5 and background_safe
    result = {'prereg': plan['prereg'], 'simulation_git_commit': plan['git_commit'],
              'topology_sha256': TOPO_SHA, 'formal_cell_count': 40,
              'diagnostic_excluded_id': '20260926-144756-ws11-02-b192-f',
              'diagnostic_replacement_id': '20260927-002500-ws11-02-b192-f-r',
              'groups': by_group, 'main_192_positive_groups': positive,
              'main_192_median_normalized_interaction_pct': median_pct,
              'background_safety_all_pass': background_safe,
              'phenomenon_go': go,
              'resource': {'max_tree_rss_mib': max(c['resource']['peak_tree_rss_mib'] for c in cells),
                           'min_mem_available_gib': min(c['resource']['minimum_mem_available_gib'] for c in cells),
                           'min_free_gib': min(c['resource']['minimum_free_gib'] for c in cells),
                           'max_sampled_load_1m': max(c['sampled_max_load_1m'] for c in cells),
                           'sum_simulation_seconds': sum(c['simulation_seconds'] for c in cells)},
              'cells': cells}
    encoded = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if OUTPUT.exists():
        assert OUTPUT.read_text(encoding='utf-8') == encoded
    else:
        OUTPUT.write_text(encoded, encoding='utf-8', newline='\n')
    print(json.dumps({'formal_cell_count': 40, 'positive_groups': positive,
                      'median_normalized_interaction_pct': median_pct,
                      'background_safety_all_pass': background_safe,
                      'phenomenon_go': go}, sort_keys=True))


if __name__ == '__main__':
    main()
