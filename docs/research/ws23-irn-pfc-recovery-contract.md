# WS-23：IRN×PFC 超时恢复契约与正确性门槛

2026-10-01 执行更新：最终两格仿真源码为 `70bf890d1ceba58c5ebd26b17e492295b34c99ca`，无损暂停 1/1、压力与资源补验各 16/16，逐流/字节/真实丢包恢复核验通过，见[两格预飞行执行状态](ws23-two-cell-preflight.md)及[机器证据](evidence/ws23-two-cell-correctness-20261001.json)。两格延期事件均为 0，端到端动态延期和原跨类因果验证仍未完成；新技术协议见[下一批预飞行](ws23-next-correctness-and-causal-preflight.md)。以下早期阶段的“未构建/未仿真”句子是历史记录，不代表当前状态。WS-23 继续 ACTIVE。

2026-09-30 接续：旧修复 `12dea54d…` 的构建与单测门槛已通过；现已冻结新源码 `f8f6afdb2d93c693e32c60bb80cc5e5cf46a5c6b` 的两格端到端正确性[预飞行协议](ws23-two-cell-preflight.md)，包含真实 pause/resume 注入、固定 ID、哈希、验收器和资源停止条件。下文“尚未构建”和“未来冻结”仅记述初版契约形成时的历史状态，不代表本接续阶段；新源码尚无构建或仿真结果，WS-23 仍未闭环。

日期：2026-09-30。分支 `feature/ws23-irn-pfc-recovery`。本阶段只修复和审查传输正确性；隔离机制性能实验仍 NO-GO。当前代码从 `feature/ws22-reorder-budget@59c1c8e53742b4d534d00c7016ff6c3f09105d6c` 分出，修复源码固定提交为 `12dea54d421243ddb98c83437b929944ab6d128c`；后续状态提交不改变该源码 SHA。本阶段未启动远程编译或仿真。

## 故障模型与原始证据

- WS-13 常规 256 条 8 KiB MoE + 64 条 8 MiB 背景四格固定仿真 SHA `babd1b90d7c027cd09ac8c7d67380511a92883a6`。IRN/PFC=11 的 `20260927-214400-irnpfc-11` 为 320/320 完成，PFC pause 0；它没有覆盖暂停或丢包恢复，不能证明 PFC=0 跨类阻塞。
- 固定 16×1 MiB 压力输入 SHA-256 `bc2db1513cbde20f12eea6efa4e2265cf74954be4fa45f2a147ff0ce84b33985`、拓扑 SHA-256 `dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad`、seed=1、ECMP/DCQCN、100G、1 MiB buffer。旧 11 格 `20260927-215700-irnpfcstress-11` 的 tag=1 为 7/8、tag=2 为 6/8，共 13/16 完成；23,295 次 PFC pause，3 次超时被抑制。旧 worker 的 `SUCCEEDED` 仅检查 FCT 非空，不是完成性判据。
- 只观测探针 `20260927-223000-irnpfcdrop-11@7af917af2743529882c3d8524d08114e4677b3ed` 与旧 11 格 FCT 逐字节相同，161 次出口准入拒绝；未完成流 13/14/15 的 `snd_una` 均能对应此前丢失的同序号数据包。上述计数已在本阶段从原始 ID 重新运行 `analyze_irn_pfc_factorial.py` 和 `analyze_irn_pfc_drop_probe.py` 核对。

源码链路：`SwitchNode::DoSwitchSend` 的出口准入失败直接丢包，PFC 开启不保证零丢包；`QbbNetDevice::Receive` 对优先级维护 `m_paused[]`，发送调度器按该状态停发；`RdmaHw::PktSent` 为数据包设 RTO，`ReceiveAck` 更新累计 ACK/SACK 并可走 NACK 恢复，`RdmaQueuePair::GetBytesLeft` 跳过已 SACK 的区间。旧 `HandleTimeout` 用 `IsQbbEnabled()` 判断，第一次 IRN+PFC RTO 无条件返回且不再安排计时器。该谓词只是配置位，不能代表正在暂停。

