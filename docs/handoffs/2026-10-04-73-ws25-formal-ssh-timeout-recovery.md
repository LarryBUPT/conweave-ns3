# Handoff 73：WS-25 正式矩阵 status SSH 长时间不退出与恢复

日期：2026-10-04。WS-25 第一课题；本次是重复的控制层 SSH 停滞诊断。正式矩阵仍 ACTIVE，没有正式性能结论。

## 1. 本对话目标

修复正式矩阵续跑时只读 SSH 查询长时间等待的问题，保留固定正式协议、仿真源码 SHA、576 原 ID 和现有 raw；确认现场安全后从原 ID 防重恢复。

## 2. 已确认的项目事实

- 正式矩阵仍固定仿真/输入源码 `ce699dffe2845dc83e2171a1c309c6d96b96d2b3`，24 个最终需求 seed × 4 背景档 × 6 模式，共 576 格；计划和随机次序未修改。
- 前 9 批 144/576 格已 raw、哈希、完成率和资源验收。执行摘要在 `results/ws25-v1fix-formal-summary.json`，计划及执行收据在 `docs/research/evidence/ws25-v1fix-formal-plan.json`、`results/ws25-v1fix-formal-receipts.jsonl`。
- 上次续跑在 144 格之后退出。stderr 表明本地 `remote_experiment.py status` 收到完整 `BUILT` metadata 后，SSH 仍未退出；子进程在 600 秒控制器超时后报错。主对话精确结束 4 个旧 `ssh.exe`，未动远端结果或 144 格 raw。
- 设置 45 秒 timeout 后重试，SSH 仍在输出 `BUILT` metadata 后挂起并按新 45 秒上限终止，唯一 runner 再次安全退出；仍无新仿真启动。故障只在 `remote_worker.py status <id>` 这一路复现；单次批量 metadata/输入核对 SSH 能正常结束。
- 改成单 ID 直接读取 metadata 后，CLI status 单次探测成功；但第三次 runner 的四路并发远端检查仍有一条 trace SHA SSH 到 45 秒超时。一个超时错误包含字面字符串 `metadata.json`，旧 `build_one` 将它误判为 metadata 缺失，尝试复用已有 ID 构建；远端以 `Experiment ID already exists` 拒绝，随后 status 回读确认仍为 `BUILT`。无仿真启动、无数据改写。证据表明控制面应串行访问服务器，并以明确缺失标记区分状态超时和确实没有 metadata。
- 一次只读 SSH 核对第 10 批相关 16 个原 ID：全部 `BUILT`、metadata 源码 SHA 与 `ce699df…` 相符、raw 文件数均为 0；16/16 trace SHA 与正式计划相符，拓扑 SHA 均为 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。远端没有其他普通用户进程、活动 worker/ns-3 或持有的 `simulation-start.lock`。
- 远端最近资源审计：load 0.0、可用内存约 122 GiB、可用磁盘约 5286 GiB，无活动仿真。未达到任何资源停止线。

## 3. 已完成工作

1. 停止并核对本地上一 runner 已退出；读本地收据为 144 格 verified，没有对应旧 runner。远端仅做一次批量只读核验，确认 16 个原 ID 状态、输入与拓扑哈希、raw、其他用户进程和锁状态。
2. 在 `remote_experiment.py` 缩短 keepalive 间隔并按操作配置超时：`status/audit` 45 秒、`fetch-check/run` 60 秒、构建与同步仍保留 1800 秒；结果 SCP 增加 1800 秒上限。
3. `run_ws25_preflight.py` 的本地控制器等待设为 90 秒；watcher 启动、等待、配置日志检查及 SCP 均设有适当上限。校准 trace 哈希读取与其他用户进程审计 SSH 设为 45 秒，资源审计经 `remote_experiment.py audit` 使用 45 秒上限。
4. 将 `remote_experiment.py status` 改为经单次短超时 SSH 只读读取并验证远端该 ID 的 `metadata.json`，避免调用会卡在退出阶段的 `remote_worker.py status` 路径；RUNNING 状态仍在远端检查记录 PID 并输出存活信息。对已知挂起 ID 实测，新 status 命令在 1 秒内返回 `BUILT` 和固定 SHA。
5. 再修正式 runner 将一批四路并发的状态/trace SSH 检查改为串行，消除控制面并发连接；trace 超时改为带 ID 的可读错误。metadata 缺失改由明确 sentinel 表示，只有确实缺失时才允许 build-one 恢复，超时错误不再可能触发对现有 ID 的 build 请求。
6. 串行预检同一批 16 个原 ID 全部快速通过：status `BUILT`、源码 SHA 匹配、trace 哈希匹配；资源门通过（load 0.0、可用内存约 122.89 GiB、空盘约 5285.4 GiB）。修复提交并推送为 `805e5438b4358802d5c9664c47b02ef5ade6caec`。
7. 以唯一 runner PID `46324` 从原计划恢复，第十批 **16/16 ID 已发出启动请求**；截至 2026-10-04 14:24（北京时间），本地收据为 160 started、144 verified，batch 10 尚未终态，stderr 为空。仿真进入后台静默阶段，后续按半小时监督。
8. `py_compile`、`git diff --check` 和冻结计划 576 格核对通过；改动仅限本地控制/恢复层与状态记录，未改仿真源码、输入、计划、ID、停止线或统计判据。

