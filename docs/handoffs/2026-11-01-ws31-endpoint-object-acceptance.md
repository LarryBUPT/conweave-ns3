# WS-31 第十七节点：实际对象预检验收整合

日期：2026 年 11 月 1 日。来源为“WS-31 主对话：类别感知新机制构思与论证”（`01a19322-95a5-76e3-a4f5-1f1e9dde81ce`）的[节点交接](../research/evidence/ws31-endpoint-object-acceptance-20261101-r1/snapshots/main/endpoint-object-node17-handoff.md)。Integration 只核本地原证据和 Git 内容，不运行主核验器、二进制或远端命令。

## 1. 本对话目标

独立确认实际对象夹具的构建、原始输出与完整来源，再更新权威状态。本节点只完成手工状态下的真实 NS-3 对象读取与拒绝验证，不增加 43 格技术网络或 17 例适配器条件。

## 2. 已确认的项目事实

固定源为 `8cd1ba69469bf80143d5c89edc17fa72611018e8`，ID 为 `20261101-173000-ws31-endpoint-object-r1`。冻结计划哈希 `d91892f73bc6a6b45c0541f2c588ba59ba3fd3694ec75a75e35be5265dd5b255`；独立 index 为 `11137470407f9fc587971e8ad6ec2cb0000699a9959cf19166aabd2431751f5f`，QA 为 `98bb162d029300695ac852939d293beea643a90aa054a26fcfc085e9c4e46658`，与主聚合收据一致。

实际一次同步、一次 optimized `-j2` 全构建、一次新对象夹具。部署、网络、独立核心编译及旧核心／适配器／参考重跑均为 0。所有调用在新固定源及隔离 ID 下执行，旧成功 ID 未覆盖。

## 3. 已完成工作

[Integration 独立收据](../research/evidence/ws31-endpoint-object-acceptance-20261101-r1/verification.json)核 170 项索引、109 项 raw、13 项旧文件及完整 4,847 条 Git 文件路径的模式、blob、大小和 SHA-256，共 284,719,415 B。路径数不称唯一 Git 对象数；三个实际输入及 CRLF 工作字节分别核对，原两份核心输入未变。

构建完成 1,470 项，外层收据 358.507 s，Waf 内层 5m57.379s。实际新夹具编译命令从保存的 stdout／stderr 提取，为 -O3／-g／gnu++11，无 -DNDEBUG；与此前可移植核心参数分列。configure、build、fixture 顺序、cwd、显式环境、退出码、资源门与原日志均匹配，fixture stderr 为空。

| 原始输出 | 独立核对结果 |
| --- | --- |
| 八组双读、16 条设备记录 | 同组前后展示值及完整协议字符串检查标记一致；实际设备、队列、组和保存对象地址在各组稳定 |
| 13 条保留槽位、8 条 SACK | 累计确认完成与旧 finished 位分别读取；两个 SACK 区间保留，保守 pending 为 8,192 B；追加未完成 QP 后为 4,096 B，旧／新槽位可区分 |
| 队列与事件状态 | 物理队列 32 B、ACK 队列 48 B，末组 TX／RX 事件各一项、设备事件两项、发送占用一项，与手工设置一致 |
| 16 条拒绝、1 条汇总 | 十四项 Read 拒绝有协议不变标记，另有 mask 和 Capture 拒绝。31 次 Read 中 17 次成功返回、14 次拒绝；一次成功返回随后被账本因 mask 拒绝 |

全部 62 行均已解析。主冻结输出核验器哈希保持 `cac9e289b7cfbdf5884f20adf65fa38af9a8728c974a9f8c0ba0960be185f147`，主对完整字段与精确拒绝原因逐行验收；Integration 另核上述状态、计数、对象与槽位关系。完整协议字符串比较在固定 C++ 内执行，展示 FNV 不是唯一依据；验证对象是明确协议字段，不是整个 C++ 对象内存。

实际 ELF 为 1,709,032 B，SHA-256 `06bbe540d28f35571502e0b4189c1029e2282fae179402443f43dc1258e099ef`。36 项隔离工程库副本均在本地核字节；9 项系统依赖仅为远端路径与指纹。库来源来自 ldd 解析及保存字节，不作内核运行时映射证明。大型 ELF 留原本地目录，Git 仅保存来源、哈希和较小证据，见[来源清单](../research/evidence/ws31-endpoint-object-acceptance-20261101-r1/source-manifest.json)。

