"""Local raw UID/clock/presence and first-policy verifier; no remote execution."""
import hashlib, importlib.util, json, pathlib, re, sys
from collections import Counter, defaultdict
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parent
PREFIX='label-dynamic-validation-r1'
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
R=module('dynamic_pure_replays',PREFIX+'-replays.py')
I=module('dynamic_identity',PREFIX+'-identity.py')
class CoverageGap(RuntimeError):pass
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ip(host):return (11<<24)|(host<<8)|1
def key(v):return ((v['sip']>>8)&65535,(v['dip']>>8)&65535,v['sport'],v['dport'])
def start_hash(flow):
    a,z,sport,dport=flow;h=2166136261^0x43c2a517
    for word in (ip(a),ip(z),sport|(dport<<16)):
        for shift in range(0,32,8):h=((h^((word>>shift)&255))*16777619)&0xffffffff
    h^=h>>16;h=(h*0x85ebca6b)&0xffffffff;h^=h>>13;return h
def visible(profile,original,elapsed,flow):
    assert elapsed>=0
    if profile==1 and elapsed<500:return 0,0
    swap=(profile==2 and elapsed>=500) or (profile==3 and (start_hash(flow)&3)==0)
    return (3-original if swap and original in (1,2) else original),1
def records(log):
    values=[]
    with log.open('rb') as f:
        for line in f:
            assert b'WS30_OBSERVATION_OVERFLOW' not in line
            if line.startswith((b'WS30_',b'WS31_')):
                prefix=line.split(b' ',1)[0].decode('ascii')
                # Other WS30 summaries may contain non key=value tokens.
                if prefix in ('WS30_CHOICE','WS30_ROUTE','WS30_PATH','WS30_QUEUE') or prefix.startswith(('WS31_LABEL_','WS31_C1_','WS31_C2_','WS31_C3_')):
                    values.append((prefix,R.fields(line.decode('ascii')),line))
    return values
def hashes(rows):
    hh={k:hashlib.sha256() for k in ('choice','route','combined','choice_without_tag','route_without_tag','combined_without_tag')}
    counts=Counter()
    for prefix,v,line in rows:
        if prefix not in ('WS30_CHOICE','WS30_ROUTE'):continue
        k='choice' if prefix=='WS30_CHOICE' else 'route';counts[k]+=1
        clean=re.sub(rb' uid=[^ \r\n]+',b'',line);hh[k].update(clean);hh['combined'].update(clean)
        clean=re.sub(rb' tag=[^ \r\n]+',b'',clean);hh[k+'_without_tag'].update(clean);hh['combined_without_tag'].update(clean)
    return {'hashes':{k:h.hexdigest() for k,h in hh.items()},'counts':dict(counts)}
def neighbors(topology):
    lines=topology.read_text(encoding='ascii').splitlines();ct=Counter();result={}
    for line in lines[2:2+int(lines[0].split()[2])]:
        a,z=map(int,line.split()[:2]);ct[a]+=1;ct[z]+=1;result[a,ct[a]]=z;result[z,ct[z]]=a
    return result
def reference(target):
    log=next((target/'raw').glob('*/config.log'));rows=records(log);hosts,unused=R.topo(target/'config/topology.txt')
    first=[]
    for prefix,v,line in rows:
        if prefix=='WS30_CHOICE' and v['switch']==hosts[key(v)[0]]:
            first.append({k:v[k] for k in ('time_ns','switch','sip','dip','sport','dport','first','second','q1','q2','chosen')})
    return {'target':str(target),'fct':str(next((target/'raw').glob('*/*_out_fct.txt'))),'ordered':hashes(rows),'source_first':first}
