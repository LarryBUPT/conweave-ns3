# 参考文献论文候选

更新日期：2026 年 11 月 1 日。候选保留与毕业论文机制相关、值得进一步借鉴的论文，不等于最终引用清单或已复现成果。

阅读与筛选遵循 [每日流程](workflow.md)。[累计阅读文档](reading-log.md)持续追加通俗心得；[筛选记录](screening-log.md)保存排除原因和硬件依赖；[11 月 1 日日报](daily/2026-11-01.md)反馈最近一次完成的阅读。

本地及新增候选已完成 43 篇全文阅读，最近入库的是 RLB。今日实际查询和逐项理由见[11 月 1 日筛选](evidence/literature-screening-2026-11-01.md)。

## 1. 本轮候选

| 机制 | 论文与版本 | 阅读状态 | 本项目价值与限制 |
| --- | --- | --- | --- |
| PDLB | *PDLB: Path Diversity-aware Load Balancing with adaptive granularity in data center networks*；Springer *Journal of Cloud Computing* 2023，DOI:10.1186/s13677-023-00548-x；正式 PDF 16 页。最早核实公开：Research Square 2022-01-12；正式在线：2023-12-07。CCF 第七版（2026）未收录该期刊；期刊研究论文 | [通俗分析](papers/pdlb-2023/analysis.md) · [技术附件](papers/pdlb-2023/analysis-technical.md) · [证据](papers/pdlb-2023/evidence.csv) · [核验](papers/pdlb-2023/merge-verification.md) | 随路径时延差调整 flowcell 粒度，可借鉴粒度、利用率与乱序联合评估；NS2/TCP 收益不能外推到本项目 RDMA QP 双主指标，真实 TSO/NIC 开销未验证。 |
| APS | *APS: Adaptive Packet Spraying to Isolate Mix-flows in Data Center Network*；IEEE Transactions on Cloud Computing 2022，DOI:10.1109/TCC.2020.2985037；作者公开 14 页接收稿；最早可核验公开及首次出版记录为 2020-04-16，作者页面发布于 2020-04-18；CCF 第七版（2026）计算机体系结构／并行与分布计算／存储系统 C 类期刊，常规期刊论文 | [通俗分析](papers/aps-2020/analysis.md) · [技术附件](papers/aps-2020/analysis-technical.md) · [证据](papers/aps-2020/evidence.csv) · [核验](papers/aps-2020/merge-verification.md) | 短流活跃时按类别分配路径，空闲时借出容量；可在 ns-3 抽象，但 TCP、NS2 和 DPDK 效果不能外推为项目 RDMA QP 双主指标收益。 |
| LetFlow | *Let It Flow: Resilient Asymmetric Load Balancing with Flowlet Switching*；NSDI 2017，USENIX 官方 PDF 15 页；官方未列 DOI；最早可核验公开与出版方公开均为 2017-03-27（依据 CFP 首日公开政策，条目级上线时间戳待核实）；CCF 第七版（2026）计算机网络 A 类 venue，主会 refereed Full/Regular paper | [通俗分析](papers/letflow-2017/analysis.md) · [技术附件](papers/letflow-2017/analysis-technical.md) · [证据](papers/letflow-2017/evidence.csv) · [核验](papers/letflow-2017/merge-verification.md) | 按 flowlet 随机选路，利用拥塞导致的 flowlet 大小变化适应路径不对称；可在 ns-3 抽象，但论文 TCP／测试床结果未验证本项目 RDMA QP、MoE 批次与背景 P99 FCT。 |
| RPS | *On the Impact of Packet Spraying in Data Center Networks*；IEEE INFOCOM 2013，DOI:10.1109/INFCOM.2013.6567015；固定作者托管版 9 页，正式出版社 PDF 未逐字节比对；最早公开日及 IEEE 精确首次在线日待核实，Crossref 出版月份为 2013-04；CCF 第七版（2026）计算机网络 A 类 venue，主会正式长文，Full/Regular 资格据论文集和篇幅判断 | [通俗分析](papers/rps-2013/analysis.md) · [技术附件](papers/rps-2013/analysis-technical.md) · [证据](papers/rps-2013/evidence.csv) · [核验](papers/rps-2013/merge-verification.md) | 对称多路径下逐包喷洒的低乱序条件与故障后失效可供 ns-3 分析；作者使用 TCP／NetFPGA，未验证本项目 RDMA QP、MoE 批次或背景 P99 FCT。 |
| ExpressPass | *Credit-Scheduled Delay-Bounded Congestion Control for Datacenters*；ACM SIGCOMM 2017，DOI:10.1145/3098822.3098840；正式版 14 页，预印本 arXiv:1610.04688v1 为 8 页；最早公开 2016-10-15，正式出版 2017-08-07；CCF 第七版（2026）计算机网络 A 类 venue，主会正式长文，Full/Regular 资格据篇幅和正式论文集判断 | [通俗分析](papers/expresspass-2017/analysis.md) · [技术附件](papers/expresspass-2017/analysis-technical.md) · [证据](papers/expresspass-2017/evidence.csv) · [核验](papers/expresspass-2017/merge-verification.md) | 反向信用包预约数据发送，可借鉴反馈时延、控制开销和 P99 的联合评估；这是拥塞控制，不是类别选路，真实交换机与 SoftNIC 结果不能由 ns-3 验证。 |
| MSwift/MNSCC | *Congestion Control for Spraying with Congested Paths*；固定 arXiv:2509.07907v2，arXiv 预印本 DOI:10.48550/arXiv.2509.07907；最早公开 2025-09-09，v2 更新 2026-03-19；正式 venue、出版方 DOI 与出版日期待核实，CCF 第七版（2026）venue 类别和 Full/Regular 资格不适用 | 11 页全文已逐页核验；[通俗分析](papers/mswift-mnscc-2025/analysis.md) · [技术附件](papers/mswift-mnscc-2025/analysis-technical.md) · [证据](papers/mswift-mnscc-2025/evidence.csv) · [核验](papers/mswift-mnscc-2025/verification.md) | 逐包喷洒时的反馈中位数可作 ns-3 方法参考；作者在 htsim 的 CCT inflation 不等于项目 MoE 批次或背景 P99 收益，图 4 AR 组的图文差异须保留。 |
| IRN | *Revisiting Network Support for RDMA*；ACM SIGCOMM 2018，DOI:10.1145/3230543.3230557；arXiv v1 最早公开 2018-06-21，ACM 首次在线 2018-08-07；CCF 第七版（2026）计算机网络 A 类 venue，主会 Full/Regular | 正式 PDF 15 页（含封页）逐页核验；[通俗分析](papers/irn-2018/analysis.md) · [技术附件](papers/irn-2018/analysis-technical.md) · [证据](papers/irn-2018/evidence.csv) · [核验](papers/irn-2018/verification.md) | 选择性重传、有限窗口与乱序接收状态可作为 ns-3 传输代价参照；它不做类别感知选路，真实 NIC／FPGA 资源与论文收益不能外推到双主指标 |
| DCQCN | *Congestion Control for Large-Scale RDMA Deployments*；ACM SIGCOMM 2015；DOI:10.1145/2785956.2787484；最早可核验公开及出版方首次在线均为 2015-08-17；CCF 第七版（2026）计算机网络 A 类 venue，主会 Full/Regular | 本地 14 页 PDF 已逐页核验；[通俗分析](papers/dcqcn-2015/analysis.md) · [技术附件](papers/dcqcn-2015/analysis-technical.md) · [证据](papers/dcqcn-2015/evidence.csv) · [核验](papers/dcqcn-2015/verification.md) | ECN/CNP 逐流调速与 PFC 阈值关系可作 ns-3 反馈基线；真实 NIC、交换机及大规模部署结论不能外推到项目双主结果 |
| REPS | *REPS: Recycled Entropy Packet Spraying for Adaptive Load Balancing and Failure Mitigation*；arXiv:2407.21625v6；最早公开 2024-07-31；EuroSys 2026，DOI:10.1145/3767295.3769320；正式出版 2026-04-26；CCF 第七版（2026）计算机体系结构／并行与分布计算／存储系统 A 类；Full/Regular | 已完成 22 页全文和逐页核验；[通俗分析](papers/reps-2026/analysis.md) · [技术附件](papers/reps-2026/analysis-technical.md) · [证据](papers/reps-2026/evidence.csv) · [核验](papers/reps-2026/verification.md) | ACK/ECN 反馈、健康路径缓存与故障冻结可在 ns-3 抽象；自定义 FPGA RNIC、乱序传输和未测的 MoE 双指标须单列 |
| FlowDyn | *FlowDyn: Towards a Dynamic Flowlet Gap Detection using Programmable Data Planes*；arXiv:1910.03324v1，2019-10-08 最早公开；IEEE CloudNet 2019，DOI:10.1109/CloudNet47604.2019.9064146；Crossref 出版月份为 2019-11，IEEE 首次在线具体日待核实；CCF 第七版（2026）计算机网络领域未收录；Full/Regular 论文级标签待核实 | 已完成 7 页全文、11 幅图和 26 条证据核验；[通俗分析](papers/flowdyn-2019/analysis.md) · [技术附件](papers/flowdyn-2019/analysis-technical.md) · [证据](papers/flowdyn-2019/evidence.csv) · [核验](papers/flowdyn-2019/verification.md) | 动态 flowlet gap、反馈时效与保守回退可作 ns-3 方法参考；原论文只测 NS-2/TCP 平均 FCT，P4 硬件与本项目双指标须分开 |
| Flowcut | *Flowcut Switching: High-Performance Adaptive Routing with In-Order Delivery Guarantees*；固定阅读 arXiv:2506.21406v2，最早公开 2025-06-26；正式期刊 *IEEE Transactions on Networking* 34（2026），1974～1987，DOI:10.1109/TON.2025.3636209；首次在线日待核实；CCF 第七版（2026）计算机网络目录只列旧刊名 A 类，本篇新刊名类别待核实 | 已完成 16 页全文核验；[通俗分析](papers/flowcut-2026/analysis.md) · [技术附件](papers/flowcut-2026/analysis-technical.md) · [证据](papers/flowcut-2026/evidence.csv) · [核验](papers/flowcut-2026/verification.md) | 可借鉴在途数据排空后换路的保序条件；HPC 拓扑、交换机／NIC 依赖和本项目 MoE 双指标之间的差异须分开验证 |
| Hopper | PDF 首页题名 *Predictive Load Balancing for RDMA Traffic*；arXiv:2506.08132v1（摘要页题名不同）；2025 年 6 月 9 日首次公开；arXiv DOI:10.48550/arXiv.2506.08132；正式 venue／出版日期待核实，CCF 第七版类别不适用 | 已完成 11 页逐页审读；[通俗分析](papers/hopper-2025/analysis.md) · [技术附件](papers/hopper-2025/analysis-technical.md) · [证据](papers/hopper-2025/evidence.csv) · [引用](papers/hopper-2025/reference.bib) · [核验](papers/hopper-2025/verification.md) | 宿主侧 RTT 探测、双候选路径与换路等待可作 ns-3 方法参考；测试床训练时间数据自相矛盾，不能引用为确定收益；无 MoE 批次与背景 P99 双指标证据 |
| PSP | *PSP: Low-Overhead Packet-Level Load Balancing for Stale-State and Bandwidth-Asymmetric Networks*；arXiv:2608.08425v1，2026；发表 venue：IEEE LCN 2026；CCF 第七版（2026）计算机网络 C 类；最早公开：2026-08-09；IEEE Xplore 收录：2026-09-07 | 已完成 12 页全文、8 幅图和 5 张表核验；[通俗分析](papers/psp-2026/analysis.md) · [技术附件](papers/psp-2026/analysis-technical.md) · [证据](papers/psp-2026/evidence.csv) · [引用](papers/psp-2026/reference.bib) | 陈旧状态下的概率化逐包选路；自建周期精确模拟器，无 RDMA QP 实验；队列 P99 仅作乱序代理，硬件成本不可由 ns-3 验证 |
| DeFlow | Differential flowlet switching for load balancing in datacenter networks；Computer Networks，2025；DOI:10.1016/j.comnet.2024.110980 | 已完成 14 页全文及图表核验；[通俗分析](papers/deflow-2025/analysis.md) · [技术附件](papers/deflow-2025/analysis-technical.md) · [证据](papers/deflow-2025/evidence.csv) · [引用](papers/deflow-2025/reference.bib) | 差异化换路与大小流干扰；ns-3 机制可借鉴，Tofino 原型资源证据和 RDMA 适配需分开 |
| DiffFlow | Differentiating Short and Long Flows for Load Balancing in Data Center Networks；arXiv:1604.05107v1，2016 | 已完成 6 页全文及图表核验；[通俗分析](papers/diffflow-2016/analysis.md) · [技术附件](papers/diffflow-2016/analysis-technical.md) · [证据](papers/diffflow-2016/evidence.csv) · [引用](papers/diffflow-2016/reference.bib) | 类别决定选路粒度；简化传输和独立队列限制结论迁移 |
| SeqBalance | Congestion-Aware Load Balancing with no Reordering for RoCE；arXiv:2407.09808v1，2024 | 已完成 12 页及全部图表核验；[通俗分析](papers/seqbalance-2024/analysis.md) · [技术附件](papers/seqbalance-2024/analysis-technical.md) · [证据](papers/seqbalance-2024/evidence.csv) · [引用](papers/seqbalance-2024/reference.bib) | 子 QP 固定路径与反馈准入；跨 QP 语义、完成聚合和硬件成本单列 |
| WCMP | *WCMP: Weighted Cost Multipathing for Improved Fairness in Data Centers*；EuroSys 2014；DOI:10.1145/2592798.2592803 | 已完成 14 页正文、公式、算法、12 幅图、2 张表及逐页审读；[通俗分析](papers/wcmp-2014/analysis.md) · [技术附件](papers/wcmp-2014/analysis-technical.md) · [证据](papers/wcmp-2014/evidence.csv) · [引用](papers/wcmp-2014/reference.bib) | CCF 第七版（2026）体系结构/并行与分布计算/存储系统 A 类；最早可查公开及正式出版日 2014-04-14。仅作容量权重和公平性分析参考；硬件部署结论不能由 ns-3 验证 |
| SGLB | *SGLB: Scalable and Robust Global Load Balancing in Commodity AI Clusters*；SIGCOMM 2025；DOI:10.1145/3718958.3750527 | 已完成 20 页正文、附录、公式、算法、23 幅图及 2 张表核验；[通俗分析](papers/sglb-2025/analysis.md) · [技术附件](papers/sglb-2025/analysis-technical.md) · [证据](papers/sglb-2025/evidence.csv) · [引用](papers/sglb-2025/reference.bib) | CCF 第七版（2026）计算机网络 A 类 Full paper；最早可查公开及正式出版日 2025-08-27。仅作全局反馈和状态压缩方法参考；ASIC/EDK 机制与作者收益不能由 ns-3 验证 |
| MicroTE | *MicroTE: Fine Grained Traffic Engineering for Data Centers*；ACM CoNEXT 2011；DOI:10.1145/2079296.2079304 | 已完成 12 页全文、公式、算法、图 1～7、架构图和表 1 审读；[通俗分析](papers/microte-2011/analysis.md) · [技术附件](papers/microte-2011/analysis-technical.md) · [证据](papers/microte-2011/evidence.csv) · [引用](papers/microte-2011/reference.bib) | CCF 第七版（2026）计算机网络 B 类；Full/Regular 资格待核实。最早可查公开及正式出版日 2011-12-06。仅作流量稳定性与全局分配方法参考，控制器和交换机实测不能由 ns-3 验证 |
| TeXCP | *Walking the Tightrope: Responsive Yet Stable Traffic Engineering*；ACM SIGCOMM 2005；DOI:10.1145/1080091.1080122 | 已完成 12 页全文、14 幅图、5 张表及附录核验；[通俗分析](papers/texcp-2005/analysis.md) · [技术附件](papers/texcp-2005/analysis-technical.md) · [证据](papers/texcp-2005/evidence.csv) · [引用](papers/texcp-2005/reference.bib) | CCF 第七版（2026）计算机网络 A 类；Full/Regular 资格待核实；正式出版 2005-08-22，绝对最早公开日待核实。仅作双时间尺度反馈与过渡分析的方法参考，ISP/MPLS 部署及 FCT 收益不可外推 |
| DRB-TTC | *Randomized Load-balanced Routing for Fat-tree Networks*；arXiv:1708.09135v1（2017）；arXiv DOI:10.48550/arXiv.1708.09135；正式 venue 待核实 | 已完成 13 页全文及逐页核验；[通俗分析](papers/drb-ttc-2017/analysis.md) · [技术附件](papers/drb-ttc-2017/analysis-technical.md) · [证据](papers/drb-ttc-2017/evidence.csv) · [引用](papers/drb-ttc-2017/reference.bib) | arXiv/CoRR 预印本，未核实正式 venue；CCF 与 Full/Regular 不适用。最早公开 2017-08-30，正式出版日期待核实。D-mod-k+TTC 适合作为 Fat-tree 路径碰撞和阈值改道的方法参考；未评测 RDMA/MoE 双指标。
| RDMACell | *RDMACell: Token-Based Flowcell-Level RDMA Load Balancing for Large-Scale AI Training*；arXiv:2606.20581v1（2026）；arXiv DOI:10.48550/arXiv.2606.20581；正式 venue 待核实 | 已完成 7 页全文及逐页核验；[通俗分析](papers/rdmacell-2026/analysis.md) · [技术附件](papers/rdmacell-2026/analysis-technical.md) · [证据](papers/rdmacell-2026/evidence.csv) · [引用](papers/rdmacell-2026/reference.bib) | arXiv 预印本，未核实正式 venue；CCF 与 Full/Regular 不适用。最早公开 2026-05-07（编号月份与提交日存在张力）；正式出版日期待核实。宿主侧 flowcell 粒度与令牌反馈可在 ns-3 抽象；作者在存储 trace 上的 P99 收益不能外推为 MoE 批次或背景 P99 收益 |
| Fastpass | *Fastpass: A Centralized “Zero-Queue” Datacenter Network*；ACM SIGCOMM 2014；DOI:10.1145/2619239.2626309 | 已完成 12 页全文、图 1～16、附录公式及 17 项证据核验；[通俗分析](papers/fastpass-2014/analysis.md) · [技术附件](papers/fastpass-2014/analysis-technical.md) · [证据](papers/fastpass-2014/evidence.csv) · [引用](papers/fastpass-2014/reference.bib) | CCF 第七版（2026）计算机网络 A 类；主会长文，Full/Regular 资格待核实；最早公开介绍 2014-07-17，全文首发日待核实；正式出版 2014-08-17。仅借鉴集中协调与约束分解方法，硬件收益不能由 ns-3 验证 |
| ECMP | *Analysis of an Equal-Cost Multi-Path Algorithm*；RFC 2992，2000；DOI:10.17487/RFC2992 | 已完成 8 页全文、公式与图 1～2 核验；[通俗分析](papers/ecmp-rfc2992/analysis.md) · [技术附件](papers/ecmp-rfc2992/analysis-technical.md) · [证据](papers/ecmp-rfc2992/evidence.csv) · [引用](papers/ecmp-rfc2992/reference.bib) | Informational RFC，无会议/期刊 venue；CCF 与 Full/Regular 类别不适用。最早公开草案登记于 1999-01-06；RFC Editor 正式发布于 2000-11。仅作映射稳定性方法参考 |

