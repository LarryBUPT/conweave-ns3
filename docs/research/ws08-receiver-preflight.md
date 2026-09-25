# WS-08 前置门槛：逐包尾流与共同接收契约

日期：2026-09-25。本文记录技术诊断和待检验契约；它不授予 GuardHash/HarmGate 实现许可。以各实验 ID 的 `metadata.json`、`config/traffic_trace.txt`、原始 FCT、CNP、`raw/<raw ID>/config.log` 为证据。WS-07 冻结判据见 [双轨契约](ws07-dual-track-contract.md)，机制门槛见 [ADR-006](../decisions/ADR-006-conditional-guardhash-selection.md)。

## 原始尾流诊断

WS-07 的 packet0 `20260925-053000-ws07-pilot-bg0-packet` 固定源码 `8c99e5407ef41d14a6b67fc7dad55aada273946a`，256 条 8 KiB MoE 流全部完成，但 4 条 FCT 为 4,002,086–4,002,653 ns，其余 252 条不超过 2,758 ns。该格的原始 FCT SHA-256 为 `dd922036f6b15f0aee324c9bf9ca1b3c0d4141bc78a3becb655bbdd8004f085e`，trace SHA-256 为 `d60ca03e36f1607328f7af0e79b39f4c9bf74cd0feca8d59f1283de56d778560`。

只加日志、不改接收或选路语义的复跑为 `20260925-210024-ws08-nack-diagnostic`，源码 `c8ca6a601dd4380bae36233053b654307d61d292`、raw ID `647767531`。其原始 FCT SHA-256 与 WS-07 packet0 **逐字节相同**；日志 SHA-256 为 `82106084907be4dcb21eefc2c844f8a114713605bf49ee0ae26f1fd50c9ec707`。日志记录 601 个接收端乱序 NACK、571 个发送端 NACK 和恰好 4 个发送端超时。超时 flow ID `255, 155, 240, 91` 分别对应上述四条尾流；发生在 `2.004001576, 2.004001751, 2.004002082, 2.004002143 s`，均为 `rto_ns=4000000`、`snd_una=8000`、`snd_nxt=8192`。四者此前均有接收端乱序 NACK 和发送端 NACK。源数据支持：最后 192 B 未获累计确认后由 4 ms RTO 驱动恢复，足以解释此 pilot 的批次尾部。它不能证明网络中不存在其他丢失机制。

源码路径：`RdmaHw::ReceiverCheckSeq` 对 `seq>expected` 的非 IRN 包生成 NACK，并不保存乱序负载；`ReceiveAck` 的非 IRN NACK 调 `RecoverQueue` 将 `snd_nxt` 回退到 `snd_una`；`PktSent` 每次发送重置重传计时器；`HandleTimeout` 再次调用 `RecoverQueue`。`RdmaQueuePair` 默认 `m_timeout=4 ms`。`ReceiverCheckSeq` 的乱序 NACK 还置 CNP，故 WS-07 的 OoO CNP 与此路径一致，但 CNP 数不是重传数。

## 候选的共同传输/接收契约

先使用仓库已有的 **PFC=0、IRN=1** 模式做敏感性实验，`fecmp` 与 `dualtrack`、tag=1 与 tag=2 **全部使用同一配置**：DCQCN (`CC_MODE=1`)、`L2_ACK_INTERVAL=1`、1,000 B payload、同一拓扑、trace 文件、模拟 seed=1 和 BDP 推导。IRN 的接收端对乱序段登记 SACK，发送端从 SACK 恢复；scratch 在此拓扑配置 RTO low/high 为 100/320 µs，PFC 关闭后超时不被 IRN 的 PFC 分支禁用。每格须在元数据和 `config.txt` 中逐项核对该契约，不给 tag=2 单独改变接收能力。IRN 路径仍可能因乱序置 CNP，故需报告 CNP、超时和包数；PacketTag 不产生线上字节开销。

该契约是**待比较的新传输条件**，不能与 WS-07 的 PFC=1、IRN=0 四格混算交互。若无背景逐包批次仍由少数超时流决定，或任一格未全数完成，则保留此负结果并停在接收门槛。若先导可行，重做 32 主机两单类/双类、1280 跨 ToR 双类正确性及同一 trace 的 packet/flow × 背景 0/64 四格，再检查固定总字节 0/2/4 资源样本。只有随后冻结 5 个独立 trace seed 并满足 WS-07 契约的 4/5 同向、中位归一化交互 ≥5%、背景 P99 恶化 ≤5% 和各类 100% 完成，才评估 ADR-006 的 GuardHash 条件。单 seed 的正负数值只作技术诊断。

