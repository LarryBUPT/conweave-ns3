"""Main independent C2/C3 matched-control and unknown raw replay."""
import argparse
from collections import Counter, defaultdict
import copy
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

common = module('ws31_c23_common', 'verify_dynamic_raw_r1.py')
ident = module('ws31_c23_identity', 'verify_c2_label_raw_r1.py')
MAX64 = (1 << 64)-1


def event_key(v):
    return tuple(v[k] for k in ('switch', 'sip', 'dip', 'sport', 'dport'))


def flow_key(v):
    return ((v['sip'] >> 8) & 65535, (v['dip'] >> 8) & 65535, v['sport'], v['dport'])


def topology(path):
    rows = path.read_text(encoding='ascii').splitlines()
    switches = set(map(int, rows[1].split()))
    device, ports, host = Counter(), defaultdict(list), {}
    for line in rows[2:2+int(rows[0].split()[2])]:
        a, b = map(int, line.split()[:2])
        device[a] += 1
        device[b] += 1
        if a not in switches:
            host[a] = b
        if b not in switches:
            host[b] = a
        if a in switches and b in switches:
            ports[a].append(device[a])
            ports[b].append(device[b])
    return host, {sw: sorted(v) for sw, v in ports.items()}


def events(base, prefix):
    return [common.values(line) for line in ident.raw_paths(base)[1].open(encoding='utf-8')
            if line.startswith(prefix+' ')]


def c2_replay(base, mode, expected, by_id):
    demands, launches, finishes = (events(base, p) for p in
                                  ('WS31_C2_DEMAND', 'WS31_C2_LAUNCH', 'WS31_C2_FINISH'))
    tables = []
    for rows in (demands, launches, finishes):
        table = {v['flow_id']: v for v in rows}
        assert len(table) == len(rows) and table.keys() == by_id.keys()
        tables.append(table)
    waits, by_tag = [], defaultdict(list)
    for i, key in by_id.items():
        e = expected[key]
        d, launch, finish = (t[i] for t in tables)
        eligible = mode == 'ws31-c2-unified' or e['size'] == 8192
        wait = ident.hash_wait(key, 2) if eligible else 0
        assert d['tag'] == d['policy_tag'] == e['tag'] and d['tag_transform'] == 0
        assert d['delay_ns'] == launch['wait_ns'] == finish['wait_ns'] == wait
        assert d['demand_ns'] == launch['demand_ns'] == finish['demand_ns'] == e['demand_ns']
        assert launch['launch_ns'] == finish['launch_ns'] == e['demand_ns']+wait <= finish['finish_ns']
        assert finish['fct_ns'] == finish['finish_ns']-e['demand_ns']
        assert d['size'] == launch['size'] == finish['size'] == e['size']
        waits.append(wait)
        by_tag[e['tag']].append(wait)
    states = events(base, 'WS31_C2_STATE')
    assert len(states) == 1
    s = states[0]
    assert s['frozen_max_ns'] == 500
    for k in ('demanded', 'launched', 'finished'):
        assert s[k] == len(expected)
    for k in ('demand_bytes', 'launch_bytes', 'finish_bytes'):
        assert s[k] == sum(e['size'] for e in expected.values())
    for k in ('pending', 'unfinished', 'cancelled', 'cancel_bytes'):
        assert s[k] == 0
    assert s['waited'] == sum(w > 0 for w in waits)
    assert s['delay_sum_ns'] == sum(waits) and s['delay_max_ns'] == max(waits)
    assert any(by_tag[2]) and (any(by_tag[1]) if mode == 'ws31-c2-unified' else not any(by_tag[1]))
    return {'requests_exact_hash_timing_replayed': len(waits), 'positive_waits': sum(w > 0 for w in waits),
            'wait_sum_ns': sum(waits), 'wait_max_ns': max(waits),
            'positive_waits_by_original_tag': {tag: sum(w > 0 for w in v) for tag, v in by_tag.items()}}