独立对话 ID 和固定版本见 [阅读任务登记](reading-jobs.json)。已完成论文均经全文阅读，文件哈希已核验，心得按累计方式追加；Hopper 对话已归档并保留全部文档和 PDF。RDMACell 独立对话曾因平台鉴权错误未运行，全文产物由总控完成，原对话留作失败断点。SeqBalance 的 2025 年正式期刊记录已核验，但正文未比对，本轮分析仍限定 v1。未复现作者实验，也未验证本项目性能收益。

## 2. 已有阅读与后续初筛队列

Ofan（arXiv:2507.21372v2）已迁移并完成七项归档，23 页覆盖。最早公开为 2025-07-28；正式会议／期刊及出版日期待核实，预印本不赋予 CCF venue 类别。见 [通俗分析](papers/ofan-2025/analysis.md)、[技术附件](papers/ofan-2025/analysis-technical.md)、[核验记录](papers/ofan-2025/verification.md)和 [引用](papers/ofan-2025/reference.bib)。摘要已去重加入累计文档，对话已归档，全部材料保留。后稿 2610.07230v1 单列，未并入本篇效果。

Themis 和 Spritz 等仍在进一步核验队列；Ethereal 已读并入库。MSwift/MNSCC、REPS 与 FlowDyn 已读并入库。APSCC 因公开全文尚未取得而列为待获取。优先级以机制适配性和证据条件决定，不按新旧、引用量或会议等级设门槛。







