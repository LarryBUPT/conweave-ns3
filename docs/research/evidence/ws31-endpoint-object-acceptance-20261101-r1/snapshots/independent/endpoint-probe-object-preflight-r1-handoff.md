# WS-31 实际对象快照工程预检九节交接

日期：2026 年 11 月 1 日。来源聊天 `01a19323-2201-7b23-a0f1-905c71496d38`，委派主聊天 `01a19322-95a5-76e3-a4f5-1f1e9dde81ce`。证据等级：实际 NS-3 对象手工状态下的读取／覆盖／纯度工程验证。

## 1. 本对话目标

按[冻结计划](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/main/endpoint-probe-object-preflight-r1.json)先独立审源，通过后执行新门、至多一次 sync、一次 optimized `-j2` 完整构建和一次新对象夹具。全部输出位于 independent 的 `endpoint-probe-object-preflight-r1*` 范围；不得修改主源、判据或重跑旧核心／参考／网络。

## 2. 已确认的项目事实

固定源 `8cd1ba69469bf80143d5c89edc17fa72611018e8`，父源 `20bc2d9f7c7c435bf832ba2fcaf0e07df00cf5da`，分支 `feature/ws31-candidates`，实际个人 origin 引用一致。本地前后干净，恰三文件差异：新 probe、scratch 夹具和 qbb 头文件注释／两个 friend。完整树 4847 项、284,719,415 B，树输出 SHA-256 `8096510b5b068ef31269f88d836112a6e53b2b351984694bc796a0a4a4c05855`；两份已验核心及 13 项旧交付／封存字节不变。Windows qbb 头文件为 CRLF，固定 Git／Linux 字节为 LF，等价性和两类原字节均保留。

## 3. 已完成工作

主对话冻结源码、契约、ID 和判据；本副独立审源、新门、一次同步和隔离源逐文件核验。ID `20261101-173000-ws31-endpoint-object-r1` 完整构建退出 0；直接运行新夹具一次，退出 0、stderr 为空，精确汇总 reads=31／refusals=16／network_runs=0／event_calls=0／actual_network_completions=0。核 8 组同刻双读、14 组 Read 拒绝纯度、另 mask 与 Capture 两拒绝，及 16 设备、13 槽位、8 SACK raw。109 项 raw 与 36 项工程库副本全部回传通过，45 项加载来源有收据。详见[报告](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-report.md)及[索引](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-index.json)。

## 4. 已形成的设计决策

P1 使用 setup 实际 driver／HW／NIC／组绑定，保存 TX 始终入账且须在所选组恰好出现一次。P2 冻结全进程 Node／接口／队列身份，仅排 loopback，拒绝共享和重复 QP。P3 live 空 Ptr 先拒绝。GetObject 在纯度指纹前的 Capture，Read 避开 mutable getter；pending 是字段保守界，生产位图和累计完成分别读取。mask 保持 127，不能靠默认零补 ALL。所有设置状态、队列和事件只属于对象夹具，不改变生产策略。

## 5. 当前状态

COMPLETE FOR ACTUAL-OBJECT PROBE PREFLIGHT；WS-31 ACTIVE。完整 optimized 构建 1，新对象夹具 1，sync 1；部署、独立核心编译、旧测试重跑、网络均 0。31 次 Read 含 14 次 Read 拒绝，成功返回数由源码与 raw 推得 17，其中 1 次仅供不完整 mask 拒绝。二进制 1,709,032 B，SHA-256 `06bbe540d28f35571502e0b4189c1029e2282fae179402443f43dc1258e099ef`。所有来源／构建／fixture 进程及 SSH／scp 调用均终态；[source／entry／environment 已显式释放](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-guards-released.json)，无持久驱动或下一项执行授权。

## 6. 未解决问题

仍必做：真实 switch 状态、原事件 channel token／post-Receive 闭合、真实完成回调 savedRX 捕获和历史处理、保留旧 QP／追加新 QP 的真实发送分支、G1 以及两代网络正例／拒绝例。继续必做独立 C1 V0、三候选双侧效果及状态／运行成本。当前对象预检无未完成验收项；它不覆盖这些后继任务，不形成自然排空或 ALL 证书。

## 7. 后续推荐动作

主对话先从 index／QA 独立核来源、109 raw、36 库副本、实际 argv／env、逐组结果与释放；再按依赖实现 switch／channel／完成回调／history，另冻源码、输入、ID 和资源门后开展 G1／网络。不要把手工累计确认或 BUSY 状态写成自然传输，也不要重跑已验旧格。本副到本单目标交付停止。

## 8. 与其他工作流的关系

未改主材料或科学源，无 Ofan 专门工作、WS-29、旧控制器／矩阵；未新增正式基线。20bc 便携核心和父源默认网络证据保持旧身份，不外推为 8cd 网络验收。DiffFlow v1 仅提供顺序借鉴，缺少完整结束／回收协议，不提供 RDMA 或双侧收益证据。两项本地辅助核验器错误（CRLF 误等同、Waf 日志通道）保留失败记录并修正提取，未改变源码／计划／判据，未新增科学执行。

## 9. CONTEXT SNAPSHOT

固定 `8cd1ba69` 已通过审源、新门、单 sync、4847 文件来源核验、1 次 optimized-j2 全构建及 1 次实际对象夹具。计划 SHA-256 `d91892f73bc6a6b45c0541f2c588ba59ba3fd3694ec75a75e35be5265dd5b255`；ID `20261101-173000-ws31-endpoint-object-r1`。八组双读与十四项 Read 拒绝的完整协议字符串检查通过，总 Read31／拒绝16，mask127、Noop0、network0、自然完成0。109 raw、36 工程库本地副本、45 依赖指纹及源码树可从 raw/remote-results 读取；二进制哈希 `06bbe540d28f35571502e0b4189c1029e2282fae179402443f43dc1258e099ef`。约束已释放，本地实现树干净，旧字节不变。下一步由主验收并实现真实 switch/channel/history/G1/网络与效果成本，本副没有继续执行授权。
