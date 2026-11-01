"""Main provenance audit of two separately replayed default-dispatch cells."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify(repo, source):
    main = repo/'docs/research/ws31/main'
    independent = main.parent/'independent'
    prefix = 'adapter-default-validation-r1'
    index_path = independent/(prefix+'-index.json')
    index_hash = sha(index_path)
    index = read(index_path)
    qa_path = independent/(prefix+'-qa.json')
    qa = read(qa_path)
    assert qa['status']=='PASS_TWO_DEFAULT_COMPATIBILITY_EXECUTOR_DELIVERY'
    assert qa['index_sha256']==index_hash
    plan_path = main/(prefix+'.json')
    plan = read(plan_path)
    assert index['plan_sha256']==sha(plan_path) and index['source_sha']==plan['source_sha']
    assert [c['id'] for c in index['cells']]==[c['id'] for c in plan['cells']]
    counts = {}
    for field in ('documents','dependencies','immutable_reference_files'):
        counts[field] = 0
        for rel,entry in index[field].items():
            path = Path(rel) if field=='immutable_reference_files' else independent/rel
            expected = entry['sha256'] if isinstance(entry,dict) else entry
            assert sha(path)==expected,path
            if isinstance(entry,dict):
                assert path.stat().st_size==entry['bytes'],path
            counts[field] += 1
    assert index['immutable_reference_files']==read(independent/(prefix+'-reference-integrity-before.json'))
    assert index['immutable_reference_files']==read(independent/(prefix+'-reference-integrity-after.json'))
    blobs, cells, maps = {}, [], 0
    results = supports = 0
    for cell,planned in zip(index['cells'],plan['cells']):
        folder = independent/(prefix+'-evidence')/cell['id']
        base = folder/'results'
        for rel,entry in cell['supporting_files'].items():
            path = folder/rel
            assert path.stat().st_size==entry['bytes'] and sha(path)==entry['sha256'],path
            supports += 1
        for rel,entry in cell['result_files'].items():
            path = base/rel
            assert path.stat().st_size==entry['bytes'] and sha(path)==entry['sha256'],path
            results += 1
        meta = read(base/'metadata.json')
        assert meta['status']=='SUCCEEDED' and meta['experiment_id']==cell['id']
        assert meta['git_commit']==plan['source_sha'] and meta['cpu_jobs']==2
        assert meta['build_mode']=='optimized'
        assert meta['git_repository']=='https://github.com/LarryBUPT/conweave-ns3.git'
        for rel,expected in cell['source_hashes'].items():
            assert rel not in blobs or blobs[rel]==expected
            blobs[rel] = expected
            maps += 1
        suffix = 'q12' if cell['lb']=='ws30v13-q12' else 'c2'
        receipt_path = main/('evidence/adapter-default-'+suffix+'-main-acceptance-r1.json')
        raw = read(receipt_path)
        assert raw['status']=='MAIN_PASS_DEFAULT_DISPATCH_NETWORK_COMPATIBILITY'
        assert raw['id']==cell['id'] and raw['source_sha']==plan['source_sha']
        assert raw['flows']==cell['flows']==104
        assert raw['payload_bytes']==cell['payload_bytes']==201981952
        assert raw['fct_sha256']==cell['fct_sha256'] and raw['log_sha256']==cell['log_sha256']
        assert raw['fct_sha256']==planned['reference_fct_sha256']
        cells.append(raw)
    assert maps==84 and len(blobs)==42
    for rel,expected in blobs.items():
        data = subprocess.run(['git','show',plan['source_sha']+':'+rel],cwd=source,
                              check=True,capture_output=True).stdout
        assert hashlib.sha256(data).hexdigest()==expected,rel
    tree = subprocess.run(['git','ls-tree','-r',plan['source_sha']],cwd=source,
                          check=True,capture_output=True).stdout
    assert len(tree.splitlines())==4843
    assert tree==(independent/(prefix+'-source-git-tree.txt')).read_bytes()
    receipt = read(independent/(prefix+'-receipt.json'))
    assert receipt['status']=='COMPLETE_FOR_TWO_DEFAULT_DISPATCH_NETWORK_COMPATIBILITY_CELLS_ONLY'
    assert receipt['build_commands']==2 and receipt['network_runs_started']==2
    for field in ('sync_commands','deploy_commands','core_commands','fixture_commands','reference_runs'):
        assert receipt[field]==0
    builds = [c for c in receipt['commands'] if c['operation']=='guarded-build']
    runs = [c for c in receipt['commands'] if c['operation']=='guarded-run']
    assert len(builds)==len(runs)==2
    assert [c['cell'] for c in runs]==[c['id'] for c in plan['cells']]
    assert all(c['exit_code']==0 for c in builds+runs)
    assert max(c['end_utc'] for c in builds)<=runs[0]['start_utc']
    assert runs[0]['end_utc']<=runs[1]['start_utc']
    assert read(independent/(prefix+'-guards-released.json'))['status']=='RELEASED'
    prep = read(main/'evidence/adapter-default-verifier-preparation-r1.json')
    assert sha(main/'scripts/verify_adapter_default_raw_r1.py')==prep['script_sha256']
    assert sha(plan_path)==prep['plan_sha256']
    refs = read(independent/(prefix+'-reference-review.json'))['sources']
    for rel,expected in refs.items():
        assert sha(Path(rel))==expected,rel
    assert sha(index_path)==index_hash,'Delivery changed during audit'
    return {'at_utc':datetime.now(timezone.utc).isoformat(),
            'status':'MAIN_ACCEPTED_TWO_DEFAULT_DISPATCH_NETWORK_CELLS_AND_FINAL_DELIVERY',
            'source_sha':plan['source_sha'],'plan_sha256':sha(plan_path),
            'index_sha256':index_hash,'QA_sha256':sha(qa_path),'delivery_files_hashed':counts,
            'result_files_hashed':results,'support_files_hashed':supports,'reference_sources_hashed':len(refs),
            'source_map_entries':maps,'unique_git_objects':42,'git_tree_entries':4843,
            'completed_records':208,'completed_payload_bytes':403963904,
            'cells':cells,'resources':index['resources'],'prior_reference_runs':0,'core_or_fixture_runs':0,
            'scope':'Default dispatch technical compatibility only; real endpoint lifecycle and independent V0/effects/cost remain'}


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path)
    parser.add_argument('source',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    assert not args.output.exists(),'Refusing to overwrite main acceptance'
    result = verify(args.repo,args.source)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='cells'}))
