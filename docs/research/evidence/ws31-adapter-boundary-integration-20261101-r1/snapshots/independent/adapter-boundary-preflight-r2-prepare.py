"""Freeze recovery and preserve r1; generate driver with no sync/deploy path."""
import ast,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parent
PREFIX='adapter-boundary-preflight-r2'
OLD='adapter-boundary-preflight-r1'
REPO=ROOT.parents[4]/'ws31-candidates-implementation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(REPO),*a])
def dump(s,v):(ROOT/(PREFIX+'-'+s)).write_text(json.dumps(v,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
def main():
    p=ROOT.parent/'main'/(PREFIX+'.json');assert sha(p)=='e09f0883fe8839f5e77ee2797ebbf75aeb88e0fa9959b7b7ddf84b5acb328061'
    plan=json.loads(p.read_text(encoding='utf-8'));assert sha(ROOT/(OLD+'-index.json'))==plan['stopped_index_sha256'] and sha(ROOT/(OLD+'-qa.json'))==plan['stopped_QA_sha256']
    files={}
    for f in ROOT.glob(OLD+'-*'):
        for item in [f] if f.is_file() else f.rglob('*'):
            if item.is_file():files[str(item.relative_to(ROOT))]={'bytes':item.stat().st_size,'sha256':sha(item)}
    dump('original-r1-integrity-before.json',files)
    for src,suffix in [(p,'frozen-plan.json'),(p.with_suffix('.md'),'frozen-plan.md')]:
        dst=ROOT/(PREFIX+'-'+suffix);assert not dst.exists();dst.write_bytes(src.read_bytes())
    review=json.loads((ROOT/(OLD+'-source-review.json')).read_text(encoding='utf-8'));assert review['no_material_source_issue_found'] and review['source_sha']==plan['source_sha']
    assert git('rev-parse','HEAD').decode().strip()==plan['source_sha'] and not git('status','--porcelain').strip()
    for path,h in plan['source_changes_sha256'].items():assert hashlib.sha256(git('show',plan['source_sha']+':'+path)).hexdigest()==h
    objects=json.loads((ROOT/(OLD+'-index.json')).read_text(encoding='utf-8'))['fixed_local_source_objects']
    for path,h in objects.items():assert hashlib.sha256(git('show',plan['source_sha']+':'+path)).hexdigest()==h
    tree=git('ls-tree','-r',plan['source_sha']);assert len(tree.splitlines())==4843 and tree==(ROOT/(OLD+'-source-git-tree.txt')).read_bytes()
    (ROOT/(PREFIX+'-source-git-tree.txt')).write_bytes(tree)
    dump('source-review.json',dict(review,reused_original_review_sha256=sha(ROOT/(OLD+'-source-review.json')),fixed_42_objects_rechecked=objects))
    ev=ROOT/(PREFIX+'-evidence');ev.mkdir();(ev/'.gitignore').write_text('*\n!.gitignore\n',encoding='ascii')
    (ROOT/(PREFIX+'-verify.py')).write_bytes((ROOT/(OLD+'-verify.py')).read_bytes())
    text=(ROOT/(OLD+'-driver.py')).read_text(encoding='utf-8')
    text=text.replace("PREFIX='adapter-boundary-preflight-r1'","PREFIX='adapter-boundary-preflight-r2'")
    text=text.replace('28fc60860857cb6fe3029c72d62b1a50b0d0e053d9d2927d7655e57afb483926','e09f0883fe8839f5e77ee2797ebbf75aeb88e0fa9959b7b7ddf84b5acb328061')
    tree=ast.parse(text);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sync')
    lines=text.splitlines(True);text=''.join(lines[:fn.lineno-1]+lines[fn.end_lineno:])
    old="resource('resources-initial',True);current=cache('cache-before-sync');sync(current);cache('cache-after-sync',True)"
    assert old in text;text=text.replace(old,"process_gate('processes-initial');resource('resources-initial',True);cache('cache-read-only',True);process_gate('processes-before-build')")
    text=text.replace(" 'new_id_absent':all(not os.path.lexists('/home/fnl/lzy/'+p+'/'+i) for p in ['runs','results']),", " 'new_id_absent':all(not os.path.lexists('/home/fnl/lzy/'+p+'/'+i) for p in ['runs','results']),\n 'old_reserved_id_absent':all(not os.path.lexists('/home/fnl/lzy/'+p+'/20261101-143000-ws31-adapter-preflight-r1') for p in ['runs','results']),")
    text=text.replace("and not r['clean'] and r['new_id_absent']","and not r['clean'] and r['new_id_absent'] and r['old_reserved_id_absent']")
    text=text.replace("assert read(OUT/(PREFIX+'-source-review.json'))['no_material_source_issue_found']","assert read(OUT/(PREFIX+'-source-review.json'))['no_material_source_issue_found'];preserved()")
    text=text.replace("assert r['step']['status']=='PASS',name+' fixture failed'", "assert r['step']['status']=='PASS',name+' fixture failed'\n    checked=V.c2(log) if name=='C2' else V.switch(log,name);dump('raw-verification-'+name+'.json',checked)")
    text=text.replace("dump('guards-released.json',", "preserved();dump('original-r1-integrity-after.json',read(OUT/(PREFIX+'-original-r1-integrity-before.json')))\n    dump('guards-released.json',")
    extra=(ROOT/(PREFIX+'-driver-additions.py')).read_text(encoding='utf-8')
    text=text.replace("def main():",extra+'\ndef main():')
    ast.parse(text);assert 'def sync(' not in text and "'guarded-sync'" not in text
    (ROOT/(PREFIX+'-driver.py')).write_text(text,encoding='utf-8')
    print(json.dumps({'status':'R2_PREPARED','r1_files_preserved':len(files),'source_objects_rechecked':len(objects),'sync_paths_removed':True}))
if __name__=='__main__':main()
