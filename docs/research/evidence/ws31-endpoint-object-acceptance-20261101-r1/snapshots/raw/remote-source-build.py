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

assert all(result['id_absent'].values())
run=root+'/runs/'+ident; results=root+'/results/'+ident; source=run+'/source'
for p in (root+'/runs',root+'/results',cache): assert os.path.isdir(p) and os.path.realpath(p)==p and not os.path.islink(p)
os.mkdir(run); os.mkdir(results)
for sub in ('artifacts','logs','provenance','tmp'): os.mkdir(results+'/'+sub)
def save(name,data):
 with open(results+'/'+name,'x') as f: json.dump(data,f,sort_keys=True,indent=2); f.write('\n')
def now():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def resources():
 mem={line.split(':',1)[0]:int(line.split(':',1)[1].strip().split()[0]) for line in open('/proc/meminfo')}
 return {'at_utc':now(),'load':list(os.getloadavg()),'mem_available_gib':mem['MemAvailable']/float(1024**2),'disk_available_gib':shutil.disk_usage(root).free/float(1024**3)}
env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/home/fnl','USER':'fnl','LOGNAME':'fnl','LANG':'C','LC_ALL':'C','TZ':'UTC','TMPDIR':results+'/tmp','PWD':source,'WS30_OBSERVE':'0','WS31_LABEL_PROFILE':'0','WS30_TAG_TRANSFORM':'0','WS30_LIFECYCLE':'0','WS30_LIFE_PROFILE':'0','WS30_COMPOSITION':'0'}
meta={'experiment_id':ident,'status':'SOURCE_ESTABLISHING','git_repository':'https://github.com/LarryBUPT/conweave-ns3.git','git_commit':sha,'parent_sha':'20bc2d9f7c7c435bf832ba2fcaf0e07df00cf5da','git_branch':'feature/ws31-candidates','source':source,'results':results,'build_mode':'optimized','jobs':2,'full_builds':0,'fixture_runs':0,'standalone_core_compiles':0,'network_runs':0,'started_utc':now(),'source_build_driver_pid':os.getpid()}
def metadata():
 with open(results+'/metadata.json','w') as f: json.dump(meta,f,sort_keys=True,indent=2); f.write('\n')
metadata(); save('provenance/before-source-gate.json',result); save('provenance/build-environment.json',env)
commands=[]
def invoke(argv,label,cwd):
 item={'argv':argv,'cwd':cwd,'environment':env,'start_utc':now(),'resources_before':resources(),'stdout':'logs/'+label+'.stdout','stderr':'logs/'+label+'.stderr'}
 save('provenance/'+label+'-started.json',item); started=time.monotonic()
 with open(results+'/'+item['stdout'],'xb') as out,open(results+'/'+item['stderr'],'xb') as err,open(results+'/provenance/'+label+'-resources.jsonl','x') as samples:
  child=subprocess.Popen(argv,cwd=cwd,env=env,stdout=out,stderr=err); item['pid']=child.pid
  while True:
   pid,status,usage=os.wait4(child.pid,os.WNOHANG)
   sample=resources(); sample['child_pid']=child.pid; samples.write(json.dumps(sample,sort_keys=True)+'\n'); samples.flush()
   if pid:break
   time.sleep(2)
  rc=os.WEXITSTATUS(status) if os.WIFEXITED(status) else -os.WTERMSIG(status); child.returncode=rc
 item.update({'end_utc':now(),'elapsed_seconds':time.monotonic()-started,'exit':rc,'wait_status':status,'resources_after':resources(),'rusage':{'user_seconds':usage.ru_utime,'system_seconds':usage.ru_stime,'max_rss_kib':usage.ru_maxrss,'major_faults':usage.ru_majflt,'minor_faults':usage.ru_minflt}})
 for key in ('stdout','stderr'):item[key+'_sha256']=hashlib.sha256(open(results+'/'+item[key],'rb').read()).hexdigest()
 commands.append(item); save('provenance/'+label+'-result.json',item)
 if rc: raise RuntimeError('Command failed once, no retry: '+label)
 return item
