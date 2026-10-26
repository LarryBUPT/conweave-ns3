"""WS-30 internal v14 executor; v13 paper target. Offline by default.
No sync/deploy/push path. Execution requires a separately authorized, hash-bound receipt.
"""
import argparse
import collections
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

import run_ws30_stage3 as recovery
import run_ws30_v13 as legacy
import verify_ws30_v14_raw as life

ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'docs/research/evidence'
CONTRACT=EV/'ws30-v14-disabled-contract-r2.json'
SCHEDULE=EV/'ws30-v14-executor-schedule-r1.json'
AUTH=EV/'ws30-v14-execution-authorization.json'
GROUPS=('regression','lifecycle','lifecycle_observation_controls','ConWeave_observation_controls','W5','formal_disabled')
CONTROLS=('scripts/run_ws30_v14.py','scripts/verify_ws30_v14_raw.py','scripts/remote_experiment.py','scripts/remote_worker.py','scripts/run_ws30_stage3.py','scripts/run_ws30_v13.py','scripts/run_ws30_stage2.py','scripts/run_ws25_formal.py','scripts/run_ws25_preflight.py','scripts/run_ws25_resource_pilot.py','scripts/run_ws25_v1fix_calibration.py')
MODEL_POLICY={'supervision':('gpt-6-luna','medium'),'analysis':('gpt-6.1-sol','medium')}

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise RuntimeError(message)

def schedule(plan):
    reg=plan['regression']; cw=plan['ConWeave_observation_controls']; w5=plan['W5']; formal=plan['formal_disabled']
    profile=lambda n:[c for group in ('lifecycle','lifecycle_observation_controls') for c in plan[group] if c['life_profile']==n and c['lifecycle']==5]
    wresource=[c for c in w5 if c['demand_seed']==20263101 and 'concurrent' in c['trace'] and c['arm'] in ('E','Q12','U12','conweave')]
    definitions=[('technical-single',reg[:1],[],1),('technical-rest',reg[1:],['technical-single'],4),
      ('life-pair',profile(1),['technical-rest'],4),('life-state',profile(2),['technical-rest'],4),
      ('life-other',[c for c in plan['lifecycle'] if c['lifecycle']!=5],['life-pair','life-state'],4),
      ('cw-tech',[c for c in cw if 'cw-tech-' in c['id']],['technical-rest'],4),
      ('cw-long',[c for c in cw if 'cw-long-' in c['id']],['cw-tech'],4),
      ('w5-resource',wresource,['cw-long'],4),('w5-rest',[c for c in w5 if c not in wresource],['w5-resource'],4),
      ('formal-first',formal[:4],['old-source-technical-resource'],4),
      ('formal-rest',formal[4:],['formal-first'],8)]
    phases={name:{'ids':[c['id'] for c in cells],'requires':deps,'maximum_cap':cap,'source_sha':cells[0]['source_sha']} for name,cells,deps,cap in definitions}
    ids=[i for p in phases.values() for i in p['ids']]
    require(len(ids)==len(set(ids))==252,'Schedule lost or duplicated cells')
    return {'contract_sha256':sha(CONTRACT),'execution_enabled':False,'paper_target':'v13','internal_revision':'v14',
      'phases':phases,'automatic_order':[n for n,_,_,_ in definitions],
      'same_host_overlap':False,'new_source_initial_cap':1,'new_source_sustained_cap':4,
      'new_source_cap8_enabled':False,'formal_lifecycle_dependency':False,
      'failure_policy':'preserve ID/raw; stop admissions; repair requires new SHA/ID/contract',
      'authorization_file':str(AUTH.relative_to(ROOT)).replace('\\','/')}

