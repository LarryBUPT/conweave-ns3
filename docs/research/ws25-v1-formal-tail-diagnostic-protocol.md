# WS-25 v1 正式反例的非扰动诊断复跑协议

冻结日期：2026-10-06。性质：**已揭盲正式 seed 的事后机制诊断**，不增加确认性样本，不改变 v1 的 NO-GO，也不充当 v2 正式验证。目的只是在已见反例中核查背景尾流的逐跳等待、出口队列和逐 QP 反馈是否与终点 FCT 对齐，从而决定新候选需要的可观测信号。

## 固定身份与对照

沿用正式仿真与输入提交 `ce699dffe2845dc83e2171a1c309c6d96b96d2b3`、拓扑 SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba` 和正式共同参数：ns-3 seed 1、PFC=0、IRN=1、DCQCN、400 Gbps、buffer=9 MiB、`simul_time=0.01`、`netload=10`。每格算法均为 `classreserve`，唯一变化是将 `--ws25-diag 0` 改为 `--ws25-diag 1`，启用既有诊断日志。[机器计划](evidence/ws25-v1-formal-tail-diagnostic-plan.json)保存下表身份与参数；每格新建独立构建/结果目录，不读取或覆盖正式 ID 的远端 raw。

| 诊断新 ID | 需求与输入文件 SHA-256 | 正式 ClassReserve 原 ID 与 FCT SHA-256 |
| --- | --- | --- |
| `20261006-180000-ws25-v1diag-s43-b064-classreserve` | seed `20262543`、64 背景；`ws25_seed20262543_b64.txt`，`035228c6e0e5c235e31200d70ab413c1a587f8301437d8e6f180756a264d12aa` | `20261004-070000-ws25-formal-s43-b064-classreserve`，`02bbd3324a22a9a1cb128efb0bf4f8a9319bb068f7f21ed2797902ed35a2980c` |
| `20261006-180001-ws25-v1diag-s24-b192-classreserve` | seed `20262524`、192 背景；`ws25_seed20262524_b192.txt`，`d72f0f360d89dd3504c4cba730d903e1d939400ff2abd3566cf0428f4e59e2e3` | `20261004-070000-ws25-formal-s24-b192-classreserve`，`aadffa71291fbaf6fab0fce7635b54bad0f3729fdb59c5841c817c3ba99acb8e` |

## 准入、运行与停止线

运行前单次远端 host gate 核对无其他用户作业、未知 ns-3/worker 或持锁进程，load 1m≤20、MemAvailable≥32 GiB、空闲盘≥100 GiB。每个新构建按 `-j2`，诊断仿真先 cap=1；第二格只有在首格逐项通过且再次核对 host gate 后才启动。每 worker 预留 5 GiB 后仍须至少 32 GiB 可用；RSS≤32 GiB。后台静默运行，阶段性只核对简要资源/异常收据。SSH 观察超时不代表远端终止；先查原 ID 状态和在途进程，绝不为同 ID 重复构建/启动。出现资源线、他人作业、缺失流或身份失配即停开新格，保存原始 ID 与日志。

单格必须 `SUCCEEDED`、metadata 源码/拓扑/trace/参数哈希一致、全部 `16,384 + background` 输入流完成、ClassReserve 类别队列守恒且无 drop/违规，并回传 `config.log`、FCT、`WS25_QP`、`WS13_HOP`、`WS13_INFLIGHT`、资源样本及其他 raw。将诊断 FCT SHA 与上表正式同输入 ClassReserve FCT SHA **逐字节比较**；若不同，将该格诊断标为有扰动，禁止用其逐跳/反馈解释正式 FCT。即使相同，也只支持这两个输入下的非扰动，不自动推广到其他需求。

## 预先规定的诊断读法

先在正式原始 FCT 中识别背景尾流：seed43/b64 的目的主机 `1040/1052` 共属 ToR `1408`，seed24/b192 的目的主机 `1176` 属 ToR `1412`。诊断通过 trace 顺序所定的 `flow_id` 将同一 `src,dst,sport,dport` 的尾流映射到 `WS25_QP` 反馈，再读取目的 ToR→主机 `WS13_HOP` 等待和排队字节，并与非尾流及源 ToR 上联记录并列。检查这些计数是否非零、是否同方向，但不把逐跳汇总峰值相加成 FCT，不把 ECN/CNP 计数当重传，不能因单流同现判因果。若日志缺完整时序，明确保留该缺口，之后另设计非扰动时序探针。

解释完成后，只允许据此**提出** v2 的具体可控路径和失败预测；v2 必须使用全新 SHA/ID、独立筛选及校准，以及未揭盲的正式需求 seed。第二课题状态反馈不在本次诊断范围。

## 2026-10-06 资源收据恢复附记

首格 `20261006-180000-ws25-v1diag-s43-b064-classreserve` 已终态 `SUCCEEDED` 并回传；其 FCT SHA 与上表正式同输入 ClassReserve 完全相同，原始诊断 `config.log` 存在。但该次启动前未建立逐运行资源采样，远端和回传结果均缺 `resource-samples.jsonl` 与 `resource-summary.json`。因此它保留为未完整验收的技术复跑，不用于满足本协议的诊断验收。不能事后补造资源采样，也不覆盖原 ID/raw。

独立[恢复计划](evidence/ws25-v1-tail-diagnostic-recovery-plan.json)固定同输入、同源码、同参数的新 ID `20261006-180002-ws25-v1diag-s43-b064-classreserve-r1`。先核对该 ID 不存在、远端无人作业且通过资源门；构建后核对 trace/源码；**在仿真启动前确认资源 watcher 已开始写样本**，再以 cap=1 运行。新格完成、回传并逐项验收后，才启动原计划尚未创建的第二格。恢复计划仅修补诊断运行的收据，不改变已冻结的 576 格正式矩阵或 v1 NO-GO。
