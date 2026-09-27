# Handoff 13：WS-12 全量 MoE 加背景多逐包策略对照

日期：2026-09-27（中国时间）。来源：[WS-12 多逐包策略对照与双侧证据整合](codex://threads/01a0def1-82cd-7941-89a2-759e0072d8ef)，任务 ID `01a0def1-82cd-7941-89a2-759e0072d8ef`；120 个正式实验 ID 与逐格证据见[机器摘要](../research/ws12-packet-strategies-formal-summary.json)，以原始结果而非对话为准。

## 1. 本对话目标

沿用 WS-11 的 16,384 条固定 MoE 流加 0/64/128/192 条逐档追加背景流，完成全流 ECMP、既有逐包哈希、逐包 RR、随机、自适应和 DRILL 的前瞻性同输入对照；背景流保持逐流 ECMP。用户要求后台静默、每半小时低频检查，不逐格报告。

## 2. 已确认的项目事实

个人 fork 分支为 `feature/ws12-packet-strategies`，正式仿真源码统一为 `adae7956e3fc874d9237e62a6ea8e32b26d5def1`。六模式共用拓扑、trace、seed=1、DCQCN/PFC=0/IRN=1 与 400G/9 MiB 契约；四个新增模式只对 tag=2 MoE 数据逐包选路，tag=1 背景与控制包仍按流 ECMP。五组为原始输入与四组确定性行顺序置换，不是五个独立需求样本。旧 `fecmp/dualtrack` 的 40 格原始 FCT SHA 与 WS-11 对应格 40/40 相同。两份参考仓库只读。

## 3. 已完成工作

- 用户决定保持固定全量 MoE 加逐档追加背景的输入模式；助手在策略代码前提交[预注册](../research/ws12-packet-strategies-prereg-v1.md)，实现四个新模式，并完成[小样、旧模式回归与六格资源 pilot](../research/ws12-implementation-and-pilot.md)。
- 120/120 个唯一正式实验 ID 均完成，两类输入逐格 100% 完成，PFC 原始事件文件均空，源码、输入、拓扑、seed、原始指标与资源收据经[独立脚本](../../scripts/verify_ws12_formal.py)核验。逐格原始目录为个人 fork 的忽略目录 `results/<实验ID>/` 和远端 `/home/fnl/lzy/results/<实验ID>/`；报告和索引见[正式报告](../research/ws12-packet-strategies-formal-report.md)与[机器摘要](../research/ws12-packet-strategies-formal-summary.json)。
- 主 192 档相对既有哈希的 MoE 合成批次中位缩短：RR 16.116%、随机 18.406%、自适应 21.056%、DRILL 22.549%；不慢于哈希分别为 4/5、5/5、5/5、5/5。但 15 个有背景格的背景 P99 安全通过数分别仅 14、14、13、14，四者预注册双侧判据均 **no-go**。原始 192 档 RR/随机/自适应分别越线 +6.294%/+8.459%/+8.964%；DRILL 在顺序组 20261103 的 128 档越线约 +8.46%。
- 峰值采样负载 18.41、单格进程树 RSS 4540.68 MiB、最低可用内存 85.89 GiB；18 与 19 CPU 令牌的 12 格墙钟均约 18.2 分钟，按预注册退回 18，未试 20。一次采样器启动确认失败留下 74 条 `stopped` 控制收据；对应格尚为 `BUILT`，幂等重试后按原 ID 恢复，没有覆盖原始结果或正式仿真失败。

## 4. 已形成的设计决策

**决定：四个新增策略均按本场景复合判据判为 no-go。**预注册要求主档 MoE 改善与所有有背景格 P99 ≤5% 同时成立，不能只挑主档 MoE 速度或事后剔除越线格。保留全流 ECMP 和既有哈希为共同/强对照，保留每个策略的有利与不利数据。19 令牌无吞吐提升时回到 18；控制收据不当作正式结果或新实验格。

## 5. 当前状态

WS-12 多逐包策略正式对照在预注册矩阵、正确性、资源和双侧判据范围内完成；四个新增策略均 no-go。[WS-10/11/12 解释性证据提纲](../research/ws12-ws10-ws11-negative-evidence.md)已并列收录三场输入契约、主结果、边界与不可观测项，WS-12 解释性收尾亦完成。正式仿真 SHA 不随本次报告、Handoff 或状态提交改变。最近一次独立运行 `python scripts/verify_ws12_formal.py` 返回码 0，输出 `complete=true`、`formal_cell_count=120`、`legacy_fct_hash_matches=40`，四策略 `two_sided_acceptable=false`。远端最后检查无在途仿真；执行新的远端操作前须重新核实。

## 6. 未解决问题

五组只检验同一流记录的顺序敏感性，不能推断独立需求总体；新增背景同时增加总提供字节，不能称纯比例效应。物理 MMU 队列、可靠独立 NACK/超时计数不可得，不能记为零。热点与背景长尾的因果机制尚需独立可观测性设计；本轮不证明 GuardHash/HarmGate 的收益，也不代表硬件或线上部署。

## 7. 后续推荐动作

已把 WS-12 双侧负结果与 WS-10 固定总字节、WS-11 全量追加背景的各自 no-go 并列纳入[论文证据提纲](../research/ws12-ws10-ws11-negative-evidence.md)，保留各自预注册、输入契约和原始 ID。下一步是确定论文论点或另立机制收益问题；后者须先冻结新的场景、独立需求重复与双侧安全门槛，再做等信息强对照。当前无待补正式格或需要继续运行的仿真。

## 8. 与其他工作流的关系

WS-06 输入 tag、WS-07 `dualtrack`、WS-08 共同 IRN、WS-11 全量 trace 与顺序组是本轮底座。WS-12 没有改写 WS-10/11 的门槛或结果；WS-09 GuardHash/HarmGate 仍只有工程原型证据。参考仓库中的 probe 和独有接收重排没有移植，不能称完整参考算法复现。

## 9. CONTEXT SNAPSHOT

`feature/ws12-packet-strategies` 的正式仿真固定 `adae7956e3fc874d9237e62a6ea8e32b26d5def1`；16,384 条 MoE 加 0/64/128/192 条追加背景，5 顺序组 × 4 档 × 6 模式，共 120/120 格核验完成、两类流 100% 完成、PFC 文件均空、旧两模式 40/40 FCT 哈希与 WS-11 相同。RR/随机/自适应/DRILL 的主 192 档 MoE 批次相对哈希中位缩短 16.116%/18.406%/21.056%/22.549%，但各有背景 P99 >5% 越线，四者复合 no-go。正式报告、逐格哈希/指标和核验脚本分别见[报告](../research/ws12-packet-strategies-formal-report.md)、[摘要](../research/ws12-packet-strategies-formal-summary.json)、[脚本](../../scripts/verify_ws12_formal.py)。无剩余正式格；WS-10/11 no-go 和机制效果门槛维持原状。

## 集成交接核验（2026-09-27）

集成任务再次运行 `python scripts/verify_ws12_formal.py`，返回码 0；从 120 个正式实验 ID 的原始数据与资源收据重算 `complete=true`、旧两模式 FCT 哈希 `40/40` 匹配，RR/随机/自适应/DRILL 均 `two_sided_acceptable=false`。集成前本地、`origin` 和 GitHub 的 `feature/ws12-packet-strategies` 均为 `2c1fea5eeb4a20c404b9b6d949b1e7d7169e03c1`，工作树干净。WS-12 的预注册对照、解释性证据提纲和本任务问答已收口；正式仿真源码 SHA 仍为 `adae7956e3fc874d9237e62a6ea8e32b26d5def1`。可以归档；未解决的背景尾部因果解释与独立需求重复列为 WS-13 及以后新任务，不回填 WS-12 判据。
