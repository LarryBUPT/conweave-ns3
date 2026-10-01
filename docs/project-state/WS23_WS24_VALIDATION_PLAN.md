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

**资源收据纠正（2026-10-02）：**首版 SHA `166ca670…` 的 j01 fixed_single ID `20261002-180000-ws24-ind-j01-fs` 已有动态逐流正确性 raw，但未启动观察器，缺少资源收据，故不计新 pilot 或 48 格矩阵。保留其结果；修复版 SHA `3b992ee` 自动启动 5 秒观察器并将该臂映射到新 ID `20261002-180000-ws24-ind-j01-fs-r2`。余下 47 个 ID 未运行。详见[纠正交接](../handoffs/2026-10-02-54-ws24-resource-watch-correction.md)。

**2026-10-02 范围决定：**用户明确决定“不要真实主机数据，仅NS3模拟”，见 [ADR-009](../decisions/ADR-009-ws24-ns3-only-scope.md)。真实 physical-host/NIC/job/rank 数据不再是 WS-24 验收条件；所有新旧 WS-24 输入与结果只作为 ns-3 合成模拟解释。独立 job 需求下的多 rail × placement 效果验收仍为必做，按[冻结协议](../research/ws24-independent-synthetic-effects-protocol.md)执行，未完成前状态保持 ACTIVE。

**2026-10-02 Sol High 复核：WS-24 仍 ACTIVE。**结果 ID `20261002-142000-ws24-point-to-point-unit-r2` 的隔离源码与 metadata 均为固定实验 SHA `b1184d6a7bd38577b235b7f119f920973308774f`；个人 origin 同名分支当时 HEAD 为文档提交 `3f04f32…`，包含该实验提交。显式启用测试构建及 `devices-point-to-point` suite 均退出 0，5 条 PASS、0 条 FAIL。193 点资源收据未越界，临时 helper 已恢复并核对 blob/SHA-256；16 个远端/本地回传文件哈希相同。runner 列表退出码字段在 summary 中为 null；驱动在非零时会终止，suite 随后成功执行，故仅凭控制流确认列表步骤成功。14 格 raw 重算与机器摘要逐项相同。完整证据见[补验协议](../research/ws24-point-to-point-unit-protocol.md)和 [Handoff 52](../handoffs/2026-10-02-52-ws24-sol-review.md)。

- [x] 在共同固定 SHA 的独立隔离副本显式启用测试、编译并运行 `devices-point-to-point`；回传 runner、资源和临时 helper 恢复收据，核对通过后关闭此单测项。2026-10-02 ID `20261002-142000-ws24-point-to-point-unit-r2`：构建/测试退出码 0，5 条 PASS、0 条 FAIL，固定 SHA `b1184d6…`，恢复哈希与资源收据通过。14 格 optimized build 不计单测。**仅完成本项；WS-24 其他合成验证范围与真实部署/确认性性能限制见下方，不据此归档整个 WS。**

执行对话：`01a0f1da-f1e2-7870-9361-24b4d626fd76`。依据 [表示能力审计](../research/ws24-multirail-representability-audit.md) 与 [v2 最小格预飞行/结果](../research/ws24-minimal-multinic-preflight.md)。**状态仍 ACTIVE。**较早的 v2 最小格源码为 `824e3fa0c4c06dd9894474a81e729931d59a3108`：正例 `20261001-100000-ws24-minimal-v2` 成功，跨 rail 负例 `20261001-100100-ws24-crossrail-reject-v2` 在解析阶段按预期失败。后续 A/B/C/D 共同源码为 `b1184d6a7bd38577b235b7f119f920973308774f`；其 14 格验收见下列条目。

