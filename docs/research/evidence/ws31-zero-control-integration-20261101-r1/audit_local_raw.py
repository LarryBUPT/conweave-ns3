"""Integration-only read-only audit of the completed WS31 zero controls."""
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import subprocess


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def audit(root):
    independent = root / 'docs/research/ws31/independent'
    main = root / 'docs/research/ws31/main'
    index = json.loads((independent / 'zero-control-pilot-r1-index.json').read_text(encoding='utf-8-sig'))
    plan = json.loads((main / 'zero-control-pilot-r1.json').read_text(encoding='utf-8-sig'))
    source_repo = root.parent / 'ws31-candidates-implementation'
    counts = Counter()
    cells = []
    source_hashes = None
    for entry in index['cells']:
        base = independent / 'zero-control-pilot-r1-evidence' / entry['id']
        manifest = json.loads((base / 'remote-manifest.json').read_text(encoding='utf-8-sig'))
        results = base / 'results'
        assert manifest['source_head'] == plan['source_sha']
        if source_hashes is None:
            source_hashes = manifest['source_hashes']
            for rel, wanted in source_hashes.items():
                content = subprocess.check_output(['git', '-C', str(source_repo), 'show', plan['source_sha'] + ':' + rel])
                assert hashlib.sha256(content).hexdigest() == wanted, rel
                counts['unique_fixed_source_objects'] += 1
        else:
            assert manifest['source_hashes'] == source_hashes
        for rel, info in manifest['files'].items():
            path = results / rel
            assert path.stat().st_size == info['bytes'] and digest(path) == info['sha256'], str(path)
            counts['result_files'] += 1
        for name, wanted in entry['supporting_files'].items():
            assert digest(base / name) == wanted, name
            counts['support_files'] += 1
        meta = json.loads((results / 'metadata.json').read_text(encoding='utf-8-sig'))
        assert meta['status'] == 'SUCCEEDED' and meta['git_commit'] == plan['source_sha']
        assert meta['experiment_id'] == entry['id'] and meta['algorithm'] == entry['lb']
        assert meta['concurrency_cap'] == 1
        for key, value in plan['common'].items():
            if key != 'max_concurrent':
                assert meta['parameters'][key] == value, key
        for key in ['ws30_composition', 'ws30_lifecycle', 'ws30_tag_transform', 'ws30_life_profile']:
            assert meta['parameters'].get(key, 0) == 0
        trace = results / 'config/traffic_trace.txt'
        assert digest(trace) == plan['inputs']['config/ws31_correctness_r1.txt']
        assert digest(results / 'config/topology.txt') == plan['inputs']['config/leaf_spine_128_100G_OS2.txt']
        lines = trace.read_text().splitlines()
        expected = {}
        by_index = {}
        sport = defaultdict(lambda: 10000)
        dport = defaultdict(lambda: 100)
        for index_no, line in enumerate(lines[1:]):
            src, dst, _, size, start, _ = line.split()
            src, dst, size = int(src), int(dst), int(size)
            key = (src, dst, sport[src], dport[dst])
            expected[key] = (size, int(Fraction.from_float(float(start)) * 10**9))
            by_index[index_no] = key
            sport[src] += 1
            dport[dst] += 1
        assert len(expected) == int(lines[0]) == plan['flow_count'] == 104
        fct_paths = list((results / 'raw').glob('*/*_out_fct.txt'))
        log_paths = list((results / 'raw').glob('*/config.log'))
        assert len(fct_paths) == len(log_paths) == 1
        fct = fct_paths[0]
        completed = {}
        for line in fct.read_text().splitlines():
            row = tuple(map(int, line.split()))
            assert len(row) == 8
            key = row[:4]
            assert key in expected and key not in completed
            assert row[4:6] == expected[key] and row[6] >= 0 and row[7] > 0
            completed[key] = row
        assert set(completed) == set(expected)
        payload = sum(row[4] for row in completed.values())
        assert payload == plan['payload_bytes'] == 201981952
        events = Counter()
        ordered = {prefix: hashlib.sha256() for prefix in ['WS30_CHOICE', 'WS30_ROUTE']}
        summaries, ports, c2 = {}, {}, {}
        previous_time = -1
        with log_paths[0].open(encoding='utf-8') as handle:
            for line in handle:
                assert 'WS30_OBSERVATION_OVERFLOW' not in line
                tokens = line.split()
                if not tokens or tokens[0] not in ['WS30_CHOICE', 'WS30_ROUTE', 'WS30_QUEUE', 'WS30_PATH', 'WS30_QP', 'WS31_C2_FINISH', 'WS31_C2_STATE']:
                    continue
                prefix = tokens[0]
                events[prefix] += 1
                fields = dict(token.split('=', 1) for token in tokens[1:] if '=' in token)
                if prefix in ordered:
                    ordered[prefix].update((' '.join(token for token in tokens if not token.startswith('uid=')) + '\n').encode())
                    now = int(fields['time_ns'])
                    assert now >= previous_time
                    previous_time = now
                if prefix in ['WS30_QUEUE', 'WS30_PATH', 'WS31_C2_STATE']:
                    summaries[prefix] = fields
                if prefix == 'WS30_ROUTE':
                    key = ((int(fields['sip']) >> 8) & 65535, (int(fields['dip']) >> 8) & 65535, int(fields['sport']), int(fields['dport']))
                    assert key in expected
                    switch_key = (fields['switch'], key)
                    assert ports.setdefault(switch_key, fields['port']) == fields['port']
                if prefix == 'WS31_C2_FINISH':
                    values = {key: int(value) for key, value in fields.items()}
                    i = values['flow_id']
                    assert i in by_index and i not in c2
                    row = completed[by_index[i]]
                    assert values['demand_ns'] == values['launch_ns'] == row[5]
                    assert values['wait_ns'] == 0 and values['finish_ns'] == row[5] + row[6]
                    assert values['fct_ns'] == row[6] and values['size'] == row[4]
                    c2[i] = values
        assert events['WS30_CHOICE'] == 312 and events['WS30_ROUTE'] == 606168
        assert events['WS30_QP'] == 104 and events['WS30_QUEUE'] == events['WS30_PATH'] == 1
        assert len(ports) == int(summaries['WS30_PATH']['switch_qps']) == 312
        assert int(summaries['WS30_PATH']['full_rows']) == events['WS30_ROUTE']
        assert all(int(summaries['WS30_PATH'][key]) == 0 for key in ['port_changes', 'changed_qps', 'rejected'])
        assert summaries['WS30_QUEUE']['enqueued'] == summaries['WS30_QUEUE']['dequeued']
        assert all(int(summaries['WS30_QUEUE'][key]) == 0 for key in ['current', 'dropped', 'admission_dropped_bytes', 'queue_rejected_bytes', 'violations'])
        if entry['lb'] == 'ws31-c2-zero':
            assert set(c2) == set(by_index)
            state = summaries['WS31_C2_STATE']
            assert all(int(state[key]) == 0 for key in ['pending', 'unfinished', 'cancelled', 'cancel_bytes', 'waited', 'delay_sum_ns', 'delay_max_ns'])
            assert all(int(state[key]) == 104 for key in ['demanded', 'launched', 'finished'])
            assert all(int(state[key]) == payload for key in ['demand_bytes', 'launch_bytes', 'finish_bytes'])
        hashes = {key: value.hexdigest() for key, value in ordered.items()}
        assert digest(fct) == index['common_fct_sha256']
        assert hashes == {key: index['common_ordered_normalized_hashes'][key.lower().replace('ws30_', '')] for key in ordered}
        cells.append({'id': entry['id'], 'lb': entry['lb'], 'result_directory': results.relative_to(root).as_posix(), 'flows': 104, 'payload_bytes': payload, 'fct_sha256': digest(fct), 'ordered_hashes': hashes, 'observation_rows': dict(events), 'c2_zero_timing_rows': len(c2), 'within_qp_port_changes': 0, 'status': 'PASS'})
    return {'scope': 'Integration local raw/FCT/accounting/path equality audit; technical zero controls only', 'source_sha': plan['source_sha'], 'checks': dict(counts), 'cells': cells, 'completed_flow_records': sum(cell['flows'] for cell in cells), 'completed_payload_bytes': sum(cell['payload_bytes'] for cell in cells), 'failures': 0, 'boundary': 'No remote access, rerun, new effects inference, or Ofan admission; per-source-QP payload reconstruction was main-audited and is not independently repeated here.'}


if __name__ == '__main__':
    root = Path.cwd()
    out = Path(__file__).with_name('raw-verification.json')
    if out.exists():
        raise RuntimeError('Refusing to overwrite an existing Integration receipt')
    result = audit(root)
    out.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'checks': result['checks'], 'cells': len(result['cells']), 'completed_flow_records': result['completed_flow_records'], 'completed_payload_bytes': result['completed_payload_bytes'], 'failures': 0}))
