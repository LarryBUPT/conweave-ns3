"""Main build/artifact/provenance audit after separate adapter raw replays."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify(repo, source):
    main = repo/'docs/research/ws31/main'
    independent = main.parent/'independent'
    prefix = 'adapter-boundary-preflight-r2'
    index_path = independent/(prefix+'-index.json')
    index_hash = digest(index_path)
    index = read(index_path)
    qa_path = independent/(prefix+'-qa.json')
    qa = read(qa_path)
    assert qa['status']=='PASS_17_ADAPTER_EXECUTOR_DELIVERY' and qa['index_sha256']==index_hash
    plan_path = main/(prefix+'.json')
    plan = read(plan_path)
    assert index['source_sha']==plan['source_sha'] and index['plan_sha256']==digest(plan_path)
    counts = {}
    for field in ('documents','dependencies','original_r1_files'):
        counts[field] = 0
        for rel,entry in index[field].items():
            path = independent/rel
            expected = entry['sha256'] if isinstance(entry,dict) else entry
            assert digest(path)==expected,path
            if isinstance(entry,dict):
                assert path.stat().st_size==entry['bytes'],path
            counts[field] += 1
    before = read(independent/(prefix+'-original-r1-integrity-before.json'))
    after = read(independent/(prefix+'-original-r1-integrity-after.json'))
    assert before==after==index['original_r1_files']
    stopped = main/'evidence/adapter-boundary-preflight-stop-main-review-r1.json'
    old = read(stopped)
    assert digest(independent/'adapter-boundary-preflight-r1-index.json')==old['index_sha256']
    assert digest(independent/'adapter-boundary-preflight-r1-qa.json')==old['QA_sha256']
    target = Path(index['results_path'])
    folder = independent/(prefix+'-evidence')/plan['id']
    assert target.resolve()==(folder/'results').resolve()
    for rel,entry in index['support_files'].items():
        path = folder/rel
        assert path.stat().st_size==entry['bytes'] and digest(path)==entry['sha256'],path
    for rel,entry in index['result_files'].items():
        path = target/rel
        assert path.stat().st_size==entry['bytes'] and digest(path)==entry['sha256'],path
    assert not any((target/'raw').rglob('*'))
    meta = read(target/'metadata.json')
    assert meta['status']=='BUILT' and meta['git_commit']==plan['source_sha'] and meta['cpu_jobs']==2
    assert meta['experiment_id']==plan['id'] and meta['build_mode']=='optimized'
    assert meta['git_repository']=='https://github.com/LarryBUPT/conweave-ns3.git'
    for rel,expected in index['source_hashes'].items():
        data = subprocess.run(['git','show',plan['source_sha']+':'+rel],cwd=source,
                              check=True,capture_output=True).stdout
        assert hashlib.sha256(data).hexdigest()==expected,rel
    assert len(index['source_hashes'])==42
    tree = subprocess.run(['git','ls-tree','-r',plan['source_sha']],cwd=source,
                          check=True,capture_output=True).stdout
    assert tree==(independent/(prefix+'-source-git-tree.txt')).read_bytes()
    assert len(tree.splitlines())==4843
    technical = read(target/'technical/adapter-boundary/receipt.json')
    assert technical==index['binary_library_artifacts']
    assert technical['source_sha']==plan['source_sha']
    assert len(technical['binaries'])==2 and len(technical['libraries'])==36
    for info in list(technical['binaries'].values())+list(technical['libraries'].values()):
        assert digest(target/info['artifact'])==info['sha256']
    remote_source = '/home/fnl/lzy/runs/'+plan['id']+'/source'
    allowed_env = {**plan['environment'],'LD_LIBRARY_PATH':remote_source+'/build',
                   'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'}
    assert technical['env_whitelist']==allowed_env
    for binary,text in technical['ldd'].items():
        assert binary in technical['binaries'] and 'not found' not in text
        found = set()
        for line in text.splitlines():
            fields = line.split()
            if fields and fields[0].startswith('libns3.'):
                assert fields[1]=='=>' and fields[0] in technical['libraries']
                assert fields[2]==remote_source+'/build/'+fields[0]
                found.add(fields[0])
        assert found==set(technical['libraries'])
    steps = technical['steps']
    assert [s['candidate'] for s in steps]==['C1','C2','C3']
    accepted = []
    last_end = None
    for step,planned in zip(steps,plan['ordered_executions']):
        name = step['candidate']
        assert step['status']=='PASS' and step['exit_code']==0 and step['coverage_pass']
        assert step['argv']==[remote_source+'/'+planned['relative_binary']]+planned['args']
        assert step['cwd']==remote_source and step['env_whitelist']==allowed_env
        if last_end is not None:
            assert step['start_utc']>=last_end
        last_end = step['end_utc']
        local_log = folder/('adapter-'+name+'.log')
        assert digest(local_log)==digest(target/'logs'/local_log.name)==step['log_sha256']
        receipt = main/('evidence/adapter-boundary-'+name.lower()+'-main-acceptance-r1.json')
        raw = read(receipt)
        assert raw['status']=='MAIN_PASS_ADAPTER_FIXTURE_RAW_REPLAY'
        assert raw['candidate']==name.lower() and raw['cases']==planned['case_count']
        assert raw['log_sha256']==step['log_sha256']
        accepted.append({'candidate':name,'main_receipt_sha256':digest(receipt),'replay':raw})
    controller = read(independent/(prefix+'-receipt.json'))
    assert controller['status']=='COMPLETE_FOR_ONE_BUILD_AND_NEW_17_ADAPTER_BOUNDARY_CASES_ONLY'
    assert controller['build_commands']==1 and controller['fixture_commands']==3
    for field in ('sync_commands','deploy_commands','network_runs_started','core_commands'):
        assert controller[field]==0
    assert len(controller['commands'])==1 and controller['commands'][0]['operation']=='guarded-build'
    assert controller['commands'][0]['exit_code']==0
    assert read(independent/(prefix+'-guards-released.json'))['status']=='RELEASED'
    build = (target/'logs/build.log').read_text(encoding='utf-8')
    assert "'build' finished successfully" in build
    tasks = max(int(y) for x,y in re.findall(r'\[\s*(\d+)\s*/\s*(\d+)\s*\]',build))
    duration = re.findall(r"'build' finished successfully \(([^)]+)\)",build)
    assert tasks>1464 and len(duration)==1
    reference = read(independent/(prefix+'-reference-review.json'))
    for name,expected in reference['sources'].items():
        assert digest(Path(name))==expected,name
    assert digest(index_path)==index_hash,'Delivery changed during audit'
    return {'at_utc':datetime.now(timezone.utc).isoformat(),
            'status':'MAIN_ACCEPTED_ONE_FULL_BUILD_AND_17_ADAPTER_CASES_AND_DELIVERY',
            'source_sha':plan['source_sha'],'id':plan['id'],'plan_sha256':digest(plan_path),
            'index_sha256':index_hash,'QA_sha256':digest(qa_path),'files_hashed':counts,
            'support_files_hashed':len(index['support_files']),'result_files_hashed':len(index['result_files']),
            'reference_files_hashed':len(reference['sources']),'fixed_git_objects':42,
            'git_tree_entries':4843,'build_tasks':tasks,'build_duration':duration[0],
            'fixture_processes':3,'cases':17,'real_QPs':0,'network_runs':0,'core_repeats':0,
            'binary_artifacts':2,'resolved_ns3_library_artifacts':36,'raw_acceptances':accepted,
            'resources':index['resources'],'stopped_r1_evidence_preserved':True,
            'scope':'Production adapter fixture boundaries only; real endpoint lifecycle/default network compatibility/independent V0 and effects/cost remain'}


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path)
    parser.add_argument('source',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    assert not args.output.exists(),'Refusing to overwrite main acceptance'
    result = verify(args.repo,args.source)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='raw_acceptances'}))
