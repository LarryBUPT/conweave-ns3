#!/usr/bin/env python3
"""Create and verify four order-only repetitions of the imported full traces."""
import collections
import hashlib
import json
import random
from pathlib import Path

from audit_ws11_inputs import EXPECTED, ROOT, STEM

SEEDS = (20261101, 20261102, 20261103, 20261104)
LEVELS = (0, 64, 128, 192)


def source_path(bg):
    return ROOT / 'config' / (STEM + ('' if bg == 0 else '_hybrid_%dfecmp' % bg) + '.txt')


def output_path(seed, bg):
    return ROOT / 'config' / ('ws11_s%d_bg%d.txt' % (seed, bg))


def read_rows(path):
    with path.open() as handle:
        count = int(handle.readline())
        rows = [line.rstrip('\r\n') for line in handle]
    assert count == len(rows)
    return rows


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    originals = {bg: read_rows(source_path(bg)) for bg in LEVELS}
    for bg in LEVELS:
        assert sha(source_path(bg)) == EXPECTED[bg]
    moe = [r for r in originals[0] if r.split()[-1] == '2']
    bg_all = [r for r in originals[192] if r.split()[-1] == '1']
    assert len(moe) == 16384 and len(bg_all) == 192
    assert all([r for r in originals[bg] if r.split()[-1] == '2'] == moe for bg in LEVELS)
    assert all([r for r in originals[bg] if r.split()[-1] == '1'] == bg_all[:bg]
               for bg in LEVELS)
    manifest = {'kind': 'order-only full-input robustness, not independent demand',
                'seeds': list(SEEDS), 'inputs': {}}
    for seed in SEEDS:
        moe_order = list(moe)
        background_order = list(bg_all)
        random.Random(seed).shuffle(moe_order)
        random.Random(seed ^ 0x9E3779B9).shuffle(background_order)
        # Preserve nested background sets: sort each prefix by one common rank.
        rank = {row: index for index, row in enumerate(background_order)}
        assert len(rank) == len(background_order)
        manifest['inputs'][str(seed)] = {}
        for bg in LEVELS:
            rows = moe_order + sorted(bg_all[:bg], key=rank.__getitem__)
            path = output_path(seed, bg)
            if path.exists():
                assert read_rows(path) == rows, 'Existing output differs: %s' % path
            else:
                with path.open('w', newline='\n') as target:
                    target.write(str(len(rows)) + '\n')
                    target.write('\n'.join(rows) + '\n')
            assert collections.Counter(read_rows(path)) == collections.Counter(originals[bg])
            manifest['inputs'][str(seed)][str(bg)] = {
                'file': path.name, 'sha256': sha(path), 'rows': len(rows),
                'source_sha256': EXPECTED[bg],
            }
    manifest_path = ROOT / 'docs' / 'research' / 'ws11-permutation-manifest.json'
    encoded = json.dumps(manifest, indent=2, sort_keys=True) + '\n'
    if manifest_path.exists():
        assert manifest_path.read_text(encoding='utf-8') == encoded
    else:
        manifest_path.write_text(encoded, encoding='utf-8', newline='\n')
    print('Verified 16 order-only full-input traces; manifest: %s' % manifest_path)


if __name__ == '__main__':
    main()
