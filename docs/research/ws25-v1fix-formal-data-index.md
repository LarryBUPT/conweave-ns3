# WS-25 v1 正式矩阵逐格数据索引

本索引对应冻结仿真源码 `ce699dffe2845dc83e2171a1c309c6d96b96d2b3` 的 24 个需求 seed × 4 个背景档 × 6 个模式，共 576 个正式原 ID。全部原始结果保留在 Git 忽略的本地 `results/<ID>/`；表中给出相对工作区根目录的 raw FCT 路径、原始目录号、输入与输出 SHA，便于回查，不把 CSV 当作 raw 替代品。

- [576 格逐格指标表](evidence/ws25-v1fix-formal-cell-metrics.csv)：每格 MoE 与背景的完成数、FCT 均值及 P50/P90/P95/P99、slowdown 的 P50/P90/P99，以及合成批次时间。0 背景档的背景指标留空，完成数为 0。单位为微秒，slowdown 无量纲。
- [840 条逐 seed 配对表](evidence/ws25-v1fix-formal-seed-pairs.csv)：每个 seed、档位将 ClassReserve 与五个基线逐一配对；0 档只有 MoE 指标，其余档位各有 MoE 与背景 P99。变化率为 `100 × (ClassReserve/基线 − 1)`，负值表示候选较快。每个需求 seed 才是独立统计单位。
- [正式分析与门槛](ws25-v1fix-formal-analysis.md)：192 档共同主结果 NO-GO；上面两表为逐格和逐 seed 查询入口，不修改冻结判据。

重建命令：`python scripts/export_ws25_formal_tables.py`。脚本要求分析 JSON 已逐格核验 576 格，从每个正式 ID 的 trace/FCT raw 重建类别统计、校验完成数及哈希，再写 CSV。P90 与 slowdown 直接由已完成流 FCT 原始行计算；合成批次和其余百分位与项目的 `analyze_moe_tags.py` 口径一致。本次重建得到 576 行与 840 条配对；192 档对 ECMP 的 MoE 中位变化 −3.536465%（20/24 改善）、背景 P99 −0.064643%（13/24 改善），与正式报告四舍五入值一致。

图包仍需完成逐 seed 六臂 CDF、完整负载档位对比、适用的上联采样速率与 ConWeave VOQ 图；本索引先固定这些图的 ID 与指标入口。上联原始值为累计字节，后续换算必须使用实际相邻采样时间；ConWeave VOQ 不等于物理 MMU 队列。
