# Handoff 44：WS-24 多 rail 与作业放置可表示性审计

1. **本对话目标：** 承接“ConWeave Research · Integration”（来源 task `01a0cfac-3176-7590-bf34-c0f176a45118`）的 WS-24；在 `feature/ws24-multirail-input`、父提交 `7dfacee3a968073c5c80d5bb3c315a6557b980e3` 上做本地可表示性审计，明确同一物理 host 多 NIC、流到 rail 和 job placement 的门槛。用户明确要求门槛缺失时远程仿真 NO-GO，并同步 WS-23 修复状态。

2. **已确认的项目事实：** 固定 OS1 拓扑 SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`，有四个互不连通组件，每组 464 节点及 320 个度 1 的 host 端点；WS-17 生成器只选 `ID mod 4 = 0`。`scratch/network-load-balance.cc` 当前为每端点建独立 Node/RDMA Hw，以接口 1 的唯一主机 IP 建目的路由，五/六列流输入没有 job/rank/rail/physical host。`RdmaHw::m_nic` 可存多设备，但当前 scratch 没将四端点合为一个物理主机。详见[审计](../research/ws24-multirail-representability-audit.md)。NCCL 官方文档把 NIC、rail 和设备分配作为显式身份；它仅供抽象对照，不能替代本仓库实现证据。

3. **已完成工作：** 阅读项目远程工作流、baseline fidelity 审计、状态技能与前序 Handoff，核对当前 Git 分支及源码。新增[`scripts/audit_ws24_multirail.py`](../../scripts/audit_ws24_multirail.py)和[静态收据](../research/evidence/ws24-multirail-static-audit.json)：逐边核算组件；以明示为合成的四端点/物理 host 假设样例解析一个两 rank job 的四条同 rail 流；检查重复端点、未知 rank、异 rail 绑定被拒。写出数据契约、实现次序与停止条件，并更新 `CURRENT_STATE.md`、`WORKSTREAMS.md`、`ROADMAP.md`、`WS17_PLUS_PLAN.md`。脚本本地执行通过；没有编译或运行 ns-3、没有新实验 ID 或 raw。

4. **已形成的设计决策：** **WS-24 remote simulation NO-GO**。理由是拓扑分区不能证明物理主机共享、现有输入没有 job placement，当前 simulator 路径也未验证多 NIC QP。拒绝把 `node_id // 4` 直接当真实主机 ID、把不同 rail 网络错误地称为可直连、或用合成 sidecar 报告吞吐收益。保留旧 trace 格式与四 baseline；若日后有可信来源，先引入可审计 sidecar，再实现多 NIC 主机、显式 IP/路由和流绑定，最后做最小正确性格。

5. **当前状态：** 2026-09-30，WS-24 **COMPLETE FOR LOCAL REPRESENTABILITY AUDIT; REMOTE SIMULATION NO-GO**。分支 `feature/ws24-multirail-input`；本阶段仅新增审计脚本、静态收据、报告、Handoff 和状态文档。WS-23 固定修复 SHA `12dea54d421243ddb98c83437b929944ab6d128c` 仍只有隔离 optimized build 与 `devices-point-to-point` 单测通过（见[Handoff 43](2026-09-30-43-ws23-build-unit-ws24-topology-gate.md)），没有修复版端到端仿真；恢复正确性待验证，隔离性能实验 NO-GO。

6. **未解决问题：** **必须先解决**物理 host→NIC/rail 的可信来源、作业 rank→host placement 和独立需求来源、src/dst NIC 与双向 QP/ACK/CNP 绑定及 simulator 多 NIC 端到端正确性。**可后置**效果协议、固定/可变 placement 强对照、背景代价与资源共享建模，但在这些完成前不进入远程性能阶段。真实训练 job 数据、业务 SLO 与跨 rail 主机侧转发模型均不存在于现有输入。

7. **后续推荐动作：** 先向数据/拓扑来源核对四端点是否确属同一物理服务器，并取得 rank/作业放置记录；若无，则保持条件性 no-go。若有，按[审计契约](../research/ws24-multirail-representability-audit.md)冻结拓扑、映射、需求 seed 与哈希；在新分支实现共享 host 多 NIC 和显式流/返回路径，先做本地结构及最小端到端正确性，再决定是否需要资源 pilot 和双侧探索。若进入长时远程阶段，须实际切换 GPT-6 Luna High 静默监督，终态 raw 回传后实际切回 GPT-6 Sol High 分析；本次未进入该阶段。

8. **与其他工作流的关系：** WS-24 没有重新解释 WS-10/11/12/19/20/21 的单 rail 数据，也不重判 WS-22 的重排 NO-GO。WS-23 修复 build/单测不等于其端到端可靠性，不能用于 WS-24 效果。WS-25 继续按实际证据收束论文范围，导师确认的创新与业务场景仍待定；没有自动启动下一任务。

9. **CONTEXT SNAPSHOT：** `feature/ws24-multirail-input` 的本地审计确认 OS1 四个断开的 rail 分区，当前 scratch 是每端点独立 Node/RDMA Hw，trace 缺 job/rank/physical host/rail；底层 NIC vector 不足以证明现有多 NIC 主机。合成 sidecar 静态正反例通过，但无真实物理或作业来源，因此 WS-24 远程仿真 NO-GO、无新效果数据。入口是[审计报告](../research/ws24-multirail-representability-audit.md)、[静态收据](../research/evidence/ws24-multirail-static-audit.json)及项目状态。WS-23 修复 SHA `12dea54d…` 只过 build/单测，无修复版端到端仿真，性能实验 NO-GO。
