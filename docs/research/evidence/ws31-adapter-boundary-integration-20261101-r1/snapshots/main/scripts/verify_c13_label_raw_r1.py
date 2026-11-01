"""Main raw replay for frozen C1/C3 removal/swap; business truth stays original.

The static verification routines below extend accepted local replay logic.
They never rewrite traces, metadata, plans, logs, or former acceptance receipts.
"""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent

def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE/filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

identity = ident = module('c13_identity', 'verify_c2_label_raw_r1.py')
common = module('c13_dynamic', 'verify_dynamic_raw_r1.py')
c1 = module('c13_c1', 'verify_c1_controls_raw_r1.py')
c23 = module('c13_c23', 'verify_c23_controls_raw_r1.py')
digest, fields, policy_label = ident.digest, ident.fields, ident.policy_label
trace_rows, raw_paths = ident.trace_rows, ident.raw_paths
MAX64 = (1 << 64)-1
framed, record_key, topology_hosts = c1.framed, c1.record_key, c1.topology_hosts
events, event_key, flow_key, topology = c23.events, c23.event_key, c23.flow_key, c23.topology


def verify_common(base, plan):
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
    assert mtu == 1000 and config['LB_MODE'] == [str({'ws31-c1': 36, 'ws31-c3': 47}[cell['lb']])]
    # remote_worker sets WS30_TAG_TRANSFORM in the child environment.
    # Metadata checks the requested intervention; every ROUTE checks its effect.
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
        if prefix == 'WS30_CHOICE':
            # QueuePin deliberately passes literal0 to Ws30Choice. It is a
            # policy observation field, not a copy of the packet WorkloadTag.
            assert v['tag'] == 0
            continue
        assert v['tag'] == packet_tag
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
    assert len(qp_ports) == 3*len(expected)
    assert counts['WS30_CHOICE'] == 2*len(expected)
    assert not any(timing.values()) and 'WS31_C2_STATE' not in summaries
    return {'id': cell['id'], 'source_sha': plan['source_sha'], 'lb': cell['lb'],
            'flow_count': len(completed), 'payload_bytes': unique_bytes,
            'original_business_tags': dict(Counter(e['tag'] for e in expected.values())),
            'packet_tag_data_hops': dict(observed_packet_tags), 'transform': intervention,
            'queue_summary': q, 'path_summary': path, 'observation_counts': dict(counts),
            'fct_sha256': digest(fct), 'log_sha256': digest(log),
            'ordered_hashes_remove_uid_only': ident.ordered_hashes(log)}