def load():
    plan=read(CONTRACT); expected=schedule(plan)
    require(read(SCHEDULE)==expected,'Frozen schedule differs')
    require(plan['execution_enabled'] is False and plan['approved_execution_cells']==0,'Do not edit the disabled design to authorize it')
    cells={c['id']:c for g in GROUPS for c in plan[g]}
    require(len(cells)==252,'Contract ID collision')
    blobs={}
    for c in cells.values():
        require(c['simulation_seed']==1 and 'seed' not in c,'Ambiguous seed')
        for rel,digest in (('config/'+c['trace'],c['trace_sha256']),('config/'+c['topology']+'.txt',c['topology_sha256'])):
            require(sha(ROOT/rel)==digest,'Local input changed: '+rel)
            key=(c['source_sha'],rel)
            if key not in blobs:blobs[key]=hashlib.sha256(subprocess.check_output(['git','-c','safe.directory='+ROOT.as_posix(),'show',c['source_sha']+':'+rel],cwd=ROOT)).hexdigest()
            require(blobs[key]==digest,'Fixed-source input blob changed')
        require(c['source_sha']==(plan['formal_source_sha_preserved'] if c in plan['formal_disabled'] else plan['source_sha']),'Wrong per-cell source')
    return plan,expected,cells

def actual_model(path):
    require(path is not None,'Actual supervising session file required')
    context=None
    for line in path.open(encoding='utf-8'):
        row=json.loads(line)
        if row.get('type')=='turn_context':context=row['payload']
    require(context is not None,'Missing actual turn context')
    return context

def require_model(session,role):
    context=actual_model(session)
    require((context['model'],context.get('effort'))==MODEL_POLICY[role],
            'Actual '+role+' must be '+MODEL_POLICY[role][0]+' / Medium')
    return context

def authorize(phases,session):
    require(AUTH.exists(),'Execution closed: no main-chat authorization receipt; no remote access performed')
    gate=read(AUTH)
    require(gate.get('approved') is True and gate.get('external_sync_approved') is True and gate.get('authorization_evidence'),'Explicit scope/export authorization missing')
    require(gate.get('contract_sha256')==sha(CONTRACT) and gate.get('schedule_sha256')==sha(SCHEDULE),'Authorization contract/schedule changed')
    require(gate.get('control_sha256')=={p:sha(ROOT/p) for p in CONTROLS},'Controller/worker/verifier version not approved')
    require(set(phases)<=set(gate.get('phases',[])),'Phase not authorized')
    require_model(session,'supervision')
    require((gate.get('supervision_model'),gate.get('supervision_effort'))==MODEL_POLICY['supervision'],'Receipt does not bind actual supervision policy')
    require((gate.get('analysis_model'),gate.get('analysis_effort'))==MODEL_POLICY['analysis'],'Receipt does not bind actual analysis policy')
    return gate

