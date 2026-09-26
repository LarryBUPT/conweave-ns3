# ConWeave 毕业论文项目状态

更新：2026-09-26（中国时间）。本文件是跨对话的**状态入口**，不是实验原始证据。状态会过期；执行代码、实验或对外陈述前，应核对当前 Git、源码、实验 ID 与原始数据。工作规则以 `docs/REMOTE_EXPERIMENT_WORKFLOW.md` 为准，baseline 和指标口径以 `docs/research/10-baseline-fidelity-and-dataflow-audit.md` 为准。

## 当前阶段与目标

阶段：**WS-10 固定总字节与五 seed 正式现象复核已完成，预注册主判据 no-go；WS-11 效果实验门槛未打开。**WS-07 的 PFC=1、IRN=0 逐包无背景约 4 ms 尾部已对应四个末段 RTO；WS-08 的 PFC=0、IRN=1 单 seed 交互为 `−0.053 µs`（`−3.7456%`）。WS-09 GuardHash/HarmGate v0 工程原型完成，但没有正式效果证据。WS-10 的 30/30 个正式格全类完成，4 背景档五 seed 交互仅 1 个正向、归一化中位数 `−1.3947%`，见 [Handoff 11](../handoffs/2026-09-26-11-ws10-fixed-load-formal.md) 与 [正式报告](../research/ws10-fixed-load-formal-report.md)。

## 已完成且可核验

