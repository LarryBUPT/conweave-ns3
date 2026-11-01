"""Main independent C1 control replay, retaining frozen technical-only scope."""
import argparse
from collections import Counter, defaultdict
import copy
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ws31_main_common', HERE/'verify_dynamic_raw_r1.py')
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
spec = importlib.util.spec_from_file_location('ws31_main_identity', HERE/'verify_c2_label_raw_r1.py')
identity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(identity)
MAX64 = (1 << 64)-1


def framed(payload):
    return min(MAX64, payload+((payload+999)//1000)*48)


def record_key(v):
    return tuple(v[k] for k in ('switch', 'sip', 'dip', 'sport', 'dport'))


def topology_hosts(path):
    lines = path.read_text(encoding='ascii').splitlines()
    switches = set(map(int, lines[1].split()))
    result = {}
    for line in lines[2:2+int(lines[0].split()[2])]:
        a, b = map(int, line.split()[:2])
        if a not in switches:
            result[a] = b
        if b not in switches:
            result[b] = a
    return result


def source_decisions(base, drop_category=False):
    result = []
    for line in identity.raw_paths(base)[1].open(encoding='utf-8'):
        if line.startswith('WS31_C1_CHOICE '):
            v = identity.fields(line)
            if drop_category:
                del v['category']
            result.append(v)
    return result


def candidate_reference(base):
    pairs = {}
    for line in identity.raw_paths(base)[1].open(encoding='utf-8'):
        if line.startswith('WS30_CHOICE '):
            v = identity.fields(line)
            key = record_key(v)
            assert key not in pairs
            pairs[key] = (v['first'], v['second'])
    return pairs


def replay(base, cell, pairs):
    expected, _ = identity.trace_rows(base/'config/traffic_trace.txt')
    host_tor = topology_hosts(base/'config/topology.txt')
    # Both frozen inputs have a single source ToR; explicit gate for peak scope.
    assert len({host_tor[k[0]] for k in expected}) == 1
    mode = cell['lb']
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
            assert prefix == 'WS30_ROUTE' and v['tag'] == expected[flow]['tag']
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
            tag, size = expected[flow]['tag'], expected[flow]['size']
            category = tag if mode in ('ws31-c1', 'ws31-c1-count') else (
                1 if size == 8388608 else 2 if size == 8192 else 0) if mode == 'ws31-c1-size' else 0
            payload = 65536 if category == 1 else 8192
            assert v['category'] == category and v['predicted'] == (0 if history else payload)
            pins[key] = wanted
            if not history:
                ledger[key] = {'port': wanted, 'remaining': payload, 'deadline': now+20000, 'next_seq': 0}
                peak = max(peak, len(ledger))
            decisions += 1
            positive += bool(v['r1'] or v['r2'])
            continue
        assert v['tag'] == expected[flow]['tag'] and pins[key] == v['port']
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
            'candidate_pairs_equal_accepted_QueuePin': True, 'positive_pressure_decisions': positive,
            'unique_payload_counter': unique, 'predictor_peak': peak,
            'expired_during_source_arrivals': expired, 'retained_predictor_entries_at_summary': len(ledger),
            'count_no_interval_work': count, 'recursive_observed_wire_memory': history,
            'conditions': 'One sourceToR, MTU1000, source framing48B, no drops/rejection and sequential live-predictor intervals; queue byte domain is separate'}


def verify(base, plan, pairs, reference=None):
    meta = json.loads((base/'metadata.json').read_text(encoding='utf-8'))
    cell = next(c for c in plan['cells'] if c['id'] == meta['experiment_id'])
    # Reuse the already checked common all-input/queue/path verifier. Its legacy
    # expected-hash lookup uses a fixed key name; only that lookup is adapted to
    # this cell's actual file. No input/config or on-disk plan is changed.
    adapted = copy.deepcopy(plan)
    adapted['flow_count'], adapted['payload_bytes'] = cell['flow_count'], cell['payload_bytes']
    adapted['common']['flow_file'] = cell['flow_file']
    adapted['inputs']['config/ws31_correctness_r1.txt'] = plan['inputs']['config/'+cell['flow_file']]
    result = common.verify(base, adapted)
    result['scope'] = 'Main independent C1 matched-control/unknown raw verification; technical only'
    result['inputs'] = {'config/'+cell['flow_file']: plan['inputs']['config/'+cell['flow_file']],
                        'config/leaf_spine_128_100G_OS2.txt': plan['inputs']['config/leaf_spine_128_100G_OS2.txt']}
    result['mechanism_replay'] = replay(base, cell, pairs)
    suffix = cell['id'].removeprefix('20261101-083000-ws31-c1ctrl-r1-')
    if suffix in ('size', 'unknown-unified'):
        assert reference is not None
        ref_meta = json.loads((reference/'metadata.json').read_text(encoding='utf-8'))
        assert ref_meta['experiment_id'] == plan['references'][suffix] and ref_meta['status'] == 'SUCCEEDED'
        fct, log = identity.raw_paths(base)
        ref_fct, ref_log = identity.raw_paths(reference)
        assert common.digest(fct) == common.digest(ref_fct)
        assert identity.ordered_hashes(log)['WS30_ROUTE'] == identity.ordered_hashes(ref_log)['WS30_ROUTE']
        drop = suffix == 'unknown-unified'
        assert source_decisions(base, drop) == source_decisions(reference, drop)
        result['regression'] = {'reference_id': ref_meta['experiment_id'], 'full_fct_equal': True,
                                'ordered_ROUTE_remove_uid_equal': True, 'source_decisions_equal': True,
                                'removed_source_fields': ['category'] if drop else []}
    result['status'] = 'PASS_FOR_C1_CONTROL_TECHNICAL_SCOPE'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--candidates', type=Path, required=True, help='Previously accepted QueuePin results')
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Refusing to overwrite main acceptance receipt'
    result = verify(args.results, json.loads(args.plan.read_text(encoding='utf-8')),
                    candidate_reference(args.candidates), args.reference)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'id': result['id'], 'replay': result['mechanism_replay']}))
