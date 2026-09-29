# Handoff 37：WS-21 局部心跳本地预飞行

**后续执行勘误（2026-09-30）：**本页保留预飞行时的状态；七个预留 ID 后来全部执行、回传并通过逐格原始核验，结论见[结果报告](../research/ws21-local-heartbeat-pilot-report.md)与[Handoff 38](2026-09-30-38-ws21-local-heartbeat-pilot.md)。下文 `445cf1e2…` 是 Windows CRLF 工作副本哈希；固定 Git 内容及远端拓扑快照的 LF SHA-256 为 `dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad`，规范化后内容相同。“尚未运行/未切换”仅描述本页形成时，不代表当前项目状态。

1. **本对话目标：** 回应用户对 SGLB 原论文“五种状态”的疑问，并在 WS-21 已完成的 STATE 成本矩阵之后，准备适合本项目的小拓扑 HELLO/ACK 故障技术试验。本阶段限于本地实现、轻量校验与冻结输入；不启动远端构建或仿真。用户要求分析用 Sol、实验用 Luna，模型切换须实际生效；本任务未取得当前模型的切换凭据。

2. **已确认的项目事实：** SGLB 的 Open、Keepalive、Area Descriptor、Request、Update 是 SyncMesh 五类控制消息，不是五种心跳状态；本项目只借鉴局部探测。旧 WS-21 off/5/10/20/40 µs STATE 矩阵固定 SHA `2c14d3b4c952a9cece89a9de14216709b604706f`，结论见[长尾报告](../research/ws21-compact-longtail-interval-report.md)；缓存未参与选路，效果矩阵 NO-GO。新心跳技术原型固定源码 SHA `770b6b5617657832393bd721e0d634c6639405fb`，输入哈希、参数和预留实验 ID 见[预飞行](../research/ws21-local-heartbeat-preflight.md)。新代码无实验原始数据。

3. **已完成工作：** 助手在个人 fork 的 `feature/ws21-downstream-feedback` 加入 10 B HELLO/ACK 头部、按实际入端口和会话序号核验的直连探测、活跃上联订阅/四周期撤订、三次无有效 ACK 标 `UNKNOWN`、HELLO/ACK 故障时间窗、逐跳与 STATE 分账、ACK 往返时间、有限事件日志；同时贯通 `run.py`、scratch、`remote_experiment.py`、`remote_worker.py` 和头部单测。新 trace 为一条 64 MiB 跨 ToR 长流，已强制纳入 Git。Python 三文件 `py_compile`、worker CLI 帮助及 `git diff --check` 通过；本机无可用 C++ 编译器，单测尚未运行。用户提出的“协议精简、局部心跳和成本权衡”是需求；具体协议实现和门槛由助手完成。

4. **已形成的设计决策：** STATE 继续是独立 26 B 拥塞汇总；HELLO/ACK 仅含版本、类型、epoch、序号，共 10 B，不复制 SyncMesh 全套消息。原因是直连设备已给邻居/端口，发送时刻可留本地。第一轮只监测，`UNKNOWN` 不排除业务端口；当前实验只能检验通信和状态收敛，不能证明故障绕路或负载均衡收益。故障首轮只支持丢 HELLO/ACK，乱序、重启与链路 up 留待定向验证。

5. **当前状态：** 2026-09-30 本地代码已提交，固定 SHA 如上；协议契约、预飞行、状态文档与本 Handoff 一起作为后续文档提交。没有远端同步、构建、仿真、实验 ID 实体或资源收据；所有预留 ID 的远端空闲性未核验。当前阶段停在 Luna High 切换边界，不声明模型已切换。

6. **未解决问题：** 必须完成独立 optimized C++ 构建和 `devices-point-to-point` 单测，验证 packet 路径、队列/Mmu 计数、故障注入相位与资源收据；若修复源码须重新固定 SHA 和 ID。单份丢失、旧/重复/乱序/跨端口 ACK、重启、显式链路 up 尚未覆盖。后续还需候选状态可区分性、缓存进入决策与 `adopted/fallback`，才可讨论效果矩阵。

7. **后续推荐动作：** 在实际 Luna High 中检查个人 fork 推送/同步、服务器健康及 ID 空闲；先独立构建和单测，再按预飞行顺序跑 off、200 µs 正常、丢 HELLO、丢 ACK，成功后才扫 50/1000 µs。每格固定 SHA/输入/seed、启动资源 watcher、保留独立 raw，异常即停。所有终态结果回传后切 Sol High 做自然语言、双侧代价与限制分析。

8. **与其他工作流的关系：** 新心跳与旧 STATE 长尾矩阵分账，不能把旧 16,576 流数据说成心跳收益或更改旧 no-go。WS-21 缓存选路和后续 WS-25 论文整合依赖各自门槛；其它 WS 结论不变。

9. **CONTEXT SNAPSHOT（预飞行当时）：** 个人 fork 分支 `feature/ws21-downstream-feedback`；仿真 SHA `770b6b5617657832393bd721e0d634c6639405fb`；52 节点拓扑 Windows CRLF 工作副本 SHA `445cf1e29b91813a5fcfec2e56966fb08e4436138d1f8f0771015ccfe6e24466`；单流 trace SHA `032b6baaf3b1a6b4507a7699ef3a148eeadd1f343a13c61a12b79c65f1d49ff5`。本页形成时已做本地轻量检查、未做 C++ 构建或远端实验；后续终态见页首勘误和 Handoff 38。当前机制仅监测 `UNKNOWN`，效果矩阵 NO-GO。