## 已读论文发表信息补核

CCF 采用第七版（2026）官方目录，专业领域为计算机网络。

| 机制 | 正式会议／期刊 | CCF 类别及资格 | 最早公开 | 正式出版 |
| --- | --- | --- | --- |
| DiffFlow | 2016 IEEE Global Communications Conference（GLOBECOM） | 计算机网络 C 类会议；本篇 Full／Regular paper 资格待核实 | 2016-04-18（arXiv v1 首次提交） | 2016-12（Crossref 出版年月）；首次在线／收录日待核实 |
| DeFlow | Computer Networks 257（2025），110980 | 计算机网络 B 类期刊；正式研究论文 | 2024（SSRN 预印本公开年份；具体月日待核实） | 2024-12-09（正式稿首页 Available online）；卷期为 2025-02 |
| SeqBalance | IEEE Internet of Things Journal 12（13），2025，25707～25719 | 计算机网络 C 类期刊；正式期刊记录，最终正文未比对 | 2024-07-13（arXiv v1 首次提交） | 2025-07-01（正式卷期出版）；首次在线日待核实 |
| WCMP | ACM EuroSys 2014 正式会议长文 | CCF 第七版（2026）计算机体系结构/并行与分布计算/存储系统 A 类会议 | 2014-04-14（Crossref 最早可查在线记录；更早预印本未检出） | 2014-04-14（Crossref 在线及印刷出版字段） |
| TeXCP | ACM SIGCOMM 2005 主会正式论文；明确 Full/Regular 资格待核实 | CCF 第七版（2026）计算机网络 A 类会议 | 绝对最早公开日待核实；最早核实在线出版记录 2005-08-22 | 2005-08-22（Crossref 在线及印刷字段） |
| ECMP | RFC 2992 Informational RFC；非会议或期刊论文 | 不适用：RFC 不属于 CCF 会议／期刊目录 | 1999-01-06（Datatracker 登记 Internet-Draft 00） | 2000-11（RFC Editor 发布月份） |


