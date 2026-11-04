# WS-31 channel r2 静态复核

日期：2026 年 11 月 1 日。结论为 **FIX REQUIRED，1 项 P2 必须修订**。r2 的主要修复方向成立，但 leave 的按值传参仍留下事件 catch 之外的复制异常。此处修复后再冻结执行源；本轮没有编译或运行。

固定父源为 `8cd1ba69469bf80143d5c89edc17fa72611018e8`，计划 SHA-256 为 `6562ce1cb84f6b1b942b0d2e61982d86203371fc7f977e85e459bbb767b975e0`。五份受审工作字节与计划及主封存相符。r1 原 WIP、报告、QA 和释放收据保持原样。

## 1. 必须修订：事件调用前的 leave 复制

**R2-01 / P2。** [声明](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-channel.h:142)和[定义](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-channel.cc:152)仍将第五参数写为 `Ws31Leave leave`。函数体第 155 行才进入 try。

旧 [MakeEvent 第 430 行](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/core/model/make-event.h:430)从事件成员调用函数：`(*m_function)(m_a1, ..., m_a5)`。其中 m_a5 是保存的 std::function 左值。构造按值 leave 参数会复制它，复制可能分配并抛出异常；这一步发生在 DeliverWs31 函数体执行之前。

若此复制失败，异常仍穿过 [ProcessOneEvent 的 Invoke](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/core/model/default-simulator-impl.cc:142)，跳过下一行 Unref。channel 没有机会锁存该异常或 Stop，当前事件引用及其持有对象仍可能保留。pending 和 open 仍为正，不能称为伪造闭合；问题是 r2 承诺的事件内错误边界尚未覆盖整个调用过程。当前夹具没有触发这类复制失败，本结论是条件式源码分析。

最小修订是让 DeliverWs31 的声明和定义都接收 `const Ws31Leave &leave`。事件仍按值拥有 std::function，调用时只绑定引用。旧模板分别推导函数参数 U5 与存储参数 T5，[TypeTraits](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/core/model/type-traits.h:21)对当前 T5 保存值，因此可保留事件所有权并避免此处复制。或者在事件边界内完成所有可能抛出的复制；没有必要修改旧模拟器。

修订后还须由新冻结版本的编译与夹具确认 const 引用参数的模板适配。事件内部执行、leave 调用和异常保存的检查继续保留。此建议没有授权任何编译或运行。

## 2. C1～C5 与晚绑定复核

