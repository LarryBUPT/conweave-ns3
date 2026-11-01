# 标签与生命周期边界独立源审查

日期：2026 年 11 月 1 日。结论：**方案可实现，契约需修订后再冻结实现和验收。** 固定源码为 `50603927fc09a68d9f2e038129aaee3a3d021081`。本轮只读取本地源码、契约和历史收据，没有构建、测试或远端操作。

## 1. 必须先修订的定义

**首次类别需要构包前提。** 需求后 500 ns 可得，不保证首次构包发生在 500 ns 前。NIC 排队或 C2 等待可能推迟首次构包。因此，profile 1 的“首次类别仍为 0”和 profile 2 的“先用原类别”，都必须增加输入前提：目标 QP 首次构包早于阈值，且存在阈值后的构包。否则，应按首次实际构包的可见标签确定首次策略。构包发生于 [GetNxtPacket](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:1092)，随后才经历链路发送及传播，见 [QbbChannel](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/qbb-channel.cc:102)。

**缺失与标签 0 分开记录。** 固定源的移除操作实际上不附加 WorkloadTag，见 [构包标签代码](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:1103)。现有 ROUTE 将缺失与显式 0 都打印为 0，见 [观测代码](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws30-observer.h:83)。profile 1 应明确阈值前 `present=false`、决策值为 0；阈值后恢复原标签及存在性。原始标签为 0 时也要保留这个区别。

**部分错误需要固定完整选择规则。** 契约尚未指定哈希、字节序、salt 和桶号。一个哈希桶表示约四分之一，不能保证小输入恰有四分之一请求。应在输入冻结时列出实际选中四元组和两类计数，并确认错误／正确请求均出现。选择只依赖固定四元组，同一请求的重传和同四元组重建保持同一选择桶。若要求精确比例，须另行规定确定性排序截取，不能混用两种含义。

## 2. 标签调用链与默认回归

C2 在 [StartApplication](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/applications/model/rdma-client.cc:149) 采样需求标签并决定一次等待；[StartRequest](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/applications/model/rdma-client.cc:172) 保留原需求时刻，再经 [AddQueuePair](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:267) 写入 QP。QP 的 `m_workload_tag` 应继续保存原业务真值。新夹具需要一个共用、无 RNG 和无新事件的可见性函数，分别在需求采样时和每次构包时调用，不能在源交换机重新按时钟计算标签。

C1 只在首次路径缓存未命中时读取类别并登记模板，见 [首次路径与模板](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/switch-node.cc:1460)。它没有独立的持久类别字段；后续行为由固定路径及剩余预算体现。预算到期后，路径缓存仍在，后到包不会重新登记。C3 则明确保存首次 `Decision.category`，后续活动按缓存类别更新，见 [QuotaAdmission](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-quota.h:62)。这两处逻辑已支持预期缓存语义，不必为新夹具改选路规则。

需要新增构包日志：原需求、构包时刻、uid、flow_id／generation、四元组、seq、载荷长度、原标签、可见标签和 present。原包及重传由 [GetNxtPacket](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:1102) 新建 Packet；[RecoverQueue](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:1016) 仅回退发送序号。重传须按当次构包重新求标签，按 uid 对应源 ROUTE，不能只按 seq 合并。Packet 的复制保留元数据，见 [复制构造](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/network/model/packet.cc:145)。

默认 profile 0 必须原样走既有标签／transform 语义。新增配置应显式进入 controller、worker 元数据及子进程环境；清除外部残留值，并在 worker 与 C++ 入口同时拒绝新夹具和非零旧 transform 共开。默认回归复用已验固定输入与 C1／C2／C3 raw 参考，只运行后续获准的新源对应格，不重跑旧参考或旧核心。新日志仅在夹具启用时输出，现有 FCT、ROUTE 和专属日志默认格式保持。

新夹具启用时还应限定冻结的 WS-31 模式，并拒绝旧 composition／lifecycle 和故障夹具共开。否则，同一 QP 的多轮需求及旧 generation 控制会改变“原需求时刻”的含义，无法按本契约的单请求时钟核验。

## 3. C2 同刻、零等待与放行后语义

同刻事件按时间再按 event uid 排序，见 [Scheduler 比较](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/core/model/scheduler.h:111)。标准 [Application::DoStart](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/network/model/application.cc:86) 预先排入 Stop；C2 Launch 在 StartApplication 内才排入。仅使用 SetStopTime 通常只能覆盖 Stop 先到，不能据此声称两种同刻顺序都通过。

