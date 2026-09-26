#!/usr/bin/env python3
"""Local controller for the workspace-only ConWeave worker."""
import argparse
import datetime
import os
import re
import shlex
import shutil
import subprocess
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
ENV_FILE = os.path.join(PROJECT, '.project', 'remote.env')
WORKER = os.path.join(PROJECT, 'scripts', 'remote_worker.py')
ID_RE = re.compile(r'^[0-9]{8}-[0-9]{6}-[a-z0-9][a-z0-9-]{0,40}$')
FORK_RE = re.compile(r'^https://github[.]com/LarryBUPT/[A-Za-z0-9_.-]+(?:[.]git)?$')


def config():
    if not os.path.isfile(ENV_FILE):
        raise RuntimeError('Copy .project/remote.env.example to .project/remote.env')
    values = {}
    with open(ENV_FILE) as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                raise RuntimeError('Invalid remote.env line')
            key, value = line.split('=', 1)
            if key not in ('REMOTE_HOST', 'REMOTE_USER', 'REMOTE_ROOT') or not value:
                raise RuntimeError('Unexpected or empty remote.env setting')
            values[key] = value
    if set(values) != set(('REMOTE_HOST', 'REMOTE_USER', 'REMOTE_ROOT')):
        raise RuntimeError('remote.env needs host, user, and root')
    if values['REMOTE_ROOT'] != '/home/fnl/lzy':
        raise RuntimeError('Remote root must be /home/fnl/lzy')
    for name in ('REMOTE_HOST', 'REMOTE_USER'):
        if not re.match(r'^[A-Za-z0-9._-]+$', values[name]):
            raise RuntimeError('Invalid SSH host or user')
    return values


