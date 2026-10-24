"""Recoverable WS-30 execution; formal phases require a separately approved gate."""
import argparse
import collections
import contextlib
import datetime
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

import run_ws30_stage2 as stage
import prepare_ws30_composition as composition

ROOT, EV = stage.ROOT, stage.EV
COMPOSITION_SOURCE = 'a674637dd10404066211b0706308d7337395d85a'
PLAN = EV / 'ws30-stage3-execution-plan-r3.json'
CHECK_PLAN = EV / 'ws30-stage3-correctness-plan-r3.json'
AUTHORIZATION = EV / 'ws30-stage3-execution-authorization.json'
REVIEW_SHA = 'c48c4bfeacffc6bfc915cd035309fd12317802dc78cf2927e96956d76bda0c1b'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    os.replace(temporary, path)


@contextlib.contextmanager
def controller_lock():
    path = ROOT / 'results/ws30-stage3-controller.lock'
    path.parent.mkdir(exist_ok=True)
    with path.open('a+b') as handle:
        if handle.tell() == 0:
            handle.write(b'0'); handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt': msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def prepare():
    review_file = EV / 'ws30-stage3-review-plan-r1.json'
    assert stage.sha(review_file) == REVIEW_SHA
    review, design = read(review_file), composition.generate()
    comp = []
    for trace in design['traces']:
        for arm in design['arms']:
            comp.append(dict(trace, id='20261024-220000-ws30-comp3-s%d-c%d-%s' %
                             (trace['swap'], trace['continuing'], arm.lower()), arm=arm,
                             mode=stage.ARMS[arm], role='composition', cap=12, observe=2,
                             source_sha=COMPOSITION_SOURCE, topology=design['topology'],
                             topology_sha256=design['topology_sha256'], composition=1))
    default_topo = 'topo_1280_400G_400G_OS1'
    main = [dict(c, topology=default_topo, topology_sha256=stage.sha(ROOT/'config'/
             (default_topo+'.txt')), composition=0) for c in review['main']]
    lead = [dict(c, topology=default_topo, topology_sha256=main[0]['topology_sha256'],
                 composition=0) for c in review['lead']]
    data = {'kind': 'WS-30 stage-3 frozen execution contract; authorization separate',
            'execution_enabled': False, 'review_plan_sha256': REVIEW_SHA,
            'composition_design_sha256': stage.sha(EV/'ws30-composition-design-r2.json'),
            'superseded_plan_sha256':stage.sha(EV/'ws30-stage3-execution-plan-r2.json'),
            'preserved_unrun_build':'20261024-210000-ws30-cprep-s0-c0-c16',
            'preserved_failed_id':'20261024-210000-ws30-cprep2-s0-c0-c16',
            'main': main, 'lead': lead, 'composition': comp,
            'required_counts': {'main':192, 'lead':72, 'composition':12},
            'maximum_cap':12, 'authorization_file':str(AUTHORIZATION.relative_to(ROOT)).replace('\\','/'),
            'resource_limits': review['resource_limits']}
    allcells=main+lead+comp
    assert len({c['id'] for c in allcells}) == 276
    for c in allcells:
        assert stage.remote.remote.ID_RE.fullmatch(c['id'])
        assert stage.sha(ROOT/'config'/c['trace']) == c['trace_sha256']
    stage.frozen(PLAN, data)
    # Six branch checks cover E/Q16/C16 and all C16 orientation/arrival
    # conditions; they have separate IDs and never count as formal cells.
    chosen = [next(c for c in comp if c['arm']=='C16' and c['swap']==0 and c['continuing']==0)]
    chosen += [c for c in comp if c not in chosen and
               (c['arm']=='C16' or (c['swap']==0 and c['continuing']==0))]
    checks = [dict(c, id='20261024-210000-ws30-cprep3-s%d-c%d-%s' %
                   (c['swap'],c['continuing'],c['arm'].lower()), role='composition-check',cap=4)
              for c in chosen]
    old=read(EV/'ws30-stage2-recovery-plan-r1.json')
    accepted=read(EV/'ws30-technical-results-recovered-r1.json')
    for arm in ['E','C16']:
        prior=next(c for c in old['technical'] if c['arm']==arm and c['role']=='bridge-precheck')
        expected=next(r for r in accepted['rows'] if r['id']==prior['id'])['fct_sha256']
        checks.append(dict(prior,id='20261024-210000-ws30-cprep3-off-'+arm.lower(),
                           source_sha=COMPOSITION_SOURCE,role='compatibility-check',cap=4,
                           topology=default_topo,topology_sha256=main[0]['topology_sha256'],
                           composition=0,expected_fct_sha256=expected))
    assert len(checks)==8
    stage.frozen(CHECK_PLAN,{'kind':'WS-30 small correctness only; no formal effects',
                            'source_sha':COMPOSITION_SOURCE,'cells':checks,
                            'formal_plan_sha256':stage.sha(PLAN)})
    return data


