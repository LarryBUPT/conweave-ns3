# 项目持久参考

在本仓库的每次对话或任务开始时，第一步先阅读 `docs/REMOTE_EXPERIMENT_WORKFLOW.md`，再开展源码阅读、远程实验、分析或修改。其项目总目录副本为 `E:\研\毕业论文\docs\REMOTE_EXPERIMENT_WORKFLOW.md`；两份应保持同步。

涉及 baseline、数据流或指标口径时，随后阅读仓库内的 `docs/research/10-baseline-fidelity-and-dataflow-audit.md`。所有实验应以固定源码 SHA、trace 哈希、seed 和原始结果核验。

跨对话交接、项目集成或下一工作流选择时，使用 `.agents/skills/conweave-project-state/SKILL.md`，并核验 `docs/project-state/CURRENT_STATE.md`。`AGENTS.md` 只存稳定规则；阶段状态以项目状态文件及其所引用的实际证据为准。

每个 WS 分支任务均受 `docs/REMOTE_EXPERIMENT_WORKFLOW.md` 的长时矩阵准则约束：远程仿真静默、约半小时精简监督，监督阶段使用 GPT-6 Luna High，实验结束后使用 GPT-6 Sol High 分析收束；交接和最终说明用自然语言交代流程、实验数据、结论与限制。模型切换须实际生效，不以提示文字代替。

## 上下文压缩后的续接与时间记录

- 续接前先区分最新真实用户消息、压缩前停点、已完成历史、转交消息和环境信息。保留在上下文中的旧用户指令，不等于本轮新指令。
- 压缩摘要与当前文件均确认完成的工作保持完成；没有新证据或用户重新要求，不重复核实、归档、派发或运行。摘要与文件冲突时，只核对冲突涉及的最小证据。
- 分别记录事件发生时间、收据生成时间、观察时间和报告时间。重新读取旧收据，不能将读取时间写成事件时间。
- 原始时间保留时区和精度。对用户默认使用北京时间（Asia/Shanghai），从 UTC 换算时同时核对日期；只有日期的来源不补造时分秒，未知时间明确记为未知。
- 本次纠错依据：`docs/research/evidence/integration-compaction-chronology-correction-20261104-r1.json`（位于个人 fork）。WS-26～WS-28 归档和 WS-31 心跳删除同步均为已完成历史；HOLD 不因压缩而恢复执行。
