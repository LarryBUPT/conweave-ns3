# WS-31 channel 静态审查九节交接

日期：2026 年 11 月 1 日。来源聊天 `01a19323-2201-7b23-a0f1-905c71496d38`；主聊天 `01a19322-95a5-76e3-a4f5-1f1e9dde81ce`。主对话发来恢复指令，限定为原计划的本地只读审查。旧关闭检查点保持未完成身份，本轮另交最终审查。

## 1. 本对话目标

完成 endpoint-channel-local-review-r1 的静态审查。范围包括五份冻结 WIP、默认路径、旧调度模板、账本身份、异常、生命周期及替代 Receive 夹具。仅允许写 independent 目录下同名前缀材料；不执行科学程序。

## 2. 已确认的项目事实

实现树为 `E:/研/毕业论文/workspace/ws31-candidates-implementation`，父源和当前 HEAD 均为 `8cd1ba69469bf80143d5c89edc17fa72611018e8`。计划 SHA-256 为 `5e73c6e98844c393dc63f6e2a1d141d6116af2466b8426156d6378da2c85d20d`。五份工作字节与原计划一致；三份 tracked 修改、两份 untracked。

完整哈希和锚点见[review JSON](endpoint-channel-local-review-r1-final-review.json)。[证据索引](endpoint-channel-local-review-r1-final-evidence-index.json)引用旧 23 项快照，另保存 7 份父源及 6 份文献记录，共 36 项。旧检查点、旧 QA 和旧释放收据均未覆盖。

## 3. 已完成工作

本轮补齐 Packet → PacketTagList 的真实序列化锚点、TypeId 构造链、异常事件引用释放、交付前部分失败、setup 时序和对象引用关系。独立检查删除新增观察内容后，channel 两文件和 tag 头文件均精确恢复父 Git blob。

计划六项问题均已作答，交付[最终报告](endpoint-channel-local-review-r1-final-report.md)、review JSON、[QA](endpoint-channel-local-review-r1-final-qa.json)和本交接。正常事件时序仍属静态分析；没有把预期输出当作实测。

本重要节点已完成文献复核：DiffFlow v1 与 Flowcut v2 的技术附件、核验记录和固定 PDF 哈希均已核对。适用条件、与事件 token 的差异、不可外推的结论记入报告第 6 节。

## 4. 已形成的设计决策

结论为 FIX REQUIRED，共 4 项 P1 和 1 项 P2：C1 精确动态类型门不足；C2 U16 身份别名；C3 新夹具缺少 flow_size 初始化；C4 旧模拟器外抛异常跳过当前事件 Unref；C5 Enter／调度／动画／绑定部分失败未完整锁存。

保留当前正确的关闭顺序：Receive 完整返回 → leave 闭合 → pending 减少。保留基线 tag 类体，最小初始化修复放在新 helper；身份域或全宽身份设计由主另行冻结。C4 可选择事件内捕获并在 Run 外报告，或明确一次性终止进程范围，不修改旧模拟器来迎合夹具。

以上是审查建议，未替主选择或实现新方案。共享 State 避免回调捕获 session 裸 this，但不能当作 teardown 全回收或完整排空的证明。

## 5. 当前状态

**COMPLETE FOR LOCAL STATIC REVIEW; IMPLEMENTATION AND VALIDATION INCOMPLETE。** 审查通过范围与修复范围严格区分。源码没有变化，没有提交或推送。没有本任务后台执行者，没有新增副代理。

本轮及当前目标所有科学执行计数均为 0。五文件审查约束已[显式释放](endpoint-channel-local-review-r1-final-guards-released.json)，旧关闭收据另存不动。释放只结束本轮冻结，不产生执行授权。

## 6. 未解决问题

主必须处理 C1～C5，并明确三项接线约束：所有相关发送前完成 Bind；正常 owner 存活至 Finish；完整记录共享控制包、设备及历史状态。Receive 返回只能结束当前事件，不能代替端点完成、网络交付成功或跨代复用认证。

G1、真实 switch 纯读、完成回调／savedRX、history、两代网络正反例、独立 V0、三候选匹配消融、业务／背景双侧效果及状态／运行成本仍必做。Ofan 暂缓，不开启 WS-29、旧控制器或旧矩阵。

## 7. 后续推荐动作

主先按报告的精确锚点修复。输入拒绝保留可恢复语义；修改开始后的异常必须终态锁存，不能伪造闭合。对 C4 明确终止／恢复契约，对 C2 明确编码前身份约束或新观察身份。

修复后重新冻结源字节和计划，再按 T1～T9 编排最小验证。建议与 switch／完成回调／history／G1 接线共同冻结，避免重复全量构建未进入真实路径的版本。新的动态执行由主授权的计划承担；本次不启动任何后继运行，也不重跑原已验对象预检。

## 8. 与其他工作流的关系

当前仅向主交付独立审查，不修改 main 契约、权威项目状态、科学源或旧证据。报告第 6 节的文献借鉴不构成新机制准入。已有实际对象预检及旧技术网络证据保持各自身份，本轮没有重新审计其 raw，也没有追加其完成数。

## 9. CONTEXT SNAPSHOT

8cd 上五份原 WIP 的本地静态审查已完成，FIX REQUIRED，4 项 P1 加 1 项 P2。默认路径和 tag guard 可精确恢复父源；正常五参数事件包装及关闭顺序静态对应成立。类型门、U16 别名、夹具未初始化大小、异常事件引用和部分失败锁存必须处理。36 项证据索引、最终报告、review JSON、QA 与九节交接均在同名前缀下。旧未完成检查点保持原样。所有科学执行为 0，五文件冻结明确释放，无后台工作、无新增执行授权。主修复后另冻新源与计划；真实接线、两代网络、V0、双侧效果及成本继续必做。
