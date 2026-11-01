# WS-31 实际对象快照 probe 本地独立审查

日期：2026 年 11 月 1 日。依据[冻结计划](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/main/endpoint-probe-local-review-r1.json)，只读审查固定 HEAD `20bc2d9f7c7c435bf832ba2fcaf0e07df00cf5da` 上的两份 WIP。本轮编译、核心／夹具／网络执行、远端动作均为 0，没有修改实现或主材料。

## 1. 结论

probe 已写出实际 NS-3 对象字段的读取路径，静态审查未发现可确认的 C++11、旧 Ptr 或 friend 访问阻断。RX 反向身份、生产 packed key、原需求与放行延迟校验符合固定源；避开有副作用的 GetBytesLeft、IsFinished 和调度器查询是正确选择。

仍须补齐覆盖完整性门，才能把这些读取接成可验收快照。优先处理 P1：保存的旧 TX QP 必须被计入完成／pending 结果，并证明它仍在真实绑定的保留组中。P2、P3 分别补齐范围与重复计数规则、live map 空引用拒绝。以下反例均为静态推演，未运行；尚无实际测量或网络失败结论。

`observedFields` 为 127，刻意缺少 SWITCH_STATE。既有账本要求 ALL=255，故当前 probe 不能单独通过 Retire／Drain／SwitchCleared／复用快照门。这项拒绝应保留；默认零交换机计数也不能据此升级为实测零。

## 2. 已核实现与兼容性

| 检查项 | 固定源码核对 | 静态结论 |
| --- | --- | --- |
| 头文件依赖 | rdma-hw.h 包含完整 QbbNetDevice 和 RdmaQueuePair 定义，生产键函数、映射与历史为 public | 当前成员和类型可见；新头文件尚未经过编译与链接 |
| 旧 Ptr | [Ptr 的 safe-bool 与比较接口](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/core/model/ptr.h:104)、[PeekPointer 实现](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/core/model/ptr.h:279) | 条件判断可用；Ptr／Ptr 比较按原地址，`Ptr != nullptr` 可经 Tester* 转换参与内建比较，不能仅因没有 nullptr 专用重载认定编译失败。后继仍须用实际旧环境编译这些表达式 |
| friend 与继承字段 | [窄 friend 声明](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-net-device.h:78)；基类的 BUSY、m_txMachineState、m_linkUp、m_currentPkt 均为 protected | friend 经 QbbNetDevice 对象访问继承的 protected 成员符合访问规则；没有新增数据成员或虚函数。只读性来自实现和验证，friend 声明本身不禁止写入 |
| TX 身份与时钟 | [保存 TX 校验](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-probe.h:118)核 flow_id、完整 tuple、PG、大小、原标签、startTime 与放行延迟；[生产需求原点](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:268) | 需求与放行原点未被 probe 改写；仍依赖真实捕获对象来源，见 P1 |
| RX 翻转 | [ReceiveUdp 实参](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:511)与[GetRxQp 赋值](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:389) | 保存 RX 应为 sip=原 dip、dip=原 sip、sport=原 dport、dport=原 sport；probe 检查正确 |
| 生产资源键 | [实际函数调用](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-probe.h:113)调用 TX `(dip,sport,dport,pg)`、RX `(sip,sport,dport,pg)` | 与生产调用关系一致，没有复制可移植镜像代替实际函数 |
| 发送／接收事件 | 保存 TX 四个事件、不同 live TX、各保留 TX，及保存／不同 live RX 的 QcnTimerEvent | TX 定时对象按地址去重；RX 相同对象不重复。m_nackTimer 是 Time 阈值，不计作待执行 EventId |
| 队列和串行化 | 物理队列、主机 ACK 队列、BUSY／currentPacket、pacing／resume 事件 | 能读取不同存放位置；BUSY 与当前包任一非零即计一份发送占用，不能解释为包数量 |

## 3. 需要修复或冻结的事项

### P1：保存的 TX 对象可能未计入完成和 pending，且缺少真实组绑定门

