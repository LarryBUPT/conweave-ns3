# WS-31 channel r2 九节交接

日期：2026 年 11 月 1 日。来源聊天 `01a19323-2201-7b23-a0f1-905c71496d38`，主聊天 `01a19322-95a5-76e3-a4f5-1f1e9dde81ce`。本轮只读复核主修订的 r2 五份 WIP；r1 全部材料保留。

## 1. 本对话目标

按 endpoint-channel-local-review-r2 计划复核 C1～C5、晚绑定与新夹具。只写 independent 下 r2 同名前缀，不修改源码／main，不编译、运行、访问实验服务器或新增执行者。

## 2. 已确认的项目事实

实现树 `E:/研/毕业论文/workspace/ws31-candidates-implementation` 的 HEAD 为 `8cd1ba69469bf80143d5c89edc17fa72611018e8`，分支 feature/ws31-candidates，三份 tracked 修改和两份 untracked。r2 计划 SHA-256 为 `6562ce1cb84f6b1b942b0d2e61982d86203371fc7f977e85e459bbb767b975e0`。五份受审字节匹配计划和主封存，完整哈希见[review](endpoint-channel-local-review-r2-review.json)。

主已接收 r1 完整静态审查，r2 未编译或运行。r1 的原 WIP、review、报告、QA、证据和释放收据未覆盖。

## 3. 已完成工作

已完成计划七项问题，追踪所有新夹具分支，核对旧五参数模板、调用边界、类型检查、编码、部分事务和 marker。删除新增内容后，三个旧文件精确恢复父源。交付[报告](endpoint-channel-local-review-r2-report.md)、review、[证据索引](endpoint-channel-local-review-r2-evidence-index.json)、[QA](endpoint-channel-local-review-r2-qa.json)及本交接。

完成本节点文献复核，重查 DiffFlow v1 与 Flowcut v2 的技术／核验记录及迁移边界。所有事件时序与用例计数均为静态推导，没有新实验结果。

## 4. 已形成的设计判断

结论为 FIX REQUIRED，新增一项 P2 必须修订：DeliverWs31 的 leave 仍按值传入。旧 MakeEvent 在调用函数时复制 std::function；若复制失败，函数体 try 尚未进入，异常仍绕过锁存／Stop，并使旧 ProcessOneEvent 跳过当前事件 Unref。

最小建议是声明、定义同时改为 `const Ws31Leave &`。事件继续拥有 std::function 值，调用时绑定引用；后续按新冻结源验证旧模板适配。C1、C3、C5 与晚绑定修订在源码层成立。C4 只修正了函数体内部异常，C2 只覆盖受控编码域。

## 5. 当前状态

**COMPLETE FOR LOCAL STATIC R2 REVIEW; FIX AND DYNAMIC VALIDATION INCOMPLETE。** 所有科学执行计数为 0，无源码／main 编辑，无提交／推送，无后台任务。

五份 r2 文件的审查冻结已[明确释放](endpoint-channel-local-review-r2-guards-released.json)，不产生执行授权。主可先修订，再冻结新身份与计划；本报告不等同于动态验收通过。

## 6. 未解决问题

必须修 R2-01。建议加强原异常的具体消息／标识断言；现有 helper 只核对异常大类。真实分配器／scheduler 插入失败未测试，边界 hook 不得冒充这些结果。

实际 G1、所有 tag 生产者、共享 PFC／ACK/NACK／CNP／重传、真实 switch、完成回调／saved RX、history、两代网络正反例、独立 C1 V0、匹配消融、业务／背景双侧效果及成本继续必做。原对象循环与事件引用释放必须分开解释。

## 7. 后续推荐动作

主先修 leave 参数，再决定与真实接线共同冻结新源码和执行计划。保留 Receive → leave → pending 的关闭顺序，以及预修改输入拒绝可恢复、修改后失败终态锁存的语义。

新编译与夹具应核对 const 引用适配、事件正常返回、原异常身份、失败后禁止 Finish／接管和全部新增用例。之后按实际 G1 及完整协议覆盖推进两代网络；本轮不启动后继执行，不重跑旧已验项目。

## 8. 与其他工作流的关系

本轮仅向主提供独立材料，不修改权威状态和 main 契约。Ofan、WS-29、旧控制器及旧矩阵均未读取或启动。静态代码修复不新增网络完成数或机制收益，不形成新基线。

## 9. CONTEXT SNAPSHOT

r2 五份冻结 WIP 静态复核完成，FIX REQUIRED，1 项 P2：事件调用前的按值 leave 复制可绕过函数体 catch，建议改 const 引用。精确类型、初始化、事务锁存和用过 channel 拒绝在源码层成立；C2 的真实 G1／生产者和完整共享控制状态仍未实现。报告／review／QA／证据／九节交接已保存，旧 r1 原样保留。五文件冻结明确释放，全部科学执行为 0，无后台任务、无新增执行授权。主修后另冻新源；真实接线、两代网络、V0、双侧效果和成本继续未完成。
