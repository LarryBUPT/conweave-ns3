# Handoff 19：WS-18 最小原型与正确性重验（进行中）

四臂最小原型已经产生了完整的三时刻、完成和路径原始数据，但首轮逐流核对发现四格末四条需求各早了 1 ns。修复版已编译成五份独立源码；**还没有运行修复后的仿真，WS-18 正确性未闭环，更没有机制收益结论**。这份交接记录当前工程关口，后续须以新五格 raw 更新。

## 1. 本对话目标

延续 WS-17 允许的最小工程范围，在 `feature/ws18-admission-routing` 实现独立的发送准入、上游路径和三时刻计量，使用旧 `fecmp` 加四个 WS-18 臂做同输入正确性回归。用户已授权按远程工作流执行最小实验；WS-19/20 效果矩阵仍关闭。

## 2. 已确认的项目事实

固定 trace `config/ws18_1280_correctness.txt` SHA-256 为 `4e7d0e6a68e3230e8960a174e570a0a788c191fa0b44922408867b02c25782cc`，拓扑 SHA-256 为 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。共同条件为 DCQCN、PFC=0、IRN=1、seed=1、400 Gbps。旧 `fecmp` 参考 ID `20260928-043000-ws18-legacy` 的 FCT SHA-256 为 `446999e4ee482866127964ded0e7a2c1c1e729d4c19d4cf5e22c267e5794ce67`。WS-17 已证明固定目的主机的最后出口唯一，旧 FCT 不含准入前等待；上游路径有多候选，但不能扩容最后出口。

## 3. 已完成工作

首轮四臂源码 `d5555637f8c625c190719a7dec2d3d73b2b171ef` 的结果分别为 `20260928-054500-ws18-r1-ecmp`、`20260928-055500-ws18-r1-admission`、`20260928-055501-ws18-r1-path`、`20260928-055502-ws18-r1-joint`。四格均 `SUCCEEDED`，各 40/40 完成、33,849,344 B；准入和联合格各有 32 条正等待，路径和联合格均触发跨 ToR 路径选择。逐流从 raw 的 `_out_ws18.txt` 与 trace 十进制原文重算，四格 ID 36–39 的 `demand_ns=2000049999`，原文应为 `2000050000`，其余 36 条匹配。因此四格均未通过完整正确性契约。

修复提交 `729d2682077fedc232c10b6eabccddc5168f8191` 只让 WS-18 使用整数纳秒调度和需求记录，旧模式保留原有 `Seconds(double)`；`scripts/verify_ws18_correctness.py` 改从 `raw/<raw ID>/config.log` 检查守恒/路径，并要求新旧 `fecmp` FCT 哈希相同。Python 编译及 `git diff --check` 通过；校验器对旧四格按预期在输入 ID 39 的时间断言失败。修复已推送个人 `origin`，远程 GitHub 拉取超时后通过同 SHA Git bundle 同步。服务器没有活跃仿真进程，构建前负载 0、可用内存约 123 GiB、磁盘约 5.7 TiB；五份隔离 `-j2` 构建均为 `BUILT` 且收据 SHA 一致：

| 格 | 新实验 ID（仅 BUILT，未运行） |
| --- | --- |
| 旧 `fecmp` | `20260928-145114-ws18-r2-legacy` |
| WS-18 `(0,0)` | `20260928-145800-ws18-r2-ecmp` |
| 仅准入 `(1,0)` | `20260928-145800-ws18-r2-admission` |
| 仅路径 `(0,1)` | `20260928-145800-ws18-r2-path` |
| 联合 `(1,1)` | `20260928-145800-ws18-r2-joint` |

## 4. 已形成的设计决策

保留首轮 raw 作 1 ns 故障诊断，不把 `SUCCEEDED` 当作契约通过。新 SHA 须从旧 `fecmp` 开始重跑五格；旧模式 FCT 与旧参考整文件哈希相同，四格逐流与原始十进制需求一致。修复后 WS-18 `(0,0)` 的末四条需求将移动 1 ns，不再用其 FCT 整文件与旧 `fecmp` 强行比较。失败则停止并换新 SHA/ID 重验，不运行 12×4 效果矩阵。理由和停止条件见[正确性契约](../research/ws18-correctness-contract.md)。

## 5. 当前状态

2026-09-28：WS-18 **ACTIVE，正确性未闭环**。远程五格全部只到 `BUILT`，没有修复版 raw；源码仿真 SHA 是 `729d268…`。本 Handoff 或状态文件后续提交造成的文档 HEAD 不能冒充仿真 SHA。进入长时后台仿真前需由协调任务实际切至 GPT-6 Luna High；本阶段使用 GPT-6 Sol High，尚未宣称切换完成。

## 6. 未解决问题

必须以新固定 SHA 跑完五格、回传所有终态 raw，并执行逐流身份、输入需求、三时刻、FCT 放行起点、完成/字节/等待、路径与背景检查。若失败，先定位源码或校验器再完整重验。之后仍需独立需求与双侧安全门槛；目前无业务 SLO、物理 MMU 占用和真实硬件证据。

## 7. 后续推荐动作

协调任务先实际切换 Luna High，再按上表 ID 顺序后台运行五个短正确性格，固定 trace/拓扑及共同配置，记录启动/终态和资源收据；运行中遵守约半小时精简监督。全部终态后回传 raw，实际切回 Sol High，用 `verify_ws18_correctness.py --legacy <新旧模式 ID> --legacy-reference 20260928-043000-ws18-legacy` 和四臂 ID 完整核验。失败格不得被后续格掩盖；通过后再更新本 Handoff 与状态，WS-19/20 仍需另立前瞻性效果门槛。

## 8. 与其他工作流的关系

WS-17 的唯一最终出口和源等待缺口是 WS-18 的动机，首轮 40 流是工程正确性输入，不是 WS-19 的独立需求小样。WS-10/11/12 的正式 no-go 与 WS-14 的停止决定均未重判；GuardHash/HarmGate 仅是历史原型。WS-21–24 仍是条件性分支。

## 9. CONTEXT SNAPSHOT

分支 `feature/ws18-admission-routing`，仿真源码固定 `729d2682077fedc232c10b6eabccddc5168f8191`；五个新 ID 均 `BUILT` 未运行。首轮四格虽 40/40 完成，但末四条需求各早 1 ns，故 WS-18 正确性未通过。固定 trace/拓扑 SHA、旧 `fecmp` FCT 哈希、五格 ID 和后续验收见本 Handoff 与[契约](../research/ws18-correctness-contract.md)。仿真启动前实际切 Luna High，终态 raw 后切 Sol High；WS-19/20 效果矩阵关闭。
