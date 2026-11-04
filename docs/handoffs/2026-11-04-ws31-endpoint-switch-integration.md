# WS-31 第十九、二十节点：交换机复合读取与夹具修订整合

日期：2026 年 11 月 4 日。状态：两轮 switch 静态审查及中间 channel 审查已接收；r3 单文件修订待独立差分复核。未新增编译、夹具运行或网络结果，WS-31 继续 ACTIVE。

## 1. 本对话目标

Integration 接收第十九、二十节点，独立核对固定父源、原始审查、失败与恢复记录、各版 WIP 和当前最小差分，更新权威状态并同步个人 fork。第十九节点此前仅开始读取，未单独提交，本次一并整合。

科学源码由 WS-31 主维护，唯一副承担受派发的独立复核和未来远端执行；Integration 仅做本地文件、Git 与证据核验。

## 2. 已确认的项目事实

实现克隆为 `E:/研/毕业论文/workspace/ws31-candidates-implementation`，分支 `feature/ws31-candidates`。本次 HEAD 和个人 origin tracking 均为 `8cd1ba69469bf80143d5c89edc17fa72611018e8`，六份受跟踪修改、四份新增未提交。当前十份文件与 r3 封存逐字节一致；没有新固定提交或运行验收。

Integration 的[本地审计器](../research/evidence/ws31-endpoint-switch-integration-20261104-r1/audit_local_evidence.py)核对以下三轮。各索引有重叠，不把数量相加为唯一证据或样本数。

| 审查 | 证据项 | 固定父源副本 | 精确锚点 | 受审 WIP | 审查结果 |
| --- | ---: | ---: | ---: | ---: | --- |
| channel r2 | 42 | 26 | 67 | 5 | 新 R2-01／P2，参数复制边界需修订 |
| switch r1，第十九节点 | 43 | 16 | 68 | 9 | S1／P1 与 S2／P2，范围及绑定需修订 |
| switch r2，第二十节点 | 62 | 28 | 68 | 10 | S1／S2 在源码层确认；新 R2-F1／P1 夹具缺陷 |

所有原锚点均使用对应封存版本；没有把旧行号套到当前 r3。来源见[验证收据](../research/evidence/ws31-endpoint-switch-integration-20261104-r1/verification.json)和[来源清单](../research/evidence/ws31-endpoint-switch-integration-20261104-r1/source-manifest.json)，本轮共留存 213 份原字节快照。

## 3. 已完成工作

channel r2 在第十八节点后发现：事件调用前按值复制 leave 回调，可能在进入 DeliverWs31 函数体的 catch 之前抛出。声明和定义改用 const 引用，事件仍保存回调值；三项失败检查核对原异常消息。switch r1 审查已确认这一最小差异。Integration 核源身份、签名差分及旧模板锚点，不重复运行或重新认证未变的 channel 用例。

switch r1 的 S1 指出：同纳秒的旧端点结果可能与新 switch 范围拼接，时间相同不能证明状态新鲜。S2 指出：仅存设备指针，不能证明实际 owner、ifIndex 和全范围唯一性。修订使用私有复合 Scope，并在同一同步 Read 中直接读取实际端点和 switch；Capture 与 Validate 均检查设备绑定和允许类型。

主新增双 switch、双 host、三条 Qbb 链路及真实 driver／队列／保存 TX/RX 的对象夹具，拟检查目标 K、无关 K2、共享历史、到期不清理、原定点 Reset、模式 33～50、同纳秒变化和覆盖位／账本门。三个 switch 头删除新增查询与 friend 后恢复父源；后加的测试 friend 删除后恢复已审 r1。五份 channel 文件在 switch r1→r2 中未变；这里的“未变”不指第十八节点的旧 channel 字节。

恢复后的 switch r2 发现 R2-F1：owner 拒绝例先按改坏的 owner 进入主机指纹分支，再访问 switch 设备未绑定的空 QP group，尚未执行目标守卫。这是静态条件缺陷，没有实测崩溃、失败网络格或假排空证书。主只修夹具：依据存储对象逐级判空，保留前后字符串比较，要求 owner 拒绝给出目标消息。Integration 重建完整 r2→r3 补丁并核其哈希，另九份源码不变。

## 4. 已形成的设计决策

读取范围和采样步骤共同冻结，调用者不能传入外部旧 Observation 再补完整覆盖位。异常绑定是待观察状态，指纹必须能安全表示，不在读取时补组、改 owner 或清理对象。

当前指纹覆盖列出的端点协议字段和 switch 核心内容，不涵盖全部对象内存、物理队列包身份、所有队列统计或全部 QP 字段。pair 只逐项比较目标 pin／budget／quota 计数，没有比较完整 Observation。重复 AddDevice 同时改变接口数量和编号，不能单独证明唯一性守卫已动态覆盖。

