# WS-25：第一课题类别感知包流混合负载均衡执行清单

状态：ACTIVE，2026-10-03。依据：[ADR-010](../decisions/ADR-010-sequential-mixed-lb-paper-plan.md)、[Handoff 55](../handoffs/2026-10-02-55-ws23-ws24-final-integration.md)及[远程实验工作流](../REMOTE_EXPERIMENT_WORKFLOW.md)。用户本轮明确将旧 WS-25 的“本地证据与论文范围收束”改为**第一课题实现、验证与小论文成稿**；旧 WS-21 状态反馈余项保留在第二课题门槛，不与本课题并行。当前修正版校准遇到一次输入快照身份错误：r1 两个 ID 因 SHA 未含新 trace 在 ns-3 启动前失败，已保留且不解释为机制失败；r2 新 ID 与修正后 SHA 已冻结，详见[校准协议](../research/ws25-v1fix-independent-calibration-protocol.md)和[Handoff 63](../handoffs/2026-10-03-63-ws25-calibration-r1-input-source-mismatch.md)。

## 研究问题与边界

在 WS-11/12 现有 16,384 条 MoE 流加 0/64/128/192 条背景流的分布、主拓扑及相同传输条件下，提出可证伪的**类别感知选路**，检验逐包侧和逐流侧能否同时获得可信收益。只用远程服务器 ns-3；允许同分布新独立需求 seed，不增加流量类型或档位。WS-23/24 是旁证，不能充作本机制的收益。2026-11-02 前争取完成独立验证与小论文成稿，投稿随后进行；投稿前不启动状态反馈第二课题。

## 必做项及验收

| 阶段 | 交付与通过条件 |
| --- | --- |
| 1. 证据与机制 | 从 WS-11/12/13/19/20 的固定 SHA、raw、报告及开题背景审计双侧瓶颈，写出一个具体的类别感知机制假说、可实现信号、可控路径、预期失败模式和候选版本台账。不得把历史 NO-GO 改写为收益。 |
| 2. 同条件基线 | 在固定原始基线 SHA 所定义的 ECMP、DRILL、CONGA、LetFlow、ConWeave 五模式上逐项审查主拓扑、trace、类别标签、传输及观测的兼容性；每个可运行模式须以相同输入通过构建、最小端到端正确性、完成率和字节守恒。障碍需给源码/失败 ID 与修复重验；不能静默删基线。 |
| 3. 候选实现 | 在独立 checkout 实现类别感知机制和必要的非扰动观测；固定源码 SHA，以独立 ID 验证单类/混合、回退、路径选择、完成率、字节守恒和旧模式回归。构建/单测/最小运行不算效果验收。 |
| 4. 事前设计 | 将需求 seed 预先分为筛选、校准 pilot 和未见过的最终验证三组；同 seed 配对所有臂，行顺序置换不当独立样本。192 为主档，0/64/128 预设约束。明确 MoE 合成批次完成时间、背景 P99 FCT 的计算窗口及缺失/未完成流处理；背景吞吐、链路利用率与不均衡、上游排队、路径选择、乱序/重传作解释证据。缺失观测先补，不能填零。 |
| 5. Pilot 与冻结 | 独立 pilot 估计波动、可检测效应和运行资源；在最终矩阵前冻结双侧数值判据、其他档位约束、样本量、比较/统计方法、停止条件、源码 SHA、拓扑/trace 内容哈希、seed、全部实验 ID 与资源预算。未满足此门槛不得运行正式矩阵。 |
| 6. 正式验证 | 在现场无其他作业、隔离与资源 pilot 通过后，按冻结协议执行五基线与候选的必要配对格，使用实测吞吐安全批量调度；每格保留 raw、metadata、哈希与资源收据。失败保留原 ID，停止扩格，诊断修复后用新 SHA/ID 重验。 |
| 7. 分析及成稿 | 从 raw 逐格复核，报告全部档位、失败格与双侧主结果，并用解释指标核对机制因果链及局限；可过预设门槛才写正向结论。形成可复现清单、图表和小论文初稿。投稿作为后续里程碑单独记录。 |

