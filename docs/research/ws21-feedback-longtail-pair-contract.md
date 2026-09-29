# WS-21 长尾真实反馈技术 pair 契约

更新：2026-09-29。范围是验证真实反馈报文在预选长尾输入下的生成、回程送达、时效、队列计数和资源成本；不运行效果小样，也不声称选路收益。

## 固定输入与实验条件

- 分支：`feature/ws21-downstream-feedback`；两格使用同一个已推送 SHA 和各自独立的远端构建/结果目录。
- trace：`config/ws19_ws17_seed20261701_tor_hotspot_b192.txt`，SHA-256 `9996372ea22158ca995937c727b6fef20559e0ce910b22e77529d9a8061b0cc3`，16,576 条流、1,744,830,464 B。
- topology：`config/topo_1280_400G_400G_OS1.txt`，SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。
- 两格共同参数：mode 20 (`ws18`)、DCQCN、PFC=0、IRN=1、ns-3 seed=1、WS18 admission/path=0、WS-13 传输转折诊断=1、WS-21 identity=1、端口事件日志=0；仅 `ws21_feedback` 在 0/1 之间变化。
- 每格创建新的 build 和 experiment ID，不复用 40 流测试的构建目录或 ID。运行前检查其他用户任务、系统负载、内存、磁盘和 ns-3 进程；有他人作业、异常资源压力或结果日志逼近 50 MiB 时停止后续格并保留已有 raw。

## 通过门槛与停止条件

两格须均成功，实际源码、trace、拓扑、共同参数和 seed 一致；两格均完成 16,576/16,576 流且总字节为 1,744,830,464。FCT 与 WS18 时序 raw 的 SHA-256 必须相同，identity 校验需对全部可观测跨 ToR QP 无错误。每份 `config.log`、`simulation.log`、`worker.log` 均不得超过 50 MiB。

反馈开启格要求汇总计数 `generated=delivered`，`rejected=expired=hop_rejects=sequence_gaps=0`，逐跳 `hop_enqueues=hop_dequeues`，且 `hop_bytes >= delivered_bytes`；年龄最大值不超过 10 µs，缓存峰值不超过 16,384。资源记录保留每格运行时长、峰值 RSS、完成状态和构建隔离 ID。任一格失败、数据不守恒、反馈拒收/丢失/过期或计数不平衡时，停止，不继续重跑或扩展实验。

本轮只提供汇总反馈计数，没有逐报告的完整 hop 时间线，因此结果可核对总量、年龄分布和跳数计数，不能声称已逐条重建每条消息的排队轨迹。报告缓存尚未参与选路，且本 pair 不是候选收益实验。无论结果如何，WS-21 效果矩阵继续关闭，旧 no-go 不变。
