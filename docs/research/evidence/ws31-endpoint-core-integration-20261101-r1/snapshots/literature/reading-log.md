# 毕业论文文献累计阅读记录

建立日期：2026 年 10 月 10 日。每篇完成独立全文阅读后，按统一格式追加编号机制标题、论文题目、发表信息、内容总结、经验学习、项目适用、硬件依赖与边界，以及阅读日期、完整报告和核验链接。保留原有结论与证据边界，按论文身份和版本去重。

初筛、下载全文或预读都不计作完整阅读。下列条目均在独立全文阅读完成后核验归档。

## 1. DiffFlow：类别决定分配粒度

论文题目：《DiffFlow: Differentiating Short and Long Flows for Load Balancing in Data Center Networks》。作者为 Francisco Carpio、Anna Engelmann 和 Admela Jukan。完整阅读版本是 arXiv:1604.05107v1，2016 年，全文 6 页。

### 发表信息

正式发表：2016 IEEE Global Communications Conference（GLOBECOM）。CCF 第七版（2026）：计算机网络 C 类会议；本篇 Full／Regular paper 资格待核实。最早公开：2016-04-18（arXiv v1 首次提交）。正式出版：2016-12（Crossref 出版年月）；首次在线／收录日待核实。CCF 类别属于 venue 推荐类别。日期按实际证据精度保留，不将 DOI 创建日或会期当作出版日。来源：[早期版本](https://arxiv.org/abs/1604.05107v1)、[正式记录](https://api.crossref.org/works/10.1109%2FGLOCOM.2016.7841733)、[CCF 官方目录](https://www.ccf.org.cn/Academic_Evaluation/CN/)。核验细节见 [本篇记录](papers/diffflow-2016/verification.md)。

### 内容总结

论文研究短流时延与长流吞吐的冲突。ECMP 将整条流固定到一路，两条大流可能持续碰撞。DiffFlow 让新流先走 ECMP。ToR 周期抽样再次看到同一条流后，通知 SDN 控制器。控制器先安装中间规则，再让源 ToR 对长流逐包随机喷洒。短流继续固定路径。可以把它理解为小车保持路线，大车队分散道路；这个类比属于阅读解释。

作者使用自建 Java 模拟器，对比 ECMP、RPS 与 DiffFlow。实验省略 TCP，丢包后等待 RTT 重传，并为两类流设置独立队列。正文称，高负载时总平均 FCT 相对 RPS 约改善 7%；短流平均 FCT 约改善 15%，吞吐与 RPS 接近。这些是归一化模型结果，未报告 P99、训练批次或真实 RDMA 收益。

### 经验学习

学习重点是按业务目标决定分路粒度，以及将识别、规则安装和接收代价一起计量。论文没有报告抽样周期与控制延迟，也没有共享队列消融。独立队列是否在三臂完全一致，原文未充分说明，因此既不能忽略队列条件，也不能直接认定基线不公平。理论还存在路径概率记号和有限包数路径覆盖的疑点。

### 项目适用

对本项目，应保留混合粒度的相关工作价值，分别审查机制与效果迁移。两类业务都是 RDMA QP，目标是 MoE 合成批次与背景 P99 共同改善，不能机械照搬“长流宽松、适合喷洒”。类别标签也不等于抽样得到的长流标识。现有 ClassLane 划分类别路径集合，与 DiffFlow 的混合转发不同。

### 硬件依赖与边界

硬件方面，ns-3 可以表达分类事件、规则生效延迟和成本，却无法证明交换机抽样、OpenFlow 动作、规则容量或网卡乱序能力。建议将本文保留为机制相关候选，优先学习条件分离和延迟计量；不直接移植算法。会议 DOI 已核对元数据，但未阅读会议最终正文。本次没有改算法、启动仿真或干预 WS-26。

阅读日期：2026 年 10 月 10 日。参见 [完整通俗报告](papers/diffflow-2016/analysis.md)与 [核验记录](papers/diffflow-2016/verification.md)。

## 2. DeFlow：差异换路与拥堵缓解

论文题目：DeFlow: Differential flowlet switching for load balancing in datacenter networks。Wan 等，Computer Networks 257（2025），110980，DOI：10.1016/j.comnet.2024.110980。

### 发表信息

正式发表：Computer Networks 257（2025），110980。CCF 第七版（2026）：计算机网络 B 类期刊；正式研究论文。最早公开：2024（SSRN 预印本公开年份；具体月日待核实）。正式出版：2024-12-09（正式稿首页 Available online）；卷期为 2025-02。CCF 类别属于 venue 推荐类别。日期按实际证据精度保留，不将 DOI 创建日或会期当作出版日。来源：[早期版本](https://api.crossref.org/works/10.2139%2Fssrn.4934997)、[正式记录](https://doi.org/10.1016/j.comnet.2024.110980)、[CCF 官方目录](https://www.ccf.org.cn/Academic_Evaluation/CN/)。核验细节见 [本篇记录](papers/deflow-2025/verification.md)。

### 内容总结

DeFlow 研究大、小流共享多路径时的拥堵与乱序。它根据近期包长和包间隔做平滑分类。拥堵时，大流立即尝试换路，小流则等待足够的发送空档。可以把它理解为先移走占路较多的大车队，让短车队保持顺序通过。这个类比是阅读辅助，并非作者实验。作者用 32 台服务器、10 Gbps 的 ns-3 网络评估六组流量与拓扑搭配。结果主要支持平均 FCT 和大流吞吐改善，RPS 在部分小流指标上仍更快。

### 经验学习

负载均衡应同时考虑流量贡献、类别目标和迁移代价。自然间隔不足时，主动迁移有机会缓解排队，也可能产生较深乱序。低乱序比例不能独立证明低恢复成本。性能比值需带上场景和指标；平均 FCT 也不能替代尾部或批次完成时间。论文缺少分类准确率、组件消融和明确传输配置，α／β、算法分支及 50／100 µs 间隔还有待确认。

### 项目适用

建议保留为类别差异调度的重点相关工作，以及条件性的机制候选。本项目的 MoE 与背景流都使用 RDMA QP，分别关注合成批次时间与背景 P99。论文的大／小流不是业务标签，不能直接套用分类阈值和吞吐／时延分工。可借鉴平滑状态、差异迁移、消融及接收成本联合分析，收益须由同传输契约下的双指标证明。

### 硬件依赖与边界

Tofino 部分只报告 P4 原型资源，不提供真实网络性能和线速压力结果。本项目只有 ns-3，无法验证网卡或交换机部署。全文 14 页、算法及全部图表已核对；本次未复现，也未修改算法、启动仿真或干预 WS26。证据与未解决项见同目录技术附件、evidence.csv 和 verification.md。

阅读日期：2026 年 10 月 10 日。参见 [完整通俗报告](papers/deflow-2025/analysis.md)与 [核验记录](papers/deflow-2025/verification.md)。

## 3. SeqBalance：拆分粒度、连接顺序与反馈成本

论文题目：SeqBalance: Congestion-Aware Load Balancing with no Reordering for RoCE。阅读版本：arXiv:2407.09808v1。

### 发表信息

正式发表：IEEE Internet of Things Journal 12（13），2025，25707～25719。CCF 第七版（2026）：计算机网络 C 类期刊；正式期刊记录，最终正文未比对。最早公开：2024-07-13（arXiv v1 首次提交）。正式出版：2025-07-01（正式卷期出版）；首次在线日待核实。CCF 类别属于 venue 推荐类别。日期按实际证据精度保留，不将 DOI 创建日或会期当作出版日。来源：[早期版本](https://arxiv.org/abs/2407.09808v1)、[正式记录](https://api.crossref.org/works/10.1109%2FJIOT.2025.3559878)、[CCF 官方目录](https://www.ccf.org.cn/Academic_Evaluation/CN/)。核验细节见 [本篇记录](papers/seqbalance-2024/verification.md)。

### 内容总结

本文精读固定的 arXiv:2407.09808v1（2024 年），共 12 页。SeqBalance 研究商用 RoCE 的负载均衡粒度。整条流固定选路容易碰撞；逐包分路又可能引起 QP 内乱序和重传。作者在用户态 RDMA 驱动中加入 Shaper，将一个发送请求拆成多个子请求，交给不同 QP。每个子流固定走一条路径，发送端等待全部子请求完成，再向应用返回整体完成通知。

源 ToR 为新子流选路。目的 ToR 看到 ECN 标记后，回传拥塞报文。源端暂时禁止新子流进入该路径，默认保留 32 μs，已有子流仍沿原路传输。这个时间是状态保留期，不能当成反馈延迟。论文的“没有乱序”主要针对子 QP 内的路径差异，未证明跨 QP 或整条业务全局保序。

论文在 CX-6 与 Tofino 上展示小规模端口吞吐，在 ns-3 中比较存储和搜索负载的 FCT。摘要的 18.7% 和 33.2%，分别出现在三层仿真的不同工作负载中。实验没有验证 MoE 批次与背景 P99 的双侧改善。表格和图中还有消息大小矛盾、指标标签错误；仿真也未完整交代 IRN、重传参数和统计重复。

### 经验学习

值得学习的是先确定协议的顺序单位，再选择分路粒度；把拆分数量、完整请求完成时间和资源成本一起分析。应同时观察最后完成的子请求和原批次拖尾，避免只统计完成较快的部分。端口更均衡也须结合乱序、恢复和两类完成时间解释。论文已核验 2025 年 IEEE Internet of Things Journal 正式出版记录，但未比对最终正文。

### 项目适用

对本项目，可借鉴子 QP 固定路径、父子请求身份守恒，以及反馈年龄和通信成本的审查方法。存储／搜索的大小流不能直接对应 MoE／背景类别。建议保留为机制与评估方法参考，暂不据此选定新算法。

### 硬件依赖与边界

项目只有 ns-3，无法自然复现驱动改造、真实 QP 缓存或 Tofino 流水线成本。

阅读日期：2026 年 10 月 10 日。参见 [完整通俗报告](papers/seqbalance-2024/analysis.md)与 [核验记录](papers/seqbalance-2024/verification.md)。

## 4. PSP：陈旧状态下的概率化逐包选路

论文题目：*PSP: Low-Overhead Packet-Level Load Balancing for Stale-State and Bandwidth-Asymmetric Networks*。作者为 Jiaqi Liu、Chunyang Zhang、Heng Pan 和 Yanbiao Li。本文精读固定版本 arXiv:2608.08425v1，全文 12 页。

### 发表信息

正式发表 venue 为 IEEE LCN 2026；按 CCF 第七版（2026）计算机网络类别为 C 类会议；本篇 Full／Regular paper 资格待核实。最早公开日期为 2026-08-09（arXiv v1 首次提交）。IEEE Xplore 记录的加入日期为 2026-09-07；会议举办日期另行核对。论文已被 IEEE LCN 2026 接收，DOI：10.1109/LCN67947.2026.11660801。本次没有逐页比对最终版。

### 内容总结

PSP 将出口队列深度划分为若干 Band，再按 Band 分配权重。队列较短的端口更容易被选中，但调度器仍以概率把包分散到其他路径，避免多个发送者同时追逐少数“最空”出口。作者在自建包级周期精确模拟器中评估两层 Clos，使用 400 Gbps 链路、4 KB 调度粒度、20 μs 默认状态延迟、100%负载及 128～512 个 GPU 规模。结果显示，PSP 在多种场景下减少队列分位数；表格报告的丢包也少于 JSQ，并在部分场景优于 Random 和 Top-k。图 7 显示 Band 数从 4 增到 8 后平均队列下降，继续增加时收益趋于饱和。硬件面积比例是作者的门等效估算，不是芯片测量。

### 经验学习

可借鉴的问题是：面对陈旧反馈，概率化的队列偏好能否减少同步追逐；面对链路速率差异，调度器能否避开持续受限路径。适用于 ns-3 的方法包括扫描反馈年龄、路径容量和调度粒度，并观测队列、丢包及实际乱序代价。

### 项目适用

PSP 与本项目类别感知包／流混合机制不同；必须在相同传输条件下，检验 MoE 合成批次完成时间和背景 P99 FCT 两项结果。队列 P99 只能作为乱序压力代理，不能取代直接乱序与恢复测量。

### 硬件依赖与边界

论文讨论 RDMA、RoCEv2 和 NIC 重排能力，但实验没有实现 RDMA QP、主机协议栈或真实网卡。作者以队列占用间接表示重排压力，并承认该指标不等于 NIC 重排缓存。自建周期精确模拟器也不替代 RTL 综合和时序分析。arXiv 提供 TeX 源码，本次没有找到实验代码、固定流量 trace、逐图原始数据或完整复现脚本。正文与表 IV 对默认权重的写法还存在一位差异。该论文适合作为机制候选与评估设计参考；论文效果不能外推为本项目收益。

阅读日期：2026 年 10 月 11 日。详见[技术分析](papers/psp-2026/analysis-technical.md)、[证据表](papers/psp-2026/evidence.csv)和[核验记录](papers/psp-2026/verification.md)。

## 5. Ofan：按目的地分散流量

论文题目：《Load Balancing for AI Training Workloads》。McClure 等，阅读版本为 arXiv:2507.21372v2，全文 23 页。

### 发表信息

目前按预印本归档，正式会议／期刊 venue 和出版日期待核实。最早公开日期为 2025-07-28（arXiv 首次提交）；v2 于 2026-02-13 修订。预印本不赋予 CCF 会议／期刊类别。

### 内容总结

论文研究同步训练中的多路径分配。作者发现，两个出口的总流量一样，也可能让发往同一目的地的数据挤在某个方向。可以类比为两条出城道路都很忙，但去同一个片区的车仍集中在一路。这个类比用于解释，并非作者实验。Ofan 按目的地轮转数据包，并利用网络中的必经节点合并调度记录。作者先分离选路、丢包恢复和拥塞控制，再逐步补回现实机制。结果主要支持规整训练通信中的细粒度分路。

### 经验学习

学习重点是按目的地检查上行和下行，而非只看本地总量。衡量一轮通信，还应关注最后完成者。图中的“约 52 倍”针对超过理想下界的额外开销，不是整个通信或训练提速。模型中的平均队列性质，也不保证任意时刻没有长队。图 18 的比值方向与正文解释存在矛盾，原报告保留疑点，没有自行修正。

### 项目适用

本项目可用 ns-3 表达目的地轮转，并分开观察选路、乱序和恢复代价。两类业务均为 RDMA QP，仍须共同检查 MoE 合成批次完成时间与背景 P99 FCT。论文的隔离、同步、近似均匀条件，不能直接代替混合业务验证。Ofan 分散同目的地流量，与 ClassLane 划分类别路径集合不同，也不等同于首次选路后缓存的 DestSpread。

### 硬件依赖与边界

交换机状态更新、流水线冲突和网卡乱序能力，须列为硬件边界。后稿 2610.07230 扩展了 Ofan，涉及 pOfan 和 P4 等内容，不能混入本篇 v2。完整复现材料尚未定位；本次未运行实验或干预 WS-26。参见 [通俗分析](papers/ofan-2025/analysis.md)与 [核验记录](papers/ofan-2025/verification.md)。

阅读归档：2026 年 10 月 12 日。参见 [完整通俗报告](papers/ofan-2025/analysis.md)、[技术附件](papers/ofan-2025/analysis-technical.md)和 [核验记录](papers/ofan-2025/verification.md)。

## 6. CONGA：沿路径拥塞反馈与 flowlet 选路

论文题目： *CONGA: Distributed Congestion-Aware Load Balancing for Datacenters*。

### 发表信息

**论文元数据：** ACM SIGCOMM 2014 主会 Full/Regular paper；CCF 第七版（2026）计算机网络 A 类。最早公开日期待核实；目前可核对的 Crossref 出版方在线日期为 2014-08-17。DOI：10.1145/2619239.2626316。

### 内容总结

论文使用叶交换机之间的路径级拥塞反馈，为 TCP 流的 flowlet 选择上行路径。数据包沿途携带路径最大拥塞等级，目的叶将反馈通过反向包捎带给源叶；源叶再综合本地和远端拥塞，选择较轻路径。作者用 DRE 估计链路速率，并以 flowlet 空闲阈值控制切换粒度。论文报告其在不对称拓扑、重尾流量和故障情况下较 ECMP 有更好表现，也给出定制 ASIC、真实 TCP 测试床、包级模拟与两层 Leaf-Spine 理论分析。会议版的随机不均衡定理将证明指向长版，公式中最小负载符号还有一处不一致。



### 经验学习

本篇值得借鉴的是“本地出口指标未必揭示下游拥塞”。CONGA 的 flowlet 调度机制与项目探索的类别感知逐包/逐流混合机制不同。以及把反馈时效、量化精度、flowlet 阈值与乱序风险放在同一设计中验证。

### 项目适用

对项目而言，可在对称/故障拓扑与轻/重尾流量下检查沿途路径拥塞，并同时观察 MoE 合成批次完成时间、背景 P99 FCT 和乱序代价。原文使用 TCP，不评测 MoE、RDMA QP、背景 P99 或两类流的共同目标，故不能证明本项目收益。

研究方法论上，可学习作者同时使用真实测试床、包级模型和理论反例，再明确各自能回答的问题。在本项目中，应先固定拓扑、输入和传输条件，再分别改变反馈时效、切换粒度与路径容量；保留不改善或另一类退化的结果。还要把性能、机制覆盖和实现成本分开，避免出口更均衡就宣称业务完成更快。这是阅读者提出的实验设计借鉴，本次没有执行这些实验。

### 硬件依赖与边界

其 ASIC 面积、线速和生产部署效果属于硬件证据；当前 ns-3 环境不能验证这些主张。

阅读归档：2026 年 10 月 12 日。参见 [完整通俗报告](papers/conga-2014/analysis.md)、[技术附件](papers/conga-2014/analysis-technical.md)和 [核验记录](papers/conga-2014/verification.md)。

## 7. ConWeave：换路时由网络配合处理乱序

论文题目： *Network Load Balancing with In-network Reordering Support for RDMA*。

### 发表信息

**论文元数据：** ACM SIGCOMM 2023 论文集长文；CCF 第七版（2026）计算机网络 A 类。目录计入的 Full/Regular 资格待核实。最早公开日期待核实；出版方在线记录为 2023 年 9 月，纸本字段为 2023-09-10。DOI：10.1145/3603269.3604849。

### 内容总结

论文研究 RDMA 多路径换路时的乱序问题。flowlet 方法依赖发送空档，而 RDMA 网卡常连续发送；逐包喷洒又可能打乱到达顺序。ConWeave 在源端机架交换机监测往返时间和拥塞反馈。换路前，源端沿旧路发送一个 TAIL 包，再把后续包送到新路。目的端交换机暂存提前到达的新路包，等 TAIL 到达后通过暂停和恢复 FIFO 队列按序交付。它要求上一轮重排完成后才开始下一轮，所以通常每条流最多同时经过两条路径。TAIL 或 CLEAR 丢失时，方案用计时器恢复。

作者在 ns-3 中比较了多种负载均衡方案，并在小型 Tofino 测试床上测量 RDMA FCT。论文报告，在其 AliCloud Storage、80% 仿真负载下，平均和 P99 FCT slowdown 有改善；硬件测试则报告平均与尾部 FCT 收益。这些数字受拓扑、流量、PFC/IRN、RNIC 和对照范围约束。附录图 21 的误差坐标与图注对正负号的解释相反，引用该图时应注明疑点。

### 经验学习

这篇论文最直接的项目价值是帮助维护忠实的 ConWeave 基线。复核其结果时，应检查真实路由入口、源端反馈和目的端 VOQ 重排，而不是把它简化成普通逐包选路。本文的 RTT 反馈、换路阶段标记、FIFO 恢复与计时器也提供了检查状态机和重排代价的分析方法。

### 项目适用

本项目两类业务均使用 RDMA QP，关注 MoE 合成批次完成时间与背景流 P99 FCT，并需观察乱序代价。论文没有测量此类混合负载，也没有给出本项目收益证据。因此保留为基线及方法参考，不据此准入新机制。项目现有源码和固定实验 ID 的原始数据仍是判断实现与效果的最终依据。

### 硬件依赖与边界

论文依赖 Tofino 的队列暂停/恢复、数据面状态操作和 P4 时序。ns-3 可以研究逻辑换路与队列模型，不能证明芯片资源、线速执行、真实 RNIC 恢复反应或大规模部署效果。本次已读完固定 PDF 全 16 页并核验 25 幅图与 5 张表；未运行仿真或修改项目代码。

阅读归档：2026 年 10 月 12 日。参见 [完整通俗报告](papers/conweave-2023/analysis.md)、[技术附件](papers/conweave-2023/analysis-technical.md)和 [核验记录](papers/conweave-2023/verification.md)。

## 8. HULA：逐跳探测与目的地引导选路

论文题目： *HULA: Scalable Load Balancing Using Programmable Data Planes*。

### 发表信息

**论文元数据：** ACM SOSR 2016 会议论文；CCF 第七版（2026）领域为计算机网络，类别与 Full/Regular 资格均待核实。最早可核实的出版方在线日期及正式出版日期为 2016-03-14。DOI：10.1145/2890955.2890968。

### 内容总结

作者为 Naga Katta、Mukesh Hira、Changhoon Kim、Anirudh Sivaraman 和 Jennifer Rexford。

HULA 让每个交换机为目的 ToR 只保存当前最佳下一跳和路径最大利用率。周期探测包沿网络传播利用率摘要，使流量尚未经过的路径也能提前进入路由表。数据按 flowlet（流段）切换：只有相邻包间隔超过阈值，交换机才为后续流段重新选路。论文还用过期探测表项发现链路故障。这样做可减少全路径状态，并尽量避免逐包换路带来的乱序。代价是交换机不保留其他候选路的实时状态，短时间内可能继续使用次优路径。

作者在 ns-2 的三层 Fat-Tree 和 TCP 客户端/服务器模型中评估 HULA。实验采用 Web-search 与 data-mining 流大小分布，每组运行 3 个随机种子并取平均。论文报告，高负载和链路失效时，HULA 的平均及 P99 FCT 多数优于 ECMP 和 CONGA'。其中 Web-search 在 60% 负载下，ECMP 与 HULA 的 P99 FCT 比值约为 10；data-mining 对应比值约为 1.53。这些数字只适用于论文的拓扑、流量和 TCP 条件。

### 经验学习

值得学习的是沿路径追踪瓶颈、测量反馈到达选路点所需时间，并同时核算探测带宽和每目的地状态量。论文把路径最大利用率作为摘要，便于从逐跳信息中提取瓶颈线索。

### 项目适用

本项目研究类别感知的逐包/逐流混合选路；MoE 合成批次完成时间与背景 P99 FCT 是双主指标，两类流均为 RDMA QP。HULA 按目的地逐跳选择 flowlet，使用 TCP 接收语义，没有项目的类别区分或批次目标。因此，它适合作为逐跳诊断和状态规模的方法参考，不构成本项目算法准入或收益证据。全文、9 幅图和表 1 已核验；没有复现实验或修改代码。

### 硬件依赖与边界

P4 条件写入与芯片面积结论依赖特定数据平面操作。项目仅使用 ns-3，没有真实 NIC 或交换机，不能验证论文的芯片面积和生产部署结论。

阅读归档：2026 年 10 月 12 日。参见 [完整通俗报告](papers/hula-2016/analysis.md)、[技术附件](papers/hula-2016/analysis-technical.md)和 [核验记录](papers/hula-2016/verification.md)。

## 9. Proteus：PFC 反馈下的无损网络负载均衡

论文题目： *Enabling Load Balancing for Lossless Datacenters*。

### 发表信息

**论文元数据：** IEEE ICNP 2023；CCF 第七版（2026）计算机网络 B 类。论文类型资格按已有核验记录注明为待核实。最早可核实的作者机构公开／出版记录为 2023-10-15；Crossref 的 2023-10-10 字段与会期重合，存在日期语义疑点。DOI：10.1109/ICNP59255.2023.10355615。

### 内容总结

Jinbin Hu 等人研究启用 PFC 的无损数据中心网络。论文发现，PFC 暂停会改变常见拥塞信号的含义：链路利用率变低可能表示发送被暂停；RTT 和 ECN 要经过端到端反馈，可能在暂停结束后才到达；本地队列也不一定能看见下游的暂停。Proteus 先用 RTT 与链路利用率把路径分成未拥塞、拥塞和状态不明三类，再看每个包在交换机内已经等待多久。短暂停时先容忍等待，等待超过可容忍额度后才沿包头备用路径换路，以减少持续队头阻塞。边缘选择路径时还限制额外传播时延，照顾同一流的包顺序。

论文使用 Wedge 100BF-32X P4 交换机、8 台服务器和 DCQCN 建立测试床；另用 ns-3 模拟 128 台主机、8×8 leaf-spine、PFC 与四类重尾流量。作者报告了平均 FCT、P99 FCT、阻塞流比例和乱序包比例的改善，也检查链路速率、RTT 分类阈值与备用路径数。硬件测试依赖 P4 流水线、PFC、路径反馈、源路由和 RNIC 接收重排能力；竞争比结论则假设暂停最终结束且只比较固定延迟路径。



### 经验学习

适合借鉴的方法是先用构造场景定位信号为什么误判，再逐层加入端到端反馈、换路代价和多种工作负载，分别观察平均与尾部指标。

### 项目适用

项目两类流均为 RDMA QP，主要关注 MoE 合成通信批次完成时间和背景 P99 FCT，并把乱序作为代价。Proteus 提供“低利用率是否由暂停造成”“换路等待如何影响乱序”的可检验问题，但没有测量项目的双主指标，论文百分比不能写成项目收益。它是方法参考，不构成新机制准入或最终引用结论。

### 硬件依赖与边界

论文测试床依赖 Wedge 100BF-32X P4 交换机、PFC、源路由和 RNIC 接收重排。项目只有 ns-3，可以评估简化模型中的信号判断与等待代价，不能验证芯片资源、真实网卡行为或生产时序。

阅读归档：2026 年 10 月 12 日。参见 [完整通俗报告](papers/proteus-2023/analysis.md)、[技术附件](papers/proteus-2023/analysis-technical.md)和 [核验记录](papers/proteus-2023/verification.md)。

## 10. Gemma：路径感知选路与接收侧重排

论文题目： *Gemma: Robust and Path-aware Loading Balancing in RDMA Networks*。

### 发表信息

**论文元数据：** IEEE HPCC 2024；CCF 第七版（2026）计算机体系结构／并行与分布计算／存储系统 C 类。Full/Regular 资格待核实。最早公开日期及正式出版日待核实；Crossref 日期与会议开始日重合，不能据此确认出版时间。DOI：10.1109/HPCC64274.2024.00151。

### 内容总结

Jiuyi Liu、Zhen Zhao 和 Dongzhan Zhang 在 HPCC 2024 论文中提出 Gemma，处理 RDMA 网络逐包选路引起的乱序，以及 PFC 暂停相关拥塞。Gemma 用本地上行出口队列和同步来的远端下行出口队列计算路径分数，拥塞时逐包换到更畅通的路径。接收侧交换机以 DATA、END 标记阶段，在不同优先级队列中暂存早到包；旧阶段结束后再恢复新队列，从而在包到主机前整理顺序。作者在 ns-3 叶脊及 Fat-Tree 场景中报告平均与 P99 FCT slowdown、吞吐和队列数改善；80% 负载下，叶脊平均 slowdown 相比 ConWeave、CONGA、ECMP 分别改善 6%、35%、57%，P99 slowdown 分别改善 8%、56%、67%。更积极的改路也提高队列需求：80% 负载下，99% 案例占用低于 6 队列，极端值为 13。论文没有给出完整可复现材料、随机种子和统计区间；真实交换机实现明列为未来工作。

作者把路径选择、反馈同步和接收侧重排放在同一机制中，评估时同时报告平均与 P99 slowdown、吞吐不均衡、有效吞吐和队列数量。这样的指标组合能避免只看平均 FCT 而漏掉乱序整理成本。由于论文没有公开随机种子、原始流记录和置信区间，复核时应把这些数字标为作者报告，不能当作可独立复算的统计证据。

### 经验学习

方法论上，值得学习的是将改路收益、重排代价、路径反馈时效及队列资源放在同一评估中，并报告高负载尾部和极端值。

### 项目适用

对本项目而言，可借鉴远端路径状态观测和乱序代价核算；Gemma 本身不按类别隔离流量。项目两类流均为 RDMA QP，主要结果是 MoE 合成通信批次完成时间和背景 P99 FCT；论文没有验证这组业务和指标。

对本项目可照此拆分机制链路，逐项观测路径状态何时更新、哪些包被暂存、批次完成和背景尾部如何变化；随后用多个负载与参数检查结果是否稳定。

### 硬件依赖与边界

论文没有实现真实交换机，相关硬件实现仍属未来工作。项目仅使用 ns-3，不能验证芯片实现或生产部署表现。

阅读归档：2026 年 10 月 12 日。参见 [完整通俗报告](papers/gemma/analysis.md)、[技术附件](papers/gemma/analysis-technical.md)和 [核验记录](papers/gemma/verification.md)。

## 11. AG：按路径时延差自适应调整分组粒度

论文题目： *AG: Adaptive Switching Granularity for Load Balancing with Asymmetric Topology in Data Center Network*。

### 发表信息

**论文元数据：** IEEE ICNP 2019 主会 Long paper，列入 FullPapers；CCF 第七版（2026）计算机网络 B 类。最早可核实公开记录为 2019-09-04；正式出版日期目前只能确认到 2019 年 10 月，具体日待核实。DOI：10.1109/ICNP.2019.8888076。

### 内容总结

AG 研究多路径时延不一致时，如何在链路利用和包乱序之间调整负载均衡粒度。论文把一个 TCP 拥塞窗口内的连续包组成包列，并由叶交换机周期性测量源叶到目的叶的路径时延。路径差异较小时，AG 使用较短包列；路径差异较大时，增加包列长度，以减少乱序。作者再用简化模型估算不同长度的速率，通过搜索选择当前粒度。论文结合 NS2 大规模仿真与 BMv2/P4、Mininet 小型测试，报告其平均和尾部 FCT 优于所比较方案。



这个分析框架比只比较一个平均 FCT 数字更容易解释因果，也能暴露细粒度策略的代价。主要指标是 MoE 合成通信批次完成时间和背景 P99 FCT，乱序是代价约束。AG 没有研究这类业务组合，也没有评测 ConWeave，因此只能作为方法参考。若后续借鉴其自适应思路，应独立验证 RDMA 的乱序与拥塞反馈成本，并同时检查两个主指标；不能把论文报告的 FCT 改善当作项目收益。本文已逐页读完，报告区分原作者结果与项目分析判断；本次未独立复现，也未修改研究代码。还应检查路径状态的测量误差和采样间隔，说明机制何时能及时感知变化；比较不同方案时，同时给出场景、对照与指标定义。

本篇也提示，论文应把路径状态的测量误差和采样间隔纳入论证，并说明机制何时能及时感知变化。

### 经验学习

可借鉴的科研方法是：让路径不对称程度成为可控变量，分层比较不同粒度；同步记录路径利用、乱序、传输恢复和最终完成时间；再用测量精度与采样周期实验检查反馈滞后。复述提升比例时，应同时给出对照、场景与指标定义，避免把局部实验结论改写成普遍性能保证。

### 项目适用

本项目可将路径时延差作为待控条件，观察类别感知选路在双主指标和乱序代价上的变化。AG 的 TCP 与交换机实验结果不能直接外推到 RDMA QP。

### 硬件依赖与边界

作者采用 NS2 大规模仿真与 BMv2/P4、Mininet 小型测试；机制依赖 TCP 拥塞窗口和 TCP 头部探测字段。项目只有 ns-3，不能验证可编程交换机实现或直接推断 RDMA 性能。

阅读归档：2026 年 10 月 12 日。参见 [完整通俗报告](papers/ag/analysis.md)、[技术附件](papers/ag/analysis-technical.md)和 [核验记录](papers/ag/verification.md)。

## 12. IntFlow：逐包状态监测与 flowlet 切换融合

论文题目： *IntFlow: Integrating Per-Packet and Per-Flowlet Switching Strategy for Load Balancing in Datacenter Networks*。

### 发表信息

**论文元数据：** IEEE Transactions on Network and Service Management（TNSM）2020；CCF 第七版（2026）计算机网络 C 类期刊。最早公开及首次正式出版日期均为 2020-04-28，卷期为 2020 年第 17 卷第 3 期。DOI：10.1109/TNSM.2020.2990868。

### 内容总结

Shi 等人提出 IntFlow，想解决数据中心里两类选路方式各有短板的问题。流段切换会等到发送间隙再换路，能减少乱序，但平滑流量下可能等不到机会；逐包主动换路能更快响应拥堵，却可能让不同路径的 ACK 混在一起，干扰 TCP/DCTCP 拥塞控制。IntFlow 让主机逐包观察重传、流剩余大小、速率和单向时延，并把状态写入封装头；交换机再结合状态、流段间隙和路径拥塞决定是否换路。健康小流不因流段出现而频繁改道，拥堵或故障流则可主动转移。此处“逐包”是逐包监测与标记，不是无条件逐包喷洒。

论文在 ns-3 的 8×8 叶脊网络、128 台服务器和两种数据中心负载模型上评估 IntFlow，采用 DCTCP，并另测 TCP。作者报告，在速率不对称的 data-mining 场景中，IntFlow 的 FCT 比 CONGA 好 15%～32%；在 Web-search 部分负载下也优于 Hermes 和 LetFlow。随机丢包时，Hermes 在小流平均 FCT 上更好，说明方案没有在所有指标和故障条件下胜出。图 2a 的 80% data-mining 数据点与正文解释存在冲突，原始数据不足以裁定。

论文方法上的经验是先用小拓扑解释拥塞反馈错配，再在不同突发性负载与故障场景下比较，并联合检查重路由频次、平均 FCT、小流和尾部 FCT。复核图表时应逐点对照文字；遇到冲突就保留不确定性。论文未提供完整复现实验包，故其结果是作者报告而非本次独立复现。

### 经验学习

值得学习的是把逐包状态信号和流段边界分开分析，并同时观察完成时间、尾部时延和重传代价。

### 项目适用

本项目两类流都是 RDMA QP，主要结果是 MoE 合成批次完成时间和背景 P99 FCT，乱序也是代价。IntFlow 使用 TCP/DCTCP、INT 和可编程交换机状态，因此论文的阈值与性能数字不能移植，也不能证明本项目会受益。

### 硬件依赖与边界

IntFlow 使用 TCP/DCTCP、INT 和可编程交换机状态。项目只有 ns-3，没有真实 NIC 或交换机，不能验证数据面硬件功能；对应机制与项目收益均需分别验证。

阅读归档：2026 年 10 月 12 日。参见 [完整通俗报告](papers/intflow-2020/analysis.md)、[技术附件](papers/intflow-2020/analysis-technical.md)和 [核验记录](papers/intflow-2020/verification.md)。

## 13. CAPS：类别分流、逐包喷洒与端侧编码

论文题目： *CAPS: Coding-based Adaptive Packet Spraying to Reduce Flow Completion Time in Data Center*。

### 发表信息

**论文元数据：** IEEE INFOCOM 2018；CCF 第七版（2026）计算机网络 A 类。论文属于正式论文集长文；出版社未提供明确 Full/Regular 字段。最早公开日期待核实；Crossref 的正式出版字段只能确认到 2018 年 4 月，作者机构记录日期为 2018-10-08，二者口径差异见核验记录。DOI：10.1109/INFOCOM.2018.8486354。

### 内容总结

Hu 等在 IEEE INFOCOM 2018 发表 CAPS，研究短流和长流混合时的队头阻塞、乱序与吞吐冲突。短流经端侧 FEC 编码后由 ToR 逐包喷洒；短流活跃时，长流用 ECMP 限制到少数路径；短流空闲后，长流改用 RPS 填充空闲路径。接收端收齐足够编码包即可恢复数据。编码冗余按 ACK RTT 推算的阻塞概率调整。论文模型给出编码成功率、等待时延和额外流量公式。

作者以 Mininet 小型测试床和 NS2 大规模仿真评测。论文报告，web search 负载 0.3～0.8 时，短流平均 FCT 相对 ECMP、RPS 和 RepFlow 分别降低约 60%～70%、50%～60% 和 40%～50%；Freeway 接近 CAPS，RPS 的长流吞吐量最高。结果只适用于论文的 TCP、路径和流量模型。本次未独立复现，也未找到完整代码、随机种子和原始数据。论文没有报告置信区间，图表无法替代逐流结果和种子复查。

阅读还需对照正文、公式和图。CAPS 式（10）预示开销随长短流包数比 g 增大而下降，图 12(a) 也下降，但正文写成上升，构成待核实的内部矛盾。



### 经验学习

研究应先找出类别间的具体干扰，再提出机制；用公式写明阻塞、成功率和额外成本；以多种流量、负载和指标交叉验证。可借鉴类别划分、路径切换和双侧代价分析；同时注意作者报告的 AFCT 收益不等于项目收益。

### 项目适用

CAPS 可作为类别感知逐包/逐流设计的历史参考。项目两类业务均为 RDMA QP，关注 MoE 合成批次时间与背景 P99 FCT，乱序为代价。论文的短／长流类别不等于本项目业务类别；若建立简化模型，应明确包阻塞独立性、短流门槛和采样周期等条件。

### 硬件依赖与边界

CAPS 依赖 TCP 端侧 FEC、ACK RTT 估计和交换机配合。项目只有 ns-3，没有真实 NIC 或交换机，不能验证端侧编码开销、网卡处理能力或生产部署表现。

阅读归档：2026 年 10 月 12 日。参见 [完整通俗报告](papers/caps-2018/analysis.md)、[技术附件](papers/caps-2018/analysis-technical.md)和 [核验记录](papers/caps-2018/verification.md)。

## 14. FlowBender：端到端拥塞反馈驱动整流换路

论文题目： *FlowBender: Flow-level Adaptive Routing for Improved Latency and Throughput in Datacenter Networks*。

### 发表信息

**论文元数据：** ACM CoNEXT 2014 Full paper；CCF 第七版（2026）计算机网络 B 类。最早可核实公开日期及正式出版日期均为 2014-12-02。DOI：10.1145/2674005.2674985。

### 内容总结

Kabbani 等在 CoNEXT 2014 发表 FlowBender，研究 ECMP 将长流固定在拥挤路径后，如何利用端系统反馈动态换路。发送端逐 RTT 统计 ECN 标记比例，超过阈值便更改交换机 ECMP 哈希字段。链路故障可由 TCP 超时触发重哈希。流内数据包通常仍走同一路径，因此乱序主要出现在换路前后的在途包之间。基础方法不测量候选路径，新路径可能仍拥塞，连续换路也可能造成震荡。作者将限速换路、渐进迁移和主动探测列为后续优化。

论文使用 128 台服务器 fat-tree 的 ns-3 仿真，并在 15 台 ToR 的真实 TCP 测试床验证。在同步 250 MB 长流微基准中，8、16、24 流的平均完成时间分别从 ECMP 的 588、1,468、2,515 ms 降为 294、580、897 ms。重尾全到全仿真报告摘要级平均和尾延迟改善 73% 和 93%；测试床报告 P99 改善 15%～26%、P99.9 改善 34%～45%。这些数字属于作者的 TCP 条件，不能解释成当前项目收益。作者还显示，接收 ToR 的最后一跳成为瓶颈时，多路径换路帮助有限。

固定 PDF 为 11 页，哈希为 `4efc7dc26cbc94f05f14acb2d01cef5af58355dd658996298b3bb5048fb888c1`；出版元数据页码与本地副本有 1 页差异，核验细节见本篇记录。

研究结论应注明流量模型、网络瓶颈与采样条件。

### 经验学习

论文把机制拆成拥塞信号、换路触发和路径反馈三部分，并分别报告故障恢复、混合流量与尾部指标。值得学习的是检查瓶颈位置：若最后一跳已经饱和，上游换路不能改善结果。

### 项目适用

对本项目，最适合保留的是检查信号延迟、换路频率和乱序代价，并将 MoE 通信批次时间与背景 P99 FCT 一同观察。仍需依据本项目实际 QP 与源码定义对应机制并独立验证。

### 硬件依赖与边界

FlowBender 以 TCP ACK/ECN、RTO 和可改写 TTL/VLAN 字段为基础；当前两类业务均为 RDMA QP，ns-3 中也没有真实 NIC 或交换机，故具体反馈与实现不能直接移植。

阅读归档：2026 年 10 月 12 日。参见 [完整通俗报告](papers/flowbender-2014/analysis.md)、[技术附件](papers/flowbender-2014/analysis-technical.md)和 [核验记录](papers/flowbender-2014/verification.md)。

## 15. DeTail：队列感知选路与流完成时间尾部控制

论文题目： *DeTail: Reducing the Flow Completion Time Tail in Datacenter Networks*。

### 发表信息

**论文元数据：** ACM SIGCOMM 2012 主会 Full paper；CCF 第七版（2026）计算机网络 A 类。同题公开前身 Berkeley 技术报告日期为 2011-10-19（作者与会议版不同）；会议版正式出版日期为 2012-08-13。DOI：10.1145/2342356.2342390。

### 内容总结

DeTail 研究数据中心中的“少数慢流拖累整体请求”问题。网页构建可能同时等待许多后台服务，只要几条流卡住，页面就会延迟或缺少内容。作者用测量数据和抽样工作流说明，尾部比中位数更能解释这类等待：时延中位数更高但尾巴较短的分布，也可能让并行及串行任务更常按时结束。该部分使用实测 RTT 和合成工作流；流完成时间近似为一次 RTT，并非网页线上实验。

DeTail 是跨层网络栈。交换机逐包选择目的地的最短路径，并按队列占用挑选较空的出口。PFC 逐跳传递拥塞信息；传输层容忍乱序，以优先级、ECN 和较长重传定时器协调拥塞；应用为流设置优先级。可把它类比成分拣站按出口队列临时改道，并让急件优先。类比只用于解释。方案依赖每优先级队列信号、PFC、严格优先级调度及可重排的传输端。

评估使用 NS-3 包级模拟、Click 软件路由器和 DETER 测试床。128 台服务器全互连负载中，每秒 2,000 次请求、8 KB 响应的 P99.9 从流哈希基线的 7.3 ms 降至 2.3 ms；合成串行工作流的 P99.9 从 38 ms 降至 18 ms。背景长流与短检索共存时，P99 降低 58%～71%。模拟器没有 ECN；长流实验仅在较小 Click 环境完成；故障测试假定路由已收敛。因此这些数字只描述论文配置。



### 经验学习

可迁移的科研方法是把选路、路径拥塞反馈、接收端乱序及重传成本连成可观测因果链，再用应用指标验证整体效果。

### 项目适用

项目关注 MoE 合成批次完成时间、背景 P99 FCT，并记录乱序代价。DeTail 适合作方法参考，不能支持项目收益主张。

### 硬件依赖与边界

项目只有 ns-3，两类流均为 RDMA QP，且按类别混合逐包与逐流选路；论文研究 TCP、PFC 和优先级队列，没有测试 RDMA、MoE 或 ConWeave。

阅读归档：2026 年 10 月 12 日。参见 [完整通俗报告](papers/detail-2012/analysis.md)、[技术附件](papers/detail-2012/analysis-technical.md)和 [核验记录](papers/detail-2012/verification.md)。

## 16. Presto：端侧 flowcell 切分与接收端重排

论文题目： *Presto: Edge-based Load Balancing for Fast Datacenter Networks*。

### 发表信息

**论文元数据：** ACM SIGCOMM 2015 主会 Full paper；CCF 第七版（2026）计算机网络 A 类。最早可核实公开记录及正式出版日期均为 2015-08-17。DOI：10.1145/2785956.2787507。

### 内容总结

He、Rozner、Agarwal、Felter、Carter 和 Akella 把长 TCP 流切成约 64 KB 的 flowcell，由边缘虚拟交换机轮流放到预设端到端路径。为控制不同路径造成的乱序，作者修改 Linux GRO：每流暂存多个 TCP 段，利用 flowcell ID 和序号缺口区分块内丢包与块间重排，并按近期重排间隔设置等待时间。论文在 16 台服务器、两层 Clos、10 Gbps 网卡及 Linux TCP 环境中测试。Presto GRO 在严重重排微基准中达到 9.3 Gbps，官方 GRO 为 4.6 Gbps；轨迹驱动负载中，小流 P99 和 P99.9 FCT 相比 ECMP 分别降低 56% 和 60%。

这样既能说明参数从何而来，也能把机制开销和应用指标联系起来。

### 经验学习

论文先测 flowlet 大小分布，再解释 64 KB 粒度与 TSO 的关系，并同时报告吞吐、CPU、RTT、尾部 FCT、丢包和故障结果。它还通过单独的重排微基准解释接收端恢复能力，再把这些机制放进轨迹负载评估。这样的过程有助于把参数依据、恢复成本和应用结果连起来。

### 项目适用

这些数字来自作者的 TCP 实体测试，不能视作本项目收益。论文没有 MoE 批次完成时间或背景 RDMA P99 结果，所以 Presto 仅作方法参考，不构成机制准入或项目效果证据。对本项目，可先固定 RDMA QP 模型中的路径差、反馈时延和乱序成本，再检查批次与背景流是否同时受益。该思路仍需按本项目同一传输契约和双主指标独立验证。

### 硬件依赖与边界

项目只有 ns-3，AI/MoE 与背景流均为 RDMA QP，且使用类别感知逐包／逐流混合选路和拥塞反馈；TCP TSO/GRO、真实网卡 CPU 开销及其重排处理无法直接映射到该模型。

阅读归档：2026 年 10 月 12 日。参见 [完整通俗报告](papers/presto-2015/analysis.md)、[技术附件](papers/presto-2015/analysis-technical.md)和 [核验记录](papers/presto-2015/verification.md)。

## 17. DRB：Clos 结构下的数字反转弹跳逐包分配

论文题目： *Per-packet Load-balanced, Low-Latency Routing for Clos-based Data Center Networks*。

### 发表信息

**论文元数据：** ACM CoNEXT 2013 论文集研究长文；CCF 第七版（2026）计算机网络 B 类，按 Full/Regular 范围记录。最早公开日期待核实；Crossref 的在线和纸本出版日期均为 2013-12-09。DOI：10.1145/2535372.2535375。

### 内容总结

Cao 等人提出数字反转弹跳（DRB），用于 Fat-tree 和 VL2 数据中心网络。发送端按每个源—目的主机对保存弹跳交换机状态，并逐包轮转；轮转顺序经过数字反转，使连续包在 Clos 各层链路上更均匀地交错。论文用流量矩阵证明，在 Fat-tree 可行流量条件下，逐层均匀分摊可避免链路超载；还给出逐层链路访问间隔定理。VL2 则先扩展虚拟 spine，恢复选定弹跳点后路径唯一的性质。逐包多路径仍会乱序，实验使用接收端缓存等缺口填补或超时。仿真和 54 台服务器测试床显示，DRB 在论文环境中相较随机弹跳和普通轮转取得较高吞吐、较短队列和较少重排等待；这些结果属于 TCP、特定 Clos、流量及硬件配置。



### 经验学习

设计逐包方案时，需要从拓扑推导分配序列，而不能假设简单轮转自然均衡。评价应同时包含逐跳队列、包序、接收端重排等待和端到端完成时间。论文也展示了有用的验证链：定理说明条件，队列模型解释原因，ns-3 比较多种流量，测试床检查实现，并分别报告有无重排缓存的吞吐。Theorem 2 正文未给证明，下行队列模型还省略前序 hop 的干扰，因此复核时要把这些条件留在结论旁。论文的结构化逐包分配和重排测量可作为方法参考。

### 项目适用

当前项目的 MoE 类与背景类都是 RDMA QP，关注 MoE 合成批次完成时间和背景 P99 FCT，且需要控制乱序代价。DRB 未处理业务类别，也没有给出这两个主指标的联合结果。其数字不能外推为项目收益，也不构成新机制准入证据。

### 硬件依赖与边界

论文基于 TCP、IP-in-IP、服务端状态和接收端重排缓存；项目只有 ns-3，没有真实 NIC 或交换芯片，因此不能据此确认 RDMA 重传、NACK、NIC 重排或商用硬件性能。

阅读归档：2026 年 10 月 12 日。参见 [完整通俗报告](papers/drb-2013/analysis.md)、[技术附件](papers/drb-2013/analysis-technical.md)和 [核验记录](papers/drb-2013/verification.md)。

## 18. WCMP：按路径容量分配逐流权重

论文题目：*WCMP: Weighted Cost Multipathing for Improved Fairness in Data Centers*。

### 发表信息

正式发表：ACM EuroSys 2014，正式会议长文，DOI：10.1145/2592798.2592803。CCF 第七版（2026）：计算机体系结构／并行与分布计算／存储系统 A 类会议。最早可查公开记录与正式出版日期均为 2014-04-14，依据 Crossref `published-online` 与 `published-print` 字段；本次未发现更早的预印本时间戳。CCF 类别描述 venue，不是单篇论文质量评级。来源：[Google Research 论文页](https://research.google/pubs/wcmp-weighted-cost-multipathing-for-improved-fairness-in-data-centers-2/)、[Crossref 元数据](https://api.crossref.org/works/10.1145%2F2592798.2592803)、[CCF 第七版公告](https://www.ccf.org.cn/Academic_Evaluation/By_category/)。ACM 页面本次访问返回 403；来源限制与交叉核验见[本篇核验记录](papers/wcmp-2014/verification.md)。

### 内容总结

WCMP 关注多条路径容量不同时，等概率 ECMP 会让部分流长期经过较窄路径的问题。它依据拓扑可用容量调整逐流哈希权重，并提供权重压缩方法，在交换机表项预算与分配公平之间作取舍。同一条流仍固定走一条路径。作者在 OpenFlow/TCP 测试床和 htsim 模拟中报告，特定拓扑下的流带宽差异和流完成时间有所改善。这些结果受论文拓扑、TCP/MPTCP、ECN、流量矩阵和硬件条件限制。

### 经验学习

可借鉴论文把拓扑容量差异转成可量化权重，并显式讨论表项资源和流间公平的取舍。评估还应区分静态可用容量与动态拥塞，并检查低带宽流和完成时间尾部，避免只看平均带宽。权重压缩并非无损，超订阅限制会改变路径份额。

### 项目适用

项目只有 ns-3，两类流均为 RDMA QP，重点是 MoE 合成通信批次完成时间与背景 P99 FCT，乱序作为代价。WCMP 按流分配静态容量权重，不识别业务类别，也没有逐包拥塞反馈或乱序控制。因此可作为容量加权逐流对照或分析方法候选；不能据论文结果推断本项目收益，也不自动构成机制准入。

### 硬件依赖与边界

论文使用实体交换机、NIC、OpenFlow、TCP 和 MPTCP。当前实验条件不能验证真实表项压力、控制器更新开销或生产部署表现。本次只核验固定 PDF，未复现作者实验、未启动 ns-3 仿真、未修改研究代码，也未干预 WS-26。

阅读日期：2026 年 10 月 12 日。参见[完整通俗报告](papers/wcmp-2014/analysis.md)、[技术附件](papers/wcmp-2014/analysis-technical.md)、[证据表](papers/wcmp-2014/evidence.csv)、[逐页审读清单](papers/wcmp-2014/page-audit.csv)与[核验记录](papers/wcmp-2014/verification.md)。

## 19. SGLB：用全局拥塞反馈管理集群路径

论文题目：*SGLB: Scalable and Robust Global Load Balancing in Commodity AI Clusters*。

### 发表信息

正式发表：ACM SIGCOMM 2025 主会 Full paper，DOI：10.1145/3718958.3750527。CCF 第七版（2026）：计算机网络 A 类会议。最早可核实公开日期与正式出版日期均为 2025-08-27（ACM Published 字段）。精确标题检索未发现 arXiv 记录，但这不能排除作者通过其他渠道更早公开。来源：[ACM 论文记录](https://dl.acm.org/doi/10.1145/3718958.3750527)、[SIGCOMM 2025 发表规则](https://conferences.sigcomm.org/sigcomm/2025/cfp/)、[Full papers 列表](https://conferences.sigcomm.org/sigcomm/2025/accepted-papers/)、[CCF 第七版公告](https://www.ccf.org.cn/Academic_Evaluation/By_category/)。CCF 类别描述 venue，不是单篇论文质量评级。详细来源与边界见[本篇核验记录](papers/sglb-2025/verification.md)。

### 内容总结

SGLB 将 BGP 的目的地可达信息与 SyncMesh 传播的物理链路状态结合，由编排器计算路径组，再让交换机 GLB 引擎依据本地和下游队列、链路利用率选路。为控制硬件表项规模，系统压缩并合并路径状态；遇到 LAG 链路故障时，还会关闭部分健康上游链路来恢复上下游容量比例。作者在 H800/RoCEv2 测试床报告 LLaMA-3 总训练时间下降 12.3%；在 ASTRA-Sim/htsim 模拟中报告 CCT、FCT 和队列变化。这些结果分别依赖真实硬件与特定模拟条件，不能混为一谈。附录声明未经同行评审；模拟中的 ConWeave、CONGA 和 NDP 也经过简化或改写。

### 经验学习

可借鉴的是把局部拥塞信号、下游状态、反馈延迟、状态规模和故障恢复放在同一条因果链中观察。评估时要分开报告硬件测试与模拟器结果，也要说明对照机制的实现是否等价。不能把队列变异系数当作端到端尾时延，也不能将摘要中的最高改善幅度脱离具体场景引用。

### 项目适用

本项目只有 ns-3，MoE 合成批次完成时间与背景 P99 FCT 是双主指标，两类业务均为 RDMA QP，乱序是代价。SGLB 没有在本项目的类别感知混合策略与双指标契约下进行评测。可借鉴全局反馈、状态传播时延和路径状态压缩的分析方法；应把本项目中的状态来源、陈旧度和更新成本明确建模，并单独验证，不把它写成对 SGLB 的硬件复现。

### 硬件依赖与边界

论文核心依赖 GLB ASIC、EDK 接口、交换机控制平面与物理 NIC。项目无法验证芯片表项、厂商数据面处理或生产部署结论；论文中的训练收益和微秒级故障恢复时间不能外推为项目收益。本次未运行仿真、修改研究代码或干预 WS-26。

阅读日期：2026 年 10 月 12 日。参见[完整通俗报告](papers/sglb-2025/analysis.md)、[技术附件](papers/sglb-2025/analysis-technical.md)、[证据表](papers/sglb-2025/evidence.csv)、[逐页审读清单](papers/sglb-2025/page-audit.csv)与[核验记录](papers/sglb-2025/verification.md)。

## 20. MicroTE：用短期需求预测协调全局选路

论文题目：*MicroTE: Fine Grained Traffic Engineering for Data Centers*。

### 发表信息

正式发表：ACM CoNEXT 2011，DOI：10.1145/2079296.2079304。CCF 第七版（2026）：计算机网络 B 类会议；正式论文是否属于 Full／Regular paper 待核实。最早可核实公开日期与正式出版日期均为 2011-12-06，依据 Crossref 在线和印刷出版字段；未找到更早预印本记录。来源：[Crossref 元数据](https://api.crossref.org/works/10.1145/2079296.2079304)、[CoNEXT 2011 官方日程](https://conferences.sigcomm.org/co-next/2011/program.html)、[CCF 第七版公告](https://www.ccf.org.cn/Academic_Evaluation/By_category/)、[CCF 计算机网络目录](https://www.ccf.org.cn/Academic_Evaluation/CN/)。CCF 类别描述 venue，不是单篇论文质量评级；论文类型资格和访问限制见[核验记录](papers/microte-2011/verification.md)。

### 内容总结

MicroTE 利用数据中心流量矩阵在短时间内相对稳定这一特点，减少 ECMP 无法协调多个发送方的问题。它每秒汇总 ToR 对需求，把较可预测的部分交给全局路由优化，再用加权 ECMP 承载剩余的不确定流量。作者分析两个数据中心 trace，并以最大链路利用率、丢失流量、求路和路由安装时间评估方案。论文报告的覆盖率和性能取决于其 trace、拓扑、预测窗口与随机流量构造，不能当作普遍收益。

### 经验学习

可借鉴的研究方法是先测量业务需求能稳定多久，再逐步加入预测误差、控制时延和未知流量。评估时应区分已知矩阵下的理想分配与系统实际可观测的需求，报告求解质量和更新开销，并以不同数据集检验结果是否稳健。

### 项目适用

本项目的主指标是 MoE 合成通信批次完成时间与背景 P99 FCT，两类流均为 RDMA QP，乱序是代价约束。MicroTE 没有研究类别感知逐包／逐流混合机制，也没有测量这些指标；只适合作为流量预测和全局分配的方法参考。若把稳定性或预测误差抽象进 ns-3，需说明状态来源与更新时间，并独立验证，不能称为复现了论文系统。

### 硬件依赖与边界

MicroTE 的 Linux 内核流量监测、中心控制器、NOX/OpenFlow 规则安装和 HP ProCurve 交换机测试依赖系统软件与真实硬件。当前 ns-3 环境不能验证这些部署开销或生产效果。未运行作者代码、未启动项目仿真、未修改研究代码，也未干预 WS-26。

阅读日期：2026 年 10 月 12 日。参见[完整通俗报告](papers/microte-2011/analysis.md)、[技术附件](papers/microte-2011/analysis-technical.md)、[证据表](papers/microte-2011/evidence.csv)、[逐页审读清单](papers/microte-2011/page-audit.csv)与[核验记录](papers/microte-2011/verification.md)。

## 21. TeXCP：让反馈调整既及时又稳定

论文题目：《Walking the Tightrope: Responsive Yet Stable Traffic Engineering》。Srikanth Kandula、Dina Katabi、Bruce Davie 和 Anna Charny，2005 年，完整阅读固定 PDF 12 页。

### 发表信息

ACM SIGCOMM 2005，253～264，DOI：10.1145/1080091.1080122；另有 CCR 同文收录。CCF 第七版（2026）：计算机网络 A 类会议。主会论文身份已核验，明确 Full／Regular 资格待核实。正式在线出版为 2005-08-22，来自出版登记字段；绝对最早公开日待核实。[出版记录](https://api.crossref.org/works/10.1145%2F1080091.1080122)、[CCF 目录](https://www.ccf.org.cn/Academic_Evaluation/CN/)

### 内容总结

TeXCP 研究运营商网络的在线分路。各入口先配置多条路径，再根据沿途最繁忙链路的反馈调整比例。独立入口若同时转向空闲路径，可能一起制造新热点。作者因此把较快的发送率控制与较慢的路径调权分开，先让上次动作稳定，再作新决定。方案也会试探弃用路径，并偏向较短路线。

作者在 ns-2 的 7 个 ISP 拓扑和合成需求中评估。主要指标是最大利用率相对 Oracle 的比值，结果接近最优。收敛约需 10～15 次调权才能达到最优的 10% 内，默认约 5～7.5 s。这不是 FCT 提升，也不是数据中心恢复时间。MATE 对照复用其公开曲线，未重跑私有代码。

### 经验学习

值得学习的是把反馈时效、动作幅度与共享瓶颈放在一起分析。稳定性、接近最优和硬件部署分别需要证据。论文证明采用流体模型，并未证明全局最优；负反馈符号、容量换算及附录步骤存在疑点，均已记录。

### 项目适用

仅保留方法参考。可借鉴双时间尺度、路径范围和故障过渡评价；本项目两类均为 RDMA QP，须继续以 MoE 合成批次和背景 P99 FCT 判断结果，计入入口等待和乱序恢复。WAN 参数不能直接照搬，也不能用利用率均衡替代双方收益。

### 硬件依赖与边界

完整方案依赖 MPLS 路径、核心计数和反馈、入口状态及限速。作者只讨论部署，没有真实硬件性能验证。本项目仅有 ns-3，无法验证设备容量或 RNIC 代价。全文、14 幅图、5 张表和两份证明附录均已核验，未运行仿真、改代码或干预 WS26。

阅读日期：2026 年 10 月 12 日。见 [完整报告](papers/texcp-2005/analysis.md)、[技术附件](papers/texcp-2005/analysis-technical.md)和 [核验记录](papers/texcp-2005/verification.md)。

## 22. ECMP：哈希阈值映射与路径集合扰动

论文题目：*Analysis of an Equal-Cost Multi-Path Algorithm*。

### 发表信息

Christian E. Hopps，RFC 2992，Informational RFC，2000 年 11 月发布，DOI：10.17487/RFC2992。本文是 RFC 文档，没有会议或期刊 venue；CCF 第七版（2026）领域、类别及 Full/Regular 论文资格均不适用。Datatracker 记录的最早公开草案为 Internet-Draft 00，登记于 1999-01-06。来源：[RFC Editor](https://www.rfc-editor.org/info/rfc2992/)、[Datatracker 草案历史](https://datatracker.ietf.org/doc/draft-hopps-ecmp-algo-analysis/history/)、[本篇核验记录](papers/ecmp-rfc2992/verification.md)。

### 内容总结

论文分析哈希阈值 ECMP：先将哈希空间均分给当前的下一跳，再按流标识的哈希结果固定选择路径。路径集合不变时，流映射保持稳定；新增或删除下一跳时，重新划分区域会令部分流改道。作者推导了路径删除时的流迁移比例，并与 modulo-N 和 HRW 作理论比较。分析依赖均匀哈希与等宽路径假设，原文没有网络性能实验。

### 经验学习

可以先定义路径变化会影响多少流，再分析路径查找成本，避免把“稳定性”和“速度”混为一谈。公式中的路径数是整数，不能只用连续求导取代离散检查。本篇逐式复核发现，偶数路径数的最小扰动应从原式计算为 N/[4(N−1)]；报告将此作为独立算术核对，保留作者原文与复核结论的区别。

### 项目适用

可将路径集合变化时的流迁移比例作为 ns-3 诊断指标，并观察它与 MoE 合成通信批次完成时间、背景 P99 FCT 和乱序代价的关系。RFC 只分析映射扰动，没有评估本项目类别感知逐包／逐流混合、RDMA QP 反馈或两项主结果，因此只作稳定性分析方法参考。具体 ECMP 行为仍以本项目固定源码和实验 ID 原始数据为准。

### 硬件依赖与边界

RFC 讨论了哈希硬件并行计算，但没有验证芯片吞吐、重配置时延或表更新成本，也没有网络负载实验。ns-3 可验证映射统计和仿真行为，不能证明硬件实现性能。

阅读日期：2026 年 10 月 12 日。参见[通俗报告](papers/ecmp-rfc2992/analysis.md)、[技术附件](papers/ecmp-rfc2992/analysis-technical.md)、[证据表](papers/ecmp-rfc2992/evidence.csv)、[逐页审读清单](papers/ecmp-rfc2992/page-audit.csv)与[核验记录](papers/ecmp-rfc2992/verification.md)。

## 23. Fastpass：集中仲裁与逐包时序协调

论文题目：*Fastpass: A Centralized “Zero-Queue” Datacenter Network*。作者为 Jonathan Perry、Amy Ousterhout、Hari Balakrishnan、Devavrat Shah 和 Hans Fugal。

### 发表信息

正式发表：ACM SIGCOMM 2014，页码 307～318，DOI：10.1145/2619239.2626309。CCF 第七版（2026）将 SIGCOMM 列为计算机网络 A 类会议。论文属于主会长文；出版方未直接标明 CCF 所要求的 Full/Regular 字段资格，故该项待核实。最早核实到的公开介绍为 2014-07-17（MIT News），论文全文首次公开日期待核实。ACM Publication History 记正式出版日期为 2014-08-17。CCF 类别指 venue 推荐等级，不代表单篇论文质量。来源：[ACM 出版记录](https://doi.org/10.1145/2619239.2626309)、[MIT News 介绍](https://news.mit.edu/2014/no-wait-data-centers-0717)、[CCF 官方目录](https://www.ccf.org.cn/Academic_Evaluation/CN/)。逐项核验见[本篇记录](papers/fastpass-2014/verification.md)。

### 内容总结

Fastpass 让一个逻辑中心仲裁器为每个包安排发送时刻和路径。发送端先报告目的地及待发数据量，仲裁器再根据端口容量分配时隙，并检查路径之间是否冲突。它想解决的问题很直观：如果提前协调好包什么时候发、从哪里走，就能少在交换机里排队。

可把它想成机场塔台同时安排起飞时间和航线。作者把排时隙和挑路径拆成两步：第一步用贪心匹配避免端口冲突；第二步按拓扑条件给包分配不冲突的路径。这个拆分依赖论文设定的可重排无阻塞网络条件，并不是任何拓扑都能直接套用。

论文还实现了端点与仲裁器之间的需求、授权和重传协议，并让多个仲裁器互为主备。真实发送端依赖 Linux 定时器和 PTP 时钟同步，才能尽量按授权时刻发包。作者分别报告了 32 台服务器单机架测试、仲裁器合成压力测试和 Facebook 生产服务测试：单机架中位队列从 4,351 KB 降到 18 KB、吞吐略降；ping 中位 RTT 从 3.56 ms 降到 0.23 ms；生产服务 TCP 重传率下降约 2～2.5 倍，但请求服务时延与基线接近。不同数字来自不同测试，均是作者结果，不能合并成单一收益，也没有在本项目复现。

### 经验学习

值得学习的是把“何时准入”与“走哪条路径”分开分析，同时明确两步之间的容量条件。论文还分别测量了端点通信、调度、路径计算和计时误差，避免只凭队列变短就忽略控制开销、轻载时延或故障切换成本。科研设计上，可以把算法成立条件和实现依赖写成可检查的清单，再逐项做消融或压力测试。

### 项目适用

本项目两类业务都是 RDMA QP，关注 MoE 合成通信批次完成时间、背景 P99 FCT 和乱序代价。Fastpass 没有研究类别感知逐包／逐流混合选路、RDMA QP 乱序恢复或这两个主结果，因此只适合作为集中协调、容量约束拆分和测量设计的方法参考。ns-3 可以抽象中心调度、链路容量、控制延迟、队列及批次完成时间，但仿真中观察到的变化只能说明模型内结果，须由项目固定源码和实验数据独立证明。

### 硬件依赖与边界

实现依赖 Linux 内核模块、DPDK、支持 PTP 的 NIC、IEEE 1588 时钟同步、高精度定时器及仲裁服务器。ns-3 无法验证真实网卡计时、操作系统抖动、PTP 精度、DPDK 线速能力或生产部署收益。本文也没有测量项目的 MoE 批次时间、背景 P99 FCT 与乱序恢复代价，故论文效果不构成本项目收益证据。

阅读日期：2026 年 10 月 12 日。参见[完整通俗报告](papers/fastpass-2014/analysis.md)、[技术附件](papers/fastpass-2014/analysis-technical.md)、[证据表](papers/fastpass-2014/evidence.csv)、[逐页审读清单](papers/fastpass-2014/page-audit.csv)和[核验记录](papers/fastpass-2014/verification.md)。

## 24. DRB-TTC：默认路径分散与阈值改道

论文题目：*Randomized Load-balanced Routing for Fat-tree Networks*；Suzhen Wang、Jingjing Luo、Bruce Kwong-Bun Tong、Wing Shing Wong；固定阅读版本 arXiv:1708.09135v1，PDF 13 页。本文 DRB 是 Dynamic Randomized load-Balancing，用 DRB-TTC 与 Cao 等人的 Digital Reversal Bouncing 区分。

### 发表信息

正式会议／期刊 venue：待核实。DBLP 将该记录列为 CoRR 的非正式与其他出版物；CoRR 不作为会议或期刊。DOI `10.48550/arXiv.1708.09135` 是 arXiv 预印本 DOI。CCF 第七版（2026 年 3 月更新）按 venue 分类，因此领域、类别和 Full/Regular 资格不适用。最早公开日为 arXiv v1 首次提交日 2017 年 8 月 30 日；正式出版日期待核实。[arXiv v1](https://arxiv.org/abs/1708.09135v1)、[DBLP](https://dblp.org/rec/journals/corr/abs-1708-09135)、[CCF 第七版](https://www.ccf.org.cn/Academic_Evaluation/By_category/2026-03-05/861526.shtml)

### 内容总结

论文把 Fat-tree 的上行和下行分开处理。D-mod-k 根据目的主机标签分配默认路径，作者证明不同目的地的下行路径不会共享链路。TTC 在每台交换机本地比较默认出口与随机备选出口；只有备选负载低出阈值 T，才改道。这样限制上行调整量，尽可能保留默认路径的下行安排。

作者用两种 C++ fat-tree 模型评估机制。置换流实验统计全网最大链路流数；置换包实验统计逐层队列、平均时延和同一时隙发包中的最长时延。论文报告 DRB-TTC 在所设负载下改善这些指标。其理论还在泊松到达、随机目的地、指数服务和大规模队列近似下证明稳定性与双指数队列尾。上述证据来自受控模型，不是 RDMA 或真实交换机实验。

### 经验学习

值得借鉴的是先证明基线路由对目的地路径碰撞的影响，再允许带阈值的本地改道，并同时记录改道量、分层队列和端到端时延。作者把流路由和包路由分开测试，也提醒读者区分负载计量方式。启发式最大负载估算不是严格定理；高层队列独立性依赖额外假设。

### 项目适用

本项目只有 ns-3，可将本地队列比较和阈值改道作为待研究的建模方法。D-mod-k 的具体标签规则针对规则 fat-tree，须先按项目拓扑重新推导。项目应同时观测 MoE 合成批次完成时间、背景 P99 FCT，并把乱序作为代价约束。论文没有类别感知，也没有提供这两项主指标或 RDMA QP 的证据，不能推断项目收益。

### 硬件依赖与边界

ns-3 可模拟本地队列和路径决策，但不能验证交换芯片能否线速读取队列、随机抽样及作出阈值决策。论文没有真实 NIC/交换机部署，也未分析 RDMA 的重排、NACK、重传和接收缓存。Cao 等人 Digital Reversal Bouncing 的逐包路径轮转是另一种 DRB 机制，不能混为一谈。

阅读日期：2026 年 10 月 12 日。参见[完整报告](papers/drb-ttc-2017/analysis.md)、[技术附件](papers/drb-ttc-2017/analysis-technical.md)、[证据表](papers/drb-ttc-2017/evidence.csv)、[逐页清单](papers/drb-ttc-2017/page-audit.csv)和[核验记录](papers/drb-ttc-2017/verification.md)。

## 25. RDMACell：把流切成固定小块以兼顾粒度与保序

论文题目：*RDMACell: Token-Based Flowcell-Level RDMA Load Balancing for Large-Scale AI Training*；Yang Qinyuan、Hua Xiaoxiang、Zhang Tong、Ren Fengyuan；固定阅读版本 arXiv:2606.20581v1，PDF 7 页。

### 发表信息

正式会议／期刊 venue：待核实。arXiv 页面无 journal reference、无 comments 字段；Crossref 按题名检索未命中该论文；DBLP 在核验时返回反爬挑战，未能取得条目。DOI `10.48550/arXiv.2606.20581` 是由 DataCite 发放的 arXiv 预印本 DOI，不是出版社 DOI。CCF 第七版（2026）按 venue 分类，因此领域、类别与 Full/Regular 资格均不适用。最早公开日期按 arXiv v1 记录记为 2026 年 5 月 7 日；正式出版日期待核实。另需留档：arXiv 编号 2606.20581 的月份段对应 2026 年 6 月，PDF 生成时间为 2026 年 6 月 23 日，与 5 月 7 日的提交日存在张力，本次不做推断。来源：[arXiv v1 记录](https://arxiv.org/abs/2606.20581v1)、[本篇核验记录](papers/rdmacell-2026/verification.md)。

### 内容总结

论文针对 RDMA 数据中心网络的负载均衡粒度问题。逐流方案依赖流量空档触发换路，而 RDMA 网卡的硬件节拍把流量送得很平顺，空档很少，方案几乎不起作用；逐包方案又会造成严重乱序，RoCEv2 会把乱序当成丢包并触发重传，拖长完成时间。可编程交换机上的方案虽然精细，但部署成本高。

作者把流主动切成固定大小的小块，大小取 1.5 倍带宽时延积，然后在每条路径上整块传输、块与块之间分散到不同路径。为了让接收端知道小块边界，发送端投递成对的两个请求：前一个携带立即数据，逼出一次完成事件并把小块编号传给接收端；后一个安静地把剩余数据送过去。接收端取出编号和时间戳，生成一个小令牌，用单边写操作直接写回发送端内存里预留的槽位。发送端轮询这些槽位，按往返时延均值加两倍波动量判断超时，超时就隔离出问题的连接、把待发指针回退到最早的未确认小块、通过备份连接重新投递，并异步复位故障连接以打断重传循环。

作者在自建的 ns-3 RoCEv2 环境里评估：K=8 胖树、128 台服务器、100 Gbps 链路、每端口 2 MB 缓冲、开启 ECN，用阿里云存储 trace 与 Solar trace 模拟 all-to-all 流量，负载从 20% 加到 80%，对照 ECMP、CONGA、LetFlow、HULA 和 ConWeave。阿里云存储 trace 在 80% 负载下，99 分位 FCT 相对 ECMP 降低约 44%、相对 LetFlow 降低 42.2%；换到几乎纯小流的 Solar trace，同一负载点相对 ECMP 只降低 6.5% 至 6.8%。

### 经验学习

值得借鉴的是把切分粒度放在设计的第一位，并明确写出粒度与乱序之间的因果取舍，而不是只报告最终指标。第二个可学的地方是用固定滑动窗口配合由往返时延自适应得到的阈值来判定换路，规则简单、便于插桩和复算。第三个是反馈通道的选择：接收端用单边写把很小的凭据直接送回发送端内存，不必依赖可编程交换机。第四个是把故障处理写成状态机的一部分，把路径隔离、指针回退与恢复动作分开描述。

方法上还有两点提醒。作者给出的百分比都能由端点数值回算，但有一处例外：99 分位相对 HULA 的降幅按数值应为 47.6%，论文写作 47.1%。另外，论文的核心动机是乱序，却没有报告任何乱序度量，也没有给出丢包与重传次数、主机 CPU 开销、令牌反馈带宽、粒度敏感性与换路时延，这些缺口本身就是值得学习的清单——如果本项目采用类似设计，需要自己把这几项测出来。

### 项目适用

本项目只有 ns-3，没有网卡和交换机，两类业务都是 RDMA QP，主结果是 MoE 合成通信批次完成时间与背景 P99 FCT，乱序是代价约束。RDMACell 在这几处对得上：纯主机侧、不改交换机，粒度、窗口、阈值与反馈回路都可以在仿真中插桩；作者本身也用 ns-3 评估。

不能直接套用的地方同样明确。论文没有区分业务类别，MoE 类与背景类的差异完全没有涉及；它没有测量批次完成时间这一类应用级指标；两份 trace 都是存储型流量，不是集合通信或 MoE 的通信形态。44% 与 42.2% 只对应阿里云存储 trace 与 80% 负载这一个组合，Solar 场景只有 6.5% 至 6.8%，说明收益高度依赖流量结构，不能当作本项目的收益预期。

要在本项目里尝试类似机制，至少需要先确认现有仿真模型能否表达立即数据、完成事件与接收端写回发送端内存这几条语义，并把乱序与反馈开销真正测出来，最后在 MoE 合成批次与背景 P99 FCT 两个口径下重新验证。

### 硬件依赖与边界

机制不改网卡固件与交换机硬件，但依赖 Verbs 层的立即数据语义、完成事件、单边写操作与 RC 连接模式，以及商用网卡的硬件节拍行为。ns-3 可以近似建模这些语义，却无法验证真实网卡产生完成事件的方式、中断与轮询开销、以及 DMA 写入对端内存的实际代价。论文没有硬件原型或实机验证，"零硬件修改"是对接口兼容性的判断，不是部署结论。

对照方案 CONGA、ConWeave、HULA 所需的网内状态采集逻辑由作者自行在交换机模型中实现，未提供保真度核验，因此比较强度依赖其实现质量。论文未报告 FCT 的单位，也未说明 3.93/4.94 与 11.00 对应的具体负载点。

阅读日期：2026 年 10 月 13 日。参见[完整报告](papers/rdmacell-2026/analysis.md)、[技术附件](papers/rdmacell-2026/analysis-technical.md)、[证据表](papers/rdmacell-2026/evidence.csv)、[逐页清单](papers/rdmacell-2026/page-audit.csv)和[核验记录](papers/rdmacell-2026/verification.md)。

## 26. Hopper：按 RTT 探测并避开拥塞路径

论文题目：*Predictive Load Balancing for RDMA Traffic*，Erfan Nosrati、Majid Ghaderi，固定阅读版本 arXiv:2506.08132v1（11 页）。arXiv 官方记录题名为 *Congestion-Aware Path Selection for Load Balancing in AI Clusters*，与 PDF 首页不同，详情见核验记录。

### 发表信息

正式 venue、出版日期及 Full/Regular 资格：待核实。最早公开日期：2025 年 6 月 9 日（arXiv v1）。DOI：10.48550/arXiv.2506.08132（arXiv DOI）。CCF 第七版（2026）：无正式 venue，类别不适用；计算机网络是内容领域，不据此赋予级别。[arXiv v1 记录](https://arxiv.org/abs/2506.08132v1)、[CCF 目录](https://www.ccf.org.cn/Academic_Evaluation/By_category/)。

### 内容总结

Hopper 让主机监测当前 RDMA 路径的 RTT。路径变慢时，它随机探测两个备选路径；只有发现明显更好的路径才切换。切换前还会等待一段时间，降低新旧路径时延差造成的乱序。可以把它理解成车辆先抽查两条绕行道路，确认其中一路畅通后再改道。这个类比只用于解释机制。作者用 ns-3 比较 ECMP、FlowBender、CONGA 和 ConWeave，并在小型硬件测试床评估 Hopper。仿真中，Hopper 相对 FlowBender 的 ML 流平均和 P99 FCT slowdown 最多改善 20% 和 14%；高负载下，交换机方案通常更好。测试床还报告了单流 FCT 改善，但总训练时间段落的数值顺序和“缩短”比例互相矛盾，不能作为确定收益引用。

### 经验学习

可借鉴把探测、切换和乱序控制拆开设计，并报告拥塞门限、候选数量及路径切换时机。论文没有报告随机种子、误差区间，也没有系统量化乱序包、重传和缓存峰值。它提供了仿真设置与硬件说明，但未定位到可核验的 Hopper 完整代码和原始数据。

### 项目适用

ns-3 可表达 RTT 反馈、两个候选路径抽样、切换滞回和切换延迟。项目应分别评估 MoE 合成批次完成时间、背景流 P99 FCT，并把乱序代价单列。Hopper 未测试 MoE、类别感知或混合负载，这些指标是否获益仍待项目验证。

### 硬件依赖与边界

RTT 时间戳、RDMA QP 切换、ECMP 源端口映射和乱序缓存依赖真实 RNIC 与交换机。ns-3 只能验证抽象机制，不能证明具体硬件精度和部署效果。

阅读日期：2026 年 10 月 14 日。参见[完整报告](papers/hopper-2025/analysis.md)、[技术附件](papers/hopper-2025/analysis-technical.md)、[证据表](papers/hopper-2025/evidence.csv)、[逐页清单](papers/hopper-2025/page-audit.csv)和[核验记录](papers/hopper-2025/verification.md)。

## 27. Flowcut：排空在途数据后再切换路径

论文题目：*Flowcut Switching: High-Performance Adaptive Routing with In-Order Delivery Guarantees*，Tommaso Bonato、Daniele De Sensi、Salvatore Di Girolamo、Abdulla Bataineh、David Hewson、Duncan Roweth、Torsten Hoefler；阅读版本为 arXiv:2506.21406v2，固定 PDF 共 16 页。

### 发表信息

正式发表在 *IEEE Transactions on Networking*，2026 年，第 34 卷，1974–1987 页，DOI：10.1109/TON.2025.3636209。CCF 推荐目录第七版（2026 年 3 月更新）的计算机网络领域，将旧刊名 *IEEE/ACM Transactions on Networking* 列为 A 类；IEEE 官方期刊清单将旧名标为现刊名的前名。但 CCF 未以新刊名单独列项，本篇新名是否可直接适用该级别待核实。类别描述 venue 推荐，不代表单篇质量。论文为期刊文章，不涉及会议 Full paper／Regular paper 资格。arXiv v1 最早公开于 2025 年 6 月 26 日，v2 于 2025 年 11 月 19 日提交；出版社首次在线日期待核实。Crossref 的 DOI 创建日不能代替上线日期。[arXiv 版本记录](https://arxiv.org/abs/2506.21406)、[CCF 第七版目录](https://www.ccf.org.cn/Academic_Evaluation/By_category/2026-03-05/861526.shtml)、[IEEE 期刊信息](https://ieeexplore.ieee.org/xpl/aboutJournal.jsp?punumber=10723154)、[IEEE 刊名清单](https://open.ieee.org/wp-content/uploads/IEEE-Title-List-August-2025.pdf)。

### 内容总结

逐包选路能利用多条路径，却可能让同一流乱序；Flowlet 依赖足够长的发送空隙，持续发送的 RDMA 流往往难以满足。Flowcut 记录每流在途字节数，并用逐包 ACK 清账。只有旧窗口的数据全部确认后，后续包才能另选路径。若拥塞持续，入口可暂停该流，待在途数据排空后再恢复并换路。论文用 SST 模拟 1024 节点 fat tree 和 Dragonfly 网络，并在 2048 端点 Slingshot 上比较有序与无序模式。作者报告仿真中的排空平均占总运行时间约 5.2%～11.3%；真实系统的有序模式完成时间比无序模式约高 24%。

### 经验学习

值得借鉴的是把保序条件落实为可检查的在途状态，并同时计入暂停排空成本。逐包喷洒的 FCT 较低，但乱序包超过一半；Flowcut 在部分测试中接近受控乱序率的 Flowlet。模拟器、网络、流量和传输条件限制了外推范围，部分图未报告误差与种子。

### 项目适用

ns-3 可模拟 outstanding 字节、ACK、首个 BDP 同路、拥塞触发排空与停顿成本。本项目应同时观察 MoE 合成通信批次完成时间、背景流 P99 FCT 和乱序／重传代价。论文未评测 MoE 与背景流竞争，也未展示这两项主结果共同改善；论文效果不能写成本项目收益。

### 硬件依赖与边界

逐流 FGFC 暂停、交换机逐包状态和 ACK 生成依赖交换机/NIC。PFC 可替代逐流暂停，但会波及同一流量类。ns-3 能验证模型行为，不能证明 ASIC 存储、线速状态访问或真实 NIC 固件具备相同能力。阅读对象为 arXiv v2，尚未逐项比较期刊稿。

阅读日期：2026 年 10 月 15 日。参见[完整报告](papers/flowcut-2026/analysis.md)、[技术附件](papers/flowcut-2026/analysis-technical.md)、[证据表](papers/flowcut-2026/evidence.csv)、[逐页清单](papers/flowcut-2026/page-audit.csv)和[核验记录](papers/flowcut-2026/verification.md)。

## 28. FlowDyn：按路径时延差动态设置 Flowlet 间隔

论文题目：*FlowDyn: Towards a Dynamic Flowlet Gap Detection using Programmable Data Planes*，Cristian Hernandez Benet、Andreas J. Kassler；固定阅读版本为 arXiv:1910.03324v1。

### 发表信息

正式发表在 2019 IEEE 8th International Conference on Cloud Networking（CloudNet），DOI：10.1109/CloudNet47604.2019.9064146。CCF 第七版（2026 年 3 月 31 日正式发布，4 月 9 日勘误）计算机网络领域未收录。Crossref 记录出版月份为 2019 年 11 月；IEEE 首次在线的具体日期待核实。arXiv v1 最早公开于 2019 年 10 月 8 日。官方征稿启事区分 6 页以内的 Full paper（口头报告）和 3 页以内的 Short paper（海报）；论文集列为 7 页长文，强烈支持 Full paper，但公开目录没有论文级轨道标签，故尚不能完全确认。

### 内容总结

FlowDyn 用周期探针发现源、目的 ToR 之间的路径，并按最快与最慢路径的单向时延差设置 flowlet gap。目的 ToR 将新 gap 搭载在反向数据包或 ACK 上，途经交换机据此更新 flowlet 判断。探针失效时机制退回较大的保守值。论文指出探测和反馈约需 RTT 量级，难以跟上亚 RTT 微突发。NS-2 中的 TCP Fat-tree 实验报告：Data-mining 流量在 10% 负载时，FlowDyn-HULA 平均 FCT 比静态 HULA 小 3.19 倍；非对称 Web-search 在 90% 负载时，FlowDyn-LetFlow 比静态 LetFlow 小 1.16 倍。图中无原始数据、误差线或重复次数。

### 经验学习

可借鉴把路径时延差、探针周期、反馈年龄、过期回退和安全余量作为一个闭环评估。阶梯化 gap 用余量抵御采样噪声，但无法保证适应亚 RTT 突变。作者的平均 FCT 结果来自特定 TCP/NS-2 场景，不能从曲线精确重算，也没有乱序或重传数据。

### 项目适用

本项目可在 ns-3 表达探针、逐路径时延状态、gap 更新和过期回退。项目两类业务均为 RDMA QP，关注 MoE 合成批次完成时间与背景流 P99 FCT，并把乱序及重传作为代价；论文只测 TCP 平均 FCT。FlowDyn 没有证明本项目任一主指标会改善，也没有评测 ConWeave。

### 硬件依赖与边界

探针复制、P4 寄存器表和中间交换机读写属于可编程数据平面实现。论文只估算约 130 KB/张远端表和 100 KB 本地表，未在真实 ASIC、网卡或 SmartNIC 上测试。ns-3 无法验证硬件线速、寄存器访问、真实时钟漂移或 RNIC 乱序行为。

阅读日期：2026 年 10 月 16 日。参见[完整报告](papers/flowdyn-2019/analysis.md)、[技术附件](papers/flowdyn-2019/analysis-technical.md)、[证据表](papers/flowdyn-2019/evidence.csv)、[逐页清单](papers/flowdyn-2019/page-audit.csv)和[核验记录](papers/flowdyn-2019/verification.md)。

## 29. REPS：缓存畅通路径熵值的逐包喷洒

论文题目：*REPS: Recycled Entropy Packet Spraying for Adaptive Load Balancing and Failure Mitigation*，Tommaso Bonato 等；固定版本 arXiv:2407.21625v6（22 页）。

### 发表信息

正式 venue：EuroSys 2026，DOI：10.1145/3767295.3769320，Full/Regular paper，pp. 225–246。CCF 第七版（2026）将 EuroSys 列入“计算机体系结构/并行与分布计算/存储系统”A 类；计算机网络方向未列该会议。最早公开日期为 arXiv v1 的 2024 年 7 月 31 日（UTC）；正式出版日期为 2026 年 4 月 26 日。会议于 4 月 27—30 日举行。

### 内容总结

REPS 面向逐包喷洒产生的拥塞和故障路径问题。接收端把数据包的熵值随 ACK 回传；发送端缓存未标记 ECN 的熵值，之后优先重用。检测到丢包或链路故障时，发送端冻结随机探索，沿近期表现良好的路径继续发送。作者用 htsim 和改造过的 FPGA RDMA 网卡评估，并报告它在多种不对称与故障场景下优于随机喷洒。

### 经验学习

可以借鉴的是分开考察选路、拥塞控制和故障反馈，并把冻结探索写成可检验规则。论文的球入箱模型只证明特定条件下单交换机的局部收敛，不能扩写成多跳网络的普遍保证。

### 项目适用

REPS 可作为端点逐包选路、ACK/ECN 反馈和健康路径缓存的参照。项目可检查这些信号对 MoE 批次完成时间、背景 P99 FCT 的影响，并同步观察乱序和重传。论文没有评估 MoE 类别感知包／流混合选路，也没有报告这两个主指标的联合结果；论文收益不构成本项目收益证据。它没有与 ConWeave 直接比较。

### 硬件依赖与边界

作者的硬件结果依赖改造 FPGA RDMA NIC、自定义乱序传输、256-bit SACK 和特定交换机。论文没有完整量化乱序深度、接收缓存和排序等待成本。ns-3 可借鉴算法结构，不能据此验证真实 RNIC、FPGA 或交换芯片效果。

阅读日期：2026 年 10 月 17 日。参见[完整报告](papers/reps-2026/analysis.md)、[技术附件](papers/reps-2026/analysis-technical.md)、[证据表](papers/reps-2026/evidence.csv)、[逐页清单](papers/reps-2026/page-audit.csv)和[核验记录](papers/reps-2026/verification.md)。


## 30. DCQCN：用逐流反馈抑制 PFC 级联

论文题目：*Congestion Control for Large-Scale RDMA Deployments*。Yibo Zhu 等，ACM SIGCOMM ’15 正式论文版，14 页。

### 发表信息

正式 venue：ACM SIGCOMM ’15，DOI：10.1145/2785956.2787484。CCF 第七版（2026），计算机网络 A 类；主会 Full/Regular 论文。最早可核验公开日期和出版方首次在线日期均为 2015 年 8 月 17 日。来源见[核验记录](papers/dcqcn-2015/verification.md)。

### 内容总结

PFC 会按端口暂停数据，拥塞可能扩散到同端口上的其他流。DCQCN 让交换机用 ECN 标记拥塞，接收端 NIC 以 CNP 通知发送端，发送端 NIC 再按流降速和逐步恢复。PFC 仍负责避免突发溢出，因而 DCQCN 不能脱离正确的交换机 buffer 阈值。论文在 40 Gbps 三层 Clos 测试床和特定 Mellanox NIC 上报告吞吐、公平性、PAUSE 数量与队列长度改善。10:1 incast 下，incast 流 P10 吞吐由低于 1.12 Gbps 提高到 3.43 Gbps。5 对无 DCQCN 与 80 对启用 DCQCN 的用户流比较，得到约 16 倍流量承载结果。该 workload 是合成流量，并非真实 trace 重放。

### 经验学习

值得借鉴的是把链路级保护和端到端调速放在不同时间尺度评估，并分清 egress ECN 与 ingress PFC 的门限。作者先用流体模型选参，再用小型硬件实验验证。模型忽略 PFC 与部分增速分支，稳定性证明未完成；论文还承认多瓶颈公平性未完全解决。

### 项目适用

项目可在 ns-3 中抽象逐 QP 标记、CNP 和 PFC 事件，并借鉴对反馈收敛与队列的观测。项目两类流均为 RDMA QP，核心结果仍是 MoE 合成通信批次完成时间和背景流 P99 FCT，乱序作为代价约束。论文 throughput、queue P95、PAUSE 计数和“16 倍用户流量”不等同于项目双主结果，也不能外推成项目收益。DCQCN 调发送速率；项目关注类别感知选路，二者不是同一机制。

### 硬件依赖与边界

真实部署依赖 NIC 上每流限速定时器、字节计数器、CNP 处理和接收端状态；交换机需支持 RED/ECN、共享 buffer 动态 PFC 阈值和足够 headroom。ns-3 无法验证硬件状态容量、ASIC 阈值实现、NIC 固件代价或真实集群效果。

阅读日期：2026 年 10 月 19 日。参见[完整报告](papers/dcqcn-2015/analysis.md)、[技术附件](papers/dcqcn-2015/analysis-technical.md)、[证据表](papers/dcqcn-2015/evidence.csv)、[逐页清单](papers/dcqcn-2015/page-checklist.md)和[核验记录](papers/dcqcn-2015/verification.md)。


## 31. IRN：选择性重传与有限窗口支持有损 RDMA

论文题目：*Revisiting Network Support for RDMA*，Radhika Mittal 等；固定阅读版为 ACM SIGCOMM 2018 正式论文 PDF，正文 14 页，另含 1 页 ACM 封页。

### 发表信息

正式发表在 ACM SIGCOMM ’18，页码 313～326，DOI：10.1145/3230543.3230557。CCF 第七版（2026 年 3 月正式发布、4 月勘误）计算机网络 A 类；论文为主会 Full/Regular 长文。最早公开日期为 arXiv v1 的 2018 年 6 月 21 日；出版社首次在线日期为 2018 年 8 月 7 日。来源见[核验记录](papers/irn-2018/verification.md)。

### 内容总结

IRN 修改 RoCE 网卡的丢包恢复，使 RDMA 可以在不启用 PFC 的网络中运行。接收端保留乱序包，并用 NACK 携带累计确认和选择确认线索；发送端维护位图，只重传有证据表明丢失的包。另用静态 BDP 窗口限制在途包数，既约束排队，也限制乱序状态。对少量在途包，IRN 使用较短超时；窗口较大时改用较长超时。论文在供应商扩展的 OMNeT++/INET RoCE 模拟器中报告，IRN 无 PFC 相对 RoCE 加 PFC 在默认场景的三项指标上最高改善 2.8～3.7 倍，跨多个场景为 6%～83%。FPGA 综合与 NIC 状态估算给出实现可行性的初步证据。

### 经验学习

关键设计不是“允许乱序”本身，而是将乱序接收、选择确认、丢包判定、窗口边界和 RDMA 完成语义一起实现。消融结果显示，SACK 选择重传比 go-back-N 更关键，BDP-FC 则减少额外排队并限制状态规模。论文也明确展示无 PFC 下仍有丢包和恢复延迟。

### 项目适用

本项目只有 ns-3，两类业务均为 RDMA QP，关注 MoE 合成通信批次完成时间与背景 P99 FCT，并将乱序作为代价。IRN 可为传输恢复建模提供参照，但它不是类别感知选路策略。论文没有测试 MoE、混合业务双侧结果或这两个项目主指标。引用的性能收益不能外推成本项目收益。

### 硬件依赖与边界

作者报告的 3%～10% NIC cache 状态估计、FPGA FF/LUT 占用和模块吞吐来自特定设备与简化 HLS 设计。ns-3 无法验证真实 NIC/FPGA/ASIC 资源、DMA、网卡时序或生产网络关闭 PFC 的安全性。论文没有随文提供可独立复现的完整实验工件。

阅读日期：2026 年 10 月 20 日。参见[完整报告](papers/irn-2018/analysis.md)、[技术附件](papers/irn-2018/analysis-technical.md)、[证据表](papers/irn-2018/evidence.csv)、[逐页清单](papers/irn-2018/page-checklist.md)和[核验记录](papers/irn-2018/verification.md)。


## 32. DART：按拥塞位置分治，分别限速与保序转向

论文题目：*Dart: Divide and Specialize for Fast Response to Congestion in RDMA-Based Datacenter Networks*，Jiachen Xue、Muhammad Usama Chaudhry、Balajee Vamanan、T. N. Vijaykumar 和 Mithuna Thottethodi；固定版本为作者公开的 IEEE/ACM Transactions on Networking 期刊版 PDF，14 页。

### 发表信息

正式 venue 为 IEEE/ACM Transactions on Networking，2020 年第 28 卷第 1 期，322～335 页，DOI：10.1109/TNET.2019.2961671。CCF 第七版（2026 年 3 月更新），计算机网络 A 类期刊。此为 venue 类别；期刊目录不标注单篇 Full/Regular 标签。arXiv v1 最早公开日期为 2018 年 5 月 28 日（UTC）。期刊正式年份、卷期可核验；IEEE Xplore 的首次在线具体日期仍待核实，不能用接受日或 arXiv v2 日期替代。

### 内容总结

论文按拥塞位置选择处理办法。接收端维护活动发送者数，并把计数放入 ACK，让发送端直接分摊速率（DASR）。短消息遇到局部路径拥塞时，交换机用保序流转向（IOFD）避开队列；分散拥塞仍交给 DCQCN。作者在 20 节点真实设备上只测试了应用层 DASR 原型；IOFD 和完整 DART 的结果来自 1024 主机 Clos 的 ns-3 仿真。典型负载下，仿真的短流 P99 时延比 DCQCN 和 TIMELY 低 79%（约 4.8 倍），但网络负载和短流路径长度也增加。论文没有测量 MoE 批次或背景流 P99。

### 经验学习

可借鉴的是先判断拥塞发生在哪里，再按可观测条件选择快速处理或回退。DASR 依赖接收端准确计数；IOFD 依赖交换机 DFT/CAM、有限转向次数和严格的消息内保序。测试床应用层 DASR 的 P90、P99、P99.9 收敛时间为 28、41、44 μs，而 unloaded RTT 为 15 μs，因此“一 RTT”机制目标不能写成实测所有分位都在一 RTT 内完成。

### 项目适用

本项目两类流均为 RDMA QP，可在 ns-3 中研究接收端 incast 计数、速率分摊、局部转向、DCQCN 回退和乱序代价。验收仍应同时看 MoE 合成批次完成时间与背景流 P99 FCT。DART 研究的是拥塞控制与短消息保序转向，不等同于类别感知流/包选路；论文收益不是项目收益证据。

### 硬件依赖与边界

DASR 实际集成涉及 NIC 消息状态、ACK/固件处理；IOFD 依赖交换机 CAM/DFT、线速查询、消息标识、token 和 virtual lane。ns-3 可以验证抽象状态逻辑，不能证明真实网卡或交换机的资源、时序和部署能力。论文没有在真实设备上验证完整 DART。

阅读日期：2026 年 10 月 21 日。参见[完整报告](papers/dart-2020/analysis.md)、[技术附件](papers/dart-2020/analysis-technical.md)、[证据表](papers/dart-2020/evidence.csv)、[逐页清单](papers/dart-2020/page-checklist.md)和[核验记录](papers/dart-2020/verification.md)。


## 33. MSwift 与 MNSCC：用中位数反馈缓解拥塞路径误判

论文题目：*Congestion Control for Spraying with Congested Paths*，Barak Gerstein、Mark Silberstein、Isaac Keslassy；固定版本 arXiv:2509.07907v2，11 页。

### 发表信息

arXiv v1 最早公开于 2025 年 9 月 9 日；v2 于 2026 年 3 月 19 日更新。当前正式 venue、出版方 DOI 与正式出版日期待核实。arXiv DOI `10.48550/arXiv.2509.07907` 是预印本 DOI。CCF 第七版（2026）已发布；本篇尚无可确认的正式 venue，故不适用 CCF venue 类别及 Full/Regular 资格。来源：arXiv 版本记录、作者 Isaac Keslassy 的 Manuscript 列表和 CCF 官方目录说明。

### 内容总结

逐包喷洒时，少数拥塞路径会反复返回高时延或 ECN 信号。单路径拥塞控制若只看最近一次反馈，可能让一条慢路径代表整个 QP，导致持续降速。论文在单流、恒定路径时延差等模型下，推导五类 CCA 的吞吐量按拥塞概率平方根倒数下降。MSwift 和 MNSCC 分别对 Swift、NSCC 最近一段 ACK 时延取中位数；MSwift 还以 LSwift 缓解乱序。htsim 仿真在置换、ECMP 背景和 Llama 70B HSDP 等条件下报告较低 CCT inflation。REPS 默认场景中，MSwift 相对 LSwift 的额外 CCT inflation 约低 8.6 倍。论文没有把这比值报告为整体训练提速。

### 经验学习

可借鉴的是分别检查选路、拥塞信号、调速和乱序恢复。中位数窗口有反馈稳健性与响应延迟的权衡，作者给的 Nyquist 取值只是调参启发。图 4 的 AR 组显示 MSwift 为 33%，NSCC 为 30%，与正文“所有选路都优于 NSCC”的概括不一致，阅读时应保留原图数值。实验来源代码仓库可查，但论文未固定每图 commit、完整配置、seed 和原始数据。

### 项目适用

本项目仅用 ns-3，研究类别感知包／流混合负载均衡；两类流都是 RDMA QP。项目双主结果是 MoE 合成通信批次完成时间和背景 P99 FCT，乱序是代价约束。本篇讨论端侧 CCA 反馈规则，不是类别选路策略，且未覆盖项目双侧指标。可保留为反馈机制分析参考；作者性能不构成本项目收益证据。

### 硬件依赖与边界

论文仿真不验证真实 RNIC 的队列对行为、SACK/READ/WRITE 细节、硬件中位数或伪中位数电路、并发更新和线速成本。ns-3 可表达反馈窗口与时序，不能据此确认交换机或网卡部署效果。

阅读日期：2026 年 10 月 22 日。参见[完整报告](papers/mswift-mnscc-2025/analysis.md)、[技术附件](papers/mswift-mnscc-2025/analysis-technical.md)、[证据表](papers/mswift-mnscc-2025/evidence.csv)、[逐页清单](papers/mswift-mnscc-2025/page-checklist.md)和[核验记录](papers/mswift-mnscc-2025/verification.md)。


## 34. ExpressPass：先发信用包，再按信用发送数据

论文题目：*Credit-Scheduled Delay-Bounded Congestion Control for Datacenters*，Inho Cho、Keon Jang、Dongsu Han；固定阅读版为 ACM SIGCOMM ’17 正式版 PDF，14 页，arXiv 预印本另存并逐项比较。

### 发表信息

正式 venue：ACM SIGCOMM ’17，DOI：10.1145/3098822.3098840，页码 239～252。CCF 第七版（2026）计算机网络 A 类；主会正式长文，Full paper 资格据正式论文集和篇幅判断，未见单篇显式标签。arXiv v1 最早公开于 2016 年 10 月 15 日；出版社首次在线为 2017 年 8 月 7 日。CCF 级别描述 venue，不是论文质量评级。来源见[核验记录](papers/expresspass-2017/verification.md)。

### 内容总结

ExpressPass 用反向信用包预先安排数据发送：接收端发 credit，交换机逐端口限速，发送端收到 credit 才发数据。这样可以快速增速，同时把拥塞主要转成可丢弃的 credit。信用占链路约 5.18%，还要求信用与数据走对称路径。作者的测试床和 ns-2 结果显示，机制能快速收敛、压低数据队列；shuffle incast 中位数 FCT 略逊于 DCTCP，但 P99 和最大 FCT 更低。真实流量仿真显示短流受益，长流在部分条件下会变慢，信用浪费在小流场景中很高。

### 经验学习

值得借鉴的是把选路、拥塞反馈、缓冲上界和信用浪费分开分析，再联合检查长短流与尾延迟。机制依赖对称路径、信用丢失反馈、有限缓冲和同速/同步控制假设。作者给出了原型实现，也说明了参数和工作负载如何改变结论；但未提供完整可独立复现的源代码、trace、seed 和逐图原始数据。

### 项目适用

本项目仅用 ns-3，研究两类 RDMA QP 的 AI/MoE 包／流混合选路，主指标为 MoE 批次完成时间与背景 P99 FCT，乱序是代价。ExpressPass 是拥塞控制方法参考，不是选路算法；论文没有测试 MoE、ConWeave 或这两项双侧指标。可借鉴反馈时延、信用开销与 P99 的评估方法，不能把论文收益写成本项目效果。

### 硬件依赖与边界

作者测试床依赖 SoftNIC/DPDK、Broadcom 交换机限速、Quanta T3048-LY2 和 Intel X520 NIC。ns-3 能模拟信用包、队列和反馈，无法证明 ASIC 线速、NIC 固件成本或真实集群部署效果。

阅读日期：2026 年 10 月 23 日。参见[完整报告](papers/expresspass-2017/analysis.md)、[技术附件](papers/expresspass-2017/analysis-technical.md)、[证据表](papers/expresspass-2017/evidence.csv)、[逐页清单](papers/expresspass-2017/page-checklist.md)和[核验记录](papers/expresspass-2017/verification.md)。


## 35. RPS：对称路径上的逐包随机喷洒

论文题目：*On the Impact of Packet Spraying in Data Center Networks*，作者 Advait Dixit、Pawan Prakash、Y. Charlie Hu、Ramana Rao Kompella；固定阅读版为 `paper-local.pdf`，共 9 页。它与 Purdue 作者主页托管 PDF 字节相同，属于作者托管版，未验证为 IEEE 版本记录（VOR）。本地 SHA-256 为 `dc6a784e348db0051b1147b0669db5a37ea19d0d373ee394bc543bf8d49eb04d`。

### 发表信息

正式 venue：IEEE INFOCOM 2013，*2013 Proceedings IEEE INFOCOM*，页码 2130～2138，DOI：10.1109/INFCOM.2013.6567015。根据正式论文集和 9 页主会长文，判断为 Full/Regular paper；没有找到单篇轨道标签。CCF 第七版（2026 年 3 月 31 日发布，4 月 9 日勘误），计算机网络 A 类。最早公开日期待核实；Crossref 记录出版月份为 2013 年 4 月，IEEE 精确首次在线日期待核实。CCF 类别描述 venue，不代表论文质量。

### 内容总结

RPS 让交换机逐包随机选择等价最短路径。论文认为，对称 Fat-tree 的同跳链路承载相近流量，因此各路径的队列和时延接近，TCP 可以容忍少量乱序。作者在 36 台服务器的 NetFPGA 测试床报告：RPS 平均吞吐约为理想值的 90%，路径队列差不超过 1 包的观测占 93%。队列差并非接收端乱序率。故障会破坏路径对称，一个双流实验中，未受故障影响流的吞吐从 407 Mbps 降到 155 Mbps。作者提出 S-RED，由故障管理器标记受影响流，再选择性启用 RED。

### 经验学习

可借鉴按拓扑位置划分等价链路，测量逐流路径份额和各路径排队差，再单独注入故障。评估需区分受影响与未受影响流，并把 RED 的吞吐代价和队列差变化一起报告。论文的主要结果来自长短 TCP 流、ping 与 Hadoop Sort 等不同负载；这些证据不能合并成统一的尾延迟结论。S-RED 依赖故障识别、包标记和交换机分类队列。

### 项目适用

本项目仅用 ns-3，两类业务均为 RDMA QP；主指标是 MoE 合成通信批次完成时间和背景 P99 FCT，乱序作为代价。可将逐包喷洒、路径不对称和队列差测量建模，观察乱序、重传与双侧指标。RPS 研究 TCP，没有评估 MoE、背景 P99 或 ConWeave，不能据论文数字推断项目收益。RPS 的逐包随机路由也不同于 CONGA 的拥塞感知 flowlet、LetFlow 的 flowlet 重选，以及 ConWeave 的 epoch／phase 和接收 ToR VOQ；论文没有直接比较这些方案。

### 硬件依赖与边界

NetFPGA／ASIC 每包选口、故障管理器、S-RED 队列与真实 RDMA NIC 行为都依赖硬件或控制面。ns-3 可验证模型逻辑，不能证明线速实现能力或真实网卡的乱序恢复表现。

阅读日期：2026 年 10 月 24 日。参见[完整报告](papers/rps-2013/analysis.md)、[技术附件](papers/rps-2013/analysis-technical.md)、[证据表](papers/rps-2013/evidence.csv)、[逐页清单](papers/rps-2013/page-checklist.md)和[核验记录](papers/rps-2013/verification.md)。


## 36. LetFlow：随机选择 flowlet 路径，让单元大小随拥塞变化

论文题目：*Let It Flow: Resilient Asymmetric Load Balancing with Flowlet Switching*，Erico Vanini、Rong Pan、Mohammad Alizadeh、Parvin Taheri、Tom Edsall；固定阅读版为与 USENIX 官网逐字节相同的 NSDI 2017 正式 PDF，15 页。

### 发表信息

14th USENIX Symposium on Networked Systems Design and Implementation（NSDI 17），2017，页码 407～420，USENIX Association；官方记录未列 DOI。CCF 第七版（2026）计算机网络 A 类会议；主会 refereed Full/Regular paper。最早可核验公开日和出版方公开日均为 2017-03-27，依据 CFP 的会议首日公开政策及正式日程；独立的条目上线时间戳待核实。

### 内容总结

LetFlow 在每个新 flowlet 到达时随机选一条可用路径，同一 flowlet 的后续数据包沿用原路径。flowlet 是同一条流中被空闲间隔分开的连续包段。作者发现，拥塞路径会压低流速，使 flowlet 更容易结束；快路径上的 flowlet 则能长得更大。因此，即便路径选择比例不准，分到快路径的字节数仍可能增加，形成隐式负反馈。交换机以 5 元组索引表项，用端口、有效位和 age 位记录当前 flowlet。硬件测试床中，作者报告 LetFlow 的平均 FCT 最差约比 CONGA 高 10%～20%；高不对称大规模仿真中，90% 负载下约在 CONGA 的 1.5 倍以内。它的反应是随机且被动的，作者承认短时拥塞仍可能增加排队时延。

### 经验学习

论文用偏离理想路径权重的实验，展示 flowlet 大小会怎样补偿选路偏差；也扫描了 timeout 和缓冲区，不只展示一个最佳点。Markov 模型解释了速率更低的路径为何更常发生 timeout，但模型假设独立 Poisson 到达和路径内公平带宽，不能代表一般 TCP 或 RDMA 流量。图 17 附近的链路名称和公式（2）的路径下标有排版不一致。

### 项目适用

ns-3 可抽象按 RDMA QP 维护 flowlet 路径和超时，并联合测量 MoE 合成通信批次完成时间、背景 P99 FCT 与乱序代价。论文的 FCT 结论不能当作本项目收益证据；其机制是否改善双主指标仍待验证。

### 硬件依赖与边界

论文报告交换芯片中的 flowlet table 约需 3 Mbit 存储和 150K gates，并称已有硅实现；但未公开芯片型号和完整实现资料。论文使用 TCP、DCTCP、DCQCN、真实服务器测试床与 OMNeT++/Network Simulation Cradle 仿真。本项目只有 ns-3 RDMA QP，无法据此验证真实网卡、交换芯片、PFC 或生产网络收益。

阅读日期：2026 年 10 月 25 日。参见[完整报告](papers/letflow-2017/analysis.md)、[技术附件](papers/letflow-2017/analysis-technical.md)、[证据表](papers/letflow-2017/evidence.csv)、[逐页清单](papers/letflow-2017/page-checklist.md)和[核验记录](papers/letflow-2017/verification.md)。


## 37. APS：短流与长流的自适应路径隔离

论文题目：*APS: Adaptive Packet Spraying to Isolate Mix-flows in Data Center Network*；Jingling Liu、Jiawei Huang、Wenjun Lv、Jianxin Wang；作者公开的 14 页 IEEE 接收稿。

### 发表信息

正式发表于 IEEE Transactions on Cloud Computing，2022 年，10(2):1038–1051，DOI：10.1109/TCC.2020.2985037。CCF 第七版（2026）将该期刊列于计算机体系结构/并行与分布计算/存储系统领域的 C 类；论文为常规期刊论文。该级别描述 venue 推荐类别，不代表单篇论文质量。IEEE 首次在线/出版日期为 2020 年 4 月 16 日；作者机构页另记 4 月 18 日发布。两日期与正式卷期年分开记录。

### 内容总结

APS 面向短流和长流共存时的资源冲突。短流要求低时延，长流希望持续获得带宽。APS 在交换机根据已发送字节区分流类型，并检测短流是否活跃。短流活动期间，短流在专用路径上逐包喷洒；长流只在剩余路径上使用 ECMP。这样既减少长流对短流的干扰，也降低混合传输时的长流乱序。短流空闲时，长流可扩展到所有路径，以利用空余带宽。

作者用 M/G/1 队列模型估计满足短流截止期所需的路径数，并以 NS2 和小型 DPDK 测试床评估。论文摘要报告短流平均完成时间最多降低 60%，长流吞吐约提升 1.68 倍；DPDK 测试床的具体比例依应用和比较方案而异。论文也观察到路径切换会产生短暂乱序。模型、结果均依赖论文流量和网络配置。

### 经验学习

值得借鉴的是按类别隔离并在空闲期借出资源，同时报告两类流的指标和乱序代价。论文把选路、流大小分类和队列模型连成一套机制说明。需谨慎看待其泊松到达、固定服务率模型，以及流大小阈值和活跃检测窗口的敏感性。

### 项目适用

项目只有 ns-3 RDMA QP，关注 MoE 合成通信批次完成时间和背景 P99 FCT，并将乱序作为代价指标。APS 的短流 AFCT/P99 与长流 TCP 吞吐不能直接替代这些目标。可将类别路径隔离与空闲容量借用作为待验证思路；只有对应项目实验原始数据才能说明收益。本次阅读未运行项目实验。

### 硬件依赖与边界

APS 需要交换机逐包分类、维护每流状态、检测短流活动并在 ECMP/RPS 路径集合间切换。作者报告的测试床是四台工作站和两台 DPDK 软件交换机，不是生产 ASIC 或 RDMA 网卡。论文没有证明芯片线速实现，也没有验证本项目的 RDMA 乱序代价。

阅读日期：2026 年 10 月 26 日。参见[完整报告](papers/aps-2020/analysis.md)、[技术附件](papers/aps-2020/analysis-technical.md)、[证据表](papers/aps-2020/evidence.csv)、[逐页清单](papers/aps-2020/page-checklist.md)和[核验记录](papers/aps-2020/verification.md)。



## 38. PDLB：按路径差异调整 flowcell 粒度

论文题目：*PDLB: Path Diversity-aware Load Balancing with adaptive granularity in data center networks*，Gao 等。固定阅读版本为 Springer 正式版，16 页。

### 发表信息

正式 venue：*Journal of Cloud Computing* 12（1），Article 173（2023）；DOI：`10.1186/s13677-023-00548-x`。最早核实公开日期：2022-01-12，Research Square 预印本 Crossref posted 记录。出版社正式在线日期：2023-12-07。经 CCF 第七版（2026）官网相关领域目录检索，该刊未收录；期刊论文不适用会议 Full/Regular 资格判定。

### 内容总结

路径时延不一致时，逐包喷洒虽能用上更多链路，却会增加后发包超越先发包的机会；逐流选路较少乱序，但可能闲置路径。PDLB 在发送端估计 RTT，并按路径差动态调整 flowcell 大小：路径接近时切细，差异扩大时切粗。作者用 NS2/TCP 仿真比较短流 FCT、长流吞吐、链路利用和乱序。大规模场景有 256 台主机、8 条路径和 Web Search/Data Mining 负载；报告短流 P99 改善最高约 20%～73%，长流平均 FCT 改善最高约 8%～53%。这些范围对应不同工作负载、负载点与对照，不能视作统一收益。论文没有真实硬件实验。

### 经验学习

值得借鉴的是把粒度、路径差、利用率、完成时间和乱序/重传放在同一评估中，并主动改变坏路径数量与时延。作者先做受控机制测试，再扩展到流量模型和 256 主机场景。理论将路径简化为快慢两类，结合乱序概率与 TCP 窗口变化估算 FCT；它解释了机制链条，但依赖简化假设。原文的拥塞阈值、flowcell 粒度映射、缓冲区和模型验证流量数有口径差异，均应保留。公开仓库提供部分代码和 trace，未确认完整复现材料。

### 项目适用

项目可以借用路径差与乱序联合诊断的方法。项目两类业务都是 RDMA QP，主指标为 MoE 合成通信批次完成时间和背景流 P99 FCT，乱序为代价约束。PDLB 的 TCP 短流尾部和平均 flow FCT 不能替代项目指标；论文也没有测试 MoE 与背景业务竞争。是否适用须由固定源码和对应实验 ID 原始数据验证。

若未来把粒度纳入项目机制比较，应记录各类别的 flowcell/包大小、路径 RTT 差、路径使用情况、乱序计数和重传代价，并检查它们与批次完成时间及背景 P99 的逐格对应。PDLB 只给出作者环境下的 TCP 单流及短长流结果；这些观察既不能证明项目收益，也不能替代固定基线和项目原始数据。

### 硬件依赖与边界

PDLB 主要部署在发送端，但依赖 TCP ACK/时延、拥塞窗口、探测与分段调度。论文没有报告真实 TSO/NIC 兼容性或 CPU 开销。Presto 用固定 flowcell 并修改 GRO；LetFlow 按包间隔切 flowlet；APS 按短长流类别分路径；ConWeave 面向 RDMA 换路并在目的 ToR 暂存乱序。它们机制位置和传输语义均不同，NS2/TCP 结果不能外推到本项目 QP 或硬件部署。

这些机制各有适用问题：Presto 研究固定分块的路径分担和 TCP 接收端合并；LetFlow 利用足够长的包间隔切换路径；APS 在短流活跃时隔离长流，短流暂停后再借用路径；ConWeave 解决 RDMA 换路产生的乱序。PDLB 则需要可由发送端观测的 RTT 差，并假定 TCP 响应能为粒度模型提供依据。比较时应保留这些前提，不能只按“粒度更细”或“尾部更低”给机制排序。

阅读日期：2026 年 10 月 27 日。参见[完整报告](papers/pdlb-2023/analysis.md)、[技术附件](papers/pdlb-2023/analysis-technical.md)、[证据表](papers/pdlb-2023/evidence.csv)、[逐页清单](papers/pdlb-2023/page-checklist.md)和[核验记录](papers/pdlb-2023/verification.md)。



## 39. DRILL：每个交换机按包选择较短队列

论文题目：*DRILL: Micro Load Balancing for Low-latency Data Center Networks*。作者为 Soudeh Ghorbani、Zibin Yang、P. Brighten Godfrey、Yashar Ganjali、Amin Firoozshahian。阅读版本为作者版 14 页，SHA-256：`d5bbb340c1652d21d7e524f16d691af370d0ec775ab9f26847559d4970ddb3a1`。

### 发表信息

正式 venue 为 ACM SIGCOMM 2017 论文集，页码 225–238，DOI：10.1145/3098822.3098839。最新正式 CCF 目录为第七版（2026），计算机网络领域 A 类会议。论文列于 SIGCOMM 主会技术 session，符合 Full/Regular 长文计入资格。版本最早公开日期待核实；Crossref DOI 元数据显示出版方日期为 2017 年 8 月 7 日。CCF 类别是 venue 推荐，不是单篇论文评级。

### 内容总结

ECMP 按流哈希选路，长流碰撞时会让部分路径拥挤。DRILL 每个交换机为每个包抽查少量候选出口的队列，并选择较短的出口。算法还记住一个此前较短的队列，以减少随机选择造成的误差。论文主用 DRILL(2,1)，即两个随机候选和一个记忆候选。它不依赖跨交换机的拥塞反馈，因此可在本地快速响应。

逐包分路可能造成乱序。作者在 OMNeT++/INET 中模拟 Linux 2.6 TCP，报告 80% 负载下 0.4% 的流出现重复 ACK，0.02% 的流超过常见 TCP 重传门槛。DRILL 还把不对称路径分组，只在相似路径组里逐包均衡。对称 Clos 的 80% 负载案例中，DRILL 平均 FCT 约为论文实现的 Presto、CONGA 和 ECMP 的 1/1.3、1/1.4 和 1/1.6。该结果来自 TCP 模拟；incast 的 99.99 百分位不能当作项目背景 P99。

### 经验学习

可借鉴的是把快速局部反馈与反馈的可见范围分开分析，并留意多个并行决策源可能同步选中同一出口。作者也展示了过多采样候选可能适得其反。论文的性能受 Clos 拓扑、队列采样和 TCP 实现限制；图 14 正文与图注对第二负载点的记载不一致。

### 项目适用

本项目只有 ns-3 RDMA QP，主要观察 MoE 合成通信批次完成时间与背景流 P99 FCT，并将乱序作为代价约束。可把局部队列可见范围、采样延迟和决策同步作为后续研究问题。RPS 在对称路径上逐包随机选路，并讨论链路故障与 S-RED；DRILL 读取队列并在不对称时先分路径组。ConWeave 使用 TxToR 的 epoch/phase、RxToR VOQ 和反馈。本文没有评估 ConWeave，也没有 MoE 批次时间或背景 P99 结果。

### 硬件依赖与边界

DRILL 使用交换机本地队列采样、并行转发引擎及控制面路径分组。作者用 Verilog 和 Vivado 估算逻辑面积，不是实际芯片测试。TCP 乱序、GRO、真实队列遥测精度和线路速率均不能由本项目 ns-3 结果验证。

阅读日期：2026 年 10 月 28 日。参见[完整分析](papers/drill-2017/analysis.md)、[技术附件](papers/drill-2017/analysis-technical.md)、[证据表](papers/drill-2017/evidence.csv)、[逐页清单](papers/drill-2017/page-checklist.md)和[核验记录](papers/drill-2017/verification.md)。


## 40. MP-RDMA：用 ACK 路径反馈分配流量，并控制接收端乱序

论文题目：Yuanwei Lu、Guo Chen、Bojie Li、Kun Tan、Yongqiang Xiong、Peng Cheng、Jiansong Zhang、Enhong Chen 和 Thomas Moscibroda，《Multi-Path Transport for RDMA in Datacenters》，USENIX NSDI 2018 固定会议版，PDF 共 16 页。

### 发表信息

正式 venue 为第 15 届 USENIX Symposium on Networked Systems Design and Implementation（NSDI 2018），页码 357～371，ISBN 978-1-939133-01-4。会议版未发现可核实 DOI。CCF 第七版（2026）将 NSDI 列为计算机网络 A 类；NSDI 2018 征稿为 Full paper，本篇是正式论文集长文，符合 Full paper 计入资格。最早公开日期待核实；出版方仅提供 2018 年 4 月，精确出版日待核实。USENIX 说明公众开放从会议开始，但这不提供该文的独立首发时间戳。会议举办日 2018 年 4 月 9～11 日不替代出版日期。CCF 等级是 venue 类别，不代表单篇论文质量。

### 内容总结

RDMA 连接通常固定走一条路径，可能受哈希碰撞、拥塞或故障影响。MP-RDMA 将一条连接分散到多个虚拟路径，并用同一个拥塞窗口控制整体发送。接收端 ACK 会回传包序号、拥塞标记和原路径编号；发送端据此逐包调整窗口，并优先从确认返回的路径继续发送。这样避免给每条路径复制完整拥塞状态。

多路径会引起乱序。接收端用小型位图记住包到达情况，发送端则根据序号落差逐步排除慢路径，尽量把乱序限制在位图容量内。普通数据可直接写入应用内存；若应用要求前序写入先完成，可标记同步操作并延迟发送。作者的 FPGA 原型每连接新增状态为 66 B。试验床中，5 对排列流量的总 goodput 比 DCQCN 高 47.05%；Web Search 仿真的平均 FCT 短 6.0%～17.7%。

### 经验学习

论文将拥塞反馈、路径选择、乱序跟踪和内存写入顺序连成一套设计，并通过模型、FPGA 原型、试验床和仿真分别检查。可借鉴这种分层验证方式。结果有明确范围：同步流体模型、指定链路配置和特定工作负载，并不保证异步混合业务也得到相同收益。

### 项目适用

本项目可借鉴测量 ACK 路径与拥塞、时延差和乱序的关联，并把乱序恢复代价纳入 MoE 合成通信批次时间与背景 P99 FCT 的联合分析。论文没有评测这两个项目指标，也没有比较 ConWeave。将 ACK 时钟或乱序剪枝移入 ns-3 前，需确认当前 RDMA QP 模型能否表达相关报文和接收状态；任何效果都须由本项目输入重新验证。

### 硬件依赖与边界

FPGA 线速、RNIC 状态容量、PCIe 延迟及原型包处理能力依赖真实硬件，不能由 ns-3 结果推出。会议版的 66 B 是每连接算法状态估算，不含全部实现开销。论文还存在特定路径和 PFC/RED 设置，背景 P99 FCT 未报告。

阅读日期：2026 年 10 月 29 日。参见[完整报告](papers/mp-rdma-2018/analysis.md)、[技术附件](papers/mp-rdma-2018/analysis-technical.md)、[证据表](papers/mp-rdma-2018/evidence.csv)、[逐页清单](papers/mp-rdma-2018/page-checklist.md)和[核验记录](papers/mp-rdma-2018/verification.md)。



## 41. Maestro：以多 QP 分块汇聚 RDMA 多路径

论文题目：Accelerating Distributed Deep Learning using Multi-Path RDMA in Data Center Networks。Feng Tian、Yang Zhang、Wei Ye、Cheng Jin、Ziyan Wu 和 Zhi-Li Zhang；固定阅读版本为 SOSR 2021 正式版 13 页 PDF。

### 发表信息

正式 venue 为 ACM SIGCOMM Symposium on SDN Research（SOSR），2021 年，DOI：10.1145/3482898.3483363。CCF 第七版（2026 年 3 月正式版）领域/类别和本篇 Full/Regular 资格待核实。最早公开日期待核实。Crossref published-online 为 2021 年 11 月 8 日；同记录的 published 与 published-print 为 2021 年 10 月 11 日，故保留字段差异，不以会议日期推断最早公开时间。

### 内容总结

Maestro 在应用与 RDMA 库之间加入用户态中间层。它把大消息拆成多个 chunk，为每块建立 WR，并投递到通过不同虚拟 IP 组织的多个 QP。网络再用 ECMP、静态路由或 SDN 规则把这些连接映射到多条路径。接收端根据预先登记的内存地址直接写入对应位置，再汇总各块完成状态。道路分箱的说法仅用于解释机制。

作者在 8 台服务器、两层脊叶网络和指定 RNIC/交换机上测试，报告路径吞吐汇聚、路径故障后转移和 collective 通信时间改善。消息传输最高约减少 60%，collective 通信最高约减少 66.7%。这些结果依赖核心链路瓶颈、硬件、流量和参数；论文没有测 MoE 批次时间或项目定义的背景 P99 FCT，也未提供已核验的完整公开复现材料。

### 经验学习

可借鉴的评估问题包括：逻辑路径是否映射到不同物理路径、路径监控是否及时、chunk 粒度如何同时影响响应速度和调度开销，以及端侧工作线程和 RNIC 在途状态如何计量。文中 50 KB chunk、每个 QP worker 约 6% CPU 开销和小流结果均属于作者测试床观测，不能写成普遍参数或无损保证。

### 项目适用

本项目可把多路径映射、状态更新延迟和分配粒度转成 ns-3 待验证假设。项目中的两类业务均为 RDMA QP，主要指标是 MoE 合成通信批次完成时间与背景 P99 FCT，乱序是代价约束。Maestro 的端侧 QP/WR 分片与项目交换机侧类别感知逐包/逐流选路处于不同层次。作者的性能数字不是本项目收益，也不构成机制准入依据。

### 硬件依赖与边界

机制依赖 RNIC 的多 QP、RoCE GID/IP 绑定、注册内存、DMA、CQE、DCQCN 计数器和用户态 RDMA 库，也依赖可预测 ECMP 或 SDN 规则。ns-3 可抽象路径映射与状态变化，不能证明真实网卡驱动、交换机行为、PFC/ECN 时序或硬件部署收益。本次未运行实验或修改项目代码。

阅读日期：2026 年 10 月 30 日。参见[完整报告](papers/maestro-2021/analysis.md)、[技术分析](papers/maestro-2021/analysis-technical.md)、[证据表](papers/maestro-2021/evidence.csv)、[逐页清单](papers/maestro-2021/page-checklist.md)和[核验记录](papers/maestro-2021/verification.md)。


## 42. Ethereal：应用层拆分少量流并分配路径

论文题目：*Ethereal: Divide and Conquer Network Load Balancing in Large-Scale Distributed Training*，Vamsi Addanki、Prateesh Goyal、Ilias Marinos 和 Stefan Schmid；固定版本为 arXiv:2407.00550v2。

### 发表信息

正式 venue、出版方 DOI、正式出版日期待核实。作者主页将其列为 CoRR/arXiv。CCF 第七版（2026）按正式 venue 分类；由于 venue 未确认，领域类别与 Full/Regular 资格待核实。最早公开日期为 2024 年 6 月 30 日（arXiv v1 首次提交）；正式出版日期待核实。[arXiv 版本记录](https://arxiv.org/abs/2407.00550)、[CCF 第七版说明](https://www.ccf.org.cn/Academic_Evaluation/By_category/)。

### 内容总结

作者研究训练集体通信是否必须逐包喷洒。Ethereal 在应用通信库向网卡发送前，按目的 ToR 汇集一批已知大小的流，先把完整流平均分到多条路径，再仅拆分无法整除的少量余数流。这样，每个 QP 仍按单路径传输，减少逐包换路带来的网卡状态和重排负担。论文在 Astra-Sim 中测试 Clos 拓扑、AllReduce 和 GPT-2 通信，报告在部分大消息与故障场景中优于喷洒、REPS 或 ECMP。结果建立在流大小与拓扑已知、集体通信较规则、应用层能拆分数据等条件下。

### 经验学习

可借鉴“先判断流量结构是否允许规划，再决定是否需要逐包控制”的分析思路，也可关注路径数与流数不能整除时的余数处理。理论等价结论针对最大拥塞和特定需求模型；作者的仿真结果不等于真实 NIC 部署效果。摘要与正文报告的若干最大改善幅度并不完全一致，应引用具体拓扑、通信模式和图表。

### 项目适用

本项目研究交换机侧类别感知的包／流混合选路，Ethereal 则在应用层为一批流分配路径。两种控制位置和机制不同。本项目在 ns-3 RDMA QP 中同时评估 MoE 合成通信批次完成时间与背景流 P99 FCT，并把乱序作为代价约束。Ethereal 的 Astra-Sim 大规模训练结果不能外推为本项目收益。

### 硬件依赖与边界

Ethereal 需要通信库拦截和拆分、拓扑与 GPU 放置知识、源路由路径 ID、QP 调度、PFC、Go-Back-N 和故障状态反馈。论文没有提供与固定 v2 一一对应的完整输入、源码、随机种子及原始结果包；本次未独立复现。

阅读日期：2026 年 10 月 31 日。参见[完整报告](papers/ethereal-2024/analysis.md)、[技术附件](papers/ethereal-2024/analysis-technical.md)、[证据表](papers/ethereal-2024/evidence.csv)、[逐页清单](papers/ethereal-2024/page-checklist.md)和[核验记录](papers/ethereal-2024/verification.md)。


## 43. RLB：预测 PFC 暂停后改道或在交换机内回环

论文题目：*Enhancing Load Balancing With In-Network Recirculation to Prevent Packet Reordering in Lossless Data Centers*；Jinbin Hu、Yi He、Wangqing Luo、Jiawei Huang 和 Jin Wang；固定阅读版本为 IEEE/ACM Transactions on Networking 2024 年期刊版，14 页。

### 发表信息

IEEE/ACM Transactions on Networking，2024 年，32 卷 5 期，4114–4127 页，DOI：10.1109/TNET.2024.3403671。IEEE Xplore 首次发表日期为 2024 年 5 月 27 日。该文前稿为 ACM ICPP 2023 论文，Crossref 在线出版日为 2023 年 9 月 13 日。CCF 第七版（2026）“计算机网络”A 类期刊；这是 venue 类别，不代表单篇论文质量。会议论文 Full/Regular 资格条件不适用于期刊论文。

### 内容总结

PFC 会在交换机队列达到阈值时暂停上游端口。较早的数据包若停在被暂停路径上，较晚的数据包可能先到达，接收端还可能因此请求重传。RLB 观察入口队列增长速度，预测 PFC 即将触发，再把预警逐跳送到上游交换机。上游比较最初选中的路径、次优路径和交换机内回环延迟：若换路代价较大，就让数据包短暂回环后重新判断；若次优路径延迟更小，就立即改道。交换机故障可能造成包反复回环，因此作者按剩余缓存和回环时延设上限，并用连续周期的回环次数异常识别问题端口。

作者在 Wedge 100BF-32X 可编程交换机上实现 P4 原型，也用小型测试床和 NS-3 仿真评估。在对称 leaf-spine 的 Web Search 测试中，作者报告 P99 FCT 相对 DRILL、Presto、LetFlow 和 Hermes 最多降低 72%、67%、58% 和 54%。这些数字对应指定拓扑、工作负载和基线。Incast 实验还表明，乱序比例下降不一定按相同比例转化为尾部 FCT 改善，回环自身会增加延迟。

### 经验学习

值得借鉴的是沿着“队列增长—PFC 暂停—上游反馈—路径选择—乱序恢复”建立因果链，并同时检查平均和尾部性能。回环与改道是按延迟代价做条件选择，不应简化成固定策略。论文使用硬件原型与仿真互补；资源表和线速能力只对作者的交换机实现提供证据。本文没有给出足以复现所有实验的完整固定代码、种子、原始数据和绘图工件。

### 项目适用

本项目在 ns-3 中研究类别感知的逐包／逐流混合选路，两类业务均为 RDMA QP。MoE 合成通信批次完成时间与背景流 P99 FCT 是双主指标，乱序代价待验证。RLB 的 PFC 预测、逐跳 CNM 和真实交换机回环与项目的类别感知选择不是同一机制。可迁移的是预警时效与乱序恢复的分析方法；两项项目指标及乱序代价均无本文之外的项目证据，仍待验证。

### 硬件依赖与边界

RLB 依赖 PFC、CNM 逐跳传递、可编程交换机状态存储和 packet recirculation。ns-3 可显式模拟所需时序，不能证明 Wedge/P4 的流水线资源、线速更新或大规模真实链路效果。真实硬件与大规模部署结论应单列。

阅读日期：2026 年 11 月 1 日。参见[完整报告](papers/rlb-2024/analysis.md)、[技术附件](papers/rlb-2024/analysis-technical.md)、[证据表](papers/rlb-2024/evidence.csv)、[逐页清单](papers/rlb-2024/page-checklist.md)和[核验记录](papers/rlb-2024/verification.md)。
