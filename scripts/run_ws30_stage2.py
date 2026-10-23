"""Frozen WS-30 technical/resource execution. Does not start formal matrices."""
import argparse
import collections
import datetime
import hashlib
import json
import re
import time
from pathlib import Path

import analyze_ws30_tags
import run_ws25_formal as engine
import run_ws25_preflight as remote
import run_ws25_resource_pilot as resources

ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'docs/research/evidence'
SOURCE='3e3367a41ee5f6a119e3ba1c8a5dcb41744785dc'
MANIFEST=EV/'ws30-inputs-v2.json'
PLAN=EV/'ws30-execution-plan-r3.json'
RECEIPTS=ROOT/'results/ws30-stage2-receipts-r3.jsonl'
SUMMARY=ROOT/'results/ws30-stage2-summary-r3.json'
ARMS={'E':'fecmp','H16':'ws30-h16','R16':'ws30-r16','Q16':'cr-a0-b1',
      'C16':'classreserve','U16':'ws30-u16','Q12':'ws30-q12','M16':'cr-a0-b0','H12':'ws30-h12'}
PREFIX='20261024-210000-ws30'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def frozen(path,obj):
    data=json.dumps(obj,indent=2,sort_keys=True)+'\n'
    if path.exists():
        if path.read_text(encoding='utf-8')!=data:raise RuntimeError('Frozen artifact differs: '+str(path))
    else:path.write_text(data,encoding='utf-8')
def makecell(name,arm,trace,obs,role,seed=0,cap=4):
    path=ROOT/'config'/trace;lines=path.read_text().splitlines();counts=collections.Counter()
    for line in lines[1:]:
        f=line.split();counts[f[5] if len(f)==6 else '0']+=1
    return {'id':PREFIX+'-'+name,'arm':arm,'mode':ARMS.get(arm,arm),'trace':trace,
            'trace_sha256':sha(path),'input_flows':int(lines[0]),'expected_tags':dict(counts),
            'observe':obs,'role':role,'seed':seed,'background':counts.get('1',0),
            'cap':cap,'run_order':0,'batch':0}
def makeplan():
    technical=[]
    def tech(arm,trace='ws30_technical168.txt',obs=2,role='technical',seed=0):
        c=makecell(f't{len(technical)+1:02d}-{arm.lower()}-o{obs}',arm,trace,obs,role,seed)
        technical.append(c);return c
    for arm in ARMS:tech(arm)
    for arm in ['E','Q16','C16','U16']:tech(arm,obs=0)
    tech('cr-a1-b1')
    for arm in ['E','Q16','C16']:tech(arm,'ws30_technical168_lead.txt')
    for arm in ARMS:tech(arm,'ws30_fivecol4.txt')
    bridge=[]
    for seed in [20262521,20262721]:
        for arm in ['E','C16']:
            c=tech(arm,f'ws25_seed{seed}_b192.txt',obs=0,role='bridge-precheck',seed=seed)
            bridge.append(c)
    for arm in ['Q16','M16']:
        tech(arm,'ws25_seed20262921_b192.txt',obs=0,role='ablation-precheck',seed=20262921)
    assert len(technical)==32
    for seed in list(range(20262521,20262545))+list(range(20262721,20262745)):
        for arm in ['E','C16']:
            if any(c['seed']==seed and c['arm']==arm for c in bridge):continue
            bridge.append(makecell(f'bridge-s{seed}-{arm.lower()}',arm,
                                  f'ws25_seed{seed}_b192.txt',0,'historical-bridge',seed,12))
    pilot=[]
    for cap in [4,8,12]:
        for repeat in range(cap//4):
            for arm in ['Q16','C16','U16','R16']:
                pilot.append(makecell(f'p-c{cap:02d}-r{repeat+1}-{arm.lower()}',arm,
                                      'ws25_seed20262501_b192.txt',1,'resource-only',20262501,cap))
    design=json.loads((EV/'ws30-stage1-design.json').read_text())
    main=[makecell(f'main-s{c["demand_seed"]}-{c["arm"].lower()}',c['arm'],
                   f'ws25_seed{c["demand_seed"]}_b192.txt',1,'main',c['demand_seed'],12)
          for c in design['main_cells']]
    lead=[makecell(f'lead-s{c["demand_seed"]}-{c["arm"].lower()}',c['arm'],
                   f'ws30_seed{c["demand_seed"]}_lead20us.txt',1,'lead20us',c['demand_seed'],12)
          for c in design['background_lead_cells']]
    allcells={c['id']:c for c in technical+pilot+bridge+main+lead}
    assert len(allcells)==412
    for order,c in enumerate(allcells.values(),1):c['run_order']=order
    return {'source_sha':SOURCE,'input_manifest_sha256':sha(MANIFEST),
            'topology_sha256':'74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba',
            'technical':technical,'pilot':pilot,'bridge':bridge,'main':main,'lead':lead,
            'formal_execution_enabled':False,
            'directed_composition':'12 actual-queue fixture IDs remain for separate freeze before stage 3',
            'source_and_input_frozen_before_execution':True}
def kv(line):return {k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)}

