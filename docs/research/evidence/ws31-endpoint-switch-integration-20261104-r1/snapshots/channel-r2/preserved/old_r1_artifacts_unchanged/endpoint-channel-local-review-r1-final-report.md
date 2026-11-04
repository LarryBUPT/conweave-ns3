# WS-31 channel 本地静态审查

日期：2026 年 11 月 1 日。审查已完成，结论为 **FIX REQUIRED**。当前 WIP 有 4 项 P1 问题和 1 项 P2 问题，不能按原样进入工程执行验收。本结论限于源码静态分析。

本轮承接关闭前的[未完成检查点](endpoint-channel-local-review-r1-checkpoint-handoff.md)。旧检查点及其 QA 保留原字节。本轮没有编译、运行夹具、访问实验服务器或修改科学源码。

## 1. 审查对象与结论范围

固定父提交为 `8cd1ba69469bf80143d5c89edc17fa72611018e8`。实现树为 `E:/研/毕业论文/workspace/ws31-candidates-implementation`。计划 SHA-256 为 `5e73c6e98844c393dc63f6e2a1d141d6116af2466b8426156d6378da2c85d20d`。恢复时及交付前，五份 WIP 的哈希均与计划一致。

完整身份、精确锚点和后继动作见[review JSON](endpoint-channel-local-review-r1-final-review.json)。[证据索引](endpoint-channel-local-review-r1-final-evidence-index.json)复用旧检查点的 23 项证据，新增 7 份父源和 6 份文献记录快照；共 36 项。工作字节与 Git blob 分别记录，比较父源时只将工作文件的 CRLF 规范为 LF。

本次逐项完成六项计划问题：默认路径与改动范围、旧事件模板、身份与账本、异常与生命周期、替代 Receive 夹具、真实网络缺项。静态对应成立的部分见第 3 节。代码修复和动态验收继续由主对话承担。

## 2. 必须处理的问题

### C1 / P1：TypeId 相等不能排除覆写 channel 子类

问题位于 [Bind 的类型检查](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-channel.h:112)。检查比较 ns-3 实例 TypeId，契约却要求精确的 C++ 动态类型。

父源 [CompleteConstruct](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/core/model/object.h:415)通过 `T::GetTypeId()` 设置类型；[GetInstanceTypeId](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/core/model/object.cc:76)返回保存的 `m_tid`。未声明自身 GetTypeId 的派生类会继承基类静态方法，却仍可覆写 [virtual TransmitStart](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-channel.h:76)。

因此，一个不注册新 TypeId、覆写 TransmitStart 的子类，可以具有 QbbChannel 的 TypeId。接好两端后，它可通过 Bind，再绕过基类观察包装。仅拒绝已注册 QbbRemoteChannel 的夹具覆盖不了此情形。这是静态反例，没有创建或运行该子类。

主应使用精确 C++ 动态类型检查，或提供同等强度、覆盖全部构造入口的来源约束。`dynamic_cast<QbbChannel*>` 只能证明继承关系，不能满足精确类型要求。修订后补一个未注册 TypeId、覆写 TransmitStart 的派生类拒绝例。

### C2 / P1：流身份经 U16 序列化后发生别名

适配器在 [Enter](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-channel.h:62)读取 FlowIDNUMTag，并检查非负及已登记。父源 [Serialize](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/network/model/flow-id-num-tag.cc:41)却用 `WriteU16(flow_stat)` 写入 ID；Deserialize 在第 50 行使用 ReadU16。SetId/GetId 的 API 和成员类型仍为 int32。

这条转换真实发生在 packet tag 路径中。[Packet::AddPacketTag](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/network/model/packet.cc:840)调用 Add；[PacketTagList::Add](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/network/model/packet-tag-list.cc:147)立即 Serialize。Peek 在同文件第 162 行调用 Deserialize，然后 Enter 才读取 ID。

静态转换结果为 `-1 → 65535`、`65536 → 0`。当前夹具只登记 0，因此“negative-tag”可因 65535 未登记而被拒绝，不能证明保留了负数身份。若登记 65535，原始 -1 可被接受；若登记 0，未知 65536 可被记到 0 的账本。后续非负检查无法恢复丢失的高位。

