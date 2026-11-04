# Flowcut 版本与证据核验

核验日期：2026 年 10 月 15 日。本文只修改本论文目录。

## 固定 PDF 与阅读范围

- 固定对象：`paper-arxiv-2506.21406v2.pdf`。
- 文件哈希：SHA-256 `1ba1e8cbad41973d3b42112a1a33876629541da814ac56bd06132439704fd1a1`，与任务指定值一致。
- PDF 信息：16 页，US Letter 页面尺寸，无加密。首页水印标注 arXiv:2506.21406v2，版本日期 2025 年 11 月 19 日。
- 阅读覆盖：逐页检查正文、算法描述、公式、图 1～15、表 I～IV、讨论、结论和参考文献。第 14～16 页为参考文献，PDF 无附录。
- 图页检查：16 页均生成缩略图逐页查看；图表标签、坐标与正文可辨认，未发现页面缺页、裁切或图文错位。详细页码范围见 `page-audit.csv`。
- 未运行论文仿真，也未复现作者性能结果。

## 预印本与正式出版记录

arXiv 版本历史显示，v1 于 2025 年 6 月 26 日（UTC）首次提交，v2 于 2025 年 11 月 19 日（UTC）提交。固定 PDF 与 arXiv 的 v2 记录相符。[arXiv v1 记录](https://arxiv.org/abs/2506.21406v1)、[arXiv v2 记录](https://arxiv.org/abs/2506.21406v2)。

Crossref DOI 记录确认正式论文元数据为 *IEEE Transactions on Networking*，2026 年，第 34 卷，1974–1987 页，DOI 10.1109/TON.2025.3636209，类型为 `journal-article`。DOI 解析指向 [IEEE Xplore 记录 11299491](https://ieeexplore.ieee.org/document/11299491/)。Crossref 给出 2026 年发表年，`published-online` 字段为空，`published-print` 仅到年份。其 `created` 时间为 2025 年 12 月 12 日 18:35:05 UTC，表示 DOI 登记记录创建时间，不是可核实的出版社首次在线日。

**出版社首次在线日期仍待核实。** IEEE Xplore 页面在本次访问中未提供可读取的具体日期字段。若后续取得 IEEE Xplore 元数据 API 或出版页面显示的 Date of Publication，应补录该日期；当前不能把 Crossref 创建日期、arXiv v2 日期、期刊年份或作者网站列表日期替代为正式首次在线日。

## 刊名与 CCF 核对

CCF 官方说明显示第七版目录于 2026 年 3 月更新；官方“计算机网络”目录页明确将旧刊名 *IEEE/ACM Transactions on Networking* 列为 A 类。IEEE 官方 2025 年 Title List 将旧刊名标注为现刊 *IEEE Transactions on Networking* 的 former title，证明两刊名存在承继关系。但 CCF 目录没有以新刊名单独列项，因此本篇新刊名能否直接适用旧名的 A 类级别，**待核实**。当前记录保留旧名条目的 A 类信息，不将类别直接赋给本篇 venue。[CCF 第七版发布页](https://www.ccf.org.cn/Academic_Evaluation/By_category/2026-03-05/861526.shtml)、[CCF 计算机网络目录](https://www.ccf.org.cn/Academic_Evaluation/CN/)、[IEEE 2025 年 Title List](https://open.ieee.org/wp-content/uploads/IEEE-Title-List-August-2025.pdf)。

论文已作为期刊文章正式发表，因此 CCF 对会议论文 Full paper／Regular paper 的形式资格条件不适用。目录项本身使用旧刊名，正式论文则使用新刊名；IEEE 官方清单核实了名称承继，但 CCF 是否将旧名类别延续至新刊名仍待确认。

## v2 与正式期刊稿的差异状态

本任务指定阅读对象是 arXiv v2。正式 DOI、卷期和页码已交叉核对，但**没有对正式期刊稿做逐页内容比较**。因此不能断言期刊版本与 v2 在措辞、图表、参数、引用或实验上完全一致。引用机制细节时，应注明依据为 arXiv v2；引用出版信息时，可按 Crossref/IEEE 当前记录填写。

## 关键证据边界

1. Flowcut 保序机制依赖每流在途状态和 ACK 清账；启动时第一批 BDP 数据须走同一路径。丢包或确认状态未收敛可能阻塞排空，论文以源端超时兜底。引用“任何网络条件下保序”需一并说明其协议过程和恢复边界。
2. 论文仿真采用 SST、RDMA-like 协议、lossless credit-based flow control，主配置为 1024 节点与 200 Gbit/s 链路；此处没有 ns-3 实验。
3. 真实集群结果基于 2048 端点 Slingshot Dragonfly 的有序与无序模式比较。约 24% 完成时间差不是通用乱序处理代价，也不是与其他路由算法的公开对照。
4. 表 IV 给出排空时间占总运行时间的全网平均比例，范围约 5.2%～11.3%；没有每流尾部排空时间分布。
5. 正文对若干图未见统一的种子数、误差条或显著性检验。相近柱形不能被解释为统计等价。
6. 论文没有评测 MoE 合成通信批次与背景流混合场景，也未测量这两项项目主指标能否同时改善。论文结果不构成本项目收益证据。

## 复现材料状态

本次没有核实到与该固定版本一一对应的完整实验包，包括模拟器提交、全部配置、流量输入、随机种子、运行脚本和逐图原始结果。故状态记为“完整复现材料未确认”，不是断言作者没有公开材料。论文的方法与主要实验条件足以理解设计，但不足以仅凭 PDF 独立重建全部曲线。真实 Slingshot 结果还依赖作者所在团队的硬件实现与集群访问。

## 交付文件核对

本目录包含 `analysis.md`、`analysis-technical.md`、`evidence.csv`、`reference.bib`、`manifest.json`、`verification.md`、`reading-entry.md` 和 `page-audit.csv`。日期未核实项、固定 PDF 哈希、DOI、CCF 目录版次与类别来源均已记入对应文件。共享 `reading-log.md`、候选 README、筛选记录和日报不在本次编辑范围内。
