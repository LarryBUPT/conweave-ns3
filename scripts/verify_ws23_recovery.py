#!/usr/bin/env python3
"""Verify the two fixed WS-23 IRN+PFC transport correctness runs."""
import argparse
import hashlib
import json
import os
import re

from analyze_moe_tags import summarize
from analyze_result import PROJECT


REFERENCE = '20260927-215700-irnpfcstress-11'
PRESSURE_TRACE_SHA256 = 'bc2db1513cbde20f12eea6efa4e2265cf74954be4fa45f2a147ff0ce84b33985'
PAUSE_TRACE_SHA256 = '4f10f678000f7b380cc272e121db7926ca320a581c72b47909545f31f2a312f8'
TOPOLOGY_SHA256 = 'dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad'
PROBE_START_NS = 6000200
PROBE_END_NS = 7800200
PROBE_PAUSE_US = 2500
MAX_RTO_NS = 1350000
COMPLETE = re.compile(
    r'^WS23_IRN_PFC_QP_COMPLETE flow_id=(\d+) size=(\d+) snd_una=(\d+) '
    r'snd_nxt=(\d+) tx_payload_bytes=(\d+) tx_packets=(\d+)$')
RECOVERY = re.compile(r'^WS23_IRN_PFC_TIMEOUT_RECOVERY time_ns=(\d+) flow_id=(\d+) '
                      r'snd_una=(\d+) snd_nxt=(\d+) local_paused=(\d+)$')
DEFERRED = re.compile(r'^WS23_IRN_PFC_TIMEOUT_DEFERRED .* paused=(\d+) delay_ns=(\d+)$')
LOCAL_PFC = re.compile(r'^WS23_PFC_LOCAL_(PAUSE|RESUME) time_ns=(\d+) host=(\d+) pg=(\d+)$')
PFC_INJECT = re.compile(r'^WS23_PFC_INJECT time_ns=(\d+) host=(\d+) pg=(\d+) type=(\d+) pause_us=(\d+)$')
PFC_RX = re.compile(r'^WS23_PFC_RX time_ns=(\d+) node=(\d+) pg=(\d+) type=(\d+)$')


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def load_metadata(experiment_id):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', experiment_id):
        raise ValueError('Invalid experiment ID')
    path = os.path.join(PROJECT, 'results', experiment_id, 'metadata.json')
    with open(path, encoding='utf-8') as source:
        return json.load(source)


def result_paths(experiment_id, metadata):
    raw_id = str(metadata.get('raw_directory', ''))
    if not re.fullmatch(r'\d+', raw_id):
        raise ValueError('Invalid raw directory')
    base = os.path.join(PROJECT, 'results', experiment_id)
    raw = os.path.join(base, 'raw', raw_id)
    return base, raw, os.path.join(raw, 'config.log')


def verify_common(experiment_id, expected_trace, expected_source_sha):
    current = load_metadata(experiment_id)
    if current.get('status') != 'SUCCEEDED' or current.get('seed') != 1:
        raise ValueError('Simulation status or seed is wrong')
    if current.get('git_commit') != expected_source_sha:
        raise ValueError('Simulation source SHA differs from frozen contract')
    if current.get('git_commit') == load_metadata(REFERENCE)['git_commit']:
        raise ValueError('New run must use a distinct fixed source SHA')
    if current.get('algorithm') != 'fecmp' or current.get('input_flow_sha256') != expected_trace:
        raise ValueError('Algorithm or trace hash differs from frozen contract')
    if current.get('topology_sha256') != TOPOLOGY_SHA256:
        raise ValueError('Topology metadata differs from frozen contract')
    params = current.get('parameters', {})
    expected = {'lb': 'fecmp', 'pfc': 1, 'irn': 1, 'factorial_pilot': True,
                'factorial_drop_diag': True, 'topo': 'fat_k4_100G_OS2',
                'bw': 100, 'simul_time': '0.01'}
    for key, value in expected.items():
        if params.get(key) != value:
            raise ValueError('Parameter differs from frozen contract: ' + key)
    summary = summarize(experiment_id)
    if summary['trace_sha256'] != expected_trace:
        raise ValueError('Trace snapshot differs from frozen contract')
    base, raw, log_path = result_paths(experiment_id, current)
    if sha256(os.path.join(base, 'config', 'topology.txt')) != TOPOLOGY_SHA256:
        raise ValueError('Topology snapshot differs from frozen contract')
    return current, params, summary, base, raw, log_path


