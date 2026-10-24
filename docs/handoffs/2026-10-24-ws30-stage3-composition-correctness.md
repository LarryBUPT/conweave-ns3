# WS-30 阶段 3 组成夹具技术验收交接

日期：2026 年 10 月 24 日。源聊天：`01a16b16-9f14-74a0-9a4a-cc6eb7f28295`，标题为“WS-30｜ClassReserve 实验补正与证据分析”。工作区为 `workspace/ws30-attribution-audit`，分支为 `research/ws30-attribution-audit`。状态：组成夹具技术验收完成；WS-30 仍为 ACTIVE。

## 1. 本对话目标

完成 WS-30 阶段 3 的相同总队列、不同背景组成夹具及关闭夹具历史回归。该节点只验证夹具和选路逻辑，不估计算法性能收益。阶段 3 后续任务仍包括资源 pilot、正式矩阵和双侧分析。

## 2. 已确认的项目事实

- 固定仿真源码 SHA：`2d7e31a9f6ae24f1514d02cbf341d27e6ec0717f`。
- 12 个组成格覆盖两种初始背景组成、无／有后续背景到达及 E、Q16、C16 三臂；另有 2 个 observer 关闭的历史回归格。14 个 ID 均为 `SUCCEEDED`。
- 所有组成格在探针决策时两候选出口各有 65,536 B 总队列。背景占用交换为 65,536 B/0 B 与 0 B/65,536 B。探针 QP FCT 均为 25,665 ns。
- 固定场景中，E 选择出口 3；Q16 平局时选择出口 2；C16 随背景组成交换而在出口 2、3 间切换。
- 14 格均无丢包、准入丢弃、队列拒绝、守恒违例、超时、重传或接收序号缺口。全部输入 QP 完成，终态队列排空。
- 关闭夹具 E/C16 的 FCT SHA 与历史记录逐项一致。早期失败 ID `cprep2-s0-c0-c16`、`cprep3-s0-c0-c16`、`cprep4-s0-c0-c16` 原样保留；未运行 ID 也未补跑。
- 本地原始证据入口为[报告](../research/ws30-stage3-correctness-report-r1.md)、[合并收据](../research/evidence/ws30-stage3-correctness-combined-r1.json)、[r6 收据](../research/evidence/ws30-stage3-correctness-results-r6.json)和[审计脚本](../../scripts/audit_ws30_stage3_correctness.py)。
- 阶段协议要求的 4/8/12 资源 pilot 已在同一正式源码 SHA `1ef424749e3c551dd788d0a709bd8e21c7cc89c9` 上完成 24/24 格；吞吐分别为 43.64、73.10 和 100.00 格/小时，并按预设 5% 规则选择 cap=12。详见[资源 pilot 报告](../research/ws30-resource-pilot-report-r1.md)。剩余必做项为 192 格主矩阵、72 格先占矩阵、12 格正式组成效果矩阵及双侧分析和图表。当前正式效果格为 0/276。

## 3. 已完成工作

