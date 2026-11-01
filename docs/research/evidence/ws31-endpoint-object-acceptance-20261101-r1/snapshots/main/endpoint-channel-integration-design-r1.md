# WS-31 原交付事件 token 与端点接线设计

日期：2026 年 11 月 1 日。状态：固定 8cd 源码上的接口与验收设计；尚未实现。当前对象预检进行中，主不修改受约束的独占源码。

## 1. 原始调用顺序

`QbbNetDevice::TransmitStart` 先设置 BUSY 和当前包，按 `txTime + interframeGap` 安排 TransmitComplete，再调用 channel。`QbbChannel::TransmitStart` 按 `txTime + delay`，在目的节点 context 中直接安排 `QbbNetDevice::Receive`；随后调用既有动画 trace。

Receive 有 link-down、物理错误、PFC、switch 转发和 NIC 回调等返回路径。完成 ACK 可在 NIC 回调中触发 QpComplete；后者先取消 QP 事件、调用完成回调，最后删除 TX 映射。事件被判 expired 也不能证明这些调用栈已返回。

所以 token 必须表示一次实际定向链路交付，并在整个 Receive 返回之后闭合。读取映射或 EventId 不能代替这个顺序证据。

## 2. 拟定接口

每个 channel 保存默认空的 enter／leave 回调对及观察路径的 pending 计数。仅新的端点夹具通过受实际上下文门保护的入口安装；普通代码不安装回调。

| 接口职责 | 拟定输入与行为 |
| --- | --- |
| enter | 只读包、源设备、目的设备；返回唯一非零 serial。夹具检查 FlowIDNUMTag、登记的 flow_id／generation、UID 和四字段定向链路，再调用账本 Enter |
| 安装／卸载 | enter 与 leave 须同时存在或同时为空；pending 非零时拒绝改变绑定，避免在途凭据换接收者 |
| 原事件包装 | 用一个静态包装替代原来的一个 Receive 事件，携带 channel Ptr、目的设备、原 Packet Ptr、serial 和固定 leave 回调副本 |
| leave | 包装调用 Receive 返回后，减少 channel pending，再用该事件携带的 serial 闭合账本；校验 kind=CHANNEL、reason=RECEIVE_RETURNED |
| pending 读取 | 逐 channel 只读报告。fixture 的 channel 集合来自完整冻结拓扑；同 channel 经两个设备可见时只计一次 |

静态五参数函数可对应本仓库 Simulator::ScheduleWithContext 的现有五参数重载。接口实现前仍须用真实旧 NS-3 编译确认参数复制与调用语义。

## 3. 必须保持的行为

默认空回调分支继续执行原来的直接 ScheduleWithContext，保持目的 context、延迟、包指针和动画 trace 顺序，不增加事件。启用后也只替换一个交付事件，不在接收前后额外安排“闭合事件”。转发产生的下一跳 token 在当前 Receive 内登记，当前 token 到返回后才闭合。

serial 随事件携带，不能凭 UID 搜索待闭合项。同 UID、同链路重复发送、多跳发送和 held copy 分别保留独立 serial。包身份缺失或未知归属时停止认证；不能静默跳过应追踪数据／ACK／NACK。共享控制包的覆盖按实际上下文另行规定，不能强塞进任意 flow_id。

若 Receive 或观察回调抛出异常，保留失败和未闭合凭据，不在清理中强行扣账使之归零。Simulator::Destroy 不能用来取得排空证书；正常认证须在 Destroy 前检查 token、channel pending、真实队列、当前发送器及事件。

增加回调成员和每次发送的分支有实际内存／运行成本。默认行为回归只验证功能兼容，不证明这些成本为零。后续效果与成本协议须明确观察配置及对照条件。

## 4. 完成回调与检查事件

新端点夹具在完成回调内保存即将退出的真实 RX 对象，标记 ACK_COMPLETE，并保留原 FCT 与 RX 删除行为。捕获实际 driver／HW／NIC 绑定在 setup 完成，不在纯度指纹区间临时调用 GetObject。

端点退役检查放在独立的后继检查事件中。该事件只能在原 Receive、QpComplete 及 token leave 调用栈展开后读取；不在完成 trace 中直接退役、清理或创建第二代。检查事件属于新夹具的观测行为，不能由它推定默认关闭时也存在该事件。

## 5. 交换机与历史状态

现有 `ResetWs30V13Tuple` 函数按指定四元组擦除 Q12 pin、WS-31 pin、预测预算和 quota 条目，函数本身不是旧控制器。后续仅在新协议允许且源审查通过时复用这个已核接口；旧 lifecycle／composition 控制器继续关闭。

真实快照还需逐 switch 读取上述目标条目。预算与 quota 需窄的 const 查询，不能为观察而调用 Expire、Pressure 或 Reset。清理前后分别保存原始收据，观察与动作分开，最后才补 SWITCH_STATE 覆盖位。

Quota 的类别 seen／last 是共享活动历史，Erase 目标条目不清它们；C1 observed memory 也是单独的端口历史。不得把目标四元组清理说成“交换机全部状态为零”，更不能为了证书清除不属目标的共享状态。后续明示观察目标条目、共享状态和累计统计的不同含义。

两侧 akashic 完成历史只在真实网络排空后按已核所有者定点处理；原账本历史保留。旧完成 QP 留在真实组内，第二代追加新槽位，不 Clear 后复用旧 finished 位。第二代 Begin 前再取同一事件内的新旧代完整快照，核 actual packed key、所有权、映射、组、队列、事件及历史。

## 6. 最小验证顺序

1. 等当前对象预检终态并经主验，确认显式释放后实现 channel 与 switch 接线。
2. 新源先验证默认关闭分支与原入口的源码对应，以及接收包装对所有实际返回分支的闭合。缺身份、重复闭合、错 kind、在途改绑定均有拒绝。
3. 在实际解析的网络上下文通过 G1，再按新固定源／输入／ID／资源门，依 C1 → C2 → C3 运行必要的两代正例与明确拒绝例。当前不授权任何这些调用。
4. 正例完整保留两代原需求、放行、实际最终完成、路径、队列、事件、token、历史和清理收据。held 未入网副本的丢弃只证明持有凭据释放，不证明原生旧包接收隔离。

独立 V0、业务批次／背景尾部双侧效果及状态／运行成本仍由后继协议承担。该设计没有新实现、构建或网络结果，也未形成新组合基线。
