# WS-29 三格回归执行入口

2026 年 10 月 22 日。本阶段已完成本地准备，等待主对话的三格仿真 GO。准备阶段未使用 SSH。27 格计划中的其余 24 格继续关闭，效果 pilot 也保持关闭。

## 固定材料与顺序

仿真源码固定为 `3e68b3604e93cf34a4d938ebb48f1b1e0cfc988f`。每格重新构建独立、未修补的源码副本，按以下顺序执行。前一格须完成 raw 验收，才允许构建下一格。

| 顺序 | 新版计划 ID 后缀 | 输入流数 | 旧 reference |
| --- | --- | ---: | --- |
| 1 | `legacy-v2-hb200` | 1 | `20260930-020200-ws21hb-k4-200us` |
| 2 | `mixed8-c0` | 8 | `20261015-000010-ws28-technical-classreserve` |
| 3 | `main-c0` | 16,576 | `20261013-030000-ws27-confirm-s20262721-b192-classreserve` |

三格 ID 共用前缀 `20261022-180000-ws29-obs2-`。原 [27 格计划](evidence/ws29-engineering-plan-observation-v2.json)的 SHA-256 仍为 `5db623e7b38109a43ef0c37e0203e29713c896fe61e4d44581fd9512b551e8fd`。输入、ID、故障、控制间隔和验收门槛均未修改。[命令清单](evidence/ws29-regression-entry.json)记录各格的完整参数。

## 本地兼容核查

入口为 [run_ws29_regressions.py](../../scripts/run_ws29_regressions.py)。`prepare` 仅核对本地计划、固定 Git blob 和旧 reference 哈希。`build`、`start` 和 `collect` 每次只操作显式指定的一格，脚本没有自动推进下一格的循环。

legacy mode 20 保持 `WS18_PATH=1`、identity=1、STATE=0、HB=1 和 200,000 ns 心跳间隔。旧 reference 的 identity=0；本次 identity=1 已在固定计划中披露。验收器仅允许这一诊断字段差异和输出路径差异，继续比较其余旧配置字段。旧配置没有 `WS23_PFC_PROBE`，新配置须明确为 `-1 3 0 0`，`PAUSE_TIME` 须为 `5`。

两个 C0 格保持 mode 21、arm=0、identity=1、STATE=0 和 HB=0。控制器在校验及 metadata 写入前，按固定 `run.py` 的 arm 规则计算有效开关，并向 `run.py` 传递对应参数。三格均关闭 WS-13、WS-25 和 WS-28 额外诊断。固定源码已经通过 `WS29_ARM` 开启 C0 所需的逐 QP 传输日志，无需打开 `WS25_DIAG`。worker 在新版 ID 中清除继承的诊断环境变量，再应用显式参数。

本地共 20 项测试通过。新增测试把三格命令经过本地控制器和远端 worker 的参数解析器，核对最终 metadata；还调用固定 SHA 的 `run.py` 生成配置，并在调用 Waf 前截停。生成配置与三份旧 reference 的共同字段逐项一致。NumPy 的未使用导入和本机 Python 3.12 不再接受的 datetime RNG seed，仅在配置生成测试中被替代；这些替代未进入 runner 或仿真源码。

## GO 后的操作

主对话确认运行上下文并放行后，先推送新的控制器提交、部署 worker，再同步个人 fork。随后在本工作树内操作第一格：

```powershell
python scripts/run_ws29_regressions.py build --label legacy-v2-hb200
python scripts/run_ws29_regressions.py start --label legacy-v2-hb200
# 终态后回传并验收；运行中使用此命令只会返回 RUNNING。
python scripts/run_ws29_regressions.py collect --label legacy-v2-hb200
```

`collect` 成功后，再分别对 `mixed8-c0` 和 `main-c0` 使用同样的三条命令。正常运行按项目约半小时监督一次；完成或失败时及时处理。脚本记录 PID 和建议检查时刻，启动后立即返回，不进行短间隔 SSH 轮询。

`build` 前检查其他普通用户作业、仿真进程、活动元数据、启动锁、ID 空闲性和资源余量。构建后及启动前，再核对独立副本的 HEAD、tracked diff 和 core 测试文件原始哈希。副本必须没有兼容补丁或 `build-ws29-tests` 目录；构建命令不含 `--unit-suite` 或 `--unit-compat`。

`collect` 回传结果并调用完整的 `verify_ws29_engineering.verify`。验收包含源码与配置身份、输入哈希、全部流及字节守恒、逐字节 FCT 回归、控制关闭状态、诊断完整性和资源门槛。第一格兼容旧 mode 20 的配置结构，同时要求实际 HB 生成和 ACK 接收记录。各格验收收据保存到 `results/ws29-regression-control/<label>.verified.json`。

## 资源 pilot 与失败停止

本阶段保持并发 1，每份构建使用 `-j2`。新版 ID 的构建采样写入 `logs/build-resource-samples.jsonl` 和 `build-resource-summary.json`；仿真采样写入 `logs/resource-samples.jsonl` 和 `resource-summary.json`。两阶段各自保留原始样本，仿真终态收据须为 `SUCCEEDED`。采样间隔为 5 秒，短仿真至少保留首个样本。首格为初始资源记录，主输入格补充大拓扑与主负载占用；三格完成也不自动开放并发扩展。

沿用固定计划门槛：进程树 RSS 上限 32,768 MiB、可用内存下限 32 GiB、磁盘下限 100 GiB、1 分钟负载上限 20、单份文本日志上限 50 MiB。事件上限保持 500,000 条 WS-29 记录和 20,000 条 HB 记录。

命令返回码、原始 stdout 路径、预检结果、PID 和验收摘要写入 `results/ws29-regression-control/commands-and-events.jsonl`。构建、启动、终态或验收失败时，保留原 ID 与全部日志，并写入 `STOP.json`，阻止后续格和自动重试。网络中断后先读原 ID 的状态；任何恢复动作由主对话核验原始收据后决定。任务当前仍为工程验证进行中。

文档已按阮一峰[中文技术文档写作规范](https://github.com/ruanyf/document-style-guide)的原文检查标题、文本、段落、数值和标点。
