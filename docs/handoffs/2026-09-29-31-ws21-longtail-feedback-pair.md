# Handoff 31 — WS-21 长尾真实反馈技术 pair

## 本阶段目标与证据边界

在已通过的 40 流开关正确性 pair 之后，验证真实反馈报文在预选长尾输入中的送达、年龄、逐跳总量和运行资源。该工作不运行效果小样，也不把收到报告解释为它能区分候选路径或改善选路。

40 流 pair 的机器收据为 `docs/research/evidence/ws21-feedback-40-pair.json`。两格同 SHA、同 trace、同拓扑，40/40 流及 33,849,344 B 守恒，FCT/WS18 SHA 相同；开启格 223 条报告全部送达，拒收、过期、序号缺口为 0，逐跳队列 446 入/446 出，缓存峰值 8。该输入上游 CE 样本为 0，不能作为候选区分测试。

## 冻结的长尾 pair 条件

实验契约见 `docs/research/ws21-feedback-longtail-pair-contract.md`，核验器为 `scripts/verify_ws21_feedback_longtail.py`。固定输入是 16,576 条、1,744,830,464 B 的 WS-17 长尾 trace（SHA-256 `9996372ea22158ca995937c727b6fef20559e0ce910b22e77529d9a8061b0cc3`）和拓扑 SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。两格共同使用 WS18 mode、PFC=0、IRN=1、seed=1、WS18 admission/path=0、WS13 传输诊断=1、WS21 identity=1、port-event 日志=0；唯一实验变量是反馈开关。运行前记录源码 SHA、新 build/experiment IDs 和远端资源快照。

通过门槛为两格成功、流数/字节守恒、FCT 和 WS18 raw 哈希一致、identity 无错；反馈开启格生成数等于送达数、无拒收/过期/逐跳拒绝/序号缺口、入队出队平衡、反馈年龄不超过 10 µs、缓存不超 16,384，日志不超 50 MiB，且有每格资源数据。任何失败均停止后续格并保留 raw。当前只核对聚合计数，没有逐报告完整 hop 时间线。

## 执行结果

待本阶段长尾 pair 运行后填写实验 ID、实际 SHA、完成与字节核验、反馈计数、资源峰值和限制。未完成此节前，不得把长尾 pair 描述为通过。
