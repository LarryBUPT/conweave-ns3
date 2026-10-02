# WS-25 D1：默认关闭观测的同输入指纹核验

状态：2026-10-03，四格仿真终态且 raw/资源验收通过，等待 Sol High 结果分析。D1 是正确性与非扰动诊断，不是新候选或正式效果样本。仿真源码固定为 `feature/ws25-first-paper@b13369d3f086189b693a1c8d875cfe7e3171181e`；相对 C3 只加默认关闭的 `WS25_DIAG` 观测、CLI/worker 参数通路，不调整选路、传输、输入或指标定义。D1 先核实观测开关的 FCT 指纹一致，再以新 raw 解释四 seed pilot 的线索。D1 结果不得进入最终验证池。

## 固定输入、臂和 ID

共同输入为 `config/ws25_seed20262501_b192.txt`，SHA-256 `9791006f71843ea74b044396f6ae112ea8340aa9781cf0d267876e0940b02f48`；拓扑 `topo_1280_400G_400G_OS1`，SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。所有格 400 Gbps、9 MiB、PFC=0、IRN=1、DCQCN、`RANDOM_SEED=1`、`--simul-time 0.01 --netload 10`，输入 16,384 条 8 KiB MoE 加 192 条 8 MiB 背景，总计 16,576 流、1,744,830,464 B。

| 模式 | 观测 | 实验 ID |
| --- | --- | --- |
| ClassReserve | 关 | `20261003-160000-ws25-d1-classreserve-off` |
| ClassReserve | 开 | `20261003-160001-ws25-d1-classreserve-on` |
| DRILL | 关 | `20261003-160002-ws25-d1-drill-off` |
| DRILL | 开 | `20261003-160003-ws25-d1-drill-on` |

每格使用固定 SHA 的独立 optimized 构建、源码和结果目录；开格前检查 ID 不存在。先串行跑 ClassReserve 开关，确认指纹和资源，再串行跑 DRILL 开关。开格时 `--ws25-diag 0/1` 显式记录在 metadata；其余参数必须逐字段相等。不得覆盖旧 C2/C3 的 raw。

## 观测语义与验收

观测开时，每个完成 QP 输出一行 `WS25_QP`：接收端高于当前期望序号的包数、带非零 IRN SACK 的反馈数、带 CNP 的反馈数、曾发过序号范围的重复发送包数、实际进入超时恢复的次数。这些是事件/包数，重复发送可能由丢包或乱序恢复引发，不单独等同于丢包次数。ClassReserve 额外输出 `WS25_CHOICE` 的两候选队列是否同时为空、两个候选总排队字节的累计值、背景队列分量非零次数；`WS13_HOP` 在 D1 中作为全部背景流的逐流逐跳出口排队观测，含入队时队列字节、等待纳秒和未配对数。原有 CNP/VOQ/flowlet、uplink、FCT 仍从 raw 独立读取。观测关时不得出现 `WS25_QP`/`WS25_CHOICE`。

每格须为 `SUCCEEDED`、16,576/16,576 完成，类别流数和字节守恒，metadata/trace/拓扑哈希及资源收据完整；ClassReserve 队列守恒仍为零违反。同一模式开/关的原始 FCT SHA-256 必须逐字节相同，配置除 `ws25_diag` 与独立输出路径/ID 外相同。若不一致，诊断本身不合格，保留原 ID 并定位，不用其解释机制。比较开关的运行时和树 RSS 以估算观测成本；单次 pilot 的耗时不当作性能效果。

## 资源与停止

远端预检：无未知作业或 ns-3、worker 无在途、1 分钟 load ≤20、可用内存 ≥32 GiB、可用盘 ≥100 GiB。D1 初始并发 cap=1；若日志/资源不稳，停止新格。单格编译 >30 分钟、仿真 >4 小时、树 RSS >32 GiB、单格新增磁盘 >10 GiB、资源门槛下降、哈希或完成率错误时停止启动新格，保留现场和 raw。远程仿真后台静默，约半小时汇总完成数、失败数和资源峰值；终态回传后逐 ID 分析。

本协议冻结后停在远程仿真模型边界：由主对话实际切至 GPT-6 Luna High 后自动运行，无需额外人工确认；终态回传再实际切回 GPT-6 Sol High 分析。D1 仅提供一次修订 v1 或登记 v2 的依据，不能替代单类/混合/回退、动态分支、0/64/128 约束、独立最终验证及成稿。

首次冻结的 `52d5d0be409a6a4601f782f97a40f3c3f5014ccc` 在 `20261003-150000-ws25-d1-classreserve-off` 编译失败，原因是 `Ws25DiagnosticEnabled` 定义位于报告函数之后却未前置声明。该 ID 为 `BUILD_FAILED`，无仿真 raw；metadata、构建日志和失败收据保存在 `results/20261003-150000-ws25-d1-classreserve-off/`。旧表其余三个 ID 未构建/未启动。修复提交仅加入前置声明，所有旧 ID 作废且不复用，新四格以本文件表格为准。

## 2026-10-03 D1 终态核验

固定源码 `b13369d3f086189b693a1c8d875cfe7e3171181e` 的四格均为 `SUCCEEDED`，逐格 16,576/16,576 完成，整批 `scripts/verify_ws25_d1.py` 返回 `verified=4`。ClassReserve 开/关 FCT SHA 均为 `367a14e9b5c98add96e5b111a50a2a8d2dc5224f8b02b28ca5692dcd47f780b4`；DRILL 开/关 FCT SHA 均为 `a156f9909339b95a28bdb3a8e2951f611e63a8d33fa96df7f02e4b01502d0d5e`。观测关闭时没有 `WS25_QP`、`WS25_CHOICE` 或 `WS13_HOP` 行；打开时各模式均输出 16,576 条唯一逐 QP 记录，背景逐跳记录及 ClassReserve 选路汇总也齐全。全部资源收据通过停止线，四格最大树 RSS `4544.5391 MiB`、最低可用内存 `118.5589 GiB`、最低空闲盘 `5534.9279 GiB`；终态远端无在途仿真。原始结果位于本地忽略目录 `results/<ID>/`，远端各 ID 对应 `/home/fnl/lzy/results/<ID>/`。机器逐格摘要在 `scripts/verify_ws25_d1.py` 的运行输出与上述目录；机制解释仍待 Sol High 分析，不把 D1 当作效果样本。

Sol High 分析见[诊断报告](ws25-d1-diagnostic-analysis.md)及[机器摘要](evidence/ws25-d1-diagnostic.json)。诊断显示 v1 的 MoE 逐包换路带来较多乱序反馈，背景流的乱序计数较低；报告建议使用 v1 唯一一次修正额度，改为有依据的 MoE flowlet 路径保持。D1 不作为正式效果证据。
