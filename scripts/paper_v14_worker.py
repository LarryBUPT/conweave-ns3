#!/usr/bin/env python3
"""Python 3.5 worker: sealed binary, exact hashed plan, private cwd and outputs.

No build, sync, implicit resume, or input generation. An interrupted/failed ID is
preserved and cannot be rerun. Qualification plans cannot contain held-out traces.
"""
import argparse
import contextlib
import datetime
import fcntl
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

ROOT='/home/fnl/lzy'
ID=re.compile(r'^20261029-[0-9]{6}-pv14[a-z0-9-]{1,36}$')

def sha(p):
    d=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):d.update(b)
    return d.hexdigest()
def read(p):
    with open(p) as f:return json.load(f)
def now():return datetime.datetime.utcnow().isoformat()+'Z'
def inside(p):
    p=os.path.abspath(p)
    if not p.startswith(ROOT+'/') or os.path.realpath(p)!=p:raise RuntimeError('Redirected/outside path: '+p)
    return p
def frozen(p,d):
    inside(p)
    with open(p,'x') as f:json.dump(d,f,indent=2,sort_keys=True);f.write('\n')
def atomic(p,d):
    tmp=p+'.tmp-'+str(os.getpid())
    frozen(tmp,d);os.rename(tmp,p)
def resources():
    m={}
    for line in open('/proc/meminfo'):
        k,_,v=line.partition(':')
        if k=='MemAvailable':m['available_gib']=int(v.split()[0])/1024.0**2
    st=os.statvfs(ROOT);m['disk_free_gib']=st.f_bavail*st.f_frsize/1024.0**3;m['load_1m']=os.getloadavg()[0]
    if m['available_gib']<32 or m['disk_free_gib']<100 or m['load_1m']>20:raise RuntimeError('Resource gate '+str(m))
    return m
@contextlib.contextmanager
def admission_lock():
    p=inside(ROOT+'/.research-workflow/simulation-start.lock')
    with open(p,'a') as f:
        fcntl.flock(f,fcntl.LOCK_EX)
        try:yield
        finally:fcntl.flock(f,fcntl.LOCK_UN)
def active():
    # Inspect process ownership, never enumerate another WS's result metadata.
    known={}
    for line in subprocess.check_output(['ps','-eo','pid,args','--no-headers']).decode().splitlines():
        fields=line.strip().split(None,1)
        if len(fields)!=2:continue
        pid=int(fields[0]);cmd=fields[1]
        if pid==os.getpid() or 'python3 -c' in cmd or 'base64' in cmd:continue
        relevant=('paper_v14_worker.py run' in cmd or 'network-load-balance' in cmd or 'remote_worker.py execute' in cmd)
        if not relevant:continue
        try:cwd=os.path.realpath('/proc/'+str(pid)+'/cwd')
        except OSError:continue
        matches=re.findall(r'20261029-[0-9]{6}-pv14[a-z0-9-]+',cmd+' '+cwd)
        if not matches:raise RuntimeError('Other or unknown active simulation process')
        ident=matches[0];meta=ROOT+'/results/'+ident+'/metadata.json'
        if not os.path.isfile(meta):raise RuntimeError('Active PV14 worker lacks metadata')
        d=read(meta)
        if d.get('status')=='RUNNING':known[ident]=d
    return list(known.values())

def environment(artifact,observe):
    env={k:v for k,v in os.environ.items() if not (k.startswith('WS') or k.startswith('PAPER_V14'))}
    env['LD_LIBRARY_PATH']=artifact+'/lib';env['WS30_OBSERVE']='1';env['PAPER_V14_OBSERVE']=str(observe)
    return env
def ldd(binary,env):
    text=subprocess.check_output(['ldd',binary],env=env).decode()
    if 'not found' in text:raise RuntimeError('Unresolved dynamic dependency')
    files={}
    for line in text.splitlines():
        paths=re.findall(r'(/[^\s()]+)',line)
        if paths:
            p=os.path.realpath(paths[0]);files[p]=sha(p)
    return dict(output=text,files=files)
