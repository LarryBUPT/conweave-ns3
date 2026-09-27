# IRN × PFC 四格技术 pilot：常规输入与 PFC 压力覆盖

日期：2026-09-27。四格因子顺序均为 **IRN、PFC**：00=都关，01=仅 PFC，10=仅 IRN，11=都开。所有八格仿真源码固定 `babd1b90d7c027cd09ac8c7d67380511a92883a6`，DCQCN、ECMP、seed=1；同一场景四格共用字节级相同 trace 与拓扑。各格独立构建和结果目录；原始数据在本机/远程 `results/<实验ID>/`。机器收据由 [`analyze_irn_pfc_factorial.py`](../../scripts/analyze_irn_pfc_factorial.py) 从实验 ID 的原始 FCT、PFC、CNP、`config.log`、配置快照与元数据重算：[常规输入 JSON](evidence/ws13-irn-pfc-factorial-pilot.json)、[压力输入 JSON](evidence/ws13-irn-pfc-factorial-stress.json)。本报告为单输入技术 pilot，不是独立需求重复或正式机制效果验证。

## 256 条 MoE + 64 条背景流：四格可运行，PFC 未触发

输入 `ws07_pilot_s20260925_n256_bg64.txt`，trace SHA-256 `cbfa0e5a95b7c3b6b56dfd563e855dff8b83f4f54db2747909039285184f58e1`，1280 主机 400G 拓扑、9 MiB buffer。256 条 tag=2 为 8 KiB 同启 MoE 流；64 条 tag=1 为 8 MiB 同启背景流。每格两类 **320/320 完成**。

| IRN/PFC | 实验 ID 后缀 | MoE 合成批次 µs | 背景 P99 FCT µs | PFC pause/resume | CNP 事件 | FCT 原始哈希关系 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 00 | `20260927-214400-irnpfc-00` | 1.625 | 1206.598 | 0/0 | 4741 | 与 01 完全相同 |
| 01 | `20260927-214400-irnpfc-01` | 1.625 | 1206.598 | 0/0 | 4741 | 与 00 完全相同 |
| 10 | `20260927-214400-irnpfc-10` | 1.625 | 688.420 | 0/0 | 0 | 与 11 完全相同 |
| 11 | `20260927-214400-irnpfc-11` | 1.625 | 688.420 | 0/0 | 0 | 与 10 完全相同 |

四格 `timeout_recovery`、`IRN+PFC timeout_suppressed` 与现有 NACK 日志计数均为 0。此输入下 PFC 开关没有实际暂停事件；00/01 和 10/11 各自 FCT 相同只说明**这份输入中 PFC 未介入**。背景 P99 的跨 IRN 差约 −518.178 µs 是一个单输入观测，不可解释为普遍平均效果、PFC 动态效果或两个因子完整交互。MoE 合成批次不是八轮真实 job CCT。

## 16×1 MiB 同步 incast：PFC 触发，11 格不完整

为检验动态分支，使用先前 WS-09 压力输入 `ws09_drop_probe_16x1MiB.txt`（SHA-256 `bc2db1513cbde20f12eea6efa4e2265cf74954be4fa45f2a147ff0ce84b33985`）、32 主机 fat-tree 100G、1 MiB buffer。tag=1、tag=2 各 8 条均是 **1 MiB 压力流**，不代表上节 8 KiB MoE/8 MiB 背景业务。PFC 事件原始行的末列 1/0 分别为 pause/resume。CNP 是原始总事件计数；ECN/OoO 可在一次反馈中重叠。

| IRN/PFC | 实验 ID 后缀 | 完成数 | PFC pause/resume | CNP | NACK 发送日志 | 恢复超时 / 被抑制超时 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 00 | `20260927-215700-irnpfcstress-00` | 16/16 | 0/0 | 9442 | 1247 | 0/0 |
| 01 | `20260927-215700-irnpfcstress-01` | 16/16 | 33981/1227 | 3441 | 292 | 0/0 |
| 10 | `20260927-215700-irnpfcstress-10` | 16/16 | 0/0 | 8625 | 0 | 13/0 |
| 11 | `20260927-215700-irnpfcstress-11` | **13/16** | 23295/738 | 3407 | 0 | 0/**3** |

11 格未完成的源主机恰为 13、14、15；`config.log` 的三条 `FACTORIAL_IRN_PFC_TIMEOUT_SUPPRESSED` 恰记录 `flow_id=13/14/15`。这与 `RdmaHw::HandleTimeout` 在 IRN+PFC 时直接返回的源码路径吻合，构成明确的实现失效线索；这份单输入仍不证明所有 IRN+PFC 场景都会失败。11 格只完成流的 P99 不能同其他格作速度排名，未完成流必须列为首要结果。01 格相对 00 格确实触发了 PFC，但暂停事件数不等于独立 pause 周期数，也不能把压力输入的收益外推到 MoE 场景。

**运行器状态陷阱：**这次 11 压力格的旧 worker 仅检查 FCT 文件非空，因此元数据仍写 `SUCCEEDED`，尽管只有 13/16 条流完成。分析脚本以输入 trace 为分母揭示了缺口。后续 worker 已增加 `factorial_pilot` 的输入/完成数门禁：再遇未完成流将保留原始结果并记 `FAILED`，不会以非空 FCT 冒充完整成功；该修复不追溯改写本次原始元数据。

## 对下一步的约束

当前**不能**把四格做成完整效应估计：常规输入 PFC 动态覆盖为零，压力输入的 11 格又有删失。继续研究时应先确定 11 格是要忠实评估当前实现（将完成率作为主要结果），还是设计另一种 IRN+PFC 重传契约；后一种必须是独立的代码版本和实验问题，不可与本次 11 格混称。若要做业务条件下的效应比较，应在同一固定路由模式内，用多个独立重抽 trace 阻断配对、平衡顺序，并同时报告绝对 MoE 批次、背景 FCT/吞吐、完成率及 PFC/反馈/队列事件。当前无可核验业务 SLO，不设置新的通用安全线。WS-10/11/12 各自预注册 no-go 不受本 pilot 影响。