主必须冻结并执行身份编码契约。若保留原 tag，应在 G1、全部生产者及登记入口共同限制可表示的唯一 ID 域，并在序列化前拒绝负数和高位值。只在 Register 限制 `0..65535` 仍挡不住输入 65536 别名到已登记 0。另一条路线是单独设计全宽观察身份；这需要新的设计与冻结，不能暗改基线 tag 类体。

最小补例应覆盖上述两组别名、合法边界和跨代 ID 唯一性。所有待加 tag 均须先初始化大小。若选择限制输入域，拒绝必须发生在编码前，而不能声称事后 Peek 可以检测原始越界值。

### C3 / P1：新夹具序列化了未初始化的 flow_size

[Tagged helper](E:/研/毕业论文/workspace/ws31-candidates-implementation/scratch/ws31-endpoint-channel-test.cc:50)只调用 SetId，随后 AddPacketTag。父源 [构造函数](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/network/model/flow-id-num-tag.cc:12)只初始化 flow_stat；Serialize 第 44 行读取 flow_size 并传给 WriteU32。

这会在当前新夹具中读取未初始化整数，导致其行为没有可靠的 C++ 语义保证。尚未运行的正常段和负标签段都使用该 helper，不能直接作为有效验收输入。生产数据包的 [RdmaHw 生成路径](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:1148)则同时设置 ID 和大小。

最小修复是在新 helper 内、AddPacketTag 前设置明确大小，例如该包的 8 B。保留基线 tag 的类体和序列化接口。此修复与 C2 独立，不能用它宣称身份别名已解决。

### C4 / P2：事件异常外抛会丢失当前事件的释放机会

[DeliverWs31](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-channel.cc:147)在 Receive 或 leave 失败时锁存 channel 失败并重新抛出。账本没有伪造闭合，这一方向正确。

旧模拟器的 [ProcessOneEvent](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/core/model/default-simulator-impl.cc:131)先 RemoveNext，再于第 142 行 Invoke、第 143 行 Unref。异常穿过 Invoke 时会跳过 Unref。这里的 Scheduler::Event 只是保存裸指针的事件记录，不承担异常释放。

[五参数事件](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/core/model/make-event.h:409)持有 channel、destination、packet 和 leave 副本。丢失的当前事件引用会继续保留这些对象及回调中的 State/ledger。Destroy 的事件清理只能处理仍在队列中的事件，无法重新找到已移出的当前事件。不能因此推断夹具必然崩溃；当前最后一段仍可能打印 PASS 并退出。

主应明确二选一的错误契约。若要在同一进程内回收并继续，应在观察事件内部保存失败、停止运行并正常返回，使事件走完 Unref；随后在 Run 外报告失败。若保留异常外抛，应把该负例定义为独立的一次性终止进程，只验锁存和未闭合证据，禁止据此宣称完整回收或复用安全。不要为了此夹具修改旧模拟器基线。

### C5 / P1：交付前的部分记账与动画失败没有完整锁存

在 [Enter 第 74～77 行](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-channel.h:74)，ledger Enter 先成功，history.push_back 和 open.insert 随后才分配。若后两步抛出，账本已有 token，channel pending 尚未增加，适配器也没有失败位。

若 history.push_back 失败，或 open.insert 在插入前失败，则 `Pending()==0` 且 `open.empty()`。此时 [Finish](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-channel.h:147)可以成功卸载回调，留下未闭合账本 token。完整 ledger 的排空检查仍会拒绝该 token；问题是 channel 会把部分失败误报成正常 Finish，不能夸大成完整网络排空必然被误认证。

[TransmitStart 第 120～129 行](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-channel.cc:120)另有两段未覆盖：pending 增加后的事件构造／回调复制／调度失败，以及调度成功后的动画 trace 异常。动画失败后若调用者继续 Run，交付仍可能正常闭合，随后 Finish 成功，失败历史却未锁存。Deliver 内的 catch 覆盖不到这些路径。

[Bind 第 126～132 行](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-channel.h:126)还分步修改 channels、enter、leave 和 owner。中途分配或 std::function 赋值失败会留下部分绑定，须一并纳入 setup 失败契约。

主应明确区分两类异常。缺 tag、未知请求等在任何记账前拒绝，应保持可恢复。进入记账或绑定修改阶段后，异常必须使 State/channel 保持终态失败，阻止 Pending、Finish 和复用取得成功；也可通过预分配和无抛出提交实现原子更新。调度结果不确定时不能伪造 RECEIVE_RETURNED 来回滚 token。补充故障注入后，应验证 Enter 后分配、事件调度、动画和绑定各阶段的失败状态。

