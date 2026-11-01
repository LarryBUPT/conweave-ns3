# WS-31 端点证据账本本地独立审查

日期：2026 年 11 月 1 日。审查对象为固定 HEAD `1f917f44fcfb88e61f3ad22c5cc75fa3a06b6c0e` 上两份未跟踪的 WIP，依据[审查计划](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/main/endpoint-ledger-local-review-r1.json)执行。本轮仅阅读本地文件和 Git 信息，交付静态审查结论；编译、测试执行和网络运行均为 0。

## 1. 结论与证据范围

可保留这版可移植账本作为后续实现的基础。独立 serial、不可复用的 flow_id、逐代历史和状态顺序已有明确约束。真实端点复用尚不具备验收条件：接入前须落实实际键占用门、完成历史处理、队列组安全策略及绑定真实对象的排空收据。以下 R1～R3 是接入要求，其中 R2 发现了不能直接沿用的队列组清理行为；R4 是建议补强的 token 边界。它们不表示本轮已观察到网络失败。

两份 WIP 的前后 SHA-256 与计划一致，HEAD 和 Git 状态未变。[机器审查记录](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-local-review-r1-review.json)保存完整哈希、源码版本和条目，[QA 记录](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-local-review-r1-qa.json)保存交付检查。

## 2. 可保留的证据逻辑

- [请求登记](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-ledger.h:64)拒绝重复 flow_id、非零首代、跳代及未完成清理的同 tuple 复用。旧 Entry 不删除；generation 可由 token 的唯一 flow_id 回查。原业务标签、字节数及需求时刻在登记后保持。
- [发送与完成](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-ledger.h:81)要求先 Launch，再按精确累计 ACK 字节数完成。退役、排空、交换机清理依次推进；Retire 本身允许尚有在途 token，CertifyDrain 才要求它们全部闭合。
- [传输凭据](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-ledger.h:86)每次 Enter 分配新 serial。同 UID 的多跳发送、同一链路上的多次发送及 held copy 均可独立计数。Close 校验 serial、flow_id、UID 和有向链路；错误身份、未知或重复闭合在修改账本前被拒绝。Conserved 复核存量 token 与累计进出账。
- [测试的边界说明](E:/研/毕业论文/workspace/ws31-candidates-implementation/tests/ws31_endpoint_ledger_test.cc:50)准确说明 held copy 是未送入网络的测试副本，其显式丢弃不构成接收端旧包拒绝证明。输出字符串中的 PASS 是待执行代码，不能记为本轮测试通过。

## 3. 接入前必须处理的事项

### R1：按实际资源键检查占用，不能只查完整 tuple

位置：[完整 EndpointKey 与 current](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-ledger.h:14)、[TX 键](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:254)、[RX 键](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:382)。

账本按 `(sip, dip, sport, dport, pg)` 区分请求。实际 TX 键为 `(dip << 32) | (sport << 16) | dport | pg`，PG 与目的端口的位重叠。固定同一对主机、sport 为 1000、PG 为 3，dport 为 100 和 103 的两个完整 tuple 不同，却有相同 TX 键，因为 `100 | 3 == 103 | 3`。按 ReceiveUdp 的参数翻转关系，这两个请求也会在接收端碰撞：RX 高 16 位使用 `原 dport | pg`，低 16 位使用原 sport。

此外，[C1 键](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-budget.h:16)和[C3 键](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-quota.h:13)只有四元组，没有 PG。仅 PG 不同的请求不能被当作拥有独立交换机清理域。

最小处理：适配器按源／目的节点、真实 TX/RX packed key 和交换机四元组登记所有者 flow_id／generation；创建与清理前逐项校验。最小夹具也可先冻结输入为无别名并拒绝冲突。冲突拒绝必须发生在 AddQueuePair 等实际副作用之前。无需为本次夹具改写基线键格式或候选策略。补充不同完整 tuple 却共享真实键的拒绝例，核对旧映射和交换机表均未变化。

### R2：明确队列组保留策略，避免 Clear 后复用旧完成位

位置：[队列组构造、追加与 Clear](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-queue-pair.cc:220)、[完成位访问](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-queue-pair.h:239)、[调度器先检查完成位](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-net-device.cc:116)。

Clear 只执行 `m_qps.clear()`；AddQp 只追加向量；完成位仅在构造时清零。若第一代的索引 0 已被调度器标为 finished，清空向量后第二代又占索引 0，GetNextQindex 会在读取新 QP 前跳过它。该路径取决于旧完成位已置位，不能宣称每次完成后都会触发，但源码足以说明直接 Clear 后复用不安全。

最小处理优先采用“保留已完成旧 QP、追加新 QP”，记录旧对象仍被引用且 IsFinishedConst 为真。若夹具确需回收，则提供独立、受控的组重置或重建操作，同时处理向量、完成位、调度索引与所有绑定引用，并验证组内没有其他活动 QP。不得对共享活动组整体 Clear。正例必须让第二代真实发送和完成；额外构造旧完成位已置位的分支，才能检验该风险。

