# WS-25 补充独立校准 v3：远程执行边界

状态：2026-10-03，**仅 18 格校准 pilot**，不开放正式效果矩阵。前置证据为 [C2 seed01 分析](ws25-calibration-seed01-analysis.md)、C2 十二格逐项验证与 [原预飞行协议](ws25-classreserve-audit-and-preflight.md)。本轮只增加预分池中尚未看过结果的需求 seed 02–04；不调整 ClassReserve 算法、流量类型、背景档位或五基线。目标是估计独立需求之间的双侧配对波动、核验五模式和候选在新需求上仍全数完成，并量化乱序/资源的可重复性。单 seed01 的不利观测不得充当正式 NO-GO，也不据其修改数值判据。

## 冻结身份和输入

仿真源码固定为个人 fork `feature/ws25-first-paper@04a5277e8ed464229ef88d28a5d810271ae378fb`。与已运行 C2 `bb10309261b7c5be350fcaab75b4fdb8db95ddca` 相比，`run.py`、`scratch/`、`src/`、`traffic_gen/` 无变化；新提交仅增独立输入、分析材料及工作流文件。六臂在每个 seed 均用同一源码 SHA。主拓扑 `topo_1280_400G_400G_OS1` SHA-256 为 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`；配置为 400 Gbps、9 MiB、PFC=0、IRN=1、DCQCN、共同 `RANDOM_SEED=1`、`--simul-time 0.01 --netload 10`。需求均为 16,384 条 8 KiB/tag2 MoE 加 192 条 8 MiB/tag1 背景，2.000 s 同步启动、PG3，总计 16,576 流、1,744,830,464 B。每个需求来自 `scripts/make_ws25_demand.py` 同一生成规则，互为独立整数 seed。最终验证池 `20262521–20262544` 不在本轮生成或查看效果。

| 需求 seed | 固定 flow-file | SHA-256 |
| --- | --- | --- |
| 20262502 | `config/ws25_seed20262502_b192.txt` | `568046ba32f28d9cf74cdb72fcb0df64d6b37191bac07eed506eed35ddad799d` |
| 20262503 | `config/ws25_seed20262503_b192.txt` | `2163f9f3c7de0755c908373044b0fd3d397ce1f8c19b36e81241817808801d27` |
| 20262504 | `config/ws25_seed20262504_b192.txt` | `92404882b0abeba3abca5f41baf3af34b5ed6a362ad87603af87c98580feb3e6` |

| 模式 | seed 02 ID | seed 03 ID | seed 04 ID |
| --- | --- | --- | --- |
| ECMP | `20261003-030200-ws25-v3-cal02-fecmp` | `20261003-030300-ws25-v3-cal03-fecmp` | `20261003-030400-ws25-v3-cal04-fecmp` |
| DRILL | `20261003-030201-ws25-v3-cal02-drill` | `20261003-030301-ws25-v3-cal03-drill` | `20261003-030401-ws25-v3-cal04-drill` |
| CONGA | `20261003-030202-ws25-v3-cal02-conga` | `20261003-030302-ws25-v3-cal03-conga` | `20261003-030402-ws25-v3-cal04-conga` |
| LetFlow | `20261003-030203-ws25-v3-cal02-letflow` | `20261003-030303-ws25-v3-cal03-letflow` | `20261003-030403-ws25-v3-cal04-letflow` |
| ConWeave | `20261003-030204-ws25-v3-cal02-conweave` | `20261003-030304-ws25-v3-cal03-conweave` | `20261003-030404-ws25-v3-cal04-conweave` |
| ClassReserve | `20261003-030205-ws25-v3-cal02-classreserve` | `20261003-030305-ws25-v3-cal03-classreserve` | `20261003-030405-ws25-v3-cal04-classreserve` |

每格 optimized 独立构建，输入与结果隔离。`scripts/run_ws25_calibration_v3.py plan` 生成机器计划 `results/ws25-calibration-v3-plan.json`，`run` 仅启动此表 ID，收据为 `results/ws25-calibration-v3-receipts.jsonl`；本地已运行 `py_compile` 和 `plan`，核对 18 ID、三个 trace 哈希及源码指向。旧 C2 格不重复。正式矩阵 ID 与数值判据尚未冻结，绝不由此 runner 启动。

## 正确性、观测和停止

每格需 metadata 状态成功、同 seed 六臂 trace/拓扑哈希一致、16,576/16,576 完成、标签分别 192/16,384、输入与完成字节守恒；FCT 原始匹配、CNP/PFC/uplink 文件、`config.log` 与资源收据必须齐全。ClassReserve 队列守恒必须 `queue_violations=0`；确认其双选、改选、背景路径固定计数。MoE 批次为全部 16,384 条最晚完成绝对时刻减 2.000 s；背景 P99 对全部 192 条 FCT 线性插值。未完成格不对完成者截尾计算指标。补充解释记录 CNP 的 ECN/OoO、uplink 累计字节与不均衡、现有动态分支日志；逐 QP 重传和时序物理队列缺失仍明示，不把零/缺失混淆。所有四个校准 seed 先比较每 seed 配对差，再讨论典型幅度和变异；不把它们当最终独立验证。

开格前先核对服务器无人作业、无未知 ns-3、SSH/系统健康、远程 worker 无在途格，1 分钟 load ≤20、可用内存 ≥32 GiB、可用盘 ≥100 GiB。C2 最大树 RSS 4.562 GiB、最小可用内存 114.109 GiB、最小空闲盘 5,550.915 GiB，C2 cap=2 已实测；本轮 seed02 三对继续 cap=2，均成功后 seed03/04 至多 cap=4（四格同时优化构建上界 8 CPU 令牌、按 C2 RSS 线性保守估计约 18.25 GiB）。若资源或吞吐劣于 pilot，降回 cap=2/1；不得为并发目标牺牲 SSH/系统可用性。每格 build >30 分钟、simulation >4 小时、单格 RSS >32 GiB、单格新增磁盘 >10 GiB、总 CPU >60 core-hour、未知作业、load >20、内存/盘低于线、失败/未完成/哈希不符，均停止**启动新格**并保留在途与失败原始记录；正确性修复须新 SHA/ID，不能覆盖。首批成功后正常约 30 分钟精简监督，只汇总完成/失败/资源峰值，不做逐格对话刷屏。

## 后续决策边界

18 格全部终态回传后，实际切回 Sol High，以 seed01–04 四个独立需求为单位分析双侧结果、异常与机制解释；必要时使用预留校准池的 0/64/128 输入追加**事前冻结的**约束 pilot 或修订 v1（每版最多一次诊断修正）。只有校准和缺失观测处理充分后，才冻结正式主档改善下限、背景最大容许损害、其他档位约束、最终 seed 数、统计比较、全部 ID/哈希/资源/停止条件。任何 v1 的校准 NO-GO 不取消原 WS-25 必做正确性与成稿工作。

本协议到此停在远程执行前模型边界。主对话应实际切 WS-25 至 GPT-6 Luna High 后发送继续运行指令；模型切换完成即自动执行，不等待额外人工确认。全部终态 raw 回传后主对话实际切回 Sol High 并自动继续分析。
