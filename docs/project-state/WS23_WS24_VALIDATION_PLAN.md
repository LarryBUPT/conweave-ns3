# WS-23/24 必做验证执行清单

2026-09-30 用户纠正提前闭环。两个对话恢复执行，必须持续实验、修改、验证，完成全部预设任务后才能闭环。负结果必须经相应预设验证支持；不能通过跳过验证获得 no-go 结论。

## WS-23：先完成传输恢复正确性

执行对话：`01a0f15f-58c7-7532-84bd-9acaaaa14525`。依据 [恢复契约](../research/ws23-irn-pfc-recovery-contract.md)。已过门槛：修复 SHA `12dea54d…` 的 optimized build 与 point-to-point 单测。

- [x] 本地冻结两个正确性格的协议、源码 SHA、输入内容哈希、seed、预留 ID、资源与停止条件；已完善真实无损 pause/resume 输入/注入和验收器。见 [两格预飞行协议](../research/ws23-two-cell-preflight.md)。**该项仅代表本地准备，新的源码尚未远程构建或仿真。**
- [ ] 固定旧 16×1 MiB 反例，验证 16/16、两类 8/8、唯一 QP、序号/字节守恒、实际超时恢复、源 PG 暂停期无恢复及延期事件有效。
- [ ] 真实无损 pause/resume 格，验证暂停/恢复动态覆盖、全流完成、无数据/ACK 丢失、每 QP 发送 payload=size、无误重传和暂停期恢复。
- [ ] 任一失败时保留 raw，定位和修复，重新固定源码并运行独立 ID；全部终态 raw 回传后实际切回 Sol High，核验两格与预设验收项。
- [ ] 原拥塞隔离目标仍留在清单：审计并形成可证伪的跨类阻塞验证条件，确定适配的最小正确性/因果实验；性能比较必须有机制和因果前提。对无法建立的前提记录具体证据与缺口，不能用性能门槛取消上面的修复验证或自行宣布原目标完成。
- [ ] 源码、实验、结果报告和自然语言结论逐项一致；原始目标如需变更，提交用户明确决定。

## WS-24：补齐模型、输入与多网卡验证

执行对话：`01a0f1da-f1e2-7870-9361-24b4d626fd76`。依据 [表示能力审计](../research/ws24-multirail-representability-audit.md) 与 [v2 最小格预飞行/结果](../research/ws24-minimal-multinic-preflight.md)。**状态仍 ACTIVE。**仿真源码固定 `824e3fa0c4c06dd9894474a81e729931d59a3108`：正例 `20261001-100000-ws24-minimal-v2` 成功，跨 rail 负例 `20261001-100100-ws24-crossrail-reject-v2` 在解析阶段按预期失败。证据只覆盖两主机四 rail 合成最小正确性，不构成目标拓扑、旧 baseline 回归、动态 CNP 或效果对照的完成证据。

