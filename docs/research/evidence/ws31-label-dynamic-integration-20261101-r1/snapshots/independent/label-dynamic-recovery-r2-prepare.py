"""Preserve r1 bytes, prepare separately corrected checker and replay eight raw cells."""
import ast,copy,difflib,hashlib,importlib.util,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
PREFIX='label-dynamic-recovery-r2'
OLD='label-dynamic-validation-r1'
EV=ROOT/(PREFIX+'-evidence')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(suffix,value):(ROOT/(PREFIX+'-'+suffix)).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def module():
    spec=importlib.util.spec_from_file_location('corrected_dynamic_checker',ROOT/(PREFIX+'-checker.py'))
    q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q);return q
def immutable():
    result={}
    for p in ROOT.glob(OLD+'-*'):
        if p.is_file():result[p.name]={'bytes':p.stat().st_size,'sha256':sha(p)}
        elif p.is_dir():
            for f in p.rglob('*'):
                if f.is_file():result[str(f.relative_to(ROOT))]={'bytes':f.stat().st_size,'sha256':sha(f)}
    return result
def main():
    plan=ROOT.parent/'main'/ (PREFIX+'.json')
    assert sha(plan)=='d1dce31271e4756e4c90084bc01006e9c4a670de830d24414260a71faacd9599'
    dst=ROOT/(PREFIX+'-frozen-plan.json');assert not dst.exists();dst.write_bytes(plan.read_bytes())
    assert sha(ROOT/(OLD+'-index.json'))=='f0df25a481b353aac8c5d2ca2f5972da43b3d5d203a87d71e25468508601ad25'
    assert sha(ROOT/(OLD+'-qa.json'))=='6a1d280dcb0804365e6565b7afd90d8a90df50276f4f7e681bc8b0c715cee922'
    original=immutable();dump('original-r1-integrity-before.json',original)
    source=(ROOT/(OLD+'-checker.py')).read_text(encoding='utf-8')
    old="""        assert obs['counts']==ref['ordered']['counts']
        for k in ('choice_without_tag','route_without_tag','combined_without_tag'):assert obs['hashes'][k]==ref['ordered']['hashes'][k]
        if cell['lb']=='ws31-c3':assert detail['source_first']==ref['source_first']"""
    new="""        compare_reference(cell,obs,ref,detail,path[0],rows)"""
    assert source.count(old)==1
    helper='''def compare_reference(cell,obs,ref,detail,path,rows):
    # C3 source admissions are specialized events. Generic CHOICE equivalence
    # is required only for C2, as in the original frozen contract.
    if cell['lb']=='ws31-c2':
        assert obs['counts']==ref['ordered']['counts']
        for k in ('choice_without_tag','route_without_tag','combined_without_tag'):assert obs['hashes'][k]==ref['ordered']['hashes'][k]
    else:
        assert cell['lb']=='ws31-c3'
        n=cell['flow_count']
        fresh=[v for prefix,v,line in rows if prefix=='WS31_C3_ROUTE' and v['fresh']]
        assert obs['counts']['choice']==2*n and ref['ordered']['counts']['choice']==3*n
        assert len(fresh)==len(detail['source_first'])==n and path['switch_qps']==3*n
        assert obs['counts']['route']==ref['ordered']['counts']['route']
        assert obs['hashes']['route_without_tag']==ref['ordered']['hashes']['route_without_tag']
        assert detail['source_first']==ref['source_first']

'''
    corrected=source.replace(old,new).replace('def verify(cell,target,ref=None):',helper+'def verify(cell,target,ref=None):')
    ast.parse(corrected)
    path=ROOT/(PREFIX+'-checker.py');assert not path.exists();path.write_text(corrected,encoding='utf-8')
    (ROOT/(PREFIX+'-checker.patch')).write_text(''.join(difflib.unified_diff(source.splitlines(True),corrected.splitlines(True),fromfile=OLD+'-checker.py',tofile=PREFIX+'-checker.py')),encoding='utf-8')
    EV.mkdir();(EV/'.gitignore').write_text('*\n!.gitignore\n',encoding='ascii')
    q=module();assert q.precheck()['status']=='PASS'
    oldreceipt=read(ROOT/(OLD+'-receipt.json'));ref=read(ROOT/(OLD+'-new-q12-reference.json'))
    accepted=[]
    for c in oldreceipt['cells'][:8]:
        target=ROOT/(OLD+'-evidence')/c['id']/'results';a=q.verify(c,target,ref if c['ws31_label_profile'] else None)
        assert a['status']=='PASS';folder=EV/c['id'];folder.mkdir()
        (folder/'offline-acceptance.json').write_text(json.dumps(a,indent=2)+'\n',encoding='utf-8')
        accepted.append({'id':c['id'],'status':'PASS_OFFLINE_CORRECTED_FROZEN_CONTRACT','raw_path':str(target),
            'raw_exists':any((target/'raw').rglob('*')),'acceptance_sha256':sha(folder/'offline-acceptance.json'),
            'flows':a['identity']['flows'],'payload_bytes':a['identity']['payload_bytes']})
    c=oldreceipt['cells'][7];target=ROOT/(OLD+'-evidence')/c['id']/'results'
    a=read(EV/c['id']/'offline-acceptance.json');rows=q.records(next((target/'raw').glob('*/config.log')))
    q.compare_reference(c,a['ordered'],ref,a['mechanism'],a['path'],rows)
    examples=[]
    def rejected(name,obs,reference):
        try:q.compare_reference(c,obs,reference,a['mechanism'],a['path'],rows)
        except AssertionError:examples.append({'name':name,'status':'REJECTED_AS_REQUIRED'});return
        raise AssertionError('Negative example incorrectly accepted: '+name)
    broken=copy.deepcopy(a['ordered']);broken['hashes']['route_without_tag']='0'*64;rejected('C3 altered normalized ROUTE hash',broken,ref)
    broken=copy.deepcopy(ref);broken['source_first'][0]['chosen']+=1;rejected('C3 altered first source projection',a['ordered'],broken)
    c2=oldreceipt['cells'][4];c2a=read(EV/c2['id']/'offline-acceptance.json');broken=copy.deepcopy(c2a['ordered']);broken['hashes']['combined_without_tag']='0'*64
    try:q.compare_reference(c2,broken,ref,c2a['mechanism'],c2a['path'],[])
    except AssertionError:examples.append({'name':'C2 altered full combined hash','status':'REJECTED_AS_REQUIRED'})
    else:raise AssertionError('C2 full hash check lost')
    assert immutable()==original,'Original r1 evidence changed during preparation'
    dump('offline-negative-examples.json',{'status':'PASS','examples':examples,'data_mutation':'In-memory copies only; original raw unchanged','new_simulations':0})
    dump('offline-eight-acceptance.json',{'status':'PASS_EIGHT_ORIGINAL_RAW_OFFLINE','accepted_cells':accepted,'completed_records':120,'payload_bytes':1966080,
        'original_checker_sha256':sha(ROOT/(OLD+'-checker.py')),'corrected_checker_sha256':sha(path),'correction_diff_sha256':sha(ROOT/(PREFIX+'-checker.patch')),
        'contract':'C3 FCT/ROUTE/source projection;30common+15specialized vs45Q12 separately; C2 fullCHOICE unchanged',
        'historical_raw_flag':'Original C3p1 raw_preserved marker is not changed; actual raw exists and all identity/UID/presence/time/state checks pass',
        'build_simulation_core_sync_deploy_executions':0,'original_files_preserved':len(original)})
    print(json.dumps({'status':'PASS_OFFLINE_EIGHT_AND_NEGATIVE_EXAMPLES','accepted_cells':8,'preserved_r1_files':len(original),'corrected_checker_sha256':sha(path)}))
if __name__=='__main__':main()
