"""Bounded local supervision of the unchanged, guarded WS30 r2 entry.

Only the identified read-only SSH log-size probe may trigger a restart.
No build/run command is retried here; r2 reconciles all state on every entry.
"""
import argparse
import contextlib
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import resume_ws30_v14 as resume
import run_ws30_v14 as v

POLICY = v.EV / 'ws30-v14-formal-rest-transport-supervision-r1.json'
LOCK = v.ROOT / 'results/ws30-v14-transport-supervisor.lock'
DELAYS = (10, 30)


def retry_reason(state, stderr, previous_event_count):
    """Fail closed for identity, admission, mutation, validation, or stale errors."""
    if state.get('failures') or len(state.get('events', [])) <= previous_event_count:
        return None
    if any(x in stderr.lower() for x in (
            'host key verification failed', 'remote host identification has changed',
            'permission denied', 'authentication failed')):
        return None
    events = state['events'][previous_event_count:]
    if any(e['event'] in ('start_attention', 'admission_stop', 'validation_failed_preserved',
                          'failed_preserved', 'build_failed_preserved') for e in events):
        return None
    last = events[-1]
    error = last.get('error', '')
    if (last.get('event') != 'controller_stopped'
            or 'import glob,os,json; ids=' not in error
            or 'config.log' not in error
            or not ('returned non-zero exit status 255' in error
                    or 'timed out after 45 seconds' in error)):
        return None
    return 'identified_read_only_log_probe_transport_failure'


def preflight(session):
    policy = v.read(POLICY)
    v.require(policy.get('execution_authorized') is True, 'Supervisor authorization absent')
    v.require(policy['supervisor_sha256'] == v.sha(Path(__file__)), 'Supervisor bytes changed')
    v.require(policy['resume_plan_sha256'] == v.sha(resume.PLAN), 'r2 plan changed')
    v.require(policy['authorization_sha256'] == v.sha(resume.AUTH), 'r2 authorization changed')
    v.require(policy['maximum_transport_restarts'] == len(DELAYS)
              and policy['backoff_seconds'] == list(DELAYS), 'Retry budget changed')
    # This validates all twelve original controls, sealed receipts, scope, inputs,
    # and the ACTUAL Luna/Medium context before launching any child or SSH.
    resume.authorize(session)
    state = v.read(resume.STATE)
    v.require(not state['failures'], 'Preserved failure blocks supervised restart')
    return policy


@contextlib.contextmanager
def supervisor_lock():
    LOCK.parent.mkdir(exist_ok=True)
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
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def run(session):
    preflight(session)
    token = uuid.uuid4().hex
    events = v.ROOT / ('results/ws30-v14-transport-supervisor-' + token + '.jsonl')

    def note(event, **fields):
        row = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'event': event, 'supervisor_pid': os.getpid(), **fields}
        with events.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(row, sort_keys=True) + '\n')
            stream.flush(); os.fsync(stream.fileno())

    with supervisor_lock():
        for attempt in range(len(DELAYS) + 1):
            preflight(session)
            prior = len(v.read(resume.STATE)['events'])
            stem = v.ROOT / ('results/ws30-v14-transport-' + token + '-' + str(attempt))
            out_path, err_path = Path(str(stem) + '.out.log'), Path(str(stem) + '.err.log')
            with out_path.open('xb') as out, err_path.open('xb') as err:
                child = subprocess.Popen(
                    [sys.executable, str(v.ROOT / 'scripts/resume_ws30_v14.py'),
                     'run', '--session-file', str(session)],
                    cwd=str(v.ROOT), stdin=subprocess.DEVNULL, stdout=out, stderr=err)
                note('r2_child_started', attempt=attempt, child_pid=child.pid,
                     stdout=str(out_path), stderr=str(err_path))
                code = child.wait()
            state = v.read(resume.STATE)
            if code == 0:
                v.require(len(state['verified']) == 140 and not state['failures'],
                          'Child success without complete verified state')
                note('complete', verified=140)
                return 0
            reason = retry_reason(state, err_path.read_text(encoding='utf-8', errors='replace'), prior)
            if reason is None or attempt == len(DELAYS):
                note('stopped', child_exit=code, retry_reason=reason,
                     retry_budget_exhausted=attempt == len(DELAYS))
                return code or 1
            # No remote mutations here. The next original r2 child acquires its
            # own lock, checks fresh resource/ownership/path state, and reuses
            # BUILT/RUNNING/SUCCEEDED IDs without repeating build/run requests.
            preflight(session)
            note('bounded_transport_restart', reason=reason, delay=DELAYS[attempt])
            time.sleep(DELAYS[attempt])
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('inspect', 'run'), nargs='?', default='inspect')
    parser.add_argument('--session-file', type=Path)
    args = parser.parse_args()
    if args.command == 'inspect':
        print(json.dumps({'new_simulations': 0, 'maximum_transport_restarts': len(DELAYS),
                          'original_r2_entry': str(v.ROOT / 'scripts/resume_ws30_v14.py')}))
        return 0
    return run(args.session_file)


if __name__ == '__main__':
    raise SystemExit(main())
