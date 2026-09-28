# Handoff 20：WS-19 独立需求双侧探索小样

WS-19 已完成事前冻结的 48 格四臂配对小样，全部原始结果回传并通过逐格校验。**效果结论为 WS-20 gate no-go**：在 ToR 热点加 192 条背景流的三个独立需求 seed 中，联合臂的 MoE 八轮平均完成时间与背景 P99 均高于同输入 ECMP；预注册 30 项方向筛选有 19 项失败。主机热点的 MoE 改善和路径开关的上游触发是真实观察，但不足以满足双侧门槛。

## 1. 本对话目标

WS-19 任务 `01a0e6fe-4a68-70b2-bcbc-341bf5cfabff` 受协调任务 `01a0cfac-3176-7590-bf34-c0f176a45118` 分阶段委派：先以 Sol High 冻结独立需求、协议和源码，Luna High 监督轮 `01a0e70e-e6d6-78a3-9942-adf3ce1a8416` 完成诊断 pilot、远程矩阵及 raw 回传，再切回 Sol High 轮 `01a0e797-0354-7971-b04a-96358fa2f319` 分析、交接和推送。研究目标是同时检验发送准入与上游双候选路径对 MoE 轮次及长背景流的影响；WS-20 确认性矩阵不在本任务启动范围。

## 2. 已确认的项目事实

[事前协议 v1](../research/ws19-admission-pilot-prereg-v1.md) SHA-256 `ADE47B2C7C3F427A4756EB8E48634D329A7818280CA017BA8B28831057386DFC`；[顺序清单](../research/evidence/ws19-pilot-schedule-v1.json) SHA-256 `6DDA53C30EBAF7B5C537F50452E06376E938FE96DE33C3B4F8D57AEC769C7769`。仿真源码固定为 `b52e66f0fbf786fb57672b12a5633cf45b9311c1`，拓扑 SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。三个独立需求 seed `20261701–03`，每 seed 配对主机/ToR 热点、0/192 背景与 E/A/P/J 四臂，共 12 区组、48 格；共同 ns-3 seed=1。独立重复单位仅需求 seed `n=3`。WS-17 拓扑审计已证明跨 ToR 源侧有多上游路径，固定目的主机只有唯一最终出口。

## 3. 已完成工作

两格诊断关/开 pilot `20260928-160100-ws19-preflight-off`、`20260928-160500-ws19-preflight-on` 的 FCT SHA 同为 `964b7f757f93397d56f2ab1434aa4647dfc4b23d083ecd08ef6486fac7f0e18f`，三时刻 SHA 同为 `e12ab3388a27f2ccec9b85acf1d590680816e7b7d91a9e22b90e2a9e58e5fbab`；开启诊断覆盖 113 个背景目的端、192 条 QP，`unpaired=0`。随后按冻结 index 0–47 启动 48 格，前两格并发上限 2、其余最高 4；控制器终态 exit 0。[原始收据](../../results/ws19-pilot-receipts.jsonl) built/started/verified 各 48、无失败；`verify_ws19_cell.py` 从 raw 独立复核 48/48 通过，逐格 `SUCCEEDED`、固定输入/源码、全流完成与字节守恒、三时刻分解、路径计数、背景观测覆盖、PFC 空文件和资源阈值均通过。资源峰值 RSS 4540.848 MiB，最低可用内存 105.384 GiB、最低磁盘余量 5715.607 GiB。

新增可重算 [`analyze_ws19_pilot.py`](../../scripts/analyze_ws19_pilot.py)、[48 格机器摘要](../research/evidence/ws19-pilot-analysis.json)、[配对权衡图](../research/evidence/ws19-pilot-tradeoff.svg)与[自然语言报告](../research/ws19-admission-pilot-report.md)。分析 JSON SHA-256 `AF879AF52FD574A2752A9236783BB84CBB39C86B417BCAD586F909E4E8A74FDB`，图 SHA-256 `D7EDF2A4AE0CE4A95CE1BF1B91ACF9709FF763983FAE05E66A112216F9646745`；机器摘要还逐 ID 保存 trace/FCT/三时刻 raw SHA。脚本从原始三时刻、诊断及元数据重算 8 轮原值/均值/最大、合成批次、背景 FCT P50/P95/P99/最大、有效吞吐、最慢 QP、逐流配对差、等待/网络分量、上游与目的出口位置证据、四臂六种对比以及逐 seed 停止条件。WS-17 输入与 WS-19 顺序生成器重新 `--verify` 通过；诊断 pilot 校验重跑通过。

