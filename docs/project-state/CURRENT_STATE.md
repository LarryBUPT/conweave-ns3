# ConWeave 毕业论文项目状态

## 当前阶段（2026-11-08）

WS-31 已按 11 月 8 日的新直接用户指令恢复，当前为 `ACTIVE_NATIVE_ENTRY_R2_ACCEPTED_NEXT_G2_BOUNDED_DESIGN_REQUIRED`，见[恢复节点整合](../handoffs/2026-11-08-ws31-native-recovery-integration.md)与[真实用户消息](../research/evidence/ws31-native-recovery-integration-20261108-r1/user-instruction.json)。原主、副各一项 Codex 原生心跳均为 ACTIVE、30 分钟，ID 分别为 `ws-31`、`ws-31-2`；实际创建收据、回读和配置哈希已核。当前不据配置存在宣称已观察到定时触发。11 月 4 日的 HOLD、删除和压缩纠错保留为历史，不覆盖本次新授权。

旧 R1 构建失败与完整失败材料保留，主修复了验收消费者的清单字段；源码仅一行 Waf 头导出修复。新固定源 `21b440985f90d2081438e435ef640adc9f43a42d` 的 R2 ID `20261108-152638-ws31-native-entry-r2` 已完成一次完整 `-j2` 构建和 20 个非网络对象案例。Integration 从本地独核 R1 的 65 raw／25 归档成员、R2 的 202 raw／147 归档成员、4,870 个 Git／源码归档与终态指纹、24 条实际命令、4,482 条包记录、两输入及 ELF／36 项目库；没有执行科学代码、构建、夹具、仿真或 SSH。

R2 完成事件是北京时间 15:36:38.050986，主完整验收观察是 15:47:06.250075，Integration 观察另存[本次收据](../research/evidence/ws31-native-recovery-integration-20261108-r1/verification.json)。主已显式释放有限约束；唯一副沿主报告 completed／idle cursor `3dadc2c4-3e49-4c0c-9ee1-13940917f98a:136`，未新派发。下一步由原主形成剩余 G2 的有界设计及独立单目标计划；已终态 R1／R2 不由心跳重跑。

通过范围仅限入口工程。OS2／framing、完整完成／共享协议、真实超时两代、独立 V0、匹配消融、业务／背景双侧效果与成本均未完成；历史 43 网络、17 适配器与本次 20 对象案例分列，无新组合基线。群端附加检查因桌面缺 `CC_SESSION_KEY` 失败，原生监督检查实际通过；不据此要求用户补 Codex 权限。原 WIP、Ofan 暂缓、六基线、WS-29 后置及旧控制器边界保持。下方历史“当前”与下一步均限于其记录日期，不能恢复旧任务或覆盖新状态。

## 历史阶段（2026-11-04）

本轮有限筛查和 D1／D2 需求设计已经完成，当前执行状态为 `HOLD_CURRENT_SCOPE_FINITE_SCREEN_COMPLETE_NO_AUTOMATIC_CONTINUATION`，见[分析节点整合](../handoffs/2026-11-04-ws31-finite-screen-hold.md)。工程、测试、效果矩阵及远端继续暂缓；没有新的需求／观测证据或明确范围更新时，不重复分析、扫参、派副、创建配置／输入或续接旧接线。`ws-31` 心跳已由主对话删除；Integration 已核删除收据和本地配置缺失，见[运行状态同步](../handoffs/2026-11-04-ws31-heartbeat-stop-integration.md)。未经新指示不重建，HOLD 与全部未完成义务保持。

Integration 已从两份旧原始日志独立核验新分析：固定 c4 输入的 104 次决定、四规则共 416 行，原载荷预算、逐条报文换算及 Q＋R 选择均对应；类别扣减与计数有 3 次选择不同，类别与统一扣减有 21 次不同。Q、旧分配与到达始终沿 QueuePin 轨迹，因此不构成动态反事实、独立 V0、收益或方向正确性。C3 的 4 个借用者、7 个借用者×主人阶段组、546 包／572,208 B 及最大源到达跨度 24,507 ns 均核；滚动活动续期不等于固定 20 μs 阶段，日志不能认证物理出队／在途闭合或容量归还。

D1 仅设计两类同为 16 KiB、保留同步组与独立背景行为；D2 仅设计两类共享重叠大小分布、需求内配对。两族都没有新配置、输入或运行；未来组成员、后续请求和最终完成信息不进入在线规则。19 个科学 WIP 及 HEAD 8cd 保留，原 43 网络／17 适配器科学证据范围不变，全部正确性、V0、消融、双侧效果与成本仍未完成，未建立新基线。

### 外评范围与保留义务

最新范围已按用户在主对话的直接要求调整，见[评审后范围整合](../handoffs/2026-11-04-ws31-review-informed-rescope.md)和[用户原文](../research/evidence/ws31-review-rescope-integration-20261104-r1/user-instruction.json)。外评后的研究范围记录为 `ACTIVE_REVIEW_INFORMED_RESCOPING_CANDIDATE_ENGINEERING_PAUSED`，当前执行状态以上方 HOLD 为准：C1 条件保留信息与完整评分动作检验；C2 保留错峰／原需求起点计时对照，暂缓独立创新扩展；C3 暂缓效果与配额调优，先查逐端口、逐借用 QP 的实际回收区间。共同端点新增接线、科学源码及配置修改、构建、测试、夹具、网络和效果矩阵均暂缓，只允许有限本地只读证据清点、规则核查和有业务依据的类别／大小解耦需求设计。未完成正确性、V0、消融、双侧效果与成本义务保留，暂停不等于取消或闭环。

[三份评审综合报告](../research/evidence/ws31-review-rescope-integration-20261104-r1/snapshots/main/report/c123-review-synthesis-and-action-plan-20261104-r1.md)已交付。九个提案不批量实现：CCB／CCPB 即时版仅先查动作机会，MACA／CGQ 条件保留，CQT／CLC／CDLC／BCS 暂缓，原样 CCL 与 CCPB 批量持包扩展不采用。启发式 oracle 不是理论上界，残留总字节不是每次回收时长，8 KiB 请求不是一个 MTU 包；C1 混合技术结果和旧固定配额反例均不证明动态候选已被正式证伪。

Integration 已核三份评审原文、主五份产物、副三份产物及 19 个 WIP 路径哈希，并按原哈希恢复转换前完整状态的 CRLF 字节。科学 HEAD／个人 tracking 仍为 8cd，新字节未编译或运行。此前 r3 差分和身份／完成草稿审查已由主验收并释放；本次 Integration 只核这些收据与 WIP 身份，不把未重验的完整静态分析升级为自身验收。唯一副文档目标完成、主报告 idle cursor `d0b9dd1a-3dbb-4cea-9a35-6aefe1b3ed0d:14`，不重复派发；Integration 观察主 idle cursor `f13c4cd1-6458-4d58-888a-76f78e636578:2`。

历史上，`ws-31` 心跳曾通过应用工具更新为有限范围，保留当时 ACTIVE、原主对话和 30 分钟周期；这些原配置仍作为历史证据保留。主对话随后于 2026 年 11 月 4 日 12:12:42 UTC 记录删除完成，当前不再有该心跳配置。旧自动接线入口被覆盖，无实质变化时静默；没有存活候选依据、新契约、固定独立计划和资源门，不自动恢复工程或远端。43 格技术网络、17 例适配器和旧工程验收保持各自范围，无新组合基线。下方历史实施授权、工程下一步和 active cursor 均为当时快照，不能覆盖本条范围。

### 已完成历史与工程证据

用户已确认执行“历史归并 → WS-30/v13 归档 → WS-31 类别感知新机制构思 → 验证后建立新基线 → 后置接续 WS-29”。本次基线审计读取 33 份对话的最新两至三轮及相关交接，覆盖 WS-01～28 和 WS-30；WS-29 仅登记元数据，未读、未唤醒、未归档。详情见 [WS 覆盖表](WS_HISTORY_COVERAGE.md)与 [来源收据](../research/evidence/ws-history-20261101/coverage-and-source-manifest.json)，不把范围审计说成逐条穷尽全部历史消息或新一轮 raw 数值复验。

WS-30/v13 已完成的实验和证据保持原样；旧 v14 P0 的 52 次保留为历史补充，未执行的 840 次按用户确认的新范围结束自动续作，不写成已完成，也不混入已投稿 v13。两个实验对话已在交接、状态提交后归档，并在活动与归档目录分别复核，见 [归档收据](../research/evidence/ws-history-20261101/ws30-archive.json)。旧 `ws-30-v13` 自动化保持 PAUSED。处置依据见 [ADR-011](../decisions/ADR-011-ws30-closure-ws31-and-ws29-deferral.md)和 [WS-30 收束交接](../handoffs/2026-11-01-ws30-v13-closure.md)。

QueuePin 最新本地稿为 `E:/研/毕业论文/thesis/queuepin-v13-figure-revision-r12/queuepin-icc-authors-r12.pdf`，六页，SHA-256 `f16e2fa5e7873aa62acf6181c5f0eafc45a90dfd75d583fcc27dfed345563a0b`；作者为 Zhenyu Luo、Shuo Wang（通讯作者）。EDAS 附件显示 ICC 2027 NGNI 论文 1571378157 已上传、Active (has manuscript)，题名及作者信息一致；本次未独立下载服务器 PDF 核字节，ORCID 状态也未在附件展示。相关待核及录用后手续由 Integration 投稿跟踪承接，不恢复旧实验。

WS-31 主、副已在“科研”项目设立：[执行清单](WS31_EXECUTION.md)、[协调登记](ws31-coordination.json)。A～H 提案阶段已交付，用户随后直接授权按 C1 → C2 → C3 顺序进行判断与实现，并由主对话自主决定 Gemma 等额外负载均衡对照的实现必要性及成本，见[授权原文](../research/evidence/ws31-implementation-authorization-20261101/user-instruction.json)。旧“等待选题／只做提案”门槛已解除；当前按新协议推进实现和验证，不把授权等同于已有新 raw 或性能结论。初始对照为 QueuePin 及五个既有方法，只有新类别感知机制通过正确性和独立验证后，才形成“QueuePin＋新类别感知机制”基线。

WS-31 最新网络节点：固定 `1f917f44fcfb88e61f3ad22c5cc75fa3a06b6c0e` 的 Q12／C2 默认两格已主验并经 Integration 独立核对，累计 43 格技术网络覆盖，见[第十三节点](../handoffs/2026-11-01-ws31-adapter-default-integration.md)。两格共 208 完成、403,963,904 B；完整 FCT 及仅去 uid 的有序 CHOICE／ROUTE 恢复各自 c4／2ed 参考，C2 全部需求／放行／完成／状态事件一致。104 次等待按固定哈希独立复算，80 次为正、总 18,002 ns、最大 497 ns。Integration 核 26 文档、5 依赖、12 未变参考、52 结果、22 支持、4 文献来源、84 源映射／42 个 Git 对象及 4,843 项树。通过范围限于本输入的默认交付兼容，不是独立效果。

此前 `1ec5eedc24cd863a289b7493e8b3865c70592ab5` 的动态标签十格及恢复交付已验，当时累计 41 格。十格共 150 条完成、2,457,600 B；Integration 核 193 结果、83 支持、26 恢复文档、6 依赖、268 未变旧文件、4 参考、40 个 Git 对象及 4,841 项树。2,295 次构包、6,885 次逐跳标签关联及 90 个阈值前后请求实例均有实际证据，见[第十一节点交接](../handoffs/2026-11-01-ws31-label-dynamic-integration.md)。实例重复使用同一 15 请求输入，不作为独立需求或效果样本。完整预算／活动归属模型重放保留主验身份，Integration 另核实际 uid／时刻／存在性、首次策略、精确 C2 等待及 C3 计数。

