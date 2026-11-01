"""Integration provenance/source and stopped-gate check; no remote operations."""
from pathlib import Path
import hashlib
import json
import subprocess


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(root):
    read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
    main = root/'docs/research/ws31/main'
    ind = main.parent/'independent'
    prefix = 'adapter-boundary-preflight-r1'
    idx = read(ind/(prefix+'-index.json'))
    qa = read(ind/(prefix+'-qa.json'))
    accepted = read(main/'evidence/adapter-boundary-preflight-stop-main-review-r1.json')
    receipt = read(ind/(prefix+'-receipt.json'))
    plan_path = main/'adapter-boundary-preflight-r2.json'
    plan = read(plan_path)
    assert sha((ind/(prefix+'-index.json')).read_bytes()) == qa['index_sha256'] == accepted['index_sha256'] == plan['stopped_index_sha256']
    assert sha((ind/(prefix+'-qa.json')).read_bytes()) == accepted['QA_sha256'] == plan['stopped_QA_sha256']
    assert idx['source_sha'] == accepted['source_sha'] == plan['source_sha'] == '1f917f44fcfb88e61f3ad22c5cc75fa3a06b6c0e'
    counts = {}
    for group in ['documents', 'dependencies']:
        for rel, info in idx[group].items():
            data = (ind/rel).read_bytes()
            assert sha(data) == (info['sha256'] if isinstance(info,dict) else info),rel
            if isinstance(info,dict):assert len(data) == info['bytes']
        counts[group] = len(idx[group])
    folder = Path(idx['support_path'])
    for rel,info in idx['support_files'].items():
        data = (folder/rel).read_bytes()
        assert sha(data) == info['sha256'] and len(data) == info['bytes']
    counts['support_files'] = len(idx['support_files'])
    refs = read(ind/(prefix+'-reference-review.json'))
    for rel,h in refs['sources'].items():assert sha(Path(rel).read_bytes()) == h
    counts['reference_files'] = len(refs['sources'])
    assert counts == {'documents':22,'dependencies':2,'support_files':3,'reference_files':4}
    assert receipt['sync_commands'] == 1 and len(receipt['commands']) == 1
    assert receipt['commands'][0]['operation'] == 'guarded-sync' and receipt['commands'][0]['exit_code'] == 0
    for key in ['build_commands','fixture_commands','core_commands','network_runs_started','deploy_commands']:
        assert receipt[key] == 0
    resource = read(folder/'resources-before-build.json')
    assert resource['gate_pass'] is False and resource['utc'] == accepted['gate_sample_utc']
    assert resource['unknown_project_jobs'] == [{'comm':'git-remote-http','cwd':'/home/fnl/lzy/code/conweave-ns3','pid':297502}]
    diagnosis = read(ind/(prefix+'-process-diagnosis.json'))
    assert diagnosis['target_pid'] == 297502 and diagnosis['exists'] is False and not diagnosis['ancestors']
    assert diagnosis['recorded_utc'] == accepted['PID_absence_observed_utc']
    assert diagnosis['remote_mutations'] == diagnosis['process_signals_sent'] == 0
    cache = read(ind/(prefix+'-cache-after-sync.json'))
    assert cache['requested_commit_exists'] and cache['new_id_absent'] and cache['clean'] == ''
    assert cache['branch_ref'] == plan['source_sha']
    review = read(ind/(prefix+'-source-review.json'))
    assert review['status'] == 'PASS_STATIC_SOURCE_REVIEW_EXECUTION_PENDING'
    assert review['planned_cases'] == {'C1':5,'C2':10,'C3':2}
    assert review['changed_file_hashes'] == plan['source_changes_sha256']
    impl = root.parent/'ws31-candidates-implementation'
    git = lambda *args:subprocess.check_output(['git','-C',str(impl),*args])
    for path,h in idx['fixed_local_source_objects'].items():assert sha(git('show',plan['source_sha']+':'+path)) == h,path
    assert len(idx['fixed_local_source_objects']) == 42
    tree = git('ls-tree','-r',plan['source_sha'])
    assert tree == (ind/(prefix+'-source-git-tree.txt')).read_bytes() and len(tree.splitlines()) == 4843
    assert git('rev-parse',plan['source_sha']+'^').decode().strip() == plan['parent_sha']
    assert set(git('diff','--name-only',plan['parent_sha'],plan['source_sha']).decode().splitlines()) == set(plan['source_changes_sha256'])
    for path,h in plan['source_changes_sha256'].items():assert sha(git('show',plan['source_sha']+':'+path)) == h
    cc = git('show',plan['source_sha']+':src/applications/model/rdma-client.cc').decode()
    seam = '  DispatchRequest(demand);\n}\n\nvoid RdmaClient::DispatchRequest (uint64_t demand)\n{\n'
    assert cc.count(seam) == 1
    assert cc.replace(seam,'') == git('show',plan['parent_sha']+':src/applications/model/rdma-client.cc').decode()
    assert git('rev-parse','HEAD').decode().strip() == plan['source_sha']
    assert git('branch','--show-current').decode().strip() == plan['branch']
    assert not git('status','--porcelain').strip()
    assert git('remote','get-url','--push','origin').decode().strip() == 'https://github.com/LarryBUPT/conweave-ns3.git'
    assert git('rev-parse','refs/remotes/origin/'+plan['branch']).decode().strip() == plan['source_sha']
    assert sha(plan_path.read_bytes()) == 'e09f0883fe8839f5e77ee2797ebbf75aeb88e0fa9959b7b7ddf84b5acb328061'
    assert plan['authorized_sync_commands'] == plan['authorized_deploy_commands'] == 0
    assert plan['resource_gate']['parallel_builds'] == 1 and plan['resource_gate']['jobs_per_build'] == 2
    assert plan['resource_gate']['network_simulation_concurrency'] == 0
    assert [e['candidate'] for e in plan['ordered_executions']] == ['C1','C2','C3']
    assert [e['case_count'] for e in plan['ordered_executions']] == [5,10,2]
    assert plan['id'] != plan['stopped_id'] and plan['pre_dispatch_idle_cursor'].endswith(':87')
    return {'status':'PASS_STOP_PROVENANCE_AND_UNCHANGED_RECOVERY_PLAN','fixed_adapter_source':plan['source_sha'],'last_network_validated_source':plan['parent_sha'],'files_hashed':counts,'fixed_Git_objects_hashed':42,'fixed_tree_entries':4843,'new_source_files':5,'RdmaClient_extraction_reversal_matches_parent':True,'clean_exclusive_checkout_and_personal_origin_tracking_verified':True,'prior_sync':1,'prior_build_fixture_core_network_deploy':0,'source_copy_established':False,'unknown_PID':297502,'gate_utc':resource['utc'],'PID_later_absence_utc':diagnosis['recorded_utc'],'ownership':'UNKNOWN; no ancestry, neither own-sync nor another-user attribution','process_signals':0,'r2_plan_sha256':sha(plan_path.read_bytes()),'r2_id':plan['id'],'r2_sync_deploy_cache_mutation_authorized':False,'r2_fixture_counts_planned':[5,10,2],'r2_outcomes_accepted_here':False,'source_entry_env_guard':'R1 held guard continues through gated r2; no silent release','network_acceptance_unchanged':41,'Integration_remote_actions_tests_or_experiments':False}


if __name__ == '__main__':
    out = Path(__file__).with_name('source-verification.json')
    if out.exists():raise RuntimeError('Refusing to overwrite Integration evidence')
    result = verify(Path.cwd())
    out.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({k:result[k] for k in ['status','files_hashed','fixed_Git_objects_hashed','fixed_tree_entries','prior_sync','prior_build_fixture_core_network_deploy']}))
