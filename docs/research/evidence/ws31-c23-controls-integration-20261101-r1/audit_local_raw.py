"""Integration checks for C2/C3 controls; full C3 activity model is main-owned."""
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
    main, ind = root / 'docs/research/ws31/main', root / 'docs/research/ws31/independent'
    report = json.loads((main / 'evidence/c23-controls-pilot-main-acceptance-r1.json').read_text(encoding='utf-8-sig'))
    plan = json.loads((main / 'c23-controls-validation-r1.json').read_text(encoding='utf-8-sig'))
    prior = json.loads((root / 'docs/research/evidence/ws31-c1-controls-integration-20261101-r1/snapshots/main/evidence/c1-controls-pilot-main-acceptance-r1.json').read_text(encoding='utf-8-sig'))
    assert report['source_objects'] == prior['source_objects']
    for rel, wanted in report['support_hashes'].items():
        assert digest(root / rel.replace('\\', '/')) == wanted, rel
    output, build_times, start_times = {}, [], []
    result_count = 0
    prefixes = ['WS30_CHOICE', 'WS30_ROUTE', 'WS31_C2_DEMAND', 'WS31_C2_LAUNCH', 'WS31_C2_FINISH', 'WS31_C3_ROUTE', 'WS31_C3_STATE']
    for entry in report['cells']:
        cell = next(c for c in plan['cells'] if c['id'] == entry['id'])
        base = ind / 'c23-controls-validation-r1-evidence' / entry['id']
        results = base / 'results'
        manifest = json.loads((base / 'remote-manifest.json').read_text(encoding='utf-8-sig'))
        assert manifest['source_head'] == plan['source_sha'] == report['source_sha']
        assert manifest['source_hashes'] == prior['source_objects']
        for rel, info in manifest['files'].items():
            path = results / rel
            assert path.stat().st_size == info['bytes'] and digest(path) == info['sha256'], rel
            result_count += 1
        meta = json.loads((results / 'metadata.json').read_text(encoding='utf-8'))
        assert meta['status'] == 'SUCCEEDED' and meta['git_commit'] == plan['source_sha'] and meta['algorithm'] == cell['lb']
        assert meta['concurrency_cap'] == 1 and meta['cpu_jobs'] == 2
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
        expected, by_index = {}, {}
        sports, dports = defaultdict(lambda: 10000), defaultdict(lambda: 100)
        lines = trace.read_text().splitlines()
        for i, line in enumerate(lines[1:]):
            src, dst, _, size, origin, tag = line.split()
            src, dst = int(src), int(dst)
            key = (src, dst, sports[src], dports[dst])
            expected[key] = (int(size), int(Fraction.from_float(float(origin)) * 10**9), int(tag))
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
        assert set(completed) == set(expected) and sum(r[4] for r in completed.values()) == cell['payload_bytes']
        hashes = {p: hashlib.sha256() for p in prefixes}
        ports, addresses, summaries, finishes, states = {}, {}, {}, {}, {}
        c3 = Counter()
        with logs[0].open(encoding='utf-8') as stream:
            for line in stream:
                assert 'WS30_OBSERVATION_OVERFLOW' not in line
                if not line.startswith(('WS30_', 'WS31_')):
                    continue
                tokens = line.split()
                prefix = tokens[0]
                fields = dict(t.split('=', 1) for t in tokens[1:] if '=' in t)
                if prefix in hashes:
                    hashes[prefix].update((' '.join(t for t in tokens if not t.startswith('uid=')) + '\n').encode())
                if prefix == 'WS30_ROUTE':
                    sip, dip = int(fields['sip']), int(fields['dip'])
                    key = ((sip >> 8) & 65535, (dip >> 8) & 65535, int(fields['sport']), int(fields['dport']))
                    assert key in expected and int(fields['tag']) == expected[key][2]
                    assert ports.setdefault((fields['switch'], key), fields['port']) == fields['port']
                    addresses[key] = (sip, dip)
                if prefix in ['WS30_PATH', 'WS30_QUEUE', 'WS31_C2_STATE']:
                    summaries[prefix] = {k: int(v) for k, v in fields.items()}
                if prefix == 'WS31_C2_FINISH':
                    values = {k: int(v) for k, v in fields.items()}
                    i = values['flow_id']
                    assert i in by_index and i not in finishes
                    row = completed[by_index[i]]
                    assert values['demand_ns'] == row[5] and values['size'] == row[4]
                    assert values['finish_ns'] == row[5] + row[6] and values['fct_ns'] == row[6]
                    assert values['launch_ns'] - row[5] == values['wait_ns']
                    finishes[i] = values
                if prefix == 'WS31_C3_ROUTE':
                    values = {k: int(v) for k, v in fields.items()}
                    key = ((values['sip'] >> 8) & 65535, (values['dip'] >> 8) & 65535, values['sport'], values['dport'])
                    assert key in expected
                    policy = expected[key][2] if expected[key][2] in [1, 2] else 0
                    assert values['category'] == policy
                    if values['fresh']:
                        assert values['chosen'] == (values['first'] if values['q1'] <= values['q2'] else values['second'])
                        c3['fresh'] += 1
                        c3['restricted'] += values['restricted']
                        c3['borrowed'] += values['borrowed']
                    if values['residual']:
                        c3['residual_packets'] += 1
                        c3['residual_wire_bytes'] += values['wire_bytes']
                if prefix == 'WS31_C3_STATE':
                    assert fields['switch'] not in states and int(fields['conserved']) == 1
                    assert int(fields['activity_ns']) == 20000 and fields['pinning'] == '1'
                    states[fields['switch']] = fields
        checked = json.loads((main / entry['main_receipt']).read_text(encoding='utf-8-sig'))
        assert digest(fcts[0]) == checked['fct_sha256'] and digest(logs[0]) == checked['log_sha256']
        assert {p: hashes[p].hexdigest() for p in checked['ordered_normalized_hashes']} == checked['ordered_normalized_hashes']
        assert len(ports) == summaries['WS30_PATH']['switch_qps']
        assert all(summaries['WS30_PATH'][k] == 0 for k in ['changed_qps', 'port_changes', 'rejected'])
        assert summaries['WS30_QUEUE']['enqueued'] == summaries['WS30_QUEUE']['dequeued']
        assert all(summaries['WS30_QUEUE'][k] == 0 for k in ['current', 'dropped', 'admission_dropped_bytes', 'queue_rejected_bytes', 'violations'])
        detail = {}
        if cell['lb'].startswith('ws31-c2'):
            assert set(finishes) == set(by_index)
            waits = []
            for i, key in by_index.items():
                sip, dip = addresses[key]
                eligible = cell['lb'] == 'ws31-c2-unified' or expected[key][0] == 8192
                wanted = start_hash(sip, dip, key[2], key[3]) % 501 if eligible else 0
                assert finishes[i]['wait_ns'] == wanted
                waits.append(wanted)
            replay = entry['control_replay']
            assert sum(v > 0 for v in waits) == replay['positive_waits'] and sum(waits) == replay['wait_sum_ns'] and max(waits) == replay['wait_max_ns']
            detail = {'exact_hash_waits': len(waits), 'positive': sum(v > 0 for v in waits), 'sum_ns': sum(waits), 'max_ns': max(waits)}
        else:
            replay = entry['control_replay']
            assert c3['fresh'] == cell['flow_count']
            for key in ['restricted', 'borrowed', 'residual_packets', 'residual_wire_bytes']:
                assert c3[key] == replay[key] == sum(int(s[key]) for s in states.values())
            assert sum(int(s['moe_activations']) for s in states.values()) == replay['tag2_activations']
            detail = dict(c3)
            detail['full_activity_and_ownership_reconstruction'] = 'main-attributed; not independently rerun by Integration'
        name = entry['id'].split('ws31-c23ctrl-r1-', 1)[1]
        output[name] = {'id': entry['id'], 'flows': cell['flow_count'], 'payload_bytes': cell['payload_bytes'], 'fct_sha256': digest(fcts[0]), 'ordered_hashes': {p: h.hexdigest() for p, h in hashes.items()}, 'direct_checks': detail, 'main_control_replay': entry['control_replay']}
    assert max(build_times) <= min(start_times)
    label_prior = json.loads((root / 'docs/research/evidence/ws31-c2-label-integration-20261101-r1/raw-verification.json').read_text(encoding='utf-8'))
    dynamic_prior = json.loads((root / 'docs/research/evidence/ws31-dynamic-integration-20261101-r1/raw-verification.json').read_text(encoding='utf-8'))
    ref_c2 = label_prior['cells']['default']
    assert output['c2-size']['fct_sha256'] == ref_c2['fct_sha256']
    for prefix in ['WS30_CHOICE', 'WS30_ROUTE']:
        assert output['c2-size']['ordered_hashes'][prefix] == ref_c2['ordered_hashes']['uid'][prefix]
    ref_c3 = next(c for c in dynamic_prior['cells'] if c['mode'] == 'ws31-c3')
    assert output['c3-size']['fct_sha256'] == ref_c3['fct_sha256']
    assert output['c3-size']['ordered_hashes']['WS30_ROUTE'] == ref_c3['ordered_hashes']['WS30_ROUTE']
    unknown = label_prior['cells']['unknown-q12']
    assert output['c3-unknown']['fct_sha256'] == unknown['fct_sha256']
    assert output['c3-unknown']['ordered_hashes']['WS30_ROUTE'] == unknown['ordered_hashes']['uid']['WS30_ROUTE']
    for name, folder, ident, wanted_prefixes in [
        ('c2-size', 'c2-label-validation-r1-evidence/attempt2', '20261101-074000-ws31-c2tag-r1-default', ['WS31_C2_DEMAND', 'WS31_C2_LAUNCH', 'WS31_C2_FINISH']),
        ('c3-size', 'main-mode-dynamic-r1-evidence', ref_c3['id'], ['WS31_C3_ROUTE', 'WS31_C3_STATE']),
    ]:
        old_log = next((ind / folder / ident / 'results/raw').glob('*/config.log'))
        ref = {p: hashlib.sha256() for p in wanted_prefixes}
        with old_log.open(encoding='utf-8') as stream:
            for line in stream:
                prefix = line.split(' ', 1)[0]
                if prefix in ref:
                    ref[prefix].update((' '.join(t for t in line.split() if not t.startswith('uid=')) + '\n').encode())
        assert all(output[name]['ordered_hashes'][p] == h.hexdigest() for p, h in ref.items())
    return {'scope': 'Integration complete accounting/path/C2 exact waits and observed C3 admission/residual counters; full C3 activity model main-attributed', 'source_sha': report['source_sha'], 'result_files_hashed': result_count, 'support_files_hashed': len(report['support_hashes']), 'source_map_reused_from_prior_verified_506': 35, 'cells': output, 'completed_flow_records': sum(c['flows'] for c in output.values()), 'completed_payload_bytes': sum(c['payload_bytes'] for c in output.values()), 'all_five_builds_before_runs': True, 'size_and_unknown_regressions_pass': True, 'old_reference_logs_read_only_for_new_auxiliary_regression': True, 'remote_access': False, 'new_or_repeated_network_runs': False, 'independent_effects_validated': False}


if __name__ == '__main__':
    out = Path(__file__).with_name('raw-verification.json')
    if out.exists():
        raise RuntimeError('Refusing to overwrite an existing Integration receipt')
    result = audit(Path.cwd())
    out.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'result_files': result['result_files_hashed'], 'support_files': result['support_files_hashed'], 'cells': len(result['cells']), 'flow_records': result['completed_flow_records'], 'payload_bytes': result['completed_payload_bytes'], 'direct_wait_counter_and_regression_checks': 'PASS'}))
