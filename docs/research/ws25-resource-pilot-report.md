# WS-25 远端资源吞吐试跑结果

日期：2026-10-03。固定仿真 SHA `a656104d05c681f9b3a998b5ef4ce3e644558d02`、拓扑 SHA `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`；运行器/计划由 `bad49fd2bd7e7aa6e02d9d1b9ee12c088ab42cba` 固定。试跑只测资源和整批吞吐，不作为算法性能证据。

服务器为双路 Xeon Silver 4210R，20 物理核/40 逻辑 CPU，125 GiB 内存、无 swap。开跑前 load 0.0、可用内存 122.92 GiB、空闲磁盘 5504.5 GiB；无活动仿真或其他普通用户进程。全部 24 个副本均使用 seed05–08 已冻结 trace 的全新实验 ID，固定 SHA 和远端 trace 哈希逐格通过；r4 对应主格的 FCT SHA 逐格一致。每个实验均完成 16,576/16,576 流，结果 verifier 24/24 通过，raw、metadata、config、资源样本和 summary 已下载到本机忽略目录 `results/`。远端完成后无在途仿真，可用内存 122.95 GiB。

| 并发格数 | 格数 | 整批墙钟时间 | 吞吐（格/小时） | 最大单格树 RSS | 最低可用内存 | 峰值 load |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 4 | 354.4 秒 | 40.63 | 4561.4 MiB | 105.16 GiB | 4.23 |
| 8 | 8 | 374.8 秒 | 76.85 | 4562.2 MiB | 87.46 GiB | 8.29 |
| 12 | 12 | 439.0 秒 | 98.41 | 4562.1 MiB | 69.76 GiB | 12.52 |

吞吐由 4 到 8 格提升 1.89 倍，由 8 到 12 格再提升 1.28 倍。内存余量随并发近似下降，但 12 格仍比 32 GiB 资源线多 37.76 GiB。预构建 24 份独立源码使远端空闲盘从约 5504.5 降至 5487.3 GiB；仿真三档期间又降约 0.3 GiB，最终约 5487.0 GiB。1 分钟 load 随并发上升，未触及 20 线；它是可运行任务的平滑计数，不等于 CPU 使用率百分比。该测量支持继续阶梯试到 16/18；尚未证明更高档更高效，也不支持把 12 视为最终上限。下一档前须将 worker 白名单上限扩至 16/18，并加入按当前可用内存预测启动后保留至少 32 GiB 的 admission 检查；先运行 16，再根据吞吐和资源决定是否跑 18。不开 20，给 OS、SSH 和后台服务留下物理核与内存余量。

机器明细：从 24 个实验 ID 的原始文件独立重算的[机器分析](evidence/ws25-resource-pilot-analysis.json)；忽略目录 `results/ws25-resource-pilot-summary.json` 和 `results/ws25-resource-pilot-receipts.jsonl` 保留原始运行器收据。逐格 ID 在[冻结计划](evidence/ws25-resource-pilot-plan.json)，复算入口 `scripts/analyze_ws25_resource_pilot.py`。本轮不是正式 WS-25 矩阵；正式实验仍需完成校准分析、0/64/128 档约束、双侧判据、样本量和最终 IDs/SHA/trace 冻结。