位置：[保存对象身份检查](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-probe.h:118)、[聚合初值](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-probe.h:143)、[仅从设备组累加](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-probe.h:165)。

保存 TX 的元数据和计时事件被读到，但它的累计确认完成与 Pending 只在该指针恰好出现在枚举组时参与聚合。当前 `retainedQpsFinished` 从 true 开始，未要求在任一实际绑定组中见到 savedTx；`txNodeSeen` 也只证明该节点存在某个 Qbb 设备。

构造对象反例（未执行）：保存 TX 的 flow_id、tuple、字节、标签与时钟均匹配，但 `snd_una < m_size`、`snd_nxt < m_size`；对应映射已为空，事件及队列为空，枚举组为空或错误地挂到另一空组。当前保存 TX 的计时为 0，完成标志保留 true，pending 保留 0，`snapshot.Quiet()` 可以为 true。该对象状态违反已冻结的“保留旧 QP、追加新 QP”接线政策，却未被 probe 识别。当前缺失 SWITCH_STATE 仍阻止核心认证；问题应在完整接线前修复，不能等合并 switch 位后沿用默认完整性。

最小修复：保存 setup 阶段的真实 RdmaHw／NIC／组绑定凭据，在观察时核对传入 HW、m_nic 的设备和 qpGrp、设备的 m_rdmaEQ->m_qpGrp；要求 savedTx 出现在规定的实际保留组中。独立将 savedTx 的 IsFinishedConst、Pending 和事件纳入按对象去重的汇总，再与枚举覆盖核对；找不到应抛出明确的缺覆盖错误，不能当作空组已完成。若未来允许物理移除旧 QP，应另行提供退役收据与策略，当前合同不隐式放宽。

实际绑定关系见[RdmaDriver::Init](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-driver.cc:33)及[RdmaHw::Setup](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:225)。不要在纯度指纹区间内临时调用 Node::GetObject 来补取 driver：[DoGetObject](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/core/model/object.cc:145)可能增加访问计数并重排 aggregate 数组。可在 setup 时捕获实际 driver／HW／设备指针并记录绑定，probe 只比较和读取。

### P2：明确设备范围、缺项与共享对象的计数规则

位置：[设备必要字段](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-probe.h:76)、[NodeList 枚举](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-probe.h:151)及[当前范围门](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-probe.h:173)。

枚举所有当前 NodeList 的 Qbb 设备对最小无背景进程是保守选择；它也会包含其他节点的活动 QP、队列与设备事件，因此这里得到的是全进程 Qbb 设备静默条件，不能称单流精确占用。非 Qbb 设备被跳过，当前没有跳过原因或预期设备集合；节点出现任意一个 Qbb 设备即可满足 txNodeSeen／rxNodeSeen，不能据此验证端点的全部实际 NIC 和组都已接好。

主机允许 physicalQueuePresent=false，物理字节沿用默认 0；而本项目 [QbbHelper::Install](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/helper/qbb-helper.cc:217)为两端都建立了物理队列。若采用这一标准夹具，应检查该队列存在；若另有合法无物理队列配置，须明确声明该分支不适用，并保留实际 absence 原因，不能把未按预期装好的队列当成已测零。

timerObjects 已去重 TX 事件对象，pending 和保留条目却按每个设备引用累加。共享组或同一 QP 重复出现在组中时，pending 可能重复计数；布尔完成判断仍保守，非负重复计数本身不会把非零变为零，但不能报告为唯一载荷字节。相似规则适用于意外共享的物理／ACK 队列。

最小处理：冻结并核对预期 Node／设备／接口集合，对 loopback 等明确排除，对未知非 Qbb 数据面设备拒绝；记录设备、RDMA 队列、物理／ACK 队列、组的对象身份及组索引。对共享对象按规定范围去重，或显式拒绝标准夹具中不允许的共享／重复绑定。P1 的端点 NIC 和保存对象必达是其中必须满足的子门。不要为去重而忽略同一个 QP 在不同槽位上的 finishedBit 差异。

