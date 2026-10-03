# WS-25 ClassReserve v1 修正版：11 格正确性分析

日期：2026-10-03。固定仿真源码 `c84108b24c94a5068861e5bb090c5aa387245ee1`。原始验收协议为[修正版预飞行](ws25-classreserve-v1-correction-protocol.md)，逐格执行收据位于个人 checkout 忽略目录 `results/ws25-v1fix-correctness-receipts.jsonl`。11 个 ID 最初均已远端 `SUCCEEDED`；b192 首次验收退出是 verifier 错写 trace SHA 的本地缺陷。修正常量后，单格与全矩阵 verifier 分别返回 1/1、11/11；没有重跑或覆盖任何仿真 raw。此结果只证明正确性、回退与资源契约，不是效果比较。

## 同输入 baseline 与候选回归

六臂使用同一 8-flow mixed trace（4 背景、4 MoE，SHA-256 `29ebe2dcf38c0e4d29326947c4bc4e111f6b56fe378c020c30ee788fbaa5effb`）、相同拓扑与 PFC=0/IRN=1/400 Gbps 条件。六格均完成 8/8，输入标签计数均为 4+4，raw 与配置收据齐全。

| ID 后缀 | 模式 | FCT SHA-256 | 本格 MoE / 背景 P99（µs） | 机制覆盖边界 |
| --- | --- | --- | ---: | --- |
| `180000-…-fecmp` | ECMP | `e3fa403b…249fdbc` | 0.788 / 170.033 | correctness trace |
| `180001-…-drill` | DRILL | `1d4b790e…f6fe15f` | 0.784 / 170.033 | correctness trace |
| `180002-…-conga` | CONGA | `e3fa403b…249fdbc` | 0.788 / 170.033 | flowlet timeout 0 |
| `180003-…-letflow` | LetFlow | `e3fa403b…249fdbc` | 0.788 / 170.033 | flowlet timeout 0 |
| `180004-…-conweave` | ConWeave | `e3fa403b…249fdbc` | 0.788 / 170.033 | reroute 0、VOQ flush 0 |
| `180005-…-classreserve` | ClassReserve | `e3fa403b…249fdbc` | 0.788 / 170.033 | 8/8 完成、类别队列守恒 |

这些亚微秒级 batch 与 4 条流的 P99 仅是极小 correctness trace 的解析输出；相同 FCT 指纹不代表真实负载性能相同。CONGA、LetFlow 的 flowlet 重选，以及 ConWeave reroute/VOQ 路径均未在该 trace 触发。模式入口和回归可运行已验证，动态分支仍需专门的正确性覆盖才能支撑相应机制主张。

## ClassReserve 类别、缓存与队列不变量

| ID 后缀 | 输入类别 / 完成数 | 路由及回退计数 | 队列检查 |
| --- | --- | --- | --- |
| `180005-…-classreserve` | 背景 4/4、MoE 4/4 | MoE 新缓存/复用 8/64；双候选 2、改选 0。背景新缓存/复用 12/100,656，避队列 0；回退 0 | 入队=出队 111,608,752 B；drop=0，current=0，`queue_violations=0` |
| `180010-…-background` | 背景 4/4 | 背景新缓存/复用 12/100,656；MoE 包 0、回退 0 | 入队=出队 111,535,440 B；drop=0，current=0，`queue_violations=0` |
| `180011-…-moe` | MoE 4/4 | MoE 新缓存/复用 8/64；双候选 2、改选 0；背景包 0、回退 0 | 入队=出队 73,312 B；drop=0，current=0，`queue_violations=0` |
| `180012-…-unclassified` | tag0 共 8/8 | ECMP fallback 100,740 packet decisions | 入队=出队 111,608,752 B；drop=0，current=0，`queue_violations=0` |
| `180013-…-legacy5` | 无 tag 五列格式共 8/8 | ECMP fallback 100,740 packet decisions | 入队=出队 111,608,752 B；drop=0，current=0，`queue_violations=0` |
| `180014-…-b192` | 背景 192/192、MoE 16,384/16,384 | MoE 新缓存/复用 74,772/598,176；双候选 25,598、改选 9,551。背景新缓存/复用 884/7,414,992，避队列 41；回退 0 | 入队=出队 8,901,654,688 B；drop=0，current=0，`queue_violations=0` |

