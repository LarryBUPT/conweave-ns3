#!/usr/bin/env python3
"""Frozen, deterministic technical inputs. No performance or traffic-realism claim."""
from pathlib import Path
import hashlib
import json


def write_fixture(path, rows):
    rows = sorted(enumerate(rows), key=lambda item: (item[1][4], item[0]))
    content = str(len(rows)) + '\n'
    for _, (src, dst, pg, size, ns, tag) in rows:
        content += '{} {} {} {} {}.{:09d} {}\n'.format(src, dst, pg, size, ns//10**9, ns%10**9, tag)
    data = content.encode('ascii')
    if path.exists() and path.read_bytes() != data:
        raise RuntimeError('Refusing to overwrite changed fixture: ' + str(path))
    path.write_bytes(data)
    return {'path': path.as_posix(), 'sha256': hashlib.sha256(data).hexdigest(),
            'flows': len(rows), 'payload_bytes': sum(row[1][3] for row in rows)}


def main():
    root = Path(__file__).resolve().parents[1]
    canonical = []
    origin = 2005000000
    for i in range(16):
        canonical.append((i, 64+i, 3, 8388608, origin, 1))
    for i in range(64):
        canonical.append((i%16, 64+(7*i)%32, 3, 8192, origin+500+50*i, 2))
    for i in range(8):
        canonical.append((i, 80+i, 3, 8388608, origin+35000, 1))
    for i in range(16):
        canonical.append((i, 64+(7*i)%32, 3, 8192, origin+40000, 2))
    fallback = [(i, 64+i, 3, 8192 if i<3 else 1234, origin, [0,7,99][i%3]) for i in range(6)]
    fat = [(i%8, 16+(3*i)%16, 3, 65536 if i%2 else 8192, origin+100*i, i%2+1) for i in range(32)]
    reports=[]
    for name, rows in [('ws31_correctness_r1.txt', canonical), ('ws31_unknown_r1.txt', fallback),
                       ('ws31_ofan_fat_r1.txt', fat)]:
        reports.append(write_fixture(root/'config'/name, rows))
    print(json.dumps({'scope':'Technical correctness only; no effects sample', 'inputs': reports}, indent=2))


if __name__ == '__main__':
    main()
