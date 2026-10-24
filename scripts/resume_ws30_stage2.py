"""Resume only unverified WS-30 checks; preserve all accepted r5 cells and failures."""
import argparse
import datetime
import json
import subprocess
from pathlib import Path
import run_ws30_stage2 as s

ROOT=s.ROOT;EV=s.EV
OLD_PLAN=EV/'ws30-execution-plan-r5.json'
PLAN=EV/'ws30-stage2-recovery-plan-r1.json'
SUMMARY=ROOT/'results/ws30-stage2-recovery-summary-r1.json'
BASE_SUMMARY=ROOT/'results/ws30-stage2-summary-r5.json'
INPUT_REPAIR_SOURCE='6df0a9db9d01e1fd1b4c725b31525983425f4fac'
TECH_RESULT=EV/'ws30-technical-results-recovered-r1.json'
PILOT_RESULT=EV/'ws30-resource-results-recovered-r1.json'
BRIDGE_PLAN=EV/'ws30-bridge-resolved-recovered-r1.json'
BRIDGE_RESULT=EV/'ws30-bridge-results-recovered-r1.json'

def runtime_equivalence():
    paths=['src','scratch','run.py','scripts/remote_worker.py','wscript']
    subprocess.run(['git','-C',str(ROOT),'diff','--quiet',s.SOURCE,INPUT_REPAIR_SOURCE,'--']+paths,check=True)
    return {'core_source':s.SOURCE,'input_repair_source':INPUT_REPAIR_SOURCE,
            'identical_paths':paths,'meaning':'Only fixture/generator/artifact changes; simulator runtime sources unchanged'}

def makeplan():
    old=json.loads(OLD_PLAN.read_text());inputs=json.loads((EV/'ws30-inputs-v3.json').read_text())
    fixture=next(x for x in inputs['technical'] if x['trace']=='ws30_technical168_lead_v2.txt')
    technical=[dict(c,source_sha=s.SOURCE) for c in old['technical']]
    superseded=[]
    for index in [14,15,16]:
        prev=technical[index]
        replacement=dict(prev,**fixture,source_sha=INPUT_REPAIR_SOURCE,
                         id='20261024-010000-ws30-leadfix-'+prev['arm'].lower()+'-o2',
                         role='technical-lead-repair',replaces_failed_id=prev['id'])
        technical[index]=replacement
        superseded.append({'failed_id':prev['id'],'replacement_id':replacement['id'],
                           'cause':'Auxiliary fallback rows were earlier than the preceding delayed MoE rows'})
    assert len(technical)==32 and len({c['id'] for c in technical})==32
    return {'kind':'WS-30 stage-2 recovery; no new-effect matrix execution',
            'core_source_sha':s.SOURCE,'input_repair_source_sha':INPUT_REPAIR_SOURCE,
            'runtime_source_equivalence':runtime_equivalence(),
            'prior_plan_sha256':s.sha(OLD_PLAN),'new_input_manifest_sha256':s.sha(EV/'ws30-inputs-v3.json'),
            'technical':technical,
            'pilot':[dict(c,source_sha=s.SOURCE) for c in old['pilot']],
            'bridge':[dict(c,source_sha=s.SOURCE) for c in old['bridge']],
            'accepted_ids_to_reuse':[c['id'] for c in technical[:14]],
            'failed_cells_preserved':superseded,
            'formal_effect_matrix_execution_enabled':False,
            'long_run_model_switch':'Must be actually performed and confirmed by supervising chat before launching remaining long run'}

def load_summary():
    if SUMMARY.exists():return json.loads(SUMMARY.read_text())
    old=json.loads(BASE_SUMMARY.read_text())
    plan=makeplan()
    assert len(old['rows'])==14
    for c in plan['technical'][:14]:assert s.verify(c)==old['rows'][c['id']],c['id']
    data={'source_core':s.SOURCE,'blocks':[], 'rows':dict(old['rows']),
          'reused_accepted_ids':list(old['rows'])}
    SUMMARY.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return data

def wire():
    s.SUMMARY=SUMMARY
    s.RECEIPTS=ROOT/'results/ws30-stage2-recovery-receipts-r1.jsonl'

def collect(cells,summary):
    # A local result is verified and reused, never launched again.
    for c in cells:
        if (ROOT/'results'/c['id']).exists():summary['rows'][c['id']]=s.verify(c)
    return [c for c in cells if c['id'] not in summary['rows']]

def run_groups(cells,cap,summary):
    pending=collect(cells,summary)
    for offset in range(0,len(pending),cap):
        block=pending[offset:offset+cap]
        s.runblock(block,cap,summary)

def rows_for(cells,summary):
    return [dict(summary['rows'][c['id']],source_sha=c['source_sha'],trace_sha256=c['trace_sha256']) for c in cells]