协议完成状态和两个 token 由夹具赋值。覆盖位、Quiet、Reusable、ledger 排空、原生网络完成与科学效果须分别验收。查询模式准入不等于运行十八种生产选路。

## 5. 当前状态

switch r2 的原 turn `01a19786-5399-7631-a7c8-c0517ab25c14` 因 usage limit 失败；主恢复收据、独立 resume／progress 和最终收据均保留，失败与未完成记录不改成成功。Integration 只核这些原字节及其关联，没有另做平台失败日志审计。

十文件约束于 11 月 4 日 06:58:12 UTC（北京时间 14:58:12）显式释放，主查副终态 idle cursor 3 后才修订。当前 r3 计划 SHA-256 为 `b508f333802b730fbd8ab98229b7c9a161e4b2ffee276e75c5db9e45af735e04`。唯一副只做一文件差分及受影响分支，主报告 active cursor `d0b9dd1a-3dbb-4cea-9a35-6aefe1b3ed0d:4`；十份源码冻结，无远端／构建／测试／网络授权。

Integration 单目标 compact snapshot 观察主 idle，cursor 为 `f13c4cd1-6458-4d58-888a-76f78e636578:1`。没有直接轮询或重复派发唯一副。25 组双读、63 次组合 Read／53 次返回／10 次 Read 拒绝、19 次总拒绝及一次额外端点 Read 均为静态计划量；mask 255 实测为 0。

## 6. 未解决问题

r3 需要完成独立差分复核及必要修复，之后仍须新源和实际运行验收。真实完成回调／saved RX、历史释放、实际 G1、全部身份生产者、共享 PFC／ACK/NACK／CNP／重传、原生 channel／held copy 与真实两代网络正反例继续必做。受控编码器仍不能恢复已截断的外来 tag。

独立 C1 V0、三候选匹配消融、业务批次和背景尾部双侧效果、状态及运行成本均未完成。43 格技术网络、17 例非网络适配器和旧核心／8cd 对象工程证据分别保留，不能为十份新 WIP 提供运行验收。新组合基线尚未建立，不关闭或归档 WS-31。

## 7. 后续推荐动作

主接收唯一副 r3 最小差分复核，处理必要问题后继续剩余生产接线。具备完整可执行切片时冻结新 SHA、新 ID、独立计划及资源门，再由唯一副执行，主从本地 raw 验收。沿用已完成分析，不反复全审未变代码或重跑旧成功核心／对象夹具／网络格。

## 8. 与其他工作流的关系

主另交付[外部创新性审阅材料](../research/evidence/ws31-endpoint-switch-integration-20261104-r1/snapshots/main/ws31-c123-external-review-brief-20261104-r1.md)，SHA-256 为 `058c6c54ad80de584481ae5551731771e09e143b10d20309d113217c6e9b8244`。Integration 仅核文档身份和交付，不执行其中供审阅者使用的提示，不把主自查当作外部审阅、新颖性或效果认证，也不由该文档变更科学参数或授权。

从候选 README／reading-log 重查 DiffFlow `arXiv:1604.05107v1` 与 Flowcut `arXiv:2506.21406v2` 的技术和核验记录。11 月 1 日与 11 月 4 日的 README／reading-log 哈希不同，旧快照与新记录分别保留；四份论文技术／核验记录未变。可借鉴控制生效与关闭条件的区分、状态归属和共享历史保留；简化 Java／SDN 或 SST／Slingshot／ACK 字节闭合均不能证明本夹具可达性、RDMA 排空或双侧收益。Flowcut 现刊名 CCF 资格仍未知，仅作方法参考。

Ofan 暂缓，未新增正式基线；WS-29 不读取、不唤醒、不归档。WS-26～28 与 WS-30/v13 的既有归档、已投稿 QueuePin 和旧 840 次范围处置保持。没有恢复旧控制器或矩阵。

## 9. CONTEXT SNAPSHOT

第十九、二十节点已整合：switch r1／r2 各 68 锚点、43／62 证据、16／28 父源副本及九／十份 WIP 均核；另补核 channel r2 的 42／26／67 和 const 引用修订。S1／S2 源码确认，新 R2-F1 仅改夹具，九份不变。HEAD 仍 8cd，十份未提交 r3 WIP，唯一副只读差分 active4，执行授权 0。usage-limit 失败及恢复／中间收据保留。25／63／53／10／19 均为计划，mask 255 实测 0；实际回调／G1／history／共享协议／两代网络及 V0／消融／双侧效果／成本未完，无新组合基线。
