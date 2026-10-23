#!/usr/bin/env python3
"""One reviewed recovery phase at a time; old STOP is immutable, never cleared."""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import run_ws29_engineering as observations
import run_ws29_regressions as engine
import remote_experiment as remote
from prepare_ws29_recovery import SOURCE, PREFIX, STAGES, OLD

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/research/evidence'
CONTROL = ROOT / 'results/ws29-physical-recovery-control'
OLD_STOP = ROOT / 'results/ws29-regression-control/STOP.json'
LOCK_SHA = '2cd6994d51f5ae9090af74218bd44ef701dc299392bdaa9c668cb978635989fd'
require = engine.require
digest = engine.digest
immutable = engine.immutable


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def validate_identity(plan, contract):
    require(plan['source_sha'] == contract['source_sha'] == SOURCE, 'Top-level source identity mismatch')
    require(plan['unit_id'] == contract['new_id'] == PREFIX + 'unit', 'Unit identity mismatch')
    labels = [label for _, group in STAGES for label in group]
    require([c['label'] for c in plan['cells']] == labels, 'Recovery order/cell set mismatch')
    require(plan['stages'] == [dict(name=name, labels=list(group)) for name, group in STAGES], 'Stage mismatch')
    require(plan['max_concurrent'] == 1, 'Concurrency must remain one')
    for c in plan['cells']:
        require(c['source_sha'] == SOURCE and c['id'] == PREFIX + c['label'], 'Cell identity mismatch')
    require(contract['suite'] == 'devices-point-to-point' and contract['build_mode'] == 'optimized' and
            contract['cpu_jobs'] == 2, 'Unit build identity mismatch')
    require('WS-29 all-link faults preserve host links without telemetry' in contract['required_pass_cases'],
            'New physical test missing from unit contract')


def load():
    lock_path = EVIDENCE / 'ws29-recovery-lock.json'
    require(digest(lock_path) == LOCK_SHA, 'Recovery lock changed')
    lock = read(lock_path)
    for name, expected in lock['files'].items():
        require(digest(EVIDENCE / name) == expected, 'Locked recovery material changed: ' + name)
    require(digest(ROOT / 'scripts/remote_worker.py') == lock['worker_sha256'], 'Local worker changed')
    for name,expected in lock['controller_sha256'].items():
        require(digest(ROOT / 'scripts' / name) == expected, 'Reviewed controller dependency changed: ' + name)
    plan = read(EVIDENCE / 'ws29-segmented-recovery-plan.json')
    contract = read(EVIDENCE / 'ws29-recovery-unit-contract.json')
    validate_identity(plan, contract)
    require(lock['source_sha'] == SOURCE and lock['unit_id'] == plan['unit_id'], 'Lock identity mismatch')
    require(digest(engine.PLAN) == plan['origin_plan_sha256'] == engine.PLAN_SHA, 'Original plan changed')
    old = read(engine.PLAN); by_label = {c['label']: c for c in old['cells']}
    require(plan['resource_limits'] == old['resource_limits'], 'Resource criteria changed')
    for c in plan['cells']:
        require({k:v for k,v in c.items() if k not in ('id','source_sha')} ==
                {k:v for k,v in by_label[c['label']].items() if k not in ('id','source_sha')},
                'Frozen cell criteria changed: ' + c['label'])
        for path, expected in [('config/' + c['trace'], c['trace_sha256']),
                               ('config/' + c['topology'] + '.txt', c['topology_sha256'])]:
            data = subprocess.check_output(['git', 'show', SOURCE + ':' + path], cwd=ROOT)
            require(hashlib.sha256(data).hexdigest() == expected, 'Recovery input changed')
    reused = {c['label'] for c in plan['reuse']}
    require(reused == set(by_label) - {c['label'] for c in plan['cells']} and len(reused) == 14,
            'Reuse coverage mismatch')
    for c in plan['reuse']:
        require(c == {k:by_label[c['label']][k] for k in ('label','id','source_sha')} and
                c['source_sha'] == OLD, 'Old evidence identity mismatch')
    return plan, contract, lock


