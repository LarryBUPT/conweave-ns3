# WS-30 工程首格执行门准备

日期：2026 年 10 月 27 日。正式 168 格已通过主对话的原始记录、配对统计、批尾恒等式和历史 DRILL 回放验收。当前仅承接工程首格 `technical-single`，cap 1；technical-rest、生命周期和 W5 保持未放行。

## 1. 固定范围

目标 ID 为 `20261026-120000-w30v14-t01-e-o0`，固定源码为 `0673e4c3de34d83585dd40f6be7fbd3ed000a9ee`。冻结契约及 schedule 未变，全部原控制文件也未改。

原正式授权已被封存计划引用，不能直接追加工程阶段。本节点建立[独立首格收据](evidence/ws30-v14-technical-single-authorization-r1.json)及[独立入口](../../scripts/run_ws30_v14_technical_single.py)。收据保存主对话正式验收文件的哈希、单一 ID、源码、cap、原授权哈希、控制哈希和入口自身哈希。授权链来自既有用户任务对主对话节点验收与阶段决策的委托，以及本轮主对话仅放行首格的明确指令。

新入口在检查真实模型、范围及全部哈希后，选用独立授权文件调用原执行器。原执行器的完整授权检查、控制器锁、隔离构建、启动、资源监督、回传和 raw 验证逻辑保持原字节。入口拒绝扩阶段、提 cap、换 ID、换源码、占用目录和已有执行收据，也不提供重试或续跑路径。

## 2. 已完成的只读门槛

[预检收据](evidence/ws30-v14-technical-single-preflight-r1.json)核实：

- 实际上下文为 GPT-6.1 Sol / Medium，turn ID 为 `01a179fa-9ecd-7a70-95ab-f136276102c3`。
- origin 为个人 fork；远端分支头 `a39b149` 包含固定新源码 `0673e4c`。
- 全部冻结输入与固定源码 Git blob 一致；首格 trace 和 topology 的远端缓存哈希也一致。
- 已部署 worker 与本地字节一致，兼容新增参数和 metadata schema 3。
- 目标 ID 的本地正式目录、暂存目录、build intent、远端 runs/results 路径均无占用。
- 服务器无其他用户或未知仿真，可用内存约 122.49 GiB，磁盘约 2,697.6 GiB，load 为 0.08；独立入口二次只读预检时 load 为 0.01。

[范围与模型检查](../../scripts/test_ws30_v14_technical_single_entry.py)共 6 项通过，覆盖精确范围、阶段扩张、cap 扩张、ID/源码替换、未批准收据及错误模型在 Backend 前拒绝。测试没有远端调用或原生仿真。

## 3. 当前断点与执行入口

新增原生构建为 0，新增仿真为 0。隔离 optimized 构建与实际旧技术 FCT 回归仍未完成；不能用输入哈希或本地检查代替。

当前真实模型仍为 Sol / Medium。长时执行须在后续真实 Luna / Medium turn 中核实上下文后运行以下独立入口，stdout/stderr 使用新 results 文件，并按项目规则在后台隐藏运行。入口会重新检查资源和占用状态，然后只执行该单格。

```text
python scripts/run_ws30_v14_technical_single.py run --session-file ACTUAL-LUNA-MEDIUM-SESSION
```

终态后切回实际 Sol / Medium，核验固定源码、模拟/需求 seed、输入、完整 raw、原生构建模式、旧 FCT/路径回归、观测关闭语义和资源收据。出现失败时保留原 ID，不重跑、不覆盖。主对话验收首格后，才承接 technical-rest；本节点没有启动其他工程或 W5 阶段。