def artifact_manifest(build_source,artifact,source):
    build_source=inside(build_source);artifact=inside(artifact)
    if os.path.lexists(artifact):raise RuntimeError('Artifact occupied')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=build_source).decode().strip()!=source:raise RuntimeError('Build source differs')
    os.makedirs(artifact+'/lib')
    candidates=glob.glob(build_source+'/build/scratch/*network-load-balance*')
    candidates=[p for p in candidates if os.path.isfile(p) and os.access(p,os.X_OK)]
    if len(candidates)!=1:raise RuntimeError('Ambiguous built executable')
    shutil.copy2(candidates[0],artifact+'/network-load-balance')
    for parent,dirs,files in os.walk(build_source+'/build'):
        for name in files:
            if '.so' not in name:continue
            p=os.path.join(parent,name)
            if not os.path.isfile(p):continue
            target=artifact+'/lib/'+name
            if os.path.exists(target):
                if sha(target)!=sha(p):raise RuntimeError('Duplicate library names differ')
            else:shutil.copy2(p,target)
    env=environment(artifact,0);deps=ldd(artifact+'/network-load-balance',env)
    for path in deps['files']:
        if 'libns3' in os.path.basename(path) and not path.startswith(artifact+'/lib/'):raise RuntimeError('Library escaped immutable artifact')
    files={}
    for parent,dirs,names in os.walk(artifact):
        for name in names:
            p=os.path.join(parent,name);files[p]=sha(p);os.chmod(p,0o555 if name=='network-load-balance' else 0o444)
    d=dict(source_sha=source,build_source=build_source,original_binary=candidates[0],files=files,dependencies=deps,created_utc=now())
    frozen(artifact+'/manifest.json',d);os.chmod(artifact+'/manifest.json',0o444)
    os.chmod(artifact+'/lib',0o555);os.chmod(artifact,0o555)
    return d
def check_artifact(p,expected):
    if sha(p+'/manifest.json')!=expected:raise RuntimeError('Artifact manifest differs')
    d=read(p+'/manifest.json')
    for path,digest in d['files'].items():
        if inside(path)!=path or sha(path)!=digest:raise RuntimeError('Artifact changed')
    env=environment(p,0)
    if ldd(p+'/network-load-balance',env)['files']!=d['dependencies']['files']:raise RuntimeError('Dynamic dependency changed')
    return d
def plan_load(path,digest):
    path=inside(path)
    if sha(path)!=digest:raise RuntimeError('Plan hash differs')
    p=read(path)
    if p['repository']!='https://github.com/LarryBUPT/conweave-ns3.git':raise RuntimeError('Personal fork differs')
    if p['stage']=='qualification':
        if not p['qualification_authorized'] or any('pv14-qualification' not in c['trace'] and 'pv14-pressure' not in c['trace'] for c in p['cells']):raise RuntimeError('Qualification scope differs')
        if p['maximum_cap']!=2:raise RuntimeError('Qualification cap differs')
    elif not p.get('execution_approved') or not p.get('accepted_main_receipt_sha256'):raise RuntimeError('Production not released')
    return p
def manifest(folder):
    result={}
    for parent,dirs,files in os.walk(folder):
        for name in files:
            p=os.path.join(parent,name)
            if os.path.islink(p):raise RuntimeError('Output symlink')
            if name not in ('manifest.json','metadata.json'):result[os.path.relpath(p,folder)]=sha(p)
    return result
def verify_fct(trace,fct):
    sp={};dp={};expected={}
    lines=open(trace).read().splitlines()
    for l in lines[1:]:
        a=l.split();s,d,pg,size=map(int,a[:4]);start=int(round(float(a[4])*1e9));sport=sp.get(s,10000);dport=dp.get(d,100)
        sp[s]=sport+1;dp[d]=dport+1;key=(s,d,sport,dport,size,start)
        if key in expected:raise RuntimeError('Duplicate expected identity')
        expected[key]=int(a[5])
    if len(expected)!=int(lines[0]):raise RuntimeError('Input count differs')
    original=len(expected);payload=sum(k[4] for k in expected);observed_payload=0
    for l in open(fct):
        x=tuple(map(int,l.split()))
        if len(x)!=8 or x[6]<=0:raise RuntimeError('Invalid FCT')
        candidates=[x[:5]+(x[5]+i,) for i in (-1,0,1) if x[:5]+(x[5]+i,) in expected]
        if len(candidates)!=1:raise RuntimeError('FCT identity/size/origin differs')
        del expected[candidates[0]];observed_payload+=x[4]
    if expected or observed_payload!=payload:raise RuntimeError('Incomplete FCT/bytes')
    return dict(completed_rows=original,payload_bytes=payload,fct_sha256=sha(fct))
