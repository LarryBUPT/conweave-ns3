#!/usr/bin/env python3
import json
import os
import re
import sys
import time
import subprocess

root = '/home/fnl/lzy'
experiment_id = sys.argv[1]
if not re.match(r'^[0-9]{8}-[0-9]{6}-[a-z0-9][a-z0-9-]{0,40}$', experiment_id):
    raise RuntimeError('invalid experiment id')
base = os.path.join(root, 'results', experiment_id)
logs = os.path.join(base, 'logs')
meta_path = os.path.join(base, 'metadata.json')
samples_path = os.path.join(logs, 'resource-fast-samples.jsonl')
summary_path = os.path.join(logs, 'resource-fast-summary.json')

def process_tree_rss_kib(root_pid):
    listing = subprocess.check_output(
        ['ps', '-eo', 'pid,ppid,rss', '--no-headers']).decode('ascii')
    rows = {}
    for line in listing.splitlines():
        fields = line.split()
        if len(fields) == 3:
            rows[int(fields[0])] = (int(fields[1]), int(fields[2]))
    descendants = set([root_pid])
    for unused in range(30):
        addition = set(pid for pid, (parent, rss) in rows.items()
                       if parent in descendants)
        if addition.issubset(descendants):
            break
        descendants.update(addition)
    return sum(rows[pid][1] for pid in descendants if pid in rows)

def sample(root_pid):
    with open('/proc/meminfo') as source:
        memory = source.read()
    match = re.search(r'^MemAvailable:\s+(\d+) kB', memory, re.M)
    stat = os.statvfs(root)
    return {'time_utc_epoch': time.time(),
            'root_pid': root_pid,
            'process_tree_rss_mib': process_tree_rss_kib(root_pid) / 1024.0,
            'mem_available_gib': int(match.group(1)) / float(1024 ** 2),
            'free_gib': stat.f_bavail * stat.f_frsize / float(1024 ** 3),
            'load_1m': os.getloadavg()[0]}

terminal = ('SUCCEEDED', 'FAILED', 'BUILD_FAILED', 'INTERRUPTED')
running_seen = False
peak = 0.0
min_mem = float('inf')
min_disk = float('inf')
count = 0
started_at = time.time()
with open(samples_path, 'x') as receipt:
    receipt.write(json.dumps({'status': 'READY', 'time_utc_epoch': time.time()}) + '\n')
    receipt.flush()
    while True:
        with open(meta_path) as source:
            metadata = json.load(source)
        status = metadata.get('status')
        pid = metadata.get('pid')
        if status == 'RUNNING' and pid:
            point = sample(int(pid))
            point['status'] = status
            receipt.write(json.dumps(point, sort_keys=True) + '\n')
            receipt.flush()
            running_seen = True
            count += 1
            peak = max(peak, point['process_tree_rss_mib'])
            min_mem = min(min_mem, point['mem_available_gib'])
            min_disk = min(min_disk, point['free_gib'])
        elif status in terminal:
            break
        if time.time() - started_at > 900:
            raise RuntimeError('resource observer timed out')
        time.sleep(0.2)

summary = {'id': experiment_id, 'samples': count, 'running_seen': running_seen,
           'root_pid': metadata.get('pid'), 'peak_tree_rss_mib': peak,
           'minimum_mem_available_gib': min_mem if count else None,
           'minimum_free_gib': min_disk if count else None,
           'final_status': metadata.get('status')}
with open(summary_path, 'x') as target:
    json.dump(summary, target, indent=2, sort_keys=True)
    target.write('\n')
if not running_seen or count < 1 or peak <= 0:
    raise RuntimeError('no nonzero running-process resource sample')
