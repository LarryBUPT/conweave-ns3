#!/usr/bin/env python3
"""Verify versioned WS-07 trace manifests and replacement invariants."""
import hashlib
import json
import os


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
CONFIG = os.path.join(ROOT, 'config')
RESEARCH = os.path.join(ROOT, 'docs', 'research')


def read_rows(name):
    path = os.path.join(CONFIG, name)
    with open(path, 'rb') as source:
        raw = source.read()
    rows = raw.decode('utf-8').splitlines()
    count = int(rows[0])
    if count != len(rows) - 1:
        raise ValueError('Count mismatch: ' + name)
    return rows[1:], hashlib.sha256(raw).hexdigest()


def verify():
    with open(os.path.join(RESEARCH, 'ws07-pilot-manifest.json'), encoding='utf-8') as source:
        pilot = json.load(source)
    with open(os.path.join(RESEARCH, 'ws07-fixed-load-manifest.json'), encoding='utf-8') as source:
        fixed = json.load(source)
    for manifest in (pilot, fixed):
        for name, description in manifest['traces'].items():
            rows, digest = read_rows(name)
            if digest != description['sha256'] or len(rows) != description.get('flows', len(rows)):
                raise ValueError('Manifest hash/count mismatch: ' + name)
            offered = sum(int(row.split()[3]) for row in rows)
            if offered != description['offered_bytes']:
                raise ValueError('Offered bytes mismatch: ' + name)
            if any(int(row.split()[0]) % 4 or int(row.split()[1]) % 4 or
                   row.split()[4] != '2.000000000' for row in rows):
                raise ValueError('Rail or start-time contract violated: ' + name)
    pilot0, _ = read_rows('ws07_pilot_s20260925_n256_bg0.txt')
    pilot64, _ = read_rows('ws07_pilot_s20260925_n256_bg64.txt')
    if [row for row in pilot64 if row.split()[-1] == '2'] != pilot0 or \
            len([row for row in pilot64 if row.split()[-1] == '1']) != 64:
        raise ValueError('Pilot MoE subset or background count differs')
    target, target_hash = read_rows(fixed['target_file'])
    if target_hash != fixed['target_sha256'] or len(target) != fixed['target_moe_flows']:
        raise ValueError('Fixed target manifest mismatch')
    for name, description in fixed['traces'].items():
        rows, _ = read_rows(name)
        if not set(target).issubset(set(rows)) or \
                sum(int(row.split()[3]) for row in rows) != fixed['total_offered_bytes'] or \
                len([row for row in rows if row.split()[-1] == '1']) != description['background_flows']:
            raise ValueError('Fixed-byte or target invariant violated: ' + name)
    print('WS07 trace manifests and invariants verified')


if __name__ == '__main__':
    verify()