def c2(cell,rows,expected,completed,packets):
    tables={kind:{} for kind in ('DEMAND','LAUNCH','FINISH')};states=[];labels={}
    for prefix,v,line in rows:
        if prefix=='WS31_C2_STATE':states.append(v)
        elif prefix=='WS31_LABEL_DEMAND':
            assert v['flow_id'] not in labels;labels[v['flow_id']]=v
        elif prefix.startswith('WS31_C2_'):
            kind=prefix[len('WS31_C2_'):];assert kind in tables
            assert v['flow_id'] not in tables[kind];tables[kind][v['flow_id']]=v
    ids=set(range(len(expected)));assert all(set(t)==ids for t in tables.values()) and set(labels)==ids and len(states)==1
    profile=cell['ws31_label_profile'];timing=[]
    for flow,e in expected.items():
        index=e['index'];dem,launch,finish=(tables[k][index] for k in ('DEMAND','LAUNCH','FINISH'))
        policy,present=visible(profile,e['tag'],0,flow);wait=start_hash(flow)%501 if policy==2 else 0
        assert dem['tag']==e['tag'] and dem['policy_tag']==policy and dem['tag_transform']==0
        assert dem['delay_ns']==launch['wait_ns']==finish['wait_ns']==wait
        assert dem['size']==launch['size']==finish['size']==e['size']
        assert dem['demand_ns']==launch['demand_ns']==finish['demand_ns']==e['demand_ns']==completed[flow][5]
        assert launch['launch_ns']==finish['launch_ns']==e['demand_ns']+wait
        assert finish['finish_ns']>=launch['launch_ns']
        assert finish['fct_ns']==completed[flow][6]==finish['finish_ns']-e['demand_ns']
        assert labels[index]==dict(flow_id=index,generation=0,demand_ns=e['demand_ns'],profile=profile,original=e['tag'],visible=policy,present=present)
        assert all(p['time_ns']>=launch['launch_ns'] for p in packets[flow])
        timing.append({'flow':flow,'original':e['tag'],'policy':policy,'present':present,'wait_ns':wait,'demand_ns':e['demand_ns'],'launch_ns':launch['launch_ns'],'finish_ns':finish['finish_ns']})
    state=states[0];waits=[r['wait_ns'] for r in timing]
    for k in ('demanded','launched','finished'):assert state[k]==len(expected)
    for k in ('cancelled','pending','unfinished','cancel_bytes'):assert state[k]==0
    for k in ('demand_bytes','launch_bytes','finish_bytes'):assert state[k]==sum(e['size'] for e in expected.values())
    assert state['waited']==sum(w>0 for w in waits) and state['delay_sum_ns']==sum(waits) and state['delay_max_ns']==max(waits) and state['frozen_max_ns']==500
    prescribed={1:(0,0,0),2:(6,1588,413),3:(6,1457,409)}[profile]
    assert (sum(w>0 for w in waits),sum(waits),max(waits))==prescribed
    if profile==3:
        assert next(t['wait_ns'] for t in timing if t['flow'][0]==1)==282
        assert next(t['wait_ns'] for t in timing if t['flow'][0]==7)==0
    return {'status':'PASS','timing':timing,'state':state,'positive_waits':prescribed[0],'wait_sum_ns':sum(waits),'wait_max_ns':max(waits)}
def compare_reference(cell,obs,ref,detail,path,rows):
    # C3 source admissions are specialized events. Generic CHOICE equivalence
    # is required only for C2, as in the original frozen contract.
    if cell['lb']=='ws31-c2':
        assert obs['counts']==ref['ordered']['counts']
        for k in ('choice_without_tag','route_without_tag','combined_without_tag'):assert obs['hashes'][k]==ref['ordered']['hashes'][k]
    else:
        assert cell['lb']=='ws31-c3'
        n=cell['flow_count']
        fresh=[v for prefix,v,line in rows if prefix=='WS31_C3_ROUTE' and v['fresh']]
        assert obs['counts']['choice']==2*n and ref['ordered']['counts']['choice']==3*n
        assert len(fresh)==len(detail['source_first'])==n and path['switch_qps']==3*n
        assert obs['counts']['route']==ref['ordered']['counts']['route']
        assert obs['hashes']['route_without_tag']==ref['ordered']['hashes']['route_without_tag']
        assert detail['source_first']==ref['source_first']

