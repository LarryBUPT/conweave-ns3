# Handoff 05：Baseline Fidelity Check

来源：Codex 对话 `01a0ce38-9ddc-7f73-859a-4604fc0e4135`，标题「Baseline Fidelity Check」。由集成任务按对话、原始结果与审计文档整理。日期：2026-09-24。

## 1. 本对话目标

在不实现新算法、不做大规模性能评测的前提下，用同一输入与公共配置最小运行 ECMP、CONGA、LetFlow、ConWeave，并沿真实包路径审计输入、分派、VOQ、MMU/RNIC 与 FCT/queue/uplink 数据来源。

## 2. 已确认的项目事实

四次固定 `a8d2db5`、相同拓扑与 trace 哈希、10% 负载、0.01 秒流量生成时间、仿真 seed 1。原始 trace 生成器没有单独播种；本轮通过复用同一文件保证输入一致。ConWeave VOQ 与 MMU 物理队列不是同一指标；uplink 原始值是累计字节。PFC 在这次低负载下未触发。

## 3. 已完成工作

四次最小运行均 `SUCCEEDED`，实验 ID 为 `20260923-180001-fidelity-fecmp` 至 `20260923-180004-fidelity-conweave`。CONGA flowlet timeout 51、LetFlow 50、ConWeave reroute 376、OoO 入 VOQ 23,502 与 flush 330，为本输入下动态路径触发证据。FCT、VOQ、uplink 原始文件及本机分析已核对；论文项目结果摘要为 `results/baseline_fidelity_20260923.json`。源码/数据流入口文档为 `docs/research/10-baseline-fidelity-and-dataflow-audit.md`，个人 fork 中有对应版本。持久 `AGENTS.md` 指向工作流文档。

## 4. 已形成的设计决策

**Decision：**将四次运行解释为 baseline fidelity 与观测链路验证。**Rationale：**短窗口、单一 trace、未触发 PFC，不能支持性能排名。**Alternatives：**直接报告 P99 排序、把 VOQ 当物理 buffer；均因指标口径不符而拒绝。见 `docs/decisions/ADR-003-baseline-evidence-boundary.md`。

## 5. 当前状态

本工作流在定义的最小核验范围内完成。四份原始结果保存在远程与个人 fork 本机忽略目录；后续算法实验仍须新建实验 ID。审计文档提交 `f46abb3` 在本地工作流分支上，且已被混合流量分支继承；GitHub 工作流同名分支仍在 `a8d2db5`。

## 6. 未解决问题

必须解决：正式比较前补 trace seed/不可变输入契约及运行级重复。可延后：远程 Python 3.5 的 uplink 绘图依赖；本机已用原始脚本完成诊断。研究方向保留：物理 MMU 队列测量需要新观测逻辑，不能从现有 VOQ 文件推断。

## 7. 后续推荐动作

WS-06 修改输入管线时，以旧五列 trace 和四种 LB 分支作为回归锚；新结果保持独立 SHA、实验 ID 与输入哈希。不要再将最小运行 P99 作为“ConWeave 优于其他算法”的证据。

## 8. 与其他工作流的关系

依赖远程实验链路；为 Research Discovery 的双轨实现提供可用 baseline 和可修改面地图。仅证明原四模式在本次配置下可运行，不证明将来新模式的正确性。

## 9. CONTEXT SNAPSHOT

四基线同输入最小核验完成，固定 SHA `a8d2db5`，原始结果和指标来源可追溯；性质为技术验证。trace 生成未独立播种，VOQ 非物理队列，PFC 未触发。正式性能实验和新算法仍未开始。
