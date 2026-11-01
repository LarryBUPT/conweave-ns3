# WS-31 提案、实现与验证

日期：2026 年 11 月 1 日。当前入口为[顺序实现计划](implementation-plan-r1.md)和[状态](current-status.json)。用户已授权按 C1 → C2 → C3 判断并实现，旧提案中的“等待选题／只提案”限制已解除；最终采用的机制仍须依据验证结果由用户决定。

## 1. 核心发现

旧类别权重能改变部分选择，但已有数据未识别稳定时间增量。QueuePin 提供类别无关的对照。当前标签又与大小绑定，不能把类别策略作用直接称作业务语义独有价值。

三候选为后续突发记账、有界启动分散、新 QP 类别配额与空闲借用。首版、核心、完整构建、零控制、实际主模式、匹配消融、未知与静态标签干预均已有技术主验。[第十节点](label-default-node10-handoff.md)完成标签夹具默认关闭三格回归；[第十一节点](label-dynamic-node11-handoff.md)完成延迟可得、后续改变和固定部分错误的十格验证，现累计 41 格技术网络验收。旧检查器过度比较 C3 通用 CHOICE 的停止记录保留，恢复只运行原先已构建但未启动的两格，未重复原八格。

[第十二节点](adapter-boundary-node12-handoff.md)已完成固定 1f 源的一次完整构建和 C1 五例／C2 十例／C3 两例适配器主验，完整原日志与来源链通过。原预检资源门停止及原文件保留，恢复没有重复同步、部署或旧测试。17 例属于非网络夹具，累计技术网络验收仍为 41 格。

[第十三节点](adapter-default-node13-handoff.md)已完成新源 Q12／C2 默认两格。208 条请求全部完成，共 403,963,904 B；完整 FCT 和仅去 uid 的有序选路事件恢复各自参考，C2 精确等待及原需求计时亦通过主验。累计技术网络验收为 43 格，17 例非网络适配器条件另计。

真实端点退出／排空／跨代复用、独立 C1 V0 和三候选双侧效果及成本仍待完成。[第十四节点](endpoint-ledger-node14-handoff.md)完成端点账本静态审查与修订，核心和测试已固定为 20bc；尚未连接 NS-3。[第十五节点](endpoint-core-node15-handoff.md)已完成独立核心单次编译／运行主验；[第十六节点](endpoint-probe-node16-handoff.md)已接收实际对象快照静态审查，修复覆盖守卫并固定为 8cd；[第十七节点](endpoint-object-node17-handoff.md)已完成一次实际对象预检的 raw、固定来源和完整交付主验：八组双读、十六项拒绝通过，mask 保持 127，网络与自然完成均为 0。真实 switch／channel／完成回调接线仍待实现。用户要求暂缓 Ofan，并限定新增基线来自已核实的 CCF A/B 类会议或期刊文章；Ofan/RR 代码保留为未准入原型。

[第十八节点](endpoint-channel-node18-handoff.md)完成 channel 首版静态审查主验，四项 P1 与一项 P2 已形成 r2 源码修订；[新契约](endpoint-channel-contract-r2.md)和[五文件只读复核](endpoint-channel-local-review-r2.json)进行中，尚无编译或运行验收。身份编码的真实 G1／生产者约束和实际网络接线仍未完成。

## 2. 文件导航

