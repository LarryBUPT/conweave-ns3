#!/usr/bin/env python3
"""Summarize WS-13 per-QP IRN feedback and queue probes without causal claims."""
import collections
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'results/ws13-feedback-probe-plan.json'
OUT = ROOT / 'docs/research/evidence/ws13-feedback-probe-analysis.json'
FIELDS = ('src', 'dst', 'sport', 'dport', 'flow_id', 'snd_una', 'snd_nxt',
          'irn_nack_size', 'switch', 'port', 'packets', 'bytes',
          'queued_bytes_sum', 'queued_bytes_max', 'wait_ns_sum', 'wait_ns_max')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fields(line):
    return {key: value for key, value in
            (part.split('=', 1) for part in line.split()[1:] if '=' in part)}


def flow_key(row):
    return tuple(int(row[k]) for k in ('src', 'dst', 'sport', 'dport'))


def main():
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    cells = []
    for cell in plan['cells']:
        base = ROOT / 'results' / cell['id']
        meta = json.loads((base / 'metadata.json').read_text(encoding='utf-8'))
        assert meta['status'] == 'SUCCEEDED' and meta['git_commit'] == plan['git_commit']
        assert meta['input_flow_sha256'] == cell['flow_sha256']
        raw = base / 'raw' / str(meta['raw_directory'])
        fct_file = raw / (str(meta['raw_directory']) + '_out_fct.txt')
        assert sha(fct_file) == cell['ws12_reference_fct_sha256']
        fcts = []
        with fct_file.open(encoding='utf-8') as source:
            for line in source:
                row = list(map(int, line.split()))
                assert len(row) == 8
                fcts.append({'src': row[0], 'dst': row[1], 'sport': row[2],
                             'dport': row[3], 'size_bytes': row[4],
                             'fct_ns': row[6], 'standalone_ns': row[7]})
        log_path = raw / 'config.log'
        log = log_path.read_text(encoding='utf-8')
        qp_events = collections.defaultdict(collections.Counter)
        qp_sizes = collections.defaultdict(list)
        for line in log.splitlines():
            if not line.startswith('WS13_QP '):
                continue
            row = fields(line)
            assert 'irn_nack_size' in row
            key = tuple(int(row[k]) for k in ('src', 'dst', 'sport', 'dport'))
            event = row['event']
            assert event in ('irn_ack', 'sack', 'cnp', 'timeout')
            if event == 'sack':
                assert int(row['irn_nack_size']) > 0
                qp_sizes[key].append(int(row['irn_nack_size']))
            if event == 'irn_ack':
                assert int(row['irn_nack_size']) == 0
            qp_events[key][event] += 1
        hops = collections.defaultdict(list)
        for line in log.splitlines():
            if not line.startswith('WS13_HOP '):
                continue
            row = fields(line)
            key = tuple(int(row[k]) for k in ('src', 'dst', 'sport', 'dport'))
            hops[key].append({k: int(row[k]) for k in
                              ('switch', 'port', 'packets', 'bytes',
                               'queued_bytes_sum', 'queued_bytes_max',
                               'wait_ns_sum', 'wait_ns_max')})
        unpaired = int(re.search(r'WS13_INFLIGHT unpaired=(\d+)', log).group(1))
        assert unpaired == 0
        tails = sorted((row for row in fcts if row['size_bytes'] == 8388608),
                       key=lambda row: row['fct_ns'], reverse=True)[:2]
        tail_details = []
        for row in tails:
            key = flow_key(row)
            counters = qp_events[key]
            tail_details.append({**row, 'fct_us': round(row['fct_ns'] / 1000, 3),
                                 'qp_events': dict(counters),
                                 'sack_sizes_bytes': qp_sizes[key],
                                 'hop_queues': hops[key]})
        hop_rows = [item for records in hops.values() for item in records]
        packet_sum = sum(row['packets'] for row in hop_rows)
        wait_sum = sum(row['wait_ns_sum'] for row in hop_rows)
        event_totals = collections.Counter()
        for counts in qp_events.values():
            event_totals.update(counts)
        cells.append({'id': cell['id'], 'group': cell['group'],
                      'background': cell['background'], 'mode': cell['mode'],
                      'status': meta['status'], 'git_commit': meta['git_commit'],
                      'trace_sha256': meta['input_flow_sha256'],
                      'fct_sha256': sha(fct_file),
                      'fct_rows': len(fcts), 'config_log_mib': round(log_path.stat().st_size / 1048576, 2),
                      'qp_event_totals': dict(event_totals),
                      'sack_flow_count': sum(bool(v) for v in qp_sizes.values()),
                      'hop_records': len(hop_rows), 'hop_packet_sum': packet_sum,
                      'hop_wait_packet_ns_mean': round(wait_sum / packet_sum, 1) if packet_sum else None,
                      'hop_wait_ns_max': max((row['wait_ns_max'] for row in hop_rows), default=0),
                      'hop_queue_bytes_max': max((row['queued_bytes_max'] for row in hop_rows), default=0),
                      'unpaired_packets': unpaired, 'two_slowest_background_flows': tail_details})
    result = {'purpose': plan['role'], 'source_commit': plan['git_commit'],
              'topology_sha256': plan['topology_sha256'], 'cells': cells,
              'interpretation': 'One-seed diagnostic correlation only; hop queue summaries are not a causal decomposition.'}
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print('Wrote %d verified probe summaries to %s' % (len(cells), OUT))


if __name__ == '__main__':
    main()
