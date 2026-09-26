#!/usr/bin/env python3
"""Sample one isolated remote experiment; write receipts, stay silent."""
import argparse
import json
import os
import re
import subprocess
import time

ROOT = '/home/fnl/lzy'
ID_RE = re.compile(r'^[0-9]{8}-[0-9]{6}-[a-z0-9][a-z0-9-]{0,40}$')


def process_rss_kib(root_pid):
    listing = subprocess.check_output(
        ['ps', '-eo', 'pid,ppid,rss', '--no-headers']).decode('ascii')
    rows = {}
    for line in listing.splitlines():
        fields = line.split()
        if len(fields) == 3:
            rows[int(fields[0])] = (int(fields[1]), int(fields[2]))
    descendants = {root_pid}
    for _ in range(20):
        addition = {pid for pid, (parent, _) in rows.items() if parent in descendants}
        if addition.issubset(descendants):
            break
        descendants.update(addition)
    return sum(rows[pid][1] for pid in descendants if pid in rows)


def sample(root_pid):
    with open('/proc/meminfo') as source:
        memory = source.read()
    match = re.search(r'^MemAvailable:\s+(\d+) kB', memory, re.M)
    stat = os.statvfs(ROOT)
    return {'time_utc_epoch': time.time(), 'process_tree_rss_mib': process_rss_kib(root_pid) / 1024.0,
            'mem_available_gib': int(match.group(1)) / float(1024 ** 2),
            'free_gib': stat.f_bavail * stat.f_frsize / float(1024 ** 3),
            'load_1m': os.getloadavg()[0]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('id')
    parser.add_argument('--interval', type=int, default=5)
    args = parser.parse_args()
    if not ID_RE.match(args.id) or not 2 <= args.interval <= 60:
        raise RuntimeError('Invalid id or sample interval')
    base = os.path.join(ROOT, 'results', args.id)
    if os.path.realpath(base) != base or not os.path.isdir(base):
        raise RuntimeError('Experiment directory missing or redirected')
    path = os.path.join(base, 'logs', 'resource-samples.jsonl')
    if os.path.lexists(path):
        raise RuntimeError('Resource receipt exists; refusing overwrite')
    peak = 0.0
    min_mem = float('inf')
    min_disk = float('inf')
    count = 0
    with open(path, 'x') as receipt:
        while True:
            with open(os.path.join(base, 'metadata.json')) as source:
                metadata = json.load(source)
            pid = metadata.get('pid')
            if pid:
                point = sample(int(pid))
                point['status'] = metadata.get('status')
                receipt.write(json.dumps(point, sort_keys=True) + '\n')
                receipt.flush()
                count += 1
                peak = max(peak, point['process_tree_rss_mib'])
                min_mem = min(min_mem, point['mem_available_gib'])
                min_disk = min(min_disk, point['free_gib'])
            if metadata.get('status') not in ('BUILDING', 'BUILT', 'RUNNING'):
                break
            time.sleep(args.interval)
    summary = {'id': args.id, 'samples': count, 'peak_tree_rss_mib': peak,
               'minimum_mem_available_gib': min_mem,
               'minimum_free_gib': min_disk, 'final_status': metadata.get('status')}
    with open(os.path.join(base, 'logs', 'resource-summary.json'), 'x') as target:
        json.dump(summary, target, indent=2, sort_keys=True)
        target.write('\n')


if __name__ == '__main__':
    main()
