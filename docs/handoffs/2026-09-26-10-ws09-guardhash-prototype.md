# Handoff 10：WS-09 GuardHash/HarmGate v0 工程原型与正确性

来源：协调任务 `01a0cfac-3176-7590-bf34-c0f176a45118` 派发的「WS-09：GuardHash/HarmGate 最小工程原型与正确性验证」；日期：2026-09-26（中国时间）。本交接只关闭工程原型、计数和有限资源技术 pilot。可重跑规格见 [冻结文档](../research/ws09-guardhash-v0-spec.md)，逐 ID 原始数据核验见 [机器摘要](../research/ws09-validation-summary.json)，效果门槛仍按 [ADR-007](../decisions/ADR-007-guardhash-prototype-before-efficacy.md)。

## 1. 本对话目标

用户明确要求从已推送 WS-08 集成提交新开个人 feature 分支，加快实现可关闭 GuardHash 与 HarmGate，完成真实队列 per-port/per-tag 守恒、32 主机单/双类、导入 1280 拓扑跨 ToR 四流、旧 `fecmp/dualtrack` 回归和等输入资源 pilot。共同 DCQCN/PFC=0/IRN=1 不变；两参考 remote 只读，既存远程工作树与结果不覆盖。WS-10 的固定总字节、多 seed 现象复核及 WS-11 正式强对照不属于本轮。

## 2. 已确认的项目事实

- 开工时个人 fork `feature/ws08-guardhash-gate` 本地、`origin` 同为 `c45d41d42157dd3589e37ebe1953c75a68d5b6c2`，工作树干净；新建 `feature/ws09-guardhash-prototype`。`origin` 仅指向个人 fork，两参考 remote 的 pushurl 均为拒推地址。
- WS-08 共同 IRN 四格单 seed 交互 `−0.053 µs`、背景 P99 差 0，是当前效果 no-go；用户授权提前做工程原型，见 ADR-007。不能由本轮技术 pilot 反转正式效果判断。
- 真实出口队列在 `QbbNetDevice::SwitchSend → BEgressQueue::Enqueue`、`DequeueAndTransmit → SwitchNotifyDequeue`；MMU 准入失败发生在 `SwitchNode::DoSwitchSend` 入队前。`tag=1` 队列字节不是 ConWeave VOQ，也不来自历史上停用的 `_out_qlen.txt`。

## 3. 已完成工作

1. 写代码前冻结 [v0 规格](../research/ws09-guardhash-v0-spec.md)：`LB_MODE=13 shortq2`、`14 guardhash`（门控关）、`15 guardhashgate`（门控开）；三者共用五元组加 UDP seq 的两个确定性哈希候选。`tag=1/0` 数据保留流 ECMP，控制包保留原分派。普通模式比较 `q`，类别模式比较 `q+b`；`λ=1`、`τ=0`，HarmGate 激活/退出为 `8192/4096 B`。这些值不是根据 pilot FCT 选择。
2. 在 `switch-node`、`qbb-net-device`、`broadcom-egress-queue` 实现路由、门控及真实队列事件计数；配置、模式映射和远程运行器留痕。首版 `dff9d92` 构建失败 ID `20260926-013214-ws09-prototype`（基类 `Node` 无新通知方法）；`7930168f7bb43afbe6cc87bd134d91d28667e8c1` 显式取得 `SwitchNode` 后 `20260926-013834-ws09-compile2` 隔离 `-j2` 全量构建通过。该 SHA 承载以下九个正式技术格，所有格均 `SUCCEEDED`、原始 FCT 非空并已 fetch。
3. 32 主机：双类 `20260926-013834-ws09-compile2` 为 4/4、两类均到达源 ToR、队列违规 0；`tag=1` 单类 `20260926-021713-ws09-small-flow` 4/4，`WS09_ROUTE packets=0`；`tag=2` 单类 `20260926-022334-ws09-small-packet` 4/4，双候选 291 次、改路 15 次、队列违规 0。
4. 导入 1280 拓扑跨 ToR 四流 `20260926-022959-ws09-cross-four` 为 4/4（两类各 2），tag 缺失 0、双候选 21 次、队列违规 0。低负载小样本的 HarmGate 未激活，由下述 pilot 覆盖激活/退出。
5. 旧模式同 SHA、同 `ws07_small_flow_only.txt`：`fecmp` `20260926-024003-ws09-regress-fecmp` 与 `dualtrack` `20260926-024625-ws09-regress-dualtrack` 均 4/4；加上本轮 `guardhashgate` 单类，三份原始 FCT SHA-256 同为 `50eff7c6a0303b2fd91980f737cb8b801857e687942c125ce7a5165b68004d0e`，也与 WS-08 同传输条件的旧格相同。`dualtrack` 记录 `flow_packets=150, packet_packets=0`。
6. 等输入单 seed 技术 pilot：`20260926-014609-ws09-pilot-shortq2`、`20260926-015632-ws09-pilot-guardhash`、`20260926-020703-ws09-pilot-gate` 共用 `7930168f`、trace SHA `cbfa0e5a95b7c3b6b56dfd563e855dff8b83f4f54db2747909039285184f58e1`、拓扑 SHA `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`、seed 1、DCQCN/PFC=0/IRN=1、9 MiB buffer。三格均背景 64/64、MoE 256/256、队列违规 0，无超时/PFC；`shortq2/guardhash/gate` 的不同候选次数为 5399/5413/5738，改路为 664/685/53。门控格有 39 次激活、9 次退出、84 次评分。MoE 合成批次分别 1.421/1.415/1.49 µs，背景 P99 均 688.41974 µs；乱序 CNP 分别 1332/1340/1521。单 seed 数值**不构成效果主张**，门控格在该输入下较无门控格更慢。
7. 复查未触发的拒绝入队分支后，修复会计分类：未入队的队列拒绝不再从 `enqueued` 扣除；`admission_drop`、`queue_reject`、`queued_drop` 分开。修复与运行器 `--buffer 1..9`、版本化压力 trace 见 `9c34945c79b44476166f2f1f4dc26f6b2f6163a0`。独立 `-j2` 构建及 `20260926-025616-ws09-drop-probe` 在 32 主机、16×1 MiB 混合流、1 MiB buffer 下 16/16 完成；两类合计 MMU 准入丢包 3,041,296 B、端口守恒违规 0，HarmGate 激活/退出各 12 次。此压力格有 15 次传输超时，不作性能对照。队列自身拒绝入队和链路下线清队列在已运行格中均为 0，仍缺动态覆盖。
8. `scripts/verify_ws09_prototype.py` 从十个终态 ID 的元数据、trace/拓扑哈希、原始 FCT、`config.log` 和 CNP 重算完成数与逐端口守恒；核对三格共同输入与单类 FCT 哈希，生成 [机器摘要](../research/ws09-validation-summary.json)。所有断言通过。三格全量构建各约 342–345 秒（`-j2`），仿真约 205–210 秒；远程同一时刻仅一个仿真，结果均为新 ID。

