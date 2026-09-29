# WS-21 精简反馈：构建、单测与 40 流 pair 预飞行表

冻结日期：2026-09-29；当前已在 GPT-6 Luna High 下执行首道工程门槛。本表只覆盖 v2 报文构建、单测和 40 流 pair，不含长尾间隔矩阵、心跳或效果比较。终态 raw 回传后再实际切回 GPT-6 Sol High。源代码固定分支 `feature/ws21-downstream-feedback` 与 SHA `91f43c70bbb515ae35b3161d4d1e40d30ff90992`；若修复仿真源码，旧 ID 保留并另立 SHA/ID，不能在原格继续。

## 固定输入和顺序

| 顺序 | 预留实验 ID（`build --id` 显式指定；ID 中时间是标签，不代替实际启动时间） | 动作与唯一变量 | 通过后才能继续 |
| --- | --- | --- | --- |
| 1（已失败，保留） | `20260929-185100-ws21c-v2-unit` | 同 SHA optimized `-j2` build 为 `BUILT`；测试构建在 1,522/1,633 步遇到既有 core 测试 const helper 声明/定义不一致，v2 测试未执行 | 失败证据保留；不复用该 ID |
| 2（通过，含执行器修正） | `20260929-192700-ws21c-v2-unitfix` | 新隔离副本重新构建；仅在该副本临时同时修正同一 helper 的声明和定义参数 const，测试后逐字节恢复。测试模块编译后，首个 wrapper 未识别带版本/优化后缀的运行器；随后设定隔离库路径直接运行 | `devices-point-to-point` PASS；恢复/资源收据齐全，可进入 off40 |
| 3 | `20260929-185200-ws21c-v2-off40` | 新副本构建并运行 40 流；`--ws21-feedback 0` | 完成/字节/身份正确、raw 和资源收据齐全 |
| 4 | `20260929-185300-ws21c-v2-on40` | 新副本构建并运行同一 40 流；只改 `--ws21-feedback 1` | 在第 3 格成功后启动；核对报告与业务双侧指标 |

每个尚未开始的 ID 均须在远端 `runs/`、`results/` 和本地 `results/` 检查不存在后使用；任一已存在则停止并在运行前修订预飞行表，绝不复用或覆盖。`scripts/remote_experiment.py build --id` 支持显式 ID；`run` 使用同 ID。两个 `unit` ID 都不启动 `run`；测试只写自己的隔离目录/日志。40 流两格必须各有独立源码副本和原始输出，不能拿 unit 构建目录当仿真目录。初次单测失败后，off/on 暂停，待新的 unitfix ID 通过才可继续。

Luna 阶段的命令形态（分别把 `<ID>`/`<0或1>` 换成上表对应行；先完成 unit 格再执行两次仿真格）：

```powershell
python scripts/remote_experiment.py deploy
python scripts/remote_experiment.py sync --repo-local .
python scripts/remote_experiment.py build --repo-local . --id <ID> --source-sha 91f43c70bbb515ae35b3161d4d1e40d30ff90992
python scripts/remote_experiment.py run <ID> --lb ws18 --simul-time 0.01 --netload 10 --bw 400 --buffer 9 --topo topo_1280_400G_400G_OS1 --cdf AliStorage2019 --flow-file ws18_1280_correctness.txt --pfc 0 --irn 1 --ws18-admission 0 --ws18-path 0 --ws18-admission-rate-gbps 400 --ws21-identity 1 --ws21-port-events 0 --ws21-feedback-interval-ns 10000 --max-concurrent 1 --ws21-feedback <0或1>
```

最后一行只用于 off/on 两格；unit 格在独立测试构建后执行 `LD_LIBRARY_PATH=build-ws21-tests ./build-ws21-tests/utils/ns3.19-test-runner-optimized --suite=devices-point-to-point`，保留测试日志。若遇到 Handoff 30 记载的无关 core 测试 const 编译问题，只在 unit 隔离副本中临时修正声明和定义、测试后恢复并检查源码文件与固定提交一致；不得把此临时改动带入仿真格。

共同仿真与 runner 源码 SHA：`91f43c70bbb515ae35b3161d4d1e40d30ff90992`；本表的后续文档提交会移动分支 HEAD，所以三个 `build` 均须显式传 `--source-sha 91f43c70bbb515ae35b3161d4d1e40d30ff90992`，不能默认构建文档 HEAD。个人 `origin/feature/ws21-downstream-feedback` 必须与本地文档 HEAD 同 SHA、工作树干净，且该源码 SHA 是其祖先。Luna 阶段先 `deploy` 更新后的 worker，再 `sync` 个人 fork。40 流 trace `config/ws18_1280_correctness.txt` SHA-256 `4e7d0e6a68e3230e8960a174e570a0a788c191fa0b44922408867b02c25782cc`，拓扑 `config/topo_1280_400G_400G_OS1.txt` SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。输入预期 40 流、33,849,344 B；seed=1。固定参数：`--lb ws18 --simul-time 0.01 --netload 10 --bw 400 --buffer 9 --topo topo_1280_400G_400G_OS1 --cdf AliStorage2019 --flow-file ws18_1280_correctness.txt --pfc 0 --irn 1 --ws18-admission 0 --ws18-path 0 --ws18-admission-rate-gbps 400 --ws21-identity 1 --ws21-port-events 0 --ws21-feedback-interval-ns 10000 --max-concurrent 1`；只变反馈开关。两个格的 `metadata.json`、`config/config.txt`、trace/拓扑快照须逐项相同（开关除外）。

## 资源预检和收据

