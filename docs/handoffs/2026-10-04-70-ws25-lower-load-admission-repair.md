# Handoff 70：WS-25 低负载校准准入修复

日期：2026-10-04。来源任务：`01a0fc98-726e-76e1-8f85-2fb5dbe8d0c4`，WS-25 第一课题。此记录是阶段交接，WS-25 保持 ACTIVE。

## 1. 本对话目标

恢复已冻结的 0/64/128 档 72 格校准。用户要求实验与分析自动衔接，人工仅问询和纠偏；远程长时运行须由主对话实际切至 Luna High，终态分析再实际切回 Sol High。

## 2. 已确认的项目事实

- 唯一执行计划仍为 [r3 计划](../research/evidence/ws25-v1fix-lower-load-calibration-plan-r3.json)：四个独立需求 seed × 三档 × 六模式，共 72 个固定 ID；仿真/输入源码 SHA `a656104d05c681f9b3a998b5ef4ce3e644558d02`，拓扑和输入 SHA 均未修改。
- 全部 72 个远端 ID 为 `BUILT`，源码 SHA 一致，raw 目录均为空。首格 `20261004-030000-ws25-lower-s06-b064-fecmp` 在仿真启动前被高容量准入拒绝，metadata 仍为 `BUILT`；本地收据只新增一次 `batch_start`，没有 `started` 或算法数据。
- 拒绝原因是远端 worker 高容量白名单原本只登记四份 192 档 trace，漏了冻结的 12 份 0/64/128 档 trace；错误文本为 `High capacity trace is not frozen`。这不是路由机制或仿真正确性失败。
- 当前两类业务仍由模拟器内 RDMA QP 承载；tag1/tag2 是业务类别，不是传输协议混跑。MoE 批次和背景尾部须作为共同主要结果，正式判据不得仅把背景当可容忍的损害约束。

## 3. 已完成工作

1. 只读核对首格 metadata、raw、进程与资源：首格 `BUILT`、无 raw、无活动 ns-3；现场 load 0.0、可用内存约 122.93 GiB、空闲盘约 5409.8 GiB，且 host gate 未发现其他普通用户作业。
2. 对 PID `317062` 核实命令行确为首格资源 watcher 后停止。其 `resource-samples.jsonl` 与日志原样归档到该 ID 的 `logs/aborted-admission-20261004/`，采样文件 SHA-256 `afb0575efa4618af72e4a2cdeabad825e2745cf8edb5f306439b15a63e9593e8`；未覆盖 raw。另对旧弃用 diag ID 的孤立 watcher PID `256465` 做相同核验和归档，归档采样 SHA-256 `dc8ebe6640232f9809a23a53314ec1d5515fd7c2fbf2f36a20188c6f430e17a9`。
3. 只改 `scripts/remote_worker.py` 的高容量输入白名单，补入 12 份冻结 trace 的名称和 SHA，保留原四份 192 档条目及源码、拓扑、参数、其他用户、内存、磁盘和并发保护。修复提交 `6c699ce29dd0957222ac666c29395f8764cb1a5e` 已推送个人 fork 的 `feature/ws25-first-paper`，并经项目 `deploy` 更新远端 worker。
4. 本地语法、`git diff --check`、manifest 与 16/16 文件哈希、72/72 计划映射均通过；本地和远端 worker SHA-256 均为 `55338e85cc8ac98f49af441bdf7321b0d720565d294641f70de4432ded109257`。远端对 16/16 trace 实际文件重算哈希，并用冻结首格参数直接调用准入检查通过。没有启动仿真。

## 4. 已形成的设计决策

- 保持 72 个原 ID 与 r3 运行顺序，因为拒绝发生在写入 `RUNNING` 及生成 raw 之前。首格监控收据先归档，再由既有执行器为相同 `BUILT` ID 重新创建 watcher；旧的 `batch_start` 收据保留，下一次运行会追加新 `batch_start`，分析时只以各 ID 的 metadata/raw/逐格验收为实验结果。
- 仅扩大允许的冻结输入集合，不放宽任何资源门槛或改变 cap=16。18 路容量 pilot 的吞吐增量低于既定 5% 升档线，该决策不变。

## 5. 当前状态

- 截至本记录，工作分支 `feature/ws25-first-paper`；worker 修复提交 `6c699ce…` 已推送，远端部署哈希一致。72/72 仍为 `BUILT`，0/72 已运行，0/72 有 raw；本地正式摘要文件尚不存在。
- 远端 host gate 通过：无活动仿真、无其他普通用户作业，load 0.0、可用内存 122.93 GiB、空闲盘 5409.8 GiB。首格准入直接验证通过。
- 当前停在远程长时运行的模型边界。尚未以修复后的 worker 执行仿真；不能报告低负载校准结果或正式收益。

## 6. 未解决问题

- 72 格仍须按批运行、回传并逐格验收；资源或任一格失败即停后续批次并保留 ID/raw。
- 完成后仍须核查各档双侧结果和五基线动态分支覆盖，冻结正式双侧数值判据、样本量、未见 seed/ID，再做正式验证及成稿。最终需求池 `20262521–44` 尚未用于本轮。

## 7. 后续推荐动作

1. 主对话实际切换至 GPT-6 Luna High 后，先复核远端 `host_gate(reject_active=True)`、72 个 `BUILT` ID 和首格监控路径已清空，然后在本分支运行 `python scripts/run_ws25_lower_load_calibration.py run`。该执行器每批最多 16 格，逐批回传/验收后才扩批。
2. 正常运行约每半小时读取精简进度和资源收据；失败或资源异常立即停止新格并诊断，不覆盖原始数据。
3. 72 格终态且 raw 回传后，由主对话实际切回 GPT-6 Sol High，执行逐格 `verify`、双侧配对分析、反例和缺口核验。

## 8. 与其他工作流的关系

本次只修个人 fork 的远端执行器；既有仿真源码快照和五基线未改，旧正式 NO-GO 不重判。WS-21 状态反馈仍在投稿后的第二课题门槛。

## 9. CONTEXT SNAPSHOT

WS-25 仍 ACTIVE。0/64/128 档 72/72 已预构建、0/72 已仿真。首格因 worker 漏登记低档输入而被拒于启动前，原 ID/raw 安全；孤立 watcher 已精确停止并归档。白名单补齐、提交推送、远端部署和 16/16 输入哈希及首格准入验证完成；worker 提交 `6c699ce…`，仿真源码仍固定 `a656104d…`。下一步是主对话实际切 Luna High 后按 r3 原计划运行，终态切 Sol High 分析；当前无新的算法效果结论。
