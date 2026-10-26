"""Guarded 17-cell technical-rest entry; inspect/preflight do not execute cells.

run requires a released receipt and empty IDs. resume reconciles occupied IDs
against the retained state without reissuing builds or successful simulations.
"""
import argparse
from contextlib import contextmanager
import datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
import time
import traceback

import run_ws30_v14_technical_single as single
import supervise_ws30_v14_transport as transport

v, resume = single.v, single.resume
PHASE, CAP, SOURCE = 'technical-rest', 4, single.SOURCE
IDS = tuple('20261026-120000-w30v14-'+suffix for suffix in (
    't02-e-o2', 't03-q12-o0', 't04-q12-o2', 't05-r12-o0', 't06-r12-o2',
    't07-u12-o0', 't08-u12-o2', 't09-d-o0', 't10-d-o2', 't11-q12-o1',
    't12-h12-o2', 't13-q12-x1', 't14-q12-x2', 't15-r12-x1', 't16-r12-x2',
    't17-u12-x1', 't18-u12-x2'))
AUTH = v.EV/'ws30-v14-technical-rest-authorization-r1.json'
STATE = v.ROOT/'results/ws30-v14-technical-rest-execution-r1.json'
JOURNAL = v.ROOT/'results/ws30-v14-technical-rest-supervision-r1.jsonl'
LOCK = v.ROOT/'results/ws30-v14-technical-rest-supervisor.lock'
MAIN = v.ROOT.parents[1]/'thesis/ws30-v13-technical-single-main-verification.json'
DELAYS = (10, 30)


def note(event, **fields):
    row = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'event': event, 'pid': os.getpid(), **fields}
    with JOURNAL.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(row, sort_keys=True)+'\n')
        stream.flush()
        os.fsync(stream.fileno())


def check_scope(gate, execution=False):
    v.require(gate.get('prepared') is True and gate.get('external_sync_approved') is True,
              'Prepared scope/export receipt required')
    v.require(gate.get('phases') == [PHASE] and gate.get('phase_caps') == {PHASE: CAP}
              and gate.get('ids') == list(IDS) and gate.get('fixed_source_sha') == SOURCE,
              'Only frozen technical-rest 17 IDs at cap 4 are permitted')
    v.require(gate.get('authorization_evidence'), 'Authorization evidence absent')
    v.require(gate.get('maximum_transport_restarts') == len(DELAYS)
              and gate.get('backoff_seconds') == list(DELAYS), 'Retry budget changed')
    if execution:
        v.require(gate.get('approved') is True, 'Main acceptance/release pending')


def dependency(cells):
    state, main = v.read(single.STATE), v.read(MAIN)
    v.require(set(state['verified']) == {single.ID} and not state['pending']
              and not state['failures'] and state['events'][-1]['event'] == 'phase_accepted',
              'Single-cell accepted terminal state required')
    v.require(main.get('verified') is True and main['experiment_id'] == single.ID
              and main['source_sha'] == SOURCE and main['completed_rows'] == 168
              and main['execution_sha256'] == v.sha(single.STATE), 'Main single acceptance differs')
    row = v.verify_common(cells[single.ID])
    v.require(row['fct_sha256'] == main['raw_outputs']['_out_fct.txt']['sha256'],
              'Accepted single FCT changed')
    folder = v.ROOT/'results'/single.ID/'raw'
    for suffix, expected in main['raw_outputs'].items():
        paths = list(folder.rglob('*'+suffix))
        v.require(len(paths) == 1 and v.sha(paths[0]) == expected['sha256'],
                  'Accepted single raw changed: '+suffix)


