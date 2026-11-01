"""One full isolated build, direct new C1/C2/C3 adapter executables only."""
import sys
sys.dont_write_bytecode=True
import base64,hashlib,importlib.util,json,os,pathlib,subprocess,traceback
from concurrent.futures import ThreadPoolExecutor
OUT=pathlib.Path(__file__).resolve().parent
PREFIX='adapter-boundary-preflight-r2'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
spec=importlib.util.spec_from_file_location('adapter_build_helpers',OUT/'main-mode-dynamic-r1-driver.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d);b=d.b
d.PREFIX=b.PREFIX=PREFIX
PLAN=read(OUT/(PREFIX+'-frozen-plan.json'));CELL={'id':PLAN['id'],'status':'NOT_STARTED'}
b.PLAN=PLAN;b.RECEIPT=OUT/(PREFIX+'-receipt.json');b.EVIDENCE=OUT/(PREFIX+'-evidence')
b.state={'status':'STARTING','scope':PLAN['stage'],'source_sha':PLAN['source_sha'],'cells':[CELL],'commands':[],
    'plan_sha256':hashlib.sha256((OUT/(PREFIX+'-frozen-plan.json')).read_bytes()).hexdigest(),'driver_pid':os.getpid(),
    'network_runs_started':0,'build_commands':0,'fixture_commands':0,'core_commands':0,'sync_commands':0,'deploy_commands':0}
assert b.state['plan_sha256']=='e09f0883fe8839f5e77ee2797ebbf75aeb88e0fa9959b7b7ddf84b5acb328061'
def dump(suffix,r):(OUT/(PREFIX+'-'+suffix)).write_text(json.dumps(r,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
def resource(name,initial=False):
    r=d.fresh(CELL,name)
    if initial:assert r['available_gib']>=64 and r['free_gib']>=100 and r['loadavg'][0]<=4
    return r
def cache(name,exact=False):
    code=r'''
import os,json,subprocess,hashlib
cache='/home/fnl/lzy/code/conweave-ns3';sha=SHA;i=ID
assert os.path.realpath(cache)==cache and not os.path.islink(cache)
def git(*a):return subprocess.check_output(['git','-C',cache]+list(a)).decode().strip()
with open(os.devnull,'wb') as sink:exists=subprocess.call(['git','-C',cache,'cat-file','-e',sha+'^{commit}'],stdout=sink,stderr=sink)==0
r={'origin':git('config','--get','remote.origin.url'),'cache_realpath':os.path.realpath(cache),'clean':git('status','--porcelain'),
 'requested_commit_exists':exists,'requested_tree':git('rev-parse',sha+'^{tree}') if exists else None,
 'branch_ref':git('rev-parse','refs/remotes/origin/feature/ws31-candidates'),
 'new_id_absent':all(not os.path.lexists('/home/fnl/lzy/'+p+'/'+i) for p in ['runs','results']),
 'old_reserved_id_absent':all(not os.path.lexists('/home/fnl/lzy/'+p+'/20261101-143000-ws31-adapter-preflight-r1') for p in ['runs','results']),
 'worker_raw_sha256':hashlib.sha256(open('/home/fnl/lzy/.research-workflow/remote_worker.py','rb').read()).hexdigest()}
assert r['origin']=='https://github.com/LarryBUPT/conweave-ns3.git' and not r['clean'] and r['new_id_absent'] and r['old_reserved_id_absent']
print(json.dumps(r))
'''.replace('SHA',repr(PLAN['source_sha'])).replace('ID',repr(PLAN['id']))
    r=b.remote(code,timeout=180);proof={}
    for path in ('scripts/remote_worker.py','scripts/remote_experiment.py'):
        raw=(b.REPO/path).read_bytes();canonical=subprocess.check_output(['git','-C',str(b.REPO),'show',PLAN['source_sha']+':'+path])
        assert raw.replace(b'\r\n',b'\n')==canonical
        proof[path]={'raw_sha256':hashlib.sha256(raw).hexdigest(),'git_lf_sha256':hashlib.sha256(canonical).hexdigest(),'newline_only_equivalence':True}
    assert r['worker_raw_sha256']==proof['scripts/remote_worker.py']['raw_sha256']
    if exact:
        assert r['requested_commit_exists'] and r['branch_ref']==PLAN['source_sha']
        assert r['requested_tree']==subprocess.check_output(['git','-C',str(b.REPO),'rev-parse',PLAN['source_sha']+'^{tree}']).decode().strip()
    r['local_provenance']=proof;b.state['deployed_worker_sha256']=r['worker_raw_sha256'];dump(name+'.json',r);d.save();return r
def artifacts():
    code=r'''
import os,json,subprocess,hashlib,re,shutil
source=SOURCE;base=BASE;frozen=ENV
assert os.path.realpath(source)==source and os.path.realpath(base)==base
assert subprocess.check_output(['git','-C',source,'rev-parse','HEAD']).decode().strip()==SHA
folder=base+'/technical/adapter-boundary';assert not os.path.lexists(folder);os.makedirs(folder+'/artifacts/binaries');os.makedirs(folder+'/artifacts/libraries')
env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','LD_LIBRARY_PATH':source+'/build'};env.update(frozen)
result={'status':'PREPARED','source_sha':SHA,'env_whitelist':env,'removed_inheritance':'Constructed whitelist; no diagnostic/legacy/preload/log/global-value variables inherited','binaries':{},'libraries':{},'ldd':{},'steps':[]}
def h(p):return hashlib.sha256(open(p,'rb').read()).hexdigest()
for name in ['ws31-switch-boundary-test','ws31-start-boundary-test']:
 path=source+'/build/scratch/'+name;assert os.path.isfile(path) and os.path.realpath(path).startswith(source+'/build/')
 result['binaries'][name]={'source_path':path,'sha256':h(path),'artifact':'technical/adapter-boundary/artifacts/binaries/'+name}
 shutil.copy2(path,folder+'/artifacts/binaries/'+name)
 output=subprocess.check_output(['ldd',path],env=env,stderr=subprocess.STDOUT).decode();assert 'not found' not in output
 result['ldd'][name]=output
 for line in output.splitlines():
  match=re.search(r'(\S+)\s+=>\s+(\S+)\s+\(',line)
  if match and match.group(1).startswith('libns3'):
   lib=os.path.realpath(match.group(2));assert lib.startswith(source+'/build/') and os.path.isfile(lib)
   key=os.path.basename(lib)
   if key not in result['libraries']:
    result['libraries'][key]={'source_path':lib,'sha256':h(lib),'artifact':'technical/adapter-boundary/artifacts/libraries/'+key};shutil.copy2(lib,folder+'/artifacts/libraries/'+key)
assert result['libraries']
with open(folder+'/receipt.json','w') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
'''.replace('SOURCE',repr('/home/fnl/lzy/runs/'+PLAN['id']+'/source')).replace('BASE',repr('/home/fnl/lzy/results/'+PLAN['id'])).replace('SHA',repr(PLAN['source_sha'])).replace('ENV',repr(PLAN['environment']))
    r=b.remote(code,timeout=180);dump('artifact-preparation.json',r);return r
def execute(step):
    code=r'''
import os,json,subprocess,hashlib,time,datetime,resource,base64,traceback
source=SOURCE;base=BASE;step=STEP
folder=base+'/technical/adapter-boundary';path=folder+'/receipt.json';r=json.load(open(path));env=r['env_whitelist']
argv=[source+'/'+step['relative_binary']]+step['args'];name=step['candidate'];log=base+'/logs/adapter-'+name+'.log';assert not os.path.lexists(log)
assert env['LD_LIBRARY_PATH']==source+'/build'
s={'candidate':name,'argv':argv,'cwd':source,'env_whitelist':env,'start_utc':datetime.datetime.utcnow().isoformat()+'Z','log':log};r['steps'].append(s)
with open(path,'w') as f:json.dump(r,f,indent=2)
start=time.monotonic()
with open(log,'wb') as out:
 proc=subprocess.Popen(argv,cwd=source,env=env,stdout=out,stderr=subprocess.STDOUT);s['pid']=proc.pid
 try:s['exit_code']=proc.wait(timeout=180)
 except subprocess.TimeoutExpired:s['exit_code']=None;s['timeout']=True
s['wall_seconds']=time.monotonic()-start;s['end_utc']=datetime.datetime.utcnow().isoformat()+'Z';s['children_maxrss_kib']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
raw=open(log,'rb').read();s['log_sha256']=hashlib.sha256(raw).hexdigest();s['log_bytes']=len(raw)
text=raw.decode('utf-8','strict')
if name in ('C1','C3'):
 cases=[line.split('case=',1)[1] for line in text.splitlines() if line.startswith('WS31_SWITCH_BOUNDARY PASS case=')]
 s['cases']=cases;s['coverage_pass']=cases==step['expected_cases'] and ('WS31_SWITCH_BOUNDARY_SUMMARY PASS candidate='+name.lower()+' cases='+str(step['case_count'])+' network_runs=0 endpoint_generations=0') in text
else:
 lines=[line for line in text.splitlines() if line.startswith('WS31_C2_BOUNDARY PASS ')];s['case_lines']=lines;s['coverage_pass']=len(lines)==10 and 'WS31_C2_BOUNDARY_SUMMARY PASS cases=10 network_runs=0 completions=0' in text
s['status']='PASS' if s['exit_code']==0 and s['coverage_pass'] else 'FAIL';r['status']=s['status']
with open(path,'w') as f:json.dump(r,f,indent=2)
answer={'step':s,'stdout_b64':base64.b64encode(raw).decode('ascii')};print(json.dumps(answer))
'''.replace('SOURCE',repr('/home/fnl/lzy/runs/'+PLAN['id']+'/source')).replace('BASE',repr('/home/fnl/lzy/results/'+PLAN['id'])).replace('STEP',repr(step))
    r=b.remote(code,timeout=220);name=step['candidate'];log=b.EVIDENCE/CELL['id']/('adapter-'+name+'.log')
    assert not log.exists();log.write_bytes(base64.b64decode(r.pop('stdout_b64')))
    assert hashlib.sha256(log.read_bytes()).hexdigest()==r['step']['log_sha256']
    dump('execution-'+name+'.json',r['step']);b.state.setdefault('executions',[]).append(r['step']);b.state['fixture_commands']+=1;d.save()
    assert r['step']['status']=='PASS',name+' fixture failed'
    checked=V.c2(log) if name=='C2' else V.switch(log,name);dump('raw-verification-'+name+'.json',checked)
# Injected into the r2 driver by its local preparation script.
v_spec=importlib.util.spec_from_file_location('adapter_raw_verifier',OUT/(PREFIX+'-verify.py'))
V=importlib.util.module_from_spec(v_spec);v_spec.loader.exec_module(V)
def save_ascii():
    with d.LOCK:
        b.state['updated_utc']=b.stamp();temp=b.RECEIPT.with_suffix('.tmp')
        temp.write_text(json.dumps(b.state,ensure_ascii=True,indent=2)+'\n',encoding='utf-8');temp.replace(b.RECEIPT)
d.save=b.save=save_ascii
def preserved():
    previous=read(OUT/(PREFIX+'-original-r1-integrity-before.json'))
    for p,info in previous.items():
        path=OUT/p;assert path.stat().st_size==info['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==info['sha256']
    return previous
def process_gate(name):
    code=r'''
import os,json,re,datetime
root='/home/fnl/lzy';mine=os.getpid();uid=os.getuid();rows={};unknown=[];other=[];compute=[];helpers=[]
for name in os.listdir('/proc'):
 if not name.isdigit():continue
 pid=int(name)
 try:
  s=open('/proc/'+name+'/status').read();owner=int(re.search(r'^Uid:\s+(\d+)',s,re.M).group(1));parent=int(re.search(r'^PPid:\s+(\d+)',s,re.M).group(1));state=re.search(r'^State:\s+(.+)',s,re.M).group(1);comm=open('/proc/'+name+'/comm').read().strip()
  try:cwd=os.readlink('/proc/'+name+'/cwd')
  except OSError:cwd=None
  row={'pid':pid,'ppid':parent,'uid':owner,'state':state,'comm':comm,'cwd':cwd};rows[pid]=row
  if pid==mine:continue
  if owner>=1000 and owner!=uid and not state.startswith('Z'):other.append(pid)
  if comm.startswith(('network-load','cc1plus','g++','gcc','waf')):compute.append(pid)
  if comm.startswith('git'):helpers.append(pid)
  if owner==uid and ((cwd and (cwd==root or cwd.startswith(root+'/'))) or comm.startswith('git')):unknown.append(pid)
 except (OSError,IOError,AttributeError):pass
chains={}
for pid in set(unknown+other+compute+helpers):
 chain=[];seen=set();cursor=pid
 while cursor and cursor not in seen and cursor in rows and len(chain)<10:
  seen.add(cursor);chain.append(rows[cursor]);cursor=rows[cursor]['ppid']
 chains[str(pid)]=chain
r={'utc':datetime.datetime.utcnow().isoformat()+'Z','self_pid':mine,'all_processes':list(rows.values()),'unknown_project_pids':unknown,'other_user_pids':other,'compute_pids':compute,'git_helper_pids':helpers,'relevant_ancestor_chains':chains,'gate_pass':not unknown and not other and not compute}
print(json.dumps(r))
'''
    result=b.remote(code,timeout=180);dump(name+'.json',result)
    assert result['gate_pass'],'Fresh all-process gate failed: '+name
    return result

def main():
    assert not b.RECEIPT.exists(),'No repeated build/test or ID overwrite'
    assert read(OUT/(PREFIX+'-source-review.json'))['no_material_source_issue_found'];preserved()
    d.save();folder=b.EVIDENCE/CELL['id'];assert not folder.exists();folder.mkdir()
    assert b.controller.local_fork(str(b.REPO),require_pushed=True)[3]==PLAN['source_sha']
    query="Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.ProcessId -ne "+str(os.getpid())+" -and $_.CommandLine -match 'ws31|remote_experiment' } | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json"
    old=subprocess.check_output(['powershell','-NoProfile','-Command',query],text=True,encoding='utf-8',errors='replace');dump('local-process-gate.json',{'prior_driver_or_monitor':bool(old.strip()),'matches':old});assert not old.strip()
    process_gate('processes-initial');resource('resources-initial',True);cache('cache-read-only',True);process_gate('processes-before-build')
    resource('resources-before-build',True);b.state['build_commands']=1;d.save();error=None
    with ThreadPoolExecutor(max_workers=1) as pool:
        sampler=pool.submit(d.build_sampler)
        try:d.do_build(CELL)
        except BaseException as e:
            error=e;base='/home/fnl/lzy/results/'+PLAN['id']+'/logs'
            b.remote("import os,json;p="+repr(base)+";ok=os.path.isdir(p);open(p+'/build-batch-monitor-stop.json','w').write('{}') if ok else None;print(json.dumps({'monitor_stop':ok}))")
        sampled=sampler.result()
    b.state['build_resources']=sampled;d.save()
    if error:raise error
    assert not sampled['other_user_seen'] and not sampled['unknown_project_seen'] and sampled['max_sampled_cc1plus_count']<=2
    assert sampled['min_sampled_available_gib']>=4 and sampled['min_sampled_free_gib']>=20 and sampled['max_sampled_load_1m']<=20
    builds=d.verify_builds();dump('sources-established.json',{'source_sha':PLAN['source_sha'],'builds':builds,'all_fixed_copies_verified':True,'guard':'HELD until all3 direct fixture commands terminal','at_utc':b.stamp()})
    resource('resources-before-artifact-preparation');artifacts()
    for step in PLAN['ordered_executions']:
        resource('resources-before-'+step['candidate']);d.checkpoint(CELL,'RUNNING_NEW_ADAPTER_'+step['candidate']);execute(step);resource('resources-after-'+step['candidate'])
    d.checkpoint(CELL,'FETCHING_NEW_ADAPTER_EVIDENCE');target=b.transfer(CELL)
    assert not any((target/'raw').rglob('*')) and read(target/'metadata.json')['status']=='BUILT'
    preserved();dump('original-r1-integrity-after.json',read(OUT/(PREFIX+'-original-r1-integrity-before.json')))
    dump('guards-released.json',{'status':'RELEASED','source_copy_verified':True,'fixture_calls_terminal':3,'network_calls':0,'at_utc':b.stamp()})
    CELL['status']='PASS';b.state['status']='COMPLETE_FOR_ONE_BUILD_AND_NEW_17_ADAPTER_BOUNDARY_CASES_ONLY';d.save();print(b.state['status'],flush=True)
if __name__=='__main__':
    try:main()
    except BaseException as error:
        b.state['status']='STOPPED_ADAPTER_PREFLIGHT_ON_FAILURE';b.state['error']=str(error);b.state['traceback']=traceback.format_exc();CELL['status']='STOPPED_NOT_PASSED';d.save()
        (OUT/(PREFIX+'-driver-error.log')).write_text(traceback.format_exc(),encoding='utf-8');print(b.state['status']+' '+str(error),flush=True);d.preserve_failure();raise