既有标签夹具工程门：G1 修复源 `2ed7d342d0713a5667f43c7730ca5bc5a6a67150` 的完整构建、新标签核心与五项 mock 已验，见[第九节点交接](../handoffs/2026-11-01-ws31-label-preflight-integration.md)。Integration 核 28 文档、2 依赖、12 支持、9 结果、38 个 Git 对象和 4,839 项树；构建 1,464 项、352.659 秒，新核心断言开启，网络运行 0、raw 无产物。CRLF 原字节、固定 LF 代码及旧 checker 记录分别保留。首轮 G1 停止和未检查的旧远端 ID 仍见[原交接](../handoffs/2026-11-01-ws31-label-g1-repair.md)。

十格期间的 checker 模式比较错误已按原冻结判据修复，原八格未重跑，只运行原 BUILT、未启动的 C3 p2／p3 各一次；旧 checker、停止交付及 raw 保留。最新 r3 主收据采用 ASCII 兼容封装，旧 UTF-8 index／QA 字节仍在，decoded index 仅文档清单及时间变化。临时 JSON 报错来自主读取时遗漏 UTF-8，不是实验或原 JSON 故障。

适配器固定 1f 源此前已完成一次 optimized `-j2` 全构建及 C1 五例、C2 十例、C3 两例的主原日志验收，见[第十二节点整合](../handoffs/2026-11-01-ws31-adapter-boundary-integration.md)。Integration 独核 33 文档、4 依赖、28 原 r1 文件、15 支持、47 结果、4 参考、42 个 Git 对象及 4,843 项树；两个 ELF 二进制和 36 个库均核字节。完整 C1／C3 模型重放归主，Integration 另核原日志的区间扣减、到期、回退、实际队列、事件顺序、路径与状态计数。17 例作为非网络工程条件单列，不加入 43 格。

r1 同步成功一次后，因未知缓存 Git HTTP PID 297502 停止于构建前；后续进程消失但祖先链未取得，归属继续未知，原停止记录不改。r2 新门通过后构建 1,468 项、用时 5m59.118s，三夹具顺序执行，未同步、部署、重复旧核心或运行网络。C2 十需求合计 81,920 B，四次取消、六次交付替身，固定等待 376 ns，真实 QP 和完成均为 0。C3 的一个残留包为 156 B，夹具开销 56 B，不与旧网络格式混加。

默认回归两次全构建先于串行 Q12 → C2，未同步、部署、重复旧核心、17 例或参考格。79 次构建资源采样最多四个编译前端，最高负载 4.07、最低可用内存约 121.40 GiB；均为采样值。两调用终态后于 07:24:38 UTC 明确释放约束；主核旧驱动 22440 不存在和副 idle cursor 92 后，另派本地只读端点核心审查。该审查现已终态，原报告、JSON、QA 和两份原 WIP 均保留。

端点静态审查及修订已形成[第十四节点](../handoffs/2026-11-01-ws31-endpoint-core-integration.md)。Integration 核 11 个固定对象、原审查三份输出和两份旧 WIP 字节；另核源码发现：队列组 Clear 只清向量、不清 finished 位，旧索引已置位时可跳过重用索引的新 QP。后续真实夹具改用保留已完成旧 QP、追加新 QP，不修改基线 Clear；生产位图分支仍待实际覆盖。TX／RX packed key 别名、交换机四元组不含 PG 和 ACK／NACK 有标签才复制也已核对，旧设计“无条件复制”仅由新契约纠正，旧记录不回写。

固定 `20bc2d9f7c7c435bf832ba2fcaf0e07df00cf5da` 的独立核心预检现已主验并经 Integration 核对，见[第十五节点](../handoffs/2026-11-01-ws31-endpoint-preflight-integration.md)。一次同步、一次 C++11／-DNDEBUG 编译、一次运行，手工两代账本及 6 token 完成，真实端点快照和网络均为 0。核 90 项索引文件、41 项 raw、5 项旧文件、4 参考及全部 4,845 条 Git 文件路径／284,683,832 B；路径数不称唯一对象数。50,520 B ELF、精确 argv／stdout／stderr／退出码均匹配。五项库仍仅为 ldd 解析与远端哈希收据。全 NS-3 构建、部署、网络和旧测试重跑均为 0。

旧核心约束于 08:19:32 UTC 明确释放后形成的首版实际对象 probe，现已完成静态审查及原 WIP 留存，见[第十六节点](../handoffs/2026-11-01-ws31-endpoint-object-integration.md)。Integration 核 25 个固定源路径、8 项旧文件、审查报告／JSON／QA 和两份原草稿。保存 TX 若不在枚举组中，首版可能漏计完成／pending；这是静态覆盖反例，原 mask=127 仍阻止完整 ALL 认证，不称网络失败。修订增加实际 driver／HW／Node／NIC／队列／组绑定、保存 TX 独立入账且在所选组恰一次、设备范围冻结与去重、空 live Ptr 拒绝。

固定 `8cd1ba69469bf80143d5c89edc17fa72611018e8` 的一次 optimized `-j2` 全构建及一次新对象夹具现已主验并经 Integration 独核，见[第十七节点](../handoffs/2026-11-01-ws31-endpoint-object-acceptance.md)。1,470 项构建、退出 0；八组同刻双读、十四组 Read 拒绝及 mask／Capture 两项额外拒绝均有原日志。31 次 Read 中 17 次成功返回、14 次拒绝，其中一次成功返回随后因 mask127 被账本拒绝。62 行输出的对象绑定、13 条保留槽位、SACK、队列和事件记录匹配；真实网络完成、事件执行及 ALL255 证书均为 0。

Integration 核 170 项索引、109 raw、13 旧文件及完整 4,847 条源码路径／284,719,415 B；实际 1,709,032 B ELF 和 36 项工程库副本均核字节，9 项系统库仅远端指纹。构建实际参数为 -O3／-g／gnu++11、无 -DNDEBUG，与此前独立核心编译分列；外层 358.507 s 与 Waf 5m57.379s 是不同计时范围。两处辅助 checker 的 CRLF／LF 与 stdout-only 假设错误保留，修正只重读旧字节，无科学重试。第十七节点约束于 09:47:46 UTC 显式释放，当时副 idle107、实现树干净 8cd；这是历史观察，后继 WIP 与审查约束见下段。

channel 完整静态审查及修订形成[第十八节点](../handoffs/2026-11-01-ws31-endpoint-channel-integration.md)。Integration 独核 36 项证据、22 份固定父源副本、额外一项 scheduler 父源指纹、55 个原版本源码锚点和新旧各五份 WIP，留存 78 份原字节快照。首版审查有四项 P1、一项 P2：精确 C++ 动态类型、U16 身份别名、未初始化大小、事件异常跳过 Unref，以及部分记账／调度／动画／绑定失败。接收审查证据不批准首版代码执行。

首版约束于 12:34:40 UTC 释放、副 idle3 后，主编写 r2：精确类型检查、编码前身份范围及大小初始化、事件内保存异常并 Stop 后正常返回、失败锁存、绑定预分配与无抛出提交，以及已使用 channel 的晚绑定拒绝。五份新文件与封存副本字节一致；其中四份较 r1 改变，tag 头保持同一 include guard，原 tag 类体和编码体未改。默认路径新增使用标记写入，兼容性与成本尚未运行验收。修订和夹具仍未编译／执行，不称五项问题已获独立通过。

第十八节点时，独占实现树为五份未提交 WIP，唯一副正在审 channel r2；当时的计划与 cursor 保留在该节点。后继审查新增 R2-01／P2：事件调用前按值复制回调可能先于函数体的 catch 抛出。主改为 const 引用，事件仍持有回调值；switch r1 审查确认这一最小修订及三项原异常消息检查。Integration 补核该 channel r2 的 42 项证据、26 份父源副本和 67 锚点，不把源码修订写成运行通过。

第十九、二十节点已一并完成[本地整合](../handoffs/2026-11-04-ws31-endpoint-switch-integration.md)。switch r1 的 43 证据／16 父源副本／68 锚点／九份 WIP 均核；S1／P1 为旧端点结果与新 switch 范围可能拼接，S2／P2 为接口 owner、index 和唯一性缺项。r2 改为私有复合 Scope，在同一同步调用中直接读取实际端点与 switch，并在捕获及验证时检查设备绑定。新增双 switch／双 host 夹具，其协议状态和两个 token 由测试赋值，尚未编译或执行。

恢复后的同一 switch r2 目标已完成，Integration 核 62 项证据、28 份父源副本、68 锚点和十份封存 WIP；原 usage-limit 失败、恢复及未完成中间收据保持原身份。S1／S2 在源码层确认；新增 R2-F1／P1 是 owner 拒绝例的指纹先访问空 QP group，尚未到 Read 守卫。这是静态缺陷，没有实测崩溃。副于 11 月 4 日 06:58:12 UTC 显式释放且主查 idle 后，只改夹具的可选对象判空和目标异常消息检查，另九份文件逐字节不变。

当前 HEAD 和个人 origin tracking 仍为 8cd，六份受跟踪修改、四份新增未提交。十份 r3 当前字节与封存相同，唯一副只做最小差分复核，主报告 active cursor `d0b9dd1a-3dbb-4cea-9a35-6aefe1b3ed0d:4`；Integration 只观察主 idle cursor `f13c4cd1-6458-4d58-888a-76f78e636578:1`。计划 SHA-256 为 `b508f333802b730fbd8ab98229b7c9a161e4b2ffee276e75c5db9e45af735e04`，十文件冻结，无远端／构建／测试／网络授权。

夹具指纹限于列出的协议字段与 switch 核心内容，不覆盖全部对象内存、队列包身份或全部 QP 状态；两次 Observation 也只比较既定目标计数。25 组双读、63 次组合 Read／53 次返回／10 次 Read 拒绝及 19 次总拒绝均为静态计划，mask 255 实测为 0。重复 AddDevice 同时改变数量和编号，不能单独证明唯一性分支已动态覆盖。

主已另交付[外部创新性审阅材料](../research/evidence/ws31-endpoint-switch-integration-20261104-r1/snapshots/main/ws31-c123-external-review-brief-20261104-r1.md)。Integration 仅核文档身份与交付，不把自查当外部审阅、新颖性认证或参数变更授权。下一步接收 r3 差分复核并处理必要问题，继续真实完成回调／saved RX、历史清理、实际 G1、全部身份生产者和共享 PFC／CNP／ACK/NACK／重传，再冻结真实两代网络正反例。编码器范围检查仍不能恢复已截断的外来 tag。独立 V0、匹配消融、业务／背景双侧效果与成本继续必做；43 格技术网络、17 例适配器及旧核心／对象夹具分别保留。

此前大小克隆仅在原标签与大小绑定的输入中等价，成本差异／惰性清理及单输入 V0 两侧观察继续保留。动态标签、适配器及默认兼容通过限于各自小输入与测试条件，不估计真实分类质量或效果。Ofan 暂缓；真实端点退出／排空／跨代复用、独立 V0 和双侧效果／成本仍待完成。新组合基线尚未形成。

前序缺项已补，并按用户随后要求完成对话归档：WS-26 仍为用户暂停、完整科学范围未完成，两份草稿和未执行事项已另存交接；其主、副历史对话均在归档目录。WS-27 预设 384 格独立确认等范围完成，原对话与恢复续对话均已归档；WS-28 原生 144、组件 120、诊断 12 格范围完成，原对话已归档。详见 [归档交接](../handoffs/2026-11-01-ws26-ws28-archive.md)及[平台收据](../research/evidence/ws26-ws28-archive-20261101/archive-results.json)。WS-29 保留编号与主、副，等待新基线后再研究状态反馈增量，当前不读取或启动。下方日期段落均为历史快照，不恢复其中已过期的 ACTIVE、缺作者或旧截止日。

## 历史快照（2026-10-29；v14 P0 阶段）

