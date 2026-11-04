# WS-31 switch 首版审查九节交接

日期：2026 年 11 月 1 日。来源聊天 `01a19323-2201-7b23-a0f1-905c71496d38`，主聊天 `01a19322-95a5-76e3-a4f5-1f1e9dde81ce`。

## 1. 本对话目标

审查 endpoint-switch-local-review-r1 的九份冻结 WIP。复用已验 channel r2 分析，仅核 const 引用／异常消息差异，以及新 switch 范围、键、只读接口、覆盖位和最小后继夹具。所有科学执行授权为 0。

## 2. 已确认的项目事实

实现树 `E:/研/毕业论文/workspace/ws31-candidates-implementation` 的 HEAD 为 `8cd1ba69469bf80143d5c89edc17fa72611018e8`。九份 WIP 的工作哈希和主封存匹配。计划 SHA-256 为 `728a26f076559fd10165798a6d934994ad3c538a2a1a1f5692a19c3f1d485a2c`。完整身份见[review](endpoint-switch-local-review-r1-review.json)。

新 probe 尚未编译／运行，没有 mask 255 实测证书。r1／r2 channel 原字节与审查均保留。

## 3. 已完成工作

已逐项完成计划六项分析，核对新的 const 查询、实际四元组来源、33～50 模式表、NodeList／node／device getter 和清理语义。独立确认删除新增接口／friend 后，budget、quota、switch-node 三头文件精确恢复父源。

channel 两行签名与新增消息断言匹配 r2 建议；未重复审查或执行其未变用例。交付[报告](endpoint-switch-local-review-r1-report.md)、review、[证据索引](endpoint-switch-local-review-r1-evidence-index.json)、[QA](endpoint-switch-local-review-r1-qa.json)及本交接。完成 DiffFlow v1／Flowcut v2 的本节点参考复核。

## 4. 已形成的设计判断

FIX REQUIRED：S1 / P1 为端点 Observation 未绑定 switch 的同一范围与不可交错读取步骤。节点数量和同纳秒时间不够；真实旧结果可在同纳秒接口／队列变化后被接受。S2 / P2 为接口只有槽位指针冻结，缺少 owner、实际 ifIndex、非空和唯一性检查。

建议共享冻结范围并原子组合实际 endpoint／switch 读取；在 Capture 与 Validate 复核实际设备绑定。保持 const 查询、不借读触发清理、目标状态与共享状态分列。channel R2-01 已在源码层修正，编译门仍未通过。

## 5. 当前状态

**COMPLETE FOR LOCAL STATIC SWITCH REVIEW; FIX AND DYNAMIC VALIDATION INCOMPLETE。** 源码未变，无编译／夹具／网络／远端执行，无提交／推送，无新增代理或后台驱动。

九文件审查冻结已[明确释放](endpoint-switch-local-review-r1-guards-released.json)，没有更广泛约束或后继执行授权。

## 6. 未解决问题

S1／S2 必须处理。实际 switch 对象的同刻双读纯度、拒绝、到期不清理、未命中不插入、定点清理保留其他 tuple／共享历史等夹具尚未写或运行；具体要求见报告第 4 节。

真实 G1／所有身份生产者／共享协议、完成回调／saved RX、history、channel／held copy、两代网络、独立 C1 V0、三候选匹配消融、业务／背景双侧效果及成本继续必做。mask 数字不代表排空状态或真实网络完成。

## 7. 后续推荐动作

主先修范围来源、读取原子性和接口绑定，再冻结实际对象夹具与新源。纯度指纹应在 Capture 之后取，覆盖实际表内容／deadline／totals／共享活动及引用绑定；不要用会改变状态的 Pressure、Value 或日志清理路径来检查纯度。

夹具使用真实对象和真正 EndpointProbe::Read，单列人工种入的状态与生产协议证据。清理只在原排空门后进行，保留无关 tuple 与共享历史。后继执行需另有冻结计划，本次不启动、不重跑旧已验项目。

## 8. 与其他工作流的关系

本轮只写 independent 同名前缀材料，不改 main、权威项目状态、科学源或旧收据。文献复核不构成算法准入。Ofan、WS-29、旧控制器及旧矩阵未开展，没有新基线或性能结论。

## 9. CONTEXT SNAPSHOT

switch 首版九文件静态审查完成，FIX REQUIRED，1 项 P1 加 1 项 P2：端点结果与 switch 范围／读取步骤未绑定，接口 owner／ifIndex／唯一性未检查。const 表查询和四元组对应成立；目标与共享状态分列正确。channel 的 const 引用和三条异常消息断言在源码层对应 r2 修复。报告／review／QA／证据／交接已保存，旧材料不改，九文件冻结明确释放，所有科学执行为 0，无后台工作或新增执行授权。主先修并写实际对象纯度／拒绝／清理夹具，再另冻计划；真实接线、两代网络、V0、双侧效果和成本仍未完成。
