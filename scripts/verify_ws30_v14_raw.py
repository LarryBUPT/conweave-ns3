"""Future local verifier. Reads results only; never launches simulations."""
import hashlib
import json
import collections
from decimal import Decimal
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
def kv(line):
    out={}
    for k,v in re.findall(r'(\w+)=([^ ]+)',line):
        try:out[k]=int(v)
        except ValueError:
            try:out[k]=float(v)
            except ValueError:out[k]=v
    return out
def verify_lifecycle(c):
    folder=ROOT/'results'/c['id']; meta=json.loads((folder/'metadata.json').read_text())
    assert meta['status']=='SUCCEEDED' and meta['git_commit']==c['source_sha']
    assert meta['seed']==c['simulation_seed']==1
    assert meta['metadata_schema_version']==3 and meta['simulation_seed']==1 and meta['demand_seed']==c['demand_seed']
    assert meta['algorithm']==c['mode'] and meta['parameters']['ws30_observe']==c['observe'] and meta['parameters']['ws30_tag_transform']==0
    config=(folder/'config/config.txt').read_text()
    assert re.findall(r'^RANDOM_SEED\s+(\S+)\s*$',config,re.M)==['1']
    assert re.search(r'^LB_MODE\s+%d\s*$'%{'E':0,'Q12':33,'U12':35}[c['arm']],config,re.M)
    assert meta['parameters']['ws30_lifecycle']==c['lifecycle'] and meta['parameters']['ws30_life_profile']==c['life_profile']
    assert meta['parameters']['pfc']==0 and meta['parameters']['irn']==1 and meta['parameters']['bw']==400 and meta['parameters']['buffer']==9
    assert hashlib.sha256((folder/'config/traffic_trace.txt').read_bytes()).hexdigest()==c['trace_sha256']
    assert hashlib.sha256((folder/'config/topology.txt').read_bytes()).hexdigest()==c['topology_sha256']
    expected={};sp=collections.defaultdict(lambda:10000);dp=collections.defaultdict(lambda:100);probe_index=0
    for line in (folder/'config/traffic_trace.txt').read_text().splitlines()[1:]:
        a=line.split();src,dst,_,size=map(int,a[:4]);tag=int(a[5]);sport,dport=sp[src],dp[dst];sp[src]+=1;dp[dst]+=1
        if tag==2:
            sport=[10003,10006,10008][probe_index%3] if c['lifecycle']==6 else 10003
            dport=100;probe_index+=1
        key=(src,dst,sport,dport,size,int(Decimal(a[4])*10**9));assert key not in expected;expected[key]=tag
    raw_id=str(meta['raw_directory']); fct=folder/'raw'/raw_id/(raw_id+'_out_fct.txt')
    unmatched=dict(expected);background=[]
    for line in fct.read_text().splitlines():
        r=list(map(int,line.split()));hit=[tuple(r[:5])+(r[5]+d,) for d in (-1,0,1) if tuple(r[:5])+(r[5]+d,) in unmatched]
        assert len(hit)==1 and r[6]>0
        tag=unmatched.pop(hit[0])
        if tag==1:background.append(r[6])
    assert not unmatched and len(expected)==c['input_flows']
    lines=(folder/'logs/config.log').read_text().splitlines()
    assert not any('overflow' in l.lower() for l in lines)
    def rows(prefix):return [kv(l) for l in lines if l.startswith(prefix+' ')]
    states=rows('WS30V14_STATE'); persistent=c['lifecycle']==5
    rxstates=rows('WS30V14_RX_STATE')
    creates=rows('WS30V13_CREATE'); done=rows('WS30V13_ROUND_DONE'); deletes=rows('WS30V13_DELETE')
    assert len(creates)==len(deletes)==(1 if persistent else 3) and len(done)==3
    assert {r['serial'] for r in creates}=={r['serial'] for r in deletes}
    size=262144 if c['life_profile']==2 else 8192
    assert [d['snd_una'] for d in done]==([size,2*size,3*size] if persistent else [size]*3)
    pairs=[r for r in rows('WS30V14_PAIR') if r['switch']==4]
    releases=rows('WS30V13_RELEASE')
    sends=rows('WS30V13_FIRST_SEND');assert len(releases)==len(sends)==3
    assert [s['seq'] for s in sends]==([0,size,2*size] if persistent else [0,0,0])
    for r,s,d in zip(releases,sends,done):assert r['demand_ns']<=r['time_ns']<=s['time_ns']<=d['time_ns'] and r['demand_ns']==d['demand_ns']
    assert [r['demand_ns']-releases[0]['demand_ns'] for r in releases]==[0,10000000 if c['life_profile']==2 else 100000,20000000 if c['life_profile']==2 else 200000]
    if persistent:
        assert [r['round'] for r in releases]==[0,1,2] and [r['round'] for r in done]==[0,1,2]
        assert len({r['serial'] for r in releases+sends+done})==1
        for j in (1,2):assert done[j-1]['time_ns']<=releases[j]['time_ns'] and releases[j]['snd_una']==j*size
    queue=rows('WS30_QUEUE')
    if c['observe']:assert len(queue)==1 and queue[0]['enqueued']==queue[0]['dequeued'] and all(queue[0][k]==0 for k in ('dropped','current','violations','admission_dropped_bytes','queue_rejected_bytes'))
    if c['observe']:
        assert states
        initial=[s for s in states if s['event']=='created'];assert len(initial)==len(creates)
        assert all(s['rate']==s['target']==400000000000 and s['alpha']==1 and s['first_cnp']==1 for s in initial)
        for serial in {s['serial'] for s in states}:
            ss=[s for s in states if s['serial']==serial]
            for field in ('sack_events','cnp_events','recovery_events'):
                assert [s[field] for s in ss]==sorted(s[field] for s in ss)
        if c['arm']!='E':
            rounds=[]
            for j in range(3):
                hits=[p for p in pairs if p['time_ns']>=releases[j]['time_ns'] and (j==2 or p['time_ns']<releases[j+1]['time_ns'])]
                assert hits,'Missing actual first packet pair'
                first=min(hits,key=lambda p:p['time_ns']);assert first['first']!=first['second']
                sport=[10003,10006,10008][j] if c['lifecycle']==6 else 10003
                assert first['sport']==sport and first['dport']==100 and first['seq']==(j*size if persistent else 0)
                assert (first['first'],first['second'])==((3,2) if sport==10008 else (2,3))
                if c['life_profile']==1:assert first['q1']!=first['q2'],'Actual unequal queues not covered'
                if first['miss'] or c['arm']=='U12':assert first['chosen']==(first['second'] if first['q2']<first['q1'] else first['first'])
                rounds.append(first)
            if c['life_profile']==1:assert len({p['second'] if p['q2']<p['q1'] else p['first'] for p in rounds})==2,'Real lower-queue direction never changed'
            assert [p['miss'] for p in rounds]==([1,0,0] if c['lifecycle'] in (5,7) else [1,1,1])
            if persistent or c['lifecycle'] in (7,8):assert len({(p['first'],p['second']) for p in rounds})==1
            if c['arm']=='Q12' and c['lifecycle'] in (5,7):assert len({p['chosen'] for p in rounds})==1
            if c['lifecycle']==8:assert [r['erased'] for r in rows('WS30V13_CACHE_RESET') if r['switch']==4]==[1,1,1]
        if persistent:
            before=[s for s in states if s['event']=='release_before'];after=[s for s in states if s['event']=='release_after']
            assert len(before)==len(after)==2
            assert len({s['object'] for s in states})==1
            assert len({s['object'] for s in rxstates})==1
            assert all(s['snd_nxt']<=s['released'] for s in states)
            for a,b in zip(before,after):
                assert b['released']==a['released']+size
                assert {k:v for k,v in a.items() if k not in ('event','released')}=={k:v for k,v in b.items() if k not in ('event','released')}
                assert a['sack_bytes']==0 and a['recovery']==0
            if c['life_profile']==2:
                assert any(s['ecn_bits'] for s in rxstates),'Real queue ECN not covered; CNP alone is ambiguous'
                assert any(s['event']=='first_cnp' and s['cnp_events']>0 for s in states),'Real CNP not covered'
                assert any(s['event']=='rate_decrease' and s['cnp_events']>0 and s['rate']<400000000000 for s in states),'Real CNP rate decrease not covered'
                assert all(s['alpha']!=1 or s['rate']!=400000000000 or s['target']!=400000000000 for s in before),'Each CC boundary must retain noninitial state'
                assert all(s['cnp_events']>0 for s in before)
                if c['arm']=='U12':
                    assert any(s['seq']>s['expected_before'] and s['sack_bytes']>0 for s in rxstates),'Real receiver gap/SACK not covered'
                    assert any(s['event']=='sack_insert' and s['sack_bytes']>0 for s in states),'Real nonempty SACK not covered'
                    assert any(s['event']=='recovery_enter' and s['recovery'] for s in states)
                    assert all(s['sack_events']>0 and s['recovery_events']>0 for s in before)
    background.sort();p=(len(background)-1)*.99;i=int(p)
    return {'id':c['id'],'coverage_checked':bool(c['observe']),'lifecycle':c['lifecycle'],'profile':c['life_profile'],'round_latency_ns':[d['time_ns']-d['demand_ns'] for d in done],'background_p99_ns':background[i]+(background[min(i+1,len(background)-1)]-background[i])*(p-i),'fct_sha256':hashlib.sha256(fct.read_bytes()).hexdigest()}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--id',required=True);args=parser.parse_args()
    plan=json.loads((ROOT/'docs/research/evidence/ws30-v14-disabled-contract-r2.json').read_text(encoding='utf-8'))
    c=next(c for group in ('lifecycle','lifecycle_observation_controls') for c in plan[group] if c['id']==args.id)
    print(json.dumps(verify_lifecycle(c)))
