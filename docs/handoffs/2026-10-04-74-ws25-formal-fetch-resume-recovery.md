# Handoff 74：WS-25 第14批 fetch-check 超时与安全续跑

日期：2026-10-04。WS-25 第一课题正式矩阵；冻结协议与实验身份不变。

## 故障和证据

- 正式计划仍为24个未见需求 seed × 4个背景档 × 6个模式 = 576个原 ID，36批×16；仿真/输入 SHA `ce699dffe2845dc83e2171a1c309c6d96b96d2b3`。
- 唯一 runner PID `29620` 在批14回传阶段异常退出。stderr 指明 `fetch 20261004-070000-ws25-formal-s41-b192-fecmp` 的只读 `fetch-check` SSH 达到60秒本地超时。退出前批14的16个 ID 均有 `started` 收据；正式 summary 保持208/576，批14尚无本地 raw 目录。
- 单次批量只读远端审计确认批14的16/16 metadata 状态均为 `SUCCEEDED`，仿真 SHA 与冻结值匹配，独立 run 目录保留 FCT、config 和解释性 raw；无仍运行的正式 worker metadata。其他普通用户进程为空；`simulation-start.lock` 未持有；load 0.04、MemAvailable 122.89 GiB、可用盘 5235.63 GiB。
- 初次进程扫描把诊断 SSH 命令自身误匹配为仿真命令；随后检查所有 `RUNNING` metadata/PID，结果为空。未把误匹配当作远端活动仿真，也未启动新格、重跑 ID 或覆盖 raw。

## 控制层修复

1. `run_ws25_formal.py` 可从现有 summary 的完整连续批次前缀续跑；先检查 source SHA、随机化种子、并发 cap、批次连续性和 ID 顺序，再用本地 raw 重新运行 verifier 并逐项比对保存行。summary 不完整或不一致时拒绝恢复。
2. 同一批所有远端 ID 已 `SUCCEEDED` 时跳过固定的300秒模拟轮询等待，直接进入逐格回传与验证。
3. 批次回传和验证改为单格串行。原4线程回传池在 `fetch-check` SSH 超时；新路径避免并发状态/校验 SSH。若此前某格已完整落在本地，续跑只验证该目录，不重复下载或覆盖。

以上只改本地控制器，不改冻结仿真源码、trace、拓扑、576 ID/顺序、统计门槛、资源停止线或已验收 raw。

## 验证与下一步

- `py_compile` 与 `git diff --check` 通过。
- 本地 resume 校验重新验收了现有208格，确认完整前缀为批1–13，下一批恰为批14；source SHA 与冻结计划一致。
- 修复提交 `094e198` 已推送至个人 fork。唯一 runner PID `5752` 从批14恢复，批14的16格均仅回传并通过逐格验证，summary从208推进到224；未重跑实验。随后它在批15的ID `20261004-070000-ws25-formal-s21-b192-conga` 缺失metadata后，因 `094e198` 当时还未推送而被本地 fork 安全门拒绝构建；未发出远端build/仿真请求，该ID仍未创建。提交现已推送，下一步从summary前缀批15恢复。
- 下次恢复先检查个人origin已含当前控制器提交、唯一runner数量为0、remote host gate通过；沿冻结计划检查ID225并继续。任何已存在本地目录先 verifier 核验，不重新运行、不覆盖raw。
- 576格终态 raw 与资源逐格验收前无正式性能结论；该事件不改变WS-25状态，仍为ACTIVE。
