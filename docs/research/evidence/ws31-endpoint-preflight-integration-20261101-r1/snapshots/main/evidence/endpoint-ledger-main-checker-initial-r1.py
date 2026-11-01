"""Verify the portable endpoint core delivery without executing its binary."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(repo, source):
    ws31 = repo/'docs/research/ws31'
    main, independent = ws31/'main', ws31/'independent'
    prefix = 'endpoint-ledger-core-preflight-r2'
    index_path = independent/(prefix+'-index.json')
    index_hash = sha(index_path)
    index = read(index_path)
    qa_path = independent/(prefix+'-qa.json')
    qa = read(qa_path)
    plan_path = main/(prefix.replace('core-preflight', 'core-preflight')+'.json')
    plan = read(plan_path)
    assert index['status'] == 'PASS_FOR_PORTABLE_CORE_PREFLIGHT_ONLY'
    assert qa['status'] == 'PASS_PORTABLE_CORE_PREFLIGHT_DELIVERY'
    assert qa['index']['sha256'] == index_hash
    assert index['source_sha'] == plan['source_sha']
    assert index['plan']['sha256'] == sha(plan_path)
    assert index['id'] == plan['id']

    # The independent JSON uses ASCII-escaped path prefixes; resolve only the
    # explicit repository-relative evidence suffix, never eval a path string.
    def evidence_path(value):
        suffix = value.replace('\\', '/').split('/docs/research/ws31/', 1)[1]
        path = (ws31/suffix).resolve()
        assert path.is_relative_to(ws31.resolve())
        return path

    for item in index['artifacts']:
        path = evidence_path(item['path'])
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], path
    for name, expected in index['old_artifacts_preserved'].items():
        assert sha(evidence_path(name)) == expected
    result_root = independent/(prefix+'-raw/remote-results')
    manifest = read(result_root/'receipt-manifest.json')
    assert len(manifest) == index['raw_fetch']['verified_files'] == 41
    for item in manifest:
        path = result_root/item['path']
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
    tree = subprocess.check_output(['git', 'ls-tree', '-r', plan['source_sha']], cwd=source)
    assert tree == (result_root/'provenance/source-tree.txt').read_bytes()
    assert len(tree.splitlines()) == 4845
    assert hashlib.sha256(tree).hexdigest() == plan['tree_sha256']
    entries = {}
    for row in tree.decode('utf-8').splitlines():
        left, path = row.split('\t', 1)
        mode, kind, blob = left.split()
        assert kind == 'blob'
        entries[path] = (mode, blob)
    sources = read(result_root/'provenance/source-files.json')
    assert len(sources) == len(entries)
    assert len({item['path'] for item in sources}) == len(entries)
    process = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=source,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    total = 0
    try:
        for item in sources:
            assert entries[item['path']] == (item['mode'], item['git_blob'])
            process.stdin.write((item['git_blob']+'\n').encode('ascii'))
            process.stdin.flush()
            oid, kind, size = process.stdout.readline().split()
            assert oid.decode('ascii') == item['git_blob'] and kind == b'blob'
            remaining = int(size)
            assert remaining == item['bytes']
            digest = hashlib.sha256()
            total += remaining
            while remaining:
                block = process.stdout.read(min(remaining, 1024*1024))
                assert block
                digest.update(block)
                remaining -= len(block)
            assert process.stdout.read(1) == b'\n'
            assert digest.hexdigest() == item['sha256'], item['path']
    finally:
        process.stdin.close()
        process.stdout.close()
        assert process.wait() == 0
    assert total == index['source']['verified_source_bytes']
    for rel, expected in plan['source_changes_sha256'].items():
        path = independent/(prefix+'-raw/frozen-source')/rel
        assert sha(path) == expected

    compile_receipt = read(result_root/'provenance/compile-result.json')
    run = read(result_root/'provenance/run-result.json')
    output = '/home/fnl/lzy/results/'+plan['id']+'/artifacts/ws31_endpoint_ledger_test'
    expected_argv = [output if a.startswith('<new-ID-results>') else a for a in plan['compile']['argv']]
    assert compile_receipt['argv'] == expected_argv
    assert run['argv'] == [output]
    assert compile_receipt['exit'] == run['exit'] == 0
    assert compile_receipt['end_utc'] <= run['start_utc']
    assert compile_receipt['environment'] == run['environment'] == read(result_root/'provenance/exact-compile-run-environment.json')
    for receipt in (compile_receipt, run):
        assert receipt['cwd'] == '/home/fnl/lzy/runs/'+plan['id']+'/source'
        for stream in ('stdout', 'stderr'):
            assert sha(result_root/receipt[stream]) == receipt[stream+'_sha256']
        for sample in ('resources_before', 'resources_after'):
            resource = receipt[sample]
            assert resource['load'][0] <= 4 and resource['mem_available_gib'] >= 64
            assert resource['disk_available_gib'] >= 100
    assert (result_root/'logs/run.stdout').read_bytes() == plan['run']['expected_stdout'].encode('ascii')
    for path in ('logs/run.stderr', 'logs/compile.stdout', 'logs/compile.stderr'):
        assert (result_root/path).stat().st_size == 0
    binary = result_root/'artifacts/ws31_endpoint_ledger_test'
    assert binary.stat().st_size == index['binary']['bytes'] and sha(binary) == index['binary']['sha256']
    assert binary.read_bytes()[:4] == b'\x7fELF'
    assert index['counts'] == {'sync': 1, 'deploy': 0, 'full_ns3_build': 0,
                               'new_core_compile': 1, 'new_core_run': 1,
                               'network_run': 0, 'old_core_or_fixture_rerun': 0}
    assert index['runtime_libraries'] == read(result_root/'provenance/runtime-libraries.json')
    guards = read(independent/(prefix+'-guards-released.json'))
    assert guards['status'] == 'EXPLICITLY_RELEASED_AFTER_TERMINAL_CALLS_AND_FETCH_INTEGRITY'
    assert guards['no_persistent_driver'] and not guards['future_execution_authorized']
    for guard in ('source_guard', 'entry_guard', 'environment_guard'):
        assert guards[guard] == 'released'
    reference = read(independent/(prefix+'-reference-review.json'))
    for item in reference['source_records']:
        name = item['path'].replace('\\', '/').split('/')[-1]
        paper_root = repo.parent.parent/'参考文献/候选'
        path = paper_root/name if name in ('README.md', 'reading-log.md') else paper_root/'papers/diffflow-2016'/name
        assert sha(path) == item['sha256']
    assert sha(index_path) == index_hash
    return {'at_utc': datetime.now(timezone.utc).isoformat(),
            'status': 'MAIN_ACCEPTED_PORTABLE_ENDPOINT_CORE_SINGLE_COMPILE_RUN_AND_DELIVERY',
            'id': plan['id'], 'source_sha': plan['source_sha'],
            'plan_sha256': sha(plan_path), 'index_sha256': index_hash, 'QA_sha256': sha(qa_path),
            'indexed_artifacts_hashed': len(index['artifacts']), 'raw_files_hashed': len(manifest),
            'old_artifacts_preserved': len(index['old_artifacts_preserved']),
            'git_files_verified': len(sources), 'git_bytes_verified': total,
            'binary_sha256': sha(binary), 'binary_bytes': binary.stat().st_size,
            'compile_argv': compile_receipt['argv'], 'counts': index['counts'],
            'core_stdout': plan['run']['expected_stdout'],
            'runtime_library_fingerprints': len(index['runtime_libraries']),
            'library_evidence_scope': 'saved ldd resolution and hashes; library binaries not independently rehashed locally',
            'compile_max_rss_kib': compile_receipt['rusage']['max_rss_kib'],
            'run_max_rss_kib': run['rusage']['max_rss_kib'], 'guards_released': True,
            'scope': 'Portable manual snapshots only; actual NS3 endpoint/bitmap/channel/network and efficacy remain unvalidated'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Refusing to overwrite main acceptance'
    result = verify(args.repo, args.source)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'git_files_verified', 'indexed_artifacts_hashed', 'raw_files_hashed')}))
