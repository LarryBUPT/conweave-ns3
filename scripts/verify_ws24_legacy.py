#!/usr/bin/env python3
"""Check one WS-24 legacy five/six-column baseline cell from fetched raw data."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FLOW_SHA = {
    'legacy5': 'abebc3170428aa22ebb13b15246243b806cb4f749bf4c9e6a80fb0a4a694a3cf',
    'legacy6': 'be78b4cb5afbcceb51f42ee10594c32b8a4322bc3e069ed0413554e41ba75748',
}
TOPO_SHA = '0dddc4f3ae673139b895ff2f875befe82b234cc48e325bd8a164d9cddedc12e2'
LB_MODE = {'fecmp': 0, 'conga': 3, 'letflow': 6, 'conweave': 9}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(experiment_id, source_sha, flow_kind, lb):
    base = ROOT / 'results' / experiment_id
    meta = json.loads((base / 'metadata.json').read_text(encoding='utf-8'))
    params = meta['parameters']
    assert meta['status'] == 'SUCCEEDED' and meta['git_commit'] == source_sha
    assert params.get('ws24_multi_nic', 0) == 0 and params['lb'] == lb
    assert params['topo'] == 'leaf_spine_128_100G_OS2'
    assert int(params.get('bw', 100)) == 100 and int(params.get('buffer', 9)) == 9
    assert int(params['pfc']) == 1 and int(params['irn']) == 0
    trace = base / 'config' / 'traffic_trace.txt'
    topo = base / 'config' / 'topology.txt'
    assert sha(trace) == meta['input_flow_sha256'] == FLOW_SHA[flow_kind]
    assert sha(topo) == meta['topology_sha256'] == TOPO_SHA
    topo_rows = topo.read_text(encoding='ascii').splitlines()
    assert topo_rows[0].strip() == '144 16 192'
    assert len(topo_rows) >= 194
    assert all(len(row.split()) == 5 and row.split()[3] == '1000ns'
               for row in topo_rows[2:194])
    rows = trace.read_text(encoding='ascii').splitlines()
    assert int(rows[0]) == len(rows) - 1 == (19388 if flow_kind == 'legacy5' else 4)
    expected_columns = 5 if flow_kind == 'legacy5' else 6
    demands = Counter()
    tags = Counter()
    for line in rows[1:]:
        fields = line.split()
        assert len(fields) == expected_columns
        src, dst, pg, size = map(int, fields[:4])
        tag = int(fields[5]) if expected_columns == 6 else 0
        assert 0 <= src < 128 and 0 <= dst < 128 and src != dst and size > 0
        demands[src, dst, size] += 1
        tags[tag] += 1
    raw = base / 'raw' / str(meta['raw_directory'])
    fct_files = list(raw.glob('*_out_fct.txt'))
    uplink_files = list(raw.glob('*_out_uplink.txt'))
    assert len(fct_files) == len(uplink_files) == 1
    fct_rows = [line.split() for line in fct_files[0].read_text(encoding='ascii').splitlines()
                if line.strip()]
    assert len(fct_rows) == len(rows) - 1
    completed = Counter()
    for fields in fct_rows:
        assert len(fields) == 8
        src, dst, sport, dport, size, start, fct, standalone = map(int, fields)
        assert sport >= 0 and dport >= 0 and start > 0 and fct > 0 and standalone > 0
        completed[src, dst, size] += 1
    assert completed == demands
    uplink_rows = [line.split(',') for line in uplink_files[0].read_text(
        encoding='ascii').splitlines() if line.strip()]
    assert uplink_rows and all(len(row) == 4 and all(item.isdigit() for item in row)
                               for row in uplink_rows)
    config = (base / 'config' / 'config.txt').read_text(encoding='utf-8')
    assert config.count('LB_MODE ') == 1
    assert 'LB_MODE {}'.format(LB_MODE[lb]) in config
    log = (raw / 'config.log').read_text(encoding='utf-8', errors='replace')
    observed_tags = Counter()
    for line in log.splitlines():
        if not line.startswith('WS06_INPUT_TAG '):
            continue
        fields = dict(part.split('=', 1) for part in line.split()[1:])
        observed_tags[int(fields['tag'])] += int(fields['flows'])
    assert observed_tags == tags
    if lb == 'conweave':
        voq = list(raw.glob('*_out_voq.txt'))
        assert len(voq) == 1
        for line in voq[0].read_text(encoding='ascii').splitlines():
            if line.strip():
                assert all(item.strip().isdigit() for item in line.split(','))
    return {'experiment_id': experiment_id, 'source_sha': source_sha,
            'flow_kind': flow_kind, 'lb': lb, 'flows': len(fct_rows),
            'tags': dict(tags), 'fct_sha256': sha(fct_files[0]),
            'flow_sha256': sha(trace), 'topology_sha256': sha(topo)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('experiment_id')
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--flow-kind', required=True, choices=FLOW_SHA)
    parser.add_argument('--lb', required=True, choices=LB_MODE)
    args = parser.parse_args()
    print(json.dumps(verify(args.experiment_id, args.source_sha, args.flow_kind,
                            args.lb), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
