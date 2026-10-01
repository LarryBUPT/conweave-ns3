# Handoff 53：WS-24 纯 ns-3 独立合成需求预飞行

**后续纠正（2026-10-02）：**第一格 `20261002-180000-ws24-ind-j01-fs` 后来实际运行并通过流正确性验收，但没有资源观察器收据，因此只保留为正确性前置结果，不计入矩阵。[Handoff 54](2026-10-02-54-ws24-resource-watch-correction.md)记录控制器修复、替代 ID `...j01-fs-r2` 与新固定 SHA `3b992ee`。本 Handoff 中 `166ca67` 是旧尝试源码，已不再是正式矩阵 SHA。

日期：2026-10-02。状态：**ACTIVE；本地输入与协议已冻结，远程新矩阵未启动。**

## 1. 本对话目标

依据用户明确决定“不要真实主机数据，仅NS3模拟”，修订 WS-24 的验收边界，继续完成原多 rail × placement 目标中独立 job 需求支持的效果验证准备。旧单 seed 四臂仅作描述性 pilot。

## 2. 已确认的项目事实

工作区 `workspace/ws24-multinic-validation` 的 `feature/ws24-multinic-validation` 分支及个人 `origin` 持有新固定源码 `166ca6709e2b6ea8b60978bf80778fee636937e5`。旧仿真 SHA `b1184d6a7bd38577b235b7f119f920973308774f` 的 A/B/C/D 14 格 raw 已复算通过；同 SHA `devices-point-to-point` 补验为 5 PASS/0 FAIL，见[Handoff 52](2026-10-02-52-ws24-sol-review.md)。原拓扑只能追至合成生成器，不提供真实物理 host/NIC 或 job 证据。本次用户决定见[ADR-009](../decisions/ADR-009-ws24-ns3-only-scope.md)。

## 3. 已完成工作与证据

生成器 `scripts/make_ws24_independent_inputs.py` 已将 12 个不同生成 key 的合成 job 块写成 48 份四臂输入，每块 30 流，同一 job 的四臂逐流逻辑需求配对。固定源码提交包含生成器、输入、`config/ws24_independent_manifest.json`、逐格与矩阵验收器、控制器隔离 worker 名称入口。manifest SHA-256 为 `e94251d3717f368b8f7c1bd1de5788d524559f8dc65c5b788aeb874ccbc2977d`，记录 48 个输入哈希、12 个逻辑需求哈希、48 个预留 ID 和执行顺序。

本地实际运行 `python scripts/make_ws24_independent_inputs.py --check`，返回 48 文件/12 job、逐字节再生成通过；`python scripts/verify_ws24_independent_inputs.py` 返回 48 配对臂/12 job、字节范围 2,695,168–10,928,128 B、静态输入验收通过；对 manifest 独立 SHA-256 复核一致。`python scripts/verify_ws24_matrix.py --source-sha b1184d6a7bd38577b235b7f119f920973308774f --reference-fct-sha-json docs/research/evidence/ws24-legacy-reference-fct-sha.json` 从旧 raw 返回 `cells_verified=14`，旧描述性跨度差固定放置 −173 ns、可变放置 −164 ns。以上均非新 30 流动态结果。

已写[独立合成需求事前协议](../research/ws24-independent-synthetic-effects-protocol.md)、[必做清单](../project-state/WS23_WS24_VALIDATION_PLAN.md)和项目状态入口；旧[14 格协议](../research/ws24-followup-validation-protocols.md)及 Handoff 52 顶部标明后续范围决定，保留历史判断本身。

## 4. 已形成的设计决策

WS-24 只报告 ns-3 合成模型结果，无需取得真实服务器数据，不外推生产性能。原独立 job 需求效果验收仍必做。每个合成 job 是重复单位，四臂配对；预先冻结 12 块、指标、双侧精确符号检验及资源停止条件。真实来源路线由用户范围决定取代，旧单 seed pilot 和行序置换不充当独立重复。独立 worker 使用 `/home/fnl/lzy/.research-workflow/ws24_worker.py`，不覆盖 WS-23 共享 worker。

## 5. 当前状态

本地协议与 48 份 Git 输入已准备并通过静态检查。远端只有先前约 01:49 的只读采样（当时无登录用户、load1m 0.00、MemAvailable 约 122 GiB、空闲盘约 5,597 GiB，预留 ID 未发现）；该收据不代表启动时状态。**隔离 worker 尚未部署，j01 四臂及其余 44 格尚未 build/run/fetch。**本任务未由工具实际切换至 GPT-6 Luna High，因此未跨过远程仿真启动门槛。

## 6. 未解决问题

新 30 流输入的动态路由、NIC/rail、完成/字节守恒和运行时 RTT/BDP 尚无 raw。旧构建进程树 RSS 峰值约 7,258 MiB，接近 8 GiB 单格停止线，须以 j01 单格并发 1 实测。12 个独立合成 job 的四臂效果、反例及双侧结论均未知；任何正负效果都不能预写。

## 7. 后续动作与门槛

先由具备切换能力的监督任务**实际切至 GPT-6 Luna High**。重新只读检查其他用户/未知或 WS-23 作业、load/内存/磁盘、48 个 ID 空闲、共享和隔离 worker 状态；按协议部署并校验独立 worker，固定源码同步。以 `j01` 四臂逐格 build/run/fetch/raw 验收，单格并发 1；任一失败保留 ID/raw、定位并以新 SHA/ID 重验。pilot 通过后按 manifest 顺序完成余下 44 格，后台静默约半小时精简监督。全部终态 raw 回传后**实际切回 GPT-6 Sol High**，从 raw 逐格复核并按 job 为单位执行冻结双侧分析。闭环前核对[必做清单](../project-state/WS23_WS24_VALIDATION_PLAN.md)，不提前归档。

## 8. 与其他工作流的关系

WS-23 恢复验证独立 ACTIVE，其 checkout、共享 worker 和结果不得覆盖。WS-25 引用 WS-24 时须标明合成模型和证据等级，不替代本矩阵验收。旧 14 格、失败单测 ID 与历史 raw 均保留，旧性能 no-go 不改。

## 9. CONTEXT SNAPSHOT

用户已把 WS-24 限定为 ns-3 合成模拟，真实数据不是闭环条件。旧 14 格与同 SHA 单测已验收，但四臂只有单 seed。新固定源码 `166ca6709e2b6ea8b60978bf80778fee636937e5` 含 12 个不同合成 job × 四臂、48 个已哈希输入，manifest SHA `e94251d3717f368b8f7c1bd1de5788d524559f8dc65c5b788aeb874ccbc2977d`；静态与旧 raw 回归通过。新远程 48 格未启动，WS-24 ACTIVE。下一步实际 Luna High、远端重查、隔离 worker 与 j01 四臂 pilot；余下 44 格及终态 Sol High 分析均必做。
