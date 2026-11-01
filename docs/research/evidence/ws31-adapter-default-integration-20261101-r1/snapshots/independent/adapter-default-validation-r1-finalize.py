"""Local hash/raw/default-regression delivery for two new compatibility cells."""
import datetime,hashlib,importlib.util,json,pathlib,re,subprocess,sys
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parent
PREFIX='adapter-default-validation-r1'
EV=ROOT/(PREFIX+'-evidence')
SOURCE=ROOT.parents[4]/'ws31-candidates-implementation'
PROJECT=ROOT.parents[5]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()
def dump(s,v):(ROOT/(PREFIX+'-'+s)).write_text(json.dumps(v,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
def git(*a):return subprocess.check_output(['git','-C',str(SOURCE),*a])
def raw(log):
    hh={k:hashlib.sha256() for k in ('choice','route','combined','C2')};counts={};dedicated={}
    with log.open('rb') as stream:
        for line in stream:
            assert not line.startswith((b'WS31_LABEL',b'WS31_SWITCH_BOUNDARY',b'WS31_C2_BOUNDARY'))
            if line.startswith((b'WS30_CHOICE ',b'WS30_ROUTE ')):
                kind='choice' if line.startswith(b'WS30_CHOICE ') else 'route';counts[kind]=counts.get(kind,0)+1
                clean=re.sub(rb' uid=[^ \r\n]+',b'',line);hh[kind].update(clean);hh['combined'].update(clean)
            elif line.startswith(b'WS31_C2_'):
                hh['C2'].update(line);prefix=line.split(b' ',1)[0].decode('ascii');dedicated[prefix]=dedicated.get(prefix,0)+1
    return {'ordered_hashes':{k:hh[k].hexdigest() for k in ('choice','route','combined')},'observation_counts':counts,'C2_sha256':hh['C2'].hexdigest(),'C2_counts':dedicated}
def main():
    r=read(ROOT/(PREFIX+'-receipt.json'));plan=read(ROOT/(PREFIX+'-frozen-plan.json'))
    assert sha(ROOT/(PREFIX+'-frozen-plan.json'))==r['plan_sha256']=='01665606c32d7422b92f4202d23e8e571500321631ca376b5924ed67f5e7eb68'
    if r['status'].startswith('STOPPED_'):
        files={str(p.relative_to(EV)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in EV.rglob('*') if p.is_file()}
        dump('failure-evidence.json',{'status':r['status'],'error':r.get('error'),'files':files,'new_remote_actions':0})
        text=f"# 默认交付兼容停止报告\n\n固定 `{r['source_sha']}`，状态 `{r['status']}`，原因 `{r.get('error','见日志')}`。实际启动 {r['network_runs_started']} 格。已保全日志和原结果，未通过格不称完成；剩余停止，源码／入口／环境约束未推定释放。主需按原计划独核后安排接续。\n"
        (ROOT/(PREFIX+'-report.md')).write_text(text,encoding='utf-8')
        docs={p.name:sha(p) for p in ROOT.glob(PREFIX+'-*') if p.is_file() and p.name not in (PREFIX+'-index.json',PREFIX+'-qa.json')}
        dump('index.json',{'status':r['status'],'documents':docs,'files':files,'new_remote_actions_by_finalizer':0});dump('qa.json',{'status':'PASS_FOR_FAILURE_PRESERVATION_ONLY','index_sha256':sha(ROOT/(PREFIX+'-index.json'))})
        print(json.dumps({'status':r['status'],'index_sha256':sha(ROOT/(PREFIX+'-index.json')),'qa_sha256':sha(ROOT/(PREFIX+'-qa.json'))}));return
    assert r['status']=='COMPLETE_FOR_TWO_DEFAULT_DISPATCH_NETWORK_COMPATIBILITY_CELLS_ONLY' and r['network_runs_started']==2 and r['build_commands']==2
    assert all(c['status']=='PASS' for c in r['cells']) and 'error' not in r
    for k in ('sync_commands','deploy_commands','core_commands','fixture_commands','reference_runs'):assert r[k]==0
    auth=read(ROOT/(PREFIX+'-execution-authorization.json'));assert auth['plan_sha256']==r['plan_sha256'] and auth['source_sha']==r['source_sha']
    builds=read(ROOT/(PREFIX+'-all-builds-verified.json'));assert len(builds)==2;objects=builds[0]['source_hashes']
    for path,h in objects.items():assert hashlib.sha256(git('show',r['source_sha']+':'+path)).hexdigest()==h
    tree=git('ls-tree','-r',r['source_sha']);assert (ROOT/(PREFIX+'-source-git-tree.txt')).read_bytes()==tree and len(tree.splitlines())==4843
    spec=importlib.util.spec_from_file_location('adapter_default_identity',ROOT/(PREFIX+'-verifier.py'));V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)
    cells=[];nfiles=0;nsupport=0
    for c,built in zip(r['cells'],builds):
        folder=EV/c['id'];target=folder/'results';ref=pathlib.Path(c['reference_results']);m=read(folder/'remote-manifest.json')
        assert built['id']==c['id'] and m['source_head']==r['source_sha'] and m['source_hashes']==built['source_hashes']==objects and m['binary_sha256']==built['binary_sha256']==c['binary_sha256']
        for rel,info in m['files'].items():assert (target/rel).stat().st_size==info['bytes'] and sha(target/rel)==info['sha256'];nfiles+=1
        fct=next((target/'raw').glob('*/*_out_fct.txt'));log=next((target/'raw').glob('*/config.log'))
        ref_fct=next((ref/'raw').glob('*/*_out_fct.txt'));ref_log=next((ref/'raw').glob('*/config.log'))
        assert sha(ref_fct)==c['reference_fct_sha256'] and sha(ref_log)==c['reference_log_sha256']
        assert fct.read_bytes()==ref_fct.read_bytes();ident=V.verify(target/'config/traffic_trace.txt',fct,log);assert ident==c['acceptance']['all_input_verifier']
        actual=raw(log);assert actual==raw(ref_log)
        for key,h in actual['ordered_hashes'].items():assert h==c['acceptance']['ordered_hashes'][key]
        assert actual['observation_counts']==c['acceptance']['observation_counts']
        assert actual['C2_sha256']==c['compatibility']['dedicated_events']['sha256'] and actual['C2_counts']==c['compatibility']['dedicated_events']['event_counts']
        assert read(folder/'compatibility.json')==c['compatibility'] and read(folder/'acceptance.json')==c['acceptance']
        assert ident['flows']==104 and ident['payload_bytes']==201981952
        if c['lb']=='ws31-c2':assert len(c['acceptance']['timing'])==104 and ident['c2_timing_rows_checked']==104
        else:assert not actual['C2_counts']
        text=(target/'logs/build.log').read_text(encoding='utf-8');assert "'build' finished successfully" in text
        tasks=max(int(y) for x,y in re.findall(r'\[\s*(\d+)\s*/\s*(\d+)\s*\]',text));assert tasks==1468
        support={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in folder.iterdir() if p.is_file()};nsupport+=len(support)
        cells.append({'id':c['id'],'status':'PASS_DEFAULT_DISPATCH_ONLY','lb':c['lb'],'flows':ident['flows'],'payload_bytes':ident['payload_bytes'],
            'results_path':str(target),'reference_id':c['reference_id'],'reference_sha':c['reference_sha'],'reference_results':str(ref),
            'fct_sha256':sha(fct),'log_sha256':sha(log),'reference_receipt_sha256':c['reference_receipt_sha256'],'compatibility':c['compatibility'],
            'raw_recheck':actual,'C2_timing':c['acceptance']['timing'],'queue':c['acceptance']['queue'],'path':c['acceptance']['path'],
            'build_tasks':tasks,'build_duration':re.findall(r"'build' finished successfully \(([^)]+)\)",text),
            'warnings':[v for v in text.splitlines() if 'warning:' in v],'source_hashes':m['source_hashes'],'binary_sha256':m['binary_sha256'],
            'result_files':m['files'],'supporting_files':support,'run_resources':c['resource_samples']})
    refs=read(ROOT/(PREFIX+'-reference-integrity-before.json'));assert refs==read(ROOT/(PREFIX+'-reference-integrity-after.json'))
    for path,info in refs.items():assert pathlib.Path(path).stat().st_size==info['bytes'] and sha(pathlib.Path(path))==info['sha256']
    bc=[c for c in r['commands'] if c['operation']=='guarded-build'];rc=[c for c in r['commands'] if c['operation']=='guarded-run']
    assert len(bc)==len(rc)==2 and all(c['exit_code']==0 for c in r['commands']) and max(c['end_utc'] for c in bc)<min(c['start_utc'] for c in rc)
    assert [c['cell'] for c in rc]==[c['id'] for c in plan['cells']]
    assert read(ROOT/(PREFIX+'-sources-established.json'))['both_fixed_copies_verified'] and read(ROOT/(PREFIX+'-guards-released.json'))['status']=='RELEASED'
    dump('phase-order.json',{'status':'PASS','all_builds_before_any_run':True,'builds':bc,'runs':rc,'serial':'Prior cell terminal/transfer/acceptance before next run','no_reference_core_fixture_reruns':True})
    res=r['build_resources'];assert res['max_sampled_cc1plus_count']<=4 and res['max_sampled_building_metadata_count']<=2 and not res['other_user_seen'] and not res['unknown_project_seen']
    integrity={'status':'PASS_TWO_DEFAULT_DISPATCH_NETWORK_CELLS','source_sha':r['source_sha'],'cells':2,'failures':0,'completed_records':208,'completed_payload_bytes':403963904,
        'result_files_checked':nfiles,'support_files_hashed':nsupport,'fixed_git_objects':len(objects),'source_map_entries':2*len(objects),'source_tree_entries':4843,
        'immutable_reference_files':len(refs),'new_full_builds':2,'new_network_calls':2,'sync':0,'deploy':0,'core':0,'fixture':0,'reference_runs':0,
        'guards_released':True,'main_independent_raw_acceptance':'PENDING separate main replay','new_remote_actions_by_finalizer':0,
        'source_head_observed':git('rev-parse','HEAD').decode().strip(),'source_status_observed':git('status','--porcelain').decode()}
    dump('integrity.json',integrity)
    base=PROJECT/'参考文献/候选';refpaths=[base/p for p in ['README.md','reading-log.md','papers/diffflow-2016/analysis-technical.md','papers/diffflow-2016/verification.md']]
    dump('reference-review.json',{'sources':{str(p):sha(p) for p in refpaths},'version':'DiffFlow arXiv1604.05107v1,6pages,fixed technical/verification archive',
        'borrowing':'Separate business identity and control/dispatch activation; establish unchanged default path before studying new lifecycle behavior',
        'applicability':'This node checks the extracted default transport dispatch and one-shot C2 wait against exact old raw while labels and lifecycle controls are off',
        'difference':'DiffFlow advertises sampled long-flow identity before spraying; this project keeps pinned QPs and checks default dispatch without installing new policies',
        'not_extrapolated':['No endpoint drain/reuse/generation proof','No independentV0 or business efficacy/cost acceptance','No author outcome transfer or new combined baseline'],
        'evidence_priority':'Fixed1f917source and the two original new experiment raw IDs'})
    report=f'''# 新交付入口默认网络兼容报告

日期：2026 年 11 月 1 日。固定 `{r['source_sha']}` 的 Q12／C2 两格默认兼容均 PASS，共 208 条完成、403,963,904 B。完整 FCT、有序 CHOICE／ROUTE 只去 uid 后恢复各自固定参考；C2 的全部 DEMAND／LAUNCH／FINISH／STATE 字节流也精确恢复。主原始数据独验待完成。

## 1. 授权与来源

冻结计划 SHA-256 为 `{r['plan_sha256']}`。原条件状态未改，实际执行以[独立授权收据]({PREFIX}-execution-authorization.json)和本轮新门为依据。17 例适配器主验、明确约束释放和唯一副 idle 已满足。源 SHA 改变即失效的规则保持，未替换源。

每格 104 请求、201,981,952 B，共用 correctness r1 输入和 OS2 100 Gbps 拓扑，DCQCN、PFC 0、IRN 1、buffer 9 MiB、seed 1、0.01 s、netload 10、观测 2。新 label profile 和旧干预／故障关闭。

新 Q12 `20261101-153000-ws31-adapterdef-r1-q12` 对照 c4 的 `20261101-062753-ws31-zr1-q12`；新 C2 `20261101-153000-ws31-adapterdef-r1-c2` 对照 2ed 的 `20261101-124500-ws31-labeldef-r1-c2`。两份主参考收据、完整 FCT／log、元数据及两个输入共 12 份只读文件在执行前后及封装时哈希相同。

## 2. 实际执行与完整回归

新本地进程、全部远程进程及 Git 助手、缓存 origin／引用／对象／树／clean、worker、新 ID 与实时资源门通过。复用已匹配的缓存与 worker，sync／deploy 为 0。两个新隔离 optimized `-j2` 全构建各 1,468 项通过后，才按 Q12→C2 串行网络运行，没有构建与仿真交叠，见[顺序证据]({PREFIX}-phase-order.json)。

每格全部原请求身份、字节和需求起点均检查，没有筛选完成时间窗。实际包标签按原请求保持。有序 CHOICE／ROUTE 比较保留时间、四元组、候选、队列、tag 和端口，仅删除 uid；完整 FCT 按原始字节比较。没有新标签或适配器夹具观测。

C2 的 104 条 demand／launch／finish 按原四元组及流索引核对，冻结 StartHash 决定是否和等待多久，原需求 FCT 包含等待。三个事件表和一条终态账全部精确匹配参考，等待、launch／finish 与原起点再次核对。Q12 没有 C2 专属事件。两格队列字节守恒，丢弃、拒收、账本违规、观察溢出和 QP 内端口变化均为 0。

## 3. 来源完整性与资源

{nfiles} 份结果逐文件核大小及 SHA-256，{nsupport} 份支持文件、每格 {len(objects)} 个固定 Git 对象及 4,843 项完整树已核。构建前／运行后源映射和实际 network-load-balance 二进制匹配，配置、输入及 raw 保留。完整入口见[索引]({PREFIX}-index.json)与[完整性记录]({PREFIX}-integrity.json)。

构建每 5 秒采样，共 {res['sample_count']} 次，最大采样编译前端 {res['max_sampled_cc1plus_count']}、并行构建 {res['max_sampled_building_metadata_count']}，最高负载 {res['max_sampled_load_1m']:.2f}，最低可用内存约 {res['min_sampled_available_gib']:.3f} GiB、磁盘约 {res['min_sampled_free_gib']:,.3f} GiB。未采到其他用户或未知作业。仿真每 2 秒采样且串行，数字均为采样界值。模型没有执行或声称切换。

旧参考、核心、17 例夹具、Ofan/RR、旧控制器与矩阵均未重跑，成功 ID 未覆盖。两个源码副本及网络调用终态核验后，源码／入口／环境约束已明确释放，见[释放收据]({PREFIX}-guards-released.json)。

## 4. 结论与后继

本次验证默认虚拟交付入口提取在 Q12 公共路径与 C2 等待路径、本固定输入上保持兼容。它不建立新效果或新组合基线。真实端点退出、旧包排空、跨代 generation／drain／reuse、独立 C1 V0 和三个候选双侧业务效果／状态／运行成本继续由主总计划承接。

已从候选 README／reading-log 复核 DiffFlow v1 技术与核验记录，保留业务身份和控制生效位置的区分；其分类广告与喷洒及作者效果不代替本轮 default dispatch raw，见[参考复核]({PREFIX}-reference-review.json)。本副停止新增执行，等待主独核与下一单目标。
'''
    (ROOT/(PREFIX+'-report.md')).write_text(report,encoding='utf-8')
    parts=[('本对话目标','按明确授权执行固定新源 Q12／C2 两格默认兼容，两个新隔离构建后串行，旧参考只读。'),
        ('已确认的项目事实',f"固定 `{r['source_sha']}`，计划 SHA-256 `{r['plan_sha256']}`，条件计划原字节保留，另有当前执行授权。每格 104 请求、201,981,952 B，profile 0。"),
        ('已完成工作',f"全部新门通过，两个 optimized-j2 全构建各 1,468 项完成后串行两格，2/2 PASS，共 208 条完成、403,963,904 B。完整 FCT／uid-only CHOICE-ROUTE 与全部 C2 事件恢复参考，见[报告]({PREFIX}-report.md)。"),
        ('已形成的设计决策','默认兼容按完整原始字节及保留实际标签的有序事件判定；C2 等待计入原需求起点。只读参考不重跑，原条件冻结与当前授权分开记录。'),
        ('当前状态',f"`COMPLETE FOR TWO DEFAULT DISPATCH COMPATIBILITY CELLS ONLY`。{nfiles} 结果、{nsupport} 支持、{len(objects)} 唯一对象／{2*len(objects)} 来源映射和 4,843 树项已核；全部约束释放。主原日志独验待完成。"),
        ('未解决问题','真实端点退出／排空／跨代复用及 generation／drain／reuse、独立 C1 V0、三候选双侧业务效果和状态／运行成本仍必做；本次不形成新组合基线。'),
        ('后续推荐动作','主独立核两格 raw、实际标签、C2 时刻／哈希及全部来源，通过后另冻端点或其他单目标。本副不自动进入端点、V0 或效果。'),
        ('与其他工作流的关系','仅写本轮前缀及新结果；科学源码、worker、controller、环境和权威状态未改。sync／deploy／core／fixture／reference rerun 为 0，Ofan、WS-29 与旧矩阵未执行。'),
        ('CONTEXT SNAPSHOT',f"新源 1f917f44 的默认 Q12／C2 两格 2/2 PASS。208 条完成、403,963,904 B；完整 FCT、保留 tag 的 uid-only 有序事件及全部 C2 专属流恢复固定 c4／2ed 参考。两个构建先于串行仿真，42 固定对象／84 映射／4,843 树项及 raw 哈希已核，12 参考文件不变，全部约束释放。主独验及端点／V0／效果成本继续承接，见[索引]({PREFIX}-index.json)。")]
    handoff='# 默认交付兼容九节交接\n\n日期：2026 年 11 月 1 日。来源副对话 `01a19323-2201-7b23-a0f1-905c71496d38`，接收主对话 `01a19322-95a5-76e3-a4f5-1f1e9dde81ce`。\n'
    for i,(title,body) in enumerate(parts,1):handoff+=f'\n## {i}. {title}\n\n{body}\n'
    (ROOT/(PREFIX+'-handoff.md')).write_text(handoff,encoding='utf-8')
    deps=['label-default-validation-r1-driver.py','c2-label-validation-r1-attempt2-driver.py','main-mode-dynamic-r1-driver.py','zero-control-pilot-r1-driver.py','adapter-boundary-preflight-r2-driver-additions.py']
    docs={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in ROOT.glob(PREFIX+'-*') if p.is_file() and p.name not in (PREFIX+'-index.json',PREFIX+'-qa.json')}
    dump('index.json',{'status':r['status'],'source_sha':r['source_sha'],'plan_sha256':r['plan_sha256'],'verification':integrity,'cells':cells,'documents':docs,
        'dependencies':{p:sha(ROOT/p) for p in deps},'immutable_reference_files':refs,'resources':res,'main_raw_acceptance':'PENDING_SEPARATE_MAIN_REPLAY',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    for p,info in docs.items():assert sha(ROOT/p)==info['sha256']
    links=[]
    for text in (report,handoff):
        for rel in re.findall(r'\]\(([^)]+)\)',text):assert (ROOT/rel).exists();links.append(rel)
    assert len(re.findall(r'^## \d\.',handoff,re.M))==9
    dump('qa.json',{'status':'PASS_TWO_DEFAULT_COMPATIBILITY_EXECUTOR_DELIVERY','index_sha256':sha(ROOT/(PREFIX+'-index.json')),
        'documents_rechecked':len(docs),'support_files_hashed':nsupport,'result_files_verified':nfiles,'links_checked':len(links),'handoff_sections':9,
        'reference_files_unchanged':len(refs),'guards_released':True,'main_independent_review_required':True,'new_remote_actions_by_finalizer':0,
        'style':'Original ruanyf README and six chapters previously read; headings, spacing, paragraphs, values, punctuation and structure reviewed'})
    assert read(ROOT/(PREFIX+'-index.json'))==json.loads((ROOT/(PREFIX+'-index.json')).read_bytes())
    print(json.dumps({'status':'PASS','index_sha256':sha(ROOT/(PREFIX+'-index.json')),'qa_sha256':sha(ROOT/(PREFIX+'-qa.json')),'verification':integrity},ensure_ascii=True))
if __name__=='__main__':main()
