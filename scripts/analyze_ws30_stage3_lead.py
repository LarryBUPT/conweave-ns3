"""Reaudit fixed raw cells and analyse the paired synchronous/20-us-lead node.

No simulation is launched. Demand seeds, not flows or conditions, are the
resampling units. All observations and counterexamples are exported.
"""
import collections
import csv
import datetime
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import random
import statistics

import numpy as np
import run_ws30_stage3 as runner

ROOT, EV = runner.ROOT, runner.EV
ARMS = ('E', 'Q16', 'C16')
CONTRASTS = (('Q16', 'E'), ('C16', 'E'), ('C16', 'Q16'))
SEEDS = list(range(20263021, 20263045))
BOOT_SEED, BOOT_DRAWS = 20263003, 10000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + '\n'
    if path.exists() and path.read_text(encoding='utf-8') != text:
        raise RuntimeError('Refusing to replace a different analysis artifact: ' + str(path))
    path.write_text(text, encoding='utf-8')


def percentile(values, p):
    v = sorted(values)
    index = (len(v) - 1) * p / 100
    low, high = math.floor(index), math.ceil(index)
    return v[low] + (v[high] - v[low]) * (index - low)


def raw_audit(cell, condition):
    """Reconstruct flow keys and class origins independently using Decimal."""
    folder = ROOT / 'results' / cell['id']
    meta = runner.read(folder / 'metadata.json')
    source = folder / 'config/traffic_trace.txt'
    expected, ports, destports = {}, collections.defaultdict(lambda: 10000), collections.defaultdict(lambda: 100)
    for line in source.read_text().splitlines()[1:]:
        f = line.split()
        src, dst, pg, size = map(int, f[:4])
        tag, start = int(f[5]), int(Decimal(f[4]) * 10**9)
        key = (src, dst, ports[src], destports[dst], size)
        ports[src] += 1
        destports[dst] += 1
        assert key not in expected
        expected[key] = (tag, start, pg)
    assert len(expected) == cell['input_flows'] == 16576
    fct = folder / 'raw' / str(meta['raw_directory']) / (str(meta['raw_directory']) + '_out_fct.txt')
    completed = {}
    for line in fct.read_text().splitlines():
        row = list(map(int, line.split()))
        assert len(row) == 8
        key = tuple(row[:5])
        assert key in expected and key not in completed
        assert abs(row[5] - expected[key][1]) <= 2 and row[6] >= 0 and row[7] > 0
        completed[key] = (row[5], row[6], row[5] + row[6])
    assert completed.keys() == expected.keys()
    tags = {}
    for tag in (1, 2):
        keys = [k for k, value in expected.items() if value[0] == tag]
        origin = min(expected[k][1] for k in keys)
        end = max(completed[k][2] for k in keys)
        fcts = [completed[k][1] / 1000 for k in keys]
        tails = sorted(k for k in keys if completed[k][2] == end)
        assert origin == 2000000000 + (20000 if tag == 2 and condition == 'lead20us' else 0)
        assert len(keys) == (192 if tag == 1 else 16384)
        tags[str(tag)] = {
            'input_flows': len(keys), 'completed_flows': len(keys),
            'input_bytes': sum(k[4] for k in keys), 'completed_bytes': sum(k[4] for k in keys),
            'release_origin_ns': origin, 'batch_us': (end - origin) / 1000,
            'p50_us': percentile(fcts, 50), 'p95_us': percentile(fcts, 95),
            'p99_us': percentile(fcts, 99), 'max_us': max(fcts),
            'batch_tail_keys': [list(k) for k in tails],
        }
    identity = hashlib.sha256(json.dumps(sorted((list(k), v[0], v[2]) for k, v in expected.items())).encode()).hexdigest()
    config = dict(line.split(maxsplit=1) for line in (folder / 'config/config.txt').read_text().splitlines() if len(line.split(maxsplit=1)) == 2)
    assert config['ENABLE_PFC'] == '0' and config['ENABLE_IRN'] == '1'
    assert config['RANDOM_SEED'] == '1' and config['CC_MODE'] == '1'
    assert config['LB_MODE'] == {'E': '0', 'Q16': '27', 'C16': '21'}[cell['arm']]
    assert config['FLOW_FILE'] == 'config/' + cell['trace']
    hashes = {str(p.relative_to(folder)).replace('\\', '/'): sha(p) for p in [
        folder / 'metadata.json', source, folder / 'config/config.txt',
        folder / 'config/topology.txt', folder / 'logs/config.log', fct,
        folder / 'logs/resource-summary.json', folder / 'logs/resource-samples.jsonl']}
    return {'id': cell['id'], 'seed': cell['seed'], 'arm': cell['arm'], 'condition': condition,
            'source_sha': meta['git_commit'], 'trace_sha256': sha(source), 'topology_sha256': sha(folder / 'config/topology.txt'),
            'flow_identity_sha256': identity, 'tags': tags, 'file_sha256': hashes,
            'started_utc': meta['started_utc'], 'finished_utc': meta['finished_utc'], 'actual_cap': meta['concurrency_cap']}


