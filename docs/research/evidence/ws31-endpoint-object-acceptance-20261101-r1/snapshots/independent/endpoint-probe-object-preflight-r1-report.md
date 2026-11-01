# WS-31 实际对象快照工程预检

日期：2026 年 11 月 1 日。状态：COMPLETE FOR ACTUAL-OBJECT PROBE PREFLIGHT；WS-31 真实网络与业务验证继续 ACTIVE。依据[冻结计划](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/main/endpoint-probe-object-preflight-r1.json)执行，未修改科学源码、主材料或判据。

## 1. 验收结果

固定源 `8cd1ba69469bf80143d5c89edc17fa72611018e8` 通过独立静态审查、新门、一次同步、一次隔离 optimized `-j2` 完整构建，以及一次新对象夹具运行。构建和夹具退出码均为 0，夹具 stderr 为空。

本轮在真实 NS-3 对象上手工设置状态并实际调用读取代码，核验了范围守卫、只读字段聚合和协议纯度。31 次 Read 调用包含 14 次 Read 拒绝；由源码与 raw 计数可得 17 次成功返回，其中 1 次用于随后拒绝不完整 mask。另有 Capture 拒绝 1 次，合计 16 项拒绝。八组正常状态各连续读取两次，进程内比较完整协议字符串；十四组 Read 拒绝也比较拒绝前后的字符串，全部通过。

`mask=127`、网络运行 0、四个未来 Noop 执行 0、实际网络完成 0。该结果不形成完整 ALL 证书，不验收自然端点完成、真实排空或旧完成位下第二代发送。

## 2. 固定来源与原始证据

分支 `feature/ws31-candidates`，父源 `20bc2d9f7c7c435bf832ba2fcaf0e07df00cf5da`。实际个人 origin 分支已由 `git ls-remote` 核验。本地实现树前后干净；相对父源恰为新增 probe、新 scratch 夹具和 qbb 头文件注释／两个 friend，共三文件，无对象布局或路由动作变化。已验 20bc 两份便携核心输入未变、未重跑。

| Git 固定输入 | SHA-256 |
| --- | --- |
| `scratch/ws31-endpoint-object-test.cc` | `9bd087245c57721340df041d3d993a3a37f40a74f0356a37a1c46c6eb4c56af5` |
| `src/point-to-point/model/qbb-net-device.h` | `6564f30ea34699f0c30c37a7178261252c14908a304a8e8aa5d279210752d15f` |
| `src/point-to-point/model/ws31-endpoint-probe.h` | `210166cbd71fda71d3367a427352839efd63410489a5aed0cf057e89f296e892` |

完整 Git 树 4847 项，原始 `git ls-tree -r` 输出 SHA-256 为 `8096510b5b068ef31269f88d836112a6e53b2b351984694bc796a0a4a4c05855`。隔离源逐文件核对 Git blob 与实际字节，共 284,719,415 B；构建及运行后全部源文件哈希不变。[完整源清单](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/remote-results/provenance/source-files.json)和[Git 树](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/remote-results/provenance/source-tree.txt)保留来源。[固定输入副本](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/frozen-source)为 Git／Linux 编译字节；[Windows 工作字节](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/local-working-bytes)另行保留。

回传 109 项 raw 文件，共 183,766,520 B（不含清单自身），全部大小和 SHA-256 通过。包含实际二进制、36 项隔离构建的 NS-3 共享库副本、完整两路构建日志、运行日志、精确环境、编译／链接命令、库来源及资源收据。45 项动态依赖均记录实际路径和指纹，其中 9 项系统依赖留存哈希收据，未复制系统库。二进制与 36 项工程库在运行前后和回传后均核验一致。

先前审查、核心索引／QA／释放收据，以及两组原 WIP 封存，共 13 项旧文件字节未变；核验入口为[来源与静态审查](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/local-static-review.json)及[回传完整性](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/fetched-integrity.json)。

## 3. 独立审源和新门

P1 已从 setup 的实际聚合 driver 捕获 HW／Node／NIC／egress／队列／组绑定，Read 逐项核对；保存 TX 的完成、pending 和事件独立入账并去重，必须在所选实际保留组中恰好出现一次。P2 冻结 Node、类型、接口及队列身份，只排除 loopback，拒绝共享、重复 QP 和遗漏绑定。P3 在 live map 值解引用前拒绝空 Ptr，并保留 live 地址与 flow_id。

