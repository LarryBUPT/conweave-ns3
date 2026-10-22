#!/usr/bin/env python3
"""Bound cold-start opportunity using old input/completion times, not invented sends."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT /
                        'docs/research/evidence/ws29-cold-start-opportunity.json')
    args = parser.parse_args()
    plan = json.loads((ROOT / 'docs/research/evidence/ws27-confirm-plan.json').read_text())
    rows = []
    for cell in plan['cells']:
        if cell['mode'] != 'classreserve' or cell['background'] != 192:
            continue
        folder = args.results / cell['id']
        meta = json.loads((folder / 'metadata.json').read_text())
        trace = folder / 'config/traffic_trace.txt'
        if digest(trace) != cell['trace_sha256'] or meta['status'] != 'SUCCEEDED':
            raise ValueError(cell['id'])
        inputs = [line.split() for line in trace.read_text().splitlines()[1:]]
        starts = Counter(round(float(line[4]) * 1e9) for line in inputs)
        earliest = min(starts)
        # Any real STATE needs >=10 us aggregation after its first arriving data.
        # Ignoring all propagation/serialization is an optimistic eligibility bound.
        earliest_possible_report = earliest + 10000
        raw = str(meta['raw_directory'])
        fct = folder / 'raw' / raw / (raw + '_out_fct.txt')
        completed_before_state = 0
        for line in fct.read_text().splitlines():
            fields = list(map(int, line.split()))
            if fields[5] + fields[6] <= earliest_possible_report:
                completed_before_state += 1
        rows.append({'id': cell['id'], 'seed': cell['seed'],
                     'trace_sha256': digest(trace), 'fct_sha256': digest(fct),
                     'input_flows': len(inputs), 'distinct_demand_times': len(starts),
                     'earliest_demand_ns': earliest, 'latest_demand_ns': max(starts),
                     'earliest_possible_state_ns_optimistic': earliest_possible_report,
                     'completed_before_any_state_possible': completed_before_state,
                     'potentially_eligible_upper_bound': len(inputs) - completed_before_state,
                     'actual_first_decision_eligibility': None})
    out = {'state_interval_ns': 10000, 'cells': rows,
           'evidence_level': 'old ClassReserve raw time bounds; not new feedback simulation',
           'limits': ['Old raw has no per-QP first source-ToR decision timestamps.',
                      'Completion precedes bound implies decision precedes bound; converse does not hold.',
                      'Upper bound ignores HB, two distinct candidates, sample freshness and CE differences.',
                      'Exact two-fresh-state count requires new nonperturbing decision instrumentation.',
                      'No oracle cache, extra warmup or changed demand times are allowed.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'cells': len(rows), 'all_demand_times_equal':
                      all(r['distinct_demand_times'] == 1 for r in rows),
                      'excluded_range': [min(r['completed_before_any_state_possible'] for r in rows),
                                         max(r['completed_before_any_state_possible'] for r in rows)]}))


if __name__ == '__main__':
    main()
