# 下一阶段路线与停机条件

更新：2026-09-25。集成工作流只维护顺序和证据门槛；具体代码和实验在对应 workstream 执行。参照 [CURRENT_STATE.md](CURRENT_STATE.md) 的实时快照，在执行前再核验 Git 与远程资源。最新研究筛选见 [Handoff 07](../handoffs/2026-09-25-07-ant-project-experience.md) 和 [ADR-006](../decisions/ADR-006-conditional-guardhash-selection.md)。

已完成的前置核验：**WS-06 输入兼容**见 [Handoff 06](../handoffs/2026-09-24-06-six-column-input-and-tags.md)；**WS-07 最小双轨与单 seed 技术 pilot**见 [Handoff 08](../handoffs/2026-09-25-08-ws07-dual-track-mixtax.md)；**WS-08 接收尾流诊断与共享 IRN 单 seed pilot**见 [Handoff 09](../handoffs/2026-09-25-09-ws08-receiver-gate.md)。完整 16,384 条 MoE trace、固定总字节 0/2/4 和五独立 seed 尚未仿真。

1. **接收语义门槛，技术诊断已完成：**`20260925-210024-ws08-nack-diagnostic@c8ca6a6` 逐流记录原四条 4 ms 尾流均触发最后 192 B 未确认的 4 ms RTO。共享 PFC=0、IRN=1、DCQCN 契约在 `445593f` 的 32 主机单/双类与 1280 跨 ToR 小样本完成，四格无超时；旧 PFC 四格与 IRN 四格分开解释。若将 ConWeave 放在导入混合延迟拓扑对照，仍先审计其统一 `one_hop_delay` 时序估计。
2. **单 seed MixTax 门槛，当前负向：**共享 IRN 四格 `20260925-211439-ws08-irn-flow0`、`20260925-210820-ws08-irn-packet0`、`20260925-212042-ws08-irn-flow64`、`20260925-212745-ws08-irn-packet64` 的 MoE 批次依次为 1.415/1.415/1.625/1.572 µs，交互 `−0.053 µs`（`−3.7456%`），背景 P99 差为 0。参见 [机器摘要](../research/ws08-irn-pilot-summary.json)。没有达到预先的正向 5% 信号；它也不足以证明其他 seed 无损害。
3. **当前 Go / No-go：**固定总字节 0/2/4 设计样本只完成哈希/字节静态验证，五个独立 trace seed 未运行。当前不扩大实验、不实现 GuardHash/HarmGate；保存负结果和评估资产。若重启，先提出新可证伪条件并冻结资源预算、共享传输、固定目标/总字节与 seed 列表，再按 [实验契约](../research/ws07-dual-track-contract.md) 跑正式配对并逐项通过门槛，不追逐已见数据调参。
4. **条件性后续机制：**若未来出现稳定、可解释且实际有意义的双侧损害，再检验本地类别占用信号相对普通两选短队列的增量，之后比较始终共享、静态隔离与可核查的 APS/FLB-like 强对照。若收益只来自额外即时信息、参数或牺牲背景流，应缩小或放弃机制主张；边界实验排在其后。

本路线记录研究顺序与门槛；后续工作流按用户指示启动，不因台账状态自动开始代码或远程实验。
