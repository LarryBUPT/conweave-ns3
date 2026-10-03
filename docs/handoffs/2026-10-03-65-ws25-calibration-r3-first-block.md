# Handoff 65：WS-25 r3 首个独立需求 block 进展

1. **本阶段目标：** 按已冻结 r3 协议启动独立需求校准，记录首个 seed block 的原始完成与资源验收；后续格按运行器自动执行，不在此阶段做性能推断。
2. **固定身份：** 分支 `feature/ws25-first-paper`；仿真/输入固定 SHA `a656104d05c681f9b3a998b5ef4ce3e644558d02`，拓扑 SHA `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`，需求 seed `20262507` trace SHA `01b24bc1bd76d4932dd6c6e4e7ce159ff9d73824de2540ba4b09cd62e6ff83b7`。完整 28 格身份仍见[r3 计划](../research/evidence/ws25-v1fix-calibration-plan-r3.json)。
3. **首批终态格：** `20261003-100000-ws25-v1fix-cal07-fecmp` 和 `20261003-100000-ws25-v1fix-cal07-conweave` 均 `SUCCEEDED`，逐格 verifier 通过；两格各 192/192 背景、16,384/16,384 MoE 全完成，资源收据与 raw 文件齐全。MoE synthetic batch 分别为 18.530 / 18.654 µs，背景 P99 分别为 1774.070 / 1839.458 µs。它们是一个需求 seed 的校准描述值，既不估计独立 seed 间不确定性，也不是基线排序或收益结论。
4. **资源与现场：** 首批树 RSS 峰值分别 4544.105 / 4561.266 MiB；两格最低可用内存约 114.098 GiB，最低空闲盘分别 5524.197 / 5524.189 GiB。首批终态后现场审计 load 1m=`3.87`、active simulation PID 为空、可用内存 `122.57 GiB`、空闲盘 `5523.6 GiB`；未越停止线。运行器 session 仍在，自动推进当前 seed block。
5. **进度与执行方式：** 本次独立校准 2/28 格已通过。保持 cap=2、固定源码/trace/参数及约 30 分钟状态间隔；远端 watcher 继续为运行中的各格记录资源样本。任何 build、运行、输入哈希、完成率、队列守恒或资源条件失败时停止开启新格并保留 ID/raw；早期 r1/r2 失败 ID 均不复用。
6. **待完成：** 其余 26 格、全部 raw 回传与矩阵验证、Sol High 下逐 seed 配对分析、0/64/128 档约束、正式双侧门槛与样本量冻结、最终验证矩阵及小论文。正式门槛冻结前不运行最终效果矩阵；WS-25 保持 ACTIVE。
7. **模型与自动续行：** 当前实际模型为 GPT-6 Luna High。所有 r3 格终态并逐格验证后，主对话应实际切回 GPT-6 Sol High，自动开始全矩阵原始分析；不得在当前单 seed 结果上提前作结论或等待人工确认。
8. **与先前尝试的关系：** r1 是执行 SHA 未包含 trace，r2 是远端源码缓存未同步提交；两者均发生在仿真启动前，独立 ID 已保留且未计入 r3。本 handoff 只报告 r3 的两个成功格。前置修正版 correctness 11/11 与 seed01–04 历史 pilot 仍为各自证据等级，不能与本轮独立校准混成一个正式效果样本。
9. **CONTEXT SNAPSHOT：** WS-25 第一课题 ClassReserve v1 唯一修正版 correctness 已通过；r3 新需求校准刚开始，当前 2/28 verifier 通过，无资源越线，后台控制器继续自动执行。所有 r3 主性能格均是校准，待 28/28 完成后统一由 Sol High 分析；其它预设验收继续 ACTIVE。
