# Handoff 83：WS-26 ClassLane v4 背景流配对逐跳诊断

## 1. 本对话目标

本交接承接 WS-26 分析子任务 `/root/ws26_analyze_high` 和四格 ECMP 诊断执行。任务是核验新 ECMP 格的原始结果，再与既有 ClassLane v4 诊断格配对分析背景流路径。分析不重判高档效果门，也不运行新仿真。

## 2. 已确认的项目事实

- 当前工作区为 `feature/ws26-classmix-validation`。2026-10-10 核验时，仿真固定源码为 `41384701c865082655cdea9a9e64daae74f51327`。
- [冻结协议](../research/ws26-v4-ecmp-background-hop-diagnostic.md)规定四个 seed、四个新 ID、逐格全流和背景 QP 验收，以及诊断 FCT 与普通 ECMP 同哈希。
- [完整逐流分析](../../results/ws26-v4-ecmp-diagnostic-execution/hop-analysis.json)文件 SHA-256 为 `4c076f0ad7e916c6e9daeaae0faea56abdd4ee95a64aa41157ab872f7c8b3ca5`。重跑冻结分析器的内容一致；按 Windows 原 CRLF 换行编码后，文件哈希也一致。
- 四个诊断 ID 各完成 16,576/16,576 条流，192/192 条背景 QP 都有 `WS13_HOP`；`WS13_INFLIGHT unpaired=0`。FCT SHA-256 与各自普通 ECMP 格 4/4 相同，资源收据均通过。

这些事实由固定计划、元数据、raw、逐格校验器与资源收据支持。[机器摘要](../research/evidence/ws26-v4-ecmp-hop-diagnostic-summary.json)索引所有四格和尾流。

## 3. 已完成工作

实验副任务按 cap=1 完成四格并回传原始结果。runner 曾在仿真前两次触发设置门，随后只修复相应隔离源码的 trace 安装和忽略规则。收据最终记录四次 `run_started`、四次 `verified` 和一次 `all_cells_verified`，旧 ID 与 raw 保持原状。

本分析子任务独立重跑四格冻结校验器与分析器，确认完整流身份、逐跳覆盖、FCT 非扰动、资源门和路径连续性。还重跑四格既有 ClassLane 诊断校验器，再按同一批 192 条背景 QP 对照区域等待、P99 附近和最慢三条流。结果见[诊断报告](../research/ws26-v4-ecmp-hop-diagnostic-analysis.md)和[机器摘要](../research/evidence/ws26-v4-ecmp-hop-diagnostic-summary.json)。

## 4. 已形成的设计决策

本次没有实施 ClassLane v4 的诊断修正。候选的源 ToR 和中转区域等待 P99 在四 seed 均较 ECMP 高，但背景 FCT P99 两升两降。最慢流的身份和路径会迁移；逐跳最大等待无法解释对应 FCT 差值。MoE QP 没有同口径逐跳观测，因此无法检验其容量集中预测。现有证据不支持唯一的修正规则。

## 5. 当前状态

截至 2026-10-10，四格 ECMP 诊断已完成并通过技术验收。每格 watcher 有 60～124 条采样；最高进程树 RSS 为 4,544.79 MiB，可用内存最低为 118.33 GiB，剩余磁盘最低为 4,777.34 GiB，一分钟负载最高为 2.01。ClassLane v4 r2 高档双侧筛选仍为 NO-GO，条件低档 24 格未启动。WS-26 整体仍为 ACTIVE。

## 6. 未解决问题

当前逐跳日志只覆盖背景类 UDP 包，缺少 MoE 逐跳等待和按包时间对齐的因果证据。正式主矩阵 576 格、传输敏感性矩阵 576 格及最终原始数据验收尚未完成。本次四格诊断不构成正式效果证据，也不完成 WS-26 预设任务。

## 7. 后续推荐动作

保留 ClassLane v4 的失败反例与停止门槛。下一项候选须先有独立机制依据，并能事前预测 MoE 与背景两项结果。之后使用新源码 SHA、独立 ID 重走正确性和独立需求 pilot。正式两组 576 格及最终验收仍按[执行清单](../research/ws26-classmix-execution-plan.md)承接；变更原任务范围须用户明确决定。

## 8. 与其他工作流的关系

四格使用原 pilot 的同四个 seed，仅增加 ECMP 日志，不增加独立重复。ClassReserve v3 与 WS-25 的既有 NO-GO 不受本诊断影响。其他任务可复用背景逐跳分析方法，但不能将本轮设备出口队列值当作 MMU 物理占用。

## 9. CONTEXT SNAPSHOT

WS-26 ClassLane v4 的四个新增 ECMP 诊断格已验收：各 16,576/16,576 流、192/192 背景 QP 有逐跳记录、`unpaired=0`，诊断 FCT 与原 ECMP 配对格完全相同。完整分析 SHA-256 为 `4c076f0ad7e916c6e9daeaae0faea56abdd4ee95a64aa41157ab872f7c8b3ca5`。候选上游区域高分位等待上升，背景 P99 方向却不一致；最慢流个体也迁移。无 MoE 逐跳观测，当前不实施唯一诊断修正。v4 高档 NO-GO、低档未启动、WS-26 ACTIVE 和两组正式 576 格未完成的状态保持。
