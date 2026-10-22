# WS-29 剩余 24 格工程执行入口

2026 年 10 月 22 日。本节点完成本地准备，等待主对话审查和远端 GO。三格回归已经通过原始数据验收；剩余 24 格尚未运行，独立效果 pilot 继续关闭。

## 固定材料与前置证据

仿真源码固定为 `3e68b3604e93cf34a4d938ebb48f1b1e0cfc988f`。采用原 [27 格计划](evidence/ws29-engineering-plan-observation-v2.json)，SHA-256 为 `5db623e7b38109a43ef0c37e0203e29713c896fe61e4d44581fd9512b551e8fd`。输入、ID、故障和验收阈值保持计划原值。新入口仅调整执行顺序，将主档成本格移至最后。

三格前置 ID 共用 `20261022-180000-ws29-obs2-` 前缀，后缀分别为 `legacy-v2-hb200`、`mixed8-c0` 和 `main-c0`。三格 FCT 均与固定旧参考逐字节一致。main-c0 完成 16,576 条流、1,744,830,464 B；完整收据位于 `results/ws29-regression-control/main-c0.verified.json`。这些数据支持固定输入下的兼容性，不代表反馈效果。

mixed8 首次 collect 因解析器将表头当作数据而停止。修复提交为 `e1bd96467018e0e75cbe142a954b3d9fccc29c1b`。原仿真未重跑，原始数据经完整复核后通过。STOP 原文保存在 `results/ws29-regression-control/STOP.history/STOP-20261022-parser-recovery.json`，SHA-256 为 `a99ae08bf5cff016c732e6032b66cf16063bf24d576e2f7b2f804704bbfb2a71`。同目录的恢复审计记录说明授权、原文、哈希和复核收据。

## 阶段和顺序

| 阶段 | 数量 | 顺序 | 验收重点 |
| --- | ---: | --- | --- |
| 正常联合控制 | 1 | `k4-c1-normal` | 实际 STATE、HELLO、ACK 及逐链路字节守恒 |
| 协议正确性 | 11 | `protocol-1` 至 `protocol-11` | 单次丢失、异常 ACK、会话重启和序号边界 |
| 物理链路 | 6 | `link-20-c0`、`link-23-c0`、`link-20-c1`、`link-23-c1`、`link-20-c2`、`link-23-c2` | 两端 down/up、全流完成、队列释放与恢复 |
| 合成状态机 | 3 | `synthetic-15`、`synthetic-16`、`synthetic-17` | 新鲜可区分、过期和无样本状态的采用或退回 |
| 主档联合成本 | 3 | `main-c1`、`main-c2`、`main-c3` | 同输入完成、控制分账和真实采用机会 |

入口为 [run_ws29_engineering.py](../../scripts/run_ws29_engineering.py)。每次只处理显式指定的一格。所有前置格必须存在正式验收收据，并重新通过 raw 核验，才允许操作下一格；上一阶段全部通过后才能进入下一阶段。阶段收据也保存在 `results/ws29-regression-control/`。

本地 [命令清单](evidence/ws29-engineering-entry.json)列出各格完整计划字段、构建参数、仿真参数和 collect 命令。生成清单只读本地固定计划、旧参考和 Git blob，不使用 SSH：

```powershell
python scripts/run_ws29_engineering.py prepare
```

主对话审查并实际确认监督模型后，再按以下方式逐格执行。示例为第一格；后续标签按上表替换。

```powershell
python scripts/run_ws29_engineering.py build --label k4-c1-normal
python scripts/run_ws29_engineering.py start --label k4-c1-normal
python scripts/run_ws29_engineering.py collect --label k4-c1-normal
```

仿真运行中 collect 只返回 RUNNING。正常后台约半小时监督一次，终态后回传原始数据并验收。每格都从固定 SHA 新建未修补源码副本，使用 optimized、`-j2` 和并发 1；不复用兼容测试二进制。预检继续核对其他用户作业、活动仿真和元数据、互斥锁、ID 空闲性、资源、HEAD、tracked diff 及原始 core 文件哈希。

## 验收、分账和停止