| 项目 | r2 静态判断 | 仍需承担的验证 |
| --- | --- | --- |
| C1 精确类型 | [Bind 第 156～158 行](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-channel.h:156)同时比较 C++ typeid 与 ns-3 TypeId。夹具构造完整双端 UnregisteredOverride，确认其继承旧 TypeId，再要求拒绝。原子类绕过问题已在源码层修正。 | 当前类为多态类，typeid 用法成立。父源已有 dynamic_cast，waf-tools/cflags.py 第 26 行选 gnu++11；未发现配置源码添加禁用 RTTI／异常的选项。r2 实际构建和最终 flags 仍未验证。 |
| C2 身份域 | ValidateIdentity、Register 与 EncodeIdentity 都约束 `0..65535`；编码器在序列化前检查。合法边界和两个旧 tag 别名示例均已写入，别名包没有发送。 | 只解决受控编码器域。外来 65536 仍可截为已登记 0，-1 仍可截为 65535。真实 G1、每个生产者、协议来源及跨代唯一 ID 未接入；C2 不能标为完整解决。 |
| C3 大小 | [编码器第 134～135 行](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-channel.h:134)先设 ID 和 flow_size，再 AddPacketTag。Tagged 固定传入 8 B，原始别名示例也初始化大小。基线类体和序列化实现未改。 | 新夹具的未初始化读问题已在源码层修正，往返断言未运行。 |
| C4 函数体内异常 | Deliver 的 try 包住 guard、Receive 和 leave；捕获后保存首个异常、锁存、Stop 并正常返回。由此进入的 Receive／leave 异常能够让旧事件循环继续 Unref。 | 函数调用前的按值复制仍须按 R2-01 修订。完整对象回收和任意生产事件的异常边界不由此保证。 |
| C5 部分记账 | [Enter 第 93～104 行](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-channel.h:93)覆盖 ledger Enter、history 和 open；异常保存到 State。Healthy 在 Pending、Register、Bind、Finish 路径阻止成功。缺 tag／未知请求等记账前拒绝仍可恢复。 | 阶段受控抛出不等于真实 allocator 耗尽。必须保留此证据边界。 |
| C5 调度与动画 | [TransmitStart 第 124～142 行](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-channel.cc:124)捕获调度表达式、回调复制及动画异常，保存 channel 首个失败。动画失败后的已安排事件先见失败位，不再调用 Receive。 | 受控调度例只在 pending 增加后、实际调度前抛出；不证明调度器内部插入失败的恢复或引用回收。 |
| C5 原子 Bind | [第 173～182 行](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-channel.h:173)先构造回调并完成 vector push，再以 std::function::swap 和 owner 赋值提交。Ptr 的复制只增加引用。当前提交阶段没有可见分配点。 | BEFORE_BIND_COMMIT 例发生在 vector push 前，证明该边界的无绑定修改与重试预期；未测试真实回调分配／vector 扩容失败。 |
| I1 绑定时序 | 默认分支在调度前设置 EverTransmitted；观察分支在 Enter 成功后、pending／调度前设置。Bind 拒绝已用 channel，覆盖默认事件已安排、已返回和正常 Finish 后重绑。未发送的空会话仍可拆卸重绑。 | 新用过标记是实际状态写入，增加默认成本。正常两代必须保持同一会话；全局 G1 仍须证明绑定范围完整。 |

RethrowFailure 优先返回 State 失败，否则返回 channel 保存的异常。动画原始 runtime_error 不会被随后 guard 的 logic_error 覆盖。这里确认的是代码路径；现有 Refuse／Fail helper 只核对异常大类。建议后续对 Receive、leave 和动画分别核对具体消息或唯一标识，防止把一般失败误当作原始异常已保留。

## 3. 全部夹具分支的静态推导

下表是未执行的预期，不能作为原始计数。12 个独立仿真分段分别调用 Destroy；其中有些故障段没有调用 Run。

| 分支 | 从代码推导的结果 |
| --- | --- |
| default-off | 一次原包交付，目的 context，13 ns；新增用过标记不新增事件。 |
| 正常观察与嵌套 | 13／13／16 ns 三次返回，serial 1／2／3。Receive 内 pending 为 2／2／1，嵌套入账峰值为 3；先 leave 后减 pending。输入拒绝均在记账前。Finish 成功后，用过 channel 重绑拒绝。 |
| Receive 抛出 | 保存 logic_error，Stop 后 Run 正常返回；open=1、token=1、History 未闭合，Pending／Finish 拒绝。 |
| 默认发送后的晚绑定 | 调度前已经置标记，发送后立即 Bind 拒绝；旧直接 Receive 仍执行一次，执行后 Bind 继续拒绝。 |
| AFTER_LEDGER_ENTER | token=1、history=0、open=0，State 失败；channel 的 pending 尚未增加，Finish 仍因 Healthy 拒绝。 |
| AFTER_HISTORY_APPEND | token=1、history=1、open=0，State 失败；Finish 拒绝。两种例都没有伪造 RECEIVE_RETURNED。 |
| BEFORE_BIND_COMMIT | hook 清除自身后抛出，回调仍是局部对象，channels 尚未 push。会话健康且无 token，原会话重试和未用对象的下一会话 Bind／Finish 均可成功。 |
| pending 后、调度前 | open=1、token=1、channel 失败，没有安排交付；Finish 拒绝。并未实际耗尽 scheduler。 |
| 实际动画 trace 异常 | 已安排事件，动画 callback 抛 runtime_error，channel 保存首错。Run 时包装 guard 失败并 Stop，Receive 调用数应为 0；open=1、token=1，RethrowFailure 仍是原 runtime_error。 |
| leave 关闭前异常 | Receive 已正常返回，但 token 尚未关闭。hook 抛 runtime_error，失败锁存；open=1、token=1，History 的闭合证据仍为 false，Finish 拒绝。 |
| 空闲 owner 丢失 | session 销毁后，channel 的回调仍持有 State，owner 标识仍有效。下一会话 Bind 被占用状态拒绝；没有事件、闭合或正常 Finish。 |
| 在途 owner 丢失 | 事件及 channel 回调保留 State；Receive 的 action 没有捕获 session。交付可正常关闭一个 token，下一会话仍不能接管，也没有正常 Finish。 |

