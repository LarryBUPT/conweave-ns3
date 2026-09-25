# 下一阶段路线与停机条件

更新：2026-09-25。集成工作流只维护顺序和证据门槛；具体代码和实验在对应 workstream 执行。参照 [CURRENT_STATE.md](CURRENT_STATE.md) 的实时快照，在执行前再核验 Git 与远程资源。最新研究筛选见 [Handoff 07](../handoffs/2026-09-25-07-ant-project-experience.md) 和 [ADR-006](../decisions/ADR-006-conditional-guardhash-selection.md)。

已完成的前置门槛：**WS-06 输入兼容**见 [Handoff 06](../handoffs/2026-09-24-06-six-column-input-and-tags.md)；**WS-07 最小双轨与单 seed 技术 pilot**见 [Handoff 08](../handoffs/2026-09-25-08-ws07-dual-track-mixtax.md)。完整 16,384 条 MoE trace 尚未仿真，固定总字节设计样本尚未运行。

1. **WS-07 共同接收语义门槛：**现有 `dualtrack` 与 `fecmp` 共享 DCQCN、PFC=1、IRN=0 和原 RNIC NACK/重传，32 主机与跨 ToR 四流正确性已通过。单 seed pilot 中逐包无背景的 MoE 合成批次约 4002.653 µs，按流仅 1.415 µs；伴随 OoO CNP，但具体致因未隔离。先从原始序号、NACK、CNP、重传与计时器路径定位长尾，再决定两类/两算法共同的接收契约，并重跑正确性及四格 pilot。若在导入混合延迟拓扑对照 ConWeave，先审计统一 `one_hop_delay` 估计。
2. **WS-07 正式双向 MixTax：**现有 packet/flow × 背景 0/64 四格仅为一个 trace seed 的加背景技术 pilot：MoE 绝对交互 +2.038 µs，占逐包无背景批次的 0.0509%；背景 P99 未恶化，不能据此推出稳定跨类损害。后续用已静态验证但未仿真的固定目标、固定总字节 0/2/4 设计样本检验资源与语义，再冻结正式 seed 列表与预算。按 [实验契约](../research/ws07-dual-track-contract.md) 用 5 个独立 trace seed 配对，报告全类完成率、PFC/CNP、重传和 uplink；不可用单 seed 流数替代重复数。
3. **Go / No-go：**共同语义、固定字节和多 seed 判据全部通过才考虑 WS-08。若预定条件下没有稳定、可解释且有实际意义的跨类损害，停止把 GuardHash/HarmGate 当主论文机制；保留负结果与评估资产。
4. **WS-08 GuardHash v0 与强对照：**先检验本地类别占用信号相对普通两选短队列的增量，再与始终共享、静态隔离及可核查的 APS/FLB-like 实现比较。若收益只来自额外即时信息、调参或牺牲背景流，应缩小或放弃机制主张。最后再做拓扑不对称、反馈延迟、错标和资源开销边界实验。

本路线记录研究顺序与门槛；后续工作流按用户指示启动，不因台账状态自动开始代码或远程实验。
