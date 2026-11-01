import os,sys,json,subprocess,shutil,time,pwd,hashlib
root='/home/fnl/lzy'; cache=root+'/code/conweave-ns3'; sha='8cd1ba69469bf80143d5c89edc17fa72611018e8'; ident='20261101-173000-ws31-endpoint-object-r1'
assert os.path.realpath(root)==root and os.path.isdir(root)
def cmd(argv):
 p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE); out,err=p.communicate(); return {'argv':argv,'exit':p.returncode,'stdout':out.decode('utf-8','replace'),'stderr':err.decode('utf-8','replace')}
processes=[]
for name in os.listdir('/proc'):
 if not name.isdigit(): continue
 try:
  base='/proc/'+name; stat=open(base+'/stat').read(); tail=stat[stat.rfind(')')+2:].split(); uid=os.stat(base).st_uid
  args=open(base+'/cmdline','rb').read().split(b'\0'); argv=[a.decode('utf-8','replace') for a in args if a]
  item={'pid':int(name),'ppid':int(tail[1]),'uid':uid,'user':pwd.getpwuid(uid).pw_name,'state':tail[0],'start_ticks':int(tail[19]),'argv':argv}
  for key,suffix in [('cwd','/cwd'),('exe','/exe')]:
   try: item[key]=os.readlink(base+suffix)
   except OSError: item[key]=None
  processes.append(item)
 except (IOError,OSError,KeyError,IndexError): pass
mem={}
for line in open('/proc/meminfo'):
 k,v=line.split(':',1); mem[k]=int(v.strip().split()[0])
disk=shutil.disk_usage(root)
cacheinfo={'exists':os.path.exists(cache),'realpath':os.path.realpath(cache),'symlink':os.path.islink(cache)}
if os.path.isdir(cache):
 cacheinfo['git_dir_exists']=os.path.isdir(cache+'/.git')
 cacheinfo['origin']=cmd(['git','-C',cache,'remote','get-url','origin'])
 cacheinfo['head']=cmd(['git','-C',cache,'rev-parse','HEAD'])
 cacheinfo['status']=cmd(['git','-C',cache,'status','--porcelain'])
 cacheinfo['refs']=cmd(['git','-C',cache,'for-each-ref','--format=%(refname) %(objectname)','refs/remotes/origin/feature/ws31-candidates'])
 cacheinfo['object']=cmd(['git','-C',cache,'cat-file','-t',sha])
 if cacheinfo['object']['exit']==0:
  tree=subprocess.check_output(['git','-C',cache,'ls-tree','-r',sha]); cacheinfo['tree_entries']=len(tree.splitlines()); cacheinfo['tree_sha256']=hashlib.sha256(tree).hexdigest()
