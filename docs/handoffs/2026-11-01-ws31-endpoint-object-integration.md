# WS-31 第十六节点：探针覆盖修订与对象夹具整合

日期：2026 年 11 月 1 日。来源为“WS-31 主对话：类别感知新机制构思与论证”（`01a19322-95a5-76e3-a4f5-1f1e9dde81ce`）的[节点交接](../research/evidence/ws31-endpoint-object-integration-20261101-r1/snapshots/main/endpoint-probe-node16-handoff.md)。本轮核本地静态审查、源码与预检范围，不构建、不运行、不接管远端。

## 1. 本对话目标

核对首版实际对象探针的审查意见与原草稿留存，确认修订固定源及新对象夹具的派发依据。已有 43 格技术网络、17 例非网络适配器和 20bc 可移植核心预检分别保留，本节点不增加执行或性能证据。

## 2. 已确认的项目事实

原审查三份输出与主验收哈希一致，计划哈希为 `fd8e63b3692967d6f938d409945ee9dad12b5401772c2a07e9b56062c51482ee`。审查前后 HEAD、两份 WIP、已验核心输入和计划未变，执行计数均为 0；唯一副于 cursor102 终态、idle 后才换目标。

Integration 的[本地核验](../research/evidence/ws31-endpoint-object-integration-20261101-r1/verification.json)检查 25 个固定源路径、8 项先前文件、报告／JSON／QA、两份留存 WIP 及核心两输入。原 WIP 与第十五节点一致，当前固定修订源与旧草稿分开记录，不回写原审查。

## 3. 已完成工作

| 意见 | 静态事实与修订方向 |
| --- | --- |
| P1，保存 TX 覆盖 | 首版保存 TX 的完成与 pending 主要从枚举组汇总；保存对象不在组中时可能漏计。新源绑定实际 driver／HW／Node／NIC／队列／组，保存 TX 独立入账，并要求在所选保留组恰好出现一次 |
| P2，范围与计数 | setup 冻结 Node、设备、接口及队列身份，仅明确排除 loopback；拒绝未知数据设备、缺队列、共享队列／组及重复 QP，loopback 保留组须为空。GetObject 捕获放在纯度区间之前 |
| P3，空映射 | live map 有键而 Ptr 为空时，先明确拒绝，再读取 live 对象身份；原生产插入路径未观察到此类运行失败 |

P1 是未执行的静态覆盖反例，原 mask127 仍阻止完整 ALL 认证；本节点不称发生了错误排空或网络失败。Integration 核新守卫、读取顺序及测试锚点，完整新源独立审查与运行仍由后续预检承担。

固定新源为 `8cd1ba69469bf80143d5c89edc17fa72611018e8`，父源 `20bc2d9f7c7c435bf832ba2fcaf0e07df00cf5da`。差异恰为新增 probe、scratch 对象夹具及 Qbb 头的三行注释／friend，完整树 4,847 项，哈希与主收据及计划一致。生产 cc、对象数据成员、虚函数和原核心两输入不改。隔离实现树干净，HEAD 与个人 origin tracking ref 一致。

## 4. 已形成的设计决策

[新对象契约](../research/evidence/ws31-endpoint-object-integration-20261101-r1/snapshots/main/endpoint-probe-object-contract-r1.md)分开验证实际对象读取、自然传输完成和网络排空。夹具使用真实 NS-3 对象但手工安排状态，预定八组同刻双读、十四组 Read 拒绝和两项额外拒绝。31 次 Read 包含故意失败调用，不是 31 份成功快照，更不是独立需求数。

测试源码比较完整协议字符串、SACK、maps／sets、QP 槽位与位图、队列、包及事件字段；展示哈希不代替逐字节比较。它安排未来事件但不调用 Simulator::Run，预定 event_calls=0；mask 仍为 127，缺真实 SWITCH_STATE。保留旧 QP／追加槽位的对象测试不替代第二代实际发送。

## 5. 当前状态

Integration 主快照为 idle cursor `f7a3a118-6bff-483e-a32e-333396ead68d:23`；副 active103 为主交接状态，不直接重复派发。新源的编译、对象夹具运行和纯度结果尚未在本节点验收。

权威仓库分支为 `feature/ws23-ws24-evidence-integration`，本次整合前 HEAD 为 `40d3d59b2b2d68e7585caf9573f4bc8034ef0b2b`。只提交五份权威状态、本交接及新 Integration 证据；主、副源目录不整体暂存，实现树只读。

## 6. 未解决问题

新对象夹具的实际编译、同刻双读纯度、拒绝条件和完整来源尚待验收。真实交换机覆盖、默认关闭的原 channel 事件 token、Receive 返回后闭合、RX 保存／完成回调、实际历史清理、G1 以及真实两代网络正例和拒绝例继续必做。

独立 C1 V0、三候选业务批次／背景尾部双侧效果和状态／运行成本仍必做。技术覆盖数不作为独立需求或性能结果，没有新组合基线，WS-31 不闭环、不归档。

## 7. 后续推荐动作

唯一副已承接[对象工程预检](../research/evidence/ws31-endpoint-object-integration-20261101-r1/snapshots/main/endpoint-probe-object-preflight-r1.json)，计划哈希 `d91892f73bc6a6b45c0541f2c588ba59ba3fd3694ec75a75e35be5265dd5b255`，新 ID `20261101-173000-ws31-endpoint-object-r1`。派发时尚未核远端存在性；先独立审源，再过新进程／缓存／worker／资源／ID 门，至多一次同步、一次 optimized `-j2` 全构建和一次新夹具直接调用。

部署、网络、独立旧核心及已验适配器／参考重跑均不授权。源码／入口／环境约束保持至明确终态释放，任何源码、门、构建、纯度、输出或来源不符均保留失败并停止，副不改科学源码或判据重跑。之后再完成真实 switch／channel／完成回调接线并冻结网络正反例。

## 8. 与其他工作流的关系

Integration 维护权威状态，主负责独占实现及原证据验收，唯一副执行当前固定目标。QueuePin 投稿稿和原归档保持，WS-29 不读取、唤醒或归档，Ofan 暂缓，无新增正式方法；新增对照仍受 CCF A/B、必要性、成本及忠实性门约束。

节点参考复核由候选 README、reading-log 进入，核对 DiffFlow arXiv:1604.05107v1 的技术及核验记录。借鉴明确前置条件再启用后继行为的验证问题；其结束检测和回收协议不足以支撑本项目端点证书，分类喷洒、简化传输和独立队列下的平均结果不外推为 RDMA、批次或背景收益。

## 9. CONTEXT SNAPSHOT

首版 probe 静态审查与原 WIP 留存已验，25 固定路径及 8 项旧文件一致。P1～P3 修订固定为干净已推送的 8cd，三文件／4,847 树项，已验核心不改。对象预检已派、源码约束保持，八组双读／十六拒绝仍为待执行计划，mask127、无 Simulator::Run。43 网络／17 适配器与核心预检不变，真实网络及 V0／双侧效果成本未完成。