def verify_composition(cell, folder, log):
    expected=read(EV/'ws30-composition-design-r2.json')
    ledger={p:[0,0] for p in [2,3]}
    snapshots=[]
    for line in log.splitlines():
        if line.startswith('WS30_COMPOSITION_QUEUE '):
            row=stage.kv(line); values=ledger[row['port']]
            change=row['bytes']*(1 if row['enqueue'] else -1)
            values[0]+=change
            if row['tag']==1: values[1]+=change
            assert values==[row['total'],row['background']] and min(values)>=0
        if line.startswith('WS30_COMPOSITION_PROBE '):
            row=stage.kv(line);snapshots.append(row)
            assert ledger[2]==[65536,cell['expected_background_by_port']['2']]
            assert ledger[3]==[65536,cell['expected_background_by_port']['3']]
            assert row['q1']==row['q2']==65536
            assert row['b1']==ledger[2][1] and row['b2']==ledger[3][1]
    assert len(snapshots)==1 and ledger=={2:[0,0],3:[0,0]}
    hold=[stage.kv(l) for l in log.splitlines() if l.startswith('WS30_COMPOSITION_HOLD ')]
    assert hold==[{'time_ns':expected['hold_ns'],'hold':1},
                  {'time_ns':expected['release_ns'],'hold':0}]
    finals=[stage.kv(l) for l in log.splitlines() if l.startswith('WS30_COMPOSITION_FINAL ')]
    assert {r['port'] for r in finals}=={2,3}
    for r in finals:
        assert r['total']==r['background']==0
        assert r['after_probe_background']==(16*8288 if cell['continuing'] else 0)
    routes=[stage.kv(l) for l in log.splitlines() if l.startswith('WS30_ROUTE ')]
    probe=[r for r in routes if r['switch']==4 and r['sport']==10004 and
           r['dip']==0x0b000301 and r['seq']==0]
    assert len(probe)==1
    chosen=probe[0]['port']
    if cell['arm']=='Q16': assert chosen==2
    if cell['arm']=='C16': assert chosen==(2 if cell['swap'] else 3)
    if cell['arm']!='E':
        choices=[stage.kv(l) for l in log.splitlines() if l.startswith('WS30_CHOICE ')]
        choices=[r for r in choices if r['switch']==4 and r['sport']==10004 and r['dip']==0x0b000301]
        assert len(choices)==1 and choices[0]['first']==2 and choices[0]['second']==3
        assert choices[0]['q1']==choices[0]['q2']==65536 and choices[0]['chosen']==chosen
    meta=read(folder/'metadata.json');raw=str(meta['raw_directory'])
    fct=folder/'raw'/raw/(raw+'_out_fct.txt')
    entries=[list(map(int,l.split())) for l in fct.read_text().splitlines()]
    probes=[r for r in entries if r[:5]==[0,3,10004,100,16000]]
    assert len(probes)==1
    return {'snapshot':snapshots[0], 'chosen_port':chosen,
            'probe_fct_ns':probes[0][6], 'all_completed_rows':len(entries),
            'queue_trace_sha256':stage.sha(folder/'logs/config.log'),
            'after_probe_background_by_port':{str(r['port']):r['after_probe_background'] for r in finals}}


