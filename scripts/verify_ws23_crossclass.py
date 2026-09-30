#!/usr/bin/env python3
"""Verify the fixed WS-23 shared-egress causal preflight, not mechanism efficacy."""
import argparse
import hashlib
import json
import os
import re

from analyze_moe_tags import summarize
from analyze_result import PROJECT


TOPOLOGY_SHA256 = 'dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad'
BACKGROUND_SHA256 = '8b11ba4bbc5fac248b1983e4070e818cb3ad3658ebaae6d9eb878b3999b76b83'
MIXED_SHA256 = '379e0c87cb0c26690d438287468dbc9159054f82445e6be46d0324165d639863'
BACKGROUND_ROW = '0 24 3 8388608 2.006000000 1'
HOP = re.compile(
    r'^WS23_CROSSCLASS_HOP tag=(\d+) src=(\d+) dst=(\d+) sport=(\d+) dport=(\d+) '
    r'switch=(\d+) port=(\d+) packets=(\d+) bytes=(\d+) wait_ns_sum=(\d+) '
    r'wait_ns_max=(\d+) device_queue_bytes_max=(\d+) mmu_egress_bytes_max=(\d+) '
    r'first_enqueue_ns=(\d+) last_dequeue_ns=(\d+)$')
FIELDS = ('tag', 'src', 'dst', 'sport', 'dport', 'switch', 'port', 'packets', 'bytes',
          'wait_ns_sum', 'wait_ns_max', 'device_queue_bytes_max',
          'mmu_egress_bytes_max', 'first_enqueue_ns', 'last_dequeue_ns')
