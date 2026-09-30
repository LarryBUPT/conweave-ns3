#!/usr/bin/env python3
"""Start the WS-23 fast resource observer for one already-built experiment.

This does not deploy or replace the shared remote worker. Run it only after the
shared-worker and model-supervision gates in the WS-23 preflight are satisfied.
"""
import argparse
import base64
import os
import shlex
import subprocess

from remote_experiment import ID_RE, PROJECT, config, ssh_base


REMOTE_START = r'''
import base64
import json
import os
import re
import sys
import time

root = '/home/fnl/lzy'
experiment_id, encoded, expected_sha = sys.argv[1:4]
if not re.match(r'^[0-9]{8}-[0-9]{6}-[a-z0-9][a-z0-9-]{0,40}$', experiment_id):
    raise RuntimeError('invalid experiment ID')
if not re.match(r'^[0-9a-f]{40}$', expected_sha):
    raise RuntimeError('invalid source SHA')
base = os.path.join(root, 'results', experiment_id)
logs = os.path.join(base, 'logs')
for path in (root, base, logs):
    if os.path.realpath(path) != path or not os.path.isdir(path):
        raise RuntimeError('missing or redirected result directory')
with open(os.path.join(base, 'metadata.json')) as source:
    metadata = json.load(source)
if metadata.get('status') != 'BUILT' or metadata.get('git_commit') != expected_sha:
    raise RuntimeError('experiment is not BUILT at the expected source SHA')
program = os.path.join(logs, 'ws23-resource-watch.py')
samples = os.path.join(logs, 'resource-fast-samples.jsonl')
summary = os.path.join(logs, 'resource-fast-summary.json')
launch_log = os.path.join(logs, 'resource-fast-launch.log')
if any(os.path.lexists(path) for path in (program, samples, summary, launch_log)):
    raise RuntimeError('observer or receipt already exists; preserve this ID')
body = base64.b64decode(encoded)
fd = os.open(program, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'wb') as target:
    target.write(body)
pid = os.fork()
if pid == 0:
    os.setsid()
    input_fd = os.open('/dev/null', os.O_RDONLY)
    output_fd = os.open(launch_log, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.dup2(input_fd, 0)
    os.dup2(output_fd, 1)
    os.dup2(output_fd, 2)
    os.close(input_fd)
    os.close(output_fd)
    os.execv(sys.executable, [sys.executable, program, experiment_id])
for unused in range(100):
    if os.path.isfile(samples):
        with open(samples) as source:
            first = source.readline()
        if first:
            receipt = json.loads(first)
            if receipt.get('status') != 'READY':
                raise RuntimeError('observer did not publish READY')
            print(json.dumps({'id': experiment_id, 'observer_pid': pid,
                              'status': 'READY'}, sort_keys=True))
            break
    try:
        os.kill(pid, 0)
    except OSError:
        raise RuntimeError('observer exited before READY')
    time.sleep(0.1)
else:
    raise RuntimeError('observer did not become READY within ten seconds')
'''

REMOTE_WAIT = r'''
import json
import os
import sys
import time

experiment_id, expected_sha = sys.argv[1:3]
base = os.path.join('/home/fnl/lzy/results', experiment_id)
path = os.path.join(base, 'logs', 'resource-fast-summary.json')
with open(os.path.join(base, 'metadata.json')) as source:
    metadata = json.load(source)
if metadata.get('git_commit') != expected_sha:
    raise RuntimeError('source SHA changed')
if metadata.get('status') not in ('SUCCEEDED', 'FAILED', 'BUILD_FAILED', 'INTERRUPTED'):
    raise RuntimeError('simulation is not terminal')
for unused in range(100):
    if os.path.isfile(path):
        try:
            with open(path) as source:
                receipt = json.load(source)
        except ValueError:
            time.sleep(0.1)
            continue
        if receipt.get('id') != experiment_id or receipt.get('final_status') != metadata['status']:
            raise RuntimeError('resource receipt identity or status differs')
        if not receipt.get('running_seen') or receipt.get('samples', 0) < 1 or \
                receipt.get('peak_tree_rss_mib', 0) <= 0:
            raise RuntimeError('no positive running-process resource sample')
        if receipt['peak_tree_rss_mib'] > 8192 or \
                receipt.get('minimum_mem_available_gib', 0) < 16 or \
                receipt.get('minimum_free_gib', 0) < 100:
            raise RuntimeError('resource stop threshold crossed; preserve this ID')
        samples = os.path.join(base, 'logs', 'resource-fast-samples.jsonl')
        maximum_load = 0.0
        positive = 0
        with open(samples) as source:
            for line in source:
                point = json.loads(line)
                if point.get('status') == 'RUNNING':
                    positive += point.get('process_tree_rss_mib', 0) > 0
                    maximum_load = max(maximum_load, point.get('load_1m', 0))
        if positive < 1 or maximum_load > 20:
            raise RuntimeError('resource samples missing or load stop threshold crossed')
        receipt['maximum_sampled_load_1m'] = maximum_load
        print(json.dumps(receipt, sort_keys=True))
        break
    time.sleep(0.1)
else:
    raise RuntimeError('resource summary missing after terminal status')
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment_id')
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--wait', action='store_true',
                        help='after terminal status, require a positive resource receipt')
    args = parser.parse_args()
    if not ID_RE.fullmatch(args.experiment_id):
        parser.error('invalid experiment ID')
    if len(args.source_sha) != 40 or any(char not in '0123456789abcdef'
                                         for char in args.source_sha):
        parser.error('--source-sha must be a full lowercase Git commit SHA')
    if args.wait:
        parts = ('python3', '-c', REMOTE_WAIT, args.experiment_id,
                 args.source_sha)
    else:
        watcher = os.path.join(PROJECT, 'scripts', 'ws23_resource_watch_fast.py')
        with open(watcher, 'rb') as source:
            encoded = base64.b64encode(source.read()).decode('ascii')
        parts = ('python3', '-c', REMOTE_START, args.experiment_id,
                 encoded, args.source_sha)
    command = ' '.join(shlex.quote(part) for part in parts)
    output = subprocess.check_output(ssh_base(config()) + [command],
                                     stderr=subprocess.STDOUT, timeout=30)
    print(output.decode('utf-8').strip())


if __name__ == '__main__':
    main()
