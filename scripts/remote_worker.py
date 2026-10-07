#!/usr/bin/env python3
"""Workspace-only ConWeave experiment worker (Python 3.5 compatible)."""
import argparse
import contextlib
import datetime
import glob
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time

ROOT = '/home/fnl/lzy'
ID_RE = re.compile(r'^[0-9]{8}-[0-9]{6}-[a-z0-9][a-z0-9-]{0,40}$')
SHA_RE = re.compile(r'^[0-9a-f]{40}$')
REPO_RE = re.compile(r'^https://github[.]com/LarryBUPT/[A-Za-z0-9_.-]+(?:[.]git)?$')
REFERENCE_PUSH = 'no-push://read-only-reference'
_LOGIN_ATTEMPTED = False


def inside(path, allow_root=False):
    root = os.path.realpath(ROOT)
    if root != ROOT or not os.path.isdir(ROOT):
        raise RuntimeError('Workspace root is missing or redirected')
    full = os.path.realpath(path)
    if full != root and not full.startswith(root + os.sep):
        raise RuntimeError('Path escapes workspace: ' + path)
    if full == root and not allow_root:
        raise RuntimeError('Operation cannot target workspace root')
    return full


def make_dir(path):
    inside(path)
    if os.path.lexists(path) and os.path.islink(path):
        raise RuntimeError('Refusing symlink directory: ' + path)
    if not os.path.isdir(path):
        os.makedirs(path)
    inside(path)


