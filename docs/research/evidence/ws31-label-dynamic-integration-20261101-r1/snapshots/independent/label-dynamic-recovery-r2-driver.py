"""Run only the two unchanged BUILT-never-started C3 cells, serially."""
import sys
sys.dont_write_bytecode=True
import hashlib,importlib.util,json,os,pathlib,subprocess,traceback
OUT=pathlib.Path(__file__).resolve().parent
PREFIX='label-dynamic-recovery-r2'
OLD='label-dynamic-validation-r1'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
shared=module('recovery_shared_helpers',OUT/'label-default-validation-r1-driver.py')
L,d,b=shared.L,shared.d,shared.b
L.PREFIX=d.PREFIX=b.PREFIX=PREFIX
PLAN=read(OUT/(PREFIX+'-frozen-plan.json'))
ORIGINAL=read(OUT/(OLD+'-frozen-plan.json'))
b.PLAN=ORIGINAL;b.RECEIPT=OUT/(PREFIX+'-receipt.json');b.EVIDENCE=OUT/(PREFIX+'-evidence')
Q=module('recovery_raw_checker',OUT/(PREFIX+'-checker.py'))
b.state={'status':'STARTING','scope':PLAN['scope'],'source_sha':PLAN['source_sha'],
    'plan_sha256':sha(OUT/(PREFIX+'-frozen-plan.json')),'original_plan_sha256':PLAN['original_plan_sha256'],
    'cells':[dict(c,status='NOT_STARTED') for c in ORIGINAL['cells'] if c['id'] in PLAN['only_pending_ids']],
    'commands':[],'network_runs_started':0,'core_tests_executed':0,'build_commands':0,'sync_commands':0,'deploy_commands':0,
    'prior_eight_simulation_repeats':0,'driver_pid':os.getpid(),'started_utc':b.stamp(),
    'model_switch':'No switch performed or claimed; no switching interface available'}
assert b.state['plan_sha256']=='d1dce31271e4756e4c90084bc01006e9c4a670de830d24414260a71faacd9599'
assert [c['id'] for c in b.state['cells']]==PLAN['only_pending_ids']
def dump(suffix,r):(OUT/(PREFIX+'-'+suffix)).write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
def preserved():
    before=read(OUT/(PREFIX+'-original-r1-integrity-before.json'))
    assert all((OUT/p).stat().st_size==v['bytes'] and sha(OUT/p)==v['sha256'] for p,v in before.items())
    return before
def resource(c,name):
    r=d.fresh(c,name);assert r['available_gib']>=64 and r['free_gib']>=100 and r['loadavg'][0]<=4;return r
def built_gate():
    builds=read(OUT/(OLD+'-all-builds-verified.json'));expected=[]
    for c in b.state['cells']:
        built=next(x for x in builds if x['id']==c['id'])
        folder=OUT/(OLD+'-evidence')/c['id']/'failure-results'
        expected.append({'id':c['id'],'metadata':read(folder/'metadata.json'),'metadata_sha256':sha(folder/'metadata.json'),
            'source_hashes':built['source_hashes'],'binary_sha256':built['binary_sha256']})
    code=r'''
import os,json,hashlib,subprocess
expected=EXPECTED;sha=SHA
cache='/home/fnl/lzy/code/conweave-ns3'
def git(root,*args):return subprocess.check_output(['git','-C',root]+list(args)).decode().strip()
def h(p):return hashlib.sha256(open(p,'rb').read()).hexdigest()
assert os.path.realpath(cache)==cache and not os.path.islink(cache)
result={'cache_realpath':os.path.realpath(cache),'origin':git(cache,'config','--get','remote.origin.url'),
 'clean':git(cache,'status','--porcelain'),'branch_ref':git(cache,'rev-parse','refs/remotes/origin/feature/ws31-candidates'),
 'tree':git(cache,'rev-parse',sha+'^{tree}'),'worker_raw_sha256':h('/home/fnl/lzy/.research-workflow/remote_worker.py'),'pending':[]}
assert result['origin']=='https://github.com/LarryBUPT/conweave-ns3.git' and not result['clean'] and result['branch_ref']==sha
for e in expected:
 i=e['id'];base='/home/fnl/lzy/results/'+i;source='/home/fnl/lzy/runs/'+i+'/source'
 assert os.path.realpath(base)==base and os.path.realpath(source)==source
 m=json.load(open(base+'/metadata.json'))
 assert m['status']=='BUILT' and m==e['metadata'] and h(base+'/metadata.json')==e['metadata_sha256']
 assert m['git_commit']==sha and m['build_mode']=='optimized' and m['cpu_jobs']==2
 assert not any(os.listdir(base+'/raw'))
 assert not os.path.lexists(base+'/logs/worker.log') and not os.path.lexists(base+'/logs/simulation.log')
 assert git(source,'rev-parse','HEAD')==sha and not git(source,'status','--porcelain')
 hashes={p:h(source+'/'+p) for p in e['source_hashes']};assert hashes==e['source_hashes']
 binary=h(source+'/build/scratch/network-load-balance');assert binary==e['binary_sha256']
 result['pending'].append({'id':i,'metadata':m,'metadata_sha256':h(base+'/metadata.json'),
  'source_hashes':hashes,'binary_sha256':binary,'never_started_raw_empty':True,'source_clean':True})
print(json.dumps(result))
'''.replace('EXPECTED',repr(expected)).replace('SHA',repr(PLAN['source_sha']))
    r=b.remote(code,timeout=180)
    assert r['tree']==subprocess.check_output(['git','-C',str(b.REPO),'rev-parse',PLAN['source_sha']+'^{tree}']).decode().strip()
    proofs={}
    for path in ('scripts/remote_worker.py','scripts/remote_experiment.py'):
        raw=(b.REPO/path).read_bytes();canonical=subprocess.check_output(['git','-C',str(b.REPO),'show',PLAN['source_sha']+':'+path])
        assert raw.replace(b'\r\n',b'\n')==canonical
        proofs[path]={'raw_sha256':hashlib.sha256(raw).hexdigest(),'canonical_git_lf_sha256':hashlib.sha256(canonical).hexdigest(),'newline_only_equivalence':True}
    assert r['worker_raw_sha256']==proofs['scripts/remote_worker.py']['raw_sha256']
    r['local_file_provenance']=proofs;dump('pending-built-source-cache-gate.json',r)
    b.state['deployed_worker_sha256']=r['worker_raw_sha256'];d.save();return r
