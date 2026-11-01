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
