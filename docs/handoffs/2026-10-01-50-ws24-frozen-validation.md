# Handoff 50：WS-24 冻结 14 格合成多网卡验证

日期：2026-10-01。执行线程：`01a0f1da-f1e2-7870-9361-24b4d626fd76`。

## 1. 本对话目标

执行 WS-24 后续冻结协议 A/B/C/D 的 14 格验证：旧五列/六列四 baseline 回归、320-host 多网卡目标拓扑正确性、动态 CNP 收发/降速正确性，以及固定逻辑需求和总字节的 rail × placement 四臂 pilot。遵守逐格停机、原始数据保留和 Luna High 监督、Sol High 分析边界。

## 2. 已确认的项目事实

- 仿真源码固定 SHA：`b1184d6a7bd38577b235b7f119f920973308774f`；14 格均使用独立 optimized build（`-j2`）、seed 1。协议与验收代码在 `docs/research/ws24-followup-validation-protocols.md`、`scripts/verify_ws24_legacy.py`、`scripts/verify_ws24_result.py`、`scripts/verify_ws24_matrix.py`。
- 输入 manifest SHA-256 为 `55997be83ecf7e43accc2f6bc546b97185943657cdc64da0d5c89ef91a52b127`；离线输入验收确认 11/11 文件。目标 fixture 是合成的 320 host、1,280 NIC、576 switches、3,840 links，运行时 max RTT/IRN BDP 为 600 ns/30,000 B。
- 合成模型及其拓扑来源不提供真实服务器、物理 NIC 或 job placement 证据。所有效果数字只对应一组 seed=1 的受控合成需求。

## 3. 已完成工作

用户授权执行冻结矩阵；工具执行如下，逐格 raw 已 fetch 至对应 `results/<ID>/`，并经单格与矩阵验收器核验：

| 组 | 实验 ID | 验收结果 |
| --- | --- | --- |
| A 五列 | `20261002-100000-ws24-legacy5-fecmp`、`20261002-100100-ws24-legacy5-conga`、`20261002-100200-ws24-legacy5-letflow`、`20261002-100300-ws24-legacy5-conweave` | 每格 19,388/19,388 流、tag=0；FCT SHA 分别 `d712e769…eb976`、`0c041fd0…667d3`、`abb659fe…eee0f`、`b2334230…01255`，逐字节匹配 WS-06 历史参考 JSON。 |
| A 六列 | `20261002-101000-ws24-legacy6-fecmp`、`20261002-101100-ws24-legacy6-conga`、`20261002-101200-ws24-legacy6-letflow`、`20261002-101300-ws24-legacy6-conweave` | 每格 4/4 流；tag=1/2 各 2 条；输入与 OS2 拓扑哈希一致。四算法此微型 trace 的 FCT SHA 相同；raw 显示 CONGA/LetFlow flowlet timeout 均为 0，ConWeave reroute/OoO/VOQ flush 均为 0，故这些动态分支未触发。 |
| B 目标图 | `20261002-110000-ws24-target-320host-correctness` | 10/10 流、2,408,448 B 守恒；覆盖 4 rails（3/3/2/2）；逐流 identity、1280 NIC 路由及运行时 600 ns/30,000 B 校验通过。 |
| C CNP | `20261002-120000-ws24-cnp-incast-correctness` | 4/4 流、4,194,304 B 守恒；验收器关联 7 个 CNP flag、7 个源端接收和 7 个真实 rate-decrease 事件，QP/NIC/序号身份通过。 |
| D 固定放置 | `20261002-130000-ws24-fixed-single`、`20261002-130100-ws24-fixed-multi` | 两格均 10/10 流、2,408,448 B；单 rail 全走 rail 0，多 rail 计数 3/3/2/2。 |
| D 可变放置 | `20261002-130200-ws24-variable-single`、`20261002-130300-ws24-variable-multi` | 两格均 10/10 流、2,408,448 B；单 rail 全走 rail 0，多 rail 计数 3/3/2/2。 |

