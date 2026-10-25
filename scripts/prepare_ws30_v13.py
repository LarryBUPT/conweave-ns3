"""Prepare v13 inputs and an explicitly disabled formal plan."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'docs/research/evidence'
MODES={'E':'fecmp','Q12':'ws30v13-q12','R12':'ws30v13-r12','U12':'ws30v13-u12','D':'drill','H12':'ws30-h12'}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def frozen(p,obj):
    s=json.dumps(obj,indent=2,sort_keys=True)+'\n'
    if p.exists(): assert p.read_text(encoding='utf-8')==s, str(p)
    else: p.write_text(s,encoding='utf-8')

def traces():
    for warm in (0,1):
        # Empty warmup precedes background; concurrent first request sees the
        # already released competing demand. Every round has its own origin.
        first=2000000000+(0 if warm else 2000)
        for policy in ('persistent','fresh','reuse'):
            rows=[]
            for r in range(3):
                bg=2000000000+r*100000+(20000 if warm else 0)
                dst=1 if r%2==0 else 2
                rows.append((bg,f'0 {dst} 3 81920 {bg/1e9:.9f} 1'))
                if policy!='persistent' or r==0:
                    t=first+r*100000; size=24576 if policy=='persistent' else 8192
                    rows.append((t,f'0 3 3 {size} {t/1e9:.9f} 2'))
            rows.sort(key=lambda x:x[0])
            data=str(len(rows))+'\n'+'\n'.join(v for _,v in rows)+'\n'
            p=ROOT/f'config/ws30v13_life_w{warm}_{policy}.txt'
            if p.exists(): assert p.read_text()==data
            else:p.write_text(data,encoding='ascii')

def main():
    p=argparse.ArgumentParser();p.add_argument('--source');p.add_argument('--revision',default='r1');args=p.parse_args()
    traces()
    if not args.source:
        print('Created/verified six lifecycle input traces; plan not yet frozen.');return
    source=args.source
    assert len(source)==40
    prefix='20261026-060000-w30v13'+('' if args.revision=='r1' else '-'+args.revision)
    def cell(suffix,arm,trace='ws30_technical168.txt',observe=2,life=0,transform=0,role='technical',cap=4):
        path=ROOT/'config'/trace;lines=path.read_text().splitlines()
        tags=collections.Counter(l.split()[5] if len(l.split())==6 else '0' for l in lines[1:])
        topo='ws30_composition8' if life else 'topo_1280_400G_400G_OS1'
        return {'id':prefix+'-'+suffix,'source_sha':source,'arm':arm,'mode':MODES[arm],'trace':trace,
            'trace_sha256':sha(path),'input_flows':int(lines[0]),'expected_tags':dict(tags),
            'observe':observe,'lifecycle':life,'tag_transform':transform,'role':role,'cap':cap,
            'topology':topo,'topology_sha256':sha(ROOT/'config'/(topo+'.txt')),'seed':0,'background':tags.get('1',0),'run_order':0}
    tech=[]
    for arm in ('E','Q12','R12','U12','D'):
        for obs in (0,2):tech.append(cell('t%02d-%s-o%d'%(len(tech)+1,arm.lower(),obs),arm,observe=obs))
    tech.append(cell('t11-q12-o1','Q12',observe=1));tech.append(cell('t12-h12-o2','H12'))
    for arm in ('Q12','R12','U12'):
        for t in (1,2):tech.append(cell('t%02d-%s-x%d'%(len(tech)+1,arm.lower(),t),arm,transform=t))
    assert len(tech)==18
    life=[]
    for warm in (0,1):
        for policy,num in [('persistent',1),('fresh',2)]:
            for arm in ('E','Q12','U12'):
                life.append(cell('l-w%d-%s-%s'%(warm,policy[0],arm.lower()),arm,
                    f'ws30v13_life_w{warm}_{policy}.txt',life=num,role='lifecycle'))
    for num in (3,4):
        for arm in ('E','Q12'):
            life.append(cell('l-reuse%d-%s'%(num,arm.lower()),arm,'ws30v13_life_w0_reuse.txt',life=num,role='tuple-recreation'))
    pilot=[]
    for cap in (4,8):
        for j in range(cap):
            arm=('E','Q12','U12','D')[j%4]
            pilot.append(cell('p-c%d-%d-%s'%(cap,j,arm.lower()),arm,'ws25_seed20262501_b192.txt',observe=1,role='resource-only',cap=cap))
    formal=[]
    for seed in range(20263021,20263045):
        for arm in ('E','Q12','R12','U12','D'):
            formal.append(cell('m-s%d-%s'%(seed,arm.lower()),arm,f'ws25_seed{seed}_b192.txt',observe=1,role='formal-disabled',cap=8))
    historical=[]
    for seed in list(range(20262521,20262545))+list(range(20262721,20262745)):
        historical.append(cell('d-s%d'%seed,'D',f'ws25_seed{seed}_b192.txt',observe=1,role='historical-disabled',cap=8))
    allcells=tech+life+pilot+formal+historical
    assert len(allcells)==len({c['id'] for c in allcells})==214
    for c in allcells:
        assert len(c['id'])<=56,c['id']
        b=subprocess.check_output(['git','-c','safe.directory='+str(ROOT).replace('\\','/'),'show',source+':config/'+c['trace']],cwd=ROOT)
        assert hashlib.sha256(b).hexdigest()==c['trace_sha256']
    plan={'source_sha':source,'revision':args.revision,'formal_execution_enabled':False,
        'technical':tech,'lifecycle':life,'pilot':pilot,'formal_disabled':formal,'historical_disabled':historical,
        'total_planned_cells':214,'approved_current_stage_cells':46,
        'technical_layout':'5 arms observation off/full + Q12 summary + H12 + 3 arms both tag deletion and swap',
        'statistics':'Demand-level paired ratios; already revealed 24 demands; supplemental validation, not new blinded confirmation',
        'stops':['identity/byte/queue mismatch','observation perturbs FCT/path','unreleased bytes transmitted','persistent object or state reset','unknown process or other-user contention','resource safety failure'],
        'resources':{'max_load1':20,'min_available_gib':32,'min_disk_gib':100,'max_tree_rss_gib':32,'compile_jobs':2,'parallel_builds':4},
        'formal_requires_new_main_chat_acceptance':True}
    frozen(EV/f'ws30-v13-plan-{args.revision}.json',plan)
    print(json.dumps({'source':source,'technical':18,'lifecycle':16,'pilot':12,'formal_disabled':168,'total':214}))

if __name__=='__main__':main()
