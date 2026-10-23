"""Supplement historical audit and freeze a non-executable WS-30 design."""
import hashlib
import json
import random
import statistics
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from make_ws25_demand import make

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ev = ROOT/'docs/research/evidence'
    historical = ev/'ws30-historical-raw-audit.json'
    data = json.loads(historical.read_text(encoding='utf-8'))
    assert len(data['cells']) == 456
    regen = []
    with tempfile.TemporaryDirectory(prefix='ws30-input-audit-') as tmp:
        out = Path(tmp)
        for seed in sorted({r['seed'] for r in data['cells']}):
            generated = make(seed, out, levels=(192,))['levels']['192']
            old = {r['trace_sha256'] for r in data['cells'] if r['seed'] == seed}
            assert old == {generated['sha256']}
            regen.append({'seed': seed, 'sha256': generated['sha256'], 'byte_identical': True})
    def values(group, metric):
        return [r[metric] for r in data['cells'] if r['group']==group and r['mode']=='classreserve']
    contrasts = {}
    rng = random.Random(20263001)
    for metric in ['moe_change_pct','bg_change_pct']:
        a,b=values('ws25',metric),values('ws27',metric)
        draws=sorted(statistics.median(rng.choices(b,k=24))-statistics.median(rng.choices(a,k=24))
                     for _ in range(10000))
        contrasts[metric]={'new_minus_old_median_percentage_points':statistics.median(b)-statistics.median(a),
                           'descriptive_independent_group_bootstrap_95pct':[draws[250],draws[9750]],
                           'not_a_source_effect':True}
    supplement={'historical_audit_sha256':digest(historical),'regenerated_traces':regen,
                'group_difference':contrasts,
                'expected_group_cells':{'ws25':144,'ws27':96,'ws28native':96,'ws28ablation':120}}
    with (ev/'ws30-historical-audit-supplement.json').open('x',encoding='utf-8') as f:
        json.dump(supplement,f,indent=2,sort_keys=True);f.write('\n')
    seeds=list(range(20263021,20263045))
    arms=['E','H16','R16','Q16','C16','U16','Q12','M16']
    cells=[]
    schedule_rng=random.Random(20263002)
    seed_order=seeds[:];schedule_rng.shuffle(seed_order)
    for seed in seed_order:
        block=arms[:];schedule_rng.shuffle(block)
        for arm in block:
            cells.append({'demand_seed':seed,'arm':arm,'design_key':f'ws30-main-s{seed}-{arm}',
                          'order':len(cells)+1})
    lead=[]
    for seed in seed_order:
        block=['E','Q16','C16'];schedule_rng.shuffle(block)
        for arm in block:
            lead.append({'demand_seed':seed,'arm':arm,'moe_delay_ns':20000,
                         'design_key':f'ws30-lead20us-s{seed}-{arm}','order':len(lead)+1})
    plan={'status':'DESIGN FROZEN FOR REVIEW; NO REMOTE EXECUTION AUTHORIZED IN STAGE 1',
          'base_commit':'842b96ebd9d2037fd5c7486a41b2f101ead013c9',
          'implementation_sha':None,'trace_manifest_sha256':None,'experiment_ids':None,
          'new_seeds':seeds,'ns3_seed':1,'randomization_seed':20263002,
          'independent_unit':'demand seed; same trace shared across all arms',
          'main_cells':cells,'background_lead_cells':lead,
          'bridge_cells':96,'directed_composition_fixture_cells':12,
          'performance_cells_total':360,'technical_budget_max':32,'resource_pilot_cells_max':24,
          'total_cells_budget_max':428,'initial_concurrency_cap_max':12,
          'required_before_run':['main-thread review and explicit next-stage task',
                                 'implementation SHA and all input hashes frozen',
                                 'unique actual experiment IDs assigned',
                                 'correctness and nonperturbation gates',
                                 'resource pilot and actual model switch confirmed'],
          'arms':{
              'E':'original ECMP, 12-byte flow hash',
              'H16':'original mixed 12/16-byte candidates, first only, selected port pinned',
              'R16':'same candidates, independent stateless hash coin, selected port pinned',
              'Q16':'same candidates, total queue for BOTH classes, pinned; WS28 A0B1',
              'C16':'original ClassReserve A1B1',
              'U16':'Q16 with same first-arrival candidate PAIR retained but selected port recomputed per packet',
              'Q12':'total queue for BOTH classes, canonical 12-byte flow candidates, pinned',
              'M16':'WS28 A0B0: MoE total queue, background first candidate, pinned'},
          'mandatory_contrasts':['H16/E','R16/H16','Q16/R16','Q16/H16','U16/Q16',
                                 'Q12/E','Q16/Q12','C16/Q16','Q16/M16'],
          'stopping':'No early efficacy/futility stop; failures retained and repaired; no optional sample extension'}
    with (ev/'ws30-stage1-design.json').open('x',encoding='utf-8') as f:
        json.dump(plan,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({'regenerated_inputs':len(regen),'contrasts':contrasts,
                      'main_cells':len(cells),'lead_cells':len(lead),'design_sha256':digest(ev/'ws30-stage1-design.json')},indent=2))

if __name__=='__main__':main()
