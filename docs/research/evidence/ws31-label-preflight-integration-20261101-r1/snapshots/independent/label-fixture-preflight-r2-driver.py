"""One guarded build plus the new label core and mocked local runner only."""
import sys
sys.dont_write_bytecode=True
import pathlib,importlib.util,json,hashlib,subprocess,traceback,os
from concurrent.futures import ThreadPoolExecutor

OUT=pathlib.Path(__file__).resolve().parent
PREFIX='label-fixture-preflight-r2'
spec=importlib.util.spec_from_file_location('preflight_util',OUT/'main-mode-dynamic-r1-driver.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
b=d.b
d.PREFIX=b.PREFIX=PREFIX
PLAN=json.loads((OUT/(PREFIX+'-frozen-plan.json')).read_text(encoding='utf-8'))
b.PLAN=PLAN;b.RECEIPT=OUT/(PREFIX+'-receipt.json');b.EVIDENCE=OUT/(PREFIX+'-evidence')
CELL={'id':PLAN['id'],'status':'NOT_STARTED'}
b.state={'scope':PLAN['stage'],'source_sha':PLAN['source_sha'],'plan_sha256':hashlib.sha256((OUT/(PREFIX+'-frozen-plan.json')).read_bytes()).hexdigest(),
         'status':'STARTING','cells':[CELL],'commands':[],'network_runs_started':0,'old_core_tests_repeated':0,
         'new_build_commands':0,'new_cpp_core_commands':0,'python_mock_commands':0}
assert b.state['plan_sha256']=='7defac33294806d0369febbc79932e10263ac10112162642d0327eeb01366e3b'

def dump(name,value):
    (OUT/(PREFIX+'-'+name)).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

def fresh(name):
    result=d.fresh(CELL,name)
    assert result['available_gib']>=64 and result['free_gib']>=100 and result['loadavg'][0]<=4
    return result

def cache_snapshot(name,exact=False):
    code=r'''
import os,subprocess,json,hashlib
cache='/home/fnl/lzy/code/conweave-ns3';sha=SHA;i=ID
assert os.path.realpath(cache)==cache and not os.path.islink(cache)
def git(*a):return subprocess.check_output(['git','-C',cache]+list(a)).decode().strip()
exists=subprocess.call(['git','-C',cache,'cat-file','-e',sha+'^{commit}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)==0
worker='/home/fnl/lzy/.research-workflow/remote_worker.py'
r={'cache_realpath':os.path.realpath(cache),'origin':git('config','--get','remote.origin.url'),
 'clean':git('status','--porcelain'),'requested_commit_exists':exists,
 'branch_ref':git('rev-parse','refs/remotes/origin/feature/ws31-candidates'),
 'cache_head':git('rev-parse','HEAD'),'requested_tree':git('rev-parse',sha+'^{tree}') if exists else None,
 'new_id_runs_and_results_absent':all(not os.path.lexists('/home/fnl/lzy/'+p+'/'+i) for p in ['runs','results']),
 'deployed_worker_sha256':hashlib.sha256(open(worker,'rb').read()).hexdigest()}
assert r['origin']=='https://github.com/LarryBUPT/conweave-ns3.git' and not r['clean'] and r['new_id_runs_and_results_absent']
print(json.dumps(r))
'''.replace('SHA',repr(PLAN['source_sha'])).replace('ID',repr(PLAN['id']))
    result=b.remote(code,timeout=180);dump(name+'.json',result)
    if exact:
        assert result['requested_commit_exists'] and result['branch_ref']==PLAN['source_sha']
        assert result['requested_tree']==subprocess.check_output(['git','-C',str(b.REPO),'rev-parse',PLAN['source_sha']+'^{tree}']).decode().strip()
    return result

def core():
    code=r'''
import os,subprocess,json,hashlib,traceback
source=SOURCE;base=BASE
assert os.path.realpath(source)==source and os.path.realpath(base)==base
assert subprocess.check_output(['git','-C',source,'rev-parse','HEAD']).decode().strip()==SHA
folder=base+'/technical/ws31-label';assert not os.path.lexists(folder);os.makedirs(folder)
binary=folder+'/core-test';r={'status':'STARTING','steps':[]}
def save():
 with open(folder+'/receipt.json','w') as f:json.dump(r,f,indent=2)
def run(name,args):
 path=base+'/logs/'+name+'.log';assert not os.path.lexists(path)
 with open(path,'wb') as f:rc=subprocess.call(args,cwd=source,stdout=f,stderr=subprocess.STDOUT,timeout=180)
 r['steps'].append({'name':name,'argv':args,'cwd':source,'exit_code':rc,'log':path});save()
 if rc:raise RuntimeError(name+' failed')
try:
 run('ws31-label-core-compile',['g++','-std=c++11','-O2','-Wall','-Wextra','-pedantic','-UNDEBUG','tests/ws31_label_test.cc','-o',binary])
 symbols=subprocess.check_output(['nm','-C',binary]).decode();assert '__assert_fail' in symbols
 run('ws31-label-core-run',[binary])
 text=open(base+'/logs/ws31-label-core-run.log').read()
 assert 'WS31_LABEL_TEST PASS visibility/boundary/presence/unknown/hash/conflicts/context' in text
 r.update(status='PASS',stdout=text,assertions_enabled_symbol='__assert_fail',binary=binary,
  binary_sha256=hashlib.sha256(open(binary,'rb').read()).hexdigest(),
  source_hashes={p:hashlib.sha256(open(source+'/'+p,'rb').read()).hexdigest() for p in ['tests/ws31_label_test.cc','src/point-to-point/model/ws31-label-fixture.h','src/point-to-point/model/ws31-start.h']},
  compiler_version=subprocess.check_output(['g++','--version']).decode().splitlines()[0])
except BaseException as error:r.update(status='FAIL',error=str(error),traceback=traceback.format_exc())
save();print(json.dumps(r))
'''.replace('SOURCE',repr('/home/fnl/lzy/runs/'+PLAN['id']+'/source')).replace('BASE',repr('/home/fnl/lzy/results/'+PLAN['id'])).replace('SHA',repr(PLAN['source_sha']))
    result=b.remote(code,timeout=450);dump('core-receipt.json',result)
    b.state['new_cpp_core_commands']=len(result['steps']);b.state['new_cpp_core_status']=result['status'];d.save()
    assert result['status']=='PASS',result
    for path,h in result['source_hashes'].items():
        assert hashlib.sha256(subprocess.check_output(['git','-C',str(b.REPO),'show',PLAN['source_sha']+':'+path])).hexdigest()==h
    return result

def main():
    assert not b.RECEIPT.exists(),'No overwrite or repeated build/core'
    assert json.loads((OUT/(PREFIX+'-source-review.json')).read_text(encoding='utf-8'))['no_material_source_issue_found']
    d.save();folder=b.EVIDENCE/CELL['id'];assert not folder.exists();folder.mkdir()
    fork=b.controller.local_fork(str(b.REPO),require_pushed=True);assert fork[3]==PLAN['source_sha']
    localcode="Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.ProcessId -ne "+str(os.getpid())+" -and $_.CommandLine -match 'ws31|remote_experiment' } | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json"
    old=subprocess.check_output(['powershell','-NoProfile','-Command',localcode],text=True,encoding='utf-8',errors='replace')
    dump('local-process-gate.json',{'prior_driver_or_monitor':bool(old.strip()),'matches':old});assert not old.strip()
    fresh('resources-before-sync');cache=cache_snapshot('cache-before-sync')
    if not(cache['requested_commit_exists'] and cache['branch_ref']==PLAN['source_sha']):
        d.command(CELL,'guarded-sync',[sys.executable,'-B',str(b.REPO/'scripts/remote_experiment.py'),'sync','--repo-local',str(b.REPO)],timeout=900)
        b.state['sync_executed']=True
    else:b.state['sync_executed']=False
    cache_snapshot('cache-after-sync',exact=True);fresh('resources-before-deploy')
    d.command(CELL,'guarded-worker-deploy',[sys.executable,'-B',str(b.REPO/'scripts/remote_experiment.py'),'deploy'],timeout=180)
    current=cache_snapshot('cache-after-deploy',exact=True)
    expected=hashlib.sha256((b.REPO/'scripts/remote_worker.py').read_bytes()).hexdigest()
    assert current['deployed_worker_sha256']==expected;b.state['deployed_worker_sha256']=expected;d.save()
    fresh('resources-before-build');b.state['new_build_commands']=1;d.save()
    error=None
    with ThreadPoolExecutor(max_workers=1) as pool:
        sampler=pool.submit(d.build_sampler)
        try:d.do_build(CELL)
        except BaseException as failure:error=failure
        finally:
            if error:
                logs='/home/fnl/lzy/results/'+PLAN['id']+'/logs'
                b.remote("import os,json;p="+repr(logs)+";ok=os.path.isdir(p);open(p+'/build-batch-monitor-stop.json','w').write('{}') if ok else None;print(json.dumps({'monitor_stop':ok}))")
            sampled=sampler.result()
    b.state['build_resource_samples']=sampled;d.save()
    if error:raise error
    assert not sampled['other_user_seen'] and not sampled['unknown_project_seen']
    assert sampled['max_sampled_load_1m']<=20 and sampled['min_sampled_available_gib']>=4 and sampled['min_sampled_free_gib']>=20
    builds=d.verify_builds();dump('sources-established.json',{'status':'PASS','source_sha':PLAN['source_sha'],'builds':builds,
        'source_copy_complete':True,'compatibility_guard':'HELD until core and localmock finish','at_utc':b.stamp()})
    d.checkpoint(CELL,'BUILD_PASSED_NEW_CORE_PENDING');fresh('resources-before-core');core()
    fresh('resources-after-core')
    assert b.controller.local_fork(str(b.REPO),require_pushed=True)[3]==PLAN['source_sha']
    b.state['python_mock_commands']=1;d.save()
    d.command(CELL,'python-local-runner-mock',[sys.executable,'-B',str(b.REPO/'tests/ws31_label_runner_test.py')],timeout=180)
    text=(folder/'python-local-runner-mock.log').read_text(encoding='utf-8')
    assert 'Ran 5 tests' in text and re_search_ok(text)
    dump('local-mock-receipt.json',{'status':'PASS','methods':5,'command':'python -B tests/ws31_label_runner_test.py','remote_entry_points':'mocked','log_sha256':hashlib.sha256(text.encode()).hexdigest(),'source_hashes':{p:hashlib.sha256((b.REPO/p).read_bytes()).hexdigest() for p in ['tests/ws31_label_runner_test.py','scripts/remote_experiment.py','scripts/remote_worker.py']}})
    fresh('resources-final');target=b.transfer(CELL)
    meta=json.loads((target/'metadata.json').read_text(encoding='utf-8'));assert meta['status']=='BUILT' and meta['git_commit']==PLAN['source_sha']
    assert not any((target/'raw').rglob('*')),'No network raw expected'
    b.state['compatibility_guard']='RELEASED all preflight commands terminal; source copy verified'
    dump('guards-released.json',{'status':'RELEASED','source_copy_complete':True,'at_utc':b.stamp(),'network_runs':0})
    CELL['status']='PASS';b.state['status']='COMPLETE_FOR_SINGLE_FULL_BUILD_NEW_LABEL_CORE_AND_LOCAL_MOCK_ONLY';d.save();print(b.state['status'],flush=True)

def re_search_ok(text):
    import re
    return bool(re.search(r'^OK\s*$',text,re.M))

if __name__=='__main__':
    try:main()
    except BaseException as error:
        b.state['status']='STOPPED_ON_PREFLIGHT_FAILURE';b.state['error']=str(error);b.state['traceback']=traceback.format_exc();CELL['status']='STOPPED_ON_FAILURE';d.save()
        (OUT/(PREFIX+'-driver-error.log')).write_text(traceback.format_exc(),encoding='utf-8');print(b.state['status']+' '+str(error),flush=True)
        d.preserve_failure();raise
