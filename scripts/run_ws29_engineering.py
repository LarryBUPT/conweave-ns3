#!/usr/bin/env python3
"""Prepare or advance one of the remaining 24 frozen WS29 engineering cells."""
import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

import run_ws29_regressions as engine
from verify_ws29_engineering import fields

STAGES = (
    ('joint-control', ('k4-c1-normal',)),
    ('protocol', tuple('protocol-' + str(n) for n in range(1, 12))),
    ('physical-links', tuple('link-' + str(fault) + '-c' + str(arm)
                             for arm in range(3) for fault in (20, 23))),
    ('synthetic-state', tuple('synthetic-' + str(n) for n in (15, 16, 17))),
    ('main-cost', ('main-c1', 'main-c2', 'main-c3')),
)
LABELS = tuple(label for _, labels in STAGES for label in labels)
MANIFEST = engine.ROOT / 'docs/research/evidence/ws29-engineering-entry.json'


def load_plan():
    plan, regressions = engine.load_plan()
    by_label = {cell['label']: cell for cell in plan['cells']}
    engine.require(len(by_label) == len(plan['cells']) == 27 and
                   set(by_label) == set(engine.LABELS + LABELS), 'Engineering cell set changed')
    ordered = regressions + [by_label[label] for label in LABELS]
    blobs = {}
    for cell in ordered:
        engine.require(cell['source_sha'] == engine.SOURCE, 'Simulator SHA changed')
        for name, expected in (('config/' + cell['trace'], cell['trace_sha256']),
                               ('config/' + cell['topology'] + '.txt', cell['topology_sha256'])):
            if name not in blobs:
                blobs[name] = hashlib.sha256(subprocess.check_output(
                    ['git', 'show', engine.SOURCE + ':' + name], cwd=engine.ROOT)).hexdigest()
            engine.require(blobs[name] == expected, 'Frozen input mismatch: ' + name)
    return plan, ordered


def observation(lines, cell):
    decisions = [fields(line) for line in lines if line.startswith('WS29_DECISION ')]
    summaries = [fields(line) for line in lines if line.startswith('WS29_SUMMARY ')]
    heartbeat = [fields(line) for line in lines if line.startswith('WS21_HEARTBEAT ')]
    engine.require(len(summaries) == 1 and int(summaries[0]['rows']) <= 500000,
                   'WS29 event row limit')
    engine.require(all(int(row['event_rows']) <= 20000 for row in heartbeat), 'HB event row limit')
    injected = [fields(line) for line in lines if line.startswith('WS29_SYNTHETIC ')]
    if 'expected_synthetic_events' in cell:
        engine.require(len(injected) == cell['expected_synthetic_events'],
                       'Frozen synthetic event count differs')
    reasons = Counter(row['reason'] for row in decisions)
    eligible = sum(reasons[name] for name in ('equal_ce', 'distinct_ce'))
    scope = ('synthetic' if cell['synthetic'] else 'natural-main-demand'
             if cell['label'] in STAGES[-1][1] else 'normal-control'
             if cell['fault'] == 0 else 'protocol-or-physical-fault')
    controls = [fields(line) for line in lines if line.startswith('WS29_CONTROL ')]
    totals, per_link = {}, {}
    for control in controls:
        kind_event = control['type'] + '/' + control['event']
        link_event = '/'.join(control[key] for key in ('switch', 'port', 'type', 'event'))
        for ledger, key in ((totals, kind_event), (per_link, link_event)):
            item = ledger.setdefault(key, dict(packets=0, wire_bytes=0))
            item['packets'] += 1
            item['wire_bytes'] += int(control['bytes'])
    qps = [fields(line) for line in lines if line.startswith('WS29_QP ')]
    return dict(id=cell['id'], scope=scope, synthetic=cell['synthetic'], fault=cell['fault'],
                recorded_decisions=len(decisions), two_fresh=eligible,
                two_fresh_fraction=eligible / len(decisions) if decisions else None,
                would_change=sum(row['proposed'] != row['local'] for row in decisions),
                adopted_changed=sum(row['chosen'] != row['local'] for row in decisions),
                reasons=dict(sorted(reasons.items())),
                control_by_kind_event=totals, control_per_link_kind_event=per_link,
                application_input_bytes=cell['input_bytes'],
                tx_payload_bytes=sum(int(row['tx_payload_bytes']) for row in qps),
                cost_note='Control wire bytes are per-hop events; application bytes are an end-to-end denominator. Enqueue/dequeue are separate ledgers, not additive traffic.',
                A06='OPEN: natural opportunity/adoption requires separate review; synthetic PASS cannot close it')


def local_verify(plan, cell):
    if cell['label'] in engine.LABELS:
        return engine.local_verify(plan, cell)
    row = engine.local_verify(plan, cell, persist=False)
    folder = engine.ROOT / 'results' / cell['id']
    meta = json.loads((folder / 'metadata.json').read_text(encoding='utf-8'))
    raw = folder / 'raw' / str(meta['raw_directory'])
    observations = observation((raw / 'config.log').read_text(encoding='utf-8').splitlines(), cell)
    engine.immutable(engine.CONTROL / (cell['label'] + '.observation.json'), observations)
    engine.immutable(engine.CONTROL / (cell['label'] + '.verified.json'), row)
    return row


def prepare(plan, cells):
    by_label = {cell['label']: cell for cell in cells}
    data = dict(kind='WS29 remaining 24 engineering cells; execution awaits separate GO',
                source_sha=engine.SOURCE, plan_sha256=engine.PLAN_SHA,
                regression_prerequisites=list(engine.LABELS),
                stages=[dict(name=name, labels=list(labels)) for name, labels in STAGES],
                order=list(LABELS), resource_limits=plan['resource_limits'], cells=[])
    for label in LABELS:
        cell = by_label[label]
        data['cells'].append(dict(frozen_cell=cell, build=engine.build_arguments(cell),
            run=engine.run_arguments(cell),
            collect=['python', 'scripts/run_ws29_engineering.py', 'collect', '--label', label]))
    engine.immutable(MANIFEST, data)
    return data


def stage_receipts(cells):
    by_label = {cell['label']: cell for cell in cells}
    for name, labels in STAGES:
        if not all((engine.CONTROL / (label + '.verified.json')).exists() and
                   (engine.CONTROL / (label + '.observation.json')).exists() for label in labels):
            break
        rows = [json.loads((engine.CONTROL / (label + '.observation.json')).read_text(encoding='utf-8'))
                for label in labels]
        engine.immutable(engine.CONTROL / ('stage-' + name + '.json'),
                         dict(stage=name, ids=[by_label[label]['id'] for label in labels],
                              observations=rows, A06='OPEN; engineering completion is not natural adoption evidence'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'build', 'start', 'collect', 'verify'))
    parser.add_argument('--label', choices=LABELS)
    args = parser.parse_args()
    plan, cells = load_plan()
    if args.phase == 'prepare':
        prepare(plan, cells)
        print(json.dumps(dict(prepared=24, entry=str(MANIFEST), remote_actions=0)))
        return
    try:
        row = engine.execute_phase(args, plan, cells, verify_cell=local_verify)
        if row is not None:
            stage_receipts(cells)
    except Exception as error:
        if args.label is not None and not (engine.CONTROL / 'STOP.json').exists():
            engine.immutable(engine.CONTROL / 'STOP.json',
                             dict(id=next(c['id'] for c in cells if c['label'] == args.label),
                                  phase=args.phase, error=str(error)))
        raise


if __name__ == '__main__':
    main()
