# Handoff 26 — WS-21 长尾 pair 构建与启动门槛

## 1. 本对话目标

继续 WS-21 下游反馈诊断，为预选 WS-17 ToR 热点加 192 条背景流输入建立同 SHA 诊断开/关 pair。此阶段只验证长尾条件下的观测覆盖、QP 传输转折、出口事件完整性和诊断非扰动；不运行效果小样，不声称机制收益。

## 2. 已确认的项目事实

个人 fork 分支为 `feature/ws21-downstream-feedback`，任务开始时 HEAD 与 `origin` 同为 `fdedcd770f22491a612e76372973538b16ca31b6`，工作树干净。trace 为 `config/ws17_seed20261701_tor_hotspot_b192.txt`，SHA-256 `9996372ea22158ca995937c727b6fef20559e0ce910b22e77529d9a8061b0cc3`，共 16,576 条流、1,744,830,464 B；其中 16,384 条 8 KiB MoE 流与 192 条 8 MiB 背景流。拓扑 `config/topo_1280_400G_400G_OS1.txt` 的 SHA-256 为 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。

规定的共同参数是 mode 20 / `ws18`、DCQCN、PFC=0、IRN=1、seed=1、WS18 admission/path=0、`WS13_DIAG=1`；关闭格的 WS-21 开关为 0/0，开启格为 1/1。完整冻结契约见[WS-21 长尾技术 pair 契约](../research/ws21-long-tail-technical-pair-contract.md)。

## 3. 已完成工作

已按项目工作流读远程实验准则、baseline/dataflow 审计、项目状态 Skill、CURRENT_STATE、WORKSTREAMS、ROADMAP、Handoff 25 和长尾 pair 契约。核对源码及 Git 后发现远端缓存没有新 SHA；先按 `sync` 流程尝试服务器 GitHub fetch，工作区 `login.sh` 重试后仍超时，再使用项目脚本通过 SSH Git bundle 同步个人 fork 固定 SHA。隔离构建随后成功：实验 ID `20260929-130119-ws21-longtail-diagnostic`，SHA `fdedcd770f22491a612e76372973538b16ca31b6`，optimized、`-j2`，状态 `BUILT`，构建时间 2026-09-29 05:01:21–05:07:05 UTC（约 5 分 44 秒）。构建日志到达 1448 个目标并完成。

## 4. 已形成的设计决策

**长尾 pair 的隔离构建门槛通过；仿真尚未启动。**长时实验必须实际切换到 `gpt-6-luna` High 进行静默监督，终态后实际切回 `gpt-6-sol` High 分析。本对话暴露的工具中没有当前线程模型切换接口，因此不能确认切换生效；按项目硬门槛，不启动仿真。此限制来自 `docs/REMOTE_EXPERIMENT_WORKFLOW.md` 的“长时矩阵运行准则”，不是实验数据结论。源码已同步和构建不会单独证明仿真成功。

## 5. 当前状态

截至 2026-09-29，本机工作树在本 Handoff 与状态文档修改前干净；分支和远端均为 `fdedcd770f22491a612e76372973538b16ca31b6`。构建 ID `20260929-130119-ws21-longtail-diagnostic` 为 `BUILT`。off/on 长尾实验 ID 尚未分配，无仿真进程、raw、资源峰值或结果分析。本轮未核验仿真启动所需的远端其他用户作业和资源状态，因为模型门槛尚未满足。

## 6. 未解决问题

待完成长尾同 SHA pair；完整记录 16,576 QP 的完成/字节守恒、FCT 与 WS18 逐字节一致、跨 ToR 身份、全仿真窗口出口事件无溢出、背景 QP 的 SACK/ACK-CNP/NACK、恢复队列、重传、超时和 DCQCN 速率转折，以及运行 CPU/内存峰值、日志大小与事件速率。若日志超过 50 MB、资源受压、出现他人作业或任一格失败，按契约停止后续格并保留收据。

没有真实反馈消息，因此即使 pair 通过，也只关闭观测与非扰动技术子门槛，不能关闭完整技术 pilot或打开效果矩阵。CE 候选样本不足时报告为不可区分，不当作 0% CE。

## 7. 后续推荐动作

1. 通过可用编排工具实际切换至 GPT-6 Luna High 并核实当前配置。
2. 启动前核验远端用户作业、系统负载、可用内存、磁盘、ns-3 进程及资源收据能力。
3. 对冻结的 WS-17 trace 运行诊断关闭与开启两格，使用相同源码 SHA、输入、拓扑、seed 和共同参数；静默运行并按工作流约半小时检查精简状态。
4. 两格终态后回传和核验原始数据，实际切换至 GPT-6 Sol High，运行配对核验器及逐 QP 事件分析。
5. 若模型切换仍不可用，维持 `BUILT` 状态，不启动仿真；向后续操作线程明确交接该门槛。

## 8. 与其他工作流的关系

WS-21 效果矩阵仍为 NO-GO；40 流身份/出口事件 pair 只满足此前的技术子门槛。该长尾 pair 不能代替真实反馈路径、消息成本/年龄/丢失/回退验证。WS-10/11/12、WS-19/20 历史 no-go 不变，WS-22/23/24 前置条件不变，WS-25 只整合已实际执行的证据。

## 9. CONTEXT SNAPSHOT

`feature/ws21-downstream-feedback@fdedcd770f22491a612e76372973538b16ca31b6` 的 WS-21 长尾诊断源码已同步并通过隔离 optimized `-j2` 构建，ID `20260929-130119-ws21-longtail-diagnostic`，状态 `BUILT`，耗时约 5m44s。长尾仿真没启动；当前工具没有实际切换线程模型的能力，不能确认工作流要求的 Luna High 监督已生效。下一步先在可切换并能验证模型的线程完成切换，再检查远端资源并执行 off/on pair；终态后切回 Sol High 分析。当前没有新 raw、运行耗时或效果结论；WS-21 效果矩阵仍关闭。
