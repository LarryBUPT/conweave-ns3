# WS-29 分段恢复送审入口

2026 年 10 月 23 日。本轮只完成本地准备。尚未推送、部署 worker、构建或仿真。原 STOP 继续保留，自动化 `ws-29-2` 继续受原控制器阻断。

## 固定身份和证据边界

仿真源码固定为 `ec0c718f435a54f684d18e6933583335a60f81d5`。计划、unit 契约、各格和 runner 均使用同一身份。新的 unit ID 为 `20261023-090000-ws29-p1-unit`。所有新仿真 ID 使用 `20261023-090000-ws29-p1-<标签>`。远端 ID 空闲性尚未检查。

主审确认此次属于工程修复，不消耗机制候选或机制诊断修正名额。根因仍表述为“固定源码与原日志边界支持，暂无运行时 backtrace”。新增 C++ 测试与修复版仿真尚未运行。

主审已拒绝为统一 SHA 而重跑原 16 个通过格的建议。本入口安排 13 个新格，复用其余 14 格的旧版正确性证据。旧 `main-c0` 和 `link-20-c0` 保留为历史证据，同时分别新增同 SHA 基线和针对物理改动的必要回归。跨 SHA 组合不能称为 27 格均在新 SHA 验证。

固定材料如下。

| 文件 | 用途 |
| --- | --- |
| [分段计划](evidence/ws29-segmented-recovery-plan.json) | 新顶层源码、unit 身份、13 格顺序、14 格复用索引及原验收字段 |
| [unit 契约](evidence/ws29-recovery-unit-contract.json) | 普通 optimized 构建、兼容测试构建、补丁、恢复哈希和六条 PASS 记录 |
| [影响审计](evidence/ws29-recovery-impact-audit.json) | 改动文件、逐函数哈希、初始化影响与逐格复用依据 |
| [材料锁](evidence/ws29-recovery-lock.json) | 上述三份材料、worker 和控制器依赖文件的 SHA-256 |
| [命令清单](evidence/ws29-segmented-recovery-entry.json) | runner 选定的计划路径、unit 路径和逐格命令 |
| [本地复核](evidence/ws29-recovery-local-checks.json) | 14 格原 raw 重新核验、旧收据哈希及 STOP 未变记录 |

入口为 [run_ws29_recovery.py](../../scripts/run_ws29_recovery.py)。旧 runner、旧计划和旧 STOP 均未切换或解除。旧的 [27 格草案](evidence/ws29-physical-fix-review-plan.json)已经标为被本方案取代，不作为执行来源。

## 分段顺序

| 阶段 | 新 ID 数 | 顺序与通过条件 |
| --- | ---: | --- |
| unit | 1 | 普通 optimized 构建，再进行披露兼容修改的测试构建；包括新增三臂物理行为测试 |
| physical | 6 | `link-23-c0`、`link-20-c0`、`link-23-c1`、`link-20-c1`、`link-23-c2`、`link-20-c2` |
| baseline | 1 | `main-c0`，保留原 FCT 兼容性判据，并建立新 SHA 的主档基线 |
| synthetic | 3 | `synthetic-15`、`synthetic-16`、`synthetic-17` |
| cost | 3 | `main-c1`、`main-c2`、`main-c3`，与新 `main-c0` 配对解释成本和采用机会 |

每一阶段都需要主审单独授权。后段授权不替代前段 raw 验收。unit 失败或新增用例缺失时，物理格不能开始。任何时刻并发为 1，显式处理一格，RUNNING 时只等待下一轮监督。

原 `link-20-c0` 的必要回归单独列入[影响审计](evidence/ws29-recovery-impact-audit.json)。它经过此次修改的物理 down/up 方法和新增运行时检查，需要与全端口故障形成同 SHA 的单链路对照。其余五个物理格均是原失败或未完成项目。

## 旧格复用的影响审计

`DoLbClassReserve`、`ChooseWs29Feedback`、`GetOutDev`、heartbeat 激活及端口记录函数的函数体逐字节相同。`Ws29Fault` 的非物理分支后缀也逐字节相同。完整差异包含旧源码固定后新增的控制器、校验器和文档提交；仿真文件的差异只有 scratch 初始化、交换机物理故障目标选择，以及新增测试。

`legacy-v2-hb200` 关闭 WS-29，沿原路径运行。`k4-c1-normal` 和 11 个协议格原本就开启 heartbeat，主机端口集合的初始化不变。这些协议格不会进入 fault 20～24 的物理分支。