动画通过 TxRxQbb 的真实 trace 接口连接；其余部分失败主要使用边界 hook。两者必须分开报告。默认与观察的正常成功路径均保持原 Packet Ptr、context、txTime + delay 和“先调度、后动画”的顺序。

## 4. 源码恢复与生命周期边界

独立删除新增观察分支、包装、标记、声明和 include 后，channel cc／头文件均精确恢复父 Git blob。删除 tag include guard 后也精确恢复原文件；比较时只把工作 CRLF 规范为 LF。两个新 guard 在 src／scratch 中没有其他定义。

State 没有直接持有 channel 或 device，回调没有捕获已销毁的 session。原 Qbb device／channel 强引用关系仍存在；修正当前事件 Unref 路径不代表 Destroy 会释放全部对象。owner 丢失用例也只证明预期回调存活和禁止接管，不能作为正常关闭、资源回收或网络排空证据。

当前 Finish 只关闭自有观察会话。它不清 held copy、真实设备队列、端点状态、保存 QP、saved RX、完成历史或交换机状态。生产 Receive 的早返回和正常转发也未由这些替代 Receive 用例覆盖。

## 5. 继续必做的接线与验收

主应先修 R2-01 并冻结新字节。异常保留断言可同时加强。然后继续真实 switch 纯读、完成回调／saved RX、history 清理、实际解析 G1、所有身份生产者与共享控制状态。当前逐流观察器不能自动处理无 tag PFC，也不能跳过共享包后宣称整体排空。

真实两代网络正反例、独立 C1 V0、三候选匹配消融、业务／背景双侧效果及状态／运行成本继续必做。r2 增加的标记、异常槽位、成员和回调都有成本，静态恢复不表示零开销或默认网络已验。Ofan、WS-29、旧控制器及旧矩阵没有启动。

## 6. 本节点参考借鉴复核

从候选 README／reading-log 复核 DiffFlow v1 和 Flowcut v2 的技术分析及核验记录；六份记录与 r1 快照哈希相同。本轮重新核对两篇的迁移边界，没有新增候选或论文效果结论。

DiffFlow（arXiv:1604.05107v1）的借鉴点仍是区分类别识别、控制生效和真实传输覆盖。其简化 Java 传输和分类独立队列，不能替代本项目真实 G1／RDMA 证明。Flowcut（arXiv:2506.21406v2）提醒应明确在途闭合、暂停和状态成本；其 ACK 字节计数与本适配器的事件返回不同，SST／Slingshot 条件不能外推成跨代复用或双侧收益。

两个固定 PDF 的身份沿用 r1 已核哈希，版本和适用限制列于[review JSON](endpoint-channel-local-review-r2-review.json)。本节点只作方法复核，不修改文献库，不重跑作者实验。中文成稿沿用本对话已读的[阮一峰原规范](https://github.com/ruanyf/document-style-guide)及六章进行复查。

## 7. 交付与释放

本地静态复核范围完成，R2-01、C2 的生产范围及全部动态验证未完成。证据、锚点和计划七项问题的对应见[review JSON](endpoint-channel-local-review-r2-review.json)及[QA](endpoint-channel-local-review-r2-qa.json)；续接入口见[九节交接](endpoint-channel-local-review-r2-handoff.md)。

五文件只读约束已[显式释放](endpoint-channel-local-review-r2-guards-released.json)。没有持有更广泛约束，没有后台执行者，也没有新增执行授权。本轮 SSH／远端、同步／部署、编译、测试／夹具、网络、科学源／main 编辑、提交及推送均为 0。
