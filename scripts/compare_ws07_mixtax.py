#!/usr/bin/env python3
"""Pair a single-seed packet/flow x 0/64-background WS-07 pilot."""
import argparse
import json
import os

from analyze_moe_tags import PROJECT, summarize


def tag_rows(experiment_id, tag):
    path = os.path.join(PROJECT, 'results', experiment_id, 'config', 'traffic_trace.txt')
    with open(path, encoding='utf-8') as source:
        source.readline()
        return [line.strip() for line in source if line.split()[-1] == str(tag)]


def common_config(experiment_id):
    path = os.path.join(PROJECT, 'results', experiment_id, 'config', 'config.txt')
    with open(path, encoding='utf-8') as source:
        lines = [line.split(None, 1) for line in source if line.strip()]
    values = {item[0]: item[1].strip() for item in lines if len(item) == 2}
    keys = ('CC_MODE', 'ENABLE_PFC', 'ENABLE_IRN', 'RANDOM_SEED', 'BUFFER_SIZE',
            'PACKET_PAYLOAD_SIZE', 'HAS_WIN', 'VAR_WIN', 'RATE_BOUND',
            'KMIN_MAP', 'KMAX_MAP', 'PMAX_MAP')
    return tuple((key, values[key]) for key in keys)


def compare(ids):
    reports = {name: summarize(experiment_id) for name, experiment_id in ids.items()}
    metadata = {}
    for name, experiment_id in ids.items():
        path = os.path.join(PROJECT, 'results', experiment_id, 'metadata.json')
        with open(path, encoding='utf-8') as source:
            metadata[name] = json.load(source)
    shared = [('topology_sha256', meta['topology_sha256'],
               meta['seed'], meta['parameters']['pfc'], meta['parameters']['irn'],
               meta['parameters']['bw'], meta['parameters']['simul_time'])
              for meta in metadata.values()]
    if len({item[1:] for item in shared}) != 1:
        raise ValueError('Common topology, seed, PFC, IRN, bandwidth or time differ')
    if len({common_config(experiment_id) for experiment_id in ids.values()}) != 1:
        raise ValueError('Congestion control or shared transport config differs')
    for name in ('flow0', 'packet0', 'flow64', 'packet64'):
        report = reports[name]
        if '2' not in report['tags'] or report['tags']['2']['unfinished_flows']:
            raise ValueError(name + ' has missing MoE completions')
    if reports['flow0']['algorithm'] != 'fecmp' or reports['flow64']['algorithm'] != 'fecmp' or \
            reports['packet0']['algorithm'] != 'dualtrack' or \
            reports['packet64']['algorithm'] != 'dualtrack':
        raise ValueError('Unexpected algorithm assignment')
    if len({report['git_commit'] for report in reports.values()}) != 1:
        raise ValueError('Experiments must share one source commit')
    for left, right in (('flow0', 'packet0'), ('flow64', 'packet64')):
        if reports[left]['trace_sha256'] != reports[right]['trace_sha256']:
            raise ValueError('Paired algorithms used different trace bytes')
    if tag_rows(ids['flow0'], 2) != tag_rows(ids['flow64'], 2):
        raise ValueError('MoE sub trace changed between background levels')
    if tag_rows(ids['flow0'], 1) or len(tag_rows(ids['flow64'], 1)) != 64:
        raise ValueError('Expected 0/64 background input')
    for name in ('flow64', 'packet64'):
        if reports[name]['tags']['1']['unfinished_flows']:
            raise ValueError(name + ' has missing background completions')
    cct = {name: report['tags']['2']['synthetic_batch_completion_us']
           for name, report in reports.items()}
    bg_p99 = {name: reports[name]['tags']['1']['p99_fct_us']
              for name in ('flow64', 'packet64')}
    return {'kind': 'single-seed technical pilot, not formal inference',
            'experiment_ids': ids, 'git_commit': reports['flow0']['git_commit'],
            'moe_batch_us': cct,
            'moe_background_interaction_us': (cct['packet64'] - cct['packet0']) -
                                             (cct['flow64'] - cct['flow0']),
            'moe_interaction_pct_of_packet0': 100 * ((cct['packet64'] - cct['packet0']) -
                                                     (cct['flow64'] - cct['flow0'])) / cct['packet0'],
            'background_p99_fct_us': bg_p99,
            'background_packet_minus_flow_p99_us': bg_p99['packet64'] - bg_p99['flow64'],
            'trace_sha256': {'bg0': reports['flow0']['trace_sha256'],
                             'bg64': reports['flow64']['trace_sha256']}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('flow0', 'packet0', 'flow64', 'packet64'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--output', help='write a new JSON file, refusing overwrite')
    args = parser.parse_args()
    ids = {name: getattr(args, name) for name in ('flow0', 'packet0', 'flow64', 'packet64')}
    result = compare(ids)
    if args.output:
        with open(args.output, 'x', encoding='utf-8') as output:
            json.dump(result, output, indent=2, sort_keys=True)
            output.write('\n')
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
