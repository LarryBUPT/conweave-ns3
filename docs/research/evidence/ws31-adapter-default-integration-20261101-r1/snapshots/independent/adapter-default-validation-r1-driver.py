"""Two new default-compatibility builds then serial Q12/C2, no reference reruns."""
import sys
sys.dont_write_bytecode=True
import ast,hashlib,importlib.util,json,os,pathlib,subprocess,traceback
from concurrent.futures import ThreadPoolExecutor,as_completed
OUT=pathlib.Path(__file__).resolve().parent
PREFIX='adapter-default-validation-r1'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('adapter_default_shared',OUT/'label-default-validation-r1-driver.py')
S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S);L,d,b=S.L,S.d,S.b
L.PREFIX=d.PREFIX=b.PREFIX=PREFIX
PLAN=read(OUT/(PREFIX+'-frozen-plan.json'));b.PLAN=PLAN;b.RECEIPT=OUT/(PREFIX+'-receipt.json');b.EVIDENCE=OUT/(PREFIX+'-evidence')
b.state={'scope':PLAN['scope'],'source_sha':PLAN['source_sha'],'status':'STARTING','cells':[dict(c,status='NOT_STARTED',ws30_tag_transform=0) for c in PLAN['cells']],
    'plan_sha256':sha(OUT/(PREFIX+'-frozen-plan.json')),'commands':[],'network_runs_started':0,'build_commands':0,'sync_commands':0,'deploy_commands':0,
    'core_commands':0,'fixture_commands':0,'reference_runs':0,'driver_pid':os.getpid(),'build_parallelism':2,'max_compile_jobs':4,
    'model_switch':'No model switch performed or claimed; no switching interface available'}
