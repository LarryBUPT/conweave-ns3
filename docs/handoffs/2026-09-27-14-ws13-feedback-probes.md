# Handoff 14：WS-13 背景长尾诊断与 IRN×PFC 技术 pilot

日期：2026-09-27。状态：**WS-13 诊断及 IRN×PFC 技术 pilot 已完成；没有冻结新的业务安全线或启动 WS-14 效果实验。**

## 1. 本对话目标

来源任务 ID：`01a0e1ac-fe55-7a91-a2de-205722db854b`，标题：`WS-13 背景长尾诊断与证据化实验判据`。任务先定位背景尾流、校准评价口径与基线波动；随后延伸为 IRN `0xFD` ACK/SACK 语义修正、同输入反馈探针及 IRN×PFC 四格技术 pilot。远程监督遵守静默、低频及资源预算要求。

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
- 诊断还复用 WS-12 原始结果形成逐流配对、ECMP 绝对基准和 MoE—背景连续权衡；三份独立重抽的需求 trace 只作 ECMP/DRILL 校准。成熟方案提供评价指标和对照设计，不提供本项目可照搬的安全百分比。详见[诊断与实验契约](../research/ws13-tail-diagnosis-and-experiment-contract.md)。
- IRN×PFC 同输入 00/01/10/11 常规四格均 320/320 完成，但 PFC 事件全为 0；16×1 MiB 压力四格中仅 11 格为 13/16 完成。定向复跑的 FCT 与旧 11 格逐字节相同，记录 161 次出口准入丢包；未完成流 13/14/15 各自在被抑制超时的 `snd_una` 序号有此前丢包。分析器从原始 trace、FCT、PFC 和日志重算；旧 worker 的非空 FCT 成功判定已为后续 factorial pilot 加入完成数门禁，原始元数据保留。见[四格报告](../research/ws13-irn-pfc-factorial-pilot-report.md)及[丢包收据](../research/evidence/ws13-irn-pfc-drop-probe.json)。

## 4. 已形成的设计决策

- IRN `l3Prot=0xFD` 单独不足以判定 NACK；后续分析须以 `irn_nack_size` 区分 ACK 与 SACK。旧探针的 `event=nack` 标签作废。
- CNP 事件不自动归因于乱序；新版选定的目标 QP 未出现 SACK，原 OoO 假说在这些目标流上没有支持。目的 ToR 排队观察仍为关联证据，不是因果分解。
- 用户决定暂无可核验业务 SLO；继续显示连续权衡/灵敏度分析，不提炼通用阈值。旧正式研究 no-go 保持不变。
- 常规业务输入未触发 PFC，不能估计其动态效果；当前 IRN+PFC 实现的压力 11 格存在丢包后超时恢复被抑制，不能将已完成流的 P99 当作完整格的性能结果。今后若修复重传契约，须另立代码版本与实验问题。

## 5. 当前状态

2026-09-27 独立交接观察：个人 fork `feature/ws13-tail-diagnosis` 本地与 `origin` 同为 `62f25d15fd1123586a0edbdeeb48fb0ba96e88a0`，工作树干净。重新运行常规、压力四格和丢包探针三个分析入口，分别得到常规 4/4 全完成且 PFC 零事件、压力 11 格 13/16 与 3 次超时抑制、探针 FCT 相同且 161 次出口准入丢包。文档集成提交会移动 HEAD，仿真源码 SHA 不随之改变。

## 6. 未解决问题

- 单 seed 探针不能确认瞬时队列导致多少 FCT 增量；对照拓扑只有聚合路由与出口排队摘要。
- 未测真实 MMU buffer occupancy、逐包 ECN 标记和接收端即时发送速率。`HandleTimeout` 在 IRN+Qbb 分支于 probe logger 前提前返回，因此无有效逐 QP timeout 计数，不能把没有 timeout 行解释成零 timeout。
- 三个校准需求 trace 只能描述样本内 ECMP 波动；无业务 SLO 支持任何新安全数值。
- 当前 Codex 会话界面未暴露模型选择器（computer-use state 未列出应用或浏览器）；此轮不能验证是否已切换到 `gpt-6-luna`。远程监督按低频静默方式完成，进入代码/文档分析时应按工作流使用 `gpt-6-sol` High。
- IRN×PFC 在当前实现下的修复与正式效果比较未做；WS-14 应在共同 PFC=0/IRN=1 契约下先做单机制研究小样，不能把本压力 pilot 填入正式效应矩阵。

## 7. 后续推荐动作

1. WS-14 明确标为研究性单机制 pilot，在运行前冻结机制、连续损害曲线/敏感性范围、同输入 ECMP/逐包哈希/普通双候选/DRILL 对照、观测缺口与停止规则；优先检验目的 ToR 出口排队及每 QP CNP 的可证伪关系，不把候选线写作业务安全线。
2. 若双侧信号或完整性门槛失败，停止扩大矩阵，转入 WS-16 解释性负结果与复现收束。任何 WS-15 正式效应实验须另取独立需求 trace 并事前冻结统计契约。

## 8. 与其他工作流的关系

本交接收束 WS-13 的诊断、校准与传输技术 pilot，不改变 WS-10 固定总字节 no-go、WS-11 全量场景复合 no-go、WS-12 四新增策略 no-go。WS-14 仍为条件性研究小样，GuardHash/HarmGate 没有新增收益证据；不与四组流顺序置换或独立校准 trace 合并推断。

## 9. CONTEXT SNAPSHOT

WS-13 使用 WS-12 原始 192 背景格及 20261103/128 顺序格，逐流配对、独立校准、成熟方案指标口径和小规模队列探针均已整理。原诊断日志的 `0xFD=nack` 标签有误；修复后的四格没有目标 QP SACK，均有 CNP，并在最慢背景流的目的 ToR 出口观测到微秒级排队。FCT SHA 全部与 WS-12 一致，不能据相关性证明唯一尾因。IRN×PFC 常规四格 PFC 未触发；压力 11 格丢包并只有 13/16 完成，三个缺失流的关键序号此前出口准入被拒，超时恢复随后被抑制。用户没有可核验业务 SLO，保留连续权衡，不设通用阈值，旧 no-go 不变。重要文件：`docs/research/ws13-tail-diagnosis-and-experiment-contract.md`、`docs/research/ws13-irn-pfc-factorial-pilot-report.md`、`docs/research/evidence/ws13-irn-pfc-drop-probe.json`。WS-14 只可作为事前冻结条件的研究性小样启动；监督/分析模型按远程工作流切换。
