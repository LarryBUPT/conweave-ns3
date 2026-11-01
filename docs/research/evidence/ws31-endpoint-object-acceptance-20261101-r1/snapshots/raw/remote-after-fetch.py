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
results=root+'/results/'+ident; source=root+'/runs/'+ident+'/source'; meta=json.load(open(results+'/metadata.json'))
assert meta['status']=='OBJECT_FIXTURE_PASSED_RAW_PENDING_CHECK' and meta['full_builds']==meta['fixture_runs']==1
pids=[meta['source_build_driver_pid'],meta['fixture_driver_pid'],meta['fixture_child_pid'],json.load(open(results+'/provenance/configure-result.json'))['pid'],json.load(open(results+'/provenance/build-result.json'))['pid']]
for pid in pids:assert not os.path.exists('/proc/'+str(pid))
assert not subprocess.check_output(['git','-C',source,'status','--porcelain'])
assert hashlib.sha256(open(results+'/receipt-manifest.json','rb').read()).hexdigest()=='eaf043c82eae689e869e5b5377c32efe2b09e349fbbd833c04d6d5229976b978'
result['all_guarded_calls_terminal']=True;result['previous_task_pids_absent']=pids
result['full_builds']=1;result['fixture_runs']=1;result['network_runs']=0
print(json.dumps(result,sort_keys=True))
