# Handoff 56：WS-25 第一课题 v1 预飞行冻结

日期：2026-10-02。来源：主对话委派的 WS-25 第一课题实现任务；这是远程正确性和校准 pilot **执行前**的阶段交接，WS-25 继续 ACTIVE。

## 1. 本对话目标

只推进第一课题：类别感知包流混合选路、五原始模式同条件、独立需求、双侧主指标和小论文。WS-21 的状态反馈/心跳余项留给小论文投稿后的第二课题。本阶段被要求在远程执行前固定源码、输入、ID、资源和停止线，并停下由主对话切换监督模型。

## 2. 已确认的项目事实

项目入口工作流与 baseline 审计已读。工作分支 `feature/ws25-first-paper` 从集成点 `75092e1f6aa73766b236b2d4e3faa0bcc95f8a46` 建立；桌面端 managed worktree 工具因当前任务目录非 Git 仓库拒绝创建/附加，实际使用 `E:\研\毕业论文\workspace\ws25-first-paper` 独立 Git worktree，共享 checkout 未修改。固定仿真源码及校准 seed 01 输入提交为 `1d876a03629dcc0834e001d02e891957608a9f6c`；预飞行协议另见 [本地审计和冻结表](../research/ws25-classreserve-audit-and-preflight.md)。

从旧 raw 重跑 `verify_ws11_formal.py` 返回 40/40、`phenomenon_go=false`；重跑 `verify_ws12_formal.py` 返回 120/120、旧臂 40/40 FCT 哈希匹配，四个新增逐包策略 `two_sided_acceptable=false`。旧实验 ID/SHA 的逐格索引分别在 [WS-11 摘要](../research/ws11-full-moe-formal-summary.json)和[WS-12 摘要](../research/ws12-packet-strategies-formal-summary.json)。本任务**没有新远程 raw 或资源收据**，因而没有 ClassReserve 性能结果。

## 3. 已完成工作

按 `maplerime@470c580` 原生成规则实现显式需求 seed；用 seed 2026 复生的四档与迁入原 trace 逐行完全相同，seed 20262501 的四档和 8 流预飞行 trace 已版本化并核对 Git blob SHA-256。实现 `classreserve` (`LB_MODE 21`)：背景首包本地双候选并逐流固定，MoE 逐包在双候选中按本地总排队加背景排队选择；缺标签/控制包回 ECMP。新增队列守恒和路径计数；补远程 CLI 中遗漏的原 DRILL 及新模式。Python 语法、CLI 帮助、Git 差异检查和输入回归通过。C++ 只能在后续隔离远端构建，当前没有编译成功证据。

静态拓扑核验 rail 0 的 40 个 ToR 全部可达，交换机最短跳数最大 4。ConWeave 源码对该混合链路延迟仍用统一 1000 ns `one_hop_delay` 推估 RTT，作为兼容性风险保留，不将其静态可达等同完整正确性。

## 4. 已形成的设计决策

首版只使用本地出口队列和原有 tag，避免把未完成的下游状态反馈研究提前混入第一课题。背景固定路径以减少长流乱序，MoE 对已有背景排队加一倍惩罚；候选参数不在正式结果中调整。选择五原始算法模式号的共同 fork 源码，而非直接用只读 a8d 二进制解析六列 trace，因为后者只读五列且缺共同 tag 输入。两种做法的算法/传输差异在协议中披露，五模式动态分支仍需实跑核验。

## 5. 当前状态

预飞行身份：六臂 8 流正确性 + 六臂校准 seed 01 的 192 档，共 12 个预留实验 ID；拓扑与两个输入哈希、固定 SHA、参数、预算/停止线见 [协议第 4 节](../research/ws25-classreserve-audit-and-preflight.md)。该 12 格未构建、未仿真、未回传。筛选/校准/未见最终需求 seed 池已分开；双侧数值门槛和最终样本量须在独立校准 raw 后冻结，**正式矩阵仍关闭**。`feature/ws25-first-paper` 已推送个人 `origin`，阶段文档提交 `24c874963898ef74b38ff9fbfd04141cbddbb3b7` 推送时本地/跟踪分支同 SHA、工作树干净；本 Handoff 提交后文档 HEAD 将移动，以最新 Git 实查为准。

## 6. 未解决问题

五模式同输入 optimized build、端到端全部完成、类别/字节守恒、动态路径覆盖，ClassReserve 队列/回退，独立多 seed 校准和缺失观测均未完成。ConWeave 的 RTT 估计可能在混合延迟拓扑影响结果；若正确性失败，必须保留原 ID，修复后新 SHA/ID 重验。强对照效果、最终独立矩阵、双侧分析、论文初稿均未开始。没有任何真实 NIC/生产主张。

## 7. 后续推荐动作

主对话先确认本阶段十二格身份和服务器无在途作业，实际切到 GPT-6 Luna High 再授权远程部署 worker、sync 固定源码、按协议逐格构建与仿真，后台静默、约半小时精简监督。失败时停止新格并保留 raw/资源；正确性缺口继续修复，不能用效果 NO-GO 取消。十二格终态 raw 回传后实际切回 GPT-6 Sol High，逐 ID 分析与校准，并冻结最终双侧数值/样本/ID 才能启动正式验证。所有 WS-25 验收项见[进度账本](../project-state/WS25_FIRST_PAPER_EXECUTION.md)。

## 8. 与其他工作流的关系

WS-11/12 历史 NO-GO 不重判。WS-13/19/20 的尾部与目的出口观察约束本机制的解释，不提供新效果样本。WS-23 隔离 NO-GO 和 WS-24 合成多 rail 正向只作旁证。WS-21 后续反馈/心跳与第二课题严格顺序，当前未实现或实验。

## 9. CONTEXT SNAPSHOT

第一课题 v1 静态代码、独立 seed 01 四档和六臂 12 格预飞行计划已冻结；源码 `1d876a0`，文档 `24c8749`，个人分支 `feature/ws25-first-paper`。本地 Python/输入与旧 raw 复核通过，但无本机制远程 build/raw/资源，所以没有性能结论。下一边界是主对话实际 Luna High 的远程正确性及资源 pilot；终态后 Sol High 校准，再冻结正式矩阵。WS-25 ACTIVE，第二课题未启动。