### P3：live map 中空 Ptr 应在解引用前拒绝

位置：[live map 读取](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-probe.h:133)至第 149 行。代码区分 key 缺失，但找到 key 后立即解引用其值；保存指针和组内指针已有 Need 检查，live map 值尚无对应检查。

正常生产插入使用有效对象，本轮没有发现真实路径插入空值的证据。对象夹具中的缺项／损坏映射反例仍应得到可诊断的 fail-closed 结果。最小修复是在任何 live flow_id、Timers 或 QcnTimerEvent 读取前检查 Ptr 非空；记录 live 对象地址及必要身份，便于区分保存对象与后来重建的对象。现有 live map 只要存在就令 txAbsent／rxAbsent=false，因此不同 flow_id 或重建对象不会被误认为映射已退出；这里主要补齐错误诊断和空引用边界。

## 4. 只读性与数值含义

[GetBytesLeft](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-queue-pair.cc:96)在 IRN 首个 SACK 块从 snd_nxt 开始时，会推进 snd_nxt 并 discardUpTo；[IsFinished](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-queue-pair.cc:166)也有同样写入。RdmaEgressQueue::GetNBytes 会调用前者，GetNextQindex 会写完成位和暂停统计，均不应进入 probe。

当前调用的[IsFinishedConst](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-queue-pair.h:169)、[IsQpFinished](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-queue-pair.h:239)、[物理字节](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/network/utils/broadcom-egress-queue.cc:232)、[ACK Queue::GetNBytes](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/network/utils/queue.cc:136)及 Node／设备／Packet 标识和大小查询，沿已读实现没有协议状态写入。std::map／unordered_map 的 find／count 不插入条目；PeekPointer 不 Acquire，Ptr 临时引用按生命周期释放。结果容器分配内存与局部计数不属于修改被测协议状态。

Pending 是读取 `limit - snd_nxt` 的保守字段界，不是物理排队字节，也不是准确的待重传包集合。snd_nxt 回退或 IRN 可跳过的 SACK 区间可能让它高估；snd_nxt 到达末尾而 ACK 未完成时，仍须由完整的 QP 完成覆盖和事件／token 门阻止排空。不得通过调用 mutable getter、推进 snd_nxt 或清 SACK 来让观察结果变成 0。

[EventId::IsRunning](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/core/model/event-id.cc:59)经 IsExpired 只查询有效模拟器的状态；[当前事件的过期规则](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/core/model/default-simulator-impl.cc:387)会把已开始执行的当前事件判为 expired，因此事件数为 0 不能证明相关回调栈已返回。probe 必须在 transport／timer／Receive 调用栈展开后的独立检查事件中运行，配合原交付 token，而不是在完成 trace 中直接认证。

纯度测试应在 NodeList 与模拟器已建立、尚未 Destroy 的真实对象上下文进行。Simulator::Now 可能惰性建立实现，NodeList 首次访问会注册并安排 destroy 清理；这些初始化须放在指纹区间之前。当前 Read 需要已存在的端点 Node，正常 setup 已建立 NodeList；此项是上下文约束，不将初始化副作用误报为正常读取时的协议修改。

另需冻结动态拒绝政策：ReadDevice 能记录 paused／resume 状态，但 Read 对任意 down 或 paused 设备直接抛异常。它会阻止认证，属于 fail-closed；若按最小夹具把它定义为致命范围错误，应保留该判据与原因。如果要把 PFC 暂停作为合法非静默观察并推进账本时钟，则须返回结构化观察并参与 Quiet 条件，不能静默清除 paused 标志或只删除 Need 检查。

## 5. 最小后继编译和对象纯度测试

以下仅为设计要求，本轮未创建或运行测试，也没有新增执行授权。

