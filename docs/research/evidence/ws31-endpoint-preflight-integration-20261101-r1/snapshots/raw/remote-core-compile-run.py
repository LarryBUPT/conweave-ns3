import os,sys,json,subprocess,shutil,time,pwd,hashlib
root='/home/fnl/lzy'; cache=root+'/code/conweave-ns3'; sha='20bc2d9f7c7c435bf832ba2fcaf0e07df00cf5da'; ident='20261101-163000-ws31-endpoint-core-r2'
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

assert result['mem_available_gib']>=64 and result['disk_available_gib']>=100 and result['load'][0]<=4
assert not any(result['id_absent'].values()) and not result['old_driver_22440_present']
assert not any(result['maintenance_markers'].values())
assert result['cache']['origin']['stdout'].strip()=='https://github.com/LarryBUPT/conweave-ns3.git'
assert result['cache']['status']['stdout']=='' and result['cache']['tree_entries']==4845 and result['cache']['tree_sha256']=='3da8acbcc1809389aac24adc1936d22874821077e40ddd397723fa7d977e0e64'
assert result['cache']['refs']['stdout'].strip().endswith(sha)
byid={x['pid']:x for x in result['processes']}; ancestry=set(); p=os.getpid()
while p in byid and p not in ancestry: ancestry.add(p); p=byid[p]['ppid']
known={215645,302325,348833,377959,397391,415208,420873,420878,457365}
for x in result['processes']:
 if x['uid']>=1000 and x['pid'] not in ancestry:
  assert x['pid'] in known and x['uid']==1000 and x['state']=='S' and x['ppid'] in (1,420873), x
 if x['argv'] and x['pid'] not in ancestry:
  exe=(x.get('exe') or '').split('/')[-1]; a=' '.join(x['argv'])
  assert '/home/fnl/lzy' not in (x.get('cwd') or '') and '/home/fnl/lzy' not in a, x
  assert not exe.startswith(('git','g++','gcc','cc1plus','make','ns3','waf','scp','rsync')), x
result['decision']='PASS_FRESH_PRECOMPILE_GATE'


import resource,re,platform
run=root+'/runs/'+ident; results=root+'/results/'+ident; source=run+'/source'; binary=results+'/artifacts/ws31_endpoint_ledger_test'
for p in (run,results,source): assert os.path.isdir(p) and os.path.realpath(p)==p and not os.path.islink(p)
meta=json.load(open(results+'/metadata.json'))
assert meta['status']=='SOURCE_ESTABLISHED_NOT_COMPILED' and meta['compiler_invocations']==0 and meta['core_invocations']==0
assert not os.path.lexists(binary)
assert subprocess.check_output(['git','-C',source,'rev-parse','HEAD']).decode().strip()==sha
assert not subprocess.check_output(['git','-C',source,'status','--porcelain'])
for f,h in {'src/point-to-point/model/ws31-endpoint-ledger.h':'105b7ced338b85e12ddb87f0235ab9bfff1ac0444a34584a9127cb6cbe944524','tests/ws31_endpoint_ledger_test.cc':'da24c329cff2c8e118fe19653e9b76a1926fd9a295b55009a11b4b7a0765ba49'}.items(): assert hashlib.sha256(open(source+'/'+f,'rb').read()).hexdigest()==h
assert hashlib.sha256(open(results+'/provenance/source-files.json','rb').read()).hexdigest()==meta['source_files_manifest_sha256']
def save(name,data):
 with open(results+'/'+name,'x') as f: json.dump(data,f,sort_keys=True,indent=2); f.write('\n')
def metadata():
 with open(results+'/metadata.json','w') as f: json.dump(meta,f,sort_keys=True,indent=2); f.write('\n')
def now(): return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def resources():
 m={line.split(':',1)[0]:int(line.split(':',1)[1].strip().split()[0]) for line in open('/proc/meminfo')}
 return {'at_utc':now(),'load':list(os.getloadavg()),'mem_available_gib':m['MemAvailable']/float(1024**2),'disk_available_gib':shutil.disk_usage(root).free/float(1024**3)}
env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/home/fnl','USER':'fnl','LOGNAME':'fnl','LANG':'C','LC_ALL':'C','TZ':'UTC','TMPDIR':results+'/tmp','PWD':source}
save('provenance/before-compile-gate.json',result)
save('provenance/exact-compile-run-environment.json',env)
queries=[]
def query(argv,label):
 p=subprocess.Popen(argv,cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE); out,err=p.communicate()
 with open(results+'/logs/'+label+'.stdout','xb') as f: f.write(out)
 with open(results+'/logs/'+label+'.stderr','xb') as f: f.write(err)
 queries.append({'argv':argv,'cwd':source,'environment':'provenance/exact-compile-run-environment.json','exit':p.returncode,'stdout':'logs/'+label+'.stdout','stderr':'logs/'+label+'.stderr'})
 if p.returncode: raise RuntimeError('Provenance query failed: '+label)
 return out.decode('utf-8','replace')
def fingerprint(path):
 resolved=os.path.realpath(path)
 return {'invocation_path':path,'resolved_path':resolved,'sha256':hashlib.sha256(open(resolved,'rb').read()).hexdigest(),'bytes':os.stat(resolved).st_size}