def c1_replay(base, cell, pairs):
    expected, _ = identity.trace_rows(base/'config/traffic_trace.txt')
    host_tor = topology_hosts(base/'config/topology.txt')
    # Both frozen inputs have a single source ToR; explicit gate for peak scope.
    assert len({host_tor[k[0]] for k in expected}) == 1
    mode = cell['lb']
    intervention = cell['ws30_tag_transform']
    assert mode == 'ws31-c1' and intervention in (1, 2)
    history = mode == 'ws31-c1-history'
    count = mode in ('ws31-c1-count', 'ws31-c1-unified-count')
    ledger, memory, pins, states = {}, {}, {}, []
    peak = expired = unique = positive = arrivals = decisions = 0
    def expire(now):
        nonlocal expired
        for k, e in list(ledger.items()):
            if e['deadline'] <= now:
                del ledger[k]
                expired += 1
    def observed(key, now):
        value, time = memory.get(key, (0, 0))
        elapsed = max(0, now-time)
        return 0 if elapsed >= 20000 else value*(20000-elapsed)//20000
    for line in identity.raw_paths(base)[1].open(encoding='utf-8'):
        prefix = line.split(' ', 1)[0].strip()
        if prefix not in ('WS31_C1_CHOICE', 'WS30_ROUTE', 'WS31_C1_STATE'):
            continue
        v = identity.fields(line)
        if prefix == 'WS31_C1_STATE':
            states.append(v)
            continue
        flow = ((v['sip'] >> 8) & 65535, (v['dip'] >> 8) & 65535, v['sport'], v['dport'])
        assert flow in expected
        if v['switch'] != host_tor[flow[0]]:
            # Actual packet labels are checked on every hop.
            assert prefix == 'WS30_ROUTE' and v['tag'] == policy_label(expected[flow]['tag'], intervention)
            continue
        key, now = record_key(v), v['time_ns']
        expire(now)
        if prefix == 'WS31_C1_CHOICE':
            assert key not in pins and (v['first'], v['second']) == pairs[key]
            for suffix, port in [('1', v['first']), ('2', v['second'])]:
                truth = observed((v['switch'], port), now) if history else sum(
                    framed(e['remaining']) for k, e in ledger.items()
                    if k[0] == v['switch'] and e['port'] == port)
                assert v['r'+suffix] == truth, (key, suffix, v['r'+suffix], truth)
            wanted = v['second'] if min(MAX64, v['q2']+v['r2']) < min(MAX64, v['q1']+v['r1']) else v['first']
            assert v['chosen'] == wanted
            category = policy_label(expected[flow]['tag'], intervention)
            payload = 65536 if category == 1 else 8192
            assert v['category'] == category and v['predicted'] == (0 if history else payload)
            pins[key] = wanted
            if not history:
                ledger[key] = {'port': wanted, 'remaining': payload, 'deadline': now+20000, 'next_seq': 0}
                peak = max(peak, len(ledger))
            decisions += 1
            positive += bool(v['r1'] or v['r2'])
            continue
        assert v['tag'] == policy_label(expected[flow]['tag'], intervention) and pins[key] == v['port']
        arrivals += 1
        payload = min(1000, expected[flow]['size']-v['seq'])
        assert payload > 0
        if history:
            port_key = (v['switch'], v['port'])
            memory[port_key] = (min(MAX64, observed(port_key, now)+payload+48), now)
        elif not count and key in ledger:
            entry = ledger[key]
            # No dropped/rejected packets and complete ordered source trace are
            # verified gates, rather than assuming a universal no-retransmit rule.
            assert v['seq'] == entry['next_seq']
            entry['next_seq'] += payload
            unique += payload
            entry['remaining'] = max(0, entry['remaining']-payload)
            if not entry['remaining']:
                del ledger[key]
    assert decisions == len(expected) == len(pins)
    assert states and sum(s['entries'] for s in states) == sum(s['fresh'] for s in states) == len(expected)
    assert sum(s['hits'] for s in states) == arrivals-len(expected)
    for s in states:
        assert s['conserved'] == 1 and s['ttl_ns'] == 20000 and s['max_entries'] == 65536 and s['max_ranges'] == 32
        assert s['capacity_fallbacks'] == s['range_fallbacks'] == s['duplicates'] == 0
        assert s['moe_payload'] == s['unified_payload'] == 8192 and s['bg_payload'] == 65536
    # C1 expiry is lazy at source decision/observation. PrintSummary checks
    # conservation but does not expire entries, unlike C3. Retained storage
    # after the last packet is therefore reported, not silently purged here.
    assert sum(s['expired'] for s in states) == expired
    assert sum(s['predictor_entries'] for s in states) == len(ledger)
    assert sum(s['unique_payload'] for s in states) == unique
    assert max(s['predictor_peak'] for s in states) == peak <= 65536
    if len(expected) == 104:
        assert positive > 0
        if not count and not history:
            assert unique > 0
    if count or history:
        assert unique == 0
    return {'source_arrivals_replayed': arrivals, 'source_choices_and_scores_replayed': decisions,
            'candidate_pairs_equal_accepted_QueuePin': True,
            'policy_categories': dict(Counter(policy_label(e['tag'], intervention) for e in expected.values())), 'positive_pressure_decisions': positive,
            'unique_payload_counter': unique, 'predictor_peak': peak,
            'expired_during_source_arrivals': expired, 'retained_predictor_entries_at_summary': len(ledger),
            'count_no_interval_work': count, 'recursive_observed_wire_memory': history,
            'conditions': 'One sourceToR, MTU1000, source framing48B, no drops/rejection and sequential live-predictor intervals; queue byte domain is separate'}


def ecmp_hash(v, seed):
    mask = (1 << 32)-1
    h = seed
    for k in (v['sip'], v['dip'], v['sport'] | (v['dport'] << 16)):
        k = (k*0xcc9e2d51) & mask
        k = ((k << 15) | (k >> 17)) & mask
        k = (k*0x1b873593) & mask
        h ^= k
        h = ((h << 13) | (h >> 19)) & mask
        h = (5*h+0xe6546b64) & mask
    h ^= 12
    h ^= h >> 16
    h = (h*0x85ebca6b) & mask
    h ^= h >> 13
    h = (h*0xc2b2ae35) & mask
    return h ^ (h >> 16)


