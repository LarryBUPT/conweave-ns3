# WS-25 DestSpread v2 唯一修正的独立探索筛选

状态：2026-10-06，任何本筛选格远程构建或仿真前冻结。先完成[13 格小输入正确性/诊断](ws25-v2r1-diagnostic-correction-protocol.md)，再执行本计划；筛选只决定是否进入独立校准 pilot，不是正式收益证据。

## 固定身份与运行顺序

- 需求 seed `20262577–80` 为四个新的独立单位，与 v1 的筛选/校准/正式 seed、v2 原筛选 `20262545–48`、预留 pilot `20262549–52` 及未见正式池 `20262553–76` 均不重合。生成器仍为 `scripts/make_ws25_demand.py`，每 seed 16,384 条 8 KiB MoE 与 192 条 8 MiB 背景流，均从 2.000 s 开始。输入 SHA 见[manifest](evidence/ws25-v2r1-screen-inputs.json)。
- 六主臂 ECMP、DRILL、CONGA、LetFlow、ConWeave、修正版 DestSpread 同 seed 使用逐字节相同 trace；每 seed 增加一格候选 `ws25_diag=1` 非扰动诊断，共 28 个预先分配的唯一 ID。源码提交 `5a4334116bdb38466533204af51f6f12d77d07b4`；其中仿真 `src/`、`scratch/`、`run.py` 与修正提交 `206888df97e2fd5fd37656d51deda5fb6a4e96c1` 完全相同。拓扑 SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。
- 精确 ID、trace SHA、随机块顺序和运行参数保存在唯一[冻结计划](evidence/ws25-v2r1-screen-plan.json)。随机顺序 seed=`2026100617`；第一块为需求 seed `20262579` 七格，须先逐格验收，再扩至其他块。控制器的改动不改变计划、原 ID 或仿真源码；失败 ID 不复用、不覆盖 raw。
- 共同运行配置：ns-3 seed=1、400 Gbps、9 MiB、DCQCN、PFC=0、IRN=1、`simul_time=0.01`、`netload=10`。六主臂 `ws25_diag=0`。诊断格仅开启 `ws25_diag=1`，完整原始 FCT SHA 须与同 seed 候选主格相同。

## 原始验收与预设探索门槛

每格检查 metadata、源码/trace/拓扑 SHA、参数、FCT 原始文件与输入流身份/字节、两类全完成率、候选类别队列守恒和资源收据。候选 `moe_new + moe_reused = moe_packets`，两项均须正值；背景新建/复用也须正值，队列违规与 fallback 为 0。诊断格应有 16,576 条唯一 QP，tag1=192、tag2=16,384；逐 QP 乱序、SACK/CNP、重复发送、超时恢复字段齐全，背景逐跳记录与未配对计数有效。缺失观测不能填零；诊断 FCT 有扰动则保留 raw、停止将其解释为非扰动机制证据。

MoE 合成批次是最后一条 MoE 流的绝对完成时刻减 2.000 s；背景 P99 是 192 条背景 FCT 的线性插值第 99 百分位。每 seed 对 ECMP 的变化为 `100×(DestSpread/ECMP−1)`；越低越好。**只有 28/28 全部通过**，且两项各自四 seed 中位变化 ≤−5%、至少 3/4 严格改善，才进入另组 `20262549–52` 的校准 pilot。其他四基线的两项绝对值、配对变化、机制及反例都报告。未过时保留负结果；v2 修正额度已用，只能评估第三候选或形成有边界的负结果，不再修 v2。筛选不用于确认性显著性或正式 NO-GO，正式 24 seed 的双侧门槛须在最终池揭盲前另冻。

## 资源和恢复

首块 cap=1，以全量需求实测资源；后续块只有在首块逐格通过且新准入检查通过后尝试 cap=4。每批前核无其他用户作业、未知 ns-3/worker、启动锁、load≤20、每 worker 预留 5 GiB 后 MemAvailable≥32 GiB、空盘≥100 GiB；watcher 先于 run，单格树 RSS≤32 GiB。发生争用、资源异常、失败或吞吐下降，暂停新格或降载。SSH/build/fetch 超时先按原 ID 查 metadata/PID/raw、本地收据和远端在途；绝不双重启动或覆盖已验收 raw。仿真静默后台执行，正常精简监督；所有格终态 raw 回传并验收后实际切 Sol High 分析。