## 当前执行检查点（2026-10-03）

- 机制与兼容审计、修正版实现和 11 格正确性/fallback 验收已完成；raw 重验 11/11。mixed8 correctness 没有触发 CONGA/LetFlow flowlet timeout 或 ConWeave reroute/VOQ，不能据此声称这些动态路径已覆盖。
- 独立校准 r1 的两格因构建 SHA `c84108b24c94a5068861e5bb090c5aa387245ee1` 不含 seed07 trace，在 ns-3 启动前失败。两个失败 ID、metadata 与日志保留，详见 [Handoff 63](../handoffs/2026-10-03-63-ws25-calibration-r1-input-source-mismatch.md)；该输入打包错误不计作机制版本效果失败，也不复用 r1 ID。
- r2 已冻结输入快照 SHA `a656104d05c681f9b3a998b5ef4ce3e644558d02`、四个 trace SHA、拓扑 SHA、28 个全新唯一 ID、cap=2 及逐格远端 trace SHA 预检。版本化清单为 [r2 计划](../research/evidence/ws25-v1fix-calibration-plan-r2.json)，校准定义见[协议](../research/ws25-v1fix-independent-calibration-protocol.md)。提交推送后执行 28 格；它们仍是校准，不作正式收益或 NO-GO 判断。

## 迭代和闭环

第一课题最多三个**新的**候选版本，每版最多一次诊断修正；每次修正登记新 SHA、实验 ID 与失败原因。达到上限仍未通过事前双侧门槛，停止并如实形成 NO-GO 复盘与不能成立的主张，不改线、不无上限调参。WS-25 不因阶段 Handoff、build、pilot 或单个效果 NO-GO 提前闭环。其范围完成须逐项核对本清单、raw、资源收据、源码与结论，或依迭代上限形成有边界的负结果并交付成稿决策。小论文投稿后，才由后续任务启动第二课题的状态反馈研究；WS-21 的单次故障、联合成本和 adopted/fallback 缺口届时按主张重新审查。

## 分工与模型边界

WS-25 副对话在独立 checkout 执行机制、实验及成稿，主对话负责定时监督与项目集成。设计、诊断、终态 raw 分析使用实际 GPT-6 Sol High；协议/SHA/输入哈希/ID/资源/停止线全部冻结并停在远程运行前时，由主对话防重并实际切 GPT-6 Luna High 授权后台仿真；约半小时精简监督、正常静默。终态 raw 回传后再实际切 Sol High 逐项复核。远程共享 worker 前检查无在途作业，不并发修改共享 checkout。

## 2026-10-02 本任务进度账本

执行分支 `feature/ws25-first-paper` 从集成起点 `75092e1f6aa73766b236b2d4e3faa0bcc95f8a46` 建于独立 Git worktree。桌面端 managed worktree 工具因任务当前目录不是 Git 仓库而拒绝创建/附加；本分支未改共享 checkout。实际 Git SHA、源码、输入与实验 raw 仍须逐阶段复核。[v1 本地审计与预飞行协议](../research/ws25-classreserve-audit-and-preflight.md)记录当前证据和执行边界。

