# 工作流台账

更新：2026-09-25。状态只表示**本行定义的范围**，不把功能验证扩展成性能验证。每个工作流结束时产出 Handoff，再由集成工作流核对证据并更新本表。

| ID | 工作流 | 状态 | 已交付 / 下一门槛 | 依赖与归属 |
| --- | --- | --- | --- | --- |
| WS-01 | 科研 Skill 导航 | COMPLETE | [Handoff](../handoffs/2026-09-24-01-research-skills-navigation.md)；论文项目的 15 个 Skill 导航是资料，不是科研结果 | 独立资料工作流 |
| WS-02 | Research Discovery | CHECKPOINTED | [初轮 Handoff](../handoffs/2026-09-24-02-research-discovery.md)、[ANT 交接](../handoffs/2026-09-25-07-ant-project-experience.md)；最新静态画像与双侧损害问题将 GuardHash 本地双候选 v0 列为条件性优先原型，仍待实验否证 | WS-07、WS-08 提供证据；研究选择不启动机制实现 |
| WS-03 | ConWeave 与 maplerime 参考审计 | COMPLETE | [Handoff](../handoffs/2026-09-24-03-reference-repositories.md)；两份只读克隆、fork 演化报告 | 为 WS-02、WS-06 提供源码参照 |
| WS-04 | 本地—远程实验工作流 | COMPLETE FOR MINIMUM RUN | [Handoff](../handoffs/2026-09-24-04-local-remote-workflow.md)；隔离编译/运行/回传和 smoke test，大规模资源上限未验证 | 后续实验复用，不改既存远程工作树 |
| WS-05 | Baseline Fidelity Check | COMPLETE FOR FIDELITY | [Handoff](../handoffs/2026-09-24-05-baseline-fidelity.md)；四模式同输入最小运行与数据流审计，未做正式性能复现 | 为 WS-06、WS-07 提供回归锚点 |
| WS-06 | 六列输入与 tag 通路 | COMPLETE FOR INPUT COMPATIBILITY | [Handoff](../handoffs/2026-09-24-06-six-column-input-and-tags.md)；显式 flow file、五/六列解析、tag 到源 ToR、四模式旧输入回归及四流六列轻量验证；完整 MoE 未运行 | 交付 WS-07 的输入底座；不等于双轨或性能验证 |
| WS-07 | 包/流双轨及 MixTax | COMPLETE FOR MINIMUM DUAL-TRACK AND SINGLE-SEED PILOT | [Handoff 08](../handoffs/2026-09-25-08-ws07-dual-track-mixtax.md)：独立 MoE 分组分析、`dualtrack`、单类/双类正确性、跨 ToR 多下一跳和 packet/flow × 背景 0/64 四格技术 pilot 已核验；无背景逐包批次约 4 ms，正式主实验尚未启动 | 先隔离逐包长尾并冻结共同接收/重传语义，再重跑四格；固定总字节设计样本仅静态验证，未仿真 |
| WS-08 | GuardHash/HarmGate 与强基线 | CONDITIONAL | 仅在 WS-07 的共同语义、多 seed、固定总字节 go 门槛通过后实现 GuardHash v0，检验相对普通本地短队列二选一的类别信号增量，再做强对照、消融与边界；当前 pilot 未通过 | 依赖 [实验契约](../research/ws07-dual-track-contract.md) 与 [ADR-006](../decisions/ADR-006-conditional-guardhash-selection.md) |

`CHECKPOINTED` 表示研究资料已收口，但研究假设仍开放；各项 `COMPLETE FOR ...` 都只覆盖行内注明的核验范围，不等于论文性能实验完成。对话是否归档不改变工作流状态。
