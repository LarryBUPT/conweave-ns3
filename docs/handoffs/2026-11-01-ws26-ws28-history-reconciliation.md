# WS-26～WS-28 历史状态补全

后续状态：本文件记录本日早先的补全阶段。用户随后明确要求归档前序工作；WS-26 暂停阶段及 WS-27/28 完成阶段的对话现已归档，实际检查、未完成事项和平台结果见[归档交接](2026-11-01-ws26-ws28-archive.md)。下方科学范围和旧阶段记录保持原样。

核对日期：2026 年 11 月 1 日。来源为各原对话最新返回的两至三轮、具体交接和验收报告；本次不重跑仿真或全量 raw 分析。来源文件哈希与实际 Git 观察见 [审计收据](../research/evidence/ws-history-20261101/coverage-and-source-manifest.json)。

## 1. 本对话目标

补足 Integration 权威台账停留在 WS-25、未吸收后续 WS-26/27/28 结论的问题，使 WS-31 能继承实际失败与消融经验。源对话标题、ID 与摘录见 [覆盖表](../project-state/WS_HISTORY_COVERAGE.md)。

## 2. 已确认的项目事实

| 工作流 | 核对结论 | 具体来源 |
| --- | --- | --- |
| WS-26 | 用户暂停；v3 与 v4 r2 的高档筛选 NO-GO，第三候选仍未准入，完整主/敏感性矩阵未完成 | `E:/研/毕业论文/workspace/ws26-classmix-validation/docs/handoffs/2026-10-11-88-ws26-third-signal-admission-design.md`；同目录研究文件 `ws26-failure-cause-and-method-gate.md` |
| WS-27 | 预设比较范围完成：正确性 7/7、资源 24/24、筛选 32/32、独立确认 384/384 | `E:/研/毕业论文/workspace/ws27-guardhash-compare/docs/handoffs/2026-10-13-78-ws27-independent-confirmation.md`；确认分析 SHA-256 `51bdd82a3a5b9f52f88dd037f5a1f9acde3ad46e29370f39d686a69850144038` |
| WS-28 | 预设六项验收完成：原生六臂 144/144（其中新增 96），正式组件消融 120/120，反例诊断 12/12 | `E:/研/毕业论文/workspace/ws28-classreserve-explanation/docs/research/ws28-final-acceptance-audit.md` |

## 3. 已完成工作

读取上述原对话、WS-27 恢复续对话和 WS-26 副对话最新阶段记录，核对工作树及关键本地报告，并将来源文件列入哈希清单。未触碰各分支代码、未覆盖 raw、未把不同阶段格数相加为新独立样本。

WS-26 实际 HEAD 为 `f60c8002057a4ca65b5b31f8610acbb8549aa316`，仍有两个未跟踪草稿：`docs/research/evidence/ws26-queue-front-seed97-plan.json` 与 `scripts/make_ws26_queue_front_plan.py`。副对话最后明确暂停且未访问远端；草稿不是已冻结或已执行实验。

WS-27 实际 HEAD 为 `19112eee446b03623204a412bada2e1429c1ba72`，WS-28 为 `842b96ebd9d2037fd5c7486a41b2f101ead013c9`。这些是本地 Git 观察；本次没有重新查询远端 refs。科学运行版本仍以各实验 ID 的固定 SHA 为准。

## 4. 已形成的设计决策

WS-27 的背景 P99 跨需求中位变化小于 +3% 是当轮用户指定的工程判据。它不能回填 WS-25 的旧 NO-GO，也不保证每份需求安全或形成生产 SLO。WS-28 的整体收益与组件增量分别解释；组件区间跨零不证明等效或永远无用。

WS-26 的失败不能统一归因为机制未触发。v3 已改变选路但批次改善不足；v4 的固定 2:6 类别路径分割实际生效，却使四份筛选需求的业务批次全部变慢。逐区域峰值、累计字节和主机 CNP 汇总不足以唯一解释同一条流的 FCT 差值。

## 5. 当前状态

- WS-26：PAUSED BY USER，保持未完成身份；本轮不恢复，也不新增归档。
- WS-27：COMPLETE FOR PRESET COMPARISON，已有交接但此前未进入本主仓库台账；不自动扩展为类别贡献成立。
- WS-28：COMPLETE FOR PRESET EXPLANATION AND ABLATION，已有最终验收；不以论文范围变化重开已完成原格。

## 6. 未解决问题

旧报告中的机制因果、真实类别可得性、硬件代价和跨场景推广仍分别受证据限制。WS-26 未完成工作不静默转记为 WS-31 的已完成任务；WS-31 可借鉴诊断与代码，但须独立定义新问题和范围。

## 7. 后续推荐动作

WS-31 首先对照类别、候选生成、队列评分、保持策略与传输语义，设计能识别类别信息增量的研究问题。具体机制尚未提出，不因旧失败自动否决类别感知方向，也不直接复制固定路径分割或旧权重。

## 8. 与其他工作流的关系

WS-25 与 WS-27 的 ClassReserve 效应来自不同需求和判据；WS-30 已单独审计差异，不合并为一个胜率。WS-29 后置保留，本次未读取、唤醒或归档。

## 9. CONTEXT SNAPSHOT

WS-26 暂停且未完成，草稿保留；WS-27 的独立比较与 WS-28 的组件/反例解释均已完成预设范围。本次只补项目记忆及源索引，不新增科学结果。后续类别感知研究为 WS-31，主、副职责和门槛见 [执行清单](../project-state/WS31_EXECUTION.md)。
