# 项目持久参考

在本仓库的每次对话或任务开始时，第一步先阅读 `docs/REMOTE_EXPERIMENT_WORKFLOW.md`，再开展源码阅读、远程实验、分析或修改。其项目总目录副本为 `E:\研\毕业论文\docs\REMOTE_EXPERIMENT_WORKFLOW.md`；两份应保持同步。

涉及 baseline、数据流或指标口径时，随后阅读仓库内的 `docs/research/10-baseline-fidelity-and-dataflow-audit.md`。所有实验应以固定源码 SHA、trace 哈希、seed 和原始结果核验。

跨对话交接、项目集成或下一工作流选择时，使用 `.agents/skills/conweave-project-state/SKILL.md`，并核验 `docs/project-state/CURRENT_STATE.md`。`AGENTS.md` 只存稳定规则；阶段状态以项目状态文件及其所引用的实际证据为准。

每个 WS 分支任务均受 `docs/REMOTE_EXPERIMENT_WORKFLOW.md` 的长时矩阵准则约束：远程仿真静默、约半小时精简监督，监督阶段使用 GPT-6 Luna High，实验结束后使用 GPT-6 Sol High 分析收束；交接和最终说明用自然语言交代流程、实验数据、结论与限制。模型切换须实际生效，不以提示文字代替。

每个完整的重要工作节点结束后，按论文项目根目录 `参考文献/候选/README.md` 和 `reading-log.md` 做一次参考借鉴复核。查阅与当前问题相关的技术分析和核验记录，写明论文版本、借鉴点、适用条件、与现有机制的区别及不可外推之处。诊断收束、候选冻结、pilot 分析和正式矩阵分析属于重要节点；逐格验收与例行心跳不重复触发。候选文献不替代原始实验数据，也不自动准入新机制。
