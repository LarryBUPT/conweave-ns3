"""Integration default-off accounting/events/regression audit; no network actions.

Full prediction/activity model replay remains main-owned. Old logs are read only
for this new default-off event regression, without rerunning old experiments.
"""
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import subprocess


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


PREFIXES = ['WS30_CHOICE', 'WS30_ROUTE', 'WS31_C1_CHOICE', 'WS31_C1_STATE',
            'WS31_C2_DEMAND', 'WS31_C2_LAUNCH', 'WS31_C2_FINISH', 'WS31_C2_STATE',
            'WS31_C3_ROUTE', 'WS31_C3_STATE']


def audit(root):
    read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
    base = root / 'docs/research/ws31'
    ind, main = base / 'independent', base / 'main'
    report = read(main / 'evidence/label-default-pilot-main-acceptance-r1.json')
    plan = read(main / 'label-default-validation-r1.json')
    index = read(ind / 'label-default-validation-r1-index.json')
    qa = read(ind / 'label-default-validation-r1-qa.json')
    assert digest(ind / 'label-default-validation-r1-index.json') == qa['index_sha256'] == report['index_sha256']
    assert digest(ind / 'label-default-validation-r1-qa.json') == report['QA_sha256']
    prior = read(root / 'docs/research/evidence/ws31-label-preflight-integration-20261101-r1/snapshots/independent/label-fixture-preflight-r2-index.json')
    files = Counter()
    for rel, info in index['documents'].items():
        p = ind / rel
        assert p.stat().st_size == info['bytes'] and digest(p) == info['sha256'], rel
        files['documents'] += 1
    for rel, wanted in index['dependencies'].items():
        assert digest(ind / rel) == wanted, rel
        files['dependencies'] += 1
    for path, wanted in index['references'].items():
        assert digest(Path(path)) == wanted, path
        files['references'] += 1
    output, build_times, run_times = {}, [], []
    for cell in plan['cells']:
        indexed = next(c for c in index['cells'] if c['id'] == cell['id'])
        accepted = next(c for c in report['cells'] if c['id'] == cell['id'])
        folder = ind / 'label-default-validation-r1-evidence' / cell['id']
        results = folder / 'results'
        manifest = read(folder / 'remote-manifest.json')
        assert manifest['source_head'] == plan['source_sha'] == report['source_sha']
        assert manifest['source_hashes'] == indexed['source_hashes'] == prior['source_map']
        for rel, info in manifest['files'].items():
            p = results / rel
            assert p.stat().st_size == info['bytes'] and digest(p) == info['sha256'], rel
            files['results'] += 1
        for rel, wanted in indexed['supporting_files'].items():
            assert digest(folder / rel) == wanted, rel
            files['supports'] += 1
        meta = read(results / 'metadata.json')
        assert meta['status'] == 'SUCCEEDED' and meta['git_commit'] == plan['source_sha']
        assert meta['algorithm'] == cell['lb'] and meta['experiment_id'] == cell['id']
        assert meta['cpu_jobs'] == 2 and meta['concurrency_cap'] == 1
        for key, wanted in plan['common'].items():
            if key != 'max_concurrent':
                assert meta['parameters'][key] == wanted
        assert all(meta['parameters'].get(k, 0) == 0 for k in ['ws30_tag_transform', 'ws30_composition', 'ws30_lifecycle', 'ws30_life_profile'])
        build_times.append(meta['build_finished_utc'])
        run_times.append((meta['started_utc'], meta['finished_utc']))
        trace = results / 'config/traffic_trace.txt'
        assert digest(trace) == plan['inputs']['config/' + cell['flow_file']]
        assert digest(results / 'config/topology.txt') == plan['inputs']['config/leaf_spine_128_100G_OS2.txt']
        expected, by_index, sports, dports = {}, {}, defaultdict(lambda: 10000), defaultdict(lambda: 100)
        lines = trace.read_text().splitlines()
        for i, line in enumerate(lines[1:]):
            src, dst, _, size, origin, tag = line.split()
            src, dst = int(src), int(dst)
            key = src, dst, sports[src], dports[dst]
            expected[key] = int(size), int(Fraction.from_float(float(origin)) * 10**9), int(tag)
            by_index[i] = key
            sports[src] += 1
            dports[dst] += 1
        assert len(expected) == int(lines[0]) == cell['flow_count'] == 104
        fct = next((results / 'raw').glob('*/*_out_fct.txt'))
        log = next((results / 'raw').glob('*/config.log'))
        complete = {}
        for line in fct.read_text().splitlines():
            row = tuple(map(int, line.split()))
            assert len(row) == 8 and row[:4] in expected and row[:4] not in complete
            assert row[4:6] == expected[row[:4]][:2] and row[6] >= 0 and row[7] > 0
            complete[row[:4]] = row
        assert set(complete) == set(expected)
        assert sum(r[4] for r in complete.values()) == cell['payload_bytes']
        assert digest(fct) == accepted['fct_sha256'] and digest(log) == accepted['log_sha256']
        hashes = {p: hashlib.sha256() for p in PREFIXES}
        counts, c3 = Counter(), Counter()
        ports, summaries, states, finishes = {}, {}, [], {}
        positive = 0
        with log.open(encoding='utf-8') as stream:
            for line in stream:
                assert 'WS30_OBSERVATION_OVERFLOW' not in line and not line.startswith('WS31_LABEL_')
                if not line.startswith(('WS30_', 'WS31_')):
                    continue
                tokens = line.split()
                prefix = tokens[0]
                counts[prefix] += 1
                fields = dict(t.split('=', 1) for t in tokens[1:] if '=' in t)
                if prefix in hashes:
                    hashes[prefix].update((' '.join(t for t in tokens if not t.startswith('uid=')) + '\n').encode())
                if prefix in ['WS30_ROUTE', 'WS31_C1_CHOICE', 'WS31_C3_ROUTE']:
                    v = {k: int(x) for k, x in fields.items()}
                    key = (v['sip'] >> 8) & 65535, (v['dip'] >> 8) & 65535, v['sport'], v['dport']
                    assert key in expected
                    if prefix == 'WS30_ROUTE':
                        assert v['tag'] == expected[key][2]
                        assert ports.setdefault((v['switch'], key), v['port']) == v['port']
                    else:
                        assert v['category'] == expected[key][2]
                    if prefix == 'WS31_C1_CHOICE':
                        assert v['chosen'] == (v['first'] if v['q1'] + v['r1'] <= v['q2'] + v['r2'] else v['second'])
                        positive += int(v['r1'] > 0 or v['r2'] > 0)
                    if prefix == 'WS31_C3_ROUTE':
                        if v['fresh']:
                            c3['fresh'] += 1
                            c3['restricted'] += v['restricted']
                            c3['borrowed'] += v['borrowed']
                        if v['residual']:
                            c3['residual_packets'] += 1
                            c3['residual_wire_bytes'] += v['wire_bytes']
                if prefix == 'WS31_C2_FINISH':
                    v = {k: int(x) for k, x in fields.items()}
                    i = v['flow_id']
                    assert i in by_index and i not in finishes
                    row = complete[by_index[i]]
                    assert v['demand_ns'] == row[5] and v['size'] == row[4]
                    assert v['finish_ns'] == row[5] + row[6] and v['fct_ns'] == row[6]
                    assert v['launch_ns'] - row[5] == v['wait_ns']
                    finishes[i] = v
                if prefix in ['WS30_PATH', 'WS30_QUEUE']:
                    summaries[prefix] = {k: int(x) for k, x in fields.items()}
                if prefix in ['WS31_C1_STATE', 'WS31_C3_STATE']:
                    states.append({k: int(x) if '/' not in x else x for k, x in fields.items()})
        assert len(ports) == summaries['WS30_PATH']['switch_qps'] == 312
        assert all(summaries['WS30_PATH'][k] == 0 for k in ['changed_qps', 'port_changes', 'rejected'])
        assert summaries['WS30_QUEUE']['enqueued'] == summaries['WS30_QUEUE']['dequeued']
        assert all(summaries['WS30_QUEUE'][k] == 0 for k in ['current', 'dropped', 'admission_dropped_bytes', 'queue_rejected_bytes', 'violations'])
        for p, wanted in accepted['ordered_normalized_hashes'].items():
            assert hashes[p].hexdigest() == wanted
        if cell['lb'] == 'ws31-c1':
            assert positive == 94 and max(s['predictor_peak'] for s in states) == 58
            assert sum(s['unique_payload'] for s in states) == 2239360
        if cell['lb'] == 'ws31-c2':
            assert set(finishes) == set(by_index)
            waits = [v['wait_ns'] for v in finishes.values()]
            assert sum(v > 0 for v in waits) == 80 and sum(waits) == 18002 and max(waits) == 497
        if cell['lb'] == 'ws31-c3':
            assert c3 == Counter(fresh=104, restricted=80, borrowed=4, residual_packets=546, residual_wire_bytes=572208)
        ref = Path(indexed['reference_path'])
        assert digest(next((ref / 'raw').glob('*/*_out_fct.txt'))) == digest(fct)
        ref_hashes = {p: hashlib.sha256() for p in PREFIXES}
        with next((ref / 'raw').glob('*/config.log')).open(encoding='utf-8') as stream:
            for line in stream:
                prefix = line.split(' ', 1)[0]
                if prefix in ref_hashes:
                    ref_hashes[prefix].update((' '.join(t for t in line.split() if not t.startswith('uid=')) + '\n').encode())
        assert all(hashes[p].hexdigest() == ref_hashes[p].hexdigest() for p in PREFIXES)
        output[cell['lb']] = {'id': cell['id'], 'flows': 104, 'payload_bytes': cell['payload_bytes'], 'fct_sha256': digest(fct), 'ordered_uid_only_hashes': {p: h.hexdigest() for p, h in hashes.items()}, 'reference': cell['reference_id'], 'reference_source': cell['reference_sha'], 'whole_FCT_and_all_dedicated_events_equal': True, 'active_label_observations': 0}
    assert max(build_times) <= min(t[0] for t in run_times)
    assert all(run_times[i][1] <= run_times[i + 1][0] for i in range(2))
    nxt = read(main / 'label-dynamic-validation-r1.json')
    impl = root.parent / 'ws31-candidates-implementation'
    git = lambda *args: subprocess.check_output(['git', '-C', str(impl), *args])
    assert git('rev-parse', nxt['source_sha'] + '^').decode().strip() == plan['source_sha']
    assert set(git('diff', '--name-only', plan['source_sha'], nxt['source_sha']).decode().splitlines()) == {'config/ws31_labels_r1.txt', 'scripts/ws31_label_inputs.py'}
    for path, wanted in prior['source_map'].items():
        assert hashlib.sha256(git('show', nxt['source_sha'] + ':' + path)).hexdigest() == wanted
    newinput = git('show', nxt['source_sha'] + ':config/ws31_labels_r1.txt')
    assert hashlib.sha256(newinput).hexdigest() == nxt['inputs']['config/ws31_labels_r1.txt']
    rows = [line.split() for line in newinput.decode().splitlines()[1:]]
    assert len(rows) == 15 and sum(int(r[3]) for r in rows) == 245760
    assert Counter(int(r[5]) for r in rows) == Counter({1: 6, 2: 6, 0: 1, 7: 1, 99: 1})
    assert len({r[3] for r in rows}) == 1 and all(int(r[3]) == 16384 for r in rows)
    assert digest(main / 'label-dynamic-validation-r1.json') == '4dcc993e24db3093f3b7ae5acd0b1dfd1f581fa22455924dccb16fdba4960a90'
    return {'scope': 'Integration full accounting/original demand timing/actual labels/pinning, direct scores/wait totals/counters and full uid-only common+dedicated event regression; full C1/C2/C3 mechanism models main-owned', 'source_sha': plan['source_sha'], 'files_hashed': dict(files), 'source_maps_compared_to_prior_verified': 114, 'unique_source_objects': 38, 'completed_records': 312, 'completed_payload_bytes': 605945856, 'cells': output, 'all_three_builds_before_serial_runs': True, 'new_input_source_sha': nxt['source_sha'], 'new_input_changes_only': ['config/ws31_labels_r1.txt', 'scripts/ws31_label_inputs.py'], 'new_input_source_objects_equal_prior_38': True, 'new_input': {'requests': 15, 'bytes': 245760, 'all_payload_sizes': 16384, 'business_tag_counts': {1: 6, 2: 6, 0: 1, 7: 1, 99: 1}}, 'new_input_real_packet_timing_coverage': 'Not accepted; dynamic target must establish from actual constructions/UID/presence', 'remote_actions': False, 'old_runs_or_cores_repeated': False, 'new_combined_baseline_or_effects_accepted': False}


if __name__ == '__main__':
    out = Path(__file__).with_name('raw-verification.json')
    if out.exists():
        raise RuntimeError('Refusing to overwrite Integration raw verification')
    result = audit(Path.cwd())
    out.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'status': 'PASS', 'files_hashed': result['files_hashed'], 'completed_records': 312, 'completed_payload_bytes': 605945856, 'new_input_code_objects_unchanged': 38}))
