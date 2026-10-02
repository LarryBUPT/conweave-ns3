# Handoff 55：WS-24 独立合成 job 四臂矩阵与范围闭环

日期：2026-10-02。执行工作流：WS-24 多 rail 与放置，项目清单中的执行对话 `01a0f1da-f1e2-7870-9361-24b4d626fd76`。状态：**COMPLETE FOR NS-3 SYNTHETIC MULTI-RAIL AND PLACEMENT VALIDATION**；不代表真实主机部署效果。

## 1. 本对话目标

在用户明确决定“不要真实主机数据，仅NS3模拟”后，完成原 WS-24 必做的独立合成 job 需求 × 单/多 rail × 固定/可变放置 48 格验证。从运行时正确性、资源、原始数据回传一直做到事前 job 级双侧分析，最终核对代码、效果和结论。范围决定见 [ADR-009](../decisions/ADR-009-ws24-ns3-only-scope.md)。

## 2. 已确认的项目事实

个人 fork 分支 `feature/ws24-multinic-validation`；正式仿真固定 SHA `3b992eed218f65b4f8026eddb5170a7694e17b10`，manifest SHA-256 `e2d19ce3d7424f556bebcd74f011310538cf89c55bc2937c985e922af2b1c536`。manifest 列出 12 个不同生成 key、48 个输入 SHA、执行顺序与唯一实验 ID；每 job 四臂共用 30 条逻辑需求与总字节。共同 ns-3 seed 1、320-host × 4-NIC 合成拓扑、`fecmp`、PFC=0/IRN=1。旧 14 格和同 SHA point-to-point 单测仍属先前技术证据，不进入本次 12-job 统计。首次旧 `20261002-180000-ws24-ind-j01-fs@166ca670…` 缺资源收据，保留为 correctness-only；正式替代 ID 为 `...j01-fs-r2`。

## 3. 已完成工作与原始证据

1. 实际 Luna High 监督阶段确认隔离 worker/观察器与远端资源后，以 manifest ID 独立构建和运行 `j01` 四臂及后续 44 格。48/48 metadata `SUCCEEDED`，各 30/30 流，逐格 raw、输入快照、资源收据均下载；运行期资源采样每格至少 44 点。
2. 在实际切回 GPT-6 Sol High 后重新执行输入逐字节生成检查和静态配对检查；冻结的 `verify_ws24_independent_matrix.verify_matrix` 从 48 份原始结果独立重算通过。机器摘要：[48 格分析](../research/evidence/ws24-independent-synthetic-effects-summary.json)。逐流覆盖 NIC/IP/rail、输入/完成/字节、FCT 对应、运行时 600 ns RTT/30,000 B BDP。
3. 本地与远端 48 个结果目录的 1,056 个文件 SHA-256 逐一相同，文件索引摘要 `4bb080c07fe29a2e6d7dadfe6100b3b2d47bf5f0a5923abb3720900bda691251`，见[传输收据](../research/evidence/ws24-independent-transfer-parity.json)。资源最大进程树 RSS 7,258.44 MiB、load1m 16.24、最长构建 436 s、最长仿真 248 s，均低于事前停止线；见[执行审计](../research/evidence/ws24-independent-execution-audit.json)。
4. 事前主指标的 12 个独立 job 全为负，配对中位 −19.667%，精确双侧符号检验 `p=0.00048828125`，不低于 95% 覆盖的精确中位区间 `[−25.796%, −6.868%]`。`j02` 单 rail 拥塞反馈与尾部较强、主效应 −78.014%；`j11` 仅 −0.952%；`j09` 固定/可变放置差别明显。这些反例与逐流/CNP/PFC/发送计数列在[结果报告](../research/ws24-independent-synthetic-effects-report.md)和[描述性指标](../research/evidence/ws24-independent-descriptive-metrics.json)。
5. 矩阵首批 8 格构建后，一次错误启动命令少写拓扑名的 `_topology` 后缀，worker 在仿真启动前拒绝，8 个 ID 当时仍为 `BUILT`，未形成失败 raw。观察器已先启动并继续采样；改用正确参数直接调用**同一 WS-24 隔离 worker**在这些同 ID 上启动，8 格均含 `RUNNING` 采样并通过全部验收。该控制器调用失误没有被写成仿真通过或另起未记录 ID。

## 4. 已形成的设计决策

按冻结协议的双侧判据报告**合成生成分布内的方向证据**，不因正向结果改变样本单位或事前门槛。30 条流只用于逐流正确性与描述，12 个 job 才用于符号检验；旧 10 流单 seed pilot 不并入。无需为取得更大的收益追加调参或扩大 job 样本。用户的仅 ns-3 范围决定已见 ADR-009，本次没有再变更范围。

## 5. 当前状态

WS-24 在用户确认的 ns-3 合成范围内完成全部清单项，可标为 `COMPLETE FOR NS-3 SYNTHETIC MULTI-RAIL AND PLACEMENT VALIDATION`。本交接编辑前，本地 `feature/ws24-multinic-validation` 与个人 `origin` 同为 `0c5da72141bbe3efdee93b32db0e4a99f342b94d`、工作树干净；随后新增的报告、机器收据和状态文件需正常提交与核对最终 Git SHA。原始结果留在 Git 忽略的本地 `results/<ID>/` 和远端同 ID 目录；只把摘要和索引入 Git。

## 6. 未解决问题与边界

本范围内无必做验收项剩余。12 个需求块只由合成生成器产生，模拟器 seed 与拓扑固定；没有真实物理共享、生产 job 分布或业务 SLO。CNP 计数与尾部的同现不足以单独证明因果；PFC=0、无重传 payload 超额意味着这些动态分支未在本矩阵中被测试。若未来论文提出真实部署或更广泛放置结论，需新的数据来源和独立事前契约，不能沿用本次结论外推。

## 7. 后续推荐动作

WS-25 引用时应标为“独立合成 job 的 ns-3 内部双侧方向证据”，同时保留 `j02` 极端收益、`j11` 微小收益、`j09` 放置差异及模型限制。若新论文主张要求真实主机效应或业务阈值，应先取得可核验映射、需求和 SLO，再另立工作流。当前无 WS-24 新仿真门槛；不因本 Handoff 自动归档对话。

## 8. 与其他工作流的关系

旧 A/B/C/D 14 格、point-to-point 单测及 v2 最小正负例保持原 SHA/原始证据，未被本矩阵覆盖；旧的单 seed −173/−164 ns 不计入 12 个独立重复。WS-23 端到端传输恢复仍独立 ACTIVE，其 checkout、共享 worker 和原始数据未被本工作流修改。WS-10/11/12/19/20/21 的既有结论未被重判。

## 9. CONTEXT SNAPSHOT

WS-24 只做用户同意的 ns-3 合成模拟。正式 SHA `3b992eed218f65b4f8026eddb5170a7694e17b10`、manifest `e2d19c…` 的 12 job × 四臂 48/48 raw 与资源已验收；远端/本地 1,056 文件哈希全同。12 个 job 主效应都为负，中位 −19.667%、精确双侧 `p=0.00048828125`、中位区间 `[−25.796%, −6.868%]`。详细原始 ID 在 manifest，机器重算在 `docs/research/evidence/ws24-independent-synthetic-effects-summary.json`，解释在 `docs/research/ws24-independent-synthetic-effects-report.md`。WS-24 可按合成范围闭环，不宣称真实部署收益；WS-23 仍 ACTIVE。