## 4. 已形成的设计决策

本结果完成该手工对象夹具的读取、绑定、覆盖拒绝及协议纯度范围。mask=127、ALL=255，缺真实交换机覆盖位；事件没有执行，自然网络完成为 0。保留旧槽位并追加对象的结果不替代第二代实际发送，也不能用 EventId expired 或映射删除代替 Receive 调用栈返回。

两项辅助 checker 假设错误保留：工作 CRLF 字节不直接等于 Git LF，以及 Waf argv 不只在 stdout。修正分别核字节等价、解析原 stdout 与 stderr；原构建和夹具成功，无科学重试、源或判据变更。

## 5. 当前状态

全部源码／入口／环境约束于 09:47:46 UTC 显式释放，最终保存的进程门显示五个原任务 PID 均不存在，无持久驱动或后继执行授权。唯一副 completed、idle107；Integration 主快照为 idle cursor `f7a3a118-6bff-483e-a32e-333396ead68d:24`，未重复派发或直接唤醒副。

独占实现树为干净 8cd，HEAD 与个人 origin tracking ref 一致，无新 WIP。本轮主未改科学源或调用远端。权威仓库分支为 `feature/ws23-ws24-evidence-integration`，本节点整合前 HEAD 为 `4058f0dcff6ada867dcb3fa581ecbe166e31ac0a`。只暂存五份权威状态、本交接及新 Integration 证据，不整体纳入主、副源目录。

## 6. 未解决问题

真实交换机覆盖、默认关闭的原 channel 交付事件 token、Receive 返回后闭合、完成回调内保存 RX、实际历史清理、旧 QP 保留追加的网络分支、实际上下文 G1 及两代网络正例／拒绝例继续必做。

独立 C1 V0、三候选匹配消融、业务批次／背景尾部双侧效果、状态及运行成本未完成。当前对象工程 rusage 不当作算法运行成本。尚无独立效果结论或新组合基线，WS-31 不闭环、不归档。

## 7. 后续推荐动作

由主按[接线设计](../research/evidence/ws31-endpoint-object-acceptance-20261101-r1/snapshots/main/endpoint-channel-integration-design-r1.md)实现默认关闭的 channel 观察包装和 pending／owner 约束，保留原事件参数、时间及 context。接入真实 switch 纯读、完成回调与历史处理；观测不能触发 Expire／Pressure 或清理。

设计当前未实现，不构成新执行授权。冻结新源和契约后，再由唯一副审源、按独立计划和新资源门验证 G1／两代网络正反例；旧成功格不重跑、不覆盖。C1 → C2 → C3 实现授权已经存在，不新增候选许可门；最终基线采用仍按实际验证结果和用户决定处理。

## 8. 与其他工作流的关系

Integration 维护状态与历史，主实现并验收，唯一副沿固定目标工作。Ofan／RR 未准入原型保持，新增正式对照仍须正式发表及 CCF A/B 资格、必要性和忠实性核验；既有 DRILL、ConWeave、CONGA、ECMP、LetFlow、QueuePin 保留。WS-29 与旧矩阵不读取、启动或归档，QueuePin 投稿稿不改。

节点参考复核从候选 README、reading-log 进入，核对 DiffFlow arXiv:1604.05107v1 技术及核验记录。借鉴前置状态确认后启用后继动作的顺序问题；其结束检测及回收定义不充分，不能支持本项目排空证书，分类喷洒、简化传输和独立队列的平均结果不外推为 RDMA、批次或背景收益。

## 9. CONTEXT SNAPSHOT

8cd 全构建与实际对象夹具已主验及 Integration 独核：170 索引、109 raw、4,847 源路径、实际 ELF／36 工程库、62 行对象／槽位／SACK 输出匹配。八组双读、十六拒绝，31 Read／17 成功返回；mask127、事件和网络完成 0。全部约束释放、副 idle107、源干净，无新执行授权。下一步主实现 channel／switch／完成回调／history／G1，再冻两代网络正反例；43 网络／17 适配器另计，V0／匹配消融／效果成本未完。
