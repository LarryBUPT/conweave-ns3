#!/usr/bin/env python3
"""Prepare or advance ONE frozen WS29 regression cell; never advance implicitly."""
import argparse
import datetime
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path

import remote_experiment as remote
from verify_ws29_engineering import verify
from ws29_evidence_checks import verify_reference

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'docs/research/evidence/ws29-engineering-plan-observation-v2.json'
PLAN_SHA = '5db623e7b38109a43ef0c37e0203e29713c896fe61e4d44581fd9512b551e8fd'
SOURCE = '3e68b3604e93cf34a4d938ebb48f1b1e0cfc988f'
ORIGINAL = 'b7285686202442d47d339fd5817e9001c47bfc23377c8a8f5f596ba694373881'
LABELS = ('legacy-v2-hb200', 'mixed8-c0', 'main-c0')
CONTROL = ROOT / 'results/ws29-regression-control'
MANIFEST = ROOT / 'docs/research/evidence/ws29-regression-entry.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def load_plan():
    require(digest(PLAN) == PLAN_SHA, 'Frozen 27-cell plan changed')
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    cells = plan['cells'][:3]
    require(tuple(c['label'] for c in cells) == LABELS, 'Regression order changed')
    require(all(c['source_sha'] == SOURCE for c in cells), 'Frozen simulator SHA changed')
    for cell in cells:
        verify_reference(cell['reference'])
        for name, expected in [('config/' + cell['trace'], cell['trace_sha256']),
                               ('config/' + cell['topology'] + '.txt', cell['topology_sha256'])]:
            data = subprocess.check_output(['git', 'show', SOURCE + ':' + name], cwd=ROOT)
            require(hashlib.sha256(data).hexdigest() == expected, 'Frozen input changed: ' + name)
    return plan, cells


def run_arguments(cell):
    options = dict(lb=cell['mode'], pfc=cell['pfc'], irn=cell['irn'], bw=cell['bw'],
                   buffer=cell['buffer'], topo=cell['topology'], cdf='AliStorage2019',
                   flow_file=cell['trace'], simul_time=cell['simul_time'], netload=10,
                   max_concurrent=1, ws13_diag=0, ws25_diag=0, ws28_tail_diag=0,
                   ws18_admission=0, ws18_path=int(cell['arm'] < 0),
                   ws18_admission_rate_gbps=400, ws29_arm=cell['arm'],
                   ws21_port_events=0, ws21_port_max_bytes=268435456,
                   ws21_heartbeat_fault_mode=0, ws21_heartbeat_fault_tor=0,
                   ws21_heartbeat_fault_port=0, ws21_heartbeat_fault_start_ns=0,
                   ws21_heartbeat_fault_end_ns=0)
    options.update(cell['control_options'])
    options.update({'ws29_' + k: cell[k] for k in
                    ('fault', 'fault_tor', 'fault_port', 'fault_start_ns', 'fault_end_ns')})
    args = ['run', cell['id']]
    for name, value in options.items():
        args.extend(['--' + name.replace('_', '-'), str(value)])
    return args


def build_arguments(cell):
    return ['build', '--repo-local', str(ROOT), '--id', cell['id'], '--source-sha', SOURCE]