def parse_log(log_path):
    records = {'completions': {}, 'recoveries': [], 'deferrals': [],
               'local_pfc': [], 'injections': [], 'pfc_rx': [],
               'admission_drops': 0, 'queue_rejects': 0, 'link_drops': 0,
               'timeouts': 0, 'other_drops': 0}
    with open(log_path, encoding='utf-8', errors='replace') as source:
        for line in source:
            line = line.rstrip('\r\n')
            match = COMPLETE.fullmatch(line)
            if match:
                flow_id, size, una, nxt, tx_bytes, packets = map(int, match.groups())
                if flow_id in records['completions']:
                    raise ValueError('Duplicate QP completion')
                records['completions'][flow_id] = (size, una, nxt, tx_bytes, packets)
            elif line.startswith('WS23_IRN_PFC_QP_COMPLETE '):
                raise ValueError('Malformed QP completion receipt')
            match = RECOVERY.fullmatch(line)
            if match:
                records['recoveries'].append(tuple(map(int, match.groups())))
            elif line.startswith('WS23_IRN_PFC_TIMEOUT_RECOVERY '):
                raise ValueError('Malformed timeout recovery receipt')
            match = DEFERRED.fullmatch(line)
            if match:
                paused, delay = map(int, match.groups())
                if delay <= 0:
                    raise ValueError('Timeout deferral did not schedule a future timer')
                records['deferrals'].append((paused, delay))
            elif line.startswith('WS23_IRN_PFC_TIMEOUT_DEFERRED '):
                raise ValueError('Malformed timeout deferral receipt')
            for prefix, pattern, key in (
                    ('WS23_PFC_LOCAL_', LOCAL_PFC, 'local_pfc'),
                    ('WS23_PFC_INJECT ', PFC_INJECT, 'injections'),
                    ('WS23_PFC_RX ', PFC_RX, 'pfc_rx')):
                if line.startswith(prefix):
                    match = pattern.fullmatch(line)
                    if not match:
                        raise ValueError('Malformed PFC receipt: ' + prefix)
                    values = match.groups()
                    records[key].append(((values[0],) + tuple(map(int, values[1:])))
                                        if key == 'local_pfc' else tuple(map(int, values)))
            records['admission_drops'] += line.startswith('FACTORIAL_ADMISSION_DROP ')
            records['queue_rejects'] += line.startswith('FACTORIAL_QUEUE_REJECT ')
            records['link_drops'] += line.startswith(('WS23_LINK_RX_DROP ', 'WS23_PHY_RX_DROP ',
                                                      'WS23_PHY_TX_DROP ', 'WS23_HOST_ACK_QUEUE_REJECT '))
            records['timeouts'] += line.startswith('WS08_TX_TIMEOUT ')
            records['other_drops'] += line.startswith('WARNING - Drop occurs in SendToDevContinue()')
    return records


def verify_pressure(experiment_id, expected_source_sha):
    reference = load_metadata(REFERENCE)
    current, params, summary, base, raw, log_path = verify_common(
        experiment_id, PRESSURE_TRACE_SHA256, expected_source_sha)
    for field in ('input_flow_sha256', 'topology_sha256', 'seed', 'algorithm'):
        if current[field] != reference[field]:
            raise ValueError('Changed fixed input: ' + field)
    for key, value in reference['parameters'].items():
        if params.get(key) != value:
            raise ValueError('Changed fixed parameter: ' + key)
    if params.get('ws23_pfc_probe_host', -1) != -1 or params.get('buffer') != 1:
        raise ValueError('Pressure run must not inject a PFC probe')
    for tag in ('1', '2'):
        if summary['tags'][tag]['input_flows'] != 8 or summary['tags'][tag]['completed_flows'] != 8:
            raise ValueError('Transport completion gate failed for tag ' + tag)
    records = parse_log(log_path)
    completions = records['completions']
    if set(completions) != set(range(16)):
        raise ValueError('Missing per-QP completion/byte receipts')
    for flow_id, receipt in completions.items():
        size, una, nxt, tx_bytes, packets = receipt
        if size != 1048576 or una != size or nxt != size or tx_bytes < size or packets == 0:
            raise ValueError('QP byte/sequence conservation failed for flow ' + str(flow_id))
    if not records['recoveries'] or records['timeouts'] < len(records['recoveries']):
        raise ValueError('Stress input did not exercise timeout recovery')
    if not records['admission_drops']:
        raise ValueError('Stress input did not reproduce data admission loss')
    if records['queue_rejects'] or records['link_drops'] or records['other_drops']:
        raise ValueError('Unexpected queue/link loss changed the stress failure model')
    with open(os.path.join(base, 'config', 'traffic_trace.txt'), encoding='utf-8') as source:
        source.readline()
        flow_hosts = {number: tuple(map(int, line.split()[:3:2]))
                      for number, line in enumerate(source)}
    if set(flow_hosts) != set(range(16)):
        raise ValueError('Pressure trace flow count changed')
    for time_ns, flow_id, _, _, paused in records['recoveries']:
        if flow_id not in flow_hosts or paused != 0:
            raise ValueError('Timeout recovery occurred on a paused or unknown flow')
        host, pg = flow_hosts[flow_id]
        active = False
        for event, event_time, event_host, event_pg in records['local_pfc']:
            if (event_host, event_pg) == (host, pg) and event_time <= time_ns:
                active = event == 'PAUSE'
        if active:
            raise ValueError('Timeout recovery occurred during local PFC pause')
    return {'experiment_id': experiment_id, 'git_commit': current['git_commit'],
            'trace_sha256': summary['trace_sha256'], 'fct_sha256': summary['fct_sha256'],
            'completed_flows': 16, 'qp_byte_receipts': len(completions),
            'timeout_recoveries': len(records['recoveries']),
            'timeout_deferrals': len(records['deferrals']),
            'data_admission_drops': records['admission_drops'],
            'total_tx_payload_bytes': sum(item[3] for item in completions.values())}


