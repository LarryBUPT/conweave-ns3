# WS-30 v13 执行入口与验收集成

日期：2026 年 10 月 26 日。本节点完成默认关闭的本地执行入口和验收集成，论文交付目标保持 v13；文件名中的 v14 仅表示内部工程修订。没有访问远端、推送、部署、构建或启动仿真，新增实验为 0 格。

## 1. 已完成的入口

[执行器](../../scripts/run_ws30_v14.py)默认执行 `inspect`，只读本地契约和 Git blob。`verify-local` 只验收已有本地结果。`run` 必须明确列出阶段，并取得主对话记录的范围与外部同步授权；没有实际授权文件时，在构造远端 backend 之前拒绝执行。本节点只提供[关闭的示例](evidence/ws30-v14-execution-authorization.example.json)，没有创建授权收据。

授权绑定契约、阶段表、controller/worker、恢复/资源 helper 和验收器哈希，以及阶段与 cap。运行时还读取真实会话，要求 GPT-6 Luna / Medium 已生效。该检查不负责切换模型；完成后须实际切至 GPT-6.1 Sol / Medium 分析（按用户对 WS-30 的具体要求，覆盖通用工作流的 High 默认）。当前本地实现回合继续为 GPT-6.1 Sol / Medium。

构建逐格显式传入 `source_sha`，不使用当前 HEAD 或可变全局 SOURCE；入口没有同步、部署、推送或登录重试路径。所需 SHA 必须已通过获准流程进入远端个人仓库缓存。启动前检查实际部署 worker 的逐字节哈希、BUILT 状态、源码 SHA、trace 和 topology 哈希，再显式传入模拟与需求 seed。worker schema 3 及实际 `RANDOM_SEED 1` 也纳入回传验收。

持久化 runner 保留每阶段合同、待办 ID、验证结果和失败。构建请求先写本地 intent；回传丢失后只读状态，不再次发构建。若状态仍不明，保留 ID 并停止。已成功结果复验后复用，已有本地目录不覆盖；失败后修复须新 SHA、新 ID 和新计划。资源/未知进程门槛沿用已审计恢复器，原生日志溢出会失败；入口另外在状态检查时以 512 MiB 限制单格 aggregate config.log，超限停止新准入并保留后台进程和证据，交由监督方处理。

## 2. 精确阶段和依赖

[阶段表](evidence/ws30-v14-executor-schedule-r1.json)覆盖原契约的 252 个建议 ID，没有增加实验数。每次提交明确的 `--phase` 顺序；主对话一次授权多个阶段后，程序可在真实验收通过后连续推进，无需逐格等待人工确认。不同源不在同一 build group 中，同机各阶段串行，不自动叠加两个 lane 的资源预算。

| 阶段 | 格数 | 前置门槛 | 最高 cap |
| --- | ---: | --- | ---: |
| technical-single | 1 | 范围、同步、worker 兼容及新鲜主机门槛 | 1 |
| technical-rest | 17 | 单格回传验收 | 4 |
| life-pair | 6 | 技术 18 格及旧 raw 回归 | 4 |
| life-state | 6 | 技术 18 格及旧 raw 回归 | 4 |
| life-other | 18 | 两个持久 profile 与 6 对 off/on 均通过 | 4 |
| cw-tech | 2 | 技术 18 格及旧 raw 回归 | 4 |
| cw-long | 2 | ConWeave technical off/on 一致 | 4 |
| w5-resource | 4 | ConWeave 持续前缀 off/on 一致 | 4 |
| w5-rest | 28 | W5 的 E/Q12/U12/ConWeave 首批资源验收 | 4 |
| formal-first | 4 | 旧源技术 18 格、资源 12 格及实际 seed 1 复验 | 4 |
| formal-rest | 164 | 正式首批的新 schema、身份/字节/资源验收 | 8 |

工程为 18＋6＋6＋18＝48 格；W5 为 2＋2＋4＋28＝36 格。W5 资源格直接使用冻结的 32 个比较 ID 中 4 个，不另加格。新源没有 cap 8 准入，不能用旧源 cap 8 收据替代。表中的 cap 均为上限，实际还受授权收据和新鲜资源降载门槛约束。

## 3. 验收器和协议审计

[静态审计 r5](evidence/ws30-v14-static-audit-r5.json)新增了六个具体传输函数的逐字核对：移除新增被动 hook 并还原旧 profile 常量后，ReceiveUdp、ReceiveAck、PktSent 以及三个 DCQCN 状态更新函数与旧源相同；严格无类别选路函数也相同。ConWeave 去 hook 等价和旧三个路由函数等价继续通过。新增生命周期行为与放行前排空检查属于显式夹具改动，没有被包装成“整份源码未改”。所有结论仍为静态证据。

