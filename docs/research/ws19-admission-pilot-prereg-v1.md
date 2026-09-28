# WS-19 发送准入 × 上游路径双侧小样：事前协议 v1

冻结日期：2026-09-28。性质：探索性、配对的 2×2 因子小样；不是 WS-20 确认性验证或业务 SLO 验收。父分支 `feature/ws18-admission-routing@9d7cd87affb888a20a673caa54e4ddaa7b118bbe`，新分支 `experiment/ws19-admission-pilot`。首次效果运行前须提交并推送本协议、12 份输入、[生成器](../../scripts/prepare_ws19_pilot.py)和[顺序清单](evidence/ws19-pilot-schedule-v1.json)，记录最终仿真源码 SHA。运行后不以结果改写 v1；修改需新版本、新 SHA 和新实验 ID。

## 研究问题与预测

对同一批需求，发送端 400 Gbps 名义逐目的准入是否降低从**原始需求时刻**计的 MoE 轮次完成时间，而不把损失转嫁给 8 MiB 背景流？源 ToR 的稳定双候选路径能否在可绕行的上游热点额外改善联合方案？四臂 `(admission,path)` 固定为 `ECMP=(0,0)`、仅准入 `(1,0)`、仅路径 `(0,1)`、联合 `(1,1)`。路径开关只作用于 tag=2 跨 ToR 数据；背景路由和共同 DCQCN/PFC=0/IRN=1 传输不变。唯一目的主机出口不因上游换路增容，所以主机热点是路径机制的边界/负对照；同 ToR 多主机热点才提供上游分流机会。路径与准入都可能无益或损害两侧；任何源端等待都计入结果。

## 冻结输入、重复单位与执行顺序

[WS-17 manifest](evidence/ws17-demand-manifest.json) 的独立生成 seed `20261701–03` 各重抽专家成员、热点和背景端点。每 seed 有 `host_hotspot/tor_hotspot × b0/b192` 四个配对输入，`b0` 为 16,384 条 8 KiB MoE，`b192` 追加 192 条 8 MiB 背景；每输入 8 轮，每轮 2,048 条 MoE，轮距 50 µs。两档同 seed、同热点的 MoE 需求相同，追加背景同时增加总提供字节。12 个版本化 `config/ws19_ws17_*.txt` 与原 manifest 的 SHA-256 相同；拓扑 `config/topo_1280_400G_400G_OS1.txt` SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。sidecar 用 `scripts/make_ws17_demand.py --verify` 重生核验，不依赖安装顺序匹配端口。

**独立重复单位是重抽需求的 seed，n=3。**每 seed 的两种热点、两档背景、四臂、8 轮及每条流都是重复测量/配对观察，绝不充当额外独立样本。ns-3 `RANDOM_SEED=1` 在所有臂固定；估计仅针对这三组人工需求及此模拟器 seed。不得把行顺序置换、WS-18 40 流正确性格或旧 WS-13 校准 trace 并入 n。

设计为 12 个 `(seed,hotspot,background)` 完全配对区组，每区组四臂共用逐字节 trace、拓扑、传输参数、源码 SHA、仿真 seed。`scripts/prepare_ws19_pilot.py` 以 `20261901` 固定随机化区组先后和各区组四臂顺序；[顺序 JSON](evidence/ws19-pilot-schedule-v1.json) 有 48 行且可逐字节重生。执行时按该顺序启动，资源异常仅暂停新格，不改已冻结顺序。失败格保留 ID；修代码需整体换 SHA 并重作相关区组，不混合版本。资源技术 pilot 单独标记，不计效果。

## 前置门槛和资源 pilot

1. 静态：核实 WS-18 五格正确性 raw/哈希和 `scripts/verify_ws18_correctness.py`，12 份 trace/sidecar 重生、拓扑、四臂开关与固定 400 Gbps 参数；检查源等待在 `finish−demand` 内、背景不延后。确认当前源码诊断能定位随机新热点的上游与目的出口；若仍只看旧目的 856/576，瓶颈位置**不可判**，不启动效果矩阵。
2. 服务器：只读查其他用户作业/现有 ns-3、运维状态、1/5/15 分钟负载、40 逻辑 CPU、可用内存/磁盘和隔离目录；只有无他人作业、系统健康才构建。先同输入 `seed20261701/tor_hotspot/b192/ECMP` 做**诊断关闭/开启两格技术资源 pilot**：两格 FCT 原始 SHA 必须相同，开启格须覆盖新背景目的且 `WS13_INFLIGHT unpaired=0`，否则观测门槛失败。记录源码 SHA、trace SHA、编译/运行墙钟、进程树 RSS、系统最低可用内存/磁盘、负载、raw 完整性。pilot 不计 48 格；开启格测诊断开销。并发从 1 开始；只有隔离、吞吐与资源收据支持才提升，不以 18 令牌历史结果代替本次测量。出现争用、资源压力、吞吐下降或其它用户作业，停止启动新格并降载。
3. 每效果格应 `SUCCEEDED`、固定源码 SHA、输入/拓扑哈希、seed/参数一致且逐 ID 输入一对一完成，字节守恒，`demand≤release≤finish`、`total=wait+network`、背景等待为 0。0 路径臂选择计数为 0，1 路径臂在有跨 ToR 候选时有触发。缺失/截尾流是完成率失败，不计算“完成者 P99”来过关。任何前置或首格完整性失败即暂停，原始结果留存且本版本 no-go；修复须重冻。

