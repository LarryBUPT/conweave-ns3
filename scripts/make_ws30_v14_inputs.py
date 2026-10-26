"""Deterministic input preparation only. Never invokes ns-3, SSH or run.py."""
import collections
import hashlib
import json
from pathlib import Path
import random

ROOT=Path(__file__).resolve().parents[1]
MASK=0xffffffff
def rol(x,n):return ((x<<n)|(x>>(32-n)))&MASK
def ecmp(words,seed):
    h=seed
    for k in words:
        k=rol(k*0xcc9e2d51&MASK,15)*0x1b873593&MASK
        h=rol(h^k,13);h=(5*h+0xe6546b64)&MASK
    h^=12;h^=h>>16;h=h*0x85ebca6b&MASK;h^=h>>13
    h=h*0xc2b2ae35&MASK;h^=h>>16
    return h
def pair(port):
    words=[0x0b000001,0x0b000301,port|(100<<16)]
    return [2+ecmp(words,4)%2,2+ecmp(words,4^0x9e3779b9)%2]
def stamp(t):return '%d.%09d'%divmod(t,10**9)
def freeze(path,data):
    if path.exists():assert path.read_bytes()==data,str(path)
    else:path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
def trace(name,rows):
    rows=sorted(rows,key=lambda r:(r[0],r[5]==2,r[1],r[6]))
    data=(str(len(rows))+'\n'+'\n'.join('%d %d 3 %d %s %d'%(s,d,size,stamp(t),tag) for t,s,d,size,_,tag,_ in rows)+'\n').encode()
    digest=freeze(ROOT/'config'/name,data)
    return {'file':name,'sha256':digest,'flows':len(rows),'payload_bytes':sum(r[3] for r in rows),'tags':dict(collections.Counter(str(r[5]) for r in rows))}
def generate():
    ports=[p for p in range(10000,65536) if len(set(pair(p)))==2][:3]
    assert ports==[10003,10006,10008]
    out={'schema_version':3,'simulation_seed':1,'probe_ports':ports,'probe_pairs':{str(p):pair(p) for p in ports},'selection':'Lowest three ports having distinct native candidates; no simulation or performance search','files':[]}
    base=(ROOT/'config/ws30_composition8.txt').read_bytes()
    for profile in ('pair','state'):
        topo=base if profile=='pair' else base.replace(b'4 5 40Gbps 1000ns',b'4 5 40Gbps 10000ns')
        name='ws30v14_%s8.txt'%profile
        out['files'].append({'file':name,'sha256':freeze(ROOT/'config'/name,topo),'kind':'topology'})
        interval=100000 if profile=='pair' else 10000000
        request=8192 if profile=='pair' else 262144
        offset=2000 if profile=='pair' else 20000
        for policy in ('persistent','fresh','reuse'):
            rows=[]
            for r in range(3):
                t=2000000000+r*interval
                if profile=='pair':rows.append((t,0,1 if r%2==0 else 2,81920,3,1,0))
                else:
                    for src in (1,2):
                        for j in range(4):rows.append((t,src,3,2097152,3,1,j))
                if policy!='persistent' or r==0:
                    rows.append((t+offset,0,3,request*(3 if policy=='persistent' else 1),3,2,0))
            item=trace('ws30v14_life_%s_%s.txt'%(profile,policy),rows)
            item.update(profile=profile,policy=policy,round_bytes=request,round_interval_ns=interval)
            out['files'].append(item)
    for seed in (20263101,20263102):
        rng=random.Random(seed); hosts=list(range(0,1280,4))
        experts=sorted(rng.sample(hosts,256)); background=sorted(set(hosts)-set(experts))
        pairs=[];used=set()
        while len(pairs)<192:
            a,b=rng.choice(background),rng.choice(background)
            if a!=b and (a,b) not in used:used.add((a,b));pairs.append((a,b))
        peers={s:sorted(rng.sample([d for d in experts if d!=s],64)) for s in experts}
        for s in experts:rng.shuffle(peers[s])
        for schedule,offset in (('concurrent',0),('lead20us',20000)):
            rows=[(2000000000,s,d,67108864,3,1,j) for j,(s,d) in enumerate(pairs[:32])]
            for r in range(8):
                rows.extend((2000000000+offset+r*100000,s,d,8192,3,2,j) for s in experts for j,d in enumerate(peers[s][r*8:(r+1)*8]))
            item=trace('ws30w5_seed%d_%s.txt'%(seed,schedule),rows)
            assert item['flows']==16416 and item['payload_bytes']==2281701376
            item.update(demand_seed=seed,schedule=schedule)
            out['files'].append(item)
            if seed==20263101 and not offset:
                ordered=sorted(rows,key=lambda r:(r[0],r[5]==2,r[1],r[6]))
                prefix=[r for r in ordered if r[5]==1]+[r for r in ordered if r[5]==2 and r[0]==2000000000][:128]
                item=trace('ws30w5_sustained_prefix.txt',prefix);item.update(demand_seed=seed,schedule='concurrent-prefix');out['files'].append(item)
    return out
if __name__=='__main__':
    out=generate();p=ROOT/'docs/research/evidence/ws30-v14-input-manifest-r1.json'
    freeze(p,(json.dumps(out,indent=2,sort_keys=True)+'\n').encode())
    print('Prepared %d immutable input/topology files; no simulation.'%len(out['files']))