def technical(plan,summary):
    cells=plan['technical'];pending=collect(cells,summary)
    repair=[c for c in pending if c['source_sha']==INPUT_REPAIR_SOURCE]
    legacy=[c for c in pending if c['source_sha']==s.SOURCE]
    run_groups(repair,4,summary);run_groups(legacy,4,summary)
    assert all(c['id'] in summary['rows'] for c in cells)
    pairs=[]
    for arm in ['E','Q16','C16','U16']:
        subset=[c for c in cells if c['arm']==arm and c['trace']=='ws30_technical168.txt']
        hashes={summary['rows'][c['id']]['fct_sha256'] for c in subset};assert len(hashes)==1
        pairs.append({'arm':arm,'ids':[c['id'] for c in subset],'fct_sha256':next(iter(hashes))})
    def row(arm):return summary['rows'][next(c['id'] for c in cells if c['arm']==arm and c['trace']=='ws30_technical168.txt')]
    assert row('E')['fct_sha256']==row('H12')['fct_sha256']
    assert row('C16')['fct_sha256']==row('cr-a1-b1')['fct_sha256']
    five=[c for c in cells if c['trace']=='ws30_fivecol4.txt']
    assert len({summary['rows'][c['id']]['fct_sha256'] for c in five})==1
    s.frozen(TECH_RESULT,{'kind':plan['kind'],'verified_cells':32,'runtime_source_equivalence':runtime_equivalence(),
                         'failed_cells_preserved':plan['failed_cells_preserved'],'observation_pairs':pairs,
                         'rows':rows_for(cells,summary)})

def pilot(plan,summary):
    assert TECH_RESULT.exists(),'Complete technical gate required'
    path=EV/'ws30-technical-paths-recovered-r1.json'
    assert path.exists(),'Independent packet-path gate required'
    stages=[];baseline={}
    for cap in [4,8,12]:
        cells=[c for c in plan['pilot'] if c['cap']==cap]
        run_groups(cells,cap,summary)
        rows=[summary['rows'][c['id']] for c in cells]
        for arm in ['Q16','C16','U16','R16']:
            hs={r['fct_sha256'] for r in rows if r['arm']==arm};assert len(hs)==1
            value=next(iter(hs))
            if arm in baseline:assert baseline[arm]==value,'Concurrent replay differs'
            baseline[arm]=value
        metas=[json.loads((ROOT/'results'/c['id']/'metadata.json').read_text()) for c in cells]
        t=lambda x:datetime.datetime.fromisoformat(x.replace('Z','+00:00'))
        wall=(max(t(m['finished_utc']) for m in metas)-min(t(m['started_utc']) for m in metas)).total_seconds()
        stages.append({'cap':cap,'cells':len(rows),'simulation_wall_seconds':wall,
                       'throughput_cells_per_hour':cap*3600/wall,
                       'peak_load_1m':max(r['resource']['peak_load_1m'] for r in rows),
                       'minimum_mem_available_gib':min(r['resource']['minimum_mem_available_gib'] for r in rows),
                       'minimum_free_gib':min(r['resource']['minimum_free_gib'] for r in rows),
                       'maximum_tree_rss_mib':max(r['resource']['peak_tree_rss_mib'] for r in rows)})
    selected=12
    for i in range(1,len(stages)):
        if stages[i]['throughput_cells_per_hour']<=stages[i-1]['throughput_cells_per_hour']*1.05:
            selected=stages[i-1]['cap'];break
    s.frozen(PILOT_RESULT,{'source_sha':s.SOURCE,'verified_cells':24,'selected_cap':selected,'stages':stages,
                          'fct_sha256_by_arm':baseline,'rows':rows_for(plan['pilot'],summary)})

def bridge(plan,summary):
    assert PILOT_RESULT.exists(),'Resource gate required before full historical bridge'
    cap=json.loads(PILOT_RESULT.read_text())['selected_cap'];cells=[]
    for c in plan['bridge']:
        if c['id'] in summary['rows']:cells.append(c);continue
        new=dict(c)
        # Historical preflight IDs belong to the frozen r5 plan. Give every
        # newly launched bridge cell a fresh ID tied to the selected cap so
        # the execution plan agrees with the startup-readiness receipt.
        if c['role']=='historical-bridge':
            new.update(id=f'20261024-020000-ws30-bridge-c{cap:02d}-s{c["seed"]}-{c["arm"].lower()}',
                       cap=cap,replaces_unrun_id=c['id'])
        cells.append(new)
    s.frozen(BRIDGE_PLAN,{'source_sha':s.SOURCE,'cap':cap,'cells':cells})
    run_groups([c for c in cells if c['id'] not in summary['rows']],cap,summary)
    assert len(cells)==96 and all(c['id'] in summary['rows'] for c in cells)
    s.frozen(BRIDGE_RESULT,{'source_sha':s.SOURCE,'verified_cells':96,'all_fct_match_historical':True,
                           'rows':rows_for(cells,summary)})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['plan','technical','pilot','bridge','snapshot'])
    args=parser.parse_args();plan=makeplan();s.frozen(PLAN,plan)
    if args.phase=='plan':
        print(json.dumps({'plan_sha256':s.sha(PLAN),'remaining_technical':18,'pilot':24,
                          'bridge_total':96,'bridge_remaining_after_technical_prechecks':92,
                          'formal_effect_matrix_execution_enabled':False}));return
    wire();summary=load_summary()
    if args.phase=='snapshot':
        print(json.dumps({'verified_rows':len(summary['rows']),'reused':len(summary['reused_accepted_ids'])}));return
    {'technical':technical,'pilot':pilot,'bridge':bridge}[args.phase](plan,summary)

if __name__=='__main__':main()
