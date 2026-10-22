"""Independent raw evidence checks; absent lifecycle evidence is a rejection."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(lines, prefix):
    return [dict(w.split('=', 1) for w in line.split()[1:] if '=' in w)
            for line in lines if line.startswith(prefix + ' ')]


def verify_settings(meta, cfg, cell):
    pairs = {'ws29_arm': cell['arm']}
    pairs.update({'ws29_' + k: cell[k] for k in
                  ('fault', 'fault_tor', 'fault_port', 'fault_start_ns', 'fault_end_ns')})
    control = cell.get('legacy_control_options', {})
    pairs.update(ws21_identity=control.get('ws21_identity', int(cell['arm'] >= 0)),
                 ws21_feedback=control.get('ws21_feedback', int(cell['arm'] in (1, 2, 3))),
                 ws21_heartbeat=control.get('ws21_heartbeat', int(cell['arm'] in (1, 2))),
                 ws21_feedback_interval_ns=10000, ws21_heartbeat_interval_ns=200000)
    for name, expected in pairs.items():
        require(meta['parameters'].get(name) == expected, 'metadata mismatch: ' + name)
        require(cfg.get(name.upper()) == str(expected), 'effective config mismatch: ' + name)
    for name, key in (('RANDOM_SEED', 'ns3_seed'), ('ENABLE_PFC', 'pfc'), ('ENABLE_IRN', 'irn')):
        require(cfg.get(name) == str(cell[key]), 'effective config mismatch: ' + name)


def verify_reference(old):
    root = Path(old['root'])
    for relative, key in (('metadata.json', 'metadata_sha256'),
                          ('config/config.txt', 'config_sha256'),
                          ('config/traffic_trace.txt', 'trace_sha256'),
                          ('config/topology.txt', 'topology_sha256')):
        require(digest(root / relative) == old[key], 'old reference changed: ' + relative)
    meta = json.loads((root / 'metadata.json').read_text())
    require(meta['git_commit'] == old['source_sha'] and meta['seed'] == old['seed'] and
            meta['parameters'] == old['parameters'], 'old metadata identity/parameters differ')
    rawid = str(meta['raw_directory'])
    require(rawid.isdecimal(), 'old raw directory invalid')
    require(digest(root / 'raw' / rawid / (rawid + '_out_fct.txt')) == old['fct_sha256'],
            'old reference FCT changed')


def verify_runtime(lines, cell):
    if cell['arm'] < 0:
        return
    settings = rows(lines, 'WS29_SETTINGS')
    expected = {k: cell[k] for k in ('arm', 'fault', 'fault_tor', 'fault_port', 'fault_start_ns', 'fault_end_ns')}
    expected.update(identity=1, state=int(cell['arm'] in (1, 2, 3)),
                    heartbeat=int(cell['arm'] in (1, 2)), state_interval_ns=10000,
                    heartbeat_interval_ns=200000, decision_ttl_ns=20000)
    require(len(settings) == 1 and all(settings[0].get(k) == str(v) for k, v in expected.items()),
            'actual runtime configuration/TTL receipt differs')


def verify_control(lines, cell, counts):
    arm = cell['arm']
    if arm < 0:
        return
    controls = rows(lines, 'WS29_CONTROL')
    sends, caches, acks = (rows(lines, k) for k in
                          ('WS29_STATE_SEND', 'WS29_STATE_CACHE', 'WS29_ACK'))
    feedback, heartbeat = rows(lines, 'WS21_FEEDBACK'), rows(lines, 'WS21_HEARTBEAT')
    state_on, hb_on = arm in (1, 2, 3), arm in (1, 2)
    require(len(feedback) == int(state_on) and len(heartbeat) == int(hb_on),
            'arm control summary presence mismatch')
    require(state_on or not (sends or caches), 'STATE observed in disabled arm')
    require(hb_on or not (acks or rows(lines, 'WS21_HEARTBEAT_EVENT')),
            'heartbeat observed in disabled arm')
    ledger, totals = defaultdict(Counter), Counter()
    for row in controls:
        kind, event, size = row['type'], row['event'], int(row['bytes'])
        require(kind in ('state', 'hello', 'ack') and event in
                ('enqueue', 'dequeue', 'queued_drop', 'queue_reject', 'admission_reject'), 'unknown control event')
        require((state_on if kind == 'state' else hb_on), 'wire control in disabled arm')
        require(size == (72 if kind == 'state' else 44), 'unexpected actual control wire bytes')
        key = (row['switch'], row['port'], kind)
        for unit, amount in (('bytes', size), ('packets', 1)):
            ledger[key][event + '_' + unit] += amount
            totals[kind + '_' + event + '_' + unit] += amount
    for key, value in ledger.items():
        for unit in ('bytes', 'packets'):
            require(value['enqueue_' + unit] == value['dequeue_' + unit] +
                    value['queued_drop_' + unit], 'per-link control conservation: ' + str(key))
    for kind in ('state', 'hello', 'ack'):
        for event in ('enqueue', 'dequeue', 'queued_drop', 'queue_reject', 'admission_reject'):
            for unit in ('bytes', 'packets'):
                name = kind + '_' + event + '_' + unit
                require(counts.get(name, 0) == totals[name], 'control raw/count mismatch: ' + name)
    summary = rows(lines, 'WS29_SUMMARY')
    event_names = {'WS29_CONTROL', 'WS29_STATE_SEND', 'WS29_STATE_CACHE', 'WS29_ACK',
                   'WS29_LINK', 'WS29_SESSION', 'WS29_SYNTHETIC', 'WS29_ACK_INJECT',
                   'WS29_DECISION', 'WS29_DROP', 'WS29_TIMER', 'WS29_STATE_REJECT', 'WS29_ACK_CHECK',
                   'WS29_CONTROL_UNSENT', 'WS29_HELLO'}
    require(len(summary) == 1 and int(summary[0]['arm']) == arm and
            int(summary[0]['overflow']) == 0 and int(summary[0]['rows']) ==
            sum(line.split()[0] in event_names for line in lines if line.strip()),
            'WS29 event rows/arm/overflow mismatch')
    if state_on:
        f = feedback[0]
        require(int(f['generated']) == len(sends) and int(f['delivered']) == len(caches),
                'STATE generation/cache totals disagree')
        require(int(f['delivered_bytes']) == sum(int(r['bytes']) for r in caches),
                'STATE delivered bytes disagree')
        for field, total in (('hop_enqueues', 'state_enqueue_packets'),
                             ('hop_dequeues', 'state_dequeue_packets'),
                             ('hop_bytes', 'state_enqueue_bytes')):
            require(int(f[field]) == totals[total], 'STATE hop accounting mismatch: ' + field)
        require(int(f['hop_rejects']) == totals['state_admission_reject_packets'] +
                totals['state_queue_reject_packets'], 'STATE hop rejection mismatch')
        rejects = rows(lines, 'WS29_STATE_REJECT')
        require(sum(r['outcome'] == 'rejected' for r in rejects) == int(f['rejected']) and
                sum(r['outcome'] == 'expired' for r in rejects) == int(f['expired']),
                'STATE reject/expiry raw evidence missing')
    if hb_on:
        h = heartbeat[0]
        for field, event, unit in (('hop_enqueues', 'enqueue', 'packets'),
                                   ('hop_dequeues', 'dequeue', 'packets'),
                                   ('hop_bytes', 'enqueue', 'bytes')):
            require(int(h[field]) == sum(totals[k + '_' + event + '_' + unit]
                                        for k in ('hello', 'ack')), 'HB hop totals disagree: ' + field)
        for kind in ('hello', 'ack'):
            require(int(h[kind + '_hop_bytes']) == totals[kind + '_enqueue_bytes'],
                    'HB per-type bytes disagree')
            require(int(h[kind + '_generated']) == totals[kind + '_enqueue_packets'] +
                    totals[kind + '_admission_reject_packets'] + totals[kind + '_queue_reject_packets'],
                    'HB generated/enqueue/reject totals disagree')
        require(int(h['ack_received']) == len(acks), 'accepted ACK raw/count mismatch')
        require(int(h['hello_received']) == len(rows(lines, 'WS29_HELLO')), 'HELLO receive raw/count mismatch')
        unsent = rows(lines, 'WS29_CONTROL_UNSENT')
        require(len(unsent) == counts.get('ack_unsent_packets', 0) and
                all(r['type'] == 'ack' and r['bytes'] == '0' for r in unsent), 'unsent ACK ledger mismatch')
        require(int(h['hop_rejects']) == len(unsent) + sum(totals[k + '_' + e + '_packets']
                for k in ('hello', 'ack') for e in ('admission_reject', 'queue_reject')),
                'HB hop rejection mismatch')
        require(int(h['injected_drops']) == sum(r['event'] in ('single_drop_hello', 'single_drop_ack',
                'drop_hello', 'drop_ack') for r in rows(lines, 'WS21_HEARTBEAT_EVENT')),
                'HB injected drops raw/count mismatch')
        checks = rows(lines, 'WS29_ACK_CHECK')
        require(sum(r['accepted'] == '0' for r in checks) == int(h['rejected']),
                'HB rejected ACK raw evidence missing')
        require(sum(r['accepted'] == '1' for r in checks) == len(acks), 'accepted ACK check missing')
        require(Counter((r['switch'], r['port'], r['time_ns'], r['packet_epoch'], r['packet_sequence'])
                        for r in checks if r['accepted'] == '1') ==
                Counter((r['switch'], r['port'], r['time_ns'], r['epoch'], r['sequence']) for r in acks),
                'ACK checks do not match actual accepted ACK identities')
        require(int(h['event_overflow']) == 0 and int(h['event_rows']) ==
                len(rows(lines, 'WS21_HEARTBEAT_EVENT')), 'HB event overflow/count')
    if cell['label'] == 'k4-c1-normal':
        require(all(totals[k + '_enqueue_packets'] > 0 for k in ('state', 'hello', 'ack')),
                'normal K4 has no joint control opportunity/evidence')
    if arm == 0:
        require(not controls and not any(counts.get(k, 0) for k in counts if
                k.startswith(('state_', 'hello_', 'ack_'))), 'C0 has online control counters')


def host_tors(path):
    lines = path.read_text().splitlines()
    switches = set(map(int, lines[1].split()))
    result = {}
    for line in lines[2:]:
        values = line.split()
        if len(values) < 2:
            continue
        a, b = map(int, values[:2])
        if a not in switches and b in switches:
            result[a] = b
        if b not in switches and a in switches:
            result[b] = a
    return result


def verify_provenance(lines, topology, cell):
    if cell['arm'] < 0:
        return
    hosts = host_tors(topology)
    sends, cache, highwater, barrier, confirmed, active, down = {}, {}, {}, {}, {}, {}, set()
    def identity(r):
        return tuple(int(r[k]) for k in ('session', 'sequence', 'start_ns', 'end_ns', 'ce', 'samples'))
    for line in lines:
        if not line.strip():
            continue
        name = line.split()[0]
        r = dict(w.split('=', 1) for w in line.split()[1:] if '=' in w)
        if name == 'WS29_STATE_SEND':
            require(0 <= int(r['ce']) <= int(r['samples']) and int(r['samples']) > 0 and
                    0 <= int(r['start_ns']) <= int(r['end_ns']) <= int(r['time_ns']) and
                    int(r['session']) > 0 and int(r['sequence']) > 0, 'invalid actual STATE send')
            sends[(r['switch'], r['source_tor'], r['candidate'], identity(r))] = int(r['time_ns'])
        elif name == 'WS29_STATE_CACHE':
            key = (r['switch'], r['destination'], r['candidate'])
            send = sends.get((r['destination'], r['switch'], r['candidate'], identity(r)))
            require(cell['fault'] in (10, 15, 16, 17) or send is not None and
                    0 <= int(r['time_ns']) - send <= 10000,
                    'STATE cache has no earlier matching fresh actual SEND')
            require(int(r['start_ns']) >= barrier.get(r['switch'], 0), 'pre-restart cache admitted')
            require(int(r['session']) >= highwater.get(key, 0), 'cache producer session regressed')
            if key in cache and int(cache[key]['session']) == int(r['session']):
                require(int(r['sequence']) > int(cache[key]['sequence']), 'cache sequence regressed')
            highwater[key] = int(r['session'])
            cache[key] = r
        elif name == 'WS29_SESSION':
            barrier[r['switch']] = int(r['time_ns'])
            cache = {k: v for k, v in cache.items() if k[0] != r['switch']}
            confirmed = {k: v for k, v in confirmed.items() if k[0] != r['switch']}
        elif name == 'WS29_LINK':
            port = (r['switch'], r['port'])
            cache = {k: v for k, v in cache.items() if (k[0], k[2]) != port}
            confirmed.pop(port, None)
            if r['up'] == '0':
                down.add(port)
            else:
                down.discard(port)
        elif name == 'WS21_HEARTBEAT_EVENT':
            key = (r['tor'], r['port'])
            if r['event'] == 'activate':
                active[key] = r['epoch']
                confirmed.pop(key, None)
            elif r['event'] in ('deactivate', 'unknown_timeout', 'unknown_link_down'):
                confirmed.pop(key, None)
                if r['event'] == 'deactivate':
                    active.pop(key, None)
        elif name == 'WS29_ACK':
            key = (r['switch'], r['port'])
            require(active.get(key) == r['epoch'] and key not in down,
                    'accepted ACK lacks current active physical session')
            confirmed[key] = int(r['time_ns'])
        elif name == 'WS29_STATE_REJECT':
            key = (r['switch'], r['destination'], r['candidate'])
            if r['reason'] == 'old_session':
                require(int(r['session']) < highwater.get(key, 0), 'old STATE rejection lacks high-water evidence')
            if r['reason'] == 'before_restart':
                require(int(r['start_ns']) < barrier.get(r['switch'], 0), 'STATE restart rejection lacks barrier')
        elif name == 'WS29_DECISION' and r['reason'] in ('equal_ce', 'distinct_ce'):
            if cell['fault'] in (15, 16, 17):
                continue
            destination = str(hosts[int(r['dst'])])
            for prefix, port in (('a', r['first']), ('b', r['second'])):
                key = (r['switch'], destination, port)
                require(key in cache, 'eligible decision has no current independently recorded cache')
                c = cache[key]
                for decision_key, cache_key in (('session', 'session'), ('sequence', 'sequence'),
                                                ('start', 'start_ns'), ('end', 'end_ns'),
                                                ('ce', 'ce'), ('samples', 'samples')):
                    require(r[prefix + '_' + decision_key] == c[cache_key],
                            'decision does not consume latest actual cache: ' + decision_key)
                ack = confirmed.get((r['switch'], port))
                require((r['switch'], port) not in down and ack is not None and
                        0 <= int(r['time_ns']) - ack <= 800000,
                        'eligible decision lacks live current-session fresh ACK')


def verify_lifecycle(lines, cell, counts):
    if cell['arm'] < 0:
        return
    fault = cell['fault']
    for r in rows(lines, 'WS29_ACK_CHECK'):
        if r['accepted'] == '0':
            for k in ('last_ack', 'missed', 'outstanding', 'epoch'):
                require(r[k + '_before'] == r[k + '_after'], 'invalid ACK mutated ' + k)
        else:
            require(r['accepted'] == '1' and r['last_ack_after'] == r['time_ns'] and
                    r['missed_after'] == r['outstanding_after'] == '0' and
                    r['packet_epoch'] == r['epoch_before'] == r['epoch_after'] and
                    r['packet_sequence'] == r['outstanding_before'] and
                    int(r['outstanding_before']) > 0, 'valid ACK did not confirm current probe')
    if 3 <= fault <= 8:
        injected = rows(lines, 'WS29_ACK_INJECT')
        require(len(injected) == 1, 'injected ACK raw absent')
        r = injected[0]
        for k in ('last_ack', 'missed', 'outstanding', 'epoch'):
            require('invalid_' + k + '_before' in r and 'invalid_' + k + '_after' in r,
                    'ACK injection lacks before/after evidence: ' + k)
            require(r['invalid_' + k + '_before'] == r['invalid_' + k + '_after'],
                    'invalid injected ACK mutated ' + k)
        rejected = [a for a in rows(lines, 'WS29_ACK_CHECK') if a['accepted'] == '0' and
                    a['time_ns'] == r['time_ns']]
        require(len(rejected) == 1, 'injected invalid ACK lacks an actual rejected check')
        if fault == 4:
            accepted = [a for a in rows(lines, 'WS29_ACK_CHECK') if a['accepted'] == '1' and
                        a['time_ns'] == r['time_ns'] and a['switch'] == r['switch'] and a['port'] == r['port']]
            require(len(accepted) == 1 and accepted[0]['last_ack_after'] == r['invalid_last_ack_before'] and
                    r['invalid_outstanding_before'] == '0', 'duplicate case lacks first valid confirmation')
    timers = rows(lines, 'WS29_TIMER')
    for kind, count in (('hb', 'hb_old_timer_ignored'), ('state', 'state_old_timer_ignored')):
        ignored = [r for r in timers if r['kind'] == kind and r['outcome'] == 'ignored']
        require(len(ignored) == counts.get(count, 0), 'old timer raw/count mismatch: ' + kind)
        require(all(int(r['scheduled']) < int(r['current']) for r in ignored),
                'old timer identity not demonstrated')
    if fault in (8, 9):
        sessions, acks = rows(lines, 'WS29_SESSION'), rows(lines, 'WS29_ACK')
        require(any(r['switch'] == str(cell['fault_tor']) and int(r['time_ns']) >= cell['fault_start_ns']
                    for r in sessions), 'actual receiver restart absent')
        require(any(r['switch'] == str(cell['fault_tor']) and
                    int(r['time_ns']) > cell['fault_start_ns'] for r in acks), 'HB did not recover after restart')
    if fault == 10:
        require(any(r['reason'] == 'old_session' for r in rows(lines, 'WS29_STATE_REJECT')),
                'old STATE rejection not independently logged')
    if fault == 11:
        sends, caches = rows(lines, 'WS29_STATE_SEND'), rows(lines, 'WS29_STATE_CACHE')
        fresh = [r for r in sends if r['switch'] == str(cell['fault_tor']) and
                 int(r['sequence']) == 1 and int(r['session']) > 1 and int(r['time_ns']) >= cell['fault_start_ns']]
        require(bool(fresh),
                'STATE rollover has no real new-session sequence-one SEND')
        require(any(old['switch'] == new['switch'] and int(old['session']) + 1 == int(new['session']) and
                    int(old['time_ns']) < cell['fault_start_ns'] for old in sends for new in fresh),
                'STATE rollover lacks actual preceding producer incarnation')
        require(any(c['destination'] == r['switch'] and c['switch'] == r['source_tor'] and
                    all(c[k] == r[k] for k in ('candidate', 'session', 'sequence', 'start_ns', 'end_ns', 'ce', 'samples'))
                    for c in caches for r in fresh),
                'STATE rollover did not reach actual receiver cache')