## 4. 已形成的设计决策

- **Decision：**HarmGate 是按本地总队列字节激活的类别评分门槛；GuardHash 是同候选上的 `q+b` 评分，不把两个名字当作两套独立算法。**Rationale：**现有资料未定义第二个独立协议，门控关/开消融能归因激活条件。**Alternatives：**探测包、多跳反馈、新传输或接收端专属重排均增加混杂，v0 不引入。
- **Decision：**队列统计基于 BEgressQueue 真正接受、出队和丢包事件，拒绝入队与已入队后丢弃分别计。**Rationale：**按 MMU 准入就增加队列余额会把被后级拒绝的包误算；压力探针证明准入丢包时计数仍守恒。
- **Decision：**保留 WS-08 的效果 no-go。**Rationale：**本轮只有一个 trace seed、一个提供字节配置和局部队列信号；强对照和固定总字节、多 seed 尚未做。**Alternative：**据本轮 0.006 µs 差额宣布收益或按 FCT 改门槛，均违背预设比较契约。

## 5. 当前状态

**WS-09 COMPLETE FOR V0 ENGINEERING AND SINGLE-SEED TECHNICAL PILOT。**最终机制/压力探针代码提交 `9c34945c79b44476166f2f1f4dc26f6b2f6163a0` 已推送至个人 fork；九个无丢包技术格固定前一机制 SHA `7930168f...`，分类修复只影响这些格未触发的丢包分支。交接/状态集成提交会继续移动 HEAD，使用实验时以对应 ID 的元数据为准。十个终态原始结果在个人 fork 忽略目录 `results/<实验ID>/` 与远程 `/home/fnl/lzy/results/<实验ID>/`；原始结果未提交 Git。

## 6. 未解决问题

- BEgressQueue 拒绝入队和链路下线清队列的分支已实现并分类，但这十格未动态触发；若未来将丢包行为作为正式结果，应补专门覆盖。压力探针只验证 MMU 准入丢包，且其 1 MiB buffer 不得与 9 MiB pilot 混作同一效果条件。
- 固定总字节 0/2/4、五个独立 trace seed、完整 16,384 MoE 输入、类别信息增量与背景安全边界均未做。此 pilot 中门控虽被激活，不能证明 HarmGate 所指跨类损害存在。
- 本地队列快照不含下游拥塞，NS-3 PacketTag 不计线上标签成本；正式硬件/协议可实现性未验证。

## 7. 后续推荐动作

1. WS-10 在看原型收益前冻结条件、目标集合、固定总字节设计、独立 trace seed 与预算；按共同 IRN 契约做现象复核，保留负结果。
2. 仅当 WS-10 的损害门槛满足，WS-11 用相同候选/信息范围比较 `shortq2`、类别评分、门控关/开及更强同模型对照；双侧完成率和背景代价同时报告。
3. 若开展正式丢包敏感性或链路故障实验，先补 `queue_reject/queued_drop` 动态覆盖与资源峰值记录。当前代码可用于研究原型，不据此宣布性能优势。

## 8. 与其他工作流的关系

继承 WS-06 的六列 tag、WS-07 的 `dualtrack` 与按 tag 分析、WS-08 的 PFC=0/IRN=1 共同传输。旧四基线源码分派未改；本轮只复跑与新模式直接相邻的 `fecmp/dualtrack` 单类退化。WS-10/11 是独立现象与效果工作流，不由本 Handoff 自动启动。两参考 remote 只读；既存远程工作树和实验结果未改。

## 9. CONTEXT SNAPSHOT

个人 fork `feature/ws09-guardhash-prototype` 从已推送 WS-08 `c45d41d` 分出。`7930168f` 编译通过，九个无丢包正确性/单 seed pilot 格均 `SUCCEEDED` 且队列违规 0；三格 320 流同 trace 的 MoE 批次 `shortq2/guardhash/gate=1.421/1.415/1.49 µs`，背景 P99 相同，门控有 39 次激活、9 次退出。`9c34945` 修复丢包分类，独立压力格 `20260926-025616-ws09-drop-probe` 两类 MMU 准入丢包合计 3,041,296 B、守恒违规 0。十格机器核验见 `docs/research/ws09-validation-summary.json`。工程范围闭环，WS-08 效果 no-go 未变；WS-10 固定总字节/多 seed 与 WS-11 正式强对照仍待后续任务。
