import argparse, ctypes, datetime as dt, json, os, pathlib, runpy, subprocess, sys, time, uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'results' / 'ws25-r4-runtime'
STATE = RUNTIME / 'supervisor-state.json'
LOCK = RUNTIME / 'supervisor.lock'
EVENTS = RUNTIME / 'supervisor-events.jsonl'
RECEIPTS = ROOT / 'results' / 'ws25-v1fix-calibration-receipts-r4.jsonl'
PLAN = ROOT / 'docs' / 'research' / 'evidence' / 'ws25-v1fix-calibration-plan-r4.json'
COMPLETION = ROOT / 'results' / 'ws25-v1fix-calibration-verification-r4.json'
RUNNER = ROOT / 'scripts' / 'run_ws25_v1fix_calibration.py'
REMOTE = ROOT / 'scripts' / 'remote_experiment.py'
PYTHON = sys.executable
POLL_SECONDS = 30
RECOVERY_POLL_SECONDS = 300
MAX_RECOVERIES = 6
BACKOFF = (10, 30, 90, 180, 300, 600)
PROCESS_QUERY_LIMITED_INFORMATION, SYNCHRONIZE = 0x1000, 0x00100000
WAIT_OBJECT_0, WAIT_TIMEOUT = 0, 258

class FILETIME(ctypes.Structure):
    _fields_ = [('low', ctypes.c_ulong), ('high', ctypes.c_ulong)]

def utcnow(): return dt.datetime.now(dt.timezone.utc).isoformat()
def log_event(name, **fields):
    with EVENTS.open('a', encoding='utf-8') as f:
        f.write(json.dumps({'event': name, 'utc': utcnow(), **fields}, sort_keys=True) + '\n')
        f.flush(); os.fsync(f.fileno())

def read_state():
    try: return json.loads(STATE.read_text(encoding='utf-8'))
    except Exception: return {}

def write_state(**fields):
    s = read_state(); s.update(fields); s['updated_utc'] = utcnow()
    # Windows scanners/readers can transiently deny replacement of the shared
    # state path. Give each writer its own temp file and retry the atomic swap.
    tmp = STATE.with_name(STATE.name + '.%s.%s.tmp' % (os.getpid(), uuid.uuid4().hex))
    try:
        with tmp.open('x', encoding='utf-8') as stream:
            json.dump(s, stream, indent=2, sort_keys=True)
            stream.flush(); os.fsync(stream.fileno())
        for attempt in range(8):
            try:
                os.replace(str(tmp), str(STATE))
                return
            except PermissionError:
                if attempt == 7: raise
                time.sleep(min(0.05 * (2 ** attempt), 1.0))
    finally:
        try: tmp.unlink()
        except FileNotFoundError: pass

def open_process(pid):
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.OpenProcess.restype = ctypes.c_void_p
    k.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
    k.GetProcessTimes.argtypes = [ctypes.c_void_p, ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME),
                                  ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME)]
    k.CloseHandle.argtypes = [ctypes.c_void_p]
    k.CloseHandle.restype = ctypes.c_bool
    k.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    k.WaitForSingleObject.restype = ctypes.c_ulong
    k.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    k.GetExitCodeProcess.restype = ctypes.c_bool
    h = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, int(pid))
    if not h: return k, None, None
    creation, exit_t, kernel, user = FILETIME(), FILETIME(), FILETIME(), FILETIME()
    if not k.GetProcessTimes(h, ctypes.byref(creation), ctypes.byref(exit_t), ctypes.byref(kernel), ctypes.byref(user)):
        k.CloseHandle(h); return k, None, None
    ticks = (int(creation.high) << 32) | int(creation.low)
    return k, h, ticks

def pid_is_same(pid, ticks):
    k, h, actual = open_process(pid)
    if not h: return False
    try: return actual == ticks
    finally: k.CloseHandle(h)