| 原预设项 | 当前核验 | 仍须完成 |
| --- | --- | --- |
| 1 证据与机制 | WS-11 40/40、WS-12 120/120 从既有 raw 重跑；ClassReserve v1 假说、可观测信号、失败预测和 1/3 候选台账已写 | 补 WS-13/19/20 逐格因果指标的定向复核；机制效果须待新 raw |
| 2 五模式同条件 | C1 `1d876a0` 的 ECMP、DRILL、CONGA、LetFlow 八流格 4/4 通过；ConWeave 在配置阶段因未识别 OS1 拓扑失败（ID `20261002-220004-ws25-pre-conweave`），raw 无流记录，日志与资源终态已保留。已在 C2 `bb10309261b7c5be350fcaab75b4fdb8db95ddca` 补兼容分支 | 按协议用 C2 新 ID 重跑六臂八流 correctness；修复后的 ConWeave 端到端格及 ClassReserve 尚未验证 |
| 3 候选实现 | C1 源码 `1d876a03629dcc0834e001d02e891957608a9f6c` 的类别队列守恒和选择计数已写；Python 语法、CLI 白名单、输入生成回归与 Git 差异检查通过；ConWeave 参数映射修复已提交为 C2 | C2 远程六臂优化构建、正确性、旧模式回归、非扰动观测和全量完成率 |
| 4 事前设计 | 筛选/校准/未见最终 seed 池及共同指标口径已分离；校准 seed 01 四档及八流 trace 已定 | 生成后续独立输入、补缺失观测并冻结正式比较/缺失处理细节 |
| 5 Pilot 与冻结 | C1 四个通过格、一格配置失败和一格未启动已逐项记录；因代码修复，原 C1 ID 不复用。C2 SHA、参数和 12 个新 ID 已写入预飞行协议 | 完成 C2 六格 correctness 后执行独立校准 pilot，再冻结双侧数值、样本量、最终全部 ID/哈希/SHA |
| 6 正式验证 | 未启动 | 先通过所有前置门槛，再执行独立最终 seed 矩阵、保留失败 raw 与资源收据 |
| 7 分析及成稿 | 未启动 | 逐格 raw/双侧/反例分析、图表、可复现清单和小论文初稿 |

2026-10-02 C2 兼容修订与暂停：C1 ConWeave 配置阶段失败原因已定位为 OS1 拓扑未进入 `run.py` 的 ConWeave IRN 参数分支；失败 ID、日志和资源摘要保留。C2 源码固定为 `bb10309261b7c5be350fcaab75b4fdb8db95ddca`，只增加该拓扑条件，重新冻结 v2 12 ID。C2 ECMP、DRILL 两个 correctness 格已 8/8 完成、类别字节守恒、资源收据和逐格验证通过；主对话要求在 DRILL 终态后暂停，服务器无在途仿真。详见 [Handoff 57](../handoffs/2026-10-02-57-ws25-first-paper-c2-preflight-stop.md)。

2026-10-03 calibration 完成并按用户要求暂停：C2 六格 correctness 与六格 192 档 calibration 全部通过；correctness 为 8/8，pilot 为 16,576/16,576，类别字节守恒、ClassReserve `queue_violations=0`、metadata/raw/config.log/resource 收据齐全。pilot 资源峰值 RSS `4562.08 MiB`、最低可用内存 `114.109 GiB`、最低可用盘 `5550.915 GiB`；服务器无在途仿真。已进入分析阶段，暂不运行分析器、冻结正式判据或启动最终矩阵。详见 [Handoff 58](../handoffs/2026-10-03-58-ws25-first-paper-analysis-pause.md)。

2026-10-03 最新用户指令已解除上述暂停：WS-25 实验—分析按自动化流程继续，人工仅参与问询与方向纠偏；只在主对话实际切换 Luna High / Sol High 的边界等待模型生效，切换后自动继续。C2 十二格重新核验 12/12；seed01 六臂校准分析见[报告](../research/ws25-calibration-seed01-analysis.md)与[机器摘要](../research/evidence/ws25-calibration-seed01.json)。单需求的 ClassReserve MoE 批次 19.442 µs，五基线为 15.026–19.313 µs，不能当正式结论。新增校准 seed02–04 的 192 档六臂共 18 格已按[协议](../research/ws25-independent-calibration-v3-protocol.md)冻结，固定仿真源码 `04a5277e8ed464229ef88d28a5d810271ae378fb`、独立 ID/输入哈希和资源停止线；尚未远程执行。当前在远程执行前模型边界，主对话实际切 Luna High 后即运行，不需额外人工确认。详见 [Handoff 59](../handoffs/2026-10-03-59-ws25-calibration-analysis-and-v3-handoff.md)。

