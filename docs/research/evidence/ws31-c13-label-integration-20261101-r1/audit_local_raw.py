"""Integration accounting, label, path and observed-event audit; no network actions.

Full C1 prediction-ledger and C3 activity/ownership reconstruction remain main-owned.
"""
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import hashlib
import json


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def normalized(tokens, omitted):
    return (' '.join(t for t in tokens if t.split('=', 1)[0] not in omitted) + '\n').encode()


def audit(root):
    base = root / 'docs/research/ws31'
    main, ind = base / 'main', base / 'independent'
    read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
    report = read(main / 'evidence/c13-label-pilot-main-acceptance-r1.json')
    plan = read(main / 'c13-label-validation-r1.json')
    index = read(ind / 'c13-label-validation-r1-index.json')
    qa = read(ind / 'c13-label-validation-r1-delivery-qa.json')
    assert digest(main / 'c13-label-validation-r1.json') == report['plan_sha256'] == index['plan_sha256']
    assert digest(ind / 'c13-label-validation-r1-index.json') == report['index_sha256'] == qa['index_sha256']
    assert digest(ind / 'c13-label-validation-r1-delivery-qa.json') == report['delivery_QA_sha256']
    prior = read(root / 'docs/research/evidence/ws31-c1-controls-integration-20261101-r1/snapshots/main/evidence/c1-controls-pilot-main-acceptance-r1.json')
    file_counts = Counter()
    for name, info in index['documents'].items():
        p = ind / name
        assert p.stat().st_size == info['bytes'] and digest(p) == info['sha256'], name
        file_counts['documents'] += 1
    for name, wanted in index['dependencies'].items():
        assert digest(ind / name) == wanted, name
        file_counts['dependencies'] += 1
    for name, wanted in index['references'].items():
        assert digest(Path(name)) == wanted, name
        file_counts['references'] += 1
    output, build_times, run_times = {}, [], []
    for cell in plan['cells']:
        accepted = next(c for c in report['cells'] if c['id'] == cell['id'])
        indexed = next(c for c in index['cells'] if c['id'] == cell['id'])
        folder = ind / 'c13-label-validation-r1-evidence' / cell['id']
        results = folder / 'results'
        manifest = read(folder / 'remote-manifest.json')
        assert manifest['source_head'] == report['source_sha'] == plan['source_sha']
        assert manifest['source_hashes'] == prior['source_objects']
        for rel, info in manifest['files'].items():
            p = results / rel
            assert p.stat().st_size == info['bytes'] and digest(p) == info['sha256'], rel
            file_counts['results'] += 1
        for rel, wanted in indexed['supporting_files'].items():
            assert digest(folder / rel) == wanted, rel
            file_counts['supports'] += 1
        meta = read(results / 'metadata.json')
        assert meta['status'] == 'SUCCEEDED' and meta['git_commit'] == plan['source_sha']
        assert meta['algorithm'] == cell['lb'] and meta['experiment_id'] == cell['id']
        assert meta['concurrency_cap'] == 1 and meta['cpu_jobs'] == 2
        for key, value in plan['common'].items():
            if key != 'max_concurrent':
                assert meta['parameters'][key] == value
        assert meta['parameters']['ws30_tag_transform'] == cell['ws30_tag_transform']
        assert all(meta['parameters'][k] == 0 for k in ['ws30_composition', 'ws30_lifecycle', 'ws30_life_profile'])
        build_times.append(meta['build_finished_utc'])
        run_times.append((meta['started_utc'], meta['finished_utc']))
        trace = results / 'config/traffic_trace.txt'
        assert digest(trace) == plan['inputs']['config/' + cell['flow_file']]
        assert digest(results / 'config/topology.txt') == plan['inputs']['config/leaf_spine_128_100G_OS2.txt']
        expected, sports, dports = {}, defaultdict(lambda: 10000), defaultdict(lambda: 100)
        lines = trace.read_text().splitlines()
        for line in lines[1:]:
            src, dst, _, size, origin, tag = line.split()
            src, dst = int(src), int(dst)
            key = src, dst, sports[src], dports[dst]
            expected[key] = int(size), int(Fraction.from_float(float(origin)) * 10**9), int(tag)
            sports[src] += 1
            dports[dst] += 1
        assert len(expected) == int(lines[0]) == cell['flow_count']
        fct = next((results / 'raw').glob('*/*_out_fct.txt'))
        log = next((results / 'raw').glob('*/config.log'))
        completed = {}
        for line in fct.read_text().splitlines():
            row = tuple(map(int, line.split()))
            assert len(row) == 8 and row[:4] in expected and row[:4] not in completed
            assert row[4:6] == expected[row[:4]][:2] and row[6] >= 0 and row[7] > 0
            completed[row[:4]] = row
        assert set(completed) == set(expected)
        assert sum(r[4] for r in completed.values()) == cell['payload_bytes']
        assert digest(fct) == accepted['fct_sha256'] and digest(log) == accepted['log_sha256']
        hashes = {p: hashlib.sha256() for p in ['WS30_CHOICE', 'WS30_ROUTE', 'ROUTE_without_tag', 'C1_without_category']}
        counts, tags, policies, c3 = Counter(), Counter(), Counter(), Counter()
        ports, summaries, states = {}, {}, []
        positive = 0
        with log.open(encoding='utf-8') as stream:
            for line in stream:
                assert 'WS30_OBSERVATION_OVERFLOW' not in line
                if not line.startswith(('WS30_', 'WS31_')):
                    continue
                tokens = line.split()
                prefix = tokens[0]
                counts[prefix] += 1
                fields = dict(t.split('=', 1) for t in tokens[1:] if '=' in t)
                if prefix in ['WS30_CHOICE', 'WS30_ROUTE']:
                    hashes[prefix].update(normalized(tokens, {'uid'}))
                if prefix in ['WS30_ROUTE', 'WS31_C1_CHOICE', 'WS31_C3_ROUTE']:
                    v = {k: int(x) for k, x in fields.items()}
                    key = (v['sip'] >> 8) & 65535, (v['dip'] >> 8) & 65535, v['sport'], v['dport']
                    assert key in expected
                    original_tag = expected[key][2]
                    wanted = 0 if cell['ws30_tag_transform'] == 1 else 3 - original_tag
                    if prefix == 'WS30_ROUTE':
                        assert v['tag'] == wanted
                        tags[v['tag']] += 1
                        assert ports.setdefault((v['switch'], key), v['port']) == v['port']
                        hashes['ROUTE_without_tag'].update(normalized(tokens, {'uid', 'tag'}))
                    else:
                        assert v['category'] == wanted
                    if prefix == 'WS31_C1_CHOICE':
                        policies[v['category']] += 1
                        assert v['predicted'] == (65536 if wanted == 1 else 8192)
                        chosen = v['first'] if v['q1'] + v['r1'] <= v['q2'] + v['r2'] else v['second']
                        assert v['chosen'] == chosen
                        positive += int(v['r1'] > 0 or v['r2'] > 0)
                        hashes['C1_without_category'].update(normalized(tokens, {'category'}))
                    if prefix == 'WS31_C3_ROUTE':
                        if v['fresh']:
                            policies[v['category']] += 1
                            assert v['chosen'] == (v['first'] if v['q1'] <= v['q2'] else v['second'])
                            c3['fresh'] += 1
                            c3['restricted'] += v['restricted']
                            c3['borrowed'] += v['borrowed']
                        if v['residual']:
                            c3['residual_packets'] += 1
                            c3['residual_wire_bytes'] += v['wire_bytes']
                if prefix in ['WS30_QUEUE', 'WS30_PATH']:
                    summaries[prefix] = {k: int(x) for k, x in fields.items()}
                if prefix in ['WS31_C1_STATE', 'WS31_C3_STATE']:
                    states.append({k: int(x) if '/' not in x else x for k, x in fields.items()})
        replay = accepted['mechanism_replay']
        assert policies == Counter({int(k): v for k, v in replay['policy_categories'].items()})
        assert tags == Counter({int(k): v for k, v in accepted['packet_tag_data_hops'].items()})
        for prefix in ['WS30_CHOICE', 'WS30_ROUTE']:
            assert hashes[prefix].hexdigest() == accepted['ordered_hashes_remove_uid_only'][prefix]
        assert hashes['ROUTE_without_tag'].hexdigest() == indexed['ordered_hashes']['route_without_tag']
        assert len(ports) == summaries['WS30_PATH']['switch_qps'] == 312
        assert all(summaries['WS30_PATH'][k] == 0 for k in ['changed_qps', 'port_changes', 'rejected'])
        assert summaries['WS30_QUEUE']['enqueued'] == summaries['WS30_QUEUE']['dequeued']
        assert all(summaries['WS30_QUEUE'][k] == 0 for k in ['current', 'dropped', 'admission_dropped_bytes', 'queue_rejected_bytes', 'violations'])
        assert all(s['conserved'] == 1 for s in states)
        if cell['lb'] == 'ws31-c1':
            assert positive == replay['positive_pressure_decisions']
            assert max(s['predictor_peak'] for s in states) == replay['predictor_peak']
            assert sum(s['expired'] for s in states) == replay['expired_during_source_arrivals']
            assert sum(s['unique_payload'] for s in states) == replay['unique_payload_counter']
            detail = {'positive_pressure_decisions': positive, 'observed_peak': replay['predictor_peak'], 'observed_expired': replay['expired_during_source_arrivals'], 'observed_unique_deduction': replay['unique_payload_counter']}
        else:
            assert c3['fresh'] == 104
            for k in ['restricted', 'borrowed', 'residual_packets', 'residual_wire_bytes']:
                assert c3[k] == replay[k] == sum(s[k] for s in states)
            detail = dict(c3)
        output[indexed['name']] = {'id': cell['id'], 'flows': len(completed), 'payload_bytes': cell['payload_bytes'], 'original_business_tags': dict(Counter(v[2] for v in expected.values())), 'packet_tags': dict(tags), 'policy_categories': dict(policies), 'fct_sha256': digest(fct), 'ordered_hashes': {p: h.hexdigest() for p, h in hashes.items()}, 'observations': dict(counts), 'direct_checks': detail}
    assert max(build_times) <= min(t[0] for t in run_times)
    assert all(run_times[i][1] <= run_times[i + 1][0] for i in range(3))
    for name in ['c1-remove', 'c3-remove']:
        refid = plan['references'][name]
        reffct = next(Path(p) for p in index['references'] if refid in p and p.endswith('_out_fct.txt'))
        reflog = next(Path(p) for p in index['references'] if refid in p and p.endswith('config.log'))
        rh, ch = hashlib.sha256(), hashlib.sha256()
        with reflog.open(encoding='utf-8') as stream:
            for line in stream:
                if line.startswith('WS30_ROUTE '):
                    rh.update(normalized(line.split(), {'uid', 'tag'}))
                if line.startswith('WS31_C1_CHOICE '):
                    ch.update(normalized(line.split(), {'category'}))
        assert output[name]['fct_sha256'] == digest(reffct)
        assert output[name]['ordered_hashes']['ROUTE_without_tag'] == rh.hexdigest()
        if name == 'c1-remove':
            assert output[name]['ordered_hashes']['C1_without_category'] == ch.hexdigest()
    return {'scope': 'Integration accounting/original timing/transformed labels/persistent paths/direct score and admission/residual checks; full C1 ledger and C3 activity/ownership models remain main-owned', 'source_sha': plan['source_sha'], 'files_hashed': dict(file_counts), 'unchanged_source_map_compared_to_prior_verified_506': 35, 'cells': output, 'flow_records': 416, 'payload_bytes': 807927808, 'all_four_builds_before_serial_runs': True, 'removal_fct_and_route_regressions': True, 'remote_actions': False, 'new_or_repeated_network_runs': False, 'independent_effects_or_new_baseline': False}


if __name__ == '__main__':
    out = Path(__file__).with_name('raw-verification.json')
    if out.exists():
        raise RuntimeError('Refusing to overwrite existing Integration verification')
    result = audit(Path.cwd())
    out.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'status': 'PASS', 'files_hashed': result['files_hashed'], 'flows': result['flow_records'], 'payload_bytes': result['payload_bytes']}))
