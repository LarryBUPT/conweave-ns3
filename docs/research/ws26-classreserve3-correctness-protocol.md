# WS-26 ClassReserve v3 正确性预检

状态：修正后的 18 格正确性预检已完成，固定仿真提交为 `b6fc1a423774790f971ad86b64e1c1646d63c36b`。原首格 `20261008-030000-ws26-v3-pre-mixed8-p1i1` 在旧提交 `d4fb60dec340e282bd1150c82b2dfb2db9b64851` 下因 `missing_destination=16796` 验收失败；该 ID 和 raw 均保留，其余 17 个旧 ID 未启动。新提交修正了目的 ToR 映射初始化；本表中的 18 个新 ID 均已完成。本组只检查实现、旧模式回归和四种传输设置，不作为新候选的收益证据。日期：2026-10-08。旧 WS-25 seed 及本组小输入不进入 WS-26 正式样本。

## 固定输入与参数

全部格使用 `topo_1280_400G_400G_OS1`（SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`）、400 Gbps、9 MiB buffer、DCQCN、ns-3 seed=1、`simul_time=0.01` 和 `netload=10`。各格的 PFC/IRN 设置由下表决定。小输入沿用已验收的五份 trace，固定哈希见[WS-25 v2 正确性预检](ws25-v2-destspread-correctness-protocol.md)。新模式为 `classreserve3`（`LB_MODE 23`）；旧模式不得因新增分派而改变。

| 顺序 | 新实验 ID | 模式 | trace | PFC/IRN |
| ---: | --- | --- | --- | --- |
| 1 | `20261008-040000-ws26-v3-pre-mixed8-p1i1` | classreserve3 | mixed8 | 1/1 |
| 2 | `20261008-040001-ws26-v3-pre-background4-p1i1` | classreserve3 | background4 | 1/1 |
| 3 | `20261008-040002-ws26-v3-pre-moe4-p1i1` | classreserve3 | moe4 | 1/1 |
| 4 | `20261008-040003-ws26-v3-pre-unclassified8-p1i1` | classreserve3 | unclassified8 | 1/1 |
| 5 | `20261008-040004-ws26-v3-pre-legacy5-p1i1` | classreserve3 | legacy5 | 1/1 |
| 6 | `20261008-040005-ws26-v3-pre-unclassified8-ecmp-p1i1` | fecmp | unclassified8 | 1/1 |
| 7 | `20261008-040006-ws26-v3-pre-legacy5-ecmp-p1i1` | fecmp | legacy5 | 1/1 |
| 8 | `20261008-040007-ws26-v3-pre-mixed8-ecmp-p1i1` | fecmp | mixed8 | 1/1 |
| 9 | `20261008-040008-ws26-v3-pre-mixed8-p0i0` | classreserve3 | mixed8 | 0/0 |
| 10 | `20261008-040009-ws26-v3-pre-mixed8-p0i1` | classreserve3 | mixed8 | 0/1 |
| 11 | `20261008-040010-ws26-v3-pre-mixed8-p1i0` | classreserve3 | mixed8 | 1/0 |
| 12 | `20261008-040011-ws26-v3-pre-fecmp-mixed8-p0i1` | fecmp | mixed8 | 0/1 |
| 13 | `20261008-040012-ws26-v3-pre-drill-mixed8-p0i1` | drill | mixed8 | 0/1 |
| 14 | `20261008-040013-ws26-v3-pre-conga-mixed8-p0i1` | conga | mixed8 | 0/1 |
| 15 | `20261008-040014-ws26-v3-pre-letflow-mixed8-p0i1` | letflow | mixed8 | 0/1 |
| 16 | `20261008-040015-ws26-v3-pre-conweave-mixed8-p0i1` | conweave | mixed8 | 0/1 |
| 17 | `20261008-040016-ws26-v3-pre-background4-ecmp-p1i1` | fecmp | background4 | 1/1 |
| 18 | `20261008-040017-ws26-v3-pre-mixed8-diag-p1i1` | classreserve3 | mixed8，诊断开关开 | 1/1 |

每格使用独立源码目录、metadata、raw、资源 watcher 和收据；按表串行，cap=1。先查询原 ID 是否已使用，再决定 build/run/fetch。首格验收通过后才能扩展。

## 逐格验收与停止线

每格核对完整源码 SHA、输入和拓扑哈希、模式、传输参数及唯一 ID。逐流身份、标签、大小、完成数和 FCT 原始文件须匹配；任何未完成流使该格没有可比较性能值。候选的 `background_packets = background_new + background_reused`、`moe_packets = moe_new + moe_reused`，队列入队字节等于出队、丢弃和终态在队字节之和，违规计数为零。mixed8 应触发两类新建及缓存命中；`with_background` 和 `diverted` 可为零，但必须如实报告，不能据模式入口推断信号有效。

tag0、旧五列和背景单类的候选格必须逐字节匹配本组同输入 ECMP FCT。五个原仓库模式的 PFC=0/IRN=1 mixed8 格须与已验收的旧同参数指纹一致。四种传输设置的候选 mixed8 格均须全流完成，报告 PFC、CNP、乱序、重传和超时的可观测计数；不存在的观测标明缺失。第 18 格开启只读诊断，逐 QP 核对源 ToR 所选端口、包数与路径稳定性，并与第 1 格的 FCT 指纹比对非扰动。诊断记录数等于进入选路逻辑的新建 QP 数，即 `background_new + moe_new`；按标签统计的包数还须分别等于 `background_packets` 和 `moe_packets`。单路径或回退 QP 不产生所选上联记录。背景单类与 ECMP 的逐字节一致性另作路径回归；聚合出口包数不能替代逐 QP 证据。

每格 build 后、run 前启动 watcher，并确认首条 `resource-samples.jsonl` 已落盘。终态后确认 `resource-summary.json`，再 fetch 并验收；树 RSS≤32 GiB、可用内存≥32 GiB、空盘≥100 GiB、1 分钟负载≤20。启动前核对其他用户任务、未知 ns-3 进程、锁和系统健康。身份、流完成、路径、守恒或资源任一失败时暂停新格，保留原 ID。代码修正须用新 SHA 和新 ID 重验受影响格；控制器超时先按原 ID 防重恢复，不覆盖 raw。

全部小样通过后，另用 WS-26 独立 pilot seed 检验机制覆盖、双侧方向和安全调度量。pilot 结果仅用于候选选择及事前冻结，不计正式 24 seed 收益。

## 2026-10-08 预检结果

固定提交 `b6fc1a423774790f971ad86b64e1c1646d63c36b` 的 18 个新 ID 均为 `SUCCEEDED`，逐流身份和标签通过，输入 trace 与拓扑哈希匹配，资源收据均通过；联合验收器输出 `complete=true`、`verified=18`。全部资源样本的进程树 RSS 峰值为 4,562.31 MiB，低于 32 GiB 门槛。机器摘要和格级收据位于个人 fork 的 `results/ws26-classreserve3-preflight-b6fc1a423774790f.json` 与 `results/ws26-classreserve3-preflight-b6fc1a423774790f-receipts.jsonl`。

第 18 格的仿真 FCT 与第 1 格一致。原验收器错误地要求 8 条源 ToR 路径记录；源码只为进入多路径选路分支的 QP 记录所选上联。复核原始 trace、route 计数及 `RecordWs26V3Path` 后，诊断行数改为与 `background_new + moe_new` 一致，并逐标签核对包数总和。最终 raw 中 4 条记录覆盖 2 个背景 QP 和 2 个 MoE QP，包数分别为 16,778 和 18，`inconsistent=0`。修正后的联合验收通过，诊断开关没有改变 FCT 指纹。

此预检不证明机制收益。mixed8 的 PFC=1、IRN=1 格中 `with_background=0`、`with_same_destination=0`、`diverted=0`；有效信号是否覆盖独立需求，仍须由后续 pilot 判断。独立 pilot、正式矩阵和敏感性矩阵均未启动。
