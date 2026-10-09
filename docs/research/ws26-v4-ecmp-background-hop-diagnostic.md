# WS-26 ClassLane v4 背景流配对逐跳诊断

状态：2026-10-09 事前冻结；四格已完成并通过逐格验收。结果见[诊断分析](ws26-v4-ecmp-hop-diagnostic-analysis.md)、[机器摘要](evidence/ws26-v4-ecmp-hop-diagnostic-summary.json)和[完整逐流分析](../../results/ws26-v4-ecmp-diagnostic-execution/hop-analysis.json)。本诊断仅补齐现有 pilot 的 ECMP 逐跳观测，不重新判定候选效果，也不增加独立需求 seed。

## 问题与证据边界

[ClassLane v4 r2 高档分析](ws26-classlane4-pilot-r2-analysis.md)显示，四个 seed 的 MoE 整批时间全部变慢，背景 P99 双侧筛选也未通过。现有四格 ClassLane 诊断含背景 QP 的 `WS13_HOP`，但四格普通 ECMP 对照没有同口径逐跳队列记录。ClassLane 的单格队列峰值不能与缺失的 ECMP 数值比较。

本诊断检验同输入背景流在两种模式下的逐跳路径、排队字节和出队等待是否存在可控的差异。`WS13_HOP` 只记录背景类 UDP 数据包；队列值来自设备出口队列，不等于 MMU 物理缓冲占用。逐跳最大等待也不能相加解释整条流的 FCT。诊断不观察 MoE 逐跳等待，因此不能单独证明两条 MoE 路径导致批次变慢。

## 固定输入与四个原 ID

使用 v4 r2 原仿真源码 SHA `41384701c865082655cdea9a9e64daae74f51327`。四个 seed 为 `20262694～20262697`，背景档位为 192，拓扑及 trace 哈希与[原 pilot 冻结计划](evidence/ws26-classlane4-pilot-plan-r2.json)逐格相同。PFC=1、IRN=1、ns-3 seed 1、带宽 400 Gbit/s、buffer 9 MiB、`netload=10`、`simul_time=0.01` 保持不变。唯一变化是将 ECMP 的 `WS25_DIAG` 打开为 1。

[机器计划](evidence/ws26-v4-ecmp-diagnostic-plan.json)按 seed 升序登记四个全新实验 ID，并保存原 ECMP 配对 ID。机器计划 SHA-256 为 `030976066b815ef76fc941d0b8e612712e1a60c26a1ada05d9df8687981d6add`。旧 ID 与 raw 保持原状；四格各自隔离构建、配置和结果目录。

## 执行与逐格验收

唯一实验副对话先确认无其他用户作业、无活跃仿真或持有中的锁，再检查四个新 ID 在远端 `runs/`、`results/` 和本地结果目录均无冲突。每格 build 与 run 前执行资源门；run 前启动 watcher 并确认首条采样。采用 cap=1 串行调度。进程树 RSS 峰值上限为 32,768 MiB，可用内存下限为 32 GiB，剩余磁盘下限为 100 GiB，一分钟负载上限为 20。

每格必须核对固定源码、拓扑、trace SHA-256、运行参数和终态资源收据。16,576 条输入流均须恰好完成一次，身份、标签、大小与起始时刻一致。诊断格原始 FCT 的 SHA-256 必须与同 seed 的既有普通 ECMP 格完全相同；192 条背景 QP 必须全部映射到 `WS13_HOP`，且 `WS13_INFLIGHT unpaired=0`。任一检查失败即停止后续格，保留该 ID 的原始结果，按工作流定位后以新 ID 处理。

## 分析与修正准入

四格全部通过后，按冻结 trace 身份配对 192 条背景流。报告各 seed 的全体背景流逐跳等待分布，以及 P99 附近和最慢三条流的路径、FCT、最大队列字节与最大等待。按拓扑原文区分可选八路分叉、上游共用链路和目的主机唯一出口。路径不同的流按实际经过的区域比较，不把不同端口的峰值当作同一端口的配对变化。

尾流是已揭盲 pilot 的事后选择，描述只用于机制定位。若退化主要落在不可选择的终端出口，或各 seed 的可控上游差异不稳定，现有证据不支持 v4 的唯一一次诊断修正。即使发现可控上游差异，仍需另行验证 MoE 容量集中及双指标同时改善的可证伪预测，才能冻结修正规则。不得用本诊断改写 v4 的高档 NO-GO、启动条件低档，或将其充作正式收益证据。

WS-26 的正式 576 格主矩阵、576 格传输敏感性矩阵及最终验收继续标记未完成。后续候选仍受 [ADR-010](../decisions/ADR-010-sequential-mixed-lb-paper-plan.md) 的最多三个新版本、每版至多一次诊断修正约束。

## 执行结果（2026-10-10）

四个新 ID 均有成功终态、原始流和资源回执。每格 16,576/16,576 条流完成，192/192 条背景 QP 有逐跳记录，`WS13_INFLIGHT unpaired=0`。四格 FCT 哈希与各自普通 ECMP 格完全相同。完整分析文件 SHA-256 为 `4c076f0ad7e916c6e9daeaae0faea56abdd4ee95a64aa41157ab872f7c8b3ca5`。结论与限制见[分析报告](ws26-v4-ecmp-hop-diagnostic-analysis.md)及[Handoff 83](../handoffs/2026-10-10-83-ws26-v4-ecmp-hop-diagnostic.md)。事前门槛保持不变。
