# Handoff 09：WS-08 前置接收门槛诊断与当前 no-go

来源：协调任务 `01a0cfac-3176-7590-bf34-c0f176a45118` 派发的 WS-08 前置门槛任务；日期：2026-09-25（中国时间）。本交接是技术诊断与单 seed pilot，**没有实现 GuardHash/HarmGate，也没有正式多 seed 性能结论**。详证见 [诊断记录](../research/ws08-receiver-preflight.md)、[机器摘要](../research/ws08-irn-pilot-summary.json)、[WS-07 契约](../research/ws07-dual-track-contract.md) 与 [ADR-006](../decisions/ADR-006-conditional-guardhash-selection.md)。

## 1. 本对话目标

用户要求先定位 WS-07 无背景逐包约 4 ms 尾部，以两类流和 `fecmp`/`dualtrack` 共享的接收/重传语义重跑正确性与四格；再按契约决定固定总字节 0/2/4 与五 trace seed 正式实验的 go/no-go。只有全部门槛通过才进入 GuardHash v0 与强对照。两参考 remote 只读，既存远程工作树和结果不覆盖。

## 2. 已确认的项目事实

- 2026-09-25 开工时，个人 fork `feature/ws07-dual-track-mixtax` 本地与 `origin` 同为 `4649fb1928160c603f7df9ffd6400c091116ab60`，工作树干净；从该已推送集成提交新建 `feature/ws08-guardhash-gate`。`origin` 指向 `LarryBUPT/conweave-ns3`，两参考 remote 的 pushurl 为 `no-push://read-only-reference`。
- WS-07 原始 packet0 `20260925-053000-ws07-pilot-bg0-packet@8c99e5407ef41d14a6b67fc7dad55aada273946a` 的 256 条 FCT 中，仅四条为 4.002–4.003 ms，其余 252 条 ≤2.758 µs。诊断复跑 `20260925-210024-ws08-nack-diagnostic@c8ca6a601dd4380bae36233053b654307d61d292` 与其 FCT SHA-256 同为 `dd922036f6b15f0aee324c9bf9ca1b3c0d4141bc78a3becb655bbdd8004f085e`。新增共享 RDMA 日志记录四个尾流 `255,155,240,91` 各有 `rto_ns=4000000` 的超时，均卡在 `snd_una=8000, snd_nxt=8192`；对应 trace 行和 FCT 已逐流核对。其先前的 seq=8000 包乱序到达、收到 NACK。结合 `ReceiverCheckSeq → ReceiveAck/RecoverQueue → HandleTimeout` 源码，4 ms 尾部由最后 192 B 靠 RTO 补发解释；不能据此排除其他场景的丢包原因。
- 新 pilot 的共同语义是 PFC=0、IRN=1、DCQCN、ACK 间隔 1、相同拓扑/trace/seed；IRN SACK 接收路径与 scratch 的 100/320 µs RTO 对 `fecmp`、`dualtrack`、tag=1/2 一律适用。只读诊断日志和运行器参数扩展不对 tag=2 添加特殊接收能力。四格固定源码 SHA `445593fbc07236e18983d233407265220d360521`。

## 3. 已完成工作

执行由本任务完成，用户此前授权了该门槛诊断；没有将设计样本或单 seed pilot 当正式评测。

1. 增加 `rdma-hw.cc` 的非 IRN 接收 NACK、发送 NACK 和共享超时日志，提交 `c8ca6a6`；隔离 `-j2` 构建并复跑 `20260925-210024-ws08-nack-diagnostic`，原始日志和 FCT 下载至同 ID 的本地忽略结果目录。日志事件共 601 个 RX NACK、571 个 TX NACK、4 个超时；四个超时与四个长尾 flow ID 一一对应。
2. 运行器显式接受并在 metadata 记录 `--pfc 0 --irn 1`，拒绝两者同开/同关，提交 `445593f`。远程 worker 仅部署于 `/home/fnl/lzy/.research-workflow/`；每个实验使用新 ID 与固定 SHA 的隔离源码副本。检查服务器无并行仿真，构建 `-j2`，仿真逐个运行。
3. IRN 正确性：32 主机 flow-only `20260925-213355-ws08-irn-small-flow` 4/4；packet-only `20260925-214018-ws08-irn-small-packet` 4/4、逐包多下一跳 276；双类 `20260925-215232-ws08-irn-small-dual` tag=1/2 各 2/2、逐包多下一跳 24；1280 跨 ToR `20260925-214621-ws08-irn-cross-four` 两类各 2/2、逐包多下一跳 24、缺失 tag 包 0。按流单类与同 trace 的 `fecmp` 对照 `20260925-215842-ws08-irn-small-fecmp` 的原始 FCT SHA-256 均为 `50eff7c6a0303b2fd91980f737cb8b801857e687942c125ce7a5165b68004d0e`，证实共同 IRN 契约下的按流退化。
4. 同 SHA 四格技术 pilot 已全部 `SUCCEEDED` 并回传原始文件。`scripts/compare_ws07_mixtax.py` 验证公共配置、同档 trace、共同 MoE 子集、算法与完成率；摘要为 [ws08-irn-pilot-summary.json](../research/ws08-irn-pilot-summary.json)。

