# WS-13 背景长尾诊断与新实验契约（校准阶段草案）

日期：2026-09-27。状态：**逐流诊断已执行；新正式机制判据尚未冻结，WS-14 尚未获准启动。**本页不改 WS-10/11/12 各自的预注册 5% 规则与 no-go。

## 可复核输入、比较对象与定位

个人 fork `feature/ws13-tail-diagnosis` 从 `feature/ws12-packet-strategies@cc045154602cc399d3bfd98fc20ea740a421795c` 分出；WS-12 正式仿真 SHA 仍为 `adae7956e3fc874d9237e62a6ea8e32b26d5def1`。`scripts/diagnose_ws13_tails.py` 从[120 格正式摘要](ws12-packet-strategies-formal-summary.json)定位原始 192 档与顺序组 20261103 的 128 档，并逐格读取 `results/<ID>/config/traffic_trace.txt`、`metadata.json`、原始 `_out_fct.txt/_out_cnp.txt/_out_uplink.txt` 与 `config.log`。按源码相同的源/目的端口自增规则重建流键，核对同档同组输入哈希、100% 完成和摘要 P99；不使用摘要替代逐流原始值。输出[1600 行逐流配对 CSV](evidence/ws13-tail-paired-flows.csv)、[10 个配对收据](evidence/ws13-tail-cases.json)及[连续权衡图](evidence/ws13-tradeoff.svg)。其中 192 档五种逐包模式各 192 条背景，128 档各 128 条；ECMP 逐流基准在各行明列。WS-11 两个旧模式的原始 FCT SHA 已经在 WS-12 40/40 格复核一致，因此此处旧模式的 WS-12 副本也对应 WS-11 原始现象。

原始 192 档背景 ECMP P99 为 **1411.822 µs**。逐包哈希/RR/随机/自适应依次为 **1505.747/1500.680/1531.248/1538.374 µs**，相同输入配对增加 **93.925/88.858/119.426/126.551 µs**；DRILL 为 **1457.073 µs**，增加 **45.251 µs**，未越旧 5% 线。此格绝对 MoE 合成批次 ECMP **18.920 µs**，哈希/RR/随机/自适应/DRILL 依次 **21.369/22.332/19.040/17.799/17.675 µs**。所以主档自适应和 DRILL 可快于 ECMP，但其他三者此原始格未快于 ECMP；相对既有偏慢哈希的收益不可替代这个同档绝对比较。

20261103 顺序组 128 档背景 ECMP P99 **1238.581 µs**；自适应与 DRILL 为 **1343.298/1343.360 µs**，配对增加 **104.717/104.779 µs**。此格 MoE 批次 ECMP **16.716 µs**，自适应/DRILL **16.745/16.827 µs**，两者并未快于 ECMP。旧 5% 安全线失败同时也没有同档绝对 MoE 收益。该组只改变同一流多重集的行顺序和端口分配，不是独立业务重复。

以候选自身 FCT 降序取前 1%（192 或 128 条背景均为前 2 条）：原始 192 档哈希、RR、自适应的前 2 条都到主机 **856**（目的 ToR **1378**）；随机是一条到 856、一条到 **576**（ToR **1346**）。20261103/128 的自适应和 DRILL 前 2 条分别到 576、856。以逐流 FCT 与 ECMP 配对，原始 192 档哈希最慢两条为 `1016→856` **+327.262 µs**、`740→856` **+242.425 µs**；RR 的 `176→856` **+638.788 µs**；自适应的 `656→856` **+450.108 µs**。20261103/128 的 DRILL 最慢 `356→856` **+399.377 µs**。CSV 保留完整流键、端点/ToR、各算法 FCT、尾部名次、同源 ToR 聚合 uplink 差和 MoE 前八热点 ToR 标志。目的端 856 在原始 192 档有 **7 条**背景流，576 也有 **7 条**；它们并非唯一有多流汇聚的目的端。上述定位是尾部贡献，不是因果分解。

