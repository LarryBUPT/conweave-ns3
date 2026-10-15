# WS-28 定向探针首个反例与两因素预检交接

## 1. 本对话目标

继续完成 WS-28 的三个劣化 seed 时序诊断、两因素消融和图表解释。本文件记录首个反例的技术验收与消融准备；WS-28 总任务仍为 `ACTIVE`。

## 2. 已确认的项目事实

WS-27 原始对照源码为 `ee236f27920aa56b3dd562ed971e5abee9e1e659`。原生对照阶段已从 96 个新格及 48 个旧控制格逐 raw 核验，共 144 格，见[原生报告](../research/ws28-native-comparison-report.md)。两因素源码 SHA 为 `955d26b580c9ca9249e66dea68638b22e0e32e2c`；修正 ECMP 接收入队事件后的定向探针源码 SHA 为 `ca03c7bccf05120fde219606bbb478e48a467619`。两个 SHA 均已推送个人 fork，原始结果仍在各自独立的 `results/<实验 ID>/`。

## 3. 已完成工作

24 个未见需求 seed `20262921～20262944` 的 192 背景档 trace 已固定在[输入清单](../research/evidence/ws28-ablation-inputs.json)，SHA-256 为 `6c07022c872c6d21b321412f62d8aa70dfd601317ae0f439cd343dfbfdd073a4`。因素 A 控制 MoE 评分中的额外背景排队字节；因素 B 控制背景 QP 首包的两候选队列感知改路。六臂技术计划、24 格资源计划及 120 格正式计划生成器已落盘。正式并发须等待资源 pilot，尚未生成正式机器计划。

固定 `955d26b…` 的隔离 optimized 构建 `20261015-000001-ws28-build-check` 成功。该 ID 的 8 流 ClassReserve 技术运行与独立 ID `20261015-000010-ws28-technical-cr-a1-b1` 均为 8/8 流完成、资源收据通过，原始 FCT SHA-256 同为 `e3fa403b4768239fdd0e916f333117ecd84177c3d0553eefc923a76cb249fdbc`。后者日志确认 mode 21、A=1、B=1 和队列计数守恒。这是小输入等价性，不是四因素分支全部动态覆盖。

首个劣化需求 `20262725` 的四格定向诊断使用[计划 v2](../research/evidence/ws28-tail-plan-v2.json)，计划 SHA-256 为 `40f7eebb18c3b6576e9c2e42a0284111b02c69f9a73bf3de36723456ce9259ee`。ECMP 关闭／开启 ID 分别为 `20261015-020000-ws28-tail-s20262725-fecmp-d0/d1`；ClassReserve 关闭／开启 ID 分别为 `20261015-020000-ws28-tail-s20262725-classreserve-d0/d1`。四格均为 `SUCCEEDED`，16,576/16,576 条流完成，源码、trace、拓扑、传输和资源收据逐格通过。ECMP 两格 FCT SHA-256 均为 `25f23194366a4e52fbbe5847473cce54519fe6ed90143b4b38ab254be4fe39b0`；ClassReserve 两格均为 `792288f155807053c6926f979cb9fac057d2fa6b5b5049abc81adb58bfe8e579`。两组均与对应 WS-27 原格相同。开启格每臂各记录 72 次目标包入队尝试、72 次实际接收和 72 次出队，无拒收、丢包或 20,000 行溢出；关闭格没有探针事件。`scripts/analyze_ws28_tail.py` 已按 UID、交换机和端口配对这些事件。

该 seed 的 ECMP 批尾目标流最高序号包，逐跳队列等待合计 6,579 ns；ClassReserve 批尾目标流对应值为 6,506 ns。两个批尾流身份不同。ClassReserve 后者在交换机 1478 的目标包入队前观察到 97,464 B 背景排队字节，单跳等待 6,179 ns；源 ToR 首包选的是第一个候选出口，因此该目标流本身不能证明额外背景权重导致了首跳改路。这些是局部时序观测，尚未构成三个 seed 的完整归因。

## 4. 已形成的设计决策

探针 v1 计划保留但未运行：源码审查发现 ECMP 的接收入队事件缺失。v2 使用新 SHA、全新 ID 和固定事件窗口；以旧格 FCT 哈希及开关格一致为非扰动门槛。两因素消融保留 24 个独立未见 seed 和同输入五臂，不用已揭盲反例估计组件收益。设计冻结后的 DiffFlow 与 SeqBalance 版本、适用条件和不可外推范围已在[消融协议](../research/ws28-factorial-ablation-protocol.md)复核。

## 5. 当前状态

WS-28 仍为 `ACTIVE`。定向诊断 4/12 格逐 raw 通过；六臂技术计划中 `cr-a1-b1` 为 1/6 格通过，额外的原 ClassReserve build-check 不计计划格；资源 pilot 0/24，正式消融 0/120。2026 年 10 月 15 日观察时，个人分支为 `feature/ws28-classreserve-explanation`，没有在途远端仿真。原生对照和两种 P95 图已完成，另外两个反例的时序图、组件效应图及最终解释未完成。

本任务工具无法读取或切换当前 Codex 模型及推理强度，故不声称 Luna High 或 Sol High 已实际生效。长时矩阵进入后台监督前须核验项目工作流要求的 Luna High；终态数据分析前须核验 Sol High。

## 6. 未解决问题

需求 `20262729` 与 `20262739` 的八个诊断格尚未运行。六臂技术正确性还缺五格，资源阶梯及 120 格正式消融尚未执行。第一个反例的局部队列时序不能唯一解释批次劣化；完整路径和组件方向要以其余 raw 及未见 seed 配对结果核定。当前原生对照输入没有触发 CONGA、LetFlow 的 flowlet 超时重选或 ConWeave 中途改路，这一覆盖限制继续保留。

## 7. 后续动作

先确认本聊天实际使用 Luna High，并只读检查服务器无其他用户作业、资源健康及所有既有 ID 状态。随后用 `python scripts/run_ws28_tail.py run --limit 12` 沿已验收的四格前缀继续，保留每格原 ID，失败即停；终态后运行 `python scripts/analyze_ws28_tail.py --limit 12`。再运行 `scripts/run_ws28_technical.py` 完成六臂小输入，核对原模式与 A=1、B=1 的 FCT；按 `scripts/run_ws28_resource.py` 做 4/8/12 阶梯，并据吞吐门槛冻结正式 120 格并发及计划。正式矩阵完成后实际切回 Sol High，逐 raw 复算双侧效果、三反例和组件图；按项目工作流复核候选文献，最后逐项验收 WS-28。

## 8. 与其他工作流的关系

WS-27 旧 ID 和原始结果未覆盖或重跑；WS-25/26 的判据不重判。论文 `thesis/figures` 的集成图由主对话负责，本 WS-28 工作树没有修改它。原始实验结果在本地忽略目录与远端独立 ID 下，Git 中只存源码、输入、计划和分析器。

## 9. CONTEXT SNAPSHOT

WS-28 原生对照 144/144 格已验收，但全任务仍 `ACTIVE`。两因素源码为 `955d26b…`，诊断修正版为 `ca03c7b…`；未见需求 24 份 192 档输入已固定。第一个劣化 seed 的四格探针开关 FCT 与 WS-27 原格逐字节一致，目标包 UID/队列事件可配对；另两个 seed、技术五格、资源 pilot、正式消融与图表尚待执行。当前没有在途远端仿真；继续远端长时矩阵前须实际核验 Luna High，并从已有计划及原 ID 安全恢复。
