# ConWeave 毕业论文项目状态

更新：2026-09-25（中国时间）。本文件是跨对话的**状态入口**，不是实验原始证据。状态会过期；执行代码、实验或对外陈述前，应核对当前 Git、源码、实验 ID 与原始数据。工作规则以 `docs/REMOTE_EXPERIMENT_WORKFLOW.md` 为准，baseline 和指标口径以 `docs/research/10-baseline-fidelity-and-dataflow-audit.md` 为准。

## 当前阶段与目标

阶段：**可复现实验底座及五/六列输入与 tag 通路已完成轻量技术验证；包/流双轨语义与 MoE 分组分析待建立。**研究问题是在同一网络承载按包和按流/flowlet 选路的通信时，是否出现可重复的跨类性能损害。最新研究筛选保留 HarmGate 问题，以 GuardHash 本地双候选规则作为有条件的唯一优先原型；先测背景增加对 MoE 的额外伤害，同时检查背景侧代价。只有损害稳定且强基线未解释类别信号增量，才进入机制实现。当前没有新算法实现或正式性能结论。

## 已完成且可核验

- 研究：完成开题报告梳理、相关工作矩阵、初轮 8 个 idea、混合场景 5 个子 idea 和 MixHash 启发的 4 个算法草案。`ANT项目经验` 已按截图聊天日期及只读仓库演化完成复盘；论文项目 `docs/research/12-screenshot-lessons-and-mechanism-selection.md`、`docs/research/evidence/moe-static-profile.json` 是当前流量画像与条件性机制筛选入口，交接见 [Handoff 07](../handoffs/2026-09-25-07-ant-project-experience.md) 和 [ADR-006](../decisions/ADR-006-conditional-guardhash-selection.md)。它们是静态分析和方案，不是性能证据。
- 代码来源：`conweave-project/conweave-ns3` 与 `maplerime/conweave-ns3` 只读；个人可写 fork 为 `LarryBUPT/conweave-ns3`。maplerime 的版本演化见论文项目 `docs/research/09-maplerime-conweave-fork-evolution-report.md`。
- 实验链路：本机提交并推送个人 fork → 远程固定 SHA 的独立源码副本中编译/运行 → 按实验 ID 保存原始结果 → 下载并在本机分析。`20260923-165542-smoke-fecmp` 已验证完整链路。
- baseline：ECMP、CONGA、LetFlow、ConWeave 在相同 trace、拓扑和公共配置下各完成一次最小运行。实验 ID 为 `20260923-180001-fidelity-fecmp` 至 `20260923-180004-fidelity-conweave`，源码 SHA 均为 `a8d2db5f057172ce89730b4f6344c531e34a9302`。核验记录见论文项目 `results/baseline_fidelity_20260923.json`；**不能用于性能排序**。
- 输入资产：个人 fork 的 `feature/mixed-flow-traces` 已迁入 maplerime 的四份六列 MoE/背景流文件、拓扑和生成脚本，逐文件哈希见 `docs/research/mixed-flow-trace-provenance.md`。未迁入 MixHash 选路或接收端机制。
- WS-06 输入兼容：个人 fork `feature/ws06-flow-tags` 支持显式选择版本化 `config/*.txt`、五/六列流记录（五列默认 `tag=0`）及工作负载 tag 到源 ToR 选路入口的可见通路。32 主机和导入 1280 拓扑的四流六列探测各完成 4/4；四种旧五列 baseline 在固定旧 trace 下各完成 19,388 条流，原始 FCT 文件哈希逐模式与 WS-05 相同。证据和实验 ID 见 [Handoff 06](../handoffs/2026-09-24-06-six-column-input-and-tags.md)；这是输入与回归核验，不是双轨或性能验证。

## 当前版本快照