## 串行本地阅读队列

本地 30 个平铺 PDF 已初筛。任务登记记录 26 篇完整阅读已入库；优先复用既有对话并严格串行。详见 [逐项筛选](daily/local-batch-2026-10-12.md)、[任务登记](reading-jobs.json)和 [累计阅读文档](reading-log.md)。聚合引用见 [references.bib](references.bib)。


CONGA 已完成 12 页、图 1～17 全文核验。ACM SIGCOMM 2014，CCF 第七版（2026）计算机网络 A 类，主会 Full／Regular paper；出版记录为 2014-08-17，最早网上公开日仍待核实。见 [通俗报告](papers/conga-2014/analysis.md)、[技术附件](papers/conga-2014/analysis-technical.md)、[核验记录](papers/conga-2014/verification.md)。已去重入库并归档对话，全部论文材料保留。

ConWeave 已完成 16 页、图 1～25、5 张表核验。ACM SIGCOMM 2023，CCF 第七版（2026）计算机网络 A 类；Full／Regular 资格及最早公开日待核实。正式在线元数据为 2023-09，纸本记录为 2023-09-10。见 [完整通俗报告](papers/conweave-2023/analysis.md)、[技术附件](papers/conweave-2023/analysis-technical.md)、[核验记录](papers/conweave-2023/verification.md)。已去重入库并归档对话，所有材料保留。