ID = re.compile(r'^[0-9]{8}-[0-9]{6}-[a-z0-9][a-z0-9-]{0,40}$')


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def load_cell(experiment_id, source_sha, trace_sha, flow_file, diagnostic, flows):
    if not ID.fullmatch(experiment_id):
        raise ValueError('Invalid experiment ID')
    base = os.path.join(PROJECT, 'results', experiment_id)
    with open(os.path.join(base, 'metadata.json'), encoding='utf-8') as source:
        metadata = json.load(source)
    if metadata.get('status') != 'SUCCEEDED' or metadata.get('git_commit') != source_sha:
        raise ValueError('Cell status or source SHA differs from frozen contract: ' + experiment_id)
    if metadata.get('seed') != 1 or metadata.get('algorithm') != 'fecmp':
        raise ValueError('Cell seed or algorithm differs from frozen contract: ' + experiment_id)
    if metadata.get('input_flows') != flows or metadata.get('completed_flows') != flows:
        raise ValueError('Cell flow completion gate failed: ' + experiment_id)
    if metadata.get('concurrency_cap') != 1:
        raise ValueError('Cell concurrency differs from frozen contract: ' + experiment_id)
    params = metadata.get('parameters', {})
    expected = {'lb': 'fecmp', 'pfc': 0, 'irn': 1, 'buffer': 9, 'bw': 100,
                'simul_time': '0.01', 'netload': 10, 'topo': 'fat_k4_100G_OS2',
                'cdf': 'AliStorage2019', 'flow_file': flow_file,
                'factorial_pilot': True, 'factorial_drop_diag': True,
                'ws13_diag': int(diagnostic)}
    for key, value in expected.items():
        if params.get(key) != value:
            raise ValueError('Cell parameter differs from frozen contract: ' + key)
    if metadata.get('input_flow_sha256') != trace_sha or metadata.get('topology_sha256') != TOPOLOGY_SHA256:
        raise ValueError('Cell input or topology hash differs from frozen contract')
    trace = os.path.join(base, 'config', 'traffic_trace.txt')
    topology = os.path.join(base, 'config', 'topology.txt')
    if sha256(trace) != trace_sha or sha256(topology) != TOPOLOGY_SHA256:
        raise ValueError('Cell snapshots differ from frozen contract')
    with open(trace, encoding='utf-8') as source:
        source.readline()
        first_row = source.readline().strip()
    if first_row != BACKGROUND_ROW:
        raise ValueError('Background flow key changed between paired traces')
    summary = summarize(experiment_id)
    if summary['trace_sha256'] != trace_sha:
        raise ValueError('Tag summary trace hash differs from frozen contract')
    if summary['tags']['1']['input_flows'] != 1 or summary['tags']['1']['completed_flows'] != 1:
        raise ValueError('Background flow did not complete exactly once')
    if flows == 4 and (summary['tags']['2']['input_flows'] != 3 or
                       summary['tags']['2']['completed_flows'] != 3):
        raise ValueError('Contender flows did not complete exactly once')
    raw_id = str(metadata.get('raw_directory', ''))
    if not re.fullmatch(r'\d+', raw_id):
        raise ValueError('Invalid raw directory')
    log_path = os.path.join(base, 'raw', raw_id, 'config.log')
    hops = []
    inflight = []
    background_drops = 0
    background_timeouts = 0
    other_rejects = 0
    with open(log_path, encoding='utf-8', errors='replace') as source:
        for line in source:
            line = line.rstrip('\r\n')
            if line.startswith('WS23_CROSSCLASS_HOP '):
                match = HOP.fullmatch(line)
                if not match:
                    raise ValueError('Malformed cross-class hop receipt')
                hop = dict(zip(FIELDS, map(int, match.groups())))
                if hop['packets'] <= 0 or hop['bytes'] <= 0 or hop['last_dequeue_ns'] < hop['first_enqueue_ns']:
                    raise ValueError('Invalid cross-class hop counters')
                hops.append(hop)
            elif line.startswith('WS23_CROSSCLASS_INFLIGHT '):
                match = re.fullmatch(r'WS23_CROSSCLASS_INFLIGHT unpaired=(\d+)', line)
                if not match:
                    raise ValueError('Malformed cross-class inflight receipt')
                inflight.append(int(match.group(1)))
            background_drops += line.startswith('FACTORIAL_ADMISSION_DROP ') and ' src=0 ' in line
            background_timeouts += line.startswith('WS08_TX_TIMEOUT ') and ' flow_id=0 ' in line
            other_rejects += line.startswith(('FACTORIAL_QUEUE_REJECT ',
                                              'WARNING - Drop occurs in SendToDevContinue()'))
    if diagnostic and (inflight != [0] or not hops):
        raise ValueError('Diagnostic did not produce complete paired hop receipts')
    if not diagnostic and (hops or inflight):
        raise ValueError('Disabled diagnostic produced cross-class hop receipts')
    if background_drops or background_timeouts or other_rejects:
        raise ValueError('Background delay is confounded by a drop, queue reject or timeout')
    return {'id': experiment_id, 'summary': summary, 'hops': hops,
            'background_drops': background_drops, 'background_timeouts': background_timeouts,
            'other_rejects': other_rejects}


def verify_pair(source_sha, ids, scenario):
    if scenario == 'background':
        trace_sha, trace_file, flows = BACKGROUND_SHA256, 'ws23_crossclass_bg_1x8MiB.txt', 1
    elif scenario == 'mixed':
        trace_sha, trace_file, flows = MIXED_SHA256, 'ws23_crossclass_bg_plus_3x4MiB.txt', 4
    else:
        raise ValueError('Unknown pair scenario')
    off = load_cell(ids[0], source_sha, trace_sha, trace_file, False, flows)
    on = load_cell(ids[1], source_sha, trace_sha, trace_file, True, flows)
    if off['summary']['fct_sha256'] != on['summary']['fct_sha256']:
        raise ValueError('Diagnostic changed FCT bytes on an identical input')
    return {'scenario': scenario, 'ids': ids, 'source_sha': source_sha,
            'trace_sha256': trace_sha, 'fct_sha256': on['summary']['fct_sha256']}


