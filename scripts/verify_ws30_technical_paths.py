"""Independent checks of actual packet paths and logged decision inputs."""
import collections
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'docs/research/evidence/ws30-stage2-recovery-plan-r1.json'
def kv(line):return {k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)}
def key(r):return tuple(r[x] for x in ['switch','sip','dip','sport','dport'])
def topology(path):
    lines=path.read_text().splitlines();sw=set(map(int,lines[1].split()))
    counters=collections.defaultdict(lambda:1);edges={}
    for line in lines[2:]:
        f=line.split();a,b=map(int,f[:2])
        edges[(a,counters[a])]=b;edges[(b,counters[b])]=a
        counters[a]+=1;counters[b]+=1
    return sw,edges
def parse(cell):
    folder=ROOT/'results'/cell['id'];log=folder/'logs/config.log'
    routes=[];choices=[];qps=[]
    for line in log.read_text(encoding='utf-8').splitlines():
        if line.startswith('WS30_ROUTE '):routes.append(kv(line))
        elif line.startswith('WS30_CHOICE '):choices.append(kv(line))
        elif line.startswith('WS30_QP '):qps.append(kv(line))
    assert routes
    assert len(qps)==cell['input_flows']
    for q in qps:
        assert q['fd_feedback_frames']==q['fd_without_sack']+q['sack_feedback']
        assert (q['retransmit_packets']==0)==(q['retransmit_bytes']==0)
    switches,edges=topology(folder/'config/topology.txt')
    packets=collections.defaultdict(list)
    for r in routes:packets[(r['uid'],r['sip'],r['dip'],r['sport'],r['dport'],r['seq'])].append(r)
    qp_paths=collections.defaultdict(set)
    for packet,parts in packets.items():
        parts.sort(key=lambda r:r['time_ns'])
        src=(parts[0]['sip']>>8)&0xffff;dst=(parts[0]['dip']>>8)&0xffff
        assert edges[(src,1)]==parts[0]['switch'],('Missing source hop',cell['id'],packet)
        for a,b in zip(parts,parts[1:]):
            assert edges[(a['switch'],a['port'])]==b['switch'],('Broken path',cell['id'],packet)
        assert edges[(parts[-1]['switch'],parts[-1]['port'])]==dst,('Missing destination hop',cell['id'],packet)
        qp=packet[1:5]
        qp_paths[qp].add(tuple((r['switch'],r['port']) for r in parts))
    varied=sum(len(paths)>1 for paths in qp_paths.values())
    if cell['arm']!='U16':assert varied==0,('Pinned end-to-end path changed',cell['id'])
    by_choice={key(c):c for c in choices};assert len(by_choice)==len(choices)
    adjacency=collections.defaultdict(list)
    for (node,port),peer in edges.items():adjacency[node].append(peer)
    distances={}
    def toward(dst,sw):
        if dst not in distances:
            d={dst:0};todo=collections.deque([dst])
            while todo:
                n=todo.popleft()
                for peer in adjacency[n]:
                    if peer not in d:d[peer]=d[n]+1;todo.append(peer)
            distances[dst]=d
        d=distances[dst]
        return {port for (node,port),peer in edges.items() if node==sw and d[peer]+1==d[sw]}
    for r in routes:
        if r['tag'] not in (1,2) or cell['arm']=='E':continue
        c=by_choice[key(r)];assert r['port'] in (c['first'],c['second'])
    branch=collections.Counter()
    for c in choices:
        allowed=toward((c['dip']>>8)&0xffff,c['switch'])
        assert c['first'] in allowed and c['second'] in allowed
        if len(allowed)==1:branch['single_exit']+=1
        elif c['first']==c['second']:branch['hash_collision']+=1
        if c['first']==c['second']:branch['same_candidate']+=1
        else:
            if c['q1']==c['q2']==0:branch['empty_tie']+=1
            elif c['q1']==c['q2']:branch['nonempty_tie']+=1
            else:branch['strict_total_order']+=1
            if c['b1']!=c['b2']:branch['different_background_composition']+=1
            if c['q1']==c['q2'] and c['b1']!=c['b2']:branch['same_total_different_composition']+=1
            if (c['q2']<c['q1'])!=(c['q2']+c['b2']<c['q1']+c['b1']):branch['a_changes_choice']+=1
        mode=cell['arm'];expected=None
        if mode in ('H16','H12'):expected=c['first']
        elif mode in ('Q16','Q12','U16'):expected=c['second'] if c['q2']<c['q1'] else c['first']
        elif mode=='M16':expected=c['first'] if c['tag']==1 or c['q2']>=c['q1'] else c['second']
        elif mode in ('C16','cr-a1-b1'):
            a=c['q1']+(c['b1'] if c['tag']==2 else 0)
            b=c['q2']+(c['b2'] if c['tag']==2 else 0)
            expected=c['second'] if b<a else c['first']
        if expected is not None:assert c['chosen']==expected,('Decision violates logged inputs',cell['id'],c)
    signature=sorted(tuple(r[x] for x in ['time_ns','switch','sip','dip','sport','dport','seq','port']) for r in routes)
    return {'id':cell['id'],'arm':cell['arm'],'full_packets':len(packets),'data_hops':len(routes),
            'qps':len(qp_paths),'end_to_end_varied_qps':varied,'decision_branches':dict(branch),
            'route_signature_sha256':hashlib.sha256(json.dumps(signature).encode()).hexdigest(),
            'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()}
def main():
    plan=json.loads(PLAN.read_text());cells=[c for c in plan['technical'] if c['observe']==2]
    rows=[parse(c) for c in cells]
    byid={r['id']:r for r in rows}
    e=next(c for c in cells if c['arm']=='E' and c['trace']=='ws30_technical168.txt')
    h=next(c for c in cells if c['arm']=='H12' and c['trace']=='ws30_technical168.txt')
    assert byid[e['id']]['route_signature_sha256']==byid[h['id']]['route_signature_sha256']
    u=next(c for c in cells if c['arm']=='U16' and c['trace']=='ws30_technical168.txt')
    assert byid[u['id']]['end_to_end_varied_qps']>0,'U16 did not exercise port reselection'
    branches=collections.Counter()
    for row in rows:branches.update(row['decision_branches'])
    for needed in ['single_exit','hash_collision','same_candidate','empty_tie','strict_total_order','different_background_composition']:
        assert branches[needed]>0,('Uncovered branch',needed)
    result={'source_core_sha':plan['core_source_sha'],'verified_full_log_cells':len(rows),'branches':dict(branches),'rows':rows,
            'scope':'all accepted data packets; first-to-last switch reconstructed from topology; transport counters stop at QP completion'}
    dest=ROOT/'docs/research/evidence/ws30-technical-paths-recovered-r1.json'
    encoded=json.dumps(result,indent=2,sort_keys=True)+'\n'
    if dest.exists():assert dest.read_text()==encoded
    else:dest.write_text(encoded,encoding='utf-8')
    print(json.dumps({'verified_cells':len(rows),'branches':dict(branches)}))
if __name__=='__main__':main()