def receipt(cell, event, **data):
    CONTROL.mkdir(parents=True, exist_ok=True)
    row = dict(id=cell['id'], event=event, time_utc=datetime.datetime.now(
        datetime.timezone.utc).isoformat(), plan_sha256=PLAN_SHA, source_sha=SOURCE, **data)
    with (CONTROL / 'commands-and-events.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(row, sort_keys=True) + '\n')


def immutable(path, data):
    text = json.dumps(data, indent=2, sort_keys=True) + '\n'
    require(not path.exists() or path.read_text(encoding='utf-8') == text,
            'Receipt changed; preserve existing file: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(text, encoding='utf-8')


def local_verify(plan, cell):
    folder = ROOT / 'results' / cell['id']
    row = verify(folder, cell, plan['resource_limits'])
    build = json.loads((folder / 'logs/build-resource-summary.json').read_text())
    samples = [json.loads(x) for x in (folder / 'logs/build-resource-samples.jsonl').read_text().splitlines() if x]
    limits = plan['resource_limits']
    require(build['id'] == cell['id'] and build['final_status'] == 'BUILT' and
            build['samples'] == len(samples) > 0, 'Build resource receipt identity/count')
    require(max(s['process_tree_rss_mib'] for s in samples) <= limits['rss_mib_max'] and
            min(s['mem_available_gib'] for s in samples) >= limits['available_memory_gib_min'] and
            min(s['free_gib'] for s in samples) >= limits['free_disk_gib_min'] and
            max(s['load_1m'] for s in samples) <= limits['load_1m_max'], 'Build resource stop line')
    row['build_resource'] = build
    immutable(CONTROL / (cell['label'] + '.verified.json'), row)
    return row


def guard_sequence(plan, cells, selected):
    require(not (CONTROL / 'STOP.json').exists(), 'Failure stop receipt exists; no automatic retry')
    for cell in cells[:cells.index(selected)]:
        require((CONTROL / (cell['label'] + '.verified.json')).exists(),
                'Previous cell not accepted: ' + cell['id'])
        local_verify(plan, cell)  # Recheck raw evidence, not only a success flag.


def command(cell, args):
    argv = [sys.executable, str(ROOT / 'scripts/remote_experiment.py')] + args
    result = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=7200 if args[0] == 'build' else 1800 if args[0] == 'fetch' else 90)
    CONTROL.mkdir(parents=True, exist_ok=True)
    path = CONTROL / (cell['label'] + '.' + args[0] + '.' + str(
        datetime.datetime.now().timestamp()).replace('.', '-') + '.log')
    path.write_bytes(result.stdout)
    receipt(cell, 'command', argv=argv, exit_code=result.returncode, output_log=str(path))
    require(result.returncode == 0, 'Command failed; preserve ID and log: ' + str(path))
    return result.stdout.decode('utf-8', errors='replace')


def status(cell):
    output = command(cell, ['status', cell['id']])
    require('process_alive=False' not in output, 'Worker interrupted; preserve ID and inspect logs')
    return json.JSONDecoder().raw_decode(output.lstrip())[0]


def preflight(cell, limits, fresh):
    # No writes on the remote host. Only attempt an existing lock non-blockingly.
    code = '''import os,json,glob,subprocess,fcntl,hashlib
root='/home/fnl/lzy'; ident=%r; fresh=%r
base=root+'/results/'+ident; run=root+'/runs/'+ident; source=run+'/source'
assert os.path.realpath(root)==root
with open('/proc/meminfo') as f: mem=dict(x.split(':',1) for x in f if ':' in x)
listing=subprocess.check_output(['ps','-eo','uid,pid,stat,comm','--no-headers']).decode().splitlines()
others=[]; simul=[]
for line in listing:
 uid,pid,stat,comm=line.split()
 if int(uid)>=1000 and int(uid)!=os.getuid() and not stat.startswith('Z'): others.append(line)
 if comm.startswith('network-load-ba'): simul.append(line)
active=[]
for p in glob.glob(root+'/results/*/metadata.json'):
 d=json.load(open(p))
 if d.get('status') in ('BUILDING','TESTING','RUNNING'):
  try: os.kill(int(d['pid']),0); active.append([d.get('experiment_id'),d.get('status'),d['pid']])
  except ProcessLookupError: pass
lock=root+'/.research-workflow/simulation-start.lock'; lock_free=True
assert not os.path.islink(lock)
if os.path.exists(lock):
 fd=os.open(lock,os.O_RDONLY)
 try:
  try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(fd,fcntl.LOCK_UN)
  except IOError: lock_free=False
 finally: os.close(fd)
data=dict(other_users=others,simulations=simul,active_metadata=active,lock_free=lock_free,
 mem_available_gib=int(mem['MemAvailable'].split()[0])/float(1024**2),
 free_gib=os.statvfs(root).f_bavail*os.statvfs(root).f_frsize/float(1024**3),load_1m=os.getloadavg()[0])
assert not (others or simul or active) and lock_free
if fresh: assert not os.path.lexists(base) and not os.path.lexists(run)
else:
 assert os.path.realpath(source)==source and not os.path.islink(source)
 d=json.load(open(base+'/metadata.json'));assert d['status']=='BUILT'
 data['head']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source).decode().strip()
 data['tracked_diff']=subprocess.check_output(['git','diff','--name-only'],cwd=source).decode().strip()
 data['core_sha256']=hashlib.sha256(open(source+'/src/core/test/command-line-test-suite.cc','rb').read()).hexdigest()
 assert data['head']==%r and not data['tracked_diff'] and data['core_sha256']==%r
 assert not d.get('unit_compatibility') and not d.get('unit_suite')
 assert not os.path.lexists(source+'/build-ws29-tests')
print(json.dumps(data,sort_keys=True))
''' % (cell['id'], fresh, SOURCE, ORIGINAL)
    cfg = remote.config()
    result = subprocess.run(remote.ssh_base(cfg) + ['python3 -c ' + shlex.quote(code)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    output = result.stdout.decode('utf-8', errors='replace')
    receipt(cell, 'fresh-preflight' if fresh else 'unpatched-source-preflight',
            exit_code=result.returncode, output=output)
    require(result.returncode == 0, 'Preflight failed; no new action')
    data = json.loads(output)
    require(data['mem_available_gib'] >= limits['available_memory_gib_min'] and
            data['free_gib'] >= limits['free_disk_gib_min'] and
            data['load_1m'] <= limits['load_1m_max'], 'Resource preflight stop line')
    return data


def prepare(cells, plan):
    data = dict(kind='WS29 three regressions only; execution awaits separate GO',
                source_sha=SOURCE, plan_sha256=PLAN_SHA, resource_limits=plan['resource_limits'],
                order=list(LABELS), cells=[])
    for cell in cells:
        data['cells'].append(dict(id=cell['id'], label=cell['label'],
            build=build_arguments(cell), run=run_arguments(cell),
            collect=['python', 'scripts/run_ws29_regressions.py', 'collect', '--label', cell['label']],
            reference=cell['reference']['id'], expected_fct_sha256=cell['reference']['fct_sha256']))
    immutable(MANIFEST, data)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'build', 'start', 'collect', 'verify'))
    parser.add_argument('--label', choices=LABELS)
    args = parser.parse_args()
    plan, cells = load_plan()
    if args.phase == 'prepare':
        prepare(cells, plan)
        print(json.dumps(dict(prepared=3, entry=str(MANIFEST), remote_actions=0)))
        return
    require(args.label is not None, 'One explicit --label is required')
    cell = next(c for c in cells if c['label'] == args.label)
    guard_sequence(plan, cells, cell)
    try:
        if args.phase == 'build':
            remote.local_fork(str(ROOT), require_pushed=True)
            preflight(cell, plan['resource_limits'], fresh=True)
            command(cell, build_arguments(cell))
            preflight(cell, plan['resource_limits'], fresh=False)
            print(json.dumps(dict(id=cell['id'], status='BUILT', next='start same label')))
        elif args.phase == 'start':
            remote.local_fork(str(ROOT), require_pushed=True)
            preflight(cell, plan['resource_limits'], fresh=False)
            command(cell, run_arguments(cell))
            meta = status(cell)
            require(meta['git_commit'] == SOURCE and meta['status'] in ('RUNNING', 'SUCCEEDED'),
                    'Unexpected post-start state')
            receipt(cell, 'started', pid=meta.get('pid'), status=meta['status'],
                    check_after_utc=(datetime.datetime.now(datetime.timezone.utc) +
                                    datetime.timedelta(minutes=30)).isoformat())
            print(json.dumps(dict(id=cell['id'], pid=meta.get('pid'), status=meta['status'],
                                  next='collect same label at terminal state; no next-cell launch')))
        else:
            folder = ROOT / 'results' / cell['id']
            if args.phase == 'collect' and not folder.exists():
                meta = status(cell)
                if meta['status'] == 'RUNNING':
                    print(json.dumps(dict(id=cell['id'], status='RUNNING', next='wait; do not advance')))
                    return
                require(meta['status'] in ('SUCCEEDED', 'FAILED', 'BUILD_FAILED'), 'Not terminal')
                command(cell, ['fetch', cell['id']])
                require(meta['status'] == 'SUCCEEDED', 'Terminal failure; raw preserved')
            row = local_verify(plan, cell)
            receipt(cell, 'verified', resource=row['resource'], fct_sha256=row['fct_sha256'])
            print(json.dumps(dict(id=cell['id'], verified=True, resource=row['resource'])))
    except Exception as error:
        immutable(CONTROL / 'STOP.json', dict(id=cell['id'], phase=args.phase, error=str(error)))
        raise


if __name__ == '__main__':
    main()
