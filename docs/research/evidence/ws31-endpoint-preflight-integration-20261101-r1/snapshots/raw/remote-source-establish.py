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
assert all(result['id_absent'].values()) and not result['old_driver_22440_present']
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
result['decision']='PASS_FRESH_POST_SYNC_GATE'

run=root+'/runs/'+ident; results=root+'/results/'+ident; source=run+'/source'
for parent in (root+'/runs',root+'/results',cache): assert os.path.isdir(parent) and os.path.realpath(parent)==parent and not os.path.islink(parent)
os.mkdir(run); os.mkdir(results)
for sub in ('artifacts','logs','provenance','tmp'): os.mkdir(results+'/'+sub)
def save(name,data):
 with open(results+'/'+name,'x') as f: json.dump(data,f,sort_keys=True,indent=2); f.write('\n')
save('provenance/before-source-gate.json',result)
meta={'id':ident,'status':'SOURCE_ESTABLISHING','source_sha':sha,'parent_sha':'1f917f44fcfb88e61f3ad22c5cc75fa3a06b6c0e','source':source,'results':results,'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'pid':os.getpid(),'compiler_invocations':0,'core_invocations':0,'full_ns3_builds':0,'network_runs':0}
def metadata():
 with open(results+'/metadata.json','w') as f: json.dump(meta,f,sort_keys=True,indent=2); f.write('\n')
metadata()
commands=[]
def logged(argv,name,cwd=None):
 with open(results+'/logs/'+name+'.stdout','xb') as out,open(results+'/logs/'+name+'.stderr','xb') as err:
  rc=subprocess.call(argv,cwd=cwd,stdout=out,stderr=err)
 commands.append({'argv':argv,'cwd':cwd,'exit':rc,'stdout':'logs/'+name+'.stdout','stderr':'logs/'+name+'.stderr'})
 if rc: raise RuntimeError('Source command failed: '+name)
try:
 logged(['git','clone','--shared','--no-checkout',cache,source],'clone')
 logged(['git','-C',source,'remote','set-url','origin','https://github.com/LarryBUPT/conweave-ns3.git'],'source-origin')
 logged(['git','-C',source,'checkout','--detach',sha],'checkout')
 assert subprocess.check_output(['git','-C',source,'rev-parse','HEAD']).decode().strip()==sha
 tree=subprocess.check_output(['git','-C',source,'ls-tree','-r',sha]); assert len(tree.splitlines())==4845 and hashlib.sha256(tree).hexdigest()=='3da8acbcc1809389aac24adc1936d22874821077e40ddd397723fa7d977e0e64'
 with open(results+'/provenance/source-tree.txt','xb') as f: f.write(tree)
 files=[]
 for entry in tree.decode().splitlines():
  info,relative=entry.split('\t',1); mode,kind,blob=info.split()
  assert mode in ('100644','100755') and kind=='blob' and not relative.startswith('/') and '..' not in relative.split('/')
  target=source+'/'+relative; assert os.path.realpath(target)==target and not os.path.islink(target)
  b=open(target,'rb').read(); actual=hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest(); assert actual==blob, relative
  files.append({'path':relative,'mode':mode,'git_blob':blob,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 expected={'src/point-to-point/model/ws31-endpoint-ledger.h':'105b7ced338b85e12ddb87f0235ab9bfff1ac0444a34584a9127cb6cbe944524','tests/ws31_endpoint_ledger_test.cc':'da24c329cff2c8e118fe19653e9b76a1926fd9a295b55009a11b4b7a0765ba49'}
 for f,h in expected.items(): assert hashlib.sha256(open(source+'/'+f,'rb').read()).hexdigest()==h
 assert not subprocess.check_output(['git','-C',source,'status','--porcelain'])
 save('provenance/source-files.json',files); save('provenance/source-establishment-commands.json',commands)
 meta.update({'status':'SOURCE_ESTABLISHED_NOT_COMPILED','established_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'source_tree_entries':len(files),'source_tree_sha256':hashlib.sha256(tree).hexdigest(),'verified_source_bytes':sum(x['bytes'] for x in files),'source_files_manifest_sha256':hashlib.sha256(open(results+'/provenance/source-files.json','rb').read()).hexdigest(),'source_clean':True})
 metadata(); print(json.dumps(meta,sort_keys=True))
except Exception as error:
 meta.update({'status':'SOURCE_ESTABLISHMENT_FAILED_STOP','error':str(error)}); metadata(); raise