def verify_pause(experiment_id, expected_source_sha):
    current, params, summary, base, raw, log_path = verify_common(
        experiment_id, PAUSE_TRACE_SHA256, expected_source_sha)
    expected = {'buffer': 9, 'flow_file': 'ws23_pause_probe_1x1MiB.txt',
                'ws23_pfc_probe_host': 0, 'ws23_pfc_probe_pg': 3,
                'ws23_pfc_probe_start_ns': PROBE_START_NS,
                'ws23_pfc_probe_end_ns': PROBE_END_NS,
                'ws23_pause_time_us': PROBE_PAUSE_US}
    for key, value in expected.items():
        if params.get(key) != value:
            raise ValueError('Pause parameter differs from frozen contract: ' + key)
    if set(summary['tags']) != {'1'} or summary['tags']['1']['input_flows'] != 1 or summary['tags']['1']['completed_flows'] != 1:
        raise ValueError('Lossless pause flow did not complete exactly once')
    records = parse_log(log_path)
    if set(records['completions']) != {0}:
        raise ValueError('Pause QP must complete exactly once')
    size, una, nxt, tx_bytes, packets = records['completions'][0]
    if (size, una, nxt, tx_bytes) != (1048576,) * 4 or packets == 0:
        raise ValueError('Pause QP completion or payload byte conservation failed')
    if any(records[key] for key in ('admission_drops', 'queue_rejects', 'link_drops', 'timeouts', 'other_drops')) or records['recoveries']:
        raise ValueError('Lossless pause caused a drop or timeout recovery')
    expected_injections = [(2_000_000_000 + PROBE_START_NS, 0, 3, 0, PROBE_PAUSE_US),
                           (2_000_000_000 + PROBE_END_NS, 0, 3, 1, 0)]
    if records['injections'] != expected_injections:
        raise ValueError('Pause/resume injection was not issued at the frozen times')
    local = [(event, time_ns) for event, time_ns, host, pg in records['local_pfc']
             if (host, pg) == (0, 3)]
    rx = [(time_ns, kind) for time_ns, host, pg, kind in records['pfc_rx']
          if (host, pg) == (0, 3)]
    if len(local) != 2 or [event for event, _ in local] != ['PAUSE', 'RESUME'] or len(rx) != 2 or [kind for _, kind in rx] != [0, 1]:
        raise ValueError('Source host did not receive one real pause and resume')
    if [time_ns for _, time_ns in local] != [time_ns for time_ns, _ in rx]:
        raise ValueError('Source PFC receive and local state times disagree')
    pause_ns, resume_ns = [time_ns for _, time_ns in local]
    if pause_ns < expected_injections[0][0] or resume_ns < expected_injections[1][0] or resume_ns - pause_ns <= MAX_RTO_NS:
        raise ValueError('Pause did not span a full RTO')
    if not any(paused == 1 for paused, _ in records['deferrals']):
        raise ValueError('Pause did not exercise timeout deferral')
    with open(os.path.join(raw, str(current['raw_directory']) + '_out_fct.txt'), encoding='utf-8') as source:
        rows = [line.split() for line in source if line.strip()]
    if len(rows) != 1:
        raise ValueError('Lossless pause FCT must contain one completion')
    start_ns, fct_ns = map(int, rows[0][5:7])
    if not start_ns < pause_ns < resume_ns < start_ns + fct_ns:
        raise ValueError('Pause/resume did not occur during the flow')
    with open(os.path.join(raw, str(current['raw_directory']) + '_out_pfc.txt'), encoding='utf-8') as source:
        pfc_rows = [tuple(map(int, line.split())) for line in source if line.strip()]
    if not all(any(row[0] == time_ns and row[1] == 0 and row[2] == 0 and row[4] == kind
                   for row in pfc_rows) for time_ns, kind in ((pause_ns, 1), (resume_ns, 0))):
        raise ValueError('Raw PFC events do not confirm source pause/resume')
    return {'experiment_id': experiment_id, 'git_commit': current['git_commit'],
            'trace_sha256': summary['trace_sha256'], 'fct_sha256': summary['fct_sha256'],
            'completed_flows': 1, 'qp_byte_receipts': 1,
            'source_pause_ns': pause_ns, 'source_resume_ns': resume_ns,
            'timeout_deferrals': len(records['deferrals']), 'timeout_recoveries': 0,
            'drop_events': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=('pressure', 'pause'), required=True)
    parser.add_argument('--source-sha', required=True, help='frozen 40-hex simulation source commit')
    parser.add_argument('experiment_id')
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.source_sha):
        parser.error('--source-sha must be a full lowercase Git commit SHA')
    verify = verify_pressure if args.scenario == 'pressure' else verify_pause
    print(json.dumps(verify(args.experiment_id, args.source_sha), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