def ssh_base(cfg):
    return ['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'ConnectTimeout=10', cfg['REMOTE_USER'] + '@' + cfg['REMOTE_HOST']]


def worker_call(cfg, *args):
    remote = '/home/fnl/lzy/.research-workflow/remote_worker.py'
    command = ' '.join(shlex.quote(part) for part in ['python3', remote] + list(args))
    subprocess.check_call(ssh_base(cfg) + [command])


def git_output(repo, *args):
    return subprocess.check_output(['git', '-C', repo] + list(args),
                                   stderr=subprocess.STDOUT).decode('utf-8').strip()


def local_fork(repo, require_pushed=False):
    repo = os.path.realpath(repo)
    if not os.path.isdir(repo):
        raise RuntimeError('Local fork checkout does not exist')
    origin = git_output(repo, 'config', '--get', 'remote.origin.url')
    if not FORK_RE.match(origin):
        raise RuntimeError('origin must be a LarryBUPT GitHub repository')
    branch = git_output(repo, 'symbolic-ref', '--short', 'HEAD')
    if not re.match(r'^(feature|experiment|idea|research)/[A-Za-z0-9._/-]+$', branch):
        raise RuntimeError('Use a personal feature/, experiment/, idea/, or research/ branch')
    sha = git_output(repo, 'rev-parse', 'HEAD')
    if git_output(repo, 'status', '--porcelain'):
        raise RuntimeError('Local checkout has uncommitted changes')
    for name in ('upstream', 'reference-maplerime'):
        try:
            push_url = git_output(repo, 'remote', 'get-url', '--push', name)
        except subprocess.CalledProcessError:
            raise RuntimeError('Missing protected reference remote: ' + name)
        if push_url != 'no-push://read-only-reference':
            raise RuntimeError('Reference remote lacks push protection: ' + name)
    if require_pushed:
        refs = git_output(repo, 'ls-remote', '--heads', 'origin', branch)
        if not refs or refs.split()[0] != sha:
            raise RuntimeError('Current commit is not yet on the personal fork branch')
    return repo, origin, branch, sha


def protect_fork(repo):
    repo = os.path.realpath(repo)
    origin = git_output(repo, 'config', '--get', 'remote.origin.url')
    if not FORK_RE.match(origin):
        raise RuntimeError('origin must be a LarryBUPT GitHub repository')
    for name, url in (('upstream', 'https://github.com/conweave-project/conweave-ns3.git'),
                      ('reference-maplerime', 'https://github.com/maplerime/conweave-ns3.git')):
        try:
            old_url = git_output(repo, 'config', '--get', 'remote.' + name + '.url')
        except subprocess.CalledProcessError:
            old_url = None
        if old_url and old_url != url:
            raise RuntimeError('Unexpected URL for ' + name)
        if not old_url:
            subprocess.check_call(['git', '-C', repo, 'remote', 'add', name, url])
        subprocess.check_call(['git', '-C', repo, 'config', '--local',
                               'remote.' + name + '.pushurl', 'no-push://read-only-reference'])
    subprocess.check_call(['git', '-C', repo, 'config', '--local', 'push.default', 'nothing'])
    hook = os.path.join(repo, '.githooks', 'pre-push')
    if os.path.isfile(hook):
        subprocess.check_call(['git', '-C', repo, 'config', '--local',
                               'core.hooksPath', '.githooks'])
    print(git_output(repo, 'remote', '-v'))


def deploy(cfg):
    # stdin contains only this repository's worker source, never credentials.
    bootstrap = (
        'import os,stat,sys,tempfile; '
        'root="/home/fnl/lzy"; '
        'assert os.path.realpath(root)==root and os.path.isdir(root); '
        'folder=root+"/.research-workflow"; '
        'assert not os.path.islink(folder); '
        'os.makedirs(folder,exist_ok=True); '
        'assert os.path.realpath(folder)==folder; '
        'target=folder+"/remote_worker.py"; '
        'assert not os.path.islink(target); '
        'assert not os.path.exists(target) or stat.S_ISREG(os.stat(target).st_mode); '
        'fd,tmp=tempfile.mkstemp(prefix="worker-",dir=folder); '
        'stream=os.fdopen(fd,"wb"); '
        'stream.write(sys.stdin.buffer.read()); stream.close(); '
        'os.chmod(tmp,0o600); os.replace(tmp,target); '
        'print("worker deployed inside workspace")')
    with open(WORKER, 'rb') as source:
        body = source.read()
    command = 'python3 -c ' + shlex.quote(bootstrap)
    subprocess.run(ssh_base(cfg) + [command], input=body, check=True)


def fetch(cfg, experiment_id):
    if not ID_RE.match(experiment_id):
        raise RuntimeError('Invalid experiment ID')
    worker_call(cfg, 'fetch-check', experiment_id)
    root = os.path.realpath(os.path.join(PROJECT, 'results'))
    os.makedirs(root, exist_ok=True)
    if not root.startswith(os.path.realpath(PROJECT) + os.sep):
        raise RuntimeError('Local result path escapes project')
    target = os.path.join(root, experiment_id)
    if os.path.lexists(target):
        raise RuntimeError('Local result already exists; refusing overwrite')
    incoming = os.path.join(root, '.incoming-' + experiment_id + '-' + str(os.getpid()))
    if os.path.lexists(incoming):
        raise RuntimeError('Transfer staging path already exists')
    remote = cfg['REMOTE_USER'] + '@' + cfg['REMOTE_HOST'] + ':/home/fnl/lzy/results/' + experiment_id
    subprocess.check_call(['scp', '-r', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                           remote, incoming])
    if not os.path.isfile(os.path.join(incoming, 'metadata.json')):
        raise RuntimeError('Transfer incomplete; staging directory retained: ' + incoming)
    os.rename(incoming, target)
    print('Local results: ' + target)


def sync_by_bundle(cfg, repo, origin, branch, sha):
    """Use Git history over SSH when the server cannot reach GitHub."""
    results_root = os.path.realpath(os.path.join(PROJECT, 'results'))
    if not results_root.startswith(PROJECT + os.sep):
        raise RuntimeError('Local results path escapes project')
    bundle_dir = os.path.join(results_root, '.sync-bundles')
    os.makedirs(bundle_dir, exist_ok=True)
    bundle_name = 'sync-' + sha + '-' + str(os.getpid()) + '.bundle'
    bundle = os.path.join(bundle_dir, bundle_name)
    if os.path.lexists(bundle):
        raise RuntimeError('Git bundle staging path already exists')
    subprocess.check_call(['git', '-C', repo, 'bundle', 'create', bundle,
                           'refs/heads/' + branch])
    # The destination is under the already verified workspace tool directory.
    remote_path = '/home/fnl/lzy/.research-workflow/' + bundle_name
    check = ('test ! -e ' + shlex.quote(remote_path) +
             ' && test "$(readlink -f /home/fnl/lzy)" = /home/fnl/lzy' +
             ' && test "$(readlink -f /home/fnl/lzy/.research-workflow)" = /home/fnl/lzy/.research-workflow')
    subprocess.check_call(ssh_base(cfg) + [check])
    destination = cfg['REMOTE_USER'] + '@' + cfg['REMOTE_HOST'] + ':' + remote_path
    subprocess.check_call(['scp', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                           bundle, destination])
    worker_call(cfg, 'sync-bundle', '--repo', origin, '--sha', sha,
                '--branch', branch, '--bundle-name', bundle_name)
    print('Source synchronized through workspace Git bundle')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command')
    for name in ('deploy', 'check'):
        sub.add_parser(name)
    for name in ('push', 'sync', 'sync-bundle', 'build'):
        item = sub.add_parser(name)
        item.add_argument('--repo-local', required=True)
        if name == 'build':
            item.add_argument('--id')
            item.add_argument('--label', default='baseline')
    protect_cmd = sub.add_parser('protect-fork')
    protect_cmd.add_argument('--repo-local', required=True)
    run_cmd = sub.add_parser('run')
    run_cmd.add_argument('id')
    run_cmd.add_argument('--lb', choices=['fecmp', 'conga', 'letflow', 'conweave', 'dualtrack', 'shortq2', 'guardhash', 'guardhashgate'], default='fecmp')
    run_cmd.add_argument('--simul-time', default='0.01')
    run_cmd.add_argument('--netload', type=int, default=10)
    run_cmd.add_argument('--max-concurrent', type=int, choices=(1, 2, 4, 8, 12), default=1,
                         help='admission cap after WS-11 resource pilot; default remains one')
    run_cmd.add_argument('--bw', type=int, choices=[100, 400], default=100)
    run_cmd.add_argument('--buffer', type=int, choices=range(1, 10), default=9,
                         help='switch buffer size in MiB (1-9; default: 9)')
    run_cmd.add_argument('--topo', default='leaf_spine_128_100G_OS2')
    run_cmd.add_argument('--cdf', default='AliStorage2019')
    run_cmd.add_argument('--flow-file', help='existing tracked config/*.txt trace')
    run_cmd.add_argument('--pfc', type=int, choices=[0, 1], default=1)
    run_cmd.add_argument('--irn', type=int, choices=[0, 1], default=0)
    for name in ('status', 'fetch', 'transfer-smoke'):
        item = sub.add_parser(name)
        item.add_argument('id')
    args = parser.parse_args()
    cfg = config()
    if args.command == 'deploy':
        deploy(cfg)
    elif args.command == 'check':
        worker_call(cfg, 'audit')
    elif args.command == 'protect-fork':
        protect_fork(args.repo_local)
    elif args.command in ('push', 'sync', 'sync-bundle', 'build'):
        repo, origin, branch, sha = local_fork(args.repo_local,
                                               require_pushed=args.command != 'push')
        if args.command == 'push':
            subprocess.check_call(['git', '-C', repo, 'push', 'origin',
                                   'HEAD:refs/heads/' + branch])
        elif args.command == 'sync':
            try:
                worker_call(cfg, 'sync', '--repo', origin, '--sha', sha)
            except subprocess.CalledProcessError:
                print('Server GitHub fetch failed; using Git bundle over SSH.', file=sys.stderr)
                sync_by_bundle(cfg, repo, origin, branch, sha)
        elif args.command == 'sync-bundle':
            sync_by_bundle(cfg, repo, origin, branch, sha)
        else:
            label = re.sub(r'[^a-z0-9-]', '-', args.label.lower()).strip('-')
            experiment_id = args.id or datetime.datetime.now().strftime('%Y%m%d-%H%M%S-') + label
            if not ID_RE.match(experiment_id):
                raise RuntimeError('Invalid experiment ID')
            worker_call(cfg, 'build', '--id', experiment_id, '--sha', sha, '--branch', branch)
            print('Experiment ID: ' + experiment_id)
    elif args.command == 'run':
        if args.pfc + args.irn != 1:
            parser.error('Exactly one of --pfc and --irn must be enabled')
        command = ['run', '--id', args.id, '--lb', args.lb, '--simul-time', args.simul_time,
                    '--netload', str(args.netload), '--bw', str(args.bw),
                    '--max-concurrent', str(args.max_concurrent),
                    '--buffer', str(args.buffer),
                    '--topo', args.topo, '--cdf', args.cdf,
                    '--pfc', str(args.pfc), '--irn', str(args.irn)]
        if args.flow_file:
            command.extend(['--flow-file', args.flow_file])
        worker_call(cfg, *command)
    elif args.command == 'status':
        worker_call(cfg, 'status', args.id)
    elif args.command == 'fetch':
        fetch(cfg, args.id)
    elif args.command == 'transfer-smoke':
        worker_call(cfg, 'transfer-smoke', args.id)
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
