"""Read-only Integration checks, separate from the main mechanism replay."""
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import hashlib
import json


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def start_hash(sip, dip, sport, dport):
    h = 2166136261 ^ 0x43c2a517
    for word in [sip, dip, sport | (dport << 16)]:
        for offset in [0, 8, 16, 24]:
            h = ((h ^ ((word >> offset) & 255)) * 16777619) & 0xffffffff
    h ^= h >> 16
    h = (h * 0x85ebca6b) & 0xffffffff
    return h ^ (h >> 13)


def audit(root):
    main = root / 'docs/research/ws31/main'
    independent = root / 'docs/research/ws31/independent'
    report = json.loads((main / 'evidence/dynamic-main-modes-main-acceptance-r1.json').read_text(encoding='utf-8-sig'))
    plan = json.loads((main / 'main-mode-dynamic-r1.json').read_text(encoding='utf-8-sig'))
    previous = root / 'docs/research/evidence/ws31-zero-control-integration-20261101-r1/snapshots/20261101-062753-ws31-zr1-q12/remote-manifest.json'
    prior_sources = json.loads(previous.read_text(encoding='utf-8-sig'))['source_hashes']
    support_checks = []
    for rel, wanted in report['support_hashes'].items():
        path = root / rel.replace('\\', '/')
        assert digest(path) == wanted, rel
        support_checks.append({'path': path.relative_to(root).as_posix(), 'sha256': wanted})
    result_checks = 0
    cells = []
    for entry in report['cells']:
        base = independent / 'main-mode-dynamic-r1-evidence' / entry['id']
        results = base / 'results'
        manifest = json.loads((base / 'remote-manifest.json').read_text(encoding='utf-8-sig'))
        assert manifest['source_head'] == report['source_sha'] == plan['source_sha']
        assert manifest['source_hashes'] == report['source_objects'] == prior_sources
        for rel, info in manifest['files'].items():
            path = results / rel
            assert path.stat().st_size == info['bytes'] and digest(path) == info['sha256'], str(path)
            result_checks += 1
        meta = json.loads((results / 'metadata.json').read_text(encoding='utf-8-sig'))
        assert meta['status'] == 'SUCCEEDED' and meta['git_commit'] == report['source_sha']
        assert meta['experiment_id'] == entry['id'] and meta['algorithm'] == entry['mode']
        assert meta['concurrency_cap'] == 1
        for key, wanted in plan['common'].items():
            if key != 'max_concurrent':
                assert meta['parameters'][key] == wanted, key
        assert meta['parameters'].get('ws30_tag_transform', 0) == 0
        trace = results / 'config/traffic_trace.txt'
        assert digest(trace) == plan['inputs']['config/ws31_correctness_r1.txt']
        assert digest(results / 'config/topology.txt') == plan['inputs']['config/leaf_spine_128_100G_OS2.txt']
        expected, by_index = {}, {}
        sports = defaultdict(lambda: 10000)
        dports = defaultdict(lambda: 100)
        lines = trace.read_text().splitlines()
        for i, line in enumerate(lines[1:]):
            src, dst, _, size, start, tag = line.split()
            src, dst, size, tag = int(src), int(dst), int(size), int(tag)
            key = (src, dst, sports[src], dports[dst])
            expected[key] = (size, int(Fraction.from_float(float(start)) * 10**9), tag)
            by_index[i] = key
            sports[src] += 1
            dports[dst] += 1
        assert len(expected) == int(lines[0]) == 104
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
        payload = sum(row[4] for row in completed.values())
        assert payload == 201981952
        events, summaries, ports, addresses, finishes = Counter(), {}, {}, {}, {}
        hashes = {name: hashlib.sha256() for name in ['WS30_CHOICE', 'WS30_ROUTE']}
        previous_time = -1
        with logs[0].open(encoding='utf-8') as stream:
            for line in stream:
                assert 'WS30_OBSERVATION_OVERFLOW' not in line
                if not line.startswith(('WS30_', 'WS31_')):
                    continue
                tokens = line.split()
                prefix = tokens[0]
                events[prefix] += 1
                fields = dict(token.split('=', 1) for token in tokens[1:] if '=' in token)
                if prefix in hashes:
                    hashes[prefix].update((' '.join(t for t in tokens if not t.startswith('uid=')) + '\n').encode())
                    now = int(fields['time_ns'])
                    assert now >= previous_time
                    previous_time = now
                if prefix.endswith('_STATE') or prefix in ['WS30_QUEUE', 'WS30_PATH']:
                    summaries[prefix] = fields
                if prefix == 'WS30_ROUTE':
                    sip, dip = int(fields['sip']), int(fields['dip'])
                    key = ((sip >> 8) & 65535, (dip >> 8) & 65535, int(fields['sport']), int(fields['dport']))
                    assert key in expected
                    assert ports.setdefault((fields['switch'], key), fields['port']) == fields['port']
                    assert addresses.setdefault(key, (sip, dip)) == (sip, dip)
                if prefix == 'WS31_C2_FINISH':
                    values = {key: int(value) for key, value in fields.items()}
                    i = values['flow_id']
                    assert i in by_index and i not in finishes
                    row = completed[by_index[i]]
                    assert values['demand_ns'] == row[5] and values['size'] == row[4]
                    assert values['finish_ns'] == row[5] + row[6] and values['fct_ns'] == row[6]
                    assert values['launch_ns'] - values['demand_ns'] == values['wait_ns']
                    finishes[i] = values
        main_cell = json.loads((main / entry['main_receipt']).read_text(encoding='utf-8-sig'))
        assert digest(fcts[0]) == main_cell['fct_sha256'] and digest(logs[0]) == main_cell['log_sha256']
        assert {key: h.hexdigest() for key, h in hashes.items()} == main_cell['ordered_normalized_hashes']
        assert events['WS30_ROUTE'] == 606168 and events['WS30_QP'] == 104
        assert events['WS30_QUEUE'] == events['WS30_PATH'] == 1 and len(ports) == 312
        assert all(int(summaries['WS30_PATH'][key]) == 0 for key in ['changed_qps', 'port_changes', 'rejected'])
        assert summaries['WS30_QUEUE']['enqueued'] == summaries['WS30_QUEUE']['dequeued']
        assert all(int(summaries['WS30_QUEUE'][key]) == 0 for key in ['current', 'dropped', 'admission_dropped_bytes', 'queue_rejected_bytes', 'violations'])
        c2_check = None
        if entry['mode'] == 'ws31-c2':
            assert set(finishes) == set(by_index)
            for i, values in finishes.items():
                key = by_index[i]
                sip, dip = addresses[key]
                wanted = start_hash(sip, dip, key[2], key[3]) % 501 if expected[key][2] == 2 else 0
                assert values['wait_ns'] == wanted
            waits = [v['wait_ns'] for v in finishes.values()]
            assert sum(v > 0 for v in waits) == 80 and sum(waits) == 18002 and max(waits) == 497
            state = summaries['WS31_C2_STATE']
            assert all(int(state[key]) == 0 for key in ['cancelled', 'pending', 'unfinished', 'cancel_bytes'])
            assert all(int(state[key]) == 104 for key in ['demanded', 'launched', 'finished'])
            assert all(int(state[key]) == payload for key in ['demand_bytes', 'launch_bytes', 'finish_bytes'])
            c2_check = {'rows': 104, 'exact_hash_waits': 104, 'positive': 80, 'sum_ns': 18002, 'max_ns': 497}
        cells.append({'id': entry['id'], 'mode': entry['mode'], 'flows': 104, 'payload_bytes': payload, 'fct_sha256': digest(fcts[0]), 'ordered_hashes': main_cell['ordered_normalized_hashes'], 'events': dict(events), 'summaries': summaries, 'C2_independent_hash_and_timing': c2_check, 'main_detailed_mechanism_replay': entry['raw_replay'], 'replay_attribution': 'C1 and C3 full model replay accepted by main, not independently rerun by Integration'})
    return {'scope': 'Integration local result/support hashes, complete FCT/accounting/path checks and exact C2 waits; C1/C3 full replay attributed to main', 'source_sha': report['source_sha'], 'result_files_hashed': result_checks, 'support_files_hashed': len(support_checks), 'support_checks': support_checks, 'unchanged_source_map_compared_to_prior_verified_c4': 35, 'cells': cells, 'completed_flow_records': 312, 'completed_payload_bytes': 605945856, 'remote_access': False, 'new_or_repeated_network_runs': False, 'formal_effects_validated': False}


if __name__ == '__main__':
    out = Path(__file__).with_name('raw-verification.json')
    if out.exists():
        raise RuntimeError('Refusing to overwrite an existing Integration receipt')
    result = audit(Path.cwd())
    out.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'result_files': result['result_files_hashed'], 'support_files': result['support_files_hashed'], 'cells': len(result['cells']), 'completed_flow_records': result['completed_flow_records'], 'completed_payload_bytes': result['completed_payload_bytes'], 'C2_exact_waits': 104}))