def binding(plan, lock, stage):
    return dict(kind='main-review-go', stage=stage, source_sha=SOURCE,
        plan_sha256=lock['files']['ws29-segmented-recovery-plan.json'],
        unit_contract_sha256=lock['files']['ws29-recovery-unit-contract.json'],
        lock_sha256=LOCK_SHA, runner_sha256=digest(Path(__file__)), worker_sha256=lock['worker_sha256'],
        old_stop_sha256=plan['original_stop_sha256'], reviewed_by_main=True)


def stop_guard(plan):
    require(OLD_STOP.is_file() and not OLD_STOP.is_symlink() and
            digest(OLD_STOP) == plan['original_stop_sha256'], 'Original STOP missing or changed')
    require(not (CONTROL / 'STOP.json').exists(), 'Recovery STOP exists; no retry')


def authorize(plan, lock, stage):
    stop_guard(plan)
    approval = CONTROL / ('approval-' + stage + '.json')
    require(approval.is_file() and not approval.is_symlink(), 'Main review GO missing for stage ' + stage)
    require(read(approval) == binding(plan, lock, stage), 'Approval does not bind current materials')


def record(plan, cell, event, **data):
    CONTROL.mkdir(parents=True, exist_ok=True)
    with (CONTROL / 'commands-and-events.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(dict(id=cell['id'], event=event, source_sha=SOURCE,
            plan_sha256=digest(EVIDENCE / 'ws29-segmented-recovery-plan.json'),
            time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), **data)) + '\n')


def command(plan, cell, args):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/remote_experiment.py')] + args,
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=7200 if args[0] == 'build' else 1800 if args[0] == 'fetch' else 90)
    CONTROL.mkdir(parents=True, exist_ok=True)
    path = CONTROL / (cell['label'] + '.' + args[0] + '.' + str(datetime.datetime.now().timestamp()) + '.log')
    with path.open('xb') as f:
        f.write(result.stdout)
    record(plan, cell, 'command', argv=args, exit_code=result.returncode, output_log=str(path))
    require(result.returncode == 0, 'Command failed; preserve ID and logs')
    return result.stdout.decode('utf-8', errors='replace')