2026-10-03 v3 校准运行终态：固定仿真 SHA `04a5277e8ed464229ef88d28a5d810271ae378fb` 的 seed02–04 × 六模式 **18/18** 终态格回传并由逐格 verifier 与整批 verifier 复核通过；18 个 ID 全部 SUCCEEDED、每格 16,576/16,576 完成、无失败。树 RSS 峰值最大 `4562.0625 MiB`，最低可用内存 `105.2149 GiB`、最低空闲盘 `5538.1300 GiB`；终态现场 load 0.07、active ns-3 PIDs/workers 均为空。逐格 FCT/raw/资源收据在本地忽略目录 `results/<ID>/`，批次收据 `results/ws25-calibration-v3-receipts.jsonl`。尚未做性能分析；当前停在终态数据分析模型边界，等待主对话实际切回 Sol High 后自动分析。详见 [Handoff 60](../handoffs/2026-10-03-60-ws25-calibration-v3-complete.md)。

2026-10-03 四独立需求分析：C2 seed01 六格和 C3 seed02–04 十八格共 24/24 从 raw 重新核验通过，每格 16,576/16,576 完成。ClassReserve v1 的 MoE 批次相对 ECMP、DRILL、LetFlow、ConWeave 均为 0/4 更快，相对 CONGA 为 1/4；五基线的配对变化中位数分别为 +6.289%、+28.501%、+10.549%、+7.016%、+2.547%（正值表示更慢）。背景 P99 相对 DRILL 4/4 更好，其他基线不稳定。详见[分析报告](../research/ws25-four-seed-calibration-analysis.md)及[机器证据](../research/evidence/ws25-four-seed-calibration.json)。v1 当前选路规则不进入正式效果矩阵；这只是 pilot 筛选，不是正式 NO-GO，也不取消 WS-25 的单类/混合/回退及动态分支正确性、观测、其他档位约束、最终验证和成稿验收。下一步先补默认关闭的非扰动诊断并做同输入开/关指纹核对，再按候选版本台账决定 v1 一次修正或 v2。

2026-10-03 D1 诊断终态与分析：默认关闭的逐 QP/背景出口排队观测在源码 `b13369d3f086189b693a1c8d875cfe7e3171181e` 下完成四格同输入开关 pilot；全部 SUCCEEDED、每格 16,576/16,576 完成，`scripts/verify_ws25_d1.py` 整批返回 4/4。ClassReserve 开关 FCT SHA 完全一致 `367a14e9…47f780b4`，DRILL 开关完全一致 `a156f990…502d0d5e`；资源停止线和原始数据完整。首次 D1 ID `20261003-150000-ws25-d1-classreserve-off` 的构建失败已作为失败证据保留，未复用。逐 QP raw 显示 ClassReserve 的 MoE 接收端乱序包 8,324、重复发送包 8,023，而 DRILL 为 1,675 和 1,761；背景流则 ClassReserve 两项均 0、DRILL 为 7,667 和 16,782。该单 seed 诊断与四 seed pilot 同向显示背景尾部改善伴随 MoE 乱序反馈及批次慢化，但不构成因果确认或正式效果判决。详见 [D1 分析报告](../research/ws25-d1-diagnostic-analysis.md)及[机器摘要](../research/evidence/ws25-d1-diagnostic.json)。按有限候选台账，v1 不进入正式矩阵，使用其唯一一次修正额度改为每条 MoE flow 在每个交换机首次双选后固定复用端口；修正后重新完成旧模式回归、单类/混合/回退正确性及独立校准，正式矩阵仍关闭。WS-25 全部预设验收保持 ACTIVE。

