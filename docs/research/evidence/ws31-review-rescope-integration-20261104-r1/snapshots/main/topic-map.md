# 带证据链的选题地图

## 2026 年 11 月 4 日外评后的执行调整

用户要求据三份评审暂缓或优化。本轮以[外评工作调整](external-review-action-plan-r1.md)和 [current-status.json](current-status.json) 为当前执行入口：C1 条件信息筛查，C2 保留错峰／计时对照，C3 暂缓效果、先查实际回收时序；共同端点新增接线及全部候选效果矩阵暂缓，19 个工作路径和未完成正确性义务保留。九个新提案只作评价和有限机会检查，不自动实现。下文为此前计划与历史证据，不能覆盖本次安排。


日期：2026 年 11 月 1 日。筛选表见 [topic-funnel.csv](topic-funnel.csv)，候选见 [candidates.md](candidates.md)。每条链均从来源进入；预期贡献仍是待验主张。

当前执行已由用户授权为 C1 → C2 → C3 顺序实现与验证。三项首版及[零控制四格](zero-control-node3-handoff.md)已完成，不能据此认定假设或效果成立；最终机制采用仍交用户。新增文献基线受[CCF A/B 规则](baseline-admission-policy-r2.md)约束，Ofan 暂缓。

## 1. 主问题链

| 共识／分歧及来源 | 未解决问题 | 项目切入点 | 预期贡献 | 假设 | 验证路径 | 当前决定 |
| --- | --- | --- | --- | --- | --- | --- |
| K1、X3；[F5/F7](failure-lessons.md)；[P5/P6](literature-evidence.md) | 首包时刻类别有没有队列外信息 | C1：后续突发记账 | 固定 QP 下承诺负载的信息价值与边界 | 类别预算优于当前队列及同状态上限的统一模板 | RQ1 预测 → RQ2 动作／完成 → RQ5 成本 | 首版、核心、零回归及[实际压力重放](evidence/dynamic-c1-main-acceptance-r1.json)及[七格匹配控制](c1-controls-node6-handoff.md)通过；[移除／交换](c13-label-node8-handoff.md)通过；[延迟／部分错误十格](label-dynamic-node11-handoff.md)技术主验通过；[五例适配器](adapter-boundary-node12-handoff.md)主验通过；真实端点生命周期、独立 V0 和效果待验 |
| K2、X2；[P4](literature-evidence.md)；[F6](failure-lessons.md) | 何时细化调度而不支付迁移恢复代价 | C2：有界启动分散 | 计入原起点后，类别启动预算与非迁移选路的协同条件 | 等待成本小于拥塞代价下降 | RQ4 零延迟／统一错峰／大小错峰对照 | 首版、取消、零回归及[原起点非零等待](evidence/dynamic-c2-main-acceptance-r1.json)通过；[决策标签五格](c2-label-node5-handoff.md)通过；[统一／大小控制](c23-controls-node7-handoff.md)通过；[动态标签](label-dynamic-node11-handoff.md)技术主验通过；[十例事件边界](adapter-boundary-node12-handoff.md)主验通过；[新源默认两格](adapter-default-node13-handoff.md)主验通过；真实端点生命周期及效果待验 |
| K4、X1；[P3](literature-evidence.md) | 固定长流借用资源何时能回收 | C3：新 QP 配额与借用 | 不迁移条件下的回收可行域 | 回收时间短于目标活动窗口 | RQ3 残留模型 → 不可回收反例 → 条件性动态诊断 | 首版、核心、零回归及[借用／重激活／残留重放](evidence/dynamic-c3-main-acceptance-r1.json)通过；[固定／大小／未知控制](c23-controls-node7-handoff.md)通过；[移除／交换](c13-label-node8-handoff.md)通过；交换格借用残留代价保留，[动态标签](label-dynamic-node11-handoff.md)技术主验通过，p2 残留 16 包／16,152 B；[两例适配器](adapter-boundary-node12-handoff.md)主验通过；真实端点边界及效果待验 |

## 2. 不成立时如何转向

