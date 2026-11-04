# WS-31 switch 探针首版静态审查

日期：2026 年 11 月 1 日。结论为 **FIX REQUIRED：1 项 P1、1 项 P2**。新查询接口的只读实现和四元组键对应成立，但端点与 switch 的读取来源、接口绑定尚有缺口。本轮没有编译、运行或测得 mask 255 证书。

固定父源为 `8cd1ba69469bf80143d5c89edc17fa72611018e8`。九份受审 WIP 匹配计划及主封存，计划 SHA-256 为 `728a26f076559fd10165798a6d934994ad3c538a2a1a1f5692a19c3f1d485a2c`。本轮复用已接收的 channel r2 分析，只检查其最小差异和新增 switch 范围。所有旧交付保持原样。

## 1. 必须修订的问题

### S1 / P1：端点结果没有绑定同一范围与读取步骤

[Read 第 95～100 行](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-switch-probe.h:95)检查请求、tuple、generation、同纳秒时间、原 mask 127、零 switch 计数和节点数量。它没有把 endpoint 的完整节点／接口范围与当前 switch Scope 绑定，也没有证明端点状态在两次读取之间保持不变。

一个不用伪造 Observation 的静态反例是：先通过真实 EndpointProbe::Read 得到结果 E；在同一仿真纳秒增加某节点的接口；再 Capture 新 switch Scope B。节点数量不变，B 自身也能通过 Validate。Read(E, B) 仍满足 endpoint.nodes 的数量条件，却把未读取新接口的旧端点结果补成 mask 255。

另一个反例不需要改变拓扑：端点读取后、switch 读取前，在同纳秒向实际设备队列入包。observedNs 仍相同，旧端点的零队列结果可继续被复制。这里只说明组合检查可能接受陈旧的端点字段；并非声称已运行出排空误认证。独立 ledger／channel 门仍有各自检查。

[EndpointProbe::Observation](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-probe.h:61)只保存值与节点数量；[Scope 验证](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-probe.h:90)在此前 EndpointProbe::Read 内执行，不能由新 switch Read 自动继承为当前读取的来源证明。

最小修订应同时落实共享范围和无交错采样。可提供一个组合入口，在同一冻结对象范围内直接执行真实 endpoint Read 和 switch Read，中间不允许业务修改或调度推进；也可增加可验证的范围来源及状态采样版本。只增加时间或 context 比较仍不足以排除同纳秒、同回调内的修改。若保留当前低层组合函数，应明确限制其证据用途，不能仅凭数量和时间把任意旧结果升级为完整覆盖。

后续拒绝例必须包含“接口变化后重新 Capture switch Scope，再提交旧 endpoint 结果”和“同纳秒队列修改”。这两例与已有 Scope 自身变化拒绝不同。

### S2 / P2：接口归属、实际编号和唯一性未冻结

[Capture 第 84 行](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-switch-probe.h:84)保存设备指针，[Validate 第 59～60 行](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-switch-probe.h:59)只比较节点槽位中的指针。两处均未要求非空、设备 GetNode 等于所属节点、GetIfIndex 等于槽位，也没有跨节点／槽位去重。

父源 [Node::AddDevice](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/network/model/node.cc:108)会设置这两项属性，但它们可随后通过公开 setter 改变。父源 [SetIfIndex](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/point-to-point-net-device.cc:368)和 [SetNode](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/point-to-point-net-device.cc:541)分别写实际字段，节点 vector 的槽位指针不会因此变化。

因此，Capture 后重设某 switch 设备的 ifIndex，当前 Validate 仍会通过。设备重新指向另一个 switch，或同一设备出现在多个节点列表中，也没有被此探针独立排除。上游真实端点读取可能拒绝其中部分情形，不能据此宣称新 Scope 已完整冻结接口绑定；尤其端点基线对 switch 接口没有逐一重验 owner／ifIndex。

主应在 Capture 和 Validate 都检查设备非空、实际 owner／ifIndex 和预期槽位，并在 Capture 做全范围唯一性检查；验证时保持同一唯一绑定。明确 loopback 等允许设备的规则，与共享端点范围一致。查询可使用纯 getter，不需要 GetObject，也不应通过 setter 修正错误绑定。

## 2. channel 最小改动复核

