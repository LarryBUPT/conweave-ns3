# WS-31 实际对象快照修订与工程预检契约

日期：2026 年 11 月 1 日。状态：源码与测试已固定，编译及运行待验。本契约承接[静态审查主验](evidence/endpoint-probe-local-review-main-acceptance-r1.json)。

## 1. 本轮要验证什么

使用真实 NS-3 Node、driver、硬件、网卡、队列、QP 与 EventId 对象，验证快照读取和覆盖守卫。对象状态由夹具明确设置，不调用 AddQueuePair，不发送数据，不运行 Simulator::Run。它验证实际对象的读取行为，不验证自然传输完成或网络排空。

原[可移植核心](evidence/endpoint-ledger-core-preflight-main-acceptance-r2.json)的两个输入不变；新夹具不是重跑旧核心。`qbb-net-device.h` 只增加两个窄 friend 和注释，其余生产文件不改；新增 probe 和新 scratch 夹具。没有新增虚函数、对象数据成员或路由动作。默认网络回归不在本轮运行范围内。

## 2. 对 P1～P3 的修订

P1：setup 阶段从实际聚合的 driver 捕获 HW、Node、NIC、egress、物理队列、ACK 队列和保留组指针。观察时验证这些绑定及所选 TX／RX NIC。保存 TX 的完成、保守 pending 和事件始终单独入账；再按对象地址去重汇总，并要求它恰好出现在所选实际保留组一次。缺失或错误绑定直接拒绝。

P2：冻结整个进程的 Node、类型、设备与接口集合。只明确排除 loopback，拒绝未知非 Qbb 数据面设备。标准夹具要求每个 Qbb 物理队列存在，拒绝 setup 时共享的物理／egress／ACK 队列及保留组。读取时验证原绑定，对重复 QP 槽位或跨组引用拒绝；loopback 的非发送组必须为空。这里的零值是全进程 Qbb 范围，不称单流精确占用。

P3：live map 有键而 Ptr 为空时，在解引用前抛出明确异常。有效 live 对象保留地址及 flow_id；存在映射时 `txAbsent` 或 `rxAbsent` 为 false。

setup 的 GetObject 会涉及聚合查找 bookkeeping，放在纯度指纹之前。Read 不调用 GetObject，也不使用可变 GetBytesLeft、IsFinished、调度器查询或 RDMA GetNBytes。待发送量只按字段计算保守界，与物理队列字节分开。

## 3. 实际对象夹具

新二进制为 `build/scratch/ws31-endpoint-object-test`，一次进程覆盖下表。八组正常观察均在同一时刻连续读取两次；中间不推进事件。完整协议指纹字符串在进程内逐字节比较，stdout 的 FNV 值只作展示，不用哈希相同替代该比较。

| 正常观察组 | 预定实际状态与输出 |
| --- | --- |
| complete-unmarked | 累计确认完成，生产 finished 位尚未置位；pending 为 0 |
| complete-marked | 旧 finished 位已置位；保留 QP 仍被真实读取 |
| irn-two-sack-blocks | snd_nxt=0，两个 SACK 块为 `[0,1024)`、`[2048,3072)`；finished 位不能遮蔽未完成对象，pending 为 8,192 B |
| retain-old-append-new | 保留旧槽位，追加 4,096 B 的新未完成 QP；旧／新完成位分别保留，pending 不重复计数 |
| completion-history-present | 两侧实际完成历史集合有项，history_released 为 false |
| live-rx | 实际接收映射有对象，rxAbsent 为 false，记录 live／saved 地址 |
| physical-and-ack-queues | 真实物理队列 32 B、ACK 队列 48 B，分别读取 |
| events-and-serialization | TX／RX 事件各一个，pacing／resume 各一个，当前包与 BUSY 同时存在；发送占用计一份 |

十四组 Read 拒绝为：保存 QP 缺失、重复槽位、设备组错配、HW 组错配、物理队列缺失、TX／RX 空 Ptr、保存 flow_id 错误、RX 翻转错误、原需求时钟错误、paused、down、队列身份改变／共享、设备集合改变。拒绝前后同样逐字节比较协议指纹。

另两项拒绝是：把 mask=127 的快照直接交给账本；以及重新 Capture 含未知非 Qbb 数据面设备的范围。预计总计 31 次 Read 调用、16 次拒绝，记录 8 组正常观察、16 组拒绝和汇总。Read 调用包含故意失败的调用，不能称为 31 份成功快照。

指纹覆盖明确协议字段、完整 SACK 序列、maps／sets、QP 向量与位图、队列字节、包 UID／大小、事件 UID／时间／context／运行状态、设备和硬件绑定、当前模拟时刻。它不对整个 C++ 对象做 memcmp，不把引用计数或填充字节纳入协议纯度。

## 4. 运行边界

夹具只构造并手工设置实际对象，安排四个未来 Noop 事件但从不运行它们。销毁前后均要求 event_calls=0。当前 BUSY／currentPacket 也是夹具设置，不称实际链路发送。

`observedFields` 始终为 127，故不能成为完整端点证书；SWITCH_STATE 仍须从真实交换机状态读取。事件标记为空也不能证明当前回调栈已返回，后续仍须默认关闭的原交付 token 和 Receive 返回后闭合。

## 5. 独立执行及停止规则

依[冻结计划](endpoint-probe-object-preflight-r1.json)，唯一副先审新源和测试，材料问题即在远端动作前停止。通过新进程、缓存、ID、worker 与资源门后，至多一次同步、一次隔离 optimized `-j2` 完整构建，再直接运行新夹具一次。无部署、网络、旧核心或旧夹具重跑。

保留精确源码、输入、命令、环境、编译／运行退出码、stdout／stderr、二进制与 ldd 库来源、逐条件日志和资源收据。任何源码、门、构建、运行、纯度或来源不匹配均停后继；不改原源或判据重试，不覆盖新旧 ID。编译与运行后须明确释放约束。

## 6. 继续承担的验证

本轮不证明真实第二代发送，旧完成位加新槽位仍需网络分支验收。保存 RX 的完成回调捕获、实际历史处理、真实交换机读取、channel token、实际上下文 G1 和网络两代正例／拒绝例继续必做。独立 C1 V0、三候选业务批次与背景双侧效果、状态及运行成本继续必做；未建立新组合基线。

本节点从候选 README 和 reading-log 定向复核 DiffFlow v1 的规则安装及启用顺序记录。这里借鉴先确认前置状态再启用后继行为；其未充分交代结束检测和回收协议，不能为本快照证书背书。分类喷洒、简化传输、独立队列和平均 FCT 结果不外推为本项目收益，也不新增为正式对照。