def run(path,digest,ident,artifact,artifact_sha):
    plan=plan_load(path,digest)
    chosen=[c for c in plan['cells'] if c['id']==ident]
    if len(chosen)!=1 or not ID.match(ident):raise RuntimeError('ID not exactly in plan')
    c=chosen[0];a=check_artifact(artifact,artifact_sha)
    if a['source_sha']!=plan['source_sha']:raise RuntimeError('Source differs')
    source=a['build_source']
    if subprocess.check_output(['git','config','--get','remote.origin.url'],cwd=source).decode().strip()!=plan['repository']:raise RuntimeError('Source fork differs')
    cache=ROOT+'/code/conweave-ns3'
    if subprocess.check_output(['git','rev-parse','refs/remotes/origin/'+plan['branch']],cwd=cache).decode().strip()!=plan['source_sha']:raise RuntimeError('Source not pushed/cached on exact branch')
    base=inside(ROOT+'/results/'+ident);runpath=inside(ROOT+'/runs/'+ident)
    with admission_lock():
        resources();workers=active()
        if len(workers)>=plan['maximum_cap'] or any(w.get('pv14_plan_sha256')!=digest for w in workers):raise RuntimeError('Unknown worker/cap blocks admission')
        if os.path.lexists(base) or os.path.lexists(runpath):raise RuntimeError('Occupied ID, never retry')
        os.makedirs(base);os.makedirs(runpath)
        for name in ('config','raw/1','logs'):os.makedirs(base+'/'+name)
        frozen(runpath+'/intent.json',dict(id=ident,source_sha=plan['source_sha'],plan_sha256=digest,artifact_manifest_sha256=artifact_sha,utc=now()))
        d=dict(experiment_id=ident,status='RUNNING',pid=os.getpid(),git_commit=plan['source_sha'],git_repository=plan['repository'],pv14_plan_sha256=digest,artifact_manifest_sha256=artifact_sha,algorithm=c['mode'],simulation_seed=c['simulation_seed'],observe=c['observe'],launch=c['launch'],started_utc=now(),concurrency_cap=plan['maximum_cap'],cwd=base)
        atomic(base+'/metadata.json',d)
    try:
        for src,dest,key in [(source+'/config/'+c['trace'],base+'/config/traffic_trace.txt','trace_sha256'),(source+'/config/topo_1280_400G_400G_OS1.txt',base+'/config/topology.txt','topology_sha256')]:
            if sha(src)!=c[key]:raise RuntimeError('Input/source hash differs')
            shutil.copyfile(src,dest)
        cfg=c['config']
        if hashlib.sha256(cfg.encode()).hexdigest()!=c['config_sha256']:raise RuntimeError('Config hash differs')
        with open(base+'/config/config.txt','x') as f:f.write(cfg)
        for l in cfg.splitlines():
            z=l.split()
            if len(z)==2 and (z[0].endswith('_FILE') or z[0]=='FLOW_FILE'):
                if not z[1].startswith(('config/','raw/1/')) or '..' in z[1]:raise RuntimeError('Configuration path escapes private cwd')
        env=environment(artifact,c['observe'])
        cmd=[artifact+'/network-load-balance','config/config.txt'];cwd=base
        if c['launch']=='waf':
            cmd=[source+'/waf','--run','scratch/network-load-balance '+base+'/config/config.txt','--cwd='+base];cwd=source
        d['command']=cmd;d['resource_start']=resources();d['dynamic_dependencies']=ldd(cmd[0] if c['launch']=='direct' else a['original_binary'],env)
        atomic(base+'/metadata.json',d)
        with open(base+'/logs/simulation.log','wb') as log:
            code=subprocess.call(cmd,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,timeout=300)
        if code:raise RuntimeError('Simulator exit '+str(code))
        logtext=open(base+'/logs/simulation.log').read()
        if 'overflow' in logtext.lower():raise RuntimeError('Observation/queue overflow diagnostic')
        if c['observe'] and not re.search(r'^PV14_TERMINAL .*complete=1$',logtext,re.M):raise RuntimeError('Missing compact observation terminal')
        if not c['observe'] and 'PV14_TERMINAL' in logtext:raise RuntimeError('Disabled observer emitted rows')
        d['audit']=verify_fct(base+'/config/traffic_trace.txt',base+'/raw/1/1_out_fct.txt')
        if d['audit']['completed_rows']!=c['expected_flows'] or d['audit']['payload_bytes']!=c['expected_bytes']:raise RuntimeError('Frozen count/bytes differ')
        check_artifact(artifact,artifact_sha);d['resource_end']=resources();d['status']='SUCCEEDED'
    except Exception as e:
        d['status']='FAILED';d['error']=repr(e);raise
    finally:
        d['finished_utc']=now();atomic(base+'/metadata.json',d);frozen(base+'/manifest.json',manifest(base))
    print(json.dumps(d))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['seal','run']);p.add_argument('--source');p.add_argument('--source-sha');p.add_argument('--artifact',required=True);p.add_argument('--artifact-sha');p.add_argument('--plan');p.add_argument('--plan-sha');p.add_argument('--id');a=p.parse_args()
    if a.operation=='seal':print(json.dumps(artifact_manifest(a.source,a.artifact,a.source_sha)))
    else:run(a.plan,a.plan_sha,a.id,a.artifact,a.artifact_sha)