2026-10-03 ClassReserve v1 唯一诊断修正已在源码 `c84108b24c94a5068861e5bb090c5aa387245ee1` 实现：每个 MoE flow 在每台交换机按原分数双选一次并缓存，后续同流包固定复用；背景逻辑不变，新增流选择/缓存复用和未分类回退计数。五类正确性 trace 已固定哈希，并冻结 11 格同 SHA correctness 预飞行，见[修正协议](../research/ws25-classreserve-v1-correction-protocol.md)。当前待远程编译并实际切 Luna High 后运行；之前候选及所有既有 raw 保持不变，不把新版本小样计入正式效果，WS-25 仍 ACTIVE。

2026-10-03 预飞行门槛：修正版首格 optimized build `20261003-180005-ws25-v1fix-pre-classreserve` 已 `BUILT`；固定输入生成器复跑五个哈希全部一致。现场 load `0.12`、active simulation PIDs 为空、可用内存 `122.98 GiB`、空闲盘 `5534.2 GiB`。首格正确性仿真仍未启动；主对话实际切 Luna High 后由[执行器](../../scripts/run_ws25_v1fix_correctness.py)自动先 cap=1 运行首格，验收通过后 cap=2 分批执行其余十格，任一格失败即停止扩格。

2026-10-03 ClassReserve v1 修正版 correctness 终态：固定仿真 SHA `c84108b24c94a5068861e5bb090c5aa387245ee1` 的 11 格全部完成；六模式 mixed8、候选背景/MoE 单类、显式 tag0、旧五列 fallback 与 seed01 b192 均由逐格及整批 verifier 检查通过（11/11）。b192 最初因 verifier 将 trace SHA 误写为 `979100…be647f` 而被拒绝；协议和实际 raw 均为 `979100…b02f48`。仅修复 verifier 常量后，原实验 ID/raw 单格及整批复验成功，未重跑或覆盖数据。最大树 RSS `4562.13 MiB`，最低可用内存 `114.098 GiB`、最低空闲盘 `5527.07 GiB`；远端空闲审计通过。此批只验正确性，不作效果判断。详见 [Handoff 61](../handoffs/2026-10-03-61-ws25-v1fix-correctness-complete.md)。下一步转终态 raw 分析，等主对话实际切 Sol High 后自动继续。

2026-10-03 修正版 raw 分析与下一校准冻结：六模式 mixed8 均 8/8 完成；候选单类各 4/4，tag0 与旧五列格式各 8/8 并触发 100,740 次包级 fallback；seed01 b192 为 16,576/16,576，`queue_violations=0`、队列入出相等且无 drop/current。候选 b192 日志有 25,598 次 MoE 双选、9,551 次改选，背景固定路径缓存新建/复用 884/7,414,992。与旧 v1 同 seed raw 相比，修正版的 OoO CNP 为 0（旧 12,809）；MoE batch 和背景 P99 分别 16.286/2083.638 µs（旧 19.442/2118.305 µs）。这是单需求修正诊断，不是独立效果证据。mixed8 的 CONGA/LetFlow timeout 及 ConWeave reroute/VOQ flush 均为 0，动态分支覆盖仍不足。报告见[correctness 分析](../research/ws25-v1fix-correctness-analysis.md)。已生成新独立需求 seed05–08 的 0/64/128/192 trace 并冻结哈希；第一阶段 192 档 24 个六臂配对主格 + 每 seed 一格 diag=1 控制，共 28 个固定 ID，均用 SHA `c84108b…`、cap=2。协议、机器计划、manifest 与执行器分别见[协议](../research/ws25-v1fix-independent-calibration-protocol.md)、[计划 JSON](../research/evidence/ws25-v1fix-calibration-plan.json)、[输入 manifest](../research/evidence/ws25-v1fix-calibration-inputs.json)、[`run_ws25_v1fix_calibration.py`](../../scripts/run_ws25_v1fix_calibration.py)。校准未远程运行；最终需求池 20262521–44 未读取。下一步等待主对话实际切 Luna High 后启动校准，终态再回 Sol 分析。

此处是阶段账本，WS-25 保持 ACTIVE；构建或最小 pilot 成功不能转为闭环。WS-21 反馈/心跳余项继续在第二课题门槛，不与本课题并行。
