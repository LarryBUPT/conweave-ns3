"""Recoverable v13 engineering/pilot runner. Formal cells cannot be executed."""
import argparse
import collections
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

import run_ws30_stage3 as old
import run_ws30_stage2 as stage

ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'docs/research/evidence'
SOURCE=''

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def kv(s):return {k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',s)}
def model():
    folder=Path('C:/Users/Administrator/.codex/sessions/2026/10/26')
    path=next(folder.glob('*01a174c7-ecf5-7f21-a9dc-6f8b4f5634b8.jsonl'))
    last=None
    with path.open(encoding='utf-8') as f:
        for line in f:
            if '"type":"turn_context"' in line:
                row=json.loads(line)
                if row.get('type')=='turn_context':last=row['payload']
    assert last
    return {'model':last['model'],'effort':last.get('effort'),'turn_id':last['turn_id']}

def verify(c):
    folder=ROOT/'results'/c['id'];m=read(folder/'metadata.json');raw=str(m['raw_directory'])
    fct=folder/'raw'/raw/(raw+'_out_fct.txt');trace=folder/'config/traffic_trace.txt'
    assert m['status']=='SUCCEEDED' and m['git_commit']==c['source_sha'] and m['algorithm']==c['mode']
    assert sha(trace)==c['trace_sha256']==m['input_flow_sha256']
    assert sha(folder/'config/topology.txt')==c['topology_sha256']==m['topology_sha256']
    for k,v in {'pfc':0,'irn':1,'bw':400,'buffer':9,'ws30_observe':c['observe'],
                'ws30_lifecycle':c['lifecycle'],'ws30_tag_transform':c['tag_transform']}.items():
        assert m['parameters'][k]==v,(c['id'],k)
    assert m['seed']==1 and m['concurrency_cap']<=c['cap']
    expected=[];sp=collections.defaultdict(lambda:10000);dp=collections.defaultdict(lambda:100)
    for l in trace.read_text().splitlines()[1:]:
        a=l.split();s,d,pg,size=map(int,a[:4]);tag=int(a[5]) if len(a)==6 else 0
        sport,dport=sp[s],dp[d];sp[s]+=1;dp[d]+=1
        if c['lifecycle']>=3 and tag==2:sport,dport=10000,100
        expected.append((s,d,sport,dport,size,int(Decimal(a[4])*10**9),tag))
    actual=[list(map(int,l.split())) for l in fct.read_text().splitlines()]
    assert len(actual)==len(expected)==c['input_flows']
    unmatched={e[:6]:e for e in expected}
    assert len(unmatched)==len(expected)
    for r in actual:
        hits=[tuple(r[:5])+(r[5]+d,) for d in (-1,0,1) if tuple(r[:5])+(r[5]+d,) in unmatched]
        assert len(hits)==1,(c['id'],r)
        del unmatched[hits[0]];assert r[6]>0
    assert not unmatched
    log=(folder/'logs/config.log').read_text(encoding='utf-8',errors='replace')
    assert 'WS30_OBSERVATION_OVERFLOW' not in log
    def records(prefix):return [kv(l) for l in log.splitlines() if l.startswith(prefix+' ')]
    obs={}
    if c['observe']:
        qs,ps=records('WS30_QUEUE'),records('WS30_PATH');assert len(qs)==len(ps)==1
        q,p=qs[0],ps[0]
        assert q['enqueued']==q['dequeued'] and q['current']==q['dropped']==q['admission_dropped_bytes']==q['queue_rejected_bytes']==q['violations']==p['rejected']==0
        if c['arm'] not in ('U12','D'):assert p['changed_qps']==0
        qps=records('WS30_QP');assert len(qps)==len(expected)
        assert len({r['flow_id'] for r in qps})==len(expected)
        obs={'queue':q,'path':p,'transport_by_tag':{str(t):{k:sum(r[k] for r in qps if r['tag']==t)
            for k in ('rx_gap','rx_below_expected','fd_feedback_frames','fd_without_sack','sack_feedback','cnp_feedback','retransmit_packets','retransmit_bytes','timeout')}
            for t in sorted({r['tag'] for r in qps})}}
    else: assert not records('WS30_PATH')
    life={}
    if c['lifecycle']:
        creates=records('WS30V13_CREATE');deletes=records('WS30V13_DELETE');done=records('WS30V13_ROUND_DONE')
        sends=records('WS30V13_FIRST_SEND');releases=records('WS30V13_RELEASE')
        assert len(done)==len(sends)==3
        persistent=c['lifecycle']==1
        assert len(creates)==len(deletes)==(1 if persistent else 3)
        assert {r['serial'] for r in creates}=={r['serial'] for r in deletes}
        if persistent:
            assert [r['round'] for r in done]==[0,1,2]
            assert [r['snd_una'] for r in done]==[8192,16384,24576]
            assert len({r['serial'] for r in done+sends+creates+deletes})==1
            assert len(releases)==3 and [r['released'] for r in releases]==[8192,16384,24576]
            assert [r['seq'] for r in sends]==[0,8192,16384]
            rx=[r for r in records('WS30V13_RX') if r['flow_id']==creates[0]['flow_id']]
            assert len({r['object'] for r in rx})==1
            assert all(any(r['seq']==seq and r['expected']==seq for r in rx) for seq in (0,8192,16384))
        else:
            assert len({r['serial'] for r in creates})==3 and all(r['seq']==0 for r in sends)
            assert len(releases)==3 and all(r['released']==8192 for r in releases)
        for d,s in zip(done,sends):assert d['demand_ns']<=s['time_ns']<=d['time_ns']
        caches=[r for r in records('WS30V13_CACHE') if r['sip']==0x0b000001 and r['dip']==0x0b000301]
        if c['arm'] in ('Q12','U12'):
            assert caches
            grouped=collections.defaultdict(list)
            for r in caches:grouped[r['switch']].append(r)
            if persistent:
                for rr in grouped.values():
                    if c['arm']=='Q12':assert [r['miss'] for r in rr]==[1,0,0],rr
                    elif rr[0]['switch']==4:assert [r['miss'] for r in rr]==[1,0,0],rr
            if c['lifecycle']==3:
                for rr in grouped.values():assert [r['miss'] for r in rr]==[1,0,0]
            if c['lifecycle']==4:
                for rr in grouped.values():assert [r['miss'] for r in rr]==[1,1,1]
        life={'creates':creates,'deletes':deletes,'rounds':done,'first_sends':sends,'releases':releases,'probe_caches':caches}
    rs=read(folder/'logs/resource-summary.json');samples=[json.loads(l) for l in (folder/'logs/resource-samples.jsonl').read_text().splitlines() if l]
    assert rs['final_status']=='SUCCEEDED' and samples and rs['samples']==len(samples)
    assert rs['peak_tree_rss_mib']<=32768 and rs['minimum_mem_available_gib']>=32 and rs['minimum_free_gib']>=100
    rs['peak_load_1m']=max(r['load_1m'] for r in samples);assert rs['peak_load_1m']<=20
    return {'id':c['id'],'arm':c['arm'],'source_sha':c['source_sha'],'fct_sha256':sha(fct),'trace_sha256':sha(trace),
            'completed_rows':len(actual),'observation':obs,'lifecycle':life,'resource':rs,'cap':m['concurrency_cap']}

def compare_technical(cells,rows):
    byid={r['id']:r for r in rows}
    for arm in ('E','Q12','R12','U12','D'):
        group=[c for c in cells if c['arm']==arm]
        assert len({byid[c['id']]['fct_sha256'] for c in group})==1,('FCT perturbation',arm)
        full=[c for c in group if c['observe']==2]
        signatures=[]
        for c in full:
            text=(ROOT/'results'/c['id']/'logs/config.log').read_text(encoding='utf-8',errors='replace')
            routes=[re.sub(r' tag=\d+','',l) for l in text.splitlines() if l.startswith('WS30_ROUTE ')]
            signatures.append(hashlib.sha256('\n'.join(routes).encode()).hexdigest())
        assert len(set(signatures))==1,('Path perturbation',arm)
    hashes={c['arm']:byid[c['id']]['fct_sha256'] for c in cells}
    assert hashes['H12']==hashes['E']=='70c970c63da906181ac8745f290528c4006ac9818645eafc40af150b140b1086'
    assert hashes['Q12']=='1f71d7e802ec1b334aff9c6708be5abc2420c6fa7c31e2b6e2f3fdb1232bb44e'
    paths={}
    for c in cells:
        if c['arm'] in ('E','H12') and c['observe']==2:
            log=(ROOT/'results'/c['id']/'logs/config.log').read_text(encoding='utf-8')
            paths[c['arm']]=[l for l in log.splitlines() if l.startswith('WS30_ROUTE ')]
    assert paths['E']==paths['H12'],'H12/E complete packet path differs'
    return {'all_observation_and_tag_hashes_match':True,'H12_E_match':True,'legacy_Q12_and_E_hashes_match':True}

class Backend(old.Backend):
    def verify(self,c):return verify(c)
    def snapshot(self,cells,known=None,drain=False):
        # Reuse the audited ownership/process mapper, bounded to 15 minutes.
        previous=old.REMOTE_WAIT
        # Request timeout is controlled in base; the remote deadline is bounded here.
        old.REMOTE_WAIT=previous.replace("deadline=time.time()+q['seconds']","deadline=time.time()+min(q['seconds'],900)")
        try:return super().snapshot(cells,known,drain)
        finally:old.REMOTE_WAIT=previous
    def start(self,c,cap):
        # Resource watcher plus source/trace guards are identical to stage 3.
        code=("import os,subprocess; name=%r; sample='/home/fnl/lzy/results/'+name+'/logs/resource-samples.jsonl'; "
              "rows=subprocess.check_output(['ps','-eo','args','--no-headers']).decode().splitlines(); "
              "print(sum('ws11_resource_watch.py '+name in r and 'python3 -c' not in r for r in rows)); "
              "print(int(os.path.exists(sample)))") % c['id']
        reply=subprocess.check_output(stage.remote.remote.ssh_base(stage.remote.remote.config())+
            ['python3 -c '+shlex.quote(code)],encoding='utf-8',errors='replace',timeout=45).splitlines()
        watchers,samples=map(int,reply[-2:]);assert watchers<=1,'Duplicate resource watcher'
        if not watchers:
            assert not samples,'Resource samples exist but watcher disappeared; preserve and inspect'
            stage.remote.start_watch(c['id'])
        stage.engine.calibration.verify_remote_trace(c)
        stage.remote.command('run',c['id'],'--lb',c['mode'],'--pfc','0','--irn','1','--bw','400','--buffer','9',
            '--topo',c['topology'],'--flow-file',c['trace'],'--simul-time','0.01','--netload','10',
            '--max-concurrent',str(cap),'--ws30-observe',str(c['observe']),
            '--ws30-lifecycle',str(c['lifecycle']),'--ws30-tag-transform',str(c['tag_transform']))
    def finish(self,c):
        stage.remote.wait_watch(c['id']);stage.remote.command('fetch',c['id'])
        stage.remote.fetch_config_log(c,read(ROOT/'results'/c['id']/'metadata.json'))
        return verify(c)

def main():
    global SOURCE
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['preflight','build-first','technical','lifecycle','pilot','verify']);p.add_argument('--revision',default='r1');args=p.parse_args()
    # Scoped trust for this owned checkout and its child Git processes.
    n=int(os.environ.get('GIT_CONFIG_COUNT','0'));os.environ['GIT_CONFIG_COUNT']=str(n+1)
    os.environ['GIT_CONFIG_KEY_'+str(n)]='safe.directory';os.environ['GIT_CONFIG_VALUE_'+str(n)]=str(ROOT).replace('\\','/')
    plan=read(EV/f'ws30-v13-plan-{args.revision}.json');SOURCE=plan['source_sha']
    assert not plan['formal_execution_enabled']
    stage.engine.SOURCE_SHA=SOURCE;stage.engine.verify=verify
    stage.engine.RECEIPTS=ROOT/f'results/ws30-v13-{args.revision}-build-receipts.jsonl'
    stage.engine.pilot.RECEIPTS=stage.engine.RECEIPTS
    backend=Backend()
    if args.phase=='preflight':
        resource=backend.gate();snapshot=backend.snapshot(plan['technical']+plan['lifecycle']+plan['pilot'])
        assert not any(snapshot['states'].values()),'New ID collision'
        assert old.capacity(snapshot['resource'],4)>0
        out={'model':model(),'resource':resource,'snapshot':snapshot,'source_sha':SOURCE,'all_46_new_IDs_absent':True}
        old.atomic(EV/f'ws30-v13-host-preflight-{args.revision}.json',out)
        print(json.dumps({'host_gate':True,'IDs_absent':46,'model':out['model'],'resource':resource}));return
    if args.phase=='build-first':
        assert model()['model']=='gpt-6.1-sol' and model()['effort']=='medium'
        backend.gate();backend.build(plan['technical'][:1]);print('First isolated fixed-source build complete; simulations not started.');return
    if args.phase=='verify':
        rows=[verify(c) for c in plan['technical']+plan['lifecycle']+plan['pilot'] if (ROOT/'results'/c['id']).exists()]
        print(json.dumps({'verified':len(rows)}));return
    context=model();assert context['model']=='gpt-6-luna' and context['effort']=='medium',('Actual supervision model not active',context)
    if args.phase!='technical':assert (EV/f'ws30-v13-technical-{args.revision}.json').exists()
    if args.phase=='pilot':assert (EV/f'ws30-v13-lifecycle-{args.revision}.json').exists()
    with old.controller_lock():
        cells=plan[args.phase]
        if args.phase=='pilot':
            allrows=[];blocks=[]
            for cap in (4,8):
                group=[c for c in cells if c['cap']==cap]
                state=old.Runner(group,backend,ROOT/f'results/ws30-v13-{args.revision}-pilot-c{cap}.json',cap=cap).run()
                allrows.extend(state['verified'].values());blocks.append(state)
            for arm in ('E','Q12','U12','D'):
                assert len({r['fct_sha256'] for r in allrows if r['arm']==arm})==1
            result={'model':context,'source_sha':SOURCE,'rows':allrows,'blocks':blocks}
        else:
            state=old.Runner(cells,backend,ROOT/f'results/ws30-v13-{args.revision}-{args.phase}.json',cap=4,first_single=True).run()
            rows=list(state['verified'].values());result={'model':context,'source_sha':SOURCE,'rows':rows,'runner':state}
            if args.phase=='technical':result['cross_checks']=compare_technical(cells,rows)
        old.atomic(EV/f'ws30-v13-{args.phase}-{args.revision}.json',result)
        print(json.dumps({'phase':args.phase,'verified':len(result['rows']),'failures':0}))

if __name__=='__main__':main()
