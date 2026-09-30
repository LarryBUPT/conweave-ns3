#!/usr/bin/env python3
"""Verify a new IRN+PFC correctness run against the fixed WS-13 stress input.

This is a transport gate, not a performance comparison. It deliberately rejects
the historical 13/16 result even though its old worker marked it SUCCEEDED.
"""
import argparse
import json
import os
import re

from analyze_moe_tags import summarize
from analyze_result import PROJECT


REFERENCE = '20260927-215700-irnpfcstress-11'
COMPLETE = re.compile(
    r'^WS23_IRN_PFC_QP_COMPLETE flow_id=(\d+) size=(\d+) snd_una=(\d+) '
    r'snd_nxt=(\d+) tx_payload_bytes=(\d+) tx_packets=(\d+)$')
RECOVERY = re.compile(r'^WS23_IRN_PFC_TIMEOUT_RECOVERY .* local_paused=(\d+)$')
DEFERRED = re.compile(r'^WS23_IRN_PFC_TIMEOUT_DEFERRED .* paused=(\d+) delay_ns=(\d+)$')


def load_metadata(experiment_id):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', experiment_id):
        raise ValueError('Invalid experiment ID')
    path = os.path.join(PROJECT, 'results', experiment_id, 'metadata.json')
    with open(path, encoding='utf-8') as source:
        return json.load(source)


def verify(experiment_id):
    reference = load_metadata(REFERENCE)
    current = load_metadata(experiment_id)
    for field in ('input_flow_sha256', 'topology_sha256', 'seed', 'algorithm'):
        if current[field] != reference[field]:
            raise ValueError('Changed fixed input: ' + field)
    if current['parameters'] != reference['parameters']:
        raise ValueError('Changed fixed parameters')
    summary = summarize(experiment_id)
    if summary['trace_sha256'] != reference['input_flow_sha256']:
        raise ValueError('Trace snapshot differs from reference')
    for tag in ('1', '2'):
        if summary['tags'][tag]['input_flows'] != 8 or summary['tags'][tag]['completed_flows'] != 8:
            raise ValueError('Transport completion gate failed for tag ' + tag)
    if current['git_commit'] == reference['git_commit']:
        raise ValueError('New run must use a distinct fixed source SHA')

    raw_id = str(current['raw_directory'])
    if not re.fullmatch(r'\d+', raw_id):
        raise ValueError('Invalid raw directory')
    log_path = os.path.join(PROJECT, 'results', experiment_id, 'raw', raw_id, 'config.log')
    completions = {}
    recoveries = deferred = 0
    with open(log_path, encoding='utf-8', errors='replace') as source:
        for line in source:
            line = line.rstrip('\r\n')
            match = COMPLETE.fullmatch(line)
            if match:
                flow_id, size, una, nxt, tx_bytes, packets = map(int, match.groups())
                if flow_id in completions or not (0 <= flow_id < 16):
                    raise ValueError('Duplicate or unexpected QP completion')
                if size != 1048576 or una != size or nxt != size or tx_bytes < size or packets == 0:
                    raise ValueError('QP byte/sequence conservation failed for flow ' + str(flow_id))
                completions[flow_id] = {'payload_bytes': tx_bytes, 'packets': packets}
            match = RECOVERY.fullmatch(line)
            if match:
                if int(match.group(1)) != 0:
                    raise ValueError('Timeout recovery occurred during local PFC pause')
                recoveries += 1
            match = DEFERRED.fullmatch(line)
            if match:
                if int(match.group(2)) <= 0:
                    raise ValueError('Timeout deferral did not schedule a future timer')
                deferred += 1
    if set(completions) != set(range(16)):
        raise ValueError('Missing per-QP completion/byte receipts')
    if not recoveries:
        raise ValueError('Stress input did not exercise timeout recovery')
    return {'experiment_id': experiment_id, 'git_commit': current['git_commit'],
            'trace_sha256': summary['trace_sha256'], 'fct_sha256': summary['fct_sha256'],
            'completed_flows': 16, 'qp_byte_receipts': len(completions),
            'timeout_recoveries': recoveries, 'timeout_deferrals': deferred,
            'total_tx_payload_bytes': sum(item['payload_bytes'] for item in completions.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment_id')
    args = parser.parse_args()
    print(json.dumps(verify(args.experiment_id), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
