# WS-30 正式矩阵与分析节点交接

## 1. 本对话目标

完成授权的 formal-rest r2 140 格续跑，保留原 24 格及 formal-first 4 格，并在真实 Sol / Medium 上下文核验 raw、执行冻结分析。论文目标为 v13，执行内部版本为 v14。来源对话为 `01a174c7-ecf5-7f21-a9dc-6f8b4f5634b8`。

## 2. 已确认的项目事实

分支为 `research/ws30-attribution-audit`。固定仿真源码为 `2c9f3a50bafad0740b461496ba24fa81941a9bc7`；计划哈希为 `a7ab77abb8e0222133968c98aa28c1e25e38ddacdaeb14eebcbe10ef97bc0648`。cap 8、原十二项控制哈希及旧失败收据保留。[逐格证据](../research/evidence/ws30-v14-formal-completion-audit-r1.json)优先于本摘要。

## 3. 已完成工作

实际 Luna / Medium 下通过授权与身份门槛，启动唯一 supervisor 和 r2 子进程；复用已构建 ID 后续跑。140/140 已核验，pending 0、实验失败 0。最终正式集合为 4＋24＋140＝168 格。

实际切至 GPT-6.1 Sol / Medium 后，冻结分析脚本重新解析全部 168 格，匹配 2,784,768 条完成身份和 payload 字节；1,512 份 raw 哈希落盘。远端 168 份 FCT 与本地逐份一致，48 份历史 DRILL 回放与原始 FCT 一致。生成全部预设对照、批尾分解、恢复成本及 60 张带来源图表，并完成节点参考借鉴复核。

## 4. 已形成的设计决策

保持冻结的三组需求、直接配对估计和需求级 bootstrap，不混合历史 A/B 与新需求。旧 U16、原生 DRILL 与严格 U12 的候选和状态语义分别说明。未引入新的机制、阈值或实验格；负结果全部保留。

## 5. 当前状态

正式矩阵与其 raw/统计分析节点完成；WS-30 ACTIVE。r2 于 2026 年 10 月 27 日 04:32:27 记录合并验收并退出，supervisor 正常退出，完成后的定时监测已删除。分析代码与完整报告见[节点报告](../research/ws30-v14-formal-completion-report-r1.md)。

新需求 Q12/ECMP 的消息批变化中位为 −4.87%，背景 P99 为 +0.97%；DRILL/ECMP 分别为 −14.93% 和 +8.31%。U12/Q12 分别为 +10.43% 和 +7.41%。完整名义区间、逐需求值、反向观测和假设边界见报告，不能仅用此处的中位数替代。

## 6. 未解决问题

工程 48 格、W5 36 格、主稿结果/图注/结论整合及 26 条回复的最终科学验收仍未完成。新需求已揭盲、模拟 seed 仅 1；真实训练、硬件、持续负载与持久 QP 的结论不能由当前正式组推出。Q12 背景变化范围为 −6.42%～+9.76%，不提供逐需求无损保证。

## 7. 后续动作

先独立验收本节点原始入口和固定统计。工程阶段依 `scripts/run_ws30_v14.py` 的 technical-single → technical-rest → life-pair/life-state → life-other 顺序重新执行源码、资源及授权门槛。W5 先完成 cw-tech/cw-long 四格资格，再执行 w5-resource/w5-rest。当前节点未启动这些阶段，未取消任何必做项。

## 8. 与其他工作流的关系

本节点只更新 WS-30 当前分支内的分析和项目状态。仿真源码、原 raw、历史 v12、现有论文主稿和回复均保留。原失败记录与两次只读 SSH 中断是流程证据；不算新实验或新的性能样本。

## 9. CONTEXT SNAPSHOT

正式 168/168 已核验＝首批 4＋保留 24＋续跑 140，实验失败 0。原始根为本工作树 `results/<ID>/`，远端 `/home/fnl/lzy/results/<ID>/`。逐格审计保存来源、输入、FCT 和全部 raw 文件哈希；分析根为 `results/ws30-v14-formal-complete-analysis-r1/`，图表根为 `results/ws30-v14-formal-complete-figures-r1/`。工程 48、W5 36 和论文整合仍为必做；整个 WS-30 未闭环。
