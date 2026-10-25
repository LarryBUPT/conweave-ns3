"""Cross-check exported figure points against accepted raw-derived cell values."""
import collections
import csv
import json
import math
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'docs/research/evidence'
DATA=EV/'ws30-v12-r1'


def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def table(name):return list(csv.DictReader((DATA/name).open(encoding='utf-8')))
def close(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-12,abs_tol=1e-9),(a,b)


def main():
    cohorts=table('D1-cohorts.csv');assert len(cohorts)==4
    generators={r['cohort']:r['generator_blob_sha256'] for r in cohorts}
    assert generators['old']==generators['main_history'] and generators['factorial']==generators['new'] and generators['old']!=generators['new']
    assert all((r['ns3_seed'],r['pfc'],r['irn'],r['bandwidth_gbps'])==('1','0','1','400') for r in cohorts)
    indexed=read(DATA/'D4-experiments.json');idx={r['id']:r for r in indexed['successes']}
    assert len(idx)==1050 and sum(r['scope']=='ws30_new' for r in idx.values())==438
    assert len(indexed['failed_or_unrun'])==7
    cellvalues={}
    for r in read(EV/'ws30-historical-raw-audit.json')['cells']:
        cellvalues[r['id']]={'moe_batch':r['moe_batch_us'],'background_p99':r['background_p99_us']}
    new=read(DATA/'reconstructed-cells.json');assert len(new)==264
    for r in new:
        cellvalues[r['id']]={'moe_batch':r['tags']['2']['batch_us'],'background_p99':r['tags']['1']['p99_us']}
        assert r['tags']['2']['flows']==16384 and r['tags']['1']['flows']==192
    points=table('figure-points.csv');assert len(points)==1296
    assert collections.Counter(r['family'] for r in points)=={'F1':192,'F2':384,'F3':432,'F4':288}
    groups=collections.defaultdict(list)
    for r in points:
        ca,co,metric=r['candidate_id'],r['control_id'],r['metric'];assert ca in idx and co in idx
        close(r['value'],100*(cellvalues[ca][metric]/cellvalues[co][metric]-1))
        groups[r['family'],r['condition'],r['contrast'],metric].append(r)
    estimates=table('figure-estimates.csv');assert len(estimates)==len(groups)==54
    seen={}
    for e in estimates:
        sub=sorted(groups[e['family'],e['condition'],e['contrast'],e['metric']],key=lambda r:int(r['seed']))
        assert len(sub)==24 and len({r['seed'] for r in sub})==24
        close(e['median_pct'],statistics.median(float(r['value']) for r in sub))
        key=(e['metric'],tuple((r['candidate_id'],r['control_id']) for r in sub))
        values=[e[k] for k in ('median_pct','ci_low_pct','ci_high_pct')]
        if key in seen:
            for a,b in zip(values,seen[key]):close(a,b)
        seen[key]=values
    for e in table('factorial-arm-estimates.csv'):
        if e['mode']!='cr-a1-b1':continue
        f=next(r for r in estimates if r['family']=='F1' and r['condition']=='factorial' and r['metric']==e['metric'])
        for key in ('median_pct','ci_low_pct','ci_high_pct'):close(e[key],f[key])
    fact=table('factorial-arm-points.csv');assert len(fact)==240
    for r in fact:close(r['value'],100*(cellvalues[r['candidate_id']][r['metric']]/cellvalues[r['control_id']][r['metric']]-1))
    comp=table('factorial-points.csv');assert len(comp)==288
    for r in comp:
        ids=json.loads(r['source_ids']);v={m:cellvalues[i][r['metric']] for m,i in ids.items()};c=r['contrast']
        pair={'A_when_B0':('cr-a1-b0','cr-a0-b0'),'A_when_B1':('cr-a1-b1','cr-a0-b1'),
              'B_when_A0':('cr-a0-b1','cr-a0-b0'),'B_when_A1':('cr-a1-b1','cr-a1-b0')}
        if c in pair:a,b=pair[c];expected=100*(v[a]/v[b]-1)
        elif c=='A_by_B_interaction':expected=100*((v['cr-a1-b1']/v['cr-a0-b1']-1)-(v['cr-a1-b0']/v['cr-a0-b0']-1))
        else:expected=100*math.log((v['cr-a1-b1']/v['cr-a0-b1'])/(v['cr-a1-b0']/v['cr-a0-b0']))
        close(r['value'],expected)
    timing=table('timing-interactions.csv');assert len(timing)==144
    for r in timing:
        v=lambda k:cellvalues[r[k]][r['metric']]
        close(r['log_ratio_difference_x100'],100*math.log((v('lead_candidate_id')/v('lead_control_id'))/(v('sync_candidate_id')/v('sync_control_id'))))
    queue=table('F5-queue-events.csv');assert len(queue)==6528
    for exp in {r['id'] for r in queue}:
        ledger={2:[0,0],3:[0,0]}
        for r in queue:
            if r['id']!=exp:continue
            p,tag,n=int(r['port']),int(r['tag']),int(r['bytes'])*(1 if int(r['enqueue']) else -1)
            ledger[p][0]+=n
            if tag==1:ledger[p][1]+=n
            assert ledger[p]==[int(r['total']),int(r['background'])] and min(ledger[p])>=0
        assert ledger=={2:[0,0],3:[0,0]}
    reviews=read(DATA/'review-acceptance.json');assert len(reviews)==34 and len({(r['reviewer'],r['item']) for r in reviews})==34
    result={'status':'PASS','raw_values_source':'accepted historical cell audit and independently reconstructed new cells',
        'indexed_ids':1050,'new_successes':438,'figure_points_checked':1296,'figure_estimates_checked':54,
        'factorial_arm_points_checked':240,'factorial_component_points_checked':288,'timing_interaction_points_checked':144,
        'queue_events_replayed':6528,'review_items':34,'duplicate_contrast_intervals_consistent':True,
        'scope':'point arithmetic, denominators, units/IDs, per-seed medians, repeated intervals and queue conservation; no new simulation or significance test'}
    (DATA/'validation.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
