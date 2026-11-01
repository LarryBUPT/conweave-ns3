"""Freeze authorized default-network plan and verify immutable references locally."""
import hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parent
PREFIX='adapter-default-validation-r1'
MAIN=ROOT.parent/'main'
REPO=ROOT.parents[4]/'ws31-candidates-implementation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def git(*a):return subprocess.check_output(['git','-C',str(REPO),*a])
def main():
    src=MAIN/(PREFIX+'.json');assert sha(src)=='01665606c32d7422b92f4202d23e8e571500321631ca376b5924ed67f5e7eb68'
    plan=read(src);authpath=MAIN/'evidence/adapter-default-execution-authorization-r1.json';auth=read(authpath)
    assert auth['status']=='CONDITIONAL_PLAN_PREREQUISITES_MET_MAIN_DISPATCH_AUTHORIZED' and auth['plan_sha256']==sha(src) and auth['source_sha']==plan['source_sha']
    assert sha(MAIN/auth['main_preflight_acceptance'])==auth['main_preflight_acceptance_sha256']
    assert git('rev-parse','HEAD').decode().strip()==plan['source_sha'] and not git('status','--porcelain').strip()
    assert git('rev-parse','origin/feature/ws31-candidates').decode().strip()==plan['source_sha']
    for source,suffix in [(src,'frozen-plan.json'),(src.with_suffix('.md'),'frozen-plan.md'),(authpath,'execution-authorization.json')]:
        target=ROOT/(PREFIX+'-'+suffix);assert not target.exists();target.write_bytes(source.read_bytes())
    references={}
    for c in plan['cells']:
        receipt=MAIN/c['reference_receipt'];assert sha(receipt)==c['reference_receipt_sha256']
        target=pathlib.Path(c['reference_results']);m=read(target/'metadata.json');assert m['git_commit']==c['reference_sha'] and m['experiment_id']==c['reference_id'] and m['status']=='SUCCEEDED'
        fct=next((target/'raw').glob('*/*_out_fct.txt'));log=next((target/'raw').glob('*/config.log'))
        assert sha(fct)==c['reference_fct_sha256'] and sha(log)==c['reference_log_sha256']
        for p in (receipt,target/'metadata.json',fct,log,target/'config/traffic_trace.txt',target/'config/topology.txt'):references[str(p)]={'bytes':p.stat().st_size,'sha256':sha(p)}
    (ROOT/(PREFIX+'-reference-integrity-before.json')).write_text(json.dumps(references,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    tree=git('ls-tree','-r',plan['source_sha']);assert len(tree.splitlines())==4843
    (ROOT/(PREFIX+'-source-git-tree.txt')).write_bytes(tree)
    previous=read(ROOT/'adapter-boundary-preflight-r2-index.json')['source_hashes']
    for path,h in previous.items():assert hashlib.sha256(git('show',plan['source_sha']+':'+path)).hexdigest()==h
    (ROOT/(PREFIX+'-source-prerequisite.json')).write_text(json.dumps({'status':'PASS_FIXED_SOURCE_AND_EXPLICIT_AUTHORIZATION','source_sha':plan['source_sha'],
        'fixed_git_objects':previous,'whole_tree_entries':4843,'conditional_plan_kept_original':True,'authorization_path':str(authpath),'authorization_sha256':sha(authpath),
        'main_adapter_acceptance_sha256':auth['main_preflight_acceptance_sha256'],'reference_files':len(references),'old_reference_or_fixture_executions':0},ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    ev=ROOT/(PREFIX+'-evidence');ev.mkdir();(ev/'.gitignore').write_text('*\n!.gitignore\n',encoding='ascii')
    (ROOT/(PREFIX+'-verifier.py')).write_bytes((ROOT/'label-default-validation-r1-verifier.py').read_bytes())
    print(json.dumps({'status':'PREPARATION_PASS','fixed_objects':len(previous),'reference_files_verified':len(references),'explicit_network_authorization_verified':True}))
if __name__=='__main__':main()
