# Handoff 08：WS-07 包/流双轨与 MixTax 技术 pilot

来源：协调任务 `01a0cfac-3176-7590-bf34-c0f176a45118` 派发的「WS-07 包/流双轨及 MixTax」。交接日期：2026-09-25（中国时间）。本交接冻结一个**可核验的技术 pilot 阶段**；没有正式性能比较，也没有实现 WS-08 GuardHash。远程写入遵循 [工作流](../REMOTE_EXPERIMENT_WORKFLOW.md)，旧基线和指标边界遵循论文项目 `docs/research/10-baseline-fidelity-and-dataflow-audit.md`。

## 1. 本对话目标

从 WS-06 的五/六列解析和 tag 通路继续，建立独立的 2.000s MoE 分组分析、共同传输契约与包/流双轨最小模式；先 32 主机、再导入 1280 拓扑做正确性；随后在同一 MoE 子 trace 上进行 packet/flow × 背景 0/64 的资源受控配对诊断，并准备固定总负载、独立 trace seed 的主实验。阶段末向 WS-08 给出可证伪的交接门槛。

## 2. 已确认的项目事实

- 2026-09-25 开工核验：`feature/ws06-flow-tags` 工作树干净，本地与 `origin` 均为 `bd38ca606df66468c717980216c2e8902b83bf27`。从它新建个人 fork 分支 `feature/ws07-dual-track-mixtax`；两个参考 remote 保持只读。
- 四 rail 导入拓扑实际 1280 主机、576 交换机，10ns/100ns 链路并存；现有四份导入 trace 全部只打 rail 0。MoE 16,384 条 8 KiB 流在 2.000s 同启，无轮次字段；背景 0/64/128/192 档增加总字节。画像见论文项目 `docs/research/12-screenshot-lessons-and-mechanism-selection.md` 与其静态 JSON。本阶段只在其 rail 0 上做样本实验，未将合成批次时间称作“八轮 job CCT”。
- `RdmaHw::ReceiverCheckSeq` 在当前 PFC=1、IRN=0 的共同模型下，对乱序包使用 NACK/重传；这不等于有独立的目的端重排缓冲。`dualtrack` 与 `fecmp` 在 pilot 中均使用 DCQCN (`CC_MODE 1`)、相同 PFC、IRN、seed、拓扑和交换机阈值，已由配对脚本检查配置快照。逐包源包数和 OoO CNP 在 pilot 中增加是**实测相关性**；约 4 ms 尾部究竟由哪个定时器或传输分支主导，尚未做隔离因果验证。
- 导入拓扑的 BDP 从实际链路计算为 30,000 B，见 [ADR-005](../decisions/ADR-005-imported-topology-bdp.md)。本轮没有在该拓扑上运行 ConWeave，因此其统一 `one_hop_delay` 时序假设仍未审计。

## 3. 已完成工作

用户授权启动并持续推进 WS-07；代码、实验和取证均由本任务执行。

