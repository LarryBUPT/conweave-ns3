#!/usr/bin/env python3
"""Summarize a 2.000s synchronized trace by its explicit workload tag.

The input snapshot, rather than completed FCT rows, defines the denominator.
The old 2.005s baseline analyzer and its outputs are intentionally independent.
"""
import argparse
import collections
import hashlib
import json
import os
import re
import statistics

from analyze_result import PROJECT, ID_RE, percentile


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def summarize(experiment_id):
    if not ID_RE.fullmatch(experiment_id):
        raise ValueError('Invalid experiment ID')
    base = os.path.realpath(os.path.join(PROJECT, 'results', experiment_id))
    if not base.startswith(os.path.realpath(os.path.join(PROJECT, 'results')) + os.sep):
        raise ValueError('Result path escapes project')
    with open(os.path.join(base, 'metadata.json'), encoding='utf-8') as source:
        metadata = json.load(source)
    if metadata.get('status') != 'SUCCEEDED':
        raise ValueError('Simulation did not succeed')
    raw_id = str(metadata.get('raw_directory', ''))
    if not re.fullmatch(r'[0-9]+', raw_id):
        raise ValueError('Invalid raw directory')
    trace = os.path.join(base, 'config', 'traffic_trace.txt')
    fct = os.path.join(base, 'raw', raw_id, raw_id + '_out_fct.txt')
    if os.path.islink(trace) or os.path.islink(fct):
        raise ValueError('Input and FCT must be regular files')
    trace_hash = sha256(trace)
    if trace_hash.lower() != metadata.get('input_flow_sha256', '').lower():
        raise ValueError('Trace snapshot hash differs from metadata')

    # scratch/network-load-balance.cc initializes source/destination ports to
    # 10000/100 and increments each independently in trace order.
    source_ports = collections.defaultdict(lambda: 10000)
    destination_ports = collections.defaultdict(lambda: 100)
    pending = {}
    tags = collections.defaultdict(lambda: {'input': 0, 'finished': [], 'source_end': {}})
    with open(trace, encoding='utf-8') as source:
        declared = int(source.readline().strip())
        for number, line in enumerate(source, 2):
            fields = line.split()
            if len(fields) not in (5, 6):
                raise ValueError('Invalid trace line %d' % number)
            src, dst, pg, size = map(int, fields[:4])
            start_ns = round(float(fields[4]) * 1e9)
            tag = int(fields[5]) if len(fields) == 6 else 0
            sport, dport = source_ports[src], destination_ports[dst]
            source_ports[src] += 1
            destination_ports[dst] += 1
            key = (src, dst, sport, dport, size)
            if key in pending:
                raise ValueError('Ambiguous trace flow identity at line %d' % number)
            pending[key] = (tag, start_ns)
            tags[tag]['input'] += 1
    if sum(group['input'] for group in tags.values()) != declared:
        raise ValueError('Trace count differs from declared count')

    seen = set()
    with open(fct, encoding='utf-8') as source:
        for number, line in enumerate(source, 1):
            fields = line.split()
            if len(fields) != 8:
                raise ValueError('Invalid FCT line %d' % number)
            key = tuple(map(int, fields[:5]))
            if key not in pending or key in seen:
                raise ValueError('Unmatched or duplicate completed flow at FCT line %d' % number)
            seen.add(key)
            tag, expected_start = pending[key]
            started, fct_ns, ideal = map(int, fields[5:8])
            if abs(started - expected_start) > 2 or fct_ns < 0 or ideal <= 0:
                raise ValueError('Invalid timing at FCT line %d' % number)
            end_ns = started + fct_ns
            tags[tag]['finished'].append((fct_ns, end_ns, ideal))
            src = key[0]
            tags[tag]['source_end'][src] = max(end_ns,
                                               tags[tag]['source_end'].get(src, 0))

    output = {'experiment_id': experiment_id, 'git_commit': metadata['git_commit'],
              'algorithm': metadata['algorithm'], 'trace_sha256': trace_hash,
              'fct_sha256': sha256(fct), 'trace_start_ns': min(start for _, start in pending.values()),
              'tags': {}}
    for tag, group in sorted(tags.items()):
        completed = group['finished']
        times = sorted(item[0] / 1000 for item in completed)
        input_count = group['input']
        completed_count = len(completed)
        # A maximum completion time is defined only when all input flows finish.
        batch_ns = max((item[1] for item in completed), default=None) if completed_count == input_count else None
        source_counts = collections.Counter(key[0] for key, value in pending.items() if value[0] == tag)
        finished_source_counts = collections.Counter(key[0] for key in seen if pending[key][0] == tag)
        source_batch = sorted((group['source_end'][src] - output['trace_start_ns']) / 1000
                              for src, count in source_counts.items()
                              if finished_source_counts[src] == count)
        output['tags'][str(tag)] = {
            'input_flows': input_count, 'completed_flows': completed_count,
            'unfinished_flows': input_count - completed_count,
            'completion_rate': completed_count / input_count,
            'mean_fct_us': statistics.mean(times) if times else None,
            'p50_fct_us': percentile(times, 50) if times else None,
            'p95_fct_us': percentile(times, 95) if times else None,
            'p99_fct_us': percentile(times, 99) if times else None,
            'synthetic_batch_completion_us': (batch_ns - output['trace_start_ns']) / 1000
                                             if batch_ns is not None else None,
            'complete_sources': len(source_batch), 'input_sources': len(source_counts),
            'p99_complete_source_batch_us': percentile(source_batch, 99) if source_batch else None,
        }
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment_id')
    args = parser.parse_args()
    summary = summarize(args.experiment_id)
    destination = os.path.join(PROJECT, 'results', args.experiment_id,
                               'processed', 'moe_tag_summary.json')
    with open(destination, 'x', encoding='utf-8') as target:
        json.dump(summary, target, indent=2, sort_keys=True)
        target.write('\n')
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
