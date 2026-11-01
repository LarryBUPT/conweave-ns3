"""Reconcile the actual-object preflight delivery using local evidence only."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(repo, source):
    repo, source = repo.resolve(), source.resolve()
    ws = repo/'docs/research/ws31'
    main, independent = ws/'main', ws/'independent'
    prefix = 'endpoint-probe-object-preflight-r1'
    base = independent/(prefix+'-raw')
    raw = base/'remote-results'
    ip, qp = independent/(prefix+'-index.json'), independent/(prefix+'-qa.json')
    ih = sha(ip)
    index, qa = read(ip), read(qp)
    planpath = main/(prefix+'.json')
    plan = read(planpath)
    assert index['status'] == 'PASS_ACTUAL_OBJECT_PROBE_PREFLIGHT_ONLY'
    assert qa['status'] == 'PASS_ACTUAL_OBJECT_PREFLIGHT_DELIVERY'
    assert qa['index']['sha256'] == ih
    assert index['plan']['sha256'] == sha(planpath)
    assert index['source_sha'] == plan['source_sha']
    assert index['id'] == plan['id']

    def evidence_path(value):
        suffix = value.replace('\\', '/').split('/docs/research/ws31/', 1)[1]
        path = (ws/suffix).resolve()
        assert path.is_relative_to(ws.resolve())
        return path

    for item in index['artifacts']:
        path = evidence_path(item['path'])
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], path
    for name, expected in index['old_artifacts_preserved'].items():
        assert sha(evidence_path(name)) == expected
    manifest = read(raw/'receipt-manifest.json')
    assert len(manifest) == index['raw_fetch']['verified_files'] == 109
    assert len({item['path'] for item in manifest}) == len(manifest)
    for item in manifest:
        path = (raw/item['path']).resolve()
        assert path.is_relative_to(raw.resolve())
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], path
    assert sum(item['bytes'] for item in manifest) == index['raw_fetch']['verified_bytes']
    tree = subprocess.check_output(['git', 'ls-tree', '-r', plan['source_sha']], cwd=source)
    assert tree == (raw/'provenance/source-tree.txt').read_bytes()
    assert hashlib.sha256(tree).hexdigest() == plan['tree_sha256']
    entries = {}
    for row in tree.decode('utf-8').splitlines():
        left, path = row.split('\t', 1)
        mode, kind, blob = left.split()
        assert kind == 'blob'
        entries[path] = (mode, blob)
    sources = read(raw/'provenance/source-files.json')
    assert len(entries) == len(sources) == plan['source_tree_entries'] == 4847
    assert set(entries) == {item['path'] for item in sources}
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
            total += remaining
            digest = hashlib.sha256()
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
    assert total == index['source']['source_bytes'] == 284719415
    for rel, expected in plan['source_changes_sha256'].items():
        frozen, working = base/'frozen-source'/rel, base/'local-working-bytes'/rel
        assert sha(frozen) == expected
        assert working.read_bytes().replace(b'\r\n', b'\n') == frozen.read_bytes()
    for rel, expected in index['source']['accepted_core_inputs_unchanged'].items():
        blob = subprocess.check_output(['git', 'show', plan['source_sha']+':'+rel], cwd=source)
        assert hashlib.sha256(blob).hexdigest() == expected

    receipts = [read(raw/('provenance/'+name+'-result.json'))
                for name in ('configure', 'build', 'fixture')]
    cwd = '/home/fnl/lzy/runs/'+plan['id']+'/source'
    assert [r['argv'] for r in receipts] == [
        ['./waf', 'configure', '--build-profile=optimized'], ['./waf', '-j2', '-v'],
        [cwd+'/build/scratch/ws31-endpoint-object-test']]
    assert receipts[0]['end_utc'] <= receipts[1]['start_utc']
    assert receipts[1]['end_utc'] <= receipts[2]['start_utc']
    for pos, receipt in enumerate(receipts):
        assert receipt['exit'] == receipt['wait_status'] == 0 and receipt['cwd'] == cwd
        env = receipt['environment']
        assert env == read(raw/('provenance/'+('fixture' if pos == 2 else 'build')+'-environment.json'))
        assert 'LD_PRELOAD' not in env
        assert {k for k in env if k.startswith(('WS30_', 'WS31_'))} == {
            'WS30_OBSERVE', 'WS31_LABEL_PROFILE', 'WS30_TAG_TRANSFORM',
            'WS30_LIFECYCLE', 'WS30_LIFE_PROFILE', 'WS30_COMPOSITION'}
        assert all(v == '0' for k, v in env.items() if k.startswith(('WS30_', 'WS31_')))
        assert env.get('LD_LIBRARY_PATH') == (cwd+'/build' if pos == 2 else None)
        for stream in ('stdout', 'stderr'):
            assert sha(raw/receipt[stream]) == receipt[stream+'_sha256']
        for name in ('resources_before', 'resources_after'):
            res = receipt[name]
            assert res['load'][0] <= 4 and res['mem_available_gib'] >= 64 and res['disk_available_gib'] >= 100
    assert (raw/'logs/fixture.stderr').stat().st_size == 0
    commands = []
    combined = ''
    for stream in ('stdout', 'stderr'):
        log = (raw/('logs/build.'+stream)).read_text(encoding='utf-8')
        combined += log
        for line in log.splitlines():
            if ' runner [' in line:
                commands.append(ast.literal_eval(line.split(' runner ', 1)[1]))
    compile_commands = [a for a in commands if '../scratch/ws31-endpoint-object-test.cc' in a]
    link_commands = [a for a in commands if cwd+'/build/scratch/ws31-endpoint-object-test' in a]
    assert len(compile_commands) == len(link_commands) == 1
    assert all(flag in compile_commands[0] for flag in ('-O3', '-g', '-std=gnu++11', '-c'))
    assert '-DNDEBUG' not in compile_commands[0]
    extracted = read(base/'compiler-command-verification.json')
    assert extracted['fixture_compile']['argv'] == compile_commands[0]
    assert extracted['fixture_link']['argv'] == link_commands[0]
    tasks = [tuple(map(int, m)) for m in re.findall(r'\[(\d+)/(\d+)\]', combined)]
    assert max(tasks) == (1470, 1470) and "'build' finished successfully" in combined
    binary = raw/'artifacts/ws31-endpoint-object-test'
    assert binary.stat().st_size == index['binary']['bytes'] and sha(binary) == index['binary']['sha256']
    assert binary.read_bytes()[:4] == b'\x7fELF'
    libraries = read(raw/'provenance/runtime-libraries.json')
    assert libraries == index['runtime_libraries'] and len(libraries) == 45
    project = [lib for lib in libraries if lib['project_library']]
    assert len(project) == 36
    for lib in project:
        path = raw/lib['local_artifact']
        assert lib['realpath'].startswith(cwd+'/build/')
        assert path.stat().st_size == lib['bytes'] and sha(path) == lib['sha256']
    static = read(base/'local-static-review.json')
    gate = read(base/'before-sync-gate-review.json')
    assert static['source_sha'] == plan['source_sha'] and static['local_status'] == 'clean'
    assert static['at_utc'] < gate['at_utc'] < index['commands']['sync']['start_utc'] or static['at_utc'] < gate['at_utc'] == index['commands']['sync']['start_utc']
    assert gate['unknown_jobs'] == [] and gate['worker_verified']
    assert all(gate['id_absent'].values())
    worker = hashlib.sha256((source/'scripts/remote_worker.py').read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    for name in ('before-source-gate', 'before-fixture-gate', 'after-fixture-gate'):
        snapshot = read(raw/('provenance/'+name+'.json'))
        assert snapshot['decision'] == 'PASS_FRESH_GATE'
        assert snapshot['worker']['LF_sha256'] == worker
        assert not snapshot['worker']['symlink'] and not any(snapshot['maintenance_markers'].values())
        assert snapshot['mem_available_gib'] >= 64 and snapshot['disk_available_gib'] >= 100 and snapshot['load'][0] <= 4
    final_gate = read(base/'after-fetch-gate.stdout.json')
    guards = read(independent/(prefix+'-guards-released.json'))
    assert guards['status'] == 'EXPLICITLY_RELEASED_AFTER_ALL_TERMINAL_CALLS_AND_VERIFIED_RAW'
    assert guards['no_persistent_driver'] and not guards['future_execution_authority']
    assert all(guards[k] == 'released' for k in ('source_guard', 'entry_guard', 'environment_guard'))
    assert guards['remote_task_pids_absent'] == final_gate['previous_task_pids_absent']
    assert final_gate['all_guarded_calls_terminal']
    assert not set(guards['remote_task_pids_absent']) & {p['pid'] for p in final_gate['processes']}
    assert index['counts'] == {'sync': 1, 'deploy': 0, 'full_optimized_j2_build': 1,
        'new_object_fixture': 1, 'standalone_core_compile': 0,
        'old_core_adapter_reference_rerun': 0, 'network_run': 0}
    prep = read(main/'evidence/endpoint-object-main-verifier-preparation-r1.json')
    assert sha(main/prep['raw_verifier']) == prep['raw_verifier_sha256']
    raw_accept = read(main/'evidence/endpoint-object-raw-main-acceptance-r1.json')
    assert raw_accept['stdout_sha256'] == sha(raw/'logs/fixture.stdout')
    assert raw_accept['normal_pairs'] == 8 and raw_accept['refusals'] == 16 and raw_accept['mask'] == 127
    assert sha(ip) == ih
    return {'at_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'MAIN_ACCEPTED_ACTUAL_OBJECT_PREFLIGHT_RAW_SOURCE_AND_FINAL_DELIVERY',
        'id': plan['id'], 'source_sha': plan['source_sha'], 'plan_sha256': sha(planpath),
        'index_sha256': ih, 'QA_sha256': sha(qp), 'indexed_artifacts_hashed': len(index['artifacts']),
        'raw_files_hashed': len(manifest), 'git_files_verified': len(sources), 'git_bytes_verified': total,
        'prior_artifacts_preserved': len(index['old_artifacts_preserved']),
        'project_libraries_locally_hashed': len(project), 'system_library_remote_hash_receipts': 9,
        'binary_sha256': sha(binary), 'build_tasks': 1470,
        'build_elapsed_seconds': receipts[1]['elapsed_seconds'],
        'build_max_rss_kib': receipts[1]['rusage']['max_rss_kib'],
        'fixture_max_rss_kib': receipts[2]['rusage']['max_rss_kib'],
        'compiler_argv': compile_commands[0], 'raw_acceptance': 'endpoint-object-raw-main-acceptance-r1.json',
        'total_Read_calls': 31, 'successful_returns': 17, 'Read_refusals': 14, 'other_refusals': 2,
        'counts': index['counts'], 'guards_released': True,
        'scope': 'Manually assigned actual NS3 objects only; no natural completion, ALL255 certificate, network or algorithm performance/cost evidence'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Refusing to overwrite acceptance'
    result = verify(args.repo, args.source)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'indexed_artifacts_hashed', 'git_files_verified', 'build_tasks')}))
