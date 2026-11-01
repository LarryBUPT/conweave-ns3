"""Read-only diagnosis of the process recorded by the stopped resource gate."""
import importlib.util,json,pathlib,shlex,subprocess
ROOT=pathlib.Path(__file__).resolve().parent
PREFIX='adapter-boundary-preflight-r1'
REPO=ROOT.parents[4]/'ws31-candidates-implementation'
spec=importlib.util.spec_from_file_location('read_only_adapter_controller',REPO/'scripts/remote_experiment.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
code=r'''
import os,json,re,datetime
pid=297502;result={'recorded_utc':datetime.datetime.utcnow().isoformat()+'Z','target_pid':pid,'exists':os.path.exists('/proc/'+str(pid)),'ancestors':[]}
seen=set()
while pid and pid not in seen and len(seen)<8:
 seen.add(pid)
 try:
  text=open('/proc/'+str(pid)+'/status').read()
  parent=int(re.search(r'^PPid:\s+(\d+)',text,re.M).group(1))
  row={'pid':pid,'ppid':parent,'name':re.search(r'^Name:\s+(.+)',text,re.M).group(1),
   'state':re.search(r'^State:\s+(.+)',text,re.M).group(1),'uid':int(re.search(r'^Uid:\s+(\d+)',text,re.M).group(1))}
  try:row['cwd']=os.readlink('/proc/'+str(pid)+'/cwd')
  except OSError:row['cwd']='unavailable'
  result['ancestors'].append(row);pid=parent
 except (OSError,IOError,AttributeError):break
print(json.dumps(result))
'''
v=subprocess.run(c.ssh_base(c.config())+['python3 -c '+shlex.quote(code)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
assert v.returncode==0,v.stderr
r=json.loads(v.stdout);r['remote_mutations']=0;r['process_signals_sent']=0
out=ROOT/(PREFIX+'-process-diagnosis.json');assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps(r))
