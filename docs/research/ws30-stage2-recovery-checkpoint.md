# WS-30 阶段 2 恢复与验收入口

更新：2026 年 10 月 24 日，阶段 2 完成后。WS-30 为 ACTIVE；本节点完成技术、资源与历史桥接，等待主对话审核。正式效果矩阵保持关闭。

## 已验收范围

| 项目 | 完成情况 | 原始证据与收据 |
| --- | --- | --- |
| 技术任务 | 32/32 格；其中完整逐包日志 22 格独立重建路径 | [技术收据](evidence/ws30-technical-results-recovered-r1.json)、[路径收据](evidence/ws30-technical-paths-recovered-r1.json) |
| 资源 pilot | 24/24 格；4/8/12 阶梯验收，冻结 cap=12 | [pilot 报告](ws30-resource-pilot-report-r1.md) |
| 历史桥接 | 96/96 格；复用 4 个预检，新运行 92 格，全部 raw FCT 哈希匹配历史 | [桥接收据](evidence/ws30-bridge-results-recovered-r1.json)、[解析计划](evidence/ws30-bridge-resolved-recovered-r1.json) |
| 阶段后复验 | 148 个独立成功实验；96 组历史／新 raw 及输入哈希复验 | [后审计收据](evidence/ws30-stage2-postrun-audit-r1.json) |

32＋24＋96 中有 4 格重叠，独立成功实验为 148 个。详细过程、资源、结论、文献复核及下一阶段入口见[阶段 2 报告](ws30-stage2-completion-report-r1.md)和[阶段 Handoff](../handoffs/2026-10-24-ws30-stage2-complete.md)。此结果证明固定历史输入上的输出保持，未识别新八臂效果或类别增量。

## 固定源码、输入与失败保留

工作区为 `E:/研/毕业论文/workspace/ws30-attribution-audit`，分支 `research/ws30-attribution-audit`。核心仿真 SHA 为 `1ef424749e3c551dd788d0a709bd8e21c7cc89c9`；技术错峰输入修复 SHA 为 `6df0a9db9d01e1fd1b4c725b31525983425f4fac`。运行源码路径完全相同，48 份正式输入未被该修复改变。v3 输入清单 SHA-256 为 `7dd69012ab91c7c5fa38d2e8e3943919dc2edca7b37af237971f769fca6a0ac5`。

原 `t15-e-o2`、`t16-q16-o2`、`t17-c16-o2` 因技术输入第 162 行时间倒退失败。原 metadata、raw、配置错误日志和资源样本保留；替代格为 `20261024-010000-ws30-leadfix-{e,q16,c16}-o2`，均通过。详见[失败与修复收据](evidence/ws30-staggered-fixture-failure-and-repair-r1.json)。

桥接首次启动因新生成计划使工作树不干净而被编译保护拒绝，尚未启动仿真；日志保留在 `results/ws30-stage2-recovery-bridge-cleanliness-block-r1.log`。控制器 ID 解析修正及计划已在 `5fb0ec245f99649080e28d6433765c3842e683a3` 推送。92 个新格最终使用 `20261024-020000-ws30-bridge-c12-s<seed>-<arm>`，无新桥接仿真失败。

## 恢复与下一阶段入口

阶段 2 执行器 `scripts/resume_ws30_stage2.py bridge` 已成功完成，不再重跑。若需复核，使用以下只读数据验收入口：

```powershell
python scripts/audit_ws30_stage2_closure.py
python scripts/verify_ws30_technical_paths.py
python scripts/prepare_ws30_stage3.py
```

第三条只准备审核计划，不启动实验。[阶段 3 审核计划](evidence/ws30-stage3-review-plan-r1.json)绑定 192 个主矩阵格、72 个先占格、核心 SHA、cap=12 和 48 份输入，SHA-256 为 `c48c4bfeacffc6bfc915cd035309fd12317802dc78cf2927e96956d76bda0c1b`，执行开关关闭。没有可直接执行的正式阶段 runner；须先经主对话审核，冻结实际入队组成夹具和可恢复执行器。

| 仍须完成的任务 | 当前状态与承接 |
| --- | --- |
| 八臂归因主矩阵 192 格 | 0/192；由本 WS-30 分支承接，审核后按冻结计划执行 |
| 背景提前 20 µs 的 72 格 | 0/72；独立取 MoE 放流原点，禁止把等待时间混入批完成 |
| 实际队列组成诊断 12 格 | 0/12；需冻结精确等总占用、组成交换和两种后续到达条件 |
| 双侧分析与逐图逐表包 | 未完成；按原协议九项对比、负结果及 F1～F5、D1～D4 交付 |

完整停止条件和资源估计见阶段 2 报告。后续暂以 cap=12、每源码 `-j2`、最多 4 份并行编译规划；264 格按桥接完整吞吐估约 10.9 小时，磁盘连同组成和日志暂预留 450 GiB。启动时重新检查作业、锁和 ID 隔离；不能沿用本次终态快照。零／负效应不取消必做验证，不搜索有利权重、盐或提前量。

## 模型与交接状态

实际会话 `turn_context` 已核实：监督阶段 GPT-6 Luna / Medium，阶段后分析 GPT-6.1 Sol / Medium。后者为本 WS 明确指定设置，优先于工作流的 High 默认；此前 Sol High 文字不代表最终生效模型。模型字段与时间记录于后审计收据。

终态无活动仿真或其他用户作业，load1=0，可用内存 122.59 GiB、空盘 3,550.3 GiB，见[主机收据](evidence/ws30-stage2-final-host-gate-r1.json)。本节点已按 Gemma、SeqBalance、DiffFlow 固定版本完成参考复核。WS-29 未触碰；不启动正式矩阵、不归档 WS-30，待主对话审核。
