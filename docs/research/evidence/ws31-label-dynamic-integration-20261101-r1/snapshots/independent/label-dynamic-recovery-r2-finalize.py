"""Local delivery joining immutable first-eight raw and the two recovered runs."""
import datetime,hashlib,importlib.util,json,pathlib,re,subprocess,sys
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parent
PREFIX='label-dynamic-recovery-r2'
OLD='label-dynamic-validation-r1'
EV=ROOT/(PREFIX+'-evidence')
SOURCE=ROOT.parents[4]/'ws31-candidates-implementation'
PROJECT=ROOT.parents[5]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()
def dump(suffix,v):(ROOT/(PREFIX+'-'+suffix)).write_text(json.dumps(v,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
def git(*a):return subprocess.check_output(['git','-C',str(SOURCE),*a])
def checker():
    spec=importlib.util.spec_from_file_location('recovery_delivery_checker',ROOT/(PREFIX+'-checker.py'))
    q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q);return q
def main():
    r=read(ROOT/(PREFIX+'-receipt.json'));plan=read(ROOT/(PREFIX+'-frozen-plan.json'));oldplan=read(ROOT/(OLD+'-frozen-plan.json'))
    assert r['status']=='COMPLETE_FOR_ORIGINAL_TEN_DYNAMIC_LABEL_CELLS_WITH_EIGHT_OFFLINE_PLUS_TWO_NEW_RUNS'
    assert r['network_runs_started']==2 and all(c['status']=='PASS' for c in r['cells']) and 'error' not in r
    for k in ('core_tests_executed','build_commands','sync_commands','deploy_commands','prior_eight_simulation_repeats'):assert r[k]==0
    assert sha(ROOT/(PREFIX+'-frozen-plan.json'))==r['plan_sha256']=='d1dce31271e4756e4c90084bc01006e9c4a670de830d24414260a71faacd9599'
    assert sha(ROOT/(OLD+'-frozen-plan.json'))==plan['original_plan_sha256']
    before=read(ROOT/(PREFIX+'-original-r1-integrity-before.json'));after=read(ROOT/(PREFIX+'-original-r1-integrity-after.json'))
    assert before==after
    for p,info in before.items():assert (ROOT/p).stat().st_size==info['bytes'] and sha(ROOT/p)==info['sha256']
    assert sha(ROOT/(OLD+'-index.json'))=='f0df25a481b353aac8c5d2ca2f5972da43b3d5d203a87d71e25468508601ad25'
    assert sha(ROOT/(OLD+'-qa.json'))=='6a1d280dcb0804365e6565b7afd90d8a90df50276f4f7e681bc8b0c715cee922'
    preparation=read(ROOT/(PREFIX+'-offline-eight-acceptance.json'))
    assert sha(ROOT/(PREFIX+'-checker.py'))==preparation['corrected_checker_sha256']=='6ce22a20fe87e8ce6e90c9ef4e7d3da7a97cc4eeaf742d1201bcc13da2b5ba7c'
    assert sha(ROOT/(OLD+'-checker.py'))==preparation['original_checker_sha256']
    assert sha(ROOT/(PREFIX+'-checker.patch'))==preparation['correction_diff_sha256']
    assert len(read(ROOT/(PREFIX+'-offline-negative-examples.json'))['examples'])==3
    main8=ROOT.parent/'main/evidence/label-dynamic-first8-main-acceptance-r1.json'
    assert read(main8)['accepted_cells']==8 and read(main8)['completed_records']==120
    builds=read(ROOT/(OLD+'-all-builds-verified.json'));source_map=builds[0]['source_hashes'];assert len(builds)==10 and len(source_map)==40
    for path,h in source_map.items():assert hashlib.sha256(git('show',r['source_sha']+':'+path)).hexdigest()==h
    tree=git('ls-tree','-r',r['source_sha']);assert (ROOT/(OLD+'-source-git-tree.txt')).read_bytes()==tree
    gate=read(ROOT/(PREFIX+'-pending-built-source-cache-gate.json'))
    assert [c['id'] for c in gate['pending']]==plan['only_pending_ids']
    assert all(c['never_started_raw_empty'] and c['source_clean'] and c['metadata']['status']=='BUILT' and c['source_hashes']==source_map for c in gate['pending'])
    Q=checker();ref=read(ROOT/(OLD+'-new-q12-reference.json'));cells=[];nresults=0;nsupport=0;decision_schema={}
    for i,c in enumerate(oldplan['cells']):
        original=i<8;folder=(ROOT/(OLD+'-evidence') if original else EV)/c['id'];target=folder/'results'
        m=read(folder/'remote-manifest.json');built=builds[i]
        assert m['source_head']==r['source_sha'] and m['source_hashes']==built['source_hashes']==source_map
        assert m['binary_sha256']==built['binary_sha256']
        for rel,info in m['files'].items():
            f=target/rel;assert f.stat().st_size==info['bytes'] and sha(f)==info['sha256'];nresults+=1
        # Receipts serialize tuples as lists and integer object keys as strings.
        a=json.loads(json.dumps(Q.verify(c,target,ref if c['ws31_label_profile'] else None)));assert a['status']=='PASS'
        accepted=read(EV/c['id']/('offline-acceptance.json' if original else 'acceptance.json'));assert a==accepted
        log=next((target/'raw').glob('*/config.log'));rows=Q.records(log)
        assert all(prefix in {'WS31_LABEL_PACKET','WS31_LABEL_ROUTE','WS31_LABEL_DEMAND'} for prefix,v,line in rows if prefix.startswith('WS31_LABEL_'))
        if c['lb'] in ('ws31-c1','ws31-c3'):
            states=a['mechanism']['states'];switches=set(map(int,(target/'config/topology.txt').read_text(encoding='ascii').splitlines()[1].split()))
            assert len(states)==len(switches) and {s['switch'] for s in states}==switches and sum(s['fresh'] for s in states)==15
        if c['lb']=='ws31-c3':
            generic=a['ordered']['counts']['choice'];fresh=sum(v['fresh'] for prefix,v,line in rows if prefix=='WS31_C3_ROUTE')
            assert generic==30 and fresh==15 and a['path']['switch_qps']==45
            decision_schema[c['id']]={'generic_choices':generic,'specialized_fresh':fresh,'total_switch_qps':45,'q12_generic_choices':45}
        text=(target/'logs/build.log').read_text(encoding='utf-8');assert "'build' finished successfully" in text
        assert max(int(y) for x,y in re.findall(r'\[\s*(\d+)\s*/\s*(\d+)\s*\]',text))==1464
        support={p.name:sha(p) for p in folder.iterdir() if p.is_file()};nsupport+=len(support)
        cells.append({'id':c['id'],'status':'PASS_ORIGINAL_FROZEN_DYNAMIC_CONTRACT','source':'ORIGINAL_RAW_OFFLINE' if original else 'RECOVERY_RUN_ONCE',
            'lb':c['lb'],'profile':c['ws31_label_profile'],'results_path':str(target),'raw_exists':True,
            'flows':a['identity']['flows'],'payload_bytes':a['identity']['payload_bytes'],'fct_sha256':a['identity']['fct_sha256'],'log_sha256':sha(log),
            'packet_constructions':a['packet_constructions'],'route_rows':a['accepted_route_rows'],'label_route_rows':a['label_route_rows'],
            'early_late_requests':sum(v['early_count']>0 and v['late_count']>0 for v in a['coverage']),
            'coverage':a['coverage'],'mechanism':a['mechanism'],'first_policy':a['first_policy_per_original_request'],
            'ordered':a['ordered'],'queue':a['queue'],'path':a['path'],'paired_new_q12':a['new_q12_regression'],
            'result_files':m['files'],'source_hashes':m['source_hashes'],'binary_sha256':m['binary_sha256'],'supporting_files':support,
            'acceptance_path':str(EV/c['id']/('offline-acceptance.json' if original else 'acceptance.json')),
            'acceptance_sha256':sha(EV/c['id']/('offline-acceptance.json' if original else 'acceptance.json'))})
    assert len(r['commands'])==2 and all(c['operation']=='guarded-run' and c['exit_code']==0 for c in r['commands'])
    assert [c['cell'] for c in r['commands']]==plan['only_pending_ids']
    assert read(ROOT/(PREFIX+'-calls-established.json'))['all_original_ten_calls_started']
    released=read(ROOT/(PREFIX+'-guards-released.json'));assert released['status']=='RELEASED' and released['recovery_calls_terminal']==2
    integrity={'status':'PASS_ORIGINAL_TEN_TECHNICAL_CELLS','source_sha':r['source_sha'],'cells':10,'failures':0,
        'completed_records':sum(c['flows'] for c in cells),'completed_payload_bytes':sum(c['payload_bytes'] for c in cells),
        'packet_constructions':sum(c['packet_constructions'] for c in cells),'route_rows':sum(c['route_rows'] for c in cells),
        'label_route_rows':sum(c['label_route_rows'] for c in cells),
        'required_actual_early_late_requests':sum(c['early_late_requests'] for c in cells if c['profile'] in (1,2)),
        'result_files_checked':nresults,'original_and_recovery_support_files_hashed':nsupport,'original_r1_files_unchanged':len(before),
        'fixed_git_objects':40,'source_map_entries':400,'source_tree_entries':len(tree.splitlines()),
        'new_network_runs':2,'prior_simulation_repeats':0,'new_builds':0,'cores':0,'sync':0,'deploy':0,
        'guards_released':True,'main_accepted_prior_raw':8,'new_two_main_acceptance':'PENDING separate main replay',
        'historical_raw_flag_clarified':'Original C3p1 index marker preserved; actual raw_exists true, hashes and full corrected contract checked',
        'source_head_observed':git('rev-parse','HEAD').decode().strip(),'source_status_observed':git('status','--porcelain').decode(),
        'generation':0,'new_remote_actions_by_finalizer':0}
    assert integrity['completed_records']==150 and integrity['completed_payload_bytes']==2457600
    assert integrity['required_actual_early_late_requests']==90 and integrity['packet_constructions']==2295 and integrity['route_rows']==7650
    dump('integrity.json',integrity);dump('decision-schema.json',decision_schema)
    dump('phase-order.json',{'status':'PASS','original_all_ten_builds':str(ROOT/(OLD+'-all-builds-verified.json')),
        'offline_eight_complete_before_two_run_gate':True,'only_two_new_guarded_calls':r['commands'],'no_build_or_old_run_commands':True,
        'all_guards_released_after_terminal':released})
    candidate=PROJECT/'参考文献/候选'
    refs=[candidate/p for p in ('README.md','reading-log.md','papers/diffflow-2016/analysis-technical.md','papers/diffflow-2016/verification.md')]
    dump('reference-review.json',{'version':'DiffFlow arXiv1604.05107v1,6pages; PDF SHA256f552fcb75a0cec582286db0032c81660ff161fe475609ae5e79ad7075a0ae164',
        'sources':{str(p):sha(p) for p in refs},'borrowing':'Separate original business identity, actual visibility time and policy activation; compare equivalent decisions across different observation schemas',
        'applicability':'Delayed/changed packet labels are checked at construction and all hops, while C1/C3 cache the first strategy and C2 samples demand once',
        'difference':'DiffFlow samples and advertises long flows before spraying; these fixtures synthesize label signals on pinned RDMA QPs and do not reproduce SDN control or author transport results',
        'not_extrapolated':['No classifier error-rate estimate from2/15fixed wrong cases','Generation0 does not establish rebuild/lifecycle isolation','No independentV0, two-sided efficacy, runtime cost or new combined baseline'],
        'evidence_priority':'Fixed1ec5source and original10raw experiment IDs'})
    resources=[c['resource_samples'] for c in r['cells']]
    minmem=min(s['min_sampled_available_gib'] for s in resources);maxload=max(s['max_sampled_load_1m'] for s in resources)
    newrows=[]
    for c in cells[8:]:
        state=c['mechanism']['states'];tot={k:sum(s[k] for s in state) for k in ('fresh','restricted','borrowed','residual_packets','residual_wire_bytes')}
        newrows.append('| '+str(c['profile'])+' | '+' | '.join(format(tot[k],',') for k in tot)+' | PASS |')
    report=f'''# 动态标签恢复与十格合并验收报告

日期：2026 年 11 月 1 日。原冻结十格在本副的完整技术验收为 10/10 PASS，共 150 条完成记录、2,457,600 B。本次仅运行原来 BUILT、从未启动的 C3 p2／p3 两格，各运行一次；前八格只做离线重验。主对话已独验前八格，新增两格待主独验。

## 1. 检查器修正与旧证据保全

恢复计划 SHA-256 为 `{r['plan_sha256']}`，固定源码 `{r['source_sha']}`、原输入、500 ns、模板和配额均保持。原停止由本副给 C3 加入通用 CHOICE 总数及 combined hash 等价要求引起。原 checker、driver、finalizer、stop index、QA、日志和 raw 共 {len(before)} 份文件逐字节保持，旧停止交付没有回写。

新文件检查器 SHA-256 为 `{preparation['corrected_checker_sha256']}`，见[修订差异]({PREFIX}-checker.patch)。C3 p1 按原合同比较完整 FCT、仅去 uid／tag 的有序 ROUTE 及 15 条首次源投影；30 条通用 CHOICE＋15 条专属首次准入与 Q12 的 45 条通用 CHOICE 分开验收。总 switch QP 均为 45，不因日志分类不同丢弃决策。C2 的完整 CHOICE、ROUTE 及 combined 比较保持。

八份旧 raw 用新检查器离线通过；改坏 ROUTE 哈希、首次源投影及 C2 完整 combined 哈希的三个内存副本均被拒绝，见[负例检查]({PREFIX}-offline-negative-examples.json)。历史 C3 p1 的 raw_preserved 标记保留，新记录明确实际 raw 存在，完整身份／UID／时钟／存在性／状态已验。

## 2. 两个未运行格的实际恢复

新本地旧进程、个人 fork、cache origin／引用／树／clean、worker、作业与资源门通过。两个远程元数据与原 BUILT 快照的对象和原始哈希完全一致，raw 为空且没有 worker／simulation 日志。40 项固定源码、输入和二进制与原十构建证明一致后，仅按 p2→p3 串行 guarded run；见[启动前门]({PREFIX}-pending-built-source-cache-gate.json)。未构建、同步、部署、执行核心或重跑前八格，结果写入新的恢复目录。

| Profile | 首次准入 | 限制 | 借用 | 残留包 | 残留 B | 结果 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
{chr(10).join(newrows)}

p2 的 15 请求均有真实阈值前后构包，首次类别保持原标签；后期互换没有迁移已有策略或路径。p3 的错误源仍恰为 1／7，其他已知类别每类各五个正确，未知 0／7／99 保持。两个已知策略类别和限制准入均覆盖。所有活动、借用和残留计数按实际逐包状态重放，零值保留。

## 3. 合并十格的实际行为

九个标签格共 2,295 次构包，逐 UID 对应 6,885 条标签路由；含新 Q12 的十格合计 7,650 条 ROUTE。六个 profiles 1／2 格的 90 个请求实例均有首次 elapsed＜500 ns 和后续 elapsed≥500 ns 的真实构包。缺失 0 与显式 0 分开检查，原业务真值、需求起点及字节保持。

C1 按首次真实包值选择模板，完整重放两候选、饱和 Q＋R、区间扣减、访问时到期和保留预测项；后变标签没有重新登记。C2 在原需求时刻采样一次，p1 全立即，p2 六次总计 1,588 ns／最大 413 ns，p3 六次总计 1,457 ns／最大 409 ns。FCT 包含原等待。C3 缓存首次类别，按 20,000 ns 活动窗口重放新准入、所有权、借用与残留，已有 QP 固定路径。

C2／C3 p1 的完整 FCT 与本轮 Q12 一致；ROUTE 仅去 uid／tag 后一致，C3 的 15 条首次源投影一致，C2 额外保持完整通用选择事件比较。原身份、完成和队列账守恒，丢弃、拒收、账本违规和 QP 内换路为 0。

## 4. 完整性与资源

最终十格共 {nresults} 份结果、{nsupport} 份原始及恢复支持文件逐项哈希；400 项来源映射、40 个唯一 Git 对象及 {len(tree.splitlines()):,} 项完整树匹配。原 r1 的 {len(before)} 份文件前后不变；完整入口见[索引]({PREFIX}-index.json)及[完整性记录]({PREFIX}-integrity.json)。新两格的回传 manifest、输入、配置、binary 和 raw 分别核对，未覆盖旧 BUILT／stop 快照。

主验反馈后，确认初稿 JSON 的实际 UTF-8 字节与转义有效，但本机默认 CP936 解码会把中文字节后的反斜杠读入双字节字符，导致 JSON 解析失败。恢复 JSON 现采用 ASCII 转义序列化，原 UTF-8 索引、QA 和 receipt 以 `.bin` 保留供追溯；按字节、显式 UTF-8 和默认编码三种读取均核对。记录见[编码诊断]({PREFIX}-json-encoding-diagnostic.json)。原 r1 不变。

新增仿真每 2 秒采样且串行，最高采样负载 {maxload:.2f}，最低可用内存约 {minmem:.3f} GiB；无其他用户或未知作业。原十构建的资源收据保持，新增构建数为 0。以上为采样值。实际模型未切换，未声称切换。

## 5. 节点结论与承接

本副已完成原十格小输入合成标签正确性目标，generation 为 0。全部十源码副本保持，两次新调用终态核验后入口／环境约束已明确释放，见[释放收据]({PREFIX}-guards-released.json)。主对话继续独立验收新增两格及最终交付；本报告不代替主验。

已从候选 README／reading-log 复核 DiffFlow v1 技术与核验记录，保留分类可见性、生效位置与原业务真值的区分，见[参考复核]({PREFIX}-reference-review.json)。本次不估计真实分类错误率，不证明适配器完整生命周期或同四元组重建隔离。SwitchNode／RdmaClient 异常、cleanup／generation／drain、同刻事件、独立 C1 V0、三候选双侧业务效果与状态／运行成本继续由总计划承接；新组合基线尚未形成。本副停止新增执行，等待下一单目标。
'''
    (ROOT/(PREFIX+'-report.md')).write_text(report,encoding='utf-8')
    handoff=f'''# 动态标签恢复九节交接

日期：2026 年 11 月 1 日。来源副对话 `01a19323-2201-7b23-a0f1-905c71496d38`，接收主对话 `01a19322-95a5-76e3-a4f5-1f1e9dde81ce`。

## 1. 本对话目标

保全 r1，按原冻结判据用新检查器离线重验八份既有 raw，再仅恢复 C3 p2／p3 两个原 BUILT、从未启动的 ID。不得构建、重跑或修改源码／阈值。

## 2. 已确认的项目事实

固定源 `{r['source_sha']}`，恢复计划 SHA-256 `{r['plan_sha256']}`。主已验前八格、120 条完成、1,966,080 B。原停止 index 与 QA、所有原日志和 raw 保持；两个待运行 ID 的元数据、输入、40 项源和二进制在恢复门与原快照一致。

## 3. 已完成工作

新 checker 离线八格和三个拒绝负例通过；仅串行运行两个原 ID 各一次并 PASS。合并十格在本副为 10/10 PASS、150 条完成、2,457,600 B。逐 UID／时钟／存在性／首次策略和全部状态重放通过，见[报告]({PREFIX}-report.md)。

## 4. 已形成的设计决策

C3 的 30 通用选择＋15 专属源首次决策分别计数，按原合同比较 FCT／ROUTE／首次源投影；C2 完整通用事件比较保持。原停止归属额外检查器约束，旧交付仍保留。原 C3 p1 raw 标记不回写，新记录用真实文件及完整验证澄清。

## 5. 当前状态

`COMPLETE FOR ORIGINAL TEN SMALL DYNAMIC-LABEL TECHNICAL CELLS`。{nresults} 结果、{nsupport} 原始及恢复支持、400 来源映射／40 唯一对象／{len(tree.splitlines()):,} 项树通过；原 r1 共 {len(before)} 份文件字节不变。新两个命令终态，入口／环境约束已释放。主已验原八格，新增两格与最终交付待主独验。

## 6. 未解决问题

本目标的主独验新增两格仍待收束。适配器完整生命周期及异常、同四元组重建、cleanup／generation／drain 与同刻事件、独立 C1 V0、双侧业务效果和状态／运行成本仍必做；generation 0 和合成错误分桶不构成真实分类质量、效果或新基线。

## 7. 后续推荐动作

主对话独立核新两格 raw、最终索引及原证据不变性，通过后再冻结下一单目标。本副不自动启动生命周期或效果验证。证据入口为[索引]({PREFIX}-index.json)。

## 8. 与其他工作流的关系

只写 `label-dynamic-recovery-r2*` 及恢复证据目录；r1 文件、科学源码、worker、controller、环境和权威状态未改，未提交／推送。没有新 build／sync／deploy／core，没有前八格重跑、Ofan/RR 或 WS-29 访问。主总计划承接其余科学验证。

## 9. CONTEXT SNAPSHOT

固定 1ec5eedc，原八 raw 离线重验＋原 C3 p2／p3 各运行一次，完整十格本副 10/10 PASS。150 条完成、2,457,600 B，90 个必需请求实例具真实早晚构包；C3 p2 限制 6、借用 1、残留 16 包／16,152 B，p3 限制 11、借用与残留 0。原 268 文件不变，全部入口／环境约束已释放。新增两格主独验及生命周期／V0／双侧效果成本继续承接，见[索引]({PREFIX}-index.json)。
'''
    (ROOT/(PREFIX+'-handoff.md')).write_text(handoff,encoding='utf-8')
    dependencies=['label-default-validation-r1-driver.py','c2-label-validation-r1-attempt2-driver.py','main-mode-dynamic-r1-driver.py','zero-control-pilot-r1-driver.py',OLD+'-replays.py',OLD+'-identity.py']
    docs={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in ROOT.glob(PREFIX+'-*') if p.is_file() and p.name not in (PREFIX+'-index.json',PREFIX+'-qa.json')}
    dump('index.json',{'status':r['status'],'source_sha':r['source_sha'],'plan_sha256':r['plan_sha256'],'verification':integrity,'cells':cells,'documents':docs,
        'dependencies':{p:sha(ROOT/p) for p in dependencies},'original_r1_files':before,'original_stop_index':{'path':str(ROOT/(OLD+'-index.json')),'sha256':sha(ROOT/(OLD+'-index.json'))},
        'original_stop_qa':{'path':str(ROOT/(OLD+'-qa.json')),'sha256':sha(ROOT/(OLD+'-qa.json'))},
        'original_source_tree':{'path':str(ROOT/(OLD+'-source-git-tree.txt')),'sha256':sha(ROOT/(OLD+'-source-git-tree.txt'))},
        'main_first8_acceptance':{'path':str(main8),'sha256':sha(main8)},'new_two_main_acceptance':'PENDING_SEPARATE_MAIN_REPLAY',
        'new_run_resources':resources,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    for p,info in docs.items():assert sha(ROOT/p)==info['sha256']
    links=[]
    for text in (report,handoff):
        for rel in re.findall(r'\]\(([^)]+)\)',text):assert (ROOT/rel).exists();links.append(rel)
    assert len(re.findall(r'^## \d\.',handoff,re.M))==9
    dump('qa.json',{'status':'PASS_FOR_TEN_CELL_EXECUTOR_DELIVERY','index_sha256':sha(ROOT/(PREFIX+'-index.json')),
        'documents_rechecked':len(docs),'links_checked':len(links),'handoff_sections':9,'original_r1_files_preserved':len(before),
        'cells_fully_rechecked':10,'negative_examples_rejected':3,'original_build_and_stop_snapshots_unchanged':True,
        'new_simulations':2,'old_simulations_repeated':0,'new_builds_or_core_or_sync_or_deploy':0,'new_remote_actions_by_finalizer':0,
        'guards_released':True,'main_new_two_review_required':True,'json_encoding':'ASCII JSON valid under UTF8 and Windows default CP936',
        'style':'Original ruanyf README and six chapters read earlier in this conversation; headings, spacing, paragraphs, values, punctuation and structure reviewed'})
    parsed=0
    for p in ROOT.glob(PREFIX+'-*.json'):
        data=p.read_bytes();assert data.isascii(),p.name
        assert json.loads(data)==json.loads(p.read_text(encoding='utf-8'))==json.loads(p.read_text()),p.name
        parsed+=1
    print(json.dumps({'status':'PASS','index_sha256':sha(ROOT/(PREFIX+'-index.json')),'qa_sha256':sha(ROOT/(PREFIX+'-qa.json')),'verification':integrity},ensure_ascii=False))
if __name__=='__main__':main()
