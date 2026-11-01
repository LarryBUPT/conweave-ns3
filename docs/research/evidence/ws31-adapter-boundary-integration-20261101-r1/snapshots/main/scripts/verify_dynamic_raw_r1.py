"""Main all-input/ordered-path and mechanism replay for dynamic r1."""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def verify(base, plan):
    meta = json.loads((base/'metadata.json').read_text(encoding='utf-8'))
    assert meta['status'] == 'SUCCEEDED' and meta['git_commit'] == plan['source_sha']
    cell = next(c for c in plan['cells'] if c['id'] == meta['experiment_id'])
    assert meta['algorithm'] == cell['lb']
    for key, value in plan['common'].items():
        if key != 'max_concurrent':
            assert meta['parameters'][key] == value, key
    assert meta['concurrency_cap'] == 1
    for key in ['ws30_composition','ws30_lifecycle','ws30_tag_transform','ws30_life_profile']:
        assert meta['parameters'].get(key, 0) == 0, key
    trace, topo = base/'config/traffic_trace.txt', base/'config/topology.txt'
    for path, name in [(trace,'config/ws31_correctness_r1.txt'),(topo,'config/leaf_spine_128_100G_OS2.txt')]:
        assert digest(path) == plan['inputs'][name]
    config = dict((row.split()[0], row.split()[1:]) for row in
                  (base/'config/config.txt').read_text().splitlines() if row.strip())
    mtu = int(config['PACKET_PAYLOAD_SIZE'][0])
    expected, by_index = {}, {}
    sports, dports = defaultdict(lambda:10000), defaultdict(lambda:100)
    rows = trace.read_text().splitlines()
    assert len(rows)-1 == int(rows[0]) == plan['flow_count']
    for index, line in enumerate(rows[1:]):
        src,dst,pg,size,start,tag = line.split()
        src,dst,size,tag = map(int,(src,dst,size,tag))
        key = (src,dst,sports[src],dports[dst])
        expected[key] = (size,int(Fraction.from_float(float(start))*10**9),tag,index)
        by_index[index] = key
        sports[src] += 1; dports[dst] += 1
    fcts, logs = list((base/'raw').glob('*/*_out_fct.txt')), list((base/'raw').glob('*/config.log'))
    assert len(fcts) == len(logs) == 1
    completed = {}
    for line in fcts[0].read_text().splitlines():
        row = list(map(int,line.split())); assert len(row) == 8
        key = tuple(row[:4]); assert key in expected and key not in completed
        assert (row[4],row[5]) == expected[key][:2] and row[6] >= 0 and row[7] > 0
        completed[key] = row
    assert set(completed) == set(expected)
    assert sum(v[4] for v in completed.values()) == plan['payload_bytes']
    lines = topo.read_text().splitlines(); link_count = int(lines[0].split()[2])
    switches = set(map(int,lines[1].split())); host_tor = {}
    for line in lines[2:2+link_count]:
        a,b = map(int,line.split()[:2])
        if a not in switches and b in switches: host_tor[a] = b
        if b not in switches and a in switches: host_tor[b] = a
    counts = Counter(); hashes = {p:hashlib.sha256() for p in ['WS30_CHOICE','WS30_ROUTE']}
    summaries = {}; intervals = defaultdict(list); source_tags = {}; qp_ports = {}; c2 = {}
    previous_time = -1
    with logs[0].open(encoding='utf-8') as handle:
        for line in handle:
            assert 'WS30_OBSERVATION_OVERFLOW' not in line
            prefix = line.split(' ',1)[0].strip()
            if prefix not in ['WS30_CHOICE','WS30_ROUTE','WS30_QUEUE','WS30_PATH','WS30_QP',
                              'WS31_C2_FINISH','WS31_C2_STATE']:
                continue
            counts[prefix] += 1
            fields = dict(t.split('=',1) for t in line.split()[1:] if '=' in t)
            if prefix in hashes:
                normalized = ' '.join(t for t in line.split() if not t.startswith('uid='))+'\n'
                hashes[prefix].update(normalized.encode())
                now = int(fields['time_ns']); assert now >= previous_time; previous_time = now
            if prefix in ['WS30_QUEUE','WS30_PATH','WS31_C2_STATE']: summaries[prefix] = fields
            if prefix == 'WS31_C2_FINISH':
                values = {k:int(v) for k,v in fields.items()}; i = values['flow_id']
                assert i not in c2 and i in by_index
                raw = completed[by_index[i]]
                assert values['demand_ns'] == raw[5] and values['launch_ns'] >= raw[5]
                assert values['wait_ns'] == values['launch_ns']-values['demand_ns']
                assert 0 <= values['wait_ns'] <= 500 and values['finish_ns'] == raw[5]+raw[6]
                assert values['fct_ns'] == raw[6] and values['size'] == raw[4]
                c2[i] = values
            if prefix == 'WS30_ROUTE':
                src = (int(fields['sip'])>>8)&65535; dst = (int(fields['dip'])>>8)&65535
                key = (src,dst,int(fields['sport']),int(fields['dport'])); assert key in expected
                switch, port = int(fields['switch']), int(fields['port'])
                old = qp_ports.setdefault((switch,key),port); assert old == port
                if switch != host_tor[src]: continue
                size,_,tag,_ = expected[key]; seq = int(fields['seq']); assert 0 <= seq < size
                intervals[key].append((seq,seq+min(mtu,size-seq)))
                source_tags.setdefault(key,int(fields['tag'])); assert source_tags[key] == tag
    unique_bytes = 0
    for key,e in expected.items():
        total = 0; lo = hi = None
        for a,b in sorted(intervals[key]):
            if lo is None: lo,hi = a,b
            elif a <= hi: hi = max(hi,b)
            else: total += hi-lo; lo,hi = a,b
        if lo is not None: total += hi-lo
        assert total == e[0], key
        unique_bytes += total
    assert counts['WS30_ROUTE'] < 1000000
    assert counts['WS30_QUEUE'] == counts['WS30_PATH'] == 1
    assert counts['WS30_ROUTE'] == int(summaries['WS30_PATH']['full_rows'])
    assert counts['WS30_QP'] == len(expected)
    assert len(qp_ports) == int(summaries['WS30_PATH']['switch_qps'])
    assert int(summaries['WS30_PATH']['port_changes']) == int(summaries['WS30_PATH']['rejected']) == 0
    for key in ['admission_dropped_bytes','queue_rejected_bytes','violations','current','dropped']:
        assert int(summaries['WS30_QUEUE'][key]) == 0, key
    if cell['lb'] == 'ws31-c2':
        assert set(c2) == set(by_index)
        state = summaries['WS31_C2_STATE']
        for key in ['pending','unfinished','cancelled','cancel_bytes']:
            assert int(state[key]) == 0, key
        for key in ['demanded','launched','finished']:
            assert int(state[key]) == len(expected), key
        for key in ['demand_bytes','launch_bytes','finish_bytes']:
            assert int(state[key]) == plan['payload_bytes'], key
    return {'scope':'Main independent dynamic raw check; technical only',
            'id':meta['experiment_id'],'source_sha':plan['source_sha'],'lb':cell['lb'],
            'flows':len(completed),'payload_bytes':sum(v[4] for v in completed.values()),
            'all_demand_origins_match':True,'c2_time_rows':len(c2),'counts':dict(counts),
            'summaries':summaries,'ordered_normalized_hashes':{p:h.hexdigest() for p,h in hashes.items()},
            'fct_sha256':digest(fcts[0]),'log_sha256':digest(logs[0]),
            'source_payload_reconstruction':{'rows':sum(map(len,intervals.values())),
                'keys':len(intervals),'unique_payload_bytes':unique_bytes,'all_match_input':True,
                'first_tags':dict(Counter(source_tags.values()))},'inputs':plan['inputs']}