- [x] 追查导入拓扑/生成器来源，明确真实 host/NIC/job 映射可获得程度；不能从相邻节点号推断物理共享。[审计报告](../research/ws24-multirail-representability-audit.md)与[工作记录](../research/ws24-multinic-v0-worklog.md)确认导入图可追至合成生成器，但无真实服务器多 NIC 或 job placement 证据。
- [x] 建立明确标注为合成、可复现的受控 host/NIC/rail/job/rank/流映射，用于工程正确性与受控机制研究；记录资源共享假设与适用边界。真实部署主张仍须真实来源。
- [x] 实现一台合成 host Node 对应四 NIC/独立 IP，并完成两主机四 rail 的同 rail 双向 QP/ACK、输入身份及连续字节守恒；最小拓扑 raw 核验通过。具体结果为 4/4 流、32,768 B、max RTT 440 ns、derived IRN BDP 22,000 B。**仍未覆盖：动态 CNP flag 接收分支、320-host 目标拓扑运行、旧格式四 baseline 回归。**
- [x] 冻结并执行最小正例和跨 rail 拒错负例，核对 host/NIC/rank/flow、唯一接收/确认、FCT 对应与资源收据；正例逐流验收通过，负例在 `WS24 invalid flow row 2` 拒绝且无 FLOW_START/FCT。见两实验 ID 与 SHA 固定的[预飞行结果](../research/ws24-minimal-multinic-preflight.md)。
- [x] 本地冻结旧五列/六列四 baseline 回归契约：固定 OS2 输入哈希、四 LB_MODE、旧 1000 ns 时延及逐格输出验收。见[后续冻结协议 A](../research/ws24-followup-validation-protocols.md)。
- [x] 从个人 fork 的四份 WS-06 历史 raw 只读重算完整 FCT 哈希，保存逐字节回归锚点于 `docs/research/evidence/ws24-legacy-reference-fct-sha.json`。
- [x] 在共同固定 SHA `b1184d6a7bd38577b235b7f119f920973308774f` 上执行上述 8 格，旧格式输入与动态输出均按契约逐格验收。2026-10-01 八格均 `SUCCEEDED` 并通过 `verify_ws24_legacy.py`；五列四算法 FCT SHA 与历史参考一致，六列每格 4/4、tag 1/2 各 2。
- [x] 本地审查并冻结 320-host 目标拓扑正确性格：1280 NIC、四 rail、运行时 RTT/BDP 600 ns/30,000 B 和逐流身份守恒。见[后续冻结协议 B](../research/ws24-followup-validation-protocols.md)。
- [x] Integration 确认 WS-23 无在途远程作业、共享 worker 无切换冲突且资源门槛通过后，协调执行目标拓扑 correctness；真实运行日志须实证 600/30,000，不能以离线值代替。WS-23 五格全部成功不是这项独立回归的机械前置条件。2026-10-01 `20261002-110000-ws24-target-320host-correctness` 10/10、2,408,448 B，运行时 600 ns/30,000 B 与 NIC/route 身份通过。
- [x] 本地设计并冻结可触发的动态 CNP 正确性格和最小接收/发送端状态观测要求。新增四源同 rail incast 合成输入；见[后续冻结协议 C](../research/ws24-followup-validation-protocols.md)。
- [x] 本地加入仅 WS-24 启用、每 QP 受限的 CNP 生成/源 NIC 接收/DCQCN rate-decrease 观测及事件关联验收器；固定 SHA 已远端编译，C 格 raw 关联 flag、源端接收、pending 与真实降速事件，动态正确性通过。
- [x] 以共同固定 SHA `b1184d6…` /独立 ID 执行 CNP 格；验证 ACK/NACK flag 返回指定源 NIC、pending 生效和流完成前实际降速。无事件不得宣称 CNP 已验证。2026-10-01 `20261002-120000-ws24-cnp-incast-correctness` 4/4、4,194,304 B，验收器关联 7 组 flag/receive/rate-decrease 事件。
- [x] 本地冻结原多 rail/placement 目标的四臂协议：相同逻辑流与总字节，对照单/多 rail 与固定/可变放置；manifest 逐文件哈希及逐臂验收见[后续冻结协议 D](../research/ws24-followup-validation-protocols.md)。
- [x] 先通过目标拓扑 correctness，再由 Integration 按共享入口实际空闲情况协调执行四臂 synthetic pilot。禁止以静态审计替代机制验证；任何范围缩减仍需用户明确决定。2026-10-01 四臂均 10/10、2,408,448 B、身份与逻辑需求配对通过；结果仅为单 seed 描述性 pilot。
- [x] 14 格终态 raw、固定仿真源码及该批效果结论一致。2026-10-01 14/14 raw/resources fetched，`verify_ws24_matrix.py` 全矩阵通过；2026-10-02 Sol High 独立重算 JSON 与机器摘要逐项相同。Handoff 50 记录该批结论与证据边界。真实部署映射和确认性性能结论没有被宣称；同 SHA 单测补验见本节首项。

