# 工作流台账

更新：2026-09-26。状态只表示**本行定义的范围**，不把功能验证扩展成性能验证。每个工作流结束时产出 Handoff，再由集成工作流核对证据并更新本表。

| ID | 工作流 | 状态 | 已交付 / 下一门槛 | 依赖与归属 |
| --- | --- | --- | --- | --- |
| WS-01 | 科研 Skill 导航 | COMPLETE | [Handoff](../handoffs/2026-09-24-01-research-skills-navigation.md)；论文项目的 15 个 Skill 导航是资料，不是科研结果 | 独立资料工作流 |
| WS-02 | Research Discovery | CHECKPOINTED | [初轮 Handoff](../handoffs/2026-09-24-02-research-discovery.md)、[ANT 交接](../handoffs/2026-09-25-07-ant-project-experience.md)；最新静态画像与双侧损害问题将 GuardHash 本地双候选 v0 列为条件性优先原型，仍待实验否证 | WS-07、WS-08 提供证据；研究选择不启动机制实现 |
| WS-03 | ConWeave 与 maplerime 参考审计 | COMPLETE | [Handoff](../handoffs/2026-09-24-03-reference-repositories.md)；两份只读克隆、fork 演化报告 | 为 WS-02、WS-06 提供源码参照 |
| WS-04 | 本地—远程实验工作流 | COMPLETE FOR MINIMUM RUN | [Handoff](../handoffs/2026-09-24-04-local-remote-workflow.md)；隔离编译/运行/回传和 smoke test，大规模资源上限未验证 | 后续实验复用，不改既存远程工作树 |
| WS-05 | Baseline Fidelity Check | COMPLETE FOR FIDELITY | [Handoff](../handoffs/2026-09-24-05-baseline-fidelity.md)；四模式同输入最小运行与数据流审计，未做正式性能复现 | 为 WS-06、WS-07 提供回归锚点 |
| WS-06 | 六列输入与 tag 通路 | COMPLETE FOR INPUT COMPATIBILITY | [Handoff](../handoffs/2026-09-24-06-six-column-input-and-tags.md)；显式 flow file、五/六列解析、tag 到源 ToR、四模式旧输入回归及四流六列轻量验证；完整 MoE 未运行 | 交付 WS-07 的输入底座；不等于双轨或性能验证 |
| WS-07 | 包/流双轨及 MixTax | COMPLETE FOR MINIMUM DUAL-TRACK AND SINGLE-SEED PILOT | [Handoff 08](../handoffs/2026-09-25-08-ws07-dual-track-mixtax.md)：独立 MoE 分组分析、`dualtrack`、单类/双类正确性、跨 ToR 多下一跳和 packet/flow × 背景 0/64 四格技术 pilot 已核验；无背景逐包批次约 4 ms，正式主实验尚未启动 | 先隔离逐包长尾并冻结共同接收/重传语义，再重跑四格；固定总字节设计样本仅静态验证，未仿真 |
| WS-08 | 接收门槛诊断与共同 IRN pilot | COMPLETE FOR PREFLIGHT AND SINGLE-SEED PILOT | [Handoff 09](../handoffs/2026-09-25-09-ws08-receiver-gate.md)：四个 4 ms 尾流对应末段 RTO；共享 IRN 四格交互 `−0.053 µs`、背景 P99 差 0。**效果主张 no-go**；固定总字节 0/2/4 和五 seed 未仿真。WS-08 当时未实现 GuardHash，后续工程交付见 WS-09 | WS-09 依据 [ADR-007](../decisions/ADR-007-guardhash-prototype-before-efficacy.md) 已做工程原型；效果门槛仍沿用 [实验契约](../research/ws07-dual-track-contract.md) |
| WS-09 | GuardHash/HarmGate 最小原型与正确性 | COMPLETE FOR V0 ENGINEERING AND SINGLE-SEED TECHNICAL PILOT | [Handoff 10](../handoffs/2026-09-26-10-ws09-guardhash-prototype.md)：`shortq2/guardhash/guardhashgate` 模式 13/14/15、真实出口 per-port/per-tag 计数、32 主机单/双类、1280 跨 ToR 四流、旧 `fecmp/dualtrack` 同源码回归和三格同 trace pilot 均核验；另有 16 流受控准入丢包探针。十格机器摘要见 [JSON](../research/ws09-validation-summary.json)，无正式收益主张 | 共同 IRN 契约、固定 SHA/trace 与 [ADR-007](../decisions/ADR-007-guardhash-prototype-before-efficacy.md) 仍约束后续；`queue_reject/queued_drop` 未动态覆盖，WS-10/11 独立推进 |
| WS-10 | 固定总字节与多 seed 现象复核 | ACTIVE FOR PREREGISTRATION AND PAIRED EXPERIMENTS | 先冻结可证伪条件、预算、目标集合与独立 trace seed；运行已静态核验的 0/2/4 固定字节样本资源 pilot，再在预注册场景做五 seed 配对。报告正、负结果与原始数据 | WS-09 单 seed 数值已知，不用它挑场景或调参；共同传输、完成率和 WS-07 判据不变，变更需版本化 |
| WS-11 | 等信息强对照、消融和效果判断 | CONDITIONAL | 仅对 WS-10 成立的场景比较普通短队列双候选、GuardHash 类别信号、HarmGate 开/关、共享/静态隔离及可核查强对照；检验双侧代价与增量 | 类别增量和稳定损害不足则保留负结果，不升级论文机制主张 |
| WS-12 | 边界、成本与论文证据整合 | CONDITIONAL | 若 WS-11 有增量，测错标、反馈延迟、拓扑不对称和状态/线上标签成本；整理可复现图表与局限。若无增量，转为现象/传输机制的解释性结论 | 以 WS-10/11 的原始数据和决定为入口，不把 NS-3 原型称为硬件部署 |

`CHECKPOINTED` 表示研究资料已收口，但研究假设仍开放；各项 `COMPLETE FOR ...` 都只覆盖行内注明的核验范围，不等于论文性能实验完成。对话是否归档不改变工作流状态。
