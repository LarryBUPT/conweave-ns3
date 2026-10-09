# Handoff 82：WS-26 ClassLane v4 r2 高档筛选

## 1. 本对话目标

按冻结 r2 协议验收 ClassLane v4 的 28 格高档独立需求 pilot，并复算 MoE 整批完成时间与背景 FCT P99 的双侧筛选门。仅在两门同时通过时启动 24 格条件低档。

## 2. 已确认的项目事实

- 个人 fork 工作分支为 `feature/ws26-classmix-validation`；仿真源码 SHA 为 `41384701c865082655cdea9a9e64daae74f51327`。
- [r2 计划](../research/evidence/ws26-classlane4-pilot-plan-r2.json) SHA-256 为 `b71155816dff1fd7410073913a35ae714c9bc6988c789867eba79829aa58cc02`，含 28 个高档和 24 个条件低档 ID。
- 高档[原始汇总](../../results/ws26-classlane4-independent-pilot-r2/high-verified.json) SHA-256 为 `34f3150ba008359ffd25b2b7052b48ef2dbf768ad5302b153c01c13f20aec5ba`；逐格从 raw 重算得到相同 SHA。
- 四个需求 seed 为 `20262694`～`20262697`。每格 16,576/16,576 条流完成；诊断 FCT 非扰动 4/4 通过。

这些事实来自源码、冻结计划、逐格元数据、原始流记录及资源收据，不依赖对话进度描述。

## 3. 已完成工作

runner 按 cap=1 顺序完成 28 格，并保留每格原始数据、终态收据和 watcher 采样。分析阶段重新执行逐格校验器，核对输入身份、配置、全流完成、类别路由计数、逐 QP 路径、诊断 FCT、队列守恒和资源线。复算结果与 runner 汇总逐字节一致。

[分析报告](../research/ws26-classlane4-pilot-r2-analysis.md)和[机器分析](../research/evidence/ws26-classlane4-pilot-r2-analysis.json)记录四个 seed 的原始指标、配对变化和双侧门槛。MoE 批次中位变化为 +20.851%，0/4 个 seed 改善；背景 P99 中位变化为 −0.362%，2/4 个 seed 改善。两项均未达到中位数 ≤−3% 且至少 3/4 改善的冻结门槛。

## 4. 已形成的设计决策

按 r2 协议判定 ClassLane v4 高档筛选 NO-GO，保留全部失败反例。条件低档 24 个 ID 不启动，当前版本不进入正式矩阵冻结。该判断直接来自事前门槛；机制计数与正确性通过不改变效果判定。

## 5. 当前状态

截至 2026-10-09，高档 28/28 格完成并通过逐格验收。每格 watcher 有 57～69 条采样；RSS 峰值最高为 4,562.59 MiB，可用内存最低为 118.31 GiB，剩余磁盘最低为 4,781.16 GiB，一分钟负载最高为 2.15。条件低档无本地结果目录和 runner 事件。工作树仍在 `feature/ws26-classmix-validation`；WS-26 保持 ACTIVE。

## 6. 未解决问题

现有四 seed 结果没有给出 ClassLane v4 可通过双侧门槛的证据，也不足以定位唯一有效的路由修正。正式 576 格主矩阵、576 格敏感性矩阵、全部原始结果验收和最终统计尚未完成。当前 pilot 不构成 WS-26 整体闭环。

## 7. 后续推荐动作

先根据四 seed 反例和已有尾流诊断，提出有独立机制依据且可证伪的候选；在新源码 SHA、独立 ID 和事前门槛下，重新完成正确性与独立需求 pilot。只有通过新候选的相应门槛，才能冻结并执行正式主矩阵与敏感性矩阵。原执行清单的必做项继续保持未完成状态，范围变更需用户明确决定。

## 8. 与其他工作流的关系

本轮使用独立于 WS-25 正式池的 seed，不重判 WS-25 的正式 NO-GO。ClassReserve v3 的高档 NO-GO 与本轮是不同候选、不同输入和源码版本，不合并为一组独立重复。ConWeave 的工程比较参数须与原版官方校准区分。

## 9. CONTEXT SNAPSHOT

WS-26 ClassLane v4 r2 固定 SHA `41384701c865082655cdea9a9e64daae74f51327` 的 28 个高档 ID 已通过 raw、全流、诊断非扰动与资源验收。四 seed 的 MoE 批次均慢于 ECMP，背景 P99 仅 2/4 改善；冻结双侧门失败，24 个条件低档 ID 未启动。证据入口为[协议](../research/ws26-classlane4-independent-pilot-protocol.md)、[分析报告](../research/ws26-classlane4-pilot-r2-analysis.md)、[机器分析](../research/evidence/ws26-classlane4-pilot-r2-analysis.json)与忽略目录中的 28 个原始结果。WS-26 仍 ACTIVE，正式两组各 576 格及最终验收待完成。
