# Handoff 77：WS-25 第一课题预设实验与初稿验收

日期：2026-10-07。来源：WS-25 第一课题副对话；交由主对话做项目状态集成与实际模型边界管理。本文件不自动归档对话、不投稿，也不启动第二课题。

## 1. 本对话目标

按[执行清单](../project-state/WS25_FIRST_PAPER_EXECUTION.md)完成类别感知选路的预设证据审计、五基线与候选正确性、独立设计/校准、冻结 576 格正式矩阵、raw 与资源验收、双侧分析、反例/局限、复现图表和小论文初稿；长时运行按原 ID 防重恢复。用户要求第一课题最多三个新候选、每版至多一次诊断修正；第二课题投稿后才启动。

## 2. 已确认的项目事实

- 个人 fork 工作分支 `feature/ws25-first-paper`；固定 v1 正式仿真/输入 SHA `ce699dffe2845dc83e2171a1c309c6d96b96d2b3`，拓扑 SHA `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。24 个独立需求 seed `20262521–44` × 0/64/128/192 背景档 × ECMP、DRILL、CONGA、LetFlow、ConWeave、ClassReserve = 576 原 ID、36 批，计划未改。
- 2026-10-07 本地 `run_ws25_formal.py verify` 对 576/576 原 ID 的 metadata、trace/拓扑/FCT raw、完成率、队列和资源重新通过。`analyze_ws25_formal.py` 再读 raw 复算 576 格，机器分析 SHA-256 `f4d4ce0bb7e0ed8af26ee84276c472e082d8d6163c964e2c6dd7a3f632931f43` 与此前一致。收据 576 个唯一 `verified`，无失败事件；所有输入流完成。最高 load 16.10、最低 MemAvailable 51.80 GiB、最低空盘 4,962.54 GiB、最大格树 RSS 4,562.50 MiB。
- 192 档正式共同主结果相对 ECMP：MoE 合成批次中位 −3.536%、20/24 改善；背景 P99 FCT 中位 −0.065%、13/24 改善。各项需 ≤−5% 且 ≥17/24，交集为 **NO-GO**。四次级基线 Holm 联合比较均未过；低档约束通过但有单 seed 尾流退化。该结论仅适用于冻结合成需求与 ns-3 RDMA QP 模型。
- v2 DestSpread 原版及唯一修正版 v2r1 分别完成 28/28 新需求探索筛选，均未过各自预冻双侧门；v2r1 相对 ECMP 的 MoE 中位 −3.813%/2/4 改善，背景 P99 +1.206%/2/4 改善。它们不是正式收益证据。v1/v2 各自一次修正额度已用；第三候选剩余名额未启动，理由见[准入审查](../research/ws25-third-candidate-decision.md)。

## 3. 已完成工作

1. 完成历史 WS-11/12/13/19/20 与开题报告边界审计、五基线同输入正确性、v1 修正版 11/11 前置格与 96/96 正式候选格验收；旧模式动态分支触发不足明确记录。
2. 在未见最终需求池前冻结[正式协议](../research/ws25-v1fix-formal-protocol.md)、[96 输入 manifest](../research/evidence/ws25-v1fix-formal-inputs.json)、[576 ID 计划](../research/evidence/ws25-v1fix-formal-plan.json)及资源门，执行所有 36 批。SSH/fetch 控制面异常按原 metadata/PID/raw 防重恢复，没有覆盖已验收 raw。
3. 从 raw 形成[正式双侧分析](../research/ws25-v1fix-formal-analysis.md)、[两格尾流诊断](../research/ws25-v1-formal-tail-diagnostic-analysis.md)、[复现清单](../research/ws25-v1fix-reproducibility-checklist.md)、576 行逐格表、840 行配对表、1008 条 CDF 索引及 192 张 SVG。两格诊断重新逐流解析了已记录的上游出口等待；正式 192 档 144 格的[公共窗口上联利用率](../research/ws25-v1fix-uplink-utilization-supplement.md)也由累计原始计数补算。仍缺同粒度 ECMP 逐 QP 探针与按包时序，不能确认因果。[负结果初稿](../research/ws25-classreserve-v1-paper-draft.md)与[图文终审](../research/ws25-v1fix-paper-package-audit.md)已完成。
4. 对额外 v2/v2r1 原始数据做独立探索报告；v2r1 的 28 格重新逐 raw 验证并形成[机器分析](../research/evidence/ws25-v2r1-screen-analysis.json)。2026-10-07 对第一课题全部七项预设验收作[逐项审计](../research/ws25-first-paper-acceptance-audit.md)，列明证据和适用边界。

## 4. 已形成的设计决策

冻结 v1 主判据不随结果变更；双主结果必须分别过幅度和方向线，不能以背景可容忍退化代替改善。v2/v2r1 探索失败后，不使用未见 pilot/final seed 为 v2 追补结果，也不再改 v2。剩余第三候选名额未使用：已有本地队列、DRILL 粒度、目的地址平局轮转和逐流缓存的两版试验均未给出稳定双侧方向，当前缺少能预先识别背景尾部热点与短流乱序代价的新本地信号；任意拼接或设阈值不足以构成可证伪第三版。若未来提出新观测与信号，须按独立新 SHA/ID/seed 另行冻结，不改 v1 NO-GO。本决定不把第三版未尝试写成失败实验。

## 5. 当前状态

第一课题[七项预设的实验与初稿验收](../research/ws25-first-paper-acceptance-audit.md)均已完成；性能结论为正式 NO-GO。正式 runner 旧本地 PID `46324` 和 v2r1 runner PID `14084` 均已退出，所有当前计划原 ID 终态；没有要恢复的新格。交付时实际 Git HEAD、origin 同步与工作树清洁度以提交后的本地 Git 核对为准；本文件无法预写自身提交哈希。用户未请求归档，当前对话保持可追溯。

## 6. 未解决问题

第一课题预设验收无未完成仿真格。**后续里程碑**：目标会议模板与引用格式适配、投稿决定/投稿；这些没有被初稿验收冒充。**证据限制**：没有真实 NIC/交换机、生产 trace、业务 SLO、物理 MMU 总队列或逐 QP 速率时标；现有动态基线特有分支在本输入下触发稀少，不能推断充分覆盖。第二课题的反馈通信成本、时效、采用/回退、WS-21 历史缺口尚未启动，也不能并入本第一课题成果。

## 7. 后续推荐动作

主对话核验本 Handoff 的最终 Git SHA 与 raw/审计结论，将 WS-25 第一课题实验及小论文初稿状态集成到 `CURRENT_STATE.md`、`WORKSTREAMS.md` 和 `ROADMAP.md`；状态应区分“预设仿真/初稿完成”与“未投稿”。导师/用户确定投稿目标后另做版式、引用与投稿流程。投稿后再按 ADR-010 单独开启状态反馈第二课题，先审查旧 WS-21 与反馈成本/时效证据。若用户要求第三候选研究，先提出新可观测机制假说及独立预冻协议，不动已揭盲的 v1 最终 seed。

## 8. 与其他工作流的关系

只向个人 fork 的 `feature/ws25-first-paper` 写代码/证据，不修改两个只读参考仓库。v1 正式结果、v2/v2r1 探索结果、WS-23/24 旁证及未来第二课题之间保持独立证据身份。当前项目主状态文件仍可能有 2026-10-02 旧快照；本 Handoff 供主对话核验后集成，不以写入此文件代替集成。

## 9. CONTEXT SNAPSHOT

WS-25 第一课题固定 v1 SHA `ce699dffe2845dc83e2171a1c309c6d96b96d2b3`、24 seed×4 档×6 模式，576/576 原 ID 和 36 批 raw 于 2026-10-07 再验通过；机器分析哈希未变。192 档 MoE −3.536%/20/24、背景 P99 −0.065%/13/24，正式共同主 NO-GO；五基线、低档约束、资源、反例、图表与负结果初稿完整见[验收审计](../research/ws25-first-paper-acceptance-audit.md)。v2/v2r1 各 28/28 探索格未过双侧门，第三版未启动；没有在途矩阵，不要恢复或重跑原 ID。真实部署与物理队列因果证据缺失，稿件尚未投稿；第二课题须等投稿后。主对话负责状态集成与实际模型边界，不自动归档。
