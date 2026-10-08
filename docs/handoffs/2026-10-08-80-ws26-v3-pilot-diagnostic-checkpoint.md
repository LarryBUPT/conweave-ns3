# Handoff 80：WS-26 ClassReserve v3 pilot 诊断检查点

## 1. 本对话目标

继续任务 `01a11568-af40-7ba0-9814-8c462f6bf9e8`（“WS-26 实验副对话：远端唯一 runner 与逐格验收”），完成高档 pilot 终态核对，调查双侧筛选失败，并登记下一项有界诊断。

## 2. 已确认的项目事实

- 分支为 `feature/ws26-classmix-validation`。v2 pilot 固定仿真 SHA 为 `593038416fa16f4982b600d256b563260f9106a8`。
- `high-verified.json` 与 receipts 显示高档 28/28 格全部验收；每格完成 16,576/16,576 流，raw、输入、源码 SHA 和资源收据通过。
- 四个候选诊断格与各自普通格的 FCT SHA-256 一致。预留低档 24 个 ID 尚未启动。
- 原始分析为探索性 pilot：MoE 批次变化中位数 −0.476%，严格改善 2/4；背景 P99 变化中位数 +2.079%，严格改善 1/4。双侧筛选门失败，不能启动低档或正式矩阵。
- 机制覆盖通过：四个 seed 的 `with_background`、`diverted` 均大于零。`with_same_destination` 分别为 334、408、328 和 327。
- 高档 CNP raw 是接收主机汇总。四个 seed 的 OoO 计数、PFC pause 和 resume 均为 0。接收端 ECN 总量相对 ECMP 变化为 −9.34%、+6.13%、−4.19% 和 −12.82%。
- 背景最慢 QP 的接收主机分别为 1272、600、1052、280。对应主机聚合 ECN 计数为 944→973、467→583、1252→1249、489→607。此汇总不能定位单流、标记交换机或因果路径。

## 3. 已完成工作

- 从冻结高档 verified 摘要复算 28 格效果门与机制计数；没有把低档格记作失败或成功。
- 新增 `scripts/diagnose_ws26_v3_pilot.py`，从原始 CNP、PFC、FCT 逐格生成接收主机和尾流诊断；输出忽略目录 `results/ws26-v3-independent-pilot-r2/high-diagnostic.json`。
- 新增 `scripts/make_ws26_v3_diagnostic_plan.py`，冻结 8 个诊断复跑 ID、原始 FCT 哈希、trace 哈希与固定参数；生成[机器计划](../research/evidence/ws26-v3-tail-diagnostic-plan.json)。
- 新增[尾流反例诊断协议](../research/ws26-v3-tail-counterexample-diagnostic.md)。拟用 `ws25_diag=1` 只读记录逐 QP 反馈和逐跳排队；每个新格 FCT 必须与同输入高档 raw 完全一致。
- `py_compile`、诊断脚本、计划生成器及 `git diff --check` 通过。本文档提交前尚未验证个人 fork push。

## 4. 已形成的设计决策

**决定：**保留 ClassReserve v3 高档失败结果，不启动低档；先运行一次 8 格、cap=1 的逐 QP/逐跳诊断复跑。

**依据：**全局接收端 ECN 计数与背景 P99 在三个 seed 上方向不一致。现有高档 raw 不能识别单条尾流的 CNP、路径跳点与排队等待，因此没有足够证据选择权重修正。

**边界：**这组复跑只用于机制诊断，不增加 pilot 独立样本，也不重新估计效果门。若观测仍无法定位可控路径，不能事后增大同目的权重；再决定唯一诊断修正或下一候选。

## 5. 当前状态

WS-26 仍为 ACTIVE。高档 28/28 已验收并触发 NO-GO。低档和正式矩阵均未启动。8 个新诊断 ID 已冻结，尚未查询远端或运行。工作区为 `E:\研\毕业论文\workspace\ws26-classmix-validation`，分支 `feature/ws26-classmix-validation`；本次新增文件尚待提交。

## 6. 未解决问题

- 8 格逐 QP/逐跳诊断及其 FCT 非扰动验收。
- 是否存在证据支持的 ClassReserve v3 唯一修正。
- 独立 pilot 与正式冻结；低档 24 格仅能在高档筛选通过时运行，本轮该条件不成立。
- 长时监督前须确认 GPT-6 Luna High 实际生效；全部诊断 raw 终态并核验后，须在支持切换的线程中实际切至 GPT-6 Sol High 做最终分析。当前调用工具未返回可核验的当前模型状态。

## 7. 后续推荐动作

1. 将本次协议、计划、脚本和状态变更提交并推送个人 fork；核对工作树和 origin HEAD。
2. 在正式启动前确认诊断监督线程实际使用 GPT-6 Luna High；查询全部新 ID、唯一 runner、锁、系统资源和其他用户作业。
3. cap=1 串行执行 8 格，每格 watcher 必须先写入首条资源样本。任何门槛失败即停止后续格。
4. 用固定 FCT 哈希、逐流身份、资源摘要、逐 QP CNP/recovery 计数及逐跳队列/等待记录判断是否支持一项诊断修正。
5. 不启动低档或正式矩阵，除非未来另有符合预设筛选门的合格候选证据。

## 8. 与其他工作流的关系

本阶段属于 WS-26 第一课题机制验证，不改写 WS-25 确认性 NO-GO，也不进入投稿后的状态反馈课题。v1 旧 SHA 的 6 格与失败格继续排除；v2 高档 28 格只作探索筛选。所有新 raw 使用独立 ID。

## 9. CONTEXT SNAPSHOT

WS-26 v2 高档 28/28 格在 SHA `593038416fa16f4982b600d256b563260f9106a8` 下全流和资源验收通过。MoE 批次中位变化 −0.476%（2/4 改善），背景 P99 +2.079%（1/4 改善），故双侧筛选失败、低档 24 格未启动。全局 CNP/ECN 与尾流主机的对应只提供关联，无法定位单流路径。已冻结 8 格 `ws25_diag=1` 非扰动复跑，FCT 必须匹配高档原始 SHA；诊断与模型切换收据待完成。WS-26 保持 ACTIVE。

## 10. 恢复进度（2026-10-08）

本轮恢复确认工作树为 `feature/ws26-classmix-validation`，起始 HEAD 为 `87024a278be872a8a23390295d96376522bab33f`。新增[逐 QP/逐跳分析器](../../scripts/analyze_ws26_v3_tail_diagnostic.py)，逐格核对源提交、输入哈希、完整诊断行、资源收据与预期 FCT SHA，并生成四个 seed 的配对数据。分析器的 Python 语法检查、8 格冻结计划校验和 `git diff --check` 均通过。提交 `dd1d63400997fe78a14d6d72b6e6e72e24098887` 已推送个人 fork，工作树干净。

本轮未访问远端，也未启动实验。当前工具没有返回可核验的模型切换状态，无法确认远端监督阶段所需的 GPT-6 Luna High 已实际生效。低档 24 格和正式矩阵继续关闭。后续先在实际生效的 Luna High 监督上下文核验 8 个新 ID、服务器任务、锁和资源；全部门槛通过后，才按 cap=1 串行运行，并在每格确认 watcher 首条采样。原始数据全数通过分析器后，再切至 GPT-6 Sol High 收束。WS-26 保持 ACTIVE。