try:
 invoke(['git','clone','--local','--no-hardlinks','--no-checkout',cache,source],'clone',root)
 invoke(['git','checkout','--detach',sha],'checkout',source)
 invoke(['git','remote','set-url','origin',meta['git_repository']],'source-origin',source)
 for name,url in [('upstream','https://github.com/conweave-project/conweave-ns3.git'),('reference-maplerime','https://github.com/maplerime/conweave-ns3.git')]:
  invoke(['git','remote','add',name,url],'source-'+name,source)
  invoke(['git','remote','set-url','--push',name,'no-push://read-only-reference'],'protect-'+name,source)
 assert subprocess.check_output(['git','-C',source,'rev-parse','HEAD']).decode().strip()==sha
 tree=subprocess.check_output(['git','-C',source,'ls-tree','-r',sha]); assert len(tree.splitlines())==4847 and hashlib.sha256(tree).hexdigest()=='8096510b5b068ef31269f88d836112a6e53b2b351984694bc796a0a4a4c05855'
 with open(results+'/provenance/source-tree.txt','xb') as f:f.write(tree)
 files=[]
 for line in tree.decode().splitlines():
  attrs,rel=line.split('\t',1); mode,kind,blob=attrs.split(); target=source+'/'+rel
  assert mode in ('100644','100755') and kind=='blob' and os.path.realpath(target)==target and not os.path.islink(target)
  b=open(target,'rb').read(); assert hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()==blob,rel
  files.append({'path':rel,'mode':mode,'git_blob':blob,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 save('provenance/source-files.json',files)
 assert not subprocess.check_output(['git','-C',source,'status','--porcelain'])
 meta.update({'status':'SOURCE_ESTABLISHED_NOT_BUILT','source_tree_entries':len(files),'source_tree_sha256':hashlib.sha256(tree).hexdigest(),'source_bytes':sum(x['bytes'] for x in files),'source_files_manifest_sha256':hashlib.sha256(open(results+'/provenance/source-files.json','rb').read()).hexdigest(),'source_established_utc':now()}); metadata()
 print(json.dumps({'phase':'SOURCE_ESTABLISHED','id':ident,'files':len(files),'source_bytes':meta['source_bytes']})); sys.stdout.flush()
 invoke(['./waf','configure','--build-profile=optimized'],'configure',source)
 meta.update({'status':'BUILDING','full_builds':1,'build_started_utc':now()}); metadata()
 print(json.dumps({'phase':'FULL_OPTIMIZED_J2_BUILD_STARTED','id':ident})); sys.stdout.flush()
 built=invoke(['./waf','-j2','-v'],'build',source)
 binary=source+'/build/scratch/ws31-endpoint-object-test'; assert os.path.isfile(binary) and os.access(binary,os.X_OK)
 assert not subprocess.check_output(['git','-C',source,'status','--porcelain'])
 for entry in files: assert hashlib.sha256(open(source+'/'+entry['path'],'rb').read()).hexdigest()==entry['sha256'],entry['path']
 meta.update({'status':'BUILT_NOT_RUN','build_exit':0,'build_finished_utc':now(),'binary':{'path':binary,'sha256':hashlib.sha256(open(binary,'rb').read()).hexdigest(),'bytes':os.stat(binary).st_size},'source_clean_after_build':True,'all_source_hashes_unchanged_after_build':True})
 save('provenance/build-command-list.json',commands)
 for rel in ('build/c4che/_cache.py','build/config.log'):
  if os.path.isfile(source+'/'+rel):shutil.copy2(source+'/'+rel,results+'/provenance/'+rel.replace('/','-'))
 metadata(); print(json.dumps(meta,sort_keys=True)); sys.stdout.flush()
except Exception as error:
 meta.update({'status':'BUILD_FAILED_STOP_NO_FIXTURE','error':str(error),'finished_utc':now()}); metadata(); raise
