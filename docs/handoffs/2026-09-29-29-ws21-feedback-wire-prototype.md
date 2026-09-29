# Handoff 29 — WS-21 真实反馈报文首版原型

## 1. 本对话目标

继续 Handoff 28 的 WS-21 工程契约，开始实现明确的下游反馈报文和真实回程；不运行效果矩阵。

## 2. 已确认的项目事实

- 仓库 `E:\研\毕业论文\workspace\LarryBUPT-conweave-ns3`，分支 `feature/ws21-downstream-feedback`。开工时 HEAD 为 `b8d32dfd58a61e4ff2b4913152c0805840bc0897`，且先前契约文档有未提交改动。
- 上轮长尾诊断 pair `20260929-132600-ws21-tail-off` / `20260929-132700-ws21-tail-on` 只验证观测与路径身份非扰动，没有反馈消息或候选对照。
- 本地 Windows 没有 `g++`/`gcc`；`python run.py --help` 因本机未安装 NumPy 而不能运行，项目捆绑 Waf 文件也不是可由 Windows 本机 Python 直接解释的纯脚本。

## 3. 已完成工作

- 新增 `Ws21FeedbackHeader` 固定 51 B 网络序列化格式：版本、源/目的 ToR、候选首口、采样时间窗、CE/样本数、64-bit 序号与生成时间；含基本合法性检查。
- 在目的 ToR 的已核验入端口映射上，以非空 10 µs 窗口累计候选 CE 样本，生成 IPv4 协议 `0xFA` 报告，目标为原源主机，使用现有转发表经普通 Qbb 设备队列返回。此协议值在仿真网络协议处理代码中未发现冲突；其他 fixture 中出现的 `0xFA` 是测试字节样例。
- 在源 ToR 截获报告，验证主机/ToR 对应、包协议、候选路由端口、头字段、新鲜度和单调序号；有效报告放入每 ToR 最多 16,384 键的缓存。缓存暂不影响选路。
- 本地产生/入队接受与拒绝/出队、送达字节、接收时延粗分箱、序号缺口、过期和缓存峰值的摘要计数。自产报告放入普通数据优先级 3 的真实队列；自产首跳跳过无物理入口的 MMU ingress 记账，仍做 egress 准入；发送前去掉内部 ingress tag，避免到下一跳重复添加同类 tag。
- `run.py --ws21-feedback 1` 可写入配置，仅允许与 `--lb ws18 --ws21-identity 1` 同用；默认关闭。添加头字段序列化单元测试并更新 Waf 清单。
- Python 源码语法检查 `python -m py_compile run.py` 通过，`git diff --check` 通过。未完成 C++ 编译或单元测试执行。

### 后续核验补记（2026-09-29）

- 固定代码提交 `3f1a28a6583567744b6a177d8c11da7cc8a761dc` 的隔离构建 ID `20260929-153553-ws21-feedback-wire` 在远端 optimized `-j2` 构建成功，worker 状态为 `BUILT`。
- 另在该隔离源码副本中配置测试构建。项目已有 `src/core/test/command-line-test-suite.cc` 因向 `const CommandLine` 调用非 const `Parse` 而阻塞全套测试构建。为执行目标套件，临时放宽了该无关测试 helper 的参数 const 限定，完整测试构建随后成功；文件已恢复，并与 Git 中版本比对一致。这条临时兼容修正不在提交中。
- 直接启动构建出的测试运行器，`devices-point-to-point` 返回 `PASS`，其中包含 WS-21 反馈头的 51 B 序列化/反序列化与非法 CE 样本数检查。验证构建另存于隔离 `build-ws21-tests` 输出目录；**未启动仿真**。
- 单独过滤测试目标时，Waf 没有建立生成头文件，反而编译了不相关模块；改为完整测试配置后才成功。`test.py` 没有可执行权限，故直接调用测试运行器完成套件。

## 4. 已形成的设计决策