def validate(session, role):
    context = v.require_model(session, role)  # Before Backend/config/SSH or writes.
    gate = v.read(AUTH)
    check_scope(gate, execution=role == 'supervision')
    v.require(gate['entry_sha256'] == v.sha(Path(__file__)), 'Rest entry changed')
    for rel, digest in gate['repository_evidence_sha256'].items():
        path = (v.ROOT/rel).resolve()
        v.require(path.is_relative_to(v.ROOT) and v.sha(path) == digest,
                  'Sealed repository dependency changed: '+rel)
    v.require(gate['main_acceptance_sha256'] == v.sha(MAIN), 'Main acceptance changed')
    # Execute the unchanged single validation, including all original seals,
    # formal completion, fixed-source Git blobs, input hashes and model policy.
    single.validate(session, role)
    plan, sched, cells = v.load()
    spec = sched['phases'][PHASE]
    v.require(spec['ids'] == list(IDS) and spec['maximum_cap'] == CAP
              and spec['source_sha'] == SOURCE and spec['requires'] == [single.PHASE],
              'Frozen rest schedule changed')
    dependency(cells)
    v.prerequisite(PHASE, plan, sched, cells)  # Keep original recursive raw checks.
    return context, [cells[i] for i in IDS]


def reconcile(cells, state, snapshot, inventory, live_builds=()):
    ids = {c['id'] for c in cells}
    contract = hashlib.sha256(json.dumps(cells, sort_keys=True).encode()).hexdigest()
    v.require(state['contract'] == contract and 1 <= state['cap'] <= CAP
              and set(state['verified']) <= ids and set(state['pending']) <= ids
              and len(state['pending']) == len(set(state['pending']))
              and not state['failures'], 'Protected rest state invalid or failed')
    owned = set(state['verified']) | set(state['pending'])
    for c in cells:
        ident = c['id']
        meta, paths = snapshot['states'][ident], inventory[ident]
        local = resume.local_inventory(c)
        if meta is None:
            v.require(not any(paths.values()) and not local and ident not in state['verified'],
                      'Ambiguous empty metadata/occupied path or build intent: '+ident)
            continue
        v.require(ident in owned and meta['git_commit'] == SOURCE
                  and all(paths.values()), 'Unowned ID/source/path collision: '+ident)
        v.require(meta['status'] in ('BUILT', 'BUILDING', 'RUNNING', 'SUCCEEDED'),
                  'Failed/unknown remote ID must be preserved: '+ident)
        if meta['status'] == 'BUILDING':
            v.require(ident in live_builds, 'Stale BUILDING; inspect without rebuilding: '+ident)
        if ident in state['verified']:
            v.require(meta['status'] == 'SUCCEEDED', 'Verified remote terminal changed')
            v.verify_common(c)


def cached_source(cells):
    origin = v.subprocess.check_output(['git', 'remote', 'get-url', 'origin'],
                                       cwd=v.ROOT, encoding='utf-8').strip()
    v.require(origin == 'https://github.com/LarryBUPT/conweave-ns3.git', 'Personal fork origin differs')
    inputs = {}
    for c in cells:
        inputs['config/'+c['trace']] = c['trace_sha256']
        inputs['config/'+c['topology']+'.txt'] = c['topology_sha256']
    cfg = v.legacy.stage.remote.remote.config()
    code = ("import os,subprocess,hashlib,json; p='/home/fnl/lzy/code/conweave-ns3'; "
            "assert os.path.realpath(p)==p; source=%r; inputs=%r; "
            "subprocess.check_call(['git','cat-file','-e',source+'^{commit}'],cwd=p); "
            "print(json.dumps({r:hashlib.sha256(subprocess.check_output(['git','show',source+':'+r],cwd=p)).hexdigest() for r in inputs}))") % (SOURCE, inputs)
    actual = json.loads(v.subprocess.check_output(v.legacy.stage.remote.remote.ssh_base(cfg)+
                        ['python3 -c '+shlex.quote(code)], encoding='utf-8', timeout=45))
    v.require(actual == inputs, 'Cached fixed-source input changed')
    return {'origin': origin, 'source_sha': SOURCE, 'cached_input_sha256': actual}