| 项目 | 最小安排与验收 |
| --- | --- |
| 实际接口编译 | 新翻译单元包含 probe，使用真实旧 NS-3 头文件和库，以 C++11 编译并链接；触及 ReadDevice 与 Read、Ptr/nullptr、继承 protected friend、队列和 EventId 路径。固定新源码后独立立门，不继承已验便携核心的编译结论 |
| 实际对象、手工状态 | 创建真实 Node、QbbNetDevice、队列、QP、RdmaHw 和绑定；由夹具 setup 安排状态。测的是实际对象 getter 与聚合纯度，不是网络传输或自然排空。所有初始化和对象捕获均在指纹之前 |
| IRN 核心反例 | 设置 snd_nxt 正好等于首个 SACK 块起点，保留至少两个 SACK 块；连续两次 Read 后 snd_nxt、snd_una 和完整 SACK 序列均不变，保守 Pending 符合字段公式。可用已核纯读取的 SACK 输出／查询留证，不调用 GetBytesLeft／IsFinished 做对照 |
| 完成位与 retained | 覆盖完成 QP 但 finishedBit 尚未置位、旧完成位已置位、未完成 QP 却有 finishedBit、保留旧 QP 后追加新槽位。观察不改变向量、位图或 rr／暂停统计；此对象测试仍不证明第二代真实发送 |
| 缺覆盖与错误身份 | savedTx 不在实际绑定组、HW／NIC／组错配、缺预期设备或队列、重复组／QP、live map 空 Ptr、错误 flow_id／RX 翻转／时钟均有明确拒绝或按冻结规则计数，不产生完整可用证书 |
| 活动状态 | 分别安排 QP 事件、pacing／resume、物理及 ACK 队列、BUSY／currentPacket、未完成 QP、history 存在及 RX 重建，核原始状态与输出对应，拒绝路径也不得改对象 |
| 同时刻纯度 | 在同一检查事件中连续读取两次，中间不 Run、不推进事件。对比协议字段、SACK、maps／sets、组与位图、队列字节、包 UID／大小、事件 UID／时间／上下文／取消状态、Simulator::Now；在条件允许时加调度器事件集合前后收据，避免仅凭输出相等推断无隐式调度 |
| 覆盖位和接线边界 | 输出 mask 仍为 127，直接交给核心应因字段不完整被拒绝；只有真实交换机逐项观测才能补 SWITCH_STATE。channel／held token、回调后闭合、G1 和网络正反例另行验证 |

必要 raw 应含预期范围与实际对象地址映射、各字段前后值、两次观察、拒绝原因及精确上下文。不要以整个 C++ 对象的 memcmp 作为纯度判据，避免把引用计数、填充字节或诊断 bookkeeping 与协议状态混为一谈。

## 6. 证据边界、参考复核与交付

“已写实际对象读取代码”“实际对象纯度测试已执行”“真实网络端点已测量”是三个阶段。本轮只达到第一阶段的静态审查；三类执行计数均为 0。真实 switch 观察、channel 原事件凭据、savedRX 删除前捕获、历史清理、保留追加分支、G1 和双代网络正反例继续由主对话承担，独立 V0、双侧效果与成本仍未完成。

本节点从[候选索引](E:/研/毕业论文/参考文献/候选/README.md)和[累计阅读](E:/研/毕业论文/参考文献/候选/reading-log.md)定位 DiffFlow，复核[技术记录](E:/研/毕业论文/参考文献/候选/papers/diffflow-2016/analysis-technical.md)及[核验记录](E:/研/毕业论文/参考文献/候选/papers/diffflow-2016/verification.md)，版本为 arXiv:1604.05107v1。可借鉴先核前置状态再启用后继行为的顺序；适用于本 probe 的范围与证据门，不提供完整 RDMA 回收协议。本文处理真实对象和事件，DiffFlow 处理分类与喷洒，其简化传输和独立队列不能替代实际源或排空证据，也不外推为业务收益。本轮没有新增机制、对照或论文实验。

两份 WIP、HEAD 和两份已验核心输入前后不变；先前独立交付未改。仅交付[审查 JSON](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-local-review-r1-review.json)和[QA](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-local-review-r1-qa.json)及本报告。源码仍是未编译 WIP，本轮没有提交、冻结新源或授权后继执行；主对话据 P1～P3 修订与冻结后再推进。
