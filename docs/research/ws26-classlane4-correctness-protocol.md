# WS-26 ClassLane v4 正确性预检

状态：事前协议，尚未执行。日期：2026-10-08。新模式 `classlane4` 的实现与 [候选规格](ws26-classlane4-candidate-spec.md)须先提交为固定 SHA。本组只核对机制、旧模式回归与四种传输设置，不计算正式收益。

## 固定输入和实验 ID

全部格使用 OS1 拓扑 `topo_1280_400G_400G_OS1`，SHA-256 为 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。公共参数为 400 Gbps、9 MiB buffer、DCQCN、ns-3 seed 1、`simul_time=0.01` 和 `netload=10`。五份既有小 trace 的哈希沿用 [v3 正确性协议](ws26-classreserve3-correctness-protocol.md)。新增的 [同源同目的 ToR 四流 trace](../../config/ws26_classlane4_shared_tor4.txt) SHA-256 为 `513b85e3c2e2422df2bb8f3c9b3812408fd02f7ee4aaba2ee11fd6cfbf16db2a`，含两条背景和两条 MoE QP。其源主机同属 ToR 1280，目的主机同属 ToR 1281；[拓扑检查脚本](../../scripts/check_ws26_classlane4_topology.py)核对这一点。

下表预留 19 个独立 ID。唯一实验副对话启动前须逐个查询原 ID 是否存在；已存在者按原收据防重处理，不覆盖 raw。所有格采用同一固定 SHA、独立源码和结果目录。第 1 格经完整验收后才启动其余格。

| 顺序 | 新实验 ID | 模式 | trace | PFC/IRN | 诊断 |
| ---: | --- | --- | --- | --- | ---: |
| 1 | `20261008-223000-ws26-v4-pre-mixed8-p1i1` | classlane4 | mixed8 | 1/1 | 0 |
| 2 | `20261008-223001-ws26-v4-pre-background4-p1i1` | classlane4 | background4 | 1/1 | 0 |
| 3 | `20261008-223002-ws26-v4-pre-moe4-p1i1` | classlane4 | moe4 | 1/1 | 0 |
| 4 | `20261008-223003-ws26-v4-pre-unclassified8-p1i1` | classlane4 | unclassified8 | 1/1 | 0 |
| 5 | `20261008-223004-ws26-v4-pre-legacy5-p1i1` | classlane4 | legacy5 | 1/1 | 0 |
| 6 | `20261008-223005-ws26-v4-pre-unclassified8-ecmp-p1i1` | fecmp | unclassified8 | 1/1 | 0 |
| 7 | `20261008-223006-ws26-v4-pre-legacy5-ecmp-p1i1` | fecmp | legacy5 | 1/1 | 0 |
| 8 | `20261008-223007-ws26-v4-pre-mixed8-ecmp-p1i1` | fecmp | mixed8 | 1/1 | 0 |
| 9 | `20261008-223008-ws26-v4-pre-mixed8-p0i0` | classlane4 | mixed8 | 0/0 | 0 |
| 10 | `20261008-223009-ws26-v4-pre-mixed8-p0i1` | classlane4 | mixed8 | 0/1 | 0 |
| 11 | `20261008-223010-ws26-v4-pre-mixed8-p1i0` | classlane4 | mixed8 | 1/0 | 0 |
| 12 | `20261008-223011-ws26-v4-pre-fecmp-mixed8-p0i1` | fecmp | mixed8 | 0/1 | 0 |
| 13 | `20261008-223012-ws26-v4-pre-drill-mixed8-p0i1` | drill | mixed8 | 0/1 | 0 |
| 14 | `20261008-223013-ws26-v4-pre-conga-mixed8-p0i1` | conga | mixed8 | 0/1 | 0 |
| 15 | `20261008-223014-ws26-v4-pre-letflow-mixed8-p0i1` | letflow | mixed8 | 0/1 | 0 |
| 16 | `20261008-223015-ws26-v4-pre-conweave-mixed8-p0i1` | conweave | mixed8 | 0/1 | 0 |
| 17 | `20261008-223016-ws26-v4-pre-shared-tor4-p1i1` | classlane4 | shared_tor4 | 1/1 | 1 |
| 18 | `20261008-223017-ws26-v4-pre-mixed8-diag-p1i1` | classlane4 | mixed8 | 1/1 | 1 |
| 19 | `20261008-223018-ws26-v4-pre-shared-tor4-ecmp-p1i1` | fecmp | shared_tor4 | 1/1 | 0 |

## 逐格验收和停止线

每格先核对源码 SHA、完整输入哈希、模式、四项公共参数、传输参数和独立 ID，再核对逐流身份、标签、大小与完成数。`_out_fct.txt`、`_out_cnp.txt`、`_out_pfc.txt` 和 `_out_uplink.txt` 必须存在且可解析。任一输入流未完成时，该格无可比较性能值。

候选格须满足：每个标签的 `packets = qp_new + qp_reused`；`inconsistent=0`、`missing_destination=0`；队列 `enqueued = dequeued + queued_drop + current` 且违规计数为 0。mixed8 与 shared_tor4 应触发两类 QP 新建、缓存命中和真实改选；若改选数为 0，记录机制覆盖不足，不宣称完成效果筛选。单类格不得出现另一类候选计数。tag0 与旧五列格必须逐字节匹配本组同输入 ECMP 的 FCT；背景单类格允许因新规则改变路径和 FCT，不要求匹配 ECMP。

第 17 格的逐 QP 诊断须在源 ToR 1280、目的 ToR 1281 找到 4 条流。两类各 2 条；每条流的选定端口稳定，且背景端口与 MoE 端口集合不交叠。第 18 格的逐 QP 行数须等于两类 `qp_new` 之和，逐类包数须等于 `packets`；第 1 格与第 18 格的 FCT SHA-256 必须完全相同。旧五个基线的 PFC=0/IRN=1 mixed8 格按原 SHA、输入与参数核对后，与既有已验收指纹比较；该比较仅作代码回归，不将 WS-25 结果算作 WS-26 正式样本。

每格 build 后、run 前启动资源 watcher 并确认首条采样。终态后核对资源摘要，再 fetch 和验收。树 RSS≤32 GiB、可用内存≥32 GiB、空盘≥100 GiB、1 分钟负载≤20。启动前检查其他用户作业、未知 ns-3 进程、锁和系统健康。任一正确性或资源失败暂停新格，保留原 ID 和 raw。修复须使用新 SHA 与独立 ID 重验受影响格。

全部小样通过后，才按 [候选规格](ws26-classlane4-candidate-spec.md)进入全新独立需求 pilot。pilot 不进入 24 个正式 seed，也不能替代 576 格主矩阵或 576 格敏感性矩阵。
