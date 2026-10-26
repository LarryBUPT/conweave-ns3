"""Independent local raw audit; never launches or changes experiments."""
import collections
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / 'docs/research/evidence'

def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x): return hashlib.sha256('\n'.join(x).encode()).hexdigest()
def kv(x): return {k:int(v) for k,v in re.findall(r'(\w+)=(\d+)', x)}
def seconds(t): return datetime.fromisoformat(t.replace('Z','+00:00')).timestamp()
def percentile(x,q):
    x=sorted(x); p=(len(x)-1)*q; i=int(p)
    return x[i]+(x[min(i+1,len(x)-1)]-x[i])*(p-i)

def audit(c):
    folder=ROOT/'results'/c['id']; m=read(folder/'metadata.json')
    raw=folder/'raw'/str(m['raw_directory']); fct=raw/(str(m['raw_directory'])+'_out_fct.txt')
    trace=folder/'config/traffic_trace.txt'; topo=folder/'config/topology.txt'
    assert m['status']=='SUCCEEDED' and m['git_commit']==c['source_sha']
    assert sha(trace)==c['trace_sha256']==m['input_flow_sha256']
    assert sha(topo)==c['topology_sha256']==m['topology_sha256']
    config=(folder/'config/config.txt').read_text()
    assert re.search(r'^RANDOM_SEED\s+1\s*$',config,re.M) and m['seed']==1
    expected={}; sp=collections.defaultdict(lambda:10000); dp=collections.defaultdict(lambda:100)
    for line in trace.read_text().splitlines()[1:]:
        a=line.split(); s,d,pg,size=map(int,a[:4]); tag=int(a[5]) if len(a)>5 else 0
        sport,dport=sp[s],dp[d]; sp[s]+=1; dp[d]+=1
        if c['lifecycle']>=3 and tag==2: sport,dport=10000,100
        key=(s,d,sport,dport,size,int(Decimal(a[4])*10**9))
        assert key not in expected
        expected[key]=tag
    frows=[]; identity=[]; unmatched=dict(expected)
    for line in fct.read_text().splitlines():
        r=list(map(int,line.split())); keys=[tuple(r[:5])+(r[5]+delta,) for delta in (-1,0,1)]
        hits=[k for k in keys if k in unmatched]; assert len(hits)==1 and r[6]>0
        tag=unmatched.pop(hits[0]); frows.append(r); identity.append((r,tag))
    assert not unmatched and len(frows)==c['input_flows']
    logpath=folder/'logs/config.log'; lines=logpath.read_text().splitlines()
    records=collections.defaultdict(list)
    for line in lines:
        if line.startswith('WS30'): records[line.split()[0]].append(kv(line))
    assert not any('WS30_OBSERVATION_OVERFLOW' in line for line in lines)
    q=records['WS30_QUEUE']; path=records['WS30_PATH']
    if c['observe']:
        assert len(q)==len(path)==1
        assert q[0]['enqueued']==q[0]['dequeued'] and all(q[0][k]==0 for k in ('dropped','current','violations','admission_dropped_bytes','queue_rejected_bytes'))
        assert path[0]['rejected']==0
        assert len(records['WS30_QP'])==len(frows)
        assert collections.Counter(r['tag'] for r in records['WS30_QP'])==collections.Counter(expected.values())
    routes=records['WS30_ROUTE']; choices=records['WS30_CHOICE']
    if c['arm']=='Q12':
        assert all(r['chosen']==(r['second'] if r['q2']<r['q1'] else r['first']) for r in choices)
    tags=sorted(set(expected.values()))
    transport={str(t):{k:sum(r[k] for r in records['WS30_QP'] if r['tag']==t) for k in ('rx_gap','rx_below_expected','sack_feedback','cnp_feedback','retransmit_packets','retransmit_bytes','timeout')} for t in tags}
    metrics={}
    for t in tags:
        rows=[r for r,tag in identity if tag==t]
        if rows: metrics[str(t)]={'n':len(rows),'payload_bytes':sum(r[4] for r in rows),'p50_ns':percentile([r[6] for r in rows],.5),'p99_ns':percentile([r[6] for r in rows],.99),'max_ns':max(r[6] for r in rows),'batch_from_earliest_demand_ns':max(r[5]+r[6] for r in rows)-min(r[5] for r in rows)}
    row={'id':c['id'],'arm':c['arm'],'role':c['role'],'lifecycle':c['lifecycle'],'trace':c['trace'],'completed':len(frows),'payload_bytes':sum(r[4] for r in frows),'hashes':{'fct':sha(fct),'trace':sha(trace),'topology':sha(topo),'log':sha(logpath),'metadata':sha(folder/'metadata.json'),'config':sha(folder/'config/config.txt')},'metrics':metrics,'transport':transport,'queue':q,'path':path,'choices':{'n':len(choices),'distinct_pair':sum(r['first']!=r['second'] for r in choices),'unequal_queue_distinct_pair':sum(r['first']!=r['second'] and r['q1']!=r['q2'] for r in choices)},'route_rows':len(routes),'route_hash_without_tag':digest([re.sub(r' tag=\d+','',s) for s in lines if s.startswith('WS30_ROUTE ')]),'route_hash':digest([s for s in lines if s.startswith('WS30_ROUTE ')]),'metadata_seed':m['seed'],'plan_seed':c['seed'],'cap':m['concurrency_cap'],'created_utc':m['created_utc'],'build_finished_utc':m['build_finished_utc'],'started_utc':m['started_utc'],'finished_utc':m['finished_utc'],'build_seconds':seconds(m['build_finished_utc'])-seconds(m['created_utc']),'run_seconds':seconds(m['finished_utc'])-seconds(m['started_utc'])}
    samples=[json.loads(l) for l in (folder/'logs/resource-samples.jsonl').read_text().splitlines()]
    row['resources']={'peak_load1':max(r['load_1m'] for r in samples),'min_memory_gib':min(r['mem_available_gib'] for r in samples),'min_disk_gib':min(r['free_gib'] for r in samples),'max_tree_rss_mib':max(r['process_tree_rss_mib'] for r in samples)}
    if c['lifecycle']:
        creates=records['WS30V13_CREATE']; done=records['WS30V13_ROUND_DONE']; releases=records['WS30V13_RELEASE']; sends=records['WS30V13_FIRST_SEND']; deletes=records['WS30V13_DELETE']
        assert len(done)==len(sends)==len(releases)==3
        # Release observations, rather than a synthetic released_ns in ROUND_DONE.
        for d,s,r in zip(done,sends,releases):
            assert d['demand_ns']==r['demand_ns'] and r['demand_ns']<=r['time_ns']<=s['time_ns']<=d['time_ns']
        persistent=c['lifecycle']==1
        assert len(creates)==len(deletes)==(1 if persistent else 3)
        if persistent:
            assert len({r['serial'] for r in creates+done+sends+releases+deletes})==1
            assert [r['seq'] for r in sends]==[0,8192,16384]
            assert [r['snd_una'] for r in done]==[8192,16384,24576]
            assert [r['snd_nxt'] for r in releases]==[0,8192,16384]
            assert [r['snd_una'] for r in releases]==[0,8192,16384]
            assert deletes[0]['time_ns']==done[-1]['time_ns']
            for j,r in enumerate(releases[1:],1):
                assert r['time_ns']>done[j-1]['time_ns']
                assert (r['rate'],r['alpha'])==(done[j-1]['rate'],done[j-1]['alpha'])
        serials={r['flow_id'] for r in creates}
        rx=[r for r in records['WS30V13_RX'] if r['flow_id'] in serials]
        if persistent: assert len({r['object'] for r in rx})==1 and [r['expected'] for r in rx]==[0,8192,16384]
        caches=[r for r in records['WS30V13_CACHE'] if r['sip']==0x0b000001 and r['dip']==0x0b000301]
        grouped=collections.defaultdict(list)
        for r in caches: grouped[str(r['switch'])].append(r['miss'])
        if c['arm'] in ('Q12','U12'):
            if persistent:
                assert grouped['4']==[1,0,0]
                if c['arm']=='Q12': assert all(v==[1,0,0] for v in grouped.values())
            elif c['lifecycle']==3: assert all(v==[1,0,0] for v in grouped.values())
            elif c['lifecycle']==4: assert all(v==[1,1,1] for v in grouped.values())
            else: assert all(v==[1]*len(v) for v in grouped.values())
        probe_routes=[r for r in routes if r['sip']==0x0b000001 and r['dip']==0x0b000301]
        for r in probe_routes:
            j=min(r['seq']//8192,2) if persistent else next(i for i,v in enumerate(creates) if v['sport']==r['sport'] and v['dport']==r['dport'] and (i==len(creates)-1 or r['time_ns']<creates[i+1]['time_ns']))
            assert r['time_ns']>=releases[j]['time_ns']
            assert r['seq']<releases[j]['released']
        row['life']={'creates':creates,'releases':releases,'done':done,'deletes':deletes,'rx':rx,'round_latency_ns':[r['time_ns']-r['demand_ns'] for r in done],'release_delay_ns':[r['time_ns']-r['demand_ns'] for r in releases],'first_send_delay_ns':[s['time_ns']-r['demand_ns'] for s,r in zip(sends,releases)],'cache_misses_by_switch':dict(grouped),'resets':records['WS30V13_CACHE_RESET'],'state':records['WS30V13_STATE'],'sender_ports':[r['sport'] for r in creates],'ingress_probe_ports_by_round':[[r['port'] for r in probe_routes if r['switch']==4 and r['seq']==(j*8192 if persistent else 0) and r['time_ns']>=releases[j]['time_ns'] and (j==2 or r['time_ns']<releases[j+1]['time_ns'])] for j in range(3)],'probe_choice_distinct_pairs':sum(r['first']!=r['second'] for r in choices if r.get('dip')==0x0b000301),'cc_nontrivial':any(r['rate']!=400000000000 or r['alpha']!=1 or r['sack_bytes']!=0 for r in done),'receiver_object_count':len({r['object'] for r in rx})}
    return row

def main():
    plan=read(EV/'ws30-v13-plan-r2.json'); cells=plan['technical']+plan['lifecycle']+plan['pilot']
    rows=[audit(c) for c in cells]; byid={r['id']:r for r in rows}
    technical={}
    for arm in ('E','Q12','R12','U12','D'):
        rr=[byid[c['id']] for c in plan['technical'] if c['arm']==arm]
        full=[byid[c['id']] for c in plan['technical'] if c['arm']==arm and c['observe']==2]
        technical[arm]={'fct_unique':len({r['hashes']['fct'] for r in rr}),'route_unique_without_tag':len({r['route_hash_without_tag'] for r in full})}
        assert technical[arm]=={'fct_unique':1,'route_unique_without_tag':1}
    e=next(r for r in rows if r['id'].endswith('t02-e-o2'))
    h=next(r for r in rows if r['id'].endswith('t12-h12-o2'))
    q=next(r for r in rows if r['id'].endswith('t04-q12-o2'))
    assert e['hashes']['fct']==h['hashes']['fct']=='70c970c63da906181ac8745f290528c4006ac9818645eafc40af150b140b1086'
    assert e['route_hash']==h['route_hash']
    assert q['hashes']['fct']=='1f71d7e802ec1b334aff9c6708be5abc2420c6fa7c31e2b6e2f3fdb1232bb44e'
    pilot=[]
    for cap in (4,8):
        rr=[r for r in rows if r['role']=='resource-only' and r['cap']==cap]
        simspan=max(seconds(r['finished_utc']) for r in rr)-min(seconds(r['started_utc']) for r in rr)
        endspan=max(seconds(r['finished_utc']) for r in rr)-min(seconds(r['created_utc']) for r in rr)
        pilot.append({'cap':cap,'n':len(rr),'simulation_batch_seconds':simspan,'simulation_cells_per_hour':len(rr)*3600/simspan,'build_plus_run_span_seconds':endspan,'build_plus_run_cells_per_hour':len(rr)*3600/endspan,'median_run_seconds':statistics.median(r['run_seconds'] for r in rr),'median_build_seconds':statistics.median(r['build_seconds'] for r in rr),'run_seconds_by_arm':{a:[r['run_seconds'] for r in rr if r['arm']==a] for a in ('E','Q12','U12','D')},'resource':{'peak_load1':max(r['resources']['peak_load1'] for r in rr),'min_memory_gib':min(r['resources']['min_memory_gib'] for r in rr),'min_disk_gib':min(r['resources']['min_disk_gib'] for r in rr),'max_tree_rss_mib':max(r['resources']['max_tree_rss_mib'] for r in rr)}})
    out={'scope':'Independent local raw analysis; all formal and W5 simulations disabled','analysis_model':{'model':'gpt-6.1-sol','effort':'medium','turn_id':'01a1756f-6c1b-7630-a0c8-0e805ba8114e'},'source_sha':plan['source_sha'],'plan_sha256':sha(EV/'ws30-v13-plan-r2.json'),'counts':dict(collections.Counter(c['role'] for c in cells)),'completed_fct_rows':sum(r['completed'] for r in rows),'technical_invariances':technical,'pilot_throughput':pilot,'rows':rows}
    target=EV/'ws30-v13-engineering-raw-analysis-r2.json'
    if target.exists(): assert read(target)==out,'Preserve changed analysis revision'
    else: target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cells':len(rows),'completed_rows':out['completed_fct_rows'],'pilot':pilot},ensure_ascii=False))

if __name__=='__main__': main()