生命周期验收补上创建/删除对应、三个需求时刻、放行前累计 ACK、明确端口及序号，以及两个跨轮边界均保留非初始 CC 状态的检查。pair profile 除候选不同、每轮真实队列不等，还要求较短队列方向实际改变；新 miss 和 U12 的 chosen 必须符合真实队列大小。这样不会把一直相同的排名误算为缓存应对变化的覆盖。

state profile 继续要求实际接收 ECN、真实 CNP、后续真实降速；U12 还须出现真实 receiver gap、非空接收/发送 SACK 和恢复进入，且事件历史延续到两次放行边界。完成边界应清空 SACK 并退出恢复。计时器可在空闲期合法变化；仅比较同次 release 的 before/after，不把空闲演进误判成重建。触发不足即覆盖失败，不能以零状态、代码存在或静态测试判通过。

[离线收据](evidence/ws30-v14-executor-offline-audit-r1.json)记录 15 项通过的测试，覆盖关闭执行、哈希不匹配、源码冲突、构建回传歧义、失败保留、阶段依赖及显式 seed 传参。测试中的合成控制状态只验证运行器，不是模拟器或物理覆盖证据。另从本地原始数据复验旧源技术/资源 30 格、201,936 条 FCT，并核对各份真实配置 seed 1；未重跑旧格。

## 4. 正式 168 格可以怎样解耦

正式 168 格仍固定在 `2c9f3a50bafad0740b461496ba24fa81941a9bc7`，工程/W5 在 `0673e4c3de34d83585dd40f6be7fbd3ed000a9ee`。旧正式输入按每传输新建 QP，生命周期模式和 profile 均为 0。新增 pair/state 的跨请求复用不是正式输入的前提。旧源严格选路、技术不变性和同源 cap 4/8 资源已有原始证据，因此 formal lane 的科学门槛可以独立于新源生命周期补验。

seed 修订改变的是来源元数据：所有固定 trace 不重生，模拟 seed 仍为原配置的 1。新 worker 通过环境传观测/profile，并在运行后核对配置；不会把新 seed/profile CLI 强塞给旧源 run.py。formal-first 的四个原计划 ID 先按新 controller/worker 协议回传验收，随后才允许余下 164 格。该路径不需要等待新源 pair/state 触发，但不能因此声称正式结果证明持久 QP、WQE、连接池或真实训练收益。

解耦也不隔离共享正确性问题。若新补验发现可映射到旧源且影响 fresh QP 的协议错误，或正式自身出现身份、字节、队列、回归和资源失败，应停止受影响的正式准入并重新判定。生命周期必做验收保持 ACTIVE，不因正式 lane 可独立运行而删除。

## 5. 调度预算与剩余门槛

新源工程构建运行暂留 2～3 小时，分析 0.75～1.25 小时；W5 构建运行暂留 2～4 小时，分析 1.5～2 小时。这些是待实测估计，新源和 W5 未获吞吐准入。旧源正式以已有 cap 8 的 23.55 格/小时作依据，约 7.13 小时构建运行，加 1.5～2 小时回传分析；四格先以 cap 4 验收会增加少量调度时间。

全部串行约 14.9～19.4 小时，且不含审批、部署、同步和修复。10 月 26 日上午 9 时后，距次日不足 15 小时，不能承诺全部按时完成。若主对话优先保证正式样本，可先选择 formal-first → formal-rest；若优先消除持久状态缺口，可先选择 technical → life 两 profile。ConWeave/W5 可在技术回归后独立推进，不须人为等待 life-other。程序保留所有门槛，顺序与资源分配须由主对话明确放行。

当前仍缺外部同步授权、配套部署和真实 worker handshake、新鲜主机/ID 冲突检查、新源原生构建和单格/cap 4 资源资格、动态 off/on 回归、真实 pair/state 覆盖，以及全部新矩阵结果。代码、协议静态等价和离线测试通过只完成本节点，WS-30 未闭环。

## 6. 参考借鉴复核

从候选 README/reading-log 复核 IRN 正式版与 SeqBalance v1 的技术分析及核验记录，并沿用[前节点四篇固定版本记录](evidence/ws30-v14-reference-review-r1.json)。IRN 提供活动请求内 SACK/恢复与累计 ACK 排空的区分；SeqBalance 提供请求、WQE 和 QP 生命周期不能互换的边界。本次把这些边界落实到验收和正式 fresh-QP 结论范围，没有引入论文机制，不迁移作者硬件或性能结论。新记录见[执行节点复核](evidence/ws30-v14-executor-reference-review-r1.json)。