与 r2 封存逐字比较，qbb-channel.h 和 cc 各只有第五参数从值改为 const 引用；ws31-endpoint-channel.h 与 flow-id-num-tag.h 未变。scratch 只新增 FailureMessage helper，并替换 Receive、leave 和动画三项异常检查。

[声明](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-channel.h:143)与[定义](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-channel.cc:153)现在一致。旧 MakeEvent 的 U5／T5 分离推导允许事件仍保存 std::function 值，而调用时绑定 const 引用，消除了 r2 所指的调用前副本构造。Receive、leave 和动画分别核对各自原消息，未把一般 Healthy 失败当作原错误。

R2-01 在源码层已修正，编译／运行仍未验证。本轮没有重复审查未变的正常时序、owner 和故障用例，也没有重跑旧夹具。C2 的真实 G1／所有生产者身份门继续未完成。

## 3. 查询纯度、键与覆盖位

| 项目 | 源码判断与边界 |
| --- | --- |
| Budget／Quota Contains | 分别用 const map::count 返回是否存在。没有 Expire、插入或擦除。过期但尚未清理的真实条目仍被计入。 |
| PortCount | 返回 ports.size，不调用会插入端口的 ObservedMemory::Value。只报告端口记录数量，不是观测字节或负载总量。 |
| SharedActivity | 将 window、seen 和 last 复制到新值，不调用 Active／Expire，不改变共享活动。返回值可独立修改，不应反向影响实际对象。 |
| 布局与行为 | 两份核心头文件只增加非虚 const 方法和嵌套值类型；SwitchNode 只增加 friend。删除新增内容后，三份头文件精确恢复父源，没有新增数据成员或生产 cc 改动。 |
| 节点与角色 | Capture 遍历完整 NodeList，限制角色 0／1，要求角色与 DynamicCast 一致，并使用 typeid 拒绝 SwitchNode 派生类；至少一个实际 switch。Validate 比较节点顺序、指针、ID、角色、接口数和当前 mode。S1／S2 缺口除外。 |
| 读取副作用 | 新探针无 GetObject、Expire、Pressure、Value、Erase、Reset 调用。Node 的 GetNodeType、GetNDevices 和 GetDevice 读取字段／vector；DynamicCast 不作 aggregate 查找。临时 Ptr 引用增减不等于生产状态修改，纯度指纹应在 Capture 后取。 |
| 路由模式 | 33～35、43～46 进入 Q12 路径；36～42 进入 C1 路径；47～50 进入 C3 路径，退化路径仍可使用 Q12 表。当前范围只覆盖这些表；不认证其他对照。 |
| 实际键 | Q12、WS-31 pin、Budget 和 Quota 的生产键均为 sip／dip／sport／dport。新探针按同一顺序构造四元组，不把端点 PG 填入 switch 键。跨 PG 别名准入仍由 ledger 资源门承担。 |
| 目标与全局 | pinnedEntries 累加目标在两张 pin 表中的存在数；budgetEntries／quotaEntries 累加各 switch 的目标存在数。全表大小、observedPorts、sharedActivity 和 liveBorrowed 独立输出，不计入目标归零字段。 |
| 覆盖位 | 输入要求恰好 127、switch 计数为零、同请求／tuple／generation／纳秒；至少一行 switch 后才补 128。对已填 255、错误标记或预填计数会拒绝。补位本身不证明 Quiet、Reusable、token 排空或真实网络完成。 |

生产 [ResetWs30V13Tuple](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/switch-node.cc:1389)定点删除四种目标表状态。它没有清 ObservedMemory 或 Quota 的 seen／last 共享历史。本探针只读取，不调用该方法。后继仅在既定排空门满足后使用清理，并保留无关 tuple 与共享状态；目标清空不等于整个 switch 状态归零。

liveBorrowed 是直接复制的存储计数。若生产路径尚未处理到期，它可能仍为非零；不能把该数值当成按当前时刻重新计算的有效租约数。sharedActivity 的 window／seen／last 也保留实际原值。

## 4. 最小实际对象夹具要求

以下是主后继计划必须包含的未执行项。对象应使用真实 SwitchNode、设备、队列、驱动及保存 TX／RX；先完成全部 setup，再捕获共享范围和取纯度指纹。原对象预检仅作 setup 来源参考，不能把人工填 snapshot 的测试称为真实端点读取。

