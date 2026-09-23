# 工作流台账

更新：2026-09-24。状态只表示**本行定义的范围**，不把功能验证扩展成性能验证。每个工作流结束时产出 Handoff，再由集成工作流核对证据并更新本表。

| ID | 工作流 | 状态 | 已交付 / 下一门槛 | 依赖与归属 |
| --- | --- | --- | --- | --- |
| WS-01 | 科研 Skill 导航 | COMPLETE | 论文项目 `计算机网络科研Skills导航_精选15/README.md`；导航资料，不是科研结果 | 独立资料工作流 |
| WS-02 | Research Discovery | CHECKPOINTED | 初轮与混合场景报告、最新 GuardHash 等草案；待实验否证 | WS-06、WS-07、WS-08 提供证据 |
| WS-03 | ConWeave 与 maplerime 参考审计 | COMPLETE | 两份只读克隆、fork 演化报告；必要时按固定 SHA 复核 | 为 WS-02、WS-06 提供源码参照 |
| WS-04 | 本地—远程实验工作流 | COMPLETE FOR MINIMUM RUN | 个人 fork、脚本、隔离编译/运行/回传和 smoke test；大规模资源上限未验证 | 后续实验复用，不改既存远程工作树 |
| WS-05 | Baseline Fidelity Check | COMPLETE FOR FIDELITY | 四模式同输入最小运行、原始数据和数据流审计；未做正式性能复现 | 为 WS-06、WS-07 提供回归锚点 |
| WS-06 | 六列输入与 tag 通路 | NEXT | 显式 flow file、五/六列解析、tag 传播、小拓扑正确性、旧基线回归 | 基于个人 fork 新开发分支；先于 WS-07 |
| WS-07 | 包/流双轨及 MixTax | PLANNED | 固定传输/重排语义、同轨迹配对、固定总负载 trace、独立 seed | 依赖 WS-06；现象不成立则停止 WS-08 主线 |
| WS-08 | GuardHash/HarmGate 与强基线 | CONDITIONAL | 机制、消融、状态开销、延迟/错标/不对称边界 | 只在 WS-07 的 go 门槛通过后启动 |

`CHECKPOINTED` 表示研究资料已收口，但研究假设仍开放；`COMPLETE FOR FIDELITY` 和 `COMPLETE FOR MINIMUM RUN` 都不等于论文实验完成。对话是否归档不改变工作流状态。
