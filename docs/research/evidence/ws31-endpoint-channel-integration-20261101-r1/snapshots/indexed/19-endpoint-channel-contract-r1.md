# WS-31 channel 原交付事件接线契约

日期：2026 年 11 月 1 日。状态：首版 WIP 已冻结，待唯一副本地只读审查；未提交、编译或执行。

## 1. 当前范围

在已验 8cd 上新增默认关闭的 QbbChannel 观察路径、fixture 专用账本适配器和独立 channel 夹具。真实交换机纯读、端点完成回调、历史清理、实际解析上下文 G1 与两代传输仍为后继必做工作。本次不授权远端调用或任何 C++ 编译／运行。

此前[设计](endpoint-channel-integration-design-r1.md)保留原字节。本契约修订关闭顺序：完整 Receive 返回后，先由事件携带的 leave 回调闭合账本，再减少 channel pending。这样 leave 抛异常时 pending 仍为正；失败锁存位同时阻止正常读取与卸载。不能在 Receive 内或异常处理中取得零计数排空证据。

## 2. 五项源码变化

| 路径 | 作用 |
| --- | --- |
| `qbb-channel.h` | 私有 enter／leave、owner、pending、失败位和静态包装声明；只允许窄 friend 适配器绑定 |
| `qbb-channel.cc` | 默认分支保留原直接 ScheduleWithContext；观察分支用一个五参数事件包装替代原交付事件 |
| `ws31-endpoint-channel.h` | shared_ptr 持有账本和记录；登记 flow_id／generation，逐事件保留 serial、UID、定向四字段链路、channel、时刻与目的 context；显式 Finish |
| `flow-id-num-tag.h` | 仅添加 include guard，类体与接口不变，防止 network-module 与适配器共同包含时重复定义 |
| `ws31-endpoint-channel-test.cc` | 新 channel 工程夹具，使用替代的虚函数 Receive 检验包装边界；不调用生产 NIC／交换机接收路径 |

完整路径、工作字节哈希、原 WIP 副本和固定父源依据见[主来源审计](evidence/endpoint-channel-wip-source-audit-r1.json)。删除新增观察块后，原 channel cc 与头文件精确恢复父源；删除 include guard 后 tag 头文件精确恢复父源。这是静态对应检查，不是默认网络行为或成本验收。

## 3. 身份、生命周期和拒绝

观察路径保持原 Packet Ptr、延迟、目的 context 和动画 trace 的相对顺序，一个交付事件仍对应一个交付事件。serial 由账本分配并随事件传递，不从 UID 反查；相同包多次交付仍各有记录。Receive 内同步产生的下一跳 token 先登记，父 token 到整个虚调用返回后才关闭。

适配器只接受完整且未占用的精确本地 QbbChannel，拒绝 MPI／未知覆写类、已有 owner、未闭合交付与失败状态。包必须有非负 FlowIDNUMTag，flow_id 须已登记到同一账本 generation，实际定向链路须等于绑定时的正向或反向链路。返回时核对原 serial、请求、UID、链路、generation 和目的 context，并以 CHANNEL／RECEIVE_RETURNED 关闭。

共享 State 不持有 channel 或 device；回调不捕获 fixture 的裸 this。事件持有 channel Ptr 和 leave 副本；即使 fixture 对象提前销毁，账本与凭据不会因悬空回调丢失。析构不伪造 Finish；未显式 Finish 的绑定保持至隔离 fixture teardown，不能当作正常关闭或排空。

Finish 先检查全部自有 channel 的 pending、失败位和自有未闭合记录，再统一拆除回调。它不清账本历史，也不处理 held copy 或端点状态。后续网络证书仍须检查全部账本 token、设备、队列、映射、保留 QP、交换机及完成历史。

## 4. 工程夹具预期

首段关闭观察，直接 channel 发送到替代 Receive，核原包、13 ns 到达和目的 context。第二段观察同一个包的两次正向交付，第一次 Receive 内再发一次反向交付：三个独立 serial，闭合时刻 13／13／16 ns，Receive 内 pending 保持非零。

夹具另列重复／错代登记、未完成 channel、MPI channel、已有 owner、缺失／负数／未知标签、错误源、在途 Finish／重绑、Receive 内 Finish、重复 Finish 及 Receive 抛异常后的读取／Finish 拒绝。异常段须保留一项未闭合凭据，Destroy 后也不得凭清理将其记为已闭合。

这些都是待运行预期。夹具真实调用 Simulator 事件循环和 QbbChannel，但替代 Receive 不解析生产包、不建立真实 RDMA QP，不能称为自然端点退出、完整网络正反例或算法效果。

## 5. 审查与后继门

唯一副先按[只读计划](endpoint-channel-local-review-r1.json)核对五份 WIP、固定父源、旧 NS-3 五参数调度模板、虚调用与 Ptr 生命周期、异常和 owner 语义，确认夹具逐项预期可实现。审查期这五文件保持字节不变；副只写 independent 目录，不改源和主报告。

审查完成后由主修复必要问题，再决定是否与 switch／回调／G1 接线共同冻结新源及工程计划，避免对未进入网络接线的版本反复全量构建。正式默认回归、真实 Receive 分支、两代网络、独立 V0、三候选业务／背景双侧效果及状态／运行成本继续承担。新增成员、分支与回调具有实际成本，默认功能兼容不能解释为零开销。
