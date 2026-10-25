"""Check frozen lead inputs and class time origins without launching simulations."""
import collections
import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import analyze_moe_tags as legacy
import analyze_ws30_tags as current
import run_ws30_stage3 as runner


def main():
    root, evidence = runner.ROOT, runner.EV
    plan = runner.read(runner.PLAN)
    assert len(plan['lead']) == len({c['id'] for c in plan['lead']}) == 72
    assert {c['arm'] for c in plan['lead']} == {'E', 'Q16', 'C16'}
    seeds = sorted({c['seed'] for c in plan['lead']})
    assert seeds == list(range(20263021, 20263045))
    main_by_seed = {c['seed']: c for c in plan['main'] if c['arm'] == 'E'}
    traces = []
    for seed in seeds:
        cells = [c for c in plan['lead'] if c['seed'] == seed]
        assert len(cells) == 3 and len({c['trace_sha256'] for c in cells}) == 1
        cell = cells[0]
        assert all(c['source_sha'] == runner.stage.SOURCE and c['cap'] == 12 for c in cells)
        path = root / 'config' / cell['trace']
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == cell['trace_sha256']
        assert subprocess.check_output(['git', '-C', str(root), 'show',
                                       cell['source_sha'] + ':config/' + cell['trace']]) == data
        lines = data.decode().splitlines()
        values = [line.split() for line in lines[1:]]
        assert len(values) == int(lines[0]) == 16576
        assert [Decimal(v[4]) for v in values] == sorted(Decimal(v[4]) for v in values)
        origins = {tag: min(Decimal(v[4]) for v in values if v[5] == tag) for tag in ['1', '2']}
        assert origins == {'1': Decimal('2.000000000'), '2': Decimal('2.000020000')}
        assert collections.Counter(v[5] for v in values) == {'1': 192, '2': 16384}
        synchronized = (root / 'config' / main_by_seed[seed]['trace']).read_text().splitlines()[1:]
        identity = lambda rows: collections.Counter(tuple(v[:4] + [v[5]]) for v in rows)
        assert identity(values) == identity([line.split() for line in synchronized])
        traces.append({'seed': seed, 'trace': cell['trace'], 'sha256': cell['trace_sha256'],
                       'background_origin_ns': 2000000000, 'moe_origin_ns': 2000020000})
    assert not any((root / 'results' / c['id']).exists() for c in plan['lead'])

    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        (folder / 'config').mkdir(); (folder / 'raw/1').mkdir(parents=True)
        trace = b'3\n0 1 3 1000 2.000000000 1\n0 2 3 1000 2.000020000 2\n0 3 3 1000 2.000020000 2\n'
        (folder / 'config/traffic_trace.txt').write_bytes(trace)
        (folder / 'metadata.json').write_text(json.dumps({'status': 'SUCCEEDED', 'raw_directory': '1',
            'input_flow_sha256': hashlib.sha256(trace).hexdigest()}))
        (folder / 'raw/1/1_out_fct.txt').write_text(
            '0 1 10000 100 1000 2000000000 10000 1\n'
            '0 2 10001 100 1000 2000020000 5000 1\n'
            '0 3 10002 100 1000 2000020000 7000 1\n')
        hand = current.summarize(folder)
        assert hand['tags']['2']['release_origin_ns'] == 2000020000
        assert hand['tags']['2']['batch_us'] == 7
        assert hand['tags']['1']['p99_us'] == 10

    legacy.PROJECT = str(root)
    main_rows = runner.read(evidence / 'ws30-stage3-main-results-r5.json')['rows']
    bridge = runner.read(evidence / 'ws30-bridge-results-recovered-r1.json')
    assert len(main_rows) == 192 and bridge['verified_cells'] == 96 and bridge['all_fct_match_historical']
    rows = main_rows + bridge['rows']
    assert len({r['id'] for r in rows}) == 288
    checked = []
    for row in rows:
        fresh = current.summarize(root / 'results' / row['id'])
        old = legacy.summarize(row['id'])
        assert fresh['fct_sha256'] == row['fct_sha256']
        for tag in ['1', '2']:
            a, b = fresh['tags'][tag], old['tags'][tag]
            assert a['release_origin_ns'] == 2000000000
            assert a['input_flows'] == a['completed_flows'] == b['input_flows'] == b['completed_flows']
            assert a['batch_us'] == b['synthetic_batch_completion_us']
            for percentile in [50, 95, 99]:
                assert a['p%d_us' % percentile] == b['p%d_fct_us' % percentile]
        checked.append({'id': row['id'], 'fct_sha256': fresh['fct_sha256']})
    receipt = {'kind': 'WS-30 lead local input and time-origin acceptance',
        'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'plan_sha256': runner.stage.sha(runner.PLAN), 'source_sha': runner.stage.SOURCE,
        'lead_cells': 72, 'independent_demand_seeds': 24, 'frozen_traces': traces,
        'hand_calculated': {'moe_origin_ns': 2000020000, 'moe_batch_us': 7,
                            'background_p99_us': 10},
        'synchronized_main_regressions': 192, 'synchronized_historical_bridge_regressions': 96,
        'old_and_new_metrics_equal': True, 'raw_fct_hashes_unchanged': checked,
        'formal_lead_executed_by_this_audit': 0}
    target = evidence / 'ws30-stage3-lead-local-acceptance-r1.json'
    if target.exists():
        receipt['checked_utc'] = runner.read(target)['checked_utc']
    runner.stage.frozen(target, receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k not in ['frozen_traces', 'raw_fct_hashes_unchanged']}))


if __name__ == '__main__':
    main()