| 组别 | 最小证据 |
| --- | --- |
| 正常范围与键 | 至少一个实际 switch，并覆盖两台 switch 的累加；实际 EndpointProbe::Read 生成 127，组合读取记录各目标计数与覆盖位。对照生产四元组，明确 PG 不进入 switch 键。 |
| 读取纯度 | 同刻重复成功读取及拒绝读取前后，对 pin 内容、budget 的 entries／deadline／totals／计数器、quota 的 entries／deadline／activity／liveBorrowed、observed 的 bytes／time 及 scope 绑定取独立语义指纹。不能只比较两次 Size 或 Contains。必要时补窄 const 测试快照。 |
| 未命中与到期 | 目标未命中不插入；保留至少一个到期预算／租约，跨到期时刻读取不清理、不扣 liveBorrowed。读取期间禁止用 Pressure／Value／WriteWs30V13State 作为指纹，因为这些路径可能修改状态。 |
| 共享状态与清理 | 目标 K、无关 K2、ObservedMemory 和 borrowed activity 同时存在。合法门之后定点清理 K；K 归零，K2、共享记忆和 seen／last 保留，liveBorrowed 仅按原 Erase 语义变化。再读不得触发额外清理。 |
| 范围拒绝 | 默认 Scope、无 switch、未知角色、角色与对象不符、覆写 switch 子类、不支持 mode、mode 改变、节点／接口数或指针改变均拒绝；补齐 S2 的 owner、ifIndex 和共享设备拒绝。 |
| 来源与新鲜度 | 错 ID／tuple／generation／时间、非 127、预填计数、节点数错误均拒绝；额外加入 S1 的相同节点数新范围、同纳秒接口或队列修改。拒绝不能产生 255 或改动任何表。 |
| 覆盖与排空分离 | 即使补位成功，若实际 token、队列、事件、历史或端点未退出，完整 ledger 认证仍拒绝。数值 255 只能表示当前接口宣称覆盖哪些字段。 |

当前没有上述新 switch 夹具源码或执行收据。零 switch 条目、mask 补位和旧对象夹具通过均不能替代这些验证。

## 5. 保留的后继义务

主先修 S1／S2，并冻结实际对象夹具及新的源身份。实际 G1、所有身份生产者、共享 PFC／ACK/NACK／CNP／重传覆盖、完成回调／saved RX、history、channel／held copy 与真实两代网络正反例继续必做。

独立 C1 V0、三候选匹配消融、业务／背景双侧效果及状态／运行成本未完成，没有形成新基线。本轮不开展 Ofan、WS-29、旧控制器或旧矩阵工作。

## 6. 本节点参考借鉴复核

以候选 README／reading-log 为入口，复核 DiffFlow v1 与 Flowcut v2 的技术／核验记录。DiffFlow（arXiv:1604.05107v1）区分规则安装顺序，但未给完整回收证明；本节点借鉴其“生效顺序与生命周期分别核验”，不据其简化传输和独立队列外推 RDMA 效果。

Flowcut（arXiv:2506.21406v2）的在途计数、状态归属与 ACK 闭合提示：共享状态不能因单个 tuple 结束而擦除，闭合依赖实际协议。其 SST／Slingshot 条件和字节确认方式不等于本探针的表查询，也不支持本项目跨代排空或双指标收益。具体版本和记录哈希见证据索引；本轮没有新增候选或复现作者实验。

中文成稿对照本对话已读的[阮一峰原规范](https://github.com/ruanyf/document-style-guide)及六章检查标题、空格、句段、数值和标点。

## 7. 交付与释放

计划六项问题的分析已完成。详见[review JSON](endpoint-switch-local-review-r1-review.json)、[QA](endpoint-switch-local-review-r1-qa.json)和[九节交接](endpoint-switch-local-review-r1-handoff.md)。本地静态审查完成，修复与实际对象／网络验证保持未完成。

九文件只读约束已[显式释放](endpoint-switch-local-review-r1-guards-released.json)，没有持有更广泛约束或后台执行者，不产生后继执行授权。SSH／远端、同步／部署、编译、测试／夹具、网络、源码／main 编辑、提交及推送均为 0。
