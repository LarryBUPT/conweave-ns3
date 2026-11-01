"""Main file/source provenance audit after the separate four-cell raw replay."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify(repo, source):
    main = repo/'docs/research/ws31/main'
    independent = main.parent/'independent'
    prefix = 'c13-label-validation-r1'
    index_path = independent/(prefix+'-index.json')
    index = read(index_path)
    qa = read(independent/(prefix+'-delivery-qa.json'))
    assert qa['status'] == 'PASS' and qa['index_sha256'] == sha(index_path)
    plan = read(main/'c13-label-validation-r1.json')
    assert index['source_sha'] == plan['source_sha']
    assert index['plan_sha256'] == sha(main/'c13-label-validation-r1.json')
    checked = {}
    for field in ('documents', 'dependencies', 'references'):
        checked[field] = 0
        for name, entry in index[field].items():
            path = Path(name) if field == 'references' else independent/name
            expected = entry['sha256'] if isinstance(entry, dict) else entry
            assert sha(path) == expected, path
            if isinstance(entry, dict):
                assert path.stat().st_size == entry['bytes']
            checked[field] += 1
    results = supports = 0
    cells = []
    assert [c['id'] for c in index['cells']] == [c['id'] for c in plan['cells']]
    for cell in index['cells']:
        directory = independent/(prefix+'-evidence')/cell['id']
        for name, digest in cell['supporting_files'].items():
            assert sha(directory/name) == digest, directory/name
            supports += 1
        manifest = read(directory/'remote-manifest.json')
        base = directory/'results'
        for name, entry in manifest['files'].items():
            path = base/name
            assert path.is_file() and path.stat().st_size == entry['bytes']
            assert sha(path) == entry['sha256'], path
            results += 1
        suffix = cell['id'].removeprefix('20261101-104000-ws31-c13tag-r1-')
        raw = read(main/('evidence/c13-label-'+suffix+'-main-acceptance-r1.json'))
        assert raw['status'] == 'PASS_C1_C3_LABEL_TECHNICAL_SCOPE'
        assert raw['id'] == cell['id'] and raw['flow_count'] == 104
        assert raw['payload_bytes'] == 201981952
        assert raw['fct_sha256'] == cell['fct_sha256']
        cells.append(raw)
    sources = read(independent/(prefix+'-sources-established.json'))
    assert sources['all_four_verified'] and len(sources['builds']) == 4
    blobs = {}
    maps = 0
    for build in sources['builds']:
        meta = build['metadata']
        assert meta['git_commit'] == plan['source_sha'] and meta['cpu_jobs'] == 2
        assert meta['git_repository'] == 'https://github.com/LarryBUPT/conweave-ns3.git'
        for path, digest in build['source_hashes'].items():
            assert path not in blobs or blobs[path] == digest
            blobs[path] = digest
            maps += 1
    for path, digest in blobs.items():
        data = subprocess.run(['git', 'show', plan['source_sha']+':'+path],
                              cwd=source, check=True, capture_output=True).stdout
        assert hashlib.sha256(data).hexdigest() == digest, path
    tree = subprocess.run(['git', 'ls-tree', '-r', plan['source_sha']], cwd=source,
                          check=True, capture_output=True).stdout.decode('utf-8').splitlines()
    assert tree == (independent/(prefix+'-source-git-tree.txt')).read_text(encoding='utf-8').splitlines()
    return {'recorded_utc': datetime.now(timezone.utc).isoformat(),
            'status': 'MAIN_ACCEPTED_C1_C3_FOUR_LABEL_TECHNICAL_CELLS_AND_FINAL_DELIVERY',
            'source_sha': plan['source_sha'], 'plan_sha256': index['plan_sha256'],
            'index_sha256': sha(index_path),
            'delivery_QA_sha256': sha(independent/(prefix+'-delivery-qa.json')),
            'completed_flow_records': sum(c['flow_count'] for c in cells),
            'completed_payload_bytes': sum(c['payload_bytes'] for c in cells),
            'result_files_hashed': results, 'support_files_hashed': supports,
            'delivery_files_hashed': checked, 'source_map_entries': maps,
            'unique_git_blobs_verified': len(blobs), 'git_tree_entries_verified': len(tree),
            'cells': cells,
            'scope': 'Technical label causality/identity and provenance only; no independent efficacy or new baseline'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Refusing to overwrite main receipt'
    result = verify(args.repo, args.source)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'cells'}))
