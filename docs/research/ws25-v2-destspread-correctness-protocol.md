# WS-25 DestSpread Hybrid v2 正确性预检

状态：2026-10-06，首格远程 build/run 前冻结。此预检只判断新模式的实现与旧模式回归，不作性能推断。v1 正式 576 格及其 NO-GO 不重判。

## 固定身份

- 仿真源码：个人 fork `feature/ws25-first-paper@87bb136ba85126c8c6c883814c7fa10cdcd74fda`。新模式 `destspread` 为 `LB_MODE 22`。此 SHA 的新模式尚未经过远端编译。
- 拓扑 `topo_1280_400G_400G_OS1` SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`；400 Gbps、9 MiB buffer、DCQCN、PFC=0、IRN=1、ns-3 seed=1、`simul_time=0.01`、`netload=10`。
- 已揭盲的旧正确性小输入仅用于机制预检，不作为 v2 独立筛选或收益证据。五个 trace 的 SHA-256：`ws25_v1fix_mixed8.txt` 为 `29ebe2dcf38c0e4d29326947c4bc4e111f6b56fe378c020c30ee788fbaa5effb`，`ws25_v1fix_background4.txt` 为 `e1259a4dbb17fe70e15a72881cbc3faaeac637123ba18ac29596b4f4f2743015`，`ws25_v1fix_moe4.txt` 为 `8acfe14d19d7ef7822bfd9a78334b830ce581456003e132d6557a44d1e41ea60`，`ws25_v1fix_unclassified8.txt` 为 `73704cadbdb95708c5ba26126af43b2758af688e332a80fdad46e7bc42c66dd3`，`ws25_v1fix_legacy5.txt` 为 `cc80f3a1eb23dcf936a8b371bf5b63763acac283923361efe9bcd3ebb1ae6c94`。

## 冻结新 ID 与顺序

| 顺序 | ID | 模式 | trace |
| ---: | --- | --- | --- |
| 1 | `20261006-070000-ws25-v2-pre-mixed8` | destspread | mixed8 |
| 2 | `20261006-070001-ws25-v2-pre-background4` | destspread | background4 |
| 3 | `20261006-070002-ws25-v2-pre-moe4` | destspread | moe4 |
| 4 | `20261006-070003-ws25-v2-pre-unclassified8` | destspread | unclassified8 |
| 5 | `20261006-070004-ws25-v2-pre-legacy5` | destspread | legacy5 |
| 6–10 | `20261006-070005-ws25-v2-pre-{fecmp,drill,conga,letflow,conweave}` | 对应旧模式 | mixed8 |
| 11 | `20261006-070010-ws25-v2-pre-unclassified-ecmp` | fecmp | unclassified8 |
| 12 | `20261006-070011-ws25-v2-pre-legacy-ecmp` | fecmp | legacy5 |

每个 ID 单独源码、metadata、raw 和资源收据；顺序 1 的 build/run/验收通过后才扩展。任何旧 ID 或 v1 正式 raw 均不得覆盖。

## 验收

1. 每格的源码、trace、拓扑、参数和 ID 匹配；输入流全部完成，FCT 与输入身份/字节匹配，没有重复或未见流。
2. `destspread` 的类别队列入队=出队+丢弃+终态在队，违规为零；mixed8 中背景新建/复用和 MoE 逐包选择均非零，单类格仅有对应类别。空队列平局及源 ToR 端口分布记录为机制证据，未触发时不得臆称覆盖。
3. tag0 和五列旧输入回退到 ECMP，需比较相同输入 ECMP 的完整 FCT 指纹；旧五模式 mixed8 全部完成并复核身份与字节，不能只看模式号。
4. 对 mixed8 开诊断的同输入新 ID 在后续另冻，用逐 QP 乱序、NACK、重复发送、超时及 FCT 指纹检查非扰动；任何缺失观测保留为缺口，不填零。

## 运行安全

首格 cap=1；每次启动前确认无其他用户作业、未知 ns-3 或 worker，锁可用，1 分钟 load≤20、每 worker 预留 5 GiB 后 MemAvailable≥32 GiB、空盘≥100 GiB、树 RSS≤32 GiB。资源 watcher 先于仿真启动并留下逐格收据。编译/仿真或 SSH 观察失败时先核原 ID、metadata、PID 和 raw，不因超时重启。任一身份、完成率、守恒或资源检查失败，停止扩格，保留原 ID；代码修正必须用新 SHA 和新 ID。全部正确性通过后另用从未参与 v1 的需求 seed 做独立筛选与资源 pilot，正式门槛和计划在最终 seed 揭盲前另冻。
