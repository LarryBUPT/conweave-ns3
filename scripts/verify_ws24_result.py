#!/usr/bin/env python3
"""Verify fetched WS-24 per-flow identity, rail feedback and byte conservation."""

import argparse
import hashlib
import ipaddress
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_event(line):
    fields = {}
    for item in line.strip().split()[1:]:
        key, sep, value = item.partition('=')
        if sep:
            fields[key] = value
    return fields


def event_ipv4(ip_u32):
    """Match this repository's Ipv4Address::Print, which emits octets 2 and 3."""
    octets = str(ipaddress.IPv4Address(ip_u32)).split('.')
    return '.'.join(octets[1:3])


def verify(experiment_id, source_sha, profile='minimal', fixture=None):
    base = ROOT / 'results' / experiment_id
    meta = json.loads((base / 'metadata.json').read_text(encoding='utf-8'))
    assert meta['status'] == 'SUCCEEDED'
    assert meta['git_commit'] == source_sha
    params = meta['parameters']
    assert params['ws24_multi_nic'] == 1
    trace = base / 'config' / 'traffic_trace.txt'
    topology = base / 'config' / 'topology.txt'
    nic_file = base / 'config' / 'nics.txt'
    assert digest(trace) == meta['input_flow_sha256']
    assert digest(topology) == meta['topology_sha256']
    assert digest(nic_file) == meta['ws24_nic_sha256']
    expected = {'minimal': (8, 8, 440, 22000),
                'target': (1280, 408320, 600, 30000),
                'cnp': (1280, 408320, 600, 30000),
                'arm': (1280, 408320, 600, 30000),
                'independent': (1280, 408320, 600, 30000)}[profile]
    flow_name = {'minimal': 'ws24_synthetic_2host_4nic_flows.txt',
                 'target': 'ws24_synthetic_fixed_multi_flows.txt',
                 'cnp': 'ws24_synthetic_cnp_incast_flows.txt',
                 'arm': 'ws24_synthetic_{}_flows.txt'.format(fixture),
                 'independent': 'ws24_synthetic_independent_{}_flows.txt'.format(fixture)}[profile]
    if profile == 'arm':
        assert fixture in ('fixed_single', 'fixed_multi', 'variable_single', 'variable_multi')
    elif profile == 'independent':
        assert fixture and re.match(r'^j(0[1-9]|1[0-2])_(fixed|variable)_(single|multi)$', fixture)
    else:
        assert fixture is None
    prefix = 'ws24_synthetic_2host_4nic_' if profile == 'minimal' else 'ws24_synthetic_320host_4nic_'
    assert digest(trace) == digest(ROOT / 'config' / flow_name)
    assert digest(topology) == digest(ROOT / 'config' / (prefix + 'topology.txt'))
    assert digest(nic_file) == digest(ROOT / 'config' / (prefix + 'nics.txt'))
    assert params['irn'] == 1
    if profile != 'minimal':
        assert params['lb'] == 'fecmp'
        assert int(params['bw']) == 400 and int(params['buffer']) == 9
        assert int(params['pfc']) == 0
    nic_rows = nic_file.read_text(encoding='ascii').splitlines()
    assert int(nic_rows[0]) == len(nic_rows) - 1
    nics = {}
    for line in nic_rows[1:]:
        host, rail, ip, peer, interface, legacy = line.split()
        host, rail, peer, interface = map(int, (host, rail, peer, interface))
        assert (host, rail) not in nics and interface == rail + 1
        nics[host, rail] = (int(ipaddress.IPv4Address(ip)), interface)
    trace_rows = trace.read_text(encoding='ascii').splitlines()
    assert int(trace_rows[0]) == len(trace_rows) - 1
    demands = {}
    for line in trace_rows[1:]:
        row = tuple(map(int, line.split()))
        assert len(row) == 12 and row[0] not in demands
        demands[row[0]] = row
    raw = base / 'raw' / str(meta['raw_directory'])
    receipts = list(raw.glob('*_out_ws24.txt'))
    fct_files = list(raw.glob('*_out_fct.txt'))
    assert len(receipts) == len(fct_files) == 1
    lines = receipts[0].read_text(encoding='ascii').splitlines()
    expected_header = ('flow_id job src_rank dst_rank src_host dst_host rail src_ip_u32 '
                       'dst_ip_u32 sport dport tag bytes demand_ns release_ns finish_ns '
                       'rx_unique_bytes tx_payload_bytes snd_una snd_nxt')
    assert lines[0] == expected_header
    assert len(lines) - 1 == len(demands)
    completions = {}
    for line in lines[1:]:
        row = tuple(map(int, line.split()))
        assert len(row) == 20 and row[0] not in completions
        (flow_id, job, srank, drank, src, dst, rail, src_ip, dst_ip,
         sport, dport, tag, size, demand, release, finish,
         rx_unique, tx_payload, snd_una, snd_nxt) = row
        assert demands[flow_id] == (flow_id, job, srank, drank, src, dst,
                                    rail, rail, 3, size, demand, tag)
        assert nics[src, rail][0] == src_ip and nics[dst, rail][0] == dst_ip
        assert demand <= release <= finish
        assert rx_unique == snd_una == size and tx_payload >= size and snd_nxt >= size
        completions[flow_id] = row
    assert set(completions) == set(demands)
    fct = [tuple(map(int, line.split())) for line in fct_files[0].read_text(
        encoding='ascii').splitlines() if line.strip()]
    assert len(fct) == len(demands)
    assert all(len(row) == 8 for row in fct)
    fct_keys = Counter((row[0], row[1], row[2], row[3], row[4]) for row in fct)
    receipt_keys = Counter((row[4], row[5], row[9], row[10], row[12])
                           for row in completions.values())
    assert fct_keys == receipt_keys
    # run.py's simulation.log contains launcher output; ns-3 stdout is the raw
    # config.log copied by the remote worker.
    simulation_log = (raw / 'config.log').read_text(
        encoding='utf-8', errors='replace')
    route = ('WS24_ROUTE_SUMMARY targets={} host_pairs={} max_rtt_ns={} '
             'max_bdp_bytes={}').format(*expected)
    assert route in simulation_log
    assert 'WS24_IRN_BDP bytes={}'.format(expected[3]) in simulation_log
    uplink = list(raw.glob('*_out_uplink.txt'))
    assert len(uplink) == 1
    if profile != 'minimal':
        assert uplink[0].stat().st_size > 0
    event_names = ('WS24_TX_QP', 'WS24_RX_DATA', 'WS24_RX_ACK')
    events = {name: {} for name in event_names}
    cnp_flags = []
    cnp_rx, cnp_state, cnp_rate = [], [], []
    conservation = None
    for line in simulation_log.splitlines():
        name = line.split(' ', 1)[0]
        if name in events:
            fields = parse_event(line)
            fid = int(fields['flow_id'])
            assert fid not in events[name]
            events[name][fid] = fields
        elif name == 'WS24_CNP_FLAG':
            cnp_flags.append(parse_event(line))
        elif name == 'WS24_CNP_RX':
            cnp_rx.append(parse_event(line))
        elif name == 'WS24_CNP_STATE':
            cnp_state.append(parse_event(line))
        elif name == 'WS24_CNP_RATE':
            cnp_rate.append(parse_event(line))
        elif name == 'WS24_CONSERVATION':
            assert conservation is None
            conservation = parse_event(line)
    assert conservation is not None
    assert int(conservation['input']) == int(conservation['finished']) == len(demands)
    expected_bytes = sum(row[9] for row in demands.values())
    assert int(conservation['input_bytes']) == int(conservation['finished_bytes']) == expected_bytes
    if profile in ('target', 'arm'):
        assert len(demands) == 10 and expected_bytes == 2408448
    for name in event_names:
        assert set(events[name]) == set(demands), name
    for fid, completion in completions.items():
        rail, src, dst, src_ip, dst_ip = completion[6], completion[4], completion[5], completion[7], completion[8]
        tx, rx, ack = (events[name][fid] for name in event_names)
        assert (int(tx['host']), int(tx['rail']), int(tx['nic_if'])) == (
            src, rail, nics[src, rail][1])
        assert (tx['sip'], tx['dip']) == (event_ipv4(src_ip), event_ipv4(dst_ip))
        assert (int(rx['host']), int(rx['rail'])) == (dst, rail)
        assert (rx['local_ip'], rx['remote_ip']) == (
            event_ipv4(dst_ip), event_ipv4(src_ip))
        assert (int(ack['host']), int(ack['rail']), int(ack['nic_if'])) == (
            src, rail, nics[src, rail][1])
        assert (ack['local_ip'], ack['remote_ip']) == (
            event_ipv4(src_ip), event_ipv4(dst_ip))
    for event in cnp_flags:
        fid = int(event['flow_id'])
        assert fid in completions and int(event['rail']) == completions[fid][6]
        assert int(event['nic_if']) == nics[completions[fid][5], completions[fid][6]][1]
    if profile == 'cnp':
        assert len(demands) == 4 and expected_bytes == 4194304
        assert cnp_flags and cnp_rx and cnp_state and cnp_rate
        def identity(event, source_side):
            fid = int(event['flow_id'])
            row = completions[fid]
            ips = (row[7], row[8]) if source_side else (row[8], row[7])
            assert (int(event['local_ip_u32']), int(event['remote_ip_u32'])) == ips
            assert (int(event['sport']), int(event['dport']), int(event['pg'])) == (
                row[9], row[10], 3)
            assert int(event['rail']) == row[6]
            return (fid, event['kind'] if 'kind' in event else None, int(event['seq']) if 'seq' in event else None)
        generated = {}
        for event in cnp_flags:
            key = identity(event, False)
            assert event['cnp'] == '1' and event['kind'] in ('ack', 'nack')
            generated[key] = min(int(event['time_ns']), generated.get(key, 1 << 63))
        received = {}
        for event in cnp_rx:
            key = identity(event, True)
            row = completions[key[0]]
            assert key in generated and generated[key] <= int(event['time_ns'])
            assert event['cnp'] == '1' and event['cc_mode'] == '1'
            assert (int(event['host']), int(event['nic_if'])) == (
                row[4], nics[row[4], row[6]][1])
            received[key] = int(event['time_ns'])
        stated = {}
        for event in cnp_state:
            key = identity(event, True)
            assert key in received and received[key] <= int(event['time_ns'])
            assert event['pending_after'] == '1'
            stated[key[0]] = min(int(event['time_ns']), stated.get(key[0], 1 << 63))
        reduced = set()
        for event in cnp_rate:
            fid, _, _ = identity(event, True)
            row = completions[fid]
            assert fid in stated and stated[fid] < int(event['time_ns'])
            assert int(event['time_ns']) <= row[15] and event['pending_before'] == '1'
            assert (int(event['host']), int(event['nic_if'])) == (
                row[4], nics[row[4], row[6]][1])
            assert int(event['rate_after_bps']) < int(event['rate_before_bps'])
            reduced.add(fid)
        assert reduced
    return {
        'experiment_id': experiment_id,
        'source_sha': source_sha,
        'input_flow_sha256': digest(trace),
        'topology_sha256': digest(topology),
        'nic_sha256': digest(nic_file),
        'flows': len(demands),
        'unique_bytes': expected_bytes,
        'rails_used': dict(Counter(str(row[6]) for row in completions.values())),
        'cnp_flag_events': len(cnp_flags),
        'cnp_received_events': len(cnp_rx),
        'cnp_rate_events': len(cnp_rate),
        'profile': profile,
        'feedback_identity_verified': True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('experiment_id')
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--profile', choices=('minimal', 'target', 'cnp', 'arm', 'independent'),
                        default='minimal')
    parser.add_argument('--fixture')
    args = parser.parse_args()
    result = verify(args.experiment_id, args.source_sha, args.profile, args.fixture)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
