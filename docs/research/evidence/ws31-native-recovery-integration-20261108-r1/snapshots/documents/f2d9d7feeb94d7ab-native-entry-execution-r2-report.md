# WS-31 原生入口有限执行 R2

## 1. 结论

**一次完整 optimized -j2 构建通过，20 个独立进程案例全部通过预设判据。** 四个健康全表案例完成 4,480 条实际 QP／Packet 映射核验；16 个预期拒绝或失败边界案例均退出 0，没有把预期 Entry 失败写成健康完成。

实验 ID：`20261108-152638-ws31-native-entry-r2`；固定提交 `21b440985f90d2081438e435ef640adc9f43a42d`，个人 fork 分支 `experiment/ws31-native-entry-r2`。R2 相对 R1 的源码增量仅为 declarations 头的 Waf 导出项。R1 失败 ID 和原始收据保持。

这是断链对象条件下的原生入口工程验收，尚待主独立验收 raw；不关闭整体 G2，也没有科学网络、完成协议、真实两代或性能结论。

## 2. 固定源、输入与构建

新源码归档的全部 4,870 个普通文件逐项匹配固定 Git blob、长度、SHA-256 和可执行位；本机 HEAD／分支／个人 remote／干净状态与发布记录一致。新目录此前不存在，远端普通成员提取后再次核对全树和权限，未改共享 cache／worker 或执行同步部署。

复用 D1／D2、seed 5310001 的两份旧声明，字节、长度、家族和头部未变；新路径绑定为 `f8a2320c727d3bc168c27b58de34b7df69e72ee383a59fca7bdc66becc09b045`。Entry 仍为 305 行、夹具为 398 行。worker 原字节 c3ab5849 保持，既有 18 项纯控制检查没有重跑或计入 C++ 案例。

启动前重新核全部用户、PID 祖先、当前 CPU 增量、负载／内存／磁盘和维护候选，无其他活跃用户作业。被动调试器和 hg 查询按本次 start ticks、状态、无子进程和零 CPU 增量核对。实际使用 env -u PYTHONOPTIMIZE python3 -B，Python 3.5.2 优化关闭，科学环境变量清理规则保持。

| 实际直接子命令 | PID | 退出码 | 命令收据耗时 |
| --- | ---: | ---: | ---: |
| g++ --version | 328137 | 0 | 0.006 s |
| ./waf configure --build-profile=optimized | 328138 | 0 | 3.075 s |
| ./waf -j2 | 328377 | 0 | 368.178 s |
| ldd 新目标 ELF | 330712 | 0 | 0.019 s |

实际 Ubuntu GCC 5.4.0；一次 configure、一次完整构建、一次 ldd、20 个直接 ELF 案例，共 24 个直接子命令，全部退出 0、未超时，无案例重试。完整构建耗时约 368.178 s；build/config.log、c4che 配置与完整日志保留，不把工程构建时间当作算法成本。

## 3. 构建后实际准入

worker 在完整构建及新 ELF／ldd 成功后，于北京时间 15:35:47.234241 生成实际 request，completed_cases＝[]。之后才重新观察当前作业、CPU、资源、全部 4,870 实际源文件、两份输入、新 ELF 和 36 个实际 ns-3 库；输入观测记录了路径、长度、哈希和头部。

新 ELF SHA-256：`f3cf6e5f443219e8dbbcda5c8aa76eabb3b1b78d3d9d2b6e58f94da923be713c`。全部 36 个已构建库也是 ldd 实际加载的项目库，实际路径均在本 ID 的 build 内；它们与目标 ELF 的实字节均已回传，gate 前和终态哈希一致。

资源收据绑定 run／commit／plan／worker PID 328136／request nonce／新二进制及新 input binding，并含 input_files_checked＝2 和真实观测来源。一次 gate 通过独占临时文件、flush／fsync、同目录非覆盖原子 link 发布；没有预放行、刷新、撤销或复用。

全部案例的开始收据相对资源观察年龄为 **21.667～23.316 s**，满足每案不超过 60 s。实际顺序为 request → 请求后观测 → receipt／gate → worker accepted → 案例，无提前运行。资源观测 load1＝1.46，可用内存和磁盘满足原门槛。

## 4. 20 案实际结果

每案均为独立 PID、唯一匹配 PASS、完整 stdout／stderr 和最终退出 0。I／B／P 为实际 Session 的 Issued／Bindings／PacketReads；“未采样”表示没有 Entry 诊断快照，表中不补造 pending／liveQPs 等默认零值。

