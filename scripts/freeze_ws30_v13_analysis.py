"""Record provenance and a non-executable W5 proposal; no remote operations."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'docs/research/evidence'
PAPER=ROOT.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(name,data):
    p=EV/name; s=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    if p.exists():assert read(p)==data
    else:p.write_text(s,encoding='utf-8')
def git(repo,*args):
    return subprocess.check_output(['git','-c','safe.directory='+repo.as_posix(),'-C',str(repo),*args],text=True).strip()

plan=read(EV/'ws30-v13-plan-r2.json')
groups=('technical','lifecycle','pilot','formal_disabled','historical_disabled')
seedrows=[]
for group in groups:
    for c in plan[group]:
        match=re.search(r'_seed(\d+)_',c['trace'])
        seedrows.append({'id':c['id'],'phase':group,'legacy_plan_seed':c['seed'],'demand_seed':int(match[1]) if match else None,'simulation_seed':1,'executed':group in groups[:3]})
write('ws30-v13-seed-audit-r1.json',{'original_plan_sha256':sha(EV/'ws30-v13-plan-r2.json'),'original_plan_unchanged':True,'legacy_field_semantics':'Unspecified default metadata, not a documented sentinel or executable simulation seed. Builder receipts inherit it.','execution_dataflow':'prepare cell(seed=0) -> builder receipt; Backend.start passes no seed -> run.py template RANDOM_SEED 1 -> scratch srand and SeedManager.SetSeed; remote metadata seed=1.','evidence_lines':{'scripts/prepare_ws30_v13.py':[47,54,77,79,81,82],'scripts/run_ws30_v13.py':[44,149,162,166],'run.py':[116],'scripts/remote_worker.py':[471],'scratch/network-load-balance.cc':[1411,1439,1440]},'recommendation':'On future unlock create a new plan revision with explicit demand_seed and simulation_seed=1, retain original r2 bytes and hashes; never pass legacy seed=0 to ns-3. No rerun of the 46 verified cells is required for this metadata correction.','rows':seedrows})

reference=ROOT.parent/'conweave-ns3'
native_sha=git(reference,'rev-parse','HEAD')
files=['src/point-to-point/model/'+n for n in ('conweave-routing.cc','conweave-routing.h','conweave-voq.cc','conweave-voq.h')]
native={p:{'reference_blob':git(reference,'rev-parse','HEAD:'+p),'experiment_blob':git(ROOT,'rev-parse',plan['source_sha']+':'+p)} for p in files}
assert all(v['reference_blob']==v['experiment_blob'] for v in native.values())
rf=[]
for name in ('conweave-2023','gemma','seqbalance-2024','diffflow-2016','sglb-2025','flowcut-2026'):
    folder=PAPER/'参考文献/候选/papers'/name
    for f in ('analysis-technical.md','verification.md'):
        p=folder/f
        if p.exists():rf.append({'path':str(p.relative_to(PAPER)),'sha256':sha(p)})
    for p in sorted(folder.glob('paper*.pdf')):rf.append({'path':str(p.relative_to(PAPER)),'sha256':sha(p)})
for f in ('README.md','reading-log.md'):
    p=PAPER/'参考文献/候选'/f;rf.append({'path':str(p.relative_to(PAPER)),'sha256':sha(p)})
write('ws30-v13-reference-and-baseline-audit-r1.json',{'date_beijing':'2026-10-26','native_reference_repository':'https://github.com/conweave-project/conweave-ns3.git','native_reference_sha':native_sha,'experiment_source_sha':plan['source_sha'],'native_ConWeave_blobs':native,'reference_files':rf,'external_code_search':{'date':'2026-10-26','queries':['Gemma RDMA github Liu Zhao','SeqBalance github','DiffFlow Carpio code'],'github_api_attempts':['https://api.github.com/search/repositories?q=Gemma+RDMA','https://api.github.com/search/repositories?q=SeqBalance','https://api.github.com/search/repositories?q=DiffFlow+load+balancing'],'github_api_result':'Web access unavailable, not a zero-result query','result':'No verifiable author implementation or fixed commit located in these bounded title/author searches and the read primary PDFs. This does not establish that no code exists.','warning':'ResearchGate search snippet about all related code is from its recommended BurstBalancer article, not evidence of Gemma code.'},'fidelity':{'Gemma':{'author_code_sha':None,'missing':['queue length units and Sreroute dimensions','smooth/congested boundary','response-frequency convention and synchronization intervals','phase/END ordering at every upstream hop','queue allocation/full/fallback behavior and END loss recovery'],'required':['local and downstream queues','delayed physical feedback messages','phase/END receiving reorder','capacity and control costs']},'SeqBalance':{'version':'arXiv:2407.09808v1; 2025 final text not compared','author_code_sha':None,'required':['parent WQE splitting','independent sub-QP PSN and fixed routes','ECN feedback and path inactive lifetime','parent CQE max/bitmap completion and operation semantics']},'DiffFlow':{'version':'arXiv:1604.05107v1','author_code_sha':None,'required':['sample-based long-flow detection','SDN rule installation and delay','short ECMP and long RPS','class-queue scheduler and RDMA adaptation'],'oracle_tag_is_native':False},'SGLB':{'version':'SIGCOMM 2025 fixed local PDF; appendix unreviewed','native_baseline_ready':False,'required':['GLB/EDK profiles','SyncMesh/BGP reachability orchestration','remote-state age and compression','topology and NIC reordering assumptions']}}})

methods=['fecmp','conga','letflow','conweave','drill','ws30v13-q12','ws30v13-r12','ws30v13-u12']
cells=[{'design_id':f'W5-r1-s{s}-{timing}-{method}','demand_seed':s,'schedule':timing,'method':method,'simulation_seed':1} for s in (20263101,20263102) for timing in ('concurrent','background_lead20us') for method in methods]
qualification=[{'design_id':f'W5-r1-observer-{fixture}-o{observe}','method':'conweave','fixture':fixture,'observe':observe,'simulation_seed':1} for fixture in ('technical168','sustained_prefix') for observe in (0,1)]
qualification_spec={'technical168':'Existing immutable config/ws30_technical168.txt on the supported large topology','sustained_prefix':'Seed 20263101, all 32 background 64MiB QPs and first 128 short messages from foreground round 0; concurrent schedule','observer_limit_bytes':67108864,'passive_only':True}
write('ws30-w5-proposed-pilot-design-r1.json',{'status':'FROZEN PROPOSAL FOR MAIN-CHAT REVIEW; NOT EXECUTABLE','execution_enabled':False,'experiment_ids_allocated':False,'reference_simulation_sha':plan['source_sha'],'future_observer_source_sha':None,'new_source_and_trace_hash_freeze_required':True,'purpose':'Measure algorithm action and both traffic outcomes during sustained bulk RDMA and staggered short-message rounds; synthetic workload breadth only.','methods':methods,'external_methods_excluded_pending_fidelity':['Gemma','SeqBalance','DiffFlow','SGLB'],'topology':'topo_1280_400G_400G_OS1','common':{'cc':'dcqcn','pfc':0,'irn':1,'bw_gbps':400,'buffer_cli':9,'simulation_seed':1,'simul_time_argument':0.01,'netload_argument':10,'explicit_trace':True,'workload_tag_only_for_analysis':True},'ConWeave_parameters_us':{'extra_reply_deadline':4,'path_pause':16,'extra_voq_flush':16,'default_voq_waiting':300,'tx_expiry':1000},'demand':{'generator_basis':'make_ws25_demand.py endpoint sampling with explicit time/size changes in a new generator','expert_hosts':256,'background_hosts':64,'moe_rounds':8,'moe_flows_per_round':2048,'moe_bytes_per_flow':8192,'moe_total_flows':16384,'moe_total_bytes':134217728,'moe_peers_per_source_per_round':8,'round_interval_ns':100000,'background_flows':32,'background_bytes_per_flow':67108864,'background_total_bytes':2147483648,'total_payload_bytes':2281701376,'background_minimum_solo_serialization_ns':1342177.28,'demand_start_ns':2000000000,'concurrent_foreground_offset_ns':0,'lead_foreground_offset_ns':20000,'background_pairs':'first 32 distinct directed background pairs from the fixed seeded generator','moe_partition':'each source keeps 64 distinct peers; partition a seeded peer permutation into eight disjoint groups of eight','qp_semantics':'each bulk flow is one continuously active QP; each short trace row is a fresh QP, not a persistent WQE API model','node_order':'stable order by (time, background before foreground, source, peer index), identical across methods'},'observations':{'action':['native RTT_REPLY/CLEAR/NOTIFY counters','actual data port changes versus native reroute attempt count','bounded passive per-QP epoch/phase/INIT/TAIL/CLEAR/NOTIFY state-transition records','VOQ allocated/flushed/max packets and buffer age','feedback age and waiting cost','shared queue/identity/payload conservation','receiver gap/SACK/retransmission/timeout by tag'],'performance':['all eight per-round complete-message max from each demand origin','complete job max including staggered waiting','all 32 background FCT plus linear P99/P50/max','individual paired flow FCT distribution and completion fraction'],'notes':['32-background P99 has low tail resolution: publish all 32 values and max','two demand seeds are pilot replication, no confirmatory significance claim','zero native reroute/VOQ is an observed action outcome, not justification to change timeouts']},'observer_qualification_spec':qualification_spec,'observer_qualification_cells':qualification,'comparison_cells':cells,'total_proposed_cells':36,'acceptance':['all input identities/payloads complete','observation off/on FCT hashes identical for both qualification inputs','data route changes correspond to native phase/TAIL handling','source implementations and native timers fixed before performance runs','all zero/negative outcomes preserved'],'stop':['identity or byte loss','observer perturbation','unknown remote work or safety threshold violation','unbounded event logs','fidelity gap not declared'],'budget':{'remote_hours_range':[2,4],'source_observer_and_generator_hours_range':[1,2],'analysis_and_fetch_hours_range':[1.5,2],'total_hours_range':[4.5,8],'basis':'v13 measured cap8 383s/batch and about7min/4 isolated builds; proposed bytes are 1.3076923 times the resource pilot; this is a budget, not a measured prediction'},'formal_168_status':'still disabled; no scope extension implied'})
states=[ROOT/'results'/f'ws30-v13-r2-{suffix}.json' for suffix in ('technical','lifecycle','pilot-c4','pilot-c8')]
started=[]
for p in states:
    d=read(p); assert not d['failures'] and not d['pending']
    started.extend(e['id'] for e in d['events'] if e['event']=='started')
assert len(started)==len(set(started))==46
metas=[read(ROOT/'results'/i/'metadata.json') for i in started]
assert all(m['status']=='SUCCEEDED' and m['git_commit']==plan['source_sha'] for m in metas)
write('ws30-v13-execution-audit-r1.json',{'source_sha':plan['source_sha'],'simulation_successes':46,'simulation_failures':0,'unique_started_ids':46,'start_counts':{i:started.count(i) for i in started},'states':{str(p.relative_to(ROOT)):sha(p) for p in states},'build_receipts_sha256':sha(ROOT/'results/ws30-v13-r2-build-receipts.jsonl'),'administrative_interruptions':[{'phase':'technical','cause':'sandbox SSH denial before remote admission','simulation_started':False},{'phase':'lifecycle','cause':'generated technical summary blocked clean-check before sync/build','simulation_started':False},{'phase':'pilot','cause':'generated lifecycle summary blocked clean-check before sync/build','simulation_started':False}],'local_exclude_paths':['/docs/research/evidence/ws30-v13-technical-r2.json','/docs/research/evidence/ws30-v13-lifecycle-r2.json','/docs/research/evidence/ws30-v13-pilot-r2.json'],'all_stage_raw_fetched_and_locally_audited':True,'current_global_host_state':'Not queried again in analysis; owned run metadata all terminal','formal_execution_enabled':plan['formal_execution_enabled'],'W5_execution_enabled':False})
print('Recorded seed, reference/source, execution audits and disabled W5 design.')