assert b.state['plan_sha256']=='01665606c32d7422b92f4202d23e8e571500321631ca376b5924ed67f5e7eb68'
def dump(s,v):(OUT/(PREFIX+'-'+s)).write_text(json.dumps(v,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
def save():
    with d.LOCK:
        b.state['updated_utc']=b.stamp();tmp=b.RECEIPT.with_suffix('.tmp');tmp.write_text(json.dumps(b.state,ensure_ascii=True,indent=2)+'\n',encoding='utf-8');tmp.replace(b.RECEIPT)
d.save=b.save=save
# Reuse only the reviewed read-only process inventory function, never its driver.
addition=(OUT/'adapter-boundary-preflight-r2-driver-additions.py').read_text(encoding='utf-8')
tree=ast.parse(addition);part=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='process_gate')
exec(ast.get_source_segment(addition,part),globals())
def resource(c,name,initial=False):
    r=d.fresh(c,name)
    if initial:assert r['available_gib']>=64 and r['free_gib']>=100 and r['loadavg'][0]<=4
    return r
def cache_gate():
    code=r'''
import os,json,subprocess,hashlib
cache='/home/fnl/lzy/code/conweave-ns3';sha=SHA;ids=IDS
assert os.path.realpath(cache)==cache and not os.path.islink(cache)
def git(*a):return subprocess.check_output(['git','-C',cache]+list(a)).decode().strip()
subprocess.check_call(['git','-C',cache,'cat-file','-e',sha+'^{commit}'])
r={'cache_realpath':os.path.realpath(cache),'origin':git('config','--get','remote.origin.url'),'clean':git('status','--porcelain'),
 'branch_ref':git('rev-parse','refs/remotes/origin/feature/ws31-candidates'),'requested_tree':git('rev-parse',sha+'^{tree}'),
 'all_new_ids_absent':all(not os.path.lexists('/home/fnl/lzy/'+p+'/'+i) for i in ids for p in ['runs','results']),
 'worker_raw_sha256':hashlib.sha256(open('/home/fnl/lzy/.research-workflow/remote_worker.py','rb').read()).hexdigest()}
assert r['origin']=='https://github.com/LarryBUPT/conweave-ns3.git' and not r['clean'] and r['branch_ref']==sha and r['all_new_ids_absent']
print(json.dumps(r))
'''.replace('SHA',repr(PLAN['source_sha'])).replace('IDS',repr([c['id'] for c in b.state['cells']]))
    r=b.remote(code,timeout=180);proof={}
    for path in ('scripts/remote_worker.py','scripts/remote_experiment.py'):
        raw=(b.REPO/path).read_bytes();canonical=subprocess.check_output(['git','-C',str(b.REPO),'show',PLAN['source_sha']+':'+path]);assert raw.replace(b'\r\n',b'\n')==canonical
        proof[path]={'raw_sha256':hashlib.sha256(raw).hexdigest(),'canonical_git_lf_sha256':hashlib.sha256(canonical).hexdigest(),'newline_only_equivalence':True}
    assert r['worker_raw_sha256']==proof['scripts/remote_worker.py']['raw_sha256']
    assert r['requested_tree']==subprocess.check_output(['git','-C',str(b.REPO),'rev-parse',PLAN['source_sha']+'^{tree}']).decode().strip()
    r['local_provenance']=proof;dump('cache-worker-gate.json',r);b.state['deployed_worker_sha256']=r['worker_raw_sha256'];save()
def dedicated(log):
    h=hashlib.sha256();counts={}
    with log.open('rb') as stream:
        for line in stream:
            assert not line.startswith((b'WS31_LABEL',b'WS31_SWITCH_BOUNDARY',b'WS31_C2_BOUNDARY')),'Unexpected active label or fixture observations'
            if line.startswith(b'WS31_C2_'):
                h.update(line);key=line.split(b' ',1)[0].decode('ascii');counts[key]=counts.get(key,0)+1
    return {'sha256':h.hexdigest(),'event_counts':counts}
def references():
    ref={}
    for c in b.state['cells']:
        root=pathlib.Path(c['reference_results']);fct=next((root/'raw').glob('*/*_out_fct.txt'));log=next((root/'raw').glob('*/config.log'))
        assert sha(fct)==c['reference_fct_sha256'] and sha(log)==c['reference_log_sha256']
        m=read(root/'metadata.json');assert m['git_commit']==c['reference_sha'] and m['status']=='SUCCEEDED'
        ref[c['id']]={'root':root,'fct':fct,'ordered':L.reference(root),'dedicated':dedicated(log)}
    return ref
def analyze(c,target,ref):
    L.analyze(c,target,{})
    meta=read(target/'metadata.json');assert meta['parameters']['ws31_label_profile']==0
    assert all(meta['parameters'].get(k,0)==0 for k in ['ws30_tag_transform','ws30_composition','ws30_lifecycle','ws30_life_profile','ws21_heartbeat_fault_mode'])
    fct=next((target/'raw').glob('*/*_out_fct.txt'));log=next((target/'raw').glob('*/config.log'))
    assert fct.read_bytes()==ref['fct'].read_bytes()
    assert c['acceptance']['ordered_hashes']==ref['ordered']['hashes'] and c['acceptance']['observation_counts']==ref['ordered']['counts']
    actual=dedicated(log);assert actual==ref['dedicated']
    if c['lb']=='ws31-c2':assert actual['event_counts']=={'WS31_C2_DEMAND':104,'WS31_C2_LAUNCH':104,'WS31_C2_FINISH':104,'WS31_C2_STATE':1}
    else:assert not actual['event_counts']
    for rel in ('config/traffic_trace.txt','config/topology.txt'):assert (target/rel).read_bytes()==(ref['root']/rel).read_bytes()
    config=dict(line.split(None,1) for line in (target/'config/config.txt').read_text(encoding='ascii').splitlines() if line.strip())
    assert config['LB_MODE']==str(c['lb_mode']) and config['WS21_HEARTBEAT_FAULT_MODE']=='0'
    proof={'status':'PASS_DEFAULT_DISPATCH_COMPATIBILITY','reference_id':c['reference_id'],'reference_sha':c['reference_sha'],'full_fct_bytes_equal':True,
        'ordered_choice_route_equal_remove_uid_only':True,'actual_packet_tag_retained_and_original_checked':True,'dedicated_events':actual,
        'profile':0,'all_required_old_interventions_off':True,'no_label_or_adapter_fixture_observations':True}
    (b.EVIDENCE/c['id']/'compatibility.json').write_text(json.dumps(proof,ensure_ascii=True,indent=2)+'\n',encoding='utf-8');c['compatibility']=proof;save()
def main():
    assert not b.RECEIPT.exists(),'No repeated IDs or driver'
    assert read(OUT/(PREFIX+'-execution-authorization.json'))['status']=='CONDITIONAL_PLAN_PREREQUISITES_MET_MAIN_DISPATCH_AUTHORIZED'
    assert b.controller.local_fork(str(b.REPO),require_pushed=True)[3]==PLAN['source_sha'];save()
    for c in b.state['cells']:
        folder=b.EVIDENCE/c['id'];assert not folder.exists();folder.mkdir()
    local="Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.ProcessId -ne "+str(os.getpid())+" -and $_.CommandLine -match 'ws31|remote_experiment' } | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json"
    old=subprocess.check_output(['powershell','-NoProfile','-Command',local],text=True,encoding='utf-8',errors='replace');dump('local-process-gate.json',{'prior_driver_or_monitor':bool(old.strip()),'matches':old});assert not old.strip()
    process_gate('processes-initial');resource(b.state['cells'][0],'resources-initial',True);cache_gate();refs=references()
    process_gate('processes-before-build');resource(b.state['cells'][0],'resources-before-build',True)
    errors=[];b.state['build_commands']=2;save()
    with ThreadPoolExecutor(max_workers=3) as pool:
        sampler=pool.submit(d.build_sampler)
        for future in as_completed([pool.submit(d.do_build,c) for c in b.state['cells']]):
            try:future.result()
            except BaseException as error:errors.append(str(error))
        if errors:
            base='/home/fnl/lzy/results/'+b.state['cells'][0]['id']+'/logs'
            b.remote("import os,json;p="+repr(base)+";ok=os.path.isdir(p);open(p+'/build-batch-monitor-stop.json','w').write('{}') if ok else None;print(json.dumps({'stopped':ok}))")
        sampled=sampler.result()
    b.state['build_resources']=sampled;save()
    if errors:raise RuntimeError('; '.join(errors))
    assert not sampled['other_user_seen'] and not sampled['unknown_project_seen'] and sampled['max_sampled_cc1plus_count']<=4 and sampled['max_sampled_building_metadata_count']<=2
    assert sampled['max_sampled_load_1m']<=20 and sampled['min_sampled_available_gib']>=4 and sampled['min_sampled_free_gib']>=20
    builds=d.verify_builds();b.state['all_builds_verified_before_runs']=True;dump('sources-established.json',{'source_sha':PLAN['source_sha'],'builds':builds,'both_fixed_copies_verified':True,'guard':'HELD until both guarded network calls terminal','at_utc':b.stamp()});save()
    for c in b.state['cells']:
        resource(c,'resources-before-run');d.checkpoint(c,'STARTING_GUARDED_RUN')
        args=[sys.executable,'-B',str(b.REPO/'scripts/remote_experiment.py'),'run',c['id'],'--lb',c['lb'],'--ws30-tag-transform','0']
        for k,v in PLAN['common'].items():args+=['--'+k.replace('_','-'),str(v)]
        d.command(c,'guarded-run',args,90);b.state['network_runs_started']+=1;d.checkpoint(c,'RUNNING')
        monitored=b.monitor(c);c['resource_samples']={k:v for k,v in monitored.items() if k!='metadata'}
        d.checkpoint(c,'TRANSFERRING');target=b.transfer(c)
        assert monitored['metadata']['status']=='SUCCEEDED' and monitored['min_sampled_available_gib']>=4 and monitored['max_sampled_load_1m']<=20
        resource(c,'resources-after-run');d.checkpoint(c,'VERIFYING_FULL_DEFAULT_REGRESSION');analyze(c,target,refs[c['id']]);c['status']='PASS';save();print(c['id']+' PASS',flush=True)
    before=read(OUT/(PREFIX+'-reference-integrity-before.json'))
    for p,info in before.items():assert pathlib.Path(p).stat().st_size==info['bytes'] and sha(pathlib.Path(p))==info['sha256']
    dump('reference-integrity-after.json',before);dump('guards-released.json',{'status':'RELEASED','fixed_source_copies':2,'network_calls_terminal':2,'at_utc':b.stamp()})
    b.state['status']='COMPLETE_FOR_TWO_DEFAULT_DISPATCH_NETWORK_COMPATIBILITY_CELLS_ONLY';save();print(b.state['status'],flush=True)
if __name__=='__main__':
    try:main()
    except BaseException as error:
        b.state['status']='STOPPED_ADAPTER_DEFAULT_ON_FAILURE';b.state['error']=str(error);b.state['traceback']=traceback.format_exc()
        for c in b.state['cells']:
            if c['status'] not in ('PASS','BUILD_FAILED'):c['status']='STOPPED_NOT_PASSED'
        save();(OUT/(PREFIX+'-driver-error.log')).write_text(traceback.format_exc(),encoding='utf-8');print(b.state['status']+' '+str(error),flush=True);d.preserve_failure();raise
