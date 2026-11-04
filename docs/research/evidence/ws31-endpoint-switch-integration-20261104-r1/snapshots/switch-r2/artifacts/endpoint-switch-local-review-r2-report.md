# WS-31 switch r2 静态审查

日期：2026 年 11 月 4 日。结论为 **FIX REQUIRED：1 项 P1**。S1／S2 的探针修订在源码层成立，但新夹具的 owner 拒绝用例会先在纯度指纹中解引用空 QP group，阻断后续检查。未编译、运行或取得 mask 255 实测证书。

本轮恢复 11 月 1 日因 usage limit 中止的同一目标。失败 turn `01a19786-5399-7631-a7c8-c0517ab25c14` 保持失败身份；原计划 SHA-256 仍为 `950104b5c26805437f7dab8a877176a20ae9dd2be15d0ab1a65b75488780b775`。[恢复收据](endpoint-switch-local-review-r2-resume-receipt.json)及[中间检查收据](endpoint-switch-local-review-r2-progress-r1.json)保留未完成阶段，不覆盖为通过。

恢复及交付时，HEAD 均为 `8cd1ba69469bf80143d5c89edc17fa72611018e8`，十份 WIP 与原计划和主封存精确匹配。五份 channel 文件与前次 switch r1 审查一致，本轮只核字节并复用已接收分析。执行清单和 registry 含历史状态，当前边界以本计划、主恢复收据及实际字节为准。

## 1. R2-F1 / P1：owner 拒绝前的指纹解引用空组

触发点在[夹具第 303 行](E:/研/毕业论文/workspace/ws31-candidates-implementation/scratch/ws31-endpoint-switch-test.cc:303)：将中间链路的 switch 设备 owner 改为主机，然后调用 denyRead。denyRead 在[第 267 行](E:/研/毕业论文/workspace/ws31-candidates-implementation/scratch/ws31-endpoint-switch-test.cc:267)先计算 state，之后才执行 observe／Read。

state 的 Device helper 在[第 134 行](E:/研/毕业论文/workspace/ws31-candidates-implementation/scratch/ws31-endpoint-switch-test.cc:134)根据设备当前 owner 的角色选择主机分支。owner 已改为 host，故进入原本用于主机 NIC 的分支，并在[第 139 行](E:/研/毕业论文/workspace/ws31-candidates-implementation/scratch/ws31-endpoint-switch-test.cc:139)无条件读取 `eq->m_qpGrp->m_qp_finished`。

该设备实际仍是 switch 设备。父源 [QbbNetDevice 构造函数](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-net-device.cc:249)为它创建 RdmaEgressQueue；[队列构造函数](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-net-device.cc:91)没有赋值 m_qpGrp，因此该 Ptr 保持空值。只有[主机 RdmaHw::Setup](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:231)绑定实际 QP group；本夹具仅初始化两个主机 driver。

所以该拒绝例会先遇到空指针解引用的未定义行为，尚未执行预期的 owner／index 守卫。通常可能表现为进程崩溃，本轮没有运行观察。后续错误保存对象、history、同纳秒队列、人工 token、原定点清理和接口重捕获等分支，不能按当前源码认定已可达。

最小修订是在指纹中安全表示错误绑定。可按遍历节点或已捕获角色决定需读取哪类协议状态，并显式序列化 egress／ACK／group 的存在性后再访问。不要依赖刚被故意改坏的 GetNode 结果选择对象布局，也不要在指纹中补组或修 owner。修订后，应保留前后完整字符串比较，并核对 owner 拒绝确实来自目标守卫。

## 2. S1／S2 修订复核

