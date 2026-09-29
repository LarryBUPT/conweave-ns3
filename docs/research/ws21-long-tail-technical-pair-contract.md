# WS-21 长尾技术 pair 契约（效果矩阵仍关闭）

更新：2026-09-29。此阶段只检查预选 WS-17 长尾输入上的路径身份、诊断非扰动、出口事件完整性、背景 QP 传输转折与运行资源；不运行效果小样，不实现或声称已验证跨 ToR 反馈机制。

## 固定输入与共同参数

- 分支：`feature/ws21-downstream-feedback`；执行前冻结并记录个人 fork 已推送的完整源码 SHA，两格必须相同。
- trace：`config/ws19_ws17_seed20261701_tor_hotspot_b192.txt`，SHA-256 `9996372ea22158ca995937c727b6fef20559e0ce910b22e77529d9a8061b0cc3`；16,576 流、1,744,830,464 B，其中 16,384 条 8 KiB MoE 流和 192 条 8 MiB 背景流。该前缀是仓库中实际追踪的文件名，哈希与需求 manifest/预选输入一致。
- topology：`config/topo_1280_400G_400G_OS1.txt`，SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。
- 两格均用 mode 20 / `ws18`、DCQCN、PFC=0、IRN=1、ns-3 seed=1、WS18 admission/path=0、`WS13_DIAG=1`。诊断关闭格将 `WS21_IDENTITY=0, WS21_PORT_EVENTS=0`；诊断开启格设为 `1,1`。运行器须分别记录参数与实际源 SHA，不覆盖已有实验 ID。
- 先检查远程用户作业、负载、可用内存、磁盘和 ns-3 进程。运行时静默采集资源峰值与每格状态；如有他人作业、资源压力、日志逼近上限或仿真失败，停止后续格并保留原收据。

## 观测与判定

`WS13_DIAG=1` 对背景类 QP 输出带 `flow_id` 和仿真时间的 SACK/ACK-CNP、超时、恢复队列、重传及 DCQCN 速率变化事件；QP 事件行保留四元组、事件名、`snd_una`、`snd_nxt`、IRN SACK 长度和当前速率。普通 IRN ACK 仅保留每 QP 第一条作为进度标记，不逐包输出；SACK/CNP 与所有传输转折仍逐事件记录。`WS13_HOP` 输出逐流出口排队/等待汇总。两格都启用这些事件，比较 WS-21 身份/出口诊断开关是否改变 FCT 和 WS18 三时刻。QP/仿真文本日志（如 `config.log`、`simulation.log`）超过 50 MB 时判为资源/观测门槛失败，不截断后当作完整时间线。结构化 `_out_ws21_port.txt` 属于有界 raw 事件数据，单独受 `WS21_PORT_MAX_BYTES` 上限约束，并要求完整覆盖和 `overflow=0`。

开启格另用 WS-21 身份与端口记录，验证每条跨 ToR QP 的源首口、目的实入端口及拓扑反推首口；出口事件须覆盖首个需求到最后一个完成时刻，`overflow=0`。pair 接受条件为两格 `SUCCEEDED`、输入与拓扑 SHA 正确、16,576/16,576 完成、字节守恒、FCT 与 WS18 哈希相同、身份无错误、端口日志完整无溢出，且资源收据齐全。CE 样本为 0 时如实记录为缺测/不可区分，不将其算成 0% CE 或候选信号通过。

使用 `scripts/verify_ws21_pair.py` 对两格 raw 做配对核验，并显式传入 `--source-sha`、`--trace-sha`、`--topology-sha`、`--expected-flows 16576`、`--expected-bytes 1744830464`、`--ws13-diag 1`。另核验 `_out_ws18.txt`、FCT、身份、出口事件与 `WS13_QP/WS13_HOP` 日志；机器摘要保留每格的实验 ID、SHA、资源峰值和事件规模。

## 证据边界与下一门槛

本 pair 若通过，只说明长尾条件下观测覆盖、逐 QP 转折和诊断非扰动达到技术门槛。它不发送反馈报告，不测反馈报文头部、序列化、排队/传播、年龄、丢失或过期回退，因而**不能关闭完整技术 pilot，也不打开效果矩阵**。要继续，必须在另一个固定源码 SHA 上实现明确的目的 ToR 到源 ToR 报文路径，并逐消息核验生成、送达、丢失、过期、采用、线上字节和年龄；没有有效候选 CE 样本或可实现的真实送达路径时，停止该机制方向。
