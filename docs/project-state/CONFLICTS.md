# 冲突、过期内容与待核验点

更新：2026-09-26。记录“哪里说法不一致、当前采用什么口径、怎样消除”，不把旧文档直接删除。

| ID | 不一致或风险 | 当前采用的口径 | 后续处理 |
| --- | --- | --- | --- |
| C-01 | 论文项目 `docs/research/README.md`、`06-experiment-plan.md`、`07-ns3-only-feasibility.md` 的历史段落仍说“没有源码/未运行 NS-3”。 | 这些是创建时的历史状态；当前已有个人 fork、远程 smoke 与四模式最小核验。 | **已加状态提醒与当前状态入口**；保留历史计划正文，不覆盖原始实验记录。 |
| C-02 | 初轮报告把 PartialWeave/SemanticsBench/FreshRoute 排前；后续用户将中心明确为包/流混合负载均衡。 | 采用 `08-mixed-granularity-discovery.md` 与较新的 `11-mixhash-inspired-lb-only-discovery.md` 排序；旧方向作为历史/备选。 | 在研究索引中明确版本与继承关系。 |
| C-03 | maplerime 的 `tag=1/2` 易被解释成现成的包/流双轨选路或接收能力标签。 | WS-06 只把 tag 作为工作负载标签送到选路入口；四基线不按 tag 改路由。WS-07 的 `dualtrack` 才定义 `tag=2` 逐包、`tag=1/0` 按流；tag 不表示接收能力。参考仓库 `lb_mode=16` 对两类数据均使用 MixHash 包级选路。 | WS-08 已在双方一致的 PFC=0/IRN=1 契约下复核正确性；后续所有机制对照继续保持共同传输。 |
| C-04 | 四份混合文件的背景流数增加时，总字节数同时增加。 | 同一文件可用于算法横向对照；跨文件不能单独归因于混合比例。 | WS-07 已生成并静态核验固定总字节的 0/2/4 替换式设计样本；后续须实际仿真并做多 seed 复核。 |
| C-05 | `feature/remote-experiment-workflow` 本地 `f46abb3`、GitHub `a8d2db5`，但新混合分支包含 `f46abb3`。 | 分支指针确有不同；不是文件丢失。实际实验须记录所用分支和 SHA。 | 后续若继续维护旧工作流分支，再决定是否快进；不要强制推送。 |
| C-06 | 旧状态称远程代码缓存仍为原始 `main`、混合分支尚未运行。 | 该快照已过期。WS-06 已从固定 SHA 创建独立远程副本，运行六列四流与旧五列回归；当前缓存指针需执行时重查。 | 以后仅以对应实验 ID 的 `metadata.json`、配置快照和原始数据断言运行版本，不从旧缓存快照推断。 |
| C-07 | “Queue usage”可能混用 ConWeave VOQ 与 MMU 物理队列。 | 四模式审计只核验 ConWeave VOQ；物理队列输出当前没有有效统计。 | 若新假设依赖 MMU 占用，先补观测定义与验证。 |
| C-08 | 仿真 seed 可能被误认为控制了流量生成。 | 原始 `traffic_gen.py` 未独立播种；配对实验必须固定 trace 内容及哈希。 | WS-07 pilot 已记录独立 trace seed 20260925 和不可变输入哈希；正式实验仍须事先冻结五个独立 trace seed。 |
| C-09 | 论文项目根目录不在 Git 中，若只在根目录写状态文件，仍无法形成版本化项目记忆。 | 把当前状态、ADR、Handoff 和项目 Skill 放在个人 fork；根目录 `AGENTS.md` 提供入口。 | 若未来为论文资料建立独立版本库，再显式迁移唯一权威位置。 |
| C-10 | 导入 400G 拓扑同时有 10ns/100ns 链路；参考仓库手填 18,000 B BDP 与实测 30,000 B 不一致，ConWeave 部分时序仍假定统一 `one_hop_delay`。 | WS-06 按实际链路核对 30,000 B；WS-07 已在此拓扑完成双轨跨 ToR 四流探测，均非 ConWeave 时序验证。见 [ADR-005](../decisions/ADR-005-imported-topology-bdp.md)。 | 若在此拓扑比较 ConWeave，先审计和验证其统一 `one_hop_delay` 时序估计；不外推双轨探测。 |
| C-11 | 旧 GuardHash 草案主要写背景长流受 MoE 喷洒影响；ANT 聊天最先追问背景增加时 MoE 小流劣化。 | 论文项目 `docs/research/12-screenshot-lessons-and-mechanism-selection.md` 与 [ADR-006](../decisions/ADR-006-conditional-guardhash-selection.md)把 MoE 受害方向列为首要诊断，同时测背景侧代价；受害方向尚未实测定论。 | WS-07 用双向、配对指标检验；不因研究选择直接实现 GuardHash。 |
| C-12 | `8round` 文件名和旧 `2.005s` FCT 窗口容易被误读成八轮依次运行且已有有效 MoE 汇总。 | 静态 trace 均为 `2.000s` 同启、无轮次字段；默认窗口会排除目标流。四 rail 拓扑的现有输入只打 rail 0。WS-07 已建立独立按 tag 的完成率/FCT/合成批次分析，pilot 仅使用 256 条目标子集。 | 正式实验明确 rail、固定目标集合与输入约束；保留旧 baseline 分析口径，不把合成批次称作已观测八轮 job CCT。 |
| C-13 | WS-07 四格 pilot 的逐包无背景约 4 ms MoE 尾部易被误当作背景混合造成的损害或正式算法比较。 | 四格仅有一个 trace seed；`packet0` 为 4002.653 µs，背景交互仅 +2.038 µs（0.0509%）。WS-08 已用逐流日志把四条末段尾流对应到 4 ms RTO；共同 IRN 契约的单 seed 交互转为 `−0.053 µs`。 | 两套传输条件分开报告；固定总字节和五 seed 正式实验尚未运行，见 [Handoff 09](../handoffs/2026-09-25-09-ws08-receiver-gate.md)。 |
| C-14 | `20260925-045000-ws07-1280-four` 曾在 RUNNING 时提前 fetch，本机一度只有半成品，易误报该 ID 失败或覆盖原始结果。 | 半成品保留于忽略目录 `results/.premature-20260925-045000-ws07-1280-four/`；终态完整结果已重新下载，同 ID 四流 4/4。远程 ID 未删除。 | `remote_worker.py::fetch_check` 已要求终态并以 RUNNING 实验核验拒绝；分析只引用正式 `results/<实验ID>/` 及元数据。 |
| C-15 | WS-08 的 no-go 与用户新要求“最快推进 GuardHash/HarmGate 实现与验证”表面冲突。 | no-go 针对**当前单 seed 效果证据与正式论文主张**；用户现授权可关闭的工程原型及技术验证。两者的证据等级不同，见 [ADR-007](../decisions/ADR-007-guardhash-prototype-before-efficacy.md)。 | WS-09 冻结机制规格并实现/核验；WS-10 预注册现象实验，WS-11 才作等信息效果判断。保留 WS-08 负结果。 |