| 项目 | 源码判断 |
| --- | --- |
| S1 范围来源 | Scope 私有保存真实 EndpointProbe::Scope；Capture(drivers) 同时捕获端点与 switch。Read 不再接受外部 Observation，直接调用实际 EndpointProbe::Read，再同步读取 switch。 |
| S1 无交错采样 | 当前标准对象路径没有 Run、回调、清理或 aggregate 查找夹在两段读取之间。旧端点结果无法作为参数传入；static_assert 也固定了唯一函数签名。 |
| S1 同纳秒队列 | 用例保留旧端点结果，再直接入队 32 B。新组合 Read 会重新读取实际队列，应看见 32 B；它没有使用旧结果补位。该后续分支目前受 R2-F1 阻断。 |
| S1 接口变化 | 旧组合 Scope 会因接口数变化拒绝；重新 Capture 时端点和 switch 范围同时更新，不再拼接新旧范围。 |
| S2 设备绑定 | DeviceBinding 在 Capture 和每次 Validate 均检查非空、实际 GetNode、GetIfIndex 和全范围设备唯一性，且只接受 Qbb／loopback。节点角色、精确 SwitchNode、节点／接口数量与指针、模式和至少一个 switch 的检查保留。 |
| 只读语义 | Contains、PortCount、SharedActivity 沿用 r1 的 const 查询。Read 不调用 GetObject、Expire、Pressure、Value、Erase 或 Reset。GetObject 仅在 setup 的端点 Capture 内使用。 |
| 头文件改动 | budget、quota、switch-node 相对已审 r1 仅新增测试 friend 及必要前置声明；删除这些新增内容后精确恢复 r1，未增加生产数据成员或虚函数。 |

上述判断限于受审的标准对象及同步读取契约。真实 G1、全部身份生产者和共享控制协议仍未接入，不因组合读取而自动完成。

## 3. C++11、对象绑定与纯度指纹

检查到的新用法与本仓库声明对应：旧 EventId 提供 GetUid／GetTs／GetContext；QP group 的完成位图和 egress 队列字段可按现有权限读取；新 friend 正确指向 ns3 中的夹具类；C++11 支持范围循环、类型推导、静态类型断言和当前容器操作。未发现独立于 R2-F1 的确定性编译问题，实际构建仍待验证。

夹具先创建两个 host、两个精确 SwitchNode 和三条真实 Qbb 链路，再初始化两个 host driver。保存 TX 加入所选实际 NIC 的 group 并置完成位；保存 RX 的反向身份明确设置。协议完成状态由夹具赋值，map 原本为空，未通过实际 RDMA 传输完成。

switch 核心指纹覆盖 pin 的键和值，budget 的容量、条目、范围、期限、端口总量及计数器，quota 的决策、期限、借用／活动统计，以及 observed 的端口字节和时间。State／Other／Shared 都直接访问已有字段，不调用会清理的诊断接口。成功双读比较完整字符串，展示哈希不充当唯一判据。

端点部分是**列出的协议字段指纹**，不能称整个对象状态或内存的完整比较。它包含设备 owner／index、部分发送／暂停事件、逐优先级物理队列字节、ACK 队列计数、QP 位图和保存对象字段等；没有完整记录物理队列包身份、RR 游标、全部队列统计或全部 QP 协议字段。pair 也只逐项比较两次结果的目标 pin／budget／quota 计数，未比较整个 Observation。后续验收应保留这一范围说明；若要宣称更广的队列纯度，应补相应指纹和结果比较。

duplicate-device 用例通过 AddDevice 重复加入同一设备。该操作同时改变接口数并重设 ifIndex，因此拒绝可能先来自接口数或编号守卫；不能据此声称独立动态覆盖了 seen.insert 的唯一性分支。源码中的唯一性检查本身成立。

## 4. 断言可达性和数值推导

下述均为静态预期。原夹具完整到达汇总需先修复 R2-F1，再由新冻结源验证。