HULA 已完成 12 页、9 幅图和表 1 全文核验。ACM SOSR 2016；CCF 第七版（2026）类别与 Full／Regular 资格待核实。最早核实的出版方在线日期为 2016-03-14，未查见更早公开记录。见 [完整通俗报告](papers/hula-2016/analysis.md)、[技术附件](papers/hula-2016/analysis-technical.md)和 [核验记录](papers/hula-2016/verification.md)。已入库并归档对话，保留全部材料。探测周期与故障时间单位的疑点已单列。



Proteus 已完成 11 页、12 幅图、3 张表和 2 段算法核验。IEEE ICNP 2023；CCF 第七版（2026）计算机网络 B 类，Full／Regular 资格待核实。作者机构页记录 2023-10-15；Crossref `issued` 为 2023-10-10，与会议首日相同，故日期语义差异保留，未宣称公开日期穷尽。见 [完整通俗报告](papers/proteus-2023/analysis.md)、[技术附件](papers/proteus-2023/analysis-technical.md)和 [核验记录](papers/proteus-2023/verification.md)。已入库并归档对话，PDF 和逐页材料保留。算法 1 符号已纠正为与保序说明一致；算法 2 条件疑点单列。



Gemma 已完成 6 页、10 幅图和 4 张表全文核验。IEEE HPCC 2024；CCF 第七版（2026）计算机体系结构／并行与分布计算／存储系统 C 类，Full／Regular 资格待核实。最早公开和正式出版日期待核实；Crossref 日期与会议首日重合。见 [完整通俗报告](papers/gemma/analysis.md)、[技术附件](papers/gemma/analysis-technical.md)和 [核验记录](papers/gemma/verification.md)。已入库并归档对话，保留全部文档及 PDF。




