#!/usr/bin/env python3
"""Run the preregistered WS-14 correctness/extreme cells, with raw receipts."""
import argparse
import concurrent.futures
import json
import re
import subprocess
import threading
from pathlib import Path

import run_ws12_matrix as worker

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'results/ws14-small-plan.json'
RECEIPTS = ROOT / 'results/ws14-small-receipts.jsonl'
SPECS = ((0, 'shortq2', '0-q'), (0, 'guardhash', '0-g'),
         (192, 'fecmp', '192-f'), (192, 'dualtrack', '192-h'),
         (192, 'shortq2', '192-q'), (192, 'packet-drill', '192-d'),
         (192, 'guardhash', '192-g'))


def git(*args):
    return subprocess.check_output(['git'] + list(args), cwd=str(ROOT),
                                   universal_newlines=True).strip()


def make_plan():
    if PLAN.exists():
        return json.loads(PLAN.read_text(encoding='utf-8'))
    assert not git('status', '--porcelain'), 'Freeze and commit source before planning'
    commit = git('rev-parse', 'HEAD')
    assert worker.sha(str(ROOT / 'config/topo_1280_400G_400G_OS1.txt')) == worker.TOPO_SHA
    cells = []
    for bg, mode, code in SPECS:
        name, expected = worker.input_for('original', bg, None)
        assert worker.sha(str(ROOT / 'config' / name)) == expected
        cells.append({'id': '20260927-233000-ws14-' + code,
                      'group': 'original', 'background': bg, 'mode': mode,
                      'flow_file': name, 'flow_sha256': expected,
                      'ws13_diag': bg == 192})
    plan = {'role': 'ws14-preregistered-research-small-sample',
            'git_commit': commit, 'topology_sha256': worker.TOPO_SHA,
            'prereg': 'docs/research/ws14-single-mechanism-prereg-v1.md',
            'cells': cells}
    PLAN.parent.mkdir(exist_ok=True)
    PLAN.write_text(json.dumps(plan, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return plan


def check_probe(cell, commit):
    summary = worker.verify(cell, commit)
    base = ROOT / 'results' / cell['id']
    meta = json.loads((base / 'metadata.json').read_text(encoding='utf-8'))
    raw = base / 'raw' / str(meta['raw_directory'])
    log = (raw / 'config.log').read_text(encoding='utf-8')
    if cell['mode'] in ('shortq2', 'guardhash'):
        match = re.search(r'WS09_ROUTE packets=(\d+) two_candidates=(\d+) '
                          r'scored=(\d+) diverted=(\d+)', log)
        assert match, 'Missing routing counters'
        assert int(match.group(1)) > 0 and int(match.group(2)) > 0
        assert 'WS09_QUEUE_CHECK violations=0' in log
        for line in log.splitlines():
            if not line.startswith('WS09_QUEUE '):
                continue
            row = dict(part.split('=', 1) for part in line.split()[1:])
            assert int(row['enqueued']) == (int(row['dequeued']) +
                                            int(row['queued_drop']) + int(row['current']))
    if cell['ws13_diag']:
        assert 'WS13_INFLIGHT unpaired=0' in log
        assert 'WS13_HOP ' in log and 'WS13_QP ' in log
        assert all('irn_nack_size=' in line for line in log.splitlines()
                   if line.startswith('WS13_QP '))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('plan', 'run', 'verify'))
    parser.add_argument('--concurrency', type=int, choices=(1, 2, 4), default=2)
    args = parser.parse_args()
    plan = make_plan()
    worker.RECEIPTS = str(RECEIPTS)
    if args.phase == 'plan':
        print('WS-14 %d small cells @ %s' % (len(plan['cells']), plan['git_commit']))
        return
    if args.phase == 'verify':
        for cell in plan['cells']:
            check_probe(cell, plan['git_commit'])
        print('Verified %d cells' % len(plan['cells']))
        return
    worker.audit()
    worker.CPU_TOKENS = threading.BoundedSemaphore(18)
    done = set()
    if RECEIPTS.exists():
        for line in RECEIPTS.read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            if row['event'] == 'verified':
                done.add(row['id'])
    cells = [cell for cell in plan['cells'] if cell['id'] not in done]
    stop = threading.Event()
    slots = threading.Semaphore(args.concurrency)
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(cells),
                                                                  args.concurrency + 2)) as pool:
        futures = [pool.submit(worker.run_cell, cell, plan['git_commit'],
                               args.concurrency, slots, stop) for cell in cells]
        problems = []
        for cell, future in zip(cells, futures):
            try:
                future.result()
                check_probe(cell, plan['git_commit'])
            except Exception as error:
                stop.set()
                worker.receipt('ws14_verification_failed', cell, error=str(error))
                problems.append(str(error))
        if problems:
            raise RuntimeError('%d WS-14 cells failed: %s' % (len(problems), problems[0]))
    print('Verified %d WS-14 small cells' % len(cells))


if __name__ == '__main__':
    main()