def c3_replay(base, cell, expected):
    mode, intervention = cell['lb'], cell['ws30_tag_transform']
    assert mode == 'ws31-c3' and intervention in (1, 2)
    host, ports = topology(base/'config/topology.txt')
    side_rows = events(base, 'WS31_C3_ROUTE')
    sides = {(event_key(v), v['time_ns'], v['seq']): v for v in side_rows}
    assert len(sides) == len(side_rows)
    model, last = {}, defaultdict(dict)
    counts, activations, borrowers, maximum = (defaultdict(Counter) for _ in range(4))
    arrivals, seen_side = 0, set()
    hard = mode == 'ws31-c3-fixed'
    for line in ident.raw_paths(base)[1].open(encoding='utf-8'):
        if not line.startswith('WS30_ROUTE '):
            continue
        v = common.values(line)
        f = flow_key(v)
        assert f in expected and v['tag'] == policy_label(expected[f]['tag'], intervention)
        sw = v['switch']
        if sw != host[f[0]]:
            continue
        arrivals += 1
        key, now, seq = event_key(v), v['time_ns'], v['seq']
        size, tag = expected[f]['size'], policy_label(expected[f]['tag'], intervention)
        policy = (2 if size == 8192 else 1 if size == 8388608 else 0) if mode == 'ws31-c3-size' else (tag if tag in (1, 2) else 0)
        available = ports[sw]
        reserved = (len(available)+3)//4
        def owner(port): return 2 if port in available[:reserved] else 1
        def active(category): return category in (1, 2) and category in last[sw] and now-last[sw][category] < 20000
        fresh = key not in model
        if not fresh:
            policy = model[key]['category']
        if policy:
            if not active(policy):
                activations[sw][policy] += 1
                n = sum(e['borrowed'] and e['owner'] == policy and now-e['last'] < 20000
                        for k, e in model.items() if k[0] == sw)
                borrowers[sw][policy] += n
                maximum[sw][policy] = max(maximum[sw][policy], n)
            last[sw][policy] = now
        if fresh:
            side = sides[(key, now, seq)]
            restricted = bool(policy and len(available) > 1 and (hard or active(3-policy)))
            eligible = [p for p in available if not restricted or owner(p) == policy]
            assert side['category'] == policy and side['fresh'] == 1
            assert side['eligible'] == len(eligible) and side['restricted'] == int(restricted)
            assert side['first'] == eligible[ecmp_hash(v, sw) % len(eligible)]
            assert side['second'] == eligible[ecmp_hash(v, sw ^ 0x9e3779b9) % len(eligible)]
            chosen = side['second'] if side['q2'] < side['q1'] else side['first']
            assert chosen == side['chosen'] == v['port']
            model[key] = {'category': policy, 'owner': owner(chosen),
                          'borrowed': bool(policy and owner(chosen) != policy), 'port': chosen, 'last': now}
            counts[sw]['fresh'] += 1
            counts[sw]['restricted'] += restricted
            counts[sw]['borrowed'] += model[key]['borrowed']
        else:
            counts[sw]['hits'] += 1
        e = model[key]
        assert v['port'] == e['port']
        e['last'] = now
        residual = e['borrowed'] and active(e['owner'])
        if fresh or residual:
            item = (key, now, seq)
            seen_side.add(item)
            side = sides[item]
            assert side['fresh'] == int(fresh) and side['residual'] == int(residual)
            assert side['owner'] == e['owner'] and side['borrowed'] == int(e['borrowed'])
            assert side['category'] == e['category'] and side['chosen'] == e['port']
            assert side['wire_bytes'] == min(1000, size-seq)+48
        if residual:
            counts[sw]['residual_packets'] += 1
            counts[sw]['residual_wire_bytes'] += min(1000, size-seq)+48
    assert seen_side == sides.keys()
    states = events(base, 'WS31_C3_STATE')
    assert states and sum(s['entries'] for s in states) == sum(s['fresh'] for s in states) == len(model) == len(expected)
    assert sum(s['hits'] for s in states) == arrivals-len(expected)
    for s in states:
        sw = s['switch']
        assert s['conserved'] == s['pinning'] == 1 and s['activity_ns'] == 20000 and s['moe_lane_fraction'] == '1/4'
        for k in ('fresh', 'hits', 'restricted', 'borrowed', 'residual_packets', 'residual_wire_bytes'):
            assert s[k] == counts[sw][k]
        for category, name in ((1, 'bg'), (2, 'moe')):
            assert s[name+'_activations'] == activations[sw][category]
            assert s[name+'_borrowers_at_activation_sum'] == borrowers[sw][category]
            assert s[name+'_borrowers_at_activation_max'] == maximum[sw][category]
    totals = {k: sum(c[k] for c in counts.values()) for k in ('restricted', 'borrowed', 'residual_packets', 'residual_wire_bytes')}
    if intervention == 1:
        assert all(v == 0 for v in totals.values())
        assert all(not v for v in activations.values())
        assert {e['category'] for e in model.values()} == {0}
    else:
        assert {e['category'] for e in model.values()} == {1, 2}
        assert totals['restricted'] > 0
    return {'source_arrivals_replayed': arrivals, 'source_route_entries': len(model),
            'dedicated_events_replayed': len(sides), **totals,
            'policy_categories': dict(Counter(e['category'] for e in model.values())),
            'tag1_activations': sum(c[1] for c in activations.values()),
            'tag2_activations': sum(c[2] for c in activations.values()),
            'tag2_borrowers_at_activation_sum': sum(c[2] for c in borrowers.values())}