| 用途 | 入口 |
| --- | --- |
| 全阶段状态与验收 | [状态 JSON](current-status.json)、[阶段计划](stage-plan.md) |
| 历史失败与消融 | [失败经验](failure-lessons.md)、[独立失败审计](../independent/failure-evidence-audit-r1.md) |
| 五模块论文拆解 | [文献证据](literature-evidence.md)、[DiffFlow 卡片](papers/diffflow/paper-card.md)、[其他主集合逐图表](papers/figure-map.csv) |
| 共识、分歧与问题 | [争议地图](controversy-map.md)、[研究问题](research-questions.md) |
| 候选与评审 | [三候选](candidates.md)、[三份主对话模拟审稿](review-and-feasibility.md)、[C1 独立近邻报告](../independent/c1-neighbor-review-r1.md) |
| 选题漏斗和雷达 | [漏斗 CSV](topic-funnel.csv)、[选题地图](topic-map.md)、[增量文献雷达](literature-radar.md) |
| 具体设计边界 | [C1 信息与状态契约](c1-information-contract.md)、[独立意见处理](c1-review-resolution-r1.md) |
| 实现及验证计划 | [顺序计划](implementation-plan-r1.md)、[C2 契约](c2-implementation-contract-r1.md)、[C3 契约](c3-implementation-contract-r1.md)、[正确性协议](correctness-protocol-r1.md) |
| C2 标签接口修订 | [第五节点主验](c2-label-node5-handoff.md)、[聚合主收据](evidence/c2-label-pilot-main-acceptance-r1.json)、[源码修订记录](c2-policy-tag-fix-r1.md) |
| 新增对照与构建 | [现行 CCF A/B 准入规则](baseline-admission-policy-r2.md)、[此前独立准入评估](../independent/baseline-admission-r1.md)、[构建主核收据](evidence/c123-build-main-acceptance-r1.json) |
| 最新技术节点与下一门 | [对象预检第十七节点](endpoint-object-node17-handoff.md)、[完整主验收](evidence/endpoint-object-delivery-main-acceptance-r1.json)、[逐行 raw 主收据](evidence/endpoint-object-raw-main-acceptance-r1.json)、[默认回归第十三节点](adapter-default-node13-handoff.md)、[两格聚合主收据](evidence/adapter-default-pilot-main-acceptance-r1.json)、[快照审查第十六节点](endpoint-probe-node16-handoff.md)、[实际对象预检](endpoint-probe-object-preflight-r1.json)、[核心预检第十五节点](endpoint-core-node15-handoff.md)、[核心主验收](evidence/endpoint-ledger-core-preflight-main-acceptance-r2.json)、[真实对象首版审查](endpoint-probe-local-review-r1.json)、[端点第十四节点](endpoint-ledger-node14-handoff.md)、[端点新契约](endpoint-lifecycle-design-r2.md)、[核心预检计划](endpoint-ledger-core-preflight-r2.json)；历史节点：[适配器第十二节点](adapter-boundary-node12-handoff.md)、[适配器完整主收据](evidence/adapter-boundary-preflight-main-acceptance-r2.json)、[动态标签第十一节点](label-dynamic-node11-handoff.md)、[十格聚合主收据](evidence/label-dynamic-pilot-main-acceptance-r3.json)、[适配器契约](adapter-lifecycle-contract-r1.md)、[C1 控制第六节点](c1-controls-node6-handoff.md)、[C2／C3 第七节点](c23-controls-node7-handoff.md)、[C1／C3 标签四格计划](c13-label-validation-r1.json)、[C2 标签第五节点](c2-label-node5-handoff.md)、[三主模式动态交接](dynamic-node4-handoff.md)、[单输入 V0 技术重放](v0-technical-replay-r1.md) |
| 历史首轮提案 | [提案](proposal.md)、[第一节点交接](node1-handoff.md)；保留原阶段判断，不作为当前实现限制 |

## 3. 证据等级与术语

QP 为队列对，ToR 为机架顶交换机，RDMA 为远程直接内存访问。FCT 是流完成时间；P99 是相应样本第 99 百分位。批次完成时间使用全部目标流的最晚完成，不能与单流均值或 P99 互换。预测预算不是物理队列，也不是已验证的网络预留。

已检索、已读全文、已有项目证据和待实验验证分别标注。主集合复用固定全文阅读，近邻只读章节的范围明确保留。原始实验、技术夹具、描述性重放与候选效果不混用。当前累计 43 格技术网络验收，另有 17 例非网络适配器条件；尚无独立性能结论，也未建立已验证的新组合基线。

中文成稿遵照本轮从 [README](https://github.com/ruanyf/document-style-guide) 实读的六章规范。项目权威状态由 Integration 管理，本目录只记录主对话阶段交付。

