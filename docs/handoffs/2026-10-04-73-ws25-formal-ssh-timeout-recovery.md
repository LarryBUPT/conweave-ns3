# Handoff 73：WS-25 正式矩阵 status SSH 长时间不退出与恢复

日期：2026-10-04。WS-25 第一课题；本次是重复的控制层 SSH 停滞诊断。正式矩阵仍 ACTIVE，没有正式性能结论。

## 1. 本对话目标

修复正式矩阵续跑时只读 SSH 查询长时间等待的问题，保留固定正式协议、仿真源码 SHA、576 原 ID 和现有 raw；确认现场安全后从原 ID 防重恢复。

## 2. 已确认的项目事实

- 正式矩阵仍固定仿真/输入源码 `ce699dffe2845dc83e2171a1c309c6d96b96d2b3`，24 个最终需求 seed × 4 背景档 × 6 模式，共 576 格；计划和随机次序未修改。
- 前 9 批 144/576 格已 raw、哈希、完成率和资源验收。执行摘要在 `results/ws25-v1fix-formal-summary.json`，计划及执行收据在 `docs/research/evidence/ws25-v1fix-formal-plan.json`、`results/ws25-v1fix-formal-receipts.jsonl`。
- 上次续跑在 144 格之后退出。stderr 表明本地 `remote_experiment.py status` 收到完整 `BUILT` metadata 后，SSH 仍未退出；子进程在 600 秒控制器超时后报错。主对话精确结束 4 个旧 `ssh.exe`，未动远端结果或 144 格 raw。
- 一次只读 SSH 核对第 10 批相关 16 个原 ID：全部 `BUILT`、metadata 源码 SHA 与 `ce699df…` 相符、raw 文件数均为 0；16/16 trace SHA 与正式计划相符，拓扑 SHA 均为 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。远端没有其他普通用户进程、活动 worker/ns-3 或持有的 `simulation-start.lock`。
- 远端最近资源审计：load 0.0、可用内存约 122 GiB、可用磁盘约 5286 GiB，无活动仿真。未达到任何资源停止线。

## 3. 已完成工作

1. 停止并核对本地上一 runner 已退出；读本地收据为 144 格 verified，没有对应旧 runner。远端仅做一次批量只读核验，确认 16 个原 ID 状态、输入与拓扑哈希、raw、其他用户进程和锁状态。
2. 在 `remote_experiment.py` 缩短 keepalive 间隔并按操作配置超时：`status/audit` 45 秒、`fetch-check/run` 60 秒、构建与同步仍保留 1800 秒；结果 SCP 增加 1800 秒上限。
3. `run_ws25_preflight.py` 的本地控制器等待设为 90 秒；watcher 启动、等待、配置日志检查及 SCP 均设有适当上限。校准 trace 哈希读取与其他用户进程审计 SSH 设为 45 秒，资源审计经 `remote_experiment.py audit` 使用 45 秒上限。
4. 语法检查和 `git diff --check` 通过；核对 `python scripts/run_ws25_formal.py plan` 仍为 576 格、4 档、6 臂、随机种子 20261005、固定 SHA `ce699df…`。改动仅限本地控制/恢复层与状态记录，未改仿真源码、输入、计划、ID、停止线或统计判据。

## 4. 已形成的设计决策

只读 SSH 检查与本地子进程都必须有有限超时。构建、同步与结果传输使用长上限；状态、资源、输入哈希及锁前检查使用短上限，以免网络连接卡住时 runner 无限占用。传输异常时依赖同 ID 状态回读，不重复构建或覆盖已验收结果。正式协议保持原样。

## 5. 当前状态

改动待提交并推送至个人 fork `feature/ws25-first-paper`；观察到的本地 HEAD 为 `6f4d6f25150d9b78dd2ffc2a98fa2e501d493557`。正式矩阵为 144/576 格 raw 已验收，第十批原 16 ID `BUILT` 待运行。远端资源、用户作业和锁检查通过。控制器修复提交后可继续从正式计划恢复；WS-25 保持 ACTIVE。

## 6. 未解决问题

- 剩余 432 格尚未完成，包含已构建未运行的第十批 16 格；正式双主结果、五基线对照、低档约束、双侧分析和论文初稿尚未完成。
- SSH 不退出的底层网络原因尚未确认。本修复把等待限制在有限时长并保持可恢复，不将此故障误分类为仿真失败。
- 未见正式性能结论；不得把校准、构建或 144 格部分矩阵称为收益证据。

## 7. 后续推荐动作

提交并推送超时修复，复核分支干净、远端无人作业/无活动仿真/锁释放和资源停止线，然后以实际 Luna High 启动唯一 `python scripts/run_ws25_formal.py run`。沿冻结 576 ID 续跑，已验收 144 格只读复验；逐批验收 raw、哈希、完成率与资源后扩批。全部 576 格 raw 终态验收后实际切 Sol High 做正式双侧分析、反例解释与小论文初稿。

## 8. 与其他工作流的关系

只涉及 WS-25 正式矩阵的控制器等待和恢复。个人 fork 中固定仿真 SHA、输入、正式计划和统计判据不变；只读参考仓库、旧工作树、其他 WS 结果均未修改。

## 9. CONTEXT SNAPSHOT

WS-25 正式矩阵固定 `ce699dffe2845dc83e2171a1c309c6d96b96d2b3`，24 seed × 4 背景档 × 6 模式 = 576 ID。前 9 批 144 格 raw/资源验收。第十批相关 16 个原 ID 全部 `BUILT`、metadata SHA、trace/拓扑哈希一致、raw 空；无其他用户、活动仿真或持锁。上次续跑的 status SSH 返回 JSON 后挂住至 600 秒而退出，远端资源健康。为只读 SSH、控制器、watcher、trace 校验、审计和 SCP 补有界超时，仿真 SHA/计划/输入/ID不变。修复提交后以唯一 Luna High runner 从原 ID 恢复，按批验 raw 后扩格；576 格全验收再切 Sol High 分析。正式主效果尚无结论，WS-25 ACTIVE。