- [x] 追查导入拓扑/生成器来源，明确真实 host/NIC/job 映射可获得程度；不能从相邻节点号推断物理共享。[审计报告](../research/ws24-multirail-representability-audit.md)与[工作记录](../research/ws24-multinic-v0-worklog.md)确认导入图可追至合成生成器，但无真实服务器多 NIC 或 job placement 证据。
- [x] 建立明确标注为合成、可复现的受控 host/NIC/rail/job/rank/流映射，用于工程正确性与受控机制研究；记录资源共享假设与适用边界。真实部署主张仍须真实来源。
- [x] 实现一台合成 host Node 对应四 NIC/独立 IP，并完成两主机四 rail 的同 rail 双向 QP/ACK、输入身份及连续字节守恒；最小拓扑 raw 核验通过。具体结果为 4/4 流、32,768 B、max RTT 440 ns、derived IRN BDP 22,000 B。**仍未覆盖：动态 CNP flag 接收分支、320-host 目标拓扑运行、旧格式四 baseline 回归。**
- [x] 冻结并执行最小正例和跨 rail 拒错负例，核对 host/NIC/rank/flow、唯一接收/确认、FCT 对应与资源收据；正例逐流验收通过，负例在 `WS24 invalid flow row 2` 拒绝且无 FLOW_START/FCT。见两实验 ID 与 SHA 固定的[预飞行结果](../research/ws24-minimal-multinic-preflight.md)。
- [x] 本地冻结旧五列/六列四 baseline 回归契约：固定 OS2 输入哈希、四 LB_MODE、旧 1000 ns 时延及逐格输出验收。见[后续冻结协议 A](../research/ws24-followup-validation-protocols.md)。
- [x] 从个人 fork 的四份 WS-06 历史 raw 只读重算完整 FCT 哈希，保存逐字节回归锚点于 `docs/research/evidence/ws24-legacy-reference-fct-sha.json`。
- [ ] 在共同固定 SHA `b1184d6a7bd38577b235b7f119f920973308774f` 上执行上述 8 格，旧格式输入与动态输出均按契约逐格验收。
- [x] 本地审查并冻结 320-host 目标拓扑正确性格：1280 NIC、四 rail、运行时 RTT/BDP 600 ns/30,000 B 和逐流身份守恒。见[后续冻结协议 B](../research/ws24-followup-validation-protocols.md)。
- [ ] Integration 确认 WS-23 无在途远程作业、共享 worker 无切换冲突且资源门槛通过后，协调执行目标拓扑 correctness；真实运行日志须实证 600/30,000，不能以离线值代替。WS-23 五格全部成功不是这项独立回归的机械前置条件。
- [x] 本地设计并冻结可触发的动态 CNP 正确性格和最小接收/发送端状态观测要求。新增四源同 rail incast 合成输入；见[后续冻结协议 C](../research/ws24-followup-validation-protocols.md)。
- [x] 本地加入仅 WS-24 启用、每 QP 受限的 CNP 生成/源 NIC 接收/DCQCN rate-decrease 观测及事件关联验收器；尚未编译或远端运行，动态正确性不算通过。
- [ ] 以共同固定 SHA `b1184d6…` /独立 ID 执行 CNP 格；验证 ACK/NACK flag 返回指定源 NIC、pending 生效和流完成前实际降速。无事件不得宣称 CNP 已验证。
- [x] 本地冻结原多 rail/placement 目标的四臂协议：相同逻辑流与总字节，对照单/多 rail 与固定/可变放置；manifest 逐文件哈希及逐臂验收见[后续冻结协议 D](../research/ws24-followup-validation-protocols.md)。
- [ ] 先通过目标拓扑 correctness，再由 Integration 按共享入口实际空闲情况协调执行四臂 synthetic pilot。禁止以静态审计替代机制验证；任何范围缩减仍需用户明确决定。
- [ ] 终态 raw、最终仿真源码及效果结论一致，完成全部预设验收项后再交接闭环。最小格通过不关闭本项。

本地 14 格执行后验收入口为 `scripts/verify_ws24_legacy.py`、`scripts/verify_ws24_result.py` 和 `scripts/verify_ws24_matrix.py`；矩阵入口还要求四模式历史完整 FCT 哈希，不接受只有前缀的摘要。当前只有既有最小 v2 raw 可重验，14 格均未运行。

## 执行协调与 WS-25

WS-24 本批已使用独立 checkout `workspace/ws24-multinic-validation` 完成两格 v2 实验，并在本地冻结后续契约、CNP incast 输入与预留 ID，见[后续协议](../research/ws24-followup-validation-protocols.md)和[Handoff 49](../handoffs/2026-10-01-49-ws24-followup-protocol-freeze.md)。14 格共同仿真源码固定为 `b1184d6a7bd38577b235b7f119f920973308774f`：Git blob 中 11/11 合成文件哈希匹配 manifest，旧输入和 CNP 四类观测均存在；本地与个人 origin 曾核对为同一 SHA。14 格尚未编译或运行。下一批不得自动部署 worker、sync 或启动 WS-24 实验；Integration 在 WS-23 无在途远程作业、共享 worker 无切换冲突且资源门槛通过后协调，不必机械等待 WS-23 五格全部成功。

每次仿真前先冻结协议与收据并停在模型切换边界，监督对话实际切至 Luna High，再执行后台静默实验，约半小时精简监督；终态 raw 回传后实际切回 Sol High 分析和必要修正。不得用文字宣称模型切换。

WS-25 负责证据总账、必要主张和论文说明，必须跟踪本表完成状态及具体执行对话；它不能替代实验验收，也不能默默把必做验证变成可选事项。先前 Handoff 45 的闭环与归档决定已撤销；历史工程证据仍保留。