先只读核对服务器无他人作业、无其他 ns-3/`run.py` 活动、SSH/存储正常；记录 UTC/北京时间、负载 1/5/15 分钟、可用内存/磁盘、CPU、当前进程列表摘要。预检门槛：1 分钟负载不高于 10、可用内存至少 32 GiB、工作区磁盘至少 100 GiB；任一不满足或其他用户在运行任务则不启动。运行器自身还要求可用内存 ≥4 GiB、磁盘 ≥20 GiB、负载 ≤20；本表的预检线更保守。构建串行、每份 `-j2`；仿真 `max-concurrent=1`，不扩大并发。

每格 `run` 返回 PID 后立即在该 ID 的 `results/<ID>/logs/` 启动项目既有 `scripts/ws11_resource_watch.py <ID> --interval 2` 静默采样，保留 `resource-samples.jsonl` 和 `resource-summary.json`；两文件不得已存在。另保存 `metadata.json` 的 PID、实际开始时间、SHA、**预期**输入/拓扑哈希、预计首次检查 UTC 时间（开始后 10 分钟；若仍运行，下次约 30 分钟后）；终态再从配置快照核对**实际**哈希。读取监督摘要而不持续打印日志。暂停启动后续格的运行期条件：出现他人作业、1 分钟负载超过 20、可用内存低于 16 GiB、工作区磁盘低于 100 GiB、进程树 RSS 超过 8 GiB、任一文本日志达到 50 MiB、资源收据缺失或构建/仿真失败；先保留现有 raw 和独立目录，再查原因，不自动重跑。旧长尾格缺峰值 RSS，故本次必须有进程树峰值收据。

## 每格判据与停止

两个仿真格必须 `SUCCEEDED`、40/40 完成、33,849,344 B 守恒，40 条跨 ToR QP 身份映射无错，旧本地模式的路径/需求约束正确。开启格需 `generated=delivered>0`、`rejected=expired=hop_rejects=sequence_gaps=0`、逐跳入/出队计数相等、`hop_bytes>=delivered_bytes`、缓存峰值 ≤16,384；检查 `sample_age_max_ns >= age_max_ns` 和所有时间字段可解析。两格 FCT/WS18 raw 不强制哈希相同：真实队列反馈允许扰动；必须列逐流变好/变坏/不变数及 P50/P90/P99、反馈传输年龄/样本年龄与额外逐跳字节，不能把差异写成选路收益，因为缓存尚未参与选路。40 流上游 CE 样本在旧数据中为 0，此格不验证候选质量区分。

任一报告解码/身份/守恒错误、测试失败、参数/哈希错配或资源收据缺项，停止后续格并保留故障 ID。若仅是延迟、反馈丢失或业务 FCT 变化，记录为技术结果和退回风险，不按旧“FCT 必须逐字节相同”机械否定；但未证明安全前不进入长尾或效果阶段。完成后 `fetch` 两格和 unit 日志，按原始 raw 与 metadata 独立核验，再由 Sol High 决定是否追加长尾间隔格。旧 WS-21 技术失败、WS-19/20 等效果 no-go 均不因此追溯改判。

## Luna 阶段执行记录

2026-09-29 首次预检：服务器 `ns3host`，40 逻辑 CPU，`who` 无登录用户，活动仿真 PID 为空，load 1m=0.00、可用内存 122.99 GiB、工作区空闲 5,694.3 GiB；三项预留 ID 均不存在。个人 fork 经 SSH Git bundle 同步；直接 GitHub fetch 超时前已按流程静默尝试一次 `login.sh`。冻结 SHA `91f43c70bbb515ae35b3161d4d1e40d30ff90992` 的隔离 optimized `-j2` 构建 `20260929-185100-ws21c-v2-unit` 于 2026-09-29 11:13:54 UTC 为 `BUILT`。

该 ID 的独立测试构建在 1,522/1,633 步因仓库既有 `CommandLineTestCaseBase::Parse` 声明已去 const、定义仍带 const 而失败；WS-21 报文单测未执行。失败日志为 `results/20260929-185100-ws21c-v2-unit/logs/ws21-v2-unit-test.log`，248 个资源采样汇总 `unit-attempt-summary.json`：进程树峰值 RSS 809.7 MiB，最低可用内存 122.25 GiB，最低空闲磁盘 5,692.74 GiB，最大 load1m 2.14。tracked 源码干净、失败 ID 保留。新 ID `20260929-192700-ws21c-v2-unitfix` 中优化 build `BUILT`；临时同时修正声明和定义后测试构建完成。首个 wrapper 错误地只查找名为 `test-runner` 的文件并报未找到，实际文件为 `ns3.19-test-runner-optimized`。之后使用独立库路径直接执行 `--suite=devices-point-to-point`，结果 `PASS devices-point-to-point 0.000 s`；源码 SHA-256 `b7285686202442d47d339fd5817e9001c47bfc23377c8a8f5f596ba694373881` 恢复一致，tracked Git 状态干净，成功记录在 `logs/unit-runner-retry-summary.json`。两个早期 wrapper 失败日志保留，不覆盖。单测门槛现通过，可以在再次核对服务器资源和 off/on ID 未占用后进入 40 流格。

随后资源与 ID 检查通过，反馈关闭格 `20260929-185200-ws21c-v2-off40` 已在固定 SHA 和独立目录启动：PID 40088，开始时间 `2026-09-29T11:59:21Z`，资源 watcher PID 40135、间隔 2 秒。共同输入 SHA、参数见本表；参数 `ws21_feedback=0`。首次精简监督检查时间 `2026-09-29T12:09:21Z`；若仍运行，后续约每 30 分钟检查一次。反馈开启格不在关闭格完成、raw 和资源收据核验前启动。