- 研究：完成开题报告梳理、相关工作矩阵、初轮 8 个 idea、混合场景 5 个子 idea 和 MixHash 启发的 4 个算法草案。`ANT项目经验` 已按截图聊天日期及只读仓库演化完成复盘；论文项目 `docs/research/12-screenshot-lessons-and-mechanism-selection.md`、`docs/research/evidence/moe-static-profile.json` 是当前流量画像与条件性机制筛选入口，交接见 [Handoff 07](../handoffs/2026-09-25-07-ant-project-experience.md) 和 [ADR-006](../decisions/ADR-006-conditional-guardhash-selection.md)。它们是静态分析和方案，不是性能证据。
- 代码来源：`conweave-project/conweave-ns3` 与 `maplerime/conweave-ns3` 只读；个人可写 fork 为 `LarryBUPT/conweave-ns3`。maplerime 的版本演化见论文项目 `docs/research/09-maplerime-conweave-fork-evolution-report.md`。
- 实验链路：本机提交并推送个人 fork → 远程固定 SHA 的独立源码副本中编译/运行 → 按实验 ID 保存原始结果 → 下载并在本机分析。`20260923-165542-smoke-fecmp` 已验证完整链路。
- baseline：ECMP、CONGA、LetFlow、ConWeave 在相同 trace、拓扑和公共配置下各完成一次最小运行。实验 ID 为 `20260923-180001-fidelity-fecmp` 至 `20260923-180004-fidelity-conweave`，源码 SHA 均为 `a8d2db5f057172ce89730b4f6344c531e34a9302`。核验记录见论文项目 `results/baseline_fidelity_20260923.json`；**不能用于性能排序**。
- 输入资产：个人 fork 的 `feature/mixed-flow-traces` 已迁入 maplerime 的四份六列 MoE/背景流文件、拓扑和生成脚本，逐文件哈希见 `docs/research/mixed-flow-trace-provenance.md`。未迁入 MixHash 选路或接收端机制。
- WS-06 输入兼容：个人 fork `feature/ws06-flow-tags` 支持显式选择版本化 `config/*.txt`、五/六列流记录（五列默认 `tag=0`）及工作负载 tag 到源 ToR 选路入口的可见通路。32 主机和导入 1280 拓扑的四流六列探测各完成 4/4；四种旧五列 baseline 在固定旧 trace 下各完成 19,388 条流，原始 FCT 文件哈希逐模式与 WS-05 相同。证据和实验 ID 见 [Handoff 06](../handoffs/2026-09-24-06-six-column-input-and-tags.md)；这是输入与回归核验，不是双轨或性能验证。
- WS-07 技术 pilot：`feature/ws07-dual-track-mixtax` 新增 `dualtrack` (`tag=2` UDP 数据逐包哈希，`tag=1/0` 流 ECMP)、按输入 tag 的完成率/FCT/合成批次统计、可重生 pilot/固定总字节设计样本及配对检查。32 主机按流单类 FCT 原始哈希与同 trace `fecmp` 完全相同；导入 1280 拓扑跨 ToR 四流均完成且逐包决策触及多下一跳。四格 256-MoE × 背景 0/64 单 seed pilot 均全数完成；固定源码 SHA `8c99e5407ef41d14a6b67fc7dad55aada273946a`，结果与限制见 [Handoff 08](../handoffs/2026-09-25-08-ws07-dual-track-mixtax.md) 和 [摘要](../research/ws07-pilot-summary.json)。旧 2.005s baseline 分析保持原样；固定总字节样本尚未运行。
- WS-08 前置诊断：从个人 fork 已推送 `4649fb1928160c603f7df9ffd6400c091116ab60` 分支开工。只加日志的 `20260925-210024-ws08-nack-diagnostic@c8ca6a601dd4380bae36233053b654307d61d292` 与 WS-07 packet0 原始 FCT SHA 相同，四个约 4 ms 尾流恰与四个 4,000,000 ns 超时对应，超时均剩最后 192 B 未确认。共享 PFC=0、IRN=1、DCQCN 契约的 32 主机单类/双类及 1280 跨 ToR 四流正确性通过；同 SHA `445593fbc07236e18983d233407265220d360521` 四格各类全数完成，MoE 批次 flow0/packet0/flow64/packet64 为 1.415/1.415/1.625/1.572 µs，背景 P99 flow64/packet64 均 688.41974 µs。详证见 [Handoff 09](../handoffs/2026-09-25-09-ws08-receiver-gate.md)、[诊断](../research/ws08-receiver-preflight.md) 与 [机器摘要](../research/ws08-irn-pilot-summary.json)。固定总字节样本仅静态验证；无五 seed 推断。
- WS-09 工程原型：从已推送 `c45d41d42157dd3589e37ebe1953c75a68d5b6c2` 建 `feature/ws09-guardhash-prototype`；`shortq2/guardhash/guardhashgate` 模式 `13/14/15` 共用双候选哈希，HarmGate 是类别评分激活门槛。固定 `7930168f7bb43afbe6cc87bd134d91d28667e8c1` 完成 32 主机单/双类、导入 1280 跨 ToR 四流、同源码旧 `fecmp/dualtrack` 退化回归和 320 流同 trace 三格单 seed pilot；全部原始队列计数守恒。三格 MoE 合成批次 1.421/1.415/1.49 µs，背景 P99 均 688.41974 µs，门控实际激活 39 次、退出 9 次；仅属技术 pilot。修复提交 `9c34945c79b44476166f2f1f4dc26f6b2f6163a0` 的独立丢包探针 `20260926-025616-ws09-drop-probe` 两类准入丢包合计 3,041,296 B、计数违规 0。十格详证见 [Handoff 10](../handoffs/2026-09-26-10-ws09-guardhash-prototype.md)、[冻结规格](../research/ws09-guardhash-v0-spec.md)、[机器摘要](../research/ws09-validation-summary.json)；不作效果结论。
- WS-10 正式现象复核：预注册 v1.1 固定五个 trace seed、0/2/4 背景档、`fecmp/dualtrack`、总提供 35,651,584 B、统一 `aa778ac523bc0319999395dd3cf8085b41e73a98`。资源 pilot 6/6、正式 30/30 完成；4 档交互 1 正 4 负，归一化中位数 −1.3947%，背景安全 10/10 通过，2 档五 seed 均正但非单调，故现象 no-go。一次 SSH 状态解析故障的诊断格被同 SHA/trace 正式重跑替换，两份 FCT SHA 相同；详见 [Handoff 11](../handoffs/2026-09-26-11-ws10-fixed-load-formal.md)、[报告](../research/ws10-fixed-load-formal-report.md)、[机器摘要](../research/ws10-fixed-load-formal-summary.json)。

## 当前版本快照

2026-09-26 WS-10 集成核验：个人 fork `feature/ws10-fixed-load-mixtax` 的实验源码固定 `aa778ac523bc0319999395dd3cf8085b41e73a98`；正式 30 格的元数据、原始文件哈希、目标/类别完成率和资源收据由 `scripts/verify_ws10_formal.py` 重新读取通过。状态文件提交会移动分支 HEAD，不能把新 HEAD 误作仿真源码 SHA。WS-11 仍为条件性 no-go。

2026-09-26 WS-09 交接集成核验：`scripts/verify_ws09_prototype.py` 重新读取十个终态 ID 的元数据与原始结果，逐项通过；重生的 `docs/research/ws09-validation-summary.json` 与已提交文件 SHA-256 相同。个人 fork 本地与 `origin/feature/ws09-guardhash-prototype` 在集成前同为 `6a32df51d67b84b0a1f416e8b0c669946af15401`、工作树干净；其最后一提交只新增术语问答和状态入口。Handoff 10 已补真实 WS-09 任务 ID。集成提交会移动 HEAD。工程范围闭环，`queue_reject/queued_drop` 动态覆盖和正式类别增量仍留待后续。

