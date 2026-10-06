# WS-25 第一课题预设验收逐项核对

核对日期：2026-10-07。范围为[执行清单](../project-state/WS25_FIRST_PAPER_EXECUTION.md)的七个必做项，以及[正式协议](ws25-v1fix-formal-protocol.md)的 576 格、资源与统计门槛。本审计不把小论文投稿、第二课题状态反馈研究或真实网络部署纳入第一课题已完成的实验验收；这些事项各有后续门槛。

## 1. 历史证据与机制假说：通过

[v1 预飞行审计](ws25-classreserve-audit-and-preflight.md)从 WS-11 的 40/40、WS-12 的 120/120 原始格复算，保留其历史双侧 NO-GO；它审查 WS-13 的逐 QP/逐跳探针和 WS-19/20 的三独立需求、48 格小样与事后反例。2026-10-07 核对个人 fork 原 checkout：WS-13 反馈探针机器证据所列 4/4 原 ID、WS-19 分析所列 48/48 原 ID、WS-20 事后审查所用 12/12 原 ID 的 metadata/raw 目录仍存在；WS-19 机器结果标明逐格 raw 复验，固定仿真 SHA `b52e66f0fbf786fb57672b12a5633cf45b9311c1`，WS-20 不新增效果样本。WS-13 探针源码 SHA `a985798ef78a95f502cf8eb56982c6e3a3b1168d`，四格只作技术诊断。[WS-16 对开题报告的审计](ws16-paper-evidence-and-reproduction.md)引用的原始 `.docx` SHA-256 `532b7739eed80cf2143f3c3a2ee3deb22c175d74b94f4a6930337e002725093a` 与本机文件现值一致。v1 的可实现本地信号、选路动作、失败预测与候选台账均已在预飞行审计记录；v2 原版/唯一修正的探索反例及[第三候选准入决定](ws25-third-candidate-decision.md)没有重写历史结论。

## 2. 五模式同条件基线：通过，动态覆盖有限

固定原仓库 `a8d2db5f057172ce89730b4f6344c531e34a9302` 定义的 ECMP、DRILL、CONGA、LetFlow、ConWeave 入口，在同一后续 fork SHA 的六列 trace 兼容层下运行；没有把旧二进制误称为直接读取类别列。ConWeave 首次 OS1 参数映射失败 ID `20261002-220004-ws25-pre-conweave` 保留，C2 新 SHA/新 ID 重验；[v1fix 11 格正确性](ws25-v1fix-correctness-analysis.md)包含五原始模式同一 mixed8、ClassReserve、单类、tag0/五列回退与 192 档格。2026-10-07 重跑 `python scripts/verify_ws25_v1fix_correctness.py` 返回 **11/11**。五模式在冻结正式矩阵还各有 96 格同输入配对，全流完成与字节/标签身份核验通过。CONGA/LetFlow flowlet timeout、ConWeave reroute/VOQ 在本输入中很少触发，故只支持模式入口与本负载下的效果对照，不支持充分动态分支覆盖的主张。

## 3. 候选实现与正确性：通过

v1 修正版固定仿真 SHA `ce699dffe2845dc83e2171a1c309c6d96b96d2b3`，正式 96/96 候选格的类别队列入/出字节闭合，零记录 drop/违规、所有输入流完成。前置 11 格覆盖混合/单类、回退、旧模式回归、合法选路和资源；原 v1 逐包造成乱序后，仅按允许的一次诊断修正改为 MoE 逐流缓存，修正参考已见 seed，不用于正式估计。v2 原版 12/12 正确性加 28/28 新需求探索格，唯一修正版 v2r1 13/13 正确性加 28/28 另一组探索格；诊断格与候选主格 FCT 指纹同一。两版筛选均未过预设双侧探索门，不能写为正式收益或取代 v1 确认性 NO-GO。第三候选上限是最多三版，不要求无机制依据地用满；剩余名额未启动，不计作实验通过。

## 4. 事前设计与解释指标：通过协议验收，解释证据有边界

[正式协议](ws25-v1fix-formal-protocol.md)在未见最终池揭盲前分离筛选/校准/最终 seed，指定需求 seed 为独立单位、同 seed 六臂配对、192 档共同主结果、0/64/128 档约束及所有流未完成时指标缺失的处理。MoE 批次按最晚完成绝对时刻减 2.000 s，背景 P99 从全部 192 条输入 FCT 线性插值，不使用默认 2.005 s 截尾或完成者子集。正式矩阵的背景集合完成速率、上联累计字节不均衡、路径选择及 CNP/乱序已作解释；两格同 FCT 指纹的非扰动逐 QP/逐跳尾流探针还记录了目的跳与上游出口等待。上联累计字节不均衡不是瞬时利用率，两格探针不是 24 seed 的全量机制样本；没有同粒度 ECMP 探针或按包对齐时序，不能从中确认因果。物理 MMU 总队列、逐 QP 速率时标与真实 NIC 观测仍缺失，按冻结协议明示缺项、没有填零，也不作物理队列或部署主张。若以后要主张这些机制，须先补观测并另立验证。

