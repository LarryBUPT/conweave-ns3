"""Build the raw-traceable v12 data package from completed local experiments only."""
import collections
import csv
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import subprocess
import sys

import numpy as np
import run_ws30_stage3 as runner

ROOT=runner.ROOT
EV=runner.EV
OUT=EV/'ws30-v12-r1'
ARMS=['E','H16','R16','Q16','C16','U16','Q12','M16']
HISTORY_ROOTS={'ws25':'ws25-first-paper','ws27':'ws27-guardhash-compare','ws28native':'ws28-classreserve-explanation','ws28ablation':'ws28-classreserve-explanation'}


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def save(name,data):
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def table(name,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/name).open('w',newline='',encoding='utf-8') as h:
        w=csv.DictWriter(h,fieldnames=keys);w.writeheader();w.writerows(rows)
def pct(v,p):
    s=sorted(v);i=(len(s)-1)*p/100;lo,hi=math.floor(i),math.ceil(i)
    return s[lo]+(s[hi]-s[lo])*(i-lo)


def d1_common_settings():
    current=subprocess.check_output(['git','show','1ef424749e3c551dd788d0a709bd8e21c7cc89c9:scripts/make_ws25_demand.py'],cwd=ROOT)
    previous=subprocess.check_output(['git','show','ce699dffe2845dc83e2171a1c309c6d96b96d2b3:scripts/make_ws25_demand.py'],cwd=ROOT)
    generator=hashlib.sha256(current).hexdigest();oldhash=hashlib.sha256(previous).hexdigest()
    audit=read(EV/'ws30-historical-raw-audit.json')['source_audit']['scripts/make_ws25_demand.py']
    assert oldhash==audit['old_sha256']==audit['new_sha256']
    expected=previous.decode().replace('def make(seed, out_dir):','def make(seed, out_dir, levels=LEVELS):').replace(
        '    for level in LEVELS:\n','    for level in levels:\n        if level not in LEVELS:\n            raise ValueError("unsupported background level: {}".format(level))\n')
    assert current.decode()==expected,'Generator changed beyond the audited output-level interface'
    return {'historical_generator_blob_sha256':oldhash,'new_generator_blob_sha256':generator,
        'generator_change':'new source adds selectable output levels plus validation only; RNG and demand construction unchanged',
        'topology':'topo_1280_400G_400G_OS1','bandwidth_gbps':400,
        'cc':'DCQCN','pfc':0,'irn':1,'buffer_mib':9,'ns3_seed':1,'netload_argument':10,'simul_time_argument_s':0.01,
        'load_interpretation':'explicit flow trace defines actual offered demand; netload=10 is not a measured 10% offered load',
        'event_order':'background rows precede MoE rows; port assignment and same-timestamp insertion order preserved'}


def apply_d1_settings(cohorts):
    settings=d1_common_settings()
    for r in cohorts:
        r.update(settings)
        blob=subprocess.check_output(['git','show',r['source_sha']+':scripts/make_ws25_demand.py'],cwd=ROOT)
        r['generator_blob_sha256']=hashlib.sha256(blob).hexdigest()
        assert r['generator_blob_sha256'] in (settings['historical_generator_blob_sha256'],settings['new_generator_blob_sha256'])
    return cohorts


INDEX={}
def native_drill_observation_audit(index):
    audited=[]
    for r in index:
        if r['scope']=='historical' and r['id'].endswith('-drill'):
            p=Path(r['local_directory'])/'logs/config.log';lines=p.read_text().splitlines()
            audited.append({'id':r['id'],'log_sha256':sha(p),'WS25_QP_rows':sum(l.startswith('WS25_QP ') for l in lines),
                'WS30_QP_rows':sum(l.startswith('WS30_QP ') for l in lines),
                'explicit_repeat_rows':sum('repeated_sends=' in l or 'retransmit_packets=' in l for l in lines)})
    assert len(audited)==48 and not sum(r['WS25_QP_rows']+r['WS30_QP_rows']+r['explicit_repeat_rows'] for r in audited)
    return {'verified_logs':len(audited),'rows':audited,'finding':'No independent per-QP recovery observer rows in these native logs; absence of rows is not zero recoveries.'}


