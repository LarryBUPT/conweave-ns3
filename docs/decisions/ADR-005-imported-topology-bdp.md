# ADR-005：导入 400G 拓扑以实际链路计算 BDP

状态：Accepted for WS-06 input verification。日期：2026-09-24。

## Decision

`topo_1280_400G_400G_OS1` 在 `run.py` 和 `scratch/network-load-balance.cc` 中登记 30,000 B BDP。保留 C++ 的 `maxBdp == irn_bdp_lookup` 校验。仅对此导入拓扑允许文件中的 `10ns` 主机链路和 `100ns` 交换机链路共存；旧拓扑的统一链路延迟检查保持原样。

## Rationale

在固定源码 `29a7c16ce08a9d58a267ad5b9853c8284a76516f`、实验 `20260924-215000-ws06-1280-delay` 中，ns-3 从实际拓扑链路计算 `maxRtt=600ns`、`maxBdp=30000B`，原断言因手填 18,000 B 失败。参考仓库 maplerime 手填 18,000 B 并跳过该断言；这里以运行时实际路径与链路值为准，避免把不一致的分析 BDP 带入后续结果。

## Alternatives considered

- 直接采用 maplerime 的 18,000 B 并关闭断言：无法解释该文件实际计算出的 30,000 B。
- 将全网 `one_hop_delay` 改成单一新值：无法表示 10ns/100ns 两类链路，还会改变旧基线假设。

## Consequences

WS-06 用四流 trace 验证导入拓扑的输入与 ECMP 路径；这不验证大规模 MoE 性能。ConWeave 代码中部分 ToR 间估计仍使用统一 `one_hop_delay`，未来若在该拓扑上比较 ConWeave 或双轨机制，需先单独审计其时序假设和所有算法的公共传输/重排语义。
