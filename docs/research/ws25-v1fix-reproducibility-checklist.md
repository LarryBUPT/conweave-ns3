# WS-25 ClassReserve v1 修正版正式矩阵复现清单

核对日期：2026-10-06。本清单对应已经完成的 v1 正式矩阵，只证明冻结的合成需求与 ns-3 模型中的结论。表内的 raw 位于 Git 忽略的本地结果目录；源码仓库中的机器收据索引原始 ID 和哈希。

| 检查点 | 固定身份或验收证据 | 状态 |
| --- | --- | --- |
| 事前规则 | [正式协议](ws25-v1fix-formal-protocol.md)；两个 192 档共同主结果各需中位变化 ≤−5% 与 ≥17/24 seed 改善 | 已在最终格启动前冻结 |
| 源码 | 仿真与输入提交 `ce699dffe2845dc83e2171a1c309c6d96b96d2b3` | 576 格 metadata 与计划一致 |
| 输入 | [96 份 trace manifest](evidence/ws25-v1fix-formal-inputs.json)，需求 seed `20262521–20262544`；拓扑 SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba` | 逐格哈希验收通过 |
| 实验身份 | [576 ID 冻结计划](evidence/ws25-v1fix-formal-plan.json)，固定随机运行顺序、六臂与四档；示例首格 `20261004-070000-ws25-formal-s22-b192-fecmp` | 576 个唯一原 ID，无替换或重复 |
| 原始数据 | `results/<实验ID>/metadata.json`、`config/`、`raw/`、日志和资源采样；[逐格执行证据](evidence/ws25-v1fix-formal-execution.json) | 36 批、576/576 `SUCCEEDED` 并通过 verifier |
| 资源 | 峰值负载 16.10、最低可用内存 51.80 GiB、最低空盘 4,962.54 GiB、最大单格 RSS 4,562.50 MiB | 全部满足冻结停止线 |
| 统计 | [逐格分析 JSON](evidence/ws25-v1fix-formal-analysis.json)与[人读报告](ws25-v1fix-formal-analysis.md) | 主 GO=false；低档约束通过；四次级双侧门槛均未过 |
| 图表 | [192 档配对效应图](figures/ws25-v1fix-formal-192-effects.svg) | 由分析 JSON 生成，图内标明正式 ID 前缀与源码 SHA |
| 成稿 | [小论文初稿](ws25-classreserve-v1-paper-draft.md) | v1 负结果初稿；投稿决定及后续候选仍另行处理 |

## 本地重算

在 `E:\研\毕业论文\workspace\ws25-first-paper` 执行：

```powershell
python scripts/analyze_ws25_formal.py
python scripts/plot_ws25_formal.py
```

第一条命令先核验计划与原始结果，再重建统计 JSON。它检查 576 个计划 ID 的唯一性、源码/trace/拓扑和参数哈希、输入与完成流、FCT 行、ClassReserve 类别队列守恒和资源门；任一缺失或失配会失败。第二条命令只读取分析 JSON 并重建 SVG。两条命令均不得替代远端仿真本身。

分析 JSON 还包含从逐格 raw 验收结果派生的 `background_completion_rate_gbps` 和 192 档探索性机制摘要。速率以全部背景字节除以合成背景批次的最后完成跨度计算；端口不均衡由原始 uplink 累计字节计算。二者只供机制解释，不进入正式主判据。

复核主结果时，以每个需求 seed 为一个配对单位，计算 `100 × (ClassReserve / ECMP − 1)`；分别取 24 个比率的中位数，严格负值计为改善。单侧精确符号检验、需求层 bootstrap 区间和 Holm 次级比较以冻结协议为准。0 档无背景 P99。原始数据须全部就位才能复算，不能把分析 JSON 当作 raw 的替代物。

## 预设验收与实测对照

| 验收项 | 正式实测 | 判定 |
| --- | --- | --- |
| 576 格逐格原始数据和全部流完成 | 576/576；每格完成率 100% | 通过 |
| 192 档 MoE 相对 ECMP | 中位 −3.536%；20/24 改善 | 幅度未过 |
| 192 档背景 P99 相对 ECMP | 中位 −0.065%；13/24 改善 | 幅度、方向未过 |
| 192 档共同主结果交集 | 同 seed 双改善 12/24；两项各自门槛未同时成立 | NO-GO |
| DRILL、CONGA、LetFlow、ConWeave 次级双侧比较 | Holm 调整联合 `p` 均为 1 | 未过 |
| 0/64/128 档限制 | 所有预设限制通过；保留 64 档 +45.647% 背景 P99 单 seed 反例 | 通过，存在尾部风险 |
| 机制路径与队列 | 96 格 ClassReserve 队列守恒、零 drop/违规；192 档 612,408 次 MoE 双选 | 实现路径已触发；因果解释有限 |

## 解释范围与后续身份

所有业务均为模拟 RDMA QP，`tag=1/2` 是类别标签。MoE 指标为合成同步流集合的批次时间；PFC 关闭。缺少真实 NIC、交换机、生产流量、物理 MMU 队列和业务 SLO 验证。CONGA/LetFlow 的 flowlet timeout 及 ConWeave 的 reroute/VOQ 在本正式矩阵中覆盖不足，不能由模式完成率推断其全部动态行为。

v1 已使用一次诊断修正额度。最终 seed 已揭盲，不得在这些 seed 上对 v1 调参后重判；如果创建 v2/v3，新候选需各自的机制假说、新 SHA、新 ID、未见独立需求和事前协议。第一课题在候选决策、最终账本与全部预设交付核对完成前保持 ACTIVE。