def background_source_hop(cell):
    rows = [hop for hop in cell['hops'] if hop['tag'] == 1 and hop['src'] == 0 and
            hop['dst'] == 24 and hop['switch'] == 32]
    if len(rows) != 1:
        raise ValueError('Background path at source ToR 32 is not unique')
    return rows[0]


def verify(source_sha, ids):
    if not re.fullmatch(r'[0-9a-f]{40}', source_sha):
        raise ValueError('Source SHA must be full lowercase Git commit')
    base_off = load_cell(ids[0], source_sha, BACKGROUND_SHA256,
                         'ws23_crossclass_bg_1x8MiB.txt', False, 1)
    base_on = load_cell(ids[1], source_sha, BACKGROUND_SHA256,
                        'ws23_crossclass_bg_1x8MiB.txt', True, 1)
    mixed_off = load_cell(ids[2], source_sha, MIXED_SHA256,
                          'ws23_crossclass_bg_plus_3x4MiB.txt', False, 4)
    mixed_on = load_cell(ids[3], source_sha, MIXED_SHA256,
                         'ws23_crossclass_bg_plus_3x4MiB.txt', True, 4)
    if base_off['summary']['fct_sha256'] != base_on['summary']['fct_sha256'] or \
            mixed_off['summary']['fct_sha256'] != mixed_on['summary']['fct_sha256']:
        raise ValueError('Diagnostic changed FCT bytes on an identical input')
    background = background_source_hop(base_on)
    exposed = background_source_hop(mixed_on)
    if background['port'] != exposed['port']:
        raise ValueError('Background path changed between paired traces')
    contenders = [hop for hop in mixed_on['hops'] if hop['tag'] == 2 and
                  hop['switch'] == 32 and hop['port'] == exposed['port'] and
                  max(hop['first_enqueue_ns'], exposed['first_enqueue_ns']) <
                  min(hop['last_dequeue_ns'], exposed['last_dequeue_ns'])]
    if not contenders:
        raise ValueError('No contender overlapped the background on the same source-ToR egress')
    base_fct = base_on['summary']['tags']['1']['mean_fct_us']
    mixed_fct = mixed_on['summary']['tags']['1']['mean_fct_us']
    base_wait = background['wait_ns_sum'] / background['packets']
    mixed_wait = exposed['wait_ns_sum'] / exposed['packets']
    if not mixed_fct > base_fct or not mixed_wait > base_wait or not \
            exposed['mmu_egress_bytes_max'] > background['mmu_egress_bytes_max']:
        raise ValueError('Shared egress did not produce the preregistered background delay and occupancy change')
    return {'source_sha': source_sha, 'topology_sha256': TOPOLOGY_SHA256,
            'background_trace_sha256': BACKGROUND_SHA256,
            'mixed_trace_sha256': MIXED_SHA256,
            'ids': ids, 'shared_source_tor': 32, 'shared_port': exposed['port'],
            'overlapping_contender_flows': len(contenders),
            'background_fct_us_base': base_fct, 'background_fct_us_mixed': mixed_fct,
            'background_mean_wait_ns_base': base_wait,
            'background_mean_wait_ns_mixed': mixed_wait,
            'background_mmu_egress_bytes_max_base': background['mmu_egress_bytes_max'],
            'background_mmu_egress_bytes_max_mixed': exposed['mmu_egress_bytes_max'],
            'base_fct_sha256': base_on['summary']['fct_sha256'],
            'mixed_fct_sha256': mixed_on['summary']['fct_sha256']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--pair', choices=('background', 'mixed'),
                        help='check one diagnostic off/on pair before continuing')
    parser.add_argument('ids', nargs='+')
    args = parser.parse_args()
    if args.pair:
        if len(args.ids) != 2:
            parser.error('--pair requires two IDs: diagnostic off, then on')
        result = verify_pair(args.source_sha, args.ids, args.pair)
    else:
        if len(args.ids) != 4:
            parser.error('full causal verification requires four IDs in protocol order')
        result = verify(args.source_sha, args.ids)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
