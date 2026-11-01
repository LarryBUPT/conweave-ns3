"""Preserve the stopped pre-build gate and source review; no execution retry."""
import hashlib,json,pathlib,re,subprocess,datetime
ROOT=pathlib.Path(__file__).resolve().parent
PREFIX='adapter-boundary-preflight-r1'
REPO=ROOT.parents[4]/'ws31-candidates-implementation'
PROJECT=ROOT.parents[5]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(REPO),*a])
def dump(s,v):(ROOT/(PREFIX+'-'+s)).write_text(json.dumps(v,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
def main():
    r=read(ROOT/(PREFIX+'-receipt.json'));plan=read(ROOT/(PREFIX+'-frozen-plan.json'));review=read(ROOT/(PREFIX+'-source-review.json'))
    assert r['status']=='STOPPED_ADAPTER_PREFLIGHT_ON_FAILURE' and r['build_commands']==r['fixture_commands']==r['network_runs_started']==r['core_commands']==r['deploy_commands']==0
    assert review['no_material_source_issue_found'] and sha(ROOT/(PREFIX+'-frozen-plan.json'))==r['plan_sha256']=='28fc60860857cb6fe3029c72d62b1a50b0d0e053d9d2927d7655e57afb483926'
    gate=read(ROOT/(PREFIX+'-evidence')/plan['id']/'resources-before-build.json');assert not gate['gate_pass'] and gate['unknown_project_jobs']==[{'comm':'git-remote-http','cwd':'/home/fnl/lzy/code/conweave-ns3','pid':297502}]
    diag=read(ROOT/(PREFIX+'-process-diagnosis.json'));assert not diag['exists'] and diag['remote_mutations']==diag['process_signals_sent']==0
    cached=read(ROOT/(PREFIX+'-cache-after-sync.json'));assert cached['new_id_absent'] and cached['branch_ref']==r['source_sha'] and not cached['clean']
    assert all(c['exit_code']==0 for c in r['commands']) and len(r['commands'])==1 and r['commands'][0]['operation']=='guarded-sync'
    paths=git('diff','--name-only','21faeb2d986b0a4d9d59edd9bf11a0d0de934007',r['source_sha']).decode().splitlines()
    paths+=['src/point-to-point/model/ws30-observer.h','config/leaf_spine_128_100G_OS2.txt','config/ws31_correctness_r1.txt','scripts/verify_ws31_fct.py']
    objects={p:hashlib.sha256(git('show',r['source_sha']+':'+p)).hexdigest() for p in sorted(set(paths))}
    tree=git('ls-tree','-r',r['source_sha']);assert (ROOT/(PREFIX+'-source-git-tree.txt')).read_bytes()==tree and len(tree.splitlines())==4843
    candidate=PROJECT/'参考文献/候选';refs=[candidate/p for p in ['README.md','reading-log.md','papers/diffflow-2016/analysis-technical.md','papers/diffflow-2016/verification.md']]
    dump('reference-review.json',{'sources':{str(p):sha(p) for p in refs},'version':'DiffFlow arXiv1604.05107v1,6pages; archived fixed technical/verification records',
        'borrowing':'Make activation order and state removal explicit; rule installation claims do not establish cleanup or old-packet drain',
        'applicability':'Source review distinguishes production timer/accounting and real switch adapter boundaries from transport substitution',
        'difference':'This preflight inspects real ns3 packet/queue calls and event ordering; no SDN advertisement or spraying implemented',
        'not_extrapolated':['No fixture execution result exists in this attempt','No endpoint cleanup/drain/generation proof','No performance or author result transferred'],'priority':'Fixed1f917source and actual local/remote gate receipts'})
    folder=ROOT/(PREFIX+'-evidence')/plan['id'];support={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in folder.iterdir() if p.is_file()}
    integrity={'status':'STOPPED_BEFORE_FIRST_BUILD_RESOURCE_GATE','source_static_review':'PASS','fixed_source_sha':r['source_sha'],
        'local_fixed_git_objects':len(objects),'source_tree_entries':4843,'guarded_sync_commands':1,'builds':0,'fixtures':0,'network':0,'cores':0,'deploy':0,
        'sampled_available_gib':gate['available_gib'],'sampled_load_1m':gate['loadavg'][0],'sampled_free_gib':gate['free_gib'],
        'unknown_pid_at_gate':297502,'unknown_name_at_gate':'git-remote-http','target_absent_at_diagnosis_utc':diag['recorded_utc'],
        'process_ownership':'No ancestry available once PID disappeared; do not attribute to another user or definitively to the sync',
        'new_remote_id_absent_at_last_cache_gate':True,'remote_source_copy_established':False,'fixture_binary_or_library_artifacts':0,
        'source_entry_env_guard':'NOT RELEASED; required build/fixture actions unexecuted; main review/resume needed',
        'source_head_observed':git('rev-parse','HEAD').decode().strip(),'source_status_observed':git('status','--porcelain').decode(),
        'new_remote_actions_by_finalizer':0}
    dump('integrity.json',integrity)
    report=f'''# 适配器边界预检源审查与门控停止报告

日期：2026 年 11 月 1 日。固定 `{r['source_sha']}` 的独立静态源审查通过。新构建前的未知作业门检出了缓存内 `git-remote-http` PID 297502，驱动按计划停止。构建、17 例夹具、核心和网络执行均为 0；本次没有适配器运行通过结论。

## 1. 已完成的源码审查

已逐项核五文件差异及固定哈希。移除新增 DispatchRequest 提取和两处友元声明后，三个生产文件逐字节恢复父源。SwitchNode 生产适配器及预算／等待／配额核心未改，见[独立源审记录]({PREFIX}-source-review.json)。

实际 PPP 为 14 B、IPv4 为 20 B、UDP 为 8 B；INT mode 1 的 SeqTs 为 14 B，合计 56 B 包头。仓库 UDP 写实际剩余长度，完整 CustomHeader 减去 22 B 的 UDP／SeqTs／INT 后得到原载荷。八个 QbbNetDevice 均连接实际 BEgressQueue，负载读取真实队列，5,000 B 入队在实际容量内。

C1 重复、空洞和部分重叠的唯一账，19,999／20,000／20,001 ns 到期边界，以及容量／区间／序号跨界回退的预期与生产方法一致；观测会检查 Pressure 是否额外清理漏掉的到期。C3 借用、首次类别缓存、20,199／20,200／20,201 ns 只读快照和 20,202 ns 真调用续期逻辑一致，生产清理前后新表和历史计数分开检查。

C2 子类通过 CreateObject 设置 TypeId 并继承属性；只替换生产计时计数后的虚拟传输入口。原需求 10 ns、同刻两种 event uid 顺序、Stop／Dispose 与重复控制、零等待同步交付均有实际生产入口和优化构建有效的 NS_FATAL_ERROR 检查。上述为静态审查，尚未通过构建或执行验证。

## 2. 实际执行与停止依据

本地旧驱动门、干净已推送个人 fork、新 ID、worker 与初始资源门通过。仅执行一次 guarded sync，将缓存引用更新到固定 SHA；worker 与 controller 原始字节、规范化 LF 对象保持既有来源，未部署。

同步后 cache origin／分支／树／clean 与新 ID 均通过。紧接的新构建前门在 `2026-11-01T06:42:04.334661Z` 记录 PID 297502，cwd 为 `/home/fnl/lzy/code/conweave-ns3`。无计算进程、无其他用户进程，一分钟负载 0.24，可用内存约 122.513 GiB、磁盘约 2,298.321 GiB。停止由未知项目进程触发，不是资源不足或源码失败。

随后只读诊断在 `{diag['recorded_utc']}` 已看不到该 PID，因此无法再取其父链；不将它推断成其他用户作业，也不确定归属到本次 sync。未发送信号、绕过门控或自动续跑。见[停止前资源收据]({PREFIX}-evidence/{plan['id']}/resources-before-build.json)及[进程诊断]({PREFIX}-process-diagnosis.json)。

## 3. 保全与后继

{len(objects)} 个本地固定 Git 对象、4,843 项完整树、冻结计划／契约、差异、源码审查、sync 日志和门控收据已保全，见[索引]({PREFIX}-index.json)。新 ID 在最后 cache 门仍不存在，未建立构建源副本，也没有 raw、测试二进制或动态库产物。本副未改主源码、worker、controller、环境或既有证据，未提交／推送。

构建及 C1→C2→C3 的 17 例实际验收继续待办，需主核本次门控记录后安排新的实时门与接续。源码／入口／环境约束尚未释放，不能由缓存同步推定为副本建立。新源默认网络回归、真实端点 generation／drain／reuse、独立 C1 V0 和双侧效果／成本仍未完成。

已从候选 README／reading-log 复核 DiffFlow v1 的生效顺序与回收缺口，仅借鉴检查问题，不外推其 SDN 喷洒或平均 FCT；见[参考复核]({PREFIX}-reference-review.json)。本副停止新增执行，等待主处理。
'''
    (ROOT/(PREFIX+'-report.md')).write_text(report,encoding='utf-8')
    sections=[('本对话目标','先审固定五文件，通过后一次完整构建，再按 C1→C2→C3 执行新增 5／10／2 例；禁止网络、旧核心与旧控制器。'),
        ('已确认的项目事实',f"固定 `{r['source_sha']}`，父源 1ec5eedc；计划 SHA-256 `{r['plan_sha256']}`，新 ID `{plan['id']}`。"),
        ('已完成工作',f"源审通过，生产差异可逐字恢复父源。一次 sync 完成，新构建前作业门停止。构建／夹具／核心／网络均 0，详见[报告]({PREFIX}-report.md)。"),
        ('已形成的设计决策','保持冻结判据，检出未知项目进程后停止后继。只读诊断确认 PID 后来消失，不据此覆盖原失败门或自动放行。'),
        ('当前状态','`STOPPED BEFORE FIRST BUILD`。PID 297502 当时为缓存目录 git-remote-http；后续已不存在。固定源审查完成，工程验收未执行，源码／入口／环境约束未释放。'),
        ('未解决问题','一次全构建与 17 例运行仍待完成；还需新源默认网络回归、真实端点生命周期及 generation／drain／reuse、独立 V0、双侧效果和成本。'),
        ('后续推荐动作','主核未知进程门与只读诊断，决定接续后重新核旧进程、cache、未使用 ID 与实时资源；不重跑已验核心、不覆盖此停止交付。'),
        ('与其他工作流的关系','仅写本轮 independent 前缀；主源码、worker、controller、环境和原证据未改。Ofan/RR、WS-29 与旧矩阵未执行。'),
        ('CONTEXT SNAPSHOT',f"适配器预检固定 1f917f44，源审通过，但新构建前 PID 297502 git-remote-http 触发未知项目作业门；构建／fixture／network 均 0。PID 后续已消失，未杀进程或续跑。缓存已更新，源副本和约束释放未完成。入口见[索引]({PREFIX}-index.json)。")]
    handoff='# 适配器边界预检九节交接\n\n日期：2026 年 11 月 1 日。来源副对话 `01a19323-2201-7b23-a0f1-905c71496d38`，接收主对话 `01a19322-95a5-76e3-a4f5-1f1e9dde81ce`。\n'
    for i,(title,body) in enumerate(sections,1):handoff+=f'\n## {i}. {title}\n\n{body}\n'
    (ROOT/(PREFIX+'-handoff.md')).write_text(handoff,encoding='utf-8')
    deps=['main-mode-dynamic-r1-driver.py','zero-control-pilot-r1-driver.py']
    docs={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in ROOT.glob(PREFIX+'-*') if p.is_file() and p.name not in (PREFIX+'-index.json',PREFIX+'-qa.json')}
    dump('index.json',{'status':r['status'],'verification':integrity,'source_sha':r['source_sha'],'plan_sha256':r['plan_sha256'],
        'documents':docs,'support_files':support,'support_path':str(folder),'fixed_local_source_objects':objects,'dependencies':{p:sha(ROOT/p) for p in deps},
        'remaining':'One build and all17fixture cases unexecuted; main review/resume required','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    for p,info in docs.items():assert sha(ROOT/p)==info['sha256']
    links=[]
    for text in (report,handoff):
        for rel in re.findall(r'\]\(([^)]+)\)',text):assert (ROOT/rel).exists();links.append(rel)
    assert len(re.findall(r'^## \d\.',handoff,re.M))==9
    dump('qa.json',{'status':'PASS_FOR_STOPPED_GATE_EVIDENCE_ONLY','index_sha256':sha(ROOT/(PREFIX+'-index.json')),'documents_rechecked':len(docs),
        'support_files_hashed':len(support),'links_checked':len(links),'handoff_sections':9,'no_build_or_fixture_or_network_claimed':True,
        'guard_not_released':True,'new_remote_actions_by_finalizer':0,'style':'Original ruanyf README and six chapters previously read; headings, spacing, values, punctuation and structure reviewed'})
    assert json.loads((ROOT/(PREFIX+'-index.json')).read_bytes())==read(ROOT/(PREFIX+'-index.json'))
    print(json.dumps({'status':r['status'],'index_sha256':sha(ROOT/(PREFIX+'-index.json')),'qa_sha256':sha(ROOT/(PREFIX+'-qa.json')),'verification':integrity}))
if __name__=='__main__':main()