| 格 | 实验 ID | MoE 完成/输入；批次 µs | 背景完成/输入；P99 µs |
| --- | --- | --- | --- |
| flow0 | `20260925-211439-ws08-irn-flow0` | 256/256；1.415 | 无 |
| packet0 | `20260925-210820-ws08-irn-packet0` | 256/256；1.415 | 无 |
| flow64 | `20260925-212042-ws08-irn-flow64` | 256/256；1.625 | 64/64；688.41974 |
| packet64 | `20260925-212745-ws08-irn-packet64` | 256/256；1.572 | 64/64；688.41974 |

四格绝对交互 `−0.053 µs`，相对 packet0 `−3.7456%`；背景 P99 packet−flow `0 µs`。packet64 有 1516 次 OoO CNP，其余格为 0；四格超时计数均为 0，PFC 原始文件均为空。`verify_ws07_traces.py` 再次核验固定总字节 0/2/4 manifest 和 trace，但**未运行**该设计样本。

## 4. 已形成的设计决策

- **Decision：**把 PFC=0、IRN=1 作为一套共同的接收/重传技术敏感性契约；与旧 PFC=1、IRN=0 pilot 分开报告。**Rationale：**现有 SACK 路径可对所有类和算法一致使用，packet0 不再由四个 4 ms 超时决定。**Alternative：**只给逐包类加接收缓冲会改变双方传输公平性；直接缩短 4 ms RTO 会掩盖乱序丢弃而不处理接收语义。
- **Decision：**当前证据下 **no-go 进入 GuardHash v0 和正式扩大实验**。**Rationale：**新的共同契约四格单 seed 交互为负、绝对值很小，背景 P99 无恶化；预先约定的正向 ≥5%、5 seed 中 4/5 同向等门槛没有通过。**Alternative：**为寻找正结果继续运行 0/2/4 或调传输参数会在看到先导数值后改变实验选择；保留现有可重生设计，待新假设和预注册预算再决定。

## 5. 当前状态

WS-08 **COMPLETE FOR PREFLIGHT DIAGNOSIS; MECHANISM NO-GO ON CURRENT EVIDENCE**。已定位原 4 ms 尾部并给出共享 IRN 候选契约，完成单 seed 四格与小规模正确性。固定总字节样本仅静态验证，五个独立 trace seed、完整 16,384 MoE 输入、GuardHash 与强对照均未运行。本 Handoff/状态集成提交会移动分支 HEAD；实验仍固定 `445593f`，执行前重新查询 Git。原始结果保存在个人 fork `results/<ID>/` 与远程 `/home/fnl/lzy/results/<ID>/`，不提交 Git。

## 6. 未解决问题

- 尚无固定总字节 0/2/4 的实际 FCT、资源消耗或类别损害；已有文件不能代替实验。
- 尚无五个独立 trace seed 的稳定性证据，因此本轮 no-go 是**不推进当前机制**，不是证明 MixTax 普遍不存在。若更换接收语义、拓扑或输入规模，应重新冻结契约和门槛。
- IRN packet64 的 OoO CNP 说明乱序反馈仍存在；该 seed 的背景 P99 不变，未证明其他 seed 或更高负载下零代价。

## 7. 后续推荐动作

1. 将本轮负结果与源码/实验 ID 保留为论文问题筛选证据，不为 GuardHash 写机制代码或宣称收益。
2. 若要重启 HarmGate/GuardHash 路线，先提出可证伪的新损害条件和固定预算，再用共同接收契约对固定总字节设计做资源 pilot，预先冻结五个独立 trace seed；逐项满足 WS-07 契约和 ADR-006 后才开机制分支。
3. 若研究转向解释性贡献，可分析 PFC+Go-Back-N 的末段超时条件与 IRN SACK 的差异；不把这项传输修正包装为 GuardHash 的选路收益。

## 8. 与其他工作流的关系

继承 WS-04 隔离远程流程、WS-05 baseline 原始指标口径、WS-06 tag 输入、WS-07 最小双轨。旧四 baseline 源码分派未改；新运行器只放开共同 PFC/IRN 选项。`conweave-project` 与 `maplerime` 两参考 remote 未写入，既有远程工作树和原始结果未覆盖。WS-07 的旧 PFC pilot 仍是有效的技术记录，但不能与本轮 IRN pilot 混合作同一传输条件的性能比较。

## 9. CONTEXT SNAPSHOT

个人 fork `feature/ws08-guardhash-gate` 从已推送 `4649fb1` 分出。原 `dualtrack` packet0 的四条 4 ms 尾流由诊断 ID `20260925-210024-ws08-nack-diagnostic@c8ca6a6` 精确对应四个 `4,000,000 ns` RTO，均只剩最后 192 B 未确认。共同 PFC=0/IRN=1 契约在固定源码 `445593f` 上完成 32 主机单类/双类、1280 跨 ToR 四流以及四格单 seed pilot。四格 MoE 批次 flow0/packet0/flow64/packet64 为 1.415/1.415/1.625/1.572 µs，交互 `−0.053 µs`（`−3.7456%`），背景 P99 相同。固定总字节样本未仿真，五独立 seed 未运行，GuardHash 保持 no-go。原始数据以具体 ID 回查，正文见 `docs/research/ws08-receiver-preflight.md`。
