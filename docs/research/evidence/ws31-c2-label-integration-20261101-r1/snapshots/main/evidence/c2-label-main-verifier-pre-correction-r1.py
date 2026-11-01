"""Main independent raw acceptance for the five frozen C2 label cells.

Uses original input labels for business identity, and transformed labels only
for policy and packet checks. Accepts no partial input or completed-flow window.
"""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def fields(line):
    return {k: int(v) for k, v in
            (token.split('=', 1) for token in line.split()[1:] if '=' in token)}


def policy_label(tag, intervention):
    if intervention == 1:
        return 0
    if intervention == 2 and tag in (1, 2):
        return 3-tag
    return tag


def hash_wait(key, tag):
    if tag != 2:
        return 0
    src, dst, sport, dport = key
    words = ((11 << 24) | (src << 8) | 1,
             (11 << 24) | (dst << 8) | 1, sport | (dport << 16))
    value = 2166136261 ^ 0x43c2a517
    for word in words:
        for byte in word.to_bytes(4, 'little'):
            value = ((value ^ byte)*16777619) & 0xffffffff
    value ^= value >> 16
    value = (value*0x85ebca6b) & 0xffffffff
    value ^= value >> 13
    return value % 501


def trace_rows(path):
    lines = path.read_text(encoding='ascii').splitlines()
    assert len(lines)-1 == int(lines[0])
    sports, dports = defaultdict(lambda: 10000), defaultdict(lambda: 100)
    result, by_id = {}, {}
    for index, line in enumerate(lines[1:]):
        src, dst, pg, size, start, tag = line.split()
        src, dst, size, tag = map(int, (src, dst, size, tag))
        key = (src, dst, sports[src], dports[dst])
        assert key not in result
        result[key] = {'id': index, 'size': size, 'tag': tag,
                       'demand_ns': int(Fraction.from_float(float(start))*10**9)}
        by_id[index] = key
        sports[src] += 1
        dports[dst] += 1
    return result, by_id


def raw_paths(base):
    fcts = list((base/'raw').glob('*/*_out_fct.txt'))
    logs = list((base/'raw').glob('*/config.log'))
    assert len(fcts) == len(logs) == 1
    return fcts[0], logs[0]


def ordered_hashes(log, remove_tag=False):
    hashes = {p: hashlib.sha256() for p in ('WS30_CHOICE', 'WS30_ROUTE')}
    excluded = {'uid', 'tag'} if remove_tag else {'uid'}
    for line in log.open(encoding='utf-8'):
        tokens = line.split()
        if tokens and tokens[0] in hashes:
            normalized = ' '.join(t for t in tokens if t.split('=', 1)[0] not in excluded)+'\n'
            hashes[tokens[0]].update(normalized.encode('utf-8'))
    return {p: h.hexdigest() for p, h in hashes.items()}


