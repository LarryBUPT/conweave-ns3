# WS-26：WS-25 反例的 ECMP 配对诊断协议

冻结日期：2026-10-07。性质：已揭盲 WS-25 需求的事后机制诊断。该诊断只补齐 ECMP 同粒度原始观测，不增加 WS-26 正式样本，也不改变 WS-25 的 NO-GO。

## 固定输入与身份

沿用 WS-25 正式源码 `ce699dffe2845dc83e2171a1c309c6d96b96d2b3`、OS1 拓扑 SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`、ns-3 seed 1、PFC=0、IRN=1、DCQCN、400 Gbps、9 MiB 缓冲、`simul_time=0.01` 和 `netload=10`。模式固定为 `fecmp`。相对相应正式 ECMP 格，唯一配置差异是 `--ws25-diag 1`，用于输出已有的逐 QP 与逐跳诊断。候选 ClassReserve 的相同输入诊断已在 [WS-25 尾流报告](ws25-v1-formal-tail-diagnostic-analysis.md)验收。

| 新诊断 ID | 输入 | trace SHA-256 | 原 ECMP ID | 原 FCT SHA-256 |
| --- | --- | --- | --- | --- |
| `20261007-170000-ws26-ecmpdiag-s43-b064` | `ws25_seed20262543_b64.txt`，16,448 流 | `035228c6e0e5c235e31200d70ab413c1a587f8301437d8e6f180756a264d12aa` | `20261004-070000-ws25-formal-s43-b064-fecmp` | `2447c24415711a30e025a04df23319ad36871061ea40d312775a92617e793cb8` |
| `20261007-170001-ws26-ecmpdiag-s24-b192` | `ws25_seed20262524_b192.txt`，16,576 流 | `d72f0f360d89dd3504c4cba730d903e1d939400ff2abd3566cf0428f4e59e2e3` | `20261004-070000-ws25-formal-s24-b192-fecmp` | `48453a24b8c32fdd0d44bea7bfefbf40fcfb4cf96ac05a1c5e9cba544e70b834` |

## 准入与验收

副对话是唯一远端 runner。启动前核对这两个新 ID 均不存在、远端无其他作业或持锁进程，且 CPU、内存、磁盘和 SSH 健康。先以固定源码和 cap=1 构建、运行第一格；该格通过后再开第二格。每格运行前启动资源采样，保存原始 metadata、配置、日志、FCT、CNP、PFC、uplink、`WS25_QP`、`WS13_HOP`、`WS13_INFLIGHT` 与资源摘要。1 分钟 load 须 ≤20，可用内存 ≥32 GiB，空闲盘 ≥100 GiB，单格树 RSS ≤32 GiB。

逐格要求 `SUCCEEDED`、源码/拓扑/trace/参数哈希匹配、全部输入流完成、raw 唯一且可解析、资源收据齐备。诊断 FCT SHA 必须逐字节等于表中原 ECMP FCT SHA；不一致即标记为受扰动，不用其日志解释 WS-25 正式 FCT。SSH 或回传超时先查原 ID、PID 和 raw；不得用同 ID 重建或覆盖旧数据。任何资源异常、其他作业、缺流或身份失配均暂停新格并保留证据。

## 分析边界

先按同一流身份比对 ECMP 与 ClassReserve 的最慢背景 QP，再比较上游端口、目的 ToR→主机出口、每 QP CNP/乱序/重复发送/超时和逐跳最大等待。`WS13_HOP` 是每 QP×每跳的汇总，不能给出包级时间因果；CNP 计数也不是延迟分量。如果两格仍无法区分首次路径与共同末跳，应补有界、非扰动的时间对齐探针，再冻结新候选。诊断只用于形成可证伪假说，不用已见 seed 调参或宣称 WS-26 收益。
