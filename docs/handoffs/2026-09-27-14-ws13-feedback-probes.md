# Handoff 14：WS-13 IRN 反馈语义与目的出口探针

日期：2026-09-27。状态：**WS-13 诊断 pilot 已完成；没有冻结新的业务安全线或启动 WS-14 效果实验。**

## 1. 本对话目标

来源任务标题：`继续下一轮工作，注意模型切换使用及静默远程实验监督`（当前会话未提供可核验任务 ID）。继续 WS-13 背景长尾定位，遵守静默远程实验监督、共享 CPU 资源预算和 Luna/Sol 阶段切换要求；纠正 IRN `0xFD` ACK/NACK 标签歧义，完成最小同输入复测及项目状态交接。

## 2. 已确认的项目事实

- 仓库：个人 fork `LarryBUPT/conweave-ns3`，分支 `feature/ws13-tail-diagnosis`；只读参考仓库未改动。
- 相关提交：诊断字段修复 `a985798ef78a95f502cf8eb56982c6e3a3b1168d`；新 probe runner `44c071c`。WS-12 固定仿真参考 SHA 仍为 `adae7956e3fc874d9237e62a6ea8e32b26d5def1`。
- 用户确认没有可核验业务 SLO；成熟方案只用于校准评价指标，不照搬不同场景下的百分比。保留连续 MoE—背景权衡，不设置通用安全线，也不改 WS-10/11/12 预注册规则。

## 3. 已完成工作

- 阅读项目远程实验工作流、baseline/dataflow 审计和 `conweave-project-state` 技能。原五格诊断结果经独立检查：关闭探针首格及 4 个开启格的 FCT SHA 与 WS-12 参考一致；旧 `event=nack` 不能作为真实 NACK 证据。
- 修正 `rdma-hw.cc` 探针字段：记录 `irn_nack_size`，将 `0xFD` 且 size=0 标为 `irn_ack`，size>0 标为 `sack`，CNP 日志保留该字段。为此新增 `run_ws13_feedback_probe.py`，提交并推送个人 fork。
- 四个新版最小诊断格均成功并通过自动核验：`20260927-160000-ws13-feedback-o-f/o-a/03-f/03-d`，固定仿真 SHA `a985798...`，输入/拓扑与参考格匹配；FCT SHA 逐格与 WS-12 完全一致；两类流全完成、PFC 文件为空、探针未配对包为 0、每条 QP 事件均有反馈字段；日志 13.59–15.61 MiB，资源收据正常。原始细节见 [机器分析](../research/evidence/ws13-feedback-probe-analysis.json)。
- 四格目标背景 QP 分别有 117,446/117,446/100,668/100,668 个 IRN ACK、0 个 SACK，CNP 事件 751/881/500/580。每格最慢两条背景流可在目的 ToR 出口观察到队列等待；代表性最大等待 3.14–3.99 µs，排队前队列字节峰值约 161,452–198,192 B。结果支持目的出口排队与长尾并存，但单 seed 观测不能建立因果。
- 四份新构建并发使用每份 `-j2`，随后四格并发仿真。远端在途期间负载约 4–8、可用内存 105–123 GiB；结束时无仿真 PID、负载 0.72、可用内存 122.97 GiB，未见资源异常。

## 4. 已形成的设计决策

- IRN `l3Prot=0xFD` 单独不足以判定 NACK；后续分析须以 `irn_nack_size` 区分 ACK 与 SACK。旧探针的 `event=nack` 标签作废。
- CNP 事件不自动归因于乱序；新版选定的目标 QP 未出现 SACK，原 OoO 假说在这些目标流上没有支持。目的 ToR 排队观察仍为关联证据，不是因果分解。
- 用户决定暂无可核验业务 SLO；继续显示连续权衡/灵敏度分析，不提炼通用阈值。旧正式研究 no-go 保持不变。

## 5. 当前状态

本地分支 `feature/ws13-tail-diagnosis` 的代码修复与 probe runner 提交已推送到个人 fork；本 Handoff、WS-13 报告、机器摘要与状态入口随本次集成提交一并推送。四格已结束，远端空闲。交接前完成了链接、SHA、元数据、资源收据与工作树核验。

## 6. 未解决问题

- 单 seed 探针不能确认瞬时队列导致多少 FCT 增量；对照拓扑只有聚合路由与出口排队摘要。
- 未测真实 MMU buffer occupancy、逐包 ECN 标记和接收端即时发送速率。`HandleTimeout` 在 IRN+Qbb 分支于 probe logger 前提前返回，因此无有效逐 QP timeout 计数，不能把没有 timeout 行解释成零 timeout。
- 三个校准需求 trace 只能描述样本内 ECMP 波动；无业务 SLO 支持任何新安全数值。
- 当前 Codex 会话界面未暴露模型选择器（computer-use state 未列出应用或浏览器）；此轮不能验证是否已切换到 `gpt-6-luna`。远程监督按低频静默方式完成，进入代码/文档分析时应按工作流使用 `gpt-6-sol` High。

## 7. 后续推荐动作

1. 集成本 Handoff 与 WS-13 状态更新，并从本地及个人 fork 复核 HEAD、工作树和链接。
2. 如决定继续 WS-14，将其明确标为研究性单机制 pilot，预先给出连续损害曲线/敏感性范围；围绕目的 ToR 出口排队与每 QP CNP 对照 ECMP、DRILL。不要把候选线写作业务安全线。
3. 若研究问题不足以支撑该 pilot，则停止扩大仿真矩阵，转入 WS-16 解释性负结果与复现收束。任何正式效应实验须先冻结独立需求重复和事前统计契约。

## 8. 与其他工作流的关系

本交接只延伸 WS-13 的诊断可观测性，不改变 WS-10 固定总字节 no-go、WS-11 全量场景复合 no-go、WS-12 四新增策略 no-go。WS-14 仍为条件状态，GuardHash/HarmGate 没有新增收益证据；不与四组流顺序置换或独立校准 trace 合并推断。

## 9. CONTEXT SNAPSHOT

WS-13 使用 WS-12 原始 192 背景格及 20261103/128 顺序格，逐流配对、独立校准、成熟方案指标口径和小规模队列探针均已整理。原诊断日志的 `0xFD=nack` 标签有误；修复后的四格没有目标 QP SACK，均有 CNP，并在最慢背景流的目的 ToR 出口观测到微秒级排队。FCT SHA 全部与 WS-12 一致。该证据支持“目的出口排队伴随背景尾部”，但不能证明唯一原因。用户没有可核验业务 SLO，保留连续权衡，不设通用阈值，旧 no-go 不变。重要文件：`docs/research/ws13-tail-diagnosis-and-experiment-contract.md`、`docs/research/evidence/ws13-feedback-probe-analysis.json`、`scripts/run_ws13_feedback_probe.py`、`scripts/analyze_ws13_feedback_probe.py`。远端任务已结束；新阶段模型按工作流切到 Luna 监督、Sol High 分析。
