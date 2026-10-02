# WS-23/24 最终验证清单

更新：2026-10-02。本文件汇总两个独立实验分支的最终验收。2026-09-30 的 build/单测与静态审计阶段曾被提前视为任务闭环；该阶段性判断已被后续端到端和完整矩阵数据取代，详见 [Handoff 55](../handoffs/2026-10-02-55-ws23-ws24-final-integration.md)。

## WS-23：传输恢复与隔离探索

来源任务 `01a0f15f-58c7-7532-84bd-9acaaaa14525`，分支 `feature/ws23-validation-execution@e3919171e5d00711f13c9f5465209accac201766`。原始数据在该 checkout 的 `results/<实验ID>/` 与远端对应 ID 下；逐格 ID、源码 SHA 和判据以该分支[结果报告](https://github.com/LarryBUPT/conweave-ns3/blob/e3919171e5d00711f13c9f5465209accac201766/docs/research/ws23-isolation-matrix-r3-report.md)、[完整执行清单](https://github.com/LarryBUPT/conweave-ns3/blob/e3919171e5d00711f13c9f5465209accac201766/docs/project-state/WS23_WS24_VALIDATION_PLAN.md)为准。

- [x] 旧 16×1 MiB 丢包压力反例、无损 pause/resume 与动态延期 control/probe 均有端到端正确性 raw；失败尝试保留，新 SHA/ID 重验，最终 16/16 及字节/序号守恒通过。
- [x] 跨类共出口干扰及观测不扰动前提以独立格验证；正式比较前冻结相同输入、拓扑、算法臂、资源和停止条件。
- [x] 固定矩阵 SHA `3db2685a3540895bf49e25302bd00465bc0921e2` 的 18/18 有效格、流级 FCT 与资源收据已从 raw 重算。集成阶段再次运行 `verify_ws23_isolation_pilot.py --revision 3` 返回 18 格及 `exploratory_positive=false`。
- [x] 事前正向条件未通过：seed 2301/2302 的类别项没有改变选路；2303 的背景改善伴随最慢竞争流受损。结论为**隔离效果 NO-GO**，限于小拓扑、三组同家族合成需求；不宣称生产隔离收益或统计确认。

**状态：COMPLETE FOR PRESET NS-3 SYNTHETIC CORRECTNESS AND ISOLATION EXPLORATION; EFFICACY NO-GO。**

## WS-24：多 NIC、multi-rail 与放置

来源任务 `01a0f1da-f1e2-7870-9361-24b4d626fd76`，分支 `feature/ws24-multinic-validation@11a40fd5f9ba5c2811ecc8172f7d30dddda223ba`。用户明确限定仅 ns-3 合成模拟；无真实主机/NIC/job 数据的验收要求。逐格协议、ID、SHA、raw 与限制以该分支[结果报告](https://github.com/LarryBUPT/conweave-ns3/blob/11a40fd5f9ba5c2811ecc8172f7d30dddda223ba/docs/research/ws24-independent-synthetic-effects-report.md)和[机器摘要](https://github.com/LarryBUPT/conweave-ns3/blob/11a40fd5f9ba5c2811ecc8172f7d30dddda223ba/docs/research/evidence/ws24-independent-synthetic-effects-summary.json)为准。

- [x] 合成 host/NIC/rail/job/rank 身份模型、最小正例与跨 rail 拒错、旧五/六列四 baseline 回归、320-host 目标拓扑及 CNP 动态正确性完成；原 A/B/C/D 14 格全数回传验收，同 SHA point-to-point 单测 5 PASS。
- [x] 原单 seed 四臂只作正确性与描述性 pilot，不并入独立 job 效果检验。首版 `j01-fs` 虽有 30/30 正确性 raw，却缺资源收据，保留并排除；修复 ID `j01-fs-r2` 通过。
- [x] 正式源码 SHA `3b992eed218f65b4f8026eddb5170a7694e17b10`、manifest SHA-256 `e2d19ce3d7424f556bebcd74f011310538cf89c55bc2937c985e922af2b1c536`。12 个独立生成 key × 四臂 48/48 格从 raw 验收：每格 30/30，合计 1,440 格内流记录；1,056 个远端/本地文件 SHA-256 相同，资源收据有效。
- [x] 集成阶段再次运行 `verify_ws24_independent_matrix.verify_matrix`，48 格/12 job 的结果与保存的机器摘要完全相同。12/12 job 的主效应为负，中位配对差 −19.667%，精确双侧符号检验 `p=0.00048828125`；`j02` 极端、`j11` 微小、`j09` 放置差异均保留。结果只针对固定合成需求生成机制、拓扑和 ns-3 seed，不能推断真实网卡或生产作业收益。

**状态：COMPLETE FOR PRESET NS-3 SYNTHETIC MULTI-RAIL × PLACEMENT VALIDATION。**

## 项目边界

WS-23 的隔离探索 NO-GO 与 WS-24 的合成多 rail 统计结果都不能直接充当开题报告所需的两项包流混合新机制论文正向结论。WS-10/11/12 历史双侧 NO-GO 维持。下一阶段以开题报告的包流混合问题为背景、WS-11/12 既有流量分布与档位为主，仅远程 ns-3；用户允许同分布新独立 seed，不新增流量类型或档位。两课题主要关注负载均衡，乱序代价为次，暂拟类别感知选路与有成本、有时效的下游状态反馈选路。下一版机制最多三个候选版本且每版至多一次诊断修正，均失败即停并如实复盘。双侧效果门槛仍按 Grill-me 问答确认；未确认前不启动新研究矩阵。