def verify_common(c):
    folder=ROOT/'results'/c['id'];m=read(folder/'metadata.json');params=m['parameters']
    require(m['status']=='SUCCEEDED' and m['git_commit']==c['source_sha'] and m['algorithm']==c['mode'],'Terminal/source/mode mismatch')
    require(legacy.stage.remote.remote.FORK_RE.fullmatch(m['git_repository']) is not None,'Source repository is not personal fork')
    require(m['metadata_schema_version']==3 and m['seed']==m['simulation_seed']==c['simulation_seed']==1 and m['demand_seed']==c['demand_seed'],'Seed schema mismatch')
    for k,v in {'pfc':0,'irn':1,'bw':400,'buffer':9,'ws30_observe':c['observe'],'ws30_lifecycle':c['lifecycle'],'ws30_life_profile':c['life_profile'],'ws30_tag_transform':c['tag_transform']}.items():require(params[k]==v,'Parameter mismatch: '+k)
    require(params['topo']==c['topology'] and Path(params['flow_file']).name==c['trace'] and float(params['simul_time'])==float(c['simul_time']),'Input/runtime parameter mismatch')
    require(m['input_flow_sha256']==c['trace_sha256']==sha(folder/'config/traffic_trace.txt'),'Trace mismatch')
    require(m['topology_sha256']==c['topology_sha256']==sha(folder/'config/topology.txt'),'Topology mismatch')
    config=(folder/'config/config.txt').read_text()
    require(re.findall(r'^RANDOM_SEED\s+(\S+)\s*$',config,re.M)==['1'],'Actual ns-3 seed not unique/1')
    # Read the authoritative mode table from the fixed source instead of guessing aliases.
    source=subprocess.check_output(['git','-c','safe.directory='+ROOT.as_posix(),'show',c['source_sha']+':run.py'],cwd=ROOT).decode()
    match=re.search(r'["\']'+re.escape(c['mode'])+r'["\']\s*:\s*(\d+)',source)
    require(match is not None,'Mode absent from fixed source')
    require(re.findall(r'^LB_MODE\s+(\S+)\s*$',config,re.M)==[match[1]],'Actual LB mode mismatch')
    require(m['build_mode']=='optimized' and m['cpu_jobs']==2 and m['concurrency_cap'] in (1,4,8) and m['concurrency_cap']<=c['cap'],'Build/cap mismatch')
    log=(folder/'logs/config.log').read_text(encoding='utf-8',errors='replace')
    require('overflow' not in log.lower(),'Observation overflow')
    raw=str(m['raw_directory']);require(raw.isdigit(),'Invalid raw directory')
    fct=folder/'raw'/raw/(raw+'_out_fct.txt')
    if c['lifecycle']:
        out=life.verify_lifecycle(c)
    else:
        expected={};sp=collections.defaultdict(lambda:10000);dp=collections.defaultdict(lambda:100)
        for line in (folder/'config/traffic_trace.txt').read_text().splitlines()[1:]:
            a=line.split();s,d,pg,size=map(int,a[:4]);key=(s,d,sp[s],dp[d],size,int(Decimal(a[4])*10**9));sp[s]+=1;dp[d]+=1
            require(key not in expected,'Duplicate expected identity');expected[key]=True
        count=len(expected)
        for line in fct.read_text().splitlines():
            r=list(map(int,line.split()));hits=[tuple(r[:5])+(r[5]+delta,) for delta in (-1,0,1) if tuple(r[:5])+(r[5]+delta,) in expected]
            require(len(hits)==1 and r[6]>0,'FCT identity/byte/origin mismatch');del expected[hits[0]]
        require(not expected and count==c['input_flows'],'Incomplete FCT')
        out={'id':c['id'],'completed_rows':count,'fct_sha256':sha(fct)}
    rows=lambda prefix:[life.kv(l) for l in log.splitlines() if l.startswith(prefix+' ')]
    if c['observe']:
        q=rows('WS30_QUEUE');p=rows('WS30_PATH');qp=rows('WS30_QP')
        require(len(q)==len(p)==1 and len(qp)==c['input_flows'] and len({r['flow_id'] for r in qp})==len(qp),'Missing transport/queue observations')
        require(q[0]['enqueued']==q[0]['dequeued'] and all(q[0][k]==0 for k in ('current','dropped','admission_dropped_bytes','queue_rejected_bytes','violations')) and p[0]['rejected']==0,'Queue/drop invariant failed')
        if c['arm'] in ('E','Q12','R12','H12'):require(p[0]['changed_qps']==0,'Flow-pinned arm changed its QP path')
    else:require(not rows('WS30_QUEUE') and not rows('WS30_PATH') and not rows('WS30_CW') and not rows('WS30V14_STATE'),'Observer-off emitted records')
    if c['mode']=='conweave' and c['observe']:
        events=collections.Counter(r['event'] for r in rows('WS30_CW'))
        require(events['tx']>0,'ConWeave observer entry not exercised');out['ConWeave_events']=dict(events)
    rs=read(folder/'logs/resource-summary.json');samples=[json.loads(l) for l in (folder/'logs/resource-samples.jsonl').read_text().splitlines() if l]
    require(rs['final_status']=='SUCCEEDED' and samples and rs['samples']==len(samples),'Incomplete resource receipt')
    require(rs['peak_tree_rss_mib']<=32768 and rs['minimum_mem_available_gib']>=32 and rs['minimum_free_gib']>=100 and max(r['load_1m'] for r in samples)<=20,'Resource limit exceeded')
    out.update(source_sha=c['source_sha'],cap=m['concurrency_cap'],resource=rs)
    return out