def describe(values):
    return {**{f'p{p}': percentile(values, p) for p in (5, 25, 50, 75, 95)}, 'min': min(values), 'max': max(values)}


def main():
    plan = runner.read(runner.PLAN)
    assert runner.stage.sha(runner.PLAN) == '77ca6064d4b4f275b409123302b01bd4eabd97e9c978e013f8d3e67edbf420f8'
    verified, audited, indexed = [], [], {}
    for phase, condition in [('main', 'synchronous'), ('lead', 'lead20us')]:
        recorded = {r['id']: r for r in runner.read(EV / f'ws30-stage3-{phase}-results-r5.json')['rows']}
        cells = [c for c in plan[phase] if c['arm'] in ARMS]
        assert len(cells) == 72
        for c in cells:
            fresh = runner.verify(c)
            assert fresh == recorded[c['id']], ('Frozen result differs', c['id'])
            audit = raw_audit(c, condition)
            for tag in ('1', '2'):
                for name in ('batch_us', 'p50_us', 'p95_us', 'p99_us', 'max_us', 'release_origin_ns'):
                    assert math.isclose(fresh['tags'][tag][name], audit['tags'][tag][name], rel_tol=1e-12, abs_tol=1e-9)
            verified.append((condition, c, fresh)); audited.append(audit)
            indexed[(condition, c['seed'], c['arm'])] = audit
    for seed in SEEDS:
        rows = [indexed[(condition, seed, arm)] for condition in ('synchronous', 'lead20us') for arm in ARMS]
        assert len({r['flow_identity_sha256'] for r in rows}) == 1, seed

    rng = random.Random(BOOT_SEED)
    draws = np.array([[rng.randrange(24) for _ in range(24)] for _ in range(BOOT_DRAWS)])

    def effect(values):
        array = np.array(values, dtype=float)
        boot = np.median(array[draws], axis=1)
        return {'n': 24, 'median': float(np.median(array)), 'bootstrap_95pct': np.percentile(boot, [2.5, 97.5]).tolist(),
                'negative_n': int(sum(array < 0)), 'zero_n': int(sum(array == 0)), 'positive_n': int(sum(array > 0)),
                'range': [float(min(array)), float(max(array))], 'per_seed': dict(zip(map(str, SEEDS), array.tolist()))}

    metrics = {'moe_batch': ('2', 'batch_us'), 'background_p99': ('1', 'p99_us')}
    def values(condition, arm, metric):
        tag, key = metrics[metric]
        return np.array([indexed[(condition, seed, arm)]['tags'][tag][key] for seed in SEEDS])

    comparisons, contrast_csv = [], []
    for condition in ('synchronous', 'lead20us'):
        for candidate, control in CONTRASTS:
            out = {'condition': condition, 'contrast': candidate + '/' + control, 'candidate': candidate, 'control': control}
            for metric in metrics:
                change = 100 * (values(condition, candidate, metric) / values(condition, control, metric) - 1)
                out[metric] = effect(change)
                if metric == 'background_p99' and control == 'E':
                    out[metric]['over_engineering_3pct_seeds'] = [seed for seed, v in zip(SEEDS, change) if v > 3]
                    out[metric]['median_below_3pct'] = out[metric]['median'] < 3
                for seed, v in zip(SEEDS, change):
                    contrast_csv.append({'condition': condition, 'contrast': out['contrast'], 'metric': metric,
                                         'seed': seed, 'change_pct': v,
                                         'candidate_id': indexed[(condition, seed, candidate)]['id'],
                                         'control_id': indexed[(condition, seed, control)]['id']})
            comparisons.append(out)

    interactions = []
    for candidate, control in CONTRASTS:
        out = {'contrast': candidate + '/' + control}
        for metric in metrics:
            sync = values('synchronous', candidate, metric) / values('synchronous', control, metric)
            lead = values('lead20us', candidate, metric) / values('lead20us', control, metric)
            out[metric] = {'log_ratio_difference_x100': effect(100 * np.log(lead / sync)),
                           'paired_effect_difference_pp': effect(100 * (lead - sync)),
                           'ratio_of_ratios_pct': effect(100 * (lead / sync - 1))}
        interactions.append(out)

    arm_condition_changes = [{'arm': arm, **{metric: effect(100 * (values('lead20us', arm, metric) / values('synchronous', arm, metric) - 1)) for metric in metrics}} for arm in ARMS]
    distributions, observations, tails = [], [], []
    for condition in ('synchronous', 'lead20us'):
        for arm in ARMS:
            records = [indexed[(condition, seed, arm)] for seed in SEEDS]
            distributions.append({'condition': condition, 'arm': arm,
                'metrics_us': {f'{tag}_{key}': describe([r['tags'][tag][key] for r in records]) for tag in ('1', '2') for key in ('batch_us', 'p50_us', 'p95_us', 'p99_us', 'max_us')}})
            rows = [r for cond, c, r in verified if cond == condition and c['arm'] == arm]
            summed = {section: {key: sum(r['observation'][section][key] for r in rows) for key in rows[0]['observation'][section]} for section in ('path', 'queue', 'transport_sums')}
            summed['choices_by_tag'] = {str(tag): {k: sum(next(x for x in r['observation']['choices'] if x['tag'] == tag)[k] for r in rows) for k in rows[0]['observation']['choices'][0] if k != 'tag'} for tag in (1, 2)}
            for choices in summed['choices_by_tag'].values():
                distinct = choices['events'] - choices['same']
                choices['distinct_candidate_events'] = distinct
                choices['descriptive_pct_of_distinct'] = {key: 100 * choices[key] / distinct if distinct else None for key in ('background_nonzero', 'a_disagrees', 'composition', 'near', 'empty')}
            observations.append({'condition': condition, 'arm': arm, **summed})
        for candidate, control in CONTRASTS:
            changed = [seed for seed in SEEDS if indexed[(condition, seed, candidate)]['tags']['2']['batch_tail_keys'] != indexed[(condition, seed, control)]['tags']['2']['batch_tail_keys']]
            tails.append({'condition': condition, 'contrast': candidate + '/' + control, 'tail_identity_changed_n': len(changed), 'seeds': changed})

    raw_csv = []
    for r in audited:
        row = {k: r[k] for k in ('condition', 'seed', 'arm', 'id', 'source_sha', 'trace_sha256', 'actual_cap')}
        for tag, prefix in [('1', 'background'), ('2', 'moe')]:
            for key, value in r['tags'][tag].items(): row[prefix + '_' + key] = json.dumps(value) if isinstance(value, list) else value
        for metric in metrics:
            reference = indexed[(r['condition'], r['seed'], 'E')]
            tag, key = metrics[metric]
            row[metric + '_vs_E_pct'] = 100 * (r['tags'][tag][key] / reference['tags'][tag][key] - 1)
        raw_csv.append(row)

    caps = collections.Counter(r['actual_cap'] for r in audited if r['condition'] == 'lead20us')
    leadrows = [r for cond, c, r in verified if cond == 'lead20us']
    resources = {'peak_load_1m': max(r['resource']['peak_load_1m'] for r in leadrows),
                 'minimum_mem_available_gib': min(r['resource']['minimum_mem_available_gib'] for r in leadrows),
                 'minimum_free_gib': min(r['resource']['minimum_free_gib'] for r in leadrows),
                 'peak_tree_rss_mib': max(r['resource']['peak_tree_rss_mib'] for r in leadrows),
                 'actual_cap_cells': dict(caps)}
    result = {'analysis_version': 'r1', 'source_sha': runner.stage.SOURCE, 'plan_sha256': sha(runner.PLAN),
              'lead_verified_cells': 72, 'synchronous_comparator_cells': 72, 'independent_demand_seeds': SEEDS,
              'statistical_unit': '24 demand seeds; synchronous and lead20us are correlated conditions within seed',
              'bootstrap': {'draws': BOOT_DRAWS, 'seed': BOOT_SEED, 'implementation': 'random.Random indices; numpy median and linear percentile; same seed resampling indices across contrasts', 'interval': 'nominal two-sided 95%; no significance labels or multiplicity-adjusted claims'},
              'definitions': {'moe_batch_us': 'max(start_ns + fct_ns) - tag2 release origin, divided by 1000',
                              'background_p99_us': 'linear 99th percentile of all 192 per-flow background FCTs',
                              'effect_pct': '100*(candidate/control-1), median over demand seeds',
                              'condition_interaction': 'within-seed 100*log((candidate/control)_lead/(candidate/control)_sync); descriptive'},
              'comparisons': comparisons, 'condition_interactions': interactions, 'lead_vs_sync_same_arm_pct': arm_condition_changes,
              'distributions': distributions, 'observations': observations, 'moe_tail_identity_changes': tails, 'lead_resources': resources,
              'exclusions': [], 'composition_executed': False}
    archived = runner.read(EV / 'ws30-stage3-main-analysis-r1.json')
    old = {c['contrast']: c for c in archived['comparisons']}
    for c in archived['relative_to_E']:
        old[c['arm'] + '/E'] = {metric: c['vs_E_' + metric] for metric in metrics}
    regression = []
    for c in comparisons:
        if c['condition'] != 'synchronous':
            continue
        for metric in metrics:
            before = old[c['contrast']][metric]
            assert math.isclose(c[metric]['median'], before['median_change_pct'], abs_tol=1e-12)
            regression.append({'contrast': c['contrast'], 'metric': metric,
                               'median_equal': True, 'archived_ci': before['bootstrap_95pct'],
                               'common_indices_recomputed_ci': c[metric]['bootstrap_95pct']})
    result['synchronous_regression'] = {'all_medians_equal': True, 'rows': regression,
        'ci_note': 'This node uses the same draw-index matrix for all contrasts. Archived main results are preserved; nominal bootstrap endpoints may differ slightly due to random stream allocation.'}
    write_json(EV / 'ws30-stage3-lead-analysis-r1.json', result)
    write_json(EV / 'ws30-stage3-lead-raw-audit-r1.json', {'plan_sha256': sha(runner.PLAN), 'source_sha': runner.stage.SOURCE, 'verified_rows': 144, 'independent_reconstruction': 'Decimal origins, identity/byte conservation, FCT and percentile recomputation', 'rows': audited})
    for name, rows in [('paired', raw_csv), ('contrasts', contrast_csv)]:
        path = EV / f'ws30-stage3-lead-{name}-r1.csv'
        with path.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    for comp in comparisons:
        print(comp['condition'], comp['contrast'], {m: (comp[m]['median'], comp[m]['bootstrap_95pct'], comp[m]['positive_n']) for m in metrics})
    print('RESOURCES', resources)


if __name__ == '__main__':
    main()
