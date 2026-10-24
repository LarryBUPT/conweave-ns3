"""Revalidate stage-2 local raw, historical bridges and preserved failures."""
import argparse
import collections
import datetime
import json
from pathlib import Path

import resume_ws30_stage2 as recovery
import run_ws30_stage2 as stage

ROOT = stage.ROOT
EV = stage.EV


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def fct(folder):
    files = list((folder / 'raw').rglob('*_out_fct.txt'))
    assert len(files) == 1, (folder, files)
    return files[0]


def resource(rows):
    return {
        'peak_load_1m': max(r['resource']['peak_load_1m'] for r in rows),
        'minimum_mem_available_gib': min(r['resource']['minimum_mem_available_gib'] for r in rows),
        'minimum_free_gib': min(r['resource']['minimum_free_gib'] for r in rows),
        'peak_tree_rss_mib': max(r['resource']['peak_tree_rss_mib'] for r in rows),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--session-file', type=Path)
    args = parser.parse_args()
    plan = recovery.makeplan()
    runtime_plan = stage.makeplan()
    assert runtime_plan == read(EV / 'ws30-execution-plan-r5.json')
    # Verification hashes each cell's actual topology. Cache its immutable
    # expected contract rather than rereading all 412 input cells per result.
    stage.makeplan = lambda: runtime_plan
    bridge_plan = read(recovery.BRIDGE_PLAN)
    technical = read(recovery.TECH_RESULT)
    pilot = read(recovery.PILOT_RESULT)
    bridge = read(recovery.BRIDGE_RESULT)
    stages = [(plan['technical'], technical), (plan['pilot'], pilot),
              (bridge_plan['cells'], bridge)]
    verified = {}
    for cells, receipt in stages:
        assert len(cells) == len(receipt['rows']) == receipt['verified_cells']
        recorded = {r['id']: r for r in receipt['rows']}
        for cell in cells:
            row = stage.verify(cell)
            assert all(recorded[cell['id']][k] == v for k, v in row.items()), cell['id']
            verified[cell['id']] = row
    assert len(verified) == 148
    assert len({c['id'] for c in bridge_plan['cells']}) == 96
    preflight = read(EV / 'ws30-bridge-history-preflight-r1.json')
    old = {(r['seed'], r['arm']): r for r in preflight['rows']}
    mappings = []
    for cell in bridge_plan['cells']:
        historical = old[cell['seed'], cell['arm']]
        historical_root = ROOT.parent / {
            'ws25': 'ws25-first-paper', 'ws27': 'ws27-guardhash-compare'
        }[historical['historical_group']] / 'results' / historical['historical_id']
        actual = fct(ROOT / 'results' / cell['id'])
        prior = fct(historical_root)
        actual_sha, prior_sha = stage.sha(actual), stage.sha(prior)
        assert actual_sha == prior_sha == historical['historical_raw_fct_sha256']
        assert actual_sha == verified[cell['id']]['fct_sha256']
        assert stage.sha(historical_root / 'config/traffic_trace.txt') == cell['trace_sha256']
        assert stage.sha(ROOT / 'results' / cell['id'] / 'config/traffic_trace.txt') == cell['trace_sha256']
        lines = sum(1 for line in actual.open() if line.strip())
        assert lines == cell['input_flows'] == 16576
        mappings.append({'id': cell['id'], 'seed': cell['seed'], 'arm': cell['arm'],
                         'historical_id': historical['historical_id'],
                         'historical_group': historical['historical_group'],
                         'fct_sha256': actual_sha, 'fct_rows': lines,
                         'trace_sha256': cell['trace_sha256']})
    failures = read(EV / 'ws30-staggered-fixture-failure-and-repair-r1.json')
    for row in failures['failed_cells_preserved']:
        folder = ROOT / 'results' / row['id']
        assert read(folder / 'metadata.json')['status'] == 'FAILED'
        assert stage.sha(folder / 'metadata.json') == row['metadata_sha256']
        failed_logs = list((folder / 'raw').rglob('config.log'))
        assert len(failed_logs) == 1
        assert stage.sha(failed_logs[0]) == row['config_log_sha256']
        assert list((folder / 'raw').rglob('*'))
    blocked = ROOT / 'results/ws30-stage2-recovery-bridge-cleanliness-block-r1.log'
    assert 'Local checkout has uncommitted changes' in blocked.read_text(errors='replace')
    events = [read_line for line in (ROOT / 'results/ws30-stage2-recovery-receipts-r1.jsonl').read_text().splitlines()
              if line.strip() for read_line in [json.loads(line)]]
    fresh = [r for r in bridge['rows'] if r['role'] == 'historical-bridge']
    ids = {r['id'] for r in fresh}
    fresh_events = [e for e in events if e.get('id') in ids]
    event_counts = dict(collections.Counter(e['event'] for e in fresh_events))
    assert event_counts.get('verified') == event_counts.get('started') == 92
    metas = [read(ROOT / 'results' / r['id'] / 'metadata.json') for r in fresh]
    parse = lambda x: datetime.datetime.fromisoformat(x.replace('Z', '+00:00'))
    start = min(parse(m['created_utc']) for m in metas)
    finish = max(parse(m['finished_utc']) for m in metas)
    seconds = (finish - start).total_seconds()
    result = {
        'kind': 'WS-30 stage-2 post-run raw audit r1',
        'source_sha': stage.SOURCE, 'input_repair_source_sha': recovery.INPUT_REPAIR_SOURCE,
        'technical_cells_verified': 32, 'pilot_cells_verified': 24,
        'bridge_cells_verified': 96, 'bridge_prechecks_reused': 4,
        'new_bridge_cells_verified': 92, 'unique_successful_experiments': 148,
        'historical_fct_sha_matches': 96, 'historical_input_sha_matches': 96,
        'preserved_failed_experiments': [r['id'] for r in failures['failed_cells_preserved']],
        'blocked_controller_launch': {'path': str(blocked.relative_to(ROOT)).replace('\\', '/'),
                                     'sha256': stage.sha(blocked), 'simulation_started': False},
        'new_bridge_receipt_events': event_counts,
        'new_bridge_created_utc': start.isoformat(), 'new_bridge_finished_utc': finish.isoformat(),
        'new_bridge_build_and_simulation_wall_seconds': seconds,
        'new_bridge_end_to_end_cells_per_hour': 92 * 3600 / seconds,
        'resources_all_unique_successes': resource(list(verified.values())),
        'resources_bridge_96': resource(bridge['rows']),
        'resources_new_bridge_92': resource(fresh),
        'formal_matrix_execution_enabled': False,
        'remaining_required': {'main': 192, 'background_lead': 72, 'composition': 12,
                               'two_sided_analysis_and_figures': 'not complete'},
        'bridge_rows': mappings,
    }
    destination = EV / 'ws30-stage2-postrun-audit-r1.json'
    if args.session_file:
        contexts = []
        for line in args.session_file.open(encoding='utf-8'):
            data = json.loads(line)
            if data.get('type') == 'turn_context':
                payload = data['payload']
                contexts.append({'timestamp': data.get('timestamp'),
                                 'model': payload.get('model'), 'effort': payload.get('effort')})
        result['actual_model_turn_contexts'] = contexts[-2:]
    elif destination.exists():
        # Preserve the dated runtime evidence when a later raw-only audit
        # has no access to the original local session file.
        previous = read(destination)
        if 'actual_model_turn_contexts' in previous:
            result['actual_model_turn_contexts'] = previous['actual_model_turn_contexts']
    stage.frozen(destination, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'bridge_rows'}, indent=2))


if __name__ == '__main__':
    main()