def phase_checks(name,plan,cells):
    if name=='technical-rest':
        rows=[legacy.verify(c) for c in plan['regression']];legacy.compare_technical(plan['regression'],rows)
        targets=read(EV/'ws30-v14-pre-run-gates-r1.json')['regression_targets']
        for target in targets:
            c=cells[target['id']];row=verify_common(c);require(row['fct_sha256']==target['fct_sha256'],'Old FCT regression')
            if target['route_hash_without_tag']:
                log=(ROOT/'results'/c['id']/'logs/config.log').read_text()
                routes=[re.sub(r' tag=\d+','',l) for l in log.splitlines() if l.startswith('WS30_ROUTE ')]
                require(hashlib.sha256('\n'.join(routes).encode()).hexdigest()==target['route_hash_without_tag'],'Old complete route regression')
    if name in ('life-pair','life-state'):
        profile=1 if name=='life-pair' else 2
        for c in plan['lifecycle_observation_controls']:
            if c['life_profile']==profile:require(verify_common(c)['fct_sha256']==verify_common(cells[c['full_observer_id']])['fct_sha256'],'Lifecycle observer perturbation')
    if name in ('cw-tech','cw-long'):
        group=[c for c in plan['ConWeave_observation_controls'] if name+'-' in c['id']]
        require(len({verify_common(c)['fct_sha256'] for c in group})==1,'ConWeave observer perturbation')

def old_source_gate():
    old=read(EV/'ws30-v13-plan-r2.json')
    rows=[legacy.verify(c) for c in old['technical']+old['pilot']]
    for c in old['technical']+old['pilot']:
        config=(ROOT/'results'/c['id']/'config/config.txt').read_text()
        require(re.findall(r'^RANDOM_SEED\s+(\S+)\s*$',config,re.M)==['1'],'Old actual configuration seed changed')
    legacy.compare_technical(old['technical'],rows[:18])
    require(len(rows)==30 and {c['source_sha'] for c in old['technical']+old['pilot']}=={read(CONTRACT)['formal_source_sha_preserved']},'Old source qualification changed')
    for arm in ('E','Q12','U12','D'):require(len({r['fct_sha256'] for r in rows[18:] if r['arm']==arm})==1,'Old cap4/cap8 FCT inconsistency')
    return rows

def prerequisite(name,plan,sched,cells):
    for dep in sched['phases'][name]['requires']:
        if dep=='old-source-technical-resource':old_source_gate();continue
        p=sched['phases'][dep]
        for i in p['ids']:verify_common(cells[i])
        phase_checks(dep,plan,cells)
        prerequisite(dep,plan,sched,cells)

