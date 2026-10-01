# Handoff 55：WS-23 v2 Sol High 原始复核与共享入口释放

日期：2026-10-01。来源：WS-23 验证任务 `01a0f15f-58c7-7532-84bd-9acaaaa14525`；Integration 任务 `01a0cfac-3176-7590-bf34-c0f176a45118` 已实际将监督模型切回 GPT-6 Sol High。证据等级：固定合成输入技术正确性；不是正式效果比较。

## 1. 本对话目标

在已回传的 v2 control/probe 双格上，按工作流用 Sol High 独立核验原始数据，修正交接中的证据错误，确认 WS-23 远端入口已无在途依赖，并只读检查后续 PFC=0 跨类四格的独立固定源码和验收边界。本阶段不启动跨类四格。

## 2. 已确认的项目事实

- 双格仿真源码固定为 `94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1`；control `20261001-151000-ws23-rto-v2-control-r2`、probe `20261001-151100-ws23-rto-v2-probe-r2` 均 `SUCCEEDED`、16/16 完成，输入 trace SHA-256 `bc2db1513cbde20f12eea6efa4e2265cf74954be4fa45f2a147ff0ce84b33985`、拓扑 SHA-256 `dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad`、seed 1 一致。原始结果在本地忽略目录 `results/<实验 ID>/` 及远端同名目录。
- control 原始日志有 161 次准入丢包，源 14 为 36 次；probe 注入前的 161 条丢包记录与 control 逐行相同。两格 FCT 文件哈希分别为 `97feb0e118544f07e006da9e9bc2ead2566a10b91ad2201e0e83ced89279b18a` 和 `86ea6fc3275f08169c6b539ae2c2a534d29bb95ed31866832c9eee5322550ef0`。
- probe 唯一门控触发时目标 QP 存在未确认数据。源主机 14、PG 3 于 `2007201003 ns` 收到暂停、于 `2008801003 ns` 收到恢复；定向刷新 1599 次，暂停期延期 4 次、恢复宽限期延期 1 次。目标于 `2009121003 ns` 恢复，恰为源端恢复后 `320000 ns` 的完整 RTO，后于 `2009250592 ns` 完成；仿真停在 `2017100000 ns`。两类各 8/8；两格各 16 个唯一 QP 完成收据，大小、确认/下发序号和传输字节守恒；三次超时恢复均未发生在对应源端暂停期间。
- 两格观察器分别有 10/11 个正 RSS 样本，进程树峰值 204.26/204.39 MiB，采样负载最高 1.44/1.60，资源均未触及停止线。[机器证据](../research/evidence/ws23-deferral-v2-20261001.json)的 probe 主日志哈希曾抄漏字符，已按未变的原文件修为 `9f88ec5179db849fdae11fcbd3e7c39b2550a1b86f7697a3fc5b95df3e450d6e`；control 日志哈希为 `6d07cfb970c62a1cf031bce67bd34d56bd43fa95a03ca689f53d63821c1349b0`。
- 2026-10-01 09:31（北京时间）远端 1 分钟负载 0.0、无登录用户、无仿真或编译作业，可用内存约 122.98 GiB、空闲磁盘约 5655.9 GiB。worker SHA-256 为 `9e1b4e144d5584e8999d2c560bf4577b249ca73421d9aac6c53e5a96a798766e`。此前确认保留的长期 `hg outgoing -q` PID `377959` 仍为 0 CPU，不占 WS-23 仿真入口。

## 3. 已完成工作

- 重读项目远程工作流、baseline/dataflow 审计和交接技能，核对本地 Git、原始结果与固定源码日志生产点。
- 不依赖原验收器输出，重新计算两格 metadata、配置快照、raw FCT 和主日志的哈希；从原始日志逐条统计丢包、门控触发、暂停/恢复、延期、超时恢复和 QP 完成；从资源样本重算 RSS 峰值与阈值。独立复算通过，详见[自然语言报告](../research/ws23-deferral-v2-correctness-report.md)。
- 独立核对输入为 16 条、两类各 8 条；两格各 16 条 FCT 和 QP 收据；目标流完成晚于恢复，三次超时恢复均落在对应源端非暂停状态。
- 修正机器证据中 probe `config.log` SHA-256 的单字符抄写错误；仿真 raw、机制代码和验收断言没有修改。
- 只读检查独立 PFC=0 四格：固定候选源码 `154f537ec345df75fbb404a1674436535f92735b` 是当前 WS-23 分支祖先，两份 Git 输入哈希 `8b11ba4bbc5fac248b1983e4070e818cb3ad3658ebaae6d9eb878b3999b76b83` / `379e0c87cb0c26690d438287468dbc9159054f82445e6be46d0324165d639863` 与协议相同，拓扑哈希相同，`scripts/verify_ws23_crossclass.py` 在该 SHA 存在，四个预留 ID 本地与远端当时均空闲。该 SHA 的 worker 与远端已部署版的静态差异只增加可选 v2 PFC 探针参数；四格默认不启用探针。没有构建或运行四格。