def verify(cell,target,ref=None):
    plan=json.loads((ROOT/(PREFIX+'-frozen-plan.json')).read_text(encoding='utf-8'))
    target=pathlib.Path(target);meta=json.loads((target/'metadata.json').read_text(encoding='utf-8'))
    assert meta['status']=='SUCCEEDED' and meta['git_commit']==plan['source_sha'] and meta['experiment_id']==cell['id']
    assert meta['build_mode']=='optimized' and meta['cpu_jobs']==2 and meta['concurrency_cap']==1
    for k,v in plan['common'].items():assert (meta['concurrency_cap'] if k=='max_concurrent' else meta['parameters'][k])==v
    for k in ('lb','flow_file','ws31_label_profile','ws30_tag_transform'):assert meta['parameters'][k]==cell[k]
    for k in ('ws30_composition','ws30_lifecycle','ws30_life_profile','ws13_diag','ws25_diag','ws28_tail_diag','ws21_heartbeat','ws21_feedback','ws21_identity','ws18_admission','ws18_path','ws21_heartbeat_fault_mode'):assert meta['parameters'].get(k,0)==0
    for file,path in [('traffic_trace.txt','config/'+cell['flow_file']),('topology.txt','config/leaf_spine_128_100G_OS2.txt')]:assert sha(target/'config'/file)==plan['inputs'][path]
    config=dict(line.split(None,1) for line in (target/'config/config.txt').read_text().splitlines() if line.strip())
    for k,v in [('ENABLE_PFC','0'),('ENABLE_IRN','1'),('RANDOM_SEED','1'),('CC_MODE','1'),('BUFFER_SIZE','9'),('PACKET_PAYLOAD_SIZE','1000'),('WS21_HEARTBEAT_FAULT_MODE','0')]:assert config[k]==v
    trace=target/'config/traffic_trace.txt';expected=R.trace_rows(trace);hosts,unused=R.topo(target/'config/topology.txt');peer=neighbors(target/'config/topology.txt')
    fct=next((target/'raw').glob('*/*_out_fct.txt'));log=next((target/'raw').glob('*/config.log'));rows=records(log)
    ident=I.verify(trace,fct,log);assert ident['flows']==cell['flow_count']==15 and ident['payload_bytes']==cell['payload_bytes']==245760
    completed={tuple(v[:4]):v for v in (list(map(int,line.split())) for line in fct.read_text().splitlines())}
    allroutes=[v for prefix,v,line in rows if prefix=='WS30_ROUTE'];q=[v for prefix,v,line in rows if prefix=='WS30_QUEUE'];path=[v for prefix,v,line in rows if prefix=='WS30_PATH']
    assert len(q)==len(path)==1 and allroutes
    assert q[0]['enqueued']==q[0]['dequeued']
    for k in ('dropped','current','admission_dropped_bytes','queue_rejected_bytes','violations'):assert q[0][k]==0
    assert path[0]['full_rows']==path[0]['data_hops']==len(allroutes)
    assert path[0]['changed_qps']==path[0]['port_changes']==path[0]['rejected']==0
    routes=defaultdict(list);pins={};firstsource={}
    for v in allroutes:
        flow=key(v);assert flow in expected and v['sip']==ip(flow[0]) and v['dip']==ip(flow[1])
        pin=(v['switch'],flow);assert pin not in pins or pins[pin]==v['port'];pins[pin]=v['port']
        routes[v['uid']].append(v)
        if v['switch']==hosts[flow[0]]:firstsource.setdefault(flow,v)
    assert set(firstsource)==set(expected)
    for uid,rr in routes.items():
        flow=key(rr[0]);assert len(rr)==3 and len({v['switch'] for v in rr})==3
        assert rr[0]['switch']==hosts[flow[0]] and rr[-1]['switch']==hosts[flow[1]]
        assert peer[rr[0]['switch'],rr[0]['port']]==rr[1]['switch'] and peer[rr[1]['switch'],rr[1]['port']]==rr[2]['switch'] and peer[rr[2]['switch'],rr[2]['port']]==flow[1]
        assert all(key(v)==flow and v['seq']==rr[0]['seq'] for v in rr)
    profile=cell['ws31_label_profile'];packets=defaultdict(list);uids={};coverage=[];side=[v for prefix,v,line in rows if prefix=='WS31_LABEL_ROUTE']
    if not profile:
        assert not any(prefix.startswith('WS31_LABEL_') for prefix,v,line in rows)
        for v in allroutes:assert v['tag']==expected[key(v)]['tag']
    else:
        for prefix,p,line in rows:
            if prefix!='WS31_LABEL_PACKET':continue
            assert set(p)==set('time_ns demand_ns uid flow_id generation sip dip sport dport seq payload profile original visible present'.split())
            flow=key(p);assert flow in expected and p['uid'] not in uids;e=expected[flow]
            assert p['sip']==ip(flow[0]) and p['dip']==ip(flow[1]) and p['flow_id']==e['index'] and p['generation']==0
            assert p['demand_ns']==e['demand_ns'] and p['original']==e['tag'] and p['profile']==profile
            assert 0<=p['seq']<e['size'] and p['payload']==min(1000,e['size']-p['seq'])
            assert (p['visible'],p['present'])==visible(profile,e['tag'],p['time_ns']-p['demand_ns'],flow)
            assert not packets[flow] or p['time_ns']>=packets[flow][-1]['time_ns']
            uids[p['uid']]=p;packets[flow].append(p)
        assert set(uids)==set(routes) and set(packets)==set(expected) and len(side)==len(allroutes)
        for v,s in zip(allroutes,side):
            p=uids[v['uid']]
            assert s=={k:v[k] for k in ('time_ns','switch','uid','sip','dip','sport','dport','seq','port')}|{'visible':v['tag'],'present':p['present']}
            assert key(v)==key(p) and v['seq']==p['seq'] and v['tag']==p['visible'] and v['time_ns']>=p['time_ns']
        for flow,e in expected.items():
            pp=packets[flow];assert firstsource[flow]['uid']==pp[0]['uid']
            unique=[]
            for p in pp:unused,unique=R.novel_ranges(unique,p['seq'],p['payload'])
            assert unique==[(0,e['size'])]
            early=[p for p in pp if p['time_ns']-e['demand_ns']<500];late=[p for p in pp if p['time_ns']-e['demand_ns']>=500]
            if profile in (1,2) and (not early or not late or pp[0]['time_ns']-e['demand_ns']>=500):raise CoverageGap('Missing actual early/late construction for '+str(flow))
            coverage.append({'flow':flow,'original':e['tag'],'first_uid':pp[0]['uid'],'first_construct_elapsed_ns':pp[0]['time_ns']-e['demand_ns'],
                'early_count':len(early),'late_count':len(late),'constructed':len(pp),'unique_sequences':len({p['seq'] for p in pp}),
                'observed_value_presence':sorted({(p['visible'],p['present']) for p in pp}),'bucket':start_hash(flow)&3,
                'wrong_known_cohort':profile==3 and e['tag'] in (1,2) and (start_hash(flow)&3)==0})
        if profile==3:assert {c['flow'][0] for c in coverage if c['wrong_known_cohort']}=={1,7}
    obs=hashes(rows);detail={};firstlabels={flow:v['tag'] for flow,v in firstsource.items()}
    R.FIRST_LABELS.clear();R.FIRST_LABELS.update(firstlabels)
    if cell['lb']=='ws31-c1':detail=R.c1_replay(cell,target)
    elif cell['lb']=='ws31-c2':detail=c2(cell,rows,expected,completed,packets)
    elif cell['lb']=='ws31-c3':
        detail=R.c3_replay(cell,target,None)
        if profile==1:
            assert all(s[k]==0 for s in detail['states'] for k in ('restricted','borrowed','residual_packets','residual_wire_bytes','bg_activations','moe_activations'))
            assert all(v==0 for v in firstlabels.values())
        else:
            assert {d['category'] for prefix,d,line in rows if prefix=='WS31_C3_ROUTE' and d['fresh']}=={0,1,2}
            if not sum(s['restricted'] for s in detail['states']):raise CoverageGap('No restricted new C3 admission')
    if profile and cell['lb']!='ws31-c2':assert not any(prefix.startswith(('WS31_C2_','WS31_LABEL_DEMAND')) for prefix,v,line in rows)
    paired=cell['lb'] in ('ws31-c2','ws31-c3') and profile==1
    if paired:
        assert ref is not None and fct.read_bytes()==pathlib.Path(ref['fct']).read_bytes()
        compare_reference(cell,obs,ref,detail,path[0],rows)
    return {'status':'PASS','scope':'Synthetic dynamic label correctness only','identity':ident,'profile':profile,'packet_constructions':len(uids),
            'accepted_route_rows':len(allroutes),'label_route_rows':len(side),'three_hops_each_uid':True,'coverage':coverage,
            'first_policy_per_original_request':[{'flow':flow,'original':e['tag'],'actual_first_value':firstlabels[flow]} for flow,e in expected.items()],
            'ordered':obs,'queue':q[0],'path':path[0],'mechanism':detail,'new_q12_regression':paired,
            'generation':0,'original_business_counts':dict(Counter(e['tag'] for e in expected.values()))}