2026-09-26 WS-09 集成核验：个人 fork `feature/ws09-guardhash-prototype` 机制/压力探针提交 `9c34945c79b44476166f2f1f4dc26f6b2f6163a0` 已推送；本 Handoff/状态集成提交会移动 HEAD，执行时重新查询。`scripts/verify_ws09_prototype.py` 对十个终态 ID 的元数据、trace/拓扑哈希、FCT 行数、逐端口守恒与三格共同输入重算通过。九个常规格固定 `7930168f`；修复版丢包压力格固定 `9c34945`。WS-09 工程范围完成；正式机制效果仍 no-go，WS-10/11 待独立执行。

2026-09-26 WS-08 集成核验：个人 fork `feature/ws08-guardhash-gate` 本地与 `origin` 同为 `653250a5381bb1992a4d8acececb62593cf343aa`、工作树干净。四格正式结果均 `SUCCEEDED`、固定 `445593fbc07236e18983d233407265220d360521`、PFC=0/IRN=1；四组 trace/FCT SHA-256 逐格与记录相符，FCT 行数 256/256/320/320，原始 OoO CNP 0/0/0/1516，PFC 行数均为 0。诊断复跑 FCT 与 WS-07 packet0 逐字节相同，日志含 601 RX NACK、571 TX NACK、四个末段 TX TIMEOUT。Handoff 09 已补真实任务 ID。集成提交会移动 HEAD。WS-08 的技术范围闭环，正式跨 seed 现象仍未解决；WS-09 是根据用户新指示的工程原型工作流。

2026-09-25 WS-08 诊断观察：个人 fork `feature/ws08-guardhash-gate` 的实验代码/运行器固定在 `445593fbc07236e18983d233407265220d360521`；本状态和 Handoff 的集成提交将移动 HEAD，须再次查询。四格原始结果 `20260925-211439-ws08-irn-flow0`、`20260925-210820-ws08-irn-packet0`、`20260925-212042-ws08-irn-flow64`、`20260925-212745-ws08-irn-packet64` 均 `SUCCEEDED`、PFC=0、IRN=1、共同 trace/seed，配对脚本通过。单 seed 交互未达预设方向与幅度，GuardHash 当前不启动。32 主机/跨 ToR 的小规模正确性 ID 见 Handoff 09。固定总字节 0/2/4 与五 seed 未运行。

2026-09-25 WS-07 集成核验：四格正式结果目录的 `metadata.json` 均为 `SUCCEEDED` 和固定源码 `8c99e5407ef41d14a6b67fc7dad55aada273946a`；trace 与原始 FCT 哈希逐格核对无误，FCT 行数 256/256/320/320，原始 OoO CNP 计数 0/601/0/733，PFC 行数均为 0。Handoff 08 已补真实 WS-07 任务 ID。WS-07 按最小双轨和单 seed pilot 范围闭环，4 ms 尾部定位、共同接收契约和正式多 seed 主实验转入后续门槛工作；这不改变 GuardHash 的条件性状态。核验前个人 fork 本地、`origin` 同为 `2b30d11c1efa42afa22a632a4789789cc3937526`，工作树干净；提交后重新查询 HEAD。

2026-09-25 WS-07 交接观察：个人 fork 新分支 `feature/ws07-dual-track-mixtax` 的四格 pilot 固定在 `8c99e54`，0/64 trace SHA 分别为 `d60ca03e…7560`、`cbfa0e5a…8e1`；原始结果在 `results/<实验ID>/` 及远程同 ID 目录。交接/集成提交会移动分支 HEAD，执行时重新查询。四份导入完整 MoE trace 仍未全量仿真；WS-07 的固定总字节设计样本只有静态验证。

2026-09-24 WS-06 交接核验：`feature/ws06-flow-tags` 的输入兼容代码与资产固定在 `dba99face4b026443220e4b73e655a86aecc1aca`；九段 Handoff 已在 `267af27e445f03ee62fb46f8bf30267da780f0ab` 提交并推送到个人 fork。该分支从 `feature/mixed-flow-traces@30734578e7468a8cf156588de0aded5f96095e43` 分出。集成提交会继续移动分支指针，**执行时必须重新查询 HEAD**。`main@236a801a00e35de9078635e04acae2f701c21ded`；旧 `feature/remote-experiment-workflow` 本地 `f46abb3`、GitHub `a8d2db5` 的分支指针差异仍在。WS-06 实验各有固定 SHA 的独立远程源码副本；不据此推断远程代码缓存或既存工作树的当前状态。

2026-09-25 ANT 交接核验前，`feature/ws06-flow-tags` 本地与个人 fork `origin` 同为 `0a8d28ce89e8886b597e220cc3ff308523dc3c28`、工作树干净；本次状态集成将继续移动分支指针。论文项目根目录未纳入 Git；画像脚本重跑后 JSON SHA-256 不变。没有因研究筛选而修改算法代码或运行新的远程实验。

