#!/usr/bin/env python3
"""Small, deterministic packet-label visibility fixture; no efficacy sample."""
from pathlib import Path
import hashlib
import json


def tuple_hash(src, dst, sport=10000, dport=100):
    value = 2166136261 ^ 0x43c2a517
    for word in ((11 << 24) | (src << 8) | 1,
                 (11 << 24) | (dst << 8) | 1, sport | (dport << 16)):
        for shift in range(0, 32, 8):
            value = ((value ^ ((word >> shift) & 255))*16777619) & 0xffffffff
    value ^= value >> 16
    value = (value*0x85ebca6b) & 0xffffffff
    return value ^ (value >> 13)


def main():
    # Separate source NICs remove pre-existing source-QP scheduling as a cause
    # of late first construction. Actual early/late coverage is still checked.
    rows, cohorts = [], []
    for src in range(15):
        tag = 1 if src < 6 else 2 if src < 12 else (0, 7, 99)[src-12]
        dst = 64+src
        rows.append('{} {} 3 16384 2.005000000 {}'.format(src, dst, tag))
        bucket = tuple_hash(src, dst) & 3
        cohorts.append({'src': src, 'dst': dst, 'sport': 10000, 'dport': 100,
                        'original_tag': tag, 'bucket': bucket,
                        'swapped': tag in (1, 2) and bucket == 0})
    for tag in (1, 2):
        group = [v for v in cohorts if v['original_tag'] == tag]
        assert any(v['swapped'] for v in group) and any(not v['swapped'] for v in group)
    data = ('15\n'+'\n'.join(rows)+'\n').encode('ascii')
    path = Path(__file__).resolve().parents[1]/'config/ws31_labels_r1.txt'
    if path.exists() and path.read_bytes() != data:
        raise RuntimeError('Refusing to overwrite changed label fixture')
    path.write_bytes(data)
    print(json.dumps({'scope': 'Synthetic label correctness only; no error-rate or efficacy claim',
                      'file': path.name, 'sha256': hashlib.sha256(data).hexdigest(),
                      'flows': 15, 'payload_bytes': 245760, 'cohorts': cohorts}, indent=2))


if __name__ == '__main__':
    main()
