# WS-31 channel 静态问题与修订设计

日期：2026 年 11 月 1 日。状态：主已核对三项具体源码问题；唯一副恢复未完成的只读审查，五份 WIP 保持不变。本文件是修订设计，不是已修复或已执行结果。

## 1. 类型准入

当前 Bind 仅比较 GetInstanceTypeId 与 QbbChannel 的 TypeId。固定父源的 CreateObject 通过 T::GetTypeId 设置对象类型；未自行注册 TypeId 的 C++ 子类可继承基类静态 GetTypeId，却覆写 TransmitStart。因此，现有类型检查无法兑现“拒绝所有未知覆写类”的契约。

修订拟同时检查精确 C++ 动态类型，使用 `typeid(*PeekPointer(channel)) == typeid(QbbChannel)`，并核实际编译配置启用 RTTI。新拒绝夹具应构造一个不自行注册 TypeId、覆写 TransmitStart 的子类，证明继承 TypeId 也不能准入。这里的例子是源码反例，尚未运行。

## 2. 编码前身份范围

FlowIDNUMTag 的接口是 int32，但 Serialize 使用 WriteU16，Deserialize 使用 ReadU16。Packet::AddPacketTag 会进入 PacketTagList::Add 并实际序列化；Peek 同样实际反序列化。于是，编码前的 -1 与 65536 分别变为 65535 和 0。当前“负数标签拒绝”夹具实际只是拒绝未登记的 65535；在 flow 0 已登记时，高位身份可混同为 0。

不修改既有标签类体或扩宽全局编码。拟为本 fixture 明确建立 0～65535 的身份域：登记和编码器均在编码前校验；后续 G1 从真实解析输入核对全部请求身份唯一、位于范围内，并核对所有生产构包路径只取这些身份。高位与负数拒绝须在编码前发生。

已经截断的 tag 无法由 channel 端重新判定原整数。必须保留这个边界，不能将新输入门写成“可识别任意已编码别名”。若后续真实夹具无法证明构包身份来源受控，应停止该方案，另行设计完整身份传播，不能仅放宽观察器。

## 3. 标签大小字段

既有 FlowIDNUMTag 构造函数只初始化 flow_stat；Serialize 还读取 flow_size。新 Tagged helper 只设置 ID，会读取未初始化字段。修订只在新夹具编码器调用 SetFlowSize 设置明确值，保留基线标签类体原样。新增拒绝／正常包均通过同一个受控编码器。

## 4. 事件异常与失败状态

固定 DefaultSimulatorImpl::ProcessOneEvent 先移除事件，再调用 Invoke，最后调用 Unref。当前包装重抛 Receive 异常，会越过这个 Unref；主不能以 Destroy 证明这个已移出调度器的事件及其引用已释放。

拟在观察包装内部捕获异常，保留未闭合 token、正 pending、失败锁存和异常对象，调用 Stop 后正常返回，让原事件引用按框架顺序释放；Run 返回后再由 fixture 查询失败和原异常。不得在捕获中关闭 token，也不得将 Stop／Destroy 当作排空。需核对旧模拟器 Stop 的实际语义后才能落实。

适配器的登记前校验拒绝仍可恢复；账本 Enter、历史／open 分配、调度或动画 trace 等发生在变更之后的异常则必须锁存失败，禁止 Finish 和重新认证。修订需要区分这两个区间，不能将所有无效输入一律毒化，也不能将半完成变更误作纯拒绝。

## 5. setup 与已有事件

现有 pending 只统计观察路径。如果默认路径已经安排过 Receive，再 Bind 会遗漏旧事件。后续需将“所有 channel 在任何发送之前完成绑定”变成实际可核对的准入条件。优先考虑 channel 的一次性发送标记，并在 Bind 中拒绝已发送过的对象；该标记对默认发送的额外写入必须列入成本，不宣称零开销。

同一观察会话可登记第二代请求，保持到最终 Finish；不得靠拆卸并换 owner 遗忘前一会话。是否允许空会话解绑后重绑，由完整审查的最小修复结果决定，不能让已使用 channel 绕过 setup 门。

## 6. 执行顺序

先接收唯一副的完整只读审查，主核对全部来源与具体发现，再修改五份冻结 WIP。旧 checkpoint 保留未完成身份，原 WIP 字节不覆盖。修订后重新记录源码、契约和夹具预期，再接续 switch／完成回调／history／G1 接线。

尚未授权任何 C++ 编译、夹具、网络或远端动作。旧成功 ID 与已验 8cd 对象预检保留原范围；这些新 WIP 问题不记为旧实验失败，也不产生候选效果结论。
