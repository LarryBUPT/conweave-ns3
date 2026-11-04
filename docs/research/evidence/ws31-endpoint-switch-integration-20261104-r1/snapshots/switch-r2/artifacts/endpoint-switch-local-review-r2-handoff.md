# WS-31 switch r2 九节交接

日期：2026 年 11 月 4 日。来源聊天 `01a19323-2201-7b23-a0f1-905c71496d38`，主聊天 `01a19322-95a5-76e3-a4f5-1f1e9dde81ce`。

## 1. 本对话目标

继续同一 endpoint-switch-local-review-r2 的本地静态审查。原 turn 因 usage limit 失败，未交付最终审查；恢复不新增目标、不改变原计划。只读十文件源码，只写 independent 同名前缀。

## 2. 已确认的项目事实

HEAD 为 `8cd1ba69469bf80143d5c89edc17fa72611018e8`，十份当前及主封存 WIP 与原计划一致。计划 SHA-256 为 `950104b5c26805437f7dab8a877176a20ae9dd2be15d0ab1a65b75488780b775`。五份 channel 文件未变，复用已接收分析。

原失败 turn `01a19786-5399-7631-a7c8-c0517ab25c14` 和终态 cursor `d0b9dd1a-3dbb-4cea-9a35-6aefe1b3ed0d:1` 保留。恢复时没有既有 r2 交付；[恢复收据](endpoint-switch-local-review-r2-resume-receipt.json)与[进度收据](endpoint-switch-local-review-r2-progress-r1.json)保持当时未完成身份。

## 3. 已完成工作

按要求顺序确认工作流、执行清单、registry 和主状态，核原计划／HEAD／十文件。承接此前阅读，补齐夹具 helper、底层队列／RDMA 初始化、旧 API、纯度范围、全部断言及清理算术。

完成计划七项问题，交付[报告](endpoint-switch-local-review-r2-report.md)、[review](endpoint-switch-local-review-r2-review.json)、[QA](endpoint-switch-local-review-r2-qa.json)、[证据索引](endpoint-switch-local-review-r2-evidence-index.json)及本交接。完成 DiffFlow v1／Flowcut v2 的本节点参考复核。

## 4. 已形成的设计判断

FIX REQUIRED，新增 R2-F1 / P1：owner 变更用例的 state 指纹依赖已改坏的 owner 角色，将 switch 设备当主机读取；其 QP group 未绑定，在预期 Read 守卫前解引用空组。应安全序列化错误绑定与可选对象，或按遍历／捕获角色选择协议字段，禁止指纹替测试修状态。

S1 的私有组合 Scope／内部实际 Read，以及 S2 的 owner／index／唯一性检查，在源码层对应成立。没有新的确定性 C++11／旧 API 编译问题证据，实际构建仍未验证。

## 5. 当前状态

**COMPLETE FOR LOCAL STATIC R2 REVIEW; FIX AND DYNAMIC VALIDATION INCOMPLETE。** 全部科学执行为 0，源码／main 未改，无提交或推送。25 组双读、63 次组合 Read、19 次拒绝仅为修复后的源码计划量，当前没有实测结果。

十文件审查冻结已[明确释放](endpoint-switch-local-review-r2-guards-released.json)。无后台驱动、额外代理、更广泛约束或新增执行授权。原配额失败不改写为成功。

## 6. 未解决问题

R2-F1 必修；其后 history／队列／token／清理等分支尚不能认定可达。端点指纹是明确字段范围，不覆盖整个对象或所有队列状态；duplicate-device 例可能先被接口数／index 拒绝，不能声称独立覆盖唯一性分支。

真实完成回调／saved RX、history、G1／生产者身份／共享协议、channel／held copy、两代网络、独立 C1 V0、匹配消融、业务／背景双侧效果及成本仍必做。

## 7. 后续推荐动作

主先修错误 owner 状态下的指纹，再冻结新源与执行计划。新夹具应明确原始异常／拒绝原因，记录实际到达的分段和完整字符串比较，核 K2、共享历史、deadline／totals 和 stored liveBorrowed 的清理后语义。

保持当前读取纯度和先排空再定点清理的门。18 模式是读取准入覆盖；人工 ACK_COMPLETE 和两个 token 不是真实传输。后继实际执行需新计划，不重跑旧成功项目。

## 8. 与其他工作流的关系

本轮不修改 registry、主状态、main 契约或科学源；历史索引的滞后字段不覆盖实际计划与当前哈希。Ofan、WS-29、旧控制器／矩阵没有开展。没有形成新基线、完整网络证书或性能结论。

## 9. CONTEXT SNAPSHOT

原 switch r2 同计划恢复审查已完成，FIX REQUIRED，1 项 P1：owner 拒绝例先在指纹中解引用 switch 的空 QP group。S1／S2 源码修订对应成立，后续夹具断言需修复后才可验证。十文件及 HEAD 匹配原冻结，五份 channel 分析复用；报告／review／QA／证据／交接完整保存，配额失败和阶段收据原样保留。十文件冻结明确释放，所有科学执行为 0，无后台任务或新增执行权。主修后另冻源与计划；真实接线、两代网络、V0、双侧效果和成本继续未完成。
