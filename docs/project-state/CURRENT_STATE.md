# ConWeave 毕业论文项目状态

更新：2026-09-25（中国时间）。本文件是跨对话的**状态入口**，不是实验原始证据。状态会过期；执行代码、实验或对外陈述前，应核对当前 Git、源码、实验 ID 与原始数据。工作规则以 `docs/REMOTE_EXPERIMENT_WORKFLOW.md` 为准，baseline 和指标口径以 `docs/research/10-baseline-fidelity-and-dataflow-audit.md` 为准。

## 当前阶段与目标

阶段：**WS-07 的独立 MoE 分组分析、最小包/流双轨及单 seed 四格资源 pilot 已完成；共同接收/重传语义须先排查后才能进入正式主实验。**研究问题仍是在同一网络承载逐包和按流选路时，是否存在可重复且有实际意义的跨类损害。当前 pilot 的逐包无背景批次已出现约 4 ms 尾部，不能把它归因于背景；四格交互仅为该逐包基线的约 0.051%。GuardHash/HarmGate 保持 WS-08 的条件性选择，本阶段没有新机制实现或正式性能结论。

## 已完成且可核验

- 研究：完成开题报告梳理、相关工作矩阵、初轮 8 个 idea、混合场景 5 个子 idea 和 MixHash 启发的 4 个算法草案。`ANT项目经验` 已按截图聊天日期及只读仓库演化完成复盘；论文项目 `docs/research/12-screenshot-lessons-and-mechanism-selection.md`、`docs/research/evidence/moe-static-profile.json` 是当前流量画像与条件性机制筛选入口，交接见 [Handoff 07](../handoffs/2026-09-25-07-ant-project-experience.md) 和 [ADR-006](../decisions/ADR-006-conditional-guardhash-selection.md)。它们是静态分析和方案，不是性能证据。
- 代码来源：`conweave-project/conweave-ns3` 与 `maplerime/conweave-ns3` 只读；个人可写 fork 为 `LarryBUPT/conweave-ns3`。maplerime 的版本演化见论文项目 `docs/research/09-maplerime-conweave-fork-evolution-report.md`。
- 实验链路：本机提交并推送个人 fork → 远程固定 SHA 的独立源码副本中编译/运行 → 按实验 ID 保存原始结果 → 下载并在本机分析。`20260923-165542-smoke-fecmp` 已验证完整链路。
- baseline：ECMP、CONGA、LetFlow、ConWeave 在相同 trace、拓扑和公共配置下各完成一次最小运行。实验 ID 为 `20260923-180001-fidelity-fecmp` 至 `20260923-180004-fidelity-conweave`，源码 SHA 均为 `a8d2db5f057172ce89730b4f6344c531e34a9302`。核验记录见论文项目 `results/baseline_fidelity_20260923.json`；**不能用于性能排序**。
- 输入资产：个人 fork 的 `feature/mixed-flow-traces` 已迁入 maplerime 的四份六列 MoE/背景流文件、拓扑和生成脚本，逐文件哈希见 `docs/research/mixed-flow-trace-provenance.md`。未迁入 MixHash 选路或接收端机制。
- WS-06 输入兼容：个人 fork `feature/ws06-flow-tags` 支持显式选择版本化 `config/*.txt`、五/六列流记录（五列默认 `tag=0`）及工作负载 tag 到源 ToR 选路入口的可见通路。32 主机和导入 1280 拓扑的四流六列探测各完成 4/4；四种旧五列 baseline 在固定旧 trace 下各完成 19,388 条流，原始 FCT 文件哈希逐模式与 WS-05 相同。证据和实验 ID 见 [Handoff 06](../handoffs/2026-09-24-06-six-column-input-and-tags.md)；这是输入与回归核验，不是双轨或性能验证。
- WS-07 技术 pilot：`feature/ws07-dual-track-mixtax` 新增 `dualtrack` (`tag=2` UDP 数据逐包哈希，`tag=1/0` 流 ECMP)、按输入 tag 的完成率/FCT/合成批次统计、可重生 pilot/固定总字节设计样本及配对检查。32 主机按流单类 FCT 原始哈希与同 trace `fecmp` 完全相同；导入 1280 拓扑跨 ToR 四流均完成且逐包决策触及多下一跳。四格 256-MoE × 背景 0/64 单 seed pilot 均全数完成；固定源码 SHA `8c99e5407ef41d14a6b67fc7dad55aada273946a`，结果与限制见 [Handoff 08](../handoffs/2026-09-25-08-ws07-dual-track-mixtax.md) 和 [摘要](../research/ws07-pilot-summary.json)。旧 2.005s baseline 分析保持原样；固定总字节样本尚未运行。

## 当前版本快照