def verify(cell):
    folder=ROOT/'results'/cell['id'];meta=json.loads((folder/'metadata.json').read_text())
    assert meta['status']=='SUCCEEDED' and meta['git_commit']==SOURCE and meta['algorithm']==cell['mode']
    assert meta['seed']==1 and meta['input_flow_sha256']==cell['trace_sha256']
    assert meta['topology_sha256']==makeplan()['topology_sha256']
    assert meta['concurrency_cap']==cell['cap']
    params=meta['parameters']
    for k,v in {'pfc':0,'irn':1,'bw':400,'buffer':9,'simul_time':'0.01','netload':10,
                'flow_file':cell['trace'],'ws30_observe':cell['observe']}.items():assert params[k]==v,(cell['id'],k)
    assert sha(folder/'config/topology.txt')==meta['topology_sha256']
    stats=analyze_ws30_tags.summarize(folder)
    assert {k:v['input_flows'] for k,v in stats['tags'].items()}==cell['expected_tags']
    assert all(v['completed_flows']==v['input_flows'] for v in stats['tags'].values())
    log=(folder/'logs/config.log').read_text(encoding='utf-8',errors='replace')
    assert 'WS30_OBSERVATION_OVERFLOW' not in log
    observation={}
    if cell['observe']:
        def one(prefix):
            found=[l for l in log.splitlines() if l.startswith(prefix+' ')]
            assert len(found)==1,(prefix,cell['id'],len(found))
            return kv(found[0])
        queue=one('WS30_QUEUE');path=one('WS30_PATH')
        assert queue['enqueued']==queue['dequeued']+queue['dropped']+queue['current']
        assert queue['current']==queue['dropped']==queue['violations']==path['rejected']==0
        if cell['arm'] not in ['U16']:assert path['changed_qps']==0,cell['id']
        qps=[kv(l) for l in log.splitlines() if l.startswith('WS30_QP ')]
        assert len(qps)==cell['input_flows'] and len({r['flow_id'] for r in qps})==len(qps)
        assert collections.Counter(str(r['tag']) for r in qps)==cell['expected_tags']
        observation={'queue':queue,'path':path,'transport_sums':{k:sum(r[k] for r in qps)
                    for k in ['rx_gap','rx_duplicate','nack_feedback','sack_feedback','cnp_feedback',
                              'retransmit_packets','retransmit_bytes','timeout']},
                     'choices':[kv(l) for l in log.splitlines() if l.startswith('WS30_CHOICES ')]}
    elif 'WS30_PATH ' in log:raise RuntimeError('Observation leaked into off cell')
    if cell['role'] in ['bridge-precheck','historical-bridge','ablation-precheck']:
        audit=json.loads((EV/'ws30-historical-raw-audit.json').read_text())
        mode=cell['mode'];old=next(r for r in audit['cells'] if r['seed']==cell['seed'] and r['mode']==mode)
        assert stats['fct_sha256']==old['fct_sha256'],('Historical FCT bridge differs',cell['id'])
    rs=json.loads((folder/'logs/resource-summary.json').read_text())
    samples=[json.loads(l) for l in (folder/'logs/resource-samples.jsonl').read_text().splitlines() if l]
    assert rs['final_status']=='SUCCEEDED' and rs['samples']==len(samples)>0
    assert rs['peak_tree_rss_mib']<=32768 and rs['minimum_mem_available_gib']>=32 and rs['minimum_free_gib']>=100
    rs['peak_load_1m']=max(x['load_1m'] for x in samples);assert rs['peak_load_1m']<=20
    return {'id':cell['id'],'arm':cell['arm'],'role':cell['role'],**stats,'observation':observation,'resource':rs}

def configure(cap):
    engine.SOURCE_SHA=SOURCE;engine.MAX_CONCURRENT=cap;engine.BUILD_GROUP_SIZE=min(4,cap)
    engine.RECEIPTS=RECEIPTS;engine.pilot.RECEIPTS=RECEIPTS;engine.pilot.POLL_SECONDS=60
    engine.verify=verify
    def start(cell):
        assert not (ROOT/'results'/cell['id']).exists()
        meta=remote.status(cell['id']);assert meta['status']=='BUILT' and meta['git_commit']==SOURCE
        engine.calibration.verify_remote_trace(cell);remote.start_watch(cell['id'])
        remote.command('run',cell['id'],'--lb',cell['mode'],'--pfc','0','--irn','1','--bw','400',
                       '--buffer','9','--topo','topo_1280_400G_400G_OS1','--flow-file',cell['trace'],
                       '--simul-time','0.01','--netload','10','--max-concurrent',str(cap),
                       '--ws30-observe',str(cell['observe']))
        engine.receipt('started',cell,observe=cell['observe'],concurrency=cap)
    engine.start_one=start

