"""Local-only analysis for frozen fresh-QP and sustained-workload inputs.
No experiment execution or remote access. Missing/failed inputs remain explicit.
"""
import argparse
import collections
import csv
from decimal import Decimal
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import re
import statistics as st
import subprocess

import run_ws30_v14 as execution
from verify_ws30_v14_raw import kv

ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'docs/research/evidence'
PLAN=EV/'ws30-v14-disabled-contract-r2.json'
CONTRACT=EV/'ws30-v13-analysis-contract-r1.json'
DISPLAY={'E':'ECMP','Q12':'Two-choice queue pinning','R12':'Two-choice random pinning','U12':'Two-choice packet routing','D':'DRILL','conga':'CONGA','letflow':'LetFlow','conweave':'ConWeave'}
QUANTILES=(0,.01,.1,.25,.5,.75,.9,.95,.99,.999,1)
COUNTERS=('rx_gap','rx_below_expected','fd_feedback_frames','fd_without_sack','sack_feedback','cnp_feedback','retransmit_packets','retransmit_bytes','timeout')

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def quant(values,p):
    s=sorted(values);require(bool(s),'Empty quantile');x=(len(s)-1)*p;i=int(x)
    return s[i]+(s[min(i+1,len(s)-1)]-s[i])*(x-i)
