# 下一阶段路线与停机条件

更新：2026-09-26。集成工作流只维护顺序和证据门槛；具体代码和实验在对应 workstream 执行。参照 [CURRENT_STATE.md](CURRENT_STATE.md) 的实时快照，在执行前再核验 Git 与远程资源。研究筛选见 [ADR-006](../decisions/ADR-006-conditional-guardhash-selection.md)；用户要求的提前工程原型见 [ADR-007](../decisions/ADR-007-guardhash-prototype-before-efficacy.md)。

已完成的前置核验：**WS-06 输入兼容**见 [Handoff 06](../handoffs/2026-09-24-06-six-column-input-and-tags.md)；**WS-07 最小双轨与单 seed 技术 pilot**见 [Handoff 08](../handoffs/2026-09-25-08-ws07-dual-track-mixtax.md)；**WS-08 接收尾流诊断与共享 IRN 单 seed pilot**见 [Handoff 09](../handoffs/2026-09-25-09-ws08-receiver-gate.md)。完整 16,384 条 MoE trace、固定总字节 0/2/4 和五独立 seed 尚未仿真。

1. **接收语义门槛，技术诊断已完成：**`20260925-210024-ws08-nack-diagnostic@c8ca6a6` 逐流记录原四条 4 ms 尾流均触发最后 192 B 未确认的 4 ms RTO。共享 PFC=0、IRN=1、DCQCN 契约在 `445593f` 的 32 主机单/双类与 1280 跨 ToR 小样本完成，四格无超时；旧 PFC 四格与 IRN 四格分开解释。若将 ConWeave 放在导入混合延迟拓扑对照，仍先审计其统一 `one_hop_delay` 时序估计。
2. **单 seed MixTax 门槛，当前负向：**共享 IRN 四格 `20260925-211439-ws08-irn-flow0`、`20260925-210820-ws08-irn-packet0`、`20260925-212042-ws08-irn-flow64`、`20260925-212745-ws08-irn-packet64` 的 MoE 批次依次为 1.415/1.415/1.625/1.572 µs，交互 `−0.053 µs`（`−3.7456%`），背景 P99 差为 0。参见 [机器摘要](../research/ws08-irn-pilot-summary.json)。没有达到预先的正向 5% 信号；它也不足以证明其他 seed 无损害。
3. **WS-09 工程原型，立即推进：**在个人 fork 的新 feature 分支冻结 HarmGate 激活/退出条件和 GuardHash 双候选评分，先做 per-port/per-tag 队列字节统计及守恒检查，再实现普通短队列两选、类别感知两选和门控开/关消融。背景/控制包保持原路径；沿用共享 PFC=0/IRN=1、DCQCN。32 主机、1280 跨 ToR 正确性与有限资源 pilot 先证明能运行、能观测、可配对；这一步不宣称 MixTax 存在或算法有效。
4. **WS-10 现象实验，预注册后运行：**固定总字节 0/2/4 样本先做资源 pilot；在看原型收益之前冻结新可证伪条件、预算、共同传输、目标集合、五个独立 trace seed 和判据。同一 seed 内复用完全相同 trace。若缺 4/5 同向、归一化交互中位数 ≥5%、全类完成率 100% 或背景安全条件，保留负结果，不升级机制主张。
5. **WS-11 等信息效果评估：**仅在 WS-10 的适用场景满足门槛时，对比普通短队列双候选、类别感知 GuardHash、HarmGate 门控开/关，以及始终共享、静态隔离和可核查 APS/FLB-like 强对照。检查类别信号是否真有增量，并同时报告 MoE、背景两侧；收益若只来自额外信息、调参或牺牲背景流则停止主张。
6. **WS-12 边界与论文整合：**成立时再测错标、反馈延迟、路径不对称、资源/标签开销与不同拓扑；不成立时总结当前负结果及接收/重传解释性证据。所有图表指向固定 SHA、实验 ID 和原始数据；不声称真实硬件验证。

本路线记录研究顺序与门槛。WS-09 已由用户本轮要求启动；后续工作流按阶段 Handoff 与用户指示创建，不因台账状态自动创建对话。