class Backend:
    """Composition avoids the legacy runner's isinstance shortcut around gate()."""
    def __init__(self,cells):self.cells=cells;self.base=recovery.Backend()
    def compatible(self):
        # Exact deployed bytes ensure both new CLI fields and schema3 are supported.
        code="import hashlib;print(hashlib.sha256(open('/home/fnl/lzy/.research-workflow/remote_worker.py','rb').read()).hexdigest())"
        cfg=legacy.stage.remote.remote.config()
        actual=subprocess.check_output(legacy.stage.remote.remote.ssh_base(cfg)+['python3 -c '+shlex.quote(code)],text=True,timeout=45).strip()
        require(actual==sha(ROOT/'scripts/remote_worker.py'),'Controller/worker mismatch: approved paired deployment required')
    def gate(self):
        self.compatible()
        resource=legacy.stage.resources.host_gate(reject_active=False)
        ownership=self.snapshot(self.cells)['resource']
        require(recovery.capacity(ownership,8)>0,'Unknown worker/resource condition; no new admission')
        resource.update({k:ownership[k] for k in ('other_users','unexpected_simulation_pids','rss_mib')})
        return resource
    def snapshot(self,cells,known=None,drain=False):
        out=self.base.snapshot(cells,known,drain)
        for c in cells:
            m=out['states'][c['id']]
            if m:require(m['git_commit']==c['source_sha'] and m['status'] in ('BUILDING','BUILT','RUNNING','SUCCEEDED','FAILED','BUILD_FAILED'),'Remote ID source/state collision')
        # Native observer bounds remain primary. This admission check additionally
        # catches unbounded aggregate stdout without deleting or replacing logs.
        cfg=legacy.stage.remote.remote.config()
        code="import glob,os,json; ids=%r; print(json.dumps([n for n in ids if any(os.path.getsize(p)>536870912 for p in glob.glob('/home/fnl/lzy/runs/'+n+'/source/mix/output/*/config.log'))]))"%[c['id'] for c in cells]
        large=json.loads(subprocess.check_output(legacy.stage.remote.remote.ssh_base(cfg)+['python3 -c '+shlex.quote(code)],text=True,timeout=45))
        require(not large,'Aggregate log >512 MiB; admissions stopped, workers/raw retained: '+repr(large))
        return out
    def build(self,cells):
        self.compatible();require(len({c['source_sha'] for c in cells})==1,'Mixed-source build group')
        # Cache must already contain authorized source. No implicit sync or HEAD.
        def one(c):
            cfg=legacy.stage.remote.remote.config()
            intent=ROOT/('results/ws30-v14-build-intents/'+c['id']+'.json')
            require(not intent.exists(),'Ambiguous prior build intent: inspect retained ID; never reissue build')
            recovery.atomic(intent,{'id':c['id'],'source_sha':c['source_sha'],'contract_sha256':sha(CONTRACT),'state':'requested'})
            try:legacy.stage.remote.remote.worker_call(cfg,'build','--id',c['id'],'--sha',c['source_sha'],'--branch','research/ws30-attribution-audit')
            except Exception:
                # Lost transport is recovered by state inspection, never by retrying build.
                state=self.snapshot([c])['states'][c['id']]
                if not state or state['status']!='BUILT':raise
            require(self.snapshot([c])['states'][c['id']]['status']=='BUILT','Isolated build incomplete')
            recovery.atomic(intent,{'id':c['id'],'source_sha':c['source_sha'],'contract_sha256':sha(CONTRACT),'state':'built'})
        with ThreadPoolExecutor(max_workers=min(4,len(cells))) as pool:list(pool.map(one,cells))
    def local(self,c):
        path=ROOT/'results'/c['id']
        require(not path.is_symlink(),'Local result symlink refused')
        return path.exists()
    def verify(self,c):return verify_common(c)
    def start(self,c,cap):
        self.compatible()
        require(not self.local(c),'Local ID already exists')
        state=self.snapshot([c])['states'][c['id']]
        require(state and state['status']=='BUILT' and state['git_commit']==c['source_sha'],'Start requires untouched per-cell build')
        legacy.stage.engine.calibration.verify_remote_trace(c)
        # Watcher recovery retains all previous samples and refuses replacement.
        cfg=legacy.stage.remote.remote.config()
        topo='/home/fnl/lzy/runs/'+c['id']+'/source/config/'+c['topology']+'.txt'
        code="import hashlib,os; p=%r; assert os.path.realpath(p)==p; print(hashlib.sha256(open(p,'rb').read()).hexdigest())"%topo
        require(subprocess.check_output(legacy.stage.remote.remote.ssh_base(cfg)+['python3 -c '+shlex.quote(code)],text=True,timeout=45).strip()==c['topology_sha256'],'Remote topology mismatch before run')
        code=("import os,subprocess; n=%r; rows=subprocess.check_output(['ps','-eo','args','--no-headers']).decode().splitlines(); print(sum('ws11_resource_watch.py '+n in r and 'python3 -c' not in r for r in rows)); print(int(os.path.exists('/home/fnl/lzy/results/'+n+'/logs/resource-samples.jsonl')))")%c['id']
        watcher,samples=map(int,subprocess.check_output(legacy.stage.remote.remote.ssh_base(cfg)+['python3 -c '+shlex.quote(code)],text=True,timeout=45).splitlines()[-2:])
        require(watcher<=1,'Duplicate resource watcher')
        if not watcher:require(not samples,'Watcher missing: preserve existing samples');legacy.stage.remote.start_watch(c['id'])
        args=['run',c['id'],'--lb',c['mode'],'--pfc','0','--irn','1','--bw','400','--buffer','9','--topo',c['topology'],'--flow-file',c['trace'],'--simul-time',c['simul_time'],'--netload','10','--max-concurrent',str(cap),'--ws30-observe',str(c['observe']),'--ws30-lifecycle',str(c['lifecycle']),'--ws30-life-profile',str(c['life_profile']),'--ws30-tag-transform',str(c['tag_transform']),'--simulation-seed',str(c['simulation_seed'])]
        if c['demand_seed'] is not None:args+=['--demand-seed',str(c['demand_seed'])]
        legacy.stage.remote.command(*args)
    def finish(self,c):
        legacy.stage.remote.wait_watch(c['id'])
        if not self.local(c):legacy.stage.remote.command('fetch',c['id'])
        legacy.stage.remote.fetch_config_log(c,read(ROOT/'results'/c['id']/'metadata.json'))
        return self.verify(c)
    def preserve_failure(self,c):
        state=self.snapshot([c])['states'][c['id']]
        if state and state['status']=='BUILD_FAILED':
            if not self.local(c):legacy.stage.remote.command('fetch',c['id'])
        else:self.base.preserve_failure(c)

