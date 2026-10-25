"""Read-only independent recalculation; never rewrites the frozen synthesis package."""
import csv
import hashlib
import json
import math
import random
import re
import statistics
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / 'docs/research/evidence'
PKG = EV / 'ws30-v12-r1'
OUT = EV / 'ws30-v12-independent-review-r1'

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def rows(path):
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))

def main():
    OUT.mkdir(exist_ok=True)
    sources = {}
    for c in read(EV / 'ws30-historical-raw-audit.json')['cells']:
        sources[c['id']] = (c['seed'], c['moe_batch_us'], c['background_p99_us'], c['trace_sha256'])
    for phase in ('main', 'lead'):
        for c in read(EV / f'ws30-stage3-{phase}-results-r5.json')['rows']:
            sources[c['id']] = (int(c['id'].split('-s')[-1].split('-')[0]), c['tags']['2']['batch_us'], c['tags']['1']['p99_us'], c['trace_sha256'])
    groups = defaultdict(list)
    errors = []
    points = rows(PKG / 'figure-points.csv')
    for p in points:
        a, b = sources[p['candidate_id']], sources[p['control_id']]
        ix = 1 if p['metric'] == 'moe_batch' else 2
        actual = 100 * (a[ix] / b[ix] - 1)
        if not (a[0] == b[0] == int(p['seed']) and a[3] == b[3] and math.isclose(actual, float(p['value']), abs_tol=1e-10)):
            errors.append({'point': p, 'recalculated': actual})
        groups[tuple(p[k] for k in ('family', 'condition', 'contrast', 'metric'))].append(p)
    rng = random.Random(20263003)
    draws = np.array([[rng.randrange(24) for _ in range(24)] for _ in range(10000)])
    recalculated = []
    for e in rows(PKG / 'figure-estimates.csv'):
        key = tuple(e[k] for k in ('family', 'condition', 'contrast', 'metric'))
        ps = sorted(groups[key], key=lambda p: int(p['seed']))
        assert len(ps) == 24 and len({p['seed'] for p in ps}) == 24
        v = np.array([float(p['value']) for p in ps])
        low, high = np.percentile(np.median(v[draws], axis=1), [2.5, 97.5], method='linear')
        fields = {'median_pct': float(np.median(v)), 'ci_low_pct': float(low), 'ci_high_pct': float(high), 'lower_n': int(sum(v < 0)), 'equal_n': int(sum(v == 0)), 'higher_n': int(sum(v > 0))}
        if e['over_3pct_n']:
            fields['over_3pct_n'] = int(sum(v > 3))
        for k, value in fields.items():
            if not math.isclose(value, float(e[k]), abs_tol=1e-10):
                errors.append({'estimate': key, 'field': k, 'actual': value, 'package': e[k]})
        recalculated.append({**dict(zip(('family','condition','contrast','metric'),key)), **fields})
    result = {'scope': 'Independent recomputation from accepted per-ID result indexes, not a new full raw-FCT replay', 'figure_points': len(points), 'estimates': len(recalculated), 'errors': errors, 'recalculated': recalculated}
    (OUT / 'numeric-recalculation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'figure_points': len(points), 'estimates': len(recalculated), 'errors': len(errors)}))
    assert not errors
    extra = {'errors': [], 'native_log_checks': 0, 'drill_log_checks': 0, 'reference_hash_checks': 0}
    indexed = {c['id']: c for c in read(PKG / 'D4-experiments.json')['successes']}
    native = read(PKG / 'D3-native-dynamic.json')
    patterns = {'flowlet_timeouts': r"Number of flowlet's timeout:(\d+)", 'rtt_replies': r"Number of INIT's Reply sent \(RTT_REPLY\):(\d+)", 'notify': r'Number of NOTIFY Sent:(\d+)', 'reroute': r'Number of Rerouting:(\d+)', 'ooo_enqueued': r'Number of OoO enqueued pkts:(\d+)', 'voq_flush': r'Number of VOQ Flush Total:(\d+)'}
    for r in native['branch_receipts']:
        log = Path(indexed[r['id']]['local_directory']) / 'logs/config.log'
        blob = log.read_bytes()
        assert hashlib.sha256(blob).hexdigest() == r['log_sha256']
        text = blob.decode('utf-8', errors='replace')
        for k, count in r['counts'].items():
            found = re.findall(patterns[k], text)
            assert len(found) == 1 and int(found[0]) == count
        extra['native_log_checks'] += 1
    for r in read(PKG / 'native-drill-observation-audit.json')['rows']:
        blob = (Path(indexed[r['id']]['local_directory']) / 'logs/config.log').read_bytes()
        assert hashlib.sha256(blob).hexdigest() == r['log_sha256']
        lines = blob.decode('utf-8', errors='replace').splitlines()
        assert not any(x.startswith(('WS25_QP ', 'WS30_QP ', 'WS30_REPEAT ')) for x in lines)
        extra['drill_log_checks'] += 1
    hist = read(EV / 'ws30-historical-raw-audit.json')['cells']
    for r in rows(PKG / 'D2-native-baselines.csv'):
        group = [x for x in hist if x['mode'] == r['method'] and (x['group'] == 'ws25' if r['cohort'] == 'old' else x['group'] in ('ws27', 'ws28native'))]
        assert len(group) == 24
        group.sort(key=lambda x: x['seed'])
        for field, key in [('batch_change_pct_median','moe_change_pct'), ('background_change_pct_median','bg_change_pct'), ('batch_us_median','moe_batch_us'), ('background_p99_us_median','background_p99_us')]:
            assert math.isclose(statistics.median(x[key] for x in group), float(r[field]), abs_tol=1e-10)
            values = np.array([x[key] for x in group])
            ci = np.percentile(np.median(values[draws], axis=1), [2.5, 97.5], method='linear')
            assert all(math.isclose(float(v), float(r[field.replace('_median', suffix)]), abs_tol=1e-10) for v, suffix in zip(ci, ('_ci_low', '_ci_high')))
        assert sum(x['bg_change_pct'] > 3 for x in group) == int(r['background_gt3'])
    for r in read(PKG / 'reference-review.json')['entries']:
        for path, expected in r['file_sha256'].items():
            assert hashlib.sha256((ROOT.parents[1] / '参考文献/候选' / path).read_bytes()).hexdigest() == expected
            extra['reference_hash_checks'] += 1
    for path, expected in read(PKG / 'manifest.json')['file_sha256'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
    for r in rows(PKG / 'D3-new-arm-actions.csv'):
        source = read(EV / ('ws30-stage3-' + r['phase'] + '-results-r5.json'))['rows']
        selected = [x for x in source if x['arm'] == r['arm']]
        assert len(selected) == int(r['cells'])
        for section in ('path', 'queue', 'transport_sums'):
            for key in selected[0]['observation'][section]:
                assert sum(x['observation'][section][key] for x in selected) == int(r[section + '_' + key])
    (OUT / 'contract-native-reference-checks.json').write_text(json.dumps(extra, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(extra))
    derived = []
    for filename, estimate_file, label in [('factorial-arm-points.csv','factorial-arm-estimates.csv','mode'), ('factorial-points.csv','factorial-estimates.csv','contrast')]:
        grouped = defaultdict(list)
        for p in rows(PKG / filename):
            metric_ix = 1 if p['metric'] == 'moe_batch' else 2
            if 'candidate_id' in p:
                a, b = sources[p['candidate_id']], sources[p['control_id']]
                value = 100 * (a[metric_ix] / b[metric_ix] - 1)
            else:
                ids = json.loads(p['source_ids'])
                y = {k: sources[v][metric_ix] for k, v in ids.items()}
                a0 = 100 * (y['cr-a1-b0'] / y['cr-a0-b0'] - 1)
                a1 = 100 * (y['cr-a1-b1'] / y['cr-a0-b1'] - 1)
                values = {'A_when_B0': a0, 'A_when_B1': a1, 'B_when_A0': 100 * (y['cr-a0-b1'] / y['cr-a0-b0'] - 1), 'B_when_A1': 100 * (y['cr-a1-b1'] / y['cr-a1-b0'] - 1), 'A_by_B_interaction': a1-a0, 'A_by_B_log_interaction': 100 * math.log((y['cr-a1-b1']/y['cr-a0-b1'])/(y['cr-a1-b0']/y['cr-a0-b0']))}
                value = values[p['contrast']]
            assert math.isclose(value, float(p['value']), abs_tol=1e-10)
            grouped[p[label], p['metric']].append(p)
        for e in rows(PKG / estimate_file):
            ps = sorted(grouped[e[label], e['metric']], key=lambda p: int(p['seed']))
            v = np.array([float(p['value']) for p in ps])
            assert len(v) == 24
            ci = np.percentile(np.median(v[draws], axis=1), [2.5,97.5], method='linear')
            for actual, field in zip([np.median(v), *ci], ['median_pct','ci_low_pct','ci_high_pct']):
                assert math.isclose(float(actual), float(e[field]), abs_tol=1e-10)
        derived.append({'points':filename,'point_count':sum(map(len,grouped.values())), 'estimate_count':len(rows(PKG/estimate_file))})
    for p in rows(PKG / 'timing-interactions.csv'):
        ix = 1 if p['metric'] == 'moe_batch' else 2
        ratio = lambda a,b: sources[p[a]][ix]/sources[p[b]][ix]
        v = 100*math.log(ratio('lead_candidate_id','lead_control_id')/ratio('sync_candidate_id','sync_control_id'))
        assert math.isclose(v,float(p['log_ratio_difference_x100']),abs_tol=1e-10)
    (OUT / 'derived-checks.json').write_text(json.dumps({'factorial':derived,'timing_points':144,'errors':[]}, indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Factorial and timing checks passed')

if __name__ == '__main__':
    main()