## 5. Pilot 与冻结：通过

独立校准 seed `20262505–08`、低档 72 格和[容量 pilot](ws25-resource-capacity-timing-audit.md)在最终池以外估计波动与资源；18 并发相对 16 的吞吐增量未过事前 5% 升档线，正式 cap=16。[协议](ws25-v1fix-formal-protocol.md)在正式格之前冻结 24 seed 的双主结果各自中位 ≤−5%、至少 17/24 严格改善、四次级 Holm、低档约束、缺失格/失败与资源停止规则。唯一[机器计划](evidence/ws25-v1fix-formal-plan.json)给出 96 份 trace SHA、拓扑 SHA、源码 SHA、576 原 ID 与 36 批次顺序；当前协议/计划文件 SHA 分别与[正式机器分析](evidence/ws25-v1fix-formal-analysis.json)所记录的 `304f454b…` / `f70d1ce8…` 完全相同。Git 历史显示协议首次提交于 2026-10-04 06:20:12、计划于 06:29:43（北京时间）；576 格最早 metadata 创建于 06:30:42、最早运行于 07:09:49，顺序满足先冻后跑。校准没有并入确认性 n。

## 6. 正式验证与恢复：通过

2026-10-07 本地重新运行 `python scripts/run_ws25_formal.py verify`，返回 `complete=true, verified_cells=576`，逐格重读计划、metadata、trace/拓扑/FCT raw、类别完成、队列及资源；再运行 `python scripts/analyze_ws25_formal.py` 从同一 raw 重建全部统计，返回 `verified_cells=576, primary_pass=false`，分析 JSON 的 SHA-256 仍为 `f4d4ce0bb7e0ed8af26ee84276c472e082d8d6163c964e2c6dd7a3f632931f43`，与重算前相同。计划、[执行摘要](../../results/ws25-v1fix-formal-summary.json)与[正式分析](evidence/ws25-v1fix-formal-analysis.json)的 ID 集合均为相同的 **576/576**；36 批、576 个本地 metadata/raw 目录齐全，收据中的 `verified` 为 576 个唯一 ID、无 failure 事件，全部 `SUCCEEDED`。每格 16,384 条 MoE 与对应 0/64/128/192 条背景流完整完成。峰值 load 16.10、最低 MemAvailable 51.80 GiB、空盘 4,962.54 GiB、最大单格树 RSS 4,562.50 MiB，均在停止线内。控制面 SSH 超时曾按原 ID/metadata 防重恢复，已验收 raw 未覆盖；最终 runner PID `46324` 与后续探索 runner PID `14084` 在本机均已退出。没有未完成 v1 正式格，也不因额外 SSH 轮询制造新格。

## 7. 双侧分析、反例、图表及初稿：通过

[正式报告](ws25-v1fix-formal-analysis.md)与机器 JSON 从 raw 得到 192 档相对 ECMP 的 MoE 批次中位 **−3.536%**、20/24 改善；背景 P99 **−0.065%**、13/24 改善。两项交集 **NO-GO**；四次级基线按 Holm 报告，低档约束通过但保留 64 档单 seed +45.647% 背景 P99 反例。机制计数、上联不均衡与[两格尾流诊断](ws25-v1-formal-tail-diagnostic-analysis.md)支持代码路径执行和有限的末端拥塞线索，不提供完整因果分解。[复现清单](ws25-v1fix-reproducibility-checklist.md)、576 行逐格表、840 行逐 seed 配对、1008 条 CDF 索引和 192 张 SVG 已落盘；2026-10-07 重新解析 192/192 张 SVG 与初稿 10/10 个本地链接，均有效。[小论文负结果初稿](ws25-classreserve-v1-paper-draft.md)及[图文终审](ws25-v1fix-paper-package-audit.md)已形成，模拟 RDMA QP、合成批次、VOQ/物理队列与真实部署界限保留。

## 关闭判断与后续边界

七项预设的第一课题**实验和初稿验收均有对应证据并已通过**；效果判据本身为确认性 **NO-GO**，它是完成全部验证后的负结果，不是未完成。v2/v2r1 是额外的独立探索反例，未见 seed `20262549–52` 和 `20262553–76` 未动用，第三候选版次保留，不改 v1 的正式结果。本文稿尚未投稿；目标会议模板、投稿决定与投稿动作是 ADR-010 明列的后续里程碑。投稿之后才能开启第二课题状态反馈；旧 WS-21 的反馈成本/时效/采用证据亦在那里承接。现有结论只适用于冻结的合成需求生成器和 ns-3 模型。主对话可据本审计集成状态；**不自动归档本对话或启动第二课题**。
