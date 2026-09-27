#!/usr/bin/env python3
"""Small, recoverable ECMP/DRILL calibration on independent demand traces."""
import argparse
import concurrent.futures
import json
import threading
from pathlib import Path

import run_ws12_matrix as worker


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'results/ws13-calibration-plan.json'
RECEIPTS = ROOT / 'results/ws13-calibration-receipts.jsonl'
MANIFEST = ROOT / 'docs/research/evidence/ws13-calibration-traces.json'
SOURCE_SHA = '6a1de1d9c8c9ea3ac41921230e05d87ccda93b9d'


def plan():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    assert manifest['role'] == 'calibration-only'
    assert manifest['topology_sha256'] == worker.TOPO_SHA
    cells = []
    for i, record in enumerate(manifest['trace_replicates']):
        modes = ('fecmp', 'packet-drill') if i % 2 == 0 else ('packet-drill', 'fecmp')
        for mode in modes:
            name = record['file']
            assert worker.sha(str(ROOT / 'config' / name)) == record['sha256']
            cells.append({'id': f'20260927-153000-ws13-cal-{i+1}-{mode[-1]}',
                          'group': str(record['seed']), 'background': 192,
                          'mode': mode, 'flow_file': name, 'flow_sha256': record['sha256']})
    result = {'role': 'calibration-only', 'git_commit': SOURCE_SHA,
              'topology_sha256': worker.TOPO_SHA, 'cells': cells,
              'manifest': str(MANIFEST.relative_to(ROOT))}
    if PLAN.exists():
        assert json.loads(PLAN.read_text(encoding='utf-8')) == result
    else:
        PLAN.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('plan', 'run'))
    parser.add_argument('--concurrency', type=int, choices=(1, 2, 4), default=2)
    parser.add_argument('--max-new-cells', type=int)
    args = parser.parse_args()
    data = plan()
    if args.phase == 'plan':
        print('Calibration plan: %d cells, source %s' % (len(data['cells']), SOURCE_SHA))
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
        print('All calibration cells verified')
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
            except Exception as error:
                worker.receipt('stopped', cell, error=str(error))
                failures.append(str(error))
        if failures:
            raise RuntimeError('%d calibration cells stopped: %s' % (len(failures), failures[0]))
    print('Verified %d calibration cells' % len(cells))


if __name__ == '__main__':
    main()