| 分段 | 推导与限制 |
| --- | --- |
| 初始空对象 | 实际 map／队列为空，保存 TX 字段与完成位由夹具设置；snapshot 可为 Reusable。此时 ledger 仍 ACTIVE，snapshot 谓词不等于已完成账本生命周期。 |
| Seed 与到期 | 每个 switch 有 K／K2 两类条目。K 预算初始 1,024 B，扣 128 B 后剩余 896 B，线路预算为 928 B；K2 为 2,112 B。K 的期限为 1 ns，quota 期限为 10 ns。推进至 20 ns 后纯读仍保留这些存储条目。 |
| 两 switch 累加 | K 在两张 pin 表、两个 switch 中合计 pinned=4，budget=2，quota=2。stored liveBorrowed[2] 每 switch 为 1，Active(1,20) 为 false；这并不矛盾，因为纯读不处理到期。 |
| 18 个模式 | 每个模式重新 Capture 后读相同人工种入的表，验证查询范围及模式准入。没有运行各模式的生产选路，不能称 18 个算法行为已验。 |
| PG 投影 | 复制 Entry 并同步改保存 TX／RX 的 PG 和 packed key，switch 四元组计数应不变。这验证读取键不含 PG，没有测试 ledger 的跨 PG 新请求准入。 |
| 拒绝路径 | 默认 Scope、改变 mode、错误 index 等在进入新 Read 的守卫处应拒绝。owner 例的指纹先触发 R2-F1；其后所有分支目前是条件推导。 |
| 队列与退休 | 同纳秒入队 32 B 后，端点可退休，Quiet 为 false，CertifyDrain 应拒绝。直接从测试物理队列取走该包后，才进入后续手工 token 检查。 |
| 两个人工 token | CHANNEL 与 HELD_TEST_COPY 分别手工登记。255 覆盖位不应绕过它们；只关闭 CHANNEL 时仍拒绝，手工关闭 held 后才允许 DRAINED。这里没有原生交付事件或 held copy 生命周期证据。 |
| 原定点清理 | DRAINED 后调用原 ResetWs30V13Tuple 清 K。每个 switch 留 K2 的四类表各一条；budget port1=0、port4=2,112，两个 deadline 表各一条，stored liveBorrowed[2]=0；共享 observed／seen／last 保持。target 归零后才做 SwitchCleared。 |
| 末尾范围例 | 新 loopback 使旧 Scope 拒绝，整体重捕获后可读；随后重复设备、节点数、角色、未知接口和 switch 子类分别有拒绝路径。均需修复后实际验证。 |

若全部分支按修订意图完成，源码计划量为 25 组 paired read、63 次组合 Read（其中 10 次拒绝、53 次返回）、19 次全部拒绝。另有一次直接 EndpointProbe::Read 用于保留旧结果。当前没有这些实际计数；也没有把 25 组双读写成 25 份独立网络样本。

## 5. 后续最小动作

主先修 R2-F1，保持 malformed owner 的指纹可安全生成，并核准拒绝原因。随后冻结新十文件身份及执行计划；本报告没有授予编译或运行权限。新验证须核原始行、完整字符串比较、实际到达的分段、清理前后目标／K2／共享状态，而不能只收汇总 PASS。

实际完成回调／saved RX、history 释放、真实 G1、所有身份生产者、共享 PFC／ACK/NACK／CNP／重传、channel／held copy 与两代网络正反例继续必做。独立 C1 V0、三候选匹配消融、业务／背景双侧效果和状态／运行成本未完成。Ofan、WS-29、旧控制器及矩阵没有开展。

## 6. 本节点参考借鉴复核

以候选 README／reading-log 为入口，复核 DiffFlow v1 和 Flowcut v2 的技术及核验记录。DiffFlow（arXiv:1604.05107v1）提醒应分别验证控制生效、传输和回收，简化 Java 及分类队列结果不能替代本项目真实协议。Flowcut（arXiv:2506.21406v2）提供明确在途状态／闭合条件及成本的参考，但 ACK 字节闭合不同于本夹具的人工 token 与字段赋值。

本轮借鉴点是保持“字段覆盖、账本门、协议完成、共享状态和成本”的独立证据。两篇都不能为当前夹具可达性、mask 255 或双侧收益提供实测支持。固定版本及记录哈希见证据索引，没有新增机制或基线准入。

中文成稿依据本对话已读取的[阮一峰原规范](https://github.com/ruanyf/document-style-guide)及六章复查标题、段落、空格、数值和标点。

## 7. 交付与释放

计划七项静态审查问题已完成，详见[review JSON](endpoint-switch-local-review-r2-review.json)、[QA](endpoint-switch-local-review-r2-qa.json)、[证据索引](endpoint-switch-local-review-r2-evidence-index.json)和[九节交接](endpoint-switch-local-review-r2-handoff.md)。修复及动态验证仍未完成，原 usage-limit 失败与中间收据保留。

十文件只读约束已[显式释放](endpoint-switch-local-review-r2-guards-released.json)。没有更广泛约束、后台任务或新执行授权；SSH／远端、同步／部署、构建、C++ 测试／夹具、网络、科学源／main 编辑、提交和推送均为 0。
