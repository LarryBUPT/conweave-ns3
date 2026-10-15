# WS-28 预设任务最终验收

核对日期：2026 年 10 月 16 日。范围为[WS-28 协议](ws28-classreserve-explanation-protocol.md)中的六项预设任务。实际源码、冻结计划和每个实验 ID 的原始数据为最终依据；阶段状态文件与早期 Handoff 只作索引。

| 预设任务 | 实现与原始证据 | 验收结果 |
| --- | --- | --- |
| 现有结果复算 | WS-27 192 背景档 24 个 seed × ECMP/ClassReserve，共 48 个原始格；[逐流复算](evidence/ws28-existing-raw-analysis.json)与[阶段报告](ws28-existing-raw-diagnosis.md)定位三个批尾流切换。 | 48/48 格通过；原格未重跑或覆盖。 |
| 两种 P95 | [原生报告](ws28-native-comparison-report.md)和[最终分析](ws28-factorial-and-tail-analysis.md)区分 seed 内单流 P95 配对变化中位数 −1.012%，以及 24 个 seed 级批时间 P95 变化 −6.888%。 | 两种统计单位、公式、数值和配对图一致；保留 −6.899% 原主指标。 |
| 原生基线 | 固定 `ee236f27920aa56b3dd562ed971e5abee9e1e659`；新增 DRILL、CONGA、LetFlow、ConWeave 各 24 格，与 WS-27 ECMP/ClassReserve 各 24 格同输入配对；[机器分析](evidence/ws28-native-analysis.json)核对分派、哈希、全流完成和资源。 | 正确性 5/5、资源 pilot 24/24、新正式格 96/96、六臂总计 144/144 通过。动态切换未触发的范围已在报告标明。 |
| 两因素组件解释 | 固定 `955d26b580c9ca9249e66dea68638b22e0e32e2c`、[输入清单](evidence/ws28-ablation-inputs.json)及[计划](evidence/ws28-ablation-plan.json)；[执行收据](evidence/ws28-ablation-execution.json)与[机器分析](evidence/ws28-ablation-analysis.json)逐 raw 重算 24 个未见需求 seed × 五臂。 | 技术 6/6、资源 24/24、正式 120/120 通过；全流完成、队列守恒与资源停止线通过；两侧结果、四条件对比及交互已完整报告。 |
| 三个反例定向诊断 | 固定探针源码 `ca03c7bccf05120fde219606bbb478e48a467619`；三个旧劣化 seed × 两模式 × 探针开关，见[诊断机器结果](evidence/ws28-tail-analysis.json)。 | 12/12 格通过；六组开关与 WS-27 原格 FCT 哈希一致，逐包事件无拒收、丢包或溢出。首包出口与末包逐跳窗口已定位；未把局部关联写成唯一因果。 |
| 图表与文献 | 原有[配对图](figures/ws28-classreserve-paired-seeds.pdf)、[原生图](figures/ws28-native-comparison.pdf)，新增[组件图](figures/ws28-component-effects.pdf)与三个[反例时序图](figures/ws28-tail-timeline-s20262725.pdf)、[20262729](figures/ws28-tail-timeline-s20262729.pdf)、[20262739](figures/ws28-tail-timeline-s20262739.pdf)；各图源、统计单位、原始 ID 和 QA 见[最终分析](ws28-factorial-and-tail-analysis.md)。 | 图源静态检查、PDF 字号与碰撞审计通过，组件双面板对齐通过；逐图目视检查完成。原生、设计冻结和正式分析节点均完成版本与借鉴边界复核。 |

本轮没有以不利结果取消正确性验收。正式消融的所有组件条件效应区间跨零，因此结论保留为“整体路由框架在固定输入下改善，单组件独立收益未识别”。背景 P99 的 +3% 是跨 seed 中位数工程门槛，单 seed 越线仍逐项报告。三个反例的下游排队是观测事实，尚无可唯一隔离 A、B 或未走路径的反事实证据。上述边界限制结论范围，不构成预设实验缺格。

预设 WS-28 的六项验收均有固定源码、实验 ID、raw、结果图和相应结论对应，必做未完成项为零。后续论文排版、投稿决定、真实网络部署与新输入分布推广属于其他里程碑；不得据本验收声称已完成它们。