1. `run.py`/远程控制器登记独立 `dualtrack` (`LB_MODE=12`)。`SwitchNode` 对 `tag=2` UDP 数据以五元组加 `udp.seq` 做确定性逐包 ECMP；`tag=1/0` 和控制包沿原流 ECMP。没有改 DCQCN、PFC、IRN、RNIC 或原四 baseline 算法。模式及分析首个源码提交 `978953d6d80b55d7186855db59c65adcc0f329ee`。
2. `scripts/analyze_moe_tags.py` 从每个实验的 trace 快照建立输入分母，按运行时端口分配规则把原始 FCT 一一匹配回 tag；输出输入/完成/未完成、完成率、FCT 和仅在全数完成时定义的合成批次时间。支持 `--target-trace` 固定目标子集。旧 `scripts/analyze_result.py` 与 2.005s baseline 结果未修改。针对未完成流、固定目标与重复 FCT 的测试通过；WS-06 四流原始 ID 的分析复算为 tag=1/2 各 2/2。
3. 32 主机：`20260925-042134-ws07-small-dual` 双类 4/4；`20260925-043033-ws07-single-class` 按流单类 4/4，`packet_packets=0`；`20260925-044000-ws07-packet-only` 逐包单类 4/4，`packet_multipath=450`。同 trace 的 `20260925-055000-ws07-flow-degen` (`fecmp`) 与按流单类原始 FCT SHA-256 均为 `50eff7c6a0303b2fd91980f737cb8b801857e687942c125ce7a5165b68004d0e`，验证单类退化。
4. 1280 拓扑：`20260925-045000-ws07-1280-four` 四流 4/4，但 `packet_multipath=0`，仅验证单下一跳退化；新跨 ToR trace 的 `20260925-051000-ws07-cross-tor` 四流 4/4、`packet_multipath=30`、缺失 tag 包 0，验证真实多下一跳入口。两 ID 分别保留，不把前者伪称逐包分流证据。
5. 为 pilot 从导入资产以独立 trace seed `20260925` 固定抽取 256 条相同 MoE 流，配原背景 0/64；[manifest](../research/ws07-pilot-manifest.json) 记录源与输出 SHA。另生成 0/2/4 背景的 [固定总字节设计样本](../research/ws07-fixed-load-manifest.json)：目标 MoE 256 条不变，各档总提供字节 35,651,584 B。`scripts/verify_ws07_traces.py` 已核验哈希、rail、起点、MoE 子集及提供字节；固定负载样本**尚未仿真**。
6. 四格资源 pilot 均在固定 `8c99e5407ef41d14a6b67fc7dad55aada273946a` 上、同一拓扑/传输/seed、同档 trace 字节一致地完成。原始数据已下载至各 `results/<实验ID>/`；[版本化摘要](../research/ws07-pilot-summary.json) 由 `scripts/compare_ws07_mixtax.py` 检查配置与输入后生成。远程单仿真、隔离构建 `-j2`；观测 RSS 约 4.3–4.6 GiB，单格仿真墙钟约 3–4 分钟，未扩大到完整 16,384 条 MoE trace。

| 格 | 实验 ID / raw ID | MoE 完成/输入 | MoE 合成批次 µs | 背景完成/输入；P99 FCT µs | 源 ToR MoE 包；OoO CNP |
| --- | --- | ---: | ---: | --- | ---: |
| flow, 0 | `20260925-052000-ws07-pilot-bg0-flow` / `617957504` | 256/256 | 1.415 | 无背景 | 2304；0 |
| packet, 0 | `20260925-053000-ws07-pilot-bg0-packet` / `601752433` | 256/256 | 4002.653 | 无背景 | 4471；601 |
| flow, 64 | `20260925-054000-ws07-pilot-bg64-flow` / `165996234` | 256/256 | 1.625 | 64/64；1206.598 | 2304；0 |
| packet, 64 | `20260925-060000-ws07-pilot-bg64-packet` / `690750426` | 256/256 | 4004.901 | 64/64；1200.713 | 5080；733 |

同档 trace SHA-256 分别为 0 背景 `d60ca03e36f1607328f7af0e79b39f4c9bf74cd0feca8d59f1283de56d778560`、64 背景 `cbfa0e5a95b7c3b6b56dfd563e855dff8b83f4f54db2747909039285184f58e1`。原始 CNP 的 ECN 计数在 flow64/packet64 为 4741/4891，四格 PFC 原始文件均为空。单 seed 的绝对 MoE 交互量为 +2.038 µs，约为 packet0 批次时间的 0.0509%；64 背景 P99 的 packet−flow 为 −5.885 µs。**这些是技术 pilot 的描述值，不是多 seed 推断或机制收益。**

## 4. 已形成的设计决策

- **Decision：**先保留共同原 RNIC NACK/重传语义作为可核验最小双轨基线；不因 tag=2 擅自移植参考 fork 的 MixHash 重排、CNP 或头字段。**Rationale：**只改变选路，才可见共享传输模型的真实限制。**Alternatives：**仅为逐包类特设接收缓冲会使两类和算法传输不一致；若后续选用 IRN 或共同重排能力，必须对四格全部重跑并独立记为新契约。
- **Decision：**当前 pilot 不触发 WS-08。**Rationale：**逐包无背景已经出现约 4 ms 尾部和 601 次 OoO CNP，跨背景交互仅为其基线的 0.0509%，背景侧未见当前 seed 下的实质性损害；数据不足以支持可重复的跨类 MixTax 或类别门控机制。**Alternative：**直接在这一组图上实现 GuardHash，会把接收/重传瓶颈当选路收益来源。
- **Decision：**主实验采用固定目标集合、固定总字节和独立 trace seed；主要指标与 5 seed、4/5 同向、归一化交互中位数 ≥5%、背景 P99 恶化 ≤5%、全类完成率 100% 的门槛见 [实验契约](../research/ws07-dual-track-contract.md)。固定总字节生成脚本已备，不把本次 0/64 加背景 pilot 称作固定负载因果实验。

