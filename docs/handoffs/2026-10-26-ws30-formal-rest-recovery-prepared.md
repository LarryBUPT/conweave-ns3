# WS-30 formal-rest 修复与待验收续跑交接

## 1. 本对话目标

修复中断控制器的输出解码、错误保留和日志恢复，为冻结的 140 个空 ID 准备受控续跑。来源主对话为 `01a0cfac-3176-7590-bf34-c0f176a45118`，执行对话为 `01a174c7-ecf5-7f21-a9dc-6f8b4f5634b8`。主对话要求先验收修复，再实际切换 Luna / Medium 并启动续跑。

## 2. 已确认的项目事实

formal-first 已验收 4 格，formal-rest 已保全并重新验证 24 格、397,824 条 FCT；正式矩阵当前为 28/168。正式源码固定 `2c9f3a50bafad0740b461496ba24fa81941a9bc7`，模拟 seed 1。剩余 140 个 ID 的本地结果、暂存、build intent 及远端 runs/results 路径均为空。证据见[续跑计划 r2](../research/evidence/ws30-v14-formal-rest-resume-plan-r2.json)。

## 3. 已完成工作

以实际 GPT-6.1 Sol / Medium 修复二进制输出捕获、UTF-8 诊断解码、旧编码终端显示、完整错误落盘和 config.log 的本地恢复/安全发布。34 项本地测试及 24 格真实 raw 复核通过。旧失败收据保留 18 条 verified、8 个 pending 和 validation 失败；恢复记录的 24 格不回写旧收据。新增构建和仿真均为 0。

## 4. 已形成的设计决策

另建续跑计划、审批和状态文件，保留原授权与失败记录。只对原有 140 个空 ID 建立新 reservation；终态成功格只抓取或核验，部分目录与不明 intent 先停下检查。新审批为 `approved: false`，等待主对话接受本计划及控制哈希。详细根因、修改和风险见[修复报告](../research/ws30-v14-formal-rest-controller-repair-r1.md)。

## 5. 当前状态

2026 年 10 月 26 日，分支 `research/ws30-attribution-audit` 的控制器修复及本地验收完成，140 格真实续跑未启动。独立执行入口为 `scripts/resume_ws30_v14.py`；审批为 `docs/research/evidence/ws30-v14-formal-rest-resume-authorization-r2.json`。新状态文件尚不存在；r1 准备稿保留且未批准。控制哈希与测试输出见[审计收据 r2](../research/evidence/ws30-v14-formal-rest-repair-audit-r2.json)。

## 6. 未解决问题

原子命令的非零退出细节被旧解码异常掩盖，无法事后恢复。140 格真实执行尚待验收；工程 48 格、W5 36 格、正式双侧分析和全文整合仍是必做项。完整性能结论尚未形成。

## 7. 后续推荐动作

主对话核验修复报告、计划及控制哈希，填入实际验收依据。实际切至 Luna / Medium 后，使用新入口 `run --session-file <实际会话文件>`；入口先重查旧证据和新鲜资源，随后只承接 140 格。异常保留原 ID/raw 并停止 admission。终态数据齐全后实际切回 GPT-6.1 Sol / Medium，完成全矩阵分析。

## 8. 与其他工作流的关系

本节点只修改 WS-30 工作树内控制和文档，不改仿真机制。通用 helper 的修改可能影响后续 WS-25/30 调用，已保留原测试并新增恢复测试。候选论文复核见修复报告；没有新机制准入。此交接未更新项目集成分支，不能用分支旧状态替代原始数据。

## 9. CONTEXT SNAPSHOT

WS-30 ACTIVE；正式 28/168，其中 formal-rest 24/164。固定旧源、输入和模拟 seed 保持。140 个空 ID 的续跑计划及新控制哈希已准备，审批关闭，新增运行 0。旧失败收据不能覆盖；已成功 24 格不能重跑。先主对话验收修复，再 Luna / Medium 运行，最终 Sol / Medium 分析；工程 48、W5 36 与全文整合继续保持未完成。
