#!/usr/bin/env python3
"""Check the preregistered fixed-byte WS-10 inputs before simulation."""
import hashlib
import json
import os


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SEEDS = (20260926, 20261001, 20261002, 20261003, 20261004, 20261005)
TOTAL = 35651584
SMALL = 8192
LARGE = 8388608


def sha(path):
    with open(path, 'rb') as source:
        return hashlib.sha256(source.read()).hexdigest()


def rows(path):
    with open(path, encoding='utf-8') as source:
        declared = int(source.readline())
        content = [line.strip() for line in source if line.strip()]
    assert len(content) == declared, path
    assert all(len(row.split()) == 6 for row in content), path
    return content


def main():
    seen_targets = set()
    seen_traces = set()
    for seed in SEEDS:
        manifest_path = os.path.join(ROOT, 'docs', 'research',
                                     'ws10-fixed-s%d-manifest.json' % seed)
        with open(manifest_path, encoding='utf-8-sig') as source:
            manifest = json.load(source)
        assert manifest['trace_seed'] == seed
        assert manifest['simulator_seed'] == 1
        assert manifest['total_offered_bytes'] == TOTAL
        assert manifest['competing_bytes'] == 4 * LARGE
        assert manifest['target_moe_flows'] == 256
        assert len(set(manifest['background_source_indices'])) == 4
        target_path = os.path.join(ROOT, 'config', manifest['target_file'])
        assert sha(target_path) == manifest['target_sha256']
        target = set(rows(target_path))
        assert len(target) == 256 and all(row.split()[-1] == '2' for row in target)
        assert manifest['target_sha256'] not in seen_targets
        seen_targets.add(manifest['target_sha256'])
        backgrounds = {}
        for count in (0, 2, 4):
            name = 'ws07_fixed_s%d_t256_b4_bg%d.txt' % (seed, count)
            info = manifest['traces'][name]
            path = os.path.join(ROOT, 'config', name)
            assert sha(path) == info['sha256']
            assert info['sha256'] not in seen_traces
            seen_traces.add(info['sha256'])
            content = rows(path)
            bg = [row for row in content if row.split()[-1] == '1']
            moe = [row for row in content if row.split()[-1] == '2']
            assert len(bg) == count and len(moe) == 256 + (4 - count) * 1024
            assert info['background_flows'] == len(bg)
            assert info['moe_flows'] == len(moe)
            assert target <= set(moe)
            assert all(int(row.split()[3]) == SMALL for row in moe)
            assert all(int(row.split()[3]) == LARGE for row in bg)
            assert sum(int(row.split()[3]) for row in content) == TOTAL
            assert info['offered_bytes'] == TOTAL
            backgrounds[count] = set(bg)
        assert backgrounds[0] == set()
        assert backgrounds[2] <= backgrounds[4]
        print('seed=%d target=%s bg0/2/4=ok bytes=%d' %
              (seed, manifest['target_sha256'], TOTAL))
    print('All six independent target hashes and 18 trace hashes verified')


if __name__ == '__main__':
    main()
