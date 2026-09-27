#!/usr/bin/env python3
"""Verify and summarize one four-cell IRN/PFC technical pilot."""
import argparse
import hashlib
import json
import os
import re

from analyze_moe_tags import summarize
from analyze_result import PROJECT


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def cell_result(experiment_id):
    root = os.path.join(PROJECT, 'results', experiment_id)
    with open(os.path.join(root, 'metadata.json'), encoding='utf-8') as source:
        metadata = json.load(source)
    params = metadata['parameters']
    cell = '%d%d' % (params['irn'], params['pfc'])
    tagged = summarize(experiment_id)
    raw_id = metadata['raw_directory']
    raw = os.path.join(root, 'raw', raw_id)
    prefix = os.path.join(raw, raw_id + '_out_')
    pfc_events = {0: 0, 1: 0}
    with open(prefix + 'pfc.txt', encoding='utf-8') as source:
        for line in source:
            fields = line.split()
            if len(fields) != 5 or int(fields[4]) not in pfc_events:
                raise ValueError('Unexpected PFC row in ' + experiment_id)
            pfc_events[int(fields[4])] += 1
    cnp_events = 0
    ecn_events = 0
    ooo_events = 0
    with open(prefix + 'cnp.txt', encoding='utf-8') as source:
        for line in source:
            fields = line.split()
            if len(fields) != 5:
                raise ValueError('Unexpected CNP row in ' + experiment_id)
            ecn_events += int(fields[2])
            ooo_events += int(fields[3])
            cnp_events += int(fields[4])
    # run.py redirects the ns-3 process output to raw/<id>/config.log.
    with open(os.path.join(raw, 'config.log'), encoding='utf-8', errors='replace') as source:
        log = source.read()
    with open(os.path.join(root, 'config', 'config.txt'), encoding='utf-8') as source:
        config = source.read()
    for key, value in [('ENABLE_IRN', params['irn']), ('ENABLE_PFC', params['pfc'])]:
        if not re.search(r'^%s %d$' % (key, value), config, re.MULTILINE):
            raise ValueError('Configuration differs from metadata: ' + key)
    return cell, {
        'experiment_id': experiment_id,
        'git_commit': metadata['git_commit'],
        'trace_sha256': tagged['trace_sha256'],
        'topology_sha256': file_hash(os.path.join(root, 'config', 'topology.txt')),
        'fct_sha256': tagged['fct_sha256'],
        'seed': metadata['seed'],
        'parameters': params,
        'tags': tagged['tags'],
        'pfc_pause_events': pfc_events[1],
        'pfc_resume_events': pfc_events[0],
        'cnp_events': cnp_events,
        'ecn_events': ecn_events,
        'ooo_events': ooo_events,
        'timeout_recovery_events': log.count('WS08_TX_TIMEOUT '),
        'irn_pfc_timeout_suppressed': log.count('FACTORIAL_IRN_PFC_TIMEOUT_SUPPRESSED '),
        'nack_log_events': log.count('WS08_TX_NACK '),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment_ids', nargs=4)
    parser.add_argument('--expected-tag1', type=int, required=True)
    parser.add_argument('--expected-tag2', type=int, required=True)
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--output', help='write immutable summary JSON here')
    args = parser.parse_args()
    cells = dict(cell_result(experiment_id) for experiment_id in args.experiment_ids)
    if set(cells) != {'00', '01', '10', '11'}:
        raise ValueError('Expected exactly the four distinct IRN/PFC combinations')
    for key in ('git_commit', 'trace_sha256', 'topology_sha256', 'seed'):
        if len({cells[cell][key] for cell in cells}) != 1:
            raise ValueError('Mismatched ' + key)
    common_params = [{key: value for key, value in cells[cell]['parameters'].items()
                      if key not in ('irn', 'pfc')} for cell in sorted(cells)]
    if any(params != common_params[0] for params in common_params[1:]):
        raise ValueError('Non-factor parameters differ')
    for cell in cells:
        if (cells[cell]['tags']['1']['input_flows'] != args.expected_tag1 or
                cells[cell]['tags']['2']['input_flows'] != args.expected_tag2):
            raise ValueError('Unexpected pilot flow counts')
    output = {'design': 'single-trace exploratory technical pilot; not independent replication',
              'scenario': args.scenario, 'factor_order': 'IRN,PFC', 'cells': cells,
              'all_flows_completed': all(cells[c]['tags'][tag]['unfinished_flows'] == 0
                                         for c in cells for tag in ('1', '2'))}
    rendered = json.dumps(output, indent=2, sort_keys=True) + '\n'
    if args.output:
        with open(args.output, 'x', encoding='utf-8') as target:
            target.write(rendered)
    print(rendered)


if __name__ == '__main__':
    main()
