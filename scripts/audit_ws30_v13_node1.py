"""Read-only raw audit for v13 node 1; writes only a new evidence directory."""
import collections
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import random
import statistics as st
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT.parents[1]
OUT = ROOT / 'docs/research/evidence/ws30-v13-node1-r1'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def quant(v, p):
    s = sorted(v); x = (len(s)-1)*p; a = int(x)
    return s[a] + (s[min(a+1, len(s)-1)]-s[a])*(x-a)

def table(name, rows):
    with (OUT/name).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def main():
    OUT.mkdir(exist_ok=False)
    frozen = ROOT / 'docs/research/evidence/ws30-v12-r1'
    before = {str(p.relative_to(frozen)): sha(p) for p in frozen.rglob('*') if p.is_file()}
    receipts = read(ROOT/'docs/research/evidence/ws30-stage3-main-results-r5.json')['rows']
    selected = [r for r in receipts if r['arm'] in ('E', 'Q12')]
    assert len(selected) == 48
    byseed = {}; audits = []
    for r in selected:
        folder = ROOT/'results'/r['id']; m = read(folder/'metadata.json')
        trace = folder/'config/traffic_trace.txt'; topo = folder/'config/topology.txt'
        raw = str(m['raw_directory']); fct = folder/'raw'/raw/(raw+'_out_fct.txt')
        assert m['status'] == 'SUCCEEDED' and m['git_commit'] == r['source_sha']
        assert sha(trace) == r['trace_sha256'] and sha(fct) == r['fct_sha256']
        assert sha(topo) == m['topology_sha256']
        expected = {}; sp = collections.defaultdict(lambda:10000); dp = collections.defaultdict(lambda:100)
        lines = trace.read_text(encoding='utf-8').splitlines()
        assert int(lines[0]) == len(lines)-1 == 16576
        for line in lines[1:]:
            a = line.split(); s,d,pg,n = map(int,a[:4]); k=(s,d,sp[s],dp[d],n)
            assert k not in expected
            expected[k]=(int(a[5]),int(Decimal(a[4])*10**9)); sp[s]+=1; dp[d]+=1
        allflows={}
        for line in fct.read_text(encoding='utf-8').splitlines():
            a=list(map(int,line.split())); k=tuple(a[:5]); assert k in expected and k not in allflows
            assert abs(a[5]-expected[k][1]) <= 1
            allflows[k]=(a[6], a[5]+a[6])
        assert allflows.keys() == expected.keys()
        moe={k:v[1]-expected[k][1] for k,v in allflows.items() if expected[k][0]==2}
        bg=[v[0] for k,v in allflows.items() if expected[k][0]==1]
        assert len(moe)==16384 and len(bg)==192
        seed=int(r['id'].split('-s')[-1].split('-')[0])
        byseed.setdefault(seed,{})[r['arm']]=(moe,bg)
        audits.append({'id':r['id'],'source_sha':m['git_commit'],'trace_sha256':sha(trace),
                       'fct_sha256':sha(fct),'topology_sha256':sha(topo),'rows':len(allflows)})
    rows=[]; top=[]; cdf=[]
    for seed, arms in sorted(byseed.items()):
        e,eb=arms['E']; q,qb=arms['Q12']; assert e.keys()==q.keys()
        old=max(e,key=e.get); new=max(q,key=q.get); delta=max(q.values())-max(e.values())
        old_gain=q[old]-e[old]; replacement=max(q.values())-q[old]
        assert delta==old_gain+replacement
        rows.append({'seed':seed,'batch_change_pct':100*(max(q.values())/max(e.values())-1),
            'background_p99_change_pct':100*(quant(qb,.99)/quant(eb,.99)-1),
            'old_tail_key':str(old),'new_tail_key':str(new),'tail_switched':old!=new,
            'old_tail_E_ns':e[old],'old_tail_Q12_ns':q[old],
            'new_tail_E_ns':e[new],'new_tail_Q12_ns':q[new],
            'batch_delta_ns':delta,'old_tail_delta_ns':old_gain,'replacement_gap_ns':replacement,
            'improved_flows':sum(q[k]<e[k] for k in e),'worsened_flows':sum(q[k]>e[k] for k in e),
            'equal_flows':sum(q[k]==e[k] for k in e)})
        order=sorted(e,key=lambda k:(-e[k],k))
        for n in (1,4,16,64,256):
            keys=order[:n]
            top.append({'seed':seed,'k':n,'selection':'ECMP-ranked fixed flow identities',
                'mean_delta_ns':st.mean(q[k]-e[k] for k in keys),
                'median_flow_change_pct':st.median(100*(q[k]/e[k]-1) for k in keys),
                'improved':sum(q[k]<e[k] for k in keys)})
        for arm,v in [('E',e),('Q12',q)]:
            for p in (0,.1,.25,.5,.75,.9,.95,.99,.999,1):
                cdf.append({'seed':seed,'arm':arm,'quantile':p,'completion_from_demand_ns':quant(v.values(),p)})
    rng=random.Random(20263003); draws=[[rng.randrange(24) for _ in range(24)] for _ in range(10000)]
    estimates={}
    for key in ('batch_change_pct','background_p99_change_pct'):
        v=[r[key] for r in rows]; boot=[st.median(v[i] for i in ix) for ix in draws]
        estimates[key]={'median':st.median(v),'ci95':[quant(boot,.025),quant(boot,.975)]}
    # All 1050 ledger paths are tested without changing frozen evidence.
    ledger=read(frozen/'D4-experiments.json')['successes']
    path_audit={'entries':len(ledger),'literal_existing_directories':sum(Path(r['local_directory']).is_dir() for r in ledger)}
    context=Path('C:/Users/Administrator/.codex/sessions/2026/10/26/rollout-2026-10-26T04-37-01-01a174c7-ecf5-7f21-a9dc-6f8b4f5634b8.jsonl')
    tc=[json.loads(l)['payload'] for l in context.read_text(encoding='utf-8').splitlines() if json.loads(l).get('type')=='turn_context'][-1]
    model={'model':tc['model'],'effort':tc.get('effort'),'turn_id':tc['turn_id']}
    assert model['model']=='gpt-6.1-sol' and model['effort']=='medium'
    inputs=[PAPER/'thesis/classreserve-v12-reading.md',PAPER/'thesis/ws30-v12-reproducibility-index.md']
    inputs += list((PAPER/'paper review').glob('*/v12-review.md'))
    source=ROOT/'src/point-to-point/model/switch-node.cc'
    blobs={}
    for rev in ('1ef424749e3c551dd788d0a709bd8e21c7cc89c9','ee236f27920aa56b3dd562ed971e5abee9e1e659'):
        b=subprocess.check_output(['git','-c','safe.directory='+str(ROOT).replace('\\','/'),'show',rev+':src/point-to-point/model/switch-node.cc'],cwd=ROOT)
        a=b.index(b'uint32_t SwitchNode::DoLbDrill('); z=b.index(b'/*------------------ConWeave',a)
        blobs[rev]=hashlib.sha256(b[a:z]).hexdigest()
    assert len(set(blobs.values()))==1
    table('tail-decomposition.csv',rows); table('ecmp-topk-paired.csv',top); table('per-demand-quantiles.csv',cdf)
    result={'scope':'v13 node1 local raw audit; no simulations','model':model,'verified_raw_cells':48,
        'verified_raw_rows':sum(r['rows'] for r in audits),'raw_audit':audits,'estimates':estimates,
        'tail_switched_demands':sum(r['tail_switched'] for r in rows),
        'batch_improved_demands':sum(r['batch_change_pct']<0 for r in rows),
        'median_improved_flow_fraction':st.median(r['improved_flows']/16384 for r in rows),
        'median_old_tail_delta_ns':st.median(r['old_tail_delta_ns'] for r in rows),
        'median_replacement_gap_ns':st.median(r['replacement_gap_ns'] for r in rows),
        'ledger_path_audit':path_audit,'drill_function_blob_hashes':blobs,
        'input_hashes':{str(p.relative_to(PAPER)):sha(p) for p in inputs},'source_file_sha256':sha(source),
        'frozen_v12_files_unchanged':before=={str(p.relative_to(frozen)):sha(p) for p in frozen.rglob('*') if p.is_file()},
        'frozen_v12_file_hashes':before,
        'interpretation':'Algebraic max decomposition, not causal mediation; top-k selection uses baseline only; no pooled-flow confidence intervals.'}
    assert result['frozen_v12_files_unchanged']
    (OUT/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('verified_raw_cells','verified_raw_rows','estimates','tail_switched_demands','batch_improved_demands','median_improved_flow_fraction','median_old_tail_delta_ns','median_replacement_gap_ns','ledger_path_audit','frozen_v12_files_unchanged','model')},ensure_ascii=False))

if __name__=='__main__': main()