def register(base,cell,role,scope):
    key=cell['id'];folder=base/'results'/key
    if key in INDEX:
        assert role not in INDEX[key]['roles']
        INDEX[key]['roles'].append(role);return INDEX[key]
    m=read(folder/'metadata.json');assert m['status']=='SUCCEEDED' and m['seed']==1
    if cell.get('source_sha'):assert m['git_commit']==cell['source_sha'],key
    raw=str(m['raw_directory']);fct=folder/'raw'/raw/(raw+'_out_fct.txt')
    fhash=sha(fct);assert fhash==cell['fct_sha256'],key
    trace=folder/'config/traffic_trace.txt';thash=sha(trace)
    assert thash==cell.get('trace_sha256',m['input_flow_sha256']),key
    topo=folder/'config/topology.txt';assert sha(topo)==m['topology_sha256']
    res=folder/'logs/resource-summary.json'
    INDEX[key]={'id':key,'scope':scope,'roles':[role],'status':'SUCCEEDED','source_sha':m['git_commit'],
        'local_directory':str(folder),'metadata_sha256':sha(folder/'metadata.json'),'config_sha256':sha(folder/'config/config.txt'),
        'trace_sha256':thash,'topology_sha256':sha(topo),'fct_sha256':fhash,'raw_fct_path':str(fct),
        'pid':m.get('pid'),'started_utc':m.get('started_utc'),'finished_utc':m.get('finished_utc'),
        'concurrency_cap':m.get('concurrency_cap'),'resource':read(res) if res.exists() else None}
    return INDEX[key]


def reconstruct(folder,condition):
    m=read(folder/'metadata.json');trace=folder/'config/traffic_trace.txt'
    expected={};sp=collections.defaultdict(lambda:10000);dp=collections.defaultdict(lambda:100)
    for l in trace.read_text().splitlines()[1:]:
        f=l.split();s,d,pg,size=map(int,f[:4]);k=(s,d,sp[s],dp[d],size);sp[s]+=1;dp[d]+=1
        assert k not in expected;expected[k]=(int(f[5]),int(Decimal(f[4])*10**9))
    raw=str(m['raw_directory']);path=folder/'raw'/raw/(raw+'_out_fct.txt');completed={}
    for l in path.read_text().splitlines():
        r=list(map(int,l.split()));k=tuple(r[:5]);assert k in expected and k not in completed
        assert abs(r[5]-expected[k][1])<=1;completed[k]=(r[6],r[5]+r[6])
    assert completed.keys()==expected.keys() and len(expected)==16576
    tags={}
    for t in (1,2):
        keys=[k for k in expected if expected[k][0]==t]
        origin=min(expected[k][1] for k in keys);assert origin==2000000000+(20000 if t==2 and condition=='lead20us' else 0)
        end=max(completed[k][1] for k in keys);v=[completed[k][0]/1000 for k in keys]
        tags[str(t)]={'flows':len(keys),'bytes':sum(k[4] for k in keys),'origin_ns':origin,
            'batch_us':(end-origin)/1000,'mean_us':statistics.mean(v),
            **{f'p{p}_us':pct(v,p) for p in (50,95,99)},'max_us':max(v),
            'tail_keys':[list(k) for k in keys if completed[k][1]==end]}
    return tags


