"""Observed source-arrival intervals per borrower and owner activation.

Local reading of one old technical run. No physical-capacity recovery inference.
"""
from collections import defaultdict
from pathlib import Path
import csv
import hashlib
import json


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    m = Path(__file__).resolve().parents[1]
    acceptance = m/'evidence/dynamic-c3-main-acceptance-r1.json'
    a = json.loads(acceptance.read_text(encoding='utf-8'))
    index = m.parent/'independent/main-mode-dynamic-r1-index.json'
    idx = json.loads(index.read_text(encoding='utf-8'))
    base = Path(next(c['results_path'] for c in idx['cells'] if c['id']==a['id']))
    log = next((base/'raw').glob('*/config.log'))
    trace, topo = base/'config/traffic_trace.txt',base/'config/topology.txt'
    out, rows_out = m/'evidence/c3-source-interval-screen-r1.json',m/'evidence/c3-source-interval-screen-r1.csv'
    if out.exists() or rows_out.exists():
        raise FileExistsError('Preserve existing interval screen; do not repeat.')
    assert sha(log)==a['log_sha256']
    assert sha(trace)==a['inputs']['config/ws31_correctness_r1.txt']
    assert sha(topo)==a['inputs']['config/leaf_spine_128_100G_OS2.txt']
    lines=topo.read_text().splitlines();switches=set(map(int,lines[1].split()));host_tor={}
    for line in lines[2:2+int(lines[0].split()[2])]:
        u,v=map(int,line.split()[:2])
        if u not in switches and v in switches:host_tor[u]=v
        if v not in switches and u in switches:host_tor[v]=u
    sp,dp=defaultdict(lambda:10000),defaultdict(lambda:100);flows={}
    for line in trace.read_text().splitlines()[1:]:
        src,dst,pg,size,start,tag=line.split();src,dst=int(src),int(dst)
        k=(src,dst,sp[src],dp[dst]);sp[src]+=1;dp[dst]+=1
        flows[k]={'size':int(size),'tag':int(tag)}
    entries, sides, last, episodes, serial = {},{}, {}, {},defaultdict(int)
    groups={};route_count=residual_count=residual_bytes=0
    with log.open(encoding='utf-8') as f:
        for line_number,line in enumerate(f):
            prefix=line.split(' ',1)[0]
            if prefix=='WS30V13_CACHE_RESET':
                raise ValueError('Unexpected lifecycle reset in fixed reference.')
            if prefix not in ('WS31_C3_ROUTE','WS30_ROUTE'):
                continue
            v={k:int(x) for k,x in (t.split('=',1) for t in line.split()[1:])}
            key=((v['sip']>>8)&65535,(v['dip']>>8)&65535,v['sport'],v['dport'])
            sw,now=v['switch'],v['time_ns']
            if sw!=host_tor[key[0]]:continue
            packet=(key,now,v['seq'])
            if prefix=='WS31_C3_ROUTE':
                assert packet not in sides;sides[packet]=v
                if v['fresh']:
                    assert key not in entries
                    entries[key]=v
                continue
            route_count+=1
            entry=entries[key];category=entry['category'];owner=entry['owner']
            assert category==flows[key]['tag']==v['tag'] and entry['chosen']==v['port']
            catkey=(sw,category)
            if category:
                if catkey not in last or now-last[catkey]>=20000:
                    serial[catkey]+=1
                    ep=(sw,category,serial[catkey])
                    episodes[ep]={'switch':sw,'owner':category,'activation_id':serial[catkey],
                                  'activation_ns':now,'last_owner_arrival_ns':now}
                last[catkey]=now
                episodes[(sw,category,serial[catkey])]['last_owner_arrival_ns']=now
            residual=entry['borrowed'] and (sw,owner) in last and now-last[(sw,owner)]<20000
            side=sides.pop(packet,None)
            if side is not None:
                assert bool(side['residual'])==bool(residual)
            if residual:
                assert side is not None
                wire=min(1000,flows[key]['size']-v['seq'])+48
                assert wire==side['wire_bytes']
                ep=(sw,owner,serial[(sw,owner)])
                group=(ep,key)
                if group not in groups:
                    groups[group]={'switch':sw,'port':entry['chosen'],'owner':owner,
                        'activation_id':ep[2],'activation_ns':episodes[ep]['activation_ns'],
                        'borrower_src':key[0],'borrower_dst':key[1],
                        'borrower_sport':key[2],'borrower_dport':key[3],
                        'first_residual_source_arrival_ns':now,'last_residual_source_arrival_ns':now,
                        'residual_packets':0,'residual_wire_bytes':0}
                g=groups[group];g['last_residual_source_arrival_ns']=now
                g['residual_packets']+=1;g['residual_wire_bytes']+=wire
                residual_count+=1;residual_bytes+=wire
    assert not sides and len(entries)==104 and route_count==202056
    assert residual_count==a['mechanism_replay']['residual_packets']==546
    assert residual_bytes==a['mechanism_replay']['residual_wire_bytes']==572208
    rows=[]
    for (ep,key),g in groups.items():
        g['observed_span_ns']=g['last_residual_source_arrival_ns']-g['first_residual_source_arrival_ns']
        g['last_residual_minus_activation_ns']=g['last_residual_source_arrival_ns']-g['activation_ns']
        g['owner_activity_lease_end_ns']=episodes[ep]['last_owner_arrival_ns']+20000
        rows.append(g)
    rows.sort(key=lambda x:(x['switch'],x['owner'],x['activation_id'],x['port'],x['borrower_sport']))
    with rows_out.open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    result={'scope':'Source-arrival overlap intervals in one existing technical C3 run; NOT physical recovery times',
        'reference_id':a['id'],'source_sha':a['source_sha'],'activity_window_ns':20000,
        'source_arrivals':route_count,'borrowed_entries':sum(e['borrowed'] for e in entries.values()),
        'owner_activation_episodes':list(episodes.values()),'borrower_episode_groups':len(rows),
        'residual_packets':residual_count,'residual_wire_bytes':residual_bytes,
        'max_observed_span_ns':max(r['observed_span_ns'] for r in rows),
        'max_last_residual_minus_activation_ns':max(r['last_residual_minus_activation_ns'] for r in rows),
        'physical_recovery_duration_observable':False,
        'missing':['Per-packet actual egress service/dequeue interval and downstream/in-flight closure.',
                   'Proof of when owner traffic can obtain reclaimed capacity; last source residual arrival is not that proof.'],
        'interpretation':['Owner activity is a rolling last-arrival lease, not a fixed20us episode.',
                          'Rows ending before an activity lease do not prove borrower completion or physical queue empty.',
                          'Long inactive gaps can split the same borrower into multiple owner episodes.',
                          'Actual completion/capacity and independent effects remain unverified.'],
        'inputs_sha256':{str(p):sha(p) for p in [log,trace,topo,acceptance,index]},
        'script_sha256':sha(Path(__file__)),'rows_csv_sha256':sha(rows_out)}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['borrower_episode_groups','residual_packets',
        'residual_wire_bytes','max_observed_span_ns','max_last_residual_minus_activation_ns',
        'physical_recovery_duration_observable']},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