def c3_replay(base, mode, expected):
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
        assert f in expected and v['tag'] == expected[f]['tag']
        sw = v['switch']
        if sw != host[f[0]]:
            continue
        arrivals += 1
        key, now, seq = event_key(v), v['time_ns'], v['seq']
        size, tag = expected[f]['size'], expected[f]['tag']
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
            assert side['first'] in eligible and side['second'] in eligible
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
    if hard:
        assert totals['restricted'] == len(expected) and totals['borrowed'] == totals['residual_packets'] == totals['residual_wire_bytes'] == 0
    elif mode == 'ws31-c3-size':
        assert totals['restricted'] > 0 and totals['borrowed'] > 0 and totals['residual_packets'] > 0
    else:
        assert len(expected) == 6 and all(v == 0 for v in totals.values())
        assert all(not v for v in activations.values())
    return {'source_arrivals_replayed': arrivals, 'source_route_entries': len(model),
            'dedicated_events_replayed': len(sides), **totals,
            'tag2_activations': sum(c[2] for c in activations.values()),
            'tag2_borrowers_at_activation_sum': sum(c[2] for c in borrowers.values())}


def verify(base, plan, reference=None):
    meta = json.loads((base/'metadata.json').read_text(encoding='utf-8'))
    cell = next(c for c in plan['cells'] if c['id'] == meta['experiment_id'])
    adapted = copy.deepcopy(plan)
    adapted['flow_count'], adapted['payload_bytes'] = cell['flow_count'], cell['payload_bytes']
    adapted['common']['flow_file'] = cell['flow_file']
    adapted['inputs']['config/ws31_correctness_r1.txt'] = plan['inputs']['config/'+cell['flow_file']]
    result = common.verify(base, adapted)
    expected, by_id = ident.trace_rows(base/'config/traffic_trace.txt')
    result['scope'] = 'Main independent C2/C3 matched-control raw replay; technical only'
    result['inputs'] = {'config/'+cell['flow_file']: plan['inputs']['config/'+cell['flow_file']]}
    mode = cell['lb']
    result['control_replay'] = c2_replay(base, mode, expected, by_id) if mode.startswith('ws31-c2') else c3_replay(base, mode, expected)
    for v in events(base, 'WS30_CHOICE'):
        assert v['tag'] == 0
    for line in ident.raw_paths(base)[1].open(encoding='utf-8'):
        if line.startswith('WS30_ROUTE '):
            v = common.values(line)
            assert v['tag'] == expected[flow_key(v)]['tag']
    q = {k: int(v) for k, v in result['summaries']['WS30_QUEUE'].items()}
    assert q['enqueued'] == q['dequeued']+q['current']+q['dropped']
    suffix = cell['id'].removeprefix('20261101-094000-ws31-c23ctrl-r1-')
    if suffix in plan['references']:
        assert reference is not None
        ref_meta = json.loads((reference/'metadata.json').read_text(encoding='utf-8'))
        assert ref_meta['experiment_id'] == plan['references'][suffix] and ref_meta['status'] == 'SUCCEEDED'
        fct, log = ident.raw_paths(base)
        ref_fct, ref_log = ident.raw_paths(reference)
        assert common.digest(fct) == common.digest(ref_fct)
        a, b = ident.ordered_hashes(log), ident.ordered_hashes(ref_log)
        assert a['WS30_ROUTE'] == b['WS30_ROUTE']
        if suffix == 'c2-size':
            assert a['WS30_CHOICE'] == b['WS30_CHOICE']
            for prefix in ('WS31_C2_DEMAND', 'WS31_C2_LAUNCH', 'WS31_C2_FINISH'):
                assert events(base, prefix) == events(reference, prefix)
        elif suffix == 'c3-size':
            assert events(base, 'WS31_C3_ROUTE') == events(reference, 'WS31_C3_ROUTE')
            assert events(base, 'WS31_C3_STATE') == events(reference, 'WS31_C3_STATE')
        else:
            host, _ = topology(base/'config/topology.txt')
            keys = ('time_ns', 'switch', 'sip', 'dip', 'sport', 'dport', 'first', 'second', 'q1', 'q2', 'chosen')
            source = [{k: v[k] for k in keys} for v in events(base, 'WS31_C3_ROUTE') if v['fresh']]
            target = [{k: v[k] for k in keys} for v in events(reference, 'WS30_CHOICE')
                      if v['switch'] == host[flow_key(v)[0]]]
            assert source == target
        result['regression'] = {'reference_id': ref_meta['experiment_id'], 'full_fct_equal': True,
                                'ordered_ROUTE_remove_uid_equal': True, 'required_auxiliary_events_equal': True}
    result['status'] = 'PASS_C2_C3_CONTROL_TECHNICAL_SCOPE'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Refusing to overwrite main acceptance'
    result = verify(args.results, json.loads(args.plan.read_text(encoding='utf-8')), args.reference)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'id': result['id'], 'replay': result['control_replay'], 'regression': result.get('regression')}))