`mixed8-c0` 会新增主机端口集合，但 fault、heartbeat 和端口日志均关闭。集合的相关读取分支没有记录或选路副作用。上述判断结合相同的选路与反馈函数，支持保留该旧格；它并非新 SHA 的动态 PASS。

本地已重新核验这 14 格的完整原 raw 与构建资源，结果与原 verified 收据相同。执行新段前，runner 还会再次核对这些原证据。任何旧 raw 或收据变化都会阻断恢复。

## unit 独立验收

worker 先从新固定 SHA 建立独立源码副本，完成未修改源码的普通 optimized 构建。随后仅在测试副本中应用已披露的两行 CommandLine 签名兼容修改，使用 `build-ws29-tests` 构建测试。

必须检查全部六条 PASS 记录：suite 本身、原有四个用例，以及 `WS-29 all-link faults preserve host links without telemetry`。新增用例在三个臂下均关闭遥测，并省略主机端口注册，验证主机链路保持 up，交换机链路两端 down 后均恢复。

验收还核对 suite 注册、完整命令链、普通构建日志、原 core 文件字节、精确补丁、补丁前后及恢复哈希，以及恢复后的 tracked diff。源码恢复不改变已经构建的测试二进制；测试结果必须保留该兼容修改边界。正式仿真使用新的未修补副本。

unit 的完整资源日志为 `logs/resource-samples.jsonl` 与 `logs/resource-summary.json`。新仿真的构建和运行分别使用 `build-resource-*` 与 `resource-*`。worker 已增加恢复前缀，避免新 ID 遗漏采样或覆盖构建资源记录。该 worker 尚未部署；runner 会检查远端 worker 的哈希与材料锁一致，才允许继续。

## 执行门控

本地准备命令可以重复运行，结果必须与既有材料相同。该阶段不会接触 SSH。

```powershell
python scripts/prepare_ws29_recovery.py
python scripts/run_ws29_recovery.py prepare
```

执行命令必须由主审授权后使用。

```powershell
python scripts/run_ws29_recovery.py unit-build
python scripts/run_ws29_recovery.py unit-collect
```

物理阶段通过主审后，逐格使用 `build`、`start`、`collect --label <标签>`。每次只有一个显式标签。新 runner 不会自行推送、同步源码或部署 worker，这些前置操作也须另有授权。

阶段授权收据位于 `results/ws29-physical-recovery-control/approval-<阶段>.json`。收据必须与 runner 的 `binding(plan, lock, stage)` 返回值完全相同。绑定内容包括阶段、新源码、计划、unit 契约、材料锁、runner、worker 和原 STOP 哈希。`prepare` 不生成授权收据。本轮授权收据不存在，因此所有执行阶段都会在远端调用前拒绝。

原 STOP 必须存在、保持原哈希且不是符号链接。新控制目录若出现自己的 STOP，也立即阻断，禁止自动重试。原 STOP 从不由恢复入口删除或改写。缺少 GO 时只拒绝执行，不伪造一次实验失败；获准执行后发生异常，则保留新 ID、完整输出和新 STOP。

旧控制器继续受原 STOP 阻断。自动化 `ws-29-2` 不会因本地存在新入口而切换计划或自动恢复。

## 验收与未完成项目

每个仿真格继续使用原 raw 校验、完成数和字节、输入哈希、事件上限、overflow、队列守恒、observation 分账与资源门槛。恢复校验另外从固定拓扑独立重建端口编号，核对两端 down/up 事件的目标、时间和次数，拒收主机端口事件。没有放宽原数值门槛。

本地 53 项 Python 测试通过，覆盖身份混用拒收、unit PASS 缺失、兼容恢复失败、资源摘要与样本不符、GO/STOP 门控、参数链和物理目标核验。新增 C++ 动态验收仍未完成。原 STOP 哈希保持 `731fd085b1a7a59dd998c79488c1307d70fe4f20302f4499b7859d1a88ada7e9`。

诊断节点的 SGLB 参考复核保存在[诊断交接](../handoffs/2026-10-23-ws29-link23-stop-diagnosis.md)。本次按其身份与物理状态分账原则补充了目标校验，未引入 BGP、SyncMesh 或新反馈机制。文献结果不替代新 unit 与原 raw 验收。

A06 继续 OPEN。独立效果 pilot 和正式矩阵继续关闭。主档自然采用机会、双侧分析和参考文献复核仍由后续主审承接，当前材料不构成 WS-29 闭环。