AG 已完成 11 页全文、图 1～15、公式（1）～（7）和算法核验。IEEE ICNP 2019；CCF 第七版（2026）计算机网络 B 类，Long paper，收入 FullPapers。作者机构页最早可核验公开记录为 2019-09-04；Crossref 正式出版日期核实到 2019 年 10 月，具体日待核实。见 [完整通俗报告](papers/ag/analysis.md)、[技术附件](papers/ag/analysis-technical.md)和 [核验记录](papers/ag/verification.md)。已入库并归档对话，保留 PDF 与完整材料。




IntFlow 已完成 12 页、图 1～8、表 I～III、算法 1～2 和公式（1）核验。IEEE Transactions on Network and Service Management，CCF 第七版（2026）计算机网络 C 类期刊。最早公开和正式首次出版日期为 2020-04-28，卷期为 2020 年 9 月。见 [完整通俗报告](papers/intflow-2020/analysis.md)、[技术附件](papers/intflow-2020/analysis-technical.md)和 [核验记录](papers/intflow-2020/verification.md)。已入库并归档对话，保留 PDF 和全部文档。正文与图 2a 对 data-mining、80% 负载结果的矛盾已单列。




CAPS 已完成 9 页全文核验。IEEE INFOCOM 2018，CCF 第七版（2026）计算机网络 A 类；论文以正式论文集长文记录，出版社未提供明确 Full paper 字段。作者机构记录日期为 2018-10-08，绝对最早公开日期待核实。见 [完整通俗报告](papers/caps-2018/analysis.md)、[技术附件](papers/caps-2018/analysis-technical.md)和 [核验记录](papers/caps-2018/verification.md)。已入库并归档对话，保留 PDF 和完整材料。式（10）、图 12(a) 与正文的开销趋势矛盾已记录。




