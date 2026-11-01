"""Local-only fixed-source review record. No build or executable invocation."""
import hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parent
PREFIX='adapter-boundary-preflight-r1'
REPO=ROOT.parents[4]/'ws31-candidates-implementation'
def git(*a):return subprocess.check_output(['git','-C',str(REPO),*a])
def digest(data):return hashlib.sha256(data).hexdigest()
def main():
    mainroot=ROOT.parent/'main';p=mainroot/(PREFIX+'.json');raw=p.read_bytes()
    assert digest(raw)=='28fc60860857cb6fe3029c72d62b1a50b0d0e053d9d2927d7655e57afb483926'
    plan=json.loads(raw);sha=plan['source_sha'];parent=plan['parent_sha']
    assert git('rev-parse','HEAD').decode().strip()==sha and not git('status','--porcelain').strip()
    assert git('rev-parse','origin/feature/ws31-candidates').decode().strip()==sha
    changes=git('diff','--name-only',parent,sha).decode().splitlines();assert set(changes)==set(plan['source_changes_sha256'])
    for path,h in plan['source_changes_sha256'].items():assert digest(git('show',sha+':'+path))==h
    production=['src/applications/model/rdma-client.cc','src/applications/model/rdma-client.h','src/point-to-point/model/switch-node.h']
    restored={}
    for path in production:
        current=git('show',sha+':'+path)
        if path.endswith('rdma-client.cc'):
            token=b'  DispatchRequest(demand);\n}\n\nvoid RdmaClient::DispatchRequest (uint64_t demand)\n{\n'
            assert current.count(token)==1;current=current.replace(token,b'')
        elif path.endswith('rdma-client.h'):
            token=b'  // Transport seam for the standalone event-boundary fixture. Production\n  // dispatch retains the same driver call after demand/launch accounting.\n  virtual void DispatchRequest (uint64_t demandStartNs);\n'
            assert current.count(token)==1;current=current.replace(token,b'').replace(b'  friend class Ws31StartBoundaryProbe;\n',b'')
        else:current=current.replace(b'    friend class Ws31SwitchBoundaryProbe;\n',b'')
        assert current==git('show',parent+':'+path),path
        restored[path]={'parent_sha256':digest(current),'exact_parent_after_declared_extraction_reversal':True}
    unchanged=['src/point-to-point/model/switch-node.cc','src/point-to-point/model/ws31-budget.h','src/point-to-point/model/ws31-start.h','src/point-to-point/model/ws31-quota.h','scripts/remote_worker.py','scripts/remote_experiment.py']
    for path in unchanged:assert git('show',sha+':'+path)==git('show',parent+':'+path)
    for src,suffix in [(p,'frozen-plan.json'),(mainroot/(PREFIX+'.md'),'frozen-plan.md'),(mainroot/'adapter-lifecycle-contract-r1.md','frozen-contract.md')]:
        dst=ROOT/(PREFIX+'-'+suffix);assert not dst.exists();dst.write_bytes(src.read_bytes())
    (ROOT/(PREFIX+'-source-diff.patch')).write_bytes(git('diff',parent,sha))
    tree=git('ls-tree','-r',sha);assert len(tree.splitlines())==4843
    (ROOT/(PREFIX+'-source-git-tree.txt')).write_bytes(tree)
    ev=ROOT/(PREFIX+'-evidence');ev.mkdir();(ev/'.gitignore').write_text('*\n!.gitignore\n',encoding='ascii')
    review={'status':'PASS_STATIC_SOURCE_REVIEW_EXECUTION_PENDING','no_material_source_issue_found':True,'source_sha':sha,'parent_sha':parent,
        'changed_file_hashes':plan['source_changes_sha256'],'production_reversal_proof':restored,'unchanged_adapter_cores_and_runner':unchanged,
        'packet_review':'Real PPP14+IPv4 20+UDP8+SeqTs(6+INT timestamp8)=56B framing with IntHeader::mode1. Fork UdpHeader serializes start.GetSize(); full CustomHeader reads UDP length and subtracts22B UDP/seq/INT, yielding exact payload.',
        'queue_review':'Eight actual QbbNetDevice objects with BEgressQueue, Node AddDevice port IDs used verbatim. Load reads actual GetQueue/GetNBytesTotal; queue priority3 accepts5000B below default capacity.',
        'C1_review':'Five cases call actual DoLbWs31C1. Unique intervals0-100/300-400/50-350/400-500 yield100/200/400/500B; duplicates count once. Access at19999/20000/20001ns tests expiry and no rearm. Capacity1, maxRanges1 andseq0xfffffff0+32 exercise real fallbacks; reset calls production erasure of all3tables.',
        'observer_review':'Budget Size/expired captured before diagnostic Pressure and checked unchanged after, so observer cannot silently perform missing production expiry. C3 Idle reads const Active/Conserved without expiry.',
        'C3_review':'All queues initially0, selected first hash deliberately owner2 forclass1 borrowing. Laterlabel/missingtag uses cached class. Owner activation200ns, activity edges20199/20200/20201 and actual latecall20202ns exercise expiry/renewal. Reset removes entries/live borrower but retains historical counters, permits same tuple fresh admission.',
        'C2_review':'CreateObject CompleteConstruct sets subclass TypeId and inherited attributes; protected virtual transport seam executes after original launch accounting and preserves default AddQueuePair args. SetNode avoids automatic Application scheduling. Start at10ns; controls before/same uidbothorders/after/zero; repeated Stop/Dispose preserve counters and zero fake QPs/completions.',
        'optimization_checks':'All fixture predicates use NS_FATAL_ERROR, not std assert. Root Waf auto-discovers new scratch.cc binaries.',
        'source_review_executions':0,'remote_actions':0,'planned_cases':{'C1':5,'C2':10,'C3':2},
        'scope':'Adapter boundaries only; endpoint generation/drain/reuse and default network regression not completed'}
    (ROOT/(PREFIX+'-source-review.json')).write_text(json.dumps(review,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    print('FIXED_SOURCE_STATIC_REVIEW_PASS_NO_REMOTE_ACTIONS')
if __name__=='__main__':main()
