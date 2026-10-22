#!/usr/bin/env python3
"""Read-only validation of frozen WS-29 raw cells, including exact C0 regression."""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from ws29_evidence_checks import (verify_settings, verify_reference, verify_runtime,
                                  verify_control, verify_provenance, verify_lifecycle)

ROOT = Path(__file__).resolve().parents[1]


def require(value, message):
    if not value: raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fields(line):
    return dict(word.split('=', 1) for word in line.split()[1:] if '=' in word)


def config(path):
    return dict(line.split(None, 1) for line in path.read_text().splitlines()
                if line.strip() and not line.startswith('#'))


def check_decision(row, arm):
    n = lambda k: int(row[k])
    valid = row['reason'] in ('equal_ce', 'distinct_ce')
    if valid:
        require(n('first') != n('second'), 'aliased candidates claimed eligible')
        for p in ('a', 'b'):
            require(row[p + '_status'] == 'valid' and n(p + '_samples') > 0,
                    'eligible decision has missing samples/liveness')
            require(n(p + '_start') <= n(p + '_end') <= n('time_ns') and
                    n('time_ns') - n(p + '_end') <= 20000, 'stale eligible decision')
            require(0 <= n(p + '_ce') <= n(p + '_samples') and
                    n(p + '_session') > 0 and n(p + '_sequence') > 0,
                    'invalid state identity/ratio')
        a = n('a_ce') * n('b_samples'); b = n('b_ce') * n('a_samples')
        proposed = n('local') if a == b else n('first') if a < b else n('second')
        require(n('proposed') == proposed, 'choice does not match CE comparison')
    else:
        require(n('proposed') == n('local'), 'fallback changed local choice')
    require(n('chosen') == (n('proposed') if arm == 2 else n('local')),
            'arm consumption switch violated')
    return valid


