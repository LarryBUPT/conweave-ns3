# 工作流台账

更新：2026-09-24。状态只表示**本行定义的范围**，不把功能验证扩展成性能验证。每个工作流结束时产出 Handoff，再由集成工作流核对证据并更新本表。

| ID | 工作流 | 状态 | 已交付 / 下一门槛 | 依赖与归属 |
| --- | --- | --- | --- | --- |
| WS-01 | 科研 Skill 导航 | COMPLETE | [Handoff](../handoffs/2026-09-24-01-research-skills-navigation.md)；论文项目的 15 个 Skill 导航是资料，不是科研结果 | 独立资料工作流 |
| WS-02 | Research Discovery | CHECKPOINTED | [Handoff](../handoffs/2026-09-24-02-research-discovery.md)；初轮与混合场景报告、GuardHash 等草案待实验否证 | WS-06、WS-07、WS-08 提供证据 |
| WS-03 | ConWeave 与 maplerime 参考审计 | COMPLETE | [Handoff](../handoffs/2026-09-24-03-reference-repositories.md)；两份只读克隆、fork 演化报告 | 为 WS-02、WS-06 提供源码参照 |
| WS-04 | 本地—远程实验工作流 | COMPLETE FOR MINIMUM RUN | [Handoff](../handoffs/2026-09-24-04-local-remote-workflow.md)；隔离编译/运行/回传和 smoke test，大规模资源上限未验证 | 后续实验复用，不改既存远程工作树 |
| WS-05 | Baseline Fidelity Check | COMPLETE FOR FIDELITY | [Handoff](../handoffs/2026-09-24-05-baseline-fidelity.md)；四模式同输入最小运行与数据流审计，未做正式性能复现 | 为 WS-06、WS-07 提供回归锚点 |
| WS-06 | 六列输入与 tag 通路 | COMPLETE FOR INPUT COMPATIBILITY | [Handoff](../handoffs/2026-09-24-06-six-column-input-and-tags.md)；显式 flow file、五/六列解析、tag 到源 ToR、四模式旧输入回归及四流六列轻量验证；完整 MoE 未运行 | 交付 WS-07 的输入底座；不等于双轨或性能验证 |
| WS-07 | 包/流双轨及 MixTax | PLANNED | 下一工作流：先定共同传输/重排语义及分类观测，做单类与双类正确性；再用固定总负载、独立 trace seed 做配对 pilot | 依赖 WS-06；现象不成立则停止 WS-08 主线 |
| WS-08 | GuardHash/HarmGate 与强基线 | CONDITIONAL | 机制、消融、状态开销、延迟/错标/不对称边界 | 只在 WS-07 的 go 门槛通过后启动 |

`CHECKPOINTED` 表示研究资料已收口，但研究假设仍开放；`COMPLETE FOR INPUT COMPATIBILITY`、`COMPLETE FOR FIDELITY` 和 `COMPLETE FOR MINIMUM RUN` 都不等于论文性能实验完成。对话是否归档不改变工作流状态。