def invoke(argv,label):
 record={'argv':argv,'cwd':source,'environment':env,'start_utc':now(),'resources_before':resources(),'stdout':'logs/'+label+'.stdout','stderr':'logs/'+label+'.stderr'}
 save('provenance/'+label+'-started.json',record)
 with open(results+'/'+record['stdout'],'xb') as out,open(results+'/'+record['stderr'],'xb') as err:
  child=subprocess.Popen(argv,cwd=source,env=env,stdout=out,stderr=err)
  record['pid']=child.pid
  waited,status,usage=os.wait4(child.pid,0)
  assert waited==child.pid
  rc=os.WEXITSTATUS(status) if os.WIFEXITED(status) else -os.WTERMSIG(status)
  child.returncode=rc
 record.update({'end_utc':now(),'exit':rc,'wait_status':status,'rusage':{'user_seconds':usage.ru_utime,'system_seconds':usage.ru_stime,'max_rss_kib':usage.ru_maxrss,'minor_faults':usage.ru_minflt,'major_faults':usage.ru_majflt,'voluntary_context_switches':usage.ru_nvcsw,'involuntary_context_switches':usage.ru_nivcsw},'resources_after':resources()})
 for field in ('stdout','stderr'): record[field+'_sha256']=hashlib.sha256(open(results+'/'+record[field],'rb').read()).hexdigest()
 save('provenance/'+label+'-result.json',record)
 return record
try:
 compiler=shutil.which('g++',path=env['PATH']); assert compiler
 version=query(['g++','--version'],'compiler-version')
 machine=query(['g++','-dumpmachine'],'compiler-target').strip()
 cc1=query(['g++','-print-prog-name=cc1plus'],'compiler-cc1plus').strip()
 compiler_stdlib=query(['g++','-print-file-name=libstdc++.so.6'],'compiler-stdlib').strip()
 linker=shutil.which('ld',path=env['PATH']); assembler=shutil.which('as',path=env['PATH']); assert linker and assembler
 query(['ld','--version'],'linker-version'); query(['as','--version'],'assembler-version')
 save('provenance/toolchain.json',{'compiler':fingerprint(compiler),'cc1plus':fingerprint(cc1),'linker':fingerprint(linker),'assembler':fingerprint(assembler),'libstdcpp':fingerprint(compiler_stdlib),'compiler_version_stdout':version,'compiler_target':machine,'python':sys.version,'platform':platform.platform(),'uname':list(os.uname())})
 compile_argv=['g++','-std=c++11','-O2','-Wall','-Wextra','-pedantic','-DNDEBUG','tests/ws31_endpoint_ledger_test.cc','-o',binary]
 meta.update({'status':'COMPILING','compiler_invocations':1,'compile_started_utc':now()}); metadata()
 compiled=invoke(compile_argv,'compile')
 if compiled['exit']!=0: raise RuntimeError('Single compilation failed; run forbidden')
 save('provenance/binary-before-run.json',fingerprint(binary))
 meta.update({'status':'COMPILED_NOT_RUN','compile_exit':compiled['exit']}); metadata()
 meta.update({'status':'RUNNING','core_invocations':1,'run_started_utc':now()}); metadata()
 ran=invoke([binary],'run')
 expected=b'WS31_ENDPOINT_LEDGER PASS requests=2 completed_generations=2 closed_tokens=6 real_endpoint_snapshots=0 network_runs=0\n'
 stdout=open(results+'/logs/run.stdout','rb').read(); stderr=open(results+'/logs/run.stderr','rb').read()
 if ran['exit']!=0 or stdout!=expected or stderr!=b'': raise RuntimeError('Single runtime result differs from frozen expectation; no rerun')
 before=json.load(open(results+'/provenance/binary-before-run.json')); after=fingerprint(binary); assert before==after
 ldd=query(['ldd',binary],'binary-ldd')
 libs=[]
 for line in ldd.splitlines():
  for token in line.split():
   if token.startswith('/') and os.path.isfile(token):
    fp=fingerprint(token)
    if fp not in libs: libs.append(fp)
 assert libs
 save('provenance/runtime-libraries.json',libs); save('provenance/toolchain-query-commands.json',queries)
 assert not subprocess.check_output(['git','-C',source,'status','--porcelain'])
 source_files=json.load(open(results+'/provenance/source-files.json'))
 for entry in source_files:
  assert hashlib.sha256(open(source+'/'+entry['path'],'rb').read()).hexdigest()==entry['sha256'], entry['path']
 meta.update({'status':'CORE_PASSED_RAW_NOT_YET_FETCHED','compile_exit':compiled['exit'],'run_exit':ran['exit'],'exact_stdout':stdout.decode(),'exact_stderr':'','binary':after,'runtime_libraries':len(libs),'source_clean_after':True,'all_source_file_hashes_unchanged_after':True,'real_endpoint_snapshots':0,'network_runs':0,'full_ns3_builds':0,'finished_utc':now(),'current_pid':os.getpid()})
 metadata(); print(json.dumps(meta,sort_keys=True))
except Exception as error:
 meta.update({'status':'FAILED_STOP_NO_RETRY','error':str(error),'finished_utc':now()}); metadata(); raise