def verify(cell):
    folder=ROOT/'results'/cell['id'];meta=read(folder/'metadata.json')
    actual_cap=meta['concurrency_cap']
    assert actual_cap in [1,4,8,12] and actual_cap<=cell['cap']
    assert meta['parameters'].get('ws30_composition',0)==cell.get('composition',0)
    # Reuse the full identity, queue, transport, raw and resource verifier,
    # with the actual admitted cap and this cell's immutable topology.
    previous=stage.makeplan
    stage.makeplan=lambda:{'topology_sha256':cell['topology_sha256']}
    try: row=stage.verify(dict(cell,cap=actual_cap))
    finally: stage.makeplan=previous
    command=meta['command']
    assert '--lb '+cell['mode'] in command and '--topo '+cell['topology'] in command
    assert '--flow-file config/'+cell['trace'] in command
    if 'expected_fct_sha256' in cell: assert row['fct_sha256']==cell['expected_fct_sha256']
    if cell.get('composition'):
        row['composition']=verify_composition(cell,folder,(folder/'logs/config.log').read_text())
    row.update(source_sha=cell['source_sha'],trace_sha256=cell['trace_sha256'],actual_cap=actual_cap)
    return row


def capacity(resource, ceiling):
    if resource.get('other_users') or resource.get('unexpected_simulation_pids') or resource.get('rss_mib',0)>32768 or \
            float(resource['load_1m'])>20 or float(resource['mem_available_gib'])<32 or \
            float(resource['free_gib'])<100:
        return 0
    if float(resource['load_1m'])>17 or float(resource['mem_available_gib'])<52:return min(ceiling,4)
    if float(resource['load_1m'])>14 or float(resource['mem_available_gib'])<70:return min(ceiling,8)
    return ceiling


REMOTE_WAIT = r'''
import json,os,subprocess,sys,time
q=json.loads(sys.argv[1]); root='/home/fnl/lzy'; deadline=time.time()+q['seconds']
sys.dont_write_bytecode=True;sys.path.insert(0,root+'/.research-workflow');import remote_worker as worker
peak=0.; minmem=1e9; mindisk=1e9; maxrss=0.
while True:
    states={}
    for name in q['ids']:
        path=os.path.join(root,'results',name,'metadata.json')
        if os.path.exists(path):
            if os.path.realpath(path)!=path: raise RuntimeError('Metadata symlink')
            with open(path) as f: states[name]=json.load(f)
        else: states[name]=None
        sample=os.path.join(root,'results',name,'logs/resource-samples.jsonl')
        if os.path.isfile(sample):
            with open(sample,'rb') as f:
                f.seek(max(0,os.path.getsize(sample)-8192)); tail=f.read().decode().splitlines()
            for line in reversed(tail):
                try: row=json.loads(line)
                except ValueError: continue
                maxrss=max(maxrss,row.get('process_tree_rss_mib',0))
    load=os.getloadavg()[0]
    with open('/proc/meminfo') as f: mem={l.split(':')[0]:int(l.split()[1]) for l in f}
    available=mem['MemAvailable']/1024.**2; fs=os.statvfs(root); free=fs.f_bavail*fs.f_frsize/1024.**3
    users=[l for l in subprocess.check_output(['ps','-eo','uid,pid,stat,comm','--no-headers']).decode().splitlines()
           if int(l.split()[0])>=1000 and int(l.split()[0])!=os.getuid() and not l.split()[2].startswith('Z')]
    own=[int(v['pid']) for v in states.values() if v and v.get('status')=='RUNNING']
    unknown=[p for p in worker.active_simulations() if not any(worker.descendant_of(int(p),pid) for pid in own)]
    peak=max(peak,load); minmem=min(minmem,available); mindisk=min(mindisk,free)
    statuses={k:(v['status'] if v else None) for k,v in states.items()}
    unsafe=bool(users) or bool(unknown) or load>20 or available<32 or free<100 or maxrss>32768
    if statuses!=q['known'] or time.time()>=deadline or (unsafe and not q['drain']):
        print(json.dumps({'states':states,'resource':{'load_1m':load,'mem_available_gib':available,
          'free_gib':free,'other_users':users,'unexpected_simulation_pids':unknown,'rss_mib':maxrss},'window':{'peak_load_1m':peak,
          'minimum_mem_available_gib':minmem,'minimum_free_gib':mindisk,'peak_tree_rss_mib':maxrss}})); break
    time.sleep(10)
'''


