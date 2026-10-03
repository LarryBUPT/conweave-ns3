# Handoff 66：WS-25 r3 校准首个 seed block 4/28

1. **目标：** 按固定 r3 计划继续 ClassReserve v1 修正版独立校准，确认首个 seed block 已完成部分的原始身份、逐格验收和资源边界，并让控制器自动执行剩余格。
2. **固定身份：** 仿真/输入 SHA `a656104d05c681f9b3a998b5ef4ce3e644558d02`；拓扑 SHA `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`；seed `20262507` 的输入 SHA `01b24bc1bd76d4932dd6c6e4e7ce159ff9d73824de2540ba4b09cd62e6ff83b7`。全矩阵 28 个 ID、参数、运行顺序见[r3 冻结计划](../research/evidence/ws25-v1fix-calibration-plan-r3.json)与[协议](../research/ws25-v1fix-independent-calibration-protocol.md)。
3. **已验收：** `20261003-100000-ws25-v1fix-cal07-fecmp`、`…-cal07-conweave`、`…-cal07-letflow`、`…-cal07-drill` 均终态 `SUCCEEDED` 并逐格通过 runner verifier。每格背景 192/192、MoE 16,384/16,384 全完成，raw/config/resource 收据与输入身份通过；单个流或交换机不作为独立重复。当前总进度 4/28，所在 block 尚有 ClassReserve 主格与 diag 控制格待运行。
4. **资源：** 四格峰值树 RSS 范围 4544.105–4561.266 MiB。第一次 block 间现场审计 load 1m=`0.0`、active simulation PIDs 为空、可用内存 `122.95 GiB`、空闲盘 `5522.7 GiB`；资源和活动门槛通过。后续两格完成后控制器自动进入下一个并发组。
5. **结果解释边界：** 目前只有一个独立需求 seed 且 ClassReserve 尚未运行；这些完成格只证明当前 seed 的正确性与输入/收据链路。不得据四格做模式排名、独立变异估计、收益或 NO-GO 判断。主指标仍按冻结规则在全矩阵终态后，以四个 demand seed 为配对单位统一汇总。
6. **继续与停止规则：** 实际模型保持 GPT-6 Luna High；runner 使用 cap=2、每格启动前检查远端 trace SHA、约半小时读取运行状态，资源 watcher 持续采样。任何校验/运行/资源失败时停止新格并保留 ID/raw，不复用失败身份；若资源健康则按已冻结顺序继续。其余 24 格、矩阵级验证和分析均未完成，WS-25 保持 ACTIVE。
7. **前序失败身份：** r1 两格由于实验源码 SHA 不含新 trace，在 ns-3 启动前失败；r2 两个 build 请求由于远端源码缓存缺少固定 SHA 而无远端实验目录。失败原因与修复见[Handoff 63](2026-10-03-63-ws25-calibration-r1-input-source-mismatch.md)和[Handoff 64](2026-10-03-64-ws25-calibration-r2-sync-and-r3-freeze.md)。两批 ID 均保留，既不是 ClassReserve 的效果失败，也不混入 r3。
8. **后续研究门槛：** r3 校准后仍需完成预设 0/64/128 档约束、量化跨需求波动，并在任何最终矩阵启动前冻结双侧数值判据、样本量、统计方法、ID 和停止条件。WS-21 状态反馈/心跳保持投稿后第二课题边界；历史 NO-GO 不改判。
9. **CONTEXT SNAPSHOT：** 校准计划 r3 已启动，首个 seed block 前四个原始模式 4/4 verifier 通过，无资源越线；ClassReserve 与 diag 控制及其余三 seed 尚未完成。当前自动监督仍在 Luna High；28 格终态回传后实际切 Sol High 统一分析，不等待人工确认。