def precheck():
    plan=json.loads((ROOT/(PREFIX+'-frozen-plan.json')).read_text(encoding='utf-8'));cohorts=[]
    for c in plan['cohorts']:
        flow=(c['src'],c['dst'],c['sport'],c['dport']);bucket=start_hash(flow)&3
        assert bucket==c['bucket'] and (c['original_tag'] in (1,2) and bucket==0)==c['swapped'];cohorts.append(c)
    sums={}
    for profile in (1,2,3):
        waits=[]
        for c in cohorts:
            flow=(c['src'],c['dst'],c['sport'],c['dport']);tag=c['original_tag']
            p,present=visible(profile,tag,0,flow);waits.append(start_hash(flow)%501 if p==2 else 0)
            if profile==1:assert visible(profile,tag,499,flow)==(0,0) and visible(profile,tag,500,flow)==(tag,1)
            if profile==2:assert visible(profile,tag,499,flow)==(tag,1) and visible(profile,tag,500,flow)==((3-tag if tag in (1,2) else tag),1)
        sums[profile]=(sum(w>0 for w in waits),sum(waits),max(waits))
    assert sums=={1:(0,0,0),2:(6,1588,413),3:(6,1457,409)}
    # Interval checker handles duplicate and overlap without conflating UID observations.
    assert R.novel_ranges([(0,1000)],0,1000)==(0,[(0,1000)])
    assert R.novel_ranges([(0,1000)],500,1000)==(500,[(0,1500)])
    return {'status':'PASS','cohorts':cohorts,'c2_prescribed_waits':sums,'visibility_boundary_checked_ns':[499,500],
        'missing_zero_vs_explicit_zero':True,'pure_interval_overlap_checks':2,'core_or_simulation_executions':0}
if __name__=='__main__':
    if sys.argv[1:]==['--precheck']:print(json.dumps(precheck(),indent=2))
    else:
        cell=json.loads(sys.argv[1]);ref=json.loads(pathlib.Path(sys.argv[3]).read_text()) if len(sys.argv)>3 else None
        print(json.dumps(verify(cell,pathlib.Path(sys.argv[2]),ref),indent=2))