## 3. 已确认的静态对应

| 审查项 | 判断与证据 |
| --- | --- |
| 五文件范围 | 三份 tracked 修改、两份 untracked，与计划相符；未改既验 ledger/probe。 |
| 默认路径恢复 | 去除观察分支、静态包装及新增 include 后，qbb-channel.cc 精确恢复父 Git blob；头文件删除新声明和成员后也精确恢复。 |
| tag 头文件 | 只增加 include guard；删除 guard 后，完整原文件字节恢复。两个新 guard 在 src/scratch 内没有其他定义。 |
| 旧事件模板 | simulator.h 第 973～977 行接受五参数自由函数；make-event.h 第 404～439 行实现该模板。TypeTraits 对当前非引用参数按值保存，包含 Ptr 和 std::function。此判断不是编译结果。 |
| 事件数量与身份 | 成功路径替换一个交付事件，仍用原目的 context、txTime + delay、原 Packet Ptr。serial 由账本分配并随事件携带，没有按 UID 反查闭合。 |
| 动画顺序 | 原路径和观察路径均先安排交付，再调用 m_txrxQbb；观察记账发生在调度前。未运行 trace，也未证明动画回调无副作用。 |
| 虚调用 | 父源 qbb-net-device.h 第 101 行已声明 virtual Receive；新 Receiver 覆写它。本次没有改生产 Receive。 |
| 正常嵌套 | 静态时序为两次正向 13 ns 返回，第一回调新发反向 16 ns 返回；Receive 内 pending 为 2、2、1，嵌套入账瞬时为 3；serial 1、2、3 分别闭合。 |
| 关闭顺序 | 完整 Receive 返回 → leave 闭合账本 → pending 减少。leave 失败时不减少 pending。这符合当前契约，不恢复旧草案顺序。 |
| 显式 Finish | 在普通成功路径要求自有 channel pending 和 open 均为 0；不清除 held copy、端点、交换机或历史。C5 的异常缺口须修复。 |

## 4. 接线前必须落实的约束

**I1：绑定先于全部发送。** 当前 pending 只统计观察分支。若关闭观察时已安排直接 Receive，随后 Bind 看到的仍可为 0；Finish 也看不到旧事件。当前夹具的 default-off 使用独立 Pair，未触发该情形。G1 必须证明所有相关 channel 在任何发送前已绑定，并在 Finish 到重绑之间证明没有新默认交付。本实现不提供通用的在途晚绑定能力。

**I2：owner 正常存活至 Finish。** State 只拥有账本及数值记录；回调捕获 shared_ptr<State>，没有捕获 session 裸 this。因此 session 提前销毁不会使该回调立即悬空，但 channel 会继续绑定，其他 session 无法正常接管。析构没有生成 Finish，也没有生成排空证据。正常入口须持有 owner 至显式 Finish；owner 丢失只能作为失败／放弃用例处理。

**I3：回调安全不等于 teardown 完整回收。** [QbbNetDevice::Attach](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-net-device.cc:501)持有 channel；channel 的 Link 又持有设备。QbbNetDevice::DoDispose 第 254 行只调用父类清理；[父类第 182～189 行](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/point-to-point-net-device.cc:182)清除的是父类自身成员。派生类另有 m_channel。该强引用关系原已存在，不能归因于新 State 回调环；异常泄漏事件还会新增保留根。本轮不能承诺 Destroy 清空全部对象。

**I4：协议和共享控制包尚未接入。** 当前 Enter 要求每包都有已登记的 flow ID。生产 [SendPfc](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-net-device.cc:481)从空包构造共享 PFC，没有添加此 tag。直接绑定生产 channel 会拒绝这种包；不能跳过记账后宣称整个网络排空。G1 应冻结允许协议及覆盖方式，逐一审计数据、ACK/NACK/CNP、PFC 和重传的身份来源。共享包须有明确的全局／共享状态语义，不能随意归给单流。

**I5：事件返回不等于端到端交付成功。** 生产 Receive 在 link-down、error model、PFC 禁用时可提前正常返回，也可同步转发、修改队列并调用 RDMA。包装在正常返回后关闭当前交付事件是合理的；它只证明该调用已结束。后继事件、队列、定时器、保存 QP、savedRX 和完成历史仍需独立观测。