所有格的 CNP 原始文件均有非零记录。按 `cnp_freq_monitoring` 的 `time,node,ECN,OoO,total` 逐行求和，原始 192 档全节点 ECMP 的 ECN/OoO/total 为 **1920/0/1920**，逐包哈希 **2852/19453/22124**，自适应 **1954/12739/14646**；20261103/128 ECMP **954/0/954**，自适应 **937/9633/10557**、DRILL **890/8608/9491**。ECN 与 OoO 可在一条反馈上重叠，不能简单相加。在尾流目的主机 856，原始 192 档 ECMP 的 ECN/OoO 为 **350/0**，逐包哈希 **602/0**、自适应 **608/0**；20261103/128 ECMP **222/0**、自适应 **254/0**、DRILL **310/0**。这使“拥塞反馈伴随尾部”的假说更具体，但它是**主机级、全 QP 聚合**，无法证明所列背景 QP 收到这些反馈；专家流的乱序计数也不能套到背景流。逐流 CSV 附上各目的主机的 ECN/OoO 聚合供复核。PFC 文件为空符合共同 PFC=0/IRN=1 契约。路由计数证明各新模式在源 ToR 的 MoE 包多路径选择确实触发，但它是模式级合计，不能证明某条背景尾流与某个 MoE 包共享出口。`_out_uplink.txt` 也是 ToR/端口的 10 ms 累计发送量，不含逐包路径与亚毫秒排队。物理 MMU 队列、可靠的逐 QP NACK/重传/超时计数仍缺。背景尾流与 MoE 热点、ToR uplink、CNP 的同时出现只能构成可测试假说。

[权衡图](evidence/ws13-tradeoff.svg)用同组同档 **背景 P99−ECMP P99** 为横轴（µs，越左越好），**ECMP MoE 批次−候选批次** 为纵轴（µs，越上越好），每模式以 64→128→192 连接；原始组深色，四个顺序组淡色。图上的线是总负载随背景追加而增加的离散档位连线，**不是连续负载插值、独立样本置信带或 Pareto 最优证明**。它保留了两侧的绝对量与负区域，避免把任一百分比事后变成安全线。

## 成熟方案评价口径与可比边界

