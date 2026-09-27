#!/usr/bin/env python3
"""Recoverable five-cell tail observability probe; never a formal effect test."""
import argparse
import concurrent.futures
import json
import re
import threading
from pathlib import Path

import run_ws12_matrix as worker


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'results/ws13-probe-plan.json'
RECEIPTS = ROOT / 'results/ws13-probe-receipts.jsonl'
SOURCE_SHA = 'd4146e70564ae44c080e1bdbe18480eb83bdf2b8'


def plan():
    old = json.loads((ROOT / 'docs/research/ws12-packet-strategies-formal-summary.json').read_text(encoding='utf-8'))
    lookup = {(str(c['group']), c['background'], c['mode']): c for c in old['cells']}
    permutations = json.loads((ROOT / 'docs/research/ws11-permutation-manifest.json').read_text(encoding='utf-8'))
    specs = [('original', 192, 'fecmp', False, 'o-f-off'),
             ('original', 192, 'fecmp', True, 'o-f-on'),
             ('original', 192, 'packet-adaptive', True, 'o-a-on'),
             ('20261103', 128, 'fecmp', True, '03-f-on'),
             ('20261103', 128, 'packet-drill', True, '03-d-on')]
    cells = []
    for group, bg, mode, diag, code in specs:
        previous = lookup[(group, bg, mode)]
        if group == 'original':
            name = 'moe_1280group_256to8_8round_8KB_hybrid_192fecmp.txt'
        else:
            name = permutations['inputs'][group][str(bg)]['file']
        assert worker.sha(str(ROOT / 'config' / name)) == previous['trace_sha256']
        cells.append({'id': '20260927-160000-ws13-probe-' + code,
                      'group': group, 'background': bg, 'mode': mode,
                      'flow_file': name, 'flow_sha256': previous['trace_sha256'],
                      'ws13_diag': diag, 'ws12_reference_id': previous['id'],
                      'ws12_reference_fct_sha256': previous['raw_files']['fct']['sha256']})
    result = {'role': 'diagnostic-only', 'git_commit': SOURCE_SHA,
              'topology_sha256': worker.TOPO_SHA, 'cells': cells}
    if PLAN.exists():
        assert json.loads(PLAN.read_text(encoding='utf-8')) == result
    else:
        PLAN.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


def verify_probe(cell):
    base = ROOT / 'results' / cell['id']
    metadata = json.loads((base / 'metadata.json').read_text(encoding='utf-8'))
    assert metadata['parameters']['ws13_diag'] == int(cell['ws13_diag'])
    raw_id = str(metadata['raw_directory'])
    raw = base / 'raw' / raw_id
    assert worker.sha(str(raw / (raw_id + '_out_fct.txt'))) == cell['ws12_reference_fct_sha256'], \
        'Diagnostic source changed FCT vs fixed WS-12 reference'
    log = (raw / 'config.log').read_text(encoding='utf-8')
    if cell['ws13_diag']:
        assert 'WS13_HOP ' in log and 'WS13_INFLIGHT ' in log
        assert re.search(r'WS13_INFLIGHT unpaired=(\d+)', log)
        assert (raw / 'config.log').stat().st_size < 50000000, 'Diagnostic log exceeds 50 MB'
    else:
        assert 'WS13_HOP ' not in log


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('plan', 'run'))
    parser.add_argument('--concurrency', type=int, choices=(1, 2, 4), default=1)
    parser.add_argument('--max-new-cells', type=int)
    args = parser.parse_args()
    data = plan()
    if args.phase == 'plan':
        print('Diagnostic plan: %d cells, source %s' % (len(data['cells']), SOURCE_SHA))
        return
    worker.RECEIPTS = str(RECEIPTS)
    worker.CPU_TOKENS = threading.BoundedSemaphore(18)
    worker.audit()
    done = set()
    if RECEIPTS.exists():
        done = {row['id'] for row in map(json.loads, RECEIPTS.read_text(encoding='utf-8').splitlines())
                if row['event'] == 'verified'}
    cells = [cell for cell in data['cells'] if cell['id'] not in done]
    if args.max_new_cells is not None:
        assert args.max_new_cells > 0
        cells = cells[:args.max_new_cells]
    if not cells:
        print('All diagnostic cells verified')
        return
    stop = threading.Event()
    slots = threading.Semaphore(args.concurrency)
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(cells), args.concurrency + 2)) as pool:
        futures = [pool.submit(worker.run_cell, cell, SOURCE_SHA, args.concurrency, slots, stop)
                   for cell in cells]
        failures = []
        for cell, future in zip(cells, futures):
            try:
                future.result()
                verify_probe(cell)
            except Exception as error:
                worker.receipt('stopped', cell, error=str(error))
                failures.append(str(error))
        if failures:
            raise RuntimeError('%d probe cells stopped: %s' % (len(failures), failures[0]))
    print('Verified %d diagnostic cells' % len(cells))


if __name__ == '__main__':
    main()