## 4. 已形成的设计决策

只读 SSH 检查与本地子进程都必须有有限超时。构建、同步与结果传输使用长上限；状态、资源、输入哈希及锁前检查使用短上限，以免网络连接卡住时 runner 无限占用。正式控制器对 status 直接安全读取 metadata，绕开持续无法收尾的远端 worker status 入口。传输异常时依赖同 ID 状态回读，不重复构建或覆盖已验收结果。正式协议保持原样。

## 5. 当前状态

控制器恢复改动已推送至个人 fork `feature/ws25-first-paper`，最新提交 `805e5438b4358802d5c9664c47b02ef5ade6caec`；工作树干净。唯一 runner PID `46324` 已从原 ID 恢复，第十批 16/16 已启动，formal raw/资源验收进度仍为 144/576；批次运行中。远端启动前无人作业、资源门与锁检查均通过。WS-25 保持 ACTIVE。

## 6. 未解决问题

- 剩余 432 格尚未完成，包含已构建未运行的第十批 16 格；正式双主结果、五基线对照、低档约束、双侧分析和论文初稿尚未完成。
- SSH 不退出的底层网络原因尚未确认。本修复把等待限制在有限时长并保持可恢复，不将此故障误分类为仿真失败。
- 未见正式性能结论；不得把校准、构建或 144 格部分矩阵称为收益证据。

## 7. 后续推荐动作

提交并推送超时修复，复核分支干净、远端无人作业/无活动仿真/锁释放和资源停止线，然后以实际 Luna High 启动唯一 `python scripts/run_ws25_formal.py run`。沿冻结 576 ID 续跑，已验收 144 格只读复验；逐批验收 raw、哈希、完成率与资源后扩批。全部 576 格 raw 终态验收后实际切 Sol High 做正式双侧分析、反例解释与小论文初稿。

## 8. 与其他工作流的关系

只涉及 WS-25 正式矩阵的控制器等待和恢复。个人 fork 中固定仿真 SHA、输入、正式计划和统计判据不变；只读参考仓库、旧工作树、其他 WS 结果均未修改。

## 9. CONTEXT SNAPSHOT

WS-25 正式矩阵固定 `ce699dffe2845dc83e2171a1c309c6d96b96d2b3`，24 seed × 4 背景档 × 6 模式 = 576 ID。前 9 批 144 格 raw/资源验收。status 命令曾在输出 metadata 后不退出；直接 metadata status 解决该入口。四路并发 trace 检查有一次 45 秒超时；旧错误判断又把异常文本误判为缺 metadata，远端拒绝了已有 ID 的重复 build，原 ID 后续状态仍为 `BUILT`，没有覆盖或仿真。现在 status 只在明确远端缺 metadata 时走 build 恢复，正式批次远端 status/trace 检查串行。提交 `805e543…` 已推送；唯一 Luna High runner PID `46324` 已恢复第十批，16/16 已启动，仍待 raw 终态验收。前144格不重跑；后续逐批 raw/哈希/完成率/资源验收后扩批，576格全终态后切 Sol High 分析。无正式效果结论，WS-25 ACTIVE。
