"""Local-only final build/fixture/artifact/source delivery, preserving r1."""
import datetime,hashlib,importlib.util,json,pathlib,re,subprocess,sys
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parent
PREFIX='adapter-boundary-preflight-r2'
OLD='adapter-boundary-preflight-r1'
REPO=ROOT.parents[4]/'ws31-candidates-implementation'
PROJECT=ROOT.parents[5]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()
def dump(s,v):(ROOT/(PREFIX+'-'+s)).write_text(json.dumps(v,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
def git(*a):return subprocess.check_output(['git','-C',str(REPO),*a])
def inventory(folder):return {str(p.relative_to(folder)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in folder.rglob('*') if p.is_file()}
def main():
    r=read(ROOT/(PREFIX+'-receipt.json'));plan=read(ROOT/(PREFIX+'-frozen-plan.json'))
    assert sha(ROOT/(PREFIX+'-frozen-plan.json'))==r['plan_sha256']=='e09f0883fe8839f5e77ee2797ebbf75aeb88e0fa9959b7b7ddf84b5acb328061'
    original=read(ROOT/(PREFIX+'-original-r1-integrity-before.json'))
    for rel,info in original.items():assert (ROOT/rel).stat().st_size==info['bytes'] and sha(ROOT/rel)==info['sha256']
    assert sha(ROOT/(OLD+'-index.json'))==plan['stopped_index_sha256'] and sha(ROOT/(OLD+'-qa.json'))==plan['stopped_QA_sha256']
    folder=ROOT/(PREFIX+'-evidence')/plan['id'];target=folder/'results'
    if r['status'].startswith('STOPPED_'):
        preserved=inventory(folder);dump('failure-integrity.json',{'status':r['status'],'error':r.get('error'),'files':preserved,'original_r1_files_unchanged':len(original),
            'build_commands':r['build_commands'],'fixture_commands':r['fixture_commands'],'no_network_or_core':r['network_runs_started']==r['core_commands']==0,'new_remote_actions':0})
        report=f"# 适配器 r2 停止报告\n\n固定 `{r['source_sha']}`，状态 `{r['status']}`，原因 `{r.get('error','见日志')}`。构建命令 {r['build_commands']}，夹具命令 {r['fixture_commands']}。原 r1 的 {len(original)} 份文件字节不变，所有当前结果和错误已保全。后续停止，约束未推定释放；主需独核实际失败后再安排接续。\n"
        (ROOT/(PREFIX+'-report.md')).write_text(report,encoding='utf-8')
        docs={p.name:sha(p) for p in ROOT.glob(PREFIX+'-*') if p.is_file() and p.name not in (PREFIX+'-index.json',PREFIX+'-qa.json')}
        dump('index.json',{'status':r['status'],'documents':docs,'preserved':preserved,'original_r1':original,'new_remote_actions_by_finalizer':0})
        dump('qa.json',{'status':'PASS_FAILURE_PRESERVATION_ONLY','index_sha256':sha(ROOT/(PREFIX+'-index.json')),'unexecuted_not_pass':True})
        print(json.dumps({'status':r['status'],'index_sha256':sha(ROOT/(PREFIX+'-index.json')),'qa_sha256':sha(ROOT/(PREFIX+'-qa.json'))}));return
    assert r['status']=='COMPLETE_FOR_ONE_BUILD_AND_NEW_17_ADAPTER_BOUNDARY_CASES_ONLY'
    assert r['build_commands']==1 and r['fixture_commands']==3 and r['sync_commands']==r['deploy_commands']==r['network_runs_started']==r['core_commands']==0
    assert read(ROOT/(PREFIX+'-original-r1-integrity-after.json'))==original
    m=read(folder/'remote-manifest.json');builds=read(ROOT/(PREFIX+'-all-builds-verified.json'));assert len(builds)==1
    built=builds[0];assert m['source_head']==r['source_sha'] and m['source_hashes']==built['source_hashes'] and m['binary_sha256']==built['binary_sha256']
    for rel,info in m['files'].items():assert (target/rel).stat().st_size==info['bytes'] and sha(target/rel)==info['sha256']
    for path,h in m['source_hashes'].items():assert hashlib.sha256(git('show',r['source_sha']+':'+path)).hexdigest()==h
    tree=git('ls-tree','-r',r['source_sha']);assert (ROOT/(PREFIX+'-source-git-tree.txt')).read_bytes()==tree
    meta=read(target/'metadata.json');assert meta['status']=='BUILT' and meta['git_commit']==r['source_sha'] and meta['build_mode']=='optimized' and meta['cpu_jobs']==2
    assert not any((target/'raw').rglob('*'))
    prep=read(ROOT/(PREFIX+'-artifact-preparation.json'));technical=read(target/'technical/adapter-boundary/receipt.json')
    assert technical['binaries']==prep['binaries'] and technical['libraries']==prep['libraries'] and technical['env_whitelist']==prep['env_whitelist']
    assert len(technical['binaries'])==2 and technical['libraries']
    for info in list(technical['binaries'].values())+list(technical['libraries'].values()):assert sha(target/info['artifact'])==info['sha256']
    env=technical['env_whitelist'];assert set(env)==set(plan['environment'])|{'PATH','LANG','LC_ALL','LD_LIBRARY_PATH'}
    assert all(env[k]==v for k,v in plan['environment'].items()) and env['LD_LIBRARY_PATH']=='/home/fnl/lzy/runs/'+plan['id']+'/source/build'
    assert technical['steps']==r['executions'] and [s['candidate'] for s in technical['steps']]==['C1','C2','C3']
    def instant(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
    assert instant(meta['build_finished_utc'])<=instant(technical['steps'][0]['start_utc'])
    for i,s in enumerate(technical['steps']):
        assert s['status']=='PASS' and s['exit_code']==0 and s['coverage_pass'] and s['env_whitelist']==env
        assert s['argv']==['/home/fnl/lzy/runs/'+plan['id']+'/source/'+plan['ordered_executions'][i]['relative_binary']]+plan['ordered_executions'][i]['args']
        assert s['log_sha256']==sha(target/'logs'/('adapter-'+s['candidate']+'.log'))==sha(folder/('adapter-'+s['candidate']+'.log'))
        if i:assert instant(technical['steps'][i-1]['end_utc'])<instant(s['start_utc'])
    spec=importlib.util.spec_from_file_location('adapter_delivery_raw',ROOT/(PREFIX+'-verify.py'));v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
    checked=json.loads(json.dumps(v.verify(target)))
    for name in ('C1','C2','C3'):assert checked[name]==read(ROOT/(PREFIX+'-raw-verification-'+name+'.json'))
    dump('raw-acceptance.json',checked)
    buildtext=(target/'logs/build.log').read_text(encoding='utf-8');assert "'build' finished successfully" in buildtext
    tasks=max(int(y) for x,y in re.findall(r'\[\s*(\d+)\s*/\s*(\d+)\s*\]',buildtext))
    duration=re.findall(r"'build' finished successfully \(([^)]+)\)",buildtext)
    res=r['build_resources'];assert res['max_sampled_cc1plus_count']<=2 and res['max_sampled_building_metadata_count']<=1
    assert not res['other_user_seen'] and not res['unknown_project_seen']
    for name in ('processes-initial.json','processes-before-build.json'):
        process=read(ROOT/(PREFIX+'-'+name));assert process['gate_pass'] and not process['unknown_project_pids'] and not process['other_user_pids'] and not process['compute_pids'] and not process['git_helper_pids']
    cache=read(ROOT/(PREFIX+'-cache-read-only.json'));assert cache['old_reserved_id_absent'] and cache['new_id_absent']
    assert read(ROOT/(PREFIX+'-guards-released.json'))['status']=='RELEASED'
    integrity={'status':'PASS_ONE_FULL_BUILD_AND_17_NEW_ADAPTER_CASES','source_sha':r['source_sha'],'build_tasks':tasks,'build_duration':duration,
        'fixture_cases':{'C1':5,'C2':10,'C3':2},'fixture_commands':3,'source_map_objects':len(m['source_hashes']),'source_tree_entries':len(tree.splitlines()),
        'result_files_checked':len(m['files']),'test_binaries':2,'dynamic_libraries':len(technical['libraries']),'network_raw_empty':True,
        'actual_switch_packet_calls':checked['C1']['packet_rows']+checked['C3']['packet_rows'],'C2_demand_events':10,'C2_launch_events':6,'C2_cancel_events':4,'C2_real_QPs':0,'C2_finished':0,
        'original_r1_files_unchanged':len(original),'sync':0,'deploy':0,'core':0,'network':0,'guards_released':True,
        'source_head_observed':git('rev-parse','HEAD').decode().strip(),'source_status_observed':git('status','--porcelain').decode(),
        'main_raw_acceptance':'PENDING separate main raw replay','new_remote_actions_by_finalizer':0}
    dump('integrity.json',integrity)
    refsroot=PROJECT/'参考文献/候选';refs=[refsroot/p for p in ['README.md','reading-log.md','papers/diffflow-2016/analysis-technical.md','papers/diffflow-2016/verification.md']]
    dump('reference-review.json',{'sources':{str(p):sha(p) for p in refs},'version':'DiffFlow arXiv1604.05107v1,6pages,archived technical/verification records',
        'borrowing':'Check activation order, retained identity and explicit state removal; do not infer lifecycle from rule visibility alone',
        'applicability':'Actual adapter packet/queue and timer tests distinguish lookup/retention/expiry/reset from true endpoint drain and reuse',
        'difference':'DiffFlow advertises sampled long flows before spraying. Here isolated RDMA adapter fixtures use pinned paths and transport substitution only for C2 dispatch.',
        'not_extrapolated':['No real endpoint generation/drain/reuse acceptance','No default network regression after DispatchRequest extraction','No author efficacy, classifier error rate or combined baseline claim'],'priority':'Fixed1f917source and original r2 fixture logs'})
    support={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in folder.iterdir() if p.is_file()}
    report=f'''# 适配器边界 r2 工程预检报告

日期：2026 年 11 月 1 日。固定 `{r['source_sha']}` 的一次 optimized `-j2` 完整构建及新增 17 个适配器条件全部通过：C1 五例、C2 十例、C3 两例。主从回传原日志独立验收仍待完成。网络、核心、同步和部署次数均为 0。

## 1. 原停止保全与新门

恢复计划 SHA-256 为 `{r['plan_sha256']}`，新 ID 为 `{plan['id']}`。原 r1 的 {len(original)} 份文件前后字节相同，停止交付没有回写成功。复核原静态审查、42 个固定源对象和 4,843 项完整树后，源码和 17 例判据保持。

重新读取全部进程，Git 助手及相关祖先链单列；初始和构建前均无 Git 助手、其他用户或未知项目作业。原 PID 的历史消失不作当前门依据。缓存个人 origin、分支引用、固定对象／树／clean、worker、原保留 ID 和新 ID 均核对。旧、新 ID 在恢复门均不存在。本轮没有 sync、deploy 或缓存修补；见[只读缓存门]({PREFIX}-cache-read-only.json)。

## 2. 实际构建和三个直接命令

新隔离副本完成一次全量 optimized `-j2` 构建，任务数 {tasks:,}，原日志用时 {duration[0] if duration else '见构建日志'}。随后直接执行新 `ws31-switch-boundary-test --candidate=c1`、`ws31-start-boundary-test`、`ws31-switch-boundary-test --candidate=c3`，不使用 `waf --run`。

环境由白名单重新构造：观测 2，label／transform／lifecycle／life profile／composition 均为 0，诊断与 preload 等继承项不进入进程。`LD_LIBRARY_PATH` 只包含该隔离 build。两个二进制及实际解析的 {len(technical['libraries'])} 份 ns-3 动态库均在运行前核路径／哈希并保留副本，ldd 没有缺库。完整 argv、环境、PID、时刻、退出码和 stdout／stderr 在[技术收据](adapter-boundary-preflight-r2-evidence/{plan['id']}/results/technical/adapter-boundary/receipt.json)与索引。

## 3. 原始行为验收

C1 五例共 20 次真实包调用。PPP／IPv4／UDP／SeqTs 和 INT mode 1 完整解析，实际包头为 56 B；八个 Qbb 设备连接 BEgressQueue。重复、空洞和部分重叠的唯一扣减依次为 100、100、200、400、500 B，真实选中队列填入 5,000 B 后标签和队列变化均不迁移原路径。到期前、恰好到期、迟到无重登记、容量／区间／序号跨界回退及真实清表重建均核对。Pressure 观测没有替生产入口执行漏掉的到期。

C2 的 Stop／Dispose 各五例：放行前、同刻控制先、同刻放行先、放行后和零等待。实际 demand 共 10、launch 共 6、cancel 共 4；每例 8,192 B，原需求时刻 10 ns，等待按四元组哈希重算。同刻 uid 的两个大小顺序都成立，零等待同步交付。重复控制／Dispose 不二次计数。替身只替换计时和计数之后的传输交付，真实 QP 和完成数均为 0。

C3 两例共九次真实包调用。首先达到真实类别 1 借用类别 2 所有权端口，再激活归属类别，记录一个残留包／156 B。后续改标签及缺失标签保持首次类别和端口。20,199／20,200／20,201 ns 只读快照分别对应活动双真、类别 2 到期、两类到期，保留固定条目和惰性租约；20,202 ns 真调用执行到期并续期。真实 reset 清借用账，未知首次策略保持至显式清理后重新准入。全部逐包、空闲、清表记录见[原始重放结果]({PREFIX}-raw-acceptance.json)。

## 4. 完整性与资源

{len(m['files'])} 份远程结果逐文件核大小和 SHA-256；42 个固定源对象及 {len(tree.splitlines()):,} 项完整树匹配，两个测试二进制、{len(technical['libraries'])} 个动态库、构建／夹具日志及完整 receipt 均由 manifest 保全。元数据保持 BUILT，网络 raw 为空。原 r1 保全文件前后相同，见[索引]({PREFIX}-index.json)及[完整性记录]({PREFIX}-integrity.json)。

构建每 5 秒采样，共 {res['sample_count']} 次；最大采样编译前端 {res['max_sampled_cc1plus_count']}，最高负载 {res['max_sampled_load_1m']:.2f}，最低可用内存约 {res['min_sampled_available_gib']:.3f} GiB，磁盘约 {res['min_sampled_free_gib']:,.3f} GiB。未采到其他用户或未知项目作业。夹具前后另有资源快照和各直接子进程的 rusage；采样界值不称精确系统峰值。当前没有可用模型切换接口，未执行或声称模型切换。

## 5. 结论与承接

本次完成新增适配器工程预检，源码副本与三个调用均终态，r1 延续的源码／入口／环境约束已明确释放，见[释放收据]({PREFIX}-guards-released.json)。本副停止新增执行，等待主独核与下一单目标。

工程通过不代表真实端点退出、旧包排空、跨代 generation／drain／reuse 或默认网络兼容。DispatchRequest 提取后的必要网络回归、真实端点生命周期、独立 C1 V0 及三个候选双侧业务效果／状态／运行成本仍由总计划承接。新组合基线尚未形成。

从候选 README／reading-log 复核 DiffFlow v1 技术和核验记录，保留生效顺序、缓存身份与显式状态移除的区分；其抽样广告、喷洒和平均 FCT 不能代替本轮真实适配器或端点证据，见[参考复核]({PREFIX}-reference-review.json)。
'''
    (ROOT/(PREFIX+'-report.md')).write_text(report,encoding='utf-8')
    parts=[('本对话目标','保全 r1 停止，使用新 r2 ID 重新执行完整进程／缓存／资源门，一次全构建及新增 C1 五／C2 十／C3 二例。同步、部署与网络授权为 0。'),
        ('已确认的项目事实',f"固定 `{r['source_sha']}`，恢复计划 SHA-256 `{r['plan_sha256']}`，新 ID `{plan['id']}`。原静态源码审查与 42 对象／4,843 树项匹配，生产差异和判据未改。"),
        ('已完成工作',f"新门通过，一次完整构建 {tasks:,} 项通过；三个直接命令及 17 例 PASS。真实包调用共 29 次，C2 十需求／六交付／四取消，QP／完成 0。原 r1 的 {len(original)} 份文件不变，详见[报告]({PREFIX}-report.md)。"),
        ('已形成的设计决策','当前进程门而非历史 PID 消失决定准入；不忽略 Git 助手，不修补缓存。真实适配器和队列／包头保持，C2 只替换计时计数之后的传输交付。活动、到期、惰性清理与显式重建分别验收。'),
        ('当前状态',f"`COMPLETE FOR ONE BUILD AND 17 NEW ADAPTER CONDITIONS`。{len(m['files'])} 结果、42 固定对象、4,843 树项、两个测试二进制与 {len(technical['libraries'])} 库已核。源码／入口／环境约束明确释放，主原日志独验待完成。"),
        ('未解决问题','新源必要默认网络回归，真实端点退出／排空／generation／drain／reuse，独立 C1 V0 及双侧业务效果和状态／运行成本仍待完成。17 例不能替代端点与效果证据。'),
        ('后续推荐动作','主先独立重放原日志并核最终来源，通过后再冻结必要默认回归或端点单目标。本副不自动启动网络或更多测试。'),
        ('与其他工作流的关系','只写 r2 前缀及新证据目录；r1 原停止、科学源码、worker、controller、环境和权威状态未改。sync／deploy／core／network 为 0，Ofan/RR、WS-29 和旧矩阵未执行。'),
        ('CONTEXT SNAPSHOT',f"适配器 r2 固定 1f917f44，实时全门通过，一次 optimized-j2 全构建＋C1五／C2十／C3二 17例全部 PASS。29 次包调用，C2 六交付／四取消，真实 QP／完成 0。原 r1 的 {len(original)} 文件不变，两个二进制／{len(technical['libraries'])} 动态库及完整日志留证，全部约束释放。主独验、网络回归与完整端点／V0／效果成本继续承接；见[索引]({PREFIX}-index.json)。")]
    handoff='# 适配器预检恢复九节交接\n\n日期：2026 年 11 月 1 日。来源副对话 `01a19323-2201-7b23-a0f1-905c71496d38`，接收主对话 `01a19322-95a5-76e3-a4f5-1f1e9dde81ce`。\n'
    for i,(title,body) in enumerate(parts,1):handoff+=f'\n## {i}. {title}\n\n{body}\n'
    (ROOT/(PREFIX+'-handoff.md')).write_text(handoff,encoding='utf-8')
    docs={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in ROOT.glob(PREFIX+'-*') if p.is_file() and p.name not in (PREFIX+'-index.json',PREFIX+'-qa.json')}
    deps=['main-mode-dynamic-r1-driver.py','zero-control-pilot-r1-driver.py',OLD+'-driver.py',OLD+'-verify.py']
    dump('index.json',{'status':r['status'],'source_sha':r['source_sha'],'plan_sha256':r['plan_sha256'],'verification':integrity,'documents':docs,
        'support_files':support,'results_path':str(target),'result_files':m['files'],'source_hashes':m['source_hashes'],'binary_library_artifacts':technical,
        'original_r1_files':original,'dependencies':{p:sha(ROOT/p) for p in deps},'resources':res,'main_raw_acceptance':'PENDING_SEPARATE_MAIN_REPLAY',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    for p,info in docs.items():assert sha(ROOT/p)==info['sha256']
    links=[]
    for text in (report,handoff):
        for rel in re.findall(r'\]\(([^)]+)\)',text):assert (ROOT/rel).exists();links.append(rel)
    assert len(re.findall(r'^## \d\.',handoff,re.M))==9
    dump('qa.json',{'status':'PASS_17_ADAPTER_EXECUTOR_DELIVERY','index_sha256':sha(ROOT/(PREFIX+'-index.json')),'documents_rechecked':len(docs),
        'support_files_hashed':len(support),'result_files_verified':len(m['files']),'links_checked':len(links),'handoff_sections':9,
        'original_r1_files_preserved':len(original),'new_remote_actions_by_finalizer':0,'new_fixture_repeats_by_finalizer':0,'guards_released':True,
        'main_review_required':True,'style':'Original ruanyf README and six chapters previously read; headings, spacing, paragraphs, values, punctuation and structure reviewed'})
    assert read(ROOT/(PREFIX+'-index.json'))==json.loads((ROOT/(PREFIX+'-index.json')).read_bytes())
    print(json.dumps({'status':'PASS','index_sha256':sha(ROOT/(PREFIX+'-index.json')),'qa_sha256':sha(ROOT/(PREFIX+'-qa.json')),'verification':integrity},ensure_ascii=True))
if __name__=='__main__':main()