FlowBender 已完成本地 11 页 PDF 全文核验。ACM CoNEXT 2014，CCF 第七版（2026）计算机网络 B 类，Full paper；最早可核实公开及正式出版日期为 2014-12-02。ACM/索引页码比固定本地 PDF 多 1 页，核验记录保留此差异。见 [完整通俗报告](papers/flowbender-2014/analysis.md)、[技术附件](papers/flowbender-2014/analysis-technical.md)和 [核验记录](papers/flowbender-2014/verification.md)。已入库并归档对话，保留全部材料。




DeTail 已完成 12 页全文核验。ACM SIGCOMM 2012，CCF 第七版（2026）计算机网络 A 类，主会 Full paper。同题 Berkeley 技术报告最早公开记录为 2011-10-19（四位作者）；会议版于 2012-08-13 正式出版（五位作者）。见 [完整通俗报告](papers/detail-2012/analysis.md)、[技术附件](papers/detail-2012/analysis-technical.md)和 [核验记录](papers/detail-2012/verification.md)。已入库并归档对话，保留 PDF 和完整材料。




Presto 已完成 14 页全文审计。ACM SIGCOMM 2015，CCF 第七版（2026）计算机网络 A 类，主会 Full paper；最早已核验公开和正式出版记录均为 2015-08-17。PDF 的 CCR 元数据与会议 DOI 条目差异保留在核验记录。见 [完整通俗报告](papers/presto-2015/analysis.md)、[技术附件](papers/presto-2015/analysis-technical.md)和 [核验记录](papers/presto-2015/verification.md)。已入库并归档对话，保留全部材料。







## 串行归档当前进度

截至 2026 年 10 月 16 日已入库 28 篇，最新为 FlowDyn。RDMACell 的独立阅读对话曾因平台鉴权故障未能运行，该异常保留在[当时进度](daily/2026-10-13.md)，不影响其已核验文档的存档状态。

Dart 已完成 14 页期刊版全文、图 1～15、表 1～2 及 29 条证据核验，作为第 32 篇入库。IEEE/ACM Transactions on Networking 2020，DOI `10.1109/TNET.2019.2961671`；CCF 第七版（2026）计算机网络 A 类期刊。arXiv v1 最早公开于 2018 年 5 月 28 日，IEEE 首次在线具体日期待核实。可借鉴拥塞位置分类、接收端直接分摊与保序路径回退；真实设备仅测 DASR 原型，完整 Dart 和 IOFD 属 ns-3 模拟。见[累计条目](reading-log.md)、[通俗报告](papers/dart-2020/analysis.md)、[技术附件](papers/dart-2020/analysis-technical.md)和[总控核验](papers/dart-2020/merge-verification.md)。



## DRILL（2026 年 10 月 28 日入库）

*DRILL: Micro Load Balancing for Low-latency Data Center Networks* 发表于 ACM SIGCOMM 2017，DOI `10.1145/3098822.3098839`，主会技术论文长文。CCF 第七版（2026）将 SIGCOMM 列为计算机网络 A 类 venue。Crossref 登记出版日期为 2017 年 8 月 7 日；固定作者版本的最早公开日期待核实。已逐页核验 14 页，作为累计第 39 篇。见[通俗分析](papers/drill-2017/analysis.md)、[技术附件](papers/drill-2017/analysis-technical.md)、[证据表](papers/drill-2017/evidence.csv)、[逐页清单](papers/drill-2017/page-checklist.md)和[总控核验](papers/drill-2017/merge-verification.md)。其局部队列采样与非对称路径分组可供 ns-3 方法分析；TCP 与交换机硬件结果不能直接代表项目 RDMA QP 双主指标。

## MP-RDMA（2026 年 10 月 29 日入库）