| 结果 | 解释 | 允许的下一步 |
| --- | --- | --- |
| C1 与同成本无类别记忆相同 | 标签没有可识别增量，记忆可能有价值 | 如实重定位，交用户决定是否研究类别无关机制 |
| C1 优于 QueuePin，但不优于大小／形态控制 | 效果可由可用发送先验解释 | 收缩语义主张；比较先验取得成本 |
| 预测与动作均不同，双主时间不改善 | 规则功能成立但任务价值未成立 | 定位瓶颈与恢复；按冻结门槛停止，不改成功线 |
| C2 仅在平移计时原点后有收益 | 计量错误 | 修复原点，保留错误版本与失败收据 |
| C3 需移动已固定 QP 才有效 | 违反当前候选约束 | 本版本停止；改变传输／路径契约需重新立题 |

## 3. 证据状态图例

已检索：公开页面已访问或进入检索记录。已读全文：仅 P1～P3 的固定版本在主集合内复用完整阅读，并补查关键原文。P4 是已有全文记录的定向复读。P5/P6 是章节级近邻核验，尚未完成全图精读。

已有项目证据：F1～F8 的历史源码、ID 和 raw 入口；新方案均无效果数据。待实验验证：候选全部因果收益、误分类韧性和状态成本。各状态可并存，不能用“已读全文”替代“已验证机制”。

新技术证据：四个零控制的全部请求、原点、FCT 和有序路径一致；仅证明关闭新动作时可恢复公共基线。单输入[载荷重放](v0-technical-replay-r1.md)中，进度扣减的排序比例略高于活动权重，MAE 却更大；完整表保留这一反向观察，不能据此宣布进度信息或类别因果收益成立。

第十三节点补充证据：固定 1f 的 Q12／C2 两格共 208 条完成记录、403,963,904 B，完整 FCT 和有序选路恢复参考。累计为 43 格技术网络，另有 17 例非网络适配器条件。端点账本与测试已固定为 20bc，并通过[第十五节点](endpoint-core-node15-handoff.md)的独立核心预检；[第十四节点](endpoint-ledger-node14-handoff.md)记录资源别名、完成位及快照义务，实际对象快照首版已完成[第十六节点静态审查与修订](endpoint-probe-node16-handoff.md)，新源 8cd 已通过[第十七节点对象预检](endpoint-object-node17-handoff.md)：八组双读、十六项拒绝以及固定来源和完整交付均经主验；mask 127，网络与自然完成为 0。实际 switch／channel／完成回调／G1 接线和真实两代网络验证继续承担后继义务。[原始验收链](evidence/adapter-default-pilot-main-acceptance-r1.json)不覆盖新 WIP，也不替代独立效果。

第十八节点补充：[channel 完整静态审查](endpoint-channel-node18-handoff.md)已核四项 P1／一项 P2，主形成 r2 未编译修订并派唯一副复核。该节点完善了身份、事件返回与失败处理的证据要求；尚无新增网络、预测或双侧效果，不能推升三候选的效果证据等级。

端点接线继续推进：r2 审查要求的回调 const 引用已修订；新增实际交换机目标条目与共享状态只读 WIP，按[九文件计划](endpoint-switch-local-review-r1.json)复核。预期覆盖位 255 只是未编译的组合读取代码，尚无完整快照测量或新网络结果。

## 交换机证据工程进展

[第十九节点](endpoint-switch-node19-handoff.md)确认同纳秒旧端点结果与接口实际归属的两个静态缺口。私有复合 Scope、函数内部即时读取和 owner／index／唯一性守卫已写入；两个真实交换机的语义纯度与原定点清理夹具尚未运行。该进展补充生命周期证据路径，不改变 C1／C2／C3 的效果判断或正式基线状态。

[第二十节点](endpoint-switch-node20-handoff.md)已主核完整 r2 静态审查。新增问题位于异常绑定夹具的指纹，而非三候选的科学规则；最小修订只改一个测试文件，仍需独立复核和实际验证。字段指纹、人工账本门、真实网络完成及效果继续分别验收。
