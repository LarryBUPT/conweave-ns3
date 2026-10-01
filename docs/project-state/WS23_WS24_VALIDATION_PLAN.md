# WS-23/24 必做验证执行清单

2026-09-30 用户纠正提前闭环。两个对话恢复执行，必须持续实验、修改、验证，完成全部预设任务后才能闭环。负结果必须经相应预设验证支持；不能通过跳过验证获得 no-go 结论。

## WS-23：先完成传输恢复正确性

执行对话：`01a0f15f-58c7-7532-84bd-9acaaaa14525`。依据[恢复契约](../research/ws23-irn-pfc-recovery-contract.md)及[下一批预飞行](../research/ws23-next-correctness-and-causal-preflight.md)。2026-10-01 状态：**COMPLETE FOR PRESET SYNTHETIC CORRECTNESS AND ISOLATION EXPLORATION; ISOLATION EFFICACY NO-GO**。最终两格仿真源码 `70bf890d1ceba58c5ebd26b17e492295b34c99ca` 的 optimized build、`devices-point-to-point` 单测和端到端两格已通过；其证据等级为固定输入技术正确性。18 格探索矩阵的负结论见[全量报告](../research/ws23-isolation-matrix-r3-report.md)。

- [x] 冻结两格源码 SHA、输入/拓扑哈希、seed、独立 ID、资源停止条件、真实源端 pause/resume 与逐格验收器；见[运行前 Handoff 47](../handoffs/2026-09-30-47-ws23-two-cell-preflight.md)。
- [x] 旧 16×1 MiB 反例在 `20260930-201600-ws23-loss-recovery` 及资源补验 `20260930-213100-ws23-loss-recovery-r2` 均 16/16、两类各 8/8、16 个唯一 QP、序号/字节守恒；161 次真实准入丢包后有 3 次超时恢复，均不在源 PG 暂停期。两次 FCT SHA 相同。该两格均**未发生延期事件**，故只满足“若发生则为正时长”的条件检查，不代表延期分支端到端覆盖。
- [x] 无损暂停 `20260930-201500-ws23-lossless-pause` 实际源端 pause/resume 跨 1.8 ms，1/1 完成、QP payload=size，无数据/ACK 丢失、误重传或暂停期恢复；此格没有超时延期事件。
- [x] 两格及压力资源补验的终态 raw、配置快照和资源收据已回传并复核。[机器证据](../research/evidence/ws23-two-cell-correctness-20261001.json)记录无损格 175 点、进程树峰值 811.590 MiB；压力首格观察器启动过晚，仅一个终态零值采样，不作峰值；补验预先启动，运行 PID 有 10 个正 RSS 采样、峰值 204.012 MiB。失败或无效收据均保留，未覆盖旧 ID。
- [x] 下一批本地执行入口已补齐：一条命令在每格构建后启动独立资源观察器并等待 `READY`，终态核验正 RSS/资源阈值；跨类诊断关/开可在背景两格后先配对拒收，再决定是否进入混合格。延期探针首格已用旧方案执行并按失败保留；四格跨类观测格仍未运行，见[Handoff 49](../handoffs/2026-10-01-49-ws23-next-batch-local-readiness.md)和[Handoff 50](../handoffs/2026-10-01-50-ws23-deferral-probe-diagnosis.md)。
- [x] v2 端到端动态延期在固定 SHA `94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1` 上完成 control/probe 两格：control `20261001-151000-ws23-rto-v2-control-r2` 与 probe `20261001-151100-ws23-rto-v2-probe-r2` 均 16/16。control 重现 161 次准入丢包、源 14 的 36 次丢包和固定 FCT SHA；probe 的丢包前缀与 control 逐行一致、门控触发时有未确认数据、pause/resume 抵达源端，1599 次刷新、4 次暂停期延期、1 次恢复宽限延期，完整 320 µs RTO 后恢复，所有 16 QP 序号/字节守恒。两验收脚本均通过，资源收据正且在阈值内；实际 GPT-6 Sol High 已独立复核两份 raw，并修正机器证据中一处主日志哈希抄写错误。数据见[结果报告](../research/ws23-deferral-v2-correctness-report.md)、[机器证据](../research/evidence/ws23-deferral-v2-20261001.json)和[Handoff 55](../handoffs/2026-10-01-55-ws23-v2-sol-review-and-release.md)。此项仅为固定合成输入正确性验证。
- [x] 原拥塞隔离目标的因果前置：固定背景与新增竞争流的 PFC=0 同输入四格已实测共同可改道出口、等待、物理出口占用与背景完成影响；诊断开/关两组 FCT 字节一致。固定源码 `154f537ec345df75fbb404a1674436535f92735b`，四格 `20261001-091000-ws23-bg-off`、`20261001-091100-ws23-bg-on`、`20261001-091200-ws23-mix-off`、`20261001-091300-ws23-mix-on` 均通过总验收，见[机器结果](../research/evidence/ws23-crossclass-20261001.json)。该结论仅适用于本次合成输入。
- [x] 四格 raw 已在本轮独立复核：直接读取四个 ID 的原始快照、FCT、出口和资源样本，复算背景 FCT `708.695→1650.085 µs`、ToR 32 出口 5 活动区间重叠、等待和 MMU 占用；与原机器验收一致。见[独立复核](../research/ws23-crossclass-sol-raw-review.md)及[收据](../research/evidence/ws23-crossclass-sol-raw-audit-20261001.json)。
- [x] 隔离候选与同输入 ECMP/shortq2 的双侧探索协议、三组事前合成需求、输入哈希和停止条件已写定，见[协议及 v2/v3 执行修订](../research/ws23-isolation-paired-pilot-prereg-v1.md)与[需求清单](../research/evidence/ws23-isolation-demand-manifest.json)。v1 源码 `e263579…` 的四格已运行并保留 raw：ECMP pair 通过，`shortq2` 开诊断格缺跨类观测，六格门槛失败，后两格与 18 格均未启动。修复源码 `eff40ea…` 的 v2 ECMP 两格有效；v2 `shortq2` 两格因漏传冻结的 factorial 诊断参数而缺完成数元数据，保留为失败并停止扩格。revision 3 将以新固定提交和六个新 ID 使用正确参数重新运行完整预飞行；`guardhash` v2 两格未启动。修复观测覆盖的 C++ 源码已远端构建并通过首格单测，后续预飞行仍待验收，见[Handoff 58](../handoffs/2026-10-01-58-ws23-isolation-diagnostic-coverage.md)及本次后续交接。
- [x] revision 3 六格预飞行在 `b3d8d30826dd4550f5667d4cab2a3b4004c3cf22` 下通过：六格各 4/4，诊断配对 FCT 相同且资源收据有效。原 18 格矩阵前三个 seed 2301 背景格 1/1；第四个混合 ECMP 格因输入时间倒序报 `FLOW_INPUT_ERROR line 3`，立即停止。失败 ID/raw 和已构建未运行 ID 保留，旧背景格不并入新 SHA。详见[矩阵第二版修订](../research/ws23-isolation-paired-pilot-prereg-v1.md#矩阵第二版修正输入行序并重新冻结完整-18-格)。
- [x] 修复生成器输出顺序并逐条核对：三份背景输入字节不变，三份混合输入只改变行序，流身份、tag、字节和到达时间完全相同；新输入单调、无重复。旧/新哈希及可重算证据见[排序审计](../research/evidence/ws23-isolation-reorder-audit.json)。新矩阵全部 18 格使用新固定 SHA 和全新 ID，旧验收编号保留。
- [x] 新排序混合输入 ECMP 解析门槛在 `3db2685a3540895bf49e25302bd00465bc0921e2` 的 `20261001-200003-ws23-s2301-mix-fecmp` 通过：4/4，输入/拓扑快照哈希匹配，解析错误为零，FCT 行与 payload 完整，资源收据正且在阈值内；见[机器收据](../research/evidence/ws23-isolation-parse-gate.json)。该格是完整 18 格中的一格，不是隔离效果比较。
- [x] 新 SHA 下解析门槛与 seed 2301 的三个背景格共 4/18 有效：背景三模式 FCT SHA 均为 `458b8f12f8460a6b21f49ee4db3157148124b6700f9f07353afdacbacd31f65c`，资源收据通过。混合 `shortq2` 格 4/4 但有一条 0 RSS 启动样本，被冻结的逐样本资源验收拒收，raw 保留且不计有效格。观察器修订与替换 ID 见[revision 3](../research/ws23-isolation-paired-pilot-prereg-v1.md#revision-3资源观察器启动瞬间的零-rss-样本恢复)。
- [x] 新编号 `20261001-201000-ws23-s2301-mix-shortq2-r` 通过，其他 17 个有效逻辑格同 SHA 完成；revision 3 全矩阵原始验收 18/18。逐 seed 背景干扰、三条竞争流 FCT、最大值和类别决策触发均已计算，见[报告](../research/ws23-isolation-matrix-r3-report.md)与[机器摘要](../research/evidence/ws23-isolation-matrix-r3-summary.json)。旧 `200004` 和旧 SHA/倒序输入不计入。
- [x] 三组事前独立合成需求已全部报告；双侧正向条件未过：2301/2302 类别未改变选路，2303 背景改善但最慢竞争流受损。适用范围限定为同一小拓扑/负载家族的合成探索，缺真实业务输入与 SLO，不能声称生产隔离收益。负结果和 raw 保留，原门槛未改。
- [x] 最终源码 SHA、18 个有效 ID、原始数据、资源收据、报告与结论已逐项核对。WS-23 按原预设的合成正确性与隔离探索范围收束；真实业务和统计确认主张均未成立，也不由本次任务代做。

## WS-24：补齐模型、输入与多网卡验证

执行对话：`01a0f1da-f1e2-7870-9361-24b4d626fd76`。依据[表示能力审计](../research/ws24-multirail-representability-audit.md)、[冻结协议](../research/ws24-followup-validation-protocols.md)、[Handoff 50](../handoffs/2026-10-01-50-ws24-frozen-validation.md)及[14 格原始验收摘要](../research/evidence/ws24-followup-validation-summary.json)。固定仿真源码 `b1184d6a7bd38577b235b7f119f920973308774f`。2026-10-01 状态：**14 格冻结合成验证完成，WS-24 任务仍 ACTIVE**；原清单要求的单测没有找到可核验收据，真实物理映射和跨独立需求确认性效果也没有验证。

- [x] 已追查导入图/生成器来源；它可追至合成生成器，但无可信真实 host/NIC/job 放置资料，不能从相邻节点号推断物理共享。[审计](../research/ws24-multirail-representability-audit.md)
- [x] 已建立标明合成身份、资源共享假设与适用范围的 host/NIC/rail/job/rank/流映射；真实部署主张仍需真实来源。[协议](../research/ws24-followup-validation-protocols.md)
- [x] 已实现一台合成 host 对应四 NIC/独立 IP；最小正例与跨 rail 拒错负例核验身份、双向 QP/ACK、字节和返回路径。新固定 SHA 的旧五列/六列四 baseline 八格、320-host 目标图格与动态 CNP 格均通过：旧五列四算法 FCT 与历史锚点逐字节一致；目标图 10/10、2,408,448 B；CNP 格 4/4、4,194,304 B，flag/源端接收/真实降速各 7。[最小格](../research/ws24-minimal-multinic-preflight.md)、[14 格摘要](../research/evidence/ws24-followup-validation-summary.json)
- [ ] 本地结构检查、隔离构建和最小端到端正确性已有证据；后续固定 SHA 的每格独立 optimized 构建、输入/拓扑快照、完成/字节/身份与资源收据均通过逐格和矩阵验收。但原清单明确要求的**单测通过收据尚未找到**；须由 WS-24 在隔离源码副本运行对应单测或提供已有原始收据，再完成此项。[Handoff 50](../handoffs/2026-10-01-50-ws24-frozen-validation.md)
- [x] 已按原多 rail/placement 目标执行固定逻辑需求与总字节的单/多 rail × 固定/可变放置四臂合成 pilot，各 10/10、2,408,448 B。multi−single 完成跨度差在固定/可变放置为 −173/−164 ns，只有一个合成 seed，仅作描述，不称普遍性能收益。[机器摘要](../research/evidence/ws24-followup-validation-summary.json)
- [x] 冻结 A/B/C/D 14/14 终态 raw 与资源收据已回传，独立重跑 `verify_ws24_matrix.py` 得到与提交摘要相同的结果；最终仿真 SHA、输入和本范围结论对应。真实物理映射和独立需求的确认性性能结论仍缺证据；提出此类主张前须另取得来源并预先固定验证协议，不把本次合成 pilot 代替它们。
- [ ] WS-24 任务闭环前补齐上一项单测收据，并再次核对全部预设项与原始证据。Handoff 50 的“冻结 14 格范围完成”只覆盖实验批次，不代替任务闭环。

## 执行协调与 WS-25

WS-23 的本地分析和修改在独立副本 `workspace/ws23-execution-70bf890`；WS-24 的冻结 14 格已在 `workspace/ws24-multinic-validation` 完成，没有本批在途作业。WS-23 新批次仍须由 Integration 协调共享入口，现场核对远端 worker 版本、在途作业、ID 与资源后按固定 SHA/输入运行；不以过去的空闲收据代替现场检查。

每次仿真前先冻结协议与收据并停在模型切换边界，监督对话实际切至 Luna High，再执行后台静默实验，约半小时精简监督；终态 raw 回传后实际切回 Sol High 分析和必要修正。不得用文字宣称模型切换。

WS-25 负责证据总账、必要主张和论文说明，必须跟踪本表完成状态及具体执行对话；它不能替代实验验收，也不能默默把必做验证变成可选事项。先前 Handoff 45 的闭环与归档决定已撤销；历史工程证据仍保留。