- 只把目的 ToR 入端口处观测到的 CE 归到已核验的候选上游首口。最终主机出口的本次 ECN 标记尚未在本 ToR 的 `ObserveWs21Destination` 之前产生，因此不会被当作候选差异。
- 反馈流使用独立 IPv4 protocol `0xFA`，不借用 ACK/NACK 语义，不经 PacketTag 传递状态。所有路由跳按地址 ECMP，报告用队列 3 竞争实际服务。
- 10 µs 聚合/10 µs 接收时限仍是临时工程值；本原型暂不改变 QP 路径，不得据此推断算法收益。

## 5. 当前状态

反馈报文原型已提交；固定代码 `3f1a28a6583567744b6a177d8c11da7cc8a761dc` 的 optimized 隔离构建与远端 point-to-point 单元测试均通过。该测试构建使用了临时、已恢复的无关 core 测试兼容修正，目标 WS-21 测试源码本身按提交内容编译。当前 `scripts/remote_experiment.py` 的 `--ws21-feedback` 转发仍有一处未提交改动，提交前不得冻结新的仿真 SHA。

当前没有创建新仿真实验 ID 或原始数据。仅确认报文头和代码可构建、序列化测试通过；尚未确认实际反馈消息送达、逐跳计费、年龄、丢失/过期退回。完整技术 pilot 未就绪，效果矩阵仍关闭。

## 6. 未解决问题

- 提交并推送 runner 参数转发与本次验证记录；按新固定 SHA 重新构建，再运行 40 流同 SHA 开/关正确性 pair。
- 验证 `CustomHeader` 对协议 `0xFA` 的逐跳识别、路由与解析消费长度，实测报告经过哪些队列/链接；核对 queue/MMU 计数守恒。
- 验证 `CustomHeader` 对协议 `0xFA` 的逐跳识别、路由与解析消费长度，实测报告经过哪些队列/链接；核对 queue/MMU 计数守恒。
- 当前结果只输出聚合 summary，没有独立有界逐消息时间线；尚不能逐条关联 generated、各 hop enqueue/dequeue/drop、delivered 和 expired，也不能完整计算端到端总链路字节或控制报文尾部延迟。
- 报告接收缓存暂未用于选路，未定义正式采用/等信息消融；也未处理过期缓存条目的淘汰策略，虽然以硬上限防止无界增长。
- 未创建新的实验 ID；没有新的 CE 候选差异、反馈交付率或运行资源数据。

## 7. 后续推荐动作

按上述补记，build 与序列化单元测试门槛已过。下一步先提交 runner 和验证记录、冻结新 SHA，并在远端确认空闲资源后运行新的 40 流开/关正确性 pair；通过后继续核验长尾反馈消息的真实送达与计费。效果矩阵仍需另立双侧独立需求协议，不由技术 pair 自动解锁。

## 8. 与其他工作流的关系

此代码只在 `feature/ws21-downstream-feedback`；WS-10/11/12/19/20 原结论不变，WS-22/23/24 前置条件不变。此前长尾 pair 固定 SHA `478eca21…` 与当前未提交代码不混合。没有切换模型，也没有启动远程仿真。

## 9. CONTEXT SNAPSHOT

WS-21 既有长尾诊断 pair 已通过观测/身份子门槛。反馈通路原型包含 51 B `Ws21FeedbackHeader`、目的 ToR 的候选 CE 窗口聚合、协议 `0xFA` 的真实 Qbb 队列回程、源 ToR 校验/新鲜度/序号缓存及聚合计数；`run.py --ws21-feedback` 默认关闭，缓存还不接入选路。提交 `3f1a28a6583567746b177d8c11da7cc8a761dc` 的远端 optimized 构建成功，`devices-point-to-point` 单元测试 PASS。全量测试构建临时修正了一个无关 core 测试 helper 的 const 编译错误，随后已恢复原文件。**尚无新的仿真 ID、消息送达/年龄/成本或性能数据；未运行仿真。**待 runner 改动提交后按新 SHA 先做 40 流正确性 pair；完整技术 pilot 尚未就绪，WS-21 效果矩阵 NO-GO，历史结论不变。
