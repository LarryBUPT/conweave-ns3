#!/usr/bin/env python3
"""Recompute WS-14 small-sample comparisons from immutable experiment results."""
import collections
import json
import re
from pathlib import Path

import run_ws14_small as pilot

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/research/evidence/ws14-small-analysis.json'


def key(row):
    return tuple(row[name] for name in ('src', 'dst', 'sport', 'dport'))


def fields(line):
    return {name: value for name, value in
            (word.split('=', 1) for word in line.split()[1:] if '=' in word)}


def read_cell(cell, commit):
    summary = pilot.check_probe(cell, commit)
    base = ROOT / 'results' / cell['id']
    meta = json.loads((base / 'metadata.json').read_text(encoding='utf-8'))
    raw = base / 'raw' / str(meta['raw_directory'])
    fct = raw / (str(meta['raw_directory']) + '_out_fct.txt')
    background = {}
    for line in fct.read_text(encoding='utf-8').splitlines():
        row = list(map(int, line.split()))
        if row[4] == 8388608:
            background[(row[0], row[1], row[2], row[3])] = row[6] / 1000.0
    log = (raw / 'config.log').read_text(encoding='utf-8')
    qp = collections.defaultdict(collections.Counter)
    hops = collections.defaultdict(list)
    for line in log.splitlines():
        if line.startswith('WS13_QP '):
            item = fields(line)
            flow = tuple(int(item[name]) for name in ('src', 'dst', 'sport', 'dport'))
            qp[flow][item['event']] += 1
        elif line.startswith('WS13_HOP '):
            item = fields(line)
            flow = tuple(int(item[name]) for name in ('src', 'dst', 'sport', 'dport'))
            hops[flow].append({name: int(item[name]) for name in
                               ('switch', 'port', 'packets', 'bytes',
                                'queued_bytes_sum', 'queued_bytes_max',
                                'wait_ns_sum', 'wait_ns_max')})
    route = re.search(r'WS09_ROUTE packets=(\d+) two_candidates=(\d+) '
                      r'scored=(\d+) diverted=(\d+)', log)
    return {'cell': cell, 'summary': summary, 'fct_sha256': pilot.worker.sha(str(fct)),
            'background': background, 'qp': qp, 'hops': hops,
            'route': dict(zip(('packets', 'two_candidates', 'scored', 'diverted'),
                              map(int, route.groups()))) if route else None}


def tail(rows, reference=None):
    background = rows['background']
    selected = sorted(background, key=background.get, reverse=True)[:5] if reference is None else reference
    return [{'flow': list(flow), 'fct_us': background.get(flow),
             'qp_events': dict(rows['qp'][flow]), 'hops': rows['hops'][flow]}
            for flow in selected]


def main():
    plan = pilot.make_plan()
    by = {}
    for cell in plan['cells']:
        row = read_cell(cell, plan['git_commit'])
        by[(cell['background'], cell['mode'])] = row
    zero_q = by[(0, 'shortq2')]
    zero_g = by[(0, 'guardhash')]
    assert zero_q['fct_sha256'] == zero_g['fct_sha256'], \
        'GuardHash differs from ordinary two-choice without background'
    original_tail = sorted(by[(192, 'fecmp')]['background'],
                           key=by[(192, 'fecmp')]['background'].get, reverse=True)[:5]
    rows = []
    for cell in plan['cells']:
        row = by[(cell['background'], cell['mode'])]
        bg = cell['background']
        baseline = by.get((bg, 'fecmp'))
        paired = []
        if baseline and bg:
            assert set(row['background']) == set(baseline['background'])
            paired = [row['background'][flow] - baseline['background'][flow]
                      for flow in baseline['background']]
        summary = row['summary']
        rows.append({'id': cell['id'], 'mode': cell['mode'], 'background': bg,
                     'git_commit': summary['git_commit'],
                     'trace_sha256': summary['trace_sha256'],
                     'fct_sha256': row['fct_sha256'],
                     'moe_batch_us': summary['tags']['2']['synthetic_batch_completion_us'],
                     'moe_completed': summary['tags']['2']['completed_flows'],
                     'background_completed': summary['tags'].get('1', {}).get('completed_flows', 0),
                     'background_p95_us': summary['tags'].get('1', {}).get('p95_fct_us'),
                     'background_p99_us': summary['tags'].get('1', {}).get('p99_fct_us'),
                     'background_max_us': max(row['background'].values(), default=None),
                     'paired_background_worse_count': sum(diff > 0 for diff in paired),
                     'paired_background_better_count': sum(diff < 0 for diff in paired),
                     'route': row['route'], 'five_slowest': tail(row),
                     'ecmp_slowest_paired': tail(row, original_tail) if bg else []})
    result = {'role': plan['role'], 'git_commit': plan['git_commit'],
              'topology_sha256': plan['topology_sha256'], 'cells': rows,
              'zero_background_shortq2_guardhash_fct_identical': True,
              'interpretation': 'Single-input technical pilot; destination queue and per-QP CNP are associations, not causal decomposition.'}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print('Wrote %d raw-verified WS-14 cells to %s' % (len(rows), OUT))


if __name__ == '__main__':
    main()
