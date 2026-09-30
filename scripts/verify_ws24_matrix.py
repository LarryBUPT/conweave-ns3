#!/usr/bin/env python3
"""Verify all 14 WS-24 cells and paired synthetic rail/placement arms."""

import argparse
import json
from pathlib import Path

from verify_ws24_legacy import ROOT, verify as verify_legacy
from verify_ws24_result import verify as verify_multinic


DEFAULT_IDS = {
    'legacy5-fecmp': '20261002-100000-ws24-legacy5-fecmp',
    'legacy5-conga': '20261002-100100-ws24-legacy5-conga',
    'legacy5-letflow': '20261002-100200-ws24-legacy5-letflow',
    'legacy5-conweave': '20261002-100300-ws24-legacy5-conweave',
    'legacy6-fecmp': '20261002-101000-ws24-legacy6-fecmp',
    'legacy6-conga': '20261002-101100-ws24-legacy6-conga',
    'legacy6-letflow': '20261002-101200-ws24-legacy6-letflow',
    'legacy6-conweave': '20261002-101300-ws24-legacy6-conweave',
    'target': '20261002-110000-ws24-target-320host-correctness',
    'cnp': '20261002-120000-ws24-cnp-incast-correctness',
    'fixed_single': '20261002-130000-ws24-fixed-single',
    'fixed_multi': '20261002-130100-ws24-fixed-multi',
    'variable_single': '20261002-130200-ws24-variable-single',
    'variable_multi': '20261002-130300-ws24-variable-multi',
}


def arm_rows(experiment_id):
    base = ROOT / 'results' / experiment_id
    meta = json.loads((base / 'metadata.json').read_text(encoding='utf-8'))
    raw = base / 'raw' / str(meta['raw_directory'])
    receipts = list(raw.glob('*_out_ws24.txt'))
    assert len(receipts) == 1
    rows = {}
    for line in receipts[0].read_text(encoding='ascii').splitlines()[1:]:
        fields = tuple(map(int, line.split()))
        assert len(fields) == 20 and fields[0] not in rows
        rows[fields[0]] = fields
    return rows


def verify_matrix(ids, source_sha, reference_fct):
    assert set(ids) == set(DEFAULT_IDS) and len(set(ids.values())) == 14
    assert set(reference_fct) == {'fecmp', 'conga', 'letflow', 'conweave'}
    for experiment_id in ids.values():
        logs = ROOT / 'results' / experiment_id / 'logs'
        summary = json.loads((logs / 'resource-summary.json').read_text(encoding='utf-8'))
        assert summary['id'] == experiment_id and summary['final_status'] == 'SUCCEEDED'
        assert summary['samples'] > 0 and (logs / 'resource-samples.jsonl').stat().st_size > 0
    cells = {}
    for kind in ('legacy5', 'legacy6'):
        for lb in ('fecmp', 'conga', 'letflow', 'conweave'):
            key = kind + '-' + lb
            cells[key] = verify_legacy(ids[key], source_sha, kind, lb)
            if kind == 'legacy5':
                assert cells[key]['fct_sha256'] == reference_fct[lb]
    cells['target'] = verify_multinic(ids['target'], source_sha, 'target')
    cells['cnp'] = verify_multinic(ids['cnp'], source_sha, 'cnp')
    arms = {}
    for placement in ('fixed', 'variable'):
        for rail_policy in ('single', 'multi'):
            key = placement + '_' + rail_policy
            cells[key] = verify_multinic(ids[key], source_sha, 'arm', key)
            arms[key] = arm_rows(ids[key])
    logical = None
    metrics = {}
    for key, rows in arms.items():
        assert len(rows) == 10
        demand = {fid: (r[1], r[2], r[3], r[11], r[12], r[13]) for fid, r in rows.items()}
        if logical is None:
            logical = demand
        assert demand == logical
        placement, rail_policy = key.split('_')
        assert {r[6] for r in rows.values()} == ({0} if rail_policy == 'single' else {0, 1, 2, 3})
        wait_ns = {fid: r[14] - r[13] for fid, r in rows.items()}
        latency_ns = {fid: r[15] - r[13] for fid, r in rows.items()}
        assert all(v >= 0 for v in wait_ns.values())
        metrics[key] = {'flow_latency_ns': latency_ns, 'admission_wait_ns': wait_ns,
                        'span_ns': max(r[15] for r in rows.values()) -
                                   min(r[13] for r in rows.values())}
        if rail_policy == 'multi':
            for fid, row in rows.items():
                assert row[6] == fid % 4
        if placement == 'fixed':
            assert all(rows[fid][4:6] == arms['fixed_single'][fid][4:6] for fid in rows)
        else:
            assert all(rows[fid][4:6] == arms['variable_single'][fid][4:6] for fid in rows)
    for policy in ('single', 'multi'):
        for fid in logical:
            fixed = arms['fixed_' + policy][fid]
            variable = arms['variable_' + policy][fid]
            assert (fixed[4], fixed[5]) != (variable[4], variable[5]) or \
                   (fixed[2], fixed[3]) not in ((1, 2), (2, 1))
    paired = {}
    for placement in ('fixed', 'variable'):
        single, multi = metrics[placement + '_single'], metrics[placement + '_multi']
        paired[placement] = {'multi_minus_single_span_ns': multi['span_ns'] - single['span_ns'],
                             'multi_minus_single_flow_latency_ns': {
                                 str(fid): multi['flow_latency_ns'][fid] - single['flow_latency_ns'][fid]
                                 for fid in logical}}
    return {'source_sha': source_sha, 'cells_verified': len(cells), 'cells': cells,
            'arms': metrics, 'paired_descriptive': paired,
            'evidence_level': 'single synthetic seed; descriptive only'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--reference-fct-sha-json', type=Path, required=True,
                        help='Four complete WS-06 legacy5 raw FCT SHA-256 digests by LB name')
    parser.add_argument('--id-map', type=Path, help='JSON mapping of 14 cell keys to replacement IDs')
    args = parser.parse_args()
    ids = json.loads(args.id_map.read_text(encoding='utf-8')) if args.id_map else DEFAULT_IDS
    reference = json.loads(args.reference_fct_sha_json.read_text(encoding='utf-8'))
    print(json.dumps(verify_matrix(ids, args.source_sha, reference), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