def verify(base, plan, reference=None):
    meta = json.loads((base/'metadata.json').read_text(encoding='utf-8'))
    assert meta['git_commit'] == plan['source_sha'] and meta['status'] == 'SUCCEEDED'
    cell = next(c for c in plan['cells'] if c['id'] == meta['experiment_id'])
    assert meta['algorithm'] == cell['lb'] and meta['concurrency_cap'] == 1
    params = meta['parameters']
    for k, v in plan['common'].items():
        if k != 'max_concurrent':
            assert params[k] == v, (k, params[k], v)
    assert params['flow_file'] == cell['flow_file']
    intervention = cell['ws30_tag_transform']
    assert params.get('ws30_tag_transform', 0) == intervention
    for k in ('ws30_composition', 'ws30_lifecycle', 'ws30_life_profile'):
        assert params.get(k, 0) == 0
    trace, topo = base/'config/traffic_trace.txt', base/'config/topology.txt'
    assert digest(trace) == plan['inputs']['config/'+cell['flow_file']]
    assert digest(topo) == plan['inputs']['config/leaf_spine_128_100G_OS2.txt']
    expected, by_id = trace_rows(trace)
    assert len(expected) == cell['flow_count']
    assert sum(v['size'] for v in expected.values()) == cell['payload_bytes']
    fct, log = raw_paths(base)
    completed = {}
    for line in fct.read_text(encoding='ascii').splitlines():
        row = tuple(map(int, line.split()))
        assert len(row) == 8
        key = row[:4]
        assert key in expected and key not in completed
        e = expected[key]
        assert row[4:6] == (e['size'], e['demand_ns']) and row[6] >= 0 and row[7] > 0
        completed[key] = row
    assert completed.keys() == expected.keys()
    config = {line.split()[0]: line.split()[1:] for line in
              (base/'config/config.txt').read_text(encoding='ascii').splitlines() if line.strip()}
    mtu = int(config['PACKET_PAYLOAD_SIZE'][0])
    assert mtu == 1000 and config['LB_MODE'] == [str(43 if cell['lb'] == 'ws31-c2' else 33)]
    lines = topo.read_text(encoding='ascii').splitlines()
    switches = set(map(int, lines[1].split()))
    host_tor = {}
    for line in lines[2:2+int(lines[0].split()[2])]:
        a, b = map(int, line.split()[:2])
        if a not in switches:
            host_tor[a] = b
        if b not in switches:
            host_tor[b] = a
    counts = Counter()
    summaries = {}
    timing = {p: {} for p in ('WS31_C2_DEMAND', 'WS31_C2_LAUNCH', 'WS31_C2_FINISH')}
    qp_ports, intervals = {}, defaultdict(list)
    observed_packet_tags = Counter()
    previous_time = -1
    for line in log.open(encoding='utf-8'):
        assert 'WS30_OBSERVATION_OVERFLOW' not in line
        prefix = line.split(' ', 1)[0].strip()
        if prefix not in ('WS30_CHOICE', 'WS30_ROUTE', 'WS30_QUEUE', 'WS30_PATH', 'WS30_QP',
                          'WS31_C2_DEMAND', 'WS31_C2_LAUNCH', 'WS31_C2_FINISH', 'WS31_C2_STATE'):
            continue
        counts[prefix] += 1
        v = fields(line)
        if prefix in ('WS30_QUEUE', 'WS30_PATH', 'WS31_C2_STATE'):
            assert prefix not in summaries
            summaries[prefix] = v
        if prefix in timing:
            assert v['flow_id'] in by_id and v['flow_id'] not in timing[prefix]
            timing[prefix][v['flow_id']] = v
        if prefix not in ('WS30_CHOICE', 'WS30_ROUTE'):
            continue
        assert v['time_ns'] >= previous_time
        previous_time = v['time_ns']
        key = ((v['sip'] >> 8) & 65535, (v['dip'] >> 8) & 65535, v['sport'], v['dport'])
        assert key in expected
        packet_tag = policy_label(expected[key]['tag'], intervention)
        assert v['tag'] == packet_tag
        if prefix != 'WS30_ROUTE':
            continue
        route_key = (v['switch'], key)
        assert qp_ports.setdefault(route_key, v['port']) == v['port']
        observed_packet_tags[packet_tag] += 1
        if v['switch'] == host_tor[key[0]]:
            seq, size = v['seq'], expected[key]['size']
            assert 0 <= seq < size
            intervals[key].append((seq, seq+min(mtu, size-seq)))
    unique_bytes = 0
    for key, e in expected.items():
        total, end = 0, 0
        for lo, hi in sorted(intervals[key]):
            assert lo <= end, ('source payload gap', key, lo, end)
            total += max(0, hi-end)
            end = max(end, hi)
        assert total == end == e['size']
        unique_bytes += total
    q, path = summaries['WS30_QUEUE'], summaries['WS30_PATH']
    assert q['enqueued'] == q['dequeued']+q['dropped']+q['current']
    for k in ('dropped', 'current', 'admission_dropped_bytes', 'queue_rejected_bytes', 'violations'):
        assert q[k] == 0
    assert path['switch_qps'] == len(qp_ports) and counts['WS30_ROUTE'] == path['full_rows']
    assert path['port_changes'] == path['changed_qps'] == path['rejected'] == 0
    assert counts['WS30_ROUTE'] < 1000000 and counts['WS30_QP'] == len(expected)
    assert counts['WS30_CHOICE'] == len(qp_ports) == 3*len(expected)
    waits = []
    if cell['lb'] == 'ws31-c2':
        assert all(table.keys() == by_id.keys() for table in timing.values())
        for i, key in by_id.items():
            e, raw = expected[key], completed[key]
            d, launch, finish = (timing[p][i] for p in timing)
            policy = policy_label(e['tag'], intervention)
            wait = hash_wait(key, policy)
            assert d['tag'] == e['tag'] and d['policy_tag'] == policy and d['tag_transform'] == intervention
            assert d['delay_ns'] == launch['wait_ns'] == finish['wait_ns'] == wait
            assert d['demand_ns'] == launch['demand_ns'] == finish['demand_ns'] == raw[5]
            assert launch['launch_ns'] == finish['launch_ns'] == raw[5]+wait <= finish['finish_ns']
            assert finish['finish_ns'] == raw[5]+raw[6] and finish['fct_ns'] == raw[6]
            assert d['size'] == launch['size'] == finish['size'] == raw[4]
            waits.append(wait)
        state = summaries['WS31_C2_STATE']
        for k in ('demanded', 'launched', 'finished'):
            assert state[k] == cell['flow_count']
        for k in ('demand_bytes', 'launch_bytes', 'finish_bytes'):
            assert state[k] == cell['payload_bytes']
        for k in ('cancelled', 'cancel_bytes', 'pending', 'unfinished'):
            assert state[k] == 0
        assert state['waited'] == sum(w > 0 for w in waits)
        assert state['delay_sum_ns'] == sum(waits) and state['delay_max_ns'] == max(waits)
        if cell['id'].endswith(('default', 'swap')):
            assert any(waits)
        else:
            assert not any(waits)
    else:
        assert not any(timing.values()) and 'WS31_C2_STATE' not in summaries
    suffix = cell['id'].removeprefix('20261101-074000-ws31-c2tag-r1-')
    comparisons = {}
    if suffix in ('default', 'remove', 'unknown-c2'):
        assert reference is not None, 'Frozen regression requires reference results'
        ref_fct, ref_log = raw_paths(reference)
        expected_ref = {'default': plan['reference_ids']['c2_default'],
                        'remove': plan['reference_ids']['queuepin_zero'],
                        'unknown-c2': plan['reference_ids']['unknown_q12']}[suffix]
        ref_meta = json.loads((reference/'metadata.json').read_text(encoding='utf-8'))
        assert ref_meta['experiment_id'] == expected_ref and ref_meta['status'] == 'SUCCEEDED'
        assert digest(ref_fct) == digest(fct)
        assert digest(reference/'config/traffic_trace.txt') == digest(trace)
        assert digest(reference/'config/topology.txt') == digest(topo)
        remove_tag = suffix == 'remove'
        assert ordered_hashes(log, remove_tag) == ordered_hashes(ref_log, remove_tag)
        comparisons = {'reference_id': expected_ref, 'full_fct_equal': True,
                       'ordered_choice_route_equal': True,
                       'removed_comparison_fields': ['uid', 'tag'] if remove_tag else ['uid']}
    return {'status': 'PASS_FOR_C2_LABEL_TECHNICAL_SCOPE', 'id': cell['id'], 'source_sha': plan['source_sha'],
            'flow_count': len(completed), 'payload_bytes': unique_bytes,
            'original_business_tags': dict(Counter(e['tag'] for e in expected.values())),
            'packet_tag_data_hops': dict(observed_packet_tags), 'transform': intervention,
            'c2_exact_hash_waits_verified': len(waits), 'positive_waits': sum(w > 0 for w in waits),
            'delay_sum_ns': sum(waits), 'delay_max_ns': max(waits, default=0),
            'queue_summary': q, 'path_summary': path, 'observation_counts': dict(counts),
            'fct_sha256': digest(fct), 'log_sha256': digest(log),
            'ordered_hashes_remove_uid_only': ordered_hashes(log), 'regression': comparisons,
            'scope': 'Technical label/default/fallback only; no effects or additional baseline admission'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Refusing to overwrite main acceptance receipt'
    result = verify(args.results, json.loads(args.plan.read_text(encoding='utf-8')), args.reference)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('id', 'flow_count', 'positive_waits', 'regression')}))
