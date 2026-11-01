"""Main replay of production adapter fixture logs, independent of executor verdicts."""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('adapter_previous_hashes', HERE/'verify_c13_label_raw_r1.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
SIP, DIP, DPORT, OVERHEAD = 0x0b000001, 0x0b000101, 100, 56


def rows(path):
    out = []
    for line in path.read_text(encoding='utf-8').splitlines():
        parts = line.split()
        if not parts or not parts[0].startswith(('WS31_', 'WS30V13_CACHE_RESET')):
            continue
        if parts[0] in ('WS31_C2_BOUNDARY','WS31_C2_BOUNDARY_SUMMARY',
                        'WS31_SWITCH_BOUNDARY','WS31_SWITCH_BOUNDARY_SUMMARY'):
            assert parts[1] == 'PASS', 'Fixture completion marker is not PASS'
        values = {}
        for part in parts[1:]:
            if '=' in part:
                key, value = part.split('=', 1)
                assert key not in values
                values[key] = int(value) if value.isdecimal() else value
        out.append((parts[0], values, parts))
    return out


def check(v, expected):
    for key, wanted in expected.items():
        assert v[key] == wanted, (key, v[key], wanted, v.get('case'))


def key(v):
    check(v, {'sip': SIP, 'dip': DIP, 'dport': DPORT})
    return SIP, DIP, v['sport'], DPORT


def hash_values(k):
    v = dict(zip(('sip', 'dip', 'sport', 'dport'), k))
    return prior.ecmp_hash(v, 7), prior.ecmp_hash(v, 7 ^ 0x9e3779b9)


def wire(remaining):
    return remaining + ((remaining+999)//1000)*OVERHEAD


def start_wait(sport, tag=2):
    return prior.ident.hash_wait((0, 1, sport, DPORT), tag)


def verify_c2(log):
    allrows = rows(log)
    summaries = [v for p,v,_ in allrows if p == 'WS31_C2_BOUNDARY']
    phases = ('before','same-control-first','same-launch-first','after','zero')
    wanted = [(kind, phase) for kind in ('stop','dispose') for phase in phases]
    assert [(v['kind'],v['phase']) for v in summaries] == wanted
    sport = next(s for s in range(1,65536) if start_wait(s)>1)
    timing = defaultdict(lambda: defaultdict(list))
    for p,v,_ in allrows:
        if p in ('WS31_C2_DEMAND','WS31_C2_LAUNCH','WS31_C2_CANCEL'):
            timing[v['flow_id']][p].append(v)
        assert p != 'WS31_C2_FINISH', 'Transport substitute must never synthesize completion'
    assert set(timing) == set(range(10))
    for i,v in enumerate(summaries):
        phase = phases.index(v['phase'])
        delay = 0 if phase == 4 else start_wait(sport)
        cancelled = int(phase <= 1)
        launched = 1-cancelled
        control = 10+delay+(-1 if phase == 0 else 1 if phase == 3 else 0)
        check(v, {'sip':SIP, 'dip':DIP, 'sport':sport, 'dport':DPORT,
                  'tag':1 if phase == 4 else 2, 'size':8192, 'demand_ns':10, 'wait_ns':delay,
                  'control_ns':control, 'launched':launched, 'cancelled':cancelled,
                  'launch_ns':10+delay if launched else 0, 'dispatch_demand_ns':10 if launched else 0,
                  'calls':launched, 'demanded':1, 'demand_bytes':8192,
                  'launch_bytes':8192*launched, 'cancel_bytes':8192*cancelled,
                  'waited':int(bool(delay and launched)), 'delay_sum_ns':delay*launched,
                  'delay_max_ns':delay*launched, 'finished':0, 'pending':0, 'transport':'fixture'})
        if phase == 1:
            assert 0 < v['control_uid'] < v['launch_uid']
        elif phase == 2:
            assert 0 < v['launch_uid'] < v['control_uid']
        if phase == 4:
            assert v['launch_uid'] == 0
        t = timing[i]
        assert len(t['WS31_C2_DEMAND']) == 1
        d = t['WS31_C2_DEMAND'][0]
        check(d, {'demand_ns':10,'size':8192,'tag':v['tag'],'delay_ns':delay,
                  'policy_tag':v['tag'],'tag_transform':0})
        assert len(t['WS31_C2_LAUNCH']) == launched and len(t['WS31_C2_CANCEL']) == cancelled
        if launched:
            check(t['WS31_C2_LAUNCH'][0], {'demand_ns':10,'launch_ns':10+delay,'wait_ns':delay,'size':8192})
        else:
            check(t['WS31_C2_CANCEL'][0], {'demand_ns':10,'time_ns':control,'size':8192})
    ending = [v for p,v,_ in allrows if p == 'WS31_C2_BOUNDARY_SUMMARY']
    assert len(ending) == 1
    check(ending[0], {'cases':10,'network_runs':0,'completions':0})
    return {'cases':10,'actual_event_uid_orders':4,'cancelled':4,'transport_dispatches':6,
            'demand_requests':10,'demand_bytes':81920,'real_QPs':0,'finished':0,
            'fixed_sport':sport,'positive_wait_ns':start_wait(sport)}


def merged(ranges, lo, hi):
    result = []
    for a,b in sorted(ranges+[(lo,hi)]):
        if result and a <= result[-1][1]:
            result[-1] = (result[-1][0],max(result[-1][1],b))
        else:
            result.append((a,b))
    return result


C1_SHAPES = {
    'c1-ranges':[(0,1000,0,100,2),(1,1000,0,100,1),(2,1000,300,100,1),(3,1000,50,300,1),(4,1000,400,100,1)],
    'c1-expiry-reset':[(0,1000,0,1000,1),(19999,1000,0,1000,2),(20000,1000,1000,500,2),(20001,1000,1500,500,1),(20002,1000,0,100,2)],
    'c1-capacity':[(0,1000,0,100,2),(1,1001,0,100,2),(2,1001,100,100,1),(3,1001,0,100,2)],
    'c1-range-limit':[(0,1000,0,100,2),(1,1000,200,100,1),(2,1000,100,100,2)],
    'c1-wrap':[(0,1000,0,100,2),(1,1000,0xfffffff0,32,1),(2,1000,100,100,2)]}


def verify_c1(log):
    raw = rows(log)
    packets = [v for p,v,_ in raw if p == 'WS31_SWITCH_BOUNDARY_PACKET']
    names = list(C1_SHAPES)
    assert [v['case'] for p,v,_ in raw if p == 'WS31_SWITCH_BOUNDARY'] == names
    bycase = {name:[(v['time_ns'],v['sport'],v['seq'],v['payload'],v['tag']) for v in packets if v['case']==name] for name in names}
    assert bycase == C1_SHAPES
    assert len({v['uid'] for v in packets}) == len(packets) == 20
    pending, cache, budget, counts, current = [], {}, {}, Counter(), None
    reset_counts = Counter()
    for p,v,_ in raw:
        if p == 'WS31_C1_CHOICE':
            pending.append(v)
            continue
        if p not in ('WS31_SWITCH_BOUNDARY_PACKET','WS31_SWITCH_BOUNDARY_RESET'):
            continue
        name = v['case']
        if name != current:
            cache, budget, counts, current = {}, {}, Counter(), name
        k = key(v)
        if p.endswith('_RESET'):
            check(v, {'pairs_before':len(cache),'budget_before':len(budget),'quota_before':0,'quota_after':0,'conserved':1})
            assert k in cache
            del cache[k]
            budget.pop(k, None)
            check(v, {'pairs_after':len(cache),'budget_after':len(budget)})
            reset_counts[name] += 1
            continue
        now = v['time_ns']
        for dead in [k for k,e in budget.items() if e['end']<=now]:
            del budget[dead]
            counts['expired'] += 1
        pressure = lambda port:sum(wire(e['remaining']) for e in budget.values() if e['port']==port)
        fresh = k not in cache
        if fresh:
            h1,h2 = hash_values(k)
            first,second = h1%8,h2%8
            r1,r2 = pressure(first),pressure(second)
            chosen = second if r2 < r1 else first
            assert len(pending) == 1
            choice = pending.pop()
            predicted = 65536 if v['tag']==1 else 8192
            check(choice, {'time_ns':now,'sip':SIP,'dip':DIP,'sport':v['sport'],'dport':DPORT,
                           'first':first,'second':second,'q1':0,'q2':0,'r1':r1,'r2':r2,
                           'chosen':chosen,'category':v['tag'],'predicted':predicted})
            cache[k] = chosen
            counts['fresh'] += 1
            if name == 'c1-capacity' and len(budget) >= 1:
                counts['capacity_fallback'] += 1
            else:
                budget[k] = {'port':chosen,'remaining':predicted,'ranges':[],'end':now+20000}
        else:
            assert not pending
            counts['hits'] += 1
        if k in budget:
            e = budget[k]
            joined = merged(e['ranges'],v['seq'],v['seq']+v['payload'])
            novel = sum(b-a for a,b in joined)-sum(b-a for a,b in e['ranges'])
            if v['seq']+v['payload'] > 1<<32 or (name in ('c1-range-limit','c1-wrap') and len(joined)>1):
                del budget[k]
                counts['range_fallback'] += 1
            elif not novel:
                counts['duplicate'] += 1
            else:
                counts['unique'] += novel
                e['remaining'] = max(0,e['remaining']-novel)
                e['ranges'] = joined
                if not e['remaining']:
                    del budget[k]
        chosen = cache[k]
        check(v, {'mode':36,'wire':v['payload']+OVERHEAD,'present':1,'chosen':chosen,
                  'pairs':len(cache),'budget_entries':len(budget),'pressure':pressure(chosen),
                  'queue_bytes':5000 if name=='c1-ranges' and now>0 else 0,
                  'unique':counts['unique'],'duplicate':counts['duplicate'],'expired':counts['expired'],
                  'capacity_fallback':counts['capacity_fallback'],'range_fallback':counts['range_fallback'],
                  'quota_entries':0,'fresh':0,'hits':0,'conserved':1})
    assert not pending and reset_counts == {'c1-expiry-reset':1,'c1-capacity':2}
    ending = [v for p,v,_ in raw if p == 'WS31_SWITCH_BOUNDARY_SUMMARY']
    assert len(ending)==1
    check(ending[0], {'candidate':'c1','cases':5,'network_runs':0,'endpoint_generations':0})
    return {'cases':5,'actual_packets_replayed':20,'production_first_choices':8,'production_resets':3,
            'real_queue_fill_bytes':5000,'packet_framing_overhead':OVERHEAD}


def verify_c3(log):
    raw = rows(log)
    packets = [v for p,v,_ in raw if p == 'WS31_SWITCH_BOUNDARY_PACKET']
    borrower = next(s for s in range(1,65536) if hash_values((SIP,DIP,s,DPORT))[0]%8<2)
    owner = borrower+1 if borrower<65535 else 1
    shapes = {'c3-borrow-expiry-reset':[(0,borrower,0,1,1),(100,borrower,100,2,1),(200,owner,0,2,1),(201,borrower,200,0,0),(20202,borrower,300,2,1),(20203,borrower,0,2,1)],
              'c3-unknown-reset':[(0,1000,0,0,0),(1,1000,100,1,1),(2,1000,0,1,1)]}
    assert {n:[(v['time_ns'],v['sport'],v['seq'],v['tag'],v['present']) for v in packets if v['case']==n] for n in shapes} == shapes
    assert len({v['uid'] for v in packets}) == len(packets) == 9
    assert [v['case'] for p,v,_ in raw if p=='WS31_SWITCH_BOUNDARY'] == list(shapes)
    pending, entries, last, counts, current = [], {}, {}, Counter(), None
    resets = Counter()
    idle_times = []
    def active(cat, now):
        return int(cat in last and 0<=now-last[cat]<20000)
    def live2():
        return sum(e['live'] and e['borrowed'] and e['owner']==2 for e in entries.values())
    for p,v,_ in raw:
        if p == 'WS31_C3_ROUTE':
            pending.append(v)
            continue
        if p not in ('WS31_SWITCH_BOUNDARY_PACKET','WS31_SWITCH_BOUNDARY_RESET','WS31_SWITCH_BOUNDARY_IDLE'):
            continue
        name, now = v['case'],v['time_ns']
        if name != current:
            entries, last, counts, current = {}, {}, Counter(), name
        if p.endswith('_IDLE'):
            check(v, {'quota_entries':len(entries),'live_owner2':live2(),'active1':active(1,now),
                      'active2':active(2,now),'conserved':1,'observer_expires':0})
            idle_times.append(now)
            continue
        k = key(v)
        if p.endswith('_RESET'):
            check(v, {'pairs_before':0,'pairs_after':0,'budget_before':0,'budget_after':0,'quota_before':len(entries),'conserved':1})
            assert k in entries
            del entries[k]
            check(v, {'quota_after':len(entries)})
            resets[name] += 1
            continue
        for e in entries.values():
            if e['live'] and e['end']<=now:
                e['live'] = False
        fresh = k not in entries
        cat = (v['tag'] if v['present'] and v['tag'] in (1,2) else 0) if fresh else entries[k]['category']
        if cat:
            if not active(cat,now):
                counts['activation'+str(cat)] += 1
            last[cat] = now
        if fresh:
            restricted = int(bool(cat and active(3-cat,now)))
            eligible = [port for port in range(8) if not restricted or (2 if port<2 else 1)==cat]
            h1,h2 = hash_values(k)
            first,second = eligible[h1%len(eligible)],eligible[h2%len(eligible)]
            chosen = first
            own = 2 if chosen<2 else 1
            borrowed = int(bool(cat and own!=cat))
            e = {'category':cat,'port':chosen,'owner':own,'borrowed':borrowed,'live':False}
            entries[k] = e
            counts['fresh'] += 1
            counts['restricted'] += restricted
            counts['borrowed'] += borrowed
        else:
            e = entries[k]
            counts['hits'] += 1
        e['end'],e['live'] = now+20000,True
        residual = int(bool(e['borrowed'] and active(e['owner'],now)))
        counts['residual'] += residual
        counts['residual_bytes'] += residual*v['wire']
        if fresh or residual:
            assert len(pending) == 1
            side = pending.pop()
            check(side, {'time_ns':now,'sip':SIP,'dip':DIP,'sport':v['sport'],'dport':DPORT,
                         'seq':v['seq'],'category':cat,'fresh':int(fresh),'chosen':e['port'],
                         'owner':e['owner'],'borrowed':e['borrowed'],'residual':residual,'wire_bytes':v['wire']})
            if fresh:
                check(side, {'restricted':restricted,'eligible':len(eligible),'first':first,'second':second,'q1':0,'q2':0})
        else:
            assert not pending
        check(v, {'mode':47,'payload':100,'wire':100+OVERHEAD,'chosen':e['port'],'pairs':0,
                  'budget_entries':0,'pressure':0,'queue_bytes':0,'unique':0,'expired':0,
                  'quota_entries':len(entries),'fresh':counts['fresh'],'hits':counts['hits'],
                  'restricted':counts['restricted'],'borrowed':counts['borrowed'],'live_owner2':live2(),
                  'residual':counts['residual'],'residual_bytes':counts['residual_bytes'],
                  'active1':active(1,now),'active2':active(2,now),
                  'activation1':counts['activation1'],'activation2':counts['activation2'],'conserved':1})
    assert not pending and resets == {'c3-borrow-expiry-reset':2,'c3-unknown-reset':1}
    assert idle_times == [20199,20200,20201]
    ending = [v for p,v,_ in raw if p == 'WS31_SWITCH_BOUNDARY_SUMMARY']
    assert len(ending)==1
    check(ending[0], {'candidate':'c3','cases':2,'network_runs':0,'endpoint_generations':0})
    return {'cases':2,'actual_packets_replayed':9,'production_resets':3,'pure_idle_boundaries':3,
            'fixed_borrower_sport':borrower,'residual_packets':1,'residual_wire_bytes':100+OVERHEAD,
            'endpoint_generations':0,'packet_framing_overhead':OVERHEAD}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate',choices=('c1','c2','c3'))
    parser.add_argument('log',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Refusing to overwrite a main acceptance'
    result = globals()['verify_'+args.candidate](args.log)
    result.update({'status':'MAIN_PASS_ADAPTER_FIXTURE_RAW_REPLAY','candidate':args.candidate,
                   'log_sha256':hashlib.sha256(args.log.read_bytes()).hexdigest(),
                   'scope':'Actual adapter operations with test packets/transport seam; not real endpoint lifecycle or network efficacy'})
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