class Backend:
    def snapshot(self,cells,known=None,drain=False):
        ids=[c['id'] for c in cells]
        assert all(stage.remote.remote.ID_RE.fullmatch(i) for i in ids)
        request={'ids':ids,'known':known or {},'seconds':1800 if known else 0,'drain':drain}
        cfg=stage.remote.remote.config()
        command='python3 -c '+shlex.quote(REMOTE_WAIT)+' '+shlex.quote(json.dumps(request))
        out=subprocess.check_output(stage.remote.remote.ssh_base(cfg)+[command],text=True,timeout=1870)
        return json.loads(out)

    def gate(self):
        return stage.resources.host_gate(reject_active=True)

    def build(self,cells):
        assert len({c['source_sha'] for c in cells})==1
        if not getattr(self,'synced',False):
            try:stage.remote.command('sync','--repo-local',str(ROOT))
            except RuntimeError:
                # One quiet workspace login retry, then the normal Git bundle
                # transport. Never print the credential/bootstrap script.
                subprocess.run(stage.remote.remote.ssh_base(stage.remote.remote.config())+
                               ['bash /home/fnl/lzy/login.sh >/dev/null 2>&1'],
                               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=120)
                try:stage.remote.command('sync','--repo-local',str(ROOT))
                except RuntimeError:stage.remote.command('sync-bundle','--repo-local',str(ROOT))
            self.synced=True
        stage.engine.SOURCE_SHA=cells[0]['source_sha']
        # The shared WS-25 receipt helper expects demand fields. Composition
        # fixtures have no demand seed; add receipt-only context, leaving the
        # frozen cell contract and ns-3 seed unchanged.
        receipt_cells=[dict(c,seed=c.get('seed',0),
                            background=c.get('background',c['expected_tags'].get('1',0)),
                            run_order=c.get('run_order',0)) for c in cells]
        stage.engine.build_missing_group(receipt_cells,0,0)

    def local(self,cell):
        return (ROOT/'results'/cell['id']).exists()

    def verify(self,cell): return verify(cell)

    def start(self,cell,cap):
        # Recover the watcher created just before a controller interruption.
        code=("import os,subprocess; name=%r; sample='/home/fnl/lzy/results/'+name+'/logs/resource-samples.jsonl'; "
              "rows=subprocess.check_output(['ps','-eo','args','--no-headers']).decode().splitlines(); "
              "print(sum('ws11_resource_watch.py '+name in r and 'python3 -c' not in r for r in rows)); "
              "print(int(os.path.exists(sample)))") % cell['id']
        out=subprocess.check_output(stage.remote.remote.ssh_base(stage.remote.remote.config())+
                                    ['python3 -c '+shlex.quote(code)],text=True,timeout=45).splitlines()
        watchers,sample=map(int,out[-2:])
        assert watchers<=1,'Duplicate resource watcher'
        if not watchers:
            assert not sample,'Resource watcher disappeared; preserve samples and inspect'
            stage.remote.start_watch(cell['id'])
        stage.engine.calibration.verify_remote_trace(cell)
        stage.remote.command('run',cell['id'],'--lb',cell['mode'],'--pfc','0','--irn','1',
            '--bw','400','--buffer','9','--topo',cell['topology'],'--flow-file',cell['trace'],
            '--simul-time','0.01','--netload','10','--max-concurrent',str(cap),
            '--ws30-observe',str(cell['observe']),'--ws30-composition',str(cell.get('composition',0)))

    def finish(self,cell):
        stage.remote.wait_watch(cell['id'])
        stage.remote.command('fetch',cell['id'])
        stage.remote.fetch_config_log(cell,read(ROOT/'results'/cell['id']/'metadata.json'))
        return verify(cell)

    def preserve_failure(self,cell):
        # fetch never overwrites an existing local directory; remote originals
        # always survive even if transport or a partial fetch needs attention.
        stage.remote.wait_watch(cell['id'])
        if not self.local(cell): stage.remote.command('fetch',cell['id'])