def source_stat(s):
    return {'median_pct':s.get('median_change_pct',s.get('median_pct',s.get('median'))),
            'ci_low_pct':s['bootstrap_95pct'][0],'ci_high_pct':s['bootstrap_95pct'][1]}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    historical=read(EV/'ws30-historical-raw-audit.json')
    history=read(EV/'ws30-historical-baseline-export.json')
    mainanalysis=read(EV/'ws30-stage3-main-analysis-r1.json')
    leadanalysis=read(EV/'ws30-stage3-lead-analysis-r1.json')
    ablation=read(EV/'ws28-ablation-analysis.json')
    cells=[];new={};byid={}
    # Previous audits are retained; every source FCT/input is freshly hash-checked.
    historical_receipts={r['id']:r for r in historical['receipts']}
    for c in historical['cells']:
        r=register(ROOT.parent/HISTORY_ROOTS[c['group']],c,'historical_'+c['group'],'historical')
        assert r['metadata_sha256']==historical_receipts[c['id']]['metadata_sha256']
        assert r['config_sha256']==historical_receipts[c['id']]['config_sha256']
    for phase,condition in [('main','synchronous'),('lead','lead20us')]:
        data=read(EV/f'ws30-stage3-{phase}-results-r5.json')
        for r in data['rows']:
            register(ROOT,r,phase,'ws30_new')
            tags=reconstruct(ROOT/'results'/r['id'],condition)
            for t in ('1','2'):
                for k in ('batch_us','p50_us','p95_us','p99_us','max_us'):
                    assert math.isclose(tags[t][k],r['tags'][t][k],abs_tol=1e-9)
            seed=int(r['id'].split('-s')[-1].split('-')[0]);arm=r['arm']
            item={'id':r['id'],'seed':seed,'arm':arm,'condition':condition,'tags':tags,
                  'source_sha':r['source_sha'],'fct_sha256':r['fct_sha256'],'trace_sha256':r['trace_sha256']}
            new[(condition,seed,arm)]=item;cells.append(item);byid[r['id']]=r
    print('Raw reconstruction complete:',len(cells),flush=True)
    for filename,role in [('ws30-technical-results-recovered-r1.json','technical'),
        ('ws30-resource-results-recovered-r1.json','resource_pilot'),('ws30-bridge-results-recovered-r1.json','bridge'),
        ('ws30-stage3-correctness-combined-r1.json','composition_correctness'),
        ('ws30-stage3-composition-results-r5.json','composition')]:
        for r in read(EV/filename)['rows']:register(ROOT,r,role,'ws30_new')
    for c in read(EV/'ws28-tail-analysis.json')['analyzed_cells']:
        register(ROOT.parent/'ws28-classreserve-explanation',c,'tail_diagnostic','historical_diagnostic')
    # Historical FCT bridging independently ties the new source to both old cohorts.
    bridge=read(EV/'ws30-stage2-postrun-audit-r1.json')
    for c in bridge['bridge_rows']:
        assert INDEX[c['id']]['fct_sha256']==INDEX[c['historical_id']]['fct_sha256']
        assert INDEX[c['id']]['trace_sha256']==INDEX[c['historical_id']]['trace_sha256']

    metrics=[('moe_batch','2','batch_us'),('background_p99','1','p99_us')]
    points=[];estimates=[]
    bootstrap_rng=random.Random(20263003)
    common_draws=np.array([[bootstrap_rng.randrange(24) for _ in range(24)] for _ in range(10000)])
    def add(family,condition,contrast,seed,candidate_id,control_id,metric,value,unit='percent'):
        points.append(dict(family=family,condition=condition,contrast=contrast,seed=seed,
            metric=metric,value=value,unit=unit,candidate_id=candidate_id,control_id=control_id))
    def estimate(family,condition,contrast,metric,stat):
        selected=sorted((p for p in points if (p['family'],p['condition'],p['contrast'],p['metric'])==(family,condition,contrast,metric)),key=lambda p:p['seed'])
        v=[p['value'] for p in selected]
        assert len(v)==24 and math.isclose(stat['median_pct'],statistics.median(v),abs_tol=1e-10)
        ci=np.percentile(np.median(np.array(v)[common_draws],axis=1),[2.5,97.5])
        estimates.append({'family':family,'condition':condition,'contrast':contrast,'metric':metric,'n':24,
            'median_pct':stat['median_pct'],'ci_low_pct':float(ci[0]),'ci_high_pct':float(ci[1]),
            'archived_ci_low_pct':stat['ci_low_pct'],'archived_ci_high_pct':stat['ci_high_pct'],
            'lower_n':sum(x<0 for x in v),'equal_n':sum(x==0 for x in v),'higher_n':sum(x>0 for x in v),
            'minimum_pct':min(v),'maximum_pct':max(v),'over_3pct_n':sum(x>3 for x in v) if metric=='background_p99' else None})
    # F1: four independent demand cohorts, never pooled.
    cohort_specs=[('old','ws25','classreserve'),('main_history','ws27','classreserve'),('factorial','ws28ablation','cr-a1-b1')]
    for cohort,group,mode in cohort_specs:
        selected=[c for c in historical['cells'] if c['group']==group and c['mode']==mode]
        controls={c['seed']:c for c in historical['cells'] if c['group']==group and c['mode']=='fecmp'}
        for c in selected:
            for metric,key in [('moe_batch','moe_change_pct'),('background_p99','bg_change_pct')]:
                add('F1',cohort,'Full/E',c['seed'],c['id'],controls[c['seed']]['id'],metric,c[key])
        for metric in ('moe_batch','background_p99'):
            if cohort=='factorial':stat=source_stat(ablation['mode_effects']['cr-a1-b1'][metric])
            else:
                s=next(s for s in history['summary'] if s['cohort']==('old' if cohort=='old' else 'main') and s['mode']=='classreserve')
                key='moe' if metric=='moe_batch' else 'bg'
                stat={'median_pct':s[key+'_change_pct_median'],'ci_low_pct':s[key+'_change_pct_nominal_95pct'][0],'ci_high_pct':s[key+'_change_pct_nominal_95pct'][1]}
            estimate('F1',cohort,'Full/E',metric,stat)
    for arm in ARMS:
        for seed in mainanalysis['seeds']:
            c,e=new['synchronous',seed,arm],new['synchronous',seed,'E']
            for metric,tag,key in metrics:
                value=100*(c['tags'][tag][key]/e['tags'][tag][key]-1)
                add('F2','synchronous',arm+'/E',seed,c['id'],e['id'],metric,value)
                if arm=='C16':add('F1','new','Full/E',seed,c['id'],e['id'],metric,value)
        for metric in ('moe_batch','background_p99'):
            stat={'median_pct':0.,'ci_low_pct':0.,'ci_high_pct':0.} if arm=='E' else source_stat(next(x for x in mainanalysis['relative_to_E'] if x['arm']==arm)['vs_E_'+metric])
            estimate('F2','synchronous',arm+'/E',metric,stat)
            if arm=='C16':estimate('F1','new','Full/E',metric,stat)
    for contrast in mainanalysis['comparisons']:
        ca,co=contrast['candidate'],contrast['control']
        for seed in mainanalysis['seeds']:
            c,t=new['synchronous',seed,ca],new['synchronous',seed,co]
            for metric,tag,key in metrics:
                value=100*(c['tags'][tag][key]/t['tags'][tag][key]-1)
                assert math.isclose(value,contrast[metric]['per_seed_pct'][str(seed)],abs_tol=1e-10)
                add('F3','synchronous',contrast['contrast'],seed,c['id'],t['id'],metric,value)
        for metric in ('moe_batch','background_p99'):estimate('F3','synchronous',contrast['contrast'],metric,source_stat(contrast[metric]))
    for contrast in leadanalysis['comparisons']:
        cond=contrast['condition'];ca,co=contrast['candidate'],contrast['control']
        for seed in mainanalysis['seeds']:
            c,t=new[cond,seed,ca],new[cond,seed,co]
            for metric,tag,key in metrics:
                value=100*(c['tags'][tag][key]/t['tags'][tag][key]-1)
                assert math.isclose(value,contrast[metric]['per_seed'][str(seed)],abs_tol=1e-10)
                add('F4',cond,contrast['contrast'],seed,c['id'],t['id'],metric,value)
        for metric in ('moe_batch','background_p99'):estimate('F4',cond,contrast['contrast'],metric,source_stat(contrast[metric]))
    interactions=[]
    for r in leadanalysis['condition_interactions']:
        ca,co=r['contrast'].split('/')
        for metric in ('moe_batch','background_p99'):
            s=r[metric]['log_ratio_difference_x100']
            for seed,value in s['per_seed'].items():
                seed=int(seed)
                interactions.append({'contrast':r['contrast'],'metric':metric,'seed':seed,'log_ratio_difference_x100':value,
                    'sync_candidate_id':new['synchronous',seed,ca]['id'],'sync_control_id':new['synchronous',seed,co]['id'],
                    'lead_candidate_id':new['lead20us',seed,ca]['id'],'lead_control_id':new['lead20us',seed,co]['id']})
    table('figure-points.csv',points);table('figure-estimates.csv',estimates);table('timing-interactions.csv',interactions)
    risks=[]
    for stat in estimates:
        if stat['family'] not in ('F1','F2','F4') or stat['metric']!='background_p99':continue
        bg=[p for p in points if (p['family'],p['condition'],p['contrast'],p['metric'])==(stat['family'],stat['condition'],stat['contrast'],'background_p99')]
        moe={p['seed']:p for p in points if (p['family'],p['condition'],p['contrast'],p['metric'])==(stat['family'],stat['condition'],stat['contrast'],'moe_batch')}
        worst=max(bg,key=lambda p:p['value']);worst_moe=max(moe.values(),key=lambda p:p['value'])
        risks.append({'family':stat['family'],'condition':stat['condition'],'contrast':stat['contrast'],'n':24,
            'background_over3_n':sum(p['value']>3 for p in bg),'both_metrics_lower_n':sum(p['value']<0 and moe[p['seed']]['value']<0 for p in bg),
            'both_metrics_higher_n':sum(p['value']>0 and moe[p['seed']]['value']>0 for p in bg),
            'worst_background_seed':worst['seed'],'worst_background_pct':worst['value'],'worst_background_candidate_id':worst['candidate_id'],
            'worst_background_control_id':worst['control_id'],'worst_moe_seed':worst_moe['seed'],'worst_moe_pct':worst_moe['value'],
            'worst_moe_candidate_id':worst_moe['candidate_id'],'worst_moe_control_id':worst_moe['control_id']})
    table('per-input-risk-summary.csv',risks)
    timing_stats=[]
    for r in leadanalysis['condition_interactions']:
        for metric in ('moe_batch','background_p99'):
            selected=sorted((z for z in interactions if z['contrast']==r['contrast'] and z['metric']==metric),key=lambda z:z['seed'])
            v=np.array([z['log_ratio_difference_x100'] for z in selected]);ci=np.percentile(np.median(v[common_draws],axis=1),[2.5,97.5])
            timing_stats.append({'contrast':r['contrast'],'metric':metric,'median':float(np.median(v)),
                'ci_low':float(ci[0]),'ci_high':float(ci[1]),'unit':'100 ln ratio of ratios; lead minus sync'})
    save('timing-interaction-estimates.json',timing_stats)

    # Full factorial legacy A/B effects, plus separately named log interaction.
    factorial=[];factor_est=[];factor_arms=[];factor_arm_stats=[]
    # Use a single advancing RNG; seed is fixed before any outcome lookup.
    rng=random.Random(20263003);logdraws=np.array([[rng.randrange(24) for _ in range(24)] for _ in range(10000)])
    for c in ablation['paired_seeds']:
        source_ids=json.dumps({mode:v['id'] for mode,v in c['modes'].items()},sort_keys=True)
        for mode,v in c['modes'].items():
            for metric,key in [('moe_batch','moe_batch_vs_ecmp_pct'),('background_p99','background_p99_vs_ecmp_pct')]:
                factor_arms.append({'seed':c['seed'],'mode':mode,'metric':metric,'value':v[key],'unit':'percent',
                    'candidate_id':v['id'],'control_id':c['modes']['fecmp']['id'],'trace_sha256':c['trace_sha256']})
        for contrast,vals in c['contrasts'].items():
            for metric in ('moe_batch','background_p99'):
                factorial.append({'seed':c['seed'],'contrast':contrast,'metric':metric,'value':vals[metric+'_pct'],
                    'unit':'percentage points' if contrast=='A_by_B_interaction' else 'percent','source_ids':source_ids,'trace_sha256':c['trace_sha256']})
        for metric,key in [('moe_batch','moe_batch_us'),('background_p99','background_p99_us')]:
            m=c['modes'];value=100*math.log((m['cr-a1-b1'][key]/m['cr-a0-b1'][key])/(m['cr-a1-b0'][key]/m['cr-a0-b0'][key]))
            factorial.append({'seed':c['seed'],'contrast':'A_by_B_log_interaction','metric':metric,'value':value,
                'unit':'100 ln ratio of ratios','source_ids':source_ids,'trace_sha256':c['trace_sha256']})
    for mode in ablation['mode_effects']:
        for metric in ('moe_batch','background_p99'):
            v=np.array([r['value'] for r in sorted((r for r in factor_arms if r['mode']==mode and r['metric']==metric),key=lambda r:r['seed'])])
            ci=np.percentile(np.median(v[common_draws],axis=1),[2.5,97.5])
            factor_arm_stats.append({'mode':mode,'metric':metric,'median_pct':float(np.median(v)),'ci_low_pct':float(ci[0]),'ci_high_pct':float(ci[1]),
                'lower_n':int(sum(v<0)),'higher_n':int(sum(v>0)),'over_3pct_n':int(sum(v>3)) if metric=='background_p99' else None})
    table('factorial-arm-points.csv',factor_arms);table('factorial-arm-estimates.csv',factor_arm_stats)
    for contrast,s in ablation['component_effects'].items():
        for metric in ('moe_batch','background_p99'):
            v=np.array([z['value'] for z in sorted((z for z in factorial if z['contrast']==contrast and z['metric']==metric),key=lambda z:z['seed'])])
            stat=source_stat(s[metric+'_pct']);assert math.isclose(stat['median_pct'],float(np.median(v)),abs_tol=1e-10)
            ci=np.percentile(np.median(v[common_draws],axis=1),[2.5,97.5])
            factor_est.append({'contrast':contrast,'metric':metric,'median_pct':stat['median_pct'],
                'ci_low_pct':float(ci[0]),'ci_high_pct':float(ci[1]),'archived_ci_low_pct':stat['ci_low_pct'],'archived_ci_high_pct':stat['ci_high_pct'],
                'unit':'percentage points' if contrast=='A_by_B_interaction' else 'percent'})
    for metric in ('moe_batch','background_p99'):
        a=np.array([r['value'] for r in factorial if r['contrast']=='A_by_B_log_interaction' and r['metric']==metric]);ci=np.percentile(np.median(a[logdraws],axis=1),[2.5,97.5])
        factor_est.append({'contrast':'A_by_B_log_interaction','metric':metric,'median_pct':float(np.median(a)),'ci_low_pct':float(ci[0]),'ci_high_pct':float(ci[1]),'unit':'100 ln ratio of ratios'})
    table('factorial-points.csv',factorial);table('factorial-estimates.csv',factor_est)

    # Per-seed explanatory metrics and all tail identities; no flow-level replication.
    extra=[];tailchanges=[]
    for c in cells:
        r={k:c[k] for k in ('condition','seed','arm','id','source_sha','trace_sha256','fct_sha256')}
        for tag,prefix in [('1','background'),('2','moe')]:
            for k,v in c['tags'][tag].items():r[prefix+'_'+k]=json.dumps(v) if isinstance(v,list) else v
        extra.append(r)
    table('cell-metrics-and-tails.csv',extra)
    for contrast in mainanalysis['comparisons']:
        ca,co=contrast['candidate'],contrast['control']
        for seed in mainanalysis['seeds']:
            c,t=new['synchronous',seed,ca],new['synchronous',seed,co]
            tailchanges.append({'contrast':contrast['contrast'],'seed':seed,'candidate_id':c['id'],'control_id':t['id'],
                'tail_changed':c['tags']['2']['tail_keys']!=t['tags']['2']['tail_keys'],
                'candidate_tail':json.dumps(c['tags']['2']['tail_keys']),'control_tail':json.dumps(t['tags']['2']['tail_keys'])})
    table('tail-identity-contrasts.csv',tailchanges)
    secondary=[]
    for condition,arms in [('synchronous',ARMS),('lead20us',['E','Q16','C16'])]:
        for arm in arms:
            c=[r for r in cells if r['condition']==condition and r['arm']==arm]
            secondary.append({'condition':condition,'arm':arm,'n_demands':24,'source_ids':json.dumps([r['id'] for r in c]),'batch_across_demands_p95_us':pct([r['tags']['2']['batch_us'] for r in c],95),
                **{tag+'_'+key+'_across_demands_median_us':statistics.median(r['tags'][num][key] for r in c) for tag,num in [('moe','2'),('background','1')] for key in ('batch_us','p50_us','p95_us','p99_us','max_us')}})
    table('secondary-metrics.csv',secondary)

    # D3 actual new-arm path/queue/transport counters and choice denominators.
    actions=[];choices=[]
    for phase in ('main','lead','composition'):
        rs=read(EV/f'ws30-stage3-{phase}-results-r5.json')['rows']
        for arm in dict.fromkeys(r['arm'] for r in rs):
            sub=[r for r in rs if r['arm']==arm];o=sub[0]['observation']
            actions.append({'phase':phase,'arm':arm,'cells':len(sub),**{section+'_'+k:sum(r['observation'][section][k] for r in sub) for section in ('path','queue','transport_sums') for k in o[section]}})
            for tag in (1,2):
                selected=[next(z for z in r['observation']['choices'] if z['tag']==tag) for r in sub]
                totals={k:sum(z[k] for z in selected) for k in selected[0] if k!='tag'};den=totals['events']-totals['same']
                choices.append({'phase':phase,'arm':arm,'tag':tag,**totals,'distinct_candidate_events':den,
                    **{k+'_pct_of_distinct':100*totals[k]/den if den else None for k in ('background_nonzero','a_disagrees','near','composition','empty')}})
    table('D3-new-arm-actions.csv',actions);table('D3-choice-exposure.csv',choices)
    save('D3-native-dynamic.json',{'branch_summary':history['branch_summary'],'branch_receipts':history['branch_receipts'],
        'drill_retransmit_packets':None,'drill_rx_gap':None,'missing_reason':'Historical native logs do not carry independent DRILL recovery counters; U16 is a distinct intervention and cannot fill these fields.'})
    save('native-drill-observation-audit.json',native_drill_observation_audit(list(INDEX.values())))
    native_summary=[]
    for s in history['summary']:
        sub=sorted((r for r in history['cells'] if r['cohort']==s['cohort'] and r['mode']==s['mode']),key=lambda r:r['seed'])
        out={'cohort':s['cohort'],'method':s['mode'],'n':24}
        for name,key in [('batch_us','moe_batch_us'),('background_p99_us','background_p99_us'),('batch_change_pct','moe_change_pct'),('background_change_pct','bg_change_pct')]:
            v=np.array([r[key] for r in sub]);ci=np.percentile(np.median(v[common_draws],axis=1),[2.5,97.5])
            out.update({name+'_median':float(np.median(v)),name+'_ci_low':float(ci[0]),name+'_ci_high':float(ci[1])})
        out.update({'moe_improved':s['moe_improved'],'background_gt3':s['background_gt3']});native_summary.append(out)
    table('D2-native-baselines.csv',native_summary);table('D2-native-points.csv',history['cells'])
    # All fixture queue events are source data, including overlapping trajectories.
    queues=[]
    for c in runner.read(runner.PLAN)['composition']:
        log=ROOT/'results'/c['id']/'logs/config.log'
        for line in log.read_text().splitlines():
            if line.startswith('WS30_COMPOSITION_QUEUE '):
                queues.append({'id':c['id'],'swap':c['swap'],'continuing':c['continuing'],'arm':c['arm'],**runner.stage.kv(line)})
    table('F5-queue-events.csv',queues)
    table('F5-metrics.csv',list(csv.DictReader((EV/'ws30-stage3-composition-metrics-r1.csv').open())))
    # Preserve 0/64/128/192 per-input risks, especially the small-n P99 outlier.
    load=[r for r in read(EV/'ws27-confirm-analysis.json')['paired_changes'] if r['mode']=='classreserve']
    for c in load:
        for role,key in [('load_control','baseline_id'),('load_candidate','candidate_id')]:
            keyid=c[key]
            if keyid in INDEX:
                if role not in INDEX[keyid]['roles']:INDEX[keyid]['roles'].append(role)
            else:
                f=ROOT.parent/'ws27-guardhash-compare'/'results'/keyid;m=read(f/'metadata.json');raw=str(m['raw_directory']);p=f/'raw'/raw/(raw+'_out_fct.txt')
                register(ROOT.parent/'ws27-guardhash-compare',{'id':keyid,'fct_sha256':sha(p)},role,'historical_load')
    table('load-per-input-risks.csv',load)
    load64=min((r for r in load if r['background']==64),key=lambda r:r['background_p99_change_pct'])
    outlier=[];outlier_summary=[]
    for label,key in [('E','baseline_id'),('C16','candidate_id')]:
        exp=load64[key];directory=Path(INDEX[exp]['local_directory']);expected={};sp=collections.defaultdict(lambda:10000);dp=collections.defaultdict(lambda:100)
        for line in (directory/'config/traffic_trace.txt').read_text().splitlines()[1:]:
            f=line.split();s,d,pg,size=map(int,f[:4]);k=(s,d,sp[s],dp[d],size);sp[s]+=1;dp[d]+=1;expected[k]=int(f[5])
        for line in Path(INDEX[exp]['raw_fct_path']).read_text().splitlines():
            f=list(map(int,line.split()));k=tuple(f[:5])
            if expected[k]==1:outlier.append({'arm':label,'id':exp,'src':k[0],'dst':k[1],'sport':k[2],'dport':k[3],'size':k[4],'fct_ns':f[6]})
        v=sorted(r['fct_ns']/1000 for r in outlier if r['arm']==label);assert len(v)==64
        outlier_summary.append({'arm':label,'id':exp,'n':64,'p95_us':pct(v,95),'p99_us':pct(v,99),'max_us':max(v),'largest_four_us':v[-4:]})
    table('load64-outlier-background-flows.csv',outlier)
    save('load64-outlier-audit.json',{'seed':load64['seed'],'rows':outlier_summary,'p99_definition':'0.63 times the 63rd order statistic plus 0.37 times the 64th; linear interpolation, not the maximum',
        'paired_p99_change_pct':100*(outlier_summary[1]['p99_us']/outlier_summary[0]['p99_us']-1),'scope':'one revealed demand; no causal attribution from FCT order statistics alone'})
    cohort_table=[]
    for name,group,mode,gate in [('old','ws25','classreserve','old joint gate: both median decreases at least 5%, each >=17/24 improved; original NO-GO retained'),
        ('main_history','ws27','classreserve','background paired-P99-change median <3%; not per-input protection'),
        ('factorial','ws28ablation','cr-a1-b1','same engineering median gate, independent A/B cohort')]:
        selected=[r for r in historical['cells'] if r['group']==group and r['mode']==mode]
        cohort_table.append({'cohort':name,'purpose':'historical performance or factorial replication','n_demands':24,
            'seed_min':min(r['seed'] for r in selected),'seed_max':max(r['seed'] for r in selected),
            'source_sha':INDEX[selected[0]['id']]['source_sha'],'topology_sha256':INDEX[selected[0]['id']]['topology_sha256'],
            'moe_qps':16384,'moe_payload_bytes_each':8192,'background_qps':192,'background_payload_bytes_each':8388608,
            'total_payload_bytes':1744830464,'moe_origin_ns':2000000000,'background_origin_ns':2000000000,'gate':gate})
    cohort_table.append({'cohort':'new','purpose':'eight-arm prespecified attribution','n_demands':24,'seed_min':20263021,'seed_max':20263044,
        'source_sha':mainanalysis['source_sha'],'topology_sha256':mainanalysis['topology_sha256'],'moe_qps':16384,'moe_payload_bytes_each':8192,
        'background_qps':192,'background_payload_bytes_each':8388608,'total_payload_bytes':1744830464,'moe_origin_ns':2000000000,
        'background_origin_ns':2000000000,'gate':'background paired-P99-change median <3%; lead20us reuses these demands with tag2 origin 2000020000'})
    table('D1-cohorts.csv',apply_d1_settings(cohort_table))
    # Every new success ID is listed once, with overlap roles retained.
    success=[r for r in INDEX.values() if r['scope']=='ws30_new'];assert len(success)==438,len(success)
    failed=[]
    for r in read(EV/'ws30-technical-results-recovered-r1.json')['failed_cells_preserved']:
        failed.append({'id':r['failed_id'],'status':'FAILED_PRESERVED','replacement_id':r['replacement_id'],'reason':r['cause']})
    for key in read(EV/'ws30-stage3-correctness-combined-r1.json')['preserved_failed_ids']:
        failed.append({'id':key,'status':'FAILED_PRESERVED','replacement_id':'see accepted cprep5/cprep6 technical plan','reason':'earlier composition fixture attempts; failure receipts retained'})
    failed.append({'id':'20261024-210000-ws30-cprep-s0-c0-c16','status':'BUILT_UNRUN_PRESERVED','replacement_id':'','reason':'earlier build retained, not a formal result'})
    save('D4-experiments.json',{'unique_ws30_successes':438,'technical_bridge_overlap':4,'new_formal_effect_cells':276,
        'historical_indexed':sum(r['scope'].startswith('historical') for r in INDEX.values()),'successes':list(INDEX.values()),'failed_or_unrun':failed})
    table('D4-experiments.csv',[{k:(json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v) for k,v in r.items()} for r in INDEX.values()]+failed)
    save('reconstructed-cells.json',cells)
    save('package.json',{'scope':'WS-30 final cross-stage v12 evidence package','new_remote_experiments':0,'frozen_stage3_plan_sha256':sha(runner.PLAN),
        'raw_hash_checked_ids':len(INDEX),'raw_reconstructed_new_cells':264,'raw_reconstructed_fct_rows':264*16576,
        'ws30_unique_successes':438,'formal_main_lead_composition':[192,72,12],'historical_raw_audit_cells':456,
        'bridge_fct_matches':96,'independent_demand_cohorts':{'old':24,'main_history':24,'factorial':24,'new':24},
        'lead_is_correlated_with_new':True,'composition_is_four_controlled_conditions':True,
        'ci':'Nominal two-sided 95% demand-level bootstrap percentile intervals, 10000 draws, random.Random seed 20263003, common draw-index matrix and increasing demand seed order. Archived endpoints retained in separate fields; medians independently matched. Repeated contrasts share identical final intervals. No significance labels or pooled estimate.',
        'additional_log_interaction_bootstrap':{'draws':10000,'seed':20263003},
        'background_3pct':'prespecified median engineering constraint, not individual protection, production SLO or statistical noninferiority',
        'load64_worst':load64,'inputs':{n:sha(EV/n) for n in ['ws30-historical-raw-audit.json','ws30-historical-baseline-export.json','ws30-stage2-postrun-audit-r1.json','ws30-stage3-main-results-r5.json','ws30-stage3-main-analysis-r1.json','ws30-stage3-lead-results-r5.json','ws30-stage3-lead-analysis-r1.json','ws30-stage3-composition-results-r5.json','ws28-ablation-analysis.json','ws28-tail-analysis.json']}})
    print(json.dumps({'raw_hash_checked_ids':len(INDEX),'new_successes':len(success),'points':len(points),'estimates':len(estimates),'queue_events':len(queues),'load64_worst':load64}),flush=True)


if __name__=='__main__':main()
