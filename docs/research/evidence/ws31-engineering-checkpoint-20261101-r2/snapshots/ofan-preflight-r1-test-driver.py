import sys,pathlib,json,subprocess,shlex,importlib.util,hashlib
sys.dont_write_bytecode=True
out=pathlib.Path(__file__).resolve().parent;prefix='ofan-preflight-r1';p=out/(prefix+'-receipt.json');r=json.loads(p.read_text(encoding='utf-8'));repo=pathlib.Path(r['local_source'])
assert r['status']=='BUILD_COMMAND_PASSED'
spec=importlib.util.spec_from_file_location('controller',str(repo/'scripts/remote_experiment.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);cfg=m.config()
remote=r"""import os,json,subprocess,hashlib,datetime,re,sys
source=SOURCE
base=BASE
sha=SHA
assert os.path.realpath(source)==source and os.path.realpath(base)==base
assert subprocess.check_output(['git','-C',source,'rev-parse','HEAD']).decode().strip()==sha
meta=json.load(open(base+'/metadata.json'));assert meta['status']=='BUILT' and meta['git_commit']==sha
assert not subprocess.check_output(['git','-C',source,'status','--porcelain']).strip()
folder=base+'/technical/ofan';assert not os.path.lexists(folder);os.makedirs(folder)
exe=folder+'/ws31-ofan-test';receipt=base+'/technical/preflight-test-receipt.json'
r={'source_sha':sha,'metadata_before_tests':meta,'commands':[],'status':'RUNNING','network_simulations_started':0}
def save():
 with open(receipt,'w') as f:json.dump(r,f,indent=2)
def run(name,args,limit):
 path=base+'/logs/'+name+'.log';assert not os.path.lexists(path)
 d={'name':name,'argv':args,'cwd':source,'start_utc':datetime.datetime.utcnow().isoformat()+'Z','log':path};r['commands'].append(d);save()
 try:
  with open(path,'wb') as log:d['exit_code']=subprocess.call(args,cwd=source,stdout=log,stderr=subprocess.STDOUT,timeout=limit)
 except subprocess.TimeoutExpired:d['timeout']=True;d['exit_code']=-1
 d['end_utc']=datetime.datetime.utcnow().isoformat()+'Z';save()
 if d['exit_code']:
  r['status']='FAILED';save();print(json.dumps(r));sys.exit(1)
run('ofan-core-compile',['g++','-std=c++11','-O2','-Wall','-Wextra','-pedantic','tests/ws31_ofan_test.cc','-o',exe],180)
run('ofan-core-run',[exe],60)
core=open(base+'/logs/ofan-core-run.log').read();r['ofan_pass']='WS31_OFAN_TEST PASS mandatory-groups/cycle-rejection/rotation/independence/seed/static-gate' in core
if not r['ofan_pass']:r['status']='FAILED_MARKER';save();print(json.dumps(r));sys.exit(1)
run('c2-lifecycle',['./waf','-j2','--run','ws31-start-lifecycle-test'],180)
life=open(base+'/logs/c2-lifecycle.log').read();r['lifecycle_stop_pass']='WS31_C2_LIFECYCLE PASS kind=stop' in life;r['lifecycle_dispose_pass']='WS31_C2_LIFECYCLE PASS kind=dispose' in life
r['status']='PASS' if r['lifecycle_stop_pass'] and r['lifecycle_dispose_pass'] else 'FAILED_MARKER'
r['logs']={}
for name in ['build','ofan-core-compile','ofan-core-run','c2-lifecycle']:
 path=base+'/logs/'+name+'.log';b=open(path,'rb').read();r['logs'][name]={'path':path,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
paths=subprocess.check_output(['git','-C',source,'diff','--name-only','21faeb2d986b0a4d9d59edd9bf11a0d0de934007',sha]).decode().splitlines()
r['source_hashes']={q:hashlib.sha256(open(source+'/'+q,'rb').read()).hexdigest() for q in paths}
r['artifacts']=[]
for path in [exe,source+'/build/scratch/network-load-balance',source+'/build/scratch/ws31-start-lifecycle-test',source+'/build/libns3.19-point-to-point-optimized.so',source+'/build/libns3.19-applications-optimized.so']:
 b=open(path,'rb').read();r['artifacts'].append({'path':path,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
r['source_status_after']=subprocess.check_output(['git','-C',source,'status','--porcelain']).decode();r['raw_directory_entries']=os.listdir(base+'/raw');r['gpp_version']=subprocess.check_output(['g++','--version']).decode().splitlines()[0]
mem=open('/proc/meminfo').read();v=os.statvfs('/home/fnl/lzy');r['after_resources']={'loadavg':os.getloadavg(),'available_gib':int(re.search(r'^MemAvailable:\s+(\d+)',mem,re.M).group(1))/1024**2,'free_gib':v.f_bavail*v.f_frsize/1024**3};save();print(json.dumps(r))
if r['status']!='PASS':sys.exit(1)
""".replace('SOURCE',repr(r['remote_source'])).replace('BASE',repr(r['remote_result'])).replace('SHA',repr(r['source_sha']))
v=subprocess.run(m.ssh_base(cfg)+['python3 -c '+shlex.quote(remote)],capture_output=True,text=True,timeout=500)
(out/(prefix+'-test-ssh.log')).write_text(v.stdout+v.stderr,encoding='utf-8')
if not v.stdout.strip():raise RuntimeError('No test receipt returned: '+v.stderr[-1500:])
post=json.loads(v.stdout);(out/(prefix+'-tests.json')).write_text(json.dumps(post,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for path,h in post.get('source_hashes',{}).items():
 data=subprocess.check_output(['git','-C',str(repo),'show',r['source_sha']+':'+path]);assert hashlib.sha256(data).hexdigest()==h,path
pairs=[('metadata.json',prefix+'-remote-metadata.json'),('technical/preflight-test-receipt.json',prefix+'-remote-tests.json')]
for name in ['build','ofan-core-compile','ofan-core-run','c2-lifecycle']:
 if name=='build' or any(c['name']==name for c in post['commands']):pairs.append(('logs/'+name+'.log',prefix+'-'+name+'-remote.log'))
for rel,dest in pairs:
 target=out/dest;assert not target.exists(),str(target)
 subprocess.run(['scp','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=10',cfg['REMOTE_USER']+'@'+cfg['REMOTE_HOST']+':'+r['remote_result']+'/'+rel,str(target)],check=True,timeout=120)
for name,item in post.get('logs',{}).items():assert hashlib.sha256((out/(prefix+'-'+name+'-remote.log')).read_bytes()).hexdigest()==item['sha256']
r['acceptance']['ofan_core_compile']='PASS' if post['commands'][0]['exit_code']==0 else 'FAIL';r['acceptance']['ofan_core_run']='PASS' if post.get('ofan_pass') else 'FAIL';r['acceptance']['lifecycle_stop']='PASS' if post.get('lifecycle_stop_pass') else 'FAIL';r['acceptance']['lifecycle_dispose']='PASS' if post.get('lifecycle_dispose_pass') else 'FAIL'
success=post['status']=='PASS' and post['raw_directory_entries']==[] and post['source_status_after']==''
r['acceptance']['source_artifact_and_log_verification']='PASS' if success else 'FAIL';r['status']='COMPLETE_FOR_TECHNICAL_PREFLIGHT_ONLY' if success else 'TECHNICAL_PREFLIGHT_FAILED';r['source_files_verified']=len(post.get('source_hashes',{}));r['tests_receipt_file']=prefix+'-tests.json';p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':r['status'],'source_files_verified':r['source_files_verified'],'tests':[(c['name'],c['exit_code']) for c in post['commands']],'markers':{k:v for k,v in post.items() if k.endswith('_pass')},'artifacts':post.get('artifacts',[])},indent=2))
if not success or v.returncode:raise SystemExit(1)