## 指标和分析（运行前固定）

主结果按 seed×热点×背景×臂计算 8 个轮次各自 `max(finish_ns)−本轮最早 demand_ns`，报告八轮原值、均值和最大值；另报全部 MoE 的 `max(finish)−最早 demand`，明确它只是合成批次而非真实训练 job CCT。所有计时均包含源等待。背景只在 b192 定义：192 条逐流 `finish−demand`、P50/P95/P99/最大 FCT、有效吞吐、最慢流身份及与同 ID ECMP 的差。按完整输入分母报告 MoE/背景完成率和字节；发送等待报告正等待流数、P50/P99/最大、总等待及 `network=finish−release` 分量。位置证据分开报源 ToR 候选出口与目的 ToR→主机出口的队列等待/排队前字节、路径选择、CNP/ECN、丢包与可观测重传事件；缺观测写“不可测”，不能把空 MMU qlen、无 timeout 日志或 ConWeave VOQ 写成零。b0 的背景 P99 未定义。

对每个配对区组报 `A−E`、`P−E`、`J−E`、`J−A`、`J−P` 和交互 `J−A−P+E`（时间差负数有利），并在 b192 同样列背景 P99、最大值与逐流差。跨 seed 只给三个独立差值、范围/中位数与连续 MoE—背景权衡图；n=3 不作显著性或精确置信区间主张，不在轮次/流级检验上制造样本量。热点、背景是预定分层，不合并成一个平均收益。次要强对照 DRILL/普通双候选的历史信息预算不同且输入不同，本次四臂仅识别两个开关及其交互；若进入 WS-20，须另立同输入强对照。

## 双侧停止与 WS-20 门槛

先执行完整性硬门槛。研究性筛选采用**零损害的方向性 Pareto 条件**，不是源自业务的百分比 SLO：在三个独立 seed 的 `tor_hotspot/b192` 中，联合臂的八轮均值必须逐 seed 严格短于 ECMP、仅准入及仅路径，背景 P99 与最大值须逐 seed 不高于同输入 ECMP，且两类全完成。主机热点 b192 联合臂不得劣于仅准入的八轮均值、背景 P99 与最大值；两个 b0 场景联合臂不得劣于 ECMP 的八轮均值。须看到路径触发及上游位置改变，与唯一最终出口未扩容的结构事实相容。若任何条件失败，WS-19 可按已收集格描述连续权衡和反例，但 **WS-20 保持 no-go**；若指标混合、精确相等或机制位置不可判，也不把收益写成通过。选择零损害只是小样继续研究的保守方向筛，不宣称生产可接受损害为零；即便全过，仍仅是 WS-20 设计 go，不是普遍效果或业务安全结论。不得把 WS-10/11/12 的旧 5% 安全线移植至此。

选择这些指标依据 [DRILL](https://pbg.cs.illinois.edu/papers/ghorbani17drill.pdf)、[ConWeave](https://cse.hkust.edu.hk/~kaichen/courses/spring24/comp7215/papers/conweave-sigcomm23.pdf)、[Presto](https://conferences2.sigcomm.org/sigcomm/2015/pdf/papers/p465.pdf) 对短流尾部、长流/吞吐、队列及乱序代价的并列评价；[WS-13 证据](ws13-tail-diagnosis-and-experiment-contract.md)在旧输入中观察到背景 P99 强烈跨需求波动与目的出口等待，[WS-14 小样](ws14-guardhash-single-mechanism-pilot-report.md)出现背景最慢流迁移，故本轮看完整逐流尾部与源等待。论文中的改善幅度、旧 5% 线及三条旧校准波动均不能给本输入设业务 SLO。

静默远程运行约每 30 分钟只看完成/失败/资源精简收据，记录实验 ID、SHA、输入哈希、PID 与预计检查时间；开始长时仿真前由协调任务**实际**切至 GPT-6 Luna High，全部终态 raw 回传后实际切回 GPT-6 Sol High 才分析。若工具无法切换，不以文档假称已切换，暂停远程效果启动并通知协调任务。WS-20 在本协议及 WS-19 结果审阅前保持关闭。

设计方法参考：Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065. https://doi.org/10.48550/arXiv.2609.00065 （2026-09-28 核对 arXiv 当前 v2）。
