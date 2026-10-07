# WS-26 ClassReserve v3 正确性预检

状态：原首格在固定提交 `d4fb60dec340e282bd1150c82b2dfb2db9b64851` 下完成仿真，但 `missing_destination=16796`，正确性验收失败。原 ID `20261008-030000-ws26-v3-pre-mixed8-p1i1` 及其原始结果保留；其余 17 个旧 ID 均未启动。源码已修正目的 ToR 映射初始化。本表为修正后的 18 个全新 ID，最终固定源码 SHA 在首次 build 前登记。日期：2026-10-08。本组只检查实现、旧模式回归与四种传输设置，不作为新候选的收益证据。旧 WS-25 seed 及本组小输入不进入 WS-26 正式样本。

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

tag0、旧五列和背景单类的候选格必须逐字节匹配本组同输入 ECMP FCT。五个原仓库模式的 PFC=0/IRN=1 mixed8 格须与已验收的旧同参数指纹一致。四种传输设置的候选 mixed8 格均须全流完成，报告 PFC、CNP、乱序、重传和超时的可观测计数；不存在的观测标明缺失。第 18 格开启只读诊断，逐 QP 核对源 ToR 所选端口、包数与路径稳定性，并与第 1 格的 FCT 指纹比对非扰动。背景单类与 ECMP 的逐字节一致性另作路径回归；聚合出口包数不能替代逐 QP 证据。

每格 build 后、run 前启动 watcher，并确认首条 `resource-samples.jsonl` 已落盘。终态后确认 `resource-summary.json`，再 fetch 并验收；树 RSS≤32 GiB、可用内存≥32 GiB、空盘≥100 GiB、1 分钟负载≤20。启动前核对其他用户任务、未知 ns-3 进程、锁和系统健康。身份、流完成、路径、守恒或资源任一失败时暂停新格，保留原 ID。代码修正须用新 SHA 和新 ID 重验受影响格；控制器超时先按原 ID 防重恢复，不覆盖 raw。

全部小样通过后，另用 WS-26 独立 pilot seed 检验机制覆盖、双侧方向和安全调度量。pilot 结果仅用于候选选择及事前冻结，不计正式 24 seed 收益。
