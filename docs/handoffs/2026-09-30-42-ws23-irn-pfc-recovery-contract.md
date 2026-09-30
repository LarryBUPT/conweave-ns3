# Handoff 42：WS-23 IRN×PFC 超时恢复契约与本地修复

1. **本对话目标：** 承接“ConWeave Research · Integration”（来源 task `01a0cfac-3176-7590-bf34-c0f176a45118`）的 WS-23 后续任务。用户把阶段明确改为 IRN×PFC 超时恢复契约与正确性修复，不重复前置门槛审查；禁止在未冻结新协议前运行远程仿真。所属项目为“科研”，本轮工作在个人 fork 的 `feature/ws23-irn-pfc-recovery` 分支。

2. **已确认的项目事实：** 工作流及 baseline 审计先行读取，状态与 Handoff 40/41 只作索引。独立从原始 ID 复算：`20260927-214400-irnpfc-11@babd1b90…` 为 320/320、PFC pause 0；`20260927-215700-irnpfcstress-11@babd1b90…` 为 tag=1 7/8、tag=2 6/8、合计 13/16、23,295 次 pause、3 次超时抑制。`20260927-223000-irnpfcdrop-11@7af917a…` 复算 161 次出口准入丢弃，缺失流 13/14/15 的未确认序号均匹配此前丢包。旧 11 格的 `SUCCEEDED` 元数据只是非空 FCT 旧门禁，不能作完整性或性能证据。详见 [WS-13 原报告](../research/ws13-irn-pfc-factorial-pilot-report.md)。

3. **已完成工作：** 从 `feature/ws22-reorder-budget@59c1c8e53742b4d534d00c7016ff6c3f09105d6c` 建分支，传输补丁及[契约报告](../research/ws23-irn-pfc-recovery-contract.md)提交为 `12dea54d421243ddb98c83437b929944ab6d128c`。追踪 `QbbNetDevice` 的暂停/恢复、`RdmaHw::ReceiveAck/HandleTimeout/PktSent`、`RdmaQueuePair` 的 SACK/游标与 `RecoverQueue`。补丁让 RTO 在源 PG 实际暂停时重排、resume 后留完整 RTO、仍未确认时进入既有重传队列；初始化并设置 RTO recovery 边界，输出 QP 字节/序号完成收据。加入 `devices-point-to-point` 策略单测和 `scripts/verify_ws23_recovery.py` 压力格校验器。

4. **设计决策：** 旧条件 `irn.enabled && dev.IsQbbEnabled()` 只读 PFC 配置，不读暂停状态；一次 RTO 即永久丢失恢复机会。选择按本地 PG 实际暂停延期、resume 后完整 RTO，再由未确认字节和既有 SACK 决定重传。避免直接删除 suppression 后在本地暂停期恢复；也不延续无条件 suppress。IRN 原论文支持选择性重传和 RTO 作为可靠性机制，但此组合规则是本仿真器的可证伪保守假设，不假托为论文原文协议。中间交换机 PFC 不一定传到源 NIC，仍可能造成虚假 RTO。

5. **当前状态与核验：** 本地 `python -m py_compile scripts/verify_ws23_recovery.py` 通过；校验器对历史 13/16 格明确报 `Transport completion gate failed for tag 1`，证明完成数门槛会挡住旧假成功；`git diff --check` 通过。Windows 未发现 C++ 编译器，只发现 `docker-desktop` WSL 发行版，因此本轮**没有 C++ 编译、单测执行、隔离远端 build 或新仿真**。补丁正确性尚未由运行证据证明；没有固定修复版实验 ID 或性能数字。

6. **未解决问题：** 新源码是否在项目 GCC 5.4/optimized Waf 通过，`devices-point-to-point` 是否通过；固定压力输入能否 16/16 完成并满足发送/接收序号守恒；实际 PFC pause/resume 下是否存在虚假重传、重复完成或长期暂停导致延期；中间设备暂停不可见时的策略边界。PFC=0 跨类阻塞因果证据仍缺失，隔离性能门槛仍 NO-GO。

7. **后续动作：** 先以 `12dea54d…` 固定 SHA 在独立远端目录仅 build 和运行单测；若失败先修源码、产生新 SHA，不改旧 ID。通过后另行冻结最小正确性仿真协议、资源/停止条件，分别运行固定 16×1 MiB 压力 11 格与无损但有实际源 PG pause 的小格；用 `verify_ws23_recovery.py` 和原始 FCT/日志/元数据核对 16/16、每 QP `snd_una=snd_nxt=size`、发送 payload 守恒、恢复不在本地暂停期、无损格无重传。未满足任何项即停在正确性修复，不开启效果矩阵。若进入远程仿真，遵守工作流的静默、约半小时监督及实际 Luna High/Sol High 切换。

8. **与其他工作流关系：** WS-23 修复不重判 WS-13 旧四格、WS-10/11/12/19/20/21 no-go，也不把压力技术格作性能排名。WS-24 的 rail 0 输入缺口不变；WS-25 的论文证据收束可并行，但不能把未构建的 WS-23 补丁写成已完成论文贡献。`CURRENT_STATE.md`、`WORKSTREAMS.md`、`ROADMAP.md` 已按本阶段实际状态更新。

9. **CONTEXT SNAPSHOT：** 旧 IRN×PFC 压力 11 格 13/16，出口准入丢包后 RTO 被配置位误抑制；常规 320/320 无 PFC pause。修复源码 `12dea54d…` 已写入个人 fork 本地分支，只有 Python 静态检查和历史失败门禁通过；无 C++ build、新仿真或效果证据。下一门槛是独立 build+单测，再冻结两个最小正确性格；隔离性能实验保持 NO-GO。权威流程在 `docs/REMOTE_EXPERIMENT_WORKFLOW.md`，原始输入/规则在[恢复契约](../research/ws23-irn-pfc-recovery-contract.md)。