def verify(folder, cell, limits):
    meta = json.loads((folder / 'metadata.json').read_text())
    require(meta['experiment_id'] == cell['id'] and meta['status'] == 'SUCCEEDED' and
            meta['git_commit'] == cell['source_sha'],
            'terminal state/source mismatch')
    require(meta['algorithm'] == cell['mode'] and meta['seed'] == 1 and
            meta['build_mode'] == 'optimized', 'mode/seed/build mismatch')
    require(meta['parameters'].get('ws29_arm') == cell['arm'], 'arm metadata mismatch')
    for k in ('pfc', 'irn', 'bw', 'buffer'):
        require(meta['parameters'][k] == cell[k], 'parameter mismatch: ' + k)
    for name, key in (('traffic_trace.txt', 'trace_sha256'), ('topology.txt', 'topology_sha256')):
        require(sha(folder / 'config' / name) == cell[key], 'input snapshot mismatch: ' + name)
    rawid = str(meta['raw_directory']); require(rawid.isdecimal(), 'invalid raw directory')
    raw = folder / 'raw' / rawid
    fct = raw / (rawid + '_out_fct.txt')
    trace = [line.split() for line in (folder / 'config/traffic_trace.txt').read_text().splitlines()[1:]
             if line.strip()]
    sports, dports, expected = {}, {}, {}
    for r in trace:
        src, dst, size, start = int(r[0]), int(r[1]), int(r[3]), round(float(r[4]) * 1e9)
        sp, dp = sports.get(src, 10000), dports.get(dst, 100)
        sports[src], dports[dst] = sp + 1, dp + 1
        expected[(src, dst, sp, dp, size)] = (start, int(r[5]))
    done, done_bytes = set(), 0
    for line in fct.read_text().splitlines():
        r = list(map(int, line.split())); require(len(r) == 8, 'malformed FCT')
        key = tuple(r[:5]); require(key in expected and key not in done, 'FCT identity/duplicate')
        require(abs(expected[key][0] - r[5]) <= 2, 'demand/release timestamp changed')
        done.add(key); done_bytes += r[4]
    require(len(expected) == len(done) == cell['input_flows'] and
            done_bytes == cell['input_bytes'], 'completion/byte conservation failed')
    cfg = config(folder / 'config/config.txt')
    verify_settings(meta, cfg, cell)
    require(cfg['LB_MODE'] == ('21' if cell['mode'] == 'classreserve' else '20'), 'config LB_MODE')
    logpath = raw / 'config.log'
    if not logpath.exists(): logpath = folder / 'logs/config.log'
    lines = logpath.read_text(encoding='utf-8', errors='strict').splitlines()
    verify_runtime(lines, cell)
    if cell['mode'] == 'classreserve':
        require('WS28_FACTOR mode=21 background_weight=1 background_routing=1' in lines,
                'actual ClassReserve branch receipt absent')
        qs = [fields(x) for x in lines if x.startswith('WS25_QUEUE ')]
        cr = [fields(x) for x in lines if x.startswith('WS25_CLASSRESERVE ')]
        require(len(qs) == 1 and len(cr) == 1 and int(cr[0]['queue_violations']) == 0,
                'queue receipt/violations')
        q = qs[0]
        require(int(q['enqueued']) == int(q['dequeued']) + int(q['queued_drop']) +
                int(q['current']), 'aggregate queue conservation')
    decisions = [fields(x) for x in lines if x.startswith('WS29_DECISION ')]
    if cell['arm'] >= 0:
        require('WS06_ROUTING_TAG missing=0' in lines, 'missing workload tag')
        identity = raw / (rawid + '_out_ws21_identity.txt')
        require(identity.exists(), 'identity raw absent')
        for line in identity.read_text().splitlines():
            r = line.split(); require(len(r) == 13 and int(r[12]) == 0, 'identity unmapped')
            if cell['fault'] not in (20, 23): require(int(r[11]) == 0, 'QP path identity inconsistent')
        qps = [fields(x) for x in lines if x.startswith('WS29_QP ')]
        transport = [fields(x) for x in lines if x.startswith('WS25_QP ')]
        require(len(qps) == len(transport) == cell['input_flows'], 'QP/transport diagnostic coverage')
        require(sum(int(q['input_bytes']) for q in qps) == cell['input_bytes'] and
                all(int(q['tx_payload_bytes']) >= int(q['input_bytes']) for q in qps),
                'transmitted application byte ledger inconsistent')
    eligible = sum(check_decision(row, cell['arm']) for row in decisions)
    confirmed = {}
    for line in lines:
        r = fields(line)
        if line.startswith('WS29_ACK '): confirmed[(r['switch'], r['port'])] = int(r['time_ns'])
        elif line.startswith('WS29_LINK '): confirmed.pop((r['switch'], r['port']), None)
        elif line.startswith('WS29_SESSION '):
            confirmed = {k: v for k, v in confirmed.items() if k[0] != r['switch']}
        elif line.startswith('WS29_DECISION ') and r['reason'] in ('equal_ce', 'distinct_ce'):
            if cell['fault'] in (15, 16, 17): continue
            for key in ('first', 'second'):
                ack = confirmed.get((r['switch'], r[key]))
                require(ack is not None and 0 <= int(r['time_ns']) - ack <= 800000,
                        'eligible decision has no independently recorded fresh ACK')
    changed = sum(row['chosen'] != row['local'] for row in decisions)
    summaries = [fields(x) for x in lines if x.startswith('WS29_SUMMARY ')]
    counts = {r['name']: int(r['count']) for r in map(fields, lines) if 'name' in r and 'count' in r}
    verify_control(lines, cell, counts)
    verify_provenance(lines, folder / 'config/topology.txt', cell)
    verify_lifecycle(lines, cell, counts)
    if cell['arm'] >= 0:
        require(len(summaries) == 1 and int(summaries[0]['overflow']) == 0, 'event overflow')
        require(counts.get('two_fresh', 0) == eligible and
                counts.get('adopted_changed', 0) == changed and
                counts.get('decisions', 0) == len(decisions), 'decision totals disagree')
        topology_lines = (folder / 'config/topology.txt').read_text().splitlines()
        switches = set(map(int, topology_lines[1].split()))
        host_tor = {}
        for link in topology_lines[2:]:
            r = link.split()
            if len(r) < 2: continue
            a, b = map(int, r[:2])
            if a not in switches and b in switches: host_tor[a] = b
            if b not in switches and a in switches: host_tor[b] = a
        cross = {k[:4] for k in expected if host_tor[k[0]] != host_tor[k[1]]}
        recorded = {(int(r['src']), int(r['dst']), int(r['sport']), int(r['dport'])) for r in decisions}
        require(recorded == cross, 'missing or spurious cross-ToR first decisions')
        if cell['fault'] not in (20, 23):
            require(len(recorded) == len(decisions), 'unexpected normal QP redecision')
    ledger = defaultdict(Counter)
    for row in (fields(x) for x in lines if x.startswith('WS29_CONTROL ')):
        ledger[(row['switch'], row['port'], row['type'])][row['event']] += int(row['bytes'])
    for key, amounts in ledger.items():
        require(amounts['enqueue'] == amounts['dequeue'] + amounts['queued_drop'],
                'control per-link bytes not conserved: ' + str(key))
    if not cell['synthetic']:
        require(not any(x.startswith('WS29_SYNTHETIC ') for x in lines), 'oracle in natural cell')
    fault = cell['fault']
    if fault in (1, 2):
        require(counts.get('fault_injected') == 1, 'not exactly one dropped probe')
        hb = [fields(x) for x in lines if x.startswith('WS21_HEARTBEAT ')]
        require(len(hb) == 1 and int(hb[0]['unknown']) == 0 and int(hb[0]['injected_drops']) == 1,
                'single loss false alarm or wrong count')
    if 3 <= fault <= 8:
        events = [fields(x) for x in lines if x.startswith('WS29_ACK_INJECT ')]
        require(len(events) == 1 and int(events[0]['rejected_delta']) == 1 and
                int(events[0]['accepted_delta']) == int(fault == 4), 'ACK fault expectation')
        if fault != 4:
            require(events[0]['outstanding_after'] != '0', 'invalid ACK cleared outstanding probe')
    if fault == 9: require(counts.get('session_restart_injected') == 1, 'restart not injected')
    if fault in (8, 9): require(counts.get('hb_old_timer_ignored', 0) >= 1, 'old timer not exercised')
    if fault == 10:
        events = [fields(x) for x in lines if x.startswith('WS29_SYNTHETIC ') and fields(x).get('fault') == '10']
        require(len(events) == 1 and events[0]['rejected_delta'] == '1' and
                counts.get('state_old_session', 0) >= 1, 'old STATE session accepted')
    if fault == 11: require(counts.get('state_sequence_rollover', 0) >= 1, 'STATE did not roll session')
    if fault in (20, 23):
        events = [fields(x) for x in lines if x.startswith('WS29_LINK ')]
        require(sum(x['up'] == '0' for x in events) == (2 if fault == 20 else 4) and
                sum(x['up'] == '1' for x in events) == (2 if fault == 20 else 4), 'link pair events')
        if fault == 23: require(counts.get('no_live_port_drop', 0) > 0, 'empty-port branch not exercised')
    require(changed >= cell.get('expected_adopted_changed_min', 0), 'no forced adoption')
    require(changed <= cell.get('expected_adopted_changed_max', changed), 'unsafe synthetic fallback')
    if 'reference' in cell:
        old = cell['reference']; verify_reference(old)
        require(sha(fct) == old['fct_sha256'], 'C0/legacy FCT fingerprint differs')
        oldcfg = config(Path(old['root']) / 'config/config.txt')
        require(sha(Path(old['root']) / 'config/config.txt') == old['config_sha256'], 'old config changed')
        for key, value in oldcfg.items():
            if 'FILE' in key or key.startswith('WS21_') or key.startswith('WS29_'): continue
            require(cfg.get(key) == value, 'old/new common config differs: ' + key)
    resource = json.loads((folder / 'logs/resource-summary.json').read_text())
    samples = [json.loads(x) for x in (folder / 'logs/resource-samples.jsonl').read_text().splitlines() if x]
    require(resource['id'] == cell['id'] and resource['final_status'] == 'SUCCEEDED' and
            resource['samples'] == len(samples) > 0, 'resource identity/count')
    require(resource['peak_tree_rss_mib'] <= limits['rss_mib_max'] and
            resource['minimum_mem_available_gib'] >= limits['available_memory_gib_min'] and
            resource['minimum_free_gib'] >= limits['free_disk_gib_min'] and
            max(r['load_1m'] for r in samples) <= limits['load_1m_max'], 'resource stop line')
    require(max((p.stat().st_size for p in folder.rglob('*.log')), default=0) <=
            limits['max_text_log_bytes'], 'text log stop line')
    return {'id': cell['id'], 'source_sha': cell['source_sha'], 'fct_sha256': sha(fct),
            'config_sha256': sha(folder / 'config/config.txt'), 'completed_flows': len(done),
            'completed_bytes': done_bytes, 'recorded_source_decisions': len(decisions),
            'two_fresh_decisions': eligible, 'adopted_changed': changed,
            'two_fresh_fraction_of_recorded': eligible / len(decisions) if decisions else None,
            'counts': counts, 'resource': resource}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, default=ROOT / 'docs/research/evidence/ws29-engineering-plan.json')
    parser.add_argument('--results', type=Path, default=ROOT / 'results')
    parser.add_argument('--id')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); plan = json.loads(args.plan.read_text(encoding='utf-8'))
    cells = [x for x in plan['cells'] if not args.id or x['id'] == args.id]
    require(bool(cells), 'unknown experiment ID')
    rows = [verify(args.results / cell['id'], cell, plan['resource_limits']) for cell in cells]
    data = json.dumps({'plan_sha256': sha(args.plan), 'verified_cells': rows}, indent=2) + '\n'
    require(not args.output.exists() or args.output.read_text() == data, 'refuse changed verification output')
    args.output.write_text(data, encoding='utf-8')
    print(json.dumps({'verified': len(rows), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
