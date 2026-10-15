# WS-28 机制解释与原生对照最终交接

## 1. 本对话目标

用户要求继续完成 WS-28 的未竟任务。本轮补齐组件效应图、三个反例的末包时序图、正式双侧分析、文献借鉴复核及预设验收；工作范围仍是 ClassReserve v1 的 ns-3 合成机制解释与原生基线对照。

## 2. 已确认的项目事实

WS-27 确认源码为 `ee236f27920aa56b3dd562ed971e5abee9e1e659`。WS-28 原生对照使用同一源码和 24 个固定需求 seed，新增 96 格并复用 48 个 ECMP/ClassReserve 控制格，共 144/144 原始验收通过。消融源码为 `955d26b580c9ca9249e66dea68638b22e0e32e2c`，诊断探针源码为 `ca03c7bccf05120fde219606bbb478e48a467619`。原始实验目录仍按 ID 隔离在 `results/`，机器索引见[最终验收](../research/ws28-final-acceptance-audit.md)。

## 3. 已完成工作

六臂技术正确性 6/6、资源 pilot 24/24、正式两因素消融 120/120、三个旧劣化 seed 的探针开关 12/12 格均从 metadata、trace、raw FCT、日志和资源收据核对通过。消融 24 个未见 seed 是独立统计单位，每格 16,384 条 MoE 与 192 条背景流全完成。四消融臂相对同输入 ECMP 的 MoE 批时间中位变化为 −4.451%～−5.971%，背景 P99 中位变化均低于 +3% 工程门槛；所有单 seed 越线已列在[最终分析](../research/ws28-factorial-and-tail-analysis.md)。四个组件条件效应及交互的 95% 区间均跨零。

三个反例的批尾流身份不同。非扰动探针显示 ClassReserve 新尾流末包分别在下游等待 6,179、6,905、6,571 ns。报告将首包出口、逐跳等待及背景队列字节分开列示，没有把不同流的等待直接相减或作唯一归因。本轮新增[组件效应图](../research/figures/ws28-component-effects.pdf)和三个时序图；图源、QA 与图注见正式分析。资源 pilot 结果文件尾部的字面量 `\n` 已改为实际换行，使其重新成为可解析 JSON；数值内容未改。

## 4. 已形成的设计决策

按预设单位与对比定义报告条件效应：先在每个 seed 内配对，再取跨 seed 中位数，交互先逐 seed 作差。没有在已揭盲 WS-27 反例上调节参数，也没有把诊断格并入新效果样本。组件区间跨零时保留整体改善与组件归因之间的边界；+3% 仍只作跨 seed 中位数工程约束。

## 5. 当前状态

WS-28 六项预设任务全部完成，状态为 `COMPLETE FOR PRESET NS-3 SYNTHETIC EXPLANATION AND NATIVE COMPARISON`。[协议](../research/ws28-classreserve-explanation-protocol.md)、[验收审计](../research/ws28-final-acceptance-audit.md)、[当前状态](../project-state/CURRENT_STATE.md)、[工作流表](../project-state/WORKSTREAMS.md)和[路线](../project-state/ROADMAP.md)已同步。无需再运行既有 120 格或 12 格。

## 6. 未解决问题

预设验收无缺格。固定合成需求和 ns-3 无法证明真实 NIC/交换机部署收益；三反例的局部队列时序缺少未走路径反事实与完整 RNIC 速率时间线。CONGA、LetFlow、ConWeave 的动态切换在本轮原生输入下没有触发。这些限制约束论文措辞，不改写已完成的实验验收。

## 7. 后续推荐动作

论文主线可从本工作树选择已核验图表与文字纳入稿件，并依据目标会议模板安排投稿材料。任何新输入分布、真实部署或动态机制覆盖的主张都需要另立问题与验证协议；WS-28 不自动追加远程格。

## 8. 与其他工作流的关系

WS-27 的确认性中位主结果和两种 P95 保持原口径。WS-25 的旧正式 NO-GO 与 WS-26 暂停状态不重判。本工作树未修改论文 `thesis/figures`，论文集成由主线在读图与核对图注后执行。

## 9. CONTEXT SNAPSHOT

WS-28 在预设 ns-3 合成范围闭环：原生对照 144/144、消融正式 120/120、诊断 12/12。ClassReserve 框架在新未见输入中相对 ECMP 改善 MoE 批时间，背景中位约束通过；组件条件效应的区间均跨零。三个旧反例的末包存在下游微秒级排队，但无唯一归因。完整源码 SHA、计划、原始 ID、双侧表、图与限制见[最终分析](../research/ws28-factorial-and-tail-analysis.md)和[最终验收](../research/ws28-final-acceptance-audit.md)。