### R3：把真实快照、完成历史和最终复用门绑定到同一代

位置：[EndpointSnapshot](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-ledger.h:16)、[退役至清理](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-ledger.h:117)、[Begin 的复用检查](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-ledger.h:67)。

快照是可信调用方参数，这一点已由 WIP 明示，不作为新发现重复指控。尚缺的接入契约是：快照归属哪个 flow_id／generation、哪些真实对象与设备、何时及在哪个回调之后读取，以及每项是否实际读取。数值字段默认 0 不能当作已经测得 0。Begin 目前只读取历史状态，不重新测量真实资源，因此最终创建入口仍需在产生副作用前重新核验，或在一个不可重入的事件中完成核验与创建。

[完成调用顺序](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:1052)是取消 TX 事件、调用完成回调、再删除 TX 映射；[qp_finish](E:/研/毕业论文/workspace/ws31-candidates-implementation/scratch/network-load-balance.cc:658)在回调内删除 RX 映射。只能在回调标记 ACK_COMPLETE。须等外层 Receive 返回、TX 删除完成且对应 token 闭合后，再由后继检查事件取得退役证据；不可在完成回调中直接重建同 tuple。

正常 lifecycle 为 0 时，[RX 创建路径](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:389)仍允许晚到数据重建 RX 对象。故 ENDPOINTS_RETIRED 只是曾取得退役证据，不能永久代表映射为空。Drain、SwitchCleared 和最终创建前须重新读取；若对象复活，保持拒绝并记录、处理该代真实对象，不能清零 token 或依靠状态枚举跳过检查。

[TX 完成历史](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:366)和[RX 完成历史](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:480)会留下 akashic 集合项，再次完成时有“历史项尚不存在”的断言。排空后须由独立 WS-31 夹具按已核验所有者定点处理这些项，保存清理前后收据，保留账本的旧代历史。不要启用旧生命周期控制器。ReceiveAck 先查 live map，只有找不到才查 akashic，故不能把历史残留写成“新 ACK 必然被忽略”；这里的直接风险是完成历史冲突及复用契约缺项。

### R4：建议为不同闭合来源提供类型约束

位置：[Close](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-endpoint-ledger.h:101)、[同 UID 和链路的 channel／held token](E:/研/毕业论文/workspace/ws31-candidates-implementation/tests/ws31_endpoint_ledger_test.cc:27)。

正确传递 serial 时，现有 API 足以精确标识某次占用。它没有验证闭合调用来自 channel 接收还是 held-copy 持有者：二者若误传对方 serial，且 flow_id、UID、链路相同，Close 会接受并按存储的 kind 扣账，Conserved 仍可能为真。这是跨处理器误接线的防护缺口，不是 serial 设计错误，也不是已经发现的网络故障。

建议用类型化 handle，或分别提供 ChannelDelivered／HeldDiscarded（及转交网络）入口，校验预期 kind，并记录闭合原因。接收包装持有自己的确切 handle；禁止按 UID 搜索任意 token 来闭合。补充错误 kind／来源拒绝且账本不变的测试。

## 4. 最小真实接口与取证时刻

以下是接口职责，不要求沿用这些名称。接口只读部分不得出队、推进事件或清表；修改操作另留前后收据。

| 接口职责 | 当前源码依据 | 最低收据与顺序 |
| --- | --- | --- |
| 请求与物理键所有权 | RDMA GetQpKey、GetRxQpKey；C1／C3 四元组 | 节点、两侧 packed key、四元组、PG、flow_id、generation；创建及定点清理前核验 |
| 两端映射与旧对象 | m_qpMap、m_rxQpMap、m_flow_id | 在删除前保存旧 TX/RX Ptr；删除后记录实际查询结果及对象身份，不能只查新 map |
| QP 事件 | TX mlx 三个 EventId、m_retransmit；RX QcnTimerEvent | 对保存的旧对象读 IsRunning；本轮 PG／CC／IRN 条件冻结。RX m_nackTimer 是 Time 阈值，不是待调度 EventId；本地搜索未见 QcnTimerEvent 的调度赋值，但仍检查真实对象 |
| 队列组 | GetRdmaQueue、m_qpGrp、m_qps、完成位、IsFinishedConst | 枚举 retained QP、flow_id、完成状态和位图；区分旧代保留与其他活动 QP，采用 R2 的策略 |
| 实际队列 | GetQueue()->GetNBytesTotal；GetRdmaQueue()->m_ackQ | 覆盖夹具全部相关设备的数据／反馈队列；记录设备清单和计数。RdmaEgressQueue::GetNBytes 返回 QP 的 GetBytesLeft，不能代替物理排队字节 |
| 序列化和延迟事件 | m_txMachineState、m_currentPkt、m_nextSend、m_resumeEvt | 通过默认关闭的只读接口取状态；空队列仍须检查当前发送、pacing 和相关 PFC 事件，冻结无背景夹具的全局静默范围 |
| 链路与接收包装 | QbbChannel::TransmitStart；QbbNetDevice::Receive | 每次实际发送分配 handle，随原交付事件携带；完整 Receive 返回后才闭合，覆盖正常返回及丢包分支。转发可先登记下一跳 token；接收中的尾 ACK 不能提前令账面排空 |
| 历史和交换机清理 | 两侧 akashic 集合；真实 C1／C3 清理接口 | 排空后定点处理 transport 历史及需要处理的组，再执行真实交换机清理；记录前后值，最后复查端点／token／队列及物理键所有者 |

