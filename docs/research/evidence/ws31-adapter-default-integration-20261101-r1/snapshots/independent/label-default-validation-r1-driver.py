"""Three default-off compatibility cells; no core or reference reruns."""
import sys
sys.dont_write_bytecode=True
import pathlib,json,hashlib,importlib.util,subprocess,traceback,re,os
from concurrent.futures import ThreadPoolExecutor,as_completed

OUT=pathlib.Path(__file__).resolve().parent
PREFIX='label-default-validation-r1'
spec=importlib.util.spec_from_file_location('default_common',OUT/'c2-label-validation-r1-attempt2-driver.py')
L=importlib.util.module_from_spec(spec);spec.loader.exec_module(L)
d,b=L.d,L.b
L.PREFIX=d.PREFIX=b.PREFIX=PREFIX
b.PLAN=json.loads((OUT/(PREFIX+'-frozen-plan.json')).read_text(encoding='utf-8'))
b.RECEIPT=OUT/(PREFIX+'-receipt.json');b.EVIDENCE=OUT/(PREFIX+'-evidence')
b.state={'scope':b.PLAN['scope'],'source_sha':b.PLAN['source_sha'],'status':'STARTING',
         'cells':[dict(c,status='NOT_STARTED',ws30_tag_transform=0) for c in b.PLAN['cells']],
         'commands':[],'network_runs_started':0,'core_tests_executed':0,'sync_commands':0,'deploy_commands':0,
         'plan_sha256':hashlib.sha256((OUT/(PREFIX+'-frozen-plan.json')).read_bytes()).hexdigest()}
assert b.state['plan_sha256']=='a81e95af15bba097c8ce900348c260a58c8b2a10416b204380c217331f1d7b4e'

def dump(name,r):
    (OUT/(PREFIX+'-'+name)).write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def aux(path,kind):
    prefixes={'c1':b'WS31_C1_','c2':b'WS31_C2_','c3':b'WS31_C3_'}
    h=hashlib.sha256();counts={}
    with path.open('rb') as f:
        for line in f:
            assert not line.startswith(b'WS31_LABEL_'),'Active label observation in default0'
            if line.startswith(prefixes[kind]):
                h.update(line);prefix=line.split(b' ',1)[0].decode();counts[prefix]=counts.get(prefix,0)+1
    assert counts and any(v>0 for v in counts.values())
    return {'sha256':h.hexdigest(),'event_counts':counts,'no_active_label_observations':True}

def references():
    result={};sourcefiles={}
    for c in b.state['cells']:
        kind=c['id'].rsplit('-',1)[1]
        root=(OUT/'c2-label-validation-r1-evidence/attempt2'/c['reference_id']/'results') if kind=='c2' else (OUT/'main-mode-dynamic-r1-evidence'/c['reference_id']/'results')
        meta=json.loads((root/'metadata.json').read_text(encoding='utf-8'))
        assert meta['experiment_id']==c['reference_id'] and meta['git_commit']==c['reference_sha'] and meta['status']=='SUCCEEDED'
        ref=L.reference(root);log=next((root/'raw').glob('*/config.log'));ref['aux']=aux(log,kind);ref['path']=root
        result[kind]=ref
        for p in (ref['fct'],log,root/'metadata.json'):sourcefiles[str(p)]=sha(p)
    dump('reference-integrity-before.json',sourcefiles)
    return result