def values(line):
    result = {}
    for token in line.split()[1:]:
        if '=' in token:
            k, v = token.split('=', 1)
            result[k] = int(v) if v.isdigit() else v
    return result


def identity(v):
    return tuple(v[k] for k in ['switch','sip','dip','sport','dport'])


def mechanism(base, mode):
    trace = (base/'config/traffic_trace.txt').read_text().splitlines()[1:]
    sizes, tags, by_flow = {}, {}, {}
    sports, dports = defaultdict(lambda:10000), defaultdict(lambda:100)
    for index, line in enumerate(trace):
        src,dst,pg,size,start,tag = line.split()
        src,dst,size,tag = map(int,(src,dst,size,tag))
        key = (src,dst,sports[src],dports[dst])
        sizes[key],tags[key],by_flow[index] = size,tag,key
        sports[src] += 1; dports[dst] += 1
    topo = (base/'config/topology.txt').read_text().splitlines()
    switches = set(map(int,topo[1].split())); device=Counter(); uplinks=defaultdict(list); host_tor={}
    for line in topo[2:2+int(topo[0].split()[2])]:
        a,b = map(int,line.split()[:2]); device[a]+=1; device[b]+=1
        if a not in switches: host_tor[a]=b
        if b not in switches: host_tor[b]=a
        if a in switches and b in switches:
            uplinks[a].append(device[a]); uplinks[b].append(device[b])
    def flow(v): return ((v['sip']>>8)&65535,(v['dip']>>8)&65535,v['sport'],v['dport'])
    log = next((base/'raw').glob('*/config.log'))
    states=[]; choices={}; demands={}; launches={}; finishes={}
    ledger={}; peak=0; unique=0; expired=0; pressure=0; choice_checks=0
    route_count=0; last=defaultdict(dict); quota={}; qcounts=defaultdict(Counter)
    activation=defaultdict(Counter); borrowers=defaultdict(Counter); borrower_max=defaultdict(Counter)
    side_routes={}; expected_side={}; source_ports={}
    for line in log.open(encoding='utf-8'):
        prefix=line.split(' ',1)[0].strip()
        if not prefix.startswith(('WS30_ROUTE','WS31_')): continue
        v=values(line)
        if prefix in ['WS31_C1_STATE','WS31_C3_STATE','WS31_C2_STATE']:
            states.append(v); continue
        if prefix.startswith('WS31_C2_') and prefix != 'WS31_C2_STATE':
            table={'WS31_C2_DEMAND':demands,'WS31_C2_LAUNCH':launches,'WS31_C2_FINISH':finishes}.get(prefix)
            assert table is not None, prefix
            assert v['flow_id'] not in table
            table[v['flow_id']]=v; continue
        if prefix=='WS31_C1_CHOICE':
            key=identity(v); f=flow(v); now=v['time_ns']
            assert key not in choices and v['switch']==host_tor[f[0]]
            for k,e in list(ledger.items()):
                if e['end']<=now: del ledger[k]; expired+=1
            def framed(n): return n+((n+999)//1000)*48
            for suffix in ['1','2']:
                port=v['first' if suffix=='1' else 'second']
                truth=sum(framed(e['remaining']) for k,e in ledger.items() if k[0]==v['switch'] and e['port']==port)
                assert v['r'+suffix]==truth,(key,suffix,v['r'+suffix],truth)
            chosen=v['second'] if v['q2']+v['r2']<v['q1']+v['r1'] else v['first']
            assert v['chosen']==chosen and v['category']==tags[f]
            assert v['predicted']==(65536 if tags[f]==1 else 8192)
            choices[key]=v; ledger[key]={'port':chosen,'remaining':v['predicted'],'end':now+20000,'next_seq':0}
            peak=max(peak,len(ledger)); pressure+=bool(v['r1'] or v['r2']); choice_checks+=1
        if prefix=='WS31_C3_ROUTE':
            key=(identity(v),v['time_ns'],v['seq'])
            assert key not in side_routes; side_routes[key]=v
        if prefix!='WS30_ROUTE': continue
        f=flow(v)
        if v['switch']!=host_tor[f[0]]: continue
        key=identity(v); now=v['time_ns']; seq=v['seq']; payload=min(1000,sizes[f]-seq)
        assert payload>0
        route_count+=1; source_ports.setdefault(key,v['port']); assert source_ports[key]==v['port']
        if mode=='ws31-c1':
            for k,e in list(ledger.items()):
                if e['end']<=now: del ledger[k]; expired+=1
            assert key in choices and choices[key]['chosen']==v['port']
            if key in ledger:
                e=ledger[key]
                # This no-drop technical input has ordered, nonduplicated source
                # intervals while the predictor is live; verify that condition.
                assert seq==e['next_seq']; e['next_seq']=seq+payload
                unique+=payload; e['remaining']=max(0,e['remaining']-payload)
                if not e['remaining']: del ledger[key]
        if mode=='ws31-c3':
            sw=v['switch']; category=tags[f]; ports=sorted(uplinks[sw]); reserved=(len(ports)+3)//4
            def owner(port): return 2 if port in ports[:reserved] else 1
            def active(c): return c in last[sw] and now-last[sw][c]<20000
            fresh=key not in quota
            if not active(category):
                activation[sw][category]+=1
                n=sum(e['borrowed'] and e['owner']==category and now-e['last']<20000
                      for k,e in quota.items() if k[0]==sw)
                borrowers[sw][category]+=n; borrower_max[sw][category]=max(borrower_max[sw][category],n)
            last[sw][category]=now
            if fresh:
                restricted=active(3-category)
                eligible=[p for p in ports if not restricted or owner(p)==category]
                side=side_routes[(key,now,seq)]
                assert side['fresh']==1 and side['category']==category
                assert side['eligible']==len(eligible) and side['restricted']==int(restricted)
                assert side['first'] in eligible and side['second'] in eligible
                chosen=side['second'] if side['q2']<side['q1'] else side['first']
                assert chosen==v['port']==side['chosen']
                e={'owner':owner(chosen),'borrowed':owner(chosen)!=category,'last':now,'port':chosen}
                quota[key]=e; qcounts[sw]['fresh']+=1
                qcounts[sw]['restricted']+=restricted; qcounts[sw]['borrowed']+=e['borrowed']
            e=quota[key]; e['last']=now
            residual=e['borrowed'] and active(e['owner'])
            if fresh or residual:
                expected_side[(key,now,seq)]=(fresh,residual)
                side=side_routes[(key,now,seq)]
                assert side['fresh']==int(fresh) and side['residual']==int(residual)
                assert side['owner']==e['owner'] and side['borrowed']==int(e['borrowed'])
                assert side['chosen']==e['port']==v['port'] and side['wire_bytes']==payload+48
            if residual:
                qcounts[sw]['residual_packets']+=1; qcounts[sw]['residual_wire_bytes']+=payload+48
    if mode=='ws31-c1':
        assert choice_checks==104 and pressure>0 and unique>0
        assert all(s['conserved']==1 and s['ttl_ns']==20000 and s['max_entries']==65536 and s['max_ranges']==32 for s in states)
        assert sum(s['entries'] for s in states)==sum(s['fresh'] for s in states)==104
        assert sum(s['hits'] for s in states)==route_count-104
        assert sum(s['unique_payload'] for s in states)==unique
        assert sum(s['expired'] for s in states)==expired
        assert max(s['predictor_peak'] for s in states)==peak<=65536
        assert sum(s['predictor_entries'] for s in states)==len(ledger)==0
        return {'source_arrivals':route_count,'choices_pressure_score_replayed':choice_checks,'nonzero_pressure_choices':pressure,
                'unique_payload_deduction':unique,'predictor_peak':peak,'expiry_events':expired,
                'conditional_reconstruction':'Fixed source, MTU1000 and source-switch framing48B, complete no-drop ordered trace; every reported R and choice replayed. Queue byte counters have a different framing domain.'}
    if mode=='ws31-c2':
        assert set(demands)==set(launches)==set(finishes)==set(by_flow)
        waits=[]
        for i,key in by_flow.items():
            d,l,f=demands[i],launches[i],finishes[i]
            assert d['tag']==tags[key] and d['size']==sizes[key]
            # Independently compute the frozen portable tuple hash, wrapping
            # every multiplication in the uint32_t domain.
            sip=(11<<24)|(key[0]<<8)|1; dip=(11<<24)|(key[1]<<8)|1
            h=2166136261 ^ 0x43c2a517
            for word in [sip,dip,key[2]|(key[3]<<16)]:
                for j in range(4): h=((h^((word>>(j*8))&255))*16777619)&0xffffffff
            h^=h>>16; h=(h*0x85ebca6b)&0xffffffff; h^=h>>13
            wait=h%501 if tags[key]==2 else 0
            assert d['delay_ns']==l['wait_ns']==f['wait_ns']==wait
            assert d['demand_ns']==l['demand_ns']==f['demand_ns']
            assert l['launch_ns']==f['launch_ns']==d['demand_ns']+wait
            assert f['finish_ns']-d['demand_ns']==f['fct_ns'] and f['finish_ns']>=l['launch_ns']
            waits.append(wait)
        assert len(states)==1
        state=states[0]
        assert state['waited']==sum(w>0 for w in waits)>0
        assert state['delay_sum_ns']==sum(waits) and state['delay_max_ns']==max(waits)
        return {'demand_launch_finish_rows_each':len(by_flow),'exact_hash_waits_verified':len(waits),
                'positive_waits':sum(w>0 for w in waits),'delay_sum_ns':sum(waits),'delay_max_ns':max(waits)}
    assert mode=='ws31-c3' and set(side_routes)==set(expected_side)
    assert sum(s['entries'] for s in states)==sum(s['fresh'] for s in states)==len(quota)==104
    assert sum(s['hits'] for s in states)==route_count-104
    for s in states:
        sw=s['switch']; assert s['conserved']==1 and s['activity_ns']==20000 and s['pinning']==1
        for k in ['fresh','restricted','borrowed','residual_packets','residual_wire_bytes']: assert s[k]==qcounts[sw][k]
        for tag,name in [(1,'bg'),(2,'moe')]:
            assert s[name+'_activations']==activation[sw][tag]
            assert s[name+'_borrowers_at_activation_sum']==borrowers[sw][tag]
            assert s[name+'_borrowers_at_activation_max']==borrower_max[sw][tag]
    totals={k:sum(v[k] for v in qcounts.values()) for k in ['restricted','borrowed','residual_packets','residual_wire_bytes']}
    assert totals['restricted']>0 and totals['borrowed']>0 and totals['residual_packets']>0
    assert max(v[2] for v in activation.values())>=2
    return {'source_arrivals_replayed':route_count,'side_events_replayed':len(side_routes),'activity_window_ns':20000,
            'tag2_activations':sum(v[2] for v in activation.values()),
            'tag2_borrowers_at_activation_sum':sum(v[2] for v in borrowers.values()),**totals}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path); parser.add_argument('plan',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); assert not args.output.exists()
    plan=json.loads(args.plan.read_text(encoding='utf-8'))
    result=verify(args.results,plan)
    result['mechanism_replay']=mechanism(args.results,result['lb'])
    result['status']='PASS_FOR_INITIAL_DYNAMIC_TECHNICAL_SCOPE'
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'id':result['id'],'flows':result['flows'],'replay':result['mechanism_replay']},ensure_ascii=False))