def run_checked(argv, cwd=None, log=None, timeout=None):
    if cwd:
        inside(cwd)
    if log:
        inside(log)
        with open(log, 'ab') as output:
            try:
                result = subprocess.call(argv, cwd=cwd, stdout=output,
                                         stderr=subprocess.STDOUT, timeout=timeout)
            except subprocess.TimeoutExpired:
                raise RuntimeError('Command timed out: ' + ' '.join(argv[:3]))
    else:
        try:
            result = subprocess.call(argv, cwd=cwd, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError('Command timed out: ' + ' '.join(argv[:3]))
    if result:
        raise RuntimeError('Command failed (exit %d): %s' % (result, ' '.join(argv[:3])))


def output(argv, cwd=None):
    if cwd:
        inside(cwd)
    return subprocess.check_output(argv, cwd=cwd, stderr=subprocess.STDOUT).decode('utf-8').strip()


def stamp():
    return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def paths(experiment_id):
    if not ID_RE.match(experiment_id):
        raise RuntimeError('Invalid experiment ID')
    base = inside(os.path.join(ROOT, 'results', experiment_id))
    source = inside(os.path.join(ROOT, 'runs', experiment_id, 'source'))
    return base, source


def metadata_path(base):
    return inside(os.path.join(base, 'metadata.json'))


def save_metadata(base, data):
    path = metadata_path(base)
    tmp = inside(path + '.tmp')
    with open(tmp, 'w') as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
    os.rename(tmp, path)
    with open(inside(os.path.join(base, 'metadata.txt')), 'w') as handle:
        for key in sorted(data):
            handle.write('%s: %s\n' % (key, data[key]))


def load_metadata(base):
    with open(metadata_path(base)) as handle:
        return json.load(handle)


def resources_ok():
    stat = os.statvfs(ROOT)
    free_gb = stat.f_bavail * stat.f_frsize / float(1024 ** 3)
    if free_gb < 20:
        raise RuntimeError('Less than 20 GiB free in workspace filesystem')
    with open('/proc/meminfo') as handle:
        memory = handle.read()
    match = re.search(r'^MemAvailable:\s+(\d+) kB', memory, re.M)
    if not match or int(match.group(1)) < 4 * 1024 * 1024:
        raise RuntimeError('Less than 4 GiB memory available')
    if os.getloadavg()[0] > 20:
        raise RuntimeError('Server load is high; retry later')


WS25_CAPACITY_SHA = 'a656104d05c681f9b3a998b5ef4ce3e644558d02'
WS25_CAPACITY_TOPO_SHA = '74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba'
WS25_FORMAL_SHA = 'ce699dffe2845dc83e2171a1c309c6d96b96d2b3'
WS25_FORMAL_MANIFEST_SHA = '7dd35746c33b48245910b90cc606aa3bed59a207794fd1528dad2b8faf9b7731'
WS25_CAPACITY_TRACES = {
    'ws25_seed20262505_b0.txt': '32b2194ee2206a5bf44831a7f0071972e364e22ab781cdf4f95efcaf569a35be',
    'ws25_seed20262505_b64.txt': '774440e1d5efe8c54e931cd79a72cad65636265b3f01f873d507397805300fd2',
    'ws25_seed20262505_b128.txt': 'ee826ee32cea821f2e035fb433a6cc31a07fd904cbedbc58255efaf6d9a8e317',
    'ws25_seed20262505_b192.txt': '038d7cf09f21a56ae8e1d13164cc57e816bd14cf62631d7ff9efa59b8c1d9272',
    'ws25_seed20262506_b0.txt': 'f46676b605f96f1bd4f1a574857bcdc9335fdaa86c2639ef36b3607d82865433',
    'ws25_seed20262506_b64.txt': 'afe3b53ab85196c4e5a186109769e00aaca5e0f3f1550eb58d6adb42baff9a93',
    'ws25_seed20262506_b128.txt': 'b09902ff35d4333b5143a3028ee7536df5c393e211dca671e2937d8aa23f3cc6',
    'ws25_seed20262506_b192.txt': 'fe94e381938538ab7c2376614f6d8c27600b2e351c2d5e10a2b62fd14d2a8ed5',
    'ws25_seed20262507_b0.txt': 'cde149fc3ad92edd184f1ad804693c197ba1e50c5fc120138d18a2f8b5b497a9',
    'ws25_seed20262507_b64.txt': 'dadb098ae19c55930520cb0a9df7dcb98394076a814a99599f907b8f06f693b5',
    'ws25_seed20262507_b128.txt': 'da199c3cab60cb2c3d792a3e6efb35f01b5b4a2d8c6b2626d8ed338b563b5223',
    'ws25_seed20262507_b192.txt': '01b24bc1bd76d4932dd6c6e4e7ce159ff9d73824de2540ba4b09cd62e6ff83b7',
    'ws25_seed20262508_b0.txt': 'dee60ba5d2a9f4584dd98cfc1700b9633297e78c7b676f308f8806e19c8aa2b7',
    'ws25_seed20262508_b64.txt': 'e83ed23fa9cf8170b099a6b8b7318da4fe231d06c6a62b2881f6f2d7d015bac8',
    'ws25_seed20262508_b128.txt': 'b43300ce2ead09461c2ed5c47dfc1710d54315974622876b3fbc84c382489d42',
    'ws25_seed20262508_b192.txt': 'e68616fd2de70e466f6193d7584ae77a1eb1a437efbf90c8619930dd814ded4a',
}


def file_sha256(path):
    digest = hashlib.sha256()
    with open(inside(path), 'rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def ws25_frozen_traces(source_sha, source):
    if source_sha == WS25_CAPACITY_SHA:
        return WS25_CAPACITY_TRACES
    if source_sha != WS25_FORMAL_SHA:
        raise RuntimeError('High capacity requires a frozen WS-25 source SHA')
    path = os.path.join(source, 'docs/research/evidence/ws25-v1fix-formal-inputs.json')
    if file_sha256(path) != WS25_FORMAL_MANIFEST_SHA:
        raise RuntimeError('Formal demand manifest hash changed')
    with open(inside(path), 'r') as handle:
        manifest = json.load(handle)
    seeds = manifest.get('seeds', {})
    if set(seeds) != set(str(seed) for seed in range(20262521, 20262545)):
        raise RuntimeError('Formal demand seed pool changed')
    traces = {}
    for seed, details in seeds.items():
        levels = details.get('levels', {})
        if set(levels) != set(('0', '64', '128', '192')):
            raise RuntimeError('Formal demand levels changed')
        for level, item in levels.items():
            name = 'ws25_seed%s_b%s.txt' % (seed, level)
            if (item.get('file') != name or item.get('flows') != 16384 + int(level) or
                    not re.match(r'^[0-9a-f]{64}$', item.get('sha256', ''))):
                raise RuntimeError('Formal demand entry changed')
            traces[name] = item['sha256']
    if len(traces) != 96:
        raise RuntimeError('Formal demand trace count changed')
    return traces


def high_capacity_admission(params, data, source, workers):
    """Conservative admission for frozen WS-25 calibration and formal inputs."""
    traces = ws25_frozen_traces(data.get('git_commit'), source)
    expected = {'pfc': 0, 'irn': 1, 'bw': 400, 'buffer': 9,
                'topo': 'topo_1280_400G_400G_OS1', 'cdf': 'AliStorage2019',
                'netload': 10, 'simul_time': '0.01', 'ws25_diag': 0}
    if any(params.get(key) != value for key, value in expected.items()):
        raise RuntimeError('High capacity requires frozen WS-25 run parameters')
    if params.get('lb') not in ('fecmp', 'drill', 'conga', 'letflow', 'conweave', 'classreserve'):
        raise RuntimeError('High capacity mode is outside the frozen six-arm matrix')
    trace = params.get('flow_file')
    if trace not in traces:
        raise RuntimeError('High capacity trace is not frozen')
    if file_sha256(os.path.join(source, 'config', trace)) != traces[trace]:
        raise RuntimeError('High capacity trace hash changed')
    if file_sha256(os.path.join(source, 'config', expected['topo'] + '.txt')) != WS25_CAPACITY_TOPO_SHA:
        raise RuntimeError('High capacity topology hash changed')
    stat = os.statvfs(ROOT)
    if stat.f_bavail * stat.f_frsize < 100 * 1024 ** 3:
        raise RuntimeError('High capacity needs at least 100 GiB free disk')
    # Refuse admission when another ordinary account has an active process.
    for line in output(['ps', '-eo', 'uid,pid,stat,comm', '--no-headers']).splitlines():
        columns = line.split(None, 3)
        if len(columns) == 4 and int(columns[0]) >= 1000 and int(columns[0]) != os.getuid() and not columns[2].startswith('Z'):
            raise RuntimeError('Another ordinary user has an active process')
    with open('/proc/meminfo') as handle:
        match = re.search(r'^MemAvailable:\s+(\d+) kB', handle.read(), re.M)
    if not match:
        raise RuntimeError('Cannot read MemAvailable for high capacity')
    available_kib = int(match.group(1))
    # A cold worker may not yet have reached its 4.6 GiB observed peak.
    # Account for every worker's remaining growth plus a full new 5 GiB cell.
    reserve_kib = 5 * 1024 * 1024
    for _, worker_pid in workers:
        current_kib = 0
        for name in os.listdir('/proc'):
            if not name.isdigit() or not descendant_of(int(name), worker_pid):
                continue
            try:
                with open('/proc/%s/status' % name) as handle:
                    resident = re.search(r'^VmRSS:\s+(\d+) kB', handle.read(), re.M)
                current_kib += int(resident.group(1)) if resident else 0
            except (IOError, OSError):
                pass
        reserve_kib += max(0, 5 * 1024 * 1024 - current_kib)
    if available_kib - reserve_kib < 32 * 1024 * 1024:
        raise RuntimeError('Projected available memory below 32 GiB at high capacity')


def active_simulations():
    found = []
    # procps on the Ubuntu 16.04 host does not parse comma-separated fields
    # when each field has an '=' header override; it returns only PIDs.
    listing = output(['ps', '-eo', 'pid,comm,args', '--no-headers'])
    for line in listing.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) != 3:
            continue
        pid, command, arguments = parts
        if command.startswith('network-load-ba') or (command.startswith('python') and
                                                       ' run.py --lb ' in ' ' + arguments):
            found.append(pid)
    return found


@contextlib.contextmanager
def simulation_start_lock():
    """Serialize admission even when separate controllers launch together."""
    import fcntl  # The worker runs on Linux; keep local tooling portable.
    folder = inside(os.path.join(ROOT, '.research-workflow'))
    make_dir(folder)
    path = inside(os.path.join(folder, 'simulation-start.lock'))
    if os.path.islink(path):
        raise RuntimeError('Simulation start lock is a symlink')
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def descendant_of(pid, ancestor):
    """Identify run.py/ns-3 children belonging to a recorded worker PID."""
    seen = set()
    while pid and pid not in seen:
        if pid == ancestor:
            return True
        seen.add(pid)
        try:
            with open('/proc/%s/status' % pid) as handle:
                match = re.search(r'^PPid:\s+(\d+)', handle.read(), re.M)
            pid = int(match.group(1)) if match else 0
        except (IOError, OSError):
            return False
    return False


def running_workers():
    found = []
    for existing in glob.glob(os.path.join(ROOT, 'results', '*', 'metadata.json')):
        try:
            other = json.load(open(existing))
            if other.get('status') == 'RUNNING' and pid_alive(other.get('pid')):
                found.append((other['experiment_id'], int(other['pid'])))
        except (IOError, OSError, ValueError, KeyError):
            raise RuntimeError('Cannot audit running experiment metadata: ' + existing)
    return found


def configure_references(repo):
    for name, url in [('upstream', 'https://github.com/conweave-project/conweave-ns3.git'),
                      ('reference-maplerime', 'https://github.com/maplerime/conweave-ns3.git')]:
        current = subprocess.call(['git', 'config', '--get', 'remote.' + name + '.url'],
                                  cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if current:
            run_checked(['git', 'remote', 'add', name, url], cwd=repo)
        elif output(['git', 'config', '--get', 'remote.' + name + '.url'], cwd=repo) != url:
            raise RuntimeError('Unexpected reference remote URL')
        run_checked(['git', 'config', 'remote.' + name + '.pushurl', REFERENCE_PUSH], cwd=repo)
    run_checked(['git', 'config', 'push.default', 'nothing'], cwd=repo)


def network_retry(argv, cwd=None):
    global _LOGIN_ATTEMPTED
    try:
        run_checked(argv, cwd=cwd, timeout=45)
        return
    except RuntimeError:
        pass
    # Diagnose without exposing any credentials or login script contents.
    try:
        print('DNS github.com: ' + socket.gethostbyname('github.com'))
    except Exception:
        print('DNS github.com: failed')
    login = inside(os.path.join(ROOT, 'login.sh'))
    if not _LOGIN_ATTEMPTED and os.path.isfile(login) and not os.path.islink(login):
        _LOGIN_ATTEMPTED = True
        print('Network retry after workspace login.sh (output suppressed)')
        with open(os.devnull, 'w') as null:
            try:
                subprocess.call(['bash', login], cwd=ROOT, stdout=null, stderr=null, timeout=30)
            except subprocess.TimeoutExpired:
                pass
    run_checked(argv, cwd=cwd, timeout=45)


def audit():
    inside(ROOT, allow_root=True)
    with open('/proc/meminfo') as handle:
        meminfo = handle.read()
    available = re.search(r'^MemAvailable:\s+(\d+) kB', meminfo, re.M)
    rss_mib = 0.0
    for pid in active_simulations():
        try:
            with open('/proc/%s/status' % pid) as handle:
                status_text = handle.read()
            resident = re.search(r'^VmRSS:\s+(\d+) kB', status_text, re.M)
            if resident:
                rss_mib = max(rss_mib, int(resident.group(1)) / 1024.0)
        except (IOError, OSError):
            pass
    print('workspace=' + ROOT)
    print('host=' + socket.gethostname())
    print('cpu_logical=' + str(os.cpu_count()))
    print('load_1m=' + str(os.getloadavg()[0]))
    print('active_simulation_pids=' + ','.join(active_simulations()))
    print('mem_available_gib=%.2f' % (int(available.group(1)) / float(1024 ** 2) if available else 0.0))
    print('simulation_max_process_rss_mib=%.1f' % rss_mib)
    print('python=' + sys.version.split()[0])
    print('docker_access=' + ('yes' if os.access('/var/run/docker.sock', os.R_OK | os.W_OK) else 'no'))
    print('free_gib=%.1f' % (os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize / float(1024 ** 3)))
    for tool in ('gcc', 'g++', 'git', 'make', 'cmake', 'tmux', 'screen', 'rsync'):
        print('%s=%s' % (tool, shutil.which(tool) or 'missing'))


def sync(repo_url, sha):
    if not REPO_RE.match(repo_url) or not SHA_RE.match(sha):
        raise RuntimeError('Only an exact SHA from a LarryBUPT repository is accepted')
    resources_ok()
    code = inside(os.path.join(ROOT, 'code', 'conweave-ns3'))
    make_dir(os.path.dirname(code))
    if not os.path.exists(code):
        network_retry(['git', 'clone', repo_url, code])
    if os.path.islink(code) or not os.path.isdir(os.path.join(code, '.git')):
        raise RuntimeError('Code cache is not a plain Git checkout')
    if output(['git', 'config', '--get', 'remote.origin.url'], cwd=code).rstrip('/') != repo_url.rstrip('/'):
        raise RuntimeError('Code cache origin differs from the configured fork')
    if output(['git', 'status', '--porcelain'], cwd=code):
        raise RuntimeError('Code cache has local modifications')
    network_retry(['git', 'fetch', 'origin'], cwd=code)
    run_checked(['git', 'cat-file', '-e', sha + '^{commit}'], cwd=code)
    if not output(['git', 'branch', '-r', '--contains', sha], cwd=code).strip():
        raise RuntimeError('Commit is not on a fetched fork branch')
    configure_references(code)
    print('synced fork commit=' + sha)


def sync_bundle(repo_url, sha, branch, bundle_name):
    """Fallback: transfer Git history from a verified local fork checkout."""
    if not REPO_RE.match(repo_url) or not SHA_RE.match(sha):
        raise RuntimeError('Invalid personal fork or commit')
    if not re.match(r'^(feature|experiment|idea|research)/[A-Za-z0-9._/-]+$', branch):
        raise RuntimeError('Invalid personal branch')
    if not re.match(r'^sync-[0-9a-f]{40}-[0-9]+[.]bundle$', bundle_name):
        raise RuntimeError('Invalid bundle name')
    resources_ok()
    bundle = inside(os.path.join(ROOT, '.research-workflow', bundle_name))
    if os.path.islink(bundle) or not os.path.isfile(bundle):
        raise RuntimeError('Workspace Git bundle is missing or redirected')
    code = inside(os.path.join(ROOT, 'code', 'conweave-ns3'))
    make_dir(os.path.dirname(code))
    if not os.path.exists(code):
        run_checked(['git', 'clone', bundle, code])
        run_checked(['git', 'remote', 'set-url', 'origin', repo_url], cwd=code)
    if os.path.islink(code) or not os.path.isdir(os.path.join(code, '.git')):
        raise RuntimeError('Code cache is not a plain Git checkout')
    if output(['git', 'config', '--get', 'remote.origin.url'], cwd=code).rstrip('/') != repo_url.rstrip('/'):
        raise RuntimeError('Code cache origin differs from the personal fork')
    if output(['git', 'status', '--porcelain'], cwd=code):
        raise RuntimeError('Code cache has local modifications')
    run_checked(['git', 'fetch', bundle,
                 'refs/heads/' + branch + ':refs/remotes/origin/' + branch], cwd=code)
    run_checked(['git', 'cat-file', '-e', sha + '^{commit}'], cwd=code)
    if output(['git', 'rev-parse', 'refs/remotes/origin/' + branch], cwd=code) != sha:
        raise RuntimeError('Bundle branch does not match requested commit')
    configure_references(code)
    os.remove(bundle)  # Only this exact temporary bundle, after successful fetch.
    print('synced personal fork commit via workspace Git bundle=' + sha)


def build(experiment_id, sha, branch):
    if not SHA_RE.match(sha) or not re.match(r'^[A-Za-z0-9._/-]{1,100}$', branch):
        raise RuntimeError('Invalid commit or branch')
    resources_ok()
    base, source = paths(experiment_id)
    if os.path.lexists(base) or os.path.lexists(os.path.dirname(source)):
        raise RuntimeError('Experiment ID already exists; choose a new ID')
    code = inside(os.path.join(ROOT, 'code', 'conweave-ns3'))
    if not os.path.isdir(os.path.join(code, '.git')):
        raise RuntimeError('Sync the personal fork first')
    run_checked(['git', 'cat-file', '-e', sha + '^{commit}'], cwd=code)
    make_dir(os.path.join(ROOT, 'results'))
    make_dir(os.path.join(ROOT, 'runs'))
    make_dir(base)
    for name in ('config', 'raw', 'processed', 'figures', 'logs'):
        make_dir(os.path.join(base, name))
    make_dir(os.path.dirname(source))
    data = {'experiment_id': experiment_id, 'created_utc': stamp(), 'status': 'BUILDING',
            'git_repository': output(['git', 'config', '--get', 'remote.origin.url'], cwd=code),
            'git_commit': sha, 'git_branch': branch, 'server': socket.gethostname(),
            'cpu_jobs': 2, 'build_mode': 'optimized', 'seed': 1,
            'pid': os.getpid()}
    save_metadata(base, data)
    log = inside(os.path.join(base, 'logs', 'build.log'))
    try:
        run_checked(['git', 'clone', '--local', '--no-hardlinks', code, source], log=log)
        run_checked(['git', 'checkout', '--detach', sha], cwd=source, log=log)
        run_checked(['git', 'remote', 'set-url', 'origin', data['git_repository']], cwd=source)
        configure_references(source)
        if output(['git', 'rev-parse', 'HEAD'], cwd=source) != sha:
            raise RuntimeError('Checkout SHA mismatch')
        run_checked(['./waf', 'configure', '--build-profile=optimized'], cwd=source, log=log)
        run_checked(['./waf', '-j2'], cwd=source, log=log)
        data['status'] = 'BUILT'
    except Exception:
        data['status'] = 'BUILD_FAILED'
        raise
    finally:
        data['build_finished_utc'] = stamp()
        save_metadata(base, data)
    print('build complete=' + experiment_id)


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def execute(experiment_id):
    base, source = paths(experiment_id)
    for attempt in range(50):
        if load_metadata(base).get('pid') == os.getpid():
            break
        time.sleep(0.1)
    else:
        raise RuntimeError('Launcher did not record worker PID')
    data = load_metadata(base)
    params = data['parameters']
    command = [sys.executable, 'run.py', '--lb', params['lb'], '--pfc', str(params['pfc']),
               '--irn', str(params['irn']), '--simul_time', params['simul_time'],
               '--netload', str(params['netload']), '--bw', str(params['bw']),
               '--buffer', str(params.get('buffer', 9)),
               '--topo', params['topo'], '--cdf', params['cdf']]
    if params.get('flow_file'):
        command.extend(['--flow-file', 'config/' + params['flow_file']])
    if params.get('ws13_diag'):
        command.extend(['--ws13-diag', '1'])
    if params.get('ws25_diag'):
        command.extend(['--ws25-diag', '1'])
    if params.get('ws26_time_probe'):
        command.extend(['--ws26-time-probe', '1'])
    if params['lb'] == 'ws18':
        command.extend(['--ws18-admission', str(params['ws18_admission']),
                        '--ws18-path', str(params['ws18_path']),
                        '--ws18-admission-rate-gbps', str(params['ws18_admission_rate_gbps'])])
        command.extend(['--ws21-identity', str(params.get('ws21_identity', 0))])
        command.extend(['--ws21-feedback', str(params.get('ws21_feedback', 0))])
        command.extend(['--ws21-feedback-interval-ns',
                        str(params.get('ws21_feedback_interval_ns', 10000))])
        command.extend(['--ws21-heartbeat', str(params.get('ws21_heartbeat', 0)),
                        '--ws21-heartbeat-interval-ns',
                        str(params.get('ws21_heartbeat_interval_ns', 200000)),
                        '--ws21-heartbeat-fault-mode',
                        str(params.get('ws21_heartbeat_fault_mode', 0)),
                        '--ws21-heartbeat-fault-tor',
                        str(params.get('ws21_heartbeat_fault_tor', 0)),
                        '--ws21-heartbeat-fault-port',
                        str(params.get('ws21_heartbeat_fault_port', 0)),
                        '--ws21-heartbeat-fault-start-ns',
                        str(params.get('ws21_heartbeat_fault_start_ns', 0)),
                        '--ws21-heartbeat-fault-end-ns',
                        str(params.get('ws21_heartbeat_fault_end_ns', 0))])
        command.extend(['--ws21-port-events', str(params.get('ws21_port_events', 0)),
                        '--ws21-port-max-bytes', str(params.get('ws21_port_max_bytes', 268435456))])
    if params.get('factorial_pilot'):
        command.append('--factorial-pilot')
    if params.get('factorial_formal'):
        command.append('--factorial-formal')
    if params.get('factorial_drop_diag'):
        command.append('--factorial-drop-diag')
    if params.get('ws23_pfc_probe_host', -1) >= 0:
        command.extend(['--ws23-pfc-probe-host', str(params['ws23_pfc_probe_host']),
                        '--ws23-pfc-probe-pg', str(params['ws23_pfc_probe_pg']),
                        '--ws23-pfc-probe-start-ns', str(params['ws23_pfc_probe_start_ns']),
                        '--ws23-pfc-probe-end-ns', str(params['ws23_pfc_probe_end_ns']),
                        '--ws23-pause-time-us', str(params['ws23_pause_time_us'])])
    log = inside(os.path.join(base, 'logs', 'simulation.log'))
    data['command'] = ' '.join(command)
    save_metadata(base, data)
    try:
        if params.get('flow_file'):
            selected = inside(os.path.join(source, 'config', params['flow_file']))
            if not os.path.isfile(selected) or os.path.islink(selected):
                raise RuntimeError('Explicit flow file is missing or a symlink')
            import hashlib
            with open(selected, 'rb') as handle:
                before_hash = hashlib.sha256(handle.read()).hexdigest()
            data['input_flow_sha256'] = before_hash
            save_metadata(base, data)
        # Source writes through this link into this experiment's unique raw directory.
        output_dir = inside(os.path.join(source, 'mix', 'output'))
        if os.path.lexists(output_dir):
            raise RuntimeError('Expected a fresh, empty output path')
        os.symlink(inside(os.path.join(base, 'raw')), output_dir)
        run_checked(command, cwd=source, log=log)
        raw_dirs = [p for p in glob.glob(os.path.join(base, 'raw', '*')) if os.path.isdir(p)]
        fct = glob.glob(os.path.join(base, 'raw', '*', '*_out_fct.txt'))
        if len(raw_dirs) != 1 or len(fct) != 1 or os.path.getsize(fct[0]) == 0:
            raise RuntimeError('run.py ended without a nonempty FCT output; inspect simulation.log')
        data['raw_directory'] = os.path.basename(raw_dirs[0])
        for config in glob.glob(os.path.join(base, 'raw', '*', 'config.txt')):
            shutil.copy2(config, inside(os.path.join(base, 'config', 'config.txt')))
            config_text = open(config).read()
            flow_lines = [line.split(None, 1)[1].strip() for line in config_text.splitlines()
                          if line.startswith('FLOW_FILE ')]
            if len(flow_lines) != 1:
                raise RuntimeError('Simulation config has no unique FLOW_FILE')
            flow_source = os.path.realpath(os.path.join(source, flow_lines[0]))
            config_root = os.path.realpath(os.path.join(source, 'config'))
            if not flow_source.startswith(config_root + os.sep) or not os.path.isfile(flow_source):
                raise RuntimeError('FLOW_FILE escaped source config or is missing')
            import hashlib
            with open(flow_source, 'rb') as handle:
                flow_hash = hashlib.sha256(handle.read()).hexdigest()
            if data.get('input_flow_sha256') and data['input_flow_sha256'] != flow_hash:
                raise RuntimeError('Explicit flow file changed during simulation')
            shutil.copy2(flow_source, inside(os.path.join(base, 'config', 'traffic_trace.txt')))
            data['input_flow_sha256'] = flow_hash
            topology_source = os.path.join(source, 'config', params['topo'] + '.txt')
            shutil.copy2(topology_source, inside(os.path.join(base, 'config', 'topology.txt')))
            with open(topology_source, 'rb') as handle:
                data['topology_sha256'] = hashlib.sha256(handle.read()).hexdigest()
        if params.get('factorial_pilot') or params.get('factorial_formal'):
            with open(os.path.join(base, 'config', 'traffic_trace.txt')) as handle:
                data['input_flows'] = int(handle.readline().strip())
            with open(fct[0]) as handle:
                data['completed_flows'] = sum(1 for line in handle if line.strip())
            data['unfinished_flows'] = data['input_flows'] - data['completed_flows']
            if data['unfinished_flows']:
                raise RuntimeError('Factorial validation has %d unfinished flows' % data['unfinished_flows'])
        data['status'] = 'SUCCEEDED'
    except Exception as error:
        data['status'] = 'FAILED'
        data['error'] = str(error)
        raise
    finally:
        data['finished_utc'] = stamp()
        save_metadata(base, data)


def start(experiment_id, params, max_concurrent=1):
    resources_ok()
    if max_concurrent not in (1, 2, 4, 8, 12, 16, 18):
        raise RuntimeError('Unsupported concurrency cap')
    with simulation_start_lock():
        resources_ok()
        workers = running_workers()
        active = active_simulations()
        unknown = [pid for pid in active if not any(descendant_of(int(pid), worker_pid)
                   for _, worker_pid in workers)]
        if unknown:
            raise RuntimeError('Unknown ns-3 process; no new run: ' + ','.join(unknown))
        if len(workers) >= max_concurrent:
            raise RuntimeError('Concurrency cap reached (%d)' % max_concurrent)
        base, source = paths(experiment_id)
        data = load_metadata(base)
        if data.get('status') != 'BUILT':
            raise RuntimeError('Experiment must be built and not previously started')
        if output(['git', 'rev-parse', 'HEAD'], cwd=source) != data['git_commit']:
            raise RuntimeError('Source commit changed after build')
        if output(['git', 'status', '--porcelain'], cwd=source):
            raise RuntimeError('Source changed after build')
        if max_concurrent > 12:
            for other_id, unused_pid in workers:
                other_base, other_source = paths(other_id)
                other = load_metadata(other_base)
                if (other.get('git_commit') != data.get('git_commit') or
                        other.get('parameters', {}).get('flow_file') not in
                        ws25_frozen_traces(other.get('git_commit'), other_source)):
                    raise RuntimeError('High capacity cannot mix with other workloads')
            high_capacity_admission(params, data, source, workers)
        data['parameters'] = params
        data['topology'] = params['topo']
        data['load'] = params['netload']
        data['algorithm'] = params['lb']
        data['concurrency_cap'] = max_concurrent
        data['started_utc'] = stamp()
        data['status'] = 'RUNNING'
        worker_log = inside(os.path.join(base, 'logs', 'worker.log'))
        with open(worker_log, 'ab') as log:
            process = subprocess.Popen([sys.executable, os.path.realpath(__file__), 'execute', experiment_id],
                                       cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
        data['pid'] = process.pid
        save_metadata(base, data)
        print('started experiment=%s pid=%d cap=%d' % (experiment_id, process.pid, max_concurrent))


def status(experiment_id):
    base, unused = paths(experiment_id)
    data = load_metadata(base)
    print(json.dumps(data, indent=2, sort_keys=True))
    if data.get('status') == 'RUNNING':
        alive = pid_alive(data.get('pid'))
        print('process_alive=' + str(alive))
        if not alive:
            print('effective_status=INTERRUPTED; inspect worker.log')


def fetch_check(experiment_id):
    base, unused = paths(experiment_id)
    if not os.path.isdir(base) or os.path.islink(base):
        raise RuntimeError('Result directory missing or redirected')
    if load_metadata(base).get('status') not in ('SUCCEEDED', 'FAILED', 'BUILD_FAILED'):
        raise RuntimeError('Experiment is not in a terminal state; fetch after status settles')
    for parent, dirs, files in os.walk(base, followlinks=False):
        inside(parent)
        for name in dirs + files:
            path = os.path.join(parent, name)
            if os.path.islink(path):
                raise RuntimeError('Result contains a symlink: ' + path)
            inside(path)
    print('fetch-safe=' + experiment_id)


def transfer_smoke(experiment_id):
    base, unused = paths(experiment_id)
    if os.path.lexists(base):
        raise RuntimeError('Experiment ID already exists')
    make_dir(os.path.join(ROOT, 'results'))
    make_dir(base)
    for name in ('config', 'raw', 'processed', 'figures', 'logs'):
        make_dir(os.path.join(base, name))
    with open(inside(os.path.join(base, 'raw', 'transfer-probe.txt')), 'w') as handle:
        handle.write('ConWeave transfer smoke test\n')
    save_metadata(base, {'experiment_id': experiment_id, 'created_utc': stamp(),
                         'status': 'TRANSFER_TEST', 'server': socket.gethostname()})
    print('transfer-test=' + experiment_id)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command')
    sub.add_parser('audit')
    sync_cmd = sub.add_parser('sync')
    sync_cmd.add_argument('--repo', required=True)
    sync_cmd.add_argument('--sha', required=True)
    bundle_cmd = sub.add_parser('sync-bundle')
    bundle_cmd.add_argument('--repo', required=True)
    bundle_cmd.add_argument('--sha', required=True)
    bundle_cmd.add_argument('--branch', required=True)
    bundle_cmd.add_argument('--bundle-name', required=True)
    build_cmd = sub.add_parser('build')
    build_cmd.add_argument('--id', required=True)
    build_cmd.add_argument('--sha', required=True)
    build_cmd.add_argument('--branch', required=True)
    run_cmd = sub.add_parser('run')
    run_cmd.add_argument('--id', required=True)
    run_cmd.add_argument('--lb', choices=['fecmp', 'drill', 'conga', 'letflow', 'conweave', 'dualtrack', 'shortq2', 'guardhash', 'guardhashgate', 'packet-rr', 'packet-random', 'packet-adaptive', 'packet-drill', 'ws18', 'classreserve', 'destspread'], default='fecmp')
    run_cmd.add_argument('--simul-time', default='0.01')
    run_cmd.add_argument('--netload', type=int, default=10)
    run_cmd.add_argument('--max-concurrent', type=int, choices=(1, 2, 4, 8, 12, 16, 18), default=1)
    run_cmd.add_argument('--bw', type=int, choices=[100, 400], default=100)
    run_cmd.add_argument('--buffer', type=int, choices=range(1, 10), default=9)
    run_cmd.add_argument('--topo', default='leaf_spine_128_100G_OS2')
    run_cmd.add_argument('--cdf', default='AliStorage2019')
    run_cmd.add_argument('--flow-file')
    run_cmd.add_argument('--ws13-diag', type=int, choices=(0, 1), default=0)
    run_cmd.add_argument('--ws25-diag', type=int, choices=(0, 1), default=0)
    run_cmd.add_argument('--ws26-time-probe', type=int, choices=(0, 1), default=0)
    run_cmd.add_argument('--ws18-admission', type=int, choices=(0, 1), default=0)
    run_cmd.add_argument('--ws18-path', type=int, choices=(0, 1), default=0)
    run_cmd.add_argument('--ws21-identity', type=int, choices=(0, 1), default=0)
    run_cmd.add_argument('--ws21-feedback', type=int, choices=(0, 1), default=0)
    run_cmd.add_argument('--ws21-feedback-interval-ns', type=int, default=10000)
    run_cmd.add_argument('--ws21-heartbeat', type=int, choices=(0, 1), default=0)
    run_cmd.add_argument('--ws21-heartbeat-interval-ns', type=int, default=200000)
    run_cmd.add_argument('--ws21-heartbeat-fault-mode', type=int, choices=(0, 1, 2), default=0)
    run_cmd.add_argument('--ws21-heartbeat-fault-tor', type=int, default=0)
    run_cmd.add_argument('--ws21-heartbeat-fault-port', type=int, default=0)
    run_cmd.add_argument('--ws21-heartbeat-fault-start-ns', type=int, default=0)
    run_cmd.add_argument('--ws21-heartbeat-fault-end-ns', type=int, default=0)
    run_cmd.add_argument('--ws21-port-events', type=int, choices=(0, 1), default=0)
    run_cmd.add_argument('--ws21-port-max-bytes', type=int, default=268435456)
    run_cmd.add_argument('--ws18-admission-rate-gbps', type=int, default=400)
    run_cmd.add_argument('--pfc', type=int, choices=[0, 1], default=1)
    run_cmd.add_argument('--irn', type=int, choices=[0, 1], default=0)
    run_cmd.add_argument('--factorial-pilot', action='store_true')
    run_cmd.add_argument('--factorial-formal', action='store_true')
    run_cmd.add_argument('--factorial-drop-diag', action='store_true')
    run_cmd.add_argument('--ws23-pfc-probe-host', type=int, default=-1)
    run_cmd.add_argument('--ws23-pfc-probe-pg', type=int, default=3)
    run_cmd.add_argument('--ws23-pfc-probe-start-ns', type=int, default=0)
    run_cmd.add_argument('--ws23-pfc-probe-end-ns', type=int, default=0)
    run_cmd.add_argument('--ws23-pause-time-us', type=int, default=5)
    for name in ('execute', 'status', 'fetch-check', 'transfer-smoke'):
        command = sub.add_parser(name)
        command.add_argument('id')
    args = parser.parse_args()
    if args.command == 'audit':
        audit()
    elif args.command == 'sync':
        sync(args.repo, args.sha)
    elif args.command == 'sync-bundle':
        sync_bundle(args.repo, args.sha, args.branch, args.bundle_name)
    elif args.command == 'build':
        build(args.id, args.sha, args.branch)
    elif args.command == 'run':
        if args.factorial_pilot and args.factorial_formal:
            raise RuntimeError('Factorial pilot and formal flags are exclusive')
        if args.factorial_formal and (not args.flow_file or args.ws13_diag or args.ws25_diag or args.ws26_time_probe):
            raise RuntimeError('Factorial formal requires a fixed trace and no diagnostics')
        if args.ws26_time_probe and (not args.ws25_diag or not args.flow_file):
            raise RuntimeError('WS-26 time probe needs fixed trace and WS-25 diagnostics')
        if args.pfc + args.irn != 1 and not (args.factorial_pilot or args.factorial_formal):
            raise RuntimeError('Exactly one of PFC and IRN must be enabled')
        if args.factorial_drop_diag and not args.factorial_pilot:
            raise RuntimeError('Factorial drop diagnostics require factorial pilot mode')
        if args.ws23_pfc_probe_host >= 0 and (
                not args.factorial_pilot or (args.irn, args.pfc) != (1, 1) or
                args.lb != 'fecmp' or not 0 <= args.ws23_pfc_probe_pg < 8 or
                not 0 < args.ws23_pfc_probe_start_ns < args.ws23_pfc_probe_end_ns or
                args.ws23_pfc_probe_end_ns >= int(float(args.simul_time) * 1e9) or
                not 1 <= args.ws23_pause_time_us <= 65535):
            raise RuntimeError('Invalid WS-23 PFC probe contract')
        if args.ws23_pfc_probe_host < 0 and (
                args.ws23_pfc_probe_pg != 3 or args.ws23_pfc_probe_start_ns or
                args.ws23_pfc_probe_end_ns or args.ws23_pause_time_us != 5):
            raise RuntimeError('WS-23 PFC probe options need a host')
        if (args.ws18_admission or args.ws18_path) and args.lb != 'ws18':
            raise RuntimeError('WS-18 switches require ws18 mode')
        if args.ws21_identity and args.lb != 'ws18':
            raise RuntimeError('WS-21 identity diagnostic requires ws18 mode')
        if args.ws21_feedback and (args.lb != 'ws18' or not args.ws21_identity):
            raise RuntimeError('WS-21 feedback requires ws18 mode and identity diagnostics')
        if not 1000 <= args.ws21_feedback_interval_ns <= 60000:
            raise RuntimeError('WS-21 feedback interval must be 1000..60000 ns')
        if args.ws21_heartbeat and args.lb != 'ws18':
            raise RuntimeError('WS-21 heartbeat requires ws18 mode')
        if not 50000 <= args.ws21_heartbeat_interval_ns <= 1000000:
            raise RuntimeError('WS-21 heartbeat interval must be 50000..1000000 ns')
        if args.ws21_heartbeat_fault_mode and (
                not args.ws21_heartbeat or args.ws21_heartbeat_fault_port < 0 or
                args.ws21_heartbeat_fault_end_ns <= args.ws21_heartbeat_fault_start_ns):
            raise RuntimeError('WS-21 heartbeat fault needs enabled heartbeat and a time window')
        if args.ws21_port_events and (args.lb != 'ws18' or args.ws21_port_max_bytes < 1024):
            raise RuntimeError('WS-21 port events require ws18 and a byte cap >= 1024')
        if args.ws18_admission_rate_gbps <= 0:
            raise RuntimeError('WS-18 admission rate must be positive')
        if args.netload < 1 or args.netload > 50 or not 0.005 <= float(args.simul_time) <= 0.1:
            raise RuntimeError('Small-run safety bounds: load 1-50, simulation time 0.005-0.1 s')
        if not re.match(r'^[A-Za-z0-9_-]+$', args.topo) or not re.match(r'^[A-Za-z0-9_-]+$', args.cdf):
            raise RuntimeError('Invalid topology or CDF name')
        flow_file = args.flow_file
        if flow_file and flow_file.startswith('config/'):
            flow_file = flow_file[len('config/'):]
        if flow_file and not re.match(r'^[A-Za-z0-9_.-]+[.]txt$', flow_file):
            raise RuntimeError('Flow file must be a config/*.txt basename')
        start(args.id, {'lb': args.lb, 'pfc': args.pfc, 'irn': args.irn,
                        'simul_time': args.simul_time,
                        'netload': args.netload, 'bw': args.bw, 'buffer': args.buffer,
                        'topo': args.topo, 'cdf': args.cdf,
                        'flow_file': flow_file, 'ws13_diag': args.ws13_diag,
                        'ws25_diag': args.ws25_diag,
                        'ws26_time_probe': args.ws26_time_probe,
                        'ws18_admission': args.ws18_admission,
                        'ws18_path': args.ws18_path,
                        'ws21_identity': args.ws21_identity,
                        'ws21_feedback': args.ws21_feedback,
                        'ws21_feedback_interval_ns': args.ws21_feedback_interval_ns,
                        'ws21_heartbeat': args.ws21_heartbeat,
                        'ws21_heartbeat_interval_ns': args.ws21_heartbeat_interval_ns,
                        'ws21_heartbeat_fault_mode': args.ws21_heartbeat_fault_mode,
                        'ws21_heartbeat_fault_tor': args.ws21_heartbeat_fault_tor,
                        'ws21_heartbeat_fault_port': args.ws21_heartbeat_fault_port,
                        'ws21_heartbeat_fault_start_ns': args.ws21_heartbeat_fault_start_ns,
                        'ws21_heartbeat_fault_end_ns': args.ws21_heartbeat_fault_end_ns,
                        'ws21_port_events': args.ws21_port_events,
                        'ws21_port_max_bytes': args.ws21_port_max_bytes,
                        'ws18_admission_rate_gbps': args.ws18_admission_rate_gbps,
                        'factorial_pilot': args.factorial_pilot,
                        'factorial_formal': args.factorial_formal,
                        'factorial_drop_diag': args.factorial_drop_diag,
                        'ws23_pfc_probe_host': args.ws23_pfc_probe_host,
                        'ws23_pfc_probe_pg': args.ws23_pfc_probe_pg,
                        'ws23_pfc_probe_start_ns': args.ws23_pfc_probe_start_ns,
                        'ws23_pfc_probe_end_ns': args.ws23_pfc_probe_end_ns,
                        'ws23_pause_time_us': args.ws23_pause_time_us},
              max_concurrent=args.max_concurrent)
    elif args.command == 'execute':
        execute(args.id)
    elif args.command == 'status':
        status(args.id)
    elif args.command == 'fetch-check':
        fetch_check(args.id)
    elif args.command == 'transfer-smoke':
        transfer_smoke(args.id)
    else:
        parser.print_help()
        return 2
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        sys.exit(1)
