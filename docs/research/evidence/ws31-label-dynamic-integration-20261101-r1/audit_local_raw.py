"""Integration UID/time/presence/accounting audit, not a full budget/quota replay.

Reads fixed Git objects and completed raw files; no experiments or tests run.
"""
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import subprocess


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def tuple_hash(key):
    src, dst, sport, dport = key
    h = 2166136261 ^ 0x43c2a517
    for word in [(11 << 24) | (src << 8) | 1, (11 << 24) | (dst << 8) | 1, sport | (dport << 16)]:
        for shift in range(0, 32, 8):
            h = ((h ^ ((word >> shift) & 255)) * 16777619) & 0xffffffff
    h ^= h >> 16
    h = (h * 0x85ebca6b) & 0xffffffff
    return h ^ (h >> 13)


def key_of(v):
    return (v['sip'] >> 8) & 65535, (v['dip'] >> 8) & 65535, v['sport'], v['dport']


def projection(v):
    return {k: v[k] for k in ['time_ns', 'switch', 'sip', 'dip', 'sport', 'dport', 'first', 'second', 'q1', 'q2', 'chosen']}


def audit(root):
    read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
    b = root / 'docs/research/ws31'
    ind, main = b / 'independent', b / 'main'
    prefix = 'label-dynamic-recovery-r2'
    index = read(ind / (prefix + '-index.json'))
    qa = read(ind / (prefix + '-qa.json'))
    report = read(main / 'evidence/label-dynamic-pilot-main-acceptance-r3.json')
    assert digest(ind / (prefix + '-index.json')) == report['index_sha256'] == qa['index_sha256']
    assert digest(ind / (prefix + '-qa.json')) == report['QA_sha256']
    archived = read(ind / (prefix + '-index-utf8-original.bin'))
    archived_qa = read(ind / (prefix + '-qa-utf8-original.bin'))
    assert digest(ind / (prefix + '-index-utf8-original.bin')) == '5835f2e2c95ca6ebe0bae5273a1355250f70b094a719e2a6952ade801ad59165'
    assert digest(ind / (prefix + '-qa-utf8-original.bin')) == 'd680bc0ecd0587af9a91871de49907b2ef98dc8e08ed1e16bfaf11d23370a449'
    assert archived_qa['index_sha256'] == digest(ind / (prefix + '-index-utf8-original.bin'))
    changed = {k for k in set(index) | set(archived) if index.get(k) != archived.get(k)}
    assert changed == {'documents', 'created_utc'}
    files = Counter()
    for group in ['documents', 'dependencies', 'original_r1_files']:
        for rel, info in index[group].items():
            p = ind / rel
            assert digest(p) == (info['sha256'] if isinstance(info, dict) else info), rel
            if isinstance(info, dict):
                assert p.stat().st_size == info['bytes']
        files[group] = len(index[group])
    for name in ['original_stop_index', 'original_stop_qa', 'original_source_tree', 'main_first8_acceptance']:
        entry = index[name]
        assert digest(Path(entry['path'])) == entry['sha256']
        files['reference_files'] += 1
    assert read(ind / (prefix + '-original-r1-integrity-before.json')) == read(ind / (prefix + '-original-r1-integrity-after.json')) == index['original_r1_files']
    plan = read(main / 'label-dynamic-validation-r1.json')
    recovery = read(main / 'label-dynamic-recovery-r2.json')
    assert digest(main / 'label-dynamic-validation-r1.json') == report['original_plan_sha256']
    assert digest(main / 'label-dynamic-recovery-r2.json') == report['recovery_plan_sha256'] == index['plan_sha256']
    receipt = read(ind / (prefix + '-receipt.json'))
    assert receipt['network_runs_started'] == 2 and receipt['prior_eight_simulation_repeats'] == 0
    assert all(receipt[k] == 0 for k in ['core_tests_executed', 'build_commands', 'sync_commands', 'deploy_commands'])
    assert len(receipt['commands']) == 2 and all(c['operation'] == 'guarded-run' and c['exit_code'] == 0 for c in receipt['commands'])
    assert [c['cell'] for c in receipt['commands']] == recovery['only_pending_ids']
    gate = read(ind / (prefix + '-pending-built-source-cache-gate.json'))
    assert all(c['never_started_raw_empty'] and c['metadata']['status'] == 'BUILT' for c in gate['pending'])
    released = read(ind / (prefix + '-guards-released.json'))
    assert released['status'] == 'RELEASED' and released['recovery_calls_terminal'] == 2
    old_checker = (ind / 'label-dynamic-validation-r1-checker.py').read_text(encoding='utf-8')
    new_checker = (ind / (prefix + '-checker.py')).read_text(encoding='utf-8')
    without_function = new_checker[:new_checker.index('def compare_reference(')] + new_checker[new_checker.index('def verify('):]
    a, z = without_function.index('    if paired:\n'), without_function.index("    return {'status':'PASS',", without_function.index('    if paired:\n'))
    old_a, old_z = old_checker.index('    if paired:\n'), old_checker.index("    return {'status':'PASS',", old_checker.index('    if paired:\n'))
    assert without_function[:a] + old_checker[old_a:old_z] + without_function[z:] == old_checker
    negatives = read(ind / (prefix + '-offline-negative-examples.json'))
    assert len(negatives['examples']) == 3 and all(c['status'] == 'REJECTED_AS_REQUIRED' for c in negatives['examples'])
    cells, source_map = {}, {}
    totals = Counter()
    for idx, cell in enumerate(index['cells']):
        spec = plan['cells'][idx]
        assert cell['id'] == spec['id']
        folder = ind / (('label-dynamic-validation-r1' if idx < 8 else prefix) + '-evidence') / cell['id']
        results = Path(cell['results_path'])
        assert results.resolve() == (folder / 'results').resolve()
        for rel, info in cell['result_files'].items():
            p = results / rel
            assert p.stat().st_size == info['bytes'] and digest(p) == info['sha256']
            files['results'] += 1
        for rel, wanted in cell['supporting_files'].items():
            assert digest(folder / rel) == wanted
            files['supports'] += 1
        assert digest(Path(cell['acceptance_path'])) == cell['acceptance_sha256']
        if not source_map:
            source_map = cell['source_hashes']
        assert source_map == cell['source_hashes'] and len(source_map) == 40
        meta = read(results / 'metadata.json')
        profile = spec['ws31_label_profile']
        assert meta['status'] == 'SUCCEEDED' and meta['git_commit'] == plan['source_sha']
        assert meta['algorithm'] == spec['lb'] and meta['parameters']['ws31_label_profile'] == profile
        for k, wanted in plan['common'].items():
            if k != 'max_concurrent':
                assert meta['parameters'][k] == wanted
        trace = results / 'config/traffic_trace.txt'
        assert digest(trace) == plan['inputs']['config/ws31_labels_r1.txt']
        assert digest(results / 'config/topology.txt') == plan['inputs']['config/leaf_spine_128_100G_OS2.txt']
        expected = {}
        for i, line in enumerate(trace.read_text().splitlines()[1:]):
            src, dst, pg, size, origin, tag = line.split()
            expected[(int(src), int(dst), 10000, 100)] = {'size': int(size), 'origin': int(Fraction.from_float(float(origin)) * 10**9), 'tag': int(tag), 'flow_id': i}
        fct = next((results / 'raw').glob('*/*_out_fct.txt'))
        log = next((results / 'raw').glob('*/config.log'))
        done = {}
        for line in fct.read_text().splitlines():
            r = tuple(map(int, line.split()))
            assert r[:4] in expected and r[:4] not in done
            e = expected[r[:4]]
            assert r[4] == e['size'] and r[5] == e['origin'] and r[6] >= 0
            done[r[:4]] = r
        assert len(done) == 15 and sum(r[4] for r in done.values()) == 245760
        assert digest(fct) == cell['fct_sha256'] and digest(log) == cell['log_sha256']
        packets, routes, side, choices, c1, c3, c2finish, c2demand = {}, [], [], [], [], [], {}, {}
        summaries, states, byflow = {}, [], defaultdict(list)
        route_hash, choice_hash = hashlib.sha256(), hashlib.sha256()
        with log.open(encoding='utf-8') as stream:
            for line in stream:
                assert 'WS30_OBSERVATION_OVERFLOW' not in line
                if not line.startswith(('WS30_', 'WS31_')):
                    continue
                tokens = line.split()
                pre = tokens[0]
                fields = dict(t.split('=', 1) for t in tokens[1:] if '=' in t)
                v = {k: int(x) if '/' not in x else x for k, x in fields.items()}
                if pre == 'WS31_LABEL_PACKET':
                    assert v['uid'] not in packets
                    k = key_of(v);e = expected[k]
                    assert v['generation'] == 0 and v['flow_id'] == e['flow_id'] and v['original'] == e['tag']
                    assert v['demand_ns'] == e['origin'] and v['profile'] == profile
                    elapsed = v['time_ns'] - e['origin'];assert elapsed >= 0
                    present = int(not (profile == 1 and elapsed < 500))
                    swap = (profile == 2 and elapsed >= 500) or (profile == 3 and tuple_hash(k) & 3 == 0)
                    visible = 0 if not present else 3-e['tag'] if swap and e['tag'] in (1, 2) else e['tag']
                    assert (v['present'], v['visible']) == (present, visible)
                    packets[v['uid']] = v;byflow[k].append(v)
                if pre == 'WS30_ROUTE':
                    assert key_of(v) in expected
                    routes.append(v)
                    route_hash.update((' '.join(t for t in tokens if not t.startswith(('uid=', 'tag='))) + '\n').encode())
                if pre == 'WS31_LABEL_ROUTE':
                    side.append(v)
                if pre == 'WS30_CHOICE':
                    choices.append(v)
                    choice_hash.update((' '.join(t for t in tokens if not t.startswith(('uid=', 'tag='))) + '\n').encode())
                if pre == 'WS31_C1_CHOICE':c1.append(v)
                if pre == 'WS31_C3_ROUTE':c3.append(v)
                if pre == 'WS31_C2_FINISH':c2finish[v['flow_id']] = v
                if pre == 'WS31_C2_DEMAND':c2demand[v['flow_id']] = v
                if pre in ['WS30_QUEUE', 'WS30_PATH', 'WS31_C2_STATE']:summaries[pre] = v
                if pre in ['WS31_C1_STATE', 'WS31_C3_STATE']:states.append(v)
        ports, first_route, peruid = {}, {}, Counter()
        for v in routes:
            k = key_of(v)
            assert ports.setdefault((v['switch'], k), v['port']) == v['port']
            first_route.setdefault(k, v)
            peruid[v['uid']] += 1
            if profile:
                p = packets[v['uid']]
                assert key_of(p) == k and p['seq'] == v['seq'] and p['visible'] == v['tag']
        assert len(routes) == 765 and len(ports) == 45
        assert summaries['WS30_QUEUE']['enqueued'] == summaries['WS30_QUEUE']['dequeued']
        assert all(summaries['WS30_QUEUE'][k] == 0 for k in ['dropped', 'current', 'admission_dropped_bytes', 'queue_rejected_bytes', 'violations'])
        assert all(summaries['WS30_PATH'][k] == 0 for k in ['changed_qps', 'port_changes', 'rejected'])
        first_values, coverage = {}, 0
        if profile:
            assert len(packets) == 255 and len(side) == 765 and set(peruid) == set(packets) and set(peruid.values()) == {3}
            route_rows = Counter((v['uid'], v['switch'], v['time_ns'], *key_of(v), v['seq'], v['tag'], v['port']) for v in routes)
            side_rows = Counter()
            for v in side:
                p = packets[v['uid']]
                assert key_of(v) == key_of(p) and v['seq'] == p['seq']
                assert (v['visible'], v['present']) == (p['visible'], p['present'])
                side_rows[(v['uid'], v['switch'], v['time_ns'], *key_of(v), v['seq'], v['visible'], v['port'])] += 1
            assert route_rows == side_rows
            for k, pp in byflow.items():
                pp.sort(key=lambda v: (v['time_ns'], v['uid']))
                assert sum(p['payload'] for p in pp) == expected[k]['size']
                assert sorted((p['seq'], p['payload']) for p in pp) == [(seq, min(1000, 16384-seq)) for seq in range(0, 16384, 1000)]
                first_values[k] = pp[0]['visible']
                if profile in (1, 2):
                    assert pp[0]['time_ns'] - pp[0]['demand_ns'] < 500
                    assert any(p['time_ns'] - p['demand_ns'] >= 500 for p in pp)
                    coverage += 1
            if profile == 3:
                wrong = [k[0] for k, val in first_values.items() if val != expected[k]['tag']]
                assert sorted(wrong) == [1, 7]
        else:
            assert not packets and not side
        detail = {}
        if c1:
            assert len(c1) == 15 and {key_of(v) for v in c1} == set(expected)
            for v in c1:
                assert v['category'] == first_values[key_of(v)]
                assert v['predicted'] == (65536 if v['category'] == 1 else 8192)
                assert v['chosen'] == (v['first'] if v['q1']+v['r1'] <= v['q2']+v['r2'] else v['second'])
            assert sum(v['r1'] > 0 or v['r2'] > 0 for v in c1) == 9
            wanted_unique, retained = (135000, 0) if profile == 1 else (179304, 6)
            assert sum(v['unique_payload'] for v in states) == wanted_unique and sum(v['predictor_entries'] for v in states) == retained
            detail = {'observed_unique_payload': wanted_unique, 'observed_retained_entries': retained}
        if c2finish:
            waits = []
            for k, e in expected.items():
                d, f = c2demand[e['flow_id']], c2finish[e['flow_id']]
                policy = 0 if profile == 1 else 3-e['tag'] if profile == 3 and tuple_hash(k)&3 == 0 and e['tag'] in (1,2) else e['tag']
                wait = tuple_hash(k) % 501 if policy == 2 else 0
                assert d['policy_tag'] == policy and d['tag'] == e['tag'] and d['delay_ns'] == wait
                assert f['wait_ns'] == wait and f['launch_ns'] == e['origin'] + wait
                assert f['demand_ns'] == e['origin'] and f['finish_ns'] == e['origin']+done[k][6] and f['fct_ns'] == done[k][6]
                waits.append(wait)
            assert (sum(x > 0 for x in waits), sum(waits), max(waits)) == {1:(0,0,0),2:(6,1588,413),3:(6,1457,409)}[profile]
            detail = {'exact_C2_hash_waits': 15, 'positive': sum(x>0 for x in waits), 'sum_ns': sum(waits), 'max_ns': max(waits)}
        fresh = [v for v in c3 if v['fresh']]
        if c3:
            assert len(fresh) == 15 and len(choices) == 30
            for v in c3:
                first = first_values[key_of(v)]
                assert v['category'] == (first if first in (1,2) else 0)
            counter = {'restricted':sum(v['restricted'] for v in fresh),'borrowed':sum(v['borrowed'] for v in fresh),'residual_packets':sum(v['residual'] for v in c3),'residual_wire_bytes':sum(v['wire_bytes'] for v in c3 if v['residual'])}
            assert tuple(counter.values()) == {1:(0,0,0,0),2:(6,1,16,16152),3:(11,0,0,0)}[profile]
            for k in counter:assert counter[k] == sum(v[k] for v in states)
            detail = counter
        source_first = [projection(v) for v in fresh] if c3 else [projection(v) for v in choices if v['switch'] == first_route[key_of(v)]['switch']]
        name = cell['id'].split('ws31-labeldyn-r1-',1)[1]
        cells[name] = {'id':cell['id'],'profile':profile,'fct_sha256':digest(fct),'route_without_uid_tag':route_hash.hexdigest(),'choice_without_uid_tag':choice_hash.hexdigest(),'generic_choices':len(choices),'source_first_projection':source_first,'packet_constructions':len(packets),'route_rows':len(routes),'label_routes':len(side),'early_late_requests':coverage,'direct_checks':detail}
        totals.update({'records':15,'payload_bytes':245760,'constructed':len(packets),'routes':len(routes),'label_routes':len(side),'early_late':coverage})
    q = cells['q12']
    for name in ['c2-p1','c3-p1']:
        c = cells[name]
        assert c['fct_sha256'] == q['fct_sha256'] and c['route_without_uid_tag'] == q['route_without_uid_tag']
        if name == 'c2-p1':assert c['generic_choices'] == q['generic_choices'] == 45 and c['choice_without_uid_tag'] == q['choice_without_uid_tag']
        else:assert c['generic_choices'] == 30 and len(c['source_first_projection']) == 15 and c['source_first_projection'] == q['source_first_projection']
    impl = root.parent/'ws31-candidates-implementation'
    git = lambda *args:subprocess.check_output(['git','-C',str(impl),*args])
    for p,h in source_map.items():assert sha(git('show',plan['source_sha']+':'+p)) == h
    tree = git('ls-tree','-r',plan['source_sha'])
    assert tree == (ind/'label-dynamic-validation-r1-source-git-tree.txt').read_bytes() and len(tree.splitlines()) == 4841
    assert totals == Counter(records=150,payload_bytes=2457600,constructed=2295,routes=7650,label_routes=6885,early_late=90)
    return {'status':'PASS_INTEGRATION_DYNAMIC_UID_TIME_PRESENCE_AND_RECOVERY_RECONCILIATION','fixed_source_sha':plan['source_sha'],'files_hashed':dict(files),'fixed_Git_objects_hashed':40,'source_map_entries':400,'fixed_tree_entries':4841,'reseal_changed_only':sorted(changed),'old_utf8_index_QA_archives_valid':True,'checker_only_schema_comparison_changed':True,'three_negative_examples_retained':True,'original_r1_files_immutable':268,'recovery_runs':2,'prior_eight_reruns':0,'new_build_core_sync_deploy':0,'totals':dict(totals),'cells':cells,'full_C1_budget_C3_activity_ownership_models':'Main; direct first policy/score/state counters checked here, full model not repeated','mutable_implementation_worktree_excluded_from_fixed_source_acceptance':True,'remote_actions_or_tests_by_Integration':False,'adapter_lifecycle_or_effects_or_new_baseline_accepted':False}


if __name__ == '__main__':
    out = Path(__file__).with_name('raw-verification.json')
    if out.exists():raise RuntimeError('Refusing to overwrite Integration verification')
    result = audit(Path.cwd())
    out.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({'status':result['status'],'files_hashed':result['files_hashed'],'totals':result['totals']}))