def write_lock():
    payload = {'pid': os.getpid(), 'started_utc': utcnow()}
    _, _, ticks = open_process(os.getpid()); payload['creation_filetime'] = ticks
    while True:
        try: fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY); break
        except FileExistsError:
            try: old = json.loads(LOCK.read_text(encoding='utf-8'))
            except Exception: old = {}
            state = read_state()
            if state.get('status') in ('COMPLETE', 'STOPPED'):
                raise RuntimeError('Supervisor is terminal: %s' % state.get('status'))
            if old.get('pid') and old.get('creation_filetime') and pid_is_same(old['pid'], old['creation_filetime']):
                raise RuntimeError('Another WS-25 r4 supervisor is active (pid %s)' % old['pid'])
            try: LOCK.unlink()
            except FileNotFoundError: pass
    with os.fdopen(fd, 'w', encoding='utf-8') as f: json.dump(payload, f); f.flush(); os.fsync(f.fileno())
    return payload

def remove_lock(payload):
    try:
        old = json.loads(LOCK.read_text(encoding='utf-8'))
        if old.get('pid') == payload['pid'] and old.get('creation_filetime') == payload['creation_filetime']:
            LOCK.unlink()
    except Exception: pass

def verified_ids():
    out = set()
    if not RECEIPTS.exists(): return out
    for line in RECEIPTS.read_text(encoding='utf-8').splitlines():
        try: row = json.loads(line)
        except Exception: continue
        if row.get('event') in ('verified', 'verified_existing') and row.get('id'): out.add(row['id'])
    return out

def pending_started_ids():
    started, verified = set(), verified_ids()
    if RECEIPTS.exists():
        for line in RECEIPTS.read_text(encoding='utf-8').splitlines():
            try: row = json.loads(line)
            except Exception: continue
            if row.get('event') == 'started' and row.get('id'): started.add(row['id'])
    order = [c['id'] for c in json.loads(PLAN.read_text(encoding='utf-8'))['cells']]
    return [i for i in order if i in started and i not in verified]