def worker_identity(lock):
    result = subprocess.run(remote.ssh_base(remote.config()) +
        ['sha256sum /home/fnl/lzy/.research-workflow/remote_worker.py'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)
    require(result.returncode == 0 and result.stdout.decode().split()[0] == lock['worker_sha256'],
            'Deployed worker differs from reviewed resource/unit policy')


def resources(folder, ident, limits, status, prefix='resource'):
    summary = read(folder / 'logs' / (prefix + '-summary.json'))
    samples = [json.loads(x) for x in (folder / 'logs' / (prefix + '-samples.jsonl')).read_text().splitlines() if x]
    require(summary['id'] == ident and summary['final_status'] == status and
            summary['samples'] == len(samples) > 0, 'Resource receipt identity/count mismatch')
    expected = dict(peak_tree_rss_mib=max(s['process_tree_rss_mib'] for s in samples),
                    minimum_mem_available_gib=min(s['mem_available_gib'] for s in samples),
                    minimum_free_gib=min(s['free_gib'] for s in samples),
                    maximum_load_1m=max(s['load_1m'] for s in samples))
    require(all(summary[k] == v for k,v in expected.items()), 'Resource summary differs from samples')
    require(max(s['process_tree_rss_mib'] for s in samples) <= limits['rss_mib_max'] and
            min(s['mem_available_gib'] for s in samples) >= limits['available_memory_gib_min'] and
            min(s['free_gib'] for s in samples) >= limits['free_disk_gib_min'] and
            max(s['load_1m'] for s in samples) <= limits['load_1m_max'], 'Resource stop line')
    require(max((p.stat().st_size for p in folder.rglob('*.log')), default=0) <=
            limits['max_text_log_bytes'], 'Text log stop line')
    return summary


def verify_unit(folder, plan, contract):
    meta = read(folder / 'metadata.json')
    require(meta['experiment_id'] == contract['new_id'] and meta['git_commit'] == SOURCE and
            meta['status'] == 'TESTED' and meta['unit_status'] == 'PASS' and
            meta['unit_suite'] == contract['suite'] and meta['unit_compatibility'] is True and
            meta['cpu_jobs'] == 2 and meta['build_mode'] == 'optimized', 'Unit metadata mismatch')
    logs = folder / 'logs'
    for name in contract['required_logs']:
        require((logs / name).is_file() and (logs / name).stat().st_size > 0, 'Unit evidence missing: ' + name)
    text = (logs / 'ws29-point-to-point-unit-test.log').read_text(encoding='utf-8')
    require(not re.search(r'^\s*FAIL\b', text, re.M) and
            all('PASS ' + name in text for name in contract['required_pass_cases']), 'Required verbose unit PASS missing')
    require(set(meta['unit_pass_cases']) == set(contract['required_pass_cases']), 'Unit pass-case metadata mismatch')
    require("'build' finished successfully" in (logs / 'build.log').read_text(encoding='utf-8'),
            'Ordinary optimized build completion missing')
    require(contract['suite'] in (logs / 'unit-suites.log').read_text().splitlines(), 'Suite registration missing')
    compat = read(logs / 'unit-compatibility.json')
    require(compat['source_sha'] == SOURCE and compat['file'] == contract['file'] and
            compat['original_sha256'] == compat['restored_sha256'] == contract['original_sha256'] and
            compat['patched_sha256'] == contract['patched_sha256'] and
            compat['tracked_diff_after_restore'] == '', 'Compatibility restoration mismatch')
    require(digest(logs / 'command-line-test-suite.original') == contract['original_sha256'] and
            (logs / 'unit-compatibility.patch').read_text() == contract['exact_diff'], 'Compatibility bytes mismatch')
    commands = read(logs / 'unit-commands.json')
    require(commands[:2] == [['./waf','configure','--enable-tests','--build-profile=optimized','--out=build-ws29-tests'],
                            ['./waf','--out=build-ws29-tests','-j2']] and
            commands[-1][1:] == ['--suite=' + contract['suite'], '--verbose'], 'Unit command chain mismatch')
    return dict(id=contract['new_id'], source_sha=SOURCE, passed_cases=contract['required_pass_cases'],
                resource=resources(folder, contract['new_id'], plan['resource_limits'], 'TESTED'),
                compatibility_receipt_sha256=digest(logs / 'unit-compatibility.json'))


def verify_physical_targets(folder, cell):
    """Reconstruct interface numbering from frozen topology, independently of telemetry."""
    if cell['fault'] not in (20,23):
        return
    lines = (folder / 'config/topology.txt').read_text().splitlines()
    switches = set(map(int, lines[1].split())); ports = {}; adjacency = {}
    for line in lines[2:]:
        if not line.strip():
            continue
        a,b = map(int, line.split()[:2])
        ports[a] = ports.get(a,0) + 1; ports[b] = ports.get(b,0) + 1
        adjacency[a,ports[a]] = (b,ports[b]); adjacency[b,ports[b]] = (a,ports[a])
    tor = cell['fault_tor']
    local = [(n,p) for (n,p), (peer,_) in adjacency.items() if n == tor and peer in switches and
             (cell['fault'] == 23 or p == cell['fault_port'])]
    targets = set(local) | {adjacency[k] for k in local}
    require(bool(targets), 'Physical targets absent from topology')
    meta = read(folder / 'metadata.json'); raw = folder / 'raw' / str(meta['raw_directory'])
    events = [observations.fields(line) for line in (raw / 'config.log').read_text().splitlines()
              if line.startswith('WS29_LINK ')]
    expected = Counter((n,p,up,t) for n,p in targets for up,t in
                       ((0,cell['fault_start_ns']),(1,cell['fault_end_ns'])))
    actual = Counter(tuple(int(r[k]) for k in ('switch','port','up','time_ns')) for r in events)
    require(actual == expected, 'Physical events changed host port, target, endpoint, timing or multiplicity')


def verify_cell(plan, cell):
    folder = ROOT / 'results' / cell['id']
    row = engine.local_verify(plan, cell, persist=False)
    verify_physical_targets(folder, cell)
    meta = read(folder / 'metadata.json')
    obs = observations.observation((folder / 'raw' / str(meta['raw_directory']) / 'config.log').read_text().splitlines(), cell)
    immutable(CONTROL / (cell['label'] + '.observation.json'), obs)
    immutable(CONTROL / (cell['label'] + '.verified.json'), row)
    return row


def prerequisites(plan, contract, selected):
    unit_path = CONTROL / 'unit.verified.json'
    require(unit_path.is_file(), 'New physical C++ unit not accepted')
    require(read(unit_path) == verify_unit(ROOT / 'results' / contract['new_id'], plan, contract), 'Unit raw changed')
    old = read(engine.PLAN); by_label = {c['label']:c for c in old['cells']}
    for item in plan['reuse']:
        cell = by_label[item['label']]
        receipt = engine.CONTROL / (cell['label'] + '.verified.json')
        require(receipt.is_file() and read(receipt) == engine.local_verify(old, cell, persist=False), 'Reused old raw changed')
    immutable(CONTROL / 'reused-old-evidence.json',dict(source_sha=OLD,
        boundary='Old-SHA runtime PASS retained; static impact audit does not create new-SHA runtime evidence.',
        evidence=[dict(**item,receipt_sha256=digest(engine.CONTROL / (item['label'] + '.verified.json')))
                  for item in plan['reuse']]))
    for cell in plan['cells'][:plan['cells'].index(selected)]:
        require((CONTROL / (cell['label'] + '.verified.json')).is_file(), 'Previous recovery cell not accepted')
        verify_cell(plan, cell)


def manifest(plan, contract, lock):
    return dict(source_sha=SOURCE, unit_id=plan['unit_id'], lock_sha256=LOCK_SHA,
        plan_path=str(EVIDENCE / 'ws29-segmented-recovery-plan.json'),
        unit_contract_path=str(EVIDENCE / 'ws29-recovery-unit-contract.json'),
        old_stop_preserved=True, authorization='Separate main-review GO per stage; no approval generated by prepare',
        unit_build=engine.build_arguments(dict(id=plan['unit_id']), SOURCE) +
                   ['--unit-suite',contract['suite'],'--unit-compat'],
        cells=[dict(label=c['label'], id=c['id'], build=engine.build_arguments(c,SOURCE),
                    run=engine.run_arguments(c)) for c in plan['cells']],
        resource_logs=dict(unit='logs/resource-{samples.jsonl,summary.json}',
                           simulation_build='logs/build-resource-{samples.jsonl,summary.json}',
                           simulation='logs/resource-{samples.jsonl,summary.json}'))


def stages(plan, contract):
    for name,labels in (('unit',('unit',)),) + STAGES:
        paths = [CONTROL / (label + '.verified.json') for label in labels]
        if not all(p.is_file() for p in paths):
            break
        immutable(CONTROL / ('stage-' + name + '.json'),dict(stage=name,source_sha=SOURCE,
            ids=[read(p)['id'] for p in paths],receipt_sha256=[digest(p) for p in paths],
            A06='OPEN; engineering PASS is not natural adoption evidence'))


def execute(phase, label=None):
    plan, contract, lock = load()
    if phase == 'prepare':
        immutable(EVIDENCE / 'ws29-segmented-recovery-entry.json', manifest(plan,contract,lock))
        return dict(prepared=True, new_cells=13, reused_old_cells=14, remote_actions=0)
    is_unit = phase.startswith('unit-')
    cell = dict(id=plan['unit_id'], label='unit') if is_unit else next((c for c in plan['cells'] if c['label']==label), None)
    require(cell is not None, 'Explicit recovery label required')
    stage = 'unit' if is_unit else next(name for name,group in STAGES if label in group)
    authorize(plan, lock, stage)  # Rejected GO causes no remote call and no new failure receipt.
    try:
        if not is_unit:
            prerequisites(plan,contract,cell)
        accepted = CONTROL / (cell['label'] + '.verified.json')
        if phase in ('unit-collect','collect') and accepted.is_file():
            row = verify_unit(ROOT / 'results' / cell['id'],plan,contract) if is_unit else verify_cell(plan,cell)
            require(read(accepted) == row, 'Accepted raw changed')
            return dict(id=cell['id'],already_verified=True,remote_actions=0)
        worker_identity(lock)
        if phase in ('unit-build','build'):
            remote.local_fork(str(ROOT),require_pushed=True)
            engine.preflight(cell,plan['resource_limits'],True,source_sha=SOURCE,
                             record=lambda c,e,**d: record(plan,c,e,**d))
            args = engine.build_arguments(cell,SOURCE)
            if is_unit:
                args += ['--unit-suite',contract['suite'],'--unit-compat']
            command(plan,cell,args)
            if not is_unit:
                engine.preflight(cell,plan['resource_limits'],False,source_sha=SOURCE,
                                 record=lambda c,e,**d: record(plan,c,e,**d))
            return dict(id=cell['id'],next='unit-collect' if is_unit else 'start same label')
        if phase == 'start':
            remote.local_fork(str(ROOT),require_pushed=True)
            engine.preflight(cell,plan['resource_limits'],False,source_sha=SOURCE,
                             record=lambda c,e,**d: record(plan,c,e,**d))
            command(plan,cell,engine.run_arguments(cell))
            output = command(plan,cell,['status',cell['id']])
            meta = json.JSONDecoder().raw_decode(output.lstrip())[0]
            require(meta['git_commit'] == SOURCE and meta['status'] in ('RUNNING','SUCCEEDED'), 'Unexpected post-start state')
            record(plan,cell,'started',pid=meta.get('pid'),status=meta['status'],
                   check_after_utc=(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(minutes=30)).isoformat())
            return dict(id=cell['id'],next='collect same label after about 30 minutes; no next-cell launch')
        require(phase in ('unit-collect','collect'), 'Unsupported phase')
        folder = ROOT / 'results' / cell['id']
        if not folder.exists():
            output = command(plan,cell,['status',cell['id']])
            meta = json.JSONDecoder().raw_decode(output.lstrip())[0]
            require(meta['git_commit'] == SOURCE, 'Status source mismatch')
            if meta['status'] in ('BUILDING','TESTING','RUNNING'):
                return dict(id=cell['id'],status=meta['status'],next='wait; do not advance')
            require(meta['status'] in ('TESTED','SUCCEEDED','UNIT_FAILED','BUILD_FAILED','FAILED'), 'Not terminal')
            command(plan,cell,['fetch',cell['id']])
            require(meta['status'] == ('TESTED' if is_unit else 'SUCCEEDED'), 'Terminal failure; raw preserved')
        row = verify_unit(folder,plan,contract) if is_unit else verify_cell(plan,cell)
        if is_unit:
            immutable(CONTROL / 'unit.verified.json',row)
        stages(plan,contract)
        record(plan,cell,'verified',verification=row)
        stop_guard(plan)
        return dict(id=cell['id'],verified=True)
    except Exception as error:
        if not (CONTROL / 'STOP.json').exists():
            immutable(CONTROL / 'STOP.json',dict(id=cell['id'],phase=phase,error=str(error)))
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('prepare','unit-build','unit-collect','build','start','collect'))
    parser.add_argument('--label',choices=tuple(label for _,group in STAGES for label in group))
    args=parser.parse_args()
    print(json.dumps(execute(args.phase,args.label)))


if __name__ == '__main__':
    main()