def main():
    assert not b.RECEIPT.exists(),'Do not resume by repeating this driver'
    assert read(OUT/(PREFIX+'-offline-eight-acceptance.json'))['status']=='PASS_EIGHT_ORIGINAL_RAW_OFFLINE'
    preserved();d.save()
    assert b.controller.local_fork(str(b.REPO),require_pushed=True)[3]==PLAN['source_sha']
    localcode="Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.ProcessId -ne "+str(os.getpid())+" -and $_.CommandLine -match 'ws31|remote_experiment' } | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json"
    old=subprocess.check_output(['powershell','-NoProfile','-Command',localcode],text=True,encoding='utf-8',errors='replace')
    dump('local-process-gate.json',{'prior_driver_or_monitor':bool(old.strip()),'matches':old,'new_driver_pid':os.getpid()});assert not old.strip()
    for c in b.state['cells']:
        folder=b.EVIDENCE/c['id'];assert not folder.exists();folder.mkdir()
    resource(b.state['cells'][0],'resources-initial');built_gate()
    ref=read(OUT/(OLD+'-new-q12-reference.json'))
    for c in b.state['cells']:
        d.checkpoint(c,'RESOURCE_GATE_BEFORE_RUN');resource(c,'resources-before-run')
        args=[sys.executable,'-B',str(b.REPO/'scripts/remote_experiment.py'),'run',c['id'],'--lb',c['lb'],'--flow-file',c['flow_file'],
            '--ws30-tag-transform','0','--ws31-label-profile',str(c['ws31_label_profile'])]
        for k,v in ORIGINAL['common'].items():args+=['--'+k.replace('_','-'),str(v)]
        d.checkpoint(c,'STARTING_GUARDED_RUN');d.command(c,'guarded-run',args,90);b.state['network_runs_started']+=1
        if b.state['network_runs_started']==2:dump('calls-established.json',{'all_original_ten_calls_started':True,'new_calls':2,'entry_env_guard':'HELD until terminal release','at_utc':b.stamp()})
        d.checkpoint(c,'RUNNING');monitored=b.monitor(c);c['resource_samples']={k:v for k,v in monitored.items() if k!='metadata'}
        d.checkpoint(c,'TERMINAL_TRANSFERRING');target=b.transfer(c)
        assert monitored['metadata']['status']=='SUCCEEDED' and monitored['min_sampled_available_gib']>=4 and monitored['max_sampled_load_1m']<=20
        resource(c,'resources-after-run');d.checkpoint(c,'VERIFYING_ORIGINAL_FROZEN_CONTRACT')
        a=Q.verify(c,target,ref);assert a['status']=='PASS'
        (b.EVIDENCE/c['id']/'acceptance.json').write_text(json.dumps(a,indent=2)+'\n',encoding='utf-8');c['acceptance']=a;c['status']='PASS';d.save();print(c['id']+' PASS',flush=True)
    preserved();dump('original-r1-integrity-after.json',read(OUT/(PREFIX+'-original-r1-integrity-before.json')))
    dump('guards-released.json',{'status':'RELEASED','original_source_copies':10,'original_calls_started':10,'prior_completed_calls':8,
        'recovery_calls_terminal':2,'entry_env_guard':'RELEASED after both new calls terminal and verified','at_utc':b.stamp()})
    b.state['status']='COMPLETE_FOR_ORIGINAL_TEN_DYNAMIC_LABEL_CELLS_WITH_EIGHT_OFFLINE_PLUS_TWO_NEW_RUNS';d.save();print(b.state['status'],flush=True)
if __name__=='__main__':
    try:main()
    except BaseException as error:
        reason='COVERAGE_GAP' if isinstance(error,Q.CoverageGap) else 'FAILURE'
        b.state['status']='STOPPED_RECOVERY_ON_'+reason;b.state['error']=str(error);b.state['traceback']=traceback.format_exc()
        for c in b.state['cells']:
            if c['status']!='PASS':c['status']='STOPPED_NOT_PASSED'
        d.save();(OUT/(PREFIX+'-driver-error.log')).write_text(traceback.format_exc(),encoding='utf-8');print(b.state['status']+' '+str(error),flush=True);d.preserve_failure();raise