最小新增边界是：Stop／Dispose 分别在 Launch 前、后两个 uid 顺序到达；零等待的同步 StartRequest；放行后 Stop／Dispose 及重复清理。Stop 先到应取消一次；Launch 先到已不再 pending，[CancelPendingRequest](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/applications/model/rdma-client.cc:197) 应保持 launched，不增加 cancelled。`StopApplication` 目前不停止已放行 QP，见 [StopApplication](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/applications/model/rdma-client.cc:209)。Dispose 还会清空 app 的 node 指针，不能在 Dispose 后重新调用 StartRequest。

零等待直接在 StartApplication 调用栈内放行，不能安排一个同刻事件插入其间。也不要用 `SetStopTime(0)` 构造该边界，因为 0 表示不安排 Stop。记录事件 uid、调用顺序和请求／字节账，按 `demanded=launched+cancelled+pending`、`launched=finished+unfinished` 验收。

旧无驱动夹具只适用于放行前取消，见 [既有夹具](E:/研/毕业论文/workspace/ws31-candidates-implementation/scratch/ws31-start-lifecycle-test.cc:18)。放行后必须接真实最小 RdmaDriver／RdmaHw 调用链，或明示的测试注入点；[AddQueuePair](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-driver.h:36) 非虚函数，派生假驱动不能直接拦截。Stop 为私有函数；若需精确控制另一种 uid 顺序，可新增窄范围 friend 测试访问，不改变调度和选路机制。

## 4. 清理、重建与异常适配器

清理函数已经同时删除 C1 路径、预算和 C3 状态，见 [ResetWs30V13Tuple](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/switch-node.cc:1389)，但正常 WS-31 完成不会调用它。现有唯一调用受旧 lifecycle 4 门控制，见 [完成回调](E:/研/毕业论文/workspace/ws31-candidates-implementation/scratch/network-load-balance.cc:662)。新夹具需要独立、显式的清理入口和逐类清理记录，不能打开旧 WS-30 控制器来获得入口，也不能把空闲当成删除路径。

同四元组重建还须处理端点。普通 AddQueuePair 不清除历史完成墓碑；[DeleteQueuePair](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/rdma-hw.cc:365) 有重复删除断言，Rx 清理也独立。应冻结“旧请求完成、端点状态退出、旧包已排空、清理相关交换机缓存、再新建”的顺序。最终 ACK 本身不证明所有旧副本都已排空。若要求旧 generation 的包跨越新建边界，则还需另定 generation 检验，不能靠清除交换机缓存保证隔离。

旧 [ROUTE 统计键](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws30-observer.h:76) 没有 generation，旧 FCT 验收器也拒绝同四元组重复完成。新生命周期结果须增加 generation／flow_id 辅助账，按 generation 检查不换路；跨 generation 的合法重新准入可以换路。保留原全局统计，不以清空观测表掩盖变化。

真正新增的适配器覆盖有三组：C1 的重复／重传、到期后迟到不重建、容量／区间回退后仍固定路径；C3 的空闲后迟到、显式清理后重新准入及标签变化；C2 上节中的调度边界。容量、区间上限和 32 位 seq 边界可由专用小型 SwitchNode 夹具构造，避免用数万流或 4 GiB 网络流量重复证明核心。测试访问／小限额仅用于明示夹具，默认算法限额保持。

## 5. 已覆盖与最小后继

详细条目见[覆盖矩阵](label-lifecycle-boundary-review-r1.matrix.csv)。C1 核心已覆盖重复、空洞／交叠、到期、容量、区间回退、清理重用和饱和；C3 核心已覆盖已知类别变化仍固定、活动精确边界、迟到、Erase／重建、未知与单端口；C2 核心已覆盖 0～500 ns 和全量标签映射。相应测试文件／核心对象已按固定源哈希核对，本轮没有重跑。已有 C2 Stop／Dispose 只证明等待前取消，不包含本次新增调度边界。

建议只新增三类夹具：真实构包到源 ROUTE 的标签时序／部分错误夹具；调用实际 SwitchNode 适配器的预算与配额边界夹具；调用实际 RdmaClient 的事件顺序夹具。清理／同四元组重建可合并到第二类，但端点重建与排空条件须另有明确证据。先修订上述定义、冻结观测和调用顺序，再由主冻结新源、输入、必要格及授权；本报告不构成执行许可。

来源哈希和精确行段见[来源清单](label-lifecycle-boundary-review-r1.sources.json)，交付检查见[QA](label-lifecycle-boundary-review-r1.qa.json)。独立 V0、双侧效果和完整生命周期仍保留为后续必做项。
