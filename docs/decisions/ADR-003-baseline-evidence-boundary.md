# ADR-003：最小基线运行只作忠实度与数据链路核验

状态：Accepted。日期：2026-09-23。

## Decision

四种基线的 0.01 秒、10% 负载运行只用于验证模式入口、动态分支、相同输入与原始数据链路。不将该运行的 P99 数值写成算法性能排序；正式比较必须另行固定 trace、seed、配置和运行级统计设计。

## Rationale

四次实验均成功，输入哈希和公共配置相同，但窗口极短、只有一份 trace、PFC 未触发。ConWeave VOQ 与 MMU 物理队列语义不同，原始 `traffic_gen.py` 又没有独立 seed。现有证据支持“链路可用”，不支持更广的性能或硬件结论。

## Alternatives considered

- 直接按四个 P99 数值排名：样本与条件不足，指标只覆盖所选窗口内的已完成流。
- 把空 PFC 文件解释成 PFC 永不发生：仅能说明此低负载最小运行未触发。

## Consequences

后续引用必须标实验 ID、源码 SHA、trace 哈希及指标窗口；需要物理队列指标时先补观测。原始记录见 `docs/research/10-baseline-fidelity-and-dataflow-audit.md`。