论文项目根目录 `E:\研\毕业论文` 本身**不是 Git 仓库**。本状态文件及 Handoff、ADR、项目 Skill 因而放在个人 fork 内，避免“项目记忆”只存在于未版本化目录。

## 正在推进、未完成及依赖

1. **公共输入底座与最小双轨，已完成技术核验：**六列/五列解析、显式流文件、tag 到源 ToR、独立 MoE 分组分析和 `dualtrack` 均可用；32 主机单类及双类、导入 1280 拓扑跨 ToR 四流已全数完成。四份完整 1280 节点 MoE trace 仍未全量运行。
2. **共同接收/重传语义，技术诊断已完成：**旧 PFC+非 IRN 的四个 4 ms 尾流对应四个末段 RTO；共享 IRN+无 PFC 契约在一个 seed 的 0/64 四格全部完成且无超时。它是新的传输条件，不能与 WS-07 旧四格合并。若在导入混合延迟拓扑比较 ConWeave，仍须先审计其统一 `one_hop_delay`。
3. **正式现象实验，按 WS-10 预注册范围完成：**共同 IRN 契约、固定目标/总字节 0/2/4、五个独立 trace seed 和 30 个配对格均已运行核验。主 4 档只有 1/5 正向、归一化中位数 `−1.3947%`，不满足至少 4/5 正向且中位数 ≥5% 的门槛；本场景 no-go，不推断其他负载普遍无损害。2 档正向趋势作为非单调剂量结果保留。
4. **算法工程与效果分离：**WS-09 的 GuardHash 和 HarmGate 门控研究原型已实现，正确性、队列守恒与技术 pilot 按范围完成；目前没有机制收益或类别信号增量证据。`queue_reject/queued_drop` 未动态覆盖，压力格只证明 MMU 准入丢包可守恒。WS-10 的正式场景没有通过稳定损害门槛，WS-11 不启动效果主张，见 [ADR-007](../decisions/ADR-007-guardhash-prototype-before-efficacy.md)。

下一个里程碑：**整理 WS-10 负结果及 2/4 档非单调性，决定是否另立可证伪的新现象场景。**新场景须另行预注册，不并入当前 30 格；只有新场景重新通过现象门槛，才考虑 WS-11 等信息效果对照。也可按 WS-12 的解释性负结果路线组织论文证据。依赖与停机条件见 [WORKSTREAMS.md](WORKSTREAMS.md) 与 [ROADMAP.md](ROADMAP.md)。

## 证据边界

用户提问的术语解释与后续追加入口见 [TERM-QA 术语提问合集](../TERMINOLOGY_QA.md)；术语定义不替代本节的实验原始证据。

- 最小运行证明路径和分析链路可工作，不证明论文性能优势；ConWeave VOQ 不是 MMU 物理队列，低负载运行未触发 PFC。
- 流量生成器未单独播种；ns-3 的 `RANDOM_SEED` 不能代替 trace seed。跨算法比较须复用不可变 trace 并记录哈希。
- 仅有 NS-3 仿真条件；不能声称已完成 SmartNIC、交换芯片、真实 RNIC 或生产集群验证。

## 本次整合的来源

前五份 [Handoff](../handoffs/) 从早期对话及落地文件整理；[Handoff 06](../handoffs/2026-09-24-06-six-column-input-and-tags.md) 为 WS-06 输入底座，[Handoff 07](../handoffs/2026-09-25-07-ant-project-experience.md) 为研究筛选，[Handoff 08](../handoffs/2026-09-25-08-ws07-dual-track-mixtax.md) 为 WS-07 技术 pilot。冲突与旧文档漂移见 [CONFLICTS.md](CONFLICTS.md)。本文件由集成工作流维护；原对话用于追溯理由，不作为实时状态数据库。

[Handoff 09](../handoffs/2026-09-25-09-ws08-receiver-gate.md) 记录 WS-08 前置诊断、共同 IRN 四格的负向单 seed pilot 和当前机制 no-go；该结论不改写 WS-07 旧传输条件下的原始结果。

[Handoff 10](../handoffs/2026-09-26-10-ws09-guardhash-prototype.md) 记录 WS-09 可关闭原型、十个实验 ID 的正确性/守恒与单 seed 技术 pilot；它不改变 WS-08 效果 no-go，也不替代 WS-10/11 的正式证据门槛。

[Handoff 11](../handoffs/2026-09-26-11-ws10-fixed-load-formal.md) 记录 WS-10 预注册五 seed 正式复核、一次控制器恢复和现象 no-go；所有正式格与原始 SHA 索引在 [机器摘要](../research/ws10-fixed-load-formal-summary.json)。