result={'at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'pid':os.getpid(),'ppid':os.getppid(),'root':root,'uid':os.getuid(),'uname':list(os.uname()),'cpu_count':os.cpu_count(),'load':list(os.getloadavg()),'mem_available_gib':mem['MemAvailable']/float(1024**2),'disk_available_gib':disk.free/float(1024**3),'id_absent':{kind:not os.path.lexists(root+'/'+kind+'/'+ident) for kind in ('runs','results')},'old_driver_22440_present':os.path.exists('/proc/22440'),'processes':processes,'ps':cmd(['ps','-eo','user,pid,ppid,pgid,lstart,stat,etime,pcpu,pmem,args','--no-headers']),'who':cmd(['who']),'maintenance_markers':{p:os.path.exists(p) for p in ('/run/nologin','/var/run/reboot-required')},'cache':cacheinfo}

worker='/home/fnl/lzy/.research-workflow/remote_worker.py'
b=open(worker,'rb').read()
result['worker']={'path':worker,'symlink':os.path.islink(worker),'realpath':os.path.realpath(worker),'sha256':hashlib.sha256(b).hexdigest(),'LF_sha256':hashlib.sha256(b.replace(b'\r\n',b'\n')).hexdigest()}

assert result['mem_available_gib']>=64 and result['disk_available_gib']>=100 and result['load'][0]<=4
assert not result['old_driver_22440_present'] and not any(result['maintenance_markers'].values())
assert result['cache']['origin']['stdout'].strip()=='https://github.com/LarryBUPT/conweave-ns3.git' and result['cache']['status']['stdout']=='' and not result['cache']['symlink']
assert result['cache']['tree_entries']==4847 and result['cache']['tree_sha256']=='8096510b5b068ef31269f88d836112a6e53b2b351984694bc796a0a4a4c05855'
assert result['cache']['refs']['stdout'].strip().endswith(sha) and result['cache']['head']['stdout'].strip()=='236a801a00e35de9078635e04acae2f701c21ded'
assert result['worker']['LF_sha256']=='096695c22597b30ecd24ad3ed69284f851b26743f9be4c810bafee82d90ff569' and not result['worker']['symlink']
byid={x['pid']:x for x in result['processes']}; own=set(); q=os.getpid()
while q in byid and q not in own: own.add(q); q=byid[q]['ppid']
known={215645,302325,348833,377959,397391,415208,420873,420878,457365}
for x in result['processes']:
 if x['uid']>=1000 and x['pid'] not in own: assert x['pid'] in known and x['uid']==1000 and x['state']=='S' and x['ppid'] in (1,420873), x
 if x['argv'] and x['pid'] not in own:
  a=' '.join(x['argv']); exe=(x.get('exe') or '').split('/')[-1]
  assert '/home/fnl/lzy' not in a and '/home/fnl/lzy' not in (x.get('cwd') or ''),x
  assert not exe.startswith(('git','g++','gcc','cc1plus','make','ns3','waf','scp','rsync')),x
result['decision']='PASS_FRESH_GATE'

assert not any(result['id_absent'].values())
run=root+'/runs/'+ident; results=root+'/results/'+ident; source=run+'/source'; binary=source+'/build/scratch/ws31-endpoint-object-test'
meta=json.load(open(results+'/metadata.json')); assert meta['status']=='BUILT_NOT_RUN' and meta['full_builds']==1 and meta['fixture_runs']==0
assert not os.path.exists('/proc/'+str(meta['source_build_driver_pid']))
assert subprocess.check_output(['git','-C',source,'rev-parse','HEAD']).decode().strip()==sha and not subprocess.check_output(['git','-C',source,'status','--porcelain'])
assert hashlib.sha256(open(binary,'rb').read()).hexdigest()==meta['binary']['sha256']
def save(name,data):
 with open(results+'/'+name,'x') as f: json.dump(data,f,sort_keys=True,indent=2); f.write('\n')
def now():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def metadata():
 with open(results+'/metadata.json','w') as f: json.dump(meta,f,sort_keys=True,indent=2); f.write('\n')
def resources():
 mem={line.split(':',1)[0]:int(line.split(':',1)[1].strip().split()[0]) for line in open('/proc/meminfo')}
 return {'at_utc':now(),'load':list(os.getloadavg()),'mem_available_gib':mem['MemAvailable']/float(1024**2),'disk_available_gib':shutil.disk_usage(root).free/float(1024**3)}
def fp(path):
 real=os.path.realpath(path); return {'path':path,'realpath':real,'bytes':os.stat(real).st_size,'sha256':hashlib.sha256(open(real,'rb').read()).hexdigest()}
lddirs=set()
for directory,dirs,files in os.walk(source+'/build'):
 for name in files:
  if name.startswith('libns3') and '.so' in name:lddirs.add(directory)
assert lddirs and all(os.path.realpath(x).startswith(source+'/build') for x in lddirs)
env=json.load(open(results+'/provenance/build-environment.json')); env['LD_LIBRARY_PATH']=':'.join(sorted(lddirs))
assert 'LD_PRELOAD' not in env
save('provenance/before-fixture-gate.json',result); save('provenance/fixture-environment.json',env)
queries=[]
def query(argv,label):
 p=subprocess.Popen(argv,cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE); out,err=p.communicate()
 for suffix,b in (('stdout',out),('stderr',err)):
  with open(results+'/logs/'+label+'.'+suffix,'xb') as f:f.write(b)
 queries.append({'argv':argv,'cwd':source,'environment':env,'exit':p.returncode,'stdout':'logs/'+label+'.stdout','stderr':'logs/'+label+'.stderr'})
 if p.returncode:raise RuntimeError('Query failed before fixture: '+label)
 return out.decode('utf-8','replace')
try:
 compiler=shutil.which('g++',path=env['PATH']); assert compiler
 version=query(['g++','--version'],'compiler-version'); target=query(['g++','-dumpmachine'],'compiler-target').strip()
 cc1=query(['g++','-print-prog-name=cc1plus'],'compiler-cc1plus').strip()
 save('provenance/toolchain.json',{'compiler':fp(compiler),'cc1plus':fp(cc1),'linker':fp(shutil.which('ld',path=env['PATH'])),'compiler_version':version,'compiler_target':target,'python3':sys.version,'uname':list(os.uname())})
 ldd=query(['ldd',binary],'fixture-ldd'); assert 'not found' not in ldd
 libraries=[]; seen=set(); os.mkdir(results+'/artifacts/libraries')
 for line in ldd.splitlines():
  for token in line.split():
   if token.startswith('/') and os.path.isfile(token):
    f=fp(token)
    if f['realpath'] in seen:continue
    seen.add(f['realpath']); f['project_library']=os.path.basename(token).startswith('libns3')
    if f['project_library']:
     assert f['realpath'].startswith(source+'/build/')
     dest=results+'/artifacts/libraries/'+os.path.basename(f['realpath']); assert not os.path.lexists(dest)
     shutil.copy2(f['realpath'],dest); f['local_artifact']='artifacts/libraries/'+os.path.basename(f['realpath'])
    libraries.append(f)
 assert any(f['project_library'] for f in libraries)
 save('provenance/runtime-libraries.json',libraries); save('provenance/toolchain-query-commands.json',queries)
 shutil.copy2(binary,results+'/artifacts/ws31-endpoint-object-test'); save('provenance/binary-before-fixture.json',fp(binary))
 meta.update({'status':'OBJECT_FIXTURE_RUNNING','fixture_runs':1,'fixture_driver_pid':os.getpid(),'fixture_started_utc':now()}); metadata()
 record={'argv':[binary],'cwd':source,'environment':env,'start_utc':now(),'resources_before':resources(),'stdout':'logs/fixture.stdout','stderr':'logs/fixture.stderr'}
 save('provenance/fixture-started.json',record); began=time.monotonic()
 with open(results+'/logs/fixture.stdout','xb') as out,open(results+'/logs/fixture.stderr','xb') as err:
  child=subprocess.Popen([binary],cwd=source,env=env,stdout=out,stderr=err); record['pid']=child.pid
  waited,status,usage=os.wait4(child.pid,0); assert waited==child.pid
  rc=os.WEXITSTATUS(status) if os.WIFEXITED(status) else -os.WTERMSIG(status); child.returncode=rc
 record.update({'exit':rc,'wait_status':status,'end_utc':now(),'elapsed_seconds':time.monotonic()-began,'resources_after':resources(),'rusage':{'user_seconds':usage.ru_utime,'system_seconds':usage.ru_stime,'max_rss_kib':usage.ru_maxrss,'minor_faults':usage.ru_minflt,'major_faults':usage.ru_majflt}})
 for key in ('stdout','stderr'):record[key+'_sha256']=hashlib.sha256(open(results+'/'+record[key],'rb').read()).hexdigest()
 save('provenance/fixture-result.json',record)
 stdout=open(results+'/logs/fixture.stdout','rb').read(); stderr=open(results+'/logs/fixture.stderr','rb').read()
 expected=b'WS31_ENDPOINT_OBJECT_SUMMARY PASS reads=31 refusals=16 network_runs=0 event_calls=0 actual_network_completions=0'
 assert rc==0 and stderr==b'' and stdout.splitlines()[-1]==expected
 assert fp(binary)==json.load(open(results+'/provenance/binary-before-fixture.json'))
 for f in libraries:assert fp(f['path'])['sha256']==f['sha256']
 for entry in json.load(open(results+'/provenance/source-files.json')):assert hashlib.sha256(open(source+'/'+entry['path'],'rb').read()).hexdigest()==entry['sha256']
 assert not subprocess.check_output(['git','-C',source,'status','--porcelain'])
 meta.update({'status':'OBJECT_FIXTURE_PASSED_RAW_PENDING_CHECK','fixture_exit':rc,'fixture_child_pid':record['pid'],'fixture_finished_utc':now(),'runtime_libraries':len(libraries),'copied_project_libraries':sum(int(f['project_library']) for f in libraries),'source_and_binary_libraries_unchanged':True,'actual_network_completions':0,'noops_executed':0});metadata()
 print(json.dumps(meta,sort_keys=True))
except Exception as error:
 meta.update({'status':'OBJECT_PREFLIGHT_FAILED_STOP_NO_RETRY','error':str(error),'finished_utc':now()});metadata();raise
