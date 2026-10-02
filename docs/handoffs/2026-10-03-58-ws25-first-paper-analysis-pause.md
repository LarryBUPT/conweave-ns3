# Handoff 58：WS-25 进入分析阶段后的暂停点

日期：2026-10-03（Asia/Shanghai）。按用户要求，WS-25 在 calibration pilot 终态核验完成、进入分析阶段后暂停。正式验证矩阵未启动，WS-25 仍 ACTIVE。

## 已完成的实验与核验

源码固定为 C2 `bb10309261b7c5be350fcaab75b4fdb8db95ddca`；拓扑 SHA 为 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`；八流 correctness trace SHA 为 `29ebe2dcf38c0e4d29326947c4bc4e111f6b56fe378c020c30ee788fbaa5effb`；192 档 calibration trace SHA 为 `9791006f71843ea74b044396f6ae112ea8340aa9781cf0d267876e0940b02f48`。固定参数为 400 Gbps、9 MiB buffer、PFC=0、IRN=1、seed=1、OS1 拓扑。

- C2 correctness：6/6 模式通过；每格 8/8 流完成，tag 1 为 `33,554,432 B`，tag 2 为 `32,768 B`，模式入口和资源收据齐全。ClassReserve correctness 的 `queue_violations=0`，`moe_two_choices=18`。
- C2 calibration pilot：6/6 模式通过；每格 `16,576/16,576` 流完成，tag 1 为 `1,610,612,736 B`，tag 2 为 `134,217,728 B`，总字节守恒。ClassReserve calibration 的 `queue_violations=0`，并记录 `background_new_flows=884`、`background_reused=7414992`、`moe_two_choices=243222`。
- calibration 资源峰值：peak tree RSS 最大 `4562.08 MiB`；最低可用内存 `114.109 GiB`；最低可用盘 `5550.915 GiB`；所有采样均低于负载停止线。终态现场无活动 ns-3 进程，负载 `0.01`，可用内存约 `122.97 GiB`，可用盘约 `5550.9 GiB`。

逐格机器核验已通过：

```text
python scripts/verify_ws25_preflight.py pre    -> verified=6
python scripts/verify_ws25_preflight.py pilot  -> verified=6
```

收据位于 `results/ws25-preflight-receipts-v2.jsonl`，共 35 行事件记录；每个 ID 的 `processed/ws25_preflight_verification.json`、metadata、raw、config.log 和 resource summary 均已回传。C1 的 ConWeave 配置失败 ID 仍独立保留，未被 C2 覆盖。

## 暂停边界

本 Handoff 之后不运行分析器、不计算 FCT/P99/批次相对差、不冻结正式双侧门槛、不生成最终 seed/ID，也不启动正式验证矩阵。Calibration pilot 只证明 C2 六臂输入可完成并提供资源/波动原始数据，不能写成性能收益。

## 下一动作

恢复 WS-25 时从 v2 receipts 和 12 个终态 ID 开始，在实际分析模型下逐格读取 raw，完成 calibration 口径分析、缺失观测审查和正式双侧判据/样本量冻结；经用户后续授权后才能启动最终矩阵。当前代码和实验结果保持不变。
