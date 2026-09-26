#!/usr/bin/env python3
"""Verify full-MoE completion and preselected destination hotspots."""
import collections
import json
import os
import sys

from analyze_moe_tags import summarize
from analyze_result import PROJECT, percentile


def full_summary(experiment_id):
    common = summarize(experiment_id)
    base = os.path.join(PROJECT, 'results', experiment_id)
    with open(os.path.join(base, 'metadata.json'), encoding='utf-8') as source:
        meta = json.load(source)
    trace = os.path.join(base, 'config', 'traffic_trace.txt')
    fct = os.path.join(base, 'raw', str(meta['raw_directory']),
                       str(meta['raw_directory']) + '_out_fct.txt')
    expected = collections.Counter()
    with open(trace, encoding='utf-8') as source:
        source.readline()
        for line in source:
            fields = line.split()
            if fields[5] == '2':
                expected[int(fields[1])] += 1
    hot = [dst for dst, _ in sorted(expected.items(), key=lambda item: (-item[1], item[0]))[:8]]
    completed = collections.defaultdict(list)
    end_times = collections.defaultdict(list)
    with open(fct, encoding='utf-8') as source:
        for line in source:
            fields = line.split()
            dst, size = int(fields[1]), int(fields[4])
            if size == 8192 and dst in hot:
                completed[dst].append(int(fields[6]) / 1000.0)
                end_times[dst].append((int(fields[5]) + int(fields[6]) - 2000000000) / 1000.0)
    hotspots = []
    for dst in hot:
        times = sorted(completed[dst])
        hotspots.append({'destination': dst, 'input_flows': expected[dst],
                         'completed_flows': len(times),
                         'p99_fct_us': percentile(times, 99) if times else None,
                         'last_completion_us': max(end_times[dst]) if times and
                         len(times) == expected[dst] else None})
    return {'experiment_id': experiment_id, 'git_commit': common['git_commit'],
            'trace_sha256': common['trace_sha256'], 'fct_sha256': common['fct_sha256'],
            'tags': common['tags'], 'hotspot_destinations': hotspots,
            'hotspot_selection': 'top 8 MoE destinations by input count, ties by ID'}


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: analyze_ws11_full.py <experiment-id>')
    result = full_summary(sys.argv[1])
    target = os.path.join(PROJECT, 'results', sys.argv[1], 'processed', 'ws11_full_summary.json')
    if os.path.exists(target):
        with open(target, encoding='utf-8') as source:
            assert json.load(source) == result, 'Existing WS-11 summary differs'
    else:
        with open(target, 'x', encoding='utf-8') as output:
            json.dump(result, output, indent=2, sort_keys=True)
            output.write('\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
