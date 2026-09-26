#!/usr/bin/env python3
"""Independently audit the frozen WS-10 formal results and decision."""
import argparse
import glob
import hashlib
import json
import os
import statistics

from analyze_moe_tags import summarize


FORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHA = 'aa778ac523bc0319999395dd3cf8085b41e73a98'
TOPOLOGY = '74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba'
SEEDS = (20261001, 20261002, 20261003, 20261004, 20261005)


def digest(path):
    with open(path, 'rb') as source:
        return hashlib.sha256(source.read()).hexdigest()


def only(pattern):
    found = glob.glob(pattern)
    assert len(found) == 1, (pattern, found)
    return found[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--allow-partial', action='store_true')
    parser.add_argument('--output')
    args = parser.parse_args()
    receipts_path = os.path.join(FORK, 'results', 'ws10-formal-receipts.jsonl')
    with open(receipts_path, encoding='utf-8') as source:
        receipts = [json.loads(line) for line in source]
    stopped = [row for row in receipts if row['event'] == 'stopped']
    recovered = [row for row in receipts if row['event'] == 'recovery']
    assert len(stopped) == len(recovered) == 1
    assert stopped[0]['seed'] == recovered[0]['seed'] == 20261002
    assert stopped[0]['background'] == recovered[0]['background'] == 4
    assert stopped[0]['mode'] == recovered[0]['mode'] == 'dualtrack'
    matches = [row for row in receipts if row['event'] == 'recovery_match']
    assert len(matches) == 1 or args.allow_partial
    if matches:
        assert matches[0]['diagnostic_id'] == recovered[0]['id']
        assert matches[0]['fct_sha256'] == recovered[0]['diagnostic_fct_sha256']
        diagnostic = os.path.join(FORK, 'results', recovered[0]['id'])
        with open(os.path.join(diagnostic, 'metadata.json'), encoding='utf-8') as source:
            diagnostic_meta = json.load(source)
        assert diagnostic_meta['status'] == 'SUCCEEDED'
        assert diagnostic_meta['git_commit'] == SHA
        diagnostic_fct = only(os.path.join(diagnostic, 'raw',
                                          str(diagnostic_meta['raw_directory']), '*_out_fct.txt'))
        assert digest(diagnostic_fct) == matches[0]['fct_sha256']
    verified = [row for row in receipts if row['event'] == 'verified']
    finished = {row['id']: row for row in receipts if row['event'] == 'finished'}
    assert len(verified) == len({row['id'] for row in verified})
    assert len(finished) == len(verified)
    if not args.allow_partial:
        assert len(verified) == 30, len(verified)
    cells = {}
    for row in verified:
        seed, b, mode = row['seed'], row['background'], row['mode']
        assert seed in SEEDS and b in (0, 2, 4) and mode in ('fecmp', 'dualtrack')
        key = (seed, b, mode)
        assert key not in cells
        with open(os.path.join(FORK, 'docs', 'research',
                               'ws10-fixed-s%d-manifest.json' % seed), encoding='utf-8-sig') as source:
            manifest = json.load(source)
        trace_name = 'ws07_fixed_s%d_t256_b4_bg%d.txt' % (seed, b)
        base = os.path.join(FORK, 'results', row['id'])
        with open(os.path.join(base, 'metadata.json'), encoding='utf-8') as source:
            meta = json.load(source)
        assert meta['status'] == 'SUCCEEDED' and meta['git_commit'] == SHA
        assert meta['input_flow_sha256'] == manifest['traces'][trace_name]['sha256']
        assert meta['topology_sha256'] == TOPOLOGY
        assert meta['parameters']['pfc'] == 0 and meta['parameters']['irn'] == 1
        assert meta['parameters']['bw'] == 400 and meta['parameters']['buffer'] == 9
        assert meta['algorithm'] == mode
        assert row['trace_sha256'] == meta['input_flow_sha256']
        assert digest(os.path.join(base, 'config', 'traffic_trace.txt')) == meta['input_flow_sha256']
        assert digest(os.path.join(base, 'config', 'topology.txt')) == TOPOLOGY
        raw = os.path.join(base, 'raw', str(meta['raw_directory']))
        fct = only(os.path.join(raw, '*_out_fct.txt'))
        cnp = only(os.path.join(raw, '*_out_cnp.txt'))
        pfc = only(os.path.join(raw, '*_out_pfc.txt'))
        uplink = only(os.path.join(raw, '*_out_uplink.txt'))
        assert digest(fct) == row['fct_sha256'] and os.path.getsize(pfc) == 0
        analysis = summarize(row['id'], os.path.join(FORK, 'config', manifest['target_file']))
        assert analysis['fct_sha256'] == row['fct_sha256']
        assert analysis['target_trace_sha256'] == row['target_sha256']
        assert analysis['target_moe'] == row['target']
        assert analysis['tags'] == row['tags']
        cnp_values = [list(map(int, line.split())) for line in open(cnp, encoding='utf-8') if line.strip()]
        assert all(len(values) == 5 for values in cnp_values)
        info = finished[row['id']]
        assert info['status'] == 'SUCCEEDED' and not info['budget_breach']
        assert info['sampled_peak_process_rss_mib'] <= 16384
        assert info['disk_free_delta_gib'] <= 5
        assert info['build_seconds'] <= 1200 and info['simulation_seconds'] <= 2700
        assert row['target_sha256'] == manifest['target_sha256']
        assert row['target']['input_flows'] == row['target']['completed_flows'] == 256
        assert all(tag['completion_rate'] == 1 for tag in row['tags'].values())
        cells[key] = {
            'experiment_id': row['id'], 'raw_directory': meta['raw_directory'],
            'trace_sha256': row['trace_sha256'], 'target_sha256': row['target_sha256'],
            'fct_sha256': row['fct_sha256'], 'cnp_sha256': digest(cnp),
            'pfc_sha256': digest(pfc), 'uplink_sha256': digest(uplink),
            'cnp_ecn': sum(values[2] for values in cnp_values),
            'cnp_ooo': sum(values[3] for values in cnp_values),
            'cnp_rows': len(cnp_values), 'pfc_rows': 0,
            'uplink_rows': sum(1 for _ in open(uplink, encoding='utf-8')),
            'fct_rows': sum(1 for _ in open(fct, encoding='utf-8')),
            'target': row['target'], 'tags': row['tags'],
            'build_seconds': info['build_seconds'],
            'simulation_seconds': info['simulation_seconds'],
            'sampled_peak_process_rss_mib': info['sampled_peak_process_rss_mib'],
            'disk_free_delta_gib': info['disk_free_delta_gib'],
        }
    per_seed = []
    for seed in SEEDS:
        if any((seed, b, mode) not in cells for b in (0, 2, 4)
               for mode in ('fecmp', 'dualtrack')):
            if args.allow_partial:
                continue
            raise AssertionError('Incomplete seed %d' % seed)
        batch = lambda b, mode: cells[(seed, b, mode)]['target']['synthetic_batch_completion_us']
        assert all(batch(b, mode) is not None for b in (0, 2, 4)
                   for mode in ('fecmp', 'dualtrack'))
        packet_zero = batch(0, 'dualtrack')
        interaction = {}
        safety = {}
        for b in (2, 4):
            change = ((batch(b, 'dualtrack') - packet_zero) -
                      (batch(b, 'fecmp') - batch(0, 'fecmp')))
            interaction[str(b)] = {'absolute_us': change,
                                   'normalized_percent': 100 * change / packet_zero}
            bg_packet = cells[(seed, b, 'dualtrack')]['tags']['1']['p99_fct_us']
            bg_flow = cells[(seed, b, 'fecmp')]['tags']['1']['p99_fct_us']
            safety[str(b)] = {'packet_p99_us': bg_packet, 'flow_p99_us': bg_flow,
                              'relative_percent': 100 * (bg_packet / bg_flow - 1),
                              'passes': bg_packet <= 1.05 * bg_flow}
        per_seed.append({'seed': seed, 'packet0_us': packet_zero,
                         'batches_us': {str(b): {'flow': batch(b, 'fecmp'),
                                                 'packet': batch(b, 'dualtrack')}
                                        for b in (0, 2, 4)},
                         'interaction': interaction, 'background_safety': safety})
    result = {'source_sha': SHA, 'topology_sha256': TOPOLOGY,
              'pilot_seed_excluded': 20260926, 'formal_seeds': list(SEEDS),
              'offered_bytes_per_cell': 35651584,
              'cells_completed': len(cells), 'per_seed': per_seed,
              'recovery': {'diagnostic_id': recovered[0]['id'],
                           'official_id': matches[0]['id'] if matches else None,
                           'fct_sha256_match': bool(matches)},
              'cells': {'%d-bg%d-%s' % key: value for key, value in cells.items()}}
    if len(per_seed) == 5:
        signed = sum(s['interaction']['4']['absolute_us'] > 0 for s in per_seed)
        median_percent = statistics.median(s['interaction']['4']['normalized_percent']
                                           for s in per_seed)
        safety_pass = all(v['passes'] for s in per_seed
                          for v in s['background_safety'].values())
        result['decision'] = {'positive_seeds': signed,
                              'median_normalized_percent': median_percent,
                              'background_safety_passes': safety_pass,
                              'phenomenon_go': signed >= 4 and median_percent >= 5
                              and safety_pass}
        result['resource_totals'] = {
            'build_seconds': sum(c['build_seconds'] for c in cells.values()),
            'simulation_seconds': sum(c['simulation_seconds'] for c in cells.values()),
            'peak_sampled_rss_mib': max(c['sampled_peak_process_rss_mib']
                                        for c in cells.values()),
            'max_cell_disk_free_delta_gib': max(c['disk_free_delta_gib']
                                                for c in cells.values()),
        }
        with open(os.path.join(FORK, 'results', 'ws10-pilot-receipts.jsonl'),
                  encoding='utf-8') as source:
            pilot = [json.loads(line) for line in source]
        pilot_verified = [row for row in pilot if row['event'] == 'verified']
        pilot_finished = [row for row in pilot if row['event'] == 'finished']
        assert len(pilot_verified) == len(pilot_finished) == 6
        assert not any(row['event'] == 'stopped' for row in pilot)
        assert all(row['git_commit'] == SHA for row in pilot_verified)
        result['resource_totals']['pilot_and_formal_build_simulation_seconds'] = sum(
            row['build_seconds'] + row['simulation_seconds']
            for row in list(finished.values()) + pilot_finished)
    output = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.output:
        with open(args.output, 'x', encoding='utf-8') as target:
            target.write(output)
    else:
        print(output)


if __name__ == '__main__':
    main()
