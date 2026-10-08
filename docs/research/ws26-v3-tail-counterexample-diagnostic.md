# WS-26 ClassReserve v3 尾流反例诊断

状态：高档 pilot 双侧效果门失败；登记的 8 格逐 QP/逐跳非扰动诊断已完成。日期：2026-10-08。

## 诊断依据

v2 高档 28 格固定于源码 SHA `593038416fa16f4982b600d256b563260f9106a8`，逐格 raw 与资源验收通过。ClassReserve v3 的 `with_background` 和 `diverted` 四个 seed 均大于零；MoE 批次中位变化为 −0.476%，背景 P99 中位变化为 +2.079%。两项均未达到筛选门槛。低档 24 格因此保持未启动。

原始 `_out_cnp.txt` 按接收主机聚合 ECN/OoO 反馈计数，不按 QP 记录。`RdmaHw::ReceiveUdp` 生成携带 CNP 标志的 ACK/NACK 时增加这些计数；`cnp_freq_monitoring` 定期输出。四个 seed 的 OoO 计数均为 0，PFC pause/resume 事件也均为 0。ClassReserve v3 相对 ECMP 的接收端 ECN 反馈总量变化依次为 −9.34%、+6.13%、−4.19% 和 −12.82%。全局计数在三个 seed 下降，但背景 P99 在三个 seed 上升。

最慢背景 QP 的目的主机在四个 seed 的 ECMP/候选配对中保持一致，分别为 1272、600、1052 和 280。对应接收主机聚合 ECN 计数分别由 944 增至 973、由 467 增至 583、由 1252 降至 1249、由 489 增至 607。它们与尾流变化同现，但不能定位标记交换机、物理队列或单条流的反馈；因此不足以证明末跳或选路因果，也不足以给出某个权重的修正值。

## 一次有界复跑

计划对四个 seed 的 ECMP 与 ClassReserve v3 各运行一格，共 8 格。输入沿用高档 192 背景 trace；源码 SHA、拓扑和传输设置不变，只开启既有 `ws25_diag` 只读观测。全部新 ID、预期 FCT 哈希与参数见[机器计划](evidence/ws26-v3-tail-diagnostic-plan.json)。该组只补逐 QP 与逐跳诊断，不增加 pilot 独立样本数，也不重算效果门。

每格须通过固定 SHA/输入、16,576 个 QP 完成、raw 身份、资源收据和诊断非扰动验收。FCT SHA 必须逐格匹配同 seed、同模式的高档 pilot 原始 FCT。分析须报告背景 QP 的 CNP、OoO、重传/超时计数，以及各交换机/端口的最大排队字节与最大等待时间；CNP 不等于重传次数。失败时停止后续格并保留原始 ID。

## 解释边界与后续门槛

若逐 QP 反馈和逐跳等待把退化集中到可选上游路径，才登记 ClassReserve v3 唯一一次诊断修正，并使用新 SHA 与新 ID 做正确性和独立 pilot。若退化主要落在候选不可控制的路径或接收端聚合状态，不能用调高同目的权重冒充有证据的修正；应转入下一候选的独立设计，或在候选名额上限内形成有边界的负结果。

此复跑仍属于 NS-3 合成需求诊断。即使全部通过，也不构成正式收益证据，不改变 WS-25 的确认性 NO-GO。

## 诊断结果

8 格均完成 16,576/16,576 条流，资源收据通过；各格 FCT SHA-256 与对应 v2 高档格完全相同。四个 seed 的 192 条背景流，其 ClassReserve 源 ToR 端口均与同输入 ECMP 一致。候选最大逐跳等待端口随 seed 变化；CNP 总量在一个 seed 上升、三个 seed 下降。`rx_ooo_packets`、`sack_feedback`、`repeated_sends` 和 `timeout_recovery` 均为 0。

因此，本次诊断没有发现跨 seed 稳定且可控的退化路径，不支持 v3 的唯一调权或路由修正。原始分析、路径索引及证据边界见[Handoff 81](../handoffs/2026-10-08-81-ws26-v3-tail-diagnostic-analysis.md)、[完整分析](evidence/ws26-v3-tail-diagnostic-analysis.json)和[摘要](evidence/ws26-v3-tail-diagnostic-summary.json)。低档和正式矩阵仍关闭；候选名额、门槛和原有高档结果不变。
