# ADR-006：以双侧损害诊断为门槛选择 GuardHash v0

状态：Accepted for research planning，机制实现仍为 conditional。日期：2026-09-25。

## Decision

继续研究 HarmGate 所指的包/流共存跨类损害；从已有候选中，仅把 GuardHash 的本地双候选规则列为优先原型。WS-07 先在共同传输与接收语义下测背景流对 MoE 同步批次的影响，同时检查 MoE 逐包选路对背景流的代价。只有损害可重复且普通短队列二选一等强对照不能解释类别信号的增量，才在 WS-08 实现并评估 GuardHash v0。

## Rationale

「ANT项目经验」对话要求在相同背景下从仓库已有方案筛选，减少流量、拓扑、传输和指标反复变化造成的试错。静态画像显示四份输入为同一批 MoE 流加不同数量的背景大流；聊天记录优先追问 MoE 在背景增加时的劣化，而旧 GuardHash 草案主要写作保护背景流。双侧观测可检验受害方向，也能防止只改善 MoE 而转嫁成本。证据与方案见论文项目 `docs/research/12-screenshot-lessons-and-mechanism-selection.md` 和 [Handoff 07](../handoffs/2026-09-25-07-ant-project-experience.md)。

## Alternatives considered

- 直接实现旧 GuardHash 目标或按一次 P99 表格确定受害方向：缺乏固定输入与共同传输下的双侧原始数据。
- Inflex 多跳 probe、PhaseSalt、BorrowHash 或整套 MixHash 传输/重排移植：增加状态与混杂，且已有近邻机制；暂缓。
- AnchorHash：可作为简单基线/消融，不优先建立复杂预测器。

## Consequences

此 ADR 只冻结研究筛选与 go/no-go 门槛，不确认 GuardHash 有效、创新或已获实现授权。WS-07 先解决 MoE `2.000s` 流被默认 `2.005s` FCT 窗口排除的问题，建立按 tag 的输入、完成和未完成统计，并配对比较 packet/flow × 背景 0/64；正式比较需要固定总负载 trace 与独立 trace seed。若损害不稳定、类别信号无增量或收益依赖改变 PFC/IRN 等共同语义，应停止机制主张。
