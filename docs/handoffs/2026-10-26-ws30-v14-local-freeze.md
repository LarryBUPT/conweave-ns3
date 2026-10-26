# WS-30 v14 本地冻结交接

日期：2026 年 10 月 26 日。来源对话：`01a174c7-ecf5-7f21-a9dc-6f8b4f5634b8`，WS-30；本节点实际模型为 GPT-6.1 Sol / Medium。

## 1. 本对话目标

按主对话限定，仅完成 seed schema 补正、生命周期物理夹具与状态观测、ConWeave 被动观测和 W5 输入生成，形成可审阅的运行前契约。本节点禁止远程部署、构建、同步、仿真和推送重试，不操作 WS-29。

## 2. 已确认的项目事实

v13 固定源码 `2c9f3a50bafad0740b461496ba24fa81941a9bc7` 的 46 格及 202,020 条 raw 记录已核验，持久对象和缓存有证据，但持久格候选重合、CC/SACK 初始。详见[v13 报告](../research/ws30-v13-engineering-node-report-r1.md)。新实现固定源码为 `0673e4c3de34d83585dd40f6be7fbd3ed000a9ee`；本轮没有新 raw。

## 3. 已完成工作

已实现两种真实背景 profile、不同候选的显式探针端口、发送/接收对象和真实 CC/SACK/恢复事件日志，以及 ConWeave 原生阶段的被动日志。确定性生成 13 份输入/拓扑。规划脚本按格核对固定 Git blob 和输入哈希，raw 验收器已编码身份、字节、生命周期和真实触发检查。Python 语法、worker Python 3.5 语法、历史函数及 observer 静态等价审计通过；PATH 无原生 C++ 编译器，未构建。见[完整报告](../research/ws30-v14-local-implementation-and-execution-contract-r1.md)。

## 4. 已形成的设计决策

完成请求的边界要求 SACK 清空、恢复退出；非空 SACK/恢复在请求内部证明，跨轮以对象、累计序号、事件历史和非初始 CC 证明连续性。observer 不调用会消费 SACK 的 helper。模拟 seed 固定为 1，需求 seed 另列。正式 168 格只修 schema，保留旧仿真源；新工程/W5 用新源。没有为追求正收益改变门槛。参考复核见[记录](../research/evidence/ws30-v14-reference-review-r1.json)。

## 5. 当前状态

分支 `research/ws30-attribution-audit`。本地实现与运行前冻结完成，WS-30 ACTIVE。原 r2 不变；[新 r2 契约](../research/evidence/ws30-v14-disabled-contract-r2.json)建议工程 48 格、W5 36 格和正式 168 格，总计 252 个新 ID，`execution_enabled=false`、`approved_execution_cells=0`。本节点没有远程动作或新仿真。

## 6. 未解决问题

必须完成原生 optimized 构建、18 格历史回归、6 对生命周期和 2 对 ConWeave 观测不干扰、不同真实队列与非初始 CC/真实 SACK 恢复覆盖。新 state 输入的触发效果尚未获动态证据；新源资源未准入。新 worker 参数未部署，不能直接使用现有远端 worker。新 ID 未核远端冲突。外部同步授权由主对话处理，不重试既有推送。

## 7. 后续推荐动作

主对话接受范围和顺序后，处理外部同步、成对部署 controller/worker，再按固定 SHA 隔离构建。先旧回归和生命周期 off/on/真实条件，再 ConWeave 资格和 W5；每步由实际 raw 验收。新源从单格/cap 4 实测，再决定 cap 8。不得把新契约送入旧 v13 runner。工程与 W5 各含分析共约 6.25～10.25 小时；旧正式含分析约 8.63～9.13 小时，总计约 14.9～19.4 小时，未计审批/同步/修复。主对话须评估时限与资源，未完成项保持必做。

## 8. 与其他工作流的关系

仅更新 WS-30 分支；主稿、v12 冻结证据、旧 46 格和 WS-29 不变。原正式与新工程使用不同 source，未来执行器必须逐格读取。Gemma 等忠实度缺口仍保留，没有新增简化 baseline。父对话可通过本交接读取结果，本节点不向其他对话发消息。

## 9. CONTEXT SNAPSHOT

本地源 `0673e4c`，正式源 `2c9f3a5`；新增运行 0，工程 48＋W5 36＋正式 168 全关闭。输入 manifest SHA-256 为 `d978ec5dbe400ba778486f0e4b21beda257ac2d01ecc8cced6d39a633d459d8b`；契约 SHA-256 为 `266d9f6be946c107d4155743e6762ce718e9a85f470cb2ca0d2395f5bd544856`。[预运行门槛](../research/evidence/ws30-v14-pre-run-gates-r1.json)保存原 raw 回归目标与配对。静态通过不代表构建、动态不干扰或物理覆盖通过。WS-30 未闭环，继续由主对话承接。