关键锚点：[队列字节的实际含义](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-net-device.cc:169)、[链路交付调度](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-channel.cc:100)、[Receive 的返回分支](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-net-device.cc:380)、[序列化调度](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-net-device.cc:517)、[QP 事件字段](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-queue-pair.h:88)。默认关闭时保持原事件、时延、上下文及包行为；不要额外安排一个“闭合事件”来替代原接收调用返回。

标签关联方面，[发送侧](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:1148)在标签缺失时附加 FlowIDNUMTag，[ACK／NACK 构造](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:621)只在输入包有标签时复制。主设计把后者写为“无条件复制”，应改成按条件复制，并在夹具观测边界校验应追踪的数据／反馈包都有合法身份；缺失时拒绝认证，不能静默漏账。无需把 PFC 强行归入某个 flow_id，应通过设备／事件范围另行覆盖。

## 5. 需求时钟与测试补齐

Begin 保存 demandNs，Launch 保留独立时间，已有路径不会主动把源端等待从 FCT 中删掉。但 `demandNs >= 旧代 cleanup` 限定了当前合同：需求早于清理、清理后才放行的请求无法原样登记。若夹具预定第二代需求在清理后，这一限制可保留并明示；若要承接已到达等待的需求，则须分别登记需求与准入时刻，不能把 demand 改成 cleanup。本轮不要求扩展候选策略。

Time 当前保证每个 Entry 的成功变更时刻不倒退；返回 false 的快照检查不更新 lastNs。因此一次 100 ns 的失败检查后，90 ns 的操作仍可能通过时间门，只要此前成功变更更早。真实接入应统一使用 Simulator::Now，并在收据层保留观察顺序；若要宣称账本校验所有观察时间，则另记观察时钟并补反例。

优先补齐以下覆盖，均为后继要求，本轮没有运行：

1. 第二代从 Launch 到最终清理的完整闭环，保留两代 demand／launch／finish、ACK 字节及旧代 token 历史；加入旧组完成位已置位的分支。
2. 多 tuple 交错、实际键别名及共享组中其他活动 QP；拒绝操作前后真实状态相同。
3. 错误 UID、未知 serial、同 UID 同链路的多个 channel token、channel／held 闭合来源错配；明确 held 丢弃与交付的不同结果。
4. ACK_COMPLETE 和 ENDPOINTS_RETIRED 后新 token 进入、晚包导致 RX 复活、过期或错代快照，以及最终创建前的再次核验。
5. 真实夹具验证回调展开顺序、全部 Receive 返回分支、实际 map／事件／队列／当前发送、标签缺失拒绝，以及默认关闭路径不改变行为。

[当前测试尾部](E:/研/毕业论文/workspace/ws31-candidates-implementation/tests/ws31_endpoint_ledger_test.cc:69)只 Begin 第二代，没有 Launch 或完成它。其 quiet 快照为手工设置的布尔值和默认零值；它覆盖的是账本拒绝条件，尚未测量任何真实端点或排空状态。取消／失败请求没有终态分支；当前合同可限定为完成型夹具，后续若接取消必须单独设计，不能伪造 ACK_COMPLETE。

## 6. 本节点的参考借鉴复核

从[候选索引](E:/研/毕业论文/参考文献/候选/README.md)和[累计阅读记录](E:/研/毕业论文/参考文献/候选/reading-log.md)定位 DiffFlow，复核[技术附件](E:/研/毕业论文/参考文献/候选/papers/diffflow-2016/analysis-technical.md)与[核验记录](E:/研/毕业论文/参考文献/候选/papers/diffflow-2016/verification.md)。固定阅读版本为 arXiv:1604.05107v1，6 页；本节点没有重新阅读会议最终正文或运行作者模拟器。

具体借鉴是先完成中间规则再启用源端行为的顺序约束；适用于本项目将“完成、退役、排空、清理、下一代启用”分别留证。该文未详述规则安装确认、失败、结束检测和回收，因而不能为本项目的复用证书背书。DiffFlow 用抽样识别长流并启用喷洒，本项目这里审查实际 RDMA 请求的端点与观测账，两者机制不同。其简化传输和独立队列结果不外推为本项目的 RDMA 正确性、MoE 批次或背景 P99 收益。本轮未引入新机制。

## 7. 本次交付与承接

本地审查交付完成；实现、真实端点夹具和网络验证仍未完成，承接入口为主设计及本报告 R1～R3、测试清单。没有修改 WIP、主设计、科学源码或历史实验；没有创建脚本、编译或执行测试，也没有远程动作。后继修改由主对话落实并重新冻结源码，再按已授权范围开展审查和验证。