## 本分支的恢复契约

1. QP 完成或无在途未确认字节时，RTO 不恢复。正常 ACK/SACK/NACK 路径保持原有优先级；收到反馈会重置计时器，SACK 区间继续由既有发送队列跳过。
2. 仅在**源 NIC 对该 PG 实际处于 PFC 暂停**时，把 RTO 重新排至一个完整 RTO 后；不在本地暂停期执行 `RecoverQueue` 或 `TriggerTransmit`。
3. 每次本地 PG resume 后，至少再等待一个完整 RTO；其间 ACK 可取消或重置计时器。若到期仍有在途未确认字节且 PG 未暂停，则将本轮恢复边界设为原 `snd_nxt`，回退发送游标到 `snd_una`，按已有 SACK 选择重传。
4. `IsQbbEnabled()` 仅用于选择上述与 PFC 组合时的定时策略，不能单独禁止恢复。持续、反复的真实暂停会延长恢复；网络中间设备的暂停不一定反映到源 NIC，本补丁无法据此辨识所有虚假 RTO。`454/1350 µs` 沿用现有 IRN RTO 档，未声称是适合所有 PFC 网络的参数。

IRN 原论文将选择性重传、ACK/SACK 与 RTO 作为失包恢复机制，也在比较中单列 IRN+PFC；它**没有直接规定**本仓库混用时的“resume 后完整 RTO”规则。该规则是针对本仿真器可见的源 PG 暂停状态而提出的保守实现假设，必须用下面的正确性测试证伪或支持：[Mittal 等，Revisiting Network Support for RDMA，§3、§4、§6](https://arxiv.org/html/1806.08159)。

## 固定验证与停止条件

本地 `devices-point-to-point` 新单测覆盖四个策略分支：PFC 已启用但从未暂停、RTO 时实际暂停、resume 后观察期、观察期届满。未来隔离构建必须编译该套件并通过；仅源码检查或 Python 解析不代替 C++ 测试。当前 Windows 无 C++ 编译器、只有 `docker-desktop` WSL 发行版，本阶段不能本地构建 ns-3。后续若安排构建，须用**本分支固定提交 SHA** 创建独立源码与结果目录，运行 optimized 构建及测试套件；不可复用旧仿真源码副本。构建不是仿真。

只有构建/单测通过后，才可另行冻结并批准最小正确性仿真：使用上文固定 16×1 MiB trace/拓扑、同 seed/参数新建一个 11 格 ID；再加一个可控的本地暂停但不丢数据/ACK 的小格，覆盖无损情况下不误重传。每格须事先记录 SHA、输入哈希、seed、资源与停止时间，独立目录，服务器资源门槛及长时监督规则照 `docs/REMOTE_EXPERIMENT_WORKFLOW.md` 执行。不得直接续跑旧 ID 或把新旧完成流 FCT 排名。

压力格门槛由 `python scripts/verify_ws23_recovery.py <新实验ID>` 执行：输入/拓扑/seed/参数与旧 11 格相同、源码 SHA 不同；两类均 8/8 完成，16 个唯一 QP 完成收据均显示 `snd_una=snd_nxt=size=1 MiB`、发送 payload 字节不少于 size；确有超时恢复且所有该恢复日志 `local_paused=0`，所有延期均安排正时长未来事件。无损暂停格应有 pause/resume 动态覆盖、全部流完成、无丢包、每 QP `tx_payload_bytes=size`、无真实重传及暂停期恢复。任何一项失败，保留原始结果并停止正确性门槛；先诊断协议，再讨论新的机制或性能输入。完成后还要核对原始 FCT/日志哈希、实验元数据与运行器状态，避免“非空 FCT=成功”的旧陷阱。

上述门槛只检验这个固定反例及一个无损暂停例，不证明所有拥塞/链路故障条件的可靠性；接收端累计 ACK 与发送端完成收据支持连续序号到 size，但没有真实 RNIC 或硬件验证。PFC=0 跨类阻塞的因果证据仍缺失，WS-23 隔离性能协议与矩阵继续关闭。
