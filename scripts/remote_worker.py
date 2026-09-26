#!/usr/bin/env python3
"""Workspace-only ConWeave experiment worker (Python 3.5 compatible)."""
import argparse
import contextlib
import datetime
import glob
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
            'cpu_jobs': 2, 'build_mode': 'optimized', 'seed': 1}
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
        if len(raw_dirs) != 1 or not fct or not any(os.path.getsize(p) > 0 for p in fct):
            raise RuntimeError('run.py ended without a nonempty FCT output; inspect simulation.log')
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
        data['status'] = 'SUCCEEDED'
        data['raw_directory'] = os.path.basename(raw_dirs[0])
    except Exception as error:
        data['status'] = 'FAILED'
        data['error'] = str(error)
        raise
    finally:
        data['finished_utc'] = stamp()
        save_metadata(base, data)


def start(experiment_id, params, max_concurrent=1):
    resources_ok()
    if max_concurrent not in (1, 2, 4):
        raise RuntimeError('Concurrency must be 1, 2, or 4 after resource pilot')
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
    run_cmd.add_argument('--lb', choices=['fecmp', 'conga', 'letflow', 'conweave', 'dualtrack', 'shortq2', 'guardhash', 'guardhashgate'], default='fecmp')
    run_cmd.add_argument('--simul-time', default='0.01')
    run_cmd.add_argument('--netload', type=int, default=10)
    run_cmd.add_argument('--max-concurrent', type=int, choices=(1, 2, 4), default=1)
    run_cmd.add_argument('--bw', type=int, choices=[100, 400], default=100)
    run_cmd.add_argument('--buffer', type=int, choices=range(1, 10), default=9)
    run_cmd.add_argument('--topo', default='leaf_spine_128_100G_OS2')
    run_cmd.add_argument('--cdf', default='AliStorage2019')
    run_cmd.add_argument('--flow-file')
    run_cmd.add_argument('--pfc', type=int, choices=[0, 1], default=1)
    run_cmd.add_argument('--irn', type=int, choices=[0, 1], default=0)
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
        if args.pfc + args.irn != 1:
            raise RuntimeError('Exactly one of PFC and IRN must be enabled')
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
                        'flow_file': flow_file}, max_concurrent=args.max_concurrent)
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
