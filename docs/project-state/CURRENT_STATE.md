# ConWeave 毕业论文项目状态

2026-09-28 WS-19 **完成 48/48 格探索性双侧小样并按事前规则 no-go，WS-20 保持关闭**。[结果报告](../research/ws19-admission-pilot-report.md)、[48 格机器摘要](../research/evidence/ws19-pilot-analysis.json)、[收据](../../results/ws19-pilot-receipts.jsonl)和[Handoff 20](../handoffs/2026-09-28-20-ws19-admission-pilot.md)记录固定仿真源码 `b52e66f0fbf786fb57672b12a5633cf45b9311c1`、三独立需求 seed、12 配对区组和 48 格 raw 逐格复核。诊断开/关 pilot 的 FCT 指纹相同，矩阵全流完成、守恒、无 PFC，资源门槛通过；ToR/192 联合臂的轮均 MoE 和背景 P99 三 seed 均劣于同输入 ECMP，预注册 30 项方向筛选有 19 项失败。主机热点的 MoE 改善不能替代背景与增量门槛。独立样本仅 n=3，研究性零损害筛不是业务 SLO；旧 WS-10/11/12 no-go 不变。

更新：2026-09-28（中国时间）。本文件是跨对话的**状态入口**，不是实验原始证据。状态会过期；执行代码、实验或对外陈述前，应核对当前 Git、源码、实验 ID 与原始数据。工作规则以 `docs/REMOTE_EXPERIMENT_WORKFLOW.md` 为准，baseline 和指标口径以 `docs/research/10-baseline-fidelity-and-dataflow-audit.md` 为准。

## 当前阶段与目标

阶段：**WS-10、WS-11 和 WS-12 多策略正式对照各自预注册复合判据 no-go；WS-13 诊断 pilot 完成；WS-14 GuardHash 单机制小样按事前规则停止；WS-15 门槛复核后确认性矩阵 no-go；WS-16 证据索引完成、论文范围待导师确认；WS-17 本地审计完成；WS-18 最小工程正确性通过；WS-19 探索性双侧小样完成且 no-go；WS-20 关闭。**WS-10 固定总字节主 4 档仅 1/5 正向；WS-11 全量追加背景主 192 档虽 5/5 正交互，但原始背景 P99 +6.6527% 越过 5% 线。WS-12 的 120 格完成，四个新增策略全部复合 no-go。WS-13 目标 QP 未观察到 SACK，最慢背景流目的 ToR 出口出现微秒级排队并伴随 CNP，属于单 seed 相关性诊断。WS-14 七格 0/192 极端小样全完成；GuardHash 背景 P99 优于普通双候选，但 MoE 批次比普通双候选慢 0.552 µs、比 ECMP 慢 0.731 µs，且背景尾流转移，因此按停止规则不运行中档。WS-15 原始复核与候选筛选未找到合格新单机制，未运行新小样或正式格；这是门槛决定，不是性能零效应。暂无可核验业务 SLO，不新增通用安全线。详见 [WS-15 门槛复核](../research/ws15-independent-demand-gate-review.md)、[三场解释性证据](../research/ws12-ws10-ws11-negative-evidence.md)、[WS-13 合约与结果](../research/ws13-tail-diagnosis-and-experiment-contract.md)、[WS-14 pilot 报告](../research/ws14-guardhash-single-mechanism-pilot-report.md)。WS-09 GuardHash/HarmGate v0 仍是工程原型。

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
