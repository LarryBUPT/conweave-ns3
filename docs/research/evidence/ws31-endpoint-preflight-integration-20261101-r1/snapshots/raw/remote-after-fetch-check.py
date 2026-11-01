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
result['decision']='PASS_AFTER_FETCH_TERMINAL_GATE'



results=root+'/results/'+ident; source=root+'/runs/'+ident+'/source'; meta=json.load(open(results+'/metadata.json'))
for p in (meta['pid'],meta['current_pid'],307587,307592): assert not os.path.exists('/proc/'+str(p))
assert not subprocess.check_output(['git','-C',source,'status','--porcelain'])
assert result['cache']['head']['stdout'].strip()=='236a801a00e35de9078635e04acae2f701c21ded'
result['all_source_compile_run_calls_terminal']=True
result['exact_core_invocations']=meta['core_invocations']; result['exact_compile_invocations']=meta['compiler_invocations']
result['previous_call_pids_absent']=[meta['pid'],meta['current_pid'],307587,307592]
print(json.dumps(result,sort_keys=True))
