"""Four exact fixed-source Q+R rules on one unchanged reference trajectory.

This is local analysis, not a candidate run or dynamic counterfactual replay.
Per-entry remaining payload is framed before summing; observed packet history,
all Q values and every past assignment stay those of the old QueuePin run.
"""
from bisect import bisect_left
from collections import Counter, defaultdict
from pathlib import Path
import csv
import hashlib
import json


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    m = Path(__file__).resolve().parents[1]
    base = m.parent / 'independent/zero-control-pilot-r1-evidence/20261101-062753-ws31-zr1-q12/results'
    trace = base / 'config/traffic_trace.txt'
    log = next((base / 'raw').glob('*/config.log'))
    acceptance = m / 'evidence/zero-control-q12-main-acceptance-r1.json'
    opportunity = m / 'evidence/review-opportunity-screen-r1.json'
    opportunity_rows = m / 'evidence/review-opportunity-screen-r1.csv'
    old_v0 = m / 'evidence/v0-technical-replay-r1.csv'
    out = m / 'evidence/full-score-reference-screen-r1.json'
    rows_out = m / 'evidence/full-score-reference-screen-r1.csv'
    if out.exists() or rows_out.exists():
        raise FileExistsError('Existing screen is preserved; no repeated analysis.')
    a = json.loads(acceptance.read_text(encoding='utf-8'))
    o = json.loads(opportunity.read_text(encoding='utf-8'))
    assert sha(log) == a['log_sha256']
    assert sha(trace) == a['inputs']['config/ws31_correctness_r1.txt']
    assert sha(opportunity_rows) == o['rows_csv_sha256']
    samples = list(csv.DictReader(opportunity_rows.open(encoding='utf-8')))
    assert len(samples) == 104
    by_key, packets, source_tor = {}, defaultdict(dict), {}
    for d in samples:
        key = tuple(int(d[x]) for x in ('src', 'dst', 'sport', 'dport'))
        by_key[key] = d
        source_tor[key] = int(d['switch'])
    sp, dp, flows = defaultdict(lambda: 10000), defaultdict(lambda: 100), {}
    for line in trace.read_text().splitlines()[1:]:
        src, dst, pg, size, start, tag = line.split()
        src, dst = int(src), int(dst)
        key = (src, dst, sp[src], dp[dst]); sp[src] += 1; dp[dst] += 1
        assert int(tag) == int(by_key[key]['tag'])
        flows[key] = dict(size=int(size), tag=int(tag))
    config = dict((line.split()[0], line.split()[1:])
                  for line in (base/'config/config.txt').read_text().splitlines() if line.strip())
    assert int(config['PACKET_PAYLOAD_SIZE'][0]) == 1000
    raw_fields = {}
    with log.open(encoding='utf-8') as handle:
        for index, line in enumerate(handle):
            if line.startswith('WS30V13_CACHE_RESET '):
                raise ValueError('Reference reset needs a separate lifecycle model.')
            if not line.startswith('WS30_ROUTE '):
                continue
            v = {k:int(x) for k,x in (t.split('=',1) for t in line.split()[1:])}
            key = ((v['sip']>>8)&65535,(v['dip']>>8)&65535,v['sport'],v['dport'])
            if v['switch'] != source_tor[key]:
                continue
            raw_fields.setdefault('source_route', sorted(v))
            assert v['port'] == int(by_key[key]['baseline_chosen'])
            assert v['tag'] == flows[key]['tag']
            seq = v['seq']; length = min(1000, flows[key]['size']-seq)
            assert length > 0
            packets[key].setdefault(seq, (index,v['time_ns'],length))
    for key, f in flows.items():
        end = 0
        for seq, event in sorted(packets[key].items()):
            assert seq == end
            end += event[2]
        assert end == f['size']
        events = sorted(packets[key].values())
        f['lines'] = [e[0] for e in events]
        f['prefix'] = [0]
        for e in events:
            f['prefix'].append(f['prefix'][-1]+e[2])
    variants = ['class_progress','class_count','unified_progress','unified_count']
    old = {(int(d['line']),d['variant']): d
           for d in csv.DictReader(old_v0.open(encoding='utf-8'))}
    frame = lambda n: n + ((n+999)//1000)*48
    result_rows, chosen_by_line, totals = [], {}, defaultdict(Counter)
    for d in samples:
        line, now, sw = int(d['line']), int(d['time_ns']), int(d['switch'])
        p1,p2,q1,q2 = (int(d[k]) for k in ('first','second','q1_wire','q2_wire'))
        r = {v:defaultdict(int) for v in variants}
        payload = {v:defaultdict(int) for v in variants}
        for key, f in flows.items():
            prev = by_key[key]
            if int(prev['line']) >= line or int(prev['switch']) != sw or int(prev['time_ns'])+20000 <= now:
                continue
            port = int(prev['baseline_chosen'])
            if port not in (p1,p2):
                continue
            seen = f['prefix'][bisect_left(f['lines'],line)]
            for v in variants:
                budget = 65536 if v.startswith('class_') and f['tag']==1 else 8192
                remaining = max(0,budget-seen) if v.endswith('_progress') else budget
                payload[v][port] += remaining
                r[v][port] += frame(remaining)
        selected = {}
        for v in variants:
            # Agreement with old payload rows validates identity/order/template/expiry;
            # only per-entry framing and Q+R action are new in this artifact.
            prior = old[(line,v)]
            assert payload[v][p1] == int(prior['pred1_payload'])
            assert payload[v][p2] == int(prior['pred2_payload'])
            choice = p2 if q2+r[v][p2] < q1+r[v][p1] else p1
            selected[v] = choice
            row = dict(line=line,time_ns=now,switch=sw,src=int(d['src']),dst=int(d['dst']),
                       sport=int(d['sport']),dport=int(d['dport']),tag=int(d['tag']),variant=v,
                       first=p1,second=p2,q1=q1,q2=q2,r1=r[v][p1],r2=r[v][p2],
                       score1=q1+r[v][p1],score2=q2+r[v][p2],chosen=choice,
                       baseline_chosen=int(d['baseline_chosen']))
            result_rows.append(row)
            totals[v]['decisions'] += 1
            totals[v]['nonzero_pressure'] += bool(r[v][p1] or r[v][p2])
            totals[v]['different_from_reference'] += choice != int(d['baseline_chosen'])
        chosen_by_line[line] = selected
    contrasts = {}
    for x,y in [('class_progress','class_count'),('unified_progress','unified_count'),
                ('class_progress','unified_progress'),('class_count','unified_count')]:
        lines = [n for n,v in chosen_by_line.items() if v[x] != v[y]]
        contrasts[x+'_vs_'+y] = dict(different_decisions=len(lines),reference_lines=lines)
    with rows_out.open('x',encoding='utf-8',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=list(result_rows[0]));writer.writeheader();writer.writerows(result_rows)
    result = dict(scope='ONE TECHNICAL REFERENCE: fixed-source numerical Q+R action accounting, not dynamic policy effects',
                  reference_id=a['id'],source_sha=a['source_sha'],decisions=104,
                  state_position='Before first-choice event; earlier allocations and all Q/arrival events stay baseline',
                  R_definition='Sum remaining+ceil(remaining/1000)*48 per live prediction entry; class template65536/8192, unified8192, TTL20000ns',
                  Q_definition='Exact CalculateInterfaceLoad value recorded by baseline; no rescaling or reinterpretation of its queue framing',
                  aggregate_payload_rows_crosschecked=416,rows=416,
                  source_route_fields=raw_fields['source_route'],
                  totals={k:dict(v) for k,v in totals.items()},contrasts=contrasts,
                  nonclaims=['No altered past assignments, no new run, no independent demand or semantic evidence.',
                             'No optimization bound, performance gain, action-direction correctness, or revival permission.',
                             '48B framing is fixed-source source-side prediction framing; queue accounting is preserved as implemented.',
                             'Contiguous first-seen packet segments and zero drops are specific to this old input; no general overlap/drop/lifecycle proof.'],
                  input_sha256={str(p):sha(p) for p in [trace,log,acceptance,old_v0,opportunity,opportunity_rows]},
                  script_sha256=sha(Path(__file__)),rows_csv_sha256=sha(rows_out))
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'totals':result['totals'],'contrasts':contrasts},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