`verify_ws24_inputs.py` 返回 `offline_input_verified`；`verify_ws24_matrix.py` 返回 `cells_verified=14`。全 14 格资源收据终态均为 `SUCCEEDED`。大拓扑格峰值进程树 RSS 约 7,258 MiB，可用内存最低约 115.9 GiB，工作区空闲盘最低约 5,635 GiB；均未越过协议限值。矩阵机器摘要位于 `docs/research/evidence/ws24-followup-validation-summary.json`。

B 格最初一次 run 入口因漏写 topology 名后缀而在仿真启动前拒绝；状态仍为 `BUILT`、无 raw，随后使用协议规定的 `ws24_synthetic_320host_4nic_topology` 在同一预留 ID 正确启动并通过验收。

## 4. 已形成的设计决策

- 冻结批次通过只说明旧输入兼容、合成多网卡/目标图正确性、CNP 控制路径及四臂身份/守恒验收通过。
- D 的多 rail − 单 rail 完成跨度为固定放置 `−173 ns`、可变放置 `−164 ns`；每个臂只有一个合成需求 seed 且无准入等待。这些是描述性 pilot 数字，不形成统计或普遍性能收益结论。
- CNP 的受控 incast 触发了收发及降速路径；B/D 常规输入的 CNP 计数为零，不据此推断未触发路径的行为。

## 5. 当前状态

WS-24 的冻结 A/B/C/D 14 格执行范围已完成。执行分支为 `feature/ws24-multinic-validation`；本次状态记录基于该独立 checkout，记录时 HEAD 为 `ebdaec93f81b37f099dd4bf9f42ca9f7a029abc4`，不改动实验源码或 raw。远程监督阶段使用 GPT-6 Luna High；全部终态 raw 回传后实际切至 GPT-6 Sol High 复核。WS-23 独占 `workspace/LarryBUPT-conweave-ns3`，本次未在该共享 checkout 切分支或编辑文件。

## 6. 未解决问题

- 没有可信的真实 physical-host/NIC/job/rank placement 映射来源，合成 fixture 不能支撑真实集群部署主张。
- 没有独立需求 seed 或预注册的确认性性能样本；D 不证明跨需求普遍收益。
- WS-23 IRN×PFC 端到端恢复验证是另一工作流的未完成事项，不被本 handoff 覆盖。

## 7. 后续推荐动作

若论文或系统主张需要真实集群映射，先取得可审计的主机/NIC/job 来源，再另立对应验证。若需要推广 D 的效果，先冻结独立需求、样本数、双侧指标和停止规则，再讨论确认性矩阵；不得把本 pilot 的四臂或逐流当独立重复。除此之外，本次冻结矩阵不需要重跑。

## 8. 与其他工作流的关系

仅更新 WS-24 个人 fork 分支状态；不修改 `conweave-project/conweave-ns3` 或 `maplerime/conweave-ns3` 只读参考。WS-23 继续按其恢复契约单独执行；旧 WS-10/11/12 等性能 no-go 不被本矩阵改写。真实部署映射和本 pilot 不能并入既有性能排名。

## 9. CONTEXT SNAPSHOT

WS-24 冻结协议 14/14 格在仿真 SHA `b1184d6a7bd38577b235b7f119f920973308774f` 上全部通过单格和矩阵验收，所有 raw 与资源收据已 fetch。旧五列 FCT 与历史锚点逐字节一致；旧六列每格四流及 tag 1/2=2/2；320-host 目标图 10/10、2,408,448 B；CNP incast 4/4、4 MiB 且观察到 7 次真实降速；D 四臂各 10/10、2,408,448 B，single/multi 完成跨度只改善 173/164 ns，属于单 seed 合成描述性 pilot。状态证据见 `docs/research/evidence/ws24-followup-validation-summary.json` 和 `results/<ID>/`。不声称真实部署映射或确认性性能收益；WS-23 仍独立 ACTIVE。
