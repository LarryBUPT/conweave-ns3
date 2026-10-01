# Handoff 54：WS-23 延期 v2 双格正确性通过

日期：2026-10-01。证据类别：固定合成输入上的端到端正确性验证；不是性能实验或性能收益证据。

## 1. 本对话目标

接续 WS-23 v2：修正失败 control 的隔离构建流程，按“无探针对照先通过，再运行定向探针”执行两个端到端格，并检查 raw 是否覆盖真实 PFC 暂停、超时延期和最终恢复。

## 2. 已确认的项目事实

- 两格固定源码/验收器 SHA：`94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1`，分支 `feature/ws23-validation-execution`。
- 固定输入：trace `config/ws09_drop_probe_16x1MiB.txt`，SHA-256 `bc2db1513cbde20f12eea6efa4e2265cf74954be4fa45f2a147ff0ce84b33985`；拓扑 `config/fat_k4_100G_OS2.txt`，SHA-256 `dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad`；seed 1，ECMP，PFC=1、IRN=1、100G、1 MiB buffer、负载 10、仿真时长 0.01。
- control `20261001-151000-ws23-rto-v2-control-r2`：`SUCCEEDED`，16/16 完成，161 次准入丢包、源 14 有 36 次；FCT SHA-256 `97feb0e118544f07e006da9e9bc2ead2566a10b91ad2201e0e83ced89279b18a`，通过 `pressure` 验收。
- probe `20261001-151100-ws23-rto-v2-probe-r2`：`SUCCEEDED`，16/16 完成、两类各 8/8；探针前丢包与 control 逐行相同；只触发一次门控暂停且目标 QP 有未确认数据；主机 14/PG 3 收到 pause/resume；暂停刷新 1599 次；暂停期延期 4 次，恢复宽限期延期 1 次；完整 RTO 为 320,000 ns，目标于 `2009121003 ns` 恢复；仿真停止时刻 `2017100000 ns`；无其他队列/链路丢包；16 个 QP 均序号/字节守恒。`deferral-v2` 验收通过。
- control/probe raw FCT SHA 分别为对照固定值及 `86ea6fc3275f08169c6b539ae2c2a534d29bb95ed31866832c9eee5322550ef0`。所有逐项数值、资源收据和结果路径见[机器证据](../research/evidence/ws23-deferral-v2-20261001.json)；人类可读总结见[结果报告](../research/ws23-deferral-v2-correctness-report.md)。
- 两格资源观察器分别有 10/11 个运行期正 RSS 样本；峰值 204.26/204.39 MiB，最低可用内存 122.82/122.82 GiB、最低空闲磁盘 5656.93/5655.88 GiB、最高采样负载 1.44/1.60。原始数据保存在个人 fork 忽略目录 `results/<experiment-id>/`，未加入 Git。

## 3. 已完成工作

- 按[Handoff 53](2026-10-01-53-ws23-rto-v2-control-build-failure.md)的修复约束提交并推送文档状态更新，commit `97317c05bc6fe212c4861ec55424d2291afea9cc`；远端 GitHub fetch 超时后，遵照工作流只运行一次静默 `login.sh`，仍失败，再使用本机已验证的个人 fork Git bundle 经 SSH 同步成功。
- 远端部署 worker SHA `9e1b4e144d5584e8999d2c560bf4577b249ca73421d9aac6c53e5a96a798766e` 与本地一致，含 v2 探针参数。资源/在途作业与 ID 核对通过；此前用户确认保留的长期 `hg outgoing -q` 未终止。
- 两个 r2 ID 分别从固定 SHA 新建 optimized 副本，以 `-j2` 编译。每格运行前独立观察器都先记录 `READY`；每格均完成后核验正 RSS 收据，再安全 fetch 回本机。
- 运行 `scripts/verify_ws23_recovery.py --scenario pressure` 和 `--scenario deferral-v2`，均退出码 0。人工复查了 probe 的准入丢包、源端 PFC、延期、恢复及 RTO 相关日志；验收断言和原始数据一致。
- 追加机器证据、自然语言报告与本 Handoff，并准备更新状态索引和必做清单。

## 4. 已形成的设计决策

- 首次失败 ID `20261001-150000-ws23-rto-v2-control` 与未运行的旧 probe ID 永久保留，重试用 r2 ID；首次失败来自测试配置污染并触发已知测试 helper 编译缺陷，不是机制结果。
- 仅在 control 准确复现压力数据后运行 probe；这个前置门槛已满足。
- **结论边界：**仅确认该固定合成压力输入上的恢复契约工作正常。两格 FCT 不用于宣称性能变化；本验证不证明普遍无损、跨类流隔离或真实部署效果。

## 5. 当前状态

- 本次观察时源码仍固定为 `94f08c6…`；结果文档待提交。原始结果与资源收据已下载且未纳入版本控制。
- v2 双格技术正确性验收已通过。WS-23 整体仍 ACTIVE：PFC=0 跨类因果四格、隔离候选双侧验证和最终源码/效果/结论对应检查尚未完成。
- 项目规定终态后切换 GPT-6 Sol High。当前会话可用工具中没有实际模型切换接口，所以这次尚未完成 Sol High 独立原始数据复核；不能把当前验收器结果表述为该模型复核已完成。

## 6. 未解决问题

- 用 GPT-6 Sol High 对照验收脚本独立复核两份 metadata、配置快照、raw 事件和资源收据。
- 独立执行跨类 PFC=0 因果四格，按原观测等价与资源门槛判断共同出口竞争是否成立。
- 若跨类门槛支持继续，实施隔离候选并完成与 ECMP 的双侧验证；最后逐项核对代码、实验、原始效果与结论。此两格不会替代这些工作。

## 7. 后续推荐动作

1. 具备模型切换接口后，实际切到 GPT-6 Sol High，先复核两格原始文件和机器证据 JSON 的哈希/计数/事件时序，必要时修正报告，不改弱验收条件。
2. 按 `docs/project-state/WS23_WS24_VALIDATION_PLAN.md` 启动跨类四格的独立源码构建、运行和逐格验收。
3. 根据四格数据决定隔离候选验证的可执行路径；按既有双侧门槛完成，而非把 no-go 当作取消验证。
4. 只有全部预设项通过或得到用户明确范围决定后，才能闭环 WS-23。

## 8. 与其他工作流的关系

WS-23 与 WS-24 共用远端 worker；此次执行前已核对共享入口和资源。WS-24 的固定代码、输入和多 NIC 门槛不因这次双格结果变化，也没有由此自动启动 WS-24 格。项目历史性能 no-go、WS-21/22结论均不重判。

## 9. CONTEXT SNAPSHOT

WS-23 v2 的 control/probe 已在固定源码 `94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1` 上完成：control `20261001-151000-ws23-rto-v2-control-r2` 重现 16/16、161 次准入丢包、目标源 14 的 36 次丢包及 FCT SHA `97feb0…79b18a`；probe `20261001-151100-ws23-rto-v2-probe-r2` 通过双格验收，1599 次刷新，4 次暂停延期、1 次恢复宽限延期，完整 320 µs RTO 后恢复，16 QP 守恒。详细数据和资源收据在 `docs/research/evidence/ws23-deferral-v2-20261001.json`；自然语言总结在 `docs/research/ws23-deferral-v2-correctness-report.md`。结果属固定合成输入正确性，不是性能或真实部署证据。当前会话无 Sol High 模型切换工具，独立复核待处理。WS-23 仍 ACTIVE：跨类 PFC=0 因果四格与隔离候选双侧验证未完成；见必做清单 `docs/project-state/WS23_WS24_VALIDATION_PLAN.md`。