WS-30 的 v14 完整 P0 已完成 52 次正式运行、861,312 条 FCT 和 92,878,667,776 B 的主独验、完整分析及三稿整合；原 892 次范围尚余 840 次，完整任务继续 ACTIVE。平局匹配 Q/T 的批次变化中位数为 −2.97%，19/24 更快，背景 P99 为 +0.57%；相对 DRILL 的背景保护继续按同需求直接比较解释。当前执行轮按用户要求在北京时间 18:00 前结束，旧监督自动化保持暂停，不自动延长实验。详见 [本轮九节交接](../handoffs/2026-10-29-ws30-v14-p0-supervisor-stage.md)。

三稿、准确当前 PDF、主验和全部未完成入口见 `E:/研/毕业论文/thesis/ws30-paper-v14-current.json` 及 `ws30-paper-v14-supervisor-delivery-r1.md`。真实作者与 EDAS 元数据未知，当前稿不称全量完成或投稿就绪。下方较早快照保留其历史范围，不替代本条 WS-30 状态。


## 历史快照（2026-10-07）

WS-25 第一课题的七项预设 **ns-3 实验及小论文初稿验收已完成**，见[逐项审计](../research/ws25-first-paper-acceptance-audit.md)、[Handoff 77](../handoffs/2026-10-07-77-ws25-first-paper-prespecified-acceptance.md)与[执行清单](WS25_FIRST_PAPER_EXECUTION.md)。个人 fork `feature/ws25-first-paper@e501e773944a58ecc1bfc913f4d86d3f65a4431c` 的固定 v1 仿真 SHA `ce699dffe2845dc83e2171a1c309c6d96b96d2b3` 已完成 24 个未见需求 seed × 四背景档 × 六臂，共 **576/576** 个原 ID、36 批 raw 逐格验收；2026-10-07 重算的正式分析哈希保持一致。192 档相对 ECMP，MoE 合成批次中位变化 **−3.536%、20/24 改善**，背景 P99 FCT **−0.065%、13/24 改善**；共同主判据为确认性 **NO-GO**。v2 原版和唯一修正版 v2r1 各有 28/28 个独立探索格，均未过双侧筛选门，不能充当正式收益。第三候选名额未使用，理由见[准入审查](../research/ws25-third-candidate-decision.md)。[负结果初稿](../research/ws25-classreserve-v1-paper-draft.md)已形成，**尚未投稿**；目标会议版式、引用与投稿是后续里程碑。结果限于冻结合成需求与 ns-3 RDMA QP 模型，动态基线分支覆盖、物理队列因果及真实部署证据均有限。第二课题须待投稿后单独启动。副对话保持未归档，无在途 WS-25 矩阵。

## 历史快照（2026-10-04；以下 WS-25 运行状态已过期）

WS-25 继续执行**第一课题类别感知包流混合负载均衡实现、独立验证与小论文成稿**，逐项门槛见 [WS-25 清单](WS25_FIRST_PAPER_EXECUTION.md)。修正版校准固定 SHA `a656104d05c681f9b3a998b5ef4ce3e644558d02`：四需求 192 档 24 主格/4 诊断格和 0/64/128 档 72 格均完成并逐格验收。[192 档分析](../research/ws25-v1fix-four-seed-calibration-analysis.md)与[低档分析](../research/ws25-v1fix-lower-load-calibration-analysis.md)显示跨档和基线之间有双侧权衡，不能声称五基线普遍收益。容量试跑 18 路相对 16 路吞吐只增 4.23%，未过 5% 升档线，正式调度 cap=16。根据校准已**事前固定**[正式协议](../research/ws25-v1fix-formal-protocol.md)：192 档双主结果、24 个未见需求 seed `20262521–44`、五基线及 0/64/128 约束。96 份最终输入哈希在[manifest](../research/evidence/ws25-v1fix-formal-inputs.json)，固定输入/仿真源码 SHA `ce699dffe2845dc83e2171a1c309c6d96b96d2b3`，576 格顺序在[机器计划](../research/evidence/ws25-v1fix-formal-plan.json)。截至 2026-10-04 16:12（北京时间），前 10 批 **160/576 格**已通过正式 raw 与资源逐格验收；第 11 批 16 个原 ID 已启动。唯一 runner PID `46324` 存活、stderr 为空。收据记录 17 个 `built_recovered_transport`：一项重复 build 被远端因 ID 已存在拒绝、其余为控制器超时后状态回读；原 ID 未覆盖，raw 已验收至 160。控制器与状态记录见 [Handoff 73](../handoffs/2026-10-04-73-ws25-formal-ssh-timeout-recovery.md)。下一步按半小时读取精简收据与资源摘要；批次终态逐格验收后扩展。尚无正式算法结论，WS-25 ACTIVE。

WS-23 与 WS-24 的预设 **ns-3 合成范围均已闭环**，见 [最终验证清单](WS23_WS24_VALIDATION_PLAN.md)与 [Handoff 55](../handoffs/2026-10-02-55-ws23-ws24-final-integration.md)。WS-23 固定仿真 SHA `3db2685a3540895bf49e25302bd00465bc0921e2` 的 18/18 隔离格、传输恢复正确性和资源收据均验收；预设隔离效果 `exploratory_positive=false`，即 **NO-GO**。WS-24 固定仿真 SHA `3b992eed218f65b4f8026eddb5170a7694e17b10` 的 12 个独立合成 job × 四臂 48/48 格与资源收据验收；12/12 job 多 rail 完成跨度较短，中位配对差 −19.667%，精确双侧符号检验 `p=0.00048828125`。两者均不代表真实网卡或生产收益，也不能直接充当后续两个包流混合机制课题的正向结论。下方 2026-09-30 记录保留为历史阶段快照，其 ACTIVE/NO-GO-for-simulation 口径已被本次完成的实验取代。

WS-25 最新恢复快照（2026-10-04）：正式summary有 **224/576** 格，批14已从远端回传且16/16 raw/资源逐格验收。runner `5752` 在批15开始前因控制器提交未推送而被个人fork安全门拒绝启动；修复提交 `094e198` 现已推送，唯一runner当前待沿summary从批15恢复。第15批ID225尚未创建或启动。最近远端审计确认批14所有原 ID `SUCCEEDED`、固定仿真SHA一致，无其他用户任务/持有锁/运行worker，资源线充足。控制恢复见 [Handoff 74](../handoffs/2026-10-04-74-ws25-formal-fetch-resume-recovery.md)。

后续研究范围已由用户确认，见 [ADR-010](../decisions/ADR-010-sequential-mixed-lb-paper-plan.md)：以开题报告的包流混合负载均衡背景、流程和目标结论为主线，机制实现可调整；仅远程服务器 ns-3。沿 WS-11/12 的 16,384 条 MoE 加 0/64/128/192 条背景流既有分布与主拓扑，不增流量类型或档位，允许同分布新独立 seed。第一课题优先研究类别感知选路，以原始仓库 ECMP、DRILL、CONGA、LetFlow、ConWeave 为正式主对照；MoE 合成批次与背景 P99 FCT 为共同主结果，192 为主档，其他档预设约束。筛选、校准和最终验证使用分离的需求 seed；校准 pilot 后、正式矩阵前冻结双侧数值与样本量。目标 2026-11-02 前完成第一课题验证与小论文成稿，投稿随后进行；**投稿后才启动**有成本、有时效的状态反馈第二课题，乱序代价为次要约束，不并行推进。各课题最多三个候选版本、每版一次诊断修正，失败即停并复盘。WS-25 正式判据与最终矩阵已冻结并执行至 144/576 格；WS-10/11/12 的历史双侧 NO-GO 保持。

2026-09-30 WS-23 接续预飞行：`feature/ws23-validation` 的新增探针与双场景验收源码固定在 `70bf890d1ceba58c5ebd26b17e492295b34c99ca`；[两格协议](../research/ws23-two-cell-preflight.md)冻结了真实源端 pause/resume、旧 16×1 MiB 压力反例、输入/拓扑哈希、seed、预留 ID 与资源停止条件。Python 静态检查、解析器构造记录及旧结果拒收已通过。**此 SHA 尚未远端构建、单测或仿真，两格无新 raw；WS-23 继续 ACTIVE**。下一步在实际 Luna High 监督阶段做隔离构建/单测与两格正确性仿真，终态 raw 回传后实际切 Sol High 核验；跨类阻塞的机制与因果前提另见协议，隔离效果矩阵仍关闭。

2026-09-30 闭环纠错：此前 Handoff 45 将阶段交接当作任务闭环并归档，用户指出必做验证未完成。WS-23/24 恢复 ACTIVE，详见 [验证执行清单](WS23_WS24_VALIDATION_PLAN.md)。WS-23 优先补齐丢包恢复及无损 pause/resume 端到端验证；WS-24 继续映射来源审查、明示合成模型的多 NIC 实现与验证，再按原任务目标完成必要效果对照。WS-25 必须保留并跟踪这些执行项，不能以论文范围判断替代验证。性能 NO-GO 不取消正确性工作。

2026-09-30 WS-23/WS-24 阶段闭环并交接 WS-25，见 [Handoff 45](../handoffs/2026-09-30-45-ws23-ws24-closure-ws25.md)。WS-23 只完成修复、optimized build 与单测，端到端恢复仍待验证；WS-24 完成本地表示能力审计，多 rail 仿真 NO-GO。用户要求归档两个对话。WS-25 可据此开展本地证据与论文范围收束：先判断传输修复的端到端验证、多 NIC 模型及真实映射是否为论文主张必需，再决定另立补充任务；不默认追加仿真。

2026-09-30 WS-24 本地 host/NIC/placement 可表示性审计已完成：[审计报告](../research/ws24-multirail-representability-audit.md)、[静态机器收据](../research/evidence/ws24-multirail-static-audit.json)、[Handoff 44](../handoffs/2026-09-30-44-ws24-multirail-representability.md)。固定 OS1 拓扑四个互不连通组件、每组件 320 个单归属 host 端点；底层 `RdmaHw` 虽有多 NIC 容器，当前 scratch 却为各端点创建独立 Node/RDMA Hw 并使用单主机地址，trace 没有 job/rank/rail/physical host 字段。合成 sidecar 的四 rail 映射通过静态拒错测试，但不证明物理主机身份、模拟器多 NIC 正确性或真实 placement。**WS-24 remote simulation NO-GO**，未运行新实验。WS-23 仍仅固定修复 SHA `12dea54d421243ddb98c83437b929944ab6d128c` optimized build 与 `devices-point-to-point` 单测通过；无修复版端到端仿真，恢复正确性待验证，隔离性能实验 NO-GO。

2026-09-30 WS-23 本地修复阶段已完成 optimized build 与 `devices-point-to-point` 单测：[Handoff 43](../handoffs/2026-09-30-43-ws23-build-unit-ws24-topology-gate.md)。固定修复 SHA `12dea54d421243ddb98c83437b929944ab6d128c` 的隔离 build 成功；单测通过，但测试构建需在隔离副本临时修正仓库既有 `CommandLineTestCaseBase::Parse` const 问题，随后源码文件 SHA 恢复为原值。没有修复版仿真，故端到端传输正确性仍未验证；拥塞流隔离性能实验继续 NO-GO。WS-24 已进入本地多 rail 表示能力审计：OS1 拓扑静态图有四个互不连通组件，每个组件 320 个 rail 单归属端点；尚无同一物理服务器多 NIC/placement 的表示证据，暂不仿真。

2026-09-30 前序 WS-23/24 门槛审查均未开放效果实验，当时建议下一步进入 WS-25 本地证据与论文范围收束，见[Handoff 41](../handoffs/2026-09-30-41-ws23-ws24-gates-and-ws25.md)。该记录早于上方新启动的 WS-23 传输修复。WS-23 的 PFC=0 常规流量格没有触发 PFC，现有证据不能因果证明跨类阻塞；旧 IRN×PFC 双开压力格 13/16 完成且当时源码仍有超时恢复抑制。WS-24 当前流量生成器只选 rail 0，缺可核验的跨 rail 作业/流映射。WS-21 的心跳异常正确性、联合长尾通信代价和反馈选路采用证据列入 WS-25 必要性清单；先依据论文范围判断是否值得补充，未授权仿真。