## 4. 已形成的设计决策

按 v1 原样执行双侧方向性筛，不因 48 格全完成或主机热点 MoE 改善而放宽 ToR/192 及背景门槛。ToR/192 联合−ECMP 的 MoE 轮均三 seed 为 `+4.344/+4.739/+4.219 µs`，背景 P99 为 `+197.345/+10.737/+38.601 µs`；主机/192 联合−ECMP 虽缩短 MoE `311–312 µs`，背景 P99 却增加 `52–673 µs`，联合−仅准入轮均也三 seed 均为正。ToR/0 联合−ECMP 同样三 seed 为正。全完成硬门槛过、研究方向筛失败，故 **WS-20 no-go**。这些条件是事前研究筛选，不代表可核验业务安全阈值；历史 WS-10/11/12 的 5% 门槛没有借用。

## 5. 当前状态

2026-09-28：WS-19 **COMPLETE FOR EXPLORATORY PAIRED PILOT; WS-20 GATE NO-GO**。分支 `experiment/ws19-admission-pilot`；原始运行属于固定仿真 SHA `b52e66f…`，随后分析与状态文档提交移动分支 HEAD，不可把文档提交当作仿真源码。全部 48 格 raw 在本地 `results/<实验 ID>/`，不提交大体量原始文件；个人 `origin` 推送与工作树终态以本轮最终 Git 核验为准。

## 6. 未解决问题

样本仅三个重抽需求和一个仿真随机 seed，热点与 0/192 档为人工极端布局，追加背景同时增加总字节；不支持显著性、精确置信区间或真实训练 job CCT 推断。源 ToR 路径替代选择确已触发，背景目的出口仍排队，且尾流身份迁移；WS13_HOP/CNP 是相关的背景 QP/主机聚合观测，物理 MMU 总占用、可靠逐 QP 重传/超时、真实 RNIC 速率和业务 SLO 尚缺。同输入 DRILL 等强对照、更多独立需求与拓扑尚未进行。WS-20 未运行。

## 7. 后续推荐动作

保持 WS-20 关闭。若继续该机制方向，先围绕 ToR 轮尾与背景最慢流反例提出具体修订和可证伪位置观测，再另立版本、SHA、实验 ID 和新的双侧小样契约；只有新小样通过，才讨论足量独立需求、同输入强对照及预注册确认性设计。论文可把这次写为按事前规则停止的探索性负结果，不把单边改善包装成联合收益。

## 8. 与其他工作流的关系

WS-17 提供独立需求和可控瓶颈边界；WS-18 的 40 流格仅验证三时刻/四臂工程正确性，不计入本次 `n=3`。WS-10/11/12 各自正式 no-go、WS-14 单输入停止、WS-15 门槛 no-go、WS-16 论文范围待导师确认均未重判。WS-21–24 仍按各自条件选择，WS-25 只收束实际执行的证据。

## 9. CONTEXT SNAPSHOT

WS-19 事前协议与 schedule SHA 如第 2 节；仿真源码 `b52e66f0fbf786fb57672b12a5633cf45b9311c1`。诊断开/关 pilot 非扰动，48/48 配对格 `SUCCEEDED` 并经 raw 全量核验；[run-map](../research/evidence/ws19-pilot-run-map-v1.json)可定位所有实验 ID。[报告](../research/ws19-admission-pilot-report.md)和[机器摘要](../research/evidence/ws19-pilot-analysis.json)给出 12 区组、三独立 seed 的双侧效果和位置限制。30 项方向筛失败 19 项；**WS-20 no-go、未运行**。无业务 SLO，旧结论不变；下一步只有新机制理由与新事前双侧契约可重开研究。
