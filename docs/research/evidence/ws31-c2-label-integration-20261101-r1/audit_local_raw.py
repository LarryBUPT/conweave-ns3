"""Read-only Integration audit of C2 decision/packet labels and regressions."""
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import hashlib
import importlib.util
import json


def audit(root):
    helper = root / 'docs/research/evidence/ws31-dynamic-integration-20261101-r1/audit_local_raw.py'
    spec = importlib.util.spec_from_file_location('prior_integration_helpers', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    digest, start_hash = module.digest, module.start_hash
    main = root / 'docs/research/ws31/main'
    ind = root / 'docs/research/ws31/independent'
    report = json.loads((main / 'evidence/c2-label-pilot-main-acceptance-r1.json').read_text(encoding='utf-8-sig'))
    plan = json.loads((main / 'c2-label-validation-r1.json').read_text(encoding='utf-8-sig'))
    prior_manifest = root / 'docs/research/evidence/ws31-zero-control-integration-20261101-r1/snapshots/20261101-062753-ws31-zr1-q12/remote-manifest.json'
    expected_sources = json.loads(prior_manifest.read_text(encoding='utf-8-sig'))['source_hashes']
    fix_record = json.loads((root / 'docs/research/evidence/ws31-dynamic-integration-20261101-r1/verification.json').read_text(encoding='utf-8'))
    for item in fix_record['source_fix']['static_source_object_checks']:
        expected_sources[item['path']] = item['sha256']
    assert expected_sources == report['source_objects']
    for rel, wanted in report['support_hashes'].items():
        assert digest(root / rel.replace('\\', '/')) == wanted, rel
    cell_results, fct_contents, build_times, start_times = {}, {}, [], []
    result_file_count = 0
    for entry in report['cells']:
        cell = next(c for c in plan['cells'] if c['id'] == entry['id'])
        base = ind / 'c2-label-validation-r1-evidence/attempt2' / entry['id']
        results = base / 'results'
        manifest = json.loads((base / 'remote-manifest.json').read_text(encoding='utf-8-sig'))
        assert manifest['source_head'] == plan['source_sha'] == report['source_sha']
        assert manifest['source_hashes'] == expected_sources
        for rel, info in manifest['files'].items():
            path = results / rel
            assert path.stat().st_size == info['bytes'] and digest(path) == info['sha256'], rel
            result_file_count += 1
        meta = json.loads((results / 'metadata.json').read_text(encoding='utf-8'))
        assert meta['status'] == 'SUCCEEDED' and meta['git_commit'] == plan['source_sha']
        assert meta['algorithm'] == cell['lb'] and meta['concurrency_cap'] == 1 and meta['cpu_jobs'] == 2
        assert meta['parameters']['flow_file'] == cell['flow_file']
        assert meta['parameters'].get('ws30_tag_transform', 0) == cell['ws30_tag_transform']
        for key, wanted in plan['common'].items():
            if key != 'max_concurrent':
                assert meta['parameters'][key] == wanted
        build_times.append(meta['build_finished_utc'])
        start_times.append(meta['started_utc'])
        trace = results / 'config/traffic_trace.txt'
        assert digest(trace) == plan['inputs']['config/' + cell['flow_file']]
        assert digest(results / 'config/topology.txt') == plan['inputs']['config/leaf_spine_128_100G_OS2.txt']
        expected, by_index = {}, {}
        sports, dports = defaultdict(lambda: 10000), defaultdict(lambda: 100)
        lines = trace.read_text().splitlines()
        transform = cell['ws30_tag_transform']
        for i, line in enumerate(lines[1:]):
            src, dst, _, size, start, tag = line.split()
            src, dst, size, tag = int(src), int(dst), int(size), int(tag)
            policy = 0 if transform == 1 else 3 - tag if transform == 2 and tag in [1, 2] else tag
            key = (src, dst, sports[src], dports[dst])
            expected[key] = (size, int(Fraction.from_float(float(start)) * 10**9), tag, policy)
            by_index[i] = key
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
        assert set(completed) == set(expected)
        assert sum(row[4] for row in completed.values()) == cell['payload_bytes']
        demands, launches, finishes, ports, addresses, summaries = {}, {}, {}, {}, {}, {}
        events, packet_tags = Counter(), Counter()
        hashes = {kind: {p: hashlib.sha256() for p in ['WS30_CHOICE', 'WS30_ROUTE']} for kind in ['uid', 'uid_tag']}
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
                if prefix in hashes['uid']:
                    for kind, removed in [('uid', ('uid=',)), ('uid_tag', ('uid=', 'tag='))]:
                        hashes[kind][prefix].update((' '.join(t for t in tokens if not t.startswith(removed)) + '\n').encode())
                    now = int(fields['time_ns'])
                    assert now >= previous_time
                    previous_time = now
                if prefix == 'WS30_CHOICE':
                    assert int(fields['tag']) == 0
                if prefix == 'WS30_ROUTE':
                    sip, dip = int(fields['sip']), int(fields['dip'])
                    key = ((sip >> 8) & 65535, (dip >> 8) & 65535, int(fields['sport']), int(fields['dport']))
                    assert key in expected and int(fields['tag']) == expected[key][3]
                    packet_tags[fields['tag']] += 1
                    assert addresses.setdefault(key, (sip, dip)) == (sip, dip)
                    assert ports.setdefault((fields['switch'], key), fields['port']) == fields['port']
                if prefix in ['WS30_QUEUE', 'WS30_PATH', 'WS31_C2_STATE']:
                    summaries[prefix] = {k: int(v) for k, v in fields.items()}
                if prefix in ['WS31_C2_DEMAND', 'WS31_C2_LAUNCH', 'WS31_C2_FINISH']:
                    values = {k: int(v) for k, v in fields.items()}
                    dest = {'WS31_C2_DEMAND': demands, 'WS31_C2_LAUNCH': launches, 'WS31_C2_FINISH': finishes}[prefix]
                    i = values['flow_id']
                    assert i in by_index and i not in dest
                    dest[i] = values
        assert events['WS30_QP'] == cell['flow_count'] and events['WS30_QUEUE'] == events['WS30_PATH'] == 1
        assert events['WS30_ROUTE'] == summaries['WS30_PATH']['full_rows']
        assert len(ports) == summaries['WS30_PATH']['switch_qps']
        assert all(summaries['WS30_PATH'][k] == 0 for k in ['changed_qps', 'port_changes', 'rejected'])
        assert summaries['WS30_QUEUE']['enqueued'] == summaries['WS30_QUEUE']['dequeued']
        assert all(summaries['WS30_QUEUE'][k] == 0 for k in ['current', 'dropped', 'admission_dropped_bytes', 'queue_rejected_bytes', 'violations'])
        waits = []
        if cell['lb'] == 'ws31-c2':
            assert set(demands) == set(launches) == set(finishes) == set(by_index)
            for i, key in by_index.items():
                size, origin, original_tag, policy = expected[key]
                sip, dip = addresses[key]
                wanted = start_hash(sip, dip, key[2], key[3]) % 501 if policy == 2 else 0
                d, l, f = demands[i], launches[i], finishes[i]
                assert d['tag'] == original_tag and d['policy_tag'] == policy and d['tag_transform'] == transform
                assert d['demand_ns'] == l['demand_ns'] == f['demand_ns'] == origin
                assert d['size'] == l['size'] == f['size'] == size
                assert d['delay_ns'] == l['wait_ns'] == f['wait_ns'] == wanted
                assert l['launch_ns'] == f['launch_ns'] == origin + wanted
                row = completed[key]
                assert f['finish_ns'] == origin + row[6] and f['fct_ns'] == row[6]
                waits.append(wanted)
            state = summaries['WS31_C2_STATE']
            assert all(state[k] == cell['flow_count'] for k in ['demanded', 'launched', 'finished'])
            assert all(state[k] == 0 for k in ['pending', 'unfinished', 'cancelled', 'cancel_bytes'])
            assert all(state[k] == cell['payload_bytes'] for k in ['demand_bytes', 'launch_bytes', 'finish_bytes'])
        assert sum(v > 0 for v in waits) == entry['positive_waits']
        assert sum(waits) == entry['wait_sum_ns'] and max(waits, default=0) == entry['wait_max_ns']
        name = entry['id'].split('ws31-c2tag-r1-', 1)[1]
        fct_contents[name] = fcts[0].read_bytes()
        cell_results[name] = {'id': entry['id'], 'flows': cell['flow_count'], 'payload_bytes': cell['payload_bytes'], 'fct_sha256': digest(fcts[0]), 'ordered_hashes': {kind: {p: h.hexdigest() for p, h in value.items()} for kind, value in hashes.items()}, 'original_business_tags': dict(Counter(v[2] for v in expected.values())), 'actual_route_tag_hops': dict(packet_tags), 'C2_exact_rows': len(waits), 'positive_waits': sum(v > 0 for v in waits), 'wait_sum_ns': sum(waits), 'wait_max_ns': max(waits, default=0), 'choice_tag_literal_zero_checked': True}
    assert max(build_times) <= min(start_times)
    prior_dynamic = json.loads((root / 'docs/research/evidence/ws31-dynamic-integration-20261101-r1/raw-verification.json').read_text(encoding='utf-8'))
    old_c2 = next(c for c in prior_dynamic['cells'] if c['mode'] == 'ws31-c2')
    assert cell_results['default']['fct_sha256'] == old_c2['fct_sha256']
    assert cell_results['default']['ordered_hashes']['uid'] == old_c2['ordered_hashes']
    old_q12 = ind / 'zero-control-pilot-r1-evidence/20261101-062753-ws31-zr1-q12/results'
    old_fct = next((old_q12 / 'raw').glob('*/*_out_fct.txt'))
    assert fct_contents['remove'] == old_fct.read_bytes()
    ref_hash = {p: hashlib.sha256() for p in ['WS30_CHOICE', 'WS30_ROUTE']}
    with next((old_q12 / 'raw').glob('*/config.log')).open(encoding='utf-8') as stream:
        for line in stream:
            if line.startswith(('WS30_CHOICE ', 'WS30_ROUTE ')):
                tokens = line.split()
                ref_hash[tokens[0]].update((' '.join(t for t in tokens if not t.startswith(('uid=', 'tag='))) + '\n').encode())
    assert cell_results['remove']['ordered_hashes']['uid_tag'] == {p: h.hexdigest() for p, h in ref_hash.items()}
    assert fct_contents['unknown-c2'] == fct_contents['unknown-q12']
    assert cell_results['unknown-c2']['ordered_hashes']['uid'] == cell_results['unknown-q12']['ordered_hashes']['uid']
    default_base = ind / 'c2-label-validation-r1-evidence/attempt2/20261101-074000-ws31-c2tag-r1-default/results'
    core = json.loads((default_base / 'technical/c2-core/receipt.json').read_text(encoding='utf-8'))
    assert core['status'] == 'PASS' and all(s['exit_code'] == 0 for s in core['steps'])
    assert all('-DNDEBUG' not in s['argv'] for s in core['steps']) and core['assertions_enabled_symbol'] == '__assert_fail'
    assert 'policy-tag' in (default_base / 'logs/c2-core-run.log').read_text(encoding='utf-8')
    assert digest(default_base / 'technical/c2-core/ws31-start-test') == core['binary_sha256']
    return {'scope': 'Integration local all-input labels, exact waits, timing, paths, regression and copied core artifacts; no remote execution or independent efficacy', 'source_sha': report['source_sha'], 'result_files_hashed': result_file_count, 'support_files_hashed': len(report['support_hashes']), 'fixed_35_object_map_composed_from_prior_c4_and_three_verified_506_changes': True, 'cells': cell_results, 'completed_flow_records': sum(c['flows'] for c in cell_results.values()), 'completed_payload_bytes': sum(c['payload_bytes'] for c in cell_results.values()), 'all_five_builds_before_any_run': True, 'core_artifacts_and_PASS_checked': True, 'copied_core_binary_hash_checked': True, 'core_binary_executed_by_root': False, 'old_q12_log_read_only_for_new_planned_uid_tag_normalization': True, 'new_or_repeated_simulations': False}


if __name__ == '__main__':
    out = Path(__file__).with_name('raw-verification.json')
    if out.exists():
        raise RuntimeError('Refusing to overwrite an existing Integration receipt')
    result = audit(Path.cwd())
    out.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'result_files': result['result_files_hashed'], 'support_files': result['support_files_hashed'], 'cells': len(result['cells']), 'completed_flow_records': result['completed_flow_records'], 'completed_payload_bytes': result['completed_payload_bytes'], 'core_PASS_and_default_remove_swap_unknown': True}))
