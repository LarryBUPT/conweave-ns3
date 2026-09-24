# 下一阶段路线与停机条件

更新：2026-09-25。集成工作流只维护顺序和证据门槛；具体代码和实验在对应 workstream 执行。参照 [CURRENT_STATE.md](CURRENT_STATE.md) 的实时快照，在执行前再核验 Git 与远程资源。最新研究筛选见 [Handoff 07](../handoffs/2026-09-25-07-ant-project-experience.md) 和 [ADR-006](../decisions/ADR-006-conditional-guardhash-selection.md)。

已完成的前置门槛：**WS-06 输入兼容**已在 `feature/ws06-flow-tags` 实现，并以四流六列探测与四模式旧五列回归完成轻量核验；证据见 [Handoff 06](../handoffs/2026-09-24-06-six-column-input-and-tags.md)。完整 MoE trace 尚未全量运行。

1. **WS-07 分组分析与双轨基线：**从已核验的 WS-06 代码版本继续。先为 `2.000s` 同步启动的 MoE trace 建立按 tag 的输入数、完成数、未完成数、FCT 与合成批次完成时间；旧 `2.005s` baseline 窗口保持原样。再定义 tag 与选路粒度、接收端语义的关系，确保各算法使用相同拥塞控制、PFC 与重排规则；做单类退化和双类共存小测试。若无法正确处理逐包乱序，应收缩主张或修正模型。若在导入混合延迟拓扑对照 ConWeave，先审计统一 `one_hop_delay` 估计。
2. **WS-07 双向 MixTax：**先以同一 MoE 子 trace 配对比较 packet/flow × 背景 0/64：分别量化背景增加对 MoE 完成时间的额外影响，以及 MoE 逐包选路对背景 FCT 的代价。现有四文件只打 rail 0，且背景字节量随档位增加；将其用于剂量描述，主实验另制固定总负载、可重生的 trace。以独立 trace seed 为重复单位，固定配置并报告 PFC、重传、利用率；小规模 pilot 后冻结主指标、参数及正式重复数。
3. **Go / No-go：**若预先规定的混合条件下没有稳定、可解释的跨类损害，停止把 GuardHash/HarmGate 当主论文机制；可保留负结果与评估资产。若损害存在，才进入 WS-08。
4. **WS-08 GuardHash v0 与强对照：**先检验本地类别占用信号相对普通两选短队列的增量，再与始终共享、静态隔离及可核查的 APS/FLB-like 实现比较。若收益只来自额外即时信息、调参或牺牲背景流，应缩小或放弃机制主张。最后再做拓扑不对称、反馈延迟、错标和资源开销边界实验。

本路线记录研究顺序与门槛；后续工作流按用户指示启动，不因台账状态自动开始代码或远程实验。