class Runner:
    def __init__(self,cells,backend,path,cap=12,first_single=False):
        self.cells=cells;self.backend=backend;self.path=path;self.first_single=first_single
        self.contract=__import__('hashlib').sha256(json.dumps(cells,sort_keys=True).encode()).hexdigest()
        self.state=read(path) if path.exists() else {'contract':self.contract,'verified':{},'pending':[],
                                                    'failures':{},'cap':cap,'events':[]}
        if self.state['contract']!=self.contract:raise RuntimeError('Resume contract changed')

    def save(self,event,**details):
        self.state['events'].append({'event':event,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),**details})
        atomic(self.path,self.state)

    def collect(self,cells,states):
        for c in cells:
            meta=states.get(c['id'])
            if meta and meta['status']=='FAILED':
                self.state['failures'][c['id']]=meta
                try:self.backend.preserve_failure(c)
                except Exception as error:self.save('failure_fetch_attention',id=c['id'],error=str(error))
                self.save('failed_preserved',id=c['id'])
            elif self.backend.local(c):
                self.state['verified'][c['id']]=self.backend.verify(c)
                self.save('verified_local',id=c['id'])
            elif meta and meta['status']=='SUCCEEDED':
                self.state['verified'][c['id']]=self.backend.finish(c)
                self.save('verified_fetched',id=c['id'])

    def drain(self,cells,snapshot,halt=False):
        while True:
            self.state['cap']=min(self.state['cap'],capacity(snapshot['resource'],self.state['cap']) or 4)
            if capacity(snapshot['resource'],12)==0:
                if not halt:self.save('admission_stop',resource=snapshot['resource'])
                halt=True
            states=snapshot['states']
            for c in cells:
                meta=states[c['id']]
                if meta and meta.get('git_commit')!=c['source_sha']:
                    self.save('source_mismatch',id=c['id']);raise RuntimeError('Remote source mismatch')
            running=[c for c in cells if states[c['id']] and states[c['id']]['status'] in ['RUNNING','BUILDING']]
            if any(m and m['status']=='FAILED' for m in states.values()):halt=True
            if not running:
                self.collect(cells,states)
                if halt or self.state['failures']:raise RuntimeError('Admission stopped; all current workers drained; evidence preserved')
                return states
            known={i:m['status'] if m else None for i,m in states.items()}
            snapshot=self.backend.snapshot(cells,known,drain=halt)
            self.save('worker_change_or_supervision',resource=snapshot['resource'],window=snapshot.get('window'))

    def run(self):
        # Treat summaries only as indexes; successful rows are revalidated.
        for c in self.cells:
            if c['id'] in self.state['verified']:
                self.state['verified'][c['id']]=self.backend.verify(c)
        byid={c['id']:c for c in self.cells}
        while len(self.state['verified'])<len(self.cells):
            if self.state['failures']:raise RuntimeError('Preserved failed IDs require a new approved repair plan')
            pending=[c for c in self.cells if c['id'] not in self.state['verified']]
            if self.state['pending']:
                group=[byid[i] for i in self.state['pending']]
            else:
                gate=self.backend.gate();admitted=capacity(gate,self.state['cap'])
                if not admitted:raise RuntimeError('Host admission paused')
                self.state['cap']=admitted
                size=1 if self.first_single and not self.state['verified'] else admitted
                group=pending[:size];self.state['pending']=[c['id'] for c in group]
                self.save('batch_reserved',ids=self.state['pending'],cap=admitted)
            snapshot=self.backend.snapshot(group)
            states=self.drain(group,snapshot)
            unknown=[(i,m['status']) for i,m in states.items() if m and m['status'] not in ['BUILT','SUCCEEDED']]
            if unknown:raise RuntimeError('Unexpected remote state: '+repr(unknown))
            missing=[c for c in group if not states[c['id']] and c['id'] not in self.state['verified']]
            for offset in range(0,len(missing),min(4,self.state['cap'])):
                self.backend.gate();self.backend.build(missing[offset:offset+min(4,self.state['cap'])])
                self.save('build_group_complete',ids=[c['id'] for c in missing[offset:offset+min(4,self.state['cap'])]])
            snapshot=self.backend.snapshot(group);halt=False;started=0
            for c in group:
                meta=snapshot['states'][c['id']]
                if c['id'] in self.state['verified']:continue
                if not meta or meta['git_commit']!=c['source_sha'] or meta['status']!='BUILT':
                    halt=True;break
                resource=stage.resources.host_gate() if isinstance(self.backend,Backend) else self.backend.gate()
                admitted=capacity(resource,self.state['cap'])
                if not admitted:halt=True;break
                self.state['cap']=admitted
                if started>=admitted:break
                try:
                    self.backend.start(c,admitted);started+=1
                    self.save('started',id=c['id'],cap=admitted)
                except Exception as error:
                    halt=True;self.save('start_attention',id=c['id'],error=str(error));break
            self.drain(group,self.backend.snapshot(group),halt=halt)
            self.state['pending']=[];self.save('batch_verified',verified=len(self.state['verified']))
        return self.state