- [x] 按用户明确决定将 WS-24 限定为 ns-3 合成模拟；真实映射来源不再是闭环条件。现有 OS1 图只能追至合成生成器，任何结果均不得推断真实物理共享或生产性能。见 [ADR-009](../decisions/ADR-009-ws24-ns3-only-scope.md)。
- [x] 冻结 12 个独立生成 key 的合成 job 需求块、每块四臂共 48 个输入、共同源码 `166ca6709e2b6ea8b60978bf80778fee636937e5`、manifest/输入哈希、双侧指标和停止条件。本地逐字节再生成及静态验收通过；见[独立需求协议](../research/ws24-independent-synthetic-effects-protocol.md)。此项不代表新矩阵已运行。
- [ ] `j01` 四臂动态正确性与资源 pilot：先实际切至 Luna High，重查远端无人/作业/资源/ID，部署隔离的 `ws24_worker.py`；四格独立 build/run/fetch/raw 验收，30/30、身份和字节守恒及运行时 RTT/BDP 均须通过。失败格保留原始数据并修复重验。
- [ ] 完成其余 11 个独立合成 job 的 44 格四臂矩阵，保存每格固定 SHA、输入哈希、seed、metadata、raw 与资源收据；全部终态格从 raw 重算，按 job 为单位做事前双侧分析并记录反例。旧单 seed 四臂 pilot 的 −173/−164 ns 仅作描述，不并入 12 个重复。终态回传后实际切回 Sol High，核对代码、效果与结论，再决定 WS-24 是否闭环。

14 格验收入口为 `scripts/verify_ws24_legacy.py`、`scripts/verify_ws24_result.py` 和 `scripts/verify_ws24_matrix.py`；矩阵入口要求四模式历史完整 FCT 哈希。2026-10-01 冻结批次 14/14 全部运行、raw/resources 已 fetch 并通过验收，摘要见 `docs/research/evidence/ws24-followup-validation-summary.json`。四臂仅单 seed 合成描述性 pilot，不支持一般性能收益。新 48 格使用独立协议与验收脚本，不覆盖旧 raw。

## 执行协调与 WS-25

WS-24 使用独立 checkout `workspace/ws24-multinic-validation`。2026-10-01 的[后续协议](../research/ws24-followup-validation-protocols.md)和[Handoff 49](../handoffs/2026-10-01-49-ws24-followup-protocol-freeze.md)固定 14 格共同源码 `b1184d6a7bd38577b235b7f119f920973308774f`、输入及当时的远程入口；这些预飞行记录只描述启动前状态。14 格随后完成并由[Handoff 50](../handoffs/2026-10-01-50-ws24-frozen-validation.md)收据化，本次又由 [Handoff 52](../handoffs/2026-10-02-52-ws24-sol-review.md)从 raw 重算和补齐同 SHA 单测。WS-23 的远程作业仍须在未来 WS-24 实验入口单独协调，不机械等待其全部成功。

每次仿真前先冻结协议与收据并停在模型切换边界，监督对话实际切至 Luna High，再执行后台静默实验，约半小时精简监督；终态 raw 回传后实际切回 Sol High 分析和必要修正。不得用文字宣称模型切换。

WS-25 负责证据总账、必要主张和论文说明，必须跟踪本表完成状态及具体执行对话；它不能替代实验验收，也不能默默把必做验证变成可选事项。先前 Handoff 45 的闭环与归档决定已撤销；历史工程证据仍保留。
