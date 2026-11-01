"""Integration reads completed preflight evidence; never executes build/tests/network."""
from pathlib import Path
import hashlib
import json
import re
import subprocess


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(root):
    read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
    ind = root / 'docs/research/ws31/independent'
    main = root / 'docs/research/ws31/main'
    prefix = 'label-fixture-preflight-r2'
    index = read(ind / (prefix + '-index.json'))
    qa = read(ind / (prefix + '-qa.json'))
    receipt = read(ind / (prefix + '-receipt.json'))
    accepted = read(main / 'evidence/label-fixture-preflight-main-acceptance-r2.json')
    assert digest((ind / (prefix + '-index.json')).read_bytes()) == qa['index_sha256'] == accepted['index_sha256']
    assert digest((ind / (prefix + '-qa.json')).read_bytes()) == accepted['QA_sha256']
    assert index['source_sha'] == accepted['source_sha'] == receipt['source_sha'] == '2ed7d342d0713a5667f43c7730ca5bc5a6a67150'
    folder = ind / (prefix + '-evidence') / index['id']
    results = folder / 'results'
    counts = {}
    for group, location in [('documents', ind), ('dependencies', ind), ('supporting_files', folder), ('result_files', results)]:
        for rel, info in index[group].items():
            data = (location / rel).read_bytes()
            assert digest(data) == (info['sha256'] if isinstance(info, dict) else info), rel
            if isinstance(info, dict):
                assert len(data) == info['bytes'], rel
        counts[group] = len(index[group])
    assert counts == accepted['files_hashed']
    manifest = read(folder / 'remote-manifest.json')
    assert manifest['source_hashes'] == index['source_map']
    impl = root.parent / 'ws31-candidates-implementation'
    git = lambda *args: subprocess.check_output(['git', '-C', str(impl), *args])
    for path, wanted in index['source_map'].items():
        assert digest(git('show', index['source_sha'] + ':' + path)) == wanted, path
    tree = git('ls-tree', '-r', index['source_sha'])
    assert (ind / (prefix + '-source-git-tree.txt')).read_bytes() == tree
    assert len(tree.splitlines()) == accepted['git_tree_entries'] == 4839
    assert len(index['source_map']) == accepted['fixed_git_objects_hashed'] == 38
    meta = read(results / 'metadata.json')
    assert meta['status'] == 'BUILT' and meta['git_commit'] == index['source_sha']
    assert meta['build_mode'] == 'optimized' and meta['cpu_jobs'] == 2
    build = (results / 'logs/build.log').read_text(encoding='utf-8')
    tasks = max(int(total) for _, total in re.findall(r'\[\s*(\d+)\s*/\s*(\d+)\s*\]', build))
    assert tasks == accepted['build_tasks'] == 1464
    assert "'build' finished successfully (5m52.659s)" in build
    assert accepted['build_duration_seconds'] == 352.659
    assert receipt['new_build_commands'] == 1 and receipt['new_cpp_core_commands'] == 2
    assert receipt['python_mock_commands'] == 1
    assert receipt['network_runs_started'] == receipt['old_core_tests_repeated'] == 0
    assert all(c['exit_code'] == 0 for c in receipt['commands'])
    assert not any((results / 'raw').rglob('*'))
    core = read(ind / (prefix + '-core-receipt.json'))
    assert core == read(results / 'technical/ws31-label/receipt.json')
    assert core['status'] == 'PASS' and len(core['steps']) == 2
    assert all(s['exit_code'] == 0 for s in core['steps'])
    args = core['steps'][0]['argv']
    assert all(flag in args for flag in ['-std=c++11', '-O2', '-Wall', '-Wextra', '-pedantic', '-UNDEBUG'])
    assert '-DNDEBUG' not in args
    binary = (results / 'technical/ws31-label/core-test').read_bytes()
    assert digest(binary) == core['binary_sha256'] and b'__assert_fail' in binary
    assert (results / 'logs/ws31-label-core-run.log').read_text(encoding='utf-8') == core['stdout']
    assert 'PASS visibility/boundary/presence/unknown/hash/conflicts/context' in core['stdout']
    mock = read(ind / (prefix + '-local-mock-receipt.json'))
    mock_log = folder / 'python-local-runner-mock.log'
    mock_text = mock_log.read_text(encoding='utf-8')
    assert mock['status'] == 'PASS' and mock['methods'] == 5
    assert 'Ran 5 tests' in mock_text and re.search(r'^OK\s*$', mock_text, re.M)
    assert digest(mock_text.encode('utf-8')) == mock['log_sha256']
    byte_domains = {}
    equivalence = read(ind / (prefix + '-local-source-canonical-equivalence.json'))
    for path, wanted_raw in mock['source_hashes'].items():
        raw = (impl / path).read_bytes()
        canonical = git('show', index['source_sha'] + ':' + path)
        assert digest(raw) == wanted_raw and raw.replace(b'\r\n', b'\n') == canonical
        assert equivalence['files'][path]['raw_sha256'] == digest(raw)
        assert equivalence['files'][path]['canonical_git_lf_sha256'] == digest(canonical)
        byte_domains[path] = {'raw_sha256': digest(raw), 'fixed_git_lf_sha256': digest(canonical), 'crlf_count': raw.count(b'\r\n')}
    worker_raw = byte_domains['scripts/remote_worker.py']['raw_sha256']
    deployed = read(ind / (prefix + '-cache-after-deploy.json'))
    assert worker_raw == deployed['deployed_worker_sha256'] == receipt['deployed_worker_sha256'] == index['deployed_worker_sha256']
    correction = read(ind / (prefix + '-newline-checker-correction.json'))
    assert digest((ind / correction['old_finalizer']).read_bytes()) == correction['old_finalizer_sha256']
    assert correction['builds_or_tests_repeated'] == 0 and not correction['source_or_raw_test_logs_modified']
    released = read(ind / (prefix + '-guards-released.json'))
    assert released['status'] == 'RELEASED' and released['source_copy_complete']
    assert git('rev-parse', 'HEAD').decode().strip() == index['source_sha']
    assert not git('status', '--porcelain').strip()
    next_plan_path = main / 'label-default-validation-r1.json'
    next_plan = read(next_plan_path)
    assert digest(next_plan_path.read_bytes()) == 'a81e95af15bba097c8ce900348c260a58c8b2a10416b204380c217331f1d7b4e'
    assert next_plan['source_sha'] == index['source_sha'] and len(next_plan['cells']) == 3
    assert next_plan['common']['ws31_label_profile'] == 0
    assert [c['lb'] for c in next_plan['cells']] == ['ws31-c1', 'ws31-c2', 'ws31-c3']
    assert next_plan['build_resources']['max_parallel_builds'] == 3 and next_plan['build_resources']['max_total_compile_jobs'] == 6
    return {'status': 'PASS_LOCAL_BUILD_CORE_MOCK_AND_PROVENANCE_RECONCILIATION', 'source_sha': index['source_sha'], 'files_hashed': counts, 'git_blobs_hashed': 38, 'git_tree_entries_compared': 4839, 'build_tasks': tasks, 'build_duration_seconds': 352.659, 'new_core_compile': 1, 'new_core_run': 1, 'core_binary_hash_and_assertion_symbol_valid': True, 'python_mock_methods': 5, 'network_runs': 0, 'network_raw_empty': True, 'byte_domains': byte_domains, 'mock_log_raw_sha256': digest(mock_log.read_bytes()), 'mock_receipt_text_hash_basis': 'UTF8 after universal newline decoding', 'deployed_worker_scope': 'Local raw bytes match preserved deployment-audit hash; no independent remote access', 'historical_checker_preserved': True, 'tests_builds_or_network_reexecuted_by_Integration': False, 'next_default_profile0_plan_identity_valid': True, 'next_plan_status': 'DISPATCHED, results not accepted here', 'last_network_validated_source': '50603927fc09a68d9f2e038129aaee3a3d021081', 'dynamic_labels_lifecycle_or_effects_accepted': False}


if __name__ == '__main__':
    out = Path(__file__).with_name('delivery-verification.json')
    if out.exists():
        raise RuntimeError('Refusing to overwrite Integration delivery verification')
    result = verify(Path.cwd())
    out.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({k: result[k] for k in ['status', 'files_hashed', 'git_blobs_hashed', 'git_tree_entries_compared', 'build_tasks', 'network_runs']}))