2026-09-30 WS-22 本地重排机制审查 **NO-GO for remote simulation**：[Handoff 40](../handoffs/2026-09-30-40-ws22-reorder-budget-gate.md)。拓扑存在跨 ToR 上游多路径，但目的主机仅有一条最终出口；当前 ConWeaveVOQ 只处理受控相邻 phase 换路且没有字节预算，现有数据也不能逐 QP 还原乱序、NACK/超时/重传和接收占用。不能据此冻结重排预算实验。下一步 WS-23 只审查拥塞流隔离的既有前置证据；PFC=0 跨类阻塞尚未证明，旧 IRN×PFC 双开压力格 13/16 完成也不能当性能依据。WS-21 残余验证（单次丢失/异常 ACK/重启/真实断链、长尾 STATE+心跳联合成本、反馈实际采用/退回）列入 WS-25 逐项决定是否需要，不自动创建实验或与 WS-23 合并。

2026-09-30 WS-20/WS-21 交接闭环，并启动 WS-22 条件审查。WS-20 只完成 WS-19 反例复核，原确认性矩阵仍 NO-GO；WS-21 已完成 STATE 更新间隔技术矩阵和局部 HELLO/ACK 技术 pilot，但缓存尚未参与选路，效果矩阵仍 NO-GO。WS-22 当前仅开展重排预算与粒度的本地机制、可观测性和代价审查；需先证明可用路径机会，并能逐 QP 核验乱序、NACK/超时、接收占用及双侧完成率，才可冻结任何仿真协议。详情见[WS-20 反例报告](../research/ws20-counterexample-gate-review.md)、[WS-21 Handoff 36](../handoffs/2026-09-30-36-ws21-compact-interval-matrix.md)、[WS-21 Handoff 38](../handoffs/2026-09-30-38-ws21-local-heartbeat-pilot.md)和[WS-22 启动交接 Handoff 39](../handoffs/2026-09-30-39-ws22-reorder-budget-kickoff.md)。

2026-09-30 WS-21 局部 HELLO/ACK 小拓扑**技术 pilot 与 Sol 原始复核已完成**：[结果报告](../research/ws21-local-heartbeat-pilot-report.md)、[逐格机器摘要](../research/evidence/ws21-local-heartbeat-pilot.json)、[Handoff 38](../handoffs/2026-09-30-38-ws21-local-heartbeat-pilot.md)。固定仿真源码 `770b6b5617657832393bd721e0d634c6639405fb`；单测与六个仿真 ID 均终态并回传，六格各一条 67,108,864 B 流完整守恒，topology/trace Git 内容哈希一致。正常 50/200/1000 µs 格分别完成 112/28/6 次有效往返、产生 9,856/2,464/528 B 逐跳心跳通信；200 µs 的连续丢 HELLO 与丢 ACK 两格各注入 19 次、标 `UNKNOWN` 一次并恢复一次，实际从故障窗起点到标未知为 701.083 µs。Windows CRLF 拓扑工作副本 `445cf1e2…` 与固定 Git/远端 LF 快照 `dcca23ca…` 规范化后同内容。`UNKNOWN` 只监测，业务链路未断且选路未改，单份丢失/错误 ACK/重启/链路 up 及长尾联合成本仍待验证；**选路效果矩阵继续 NO-GO**，旧 STATE 间隔与其它正式 no-go 不重判。

2026-09-30 WS-21 v2 长尾反馈间隔技术矩阵及 Sol 复核已完成。固定仿真源码 `2c14d3b4c952a9cece89a9de14216709b604706f` 的 off/5/10/20/40 µs 五格均回传原始数据；关闭格基线指纹与旧版一致，四个开启格各 16,576/16,576 流完成、1,744,830,464 B 守恒，路径身份和资源收据通过。5 µs 格有 15/46,784 份报告按 10 µs 有效期过期并在缓存更新前丢弃；其它三档零过期。零过期且最大窗口末样本年龄严格 ≤20.000 µs 时，实测通信量最低的合格档是 10 µs（逐跳 6.452 MB）；若假设年龄上限 20.5 µs，20 µs 才成为该约束下最低成本档（4.535 MB）。20.5 µs 并非业务 SLO。缓存尚未参与路由决策，每格约 13,000–14,000 条流的完成时刻变化只能归为报文通信扰动，**反馈选路效果矩阵继续 NO-GO**。见[长尾间隔报告](../research/ws21-compact-longtail-interval-report.md)、[证据 JSON](../research/evidence/ws21-compact-longtail-interval-analysis.json)、[分析脚本](../../scripts/analyze_ws21_compact_interval_matrix.py)和[Handoff 36](../handoffs/2026-09-30-36-ws21-compact-interval-matrix.md)。该轮收束时局部 HELLO/ACK 尚未实现或测试；后续小拓扑试验见本文件顶部，缓存选路和效果矩阵仍未完成。

2026-09-29 WS-21 v2 已在 GPT-6 Sol High 完成固定 40 流开关 pair 的原始配对分析：[报告](../research/ws21-compact-40pair-sol-report.md)、[机器输出](../research/evidence/ws21-compact-40pair-sol-analysis.json)和[Handoff 35](../handoffs/2026-09-29-35-ws21-v2-sol-analysis.md)。同 SHA `91f43c70…` 的两格各 40/40、33,849,344 B、身份与资源门槛通过，逐流改善/变差/不变为 0/0/40；P50/P90/P99 均为 11.130/60.145/784.523 µs。开启格 223/223 报告送达，逐跳 26,760 B，相当于应用输入字节的 0.0791%（非链路利用率）；样本年龄最大 9.838 µs。同一 40 流输入的旧版 85 B/份与新版 60 B/份跨 SHA 技术对照，观察到逐跳字节少 29.4%，但不是选路收益。**条件性 GO：新源码 optimized 构建、单测及同 SHA 40 流回归通过后，才开放[长尾反馈间隔技术预飞行](../research/ws21-compact-longtail-interval-preflight.md)；下一阶段须实际切至 Luna High，先验证新源码，再复核远端资源/ID 后才运行。NO-GO：反馈选路效果矩阵。** 心跳仍未实现；旧 no-go 保持。

2026-09-29 WS-21 v2 Luna 实验阶段完成。固定源码 SHA `91f43c70bbb515ae35b3161d4d1e40d30ff90992`；优化构建与隔离单测通过。反馈关闭/开启 40 流格 `20260929-185200-ws21c-v2-off40` / `20260929-185300-ws21c-v2-on40` 均 `SUCCEEDED`，各 40/40 流、33,849,344 B 守恒、40 条跨 ToR QP 身份无误；两格 FCT 与 WS18 raw 哈希相同。开启格 223/223 份报告送达，拒收/过期/序号缺口均为 0，逐跳入/出队各 446，逐跳字节 26,760 B，运行峰值进程树 RSS 4,544.2 MiB。此 40 流格只证明报文链路可用且本次未观察到业务时序扰动；上游 CE 区分为 0、报告缓存没有参与选路，不能推出收益。详见[执行记录](../research/ws21-compact-40flow-preflight.md)、[机器核验收据](../research/evidence/ws21-compact-40pair-verification.json)和[Handoff 34](../handoffs/2026-09-29-34-ws21-v2-40flow-pair.md)。下一步应在符合工作流的 Sol High 分析会话中复核配对代价并决定是否追加长尾更新间隔格；局部心跳与选路采用仍未实现，历史 no-go 不变。

2026-09-29 WS-21 新增[精简协议与代价—收益契约](../research/ws21-compact-control-protocol-and-tradeoff-contract.md)：SGLB 的硬件质量更新、BGP 与 SyncMesh 不整体复刻；本项目只研究固定路由之上的候选状态报文及业务活跃 ToR 上联局部心跳。源码已把 51 B 反馈头改为 26 B 版本化报文，并让非空聚合窗口可配置为 1–60 µs；本地 `run.py` 语法检查与 `git diff --check` 通过。**新源码尚未远程编译、运行或产生新实验 ID；局部心跳、缓存选路接入与效果比较尚未实现。**旧长尾 pair 的 29,388 条报告、9,003,540 逐跳字节和 13,916 条流时序变化仍只归属旧 SHA，不能写成压缩收益。下一步先实际切换 Luna High，再按契约做隔离构建/单测和小规模正确性格；终态 raw 回传后切回 Sol High 分析。旧工程失败与效果 no-go 不追溯重判。

2026-09-29 WS-21 长尾真实反馈技术 pair 已运行，按[机器收据](../research/evidence/ws21-feedback-longtail-pair.json)与[Handoff 31](../handoffs/2026-09-29-31-ws21-longtail-feedback-pair.md)判为 **工程门槛未通过**。固定源码 `9964203cf6d3de4bc1061d61b6f959bcb537c120`，关闭/开启格 `20260929-170600-ws21-feedback-longtail` / `20260929-171900-ws21-feedback-longtail-on` 均 16,576/16,576 完成、1,744,830,464 B 守恒、身份无错；但 FCT 和 WS18 时序哈希不同，13,916 条流的逐流 FCT 有变化。开启格 29,388/29,388 报告送达，拒收/过期/逐跳拒绝/序号缺口为 0，最大年龄 8.357 µs，缓存峰值 227。运行中的峰值 RSS 未采集，故资源收据子项也不完整。此结果证明当前反馈报文能在长尾输入下通过共享队列抵达，同时会扰动应用时序；不代表候选路由或机制收益。遵守停止规则，不扩展仿真，效果矩阵与历史 no-go 不变。

2026-09-29 WS-21 真实反馈报文 40 流开关 pair 已按 `scripts/verify_ws21_feedback_pair.py` 复核通过，源码固定 `23e002e13aed71a05d6b098feb5fdab4ce7ac9f4`。关闭/开启格均 40/40 完成、33,849,344 B 守恒，FCT 与 WS18 raw SHA 相同；开启格 223/223 报告送达、拒收/过期/序号缺口为 0、逐跳入队出队各 446，缓存峰值 8。上游 CE 样本为 0，故只证明 40 流输入下的开关非扰动与反馈报文基本送达，不证明候选区分或性能收益。机器收据见[40 流反馈 pair](../research/evidence/ws21-feedback-40-pair.json)。完整技术 pilot 尚未完成，效果矩阵与旧 no-go 保持不变。

前序 WS-21 原型构建与序列化测试记录见[工程契约](../research/ws21-real-feedback-path-contract.md)、[Handoff 29](../handoffs/2026-09-29-29-ws21-feedback-wire-prototype.md)和[Handoff 30](../handoffs/2026-09-29-30-ws21-feedback-build-test.md)：源码 `3f1a28a6583567744b6a177d8c11da7cc8a761dc`、构建 ID `20260929-153553-ws21-feedback-wire`。该记录早于 40 流 pair；其“尚无仿真送达数据”是当时状态，后续以本文件顶部更新及原始收据为准。测试构建临时修正的一处无关 core 测试 const 错误已恢复。