def remote_status(experiment_id):
    cp = subprocess.run([PYTHON, str(REMOTE), 'status', experiment_id], cwd=str(ROOT),
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
    if cp.returncode: raise RuntimeError('status query failed for %s: %s' % (experiment_id, cp.stdout[-1000:]))
    return json.loads(cp.stdout)

def remote_audit():
    cp = subprocess.run([PYTHON, str(REMOTE), 'check'], cwd=str(ROOT),
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
    if cp.returncode: raise RuntimeError('remote audit failed: %s' % cp.stdout[-1000:])
    fields = {}
    for line in cp.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1); fields[k] = v
    return fields

def wait_for_safe_resume(prior_pid, exit_code):
    delay = RECOVERY_POLL_SECONDS
    while True:
        try:
            audit = remote_audit()
            active = audit.get('active_simulation_pids', '').strip()
            statuses = [(i, remote_status(i)) for i in pending_started_ids()]
            failed = [(i, s.get('status')) for i, s in statuses if s.get('status') not in ('SUCCEEDED', 'RUNNING', 'BUILT')]
            if failed:
                write_state(status='STOPPED', stop_reason='remote_terminal_failure', failed_ids=failed,
                            last_runner_pid=prior_pid, last_runner_exit_code=exit_code)
                log_event('supervisor_stopped', reason='remote_terminal_failure', failed_ids=failed)
                return False
            running = [(i, s.get('status')) for i, s in statuses if s.get('status') == 'RUNNING']
            if not active and not running:
                log_event('resume_gate_passed', unresolved_started_ids=[i for i, _ in statuses], audit=audit)
                return True
            log_event('resume_wait', active_simulation_pids=active, running_ids=running, poll_seconds=delay)
        except Exception as e:
            log_event('resume_audit_error', error=repr(e), poll_seconds=delay)
        time.sleep(delay)

def verify_only_pending_ids(ids):
    """Fetch and verify only already-started IDs; never opens the next cell."""
    scripts_dir = str(RUNNER.parent)
    inserted = scripts_dir not in sys.path
    if inserted: sys.path.insert(0, scripts_dir)
    module = runpy.run_path(str(RUNNER))
    selected = [cell for cell in module['cells']() if cell['id'] in set(ids)]
    if {cell['id'] for cell in selected} != set(ids):
        raise RuntimeError('Pending IDs are not in the frozen r4 plan')
    write_state(status='RECOVERING_CURRENT_IDS', recovery_ids=ids)
    log_event('current_id_recovery_started', ids=ids)
    for cell in selected:
        state = remote_status(cell['id'])
        if state.get('status') != 'SUCCEEDED':
            raise RuntimeError('Refusing to restart non-succeeded existing ID %s (%s)' %
                               (cell['id'], state.get('status')))
        module['run_cell'](cell)
        log_event('current_id_recovery_verified', id=cell['id'])
    audit = remote_audit()
    if audit.get('active_simulation_pids', '').strip():
        raise RuntimeError('Remote simulations remain active after current-ID recovery')
    log_event('current_id_recovery_complete', ids=ids, audit=audit)

def completion():
    try: x = json.loads(COMPLETION.read_text(encoding='utf-8'))
    except Exception: return None
    return x if x.get('verified_cells') == 28 else None

def wait_existing(k, h, pid):
    while True:
        rc = k.WaitForSingleObject(h, POLL_SECONDS * 1000)
        if rc == WAIT_OBJECT_0:
            code = ctypes.c_ulong()
            return int(code.value) if k.GetExitCodeProcess(h, ctypes.byref(code)) else None
        if rc != WAIT_TIMEOUT: return None
        write_state(last_poll_utc=utcnow(), observed_runner_pid=pid)
        log_event('runner_heartbeat', runner_pid=pid, receipt_verified_count=len(verified_ids()),
                  pending_started_ids=pending_started_ids())

def spawn_runner(attempt):
    path = RUNTIME / ('runner-attempt-%02d.log' % attempt)
    with path.open('ab', buffering=0) as out:
        p = subprocess.Popen([PYTHON, str(RUNNER), 'run'], cwd=str(ROOT), stdin=subprocess.DEVNULL,
             stdout=out, stderr=subprocess.STDOUT,
             creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
    _, _, ticks = open_process(p.pid)
    write_state(runner_pid=p.pid, runner_creation_filetime=ticks, runner_started_utc=utcnow(),
                runner_log=str(path), attempt=attempt, status='RUNNING')
    log_event('runner_started', pid=p.pid, creation_filetime=ticks, attempt=attempt, log=str(path))
    return p

def cim_start_utc(pid):
    script = "$p = Get-CimInstance Win32_Process -Filter 'ProcessId=%d'; if ($p) { $p.CreationDate.ToUniversalTime().ToString('o') }" % int(pid)
    cp = subprocess.run(['powershell.exe', '-NoProfile', '-Command', script],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20)
    return cp.stdout.strip() if cp.returncode == 0 else ''

def supervise(adopt_pid, expected_start=None):
    lock = write_lock()
    try:
        k, h, ticks = open_process(adopt_pid)
        if h and expected_start is not None and cim_start_utc(adopt_pid) != expected_start:
            k.CloseHandle(h); raise RuntimeError('Adopt PID identity mismatch; refusing PID reuse')
        if not h:
            log_event('adopt_target_already_exited', pid=adopt_pid)
            ticks = None
        else:
            log_event('supervisor_started', pid=os.getpid(), adopted_runner_pid=adopt_pid,
                      runner_creation_filetime=ticks)
        write_state(status='RUNNING', supervisor_pid=os.getpid(), supervisor_creation_filetime=lock['creation_filetime'],
                    supervisor_started_utc=utcnow(), adopted_runner_pid=adopt_pid,
                    adopted_runner_creation_filetime=ticks, recoveries=0,
                    adopted_runner_log='Codex exec session output; durable per-cell r4 receipts are in results/')
        pid = adopt_pid
        code = wait_existing(k, h, adopt_pid) if h else None
        recoveries = 0
        if h: k.CloseHandle(h)
        while True:
            log_event('runner_exited', pid=pid, exit_code=code)
            write_state(last_runner_pid=pid, last_runner_exit_code=code, last_runner_exit_utc=utcnow())
            result = completion()
            if result:
                state = 'COMPLETE' if result.get('diagnostics_nonperturbing_for_all_seeds') else 'STOPPED'
                write_state(status=state, verified_cells=28,
                            diagnostics_nonperturbing_for_all_seeds=result.get('diagnostics_nonperturbing_for_all_seeds'))
                log_event('matrix_terminal', status=state, verified_cells=28)
                return 0 if state == 'COMPLETE' else 3
            if code == 0:
                write_state(status='STOPPED', stop_reason='runner_exit_without_matrix_marker', last_runner_exit_code=code)
                log_event('supervisor_stopped', reason='runner_exit_without_matrix_marker'); return 2
            pending = pending_started_ids()
            if pending:
                if not wait_for_safe_resume(pid, code): return 2
                states = [(i, remote_status(i)) for i in pending_started_ids()]
                bad_states = [(i, s.get('status')) for i, s in states if s.get('status') != 'SUCCEEDED']
                if bad_states:
                    write_state(status='STOPPED', stop_reason='runner_exit_before_verification', unresolved_states=bad_states)
                    log_event('supervisor_stopped', reason='runner_exit_before_verification', unresolved_states=bad_states)
                    return 2
                try:
                    verify_only_pending_ids([i for i, _ in states])
                except Exception as error:
                    write_state(status='STOPPED', stop_reason='current_id_verification_failed', error=repr(error),
                                unresolved_ids=[i for i, _ in states])
                    log_event('supervisor_stopped', reason='current_id_verification_failed',
                              error=repr(error), unresolved_ids=[i for i, _ in states])
                    return 2
            if recoveries >= MAX_RECOVERIES:
                write_state(status='STOPPED', stop_reason='recovery_limit', recoveries=recoveries)
                log_event('supervisor_stopped', reason='recovery_limit'); return 2
            if not wait_for_safe_resume(pid, code): return 2
            seconds = BACKOFF[min(recoveries, len(BACKOFF)-1)]
            time.sleep(seconds); recoveries += 1
            p = spawn_runner(recoveries); pid, code = p.pid, p.wait()
    finally: remove_lock(lock)

def creation_ticks_from_iso(value):
    value = value.replace('Z', '+00:00')
    created = dt.datetime.fromisoformat(value).astimezone(dt.timezone.utc)
    epoch = dt.datetime(1601, 1, 1, tzinfo=dt.timezone.utc)
    return int((created - epoch).total_seconds() * 10000000)

def launch(pid, expected_start):
    state = read_state()
    if state.get('status') in ('COMPLETE', 'STOPPED'): raise SystemExit('Terminal supervisor state: %s' % state['status'])
    cmd = [PYTHON, str(pathlib.Path(__file__).resolve()), '--adopt-pid', str(pid)]
    if expected_start is not None: cmd += ['--expected-start-utc', expected_start]
    boot = RUNTIME / 'supervisor-bootstrap.log'
    with boot.open('ab', buffering=0) as out:
        p = subprocess.Popen(cmd, cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
    print(json.dumps({'launched': True, 'supervisor_pid': p.pid, 'adopted_runner_pid': pid,
                      'expected_start_utc': expected_start, 'bootstrap_log': str(boot)}))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--launch-adopt-pid', type=int)
    ap.add_argument('--adopt-pid', type=int)
    ap.add_argument('--expected-start-utc')
    a = ap.parse_args()
    if a.launch_adopt_pid:
        launch(a.launch_adopt_pid, a.expected_start_utc)
    elif a.adopt_pid: raise SystemExit(supervise(a.adopt_pid, a.expected_start_utc))
    else: ap.error('supply --launch-adopt-pid or --adopt-pid')
if __name__ == '__main__': main()