def runblock(cells,cap,summary):
    configure(cap)
    for c in cells:assert c['cap']==cap
    # Existing verified cells are revalidated; incomplete IDs are resumed by engine.
    resource,rows=engine.run_batch(cells,len(summary['blocks'])+1,0)
    summary['blocks'].append({'ids':[c['id'] for c in cells],'cap':cap,'resource':resource})
    summary['rows'].update({r['id']:r for r in rows})
    SUMMARY.parent.mkdir(exist_ok=True)
    SUMMARY.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'verified':len(summary['rows']),'last_block':len(cells),'cap':cap}),flush=True)
    return rows

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['plan','technical','pilot','verify'])
    args=parser.parse_args();plan=makeplan();frozen(PLAN,plan)
    if args.phase=='plan':
        print(json.dumps({'source':SOURCE,'plan_sha256':sha(PLAN),'input_sha256':sha(MANIFEST),
                          'technical':len(plan['technical']),'pilot':len(plan['pilot'])}));return
    summary=json.loads(SUMMARY.read_text()) if SUMMARY.exists() else {'source':SOURCE,'blocks':[],'rows':{}}
    assert summary['source']==SOURCE
    if args.phase=='technical':
        # First cell compiled/run in isolation; remaining groups use <=4.
        groups=[[plan['technical'][0]]]+[plan['technical'][i:i+4] for i in range(1,32,4)]
        for block in groups:runblock(block,4,summary)
        rows=summary['rows']
        for arm in ['E','Q16','C16','U16']:
            subset=[c for c in plan['technical'] if c['arm']==arm and c['trace']=='ws30_technical168.txt']
            assert len({rows[c['id']]['fct_sha256'] for c in subset})==1,('Observation perturbs',arm)
        e=next(c for c in plan['technical'] if c['arm']=='E' and c['trace']=='ws30_technical168.txt')
        h=next(c for c in plan['technical'] if c['arm']=='H12' and c['trace']=='ws30_technical168.txt')
        assert rows[e['id']]['fct_sha256']==rows[h['id']]['fct_sha256'],'H12 differs from ECMP'
        a=next(c for c in plan['technical'] if c['arm']=='cr-a1-b1')
        b=next(c for c in plan['technical'] if c['arm']=='C16' and c['trace']=='ws30_technical168.txt')
        assert rows[a['id']]['fct_sha256']==rows[b['id']]['fct_sha256']
        frozen(EV/'ws30-technical-results-r3.json',{'source':SOURCE,'verified_cells':32,'rows':[rows[c['id']] for c in plan['technical']]})
    elif args.phase=='pilot':
        assert (EV/'ws30-technical-results-r3.json').exists(),'Technical gate not passed'
        baseline={};stages=[]
        for cap in [4,8,12]:
            cells=[c for c in plan['pilot'] if c['cap']==cap];rows=runblock(cells,cap,summary)
            for arm in ['Q16','C16','U16','R16']:
                hashes={r['fct_sha256'] for r in rows if r['arm']==arm};assert len(hashes)==1
                value=next(iter(hashes))
                if arm in baseline:assert baseline[arm]==value,'Concurrency changed FCT'
                baseline[arm]=value
            metadata=[json.loads((ROOT/'results'/c['id']/'metadata.json').read_text()) for c in cells]
            t=lambda x:datetime.datetime.fromisoformat(x.replace('Z','+00:00'))
            wall=(max(t(m['finished_utc']) for m in metadata)-min(t(m['started_utc']) for m in metadata)).total_seconds()
            stages.append({'cap':cap,'cells':len(rows),'simulation_wall_seconds':wall,
                           'throughput_cells_per_hour':cap*3600/wall,'resource':summary['blocks'][-1]['resource']})
        selected=12
        for i in range(1,len(stages)):
            if stages[i]['throughput_cells_per_hour']<=stages[i-1]['throughput_cells_per_hour']*1.05:
                selected=stages[i-1]['cap'];break
        frozen(EV/'ws30-resource-results-r3.json',{'source':SOURCE,'verified_cells':24,'selected_cap':selected,
                                                'stages':stages,'hashes':baseline})
    else:
        rows=[verify(c) for c in plan['technical']+plan['pilot']]
        print(json.dumps({'verified_cells':len(rows)}))

if __name__=='__main__':main()