def cache_gate():
    ids=[c['id'] for c in b.state['cells']]
    code=r'''
import os,subprocess,json,hashlib
cache='/home/fnl/lzy/code/conweave-ns3';sha=SHA;ids=IDS
assert os.path.realpath(cache)==cache and not os.path.islink(cache)
def git(*a):return subprocess.check_output(['git','-C',cache]+list(a)).decode().strip()
worker='/home/fnl/lzy/.research-workflow/remote_worker.py'
r={'cache_realpath':os.path.realpath(cache),'origin':git('config','--get','remote.origin.url'),
 'clean':git('status','--porcelain'),'requested_tree':git('rev-parse',sha+'^{tree}'),
 'origin_branch_sha':git('rev-parse','refs/remotes/origin/feature/ws31-candidates'),
 'all_new_ids_uncreated':all(not os.path.lexists('/home/fnl/lzy/'+p+'/'+i) for i in ids for p in ['runs','results']),
 'worker_raw_sha256':hashlib.sha256(open(worker,'rb').read()).hexdigest()}
assert r['origin']=='https://github.com/LarryBUPT/conweave-ns3.git' and not r['clean'] and r['origin_branch_sha']==sha and r['all_new_ids_uncreated']
print(json.dumps(r))
'''.replace('SHA',repr(b.PLAN['source_sha'])).replace('IDS',repr(ids))
    r=b.remote(code,timeout=180)
    assert r['requested_tree']==subprocess.check_output(['git','-C',str(b.REPO),'rev-parse',b.PLAN['source_sha']+'^{tree}']).decode().strip()
    raw=(b.REPO/'scripts/remote_worker.py').read_bytes();canonical=subprocess.check_output(['git','-C',str(b.REPO),'show',b.PLAN['source_sha']+':scripts/remote_worker.py'])
    assert raw.replace(b'\r\n',b'\n')==canonical and r['worker_raw_sha256']==hashlib.sha256(raw).hexdigest()
    r['worker_git_canonical_sha256']=hashlib.sha256(canonical).hexdigest();r['newline_only_equivalence']=True
    dump('cache-worker-gate.json',r);b.state['deployed_worker_sha256']=r['worker_raw_sha256'];d.save()

def analyze(c,target,ref):
    L.analyze(c,target,{})
    meta=json.loads((target/'metadata.json').read_text(encoding='utf-8'));assert meta['parameters']['ws31_label_profile']==0
    fct=next((target/'raw').glob('*/*_out_fct.txt'));log=next((target/'raw').glob('*/config.log'))
    assert fct.read_bytes()==ref['fct'].read_bytes()
    assert c['acceptance']['ordered_hashes']==ref['hashes'] and c['acceptance']['observation_counts']==ref['counts']
    kind=c['id'].rsplit('-',1)[1];specific=aux(log,kind);assert specific==ref['aux']
    for rel in ('config/traffic_trace.txt','config/topology.txt'):
        assert (target/rel).read_bytes()==(ref['path']/rel).read_bytes()
    proof={'status':'PASS_DEFAULT_OFF_COMPATIBILITY_ONLY','reference_id':c['reference_id'],'reference_sha':c['reference_sha'],
           'full_fct_equal':True,'ordered_choice_route_remove_uid_only_equal':True,
           'tag_field_retained_and_original_truth_checked':True,'dedicated_all_events_and_states':specific,
           'metadata_profile':0,'no_active_label_observations':True}
    c['regression']=proof;(b.EVIDENCE/c['id']/'default-regression.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8');d.save()

