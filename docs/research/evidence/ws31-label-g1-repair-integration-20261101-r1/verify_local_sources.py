"""Read-only Integration check of the stopped preflight and its fixed successor.

No remote command, build, unit-test execution, network simulation or raw replay.
"""
from pathlib import Path
import ast
import hashlib
import json
import subprocess


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(root):
    read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
    base = root / 'docs/research/ws31'
    ind, main = base / 'independent', base / 'main'
    impl = root.parent / 'ws31-candidates-implementation'
    git = lambda *args: subprocess.check_output(['git', '-C', str(impl), *args])
    index_path = ind / 'label-fixture-preflight-r1-index.json'
    index = read(index_path)
    receipt = read(ind / 'label-fixture-preflight-r1-receipt.json')
    qa = read(ind / 'label-fixture-preflight-r1-qa.json')
    repair = read(main / 'evidence/label-fixture-G1-repair-main-r1.json')
    plan_path = main / 'label-fixture-preflight-r2.json'
    plan = read(plan_path)
    stopped, original, new = index['source_sha'], index['parent_sha'], plan['source_sha']
    assert stopped == '4605fa32af440998f4280b641e5c2de2195ea4c3'
    assert original == '50603927fc09a68d9f2e038129aaee3a3d021081'
    assert new == '2ed7d342d0713a5667f43c7730ca5bc5a6a67150'
    assert sha(index_path.read_bytes()) == qa['index_sha256'] == repair['stopped_delivery_index_sha256']
    assert index['status'] == receipt['status'] == 'STOPPED_ON_MATERIAL_SOURCE_REVIEW_ISSUE'
    assert receipt['execution'] == index['execution'] == repair['prior_execution']
    assert all(v == 0 for v in index['execution'].values())
    assert index['experiment_id'] == plan['previous_ID']
    assert 'no remote existence claim' in receipt['id_state']
    documents = []
    for name, info in index['documents'].items():
        data = (ind / name).read_bytes()
        assert len(data) == info['bytes'] and sha(data) == info['sha256'], name
        documents.append(name)
    changed = []
    for path, info in index['source_objects'].items():
        data = git('show', stopped + ':' + path)
        assert len(data) == info['bytes'] and sha(data) == info['sha256'], path
        assert git('rev-parse', stopped + ':' + path).decode().strip() == info['git_blob']
        changed.append(path)
    unchanged = []
    for path, wanted in index['unchanged_objects'].items():
        assert all(sha(git('show', commit + ':' + path)) == wanted for commit in [original, stopped, new]), path
        unchanged.append(path)
    assert plan['source_changes_sha256'] == repair['repair_files_sha256']
    assert set(git('diff', '--name-only', stopped, new).decode().splitlines()) == set(plan['source_changes_sha256'])
    for path, wanted in plan['source_changes_sha256'].items():
        assert sha(git('show', new + ':' + path)) == wanted, path
    assert git('rev-parse', new + '^').decode().strip() == stopped
    assert git('rev-parse', stopped + '^').decode().strip() == original
    assert git('rev-parse', 'HEAD').decode().strip() == new
    assert git('branch', '--show-current').decode().strip() == plan['branch']
    assert not git('status', '--porcelain').strip()
    assert git('remote', 'get-url', '--push', 'origin').decode().strip() == 'https://github.com/LarryBUPT/conweave-ns3.git'
    assert git('rev-parse', 'refs/remotes/origin/' + plan['branch']).decode().strip() == new
    assert sha(plan_path.read_bytes()) == repair['new_plan_sha256'] == '7defac33294806d0369febbc79932e10263ac10112162642d0327eeb01366e3b'
    assert plan['resource_gate']['parallel_builds'] == 1
    assert plan['resource_gate']['jobs_per_build'] == 2
    assert plan['resource_gate']['simulation_concurrency'] == 0
    assert plan['id'] == '20261101-121000-ws31-label-preflight-r2'
    assert plan['contract'] == 'label-lifecycle-boundary-contract-r3.md'
    old_header = git('show', stopped + ':src/point-to-point/model/ws31-label-fixture.h').decode()
    header = git('show', new + ':src/point-to-point/model/ws31-label-fixture.h').decode()
    scratch = git('show', new + ':scratch/network-load-balance.cc').decode()
    tests = git('show', new + ':tests/ws31_label_test.cc').decode()
    worker = git('show', new + ':scripts/remote_worker.py').decode()
    runner = git('show', new + ':tests/ws31_label_runner_test.py').decode()
    assert 'LabelRunContext' not in old_header and 'const LabelRunContext &context' in header
    assert 'if (!profile) return;' in header
    assert 'ws31::LabelRunContext(enable_pfc,enable_irn,cc_mode,topology_file,flow_file,' in scratch
    assert scratch.index('ws31::ValidateLabelProfile(') < scratch.index('srand(', scratch.index('ws31::ValidateLabelProfile('))
    for fragment in ['context.pfc!=0', 'context.irn!=1', 'context.ccMode!=1', 'context.fault || context.diagnostic']:
        assert fragment in header
    for fragment in ['invalid.pfc=1', 'invalid.irn=0', 'invalid.ccMode=3', 'invalid.topology=', 'invalid.flow=', 'invalid.fault=true', 'invalid.diagnostic=true']:
        assert fragment in tests
    assert 'result.pop(key, None)' in worker
    methods = [n.name for n in ast.walk(ast.parse(runner)) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
    assert len(methods) == repair['local_tests']['python_process_test_methods'] == 5
    assert 'test_active_profile_clears_disabled_inherited_diagnostics' in methods
    assert repair['local_tests']['status'] == 'PASS'
    assert repair['local_tests']['cpp_tests_executed_by_main'] == 0
    return {
        'status': 'PASS_LOCAL_PROVENANCE_AND_STATIC_REPAIR_RECONCILIATION',
        'stopped_source': stopped, 'new_implemented_source': new, 'last_network_validated_source': original,
        'stopped_index_sha256': sha(index_path.read_bytes()), 'stopped_documents_hashed': len(documents),
        'stopped_git_blobs_hashed': len(changed), 'unchanged_blobs_compared_across_three_sources': len(unchanged),
        'repair_git_blobs_hashed': len(plan['source_changes_sha256']),
        'old_whole_tree_identity': {'entries': index['whole_git_tree']['entries'], 'owner': 'Independent audit; Integration checked frozen tree file identity only'},
        'prior_execution': index['execution'], 'prior_ID_remote_state': receipt['id_state'],
        'repair_scope': 'Actual parsed C++ context, early guard, rejection cases and enabled-profile diagnostic environment cleanup are present in fixed source; no C++ execution by Integration',
        'python_mock': {'main_reported_methods_passed': 5, 'test_methods_present_in_fixed_source': methods, 'repeated_by_Integration': False},
        'new_plan_sha256': sha(plan_path.read_bytes()), 'new_ID': plan['id'],
        'new_preflight_result': 'DISPATCHED; source/build/new-core/mock outcome not accepted here',
        'source_checkout_read_only': True, 'remote_actions': False, 'network_runs_or_old_core_replays': False,
        'new_network_or_lifecycle_or_efficacy_acceptance': False,
    }


if __name__ == '__main__':
    out = Path(__file__).with_name('source-verification.json')
    if out.exists():
        raise RuntimeError('Refusing to overwrite Integration source verification')
    result = verify(Path.cwd())
    out.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({k: result[k] for k in ['status', 'stopped_documents_hashed', 'stopped_git_blobs_hashed', 'unchanged_blobs_compared_across_three_sources', 'repair_git_blobs_hashed']}))