def authorize(phase,session_file):
    if not AUTHORIZATION.exists():raise RuntimeError('Formal execution is closed: main-chat authorization receipt is absent')
    gate=read(AUTHORIZATION)
    if not (gate.get('approved') is True and phase in gate.get('phases',[]) and
            gate.get('plan_sha256')==stage.sha(PLAN)):
        raise RuntimeError('Authorization does not bind this frozen phase and plan')
    check_result=EV/'ws30-stage3-correctness-results-r3.json'
    if not check_result.exists() or stage.sha(check_result)!=gate.get('correctness_sha256'):
        raise RuntimeError('Approved correctness receipt missing or changed')
    if not session_file:raise RuntimeError('Actual supervising task session file is required')
    context=None
    for line in session_file.open(encoding='utf-8'):
        data=json.loads(line)
        if data.get('type')=='turn_context':context=data['payload']
    if not context or (context.get('model'),context.get('effort'))!=('gpt-6-luna','medium'):
        raise RuntimeError('Actual task setting is not GPT-6 Luna / Medium')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','status','verify-local','run-check','run'])
    parser.add_argument('--phase',choices=['main','lead','composition'],default='main')
    parser.add_argument('--session-file',type=Path)
    args=parser.parse_args()
    if args.command=='prepare':
        plan=prepare();print(json.dumps({'counts':plan['required_counts'],'plan_sha256':stage.sha(PLAN),'execution_enabled':False}));return
    plan=read(PLAN)
    if args.command=='run':authorize(args.phase,args.session_file)
    checks=args.command=='run-check'
    cells=read(CHECK_PLAN)['cells'] if checks else plan[args.phase]
    if args.command in ['status','verify-local']:
        local=[c for c in cells if (ROOT/'results'/c['id']).exists()]
        for c in local:verify(c)
        print(json.dumps({'phase':args.phase,'verified_local':len(local),'required':len(cells),
                          'authorization_present':AUTHORIZATION.exists()}));return
    path=ROOT/'results'/('ws30-stage3-correctness-summary-r3.json' if checks else 'ws30-stage3-'+args.phase+'-summary-r3.json')
    stage.engine.RECEIPTS=ROOT/'results/ws30-stage3-build-receipts-r3.jsonl'
    with controller_lock():
        runner=Runner(cells,Backend(),path,cap=4 if checks else 12,first_single=checks)
        try:state=runner.run()
        except Exception as error:
            runner.save('controller_stop',error=str(error))
            raise
        result={'verified_cells':len(state['verified']),'plan_sha256':stage.sha(CHECK_PLAN if checks else PLAN),
                'formal_effect_cells_counted':0 if checks else len(state['verified']),
                'rows':[state['verified'][c['id']] for c in cells]}
        output=EV/('ws30-stage3-correctness-results-r3.json' if checks else 'ws30-stage3-'+args.phase+'-results-r3.json')
        stage.frozen(output,result)
        print(json.dumps({'verified':len(state['verified']),'formal_execution':not checks}))


if __name__=='__main__':main()
