# Handoff 18：WS-17 瓶颈可控性与独立需求审计

## 1. 本对话目标

按已授权的 WS-17 计划，先审计包流混合场景里真正可改变的容量与发送时刻，再设计独立需求输入及双侧、可证伪的后续契约。启动交接来自 Codex 任务 `01a0cfac-3176-7590-bf34-c0f176a45118`，本任务标题为“启动 WS-17：审计包流混合场景的瓶颈可控性与独立需求输入”；工作分支为 `feature/ws17-bottleneck-demand`。范围限于本地源码/旧原始 ID 审计和静态资产，没有新机制仿真。

## 2. 已确认的项目事实

个人 fork `origin` 的规划父提交为 `5cf603abdec4ec3d37f400cae82b30eb6ec8751d`，两个参考 remote 只读。1280 主机拓扑 SHA `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`：每主机一条 400 Gbps 链路、每 ToR 八条上游链路；[WS-17 审计](../research/ws17-bottleneck-demand-audit.md)与[manifest](../research/evidence/ws17-demand-manifest.json)记录跨 ToR 样例源侧八个最短下一跳和目的侧唯一主机出口。旧 `qp_finish` 的 FCT 从 QP 创建算起，不含未来延迟放行前的需求等待。WS-13 四格、校准六格和 WS-14 七格的原始核验通过；其目的出口排队/CNP 是相关性，不是准入的因果收益。WS-10/11/12 no-go 与 WS-14 停止规则原样保留。

## 3. 已完成工作

助手核验本地与 `origin` 父 SHA 后创建独立分支；逐边读拓扑和路由、调度、QP/FCT 源码；重跑 `analyze_ws13_feedback_probe.py`、`analyze_ws13_calibration.py`、`make_ws13_calibration_traces.py --verify` 与 `run_ws14_small.py verify`。新增 [`make_ws17_demand.py`](../../scripts/make_ws17_demand.py)，重生三条独立 seed、两种目的热点、0/192 追加背景的 12 对 trace/sidecar，`--verify` 通过；输出在 Git 忽略的 `results/ws17-demand/`，提交版[manifest](../research/evidence/ws17-demand-manifest.json)保存完整哈希。写出[审计与后续冻结契约](../research/ws17-bottleneck-demand-audit.md)。本轮没有远程访问或新仿真；长期监督及模型切换条件没有触发。

## 4. 已形成的设计决策

**决定：WS-18 最小工程 go，WS-19/20 效果矩阵仍 no-go。**依据是发送应用可延后创建、上游路径可分流，而固定目的主机的最终出口不能靠换路扩容。仅路径在最终出口热点是负对照；仅准入必须把源等待计入完成；联合须相对两个单开和 ECMP 同时评估目标与背景。替代的“仅调 GuardHash 权重”受 WS-14 停止规则约束；“用目的出口即时队列在源端决策”当前没有真实零延迟信号，不作为首版可实现机制。该决定是研究门槛，不是实测性能判断。

## 5. 当前状态

2026-09-28：`feature/ws17-bottleneck-demand` 的本地审计和静态需求资产完成，正式效果数据为零。三个 seed 是独立需求设计样本；同 seed 的热点/背景配对条件不是额外重复。提交/推送 SHA 与干净状态在本 Handoff 集成后核验，不能预写为仿真 SHA。

## 6. 未解决问题

必须解决：WS-18 实现稳定 flow ID、原始需求/放行/完成三时刻与守恒，确保旧 FCT 不漏源端等待；四臂同输入正确性、完整完成率与背景尾部逐流分析。可后置：下游反馈真实延迟、额外消息与开销、物理 MMU 占用、全流可靠 NACK/超时口径。研究限制：新轮次/热点是合成需求，只有 rail 0、三个静态 seed，无真实训练 job、业务 SLO 或新机制效果。

## 7. 后续推荐动作

若明确启动 WS-18，从已推送 WS-17 提交另建独立分支；先冻结四臂正确性与三时刻计量，再实现最小机制。只有输入/完成/字节/等待守恒和共同传输回归通过，才讨论 WS-19 双侧小样；运行远程实验时须遵守工作流的资源 pilot、静默监督及实际 Luna High→Sol High 切换。不要自动创建新任务或重开旧判据。

## 8. 与其他工作流的关系

WS-17 继承 WS-16 的论文证据边界，利用 WS-13/14 原始 ID 定位问题，不把它们并入新效果估计。新需求 seed 不等同 WS-13 校准 seed，也不把 WS-11/12 行顺序置换当独立样本。WS-21 下游反馈仍以可绕行上游热点和反馈可实现性为条件；本审计只证明前者在拓扑中存在，不证明实际反馈机制有效。

## 9. CONTEXT SNAPSHOT

WS-17 本地审计已完成：每目标主机唯一最终出口，跨 ToR 源侧有多最短路径；旧 FCT 不含未来准入源等待。三独立 seed 的 12 对静态 trace/sidecar 有生成器和完整 manifest 哈希，尚未仿真。旧 WS-13/14 原始复核通过，只是相关性/单输入 pilot；WS-10/11/12 no-go 不变。只开放 WS-18 最小工程正确性，WS-19/20 效果矩阵仍关闭。核心入口：[审计](../research/ws17-bottleneck-demand-audit.md)、[生成器](../../scripts/make_ws17_demand.py)、[manifest](../research/evidence/ws17-demand-manifest.json)、[工作流](../REMOTE_EXPERIMENT_WORKFLOW.md)。
