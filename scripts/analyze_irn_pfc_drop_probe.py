#!/usr/bin/env python3
"""Verify the opt-in drop trace against the original IRN+PFC pressure cell."""
import argparse
import collections
import hashlib
import json
import os
import re

from analyze_result import PROJECT


def read_cell(experiment_id):
    base = os.path.join(PROJECT, 'results', experiment_id)
    with open(os.path.join(base, 'metadata.json'), encoding='utf-8') as source:
        meta = json.load(source)
    raw_id = meta['raw_directory']
    raw = os.path.join(base, 'raw', raw_id)
    fct = os.path.join(raw, raw_id + '_out_fct.txt')
    with open(fct, 'rb') as source:
        data = source.read()
    with open(os.path.join(raw, 'config.log'), encoding='utf-8', errors='replace') as source:
        log = source.read()
    return meta, data, log


def fields(line):
    return dict(re.findall(r'(\w+)=([^\s]+)', line))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original_id')
    parser.add_argument('probe_id')
    parser.add_argument('--output')
    args = parser.parse_args()
    original, original_fct, original_log = read_cell(args.original_id)
    probe, probe_fct, probe_log = read_cell(args.probe_id)
    if original['input_flow_sha256'] != probe['input_flow_sha256']:
        raise ValueError('Input trace differs')
    for key in ('irn', 'pfc', 'lb', 'buffer', 'topo', 'bw', 'netload', 'simul_time', 'flow_file'):
        if original['parameters'][key] != probe['parameters'][key]:
            raise ValueError('Non-probe parameter differs: ' + key)
    if original_fct != probe_fct:
        raise ValueError('FCT output changed with logging probe')
    completed_sources = {int(line.split()[0]) for line in probe_fct.decode('utf-8').splitlines()}
    missing_sources = sorted(set(range(16)) - completed_sources)
    drops = [fields(line) for line in probe_log.splitlines()
             if line.startswith('FACTORIAL_ADMISSION_DROP ')]
    rejects = [fields(line) for line in probe_log.splitlines()
               if line.startswith('FACTORIAL_QUEUE_REJECT ')]
    suppressed = [fields(line) for line in probe_log.splitlines()
                  if line.startswith('FACTORIAL_IRN_PFC_TIMEOUT_SUPPRESSED ')]
    if sorted(int(item['flow_id']) for item in suppressed) != missing_sources:
        raise ValueError('Suppressed timeouts do not match unfinished sources')
    by_source = collections.Counter(int(item['src']) for item in drops)
    matched = {}
    for timeout in suppressed:
        flow_id = int(timeout['flow_id'])
        relevant = [item for item in drops
                    if int(item['src']) == flow_id and
                    int(item['seq']) == int(timeout['snd_una']) and
                    int(item['time_ns']) < int(timeout['time_ns'])]
        if not relevant:
            raise ValueError('No preceding drop at outstanding sequence for flow %d' % flow_id)
        matched[str(flow_id)] = {
            'snd_una': int(timeout['snd_una']),
            'snd_nxt': int(timeout['snd_nxt']),
            'timeout_ns': int(timeout['time_ns']),
            'matching_drop_events': len(relevant),
            'first_matching_drop_ns': min(int(item['time_ns']) for item in relevant),
            'drop_switches': sorted({int(item['switch']) for item in relevant}),
            'all_data_admission_drops_for_flow': by_source[flow_id],
        }
    result = {
        'original_id': args.original_id,
        'probe_id': args.probe_id,
        'original_sha': original['git_commit'],
        'probe_sha': probe['git_commit'],
        'trace_sha256': probe['input_flow_sha256'],
        'fct_sha256': hashlib.sha256(probe_fct).hexdigest(),
        'fct_byte_identical': True,
        'input_flows': 16,
        'completed_flows': len(completed_sources),
        'missing_sources': missing_sources,
        'admission_drop_events': len(drops),
        'admission_drop_reasons': dict(collections.Counter(item['reason'] for item in drops)),
        'admission_drops_by_source': {str(key): count for key, count in sorted(by_source.items())},
        'queue_reject_events': len(rejects),
        'suppressed_timeout_events': len(suppressed),
        'matched_missing_flows': matched,
        'original_suppressed_timeout_events': original_log.count('FACTORIAL_IRN_PFC_TIMEOUT_SUPPRESSED '),
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.output:
        with open(args.output, 'x', encoding='utf-8') as target:
            target.write(rendered)
    print(rendered)


if __name__ == '__main__':
    main()
