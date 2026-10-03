# Handoff 67：WS-25 r3 校准首个 seed 六臂 6/28

1. **阶段目标：** 记录 r3 首个需求 seed 的六个主臂逐格验收，按冻结的顺序继续诊断控制格与其余 seed；本 handoff 不构成校准分析或效果判决。
2. **固定实验身份：** 仿真/输入 SHA `a656104d05c681f9b3a998b5ef4ce3e644558d02`；拓扑 SHA `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`；seed `20262507` 的 b192 trace SHA `01b24bc1bd76d4932dd6c6e4e7ce159ff9d73824de2540ba4b09cd62e6ff83b7`。模式、全部 r3 ID/输入哈希与执行顺序见[冻结计划](../research/evidence/ws25-v1fix-calibration-plan-r3.json)。
3. **已验证格：** 六个主臂 `fecmp`、`conweave`、`letflow`、`drill`、`conga`、`classreserve` 均为 `SUCCEEDED` 并经 verifier 核验 metadata、源码/trace/topology hash、参数、raw、类别流数/完成数及资源摘要。每格 16,384/16,384 MoE 和 192/192 背景全部完成。ID 使用同一前缀 `20261003-100000-ws25-v1fix-cal07-` 加各模式后缀。矩阵进度 6/28；ClassReserve 的 diag-on 指纹控制尚未终验。
4. **资源和现场：** 六格的树 RSS 最大 `4562.313 MiB`，未超过协议 32 GiB 上限。半小时现场审计 load 1m=`0.0`、active simulation PIDs 为空、可用内存 `122.95 GiB`、空闲盘 `5521.3 GiB`；停止线通过。控制器仍在运行，继续 cap=2。
5. **结果边界：** 目前只有 seed07 的六个主臂，独立需求重复仍只有一个；本轮不报告跨 seed 统计、不排序收益、不作正式 NO-GO。主指标仅在整批终态后按预定 demand seed 配对分析，诊断 FCT 指纹另行核查且不增加 n。
6. **自动继续：** 当前实际监督模型 GPT-6 Luna High。runner 自动运行 seed07 diag 格和 seed08/05/06 剩余格，约半小时读取状态；遇到失败停止启动新 ID并保留 raw/收据。全部 28 格逐格核验后实际切换 GPT-6 Sol High 分析。
7. **未完成验收：** diag 控制格、另外三个独立 demand seed、矩阵级非扰动指纹、校准分析、0/64/128 档约束、正式双侧门槛/样本量/最终矩阵和小论文均待办；WS-25 仍 ACTIVE。
8. **前序失败隔离：** r1 的输入快照失配和 r2 的远端 Git object 未同步均已使用独立 ID 保留，相关说明见 Handoff 63/64。它们在仿真启动前失败，既不归为算法性能失败，也不计入 r3。
9. **CONTEXT SNAPSHOT：** r3 的 seed07 六个模式主格均成功、6/28 通过，无资源异常；ClassReserve diag 与其余 seed 未完成。保持静默监督并自动续跑。当前候选为 v1 的唯一一次诊断修正版；校准不替代正式双侧验证。
