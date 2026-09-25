#!/usr/bin/env python3
"""Generate fixed-byte replacement traces; target MoE rows stay unchanged."""
import argparse
import hashlib
import json
import os
import random

from make_ws07_pilot_traces import CONFIG, MOE, MIXED, read_rows

SMALL = 8192
LARGE = 8388608


def digest(path):
    with open(path, 'rb') as source:
        return hashlib.sha256(source.read()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--target-moe', type=int, default=256)
    parser.add_argument('--max-background', type=int, default=4)
    args = parser.parse_args()
    moe = read_rows(MOE)
    mixed = read_rows(MIXED)
    background = [row for row in mixed if row.split()[-1] == '1']
    if [row for row in mixed if row.split()[-1] == '2'] != moe:
        raise ValueError('Imported mixed trace does not contain the original MoE rows')
    if args.max_background < 1 or args.max_background > len(background):
        raise ValueError('Invalid background count')
    filler_max = args.max_background * LARGE // SMALL
    if args.max_background * LARGE % SMALL or args.target_moe < 1 or \
            args.target_moe + filler_max > len(moe):
        raise ValueError('Insufficient distinct MoE pairs for this byte budget')
    rng = random.Random(args.seed)
    chosen = rng.sample(range(len(moe)), args.target_moe + filler_max)
    background_indices = rng.sample(range(len(background)), args.max_background)
    target_indices = set(chosen[:args.target_moe])
    filler_indices = chosen[args.target_moe:]
    target = [row for i, row in enumerate(moe) if i in target_indices]
    stem = 'ws07_fixed_s%d_t%d_b%d' % (args.seed, args.target_moe,
                                      args.max_background)
    manifest = {'trace_seed': args.seed, 'simulator_seed': 1,
                'target_moe_flows': args.target_moe,
                'competing_bytes': args.max_background * LARGE,
                'total_offered_bytes': (args.target_moe * SMALL +
                                        args.max_background * LARGE),
                'source_moe_sha256': digest(MOE), 'source_mixed_sha256': digest(MIXED),
                'background_source_indices': background_indices,
                'traces': {}}
    target_path = os.path.join(CONFIG, stem + '_target.txt')
    if os.path.exists(target_path):
        raise ValueError('Refusing to overwrite target list')
    with open(target_path, 'x', encoding='utf-8', newline='\n') as output:
        output.write(str(len(target)) + '\n' + '\n'.join(target) + '\n')
    manifest['target_file'] = os.path.basename(target_path)
    manifest['target_sha256'] = digest(target_path)
    for bg_count in (0, args.max_background // 2, args.max_background):
        filler_count = (args.max_background - bg_count) * LARGE // SMALL
        selected = target_indices | set(filler_indices[:filler_count])
        moe_rows = [row for i, row in enumerate(moe) if i in selected]
        rows = [background[i] for i in background_indices[:bg_count]] + moe_rows
        name = stem + '_bg%d.txt' % bg_count
        path = os.path.join(CONFIG, name)
        if os.path.exists(path):
            raise ValueError('Refusing to overwrite ' + name)
        with open(path, 'x', encoding='utf-8', newline='\n') as output:
            output.write(str(len(rows)) + '\n' + '\n'.join(rows) + '\n')
        offered = sum(int(row.split()[3]) for row in rows)
        if offered != manifest['total_offered_bytes']:
            raise AssertionError('Fixed offered bytes violated')
        manifest['traces'][name] = {'sha256': digest(path),
                                    'background_flows': bg_count,
                                    'moe_flows': len(moe_rows),
                                    'offered_bytes': offered}
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