def main():
    assert not b.RECEIPT.exists(),'Never overwrite or repeat IDs'
    d.save();assert b.controller.local_fork(str(b.REPO),require_pushed=True)[3]==b.PLAN['source_sha']
    for c in b.state['cells']:
        folder=b.EVIDENCE/c['id'];assert not folder.exists();folder.mkdir()
    localcode="Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.ProcessId -ne "+str(os.getpid())+" -and $_.CommandLine -match 'ws31|remote_experiment' } | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json"
    old=subprocess.check_output(['powershell','-NoProfile','-Command',localcode],text=True,encoding='utf-8',errors='replace');dump('local-process-gate.json',{'matches':old,'prior_driver_or_monitor':bool(old.strip())});assert not old.strip()
    first=b.state['cells'][0];initial=d.fresh(first,'resources-before-build')
    assert initial['available_gib']>=64 and initial['free_gib']>=100 and initial['loadavg'][0]<=4
    cache_gate();refs=references()
    fresh=d.fresh(first,'resources-admit-build-batch');assert fresh['available_gib']>=64 and fresh['free_gib']>=100 and fresh['loadavg'][0]<=4
    b.state['build_parallelism']=3;b.state['max_compile_jobs']=6;d.save();errors=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        sampler=pool.submit(d.build_sampler)
        for future in as_completed([pool.submit(d.do_build,c) for c in b.state['cells']]):
            try:future.result()
            except BaseException as e:errors.append(str(e))
        if errors:
            base='/home/fnl/lzy/results/'+first['id']+'/logs'
            b.remote("import os,json;p="+repr(base)+";ok=os.path.isdir(p);open(p+'/build-batch-monitor-stop.json','w').write('{}') if ok else None;print(json.dumps({'stopped':ok}))")
        sampled=sampler.result()
    b.state['build_resource_samples']=sampled;d.save()
    if errors:raise RuntimeError('; '.join(errors))
    assert not sampled['other_user_seen'] and not sampled['unknown_project_seen']
    assert sampled['max_sampled_load_1m']<=20 and sampled['min_sampled_available_gib']>=4 and sampled['min_sampled_free_gib']>=20
    builds=d.verify_builds();b.state['all_builds_verified_before_runs']=True
    dump('sources-established.json',{'source_sha':b.PLAN['source_sha'],'builds':builds,'all3_fixed_source_copies_verified':True,
         'algorithm_source_guard':'RELEASED after3 fixed copies; entry/env held until guardedrun3 starts','at_utc':b.stamp()});d.save()
    for c in b.state['cells']:
        d.checkpoint(c,'RESOURCE_GATE_BEFORE_RUN');d.fresh(c,'resources-before-run')
        args=[sys.executable,'-B',str(b.REPO/'scripts/remote_experiment.py'),'run',c['id'],'--lb',c['lb'],'--ws30-tag-transform','0']
        for k,v in b.PLAN['common'].items():args+=['--'+k.replace('_','-'),str(v)]
        d.checkpoint(c,'STARTING_GUARDED_RUN');d.command(c,'guarded-run',args,90);b.state['network_runs_started']+=1
        if b.state['network_runs_started']==3:
            b.state['entry_env_guard']='RELEASED all3 guarded run calls started';dump('guards-released.json',{'status':'RELEASED','source_copies_verified':True,'calls_started':3,'at_utc':b.stamp()})
        d.checkpoint(c,'RUNNING');monitored=b.monitor(c);c['resource_samples']={k:v for k,v in monitored.items() if k!='metadata'}
        d.checkpoint(c,'TERMINAL_TRANSFERRING');target=b.transfer(c)
        assert monitored['metadata']['status']=='SUCCEEDED' and monitored['min_sampled_available_gib']>=4 and monitored['max_sampled_load_1m']<=20
        d.fresh(c,'resources-after-run');d.checkpoint(c,'VERIFYING_DEFAULT_REGRESSION');analyze(c,target,refs[c['id'].rsplit('-',1)[1]])
        c['status']='PASS';d.save();print(c['id']+' PASS',flush=True)
    before=json.loads((OUT/(PREFIX+'-reference-integrity-before.json')).read_text(encoding='utf-8'));assert all(sha(pathlib.Path(p))==h for p,h in before.items());dump('reference-integrity-after.json',before)
    b.state['status']='COMPLETE_FOR_THREE_DEFAULT_OFF_NETWORK_REGRESSIONS_ONLY';d.save();print(b.state['status'],flush=True)

if __name__=='__main__':
    try:main()
    except BaseException as error:
        b.state['status']='STOPPED_ON_DEFAULT_REGRESSION_FAILURE';b.state['error']=str(error);b.state['traceback']=traceback.format_exc()
        for c in b.state['cells']:
            if c['status'] not in ('PASS','BUILD_FAILED'):c['status']='STOPPED_NOT_PASSED'
        d.save();(OUT/(PREFIX+'-driver-error.log')).write_text(traceback.format_exc(),encoding='utf-8');print(b.state['status']+' '+str(error),flush=True);d.preserve_failure();raise