2026-09-29 WS-21 长尾技术诊断 pair 完成：[机器摘要](../research/evidence/ws21-longtail-pair.json)、[配对分析器](../../scripts/analyze_ws21_longtail_pair.py)、[长尾 pair 契约](../research/ws21-long-tail-technical-pair-contract.md)和[Handoff 27](../handoffs/2026-09-29-27-ws21-long-tail-diagnostic-pair.md)记录源码 `478eca21b626113aa9dc58a33085b0d0a287f740` 的 `20260929-132600-ws21-tail-off` / `20260929-132700-ws21-tail-on`。两格均 16,576/16,576 完成、1,744,830,464 B 守恒；FCT/WS18 SHA 分别为 `964b7f75…` / `e12ab338…` 且逐字节一致。开启格 16,205 条跨 ToR QP 身份无错误，1,280 个端口共记录 7,035,136 个事件、raw 164,219,537 B、溢出 0；两格 QP 文本日志约 2.14 MB，最大进程 RSS 约 4.5 GiB。诊断看到 10,123 个上游 CE 包，但没有实现真实反馈报文或对照替代候选。两格是单输入技术诊断，不是效果比较；**完整技术 pilot 仍不就绪，WS-21 效果矩阵继续 NO-GO，历史 no-go 不变。**默认 FCT 分析器的 2.005–2.060 s 窗口排除了本 trace；专用摘要按全部 WS18 QP 时序统计。此前旧日志实现的 260 MB 诊断尝试因超过 50 MB 门槛而排除，详见 Handoff 27。

2026-09-29 WS-21 路径身份与 40 流出口事件技术子门槛通过：[pair 收据](../research/evidence/ws21-identity-port-pair.json)、[工程契约](../research/ws21-identity-diagnostic-contract.md)和[Handoff 25](../handoffs/2026-09-29-25-ws21-identity-port-pair.md)记录个人 fork 固定源码 `2a5e7e8722814befc259d1ddece814ed17cbfcbc` 的 `20260929-070000-ws21-proof-off` / `20260929-073000-ws21-proof-on`。40/40 流完成、33,849,344 B 守恒；开关 FCT/WS18 SHA 分别为 `0f8fd036…` / `bc7004a6…` 且逐字节相同；40/40 跨 ToR QP 源首口/目的反推首口一致。出口事件覆盖 1280 端口、138,080 条、3,303,220 B，溢出 0，峰值队列 308,456 B。技术收据同时发现并修复 optimized 模式中 NS_ASSERT 参数吞掉 tag 读取、map 插入和 fwrite 的问题；最短路映射跳过四个拓扑连通分量之间不可达的组合。此 pair 仅为 40 流技术验证；CE 样本为 0，未测 WS-19 长尾输入、CPU/内存峰值、QP 传输转折或真实反馈消息成本。**完整技术 pilot 仍未就绪，WS-21 效果矩阵继续 NO-GO；旧 WS-10/11/12/19/20 结论不变。**

2026-09-28 WS-21 后续路径身份子门槛：[工程契约](../research/ws21-identity-diagnostic-contract.md)、[Handoff 24](../handoffs/2026-09-28-24-ws21-identity-diagnostic-build.md)记录默认关闭的诊断源码 `382b6dfe98ff6da28aea9c737d56a55206ef344e` 已推送个人 fork，隔离构建 `20260928-232758-ws21-identity-build` 成功；源首口与目的实入口/反推首口及上游 CE 可按 QP 输出，映射冲突会使初始化失败。尚无同 SHA 开/关仿真或新 raw，完整尾部事件和真实反馈消息未实现；**只达到编译门槛，完整技术 pilot NOT READY，效果矩阵 NO-GO**。旧结论不变。

2026-09-28 WS-21 补充[设计复审](../research/ws21-feedback-design-review.md)、[六格静态预算](../research/evidence/ws21-static-budget.json)和[Handoff 23](../handoffs/2026-09-28-23-ws21-feedback-design-review.md)：原 64×1 µs 时间桶不足以覆盖 WS-19 旧格最长 13.29 ms 背景尾流；六格每流分别哈希两个候选，反馈 key 的静态下界约 3.1 千、上界约 12.1 千，全窗 10 µs 周期预算上界约 16.13 百万逻辑报告。拓扑最短路显示源首跳可由目的入端口静态反推，但当前源码未实现或逐 QP 校验。**首版技术 pilot 尚未就绪，效果矩阵继续 NO-GO。**仅继续本地路径身份、观测时长与真实反馈消息成本设计；本轮无远程实验或新效果数据。

2026-09-28 WS-21 **完成下游反馈本地可行性审查；效果矩阵 NO-GO**。[设计记录](../research/ws21-downstream-feedback-feasibility.md)及[Handoff 22](../handoffs/2026-09-28-22-ws21-downstream-feedback.md)从 `experiment/ws20-counterexample-review@cdb2d1b` 独立分支，核对 WS-19 固定 `b52e66f…` raw、WS-13/14 诊断和当前源码。源 ToR 可即时读取本地出口设备队列；目的主机唯一出口状态只在目的 ToR，本机制尚无可计延迟/开销的可靠下游反馈路径。提出每 QP 非扰动时序规格和本地/延迟反馈/oracle/ECMP 对照，但新观测与反馈都未实现或运行。下一步仅能先审查技术 pilot 设计；WS-22/23/24 保持各自条件，WS-25 只整合实际证据。WS-19/20 与旧正式 no-go 不变。

2026-09-28 WS-20 **完成本地反例审查，原确认性矩阵仍 NO-GO**。[反例报告](../research/ws20-counterexample-gate-review.md)、[逐流/逐跳机器记录](../research/evidence/ws20-counterexample-audit.json)、[条件性设计草案](../research/ws20-next-exploratory-design-v0.md)和[Handoff 21](../handoffs/2026-09-28-21-ws20-counterexample-review.md)从 WS-19 固定 `b52e66f…` 的 ToR/192 十二格原始计时与背景逐跳日志重新对齐。联合臂 24/24 轮慢于 ECMP，23/24 轮尾换流且尾流有准入等待；三 seed 背景 P99 全高于 ECMP，损害流与目的出口排队峰值同现但有反例，无法断言单一因果瓶颈。只做本地静态分析，未运行新仿真；新观测与可实现准入信号通过前不冻结探索效果小样。WS-19 的 19/30 方向筛失败、旧 WS-10/11/12 no-go 和缺失业务 SLO 均不变。

2026-09-28 WS-19 **完成 48/48 格探索性双侧小样并按事前规则 no-go，WS-20 保持关闭**。[结果报告](../research/ws19-admission-pilot-report.md)、[48 格机器摘要](../research/evidence/ws19-pilot-analysis.json)、[收据](../../results/ws19-pilot-receipts.jsonl)和[Handoff 20](../handoffs/2026-09-28-20-ws19-admission-pilot.md)记录固定仿真源码 `b52e66f0fbf786fb57672b12a5633cf45b9311c1`、三独立需求 seed、12 配对区组和 48 格 raw 逐格复核。诊断开/关 pilot 的 FCT 指纹相同，矩阵全流完成、守恒、无 PFC，资源门槛通过；ToR/192 联合臂的轮均 MoE 和背景 P99 三 seed 均劣于同输入 ECMP，预注册 30 项方向筛选有 19 项失败。主机热点的 MoE 改善不能替代背景与增量门槛。独立样本仅 n=3，研究性零损害筛不是业务 SLO；旧 WS-10/11/12 no-go 不变。

更新：2026-09-29（中国时间）。本文件是跨对话的**状态入口**，不是实验原始证据。状态会过期；执行代码、实验或对外陈述前，应核对当前 Git、源码、实验 ID 与原始数据。工作规则以 `docs/REMOTE_EXPERIMENT_WORKFLOW.md` 为准，baseline 和指标口径以 `docs/research/10-baseline-fidelity-and-dataflow-audit.md` 为准。

## 当前阶段与目标

阶段：**WS-10、WS-11 和 WS-12 多策略正式对照各自预注册复合判据 no-go；WS-13 诊断 pilot 完成；WS-14 GuardHash 单机制小样按事前规则停止；WS-15 门槛复核后确认性矩阵 no-go；WS-16 证据索引完成、论文范围待导师确认；WS-17 本地审计完成；WS-18 最小工程正确性通过；WS-19 探索性双侧小样完成且 no-go；WS-20 本地反例审查完成，原确认性矩阵关闭；WS-21 精简 STATE 传输、40 流回归与长尾更新间隔技术矩阵完成，局部心跳和缓存选路未实现、效果矩阵 no-go。**WS-10 固定总字节主 4 档仅 1/5 正向；WS-11 全量追加背景主 192 档虽 5/5 正交互，但原始背景 P99 +6.6527% 越过 5% 线。WS-12 的 120 格完成，四个新增策略全部复合 no-go。WS-13 目标 QP 未观察到 SACK，最慢背景流目的 ToR 出口出现微秒级排队并伴随 CNP，属于单 seed 相关性诊断。WS-14 七格 0/192 极端小样全完成；GuardHash 背景 P99 优于普通双候选，但 MoE 批次比普通双候选慢 0.552 µs、比 ECMP 慢 0.731 µs，且背景尾流转移，因此按停止规则不运行中档。WS-15 原始复核与候选筛选未找到合格新单机制，未运行新小样或正式格；这是门槛决定，不是性能零效应。暂无可核验业务 SLO，不新增通用安全线。详见 [WS-15 门槛复核](../research/ws15-independent-demand-gate-review.md)、[三场解释性证据](../research/ws12-ws10-ws11-negative-evidence.md)、[WS-13 合约与结果](../research/ws13-tail-diagnosis-and-experiment-contract.md)、[WS-14 pilot 报告](../research/ws14-guardhash-single-mechanism-pilot-report.md)。WS-09 GuardHash/HarmGate v0 仍是工程原型。

2026-09-28 WS-16 证据收束：在 `feature/ws16-paper-evidence` 从 WS-15 集成提交 `53b56b3d3f271356c98afdcad8779183a3fff528` 开工；[总报告](../research/ws16-paper-evidence-and-reproduction.md)、[216 ID 逐格索引](../research/evidence/ws16-experiment-index.csv)和[Handoff 17](../handoffs/2026-09-28-17-ws16-paper-evidence.md)已形成。索引直接核对元数据、trace/拓扑/FCT 原始哈希；本地正式 WS-10/11/12 与 WS-14、WS-13 校准核验通过。没有新仿真或新效果数据。开题报告的端侧分类/降级、INT/Δq、接收协同重排和硬件验证尚未完成；论文题目/创新点及业务 SLO 待导师确认。WS-13 压力 11 格实际 13/16，WS-15 确认性矩阵未运行，均不可写为正式效果。

2026-09-28 后续方向研究：[机制候选说明](../research/post-ws16-mechanism-directions.md)依据 WS-13/14 瓶颈和双侧代价，以及 ConWeave、ParaLet、SGLB、Proteus、FLB、TCCL 等原论文，提出发送准入与路径联合控制、下游反馈、重排预算、拥塞流隔离和多 rail/放置等可证伪问题。均是**提议，未运行新实验**；先审计瓶颈可控性和独立需求输入，旧 no-go 不变。

