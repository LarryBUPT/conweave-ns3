"""Prepare P0/P1/P2 and small qualification inputs; never execute simulations."""
import collections
import hashlib
import json
from pathlib import Path
from make_ws25_demand import make

ROOT = Path(__file__).resolve().parents[1]
MODES = {'E':0,'Q':33,'R':34,'T':36,'U':35,'D':2,'A':37,'conga':3,'letflow':6}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def frozen(p, data):
    if p.exists():
        if p.read_bytes() != data: raise RuntimeError('Occupied immutable input: '+str(p))
    else: p.write_bytes(data)

def identities(data):
    lines=data.decode().splitlines();sp=collections.defaultdict(lambda:10000);dp=collections.defaultdict(lambda:100)
    result=[]
    for line in lines[1:]:
        a=line.split();s,d,pg,size=map(int,a[:4]);tag=int(a[5]);origin=int(round(float(a[4])*1e9))
        result.append([s,d,sp[s],dp[d],size,origin,tag]);sp[s]+=1;dp[d]+=1
    assert len(result)==int(lines[0])
    assert len({tuple(x[:6]) for x in result})==len(result)
    return result

def prepare(selection):
    assert selection['held_out_generation_seeds']==list(range(20264021,20264045))
    assert selection['auxiliary_generation_seeds']==[20264024,20264026,20264029,20264031,20264034,20264041,20264042,20264044]
    assert selection['persistent_generation_seeds']==[20264024,20264026,20264034,20264041]
    records=[]
    for seed in selection['held_out_generation_seeds']:
        name='ws25_seed%d_b192.txt'%seed
        # Existing generator checks exact bytes; it is not a performance search.
        make(seed,ROOT/'config',levels=(192,))
        p=ROOT/'config'/name; ids=identities(p.read_bytes())
        records.append(dict(seed=seed,trace=name,sha256=sha(p),flows=len(ids),payload_bytes=sum(x[4] for x in ids),identity_sha256=hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest()))
    # Qualification never uses the 24 held-out demands.
    lines=[]
    for i in range(8): lines.append('%d %d 3 32768 2.000000000 1'%((i%4)*4,320+(i%4)*4))
    for i in range(16): lines.append('%d %d 3 8192 2.000000000 2'%(64+(i%8)*4,320+(i%4)*4))
    frozen(ROOT/'config/pv14-qualification.txt',(str(len(lines))+'\n'+'\n'.join(lines)+'\n').encode())
    # Old controlled technical traffic is retained under a new qualification name.
    frozen(ROOT/'config/pv14-pressure.txt',(ROOT/'config/ws30_technical168.txt').read_bytes())
    result=dict(selection=selection,heldout=records,qualification=[])
    for name in ('pv14-qualification.txt','pv14-pressure.txt'):
        p=ROOT/'config'/name;ids=identities(p.read_bytes());result['qualification'].append(dict(trace=name,sha256=sha(p),flows=len(ids),payload_bytes=sum(x[4] for x in ids)))
    return result

def config(base,mode,seed,trace,qualification=False):
    rows=[]
    for line in base.splitlines():
        a=line.split()
        if not a: rows.append(line);continue
        key=a[0]
        if key=='TOPOLOGY_FILE':line='TOPOLOGY_FILE config/topology.txt'
        elif key=='FLOW_FILE':line='FLOW_FILE config/traffic_trace.txt'
        elif key=='LB_MODE':line='LB_MODE '+str(MODES[mode])
        elif key=='RANDOM_SEED':line='RANDOM_SEED '+str(seed)
        elif key.endswith('_FILE') and len(a)==2 and a[1].startswith('mix/output/'):
            tail=a[1].split('/')[-1].split('_',1)[1];line=key+' raw/1/1_'+tail
        elif qualification and key in ('QLEN_MON_END','FLOWGEN_STOP_TIME'):line=key+' 2.001'
        rows.append(line)
    return '\n'.join(rows)+'\n'

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--selection',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    d=prepare(json.loads(a.selection.read_text(encoding='utf-8-sig')))
    frozen(a.out,(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode())