def verify(base, plan, candidates, reference=None):
    result = verify_common(base, plan)
    cell = next(c for c in plan['cells'] if c['id'] == result['id'])
    expected, _ = trace_rows(base/'config/traffic_trace.txt')
    if cell['lb'] == 'ws31-c1':
        result['mechanism_replay'] = c1_replay(base, cell, c1.candidate_reference(candidates))
    else:
        result['mechanism_replay'] = c3_replay(base, cell, expected)
    suffix = cell['id'].removeprefix('20261101-104000-ws31-c13tag-r1-')
    if suffix in plan['references']:
        assert reference is not None
        meta = json.loads((reference/'metadata.json').read_text(encoding='utf-8'))
        assert meta['experiment_id'] == plan['references'][suffix] and meta['status'] == 'SUCCEEDED'
        for rel in ('config/traffic_trace.txt', 'config/topology.txt'):
            assert digest(base/rel) == digest(reference/rel)
        fct, log = raw_paths(base)
        ref_fct, ref_log = raw_paths(reference)
        assert digest(fct) == digest(ref_fct)
        assert ident.ordered_hashes(log, True)['WS30_ROUTE'] == ident.ordered_hashes(ref_log, True)['WS30_ROUTE']
        if suffix == 'c1-remove':
            # category=0 is a checked policy result, not silently dropped.
            assert c1.source_decisions(base) == c1.source_decisions(reference)
        else:
            host, _ = topology(base/'config/topology.txt')
            keys = ('time_ns', 'switch', 'sip', 'dip', 'sport', 'dport', 'first', 'second', 'q1', 'q2', 'chosen')
            source = [{k:v[k] for k in keys} for v in events(base, 'WS31_C3_ROUTE') if v['fresh']]
            target = [{k:v[k] for k in keys} for v in events(reference, 'WS30_CHOICE') if v['switch'] == host[flow_key(v)[0]]]
            assert source == target
        result['regression'] = {'reference_id': meta['experiment_id'], 'full_fct_equal': True,
                                'ordered_ROUTE_equal': True, 'removed_ROUTE_fields': ['uid', 'tag'],
                                'required_source_projection_equal': True}
    result['status'] = 'PASS_C1_C3_LABEL_TECHNICAL_SCOPE'
    result['scope'] = 'Technical transformed labels and original identity only; delayed labels/lifecycle/independent effects pending'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--candidates', type=Path, required=True)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Refusing to overwrite main acceptance receipt'
    result = verify(args.results, json.loads(args.plan.read_text(encoding='utf-8')), args.candidates, args.reference)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'id': result['id'], 'replay': result['mechanism_replay'], 'regression': result.get('regression')}))
