#!/usr/bin/env python3
"""Make paired 0/64-background pilot traces with an independent trace seed."""
import argparse
import hashlib
import json
import os
import random


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
CONFIG = os.path.join(ROOT, 'config')
MOE = os.path.join(CONFIG, 'moe_1280group_256to8_8round_8KB.txt')
MIXED = os.path.join(CONFIG, 'moe_1280group_256to8_8round_8KB_hybrid_64fecmp.txt')


def read_rows(path):
    with open(path, encoding='utf-8') as source:
        count = int(source.readline())
        rows = [line.strip() for line in source if line.strip()]
    if len(rows) != count:
        raise ValueError('Declared trace count mismatch: ' + path)
    return rows


def digest(path):
    with open(path, 'rb') as source:
        return hashlib.sha256(source.read()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--moe-flows', type=int, default=256)
    args = parser.parse_args()
    moe = read_rows(MOE)
    mixed = read_rows(MIXED)
    bg = [row for row in mixed if row.split()[-1] == '1']
    if len(bg) != 64 or [row for row in mixed if row.split()[-1] == '2'] != moe:
        raise ValueError('Imported 64-background input is not the expected nested trace')
    if args.moe_flows < 1 or args.moe_flows > len(moe):
        raise ValueError('Invalid MoE subset size')
    selected_indices = set(random.Random(args.seed).sample(range(len(moe)), args.moe_flows))
    selected = [row for i, row in enumerate(moe) if i in selected_indices]
    stem = 'ws07_pilot_s%d_n%d' % (args.seed, args.moe_flows)
    output = {'trace_seed': args.seed, 'moe_flows': args.moe_flows,
              'source_moe_sha256': digest(MOE), 'source_mixed_sha256': digest(MIXED),
              'traces': {}}
    for count, rows in ((0, selected), (64, bg + selected)):
        name = '%s_bg%d.txt' % (stem, count)
        path = os.path.join(CONFIG, name)
        if os.path.exists(path):
            raise ValueError('Refusing to overwrite ' + path)
        with open(path, 'x', encoding='utf-8', newline='\n') as target:
            target.write(str(len(rows)) + '\n')
            target.write('\n'.join(rows) + '\n')
        output['traces'][name] = {'sha256': digest(path), 'flows': len(rows),
                                  'offered_bytes': sum(int(row.split()[3]) for row in rows)}
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