## 4. 已形成的设计决策

- 将 v2 双格正确性子项视为**固定输入技术验证通过**；原始日志独立复核支持该判定。FCT 哈希用于身份与时序核验，不用于声称探针带来性能收益。
- WS-23 共享远端入口在确认无仿真/构建作业和无在途依赖后释放，由 Integration 协调 WS-24 与后续 WS-23 作业的顺序；本地 WS-23 与 WS-24 checkout 保持独立，不改 WS-24 源码或 worker。
- B 节四格已具备可检查的固定源码、输入和验收脚本，但 optimized C++ 构建、单测、诊断开关等价及逐格资源/因果验收尚未做。启动前必须重新核对共享入口、worker、资源、ID 和 Luna High 监督；本次只读核验不替代这些门槛。

## 5. 当前状态

- Sol High 的 v2 原始数据独立复核通过；[Handoff 54](2026-10-01-54-ws23-rto-v2-correctness-results.md)所述“待 Sol 复核”为当时历史状态，以本 Handoff 的后续事实为准。
- 观察时 WS-23 checkout 为 `feature/ws23-validation-execution@812586eae32a744aba7db0423c146464d857868f`；本次文档/证据修正待提交。固定仿真 SHA 和两个终态实验 ID 不变。
- WS-23 仍 ACTIVE。PFC=0 共享出口因果四格、隔离候选与同输入 ECMP 的双侧验证、最终代码/效果/结论逐项对应仍未完成。WS-24 的 14 格冻结计划独立，须由 Integration 协调远端执行顺序。

## 6. 未解决问题

- 四格候选 `154f537…` 的 C++ optimized 构建、`devices-point-to-point` 单测、资源观察器与四个端到端格均未执行。背景诊断关/开 FCT 字节等价必须先通过，才运行混合两格；共同出口争用的三个预设方向须由 raw 验证。
- 即使四格成立，也只建立此受控合成输入的跨类影响前提。隔离候选的双侧验证、独立需求及业务界限仍为原始目标的一部分；不能由本轮 v2 通过或四格技术小样替代。

## 7. 后续推荐动作

1. Integration 按当前无在途作业的收据协调共享远端入口；WS-24 的固定 14 格与 WS-23 跨类四格各保留独立 checkout、SHA、输入及 ID。
2. WS-23 下次执行前重新核对 PFC=0 四格候选 SHA、两份输入/拓扑哈希、四 ID、远端 worker 和资源；实际切至 Luna High 后先做 optimized 构建与单测，再按[独立四格协议](../research/ws23-next-correctness-and-causal-preflight.md#b-共享可改道出口因果技术小样四格)逐格运行。背景关/开 pair 不等价即停止并保留 raw。
3. 四格数据回传后实际切 Sol High 核验共同出口争用及背景影响；若因果前提成立，再按事前双侧门槛完成隔离候选验证。所有必做项完成前保持 WS-23 ACTIVE。

## 8. 与其他工作流的关系

本轮只改 WS-23 结果索引和交接文档。WS-24 的多 NIC 固定源码、合成输入、14 格验收和当前 checkout 不受本次修改；后续资源顺序由 Integration 决定。历史 WS-10/11/12/19/20 的 no-go 不因 v2 正确性复核重判。

## 9. CONTEXT SNAPSHOT

WS-23 v2 在固定源码 `94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1` 上的 control/probe 两格 `20261001-151000-ws23-rto-v2-control-r2` / `20261001-151100-ws23-rto-v2-probe-r2` 均 16/16 完成。实际 GPT-6 Sol High 独立复核了 trace/拓扑/FCT/日志哈希、161 次丢包及源 14 的 36 次、1599 次刷新、4+1 次延期、恢复后完整 320 µs RTO、16 QP 守恒和正 RSS 资源收据；只修正机器证据里一处日志哈希抄写。远端 2026-10-01 09:31 无仿真/编译/登录用户，WS-23 共享入口释放。跨类 PFC=0 四格固定 `154f537ec345df75fbb404a1674436535f92735b`、两份输入和四 ID 当时静态核验可用，但 C++ 未构建、四格未运行；随后隔离候选双侧验证亦必做。WS-23 继续 ACTIVE。证据入口：[结果报告](../research/ws23-deferral-v2-correctness-report.md)、[机器证据](../research/evidence/ws23-deferral-v2-20261001.json)、[必做清单](../project-state/WS23_WS24_VALIDATION_PLAN.md)。