Fallback 数是包级路由决策计数，不是流数；缓存创建数按交换机—流计数，不能与全局 flow count 混为一谈。队列收据记录模拟器类别队列的跨队列累计值，不能解释为端到端 offered bytes 或 MMU 物理 buffer 占用。PFC=0 时所有 PFC raw 为空符合配置预期。b192 FCT 的逐类完成率为 100%，MoE synthetic batch 16.286 µs、背景 P99 2083.638 µs；这些仍来自一条已看过的 seed01 correctness trace。

## 同一 seed 上的单次修正诊断

旧 v1 校准 ID `20261002-224005-ws25-v2-cal01-classreserve` 与修正版 b192 correctness ID 使用完全相同的 seed01 trace SHA `9791006f…b02f48` 和拓扑/传输条件，但源码版本不同（旧 `bb103092…`，新 `c84108b…`）。从两份 FCT/CNP raw 描述性重算：

| 版本 | MoE batch µs | 背景 P99 µs | CNP ECN 分量 | CNP OoO 分量 | CNP 总计 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 修正前 v1 | 19.442 | 2118.305 | 3,141 | 12,809 | 15,897 |
| 修正版 | 16.286 | 2083.638 | 2,790 | 0 | 2,790 |

这个同 seed 变化与“MoE flow 固定复用路径后，路径跳变及 OoO CNP 减少”的预期一致，足以支持继续做独立校准；它不是预注册的效应试验、不是独立样本，也不能据此声称性能提升或乱序已在所有 seed 消失。正式校准必须换用未看过的需求 seed，并让六臂在每个 seed 上配对。

CNP ECN 与 OoO 标记可能在同一反馈消息中重叠，因此两列不能相加来重建总 CNP；表中 total 直接从 raw 总计字段计算。

## 资源与验收修复

11 格最大树 RSS 为 `4562.13 MiB`，最低可用内存 `114.098 GiB`、最低空闲盘 `5527.07 GiB`；终态远端 `audit(reject_active=True)` 通过。验收器原本把 b192 trace SHA 误写为 `979100…be647f`，正确值为 `979100…b02f48`；与协议和 trace snapshot 一致的常量已修复在 `scripts/verify_ws25_v1fix_correctness.py`。因此 controller 在最后一格停止扩批是正确的 fail-closed 行为；修复后只重读原实验 ID。

## 下一独立校准门槛

因 v1 修正参考了已查看的 seed01–04 结果，修正版校准改用新需求 seed `20262505–20262508`；最终保留池 `20262521–20262544` 继续封存。四个新 seed 均由 `scripts/make_ws25_demand.py` 同规则生成 0/64/128/192 档，哈希、流数与 tag 分布见[输入 manifest](evidence/ws25-v1fix-calibration-inputs.json)。第一阶段只运行 192 主档：六模式 × 四独立 seed = 24 个主格，同 seed 配对；另加每 seed 一格 ClassReserve `WS25_DIAG=1` 的四格观测控制。所有 28 格固定修正版源码 SHA `c84108b…`、相同拓扑和 PFC=0/IRN=1 条件，cap=2，运行顺序按固定随机化表分 seed block。诊断控制只作机制解释，必须逐 seed 与同输入 diag-off ClassReserve 的 FCT SHA 完全一致，才报告诊断不扰动；两者不作为两个独立样本。

接受条件是 metadata/SHA/config/input 均相符、每格 16,576/16,576 完成、标签为 192/16,384、raw 收据完整、候选队列 `queue_violations=0` 且队列字节守恒、资源低于冻结停止线。双侧差值只作四需求 seed 的校准描述，不按该小样作显著性或正式 go/no-go；数值门槛、最终样本量与正式 ID 留到校准数据分析后冻结。运行器与计划为 `scripts/run_ws25_v1fix_calibration.py`，远程开格须等主对话实际切到 Luna High。