GetObject 只在 Capture 的 setup 阶段，位于纯度指纹前；Read 不调用它，也不调用 GetBytesLeft、IsFinished、GetNextQindex 或 RDMA GetNBytes。保守 pending 与物理队列字节分开。旧 NS-3 Ptr、继承 protected friend、队列及 EventId 接口已由本轮真实编译和运行覆盖。完整静态意见见[本地审查记录](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/local-static-review.json)。

新 ID `20261101-173000-ws31-endpoint-object-r1` 在首次和同步前均确认 runs/results 不存在，回传目标也在传输前确认不存在。全用户进程快照核 UID、命令、父链、cwd 和开始标记，无活动项目驱动、Git HTTP helper、其他普通用户作业或并行构建／仿真；旧 driver 22440 不存在。长期休眠的 debugger／hg 与既有收据相符，位于本项目之外，未发送任何进程信号。

缓存 origin 为个人 fork、工作树干净，初始缺少新提交。授权的唯一 sync 退出 0，无回退、无部署。现有 worker 的换行归一化字节与固定源一致。缓存工作树 HEAD 保持 `236a801a00e35de9078635e04acae2f701c21ded`，没有切换缓存或既有实验源码。

## 4. 一次构建与一次运行

隔离工作目录为 `/home/fnl/lzy/runs/20261101-173000-ws31-endpoint-object-r1/source`。源码复制后先逐文件核验，再按工作流进行一次 configure 和一次完整构建；所有命令和环境保存，`-v` 仅用于记录编译器 argv。

```text
./waf configure --build-profile=optimized
./waf -j2 -v
```

构建退出 0，用时约 358.5 s。新夹具的实际编译 argv 包含 `/usr/bin/g++ -O3 -g -std=gnu++11 -march=native`；完整编译和链接 argv 见[命令核验](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/compiler-command-verification.json)。Waf 的详细 runner 命令写在 stderr；构建 stderr 并非错误判据，包含命令和既有诊断。本轮未发现新 fixture／probe 的诊断行，不能把全部构建 stderr 称为空。

构建环境为显式白名单。运行时仅增加隔离 build 内 NS-3 库目录的 LD_LIBRARY_PATH，LD_PRELOAD 缺席；WS30_OBSERVE、WS31_LABEL_PROFILE、WS30_TAG_TRANSFORM、WS30_LIFECYCLE、WS30_LIFE_PROFILE、WS30_COMPOSITION 均为 0。完整值见[构建环境](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/remote-results/provenance/build-environment.json)和[运行环境](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/remote-results/provenance/fixture-environment.json)。没有继承 shell 中的旧 profile 设置。

运行直接调用以下新二进制一次，无参数，未使用 waf --run 或 run.py：

```text
/home/fnl/lzy/runs/20261101-173000-ws31-endpoint-object-r1/source/build/scratch/ws31-endpoint-object-test
```

运行退出 0、stderr 为空，汇总逐字符合冻结预期：

```text
WS31_ENDPOINT_OBJECT_SUMMARY PASS reads=31 refusals=16 network_runs=0 event_calls=0 actual_network_completions=0
```

二进制大小 1,709,032 B，SHA-256 为 `06bbe540d28f35571502e0b4189c1029e2282fae179402443f43dc1258e099ef`。[工具链](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/remote-results/provenance/toolchain.json)记录编译器、目标、cc1plus、链接器、系统和指纹；[ldd 与库指纹](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/remote-results/provenance/runtime-libraries.json)记录 45 项加载来源，36 项工程库实际位于该新 source/build 范围。[构建收据](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/remote-results/provenance/build-result.json)和[运行收据](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/remote-results/provenance/fixture-result.json)含 argv、cwd、完整环境、退出状态、时间、日志哈希与 wait4 使用量。

## 5. 逐条件 raw 核验

| 正常双读组 | 已核 raw |
| --- | --- |
| complete-unmarked／complete-marked | old QP 累计确认完成，pending=0，finished 位分别为 0／1；两者均读取真实保留对象 |
| irn-two-sack-blocks | old finished 位为 1 仍不能遮蔽未完成 QP；snd_nxt=snd_una=0，pending=8192，完整 SACK 保持 `[0-1024] [2048-3072]` |
| retain-old-append-new | 旧槽位完成位 1，新槽位完成位 0、未完成，pending=4096；未重复计量保存 TX |
| completion-history-present | 两侧集合有项，history_released=0 |
| live-rx | live RX 地址等于保存 receiver，未被当作映射退出 |
| physical-and-ack-queues | 物理 32 B、ACK 48 B 分别记录 |
| events-and-serialization | TX／RX 事件各 1，设备事件 2；BUSY 与 currentPacket 合计一份发送占用 |