2026-09-28 新任务流建立时：按[WS-17 起机制计划](WS17_PLUS_PLAN.md)先启动 WS-17 审计；WS-18–20 是准入/路径联合主线的逐级门槛，WS-21–24 是条件分支，WS-25 负责证据收束。此计划形成时尚无新分支效果数据；WS-19 的后续实际结果以上方状态和[报告](../research/ws19-admission-pilot-report.md)为准。每个分支均须执行[静默远程实验、Luna High 半小时监督、Sol High 分析及自然语言交接准则](../REMOTE_EXPERIMENT_WORKFLOW.md#长时矩阵运行准则)。

2026-09-28 WS-17 本地审计闭环：个人 fork `feature/ws17-bottleneck-demand` 从已核验个人 `origin/research/post-ws16-mechanism-directions@5cf603abdec4ec3d37f400cae82b30eb6ec8751d` 分出。[审计](../research/ws17-bottleneck-demand-audit.md)、[三独立 seed、12 对静态 trace/sidecar 的哈希清单](../research/evidence/ws17-demand-manifest.json)与[Handoff 18](../handoffs/2026-09-28-18-ws17-bottleneck-demand.md)表明：固定目的主机只有唯一 400 Gbps 最终出口，跨 ToR 上游存在可分流最短路径；应用可控制放行时刻，但现有 FCT 不含放行前需求等待。WS-13 四格探针、六格独立需求校准和 WS-14 七格从旧原始 ID 重算通过；没有新仿真或效果数据。**WS-18 仅最小工程正确性 go；WS-19/20 效果矩阵 no-go，待三时刻计量、四臂和双侧完成率验证。**旧 WS-10/11/12 no-go、WS-14 停止规则均未重判。

2026-09-28 集成交接核验：WS-17 对话 `01a0e44f-d286-72f3-95ae-b4f93dfe38d0` 已完成且无未结用户请求；`feature/ws17-bottleneck-demand@47944fc117aaa9f202d4cd9b26cccb68feeba0de` 在集成前与个人 `origin` 同 SHA、工作树干净。`make_ws17_demand.py --verify` 再次核验 3 个 seed、12 对静态资产，manifest SHA 为 `0513d4b0f2cadea768220739fe8eadcd71e636f8ca763b9c6cf84fe233fead5a`；WS-13 反馈/校准及 WS-14 七格原始复核再次通过。此次基线与状态集成提交会移动分支 HEAD；其 SHA 不能误作仿真源码 SHA。WS-18 仅开放最小工程，尚未有新机制性能数据。

2026-09-28 WS-18 最小工程正确性闭环：首轮四臂 `d5555637…` 虽各完成 40/40、33,849,344 B，但输入 ID 36–39 各早 1 ns，作为失败诊断保留。修复仿真源码 `729d2682077fedc232c10b6eabccddc5168f8191` 在同一 trace/拓扑下顺序运行旧 `fecmp` 与四臂五格，均 `SUCCEEDED` 且 raw 回传；旧 FCT 与参考整文件哈希相同，四臂逐流需求、身份、三时刻、QP 起点、完成/字节/等待、路径与背景全部通过[完整校验](../research/evidence/ws18-correctness-summary.json)。每臂 40/40、33,849,344 B；准入/联合各 32 条正等待，路径/联合各 36 条路径流。详见[Handoff 19](../handoffs/2026-09-28-19-ws18-minimal-prototype.md)与[正确性契约](../research/ws18-correctness-contract.md)。这只是 40 流人为热点的技术验收；WS-19/20 效果矩阵仍需独立需求与双侧停止规则，当前关闭。

## 已完成且可核验

- 研究：完成开题报告梳理、相关工作矩阵、初轮 8 个 idea、混合场景 5 个子 idea 和 MixHash 启发的 4 个算法草案。`ANT项目经验` 已按截图聊天日期及只读仓库演化完成复盘；论文项目 `docs/research/12-screenshot-lessons-and-mechanism-selection.md`、`docs/research/evidence/moe-static-profile.json` 是当前流量画像与条件性机制筛选入口，交接见 [Handoff 07](../handoffs/2026-09-25-07-ant-project-experience.md) 和 [ADR-006](../decisions/ADR-006-conditional-guardhash-selection.md)。它们是静态分析和方案，不是性能证据。
- 代码来源：`conweave-project/conweave-ns3` 与 `maplerime/conweave-ns3` 只读；个人可写 fork 为 `LarryBUPT/conweave-ns3`。maplerime 的版本演化见论文项目 `docs/research/09-maplerime-conweave-fork-evolution-report.md`。
- 实验链路：本机提交并推送个人 fork → 远程固定 SHA 的独立源码副本中编译/运行 → 按实验 ID 保存原始结果 → 下载并在本机分析。`20260923-165542-smoke-fecmp` 已验证完整链路。
- baseline：ECMP、CONGA、LetFlow、ConWeave 在相同 trace、拓扑和公共配置下各完成一次最小运行。实验 ID 为 `20260923-180001-fidelity-fecmp` 至 `20260923-180004-fidelity-conweave`，源码 SHA 均为 `a8d2db5f057172ce89730b4f6344c531e34a9302`。核验记录见论文项目 `results/baseline_fidelity_20260923.json`；**不能用于性能排序**。
- 输入资产：个人 fork 的 `feature/mixed-flow-traces` 已迁入 maplerime 的四份六列 MoE/背景流文件、拓扑和生成脚本，逐文件哈希见 `docs/research/mixed-flow-trace-provenance.md`。未迁入 MixHash 选路或接收端机制。
- WS-06 输入兼容：个人 fork `feature/ws06-flow-tags` 支持显式选择版本化 `config/*.txt`、五/六列流记录（五列默认 `tag=0`）及工作负载 tag 到源 ToR 选路入口的可见通路。32 主机和导入 1280 拓扑的四流六列探测各完成 4/4；四种旧五列 baseline 在固定旧 trace 下各完成 19,388 条流，原始 FCT 文件哈希逐模式与 WS-05 相同。证据和实验 ID 见 [Handoff 06](../handoffs/2026-09-24-06-six-column-input-and-tags.md)；这是输入与回归核验，不是双轨或性能验证。
- WS-07 技术 pilot：`feature/ws07-dual-track-mixtax` 新增 `dualtrack` (`tag=2` UDP 数据逐包哈希，`tag=1/0` 流 ECMP)、按输入 tag 的完成率/FCT/合成批次统计、可重生 pilot/固定总字节设计样本及配对检查。32 主机按流单类 FCT 原始哈希与同 trace `fecmp` 完全相同；导入 1280 拓扑跨 ToR 四流均完成且逐包决策触及多下一跳。四格 256-MoE × 背景 0/64 单 seed pilot 均全数完成；固定源码 SHA `8c99e5407ef41d14a6b67fc7dad55aada273946a`，结果与限制见 [Handoff 08](../handoffs/2026-09-25-08-ws07-dual-track-mixtax.md) 和 [摘要](../research/ws07-pilot-summary.json)。旧 2.005s baseline 分析保持原样；固定总字节样本尚未运行。
- WS-08 前置诊断：从个人 fork 已推送 `4649fb1928160c603f7df9ffd6400c091116ab60` 分支开工。只加日志的 `20260925-210024-ws08-nack-diagnostic@c8ca6a601dd4380bae36233053b654307d61d292` 与 WS-07 packet0 原始 FCT SHA 相同，四个约 4 ms 尾流恰与四个 4,000,000 ns 超时对应，超时均剩最后 192 B 未确认。共享 PFC=0、IRN=1、DCQCN 契约的 32 主机单类/双类及 1280 跨 ToR 四流正确性通过；同 SHA `445593fbc07236e18983d233407265220d360521` 四格各类全数完成，MoE 批次 flow0/packet0/flow64/packet64 为 1.415/1.415/1.625/1.572 µs，背景 P99 flow64/packet64 均 688.41974 µs。详证见 [Handoff 09](../handoffs/2026-09-25-09-ws08-receiver-gate.md)、[诊断](../research/ws08-receiver-preflight.md) 与 [机器摘要](../research/ws08-irn-pilot-summary.json)。固定总字节样本仅静态验证；无五 seed 推断。
- WS-09 工程原型：从已推送 `c45d41d42157dd3589e37ebe1953c75a68d5b6c2` 建 `feature/ws09-guardhash-prototype`；`shortq2/guardhash/guardhashgate` 模式 `13/14/15` 共用双候选哈希，HarmGate 是类别评分激活门槛。固定 `7930168f7bb43afbe6cc87bd134d91d28667e8c1` 完成 32 主机单/双类、导入 1280 跨 ToR 四流、同源码旧 `fecmp/dualtrack` 退化回归和 320 流同 trace 三格单 seed pilot；全部原始队列计数守恒。三格 MoE 合成批次 1.421/1.415/1.49 µs，背景 P99 均 688.41974 µs，门控实际激活 39 次、退出 9 次；仅属技术 pilot。修复提交 `9c34945c79b44476166f2f1f4dc26f6b2f6163a0` 的独立丢包探针 `20260926-025616-ws09-drop-probe` 两类准入丢包合计 3,041,296 B、计数违规 0。十格详证见 [Handoff 10](../handoffs/2026-09-26-10-ws09-guardhash-prototype.md)、[冻结规格](../research/ws09-guardhash-v0-spec.md)、[机器摘要](../research/ws09-validation-summary.json)；不作效果结论。
- WS-10 正式现象复核：预注册 v1.1 固定五个 trace seed、0/2/4 背景档、`fecmp/dualtrack`、总提供 35,651,584 B、统一 `aa778ac523bc0319999395dd3cf8085b41e73a98`。资源 pilot 6/6、正式 30/30 完成；4 档交互 1 正 4 负，归一化中位数 −1.3947%，背景安全 10/10 通过，2 档五 seed 均正但非单调，故现象 no-go。一次 SSH 状态解析故障的诊断格被同 SHA/trace 正式重跑替换，两份 FCT SHA 相同；详见 [Handoff 11](../handoffs/2026-09-26-11-ws10-fixed-load-formal.md)、[报告](../research/ws10-fixed-load-formal-report.md)、[机器摘要](../research/ws10-fixed-load-formal-summary.json)。
- WS-11 全量输入正式现象验证：固定仿真源码 `208fcee4c541da9b24ed26792b32ae681a30977f`、16,384 条同步 MoE 与原始 0/64/128/192 背景输入，加四组确定性行顺序置换；40/40 正式格两类流全完成且原始文件与资源收据核验通过。主 192 档交互 5/5 正向、归一化中位数 +35.9057%，但原始组背景 P99 +6.6527% 超过 5% 安全线，复合门槛 no-go。置换组不是独立需求样本，背景增加也增加总字节。见 [Handoff 12](../handoffs/2026-09-27-12-ws11-full-moe-formal.md)、[报告](../research/ws11-full-moe-formal-report.md)、[机器摘要](../research/ws11-full-moe-formal-summary.json)。
- WS-12 多策略正式对照：固定仿真源码 `adae7956e3fc874d9237e62a6ea8e32b26d5def1`，同一全量 MoE 与追加背景输入下，五顺序组 × 四档 × 全流 ECMP/既有逐包哈希/RR/随机/自适应/DRILL 六模式共 120/120 格两类流全完成。旧 `fecmp/dualtrack` 40/40 FCT 哈希与 WS-11 一致。四个新增策略主 192 档相对哈希的批次中位缩短 16.116%/18.406%/21.056%/22.549%，但背景安全通过数仅 14/15、14/15、13/15、14/15，因此双侧判据均 no-go。见 [Handoff 13](../handoffs/2026-09-27-13-ws12-packet-strategies-formal.md)、[报告](../research/ws12-packet-strategies-formal-report.md)、[120 格摘要](../research/ws12-packet-strategies-formal-summary.json)。
- WS-13 诊断 pilot：源码观测修正提交 `a985798ef78a95f502cf8eb56982c6e3a3b1168d`；新版四格 `20260927-160000-ws13-feedback-{o-f,o-a,03-f,03-d}` 均 SUCCEEDED，FCT SHA 与 WS-12 对应格 4/4 完全一致。IRN 反馈语义复核为 0 个 SACK；CNP 事件数 751/881/500/580；最慢目标背景流在目的 ToR 出口观察到 3.14–3.99 µs 最大排队等待。原 `0xFD` 误标日志作废；逐格信息见 [机器分析](../research/evidence/ws13-feedback-probe-analysis.json)、[诊断报告](../research/ws13-tail-diagnosis-and-experiment-contract.md)及 [Handoff 14](../handoffs/2026-09-27-14-ws13-feedback-probes.md)。这是单 seed 相关证据，不作因果或安全结论。
- WS-14 GuardHash 研究 pilot：固定仿真 SHA `73401ce3ac0a5c27bf0e3e0636c9337056d9355e`，七格 `20260927-233000-ws14-{0-q,0-g,192-f,192-h,192-q,192-d,192-g}` 均完整；0 背景 GuardHash/shortq2 FCT SHA 相同。192 档 GuardHash 的 MoE 批次 19.651 µs，高于 ECMP 的 18.920 µs 与普通双候选的 19.099 µs；背景 P99 1431.183 µs，优于普通双候选 1552.660 µs，但背景尾流转移且目的出口等待未一致下降，触发停止规则。逐格原始数据重算见[分析 JSON](../research/evidence/ws14-small-analysis.json)、[报告](../research/ws14-guardhash-single-mechanism-pilot-report.md)及 [Handoff 15](../handoffs/2026-09-28-15-ws14-guardhash-single-mechanism-pilot.md)。单输入描述性 pilot，不支持因果、业务安全或普遍效果。
- WS-13 IRN×PFC 四格扩展 pilot：同一仿真源码 `babd1b90d7c027cd09ac8c7d67380511a92883a6` 的 256 MoE+64 背景四格均 320/320 完成，但 PFC pause/resume 全为 0，00/01 与 10/11 各自 FCT SHA 相同，不能据此估计 PFC 动态效果。另用 16×1 MiB incast/1 MiB buffer 压力输入验证 PFC 触发：00/01/10 均 16/16，11 仅 13/16；11 缺失的流 ID 13/14/15 与三次 IRN+PFC 超时抑制日志逐一对应。定向丢包探针 `20260927-223000-irnpfcdrop-11@7af917a` 的 FCT 与旧 11 格逐字节相同，记录 161 次数据包出口准入拒绝；三条未完成流在各自未确认序号均有先前丢包，证实丢包后超时恢复被跳过的具体链路。旧 worker 曾把非空 FCT 的 11 格记为 `SUCCEEDED`，后续 factorial pilot 已新增完成数门禁；原始元数据不改写。详见[逐格报告](../research/ws13-irn-pfc-factorial-pilot-report.md)与[常规](../research/evidence/ws13-irn-pfc-factorial-pilot.json)/[压力](../research/evidence/ws13-irn-pfc-factorial-stress.json)/[丢包](../research/evidence/ws13-irn-pfc-drop-probe.json)收据。两组均为单输入技术 pilot，不重判旧 no-go。

## 当前版本快照

2026-09-28 WS-15 独立闭环核验：来源任务 `01a0e3c8-49d4-7053-9060-9360c34dfcc3` 已结束；集成前个人 fork `feature/ws15-gate-review` 本地与 origin 同为 `f7c5a2c5098f50948337c9a6ed7bcac7a316fdb6`，工作树干净。重跑 WS-14 七格原始核验通过，分析 JSON SHA-256 `dbce7a845c8e18bd4f4ef95b6164ba2bfa8d54adf7fefd20ae2731ade07dacda` 未变；重跑 WS-13 三条独立需求六格校准，`complete=true` 且摘要哈希未变。本次无新远程实验，门槛 no-go 只阻止确认性矩阵启动，不代表新机制性能零效应。WS-15 在复核与交接范围内可归档；WS-16 承接论文负结果与复现收束。本集成提交只移动文档 HEAD。

2026-09-28 WS-15 门槛复核：从 `feature/ws14-single-mechanism@a12519938c81ce9ee35683975c86f0f39f8f7340` 建 `feature/ws15-gate-review`，本地/个人 origin 起点相同。重跑 WS-14 七格原始核验和分析，JSON SHA-256 `dbce7a845c8e18bd4f4ef95b6164ba2bfa8d54adf7fefd20ae2731ade07dacda` 未变；重跑 WS-13 三条独立需求六格校准成功。筛选结论与重开条件见[报告](../research/ws15-independent-demand-gate-review.md)及[Handoff 16](../handoffs/2026-09-28-16-ws15-gate-review.md)。本次只做本地分析与文档，无新远程仿真，正式矩阵关闭；提交后须再查 Git SHA。

2026-09-28 WS-14 独立闭环核验：来源任务 `01a0e380-6362-71f0-a95b-9b14d8ce8765` 已结束；集成前 `feature/ws14-single-mechanism` 本地与 origin 同为 `735e0b3c3ea7f13d0797f802eef9bbf698e6971a`，工作树干净。`scripts/run_ws14_small.py verify` 从实验 ID 原始目录核验 7/7 格通过；`scripts/analyze_ws14_small.py` 重生的机器摘要 SHA-256 与提交版完全相同（`dbce7a845c8e18bd4f4ef95b6164ba2bfa8d54adf7fefd20ae2731ade07dacda`）。192 档 GuardHash 相对 ECMP 的 MoE 批次慢 0.731 µs，触发事前停止规则；WS-14 在极端小样范围内可归档。用户要求启动 WS-15 对话，先复核新机制理由与门槛；正式确认性矩阵仍关闭。仿真源码 SHA `73401ce3ac0a5c27bf0e3e0636c9337056d9355e` 不随本次文档提交改变。

2026-09-27 WS-13 独立闭环核验：来源任务 `01a0e1ac-fe55-7a91-a2de-205722db854b` 已结束；集成前个人 fork `feature/ws13-tail-diagnosis` 本地与 origin 同为 `62f25d15fd1123586a0edbdeeb48fb0ba96e88a0`，工作树干净。重新从八个原始格及丢包探针运行分析器：常规 IRN×PFC 四格全完成且 PFC 零事件；压力 11 格仅 13/16 完成、三次超时抑制；定向复跑 FCT 逐字节相同，161 次出口准入丢包，三条缺失流的未确认序号此前有丢包。Handoff 14 补入真实任务 ID 与本阶段结果；本次只集成文档，仿真 SHA 与原始结果不改。WS-13 可按诊断和技术 pilot 范围归档；WS-14 只作为事前限定的研究性单机制小样启动，不能据此声称正式效果或业务安全。

2026-09-27 WS-12 独立交接核验：来源任务 ID `01a0def1-82cd-7941-89a2-759e0072d8ef` 已结束；集成前个人 fork `feature/ws12-packet-strategies` 本地、origin 与 GitHub 均为 `2c1fea5eeb4a20c404b9b6d949b1e7d7169e03c1`，工作树干净。重新运行 `scripts/verify_ws12_formal.py` 从 120 格原始结果及资源收据得到 `complete=true`、旧 `fecmp/dualtrack` FCT 哈希 40/40 匹配，RR/随机/自适应/DRILL 均 `two_sided_acceptable=false`。仿真源码固定 `adae7956e3fc874d9237e62a6ea8e32b26d5def1`；本集成提交只移动文档 HEAD。WS-12 正式对照及解释性提纲可闭环归档。WS-13 起遵照[后续计划](WS13_PLUS_PLAN.md)先诊断长尾、核对成熟方案评价口径与基线波动，再论证新限制指标。


2026-09-27 WS-12 解释性收尾核验：更新前个人 fork `feature/ws12-packet-strategies` 本地与 `origin/feature/ws12-packet-strategies` 同为 `12b06ff`、工作树干净；独立重跑 WS-10/11/12 三份正式核验脚本，返回码均为 0。WS-12 输出 `complete=true`、120 格、旧模式 FCT 哈希 40/40 匹配，四个新模式 `two_sided_acceptable=false`。三场[解释性证据提纲](../research/ws12-ws10-ws11-negative-evidence.md)和本状态提交会移动文档 HEAD，但不改变三场固定仿真源码 SHA 或原始结果。正式矩阵及 WS-12 解释性整理均无待补项。

2026-09-27 WS-12 集成核验：个人 fork `feature/ws12-packet-strategies` 在集成前为 `afee268e3eb0e5c7ab9347366944ca1210d98c72`；120 格仿真源码统一 `adae7956e3fc874d9237e62a6ea8e32b26d5def1`。独立重跑 `scripts/verify_ws12_formal.py` 从原始结果与资源收据重算，返回码 0，`complete=true`、`formal_cell_count=120`、旧模式 FCT 哈希 40/40 匹配，四个新增策略 `two_sided_acceptable=false`。报告/状态提交后须重新查询本地和 origin HEAD；文档 HEAD 不等于仿真 SHA。正式矩阵无待补格，解释性整合仍可继续。

2026-09-27 WS-11 独立交接核验：来源任务 ID `01a0de18-0f20-7201-ab7c-0a6c92c1b727` 已结束；集成前本地、origin、GitHub 的 `feature/ws11-full-moe-mixtax` 同为 `ef9c190fa119be8a8ca9ba4321a44c02d1dbc39f`，工作树干净。重新执行 `scripts/verify_ws11_formal.py` 读取 40 格原始结果与资源收据，返回码 0，输出 `positive_groups=5`、中位数 `35.90568060021436%`、`background_safety_all_pass=false`、`phenomenon_go=false`。正式仿真源码仍固定 `208fcee4c541da9b24ed26792b32ae681a30977f`；新状态提交不会改变实验归属。WS-11 按预注册现象与资源并发范围可闭环归档，条件性机制效果未启动。WS-12 承接既定多逐包策略加 ECMP 对照及解释性负结果路线。

2026-09-27 WS-11 集成前核验：个人 fork `feature/ws11-full-moe-mixtax` 当时本地 HEAD 为 `91a8f6e8b7cf013217f661ddc9fab535ea015352`；40 格仿真源码统一为 `208fcee4c541da9b24ed26792b32ae681a30977f`，后续控制器和状态提交不是仿真 SHA。`scripts/verify_ws11_formal.py` 从逐格原始结果、trace、拓扑和资源收据重算 `phenomenon_go=false`。20 物理核/40 逻辑线程的服务器上，运行器使用 18 个共享 CPU 令牌（每次 `-j2` 编译占 2、单格仿真占 1），峰值采样 1 分钟负载 17.24；没有在途仿真。缺资源采样收据的旧 ID `20260926-144756-ws11-02-b192-f` 排除，用 `20260927-002500-ws11-02-b192-f-r` 同 SHA/trace/seed 重跑，原始 FCT SHA 相同。状态集成提交会移动 HEAD，执行时重新查询。

2026-09-26 WS-10 独立集成核验：来源任务 ID `01a0da7c-8d4d-7522-b1c9-1bfb967bd170`；个人 fork `feature/ws10-fixed-load-mixtax` 的实验源码固定 `aa778ac523bc0319999395dd3cf8085b41e73a98`。`scripts/verify_ws10_formal.py` 再次从正式 30 格的元数据、原始文件哈希、目标/类别完成率和资源收据重算通过，`phenomenon_go=false`。集成前本地、origin、GitHub 同名分支均为 `6cc47c6cffa3d00f7cb3ec71411c68844f57ff76`、工作树干净。状态提交会移动分支 HEAD，不能把新 HEAD 误作仿真源码 SHA。WS-11 的全量验证已规划，效果主张仍为条件性 no-go。

2026-09-26 WS-09 交接集成核验：`scripts/verify_ws09_prototype.py` 重新读取十个终态 ID 的元数据与原始结果，逐项通过；重生的 `docs/research/ws09-validation-summary.json` 与已提交文件 SHA-256 相同。个人 fork 本地与 `origin/feature/ws09-guardhash-prototype` 在集成前同为 `6a32df51d67b84b0a1f416e8b0c669946af15401`、工作树干净；其最后一提交只新增术语问答和状态入口。Handoff 10 已补真实 WS-09 任务 ID。集成提交会移动 HEAD。工程范围闭环，`queue_reject/queued_drop` 动态覆盖和正式类别增量仍留待后续。

2026-09-26 WS-09 集成核验：个人 fork `feature/ws09-guardhash-prototype` 机制/压力探针提交 `9c34945c79b44476166f2f1f4dc26f6b2f6163a0` 已推送；本 Handoff/状态集成提交会移动 HEAD，执行时重新查询。`scripts/verify_ws09_prototype.py` 对十个终态 ID 的元数据、trace/拓扑哈希、FCT 行数、逐端口守恒与三格共同输入重算通过。九个常规格固定 `7930168f`；修复版丢包压力格固定 `9c34945`。WS-09 工程范围完成；正式机制效果仍 no-go，WS-10/11 待独立执行。

2026-09-26 WS-08 集成核验：个人 fork `feature/ws08-guardhash-gate` 本地与 `origin` 同为 `653250a5381bb1992a4d8acececb62593cf343aa`、工作树干净。四格正式结果均 `SUCCEEDED`、固定 `445593fbc07236e18983d233407265220d360521`、PFC=0/IRN=1；四组 trace/FCT SHA-256 逐格与记录相符，FCT 行数 256/256/320/320，原始 OoO CNP 0/0/0/1516，PFC 行数均为 0。诊断复跑 FCT 与 WS-07 packet0 逐字节相同，日志含 601 RX NACK、571 TX NACK、四个末段 TX TIMEOUT。Handoff 09 已补真实任务 ID。集成提交会移动 HEAD。WS-08 的技术范围闭环，正式跨 seed 现象仍未解决；WS-09 是根据用户新指示的工程原型工作流。

2026-09-25 WS-08 诊断观察：个人 fork `feature/ws08-guardhash-gate` 的实验代码/运行器固定在 `445593fbc07236e18983d233407265220d360521`；本状态和 Handoff 的集成提交将移动 HEAD，须再次查询。四格原始结果 `20260925-211439-ws08-irn-flow0`、`20260925-210820-ws08-irn-packet0`、`20260925-212042-ws08-irn-flow64`、`20260925-212745-ws08-irn-packet64` 均 `SUCCEEDED`、PFC=0、IRN=1、共同 trace/seed，配对脚本通过。单 seed 交互未达预设方向与幅度，GuardHash 当前不启动。32 主机/跨 ToR 的小规模正确性 ID 见 Handoff 09。固定总字节 0/2/4 与五 seed 未运行。

2026-09-25 WS-07 集成核验：四格正式结果目录的 `metadata.json` 均为 `SUCCEEDED` 和固定源码 `8c99e5407ef41d14a6b67fc7dad55aada273946a`；trace 与原始 FCT 哈希逐格核对无误，FCT 行数 256/256/320/320，原始 OoO CNP 计数 0/601/0/733，PFC 行数均为 0。Handoff 08 已补真实 WS-07 任务 ID。WS-07 按最小双轨和单 seed pilot 范围闭环，4 ms 尾部定位、共同接收契约和正式多 seed 主实验转入后续门槛工作；这不改变 GuardHash 的条件性状态。核验前个人 fork 本地、`origin` 同为 `2b30d11c1efa42afa22a632a4789789cc3937526`，工作树干净；提交后重新查询 HEAD。

2026-09-25 WS-07 交接观察：个人 fork 新分支 `feature/ws07-dual-track-mixtax` 的四格 pilot 固定在 `8c99e54`，0/64 trace SHA 分别为 `d60ca03e…7560`、`cbfa0e5a…8e1`；原始结果在 `results/<实验ID>/` 及远程同 ID 目录。交接/集成提交会移动分支 HEAD，执行时重新查询。四份导入完整 MoE trace 仍未全量仿真；WS-07 的固定总字节设计样本只有静态验证。

2026-09-24 WS-06 交接核验：`feature/ws06-flow-tags` 的输入兼容代码与资产固定在 `dba99face4b026443220e4b73e655a86aecc1aca`；九段 Handoff 已在 `267af27e445f03ee62fb46f8bf30267da780f0ab` 提交并推送到个人 fork。该分支从 `feature/mixed-flow-traces@30734578e7468a8cf156588de0aded5f96095e43` 分出。集成提交会继续移动分支指针，**执行时必须重新查询 HEAD**。`main@236a801a00e35de9078635e04acae2f701c21ded`；旧 `feature/remote-experiment-workflow` 本地 `f46abb3`、GitHub `a8d2db5` 的分支指针差异仍在。WS-06 实验各有固定 SHA 的独立远程源码副本；不据此推断远程代码缓存或既存工作树的当前状态。

2026-09-25 ANT 交接核验前，`feature/ws06-flow-tags` 本地与个人 fork `origin` 同为 `0a8d28ce89e8886b597e220cc3ff308523dc3c28`、工作树干净；本次状态集成将继续移动分支指针。论文项目根目录未纳入 Git；画像脚本重跑后 JSON SHA-256 不变。没有因研究筛选而修改算法代码或运行新的远程实验。

论文项目根目录 `E:\研\毕业论文` 本身**不是 Git 仓库**。本状态文件及 Handoff、ADR、项目 Skill 因而放在个人 fork 内，避免“项目记忆”只存在于未版本化目录。

## 正在推进、未完成及依赖

1. **公共输入底座与最小双轨，已完成技术核验：**六列/五列解析、显式流文件、tag 到源 ToR、独立 MoE 分组分析和 `dualtrack` 均可用；32 主机单类及双类、导入 1280 拓扑跨 ToR 四流已全数完成。四份完整 MoE trace 已在 WS-11 全量运行，结果按 WS-11 独立契约解释。
2. **共同接收/重传语义，技术诊断已完成：**旧 PFC+非 IRN 的四个 4 ms 尾流对应四个末段 RTO；共享 IRN+无 PFC 契约在一个 seed 的 0/64 四格全部完成且无超时。它是新的传输条件，不能与 WS-07 旧四格合并。若在导入混合延迟拓扑比较 ConWeave，仍须先审计其统一 `one_hop_delay`。
3. **正式现象实验，两种契约分别完成：**WS-10 的固定总字节 0/2/4、五个独立 trace seed 与 30 格主 4 档结果为 1/5 正向、中位数 `−1.3947%`；WS-11 的完整 MoE、随背景增加总字节的 40 格主 192 档为 5/5 正向、中位数 `+35.9057%`，但背景安全 14/15，原始 192 档越过 5% 线。两个预注册复合判据分别 no-go，不合并统计、不后改门槛。
4. **算法工程与效果分离：**WS-09 的 GuardHash 和 HarmGate 门控研究原型已实现，正确性、队列守恒与技术 pilot 按范围完成；目前没有机制收益或类别信号增量证据。`queue_reject/queued_drop` 未动态覆盖，压力格只证明 MMU 准入丢包可守恒。WS-10/11 均未打开正式效果比较门槛，见 [ADR-007](../decisions/ADR-007-guardhash-prototype-before-efficacy.md)。
5. **全量阶段与资源准则：**WS-11 已按预注册完成资源 pilot、并发隔离审计与 40 格矩阵；20 物理核预算下的 18 共享 CPU 令牌和阶梯并发实测可用。原始输入随背景增加总字节，不能称纯混合比例效应，也不能与 WS-10 固定总字节场景合并。未来远程矩阵仍按[工作流](../REMOTE_EXPERIMENT_WORKFLOW.md)先核对空闲资源和隔离，再按实测占用提高并发并静默监控。

WS-19 闭环复核（2026-09-28）：WS-18 的最小工程正确性与 WS-19 的探索性双侧小样均有独立 Handoff，并已集成到本分支状态台账。对 48 个 WS-19 原始格串行重跑逐格校验，48/48 通过；诊断开/关 FCT、三时刻哈希一致。逐格校验器改为流式读取大型 `config.log`，避免整份日志占用内存；分析摘要仍为原有固定 raw 哈希和结论。WS-19 结论保持：ToR/192 联合臂在三 seed 的 MoE 轮均和背景 P99 均未过事前方向门槛，30 项筛选中 19 项失败。按用户要求启动 WS-20，但限定为反例复核、可证伪机制/观测修订和重开门槛设计；**WS-19 原计划的确认性矩阵仍 no-go，当前 WS-20 不运行远程仿真**。若形成有独立依据的新候选，再另立新的事前双侧探索契约；之后是否确认性验证须依据成熟方案或业务证据论证独立需求数、同输入强对照和限制指标。WS-14 的目的出口排队/CNP 仍只是相关观测，IRN×PFC 压力 11 格仍有未完成流。暂无可核验业务 SLO，不创建通用安全百分比。WS-10/11/12 no-go 保持原样。详见[WS-19 报告](../research/ws19-admission-pilot-report.md)、[Handoff 20](../handoffs/2026-09-28-20-ws19-admission-pilot.md)、[WORKSTREAMS](WORKSTREAMS.md)与[ROADMAP](ROADMAP.md)。

后续场景口径（用户 2026-09-27 明确决定）：**保持同一批 MoE 业务流不变，逐档追加背景流，总提供字节随之增加**；不再为这条路线构造“背景增加但总字节不变”的替换式输入。每档各算法仍用相同流量配对，跨档结果解释为新增背景及相应负载的共同影响，不称纯混合比例效应。既有 WS-10 固定总字节结果作为历史独立契约保留，不重判。详见 [ADR-008](../decisions/ADR-008-additive-background-workload.md)。

## 证据边界

用户提问的术语解释与后续追加入口见 [TERM-QA 术语提问合集](../TERMINOLOGY_QA.md)；术语定义不替代本节的实验原始证据。

- 最小运行证明路径和分析链路可工作，不证明论文性能优势；ConWeave VOQ 不是 MMU 物理队列，低负载运行未触发 PFC。
- 流量生成器未单独播种；ns-3 的 `RANDOM_SEED` 不能代替 trace seed。跨算法比较须复用不可变 trace 并记录哈希。
- 仅有 NS-3 仿真条件；不能声称已完成 SmartNIC、交换芯片、真实 RNIC 或生产集群验证。

## 本次整合的来源

前五份 [Handoff](../handoffs/) 从早期对话及落地文件整理；[Handoff 06](../handoffs/2026-09-24-06-six-column-input-and-tags.md) 为 WS-06 输入底座，[Handoff 07](../handoffs/2026-09-25-07-ant-project-experience.md) 为研究筛选，[Handoff 08](../handoffs/2026-09-25-08-ws07-dual-track-mixtax.md) 为 WS-07 技术 pilot。冲突与旧文档漂移见 [CONFLICTS.md](CONFLICTS.md)。本文件由集成工作流维护；原对话用于追溯理由，不作为实时状态数据库。

[Handoff 09](../handoffs/2026-09-25-09-ws08-receiver-gate.md) 记录 WS-08 前置诊断、共同 IRN 四格的负向单 seed pilot 和当前机制 no-go；该结论不改写 WS-07 旧传输条件下的原始结果。

[Handoff 10](../handoffs/2026-09-26-10-ws09-guardhash-prototype.md) 记录 WS-09 可关闭原型、十个实验 ID 的正确性/守恒与单 seed 技术 pilot；它不改变 WS-08 效果 no-go，也不替代 WS-10/11 的正式证据门槛。

[Handoff 11](../handoffs/2026-09-26-11-ws10-fixed-load-formal.md) 记录 WS-10 预注册五 seed 正式复核、一次控制器恢复和现象 no-go；所有正式格与原始 SHA 索引在 [机器摘要](../research/ws10-fixed-load-formal-summary.json)。

[Handoff 12](../handoffs/2026-09-27-12-ws11-full-moe-formal.md) 记录 WS-11 全量输入 40 格、资源并发验证和复合 no-go；逐格原始 SHA 与资源收据索引在 [机器摘要](../research/ws11-full-moe-formal-summary.json)。

[Handoff 13](../handoffs/2026-09-27-13-ws12-packet-strategies-formal.md) 记录 WS-12 六策略 120 格全量配对、资源恢复、四策略复合 no-go；逐格原始 SHA、指标与收据索引在 [机器摘要](../research/ws12-packet-strategies-formal-summary.json)。

[Handoff 14](../handoffs/2026-09-27-14-ws13-feedback-probes.md) 记录 WS-13 的 IRN `0xFD` ACK/SACK 语义修正、四格同输入反馈/目的出口探针、FCT 哈希回归与 SLO 缺口；逐流及逐跳机器摘要见 [探针分析](../research/evidence/ws13-feedback-probe-analysis.json)。它是单 seed 诊断，不打开 WS-14 效果门槛。