2026-09-25 WS-07 交接观察：个人 fork 新分支 `feature/ws07-dual-track-mixtax` 的四格 pilot 固定在 `8c99e54`，0/64 trace SHA 分别为 `d60ca03e…7560`、`cbfa0e5a…8e1`；原始结果在 `results/<实验ID>/` 及远程同 ID 目录。交接/集成提交会移动分支 HEAD，执行时重新查询。四份导入完整 MoE trace 仍未全量仿真；WS-07 的固定总字节设计样本只有静态验证。

2026-09-24 WS-06 交接核验：`feature/ws06-flow-tags` 的输入兼容代码与资产固定在 `dba99face4b026443220e4b73e655a86aecc1aca`；九段 Handoff 已在 `267af27e445f03ee62fb46f8bf30267da780f0ab` 提交并推送到个人 fork。该分支从 `feature/mixed-flow-traces@30734578e7468a8cf156588de0aded5f96095e43` 分出。集成提交会继续移动分支指针，**执行时必须重新查询 HEAD**。`main@236a801a00e35de9078635e04acae2f701c21ded`；旧 `feature/remote-experiment-workflow` 本地 `f46abb3`、GitHub `a8d2db5` 的分支指针差异仍在。WS-06 实验各有固定 SHA 的独立远程源码副本；不据此推断远程代码缓存或既存工作树的当前状态。

2026-09-25 ANT 交接核验前，`feature/ws06-flow-tags` 本地与个人 fork `origin` 同为 `0a8d28ce89e8886b597e220cc3ff308523dc3c28`、工作树干净；本次状态集成将继续移动分支指针。论文项目根目录未纳入 Git；画像脚本重跑后 JSON SHA-256 不变。没有因研究筛选而修改算法代码或运行新的远程实验。

论文项目根目录 `E:\研\毕业论文` 本身**不是 Git 仓库**。本状态文件及 Handoff、ADR、项目 Skill 因而放在个人 fork 内，避免“项目记忆”只存在于未版本化目录。

## 正在推进、未完成及依赖

1. **公共输入底座与最小双轨，已完成技术核验：**六列/五列解析、显式流文件、tag 到源 ToR、独立 MoE 分组分析和 `dualtrack` 均可用；32 主机单类及双类、导入 1280 拓扑跨 ToR 四流已全数完成。四份完整 1280 节点 MoE trace 仍未全量运行。
2. **共同接收/重传语义，下一门槛：**当前 `dualtrack` 在共同 DCQCN、PFC=1、IRN=0 下可全部完成，但 256 条 MoE 无背景逐包批次约 4002.653 µs，全流约 1.415 µs，伴随乱序 CNP 与更多源包；具体致因尚未隔离。须先找出 4 ms 尾部机制，并对两类/两算法采用同一、可解释的接收模型后重做四格；不能把 tag 当能力标签。若在导入混合延迟拓扑比较 ConWeave，仍须先审计其统一 `one_hop_delay`。
3. **正式现象实验，依赖 2：**本轮 packet/flow × 背景 0/64 仅一组独立 trace seed 的技术 pilot，绝对交互 +2.038 µs、约逐包无背景基线的 0.051%，背景 P99 未恶化；不能据此作可重复性或因果结论。已生成固定目标、固定总字节的 0/2/4 背景设计样本，尚未运行；主实验需 5 个独立 seed 并遵守 [冻结指标与门槛](../research/ws07-dual-track-contract.md)。
4. **算法实验，依赖 3：**WS-08 GuardHash v0 继续 conditional；仅在共同语义下有稳定且实际有意义的 MixTax 时，先与普通本地短队列二选一比较类别信号增量，再做强对照。当前 pilot 不满足启动门槛。

下一个里程碑：**定位当前逐包无背景 4 ms 尾部并形成所有模式共享的接收/重传契约，重跑四格正确性与 pilot。**固定总字节设计和多 seed 正式实验必须随后进行。具体依赖见 [WORKSTREAMS.md](WORKSTREAMS.md) 与 [ROADMAP.md](ROADMAP.md)。

## 证据边界

- 最小运行证明路径和分析链路可工作，不证明论文性能优势；ConWeave VOQ 不是 MMU 物理队列，低负载运行未触发 PFC。
- 流量生成器未单独播种；ns-3 的 `RANDOM_SEED` 不能代替 trace seed。跨算法比较须复用不可变 trace 并记录哈希。
- 仅有 NS-3 仿真条件；不能声称已完成 SmartNIC、交换芯片、真实 RNIC 或生产集群验证。

## 本次整合的来源

前五份 [Handoff](../handoffs/) 从早期对话及落地文件整理；[Handoff 06](../handoffs/2026-09-24-06-six-column-input-and-tags.md) 为 WS-06 输入底座，[Handoff 07](../handoffs/2026-09-25-07-ant-project-experience.md) 为研究筛选，[Handoff 08](../handoffs/2026-09-25-08-ws07-dual-track-mixtax.md) 为 WS-07 技术 pilot。冲突与旧文档漂移见 [CONFLICTS.md](CONFLICTS.md)。本文件由集成工作流维护；原对话用于追溯理由，不作为实时状态数据库。