## 5. 最小后继验证清单

以下均为主对话后续冻结计划中的待办，本次执行数为 0。

| 项目 | 需要区分的结果 |
| --- | --- |
| T1 类型拒绝 | 未注册 TypeId 且覆写 TransmitStart 的子类被拒绝；本地精确类型可绑定。 |
| T2 身份与初始化 | 大小已初始化；合法边界可往返；-1/65535、65536/0 别名在编码前被挡住或由新身份设计区分。 |
| T3 交付错误 | 分别触发 Receive 和 leave 失败，保留未闭合 token；按 C4 明确进程终止或事件内捕获策略。 |
| T4 部分失败 | 注入 Enter 后 history/open 分配、事件构造／调度、动画和 Bind 失败；成功 Finish、重绑和排空认证均不得掩盖失败。预修改输入拒绝保持无 token、可继续。 |
| T5 生命周期 | owner 在空闲／在途时丢失，回调不访问已销毁 session；保留失败与不可正常接管的证据。单独区分正常释放、旧设备引用环和异常事件引用。 |
| T6 setup 时序 | 证明预先默认事件不能被新 session 的零 pending 覆盖；G1 在任何发送前锁定观察范围。 |
| T7 时间与动画 | 对默认／观察路径核包 Ptr、context、延迟、同刻先后、动画顺序、嵌套及 Receive 内完成回调。 |
| T8 真实 Receive | 覆盖早返回／丢弃、PFC、switch 转发、真实 RDMA 完成回调和 savedRX；明确返回与成功接收的不同含义。 |
| T9 完整网络 | G1、switch 纯读、history 清理、两代网络正反例及共享控制状态共同验收；随后完成独立 V0、匹配消融、业务／背景双侧效果和成本。 |

## 6. 参考借鉴复核

本节点已从候选 README 和 reading-log 定位相关记录，重读以下技术附件及核验记录。快照及哈希列于证据索引，两个固定 PDF 的哈希也与记录一致。本轮没有重做论文实验或扩大候选准入。

| 固定版本 | 本节点可借鉴内容 | 适用条件、差异和外推边界 |
| --- | --- | --- |
| DiffFlow，arXiv:1604.05107v1，6 页；PDF SHA-256 `f552fcb75a0cec582286db0032c81660ff161fe475609ae5e79ad7075a0ae164` | 将类别识别、控制生效和实际转发路径分别核验。其记录提醒本项目不能用替代 Receive 代替真实传输，也不能漏计分类／接线成本。 | 作者使用简化 Java 模拟器、无完整 TCP、两类独立队列。本项目为 RDMA QP 与 MoE／背景双侧目标。类别广告和 ECMP/RPS 混合不等于本项目 endpoint 证书，论文数值不支持本 WIP 正确性或收益。 |
| Flowcut，arXiv:2506.21406v2，16 页；PDF SHA-256 `1ba1e8cbad41973d3b42112a1a33876629541da814ac56bd06132439704fd1a1` | 借鉴明确在途状态、确认闭合条件和暂停排空成本的做法；对应本节点对覆盖范围、关闭时刻和保留引用的检查。 | Flowcut 按 ACK 清在途字节；本适配器按单次 Receive 返回关事件 token，两者不是同一证明。其 SST／Slingshot、启动 BDP、ACK 及暂停条件不自动成立；其保序和效果不能外推为本项目跨代复用或双指标收益。 |

本节依据[本地候选记录](E:/研/毕业论文/参考文献/候选/README.md)及证据快照，不新增学术引用或借论文替代固定源码。中文成稿已对照[阮一峰规范](https://github.com/ruanyf/document-style-guide)的 README 及六章复查标题、段落、空格、数值和标点。

## 7. 交付状态

本地静态审查范围完成，修复与所有动态验证未完成。真实 switch、完成回调／savedRX、历史、G1、两代网络、独立 V0、三候选匹配消融、双侧效果和成本继续为必做项。本轮没有形成新基线或性能结论，也没有重跑旧已验对象夹具。

审查期仅涉及五份 WIP 的只读约束，现已[明确释放](endpoint-channel-local-review-r1-final-guards-released.json)。本轮的 SSH、同步、部署、编译、测试／夹具、网络执行、源码及 main 编辑、提交和推送均为 0。后继由主先修复，再冻结新的源身份与计划；本报告本身不授权执行。