入口复用三格 runner 的执行函数、参数链、预检和失败日志。逐格核验仍使用完整 `verify_ws29_engineering.verify`，随后检查构建资源、既定事件上限和计划中的合成事件数。失败保留原 ID 与日志，写入全局 `STOP.json`，阻止后续动作和自动重试。已有 STOP 原文不会被新异常覆盖。恢复须保留审计链并由主对话决定。

资源门槛为进程树 RSS 不超过 32,768 MiB、可用内存至少 32 GiB、空闲磁盘至少 100 GiB、1 分钟负载不超过 20。单份文本日志不超过 50 MiB；WS-29 和 HB 事件分别不超过 500,000 条和 20,000 条，overflow 必须为 0。构建与仿真分别保留全部采样和终态摘要。

每格另存 observation 收据，分列 recorded decisions、two_fresh、比例、would_change、adopted_changed 和退回原因。主档自然需求、正常小拓扑、协议或物理故障、合成注入使用不同 scope，不合并为采用机会。STATE、HELLO 和 ACK 按类型、链路与事件分别计包和字节；入队与出队是两套账本，不能相加当作实际流量。应用输入字节与实际发送 payload 另列，保留分母含义。

自然主档的 two_fresh 或 adopted_changed 可以为 0。该结果须原样报告并继续审查机制机会；A06 保持 OPEN。合成格成功只支持状态机正确性，不能关闭 A06，也不能替代自然需求收益。工程格全通过后，由主对话分析 C1−C0、C2−C0 和 C2−C1 的对应含义，再决定后续门槛；本入口不开放效果 pilot。

本地共 35 项 WS-29 Python 测试通过，其中 11 项覆盖新入口。测试把全部 24 格参数送过控制器和 worker 解析器，检查阶段顺序、坏 raw 阻断、终态失败回传、运行中不推进、既有 STOP 保留、自然零机会和合成计数分离。prepare 测试禁止远端配置及命令调用。三格前置 raw 又经完整只读核验。此处没有启动新的构建、仿真或 C++ 测试。

## 三格回归节点的候选文献复核

本节点从候选 [README](../../../../参考文献/候选/README.md)和 [reading-log](../../../../参考文献/候选/reading-log.md)进入 SGLB、CONGA 的技术分析与核验记录。此前本地 REPS 复核收据保留在 `results/ws29-regression-control/three-regression-reference-review.json`，本节补充与 WS-29 设计直接相关的两篇。

SGLB 固定 SIGCOMM 2025 正文及明确标注的未评审附录，PDF SHA-256 为 `1bceebbc0a40040646ca6cd3cb81dc258d80ef621c532c62016b156def7ebd6c`。具体借鉴为拥塞状态与存活分账、down 优先、恢复确认和版本身份。适用条件是保留真实消息、会话和物理事件的独立证据。SGLB 依赖 GLB ASIC、EDK 和 BGP/SyncMesh；本项目使用 ns-3 的 CE 比例及 HELLO/ACK。三格回归不能验证其硬件时效或训练收益。[技术分析](../../../../参考文献/候选/papers/sglb-2025/analysis-technical.md)与[核验记录](../../../../参考文献/候选/papers/sglb-2025/verification.md)保留来源及附录边界。

CONGA 固定 SIGCOMM 2014 的 12 页会议版，PDF SHA-256 为 `cde4d45c8864484cd11e8fef6ae88a7c8ce12f8305eeb323ae01c9b56652072d`。具体借鉴为“目的叶 × 首跳候选”的身份索引，以及局部与远端状态分别记录。适用条件是候选对应关系、反馈窗口和更新来源可核对。CONGA 使用 DRE、路径最大拥塞等级和 flowlet；WS-29 使用全路径 CE 比例，并在 QP 内固定出口。旧 FCT 指纹一致只能验证这三份输入的兼容性，不能证明 CONGA 等价或反馈有效。[技术分析](../../../../参考文献/候选/papers/conga-2014/analysis-technical.md)与[核验记录](../../../../参考文献/候选/papers/conga-2014/verification.md)明确其 TCP 和硬件范围。

本次复核不修改已验收仿真代码、需求、评分或门槛。文档已对照阮一峰[中文技术文档写作规范](https://github.com/ruanyf/document-style-guide)的 README 和六章原文检查层级、空格、段落、数字及标点。
