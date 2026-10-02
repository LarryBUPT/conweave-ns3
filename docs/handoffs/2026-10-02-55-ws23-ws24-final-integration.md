# Handoff 55：WS-23/24 最终验收与项目基线汇总

日期：2026-10-02。来源任务：WS-23 `01a0f15f-58c7-7532-84bd-9acaaaa14525`、WS-24 `01a0f1da-f1e2-7870-9361-24b4d626fd76`。本交接只整合证据与范围，不合并两条实验分支的算法源码。

## 1. 本对话目标

完成 2026-09-30 被纠正的 WS-23/24 必做验证，保持实验、修复、重验闭环；用户最终把 WS-24 限定为远程服务器上的 ns-3 合成模拟，不要求真实主机或网卡数据。两任务全部预设验收和结论对应后汇总到个人 fork 项目状态，并归档来源任务。

## 2. 已确认的项目事实

- WS-23 执行分支 `feature/ws23-validation-execution@e3919171e5d00711f13c9f5465209accac201766`，最终隔离矩阵仿真 SHA `3db2685a3540895bf49e25302bd00465bc0921e2`。本地重跑 `python scripts/verify_ws23_isolation_pilot.py --source-sha 3db2685a3540895bf49e25302bd00465bc0921e2 --revision 3` 返回 18/18 与 `exploratory_positive=false`。完整过程与逐格 ID 见该分支的[结果报告](https://github.com/LarryBUPT/conweave-ns3/blob/e3919171e5d00711f13c9f5465209accac201766/docs/research/ws23-isolation-matrix-r3-report.md)、[机器摘要](https://github.com/LarryBUPT/conweave-ns3/blob/e3919171e5d00711f13c9f5465209accac201766/docs/research/evidence/ws23-isolation-matrix-r3-summary.json)和[执行清单](https://github.com/LarryBUPT/conweave-ns3/blob/e3919171e5d00711f13c9f5465209accac201766/docs/project-state/WS23_WS24_VALIDATION_PLAN.md)。
- WS-24 执行分支 `feature/ws24-multinic-validation@11a40fd5f9ba5c2811ecc8172f7d30dddda223ba`，正式 48 格仿真 SHA `3b992eed218f65b4f8026eddb5170a7694e17b10`，manifest SHA-256 `e2d19ce3d7424f556bebcd74f011310538cf89c55bc2937c985e922af2b1c536`。本地重跑 `verify_ws24_independent_matrix.verify_matrix` 返回 48/48 格、12 个独立合成 job，机器结果与提交的[摘要](https://github.com/LarryBUPT/conweave-ns3/blob/11a40fd5f9ba5c2811ecc8172f7d30dddda223ba/docs/research/evidence/ws24-independent-synthetic-effects-summary.json)完全相同；[报告](https://github.com/LarryBUPT/conweave-ns3/blob/11a40fd5f9ba5c2811ecc8172f7d30dddda223ba/docs/research/ws24-independent-synthetic-effects-report.md)记录 1,056 个远端/本地文件哈希一致、资源门槛和旧失败 ID 的排除。
- 两分支在 2026-10-02 核对时本地与各自 `origin` 分支同 SHA，工作树干净。原始结果在各独立 checkout 忽略的 `results/<实验ID>/` 及远端 `/home/fnl/lzy/results/<实验ID>/`；Git 只保存协议、验收器、报告与收据，不把 raw 当作版本库文件。

## 3. 已完成工作

- WS-23 补全 IRN×PFC 传输恢复：旧 16×1 MiB 压力反例、无损 pause/resume、定向延期 control/probe 和跨类干扰因果门槛均按独立 ID 验收。最终 18 格同输入探索中，2301/2302 的类别项未改变选择；2303 背景改善但最慢竞争流受损。预设双侧正向条件未通过，隔离效果 **NO-GO**。
- WS-24 完成多 NIC 合成模型、旧格式四 baseline 回归、目标拓扑、CNP 与同 SHA point-to-point 单测；旧 A/B/C/D 14 格仅各自按工程正确性和单 seed pilot 解释。正式独立合成 job 四臂 48/48 格从 raw 重算，12/12 个 job 的多 rail 完成跨度较短，主效应中位配对差 **−19.667%**，预设精确双侧符号检验 `p=0.00048828125`。`j02` 极端值、`j11` 微小值和 `j09` 放置差异均列为反例/幅度边界。
- WS-23 原资源缺失、排序错误等失败 ID 和 WS-24 首版缺资源收据的 `j01-fs` 均保留并排除；修复后使用固定 SHA/新 ID 重验，不覆盖旧 raw。

## 4. 已形成的设计决策

用户明确选择仅 ns-3 模拟，不要求真实 physical-host/NIC/job/rank 数据；该决定改变 WS-24 的验收范围，但不把合成结果写成真实硬件或业务收益。见 WS-24 分支的 [ADR-009](https://github.com/LarryBUPT/conweave-ns3/blob/11a40fd5f9ba5c2811ecc8172f7d30dddda223ba/docs/decisions/ADR-009-ws24-ns3-only-scope.md)。用户随后明确论文研究背景为包流混合负载均衡，机制和实验方法可为目标调整；以 WS-11/12 的既有流量分布与档位为主，允许同分布新独立 seed，不新增流量类型/档位。后续两课题以负载均衡为主、乱序代价为次，第一课题类别感知选路与第二课题有成本、有时效的下游状态反馈选路。每课题至多三个候选版本、每版至多一次诊断修正；均失败则停下复盘，不无限调参。成果链路为第一课题初步结论、独立数据验证、小论文完成并投稿、第二课题结论、大论文行稿；录用/见刊另行跟踪。这些是后续研究方向，不会追认 WS-23/24 为论文两个课题的正向结论。主对照、指标和时间目标已在交接后由用户确认，见 [ADR-010](../decisions/ADR-010-sequential-mixed-lb-paper-plan.md)；具体双侧数值门槛仍待独立 pilot 后冻结。

## 5. 当前状态

**WS-23 COMPLETE FOR PRESET NS-3 SYNTHETIC CORRECTNESS AND ISOLATION EXPLORATION; EFFICACY NO-GO。WS-24 COMPLETE FOR PRESET NS-3 SYNTHETIC MULTI-RAIL × PLACEMENT VALIDATION。**本交接只对应各任务预设范围；WS-10/11/12 的历史 NO-GO 不被重判。两任务已满足用户要求的来源对话归档条件；归档不删除源码或原始结果。

## 6. 未解决问题

论文目标的新型包流混合负载均衡机制尚无达到预设双侧条件的正式正向结论。WS-24 比较的是固定合成 320-host×4-NIC 下单/多 rail 与受限 rank 交换，既非真实网卡验证，也非 ConWeave/逐包逐流新算法在 WS-11/12 混合分布上的收益。第二论文课题结论及发表里程碑尚未完成；后续实验上限、独立样本与指标待用户继续明确。

## 7. 后续推荐动作

用户已完成研究范围澄清，下一步按 [ADR-010](../decisions/ADR-010-sequential-mixed-lb-paper-plan.md) 优先准备第一课题的原始五模式兼容性、正确性与独立 pilot，再冻结同输入对照、数值门槛和停止规则。只用远程服务器 ns-3；本交接不自动新增远程实验或创建新任务。小论文投稿是进入第二课题的里程碑；录用/见刊另行跟踪。

## 8. 与其他工作流的关系

WS-23 是传输恢复正确性与隔离候选负结果；WS-24 是合成多 rail/placement 结果。WS-25 或论文证据整合只能引用这两者的证据等级和限制，不能把 WS-23 的 NO-GO 改写为收益，也不能把 WS-24 的合成 job 统计结果放大为真实业务或包流混合新机制的论文主张。来源分支实验源码各自保留，不在本状态分支做未经验证的算法合并。

## 9. CONTEXT SNAPSHOT

2026-10-02：WS-23 18/18 有效隔离格，`exploratory_positive=false`；WS-24 48/48 独立合成 job 四臂格，12/12 主效应负、中位 −19.667%，仅 ns-3 合成范围。两分支已推送且干净。论文研究以现有逐包/逐流混合分布为主；每课题最多三版、每版一次诊断修正，主对照和指标见 ADR-010；双侧数值尚待 pilot，不得把上述任务闭环等同于论文成果链闭环。

交接后用户完成研究范围问答并确认共同理解；现行两课题顺序、原始仓库五模式主对照、指标、独立需求和一个月成稿目标见 [ADR-010](../decisions/ADR-010-sequential-mixed-lb-paper-plan.md)。数值门槛、独立最终样本量和新实验身份仍未冻结。
