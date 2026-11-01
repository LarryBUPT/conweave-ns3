# WS-31 端点快照接口取证表

日期：2026 年 11 月 1 日。状态：固定 1f 源码核对，尚未实现接口或执行测试。两份端点账本 WIP 保持审查时的字节。

## 1. 快照的范围

最小端点夹具先采用无背景条件，检查经过的全部主机和交换机端口。该条件允许检查全设备队列与定时器，避免把全局计数误当作某一请求的独立计数。以后加入背景时，须另立请求归属与共享状态协议。

账本中的 `EndpointSnapshot` 目前由调用者提供。下表是实际适配器必须实现的取证义务；现有布尔值和核心测试尚未履行这些义务。

## 2. 字段与真实来源

| 取证项 | 固定源码中的来源 | 接口要求 |
| --- | --- | --- |
| 发送映射退出 | `RdmaHw::m_qpMap`、`GetQpKey`、`GetQp` | 用实际键查找；若存在，另核 QP 的完整地址、端口、pg 和 flow_id。不能只把压缩键等同于完整 tuple |
| 接收映射退出 | `m_rxQpMap`、`GetRxQpKey`、`GetRxQp(..., false)` | 使用接收视角，记录原 tuple 到接收参数的映射；观察时不创建 QP |
| 发送 QP 定时器 | `mlx.m_eventUpdateAlpha`、`mlx.m_eventDecreaseRate`、`mlx.m_rpTimer`、`m_retransmit` | 完成前保存 QP 引用；映射删除后仍读取这些对象，分别记录 `IsRunning()` |
| 接收 QP 定时器 | `RdmaRxQueuePair::QcnTimerEvent` | 接收映射删除前保存引用；删除映射不能当作定时器自动取消的证据 |
| 设备定时器 | `QbbNetDevice::m_nextSend`、`m_resumeEvt[]` | 新只读接口须逐项报告；PFC 关闭时也记录实际事件状态。不能只统计 QP 定时器 |
| 网卡队列组 | `RdmaEgressQueue::m_qpGrp`、`RdmaQueuePairGroup::m_qps` | 逐项记录 flow_id、`snd_una`、`m_size` 和现有 finished 位；用 `IsFinishedConst()` 观察完成，不调用调度器补置 finished 位 |
| 待发送需求与 ACK 队列 | `RdmaEgressQueue::GetNBytes(i)`、`m_ackQ` | QP 剩余发送字节与 ACK 队列字节分别报告；前者不是已构造数据包的物理队列字节 |
| 交换机物理队列 | `QbbNetDevice::GetQueue()`、`BEgressQueue::GetNBytesTotal()` | 汇总全部相关出口，包括回向 ACK 路径；读数不触发出队 |
| 当前串行化 | 父类的 `m_txMachineState`、`m_currentPkt` | 由窄只读接口同时报告 BUSY 和当前包；不能以队列空替代发送器空闲 |
| 在途交付 | `QbbChannel::TransmitStart` | 每次实际发送独立 token；接收处理返回后才关闭。保持原目的节点 context 与原交付时间 |
| 完成历史 | `akashic_Qp`、`akashic_RxQp` | 先记录旧代历史存在，再在通过排空门后的明确操作中处理；保留账本旧代记录及前后收据 |

源文件与 Git 字节哈希见[配套来源收据](evidence/endpoint-snapshot-interface-audit-r1.json)。该表补充[端点设计](endpoint-lifecycle-design-r1.md)，不改变正在审查的 WIP 或其审查计划。

## 3. 调用顺序与只读边界

`RdmaHw::QpComplete` 先取消发送事件，再调用完成回调，最后删除发送映射。完成回调中的快照必然可能仍有发送映射。端点退役检查应在回调和该次 ACK 接收处理返回后执行，且最后 ACK 的在途 token 此时才可闭合。

`RdmaEgressQueue::GetNextQindex` 会写 finished 位和暂停统计。`DequeueAndTransmit` 还可能构包、发送或调度 `m_nextSend`。两者都不能作为只读快照入口。快照应直接读取现有字段，记录原有 finished 位与实际累计确认完成是否一致；若不一致，保留差异并按预定规则拒绝或等待后续真实事件。

无背景夹具仅在组内每个保留 QP 都已确认完成、全部相关事件已退役且网络排空时，才允许明确执行队列组清理。该动作与观察分开记录，不为获得零快照而调用清理或取消事件。

## 4. 接线前的决定

现有快照只有 `txTimers` 和 `rxTimers` 两项事件计数，设备事件尚无独立字段。接线时应增加设备事件计数并纳入 Quiet 条件，或者明确定义一个覆盖全部事件的计数；优先使用独立字段，便于定位拒绝原因。实际修订待唯一副当前审查返回后统一处理。

新链路包装只在新夹具明确开启时替代一次交付事件，普通路径继续使用现有直接调度。token 取证需要实际链路身份；在存在同节点间多链路时，不能仅以节点对表示链路。最小夹具应冻结接口／channel 映射，并据此核对串行号与定向链路。

这些是实现要求，不是端点排空实测结论。尚未运行编译、核心测试或新网络格，独立 V0 和三候选业务／背景效果及成本仍由后续固定协议承担。