def write_json(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_csv(p,rows,fields):
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def fingerprint(keys):return hashlib.sha256(json.dumps(sorted(keys),separators=(',',':')).encode()).hexdigest()

def build_contract():
    plan=read(PLAN); targets=[]
    for c in plan['formal_disabled']:
        group='fresh-pairs' if c['role']=='formal-disabled' else ('historical-A' if c['demand_seed']<20262700 else 'historical-B')
        targets.append(dict(c,cohort=group,condition='synchronous',folder='results/'+c['id']))
    for c in plan['W5']:
        condition='background-lead' if 'lead20us' in c['trace'] else 'concurrent'
        targets.append(dict(c,cohort='sustained-pilot',condition=condition,folder='results/'+c['id']))
    exported=read(EV/'ws30-historical-baseline-export.json')['cells']
    ledger={r['id']:r for r in read(EV/'ws30-v12-r1/D4-experiments.json')['successes']}
    anchors=[]
    for c in targets:
        if not c['cohort'].startswith('historical'):continue
        for mode,arm in (('fecmp','E'),('drill','D')):
            old=next(r for r in exported if r['seed']==c['demand_seed'] and r['mode']==mode)
            locator=ledger[old['id']]
            folder=Path(locator['local_directory'].replace('\\\\','\\')).resolve()
            require(folder.is_relative_to(ROOT.parents[1]),'Historical locator escaped paper workspace')
            anchors.append({'id':old['id'],'source_sha':locator['source_sha'],'arm':arm,'mode':mode,
                'trace':c['trace'],'trace_sha256':c['trace_sha256'],'topology':c['topology'],'topology_sha256':c['topology_sha256'],
                'input_flows':c['input_flows'],'observe':0,'lifecycle':0,'simulation_seed':1,'demand_seed':c['demand_seed'],
                'cohort':c['cohort'],'condition':c['condition'],'folder':str(folder),'expected_fct_sha256':old['fct_sha256'],
                'expected_metadata_sha256':locator['metadata_sha256'],'expected_config_sha256':locator['config_sha256'],
                'purpose':'historical performance anchor; not a new observation or new independent sample'})
    return {'version':1,'execution_enabled':False,'paper_target':'v13','plan_sha256':sha(PLAN),
      'reference_sha256':{f:sha(EV/f) for f in ('ws30-historical-baseline-export.json','ws30-v12-r1/D4-experiments.json')},
      'display_names':DISPLAY,'target_cells':targets,'historical_anchors':anchors,'qualification_cells':plan['ConWeave_observation_controls'],
      'units':{'fresh-pairs':'24 already revealed independent demand seeds; supplemental validation, not blinded confirmation',
        'historical-A':'24 historical demand seeds; DRILL observation replay against historical ECMP',
        'historical-B':'24 separate historical demand seeds; never pooled with other cohorts',
        'sustained-pilot':'2 independent demand seeds; timing conditions and 8 rounds are repeated measures'},
      'contrasts':{'fresh-pairs':[['Q12','E'],['R12','E'],['U12','E'],['D','E'],['R12','Q12'],['U12','Q12'],['D','Q12']],
        'historical-A':[['D','E']],'historical-B':[['D','E']],
        'sustained-pilot':[[a,'E'] for a in ('Q12','R12','U12','D','conga','letflow','conweave')]+[['R12','Q12'],['U12','Q12'],['D','Q12'],['conweave','Q12']]},
      'estimand':'Within-demand 100*(candidate/reference-1); demand median; never ratio of pooled means or pooled flow inference',
      'bootstrap':{'draws':10000,'seed':20263003,'interval':[.025,.975],'unit':'demand seed, identical resampling indexes for both endpoints and all contrasts within cohort',
        'enabled_for_complete_cohorts_only':True,'pilot_CI':False,'interpretation':'Nominal unadjusted percentile intervals; no p-values, significance stars or automatic pass/fail'},
      'topk':[1,4,16,64,256],'topk_selection':'ECMP FCT-ranked fixed message identities within each demand/round; deterministic identity tie-break; all max ties retained separately in batch-tail metadata',
      'missing_policy':'Record every expected cell and pair; no zero filling, timeout substitution, completion-only ranking or complete-case inferential summaries',
      'required_figures':['paired two-endpoint scatter','per-demand distributions of identity-paired flow changes','original/replacement batch-tail decomposition','state and recovery costs'],
      'qualifications':'Sustained results await both ConWeave off/on FCT pairs; historical recovery/performance join awaits all 48 historical DRILL FCT hashes matching originals',
      'snapshot_only':True}

def trace_records(path):
    lines=path.read_text(encoding='utf-8').splitlines();require(int(lines[0])==len(lines)-1,'Trace count mismatch')
    sp=collections.defaultdict(lambda:10000);dp=collections.defaultdict(lambda:100);records={}
    for i,line in enumerate(lines[1:]):
        a=line.split();s,d,pg,size=map(int,a[:4]);origin=int(Decimal(a[4])*10**9);tag=int(a[5]) if len(a)>5 else 0
        key=(s,d,sp[s],dp[d],size,origin);sp[s]+=1;dp[d]+=1
        require(key not in records,'Duplicate demand identity')
        records[key]={'tag':tag,'pg':pg,'row':i,'origin_ns':origin,'payload_bytes':size}
    return records

def parse_raw(c,strict_new=False,partial=False):
    folder=Path(c['folder']);folder=folder if folder.is_absolute() else ROOT/folder
    m=read(folder/'metadata.json');require(m['git_commit']==c['source_sha'],'Source SHA mismatch')
    require(m['algorithm']==c['mode'],'Algorithm mismatch')
    trace=folder/'config/traffic_trace.txt';topo=folder/'config/topology.txt'
    if 'expected_metadata_sha256' in c:
        require(sha(folder/'metadata.json')==c['expected_metadata_sha256'] and sha(folder/'config/config.txt')==c['expected_config_sha256'],'Historical provenance changed')
    require(sha(trace)==c['trace_sha256'] and sha(topo)==c['topology_sha256'],'Snapshot input hash mismatch')
    require(m.get('seed')==1,'Simulation seed mismatch')
    records=trace_records(trace);require(len(records)==c['input_flows'],'Expected flow count mismatch')
    raw=str(m.get('raw_directory',''));require(raw.isdigit(),'Missing raw directory')
    fct=folder/'raw'/raw/(raw+'_out_fct.txt'); observed={}
    for line in fct.read_text().splitlines():
        a=list(map(int,line.split()));require(len(a)>=8 and a[6]>0,'Invalid FCT record')
        hits=[tuple(a[:5])+(a[5]+delta,) for delta in (-1,0,1) if tuple(a[:5])+(a[5]+delta,) in records]
        require(len(hits)==1 and hits[0] not in observed,'Unmatched/duplicate completion identity')
        k=hits[0];observed[k]=dict(records[k],fct_ns=a[6],actual_start_ns=a[5],end_ns=a[5]+a[6])
    payload=sum(r['payload_bytes'] for r in records.values());donebytes=sum(r['payload_bytes'] for r in observed.values())
    audit={'expected_rows':len(records),'completed_rows':len(observed),'expected_payload_bytes':payload,'completed_payload_bytes':donebytes,
      'completion_fraction':len(observed)/len(records),'identity_sha256':fingerprint([tuple(k)+(r['tag'],r['pg']) for k,r in records.items()]),
      'fct_sha256':sha(fct),'trace_sha256':sha(trace),'topology_sha256':sha(topo),'metadata_sha256':sha(folder/'metadata.json'),
      'config_sha256':sha(folder/'config/config.txt'),'log_sha256':sha(folder/'logs/config.log') if (folder/'logs/config.log').exists() else None,
      'missing_identity_count':len(records)-len(observed)}
    if not partial:
        require(observed.keys()==records.keys() and payload==donebytes,'Incomplete identity/byte conservation')
        if 'expected_fct_sha256' in c:require(audit['fct_sha256']==c['expected_fct_sha256'],'Historical anchor FCT changed')
        if strict_new:execution.verify_common(c)
    return records,observed,audit,folder

def cell_status(c):
    folder=Path(c.get('folder','results/'+c['id']));folder=folder if folder.is_absolute() else ROOT/folder
    base={k:c.get(k) for k in ('id','cohort','condition','demand_seed','arm','source_sha','trace_sha256')}
    if not folder.exists():return dict(base,status='MISSING',reason='local result directory absent')
    if not (folder/'metadata.json').exists():return dict(base,status='LOCAL_PARTIAL',reason='metadata absent')
    try:
        m=read(folder/'metadata.json');status=m.get('status','UNKNOWN')
        if status!='SUCCEEDED':
            out=dict(base,status=status,reason='not a successful terminal cell')
            try:out['partial_conservation']=parse_raw(c,partial=True)[2]
            except (OSError,ValueError,KeyError) as error:out['partial_audit_unavailable']=str(error)
            return out
        audit=parse_raw(c,strict_new=True)[2]
        return dict(base,status='VERIFIED',reason='',**audit)
    except Exception as error:return dict(base,status='INVALID',reason=type(error).__name__+': '+str(error))

def observations(c,folder):
    path=folder/'logs/config.log'
    if not path.exists():return {'availability':'log unavailable','transport':None,'path':None,'state':None,'ConWeave':None}
    qps=[];paths=[];state=[];events=collections.Counter();ages=collections.defaultdict(list);cwbytes=0;peakaux=0;native={};flags=collections.Counter()
    for line in path.open(encoding='utf-8',errors='replace'):
        if line.startswith('WS30_QP '):qps.append(kv(line))
        elif line.startswith('WS30_PATH '):paths.append(kv(line))
        elif line.startswith('WS30V13_STATE '):state.append(kv(line))
        elif line.startswith('WS30_CW '):
            r=kv(line);events[r['event']]+=1;cwbytes+=len(line.encode('utf-8'));peakaux=max(peakaux,r.get('aux',0) if r['event']=='rx_buffer' else 0)
            if r['event']=='tx':flags[str(r['flag'])]+=1
            if r.get('age_ns',-1)>=0:ages[r['event']].append(r['age_ns'])
        else:
            match=re.match(r'Number of (Rerouting|OoO enqueued pkts|VOQ Flush From History):\s*(\d+)',line.strip())
            if match:native[match[1]]=int(match[2])
    transport=None
    if qps:
        transport={str(t):{key:sum(r[key] for r in qps if r['tag']==t) for key in COUNTERS} for t in sorted({r['tag'] for r in qps})}
    return {'availability':'observed' if qps else 'observation absent; counters unknown','transport':transport,'path':paths[0] if len(paths)==1 else None,
      'state':{'per_switch':state,'entry_count_not_bytes':True} if state else None,
      'ConWeave':{'events':dict(events),'tx_flags':dict(flags),'native_counts':native,'log_bytes':cwbytes,'max_observed_single_VOQ_packets':peakaux,'not_physical_MMU_occupancy':True,'age_unavailable_count':{k:n-len(ages[k]) for k,n in events.items()},'ages_ns':{k:{'n':len(v),'p50':quant(v,.5),'p99':quant(v,.99),'max':max(v)} for k,v in ages.items() if v},
      'age_semantics':'reply_rx=matched request RTT; rx_mark/rx_buffer=source timestamp age; flush=first buffer to release; unavailable ages excluded and not zero-filled'} if events else None}

def metrics(c,flows):
    result={};front_origins=sorted({r['origin_ns'] for r in flows.values() if r['tag']==2})
    if c['cohort']=='sustained-pilot':require(len(front_origins)==8,'Sustained trace does not have eight rounds')
    origin_to_round={t:i for i,t in enumerate(front_origins)}
    for tag in sorted({r['tag'] for r in flows.values()}):
        rows=[r for r in flows.values() if r['tag']==tag];origin=min(r['origin_ns'] for r in rows)
        result[str(tag)]={'rows':len(rows),'payload_bytes':sum(r['payload_bytes'] for r in rows),'origin_ns':origin,
            'fct_p50_ns':quant([r['fct_ns'] for r in rows],.5),'fct_p95_ns':quant([r['fct_ns'] for r in rows],.95),'fct_p99_ns':quant([r['fct_ns'] for r in rows],.99),'fct_max_ns':max(r['fct_ns'] for r in rows),
            'span_from_original_demand_ns':max(r['end_ns'] for r in rows)-origin}
    rounds=[]
    for origin in front_origins:
        subset=[r for r in flows.values() if r['tag']==2 and r['origin_ns']==origin]
        rounds.append({'round':origin_to_round[origin],'origin_ns':origin,'rows':len(subset),'payload_bytes':sum(r['payload_bytes'] for r in subset),'batch_ns':max(r['end_ns'] for r in subset)-origin})
    if c['cohort']=='sustained-pilot':require(all(r['rows']==2048 and r['payload_bytes']==16777216 for r in rounds),'Wrong sustained round identities/bytes')
    return {'classes':result,'rounds':rounds,'foreground_span_ns':result['2']['span_from_original_demand_ns'],'background_p99_ns':result['1']['fct_p99_ns']}

def pair_rows(c,ref,cf,rf,ecmp,flow_writer):
    require(cf.keys()==rf.keys(),'Pair demand identities differ')
    require(all((cf[k]['tag'],cf[k]['pg'])==(rf[k]['tag'],rf[k]['pg']) for k in cf),'Pair labels/priority differ')
    cm,rm=metrics(c,cf),metrics(ref,rf);base={'cohort':c['cohort'],'condition':c['condition'],'demand_seed':c['demand_seed'],'candidate':c['arm'],'reference':ref['arm'],'candidate_id':c['id'],'reference_id':ref['id']}
    summary=dict(base,status='PAIRED',foreground_change_pct=100*(cm['foreground_span_ns']/rm['foreground_span_ns']-1),background_p99_change_pct=100*(cm['background_p99_ns']/rm['background_p99_ns']-1),candidate_foreground_ns=cm['foreground_span_ns'],reference_foreground_ns=rm['foreground_span_ns'],candidate_background_p99_ns=cm['background_p99_ns'],reference_background_p99_ns=rm['background_p99_ns'])
    tails=[];tops=[];distributions=[];backgrounds=[];roundpairs=[]
    frontorigins=sorted({r['origin_ns'] for r in cf.values() if r['tag']==2})
    selections=[('all',None)]+[(str(i),t) for i,t in enumerate(frontorigins)] if len(frontorigins)>1 else [('all',None)]
    for round_label,origin in selections:
        keys=[k for k in cf if cf[k]['tag']==2 and (origin is None or cf[k]['origin_ns']==origin)]
        t0=min(cf[k]['origin_ns'] for k in keys);a={k:cf[k]['end_ns']-t0 for k in keys};b={k:rf[k]['end_ns']-t0 for k in keys}
        oldmax,newmax=max(b.values()),max(a.values())
        oldties=sorted(k for k in keys if b[k]==oldmax);newties=sorted(k for k in keys if a[k]==newmax)
        old,new=oldties[0],newties[0];delta=a[new]-b[old];oldchange=a[old]-b[old];replacement=a[new]-a[old]
        require(delta==oldchange+replacement,'Tail identity decomposition failed')
        tails.append(dict(base,round=round_label,old_tail_identity=json.dumps(old),new_tail_identity=json.dumps(new),old_tied_identities=json.dumps(oldties),new_tied_identities=json.dumps(newties),tail_identity_changed=old!=new,batch_delta_ns=delta,old_tail_delta_ns=oldchange,replacement_gap_ns=replacement,old_tail_reference_ns=b[old],old_tail_candidate_ns=a[old],new_tail_reference_ns=b[new],new_tail_candidate_ns=a[new]))
        if round_label!='all':roundpairs.append(dict(base,round=round_label,batch_change_pct=100*(max(a.values())/max(b.values())-1)))
        if ecmp:
            require(ecmp.keys()==cf.keys(),'ECMP selector identities mismatch')
            ranked=sorted(keys,key=lambda k:(-ecmp[k]['fct_ns'],k))
            for n in (1,4,16,64,256):
                selected=ranked[:min(n,len(ranked))]
                tops.append(dict(base,round=round_label,requested_k=n,actual_k=len(selected),selection='ECMP-FCT-ranked fixed identities',mean_delta_ns=st.mean(cf[k]['fct_ns']-rf[k]['fct_ns'] for k in selected),median_change_pct=st.median(100*(cf[k]['fct_ns']/rf[k]['fct_ns']-1) for k in selected)))
    for tag in (1,2):
        keys=[k for k in cf if cf[k]['tag']==tag]
        delta=[cf[k]['fct_ns']-rf[k]['fct_ns'] for k in keys];pct=[100*(cf[k]['fct_ns']/rf[k]['fct_ns']-1) for k in keys]
        for q in QUANTILES:distributions.append(dict(base,tag=tag,quantile=q,paired_delta_ns=quant(delta,q),paired_change_pct=quant(pct,q),candidate_marginal_fct_ns=quant([cf[k]['fct_ns'] for k in keys],q),reference_marginal_fct_ns=quant([rf[k]['fct_ns'] for k in keys],q),n_flows=len(keys)))
        for k in keys:
            flow_writer.writerow(dict(base,tag=tag,identity=json.dumps(k),candidate_fct_ns=cf[k]['fct_ns'],reference_fct_ns=rf[k]['fct_ns'],delta_ns=cf[k]['fct_ns']-rf[k]['fct_ns'],change_pct=100*(cf[k]['fct_ns']/rf[k]['fct_ns']-1)))
            if tag==1:backgrounds.append(dict(base,identity=json.dumps(k),candidate_fct_ns=cf[k]['fct_ns'],reference_fct_ns=rf[k]['fct_ns']))
    return summary,tails,tops,distributions,backgrounds,roundpairs

def summary_statistics(contract,pairs):
    groups=collections.defaultdict(list)
    for row in pairs:groups[(row['cohort'],row['condition'],row['candidate'],row['reference'])].append(row)
    output=[]
    for (cohort,condition,candidate,ref),rows in sorted(groups.items()):
        valid=[r for r in rows if r['status']=='PAIRED'];n=2 if cohort=='sustained-pilot' else 24
        bootstrap=None
        if len(valid)==n and n>=24:
            rng=random.Random(contract['bootstrap']['seed']);bootstrap=[[rng.randrange(n) for _ in range(n)] for _ in range(contract['bootstrap']['draws'])]
        for metric in ('foreground_change_pct','background_p99_change_pct'):
            values=[r[metric] for r in valid];ci=None
            if bootstrap:ci=[quant([st.median(values[i] for i in draw) for draw in bootstrap],q) for q in (.025,.975)]
            output.append({'cohort':cohort,'condition':condition,'candidate':candidate,'reference':ref,'metric':metric,'expected_n':n,'paired_n':len(valid),'complete':len(valid)==n,'median':st.median(values) if values else None,'range':[min(values),max(values)] if values else None,'ci95_nominal_unadjusted':ci,'inference':'descriptive pilot only' if n==2 else ('nominal demand bootstrap' if ci else 'incomplete; no inferential interval')})
    return output

BASE_FIELDS=['cohort','condition','demand_seed','candidate','reference','candidate_id','reference_id']
def analyze(contract,out):
    targets=contract['target_cells'];status=[cell_status(c) for c in targets];byid={r['id']:r for r in status}
    quals=[cell_status(dict(c,folder='results/'+c['id'])) for c in contract['qualification_cells']]
    qualgood=all(r['status']=='VERIFIED' for r in quals)
    if qualgood:
        for name in ('cw-tech','cw-long'):
            hashes=[r['fct_sha256'] for r in quals if name+'-' in r['id']];qualgood=qualgood and len(set(hashes))==1
    history_good=all(byid[c['id']]['status']=='VERIFIED' and byid[c['id']]['fct_sha256']==next(a['expected_fct_sha256'] for a in contract['historical_anchors'] if a['arm']=='D' and a['demand_seed']==c['demand_seed']) for c in targets if c['cohort'].startswith('historical'))
    units=collections.defaultdict(list)
    for c in targets:units[(c['cohort'],c['condition'],c['demand_seed'])].append(c)
    pairs=[];tails=[];tops=[];dist=[];background=[];rounds=[];cost=[];sources=[];cellmetrics=[]
    flowfields=BASE_FIELDS+['tag','identity','candidate_fct_ns','reference_fct_ns','delta_ns','change_pct']
    with gzip.open(out/'paired-flows.csv.gz','wt',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=flowfields);writer.writeheader()
        for (cohort,condition,seed),cells in sorted(units.items()):
            loaded={}
            for c in cells:
                if byid[c['id']]['status']!='VERIFIED':continue
                _,flows,audit,folder=parse_raw(c);loaded[c['arm']]=(c,flows)
                sources.append(dict(id=c['id'],source_sha=c['source_sha'],cohort=cohort,condition=condition,demand_seed=seed,arm=c['arm'],**audit))
                cm=metrics(c,flows);cellmetrics.append(dict(id=c['id'],cohort=cohort,condition=condition,demand_seed=seed,arm=c['arm'],**cm))
                obs=observations(c,folder)
                obs['payload_bytes_by_tag']={tag:r['payload_bytes'] for tag,r in cm['classes'].items()}
                cost.append(dict(id=c['id'],cohort=cohort,condition=condition,demand_seed=seed,arm=c['arm'],**obs))
            gate='READY'
            if cohort.startswith('historical'):
                if not history_good:gate='HISTORICAL_FCT_QUALIFICATION_PENDING'
                # Only open existing anchors when the new replay is available.
                if loaded:
                    for anchor in contract['historical_anchors']:
                        if anchor['demand_seed']==seed and anchor['arm']=='E':
                            try:
                                _,flows,audit,folder=parse_raw(anchor);loaded['E']=(anchor,flows);sources.append(dict(id=anchor['id'],source_sha=anchor['source_sha'],purpose='historical anchor',**audit))
                            except Exception as error:gate='HISTORICAL_ANCHOR_INVALID: '+str(error)
            if cohort=='sustained-pilot' and not qualgood:gate='OBSERVER_QUALIFICATION_PENDING'
            for candidate,ref in contract['contrasts'][cohort]:
                expected_ref=next((a['id'] for a in contract['historical_anchors'] if a['demand_seed']==seed and a['arm']==ref),None) if cohort.startswith('historical') else None
                base={'cohort':cohort,'condition':condition,'demand_seed':seed,'candidate':candidate,'reference':ref,'candidate_id':next((c['id'] for c in cells if c['arm']==candidate),None),'reference_id':loaded[ref][0]['id'] if ref in loaded else next((c['id'] for c in cells if c['arm']==ref),expected_ref)}
                if gate!='READY' or candidate not in loaded or ref not in loaded:
                    pairs.append(dict(base,status=gate if gate!='READY' else 'PAIR_MEMBER_MISSING_OR_INVALID'));continue
                try:
                    c,cf=loaded[candidate];r,rf=loaded[ref]
                    result=pair_rows(c,r,cf,rf,loaded.get('E',(None,None))[1],writer)
                    pairs.append(result[0]);tails.extend(result[1]);tops.extend(result[2]);dist.extend(result[3]);background.extend(result[4]);rounds.extend(result[5])
                except Exception as error:pairs.append(dict(base,status='PAIR_INVALID',reason=str(error)))
    actual_sources={r['id']:r for r in sources};source_map=[]
    for c in targets+contract['historical_anchors']+contract['qualification_cells']:
        row={k:c.get(k) for k in ('id','source_sha','cohort','condition','demand_seed','arm','mode','trace','trace_sha256','topology','topology_sha256','folder')}
        row['display_name']=DISPLAY.get(c['arm'],c['arm'])
        row['availability']=byid[c['id']]['status'] if c['id'] in byid else 'DECLARED_REFERENCE_OR_QUALIFICATION'
        row.update(actual_sources.get(c['id'],{}));source_map.append(row)
    write_json(out/'cell-status.json',status);write_json(out/'qualification-status.json',quals);write_json(out/'source-map.json',source_map)
    write_json(out/'cell-metrics.json',cellmetrics);write_json(out/'costs.json',cost);write_json(out/'pair-status.json',pairs)
    transport_rows=[];state_rows=[];cw_rows=[]
    for record in cost:
        base={k:record[k] for k in ('id','cohort','condition','demand_seed','arm')}
        for tag,values in (record['transport'] or {}).items():
            payload=record['payload_bytes_by_tag'][tag]
            transport_rows.append(dict(base,tag=tag,payload_bytes=payload,retransmission_payload_pct=100*values['retransmit_bytes']/payload,**values))
        if record['state']:
            for values in record['state']['per_switch']:state_rows.append(dict(base,**values))
        if record['ConWeave']:
            for event,count in record['ConWeave']['events'].items():
                age=record['ConWeave']['ages_ns'].get(event,{})
                cw_rows.append(dict(base,event=event,event_count=count,age_available_n=age.get('n',0),age_unavailable_n=record['ConWeave']['age_unavailable_count'][event],age_p50_ns=age.get('p50'),age_p99_ns=age.get('p99'),age_max_ns=age.get('max')))
    write_csv(out/'recovery-costs.csv',transport_rows,['id','cohort','condition','demand_seed','arm','tag','payload_bytes','retransmission_payload_pct']+list(COUNTERS))
    write_csv(out/'cache-state-entries.csv',state_rows,['id','cohort','condition','demand_seed','arm','switch','entries','peak','hits','misses'])
    write_csv(out/'conweave-event-ages.csv',cw_rows,['id','cohort','condition','demand_seed','arm','event','event_count','age_available_n','age_unavailable_n','age_p50_ns','age_p99_ns','age_max_ns'])
    write_json(out/'summary.json',{'contract_sha256':sha(CONTRACT),'expected_new_performance_cells':200,'status_counts':dict(collections.Counter(r['status'] for r in status)),'ConWeave_qualification_pass':qualgood,'historical_all48_FCT_match':history_good,'statistics':summary_statistics(contract,pairs),'simulation_launches_by_this_script':0,'paper_release_ready':False})
    write_csv(out/'paired-endpoints.csv',pairs,BASE_FIELDS+['status','foreground_change_pct','background_p99_change_pct','candidate_foreground_ns','reference_foreground_ns','candidate_background_p99_ns','reference_background_p99_ns'])
    write_csv(out/'tail-decomposition.csv',tails,BASE_FIELDS+['round','old_tail_identity','new_tail_identity','old_tied_identities','new_tied_identities','tail_identity_changed','batch_delta_ns','old_tail_delta_ns','replacement_gap_ns','old_tail_reference_ns','old_tail_candidate_ns','new_tail_reference_ns','new_tail_candidate_ns'])
    write_csv(out/'fixed-ecmp-topk.csv',tops,BASE_FIELDS+['round','requested_k','actual_k','selection','mean_delta_ns','median_change_pct'])
    write_csv(out/'per-input-distributions.csv',dist,BASE_FIELDS+['tag','quantile','paired_delta_ns','paired_change_pct','candidate_marginal_fct_ns','reference_marginal_fct_ns','n_flows'])
    write_csv(out/'all-background-pairs.csv',background,BASE_FIELDS+['identity','candidate_fct_ns','reference_fct_ns'])
    write_csv(out/'round-pairs.csv',rounds,BASE_FIELDS+['round','batch_change_pct'])
    timing=[]
    for candidate,reference in contract['contrasts']['sustained-pilot']:
        for seed in (20263101,20263102):
            members={r['condition']:r for r in pairs if r['cohort']=='sustained-pilot' and r['demand_seed']==seed and r['candidate']==candidate and r['reference']==reference and r['status']=='PAIRED'}
            row={'demand_seed':seed,'candidate':candidate,'reference':reference,'status':'PAIRED_TIMINGS' if set(members)=={'concurrent','background-lead'} else 'TIMING_MEMBER_MISSING'}
            if row['status']=='PAIRED_TIMINGS':
                for metric in ('foreground_change_pct','background_p99_change_pct'):
                    value=math.log1p(members['background-lead'][metric]/100)-math.log1p(members['concurrent'][metric]/100)
                    row[metric+'_log_ratio_difference']=value;row[metric+'_relative_factor_pct']=100*math.expm1(value)
            timing.append(row)
    write_json(out/'timing-interactions.json',{'unit':'same demand seed across timings; descriptive n=2, no CI','rows':timing})
    write_json(out/'run-provenance.json',{'script_sha256':sha(Path(__file__)),'contract_sha256':sha(CONTRACT),'raw_only':True,'snapshot_warning':'Missing rows reflect local snapshot, never inferred remote absence; rerun to a new directory after fetch.'})
    return dict(collections.Counter(r['status'] for r in status))

def smoke(out):
    old=read(EV/'ws30-v13-plan-r2.json');expected=read(EV/'ws30-v13-engineering-raw-analysis-r2.json');reports=[];parsed={}
    for suffix in ('t02-e-o2','t04-q12-o2','t06-r12-o2','t08-u12-o2','t10-d-o2'):
        c=next(c for c in old['technical'] if c['id'].endswith(suffix));c=dict(c,folder='results/'+c['id'],cohort='PARSER_ONLY_NOT_A_STATISTICAL_COHORT')
        _,flows,audit,folder=parse_raw(c);observed=metrics(c,flows);prior=next(r for r in expected['rows'] if r['id']==c['id'])
        require(observed['foreground_span_ns']==prior['metrics']['2']['batch_from_earliest_demand_ns'],'Foreground parser regression')
        require(abs(observed['background_p99_ns']-prior['metrics']['1']['p99_ns'])<1e-6,'Background parser regression')
        counters=observations(c,folder)['transport']
        require(all(counters[tag][field]==value for tag,fields in prior['transport'].items() for field,value in fields.items()),'Recovery counter parser regression')
        parsed[c['arm']]=(dict(c,condition='parser-only',demand_seed=None),flows)
        reports.append({'id':c['id'],'parse_only':True,'rows':audit['completed_rows'],'identity_and_bytes_match':True,'metrics_match_frozen_raw_analysis':True,'not_an_independent_formal_sample':True})
    class Sink:
        def writerow(self,row):pass
    candidate,cf=parsed['Q12'];reference,rf=parsed['E']
    pair=pair_rows(candidate,reference,cf,rf,rf,Sink())
    require(pair[1][0]['batch_delta_ns']==pair[1][0]['old_tail_delta_ns']+pair[1][0]['replacement_gap_ns'],'Real raw tail-identity arithmetic failed')
    for seed in (20263101,20263102):
        identities=[]
        for condition in ('concurrent','lead20us'):
            trace=trace_records(ROOT/('config/ws30w5_seed%d_%s.txt'%(seed,condition)));origins=sorted({r['origin_ns'] for r in trace.values() if r['tag']==2})
            require(len(origins)==8 and all(sum(r['tag']==2 and r['origin_ns']==t for r in trace.values())==2048 for t in origins),'W5 round definition invalid')
            identities.append(sorted(k[:5]+(r['tag'],r['pg'],origins.index(r['origin_ns']) if r['tag']==2 else -1) for k,r in trace.items()))
            require(sum(r['payload_bytes'] for r in trace.values())==2281701376,'W5 byte definition invalid')
        require(identities[0]==identities[1],'W5 timing conditions changed demand identities')
    write_json(out/'parser-validation.json',{'existing_raw_validation_only':reports,'tail_identity_arithmetic_validated_on_existing_raw_only':True,'W5_trace_structure_only':{'traces':4,'rounds':8,'messages_each':2048,'identity_and_bytes_across_timings_equal':True},'formal_results_generated':False,'figures_generated':0})
    return {'parser_cells':5,'formal_results_generated':False,'figures_generated':0}

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=('freeze','analyze','smoke'));p.add_argument('--out',type=Path);p.add_argument('--session-file',type=Path);args=p.parse_args()
    if args.command=='freeze':
        data=build_contract()
        if CONTRACT.exists():require(read(CONTRACT)==data,'Preserve changed analysis contract revision')
        else:write_json(CONTRACT,data)
        print('Frozen local analysis contract; no execution path.');return
    execution.require_model(args.session_file,'analysis')
    require(args.out is not None,'New output directory required');out=args.out.resolve();require(out.is_relative_to(ROOT),'Output must remain in this worktree');out.mkdir(parents=True,exist_ok=False)
    contract=read(CONTRACT);require(contract['plan_sha256']==sha(PLAN),'Frozen experiment plan changed')
    require(all(sha(EV/f)==digest for f,digest in contract['reference_sha256'].items()),'Historical reference index changed')
    print(json.dumps(smoke(out) if args.command=='smoke' else analyze(contract,out)))
if __name__=='__main__':main()
