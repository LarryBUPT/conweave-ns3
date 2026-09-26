# 下一阶段路线与停机条件

更新：2026-09-26。集成工作流只维护顺序和证据门槛；具体代码和实验在对应 workstream 执行。参照 [CURRENT_STATE.md](CURRENT_STATE.md) 的实时快照，在执行前再核验 Git 与远程资源。研究筛选见 [ADR-006](../decisions/ADR-006-conditional-guardhash-selection.md)；用户要求的提前工程原型见 [ADR-007](../decisions/ADR-007-guardhash-prototype-before-efficacy.md)。

已完成的前置核验：**WS-06 输入兼容**见 [Handoff 06](../handoffs/2026-09-24-06-six-column-input-and-tags.md)；**WS-07 最小双轨与单 seed 技术 pilot**见 [Handoff 08](../handoffs/2026-09-25-08-ws07-dual-track-mixtax.md)；**WS-08 接收尾流诊断与共享 IRN 单 seed pilot**见 [Handoff 09](../handoffs/2026-09-25-09-ws08-receiver-gate.md)；**WS-09 可关闭原型与技术核验**见 [Handoff 10](../handoffs/2026-09-26-10-ws09-guardhash-prototype.md)；**WS-10 固定总字节 0/2/4、五独立 seed 正式现象复核**见 [Handoff 11](../handoffs/2026-09-26-11-ws10-fixed-load-formal.md)。完整 16,384 条 MoE trace 仍未全量仿真，不与 WS-10 的抽样固定负载混同。

1. **接收语义门槛，技术诊断已完成：**`20260925-210024-ws08-nack-diagnostic@c8ca6a6` 逐流记录原四条 4 ms 尾流均触发最后 192 B 未确认的 4 ms RTO。共享 PFC=0、IRN=1、DCQCN 契约在 `445593f` 的 32 主机单/双类与 1280 跨 ToR 小样本完成，四格无超时；旧 PFC 四格与 IRN 四格分开解释。若将 ConWeave 放在导入混合延迟拓扑对照，仍先审计其统一 `one_hop_delay` 时序估计。
2. **单 seed MixTax 门槛，当前负向：**共享 IRN 四格 `20260925-211439-ws08-irn-flow0`、`20260925-210820-ws08-irn-packet0`、`20260925-212042-ws08-irn-flow64`、`20260925-212745-ws08-irn-packet64` 的 MoE 批次依次为 1.415/1.415/1.625/1.572 µs，交互 `−0.053 µs`（`−3.7456%`），背景 P99 差为 0。参见 [机器摘要](../research/ws08-irn-pilot-summary.json)。没有达到预先的正向 5% 信号；它也不足以证明其他 seed 无损害。
3. **WS-09 工程原型，已按范围完成：**个人 fork `feature/ws09-guardhash-prototype` 冻结并实现普通短队列两选、类别感知两选与 HarmGate 门控开/关；真实出口队列的 per-port/per-tag 计数、32 主机单/双类、1280 跨 ToR、旧 `fecmp/dualtrack` 回归和同 trace 三格 pilot 已核验。压力格触发两类 MMU 准入丢包并守恒；队列拒绝/清队列尚未动态覆盖。见 [Handoff 10](../handoffs/2026-09-26-10-ws09-guardhash-prototype.md)。这一步不宣称 MixTax 存在或算法有效。
4. **WS-10 现象实验，已完成且 no-go：**[预注册 v1.1](../research/ws10-fixed-load-prereg-v1.md) 在新效果运行前冻结共同传输、固定目标/总字节、五 trace seed、资源预算和判据。六格 pilot 与 30 格正式配对均完成，全类 100% 完成且背景安全通过；主 4 档只有 1/5 正向，中位数 −1.3947%，未达到 4/5 与 ≥5% 门槛。2 档五 seed 均正而 4 档多数负，明确保留非单调结果。见 [报告](../research/ws10-fixed-load-formal-report.md)。
5. **WS-11 等信息效果评估，当前门槛未满足：**不能从 WS-10 当前场景升级 GuardHash 效果主张。若后续独立新场景重新预注册并达到稳定损害门槛，再对比普通短队列双候选、类别感知 GuardHash、HarmGate 门控开/关，以及始终共享、静态隔离和可核查 APS/FLB-like 强对照；同时检查 MoE、背景两侧和类别信号增量。
6. **WS-12 边界与论文整合：**当前可整理 WS-10 负结果、2/4 档非单调性、接收/重传解释性证据和适用边界。若未来新场景支持机制增量，再测错标、反馈延迟、路径不对称、资源/标签开销与不同拓扑。所有图表指向固定 SHA、实验 ID 和原始数据；不声称真实硬件验证。

本路线记录研究顺序与门槛。WS-09 工程范围和 WS-10 预注册现象复核均已闭环；后续工作流按阶段 Handoff 与用户指示创建，不因台账状态自动创建对话。
