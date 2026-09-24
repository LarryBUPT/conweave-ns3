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


def group_stats(keys, completed_by_key, trace_start_ns):
    completed = [completed_by_key[key] for key in keys if key in completed_by_key]
    times = sorted(item[0] / 1000 for item in completed)
    input_count = len(keys)
    completed_count = len(completed)
    batch_ns = max((item[1] for item in completed), default=None) if completed_count == input_count else None
    source_counts = collections.Counter(key[0] for key in keys)
    finished_source_counts = collections.Counter(key[0] for key in keys if key in completed_by_key)
    source_end = {}
    for key in keys:
        if key in completed_by_key:
            source_end[key[0]] = max(source_end.get(key[0], 0), completed_by_key[key][1])
    source_batch = sorted((source_end[src] - trace_start_ns) / 1000
                          for src, count in source_counts.items()
                          if finished_source_counts[src] == count)
    return {
        'input_flows': input_count, 'completed_flows': completed_count,
        'unfinished_flows': input_count - completed_count,
        'completion_rate': completed_count / input_count,
        'mean_fct_us': statistics.mean(times) if times else None,
        'p50_fct_us': percentile(times, 50) if times else None,
        'p95_fct_us': percentile(times, 95) if times else None,
        'p99_fct_us': percentile(times, 99) if times else None,
        'synthetic_batch_completion_us': (batch_ns - trace_start_ns) / 1000
                                         if batch_ns is not None else None,
        'complete_sources': len(source_batch), 'input_sources': len(source_counts),
        'p99_complete_source_batch_us': percentile(source_batch, 99) if source_batch else None,
    }


def summarize(experiment_id, target_trace=None):
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
    tags = collections.Counter()
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
            tags[tag] += 1
    if len(pending) != declared:
        raise ValueError('Trace count differs from declared count')

    completed_by_key = {}
    with open(fct, encoding='utf-8') as source:
        for number, line in enumerate(source, 1):
            fields = line.split()
            if len(fields) != 8:
                raise ValueError('Invalid FCT line %d' % number)
            key = tuple(map(int, fields[:5]))
            if key not in pending or key in completed_by_key:
                raise ValueError('Unmatched or duplicate completed flow at FCT line %d' % number)
            tag, expected_start = pending[key]
            started, fct_ns, ideal = map(int, fields[5:8])
            if abs(started - expected_start) > 2 or fct_ns < 0 or ideal <= 0:
                raise ValueError('Invalid timing at FCT line %d' % number)
            end_ns = started + fct_ns
            completed_by_key[key] = (fct_ns, end_ns, ideal)

    trace_start_ns = min(start for _, start in pending.values())
    output = {'experiment_id': experiment_id, 'git_commit': metadata['git_commit'],
              'algorithm': metadata['algorithm'], 'trace_sha256': trace_hash,
              'fct_sha256': sha256(fct), 'trace_start_ns': trace_start_ns,
              'tags': {}}
    for tag in sorted(tags):
        keys = [key for key, value in pending.items() if value[0] == tag]
        output['tags'][str(tag)] = group_stats(keys, completed_by_key, trace_start_ns)
    if target_trace:
        with open(target_trace, encoding='utf-8') as source:
            declared_target = int(source.readline().strip())
            signatures = set()
            for line in source:
                fields = line.split()
                if len(fields) != 6 or int(fields[5]) != 2:
                    raise ValueError('Target file must contain six-column tag=2 rows')
                signatures.add((int(fields[0]), int(fields[1]), int(fields[3]),
                                round(float(fields[4]) * 1e9)))
        if len(signatures) != declared_target:
            raise ValueError('Target file has duplicate rows or incorrect count')
        keys = [key for key, value in pending.items()
                if (key[0], key[1], key[4], value[1]) in signatures]
        if len(keys) != declared_target or any(pending[key][0] != 2 for key in keys):
            raise ValueError('Target MoE rows do not match this experiment input uniquely')
        output['target_moe'] = group_stats(keys, completed_by_key, trace_start_ns)
        output['target_trace_sha256'] = sha256(target_trace)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment_id')
    parser.add_argument('--target-trace', help='versioned six-column target MoE subset')
    args = parser.parse_args()
    summary = summarize(args.experiment_id, args.target_trace)
    name = 'moe_target_summary.json' if args.target_trace else 'moe_tag_summary.json'
    destination = os.path.join(PROJECT, 'results', args.experiment_id, 'processed', name)
    with open(destination, 'x', encoding='utf-8') as target:
        json.dump(summary, target, indent=2, sort_keys=True)
        target.write('\n')
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
