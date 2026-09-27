#!/usr/bin/env python3
"""Run WS-13 probes with unambiguous per-QP IRN ACK/SACK logging."""
import argparse
import concurrent.futures
import json
import re
import threading
from pathlib import Path

import run_ws12_matrix as worker


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'results/ws13-feedback-probe-plan.json'
RECEIPTS = ROOT / 'results/ws13-feedback-probe-receipts.jsonl'
SOURCE_SHA = 'a985798ef78a95f502cf8eb56982c6e3a3b1168d'


def make_plan():
    summary = json.loads((ROOT / 'docs/research/ws12-packet-strategies-formal-summary.json')
                         .read_text(encoding='utf-8'))
    lookup = {(str(c['group']), c['background'], c['mode']): c for c in summary['cells']}
    permutation = json.loads((ROOT / 'docs/research/ws11-permutation-manifest.json')
                             .read_text(encoding='utf-8'))
    specs = [('original', 192, 'fecmp', 'o-f'),
             ('original', 192, 'packet-adaptive', 'o-a'),
             ('20261103', 128, 'fecmp', '03-f'),
             ('20261103', 128, 'packet-drill', '03-d')]
    cells = []
    for group, background, mode, code in specs:
        reference = lookup[(group, background, mode)]
        if group == 'original':
            flow_file = 'moe_1280group_256to8_8round_8KB_hybrid_192fecmp.txt'
        else:
            flow_file = permutation['inputs'][group][str(background)]['file']
        flow_sha = reference['trace_sha256']
        assert worker.sha(str(ROOT / 'config' / flow_file)) == flow_sha
        cells.append({'id': '20260927-160000-ws13-feedback-' + code,
                      'group': group, 'background': background, 'mode': mode,
                      'flow_file': flow_file, 'flow_sha256': flow_sha,
                      'ws13_diag': True,
                      'ws12_reference_id': reference['id'],
                      'ws12_reference_fct_sha256': reference['raw_files']['fct']['sha256']})
    plan = {'role': 'diagnostic-only-irn-feedback-semantics',
            'git_commit': SOURCE_SHA, 'topology_sha256': worker.TOPO_SHA, 'cells': cells}
    if PLAN.exists():
        assert json.loads(PLAN.read_text(encoding='utf-8')) == plan
    else:
        PLAN.write_text(json.dumps(plan, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return plan


def verify_feedback(cell):
    summary = worker.verify(cell, SOURCE_SHA)
    assert summary['fct_sha256'] == cell['ws12_reference_fct_sha256'], \
        'Logging-only change altered the fixed WS-12 FCT'
    base = ROOT / 'results' / cell['id']
    meta = json.loads((base / 'metadata.json').read_text(encoding='utf-8'))
    assert meta['parameters']['ws13_diag'] == 1
    raw = base / 'raw' / str(meta['raw_directory'])
    log = (raw / 'config.log').read_text(encoding='utf-8', errors='strict')
    qp_events = [line for line in log.splitlines() if line.startswith('WS13_QP ')]
    assert qp_events and all('irn_nack_size=' in line for line in qp_events)
    assert not any('event=nack ' in line for line in qp_events)
    for line in qp_events:
        size = int(re.search(r'irn_nack_size=(\d+)', line).group(1))
        if 'event=irn_ack ' in line:
            assert size == 0
        if 'event=sack ' in line:
            assert size > 0
    assert re.search(r'WS13_INFLIGHT unpaired=(\d+)', log)
    assert (raw / 'config.log').stat().st_size < 50000000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('plan', 'run'))
    parser.add_argument('--concurrency', type=int, choices=(1, 2, 4), default=1)
    args = parser.parse_args()
    plan = make_plan()
    if args.phase == 'plan':
        print('Planned %d feedback probes at %s' % (len(plan['cells']), SOURCE_SHA))
        return
    worker.RECEIPTS = str(RECEIPTS)
    worker.CPU_TOKENS = threading.BoundedSemaphore(18)
    worker.audit()
    existing = []
    if RECEIPTS.exists():
        existing = [json.loads(line) for line in RECEIPTS.read_text(encoding='utf-8').splitlines()]
    done = {row['id'] for row in existing if row['event'] == 'verified'}
    cells = [cell for cell in plan['cells'] if cell['id'] not in done]
    if not cells:
        print('All feedback probes are already verified')
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
                verify_feedback(cell)
            except Exception as error:
                worker.receipt('feedback_verification_failed', cell, error=str(error))
                failures.append(str(error))
        if failures:
            raise RuntimeError('%d feedback probes failed: %s' % (len(failures), failures[0]))
    print('Verified %d feedback probes' % len(cells))


if __name__ == '__main__':
    main()