1. 用户此前已授权：服务器无人、隔离与资源 pilot 通过后，尽可能利用空闲资源执行研究矩阵；无需重复询问。
2. 阶段 3 的技术格和合并收据已生成。运行 `python scripts/audit_ws30_stage3_correctness.py` 通过。
3. 完成报告 SHA 与原始收据复核，并修正报告中的 Gemma PDF SHA-256。正确值为 `2b11ed4e673f8f6201c0182f158359a4d8f8394eb6029fa394dcd2c736052e15`。
4. 依据项目规则从候选 README 和阅读日志核对 Gemma、DiffFlow、SeqBalance 固定版本，记录借鉴点、适用条件和不可外推范围。论文只作方法参考，不替代项目 raw 证据。
5. 阅读阮一峰《中文技术文档的写作规范》README 及标题、文本、段落、数值、标点符号、文档体系六章，并据此复核报告和状态文字。原文：[写作规范](https://github.com/ruanyf/document-style-guide)。

## 4. 已形成的设计决策

- 12 格合成夹具归类为技术验证，不计入 24 个独立需求 seed，不计入正式效果格。
- 组成交换改变 C16 选择只能说明该固定输入下的类别队列读数参与选路。静态 FIFO 中相同总字节的即时等待不会因类别标签自动降低，因此不把选择变化写成时延改善。
- 资源 pilot 启动前重查作业、CPU/load、内存、磁盘、运行器锁、目录隔离、失败恢复和吞吐。原计划 cap 阶梯为 4/8/12；提高上限先审计 runner 与 remote_worker 硬限制，不绕过保护。
- 阶段协议要求监督时实际使用 GPT-6 Luna / Medium。已从当前 Codex 会话 JSONL 的最后一条 `turn_context` 核实模型为 `gpt-6-luna`、effort 为 `medium`，turn ID 为 `01a16e6f-65eb-7b41-86aa-c00ee45355aa`。

## 5. 当前状态

阶段 3 文件提交 `2b44ccf` 与资源预检状态提交 `8e5ebdd` 已推送到个人 fork 的 `research/ws30-attribution-audit`。本次 runner 授权校验、执行授权收据和最终状态更新尚待提交。

阶段 3 组成夹具技术验收完成。此前同 WS-30 正式源码 SHA 的资源 pilot 为 24/24，通过 4/8/12 阶梯并选择 cap=12。2026-10-24 本次远端只读审计显示：无活动仿真，load1=0.0、可用内存 122.57 GiB、空闲磁盘 3,522.0 GiB。账户 UID 1000 下有 6 个长期 VS Code `OpenDebugAD7` 进程（各约 29 MiB RSS、采样 CPU 0%）和一个 `/usr/bin/python /usr/bin/hg outgoing -q` 进程（约 12 MiB RSS、CPU 0%）；未见其他非本账户普通 UID 作业。`simulation-start.lock` 存在但未见于 `lslocks` 的已持有锁。没有终止或修改这些进程。当前 turn_context 已核实为 GPT-6 Luna / Medium。主矩阵 runner 已启动，首批 12 格已保留；首格 `20261024-230000-ws30-main-s20263040-q16` 正在构建，当前验收 0/192、失败 0。先占和正式组成格未启动；正式效果格仍为 0/276。WS-30 整体未闭环，也不得据此归档。

## 6. 未解决问题

已完成的 4/8/12 资源 pilot：同正式源码 SHA 的 24/24 格通过，选定 cap=12。启动正式阶段前仍要刷新资源与锁审计。

必做且未完成：
- 完成 192 格主矩阵、72 格先占矩阵、12 格正式组成效果矩阵。
- 所有格回传后，完成逐格 raw 核验、双侧分析、统计、图表及反例审查。
- 验收最终代码、实际效果与结论逐项对应，完成任务闭环。

## 7. 后续推荐动作

1. runner 已改为校验完整 14 格合并正确性收据及冻结正式计划；将授权收据与修正一并提交并推送。
3. 使用已核实的 GPT-6 Luna / Medium 会话、已完成的 24 格资源 pilot 和最新远端快照，按冻结计划启动正式矩阵。每个阶段开始前仍须重查资源并遵守 runner 锁、cap 和降载门槛。
4. 固定 SHA、trace、seed、ID 和顺序；不得覆盖已有 raw，也不得因负效应取消正确性验收。
5. 正式格终态并回传后，切换到分析模型，完成逐格验收、双侧结果、图表和未完成项审查。

## 8. 与其他工作流的关系

本次更新只属于 `research/ws30-attribution-audit`。状态页入口为 `docs/project-state/CURRENT_STATE.md`、`WORKSTREAMS.md` 和 `ROADMAP.md`。没有修改 WS-29，也没有触碰参考仓库。WS-30 正式数据尚未产生，不改变 WS-25／27／28 的既有结论。候选文献仅提供机制与测量参考，不替代阶段协议、源码或固定 ID 的 raw。

## 9. CONTEXT SNAPSHOT

WS-30 阶段 3 的组成夹具技术验收为 14/14：12 个组成格、2 个关闭夹具历史回归格，固定仿真 SHA `2d7e31a9f6ae24f1514d02cbf341d27e6ec0717f`。总队列均为每候选 65,536 B；背景组成交换时 C16 切换出口，E/Q16 在固定场景中保持其选择。该结果是技术验证，不是性能收益。3 个早期失败 ID 保留。资源 pilot 24/24 已完成并选择 cap=12；当前正式效果格 0/276。当前 turn_context 已核实为 GPT-6 Luna / Medium。执行授权收据已绑定冻结计划和合并正确性收据。主矩阵、先占矩阵、正式组成矩阵及双侧分析未完成，WS-30 仍 ACTIVE。