## 先导观察

`20260925-210820-ws08-irn-packet0`，源码 `445593fbc07236e18983d233407265220d360521`、raw ID `655381919`，与上面相同 trace：256/256 完成，合成批次 1.415 µs，P99 FCT 1.36135 µs，最长 FCT 1.415 µs，原始 FCT 中没有超过 10 µs 的流；`config.log` 记录 `packet_multipath=3298`，所以逐包多路径入口仍被触发。该结果单独只检验新契约的一个无背景格；四格配对见下节。

## 同一 IRN 契约的四格复跑

四格均为 `445593fbc07236e18983d233407265220d360521`、PFC=0、IRN=1、DCQCN、seed=1、相同拓扑及阈值。配对脚本 `scripts/compare_ws07_mixtax.py` 核验公共配置、同档 trace SHA、跨档 MoE 子 trace 和全部完成记录，机器摘要见 [ws08-irn-pilot-summary.json](ws08-irn-pilot-summary.json)。原始数据在各 `results/<ID>/`（Git 忽略）。0 档 trace SHA-256 为 `d60ca03e36f1607328f7af0e79b39f4c9bf74cd0feca8d59f1283de56d778560`，64 档为 `cbfa0e5a95b7c3b6b56dfd563e855dff8b83f4f54db2747909039285184f58e1`。

| 格 | 实验 ID / raw ID | MoE 完成 | MoE 批次 µs | 背景完成与 P99 µs | OoO CNP / 超时 |
| --- | --- | ---: | ---: | --- | ---: |
| flow0 | `20260925-211439-ws08-irn-flow0` / `766028927` | 256/256 | 1.415 | 无背景 | 0 / 0 |
| packet0 | `20260925-210820-ws08-irn-packet0` / `655381919` | 256/256 | 1.415 | 无背景 | 0 / 0 |
| flow64 | `20260925-212042-ws08-irn-flow64` / `393633748` | 256/256 | 1.625 | 64/64；688.41974 | 0 / 0 |
| packet64 | `20260925-212745-ws08-irn-packet64` / `568818908` | 256/256 | 1.572 | 64/64；688.41974 | 1516 / 0 |

四格原始 FCT 行数依次为 256/256/320/320，PFC 原始文件均为空。packet0/packet64 的源 ToR 多下一跳计数为 3298/3492；packet64 的 OoO CNP 存在，但背景 P99 不变。四格绝对交互量 `−0.053 µs`，以 packet0 批次归一化为 `−3.7456%`；背景 P99 的 packet−flow 为 `0 µs`。这是**单 trace seed 的加背景技术 pilot**，不满足预设的正向 ≥5% 损害方向，也不能推断任何跨 seed 的无效性。旧 PFC pilot 与本 IRN pilot 的传输条件不同，不合并统计。

固定总字节 0/2/4 manifest 的静态哈希与字节检查由 `scripts/verify_ws07_traces.py` 再次通过，但这些样本尚未仿真。鉴于本技术 pilot 没有达到 WS-07/ADR-006 的进入信号，当前决定 **不启动**固定负载扩大运行、五个独立 trace seed 正式实验或 GuardHash v0；保留设计样本与上述负结果供后续提出新假设时复用。此决定是当前证据下的阶段性 no-go，不声称已经证明所有条件下不存在 MixTax。

## 正确性复核

同一固定源码 `445593fbc07236e18983d233407265220d360521` 下，32 主机 fat-tree 的 tag=1 单类 `20260925-213355-ws08-irn-small-flow` 4/4 完成；tag=2 单类 `20260925-214018-ws08-irn-small-packet` 4/4，逐包多下一跳计数 276、缺失 tag 包 0；双类 `20260925-215232-ws08-irn-small-dual` 两类各 2/2，逐包多下一跳 24、缺失 tag 包 0。导入 1280 拓扑的跨 ToR 双类 `20260925-214621-ws08-irn-cross-four` 两类各 2/2，逐包多下一跳 24、缺失 tag 包 0。按流单类和同 trace 的 `fecmp` 对照 `20260925-215842-ws08-irn-small-fecmp` 原始 FCT SHA-256 均为 `50eff7c6a0303b2fd91980f737cb8b801857e687942c125ce7a5165b68004d0e`；配对的拓扑、trace SHA、seed 与 PFC/IRN 参数相同。小样本只证明路径和完成，不用于性能排序。
