# WS-31 第十八节点：channel 静态审查与修订整合

日期：2026 年 11 月 1 日。状态：完整首版静态审查已接收；修订版为未编译、未执行的 WIP，独立只读复核中。WS-31 继续 ACTIVE。

## 1. 本对话目标

Integration 独立核对 WS-31 主交接的 channel 审查证据、原始文件留存和 r2 修订身份，更新权威状态。算法实现由主承担，唯一副承担本次只读复核；本对话不接管科学源码或远端。

## 2. 已确认的项目事实

实现克隆为 `E:/研/毕业论文/workspace/ws31-candidates-implementation`，分支 `feature/ws31-candidates`。本次本地观察 HEAD 和个人 origin tracking 均为 `8cd1ba69469bf80143d5c89edc17fa72611018e8`，三份受跟踪修改、两份新增未提交。既验网络仍为 43 格；17 例非网络适配器、20bc 可移植核心和 8cd 对象夹具分别保留，不合并为性能样本。

首版 review SHA-256 为 `85b22cc6a3393d2f4d07d597d32128864aa2e95eb06e6c20481b01c208e7f1f9`，QA 为 `9e96f3f9480a0f88feb76f94fd0d9299985afc9db9cfa8750bd97b7e825141fe`。原审查有四项 P1、一项 P2，不批准首版按原样执行。

## 3. 已完成工作

Integration 的[本地审计器](../research/evidence/ws31-endpoint-channel-integration-20261101-r1/audit_local_evidence.py)核对 36 项证据、22 份父源 Git blob 副本、额外一项 scheduler 父源指纹、55 个原版本源码锚点及新旧各五份 WIP。原版本锚点使用 r1 封存字节，未错误指向已修订的工作文件。审查、报告、QA、释放记录和主验收据哈希一致；旧未完成检查点和原释放记录也已保留。

五项问题与修订对应如下。右栏只表示代码已编写，尚无编译或运行通过结论。

| 问题 | 严重程度 | r2 写入内容与未完成边界 |
| --- | --- | --- |
| C1：继承 TypeId 的覆写子类可绕过包装 | P1 | 同时检查精确 C++ typeid 与 ns-3 TypeId；新增覆写子类拒绝代码，实际 RTTI 兼容未验。 |
| C2：U16 序列化使负数／高位 ID 别名到合法 ID | P1 | 新编码器和登记限制 0～65535；实际 G1／全生产者检查未接入，不能识别已经截断的外来身份。 |
| C3：新 helper 未初始化 flow_size | P1 | 新编码器在 AddPacketTag 前明确设置 ID 和大小；原 tag 类体及编码体保持。 |
| C4：事件异常外抛跳过当前事件 Unref | P2 | 事件内保存异常并 Stop 后正常返回，Run 外查询原失败；不伪造 token 闭合，不承诺全部对象回收。 |
| C5：部分记账／调度／动画／Bind 失败未完整锁存 | P1 | 增加失败锁存，绑定先分配后以无抛出 swap／owner 赋值提交；故障代码均未运行。 |

另增加已使用 channel 的晚绑定拒绝和 owner 丢失夹具。新旧各三项删除恢复检查通过，默认路径新增使用标记写入，其功能和成本待实测。新五文件与封存逐字节相同，四份较 r1 改变；tag 头字节未变。

审计留存 78 份快照，见[验证收据](../research/evidence/ws31-endpoint-channel-integration-20261101-r1/verification.json)与[来源清单](../research/evidence/ws31-endpoint-channel-integration-20261101-r1/source-manifest.json)。本轮没有运行其他 checker、编译器、夹具或仿真，没有重算旧 raw。

## 4. 已形成的设计决策

保留基线 FlowIDNUMTag 类体与编码体，在受控新入口限制身份域；完整方案仍须接入真实解析 G1 和每个生产者。只检查 Register 或 Peek 不能补回编码时丢失的高位。

失败后保留原异常和未闭合 token。观察事件正常返回以到达旧模拟器的 Unref，不将停止或 Destroy 写成完整排空。部分故障是准确变更边界的受控抛出，不能称为实际内存耗尽或调度器插入失败；动画通过真实 trace 回调编写。

## 5. 当前状态

首版约束于 12:34:40 UTC（北京时间 20:34:40）明确释放，主在副 idle3 后修订。r2 新只读计划 SHA-256 为 `6562ce1cb84f6b1b942b0d2e61982d86203371fc7f977e85e459bbb767b975e0`。主报告唯一副 active cursor `e48b2fab-5538-4004-8e5d-575b33e8e994:4`；五份受审文件冻结，所有远端、构建和测试授权为 0。

Integration 本次单目标 compact snapshot 观察主为 idle，cursor 已重置为 `30516c1d-6c65-4481-bd73-77602ce15c3a:1`。副 cursor 来自主交接，没有直接轮询或重复派发。r2 尚未获独立通过，也未提交／推送，8cd 的旧验收不扩展到新工作字节。

## 6. 未解决问题

必须接收 r2 复核并处理必要问题，完成真实 switch 纯读、完成回调／saved RX、历史清理、实际 G1、全部生产身份来源及共享 PFC／CNP、ACK/NACK、重传覆盖。替代 Receive 不能替代生产 NIC／交换机／RDMA 路径；单次 Receive 返回也不是网络交付成功或全局排空。

真实两代网络正例／拒绝例、独立 C1 V0、三候选匹配消融、业务批次与背景尾部双侧效果、状态和运行成本继续必做。没有新组合基线，不关闭或归档 WS-31。

## 7. 后续推荐动作

主先接收唯一副的 r2 只读复核，必要修复后继续实际接线，再共同冻结新源、工程计划及网络正反例。独立计划、正确性和新资源门通过后，由唯一副以新 ID 执行；不对未接线版本反复全量构建，不重跑旧成功 ID。

## 8. 与其他工作流的关系

本次按主的[参考复核](../research/evidence/ws31-endpoint-channel-integration-20261101-r1/snapshots/main/evidence/endpoint-channel-node18-reference-review-r1.json)，从候选 README／reading-log 重查 DiffFlow `arXiv:1604.05107v1` 和 Flowcut `arXiv:2506.21406v2` 的技术、核验记录，共六份现行本地记录与快照哈希一致。DiffFlow 提醒区分类别识别、控制启用和实际传输；Flowcut 提醒明确在途状态、闭合条件及排空成本。前者的简化传输与分类喷洒、后者的 ACK 字节闭合及 SST／Slingshot 条件，均不证明本项目 RDMA 端点排空、跨代复用或双侧收益。

Flowcut 现刊名的 CCF 资格仍未核定，本节点仅作方法参考，不新增正式基线。Ofan 暂缓；WS-29 不读取、不启动、不归档。WS-26～28 归档状态和 QueuePin 已投稿文稿保持原样，不恢复旧控制器或矩阵。

## 9. CONTEXT SNAPSHOT

第十八节点已接收 r1 完整静态审查，36 证据／22 父源副本／55 锚点和新旧各五文件均核，四 P1／一 P2。主释放后写 r2 并封存，独立只读复核 active4；HEAD 仍 8cd，五份未提交 WIP，编译／运行／远端授权 0。实际 switch／回调／history／G1／全生产者身份／共享控制与两代网络仍未完成。43 格网络、17 例适配器及旧核心／对象工程证据分列；V0／消融／双侧效果／成本保持必做，无新组合基线。