*Multi-Path Transport for RDMA in Datacenters* 发表于 USENIX NSDI 2018，正式论文集页码 357～371；会议版 DOI 未见于 USENIX 记录。CCF 第七版（2026）将 NSDI 列为计算机网络 A 类 venue；本篇属于主会 Full paper。最早公开精确日期和出版方精确上线日待核实，USENIX 书目仅给出 2018 年 4 月。固定官方 PDF 为 16 页，已逐页核验并作为累计第 40 篇。见[通俗报告](papers/mp-rdma-2018/analysis.md)、[技术附件](papers/mp-rdma-2018/analysis-technical.md)、[证据表](papers/mp-rdma-2018/evidence.csv)、[逐页清单](papers/mp-rdma-2018/page-checklist.md)和[总控核验](papers/mp-rdma-2018/merge-verification.md)。可借鉴 ACK 路径反馈与乱序门限的联合设计；FPGA/RNIC 资源和部署结论不能由本项目 ns-3 直接验证。

## Maestro（2026 年 10 月 30 日入库）

*Accelerating Distributed Deep Learning using Multi-Path RDMA in Data Center Networks* 发表于 ACM SIGCOMM SOSR 2021，DOI `10.1145/3482898.3483363`。CCF 第七版 SOSR 类别及本篇 Full/Regular 资格待核实。最早公开日期待核实；Crossref 在线出版字段为 2021-11-08，另有 2021-10-11 出版字段差异。固定 13 页会议 PDF 已逐页核验，作为累计第 41 篇。见[通俗报告](papers/maestro-2021/analysis.md)、[技术附件](papers/maestro-2021/analysis-technical.md)、[证据表](papers/maestro-2021/evidence.csv)、[逐页清单](papers/maestro-2021/page-checklist.md)和[总控核验](papers/maestro-2021/merge-verification.md)。端侧多 QP 分块可供方法比较；真实 RNIC、交换机与软件栈性能不能由本项目 ns-3 验证。

## Ethereal（2026 年 10 月 31 日入库）

*Ethereal: Divide and Conquer Network Load Balancing in Large-Scale Distributed Training*，固定 arXiv:2407.00550v2 的 15 页 PDF，v1 最早公开 2024-06-30。正式 venue、出版方 DOI、正式出版日期和 CCF 第七版类别待核实。已逐页核验并作为累计第 42 篇入库。见[通俗报告](papers/ethereal-2024/analysis.md)、[技术附件](papers/ethereal-2024/analysis-technical.md)、[证据表](papers/ethereal-2024/evidence.csv)、[逐页清单](papers/ethereal-2024/page-checklist.md)和[总控核验](papers/ethereal-2024/merge-verification.md)。它的应用层流拆分、余数流处理可为 ns-3 对比设计提供思路；Astra-Sim 与大规模训练效果不能直接代表本项目双主指标。

## 用户指定优先待读（2026 年 10 月 31 日）

RLB 与用户列出的《Enhancing Load Balancing With In-Network Recirculation to Prevent Packet Reordering in Lossless Data Centers》是同一篇，按 DOI 去重后共 **4 篇**：[RLB](papers/rlb-2024/paper-author.pdf)、FLB 的 2026 年 ToN 期刊版、[Proteus 的 2024 年 ToN 期刊版](papers/proteus-ton-2024/paper-author.pdf)、RoSR。前两篇正式期刊和 Proteus 期刊版均对应 CCF 第七版计算机网络 A 类 TON 条目；RoSR 所在 *IEEE Computer Architecture Letters* 未见目录收录。RLB 已完成精读和归档；FLB 目前只取得[2025 年 USENIX ATC 相关版本](papers/flb-ton-2026/related-atc25.pdf)，RoSR 尚缺全文。四篇的正式发表、最早可核实日期、硬件边界、固定 PDF 哈希和来源见[队列核验记录](evidence/user-priority-2026-10-31/README.md)；状态与顺序见[阅读任务登记](reading-jobs.json)。候选身份不等于最终引用。

## RLB（2026 年 11 月 1 日入库）

*Enhancing Load Balancing With In-Network Recirculation to Prevent Packet Reordering in Lossless Data Centers*，IEEE/ACM Transactions on Networking 32(5):4114–4127（2024），DOI `10.1109/TNET.2024.3403671`。CCF 第七版计算机网络 A 类期刊。IEEE Xplore 首次发表 2024-05-27；ACM ICPP 2023 前稿的 Crossref 在线记录为 2023-09-13。固定作者托管 14 页 PDF 已逐页核验并作为累计第 43 篇。见[通俗报告](papers/rlb-2024/analysis.md)、[技术附件](papers/rlb-2024/analysis-technical.md)、[证据表](papers/rlb-2024/evidence.csv)、[逐页清单](papers/rlb-2024/page-checklist.md)和[总控核验](papers/rlb-2024/merge-verification.md)。PFC 预警与乱序恢复方法可借鉴；真实 P4 交换机回环和测试床效果不作为本项目收益。
