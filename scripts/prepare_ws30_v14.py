"""Freeze explicit-seed v14 contracts. Deliberately contains no execution phase."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess
from make_ws30_v14_inputs import generate

ROOT=Path(__file__).resolve().parents[1]; EV=ROOT/'docs/research/evidence'
MODES={'E':'fecmp','Q12':'ws30v13-q12','R12':'ws30v13-r12','U12':'ws30v13-u12','D':'drill','H12':'ws30-h12'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);args=parser.parse_args()
    assert re.fullmatch('[0-9a-f]{40}',args.source)
    inputs=generate(); old=json.loads((EV/'ws30-v13-plan-r2.json').read_text())
    prefix='20261026-120000-w30v14-'
    def normalize(c):
        c=dict(c);c.pop('seed',None);c['simulation_seed']=1
        match=re.search(r'_seed(\d+)_',c['trace']);c['demand_seed']=int(match[1]) if match else None
        c['source_sha']=args.source;c['life_profile']=0
        c['simul_time']='0.01'
        c['id']=prefix+c['id'].split('r2-')[1]
        return c
    regress=[]
    for c in old['technical']:
        n=normalize(c);n['regression_original_id']=c['id'];n['role']='regression';regress.append(n)
    def cell(label,arm,trace,topology='topo_1280_400G_400G_OS1',observe=1,life=0,profile=0,role='W5',cap=8):
        lines=(ROOT/'config'/trace).read_text().splitlines();match=re.search(r'_seed(\d+)_',trace)
        return {'id':prefix+label,'source_sha':args.source,'arm':arm,'mode':MODES.get(arm,arm),'trace':trace,'trace_sha256':sha(ROOT/'config'/trace),'topology':topology,'topology_sha256':sha(ROOT/'config'/(topology+'.txt')),'input_flows':int(lines[0]),'expected_tags':dict(collections.Counter(l.split()[5] for l in lines[1:])),'simulation_seed':1,'demand_seed':int(match[1]) if match else (20263101 if trace=='ws30w5_sustained_prefix.txt' else None),'observe':observe,'tag_transform':0,'lifecycle':life,'life_profile':profile,'role':role,'cap':cap,'simul_time':'0.05' if profile==2 else '0.01'}
    lifecycle=[];observation=[]
    for profile,name in ((1,'pair'),(2,'state')):
        for policy,mode in (('persistent',5),('fresh',6),('retain',7),('cleanup',8)):
            trace='ws30v14_life_%s_%s.txt'%(name,policy if mode<7 else 'reuse')
            for arm in ('E','Q12','U12'):
                c=cell('l-%s-%s-%s'%(name,policy,arm.lower()),arm,trace,'ws30v14_%s8'%name,2,mode,profile,'lifecycle',4)
                lifecycle.append(c)
                if policy=='persistent':
                    n=dict(c,id=prefix+'o0-%s-%s'%(name,arm.lower()),observe=0,role='lifecycle-observation-control');n['full_observer_id']=c['id'];observation.append(n)
    w5=[]
    methods=['E','conga','letflow','conweave','D','Q12','R12','U12']
    for seed in (20263101,20263102):
        for timing in ('concurrent','lead20us'):
            for arm in methods:w5.append(cell('w5-s%d-%s-%s'%(seed,timing,arm.lower()),arm,'ws30w5_seed%d_%s.txt'%(seed,timing)))
    cw=[]
    for name,trace in (('tech','ws30_technical168.txt'),('long','ws30w5_sustained_prefix.txt')):
        for observe in (0,1):cw.append(cell('cw-%s-o%d'%(name,observe),'conweave',trace,observe=observe,role='ConWeave-observation-control'))
    # Schema correction does not migrate the already frozen formal simulation source.
    formal=[dict(normalize(c),source_sha=old['source_sha']) for c in old['formal_disabled']+old['historical_disabled']]
    allcells=regress+lifecycle+observation+cw+w5+formal
    assert len(allcells)==len({c['id'] for c in allcells})==252
    for c in allcells:
        assert len(c['id'])<=56 and 'seed' not in c and c['simulation_seed']==1
        for rel,digest in [('config/'+c['trace'],c['trace_sha256']),('config/'+c['topology']+'.txt',c['topology_sha256'])]:
            data=subprocess.check_output(['git','-c','safe.directory='+ROOT.as_posix(),'show',c['source_sha']+':'+rel],cwd=ROOT)
            assert hashlib.sha256(data).hexdigest()==digest,(c['id'],rel)
    out={'schema_version':3,'source_sha':args.source,'execution_enabled':False,'approved_execution_cells':0,'preserved_r2_plan_sha256':sha(EV/'ws30-v13-plan-r2.json'),'regression':regress,'lifecycle':lifecycle,'lifecycle_observation_controls':observation,'ConWeave_observation_controls':cw,'W5':w5,'formal_disabled':formal,'counts':{'new_engineering':48,'W5_with_qualification':36,'formal_disabled':168,'total_proposed_new':252},'gates':['local static checks only; native build and dynamic regression pending','main-chat scope acceptance','explicit model and fresh host gate','fixed source/input/topology/seed','all on/off regressions hash-identical','pair queues distinct and unequal in actual logs','real CNP/CC and U12 SACK/recovery observed within rounds','completed-round boundary drained; nonempty SACK across it is not required'],'stop':['byte/identity mismatch','observation perturbs FCT or paths','release-before-ACK','unobserved required physical condition','resource/unknown worker/overflow'],'old_r2_cells_retained':46,'inputs':inputs}
    out['formal_source_sha_preserved']=old['source_sha']
    p=EV/'ws30-v14-disabled-contract-r2.json';s=json.dumps(out,ensure_ascii=False,indent=2)+'\n'
    if p.exists():assert json.loads(p.read_text(encoding='utf-8'))==out
    else:p.write_text(s,encoding='utf-8')
    print(json.dumps(out['counts']))
if __name__=='__main__':main()