| 原始来源 | 场景与指标实际口径 | 本项目可借鉴之处及不可照搬之处 |
| --- | --- | --- |
| [DRILL, SIGCOMM 2017](https://pbg.cs.illinois.edu/papers/ghorbani17drill.pdf) §4 | OMNeT++/Linux TCP，2/3 级 Clos、实际流大小/到达分布与 incast；报告 FCT、吞吐、队列时间、极尾 FCT、TCP dupACK/乱序及故障/非对称场景；和 ECMP、CONGA、Presto 对照。 | 借鉴负载梯度、短流尾部与长流吞吐、排队/乱序诊断、强对照。其 TCP dupACK/GRO 与本项目 RDMA IRN 不同，1.3× 等改善不是安全阈值。 |
| [ConWeave, SIGCOMM 2023](https://cse.hkust.edu.hk/~kaichen/courses/spring24/comp7215/papers/conweave-sigcomm23.pdf) §4 | ns-3 叶脊 RDMA，AliCloud/Meta 流大小、Poisson 到达，50/80% 负载；DCQCN 下分 lossless 与 IRN；报告均值和 P99 FCT slowdown、按流大小分组、ToR uplink 不均衡、VOQ 数/内存，硬件试验报告绝对 FCT 与尾部。 | 共同 DCQCN/IRN、同输入 ECMP/DRILL 对照和 FCT/资源双侧指标最接近；其 VOQ 是 ConWeave 重排缓存，不能代本项目物理 MMU 队列。其 100G、2:1、到达过程与本项目 400G、同步 MoE 不同，论文改善幅度不作门槛。 |
| [Presto, SIGCOMM 2015](https://conferences2.sigcomm.org/sigcomm/2015/pdf/papers/p465.pdf) §5 | 10G TCP/虚拟交换机 testbed；吞吐、RTT、50 KB mice 的应用层 ACK FCT、丢包、公平性，10 s × 20 次；评估 GRO 对乱序与 CPU 的影响、不同流量图和拓扑不对称。 | 借鉴短流和长流业务分侧、可见重排/CPU 代价、多次运行；64 KB flowcell+GRO 属 TCP 端侧实现，不能当成本项目 RDMA 逐包策略或设定 5% 容忍度。 |
| [SeqBalance, arXiv 2024](https://arxiv.org/pdf/2407.09808) §IV | RoCE testbed 与 ns-3：ECMP/LetFlow/CONGA/DRILL，DCQCN、AliCloud/WebSearch、30–80% 负载；FCT slowdown、均值/P99 与 uplink 不均衡，同时讨论 QP 数成本和乱序；其模拟 PFC=on。 | 借鉴 RDMA 强对照、逐流大小及 QP/反馈开销；与本项目 PFC=0/IRN=1、同启负载和实现信息预算不同，不搬用 18.7%/33.2% 为收益线。 |

这些文献共同支持**同时报告绝对与相对 FCT、按大小/业务类别分组、尾部分位、吞吐/批次、队列与重传/乱序、资源成本、负载与拓扑敏感性**。本项目当前 MoE 全为 8 KiB、背景全为 8 MiB，所谓“小/大流”首先只是这两个构造类别；背景 8 MiB 的完成时间和有效吞吐应并列，不能把它当 50 KB TCP mice。`synthetic_batch_completion_us` 是同一批末流完成时刻，不是真实 MoE 轮次依赖的 job CCT。所有百分比阈值须由本项目独立校准波动与真实业务可接受损害共同论证；目前仓库未见可核验 MoE 或背景生产 SLO，因此新正式安全数值 **未定义**。

## 独立校准与未来正式验证的预注册草案

`scripts/make_ws13_calibration_traces.py` 已按种子 `20261301/02/03` **独立重抽** 256 个 MoE 专家主机、每源 64 个不同目的端及 192 对背景端点，生成三个互不相同的六列需求 trace，清单/哈希在[校准 manifest](evidence/ws13-calibration-traces.json)。这不是旧需求行顺序置换；它保持原生成器的 rail-0 主机池、16,384×8 KiB 同启 MoE、192×8 MiB 同启背景及 ADR-008 的追加负载语义。六格校准已由[原始核验脚本](../../scripts/analyze_ws13_calibration.py)逐 ID 复核完成，固定仿真源码 `6a1de1d9c8c9ea3ac41921230e05d87ccda93b9d`，每 trace 内 ECMP 与本 fork DRILL 共享字节级同一 trace、拓扑、DCQCN/PFC=0/IRN=1、simulator seed=1；顺序按 ECMP→DRILL、DRILL→ECMP、ECMP→DRILL 交替。三个 ECMP 背景 P99 为 **1292.771、2179.572、2127.727 µs**（范围 886.801 µs），MoE 批次范围 **17.614–20.662 µs**。DRILL 对同 trace ECMP 的背景 P99 配对差为 **−30.986、−48.140、−5.212 µs**，MoE 批次差 **−0.273、−0.477、−2.073 µs**；全量收据见[校准摘要](evidence/ws13-calibration-summary.json)和忽略目录 `results/ws13-calibration-plan.json`、`results/ws13-calibration-receipts.jsonl`。这只测本场景 ECMP/强对照在**需求重抽**下的变动，不测试新机制；三个 trace 的跨输入波动显著大于本次 DRILL 背景配对差，不能把三点极值当预测区间、把负差称普遍安全或由此导出通用百分比线。校准 trace ID 永不用于 WS-15 正式验证。

未来 WS-15 每个独立需求 trace 才是推断重复单位；每组重抽业务需求并冻结输入文件 SHA，同档所有算法逐字节共用它，固定 DCQCN/PFC=0/IRN=1、seed 和拓扑，以阻断/配对估计 **MoE 批次相对同档 ECMP 的变化**、**背景绝对 P99/逐流尾部相对同档 ECMP 的代价**。按 ADR-008 固定该组 MoE 的端点、大小和时刻，背景 0/64/128/192 嵌套追加，明确每档总字节。运行顺序在每 trace 内用事先记录的 RNG seed 平衡；旧四顺序置换只作敏感性，不作独立样本。首要对照为 ECMP；同信息预算的普通双候选与已实现 DRILL 分层报告，不把使用不同反馈的模式叫纯机制消融。记录模式级/每包状态读取、计数器存储、额外消息、决策路径成本，以及完整 FCT/反馈/排队原始数据。可做 64/128/192 的**连续权衡、不同尾部分位和不同候选容忍度的灵敏度曲线**；业务 SLO 缺失期间不宣布某个线为“安全”。正式验证的独立 trace 数、收益幅度、安全门槛、统计规则与停止规则必须在新机制跑正式格前冻结，校准数据只用于设计，不参与确认性估计。

## 可证伪机制与停机门槛

## 最小同输入诊断探针结果

默认关闭的 `--ws13-diag 1` 观测补丁已在固定输入上验证。关闭探针的原始 192 档 ECMP 和开启探针的对应格 FCT SHA 均为 `9d600f055044d50a20ed0d036552922c9de916665af5a44a6791e77a755038e1`，与 WS-12 原格相同。开启探针的原始 ECMP、自适应及 20261103/128 ECMP、DRILL 四格也都与各自 WS-12 参考 FCT SHA 完全一致；四格日志分别为 15.57/15.61/13.59/13.62 MiB，未配对队列包均为 0。实验 ID、逐格 SHA 和压缩后的流/逐跳细节见[探针分析 JSON](evidence/ws13-feedback-probe-analysis.json)；独立 runner 为 [`run_ws13_probe.py`](../../scripts/run_ws13_probe.py) 与 [`run_ws13_feedback_probe.py`](../../scripts/run_ws13_feedback_probe.py)，关闭/开启首格和两格旧补测收据在忽略目录 `results/ws13-probe-receipts.jsonl`，新版四格收据在 `results/ws13-feedback-probe-receipts.jsonl`。

原探针把所有 `l3Prot=0xFD` 反馈标成 `nack`，但 IRN 下该协议号也用于完成 ACK。追加 `irn_nack_size` 字段并以 `irn_ack`/`sack` 区分后，原始 192 档 ECMP、自适应及 20261103/128 ECMP、DRILL 四格的目标背景 QP 分别出现 117,446/117,446/100,668/100,668 个 IRN ACK 和 **0 个 SACK**；CNP 事件分别为 **751/881/500/580**，没有证据把这些 CNP 归为乱序 SACK。每格最慢两条 8 MiB 背景流在目的 ToR 出口都观测到排队：ECMP 192 档 ToR 1346/port 1 的最大等待约 3.62 µs、排队前队列字节峰值 186,544 B；自适应同档 ToR 1378/port 7 约 3.99 µs、198,192 B；20261103/128 的 ECMP 与 DRILL 对应出口最大等待约 3.14/3.30 µs、队列峰值约 161,452/166,692 B。探针只统计目的主机 856/576 的 tag=1 流；它证明这些慢流经过并排队于目的出口，且同一 QP 收到 CNP，但单 seed 的排队摘要与 FCT 并存仍不是因果分解，也不能推出队列是唯一瓶颈。

**事件口径修正：**旧版 `event=nack` 行不作为真实 NACK/丢包证据。新版目标 QP 未观测到 SACK；这些格的 OoO/SACK 假说在所选背景流上没有得到支持，先前目的主机聚合的 `OoO=0` 与此一致。代码中 IRN+Qbb 路径在 `HandleTimeout` 的观测日志前提前返回，因此本轮没有有效的逐 QP timeout 计数，不能据缺行宣称无超时。仍缺逐包 ECN 标记、MMU 物理队列占用、端到端拥塞窗口/即时发送速率；当前队列量是排队前真实出口队列观测，不是 MMU 总 buffer。若后续解释依赖 timeout，需另做不改传输行为的精准观测。

## 新判据与下一步边界

用户确认**暂无可核验业务 SLO**。成熟方案研究只支持并列呈现绝对与相对 FCT、按业务类分组的尾部、长流完成时间/吞吐、队列/重排与资源开销；不同 TCP/RDMA、拓扑和负载论文的改善百分比不能当本项目安全线。三个独立需求 trace 的 ECMP 背景 P99 范围为 886.801 µs，而同输入 DRILL 配对差 −5.212 至 −48.140 µs；它们只能说明该校准样本下的波动，不能由三点设通用界值。

因此 WS-13 保留连续 MoE—背景权衡及多种候选容忍度的灵敏度曲线，不定义新的通用安全百分比，也不改 WS-10/11/12 的预注册 5% 规则或 no-go。下一步若做 WS-14，只能作为研究性单机制小样，先声明研究者选择的候选损害曲线，不称业务安全门槛；需围绕目的 ToR 出口排队和每 QP CNP 对照 ECMP/DRILL，并明确 timeout 与物理队列观测缺口。若没有清晰双侧研究问题，则停止新机制效果矩阵，按解释性负结果收束。