## 5. 当前状态

WS-07 **COMPLETE FOR MINIMUM DUAL-TRACK AND SINGLE-SEED PILOT**，正式主实验未启动。此处的完成范围是分析入口、单类/双类正确性、导入拓扑多路径入口、单 seed 四格资源 pilot 与可重生 trace 设计。`feature/ws07-dual-track-mixtax` 的四格仿真固定 SHA 为 `8c99e54`；本 Handoff 和状态集成的后续提交会移动分支指针，运行时须重新查 HEAD。原始数据只在个人 fork 忽略的 `results/` 与远程 `/home/fnl/lzy/results/`，不提交到 Git。

一次误在 `20260925-045000-ws07-1280-four` 仍为 RUNNING 时 fetch，本机半成品保留为 `results/.premature-20260925-045000-ws07-1280-four/`，后来已在终态重新下载完整同 ID；远程 ID 未受影响。`scripts/remote_worker.py::fetch_check` 已加终态门槛，并用 RUNNING 的下一实验验证会拒绝提前 fetch。无失败仿真 ID 被删除或覆盖。

## 6. 未解决问题

- **先解决：**识别逐包无背景约 4 ms 尾部的具体机制，设计两类/两算法共同且可解释的接收乱序与重传契约，再重复四格正确性及 pilot。当前“完成 100%”不代表逐包吞吐/尾延迟模型足以做算法收益归因。可能的 NACK、CNP、重传定时器解释属于待验证假设。
- **正式实验仍缺：**固定总字节设计样本未运行，trace seed 仅有 1 个 pilot；没有五个独立 seed、完整 16,384 MoE 输入、误差区间或显著性推断。四份原始 0/64/128/192 文件总字节不同，不可据此归因混合比例。
- 若将 ConWeave 放到导入混合延迟拓扑，先审计统一 `one_hop_delay` 对 Tx/Rx ToR 时序估计的影响；本阶段没有这种对照。仿真 PacketTag 也不代表硬件实际携带标签的线上开销。

## 7. 后续推荐动作

1. 以原始 `*_out_fct.txt`、`*_out_cnp.txt`、`config.log` 定位逐包 4 ms 长尾对应的序号/NACK/CNP/重传路径，给出可测的共同接收契约。可将 IRN/PFC 或统一重排模型作为**另一套**共同配置做小规模敏感性测试；不得只替换逐包类。
2. 同一新契约重新做 32 主机单类、1280 跨 ToR 四流与 0/64 四格；先达到全数完成且无由少数重传主导的极端无背景尾部，再考虑固定总字节 0/2/4 设计和更多独立 trace seed。目标流用 `--target-trace` 单独统计。
3. 只有新契约下达到 [ADR-006](../decisions/ADR-006-conditional-guardhash-selection.md) 与实验契约的稳定、有实际意义损害门槛，才交 WS-08 实现 GuardHash 并比较普通两选等强基线；否则保留负结果和评估资产。

## 8. 与其他工作流的关系

继承 WS-04 的隔离远程工作流、WS-05 的 baseline fidelity 边界和 WS-06 的输入兼容；未改旧四基线分派或旧 2.005s 分析口径。本轮向 WS-08 交付的是一个**条件尚未通过**的诊断结论，不是 GuardHash 代码或正式性能胜出证据。论文项目根目录不是 Git 仓库，版本化状态/Handoff 放在个人 fork；两个参考仓库保持只读。

## 9. CONTEXT SNAPSHOT

分支 `feature/ws07-dual-track-mixtax` 已实现 `tag=2` 逐包、`tag=1/0` 按流的最小模式与独立 MoE 分组分析；32 主机和 1280 跨 ToR 四流均全数完成，按流单类 FCT 与 `fecmp` 原始 SHA 相同。四格资源 pilot 使用 `8c99e54`、seed 20260925 的同一 256 条 MoE 子 trace，0/64 两档哈希和四 ID 见上表；绝对交互 +2.038 µs，仅为逐包无背景 4 ms 批次的 0.0509%，背景 P99 未恶化。严重无背景逐包尾部与 OoO CNP 同时出现，原因待隔离；WS-08 仍 conditional。固定总字节生成器和目标子集分析已备但未运行正式实验。下一步先建立并验证共同接收/重传语义，再重做四格和多 seed 门槛。