def preflight(session, role='analysis', continuing=False):
    context, cells = validate(session, role)
    if continuing:
        v.require(STATE.exists(), 'Resume requires retained protected state')
    else:
        v.require(not STATE.exists(), 'State exists; use read-only reconciliation before resume')
        v.require(not any(resume.local_inventory(c) for c in cells), 'Local ID/staging/intent occupied')
    backend = v.Backend(cells)
    backend.compatible()
    source = cached_source(cells)
    snapshot = backend.snapshot(cells)
    inventory = resume.remote_inventory(cells)
    if continuing:
        # A live build must be evidenced by an actual remote build/waf process.
        cfg = v.legacy.stage.remote.remote.config()
        code = ("import subprocess,json; ids=%r; rows=subprocess.check_output(['ps','-eo','args']).decode().splitlines(); "
                "print(json.dumps([i for i in ids if any(i in r and 'python3 -c' not in r and "
                "('remote_worker.py build ' in r or '/waf' in r) for r in rows)]))") % list(IDS)
        builds = json.loads(v.subprocess.check_output(v.legacy.stage.remote.remote.ssh_base(cfg)+
                            ['python3 -c '+shlex.quote(code)], encoding='utf-8', timeout=45))
        reconcile(cells, v.read(STATE), snapshot, inventory, builds)
    else:
        resume.require_empty(cells, snapshot, inventory)
    resource = backend.gate()
    v.require(not resource['other_users'] and not resource['unexpected_simulation_pids'],
              'Other work blocks admission')
    return {'phase': PHASE, 'ids': list(IDS), 'source_sha': SOURCE, 'cap': CAP,
            'new_builds': 0, 'new_simulations': 0, 'continuing': continuing,
            'actual_context': {k: context.get(k) for k in ('model', 'effort', 'turn_id')},
            'resource': resource, 'remote_inventory': inventory, 'fixed_source': source}


@contextmanager
def scoped_executor(session):
    original_load, previous_auth, previous_argv = v.load, v.AUTH, sys.argv
    def frozen_load():
        active = v.AUTH
        try:
            v.AUTH = single.ORIGINAL_AUTH
            return original_load()
        finally:
            v.AUTH = active
    try:
        v.load, v.AUTH = frozen_load, AUTH
        sys.argv = [str(v.ROOT/'scripts/run_ws30_v14.py'), 'run', '--phase', PHASE,
                    '--session-file', str(session)]
        yield
    finally:
        v.load, v.AUTH, sys.argv = original_load, previous_auth, previous_argv


@contextmanager
def supervisor_lock():
    with LOCK.open('a+b') as handle:
        if handle.tell() == 0:
            handle.write(b'0'); handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt': msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def run(session, continuing=False):
    validate(session, 'supervision')
    with supervisor_lock():
        note('supervisor_started', continuing=continuing)
        for attempt in range(len(DELAYS)+1):
            invoked = False
            try:
                checked = preflight(session, 'supervision', continuing=continuing or attempt > 0)
                note('reconciled_preflight', attempt=attempt, check=checked)
                count = len(v.read(STATE)['events']) if STATE.exists() else 0
                with scoped_executor(session):
                    invoked = True
                    v.main()
                note('supervisor_complete')
                return
            except Exception as error:
                note('supervisor_error_preserved', attempt=attempt, error=str(error),
                     traceback=traceback.format_exc())
                if not invoked or attempt >= len(DELAYS) or not STATE.exists():
                    raise
                reason = transport.retry_reason(v.read(STATE), str(error), locals().get('count', 0))
                if reason is None:
                    raise
                note('read_only_transport_recovery_scheduled', reason=reason, delay=DELAYS[attempt])
                time.sleep(DELAYS[attempt])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('inspect', 'preflight', 'reconcile', 'run', 'resume'),
                        nargs='?', default='inspect')
    parser.add_argument('--session-file', type=Path)
    args = parser.parse_args()
    if args.command == 'inspect':
        print(json.dumps({'phase': PHASE, 'ids': list(IDS), 'cap': CAP, 'source_sha': SOURCE}))
    elif args.command in ('preflight', 'reconcile'):
        print(json.dumps(preflight(args.session_file, continuing=args.command == 'reconcile')))
    else:
        run(args.session_file, continuing=args.command == 'resume')


if __name__ == '__main__':
    main()
