"""Integration raw accounting, observed scores, summaries and C1 regressions."""
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import hashlib
import importlib.util
import json


def audit(root):
    helper = root / 'docs/research/evidence/ws31-dynamic-integration-20261101-r1/audit_local_raw.py'
    spec = importlib.util.spec_from_file_location('integration_digest', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    digest = module.digest
    main, ind = root / 'docs/research/ws31/main', root / 'docs/research/ws31/independent'
    report = json.loads((main / 'evidence/c1-controls-pilot-main-acceptance-r1.json').read_text(encoding='utf-8-sig'))
    plan = json.loads((main / 'c1-controls-validation-r1.json').read_text(encoding='utf-8-sig'))
    prior = json.loads((root / 'docs/research/evidence/ws31-c2-label-integration-20261101-r1/snapshots/main/evidence/c2-label-pilot-main-acceptance-r1.json').read_text(encoding='utf-8-sig'))
    assert report['source_objects'] == prior['source_objects']
    for rel, wanted in report['support_hashes'].items():
        assert digest(root / rel.replace('\\', '/')) == wanted, rel
    output, fct_bytes, build_times, start_times = {}, {}, [], []
    result_files = 0
    for entry in report['cells']:
        cell = next(c for c in plan['cells'] if c['id'] == entry['id'])
        base = ind / 'c1-controls-validation-r1-evidence' / entry['id']
        results = base / 'results'
        manifest = json.loads((base / 'remote-manifest.json').read_text(encoding='utf-8-sig'))
        assert manifest['source_head'] == report['source_sha'] == plan['source_sha']
        assert manifest['source_hashes'] == report['source_objects']
        for rel, info in manifest['files'].items():
            path = results / rel
            assert path.stat().st_size == info['bytes'] and digest(path) == info['sha256'], rel
            result_files += 1
        meta = json.loads((results / 'metadata.json').read_text(encoding='utf-8'))
        assert meta['status'] == 'SUCCEEDED' and meta['git_commit'] == plan['source_sha']
        assert meta['algorithm'] == cell['lb'] and meta['concurrency_cap'] == 1 and meta['cpu_jobs'] == 2
        assert meta['parameters']['flow_file'] == cell['flow_file']
        for key, value in plan['common'].items():
            if key != 'max_concurrent':
                assert meta['parameters'][key] == value
        for key in ['ws30_tag_transform', 'ws30_composition', 'ws30_lifecycle', 'ws30_life_profile']:
            assert meta['parameters'].get(key, 0) == 0
        build_times.append(meta['build_finished_utc'])
        start_times.append(meta['started_utc'])
        trace = results / 'config/traffic_trace.txt'
        assert digest(trace) == plan['inputs']['config/' + cell['flow_file']]
        assert digest(results / 'config/topology.txt') == plan['inputs']['config/leaf_spine_128_100G_OS2.txt']
        expected = {}
        sports, dports = defaultdict(lambda: 10000), defaultdict(lambda: 100)
        lines = trace.read_text().splitlines()
        for line in lines[1:]:
            src, dst, _, size, origin, tag = line.split()
            src, dst = int(src), int(dst)
            key = (src, dst, sports[src], dports[dst])
            expected[key] = (int(size), int(Fraction.from_float(float(origin)) * 10**9), int(tag))
            sports[src] += 1
            dports[dst] += 1
        assert len(expected) == int(lines[0]) == cell['flow_count']
        fcts = list((results / 'raw').glob('*/*_out_fct.txt'))
        logs = list((results / 'raw').glob('*/config.log'))
        assert len(fcts) == len(logs) == 1
        completed = {}
        for line in fcts[0].read_text().splitlines():
            row = tuple(map(int, line.split()))
            assert len(row) == 8 and row[:4] in expected and row[:4] not in completed
            assert row[4:6] == expected[row[:4]][:2] and row[6] >= 0 and row[7] > 0
            completed[row[:4]] = row
        assert set(completed) == set(expected) and sum(r[4] for r in completed.values()) == cell['payload_bytes']
        events, ports, summaries, states, decisions = Counter(), {}, {}, {}, []
        hashes = {p: hashlib.sha256() for p in ['WS30_CHOICE', 'WS30_ROUTE', 'WS31_C1_CHOICE']}
        no_category = hashlib.sha256()
        positive = 0
        previous_time = -1
        with logs[0].open(encoding='utf-8') as stream:
            for line in stream:
                assert 'WS30_OBSERVATION_OVERFLOW' not in line
                if not line.startswith(('WS30_', 'WS31_')):
                    continue
                tokens = line.split()
                prefix = tokens[0]
                events[prefix] += 1
                fields = dict(t.split('=', 1) for t in tokens[1:] if '=' in t)
                if prefix in hashes:
                    normalized = ' '.join(t for t in tokens if not t.startswith('uid=')) + '\n'
                    hashes[prefix].update(normalized.encode())
                    now = int(fields['time_ns'])
                    assert now >= previous_time
                    previous_time = now
                if prefix == 'WS30_ROUTE':
                    key = ((int(fields['sip']) >> 8) & 65535, (int(fields['dip']) >> 8) & 65535, int(fields['sport']), int(fields['dport']))
                    assert key in expected and int(fields['tag']) == expected[key][2]
                    assert ports.setdefault((fields['switch'], key), fields['port']) == fields['port']
                if prefix in ['WS30_PATH', 'WS30_QUEUE']:
                    summaries[prefix] = {k: int(v) for k, v in fields.items()}
                if prefix == 'WS31_C1_CHOICE':
                    values = {k: int(v) for k, v in fields.items()}
                    maximum = (1 << 64) - 1
                    first = min(maximum, values['q1'] + values['r1'])
                    second = min(maximum, values['q2'] + values['r2'])
                    assert values['chosen'] == (values['first'] if first <= second else values['second'])
                    positive += int(values['r1'] > 0 or values['r2'] > 0)
                    no_category.update((' '.join(t for t in tokens if not t.startswith('category=')) + '\n').encode())
                    decisions.append(values)
                if prefix == 'WS31_C1_STATE':
                    values = {k: int(v) for k, v in fields.items()}
                    assert values['switch'] not in states and values['conserved'] == 1
                    assert values['ttl_ns'] == 20000 and values['max_entries'] == 65536 and values['max_ranges'] == 32
                    states[values['switch']] = values
        main_cell = json.loads((main / entry['main_receipt']).read_text(encoding='utf-8-sig'))
        assert digest(fcts[0]) == main_cell['fct_sha256'] and digest(logs[0]) == main_cell['log_sha256']
        assert {p: hashes[p].hexdigest() for p in main_cell['ordered_normalized_hashes']} == main_cell['ordered_normalized_hashes']
        assert events['WS30_QP'] == events['WS31_C1_CHOICE'] == cell['flow_count']
        assert events['WS30_QUEUE'] == events['WS30_PATH'] == 1
        assert events['WS30_ROUTE'] == summaries['WS30_PATH']['full_rows']
        assert len(ports) == summaries['WS30_PATH']['switch_qps']
        assert all(summaries['WS30_PATH'][k] == 0 for k in ['changed_qps', 'port_changes', 'rejected'])
        assert summaries['WS30_QUEUE']['enqueued'] == summaries['WS30_QUEUE']['dequeued']
        assert all(summaries['WS30_QUEUE'][k] == 0 for k in ['current', 'dropped', 'admission_dropped_bytes', 'queue_rejected_bytes', 'violations'])
        observed = {'positive_pressure_decisions': positive, 'unique_payload_counter': sum(s['unique_payload'] for s in states.values()), 'predictor_peak': max(s['predictor_peak'] for s in states.values()), 'expired_during_source_arrivals': sum(s['expired'] for s in states.values()), 'retained_predictor_entries_at_summary': sum(s['predictor_entries'] for s in states.values())}
        assert all(observed[key] == entry['mechanism_replay'][key] for key in observed)
        name = entry['id'].split('ws31-c1ctrl-r1-', 1)[1]
        fct_bytes[name] = fcts[0].read_bytes()
        output[name] = {'id': entry['id'], 'mode': cell['lb'], 'flows': cell['flow_count'], 'payload_bytes': cell['payload_bytes'], 'fct_sha256': digest(fcts[0]), 'route_hash_remove_uid': hashes['WS30_ROUTE'].hexdigest(), 'source_choice_hash_all_fields': hashes['WS31_C1_CHOICE'].hexdigest(), 'source_choice_hash_remove_category': no_category.hexdigest(), 'direct_score_decisions_checked': len(decisions), 'observed': observed, 'main_full_model_replay': entry['mechanism_replay'], 'full_model_attribution': 'Main reconstructed R/ledger/history; Integration checks observed Q/R arithmetic and raw summaries, not a duplicate model reconstruction'}
    assert max(build_times) <= min(start_times)
    prior_dynamic = json.loads((root / 'docs/research/evidence/ws31-dynamic-integration-20261101-r1/raw-verification.json').read_text(encoding='utf-8'))
    old = next(c for c in prior_dynamic['cells'] if c['mode'] == 'ws31-c1')
    assert output['size']['fct_sha256'] == old['fct_sha256'] and output['size']['route_hash_remove_uid'] == old['ordered_hashes']['WS30_ROUTE']
    old_log = next((ind / 'main-mode-dynamic-r1-evidence' / old['id'] / 'results/raw').glob('*/config.log'))
    h = hashlib.sha256()
    with old_log.open(encoding='utf-8') as stream:
        for line in stream:
            if line.startswith('WS31_C1_CHOICE '):
                h.update((' '.join(line.split()) + '\n').encode())
    assert output['size']['source_choice_hash_all_fields'] == h.hexdigest()
    assert fct_bytes['unknown-class'] == fct_bytes['unknown-unified']
    assert output['unknown-class']['route_hash_remove_uid'] == output['unknown-unified']['route_hash_remove_uid']
    assert output['unknown-class']['source_choice_hash_remove_category'] == output['unknown-unified']['source_choice_hash_remove_category']
    driver = json.loads((ind / 'c1-controls-validation-r1-receipt.json').read_text(encoding='utf-8-sig'))
    assert driver['network_runs_started'] == 7 and driver['core_tests_executed'] == 0
    return {'scope': 'Integration full accounting/path/observed-score and direct C1 counter checks; full R/history reconstruction remains main-attributed', 'source_sha': report['source_sha'], 'result_files_hashed': result_files, 'support_files_hashed': len(report['support_hashes']), 'fixed_35_source_map_matches_prior_verified_506': True, 'cells': output, 'completed_flow_records': sum(c['flows'] for c in output.values()), 'completed_payload_bytes': sum(c['payload_bytes'] for c in output.values()), 'all_seven_builds_before_any_run': True, 'core_tests_repeated': 0, 'driver_terminal_receipt_utc': driver['updated_utc'], 'history_predictor_zero_not_all_state_zero': True, 'count_modes_not_equal_computational_cost': True, 'unknown_retained_storage_not_forced_to_zero': True, 'remote_access': False, 'simulations_restarted_by_root': False}


if __name__ == '__main__':
    out = Path(__file__).with_name('raw-verification.json')
    if out.exists():
        raise RuntimeError('Refusing to overwrite an existing Integration receipt')
    result = audit(Path.cwd())
    out.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'result_files': result['result_files_hashed'], 'support_files': result['support_files_hashed'], 'cells': len(result['cells']), 'flow_records': result['completed_flow_records'], 'payload_bytes': result['completed_payload_bytes'], 'scores_and_size_unknown_regressions': 'PASS'}))