共核 8 条正常主记录、16 条设备记录、13 条槽位记录、8 条 SACK 记录、16 条拒绝及 1 条汇总，无其他 stdout 行。设备／物理队列／egress／ACK／组的对象身份在正常组间一致，保存 TX／RX 地址稳定。

十四项 Read 拒绝分别对应保存 QP 缺失、重复槽位、设备／HW 组错配、缺物理队列、TX／RX 空值、保存 flow_id／RX 翻转／原时钟错误、paused／down、队列身份改变／共享和设备集合改变。另两项是 mask 不完整及未知非 Qbb Capture；全部拒绝原因与固定源的预期守卫对应，见[拒绝来源映射](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/refusal-guard-mapping.json)。

实际比较的是进程内完整的已定义协议字符串；FNV 仅为 stdout 展示。指纹覆盖 SACK、maps／sets、QP 向量／位图、队列字节、包标识／大小、相关事件、绑定和时刻，不是整个 C++ 对象 memcmp，也不是任意隐藏调度器状态的普遍证明。四个 Noop 未执行；Simulator::Destroy 仍执行正常 teardown，event_calls=0 不表示所有 NS-3 销毁回调均未执行。完整[stdout](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/remote-results/logs/fixture.stdout)、[stderr](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/remote-results/logs/fixture.stderr)及[raw 核验](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/fixture-output-verification.json)均已保留。

## 6. 资源、核验器修正与释放

构建和源建立阶段共 202 个离散资源样本，1 分钟负载采样最大 2.24，可用内存采样最小约 121.76 GiB；最终门磁盘仍约 2289.66 GiB。构建 wait4 最大 RSS 为 603,088 KiB，夹具为 26,084 KiB。它们描述本次工程过程，不作为候选算法成本或连续系统峰值，见[资源摘要](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/resource-summary.json)。

两项本地核验器错误均保留，没有重构建、重运行或改判据。第一项将 Windows 工作字节误当 Git blob；qbb 头文件仅相差 231 个 CRLF，Git blob 哈希精确匹配计划，工作副本哈希为 `7007de27f3a3faae3411e171b35c109099df3a3f3a62f84e294e2de6ee1f602c`。修正后分别保存两类字节与归一化证明，见[首次来源检查错误](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/initial-local-verifier-failure.json)。第二项只从 stdout 提取编译命令；修正为读取两路原日志并解析 runner argv，见[首次日志提取错误](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-raw/initial-log-extractor-failure.json)。二者均为辅助核验器假设错误，不是源码、科学构建／运行或原始证据失败。

最终远端门确认来源 driver 308083、configure 308120、build 308359、fixture driver 310589 和 fixture 310625 均已不存在；全部 SSH／scp 调用终态。Windows 仅余已知 ElectricBillMonitor 服务，无遗留项目驱动。[显式释放收据](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-guards-released.json)已释放本目标 source／entry／environment 约束，无下一项执行授权。

## 7. 参考复核与继续承担的验证

本节点从候选 README、reading-log 定位 DiffFlow，复核 arXiv:1604.05107v1 技术与核验记录。借鉴的是前置状态确认和后续启用的顺序，用于范围绑定与证据门；其未充分定义回收与结束检测，不能背书本项目端点复用。分类喷洒、简化传输和独立队列与这里的真实对象读取不同，平均 FCT 不外推为本项目业务收益。本轮未引入机制或正式对照，见[参考复核](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-reference-review.json)。

主对话继续承担真实 switch 覆盖、channel 原交付 token 与 Receive 返回后闭合、完成回调中的 savedRX 捕获、实际历史清理、旧 QP 保留追加网络分支、实际上下文 G1 和双代网络正例／拒绝例，以及独立 C1 V0、三候选业务／背景双侧效果及状态／运行成本。Ofan 专门工作、WS-29、旧控制器和旧矩阵均未开展；旧证据不转为新源网络验收。

[索引](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-index.json)、[QA](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-qa.json)和[九节交接](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-probe-object-preflight-r1-handoff.md)提供完整交付入口。本节点完成对象读取工程预检，不代表 WS-31 全部任务闭环。
