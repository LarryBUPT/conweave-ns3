"""Full-input tag metrics with a separate release origin for each class."""
import collections
import hashlib
import json
from pathlib import Path
from analyze_result import percentile

def summarize(folder):
    folder=Path(folder)
    meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    assert meta['status']=='SUCCEEDED'
    trace=folder/'config/traffic_trace.txt'
    assert hashlib.sha256(trace.read_bytes()).hexdigest()==meta['input_flow_sha256']
    pending={};srcport=collections.defaultdict(lambda:10000);dstport=collections.defaultdict(lambda:100)
    lines=trace.read_text().splitlines()
    for line in lines[1:]:
        f=line.split();src,dst,pg,size=map(int,f[:4]);start=round(float(f[4])*1e9)
        key=(src,dst,srcport[src],dstport[dst],size);srcport[src]+=1;dstport[dst]+=1
        assert key not in pending
        pending[key]=(int(f[5]) if len(f)==6 else 0,start)
    assert len(pending)==int(lines[0])
    raw=str(meta['raw_directory']);fct=folder/'raw'/raw/(raw+'_out_fct.txt');completed={}
    for line in fct.read_text().splitlines():
        vals=list(map(int,line.split()));assert len(vals)==8
        key=tuple(vals[:5]);assert key in pending and key not in completed
        assert abs(vals[5]-pending[key][1])<=2 and vals[6]>=0 and vals[7]>0
        completed[key]=(vals[6],vals[5]+vals[6])
    result={}
    for tag in sorted({v[0] for v in pending.values()}):
        keys=[k for k,v in pending.items() if v[0]==tag]
        origin=min(pending[k][1] for k in keys)
        times=sorted(completed[k][0]/1000 for k in keys if k in completed)
        full=len(times)==len(keys)
        result[str(tag)]={'input_flows':len(keys),'completed_flows':len(times),'release_origin_ns':origin,
                          'batch_us':(max(completed[k][1] for k in keys)-origin)/1000 if full else None,
                          **{f'p{p}_us':percentile(times,p) if times else None for p in (50,95,99)},
                          'max_us':max(times) if times else None}
    return {'tags':result,'fct_sha256':hashlib.sha256(fct.read_bytes()).hexdigest()}