2026-09-24 WS-06 交接核验：`feature/ws06-flow-tags` 的输入兼容代码与资产固定在 `dba99face4b026443220e4b73e655a86aecc1aca`；九段 Handoff 已在 `267af27e445f03ee62fb46f8bf30267da780f0ab` 提交并推送到个人 fork。该分支从 `feature/mixed-flow-traces@30734578e7468a8cf156588de0aded5f96095e43` 分出。集成提交会继续移动分支指针，**执行时必须重新查询 HEAD**。`main@236a801a00e35de9078635e04acae2f701c21ded`；旧 `feature/remote-experiment-workflow` 本地 `f46abb3`、GitHub `a8d2db5` 的分支指针差异仍在。WS-06 实验各有固定 SHA 的独立远程源码副本；不据此推断远程代码缓存或既存工作树的当前状态。

2026-09-25 ANT 交接核验前，`feature/ws06-flow-tags` 本地与个人 fork `origin` 同为 `0a8d28ce89e8886b597e220cc3ff308523dc3c28`、工作树干净；本次状态集成将继续移动分支指针。论文项目根目录未纳入 Git；画像脚本重跑后 JSON SHA-256 不变。没有因研究筛选而修改算法代码或运行新的远程实验。

论文项目根目录 `E:\研\毕业论文` 本身**不是 Git 仓库**。本状态文件及 Handoff、ADR、项目 Skill 因而放在个人 fork 内，避免“项目记忆”只存在于未版本化目录。

## 正在推进、未完成及依赖

1. **公共输入底座，已完成轻量核验：**六列/五列解析、显式流文件和 tag 到源 ToR 入口已可用；四份完整 1280 节点 MoE trace 只做静态格式核对，尚无全量仿真或资源 pilot。
2. **双轨语义与分析，未完成：**`tag=1/2` 只是数据标签，不证明接收端乱序能力；当前没有同网并行运行包级与流级选路的模式。四份 MoE 输入全部于 `2.000s` 启动，旧 `2.005s` FCT 窗口会漏掉目标流。WS-07 须固定两类流量共同的传输、PFC 和重排规则，补按 tag 的输入/完成/未完成、FCT 与合成批次指标，再做单类及混合小测试。若在导入混合延迟拓扑上比较 ConWeave，还须先审计其统一 `one_hop_delay` 时序估计。
3. **现象实验，依赖 2：**先在固定 MoE 子 trace 下配对比较 packet/flow × 背景 0/64，分别估计背景对 MoE 的额外影响和 MoE 逐包选路对背景流的影响。四份现有输入只打 rail 0，且背景字节数随档位增加，不能直接作为“只改变混合比例”的因果比较；主实验需固定总负载、可重生 trace 和独立 trace seed。
4. **算法实验，依赖 3：**仅在 MixTax 可重复且有实际意义时实现 GuardHash v0；先与普通本地短队列二选一比较类别信号增量，再与静态隔离及 APS/FLB 类同模型对照。若无损害、无增量或只把代价转移给背景流，则停止机制主张。

下一个里程碑：**WS-07 修正 MoE 统计窗口并建立分类观测与共同传输语义，再通过单类退化及双类共存的小规模正确性检查。**此后才进入双向 MixTax pilot。具体任务和阻塞关系见 [WORKSTREAMS.md](WORKSTREAMS.md)，顺序见 [ROADMAP.md](ROADMAP.md)。

## 证据边界

- 最小运行证明路径和分析链路可工作，不证明论文性能优势；ConWeave VOQ 不是 MMU 物理队列，低负载运行未触发 PFC。
- 流量生成器未单独播种；ns-3 的 `RANDOM_SEED` 不能代替 trace seed。跨算法比较须复用不可变 trace 并记录哈希。
- 仅有 NS-3 仿真条件；不能声称已完成 SmartNIC、交换芯片、真实 RNIC 或生产集群验证。

## 本次整合的来源

前五份 [Handoff](../handoffs/) 从早期对话及落地文件整理；[Handoff 06](../handoffs/2026-09-24-06-six-column-input-and-tags.md) 由 WS-06 任务提交并核验；[Handoff 07](../handoffs/2026-09-25-07-ant-project-experience.md) 由本次集成按 ANT 对话、根目录研究文档、Git 与静态画像整理。冲突与旧文档漂移见 [CONFLICTS.md](CONFLICTS.md)。本文件由集成工作流维护；原对话用于追溯理由，不作为实时状态数据库。
