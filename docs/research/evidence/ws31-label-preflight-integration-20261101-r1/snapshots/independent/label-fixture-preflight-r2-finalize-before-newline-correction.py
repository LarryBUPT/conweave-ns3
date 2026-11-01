"""Package already completed build/core/mock evidence without executing tests."""
import pathlib,json,hashlib,subprocess,re,datetime
ROOT=pathlib.Path(__file__).resolve().parent
PREFIX='label-fixture-preflight-r2'
REPO=ROOT.parents[4]/'ws31-candidates-implementation'
PROJECT=ROOT.parents[5]

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()
def dump(suffix,r):
    (ROOT/(PREFIX+'-'+suffix)).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def git(*args):return subprocess.check_output(['git','-C',str(REPO),*args])

def main():
    receipt=read(ROOT/(PREFIX+'-receipt.json'));plan=read(ROOT/(PREFIX+'-frozen-plan.json'))
    assert receipt['status']=='COMPLETE_FOR_SINGLE_FULL_BUILD_NEW_LABEL_CORE_AND_LOCAL_MOCK_ONLY'
    assert receipt['new_build_commands']==1 and receipt['new_cpp_core_commands']==2 and receipt['python_mock_commands']==1
    assert receipt['network_runs_started']==receipt['old_core_tests_repeated']==0 and 'error' not in receipt
    assert sha(ROOT/(PREFIX+'-frozen-plan.json'))==receipt['plan_sha256']=='7defac33294806d0369febbc79932e10263ac10112162642d0327eeb01366e3b'
    folder=ROOT/(PREFIX+'-evidence')/plan['id'];target=folder/'results'
    manifest=read(folder/'remote-manifest.json');builds=read(ROOT/(PREFIX+'-all-builds-verified.json'))
    assert len(builds)==1 and manifest['source_head']==plan['source_sha']
    assert manifest['source_hashes']==builds[0]['source_hashes']
    assert manifest['binary_sha256']==builds[0]['binary_sha256']
    for path,h in manifest['source_hashes'].items():
        assert hashlib.sha256(git('show',plan['source_sha']+':'+path)).hexdigest()==h
    for rel,info in manifest['files'].items():
        p=target/rel;assert p.stat().st_size==info['bytes'] and sha(p)==info['sha256']
    meta=read(target/'metadata.json')
    assert meta['status']=='BUILT' and meta['git_commit']==plan['source_sha'] and meta['build_mode']=='optimized' and meta['cpu_jobs']==2
    assert not any((target/'raw').rglob('*'))
    core=read(ROOT/(PREFIX+'-core-receipt.json'));mock=read(ROOT/(PREFIX+'-local-mock-receipt.json'))
    assert core['status']==mock['status']=='PASS'
    assert core==read(target/'technical/ws31-label/receipt.json')
    assert len(core['steps'])==2 and all(s['exit_code']==0 for s in core['steps'])
    compile_args=core['steps'][0]['argv'];assert '-UNDEBUG' in compile_args and '-DNDEBUG' not in compile_args
    assert all(x in compile_args for x in ['-std=c++11','-O2','-Wall','-Wextra','-pedantic'])
    assert core['assertions_enabled_symbol']=='__assert_fail'
    assert sha(target/'technical/ws31-label/core-test')==core['binary_sha256']
    for path,h in core['source_hashes'].items():assert hashlib.sha256(git('show',plan['source_sha']+':'+path)).hexdigest()==h
    log=folder/'python-local-runner-mock.log';text=log.read_text(encoding='utf-8')
    assert 'Ran 5 tests' in text and re.search(r'^OK\s*$',text,re.M) and mock['methods']==5
    assert hashlib.sha256(text.encode()).hexdigest()==mock['log_sha256']
    dump('local-mock-log-integrity.json',{'status':'PASS','raw_log_sha256':sha(log),
        'original_receipt_log_hash':mock['log_sha256'],'original_receipt_hash_basis':'UTF8 text after universal newline decoding as in driver',
        'raw_vs_text_hash_equal':sha(log)==mock['log_sha256'],'log_bytes':log.stat().st_size,
        'tests_reexecuted_during_packaging':0})
    for path,h in mock['source_hashes'].items():assert hashlib.sha256(git('show',plan['source_sha']+':'+path)).hexdigest()==h
    tree=git('ls-tree','-r',plan['source_sha']);assert (ROOT/(PREFIX+'-source-git-tree.txt')).read_bytes()==tree
    buildlog=(target/'logs/build.log').read_text(encoding='utf-8',errors='strict')
    assert "'build' finished successfully" in buildlog
    tasks=re.findall(r'\[\s*(\d+)\s*/\s*(\d+)\s*\]',buildlog)
    duration=re.findall(r"'build' finished successfully \(([^)]+)\)",buildlog)
    warnings=[line for line in buildlog.splitlines() if 'warning:' in line]
    assert all(c['exit_code']==0 for c in receipt['commands'])
    builds_cmd=[c for c in receipt['commands'] if c['operation']=='guarded-build'];assert len(builds_cmd)==1
    local_cmd=[c for c in receipt['commands'] if c['operation']=='python-local-runner-mock'];assert len(local_cmd)==1
    res=receipt['build_resource_samples'];assert not res['other_user_seen'] and not res['unknown_project_seen']
    gates=read(ROOT/(PREFIX+'-guards-released.json'));assert gates['source_copy_complete'] and gates['status']=='RELEASED'
    integrity={'status':'PASS','source_sha':plan['source_sha'],'result_files':len(manifest['files']),
               'fixed_source_map_objects':len(manifest['source_hashes']),'whole_tree_entries':len(tree.splitlines()),
               'build_metadata_status':meta['status'],'build_tasks':max((int(y) for x,y in tasks),default=None),
               'build_duration':duration,'build_warnings':warnings,'simulation_binary_sha256':manifest['binary_sha256'],
               'new_core_compile':1,'new_core_run':1,'new_core_assertions':'-UNDEBUG and __assert_fail',
               'local_mock_invocations':1,'local_mock_methods':5,'network_runs':0,'old_cores':0,'network_raw_empty':True,
               'source_copy_complete':True,'compatibility_guards_released':True,'main_algorithm_edits_by_independent':0,
               'checkout':{'head':git('rev-parse','HEAD').decode().strip(),'status':git('status','--porcelain').decode()}}
    dump('integrity.json',integrity)
    refroot=PROJECT/'参考文献/候选'
    refs=[refroot/'README.md',refroot/'reading-log.md',refroot/'papers/diffflow-2016/analysis-technical.md',refroot/'papers/diffflow-2016/verification.md']
    dump('reference-review.json',{'scope':'Completed engineering-preflight node only','sources':{str(p):sha(p) for p in refs},
        'version':'DiffFlow arXiv1604.05107v1 archive technical and verification records','borrowing':'Separate label visibility and original identity, and measure actual activation point',
        'difference':'This node verifies source/build/new decision helper and mocked runner; it does not verify dynamic network classification, SDN control or RDMA performance',
        'not_extrapolated':['No label network profiles/default regression completed','No lifecycle/generation isolation or effects/cost established','No additional baseline or candidate admitted']})
    report=f'''# 标签夹具 r2 预检报告

日期：2026 年 11 月 1 日。固定 `{plan['source_sha']}` 的源码门、单份完整构建、新标签核心和本地 mock 均通过。网络仿真为 0，默认回归与动态标签网络覆盖仍未完成。

## 1. 来源与修订范围

冻结计划 SHA-256 为 `{receipt['plan_sha256']}`，实验 ID 为 `{plan['id']}`。G1 的五文件修订和相对 506 的完整标签差异已独立阅读并核哈希。C++ 从实际配置构造 LabelRunContext，检查位于配置解析后、随机种子和网络初始化前。C1／C2／C3 算法、500 ns、StartHash 和桶规则不变，见[源审查]({PREFIX}-source-review.json)。

## 2. 实际执行

新 ID 的 runs／results 均在本次启动前核为空，旧 r1 ID 没有被复用或据此推断不存在。缓存真实路径、个人 origin／推送引用、树与干净状态核对后，同步新 SHA；无其他用户／未知作业时部署新 worker，哈希与固定对象一致。

只运行一次 guarded optimized `-j2` 完整构建，最终任务数为 {integrity['build_tasks']:,}，日志用时为 {duration[0] if duration else '见原日志'}。未运行 run.py 或网络 run。构建后只编译／运行新增 ws31_label_test.cc，显式 `-UNDEBUG`，二进制含 `__assert_fail`，输出完整 context PASS。二进制和日志均在该 ID 结果目录，位于 source 之外。

新增 Python runner mock 只执行一次，5 个方法全部通过。远程入口在测试中被替换为 mock。日志原始字节哈希与驱动按文本解码后的哈希分别保留，见[日志完整性]({PREFIX}-local-mock-log-integrity.json)。旧核心、旧取消夹具和网络格均未重复。

## 3. 证据与资源

{len(manifest['files'])} 份结果逐文件核大小及 SHA-256；{len(manifest['source_hashes'])} 个固定源对象、模拟二进制、新核心二进制和 {len(tree.splitlines()):,} 项 Git 树均匹配。构建元数据保持 BUILT，核心与 mock 分别有独立 PASS 收据，见[完整性记录]({PREFIX}-integrity.json)。

构建每 5 秒采样，共 {res['sample_count']} 次。最高采样负载 {res['max_sampled_load_1m']:.2f}，最大编译前端数 {res['max_sampled_cc1plus_count']}，最低采样可用内存约 {res['min_sampled_available_gib']:.3f} GiB，磁盘余量约 {res['min_sampled_free_gib']:,.3f} GiB。未采到其他用户或未知项目作业；采样值不称精确峰值。全部警告保留在索引与日志。

## 4. 结论与后继

本次完成新标签源码的工程预检，主核网络证据仍需后续计划。真实 GetNxtPacket 到每跳 ROUTE 的默认 0 回归、profiles 1／2／3、重传时刻关联、完整适配器生命周期及 generation 边界均未验。独立 V0、双侧效果和成本仍必做，新组合基线未形成。

节点参考复核从候选 README／reading-log 进入，保留 DiffFlow v1 关于分类可见性与生效位置的区分；作者结果不能替代本次源和测试证据，见[复核记录]({PREFIX}-reference-review.json)。固定副本已核，全部预检命令终态，兼容约束已释放。本副停止新增执行，等待下一单目标。
'''
    (ROOT/(PREFIX+'-report.md')).write_text(report,encoding='utf-8')
    handoff=f'''# 标签夹具 r2 预检九节交接

日期：2026 年 11 月 1 日。来源副对话 `01a19323-2201-7b23-a0f1-905c71496d38`，接收主对话 `01a19322-95a5-76e3-a4f5-1f1e9dde81ce`。

## 1. 本对话目标

先独立审 G1 修订及完整标签源码；通过后只做一次完整构建、新标签核心及本地 Python mock。禁止网络、旧核心、旧取消与旧控制器恢复。

## 2. 已确认的项目事实

固定源 `{plan['source_sha']}`，parent 4605fa32，机制基底 50603927。计划 SHA-256 `{receipt['plan_sha256']}`，新 ID `{plan['id']}`。r1 在源码门停止的原证据保持，未复用或检查旧 ID 后认定其不存在。

## 3. 已完成工作

源审查及新缓存／ID／作业／资源门通过，已同步并安全部署固定 worker。单份 optimized `-j2` 全构建通过；仅新增标签核心编译一次、执行一次，断言开启；Python mock 一次、5 方法 PASS。固定源码、whole tree、日志、二进制和资源均留证，见[报告]({PREFIX}-report.md)。

## 4. 已形成的设计决策

G1 由实际 C++ 传输／输入／故障／诊断上下文校验解决，检查在随机种子与网络初始化前。默认 0 保留旧准入语义；标签 500 ns、桶 0、原业务真值及三候选算法未改。此次通过只限工程预检。

## 5. 当前状态

`COMPLETE FOR SINGLE BUILD / NEW LABEL CORE / LOCAL MOCK ONLY`。{len(manifest['files'])} 份结果、{len(manifest['source_hashes'])} 个固定对象及 {len(tree.splitlines()):,} 项树通过；网络运行数为 0，raw 为空。来源副本已建立并核对，所有命令终态，主对实现／入口／环境的兼容约束均已释放。

## 6. 未解决问题

新源默认 0 网络回归、profiles 1／2／3 的真实前后构包／标签覆盖、SwitchNode 与 RdmaClient 生命周期和异常适配器、独立 V0 及双侧效果／成本仍待完成。generation=0 不证明重建隔离，构建与核心 PASS 不代替网络验收。

## 7. 后续推荐动作

主独立核预检交付，再冻结小输入、参考 raw、观测关联与最小网络计划。生命周期夹具仍按修订契约单独冻结。本副不自动运行网络或扩展测试，等待下一目标。

## 8. 与其他工作流的关系

只写本轮前缀，远端仅按授权同步缓存、部署 workspace worker、建立新 ID 和运行新核心。未改实现源／算法或系统，未提交／推送；无 Ofan/RR 专测和 WS-29 访问。历史失败与成功证据均保留。

## 9. CONTEXT SNAPSHOT

标签预检 r2 源码门、唯一完整构建、新标签核心与本地 5 方法 mock PASS。固定 2ed7d342，ID `{plan['id']}`；网络／旧核心／旧取消重复均为 0。固定源、whole tree、命令和资源入口见[最终索引]({PREFIX}-index.json)。全部预检约束已释放，网络回归与完整科学范围继续 ACTIVE。
'''
    (ROOT/(PREFIX+'-handoff.md')).write_text(handoff,encoding='utf-8')
    docs={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in ROOT.glob(PREFIX+'*') if p.is_file() and p.name not in (PREFIX+'-index.json',PREFIX+'-qa.json')}
    support={p.name:sha(p) for p in folder.iterdir() if p.is_file()}
    dump('index.json',{'status':receipt['status'],'source_sha':plan['source_sha'],'plan_sha256':receipt['plan_sha256'],
                       'id':plan['id'],'verification':integrity,'documents':docs,'supporting_files':support,
                       'result_files':manifest['files'],'result_path':str(target),'source_map':manifest['source_hashes'],
                       'deployed_worker_sha256':receipt['deployed_worker_sha256'],'resources':res,
                       'dependencies':{n:sha(ROOT/n) for n in ['main-mode-dynamic-r1-driver.py','zero-control-pilot-r1-driver.py']},
                       'main_acceptance':'Independent preflight delivery; main review separate',
                       'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    for n,info in docs.items():assert sha(ROOT/n)==info['sha256']
    linkcount=0
    for text in (report,handoff):
        for rel in re.findall(r'\]\(([^)]+)\)',text):assert (ROOT/rel).exists();linkcount+=1
    assert len(re.findall(r'^## \d\.',handoff,re.M))==9
    dump('qa.json',{'status':'PASS','index_sha256':sha(ROOT/(PREFIX+'-index.json')),'documents_rechecked':len(docs),
                    'support_files_rechecked':len(support),'relative_links_checked':linkcount,'handoff_sections':9,
                    'scope':'Engineering preflight only; no network/adapter/effects conclusion','source_copy_and_compatibility_guard_released':True,
                    'new_execution_during_finalization':0,'style':'Original ruanyf README and6 chapters read; heading/spacing/paragraphs/numbers/punctuation/structure checked'})
    print(json.dumps({'status':'PASS','index_sha256':sha(ROOT/(PREFIX+'-index.json')),'qa_sha256':sha(ROOT/(PREFIX+'-qa.json')),'verification':integrity},ensure_ascii=False))

if __name__=='__main__':main()