| 案例 | PID | I／B／P | Entry 诊断 |
| --- | ---: | --- | --- |
| entry-d1 | 330808 | 1120/1120/1120 | 健康完成 |
| entry-d2 | 330809 | 1120/1120/1120 | 健康完成 |
| nonzero-install | 330810 | 1120/1120/1120 | 健康完成 |
| bad-final-declaration | 330811 | 0/0/0 | 预期失败 |
| duplicate-install | 330812 | 0/0/0 | 预期失败 |
| late-install | 330813 | 0/0/0 | 预期失败 |
| wrong-address | 330814 | 0/0/0 | 预期失败 |
| wrong-hw-owner | 330815 | 0/0/0 | 预期失败 |
| bad-reverse-route | 330816 | 0/0/0 | 预期失败 |
| missing-pair-timing | 330817 | 0/0/0 | 预期失败 |
| repeated-run | 330818 | 1120/1120/0 | 预期失败 |
| early-stop | 330819 | 0/0/0 | 预期失败 |
| pending-producer-failure | 330820 | 16/1/0 | 预期失败 |
| terminal-mtu | 330821 | 1120/1120/0 | 预期失败 |
| terminal-route | 330822 | 1120/1120/0 | 预期失败 |
| postrun-live-map | 330823 | 1120/1120/1 | 预期失败 |
| dispose-before-run | 330824 | 0/0/0 | 未采样 |
| diagnostic-before-terminal | 330825 | 0/0/0 | 未采样 |
| policy-variants | 330826 | 1120/1120/1120 | 健康完成 |
| postrun-context | 330827 | 1120/1120/1 | 预期失败 |

四个健康案各核 1,120 个原 ordinal／身份、原需求 ns、实际 QP 属性与实际包策略；独立按固定输入和整数 tuple hash 复核全部 4,480 条包记录，UID／ordinal 无重复。nonzero-install 的 100 ns 预步没有平移原绝对需求时刻，D2 逐对时序和 D1 全局时序均通过其原断言。

policy-variants 仅使用原合同规定的四组策略字段，原 13 个身份／需求字段未改。实际 id 0、1、2 的等待均为 0；id 16 原类别为 1、策略为 2，实际等待 485 ns。缺失和未知策略没有被原类别冒充。

## 5. 关键故障的实际区分

[pending 原始日志](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/native-entry-execution-r2-raw/remote-result/execution/case-pending-producer-failure.stdout)实际观察到真实 id 13 已绑定，同时另有 15 个 C2 pending。擦 live key 后的真实 GetNxtPacket 拒绝没有推进序号、发送字节或 PacketReads。

随后保持 Entry／Client 存活，从 **2,005,000,093 ns 推进至 2,015,550,400 ns**，只出现一次 ENTRY_FAILURE_DRAIN，11 项诊断残留账、11 项 StartData 和首错保持。终态 issued／demandReads＝16、bindings＝1、PacketReads＝0、pending＝0、未准入＝1,104、liveQPs＝0，正常取消计数及字节为 0。推进没有残余回调异常，之后才 Dispose／Destroy。

terminal-mtu／terminal-route 均在完整 1,120 绑定后由 Run 终态复核拒绝。postrun-context 由实时诊断自身发现 Run 后 MTU 错配；postrun-live-map 的真实 producer 拒绝使 Session 原因锁存，诊断变为失败，liveQPs＝1,119、PacketReads＝1。独立读出的原 Session 文本与导出的 firstError 均为 V2 session failed: V2 hardware boundary failed；不混用直接 producer 异常文本。

析构前未 Run 和诊断早读两案实际输出 diag_observed＝0、diagnostic＝not_sampled，省略 Entry 状态／pending／liveQPs；Session 的实际计数另行保留。全部失败边界未制造正常成功取消。

## 6. 原始回传、时间和保护

[完整 raw](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/native-entry-execution-r2-raw)包含真实 request／资源收据／gate／accepted、24 个子命令和 20 案完整日志、新 ELF 与 36 库实字节、两输入、源码归档／终态 4,870 身份，以及独立校验和全部前置／终态资源观察。安全归档共 147 个普通成员，拒绝链接／重复／穿越；146 个清单成员及清单自身哈希均逐项通过。

归档 SHA-256：`235e267b3b4126d5758011e8352d52e179bf6c11150015d1abb168e122b7b4da`；transfer-inventory.json SHA-256：`ed3004664b2be83ccbb9d414e24a6599f8564645c58274b60b614a1de7d5e459`。本地 raw-manifest 的路径、SHA 和 files 列表由 evidence 的 raw_manifest 明确引用，清单自身不递归纳入。

实际完成收据为 **2026 年 11 月 8 日 15:36:38.050986（北京时间）**，原值 2026-11-08T07:36:38.050986Z；独立校验在 15:42:00 进行，本机保护终检在 15:42:52 进行。命令开始字段、执行完成、观察和报告时间分别保留，未把旧 R1 的失败时间或本次读取时间写成完成事件。

终态 worker 已退出，无该 run 残余进程或编译器；远端源码、两输入、新 ELF／库的最终字节保持。本机发布树 4,870 文件、原 WIP 4,868 文件与两边 HEAD／branch／index／status，以及 24 份绑定工件均不变。只写计划的 R2 report／evidence／raw 前缀，guard 保持待主独立验收。

## 7. 参考复核与交接范围

从候选 README／reading-log 入口复核 SeqBalance arXiv:2407.09808v1 的技术分析和核验记录。本节点继续借鉴“原请求、实际 QP 与最终完成分开记证”的口径；该论文有父 WQE 拆分和 CQE 聚合，本例只有 generation 0 的断链入口／QP／Packet，没有实现这些机制。作者性能和硬件成本不能外推成本项目证据，详见 raw/reference-node-review.json。

本轮原生入口有限工程判据已实际通过，待主独立核验原始材料后承接下一单目标。OS2／实际 framing、完整完成与共享协议、真实超时／两代、V0、匹配消融、业务／背景双侧效果与实际成本继续保持未完成；没有新增科学候选、需求或性能样本。