class Runner(recovery.Runner):
    def collect(self,cells,states):
        for c in cells:
            if states.get(c['id']) and states[c['id']]['status']=='BUILD_FAILED':
                self.state['failures'][c['id']]=states[c['id']];self.save('build_failed_preserved',id=c['id'])
                try:self.backend.preserve_failure(c)
                except Exception as error:self.save('build_failure_fetch_attention',id=c['id'],error=str(error))
        try:super().collect(cells,states)
        except Exception as error:
            self.state['failures']['validation']={'error':str(error)};self.save('validation_failed_preserved');raise
    def run(self):
        try:
            require(not self.state['failures'],'Retained failure requires a new approved repair plan')
            return super().run()
        except Exception as error:self.save('controller_stopped',error=str(error));raise

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=('inspect','verify-local','run'),nargs='?',default='inspect')
    parser.add_argument('--phase',action='append');parser.add_argument('--session-file',type=Path);args=parser.parse_args()
    plan,sched,cells=load();phases=args.phase or []
    require(set(phases)<=set(sched['phases']),'Unknown phase')
    if args.command=='inspect':
        print(json.dumps({'execution_enabled':False,'new_simulations':0,'phases':{k:{'count':len(v['ids']),'requires':v['requires'],'cap':v['maximum_cap'],'source':v['source_sha']} for k,v in sched['phases'].items()}}));return
    if args.command=='verify-local':
        require_model(args.session_file,'analysis')
        ids=[i for name in phases for i in sched['phases'][name]['ids']] if phases else list(cells)
        rows=[verify_common(cells[i]) for i in ids if (ROOT/'results'/i).exists()]
        print(json.dumps({'verified_local':len(rows),'required':len(ids),'new_simulations':0}));return
    # Deliberately before Backend construction, SSH/config lookup, or controller writes.
    require(phases,'Explicit ordered --phase list required; inspect is the default')
    gate=authorize(phases,args.session_file)
    with recovery.controller_lock():
        for name in phases:
            prerequisite(name,plan,sched,cells)
            spec=sched['phases'][name];group=[cells[i] for i in spec['ids']]
            cap=min(spec['maximum_cap'],gate.get('phase_caps',{}).get(name,0));require(cap in (1,4,8),'Missing approved phase cap')
            path=ROOT/('results/ws30-v14-'+name+'-execution-r1.json')
            runner=Runner(group,Backend(group),path,cap=cap)
            runner.save('authorized_controller_started',phase=name,pid=os.getpid(),authorization_sha256=sha(AUTH),source_sha=spec['source_sha'])
            runner.run()
            try:phase_checks(name,plan,cells)
            except Exception as error:
                runner.state['failures']['phase_validation']={'error':str(error)};runner.save('phase_validation_failed');raise
            runner.save('phase_accepted')
        print(json.dumps({'accepted_phases':phases}))
if __name__=='__main__':main()
