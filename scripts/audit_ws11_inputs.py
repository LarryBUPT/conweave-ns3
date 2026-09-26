#!/usr/bin/env python3
"""Audit the imported full-MoE traces without changing their contents."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEM = 'moe_1280group_256to8_8round_8KB'
EXPECTED = {
    0: '9e00baa5c79ab45b107b82b4c18d43cbb9a1073101bf14123aedd2d90d2e89fd',
    64: '83d0b2ff46d683d243bcd1d4b2fc4c2fefa330324062d13dcfb878af5abdd7dc',
    128: 'd1dd382fb7cefc368cbfe10ad5a7db21566aa417e16248172559a7bd9283f5c5',
    192: 'bf1a1960651b2d5bd27cd1304433d489363727a7c02d08c5c05df2b2415d9c8a',
}
TOPO_SHA = '74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(bg):
    suffix = '' if bg == 0 else '_hybrid_%dfecmp' % bg
    path = ROOT / 'config' / (STEM + suffix + '.txt')
    actual = digest(path)
    assert actual == EXPECTED[bg], (path, actual)
    with path.open() as source:
        count = int(source.readline().strip())
        rows = [tuple(line.split()) for line in source]
    assert count == len(rows) == 16384 + bg
    assert all(len(row) == 6 and row[2] == '3' and row[4] == '2.000000000' for row in rows)
    moe = [row for row in rows if row[5] == '2']
    background = [row for row in rows if row[5] == '1']
    assert len(moe) == 16384 and len(background) == bg
    assert all(int(row[3]) == 8192 for row in moe)
    assert all(int(row[3]) == 8388608 for row in background)
    sources = collections.Counter(int(row[0]) for row in moe)
    destinations = collections.Counter(int(row[1]) for row in moe)
    pairs = collections.Counter((int(row[0]), int(row[1])) for row in moe)
    return {
        'file': path.name, 'sha256': actual, 'count': count,
        'moe_rows': moe, 'background_rows': background,
        'moe_bytes': 16384 * 8192, 'background_bytes': bg * 8388608,
        'offered_bytes': 16384 * 8192 + bg * 8388608,
        'moe_source_count': len(sources), 'moe_destination_count': len(destinations),
        'moe_source_max_flows': max(sources.values()),
        'moe_destination_max_flows': max(destinations.values()),
        'moe_pair_max_flows': max(pairs.values()),
        'moe_destination_top8': destinations.most_common(8),
        'background_source_count': len(set(int(row[0]) for row in background)),
        'background_destination_count': len(set(int(row[1]) for row in background)),
    }


def main():
    topo = ROOT / 'config' / 'topo_1280_400G_400G_OS1.txt'
    assert digest(topo) == TOPO_SHA
    data = {bg: inspect(bg) for bg in EXPECTED}
    base_moe = data[0]['moe_rows']
    for bg in (64, 128, 192):
        assert data[bg]['moe_rows'] == base_moe, 'MoE rows/order differ at bg %d' % bg
    for low, high in ((64, 128), (128, 192)):
        assert (data[high]['background_rows'][:low] == data[low]['background_rows']), \
            'Background records not nested: %d -> %d' % (low, high)
    result = {'topology_sha256': TOPO_SHA,
              'same_ordered_moe_in_all_files': True,
              'nested_background_across_levels': True,
              'inputs': {str(bg): {key: value for key, value in row.items()
                                    if not key.endswith('_rows')} for bg, row in data.items()}}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
