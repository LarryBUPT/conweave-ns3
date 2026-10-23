#!/usr/bin/env python3
"""Local-only segmented recovery materials; never contact a remote host."""
import copy
import difflib
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/research/evidence'
OLD = '3e68b3604e93cf34a4d938ebb48f1b1e0cfc988f'
SOURCE = 'ec0c718f435a54f684d18e6933583335a60f81d5'
PREFIX = '20261023-090000-ws29-p1-'
STAGES = (
    ('physical', ('link-23-c0', 'link-20-c0', 'link-23-c1', 'link-20-c1', 'link-23-c2', 'link-20-c2')),
    ('baseline', ('main-c0',)),
    ('synthetic', ('synthetic-15', 'synthetic-16', 'synthetic-17')),
    ('cost', ('main-c1', 'main-c2', 'main-c3')),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(rev, name):
    return subprocess.check_output(['git', 'show', rev + ':' + name], cwd=ROOT)


def write(name, row):
    path = EVIDENCE / name
    text = json.dumps(row, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    if path.exists() and path.read_text(encoding='utf-8') != text:
        raise RuntimeError('Material changed; review existing file: ' + name)
    if not path.exists():
        path.write_text(text, encoding='utf-8')
    return sha(path.read_bytes())


def prepare():
    original_path = EVIDENCE / 'ws29-engineering-plan-observation-v2.json'
    original = json.loads(original_path.read_text(encoding='utf-8'))
    assert sha(original_path.read_bytes()) == '5db623e7b38109a43ef0c37e0203e29713c896fe61e4d44581fd9512b551e8fd'
    labels = [label for _, group in STAGES for label in group]
    by_label = {c['label']: c for c in original['cells']}
    plan = copy.deepcopy(original)
    plan.update(kind='WS29 segmented engineering recovery; explicit stage GO required',
                source_sha=SOURCE, unit_id=PREFIX + 'unit', max_concurrent=1,
                stages=[dict(name=name, labels=list(group)) for name, group in STAGES],
                cells=[])
    for label in labels:
        cell = copy.deepcopy(by_label[label])
        cell.update(id=PREFIX + label, source_sha=SOURCE)
        plan['cells'].append(cell)
    reused = [c for c in original['cells'] if c['label'] not in labels]
    plan['reuse'] = [dict(label=c['label'], id=c['id'], source_sha=OLD) for c in reused]
    plan['origin_plan_sha256'] = sha(original_path.read_bytes())
    plan['original_stop_sha256'] = '731fd085b1a7a59dd998c79488c1307d70fe4f20302f4499b7859d1a88ada7e9'
    core_name = 'src/core/test/command-line-test-suite.cc'
    core = blob(SOURCE, core_name)
    token = b'Parse (const CommandLine &cmd, int n, ...)'
    assert core.count(token) == 2
    patched = core.replace(token, b'Parse (CommandLine &cmd, int n, ...)')
    contract = dict(source_sha=SOURCE, new_id=plan['unit_id'], file=core_name,
                    original_sha256=sha(core), patched_sha256=sha(patched),
                    exact_diff=''.join(difflib.unified_diff(core.decode().splitlines(True),
                        patched.decode().splitlines(True), fromfile='a/' + core_name, tofile='b/' + core_name)),
                    suite='devices-point-to-point', build_mode='optimized', cpu_jobs=2,
                    required_pass_cases=[
                        'devices-point-to-point', 'PointToPoint',
                        'IRN timeout is deferred only for an actual PFC pause and its resume grace',
                        'WS-21 feedback header serialization and validation',
                        'WS-21 heartbeat header serialization and validation',
                        'WS-29 all-link faults preserve host links without telemetry'],
                    scope='Fresh source: ordinary optimized build first, then disclosed test-only compatibility build; restore source in finally. Not a simulation binary.',
                    required_logs=['build.log', 'ws29-point-to-point-unit-test.log', 'unit-suites.log',
                        'unit-commands.json', 'unit-compatibility.json', 'unit-compatibility.patch',
                        'command-line-test-suite.original', 'resource-summary.json', 'resource-samples.jsonl'],
                    availability='NOT CHECKED; local preparation only')
    changed = subprocess.check_output(['git', 'diff', '--name-only', OLD, SOURCE], cwd=ROOT, text=True).splitlines()
    simulation_changes = [p for p in changed if p.startswith(('scratch/', 'src/', 'config/')) or p == 'run.py']
    assert set(simulation_changes) == {'scratch/network-load-balance.cc',
        'src/point-to-point/model/switch-node.cc', 'src/point-to-point/test/point-to-point-test.cc'}
    functions = ['DoLbClassReserve', 'ChooseWs29Feedback', 'GetOutDev', 'TouchWs21Heartbeat',
                 'RecordWs21PortEvent', 'RecordWs21PortBoundary']
    def function(data, name):
        text = data.decode(); at = text.index('SwitchNode::' + name + '(')
        start = text.index('{', at); depth = 1; end = start + 1
        while depth:
            depth += (text[end] == '{') - (text[end] == '}'); end += 1
        return text[at:end].encode()
    before = blob(OLD, 'src/point-to-point/model/switch-node.cc')
    after = blob(SOURCE, 'src/point-to-point/model/switch-node.cc')
    hashes = {}
    for name in functions:
        a, b = function(before, name), function(after, name)
        assert a == b
        hashes[name] = dict(old_sha256=sha(a), new_sha256=sha(b), byte_identical=True)
    # All nonphysical fault branches follow this boundary, and remain byte-identical.
    a = function(before, 'Ws29Fault'); b = function(after, 'Ws29Fault')
    boundary = b'if (fault == 9)'
    assert a[a.index(boundary):] == b[b.index(boundary):]
    hashes['Ws29Fault_nonphysical_suffix'] = dict(byte_identical=True,
        old_sha256=sha(a[a.index(boundary):]), new_sha256=sha(b[b.index(boundary):]))
    reuse_rows = []
    for c in reused:
        if c['arm'] < 0:
            reason = 'WS29 disabled; host-port initialization and physical fault paths unchanged for this cell.'
        elif c['control_options']['ws21_heartbeat']:
            reason = 'Host ports already initialized by heartbeat; no fault20-24 call; nonphysical suffix and routing/feedback functions byte-identical.'
        else:
            reason = 'Host set newly populated; fault=0, heartbeat=0, port-events=0: all set readers inactive for this cell; routing/feedback functions byte-identical.'
        assert c['fault'] not in (20, 21, 22, 23, 24)
        reuse_rows.append(dict(label=c['label'], id=c['id'], source_sha=OLD, reason=reason,
                               claim='Verified only on old SHA; static impact audit supports reuse, not a new-SHA runtime PASS.'))
    impact = dict(old_source_sha=OLD, source_sha=SOURCE, changed_files=changed,
        simulation_changes=simulation_changes,
        other_changes='Intervening local controller, verifier, test and documentation commits are listed separately from the simulation production diff; run.py and all config inputs are unchanged.',
        unchanged_functions=hashes, reused= reuse_rows,
        initialization_readers=['RecordWs21PortEvent: disabled by port-events=0',
            'TouchWs21Heartbeat: disabled by heartbeat=0', 'Ws29Fault bulk physical: fault23/24 only',
            'Ws29Fault abnormal ACK ingress selection: already initialized in protocol heartbeat cells'],
        mandatory_revalidation=[dict(label='link-20-c0', reason='Direct physical down/up and new runtime guards changed; compare single-link baseline with all-link failure under same new SHA.'),
            dict(label='main-c0', reason='Same-SHA natural baseline required for C1-C0, C2-C0, C2-C1 and C3 cost interpretation; old baseline kept as compatibility evidence.')],
        mechanism_budget='Engineering correction; no candidate/diagnostic-revision slot consumed (main review confirmed).',
        cause_evidence='Fixed source and raw log boundary support the path; no runtime backtrace or dynamic reproduction.',
        runtime_validation='NOT RUN')
    lock = dict(source_sha=SOURCE, unit_id=plan['unit_id'], files={})
    for name, row in [('ws29-segmented-recovery-plan.json', plan),
                      ('ws29-recovery-unit-contract.json', contract),
                      ('ws29-recovery-impact-audit.json', impact)]:
        lock['files'][name] = write(name, row)
    lock['worker_sha256'] = sha((ROOT / 'scripts/remote_worker.py').read_bytes())
    lock['controller_sha256'] = {name: sha((ROOT / 'scripts' / name).read_bytes()) for name in (
        'prepare_ws29_recovery.py', 'remote_experiment.py', 'run_ws29_regressions.py',
        'run_ws29_engineering.py', 'verify_ws29_engineering.py', 'ws29_evidence_checks.py')}
    digest = write('ws29-recovery-lock.json', lock)
    print(json.dumps(dict(lock_sha256=digest, new_cells=len(labels), reused=len(reused), remote_actions=0)))


if __name__ == '__main__':
    prepare()
