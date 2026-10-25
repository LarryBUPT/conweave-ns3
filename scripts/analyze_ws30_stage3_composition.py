"""Audit all frozen composition raw data; four controlled conditions, no resampling."""
import collections
import csv
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import statistics

import run_ws30_stage3 as runner

ROOT, EV = runner.ROOT, runner.EV
PROBE = (0, 3, 10004, 100, 16000)
ARMS = ('E', 'Q16', 'C16')
CONTRASTS = (('Q16', 'E'), ('C16', 'E'), ('C16', 'Q16'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    value = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + '\n'
    if path.exists() and path.read_text(encoding='utf-8') != value:
        raise RuntimeError('Different frozen artifact exists: ' + str(path))
    path.write_text(value, encoding='utf-8')


def percentile(v, p):
    v = sorted(v)
    i = (len(v)-1)*p/100
    lo, hi = math.floor(i), math.ceil(i)
    return v[lo] + (v[hi]-v[lo])*(i-lo)


def audit(cell):
    folder = ROOT/'results'/cell['id']
    meta = runner.read(folder/'metadata.json')
    expected, ports, dports = {}, collections.defaultdict(lambda: 10000), collections.defaultdict(lambda: 100)
    trace = folder/'config/traffic_trace.txt'
    lines = trace.read_text().splitlines()
    for line in lines[1:]:
        f = line.split()
        src, dst, pg, size = map(int, f[:4])
        start, tag = int(Decimal(f[4])*10**9), int(f[5])
        key = (src, dst, ports[src], dports[dst], size)
        ports[src] += 1; dports[dst] += 1
        assert key not in expected
        expected[key] = {'tag': tag, 'start_ns': start, 'pg': pg}
    assert len(expected) == int(lines[0]) == cell['input_flows'] == (37 if cell['continuing'] else 5)
    raw = str(meta['raw_directory'])
    fct = folder/'raw'/raw/(raw+'_out_fct.txt')
    completed = {}
    for line in fct.read_text().splitlines():
        r = list(map(int, line.split())); key = tuple(r[:5])
        assert len(r) == 8 and key in expected and key not in completed
        assert abs(r[5]-expected[key]['start_ns']) <= 1 and r[6] > 0 and r[7] > 0
        completed[key] = {'start_ns': r[5], 'fct_ns': r[6], 'finish_ns': r[5]+r[6], 'standalone_ns': r[7]}
    assert completed.keys() == expected.keys()
    tags = {}
    for tag in (1, 2):
        keys = [k for k in expected if expected[k]['tag'] == tag]
        origin = min(expected[k]['start_ns'] for k in keys)
        end = max(completed[k]['finish_ns'] for k in keys)
        values = [completed[k]['fct_ns']/1000 for k in keys]
        assert origin == 2000000000 and len(keys) == (3 if tag == 2 else 34 if cell['continuing'] else 2)
        tags[str(tag)] = {'input_flows': len(keys), 'completed_flows': len(keys),
            'input_bytes': sum(k[4] for k in keys), 'completed_bytes': sum(k[4] for k in keys),
            'release_origin_ns': origin, 'batch_us': (end-origin)/1000,
            'mean_us': statistics.mean(values), **{f'p{p}_us': percentile(values, p) for p in (50, 95, 99)},
            'max_us': max(values), 'batch_tail_keys': [list(k) for k in keys if completed[k]['finish_ns'] == end]}
    assert expected[PROBE] == {'tag': 2, 'pg': 3, 'start_ns': 2000020000}
    logpath = folder/'logs/config.log'; log = logpath.read_text()
    events = [runner.stage.kv(l) for l in log.splitlines() if l.startswith('WS30_COMPOSITION_QUEUE ')]
    snapshots = [runner.stage.kv(l) for l in log.splitlines() if l.startswith('WS30_COMPOSITION_PROBE ')]
    assert len(snapshots) == 1
    snapshot = snapshots[0]; probe_time = snapshot['time_ns']
    ledger = {2: [0, 0], 3: [0, 0]}
    at_probe = {p: [0, 0] for p in ledger}
    for e in events:
        p, n = e['port'], e['bytes']*(1 if e['enqueue'] else -1)
        ledger[p][0] += n
        if e['tag'] == 1: ledger[p][1] += n
        assert ledger[p] == [e['total'],e['background']] and min(ledger[p]) >= 0
        if e['time_ns'] < probe_time: at_probe[p] = ledger[p][:]
    assert ledger == {2: [0, 0], 3: [0, 0]}
    assert at_probe == {p: [65536,cell['expected_background_by_port'][str(p)]] for p in (2,3)}
    assert snapshot['q1'] == snapshot['q2'] == 65536
    assert [snapshot['b1'],snapshot['b2']] == [at_probe[2][1],at_probe[3][1]]
    prefill = [e for e in events if e['enqueue'] and e['time_ns'] < probe_time]
    assert len(prefill) == 128 and collections.Counter(e['port'] for e in prefill) == {2:64,3:64}
    assert max(e['time_ns'] for e in prefill) == 2000003500
    # Each 31,232-B QP has 31 full 1,048-B wire packets and a 280-B tail.
    assert collections.Counter(e['bytes'] for e in prefill) == {1048:124,280:4}
    assert {p:sum(e['bytes'] for e in prefill if e['port']==p) for p in (2,3)} == {2:65536,3:65536}
    hold = [runner.stage.kv(l) for l in log.splitlines() if l.startswith('WS30_COMPOSITION_HOLD ')]
    assert hold == [{'time_ns':1999999000,'hold':1},{'time_ns':2000022000,'hold':0}]
    assert min(e['time_ns'] for e in events if not e['enqueue']) >= 2000022000 > probe_time
    routes = [runner.stage.kv(l) for l in log.splitlines() if l.startswith('WS30_ROUTE ')]
    probe_routes = [r for r in routes if r['switch']==4 and r['sport']==10004 and r['dip']==0x0b000301]
    first = [r for r in probe_routes if r['seq']==0]
    assert len(first)==1
    chosen = first[0]['port']
    assert chosen == {'E':3,'Q16':2,'C16':2 if cell['swap'] else 3}[cell['arm']]
    assert {r['port'] for r in probe_routes} == {chosen} and len(probe_routes)==16
    choices = [runner.stage.kv(l) for l in log.splitlines() if l.startswith('WS30_CHOICE ')]
    probe_choice = [r for r in choices if r['switch']==4 and r['sport']==10004 and r['dip']==0x0b000301]
    if cell['arm']=='E': assert not probe_choice
    else:
        assert len(probe_choice)==1
        q=probe_choice[0]
        assert (q['first'],q['second'],q['q1'],q['q2'],q['chosen'])==(2,3,65536,65536,chosen)
        assert (q['b1'],q['b2'])==(at_probe[2][1],at_probe[3][1])
    # The only enqueues after the snapshot and before release are the full probe train.
    train = [e for e in events if e['enqueue'] and probe_time <= e['time_ns'] < 2000022000]
    assert len(train)==16 and {e['port'] for e in train}=={chosen} and {e['tag'] for e in train}=={2}
    assert sum(e['bytes'] for e in train)==16768
    after = [e for e in events if e['enqueue'] and e['tag']==1 and e['time_ns']>=probe_time]
    if cell['continuing']:
        assert min(e['time_ns'] for e in after)==2000023019 > max(e['time_ns'] for e in train)
        assert {p:sum(e['bytes'] for e in after if e['port']==p) for p in (2,3)}=={2:134144,3:134144}
    else: assert not after
    config = dict(l.split(maxsplit=1) for l in (folder/'config/config.txt').read_text().splitlines() if len(l.split(maxsplit=1))==2)
    assert config['ENABLE_PFC']=='0' and config['ENABLE_IRN']=='1' and config['RANDOM_SEED']=='1' and config['CC_MODE']=='1'
    assert config['LB_MODE']=={'E':'0','Q16':'27','C16':'21'}[cell['arm']]
    assert meta['git_commit']==runner.COMPOSITION_SOURCE and meta['status']=='SUCCEEDED' and meta['concurrency_cap']==4
    assert sha(trace)==cell['trace_sha256'] and sha(folder/'config/topology.txt')==cell['topology_sha256']
    hashed = [folder/'metadata.json', trace, folder/'config/topology.txt', folder/'config/config.txt', logpath, fct,
              folder/'logs/resource-summary.json',folder/'logs/resource-samples.jsonl']
    flowrows = [{'id':cell['id'],'swap':cell['swap'],'continuing':cell['continuing'],'arm':cell['arm'],
                 'src':k[0],'dst':k[1],'sport':k[2],'dport':k[3],'size':k[4],
                 'tag':expected[k]['tag'],'pg':expected[k]['pg'],'planned_start_ns':expected[k]['start_ns'],**completed[k]} for k in expected]
    row = {'id':cell['id'],'swap':cell['swap'],'continuing':cell['continuing'],'arm':cell['arm'],
           'source_sha':meta['git_commit'],'tags':tags,'probe':{'identity':list(PROBE),**completed[PROBE]},
           'start_rounding_ns':dict(collections.Counter(completed[k]['start_ns']-expected[k]['start_ns'] for k in expected)),
           'queue':{'snapshot':snapshot,'prefill_packets_per_port':64,'wire_bytes_per_port':65536,
                    'last_prefill_enqueue_ns':max(e['time_ns'] for e in prefill),'first_dequeue_ns':min(e['time_ns'] for e in events if not e['enqueue']),
                    'probe_train_last_enqueue_ns':max(e['time_ns'] for e in train),'probe_train_wire_bytes':16768,
                    'first_continuing_background_enqueue_ns':min((e['time_ns'] for e in after),default=None),'final_bytes_by_port':ledger},
           'decision':{'chosen_port':chosen,'first':2 if probe_choice else None,'second':3 if probe_choice else None,
                       'choice':probe_choice[0] if probe_choice else None,'probe_data_packets':len(probe_routes),'probe_ports':sorted({r['port'] for r in probe_routes})},
           'file_sha256':{str(p.relative_to(folder)).replace('\\','/'):sha(p) for p in hashed},
           'actual_cap':meta['concurrency_cap'],'started_utc':meta['started_utc'],'finished_utc':meta['finished_utc']}
    return row, flowrows


def main():
    plan=runner.read(runner.PLAN); cells=plan['composition']; assert len(cells)==12
    assert sha(runner.PLAN)=='77ca6064d4b4f275b409123302b01bd4eabd97e9c978e013f8d3e67edbf420f8'
    recorded={r['id']:r for r in runner.read(EV/'ws30-stage3-composition-results-r5.json')['rows']}
    rows,flows,verified=[],[],[]
    for c in cells:
        v=runner.verify(c); assert v==recorded[c['id']]
        r,f=audit(c)
        for tag in ('1','2'):
            for key in ('batch_us','p50_us','p95_us','p99_us','max_us','release_origin_ns'):
                assert math.isclose(v['tags'][tag][key],r['tags'][tag][key],rel_tol=1e-12,abs_tol=1e-10)
        assert v['composition']['probe_fct_ns']==r['probe']['fct_ns']
        rows.append(r); flows.extend(f); verified.append(v)
    index={(r['swap'],r['continuing'],r['arm']):r for r in rows}
    byflow={r['id']:{(f['src'],f['dst'],f['sport'],f['dport'],f['size']):f for f in flows if f['id']==r['id']} for r in rows}
    comparisons=[]; perflow=[]
    for swap in (0,1):
        for cont in (0,1):
            for a,b in CONTRASTS:
                r,t=index[swap,cont,a],index[swap,cont,b]
                assert byflow[r['id']].keys()==byflow[t['id']].keys()
                out={'swap':swap,'continuing':cont,'contrast':a+'/'+b,'candidate_id':r['id'],'control_id':t['id'],
                     'probe_fct_change_ns':r['probe']['fct_ns']-t['probe']['fct_ns'],
                     'tag2_batch_change_us':r['tags']['2']['batch_us']-t['tags']['2']['batch_us'],
                     'background_p99_change_us':r['tags']['1']['p99_us']-t['tags']['1']['p99_us'],
                     'background_mean_change_us':r['tags']['1']['mean_us']-t['tags']['1']['mean_us'],
                     'background_batch_change_us':r['tags']['1']['batch_us']-t['tags']['1']['batch_us']}
                for metric,key in [('tag2_batch','batch_us'),('background_p99','p99_us')]:
                    tag='2' if metric=='tag2_batch' else '1';out[metric+'_change_pct']=100*(r['tags'][tag][key]/t['tags'][tag][key]-1)
                for tag in (1,2):
                    diffs=[]
                    for k,f in byflow[r['id']].items():
                        g=byflow[t['id']][k]; assert f['tag']==g['tag'] and f['start_ns']==g['start_ns']
                        if f['tag']!=tag:continue
                        delta=f['fct_ns']-g['fct_ns'];diffs.append(delta)
                        perflow.append({'swap':swap,'continuing':cont,'contrast':a+'/'+b,'tag':tag,
                            'src':k[0],'dst':k[1],'sport':k[2],'dport':k[3],'size':k[4],
                            'candidate_id':r['id'],'control_id':t['id'],'candidate_fct_ns':f['fct_ns'],'control_fct_ns':g['fct_ns'],
                            'change_ns':delta,'change_pct':100*delta/g['fct_ns']})
                    out['tag'+str(tag)+'_flow_changes']={'n':len(diffs),'lower':sum(d<0 for d in diffs),'equal':sum(d==0 for d in diffs),'higher':sum(d>0 for d in diffs),'min_ns':min(diffs),'max_ns':max(diffs)}
                comparisons.append(out)
    resources={key:fn(v['resource'][key] for v in verified) for key,fn in [('peak_load_1m',max),('minimum_mem_available_gib',min),('minimum_free_gib',min),('peak_tree_rss_mib',max)]}
    result={'version':'r1','source_sha':runner.COMPOSITION_SOURCE,'plan_sha256':sha(runner.PLAN),
        'verified_cells':12,'raw_fct_rows':len(flows),'controlled_conditions':4,'arms':list(ARMS),'statistical_unit':'four fixed controlled fixture conditions; one simulation per arm and condition; no independent demand replication',
        'inference':'descriptive paired contrasts only; no bootstrap, confidence interval or significance test',
        'definitions':{'tag2_batch_us':'max(start_ns + fct_ns) over all three tag2 QPs minus 2000000000 ns, divided by 1000',
                       'probe_fct_us':'probe FCT only; own release 2000020000 ns; identity [0,3,10004,100,16000]',
                       'background_p99_us':'linear quantile at index (n-1)*0.99 of all tag1 per-flow FCTs; n=2 or 34',
                       'background_batch_us':'last tag1 completion minus first tag1 release; includes later-arrival interval'},
        'rows':rows,'comparisons':comparisons,'resources_from_simulation_watchers':resources,
        'resource_rss_note':'All 2-s watcher samples recorded 0 MiB for process trees; sub-second simulations can finish between samples. Zero is not a measured zero peak.',
        'exclusions':[]}
    write(EV/'ws30-stage3-composition-analysis-r1.json',result)
    write(EV/'ws30-stage3-composition-raw-audit-r1.json',{'source_sha':runner.COMPOSITION_SOURCE,'verified_cells':12,'raw_rows':len(flows),'independent_reconstruction':'Decimal timestamps; all QP keys and bytes; per-class FCT; full queue event replay, hold, first packet and complete probe train','rows':rows})
    summary=[]
    for r in rows:
        summary.append({'swap':r['swap'],'continuing':r['continuing'],'arm':r['arm'],'id':r['id'],
            'chosen_port':r['decision']['chosen_port'],'tag2_batch_us':r['tags']['2']['batch_us'],'probe_fct_us':r['probe']['fct_ns']/1000,
            **{'background_'+k:r['tags']['1'][k] for k in ('input_flows','input_bytes','batch_us','mean_us','p50_us','p95_us','p99_us','max_us')}})
    for name,values in [('metrics',summary),('flows',flows),('flow-contrasts',perflow)]:
        with (EV/f'ws30-stage3-composition-{name}-r1.csv').open('w',newline='',encoding='utf-8') as h:
            w=csv.DictWriter(h,fieldnames=list(values[0]));w.writeheader();w.writerows(values)
    for r in summary:print(r)
    for c in comparisons:print('CONTRAST',c)
    print('RESOURCES',resources)


if __name__=='__main__': main()
