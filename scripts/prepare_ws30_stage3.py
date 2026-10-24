"""Prepare a disabled WS-30 stage-3 review plan; never launch experiments."""
import json
import subprocess
from pathlib import Path

import run_ws30_stage2 as stage


def main():
    root, evidence = stage.ROOT, stage.EV
    plan = json.loads((evidence / 'ws30-execution-plan-r5.json').read_text())
    cells = plan['main'] + plan['lead']
    assert len(plan['main']) == 192 and len(plan['lead']) == 72
    assert len({c['id'] for c in cells}) == 264
    assert len({c['seed'] for c in plan['main']}) == 24
    assert {c['seed'] for c in plan['main']} == {c['seed'] for c in plan['lead']}
    traces = {}
    for cell in cells:
        assert cell['cap'] == 12 and cell['observe'] == 1
        assert not (root / 'results' / cell['id']).exists(), cell['id']
        path = root / 'config' / cell['trace']
        assert stage.sha(path) == cell['trace_sha256']
        if cell['trace'] in traces:
            continue
        committed = subprocess.check_output(['git', '-C', str(root), 'show',
                                              stage.SOURCE + ':config/' + cell['trace']])
        assert committed == path.read_bytes(), cell['trace']
        lines = path.read_text().splitlines()
        assert len(lines) - 1 == int(lines[0]) == cell['input_flows'] == 16576
        times = [float(line.split()[4]) for line in lines[1:]]
        assert times == sorted(times), cell['trace']
        origins = {tag: min(float(line.split()[4]) for line in lines[1:]
                            if line.split()[5] == tag) for tag in ['1', '2']}
        assert origins['1'] == 2.0
        assert origins['2'] == (2.00002 if cell['role'] == 'lead20us' else 2.0)
        traces[cell['trace']] = {'sha256': cell['trace_sha256'], 'release_origins_s': origins}
    assert len(traces) == 48
    data = {
        'kind': 'WS-30 stage-3 review plan; preparation only',
        'execution_enabled': False, 'source_sha': stage.SOURCE, 'cap': 12,
        'parent_plan_sha256': stage.sha(evidence / 'ws30-execution-plan-r5.json'),
        'input_manifest_sha256': stage.sha(evidence / 'ws30-inputs-v3.json'),
        'main': [dict(c, source_sha=stage.SOURCE) for c in plan['main']],
        'lead': [dict(c, source_sha=stage.SOURCE) for c in plan['lead']],
        'traces': traces,
        'composition': {'required_cells': 12, 'status': 'actual-enqueue fixture not frozen',
                        'entry': 'docs/research/ws30-prespecified-protocol.md#背景先占与队列组成'},
        'required_before_execution': ['main-chat review of stage-2 evidence',
                                     'freeze composition input and implementation contract',
                                     'review and freeze resumable stage-3 runner',
                                     'fresh host, other-user, lock and remote-ID isolation checks',
                                     'actual task model switch to user-specified supervision setting'],
        'technical_stops': ['input/source/config mismatch', 'incomplete or duplicated flow identity',
                            'observation overflow or perturbation', 'queue accounting violation',
                            'other-user contention or resource limits exceeded'],
        'resource_limits': {'load_1m_max': 20, 'mem_available_gib_min': 32,
                            'free_gib_min': 100, 'process_tree_rss_gib_max': 32,
                            'compile_jobs_per_source': 2, 'parallel_builds_max': 4},
        'effect_stops': 'No early stop or tuning on null, adverse or opposite effects',
    }
    target = evidence / 'ws30-stage3-review-plan-r1.json'
    stage.frozen(target, data)
    print(json.dumps({'main': 192, 'lead': 72, 'composition_required': 12,
                      'traces_verified': len(traces), 'execution_enabled': False,
                      'plan_sha256': stage.sha(target)}))


if __name__ == '__main__':
    main()
