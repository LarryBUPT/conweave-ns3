# WS-31 channel 审查关闭前存档

存档日期：2026 年 11 月 1 日。用户明确要求保留当前节点，准备关闭 Codex。状态为 **CHECKPOINT / REVIEW INCOMPLETE**，没有最终审查通过结论。来源聊天 `01a19323-2201-7b23-a0f1-905c71496d38`；主聊天 `01a19322-95a5-76e3-a4f5-1f1e9dde81ce`。

## 1. 本对话目标

本地只读审查 endpoint-channel-local-review-r1 的五份 WIP，检查原事件包装、账本身份、异常、生命周期和替代 Receive 夹具。当前按用户关闭要求停在内容存档，不启动新执行。

## 2. 已确认的项目事实

父源 `8cd1ba69469bf80143d5c89edc17fa72611018e8`。计划 SHA-256 `5e73c6e98844c393dc63f6e2a1d141d6116af2466b8426156d6378da2c85d20d`。五份 WIP 哈希与计划一致，Git 状态为三份 tracked 修改、两份 untracked；精确路径与哈希见[checkpoint JSON](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-channel-local-review-r1-checkpoint.json)。23 项副本已保存：五份工作字节、三份主材料、十五份固定父源 Git blob，位于[存档证据目录](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-channel-local-review-r1-checkpoint-evidence)。

前项 8cd 对象预检已完成主验并释放；其交付仍在原目录，本次未改动。当前目标没有远端、编译、测试、fixture、网络、提交或推送权限。

## 3. 已完成工作

已读工作流、计划、契约、来源审计及五份 WIP，核前后字节。已定位旧 NS-3 五参数 ScheduleWithContext／MakeEvent、值拷贝类型、既有 virtual Receive、Object TypeId 和异常事件处理源码。正常夹具的静态时序可对应：两次正向在 13 ns 返回，第一次内部新增的反向交付在 16 ns 返回；三个 serial 独立。未执行验证。

## 4. 已形成的审查判断

以下是源码发现，尚未形成完整最终 review，均未运行反例。

- **C1 / P1：** ns-3 TypeId 相等不等于 C++ 动态类型精确相同。未自行注册 TypeId 的 QbbChannel 子类可继承 GetTypeId，同时覆写 TransmitStart，可能被 Bind 接受而绕过包装。最小修复为精确动态类型或同等强度的 setup 来源门，并补拒绝例。
- **C2 / P1：** FlowIDNUMTag 的 int32 ID 实际以 U16 序列化、以 U16 反序列化。`-1` 可成为 65535，65536 可成为 0。当前负标签例可能只因 65535 未登记而被拒绝；未知高位 ID 可别名到已登记 0。恢复后先核 PacketTagList::Add／Peek 的精确 Serialize／Deserialize 调用，再冻结输入身份域或独立全宽观测身份设计；不能直接修改基线 tag 类体来绕过范围约束。
- **C3 / P1：** 新 Tagged helper 只 SetId；父源 tag 构造函数未初始化 flow_size，但 AddPacketTag 序列化会读它。新夹具需在 AddPacketTag 前 SetFlowSize，保留基线类体。

关闭顺序 Receive 返回 → leave 闭合 → pending 减少符合本版明确契约；不恢复旧草案顺序。

## 5. 当前状态

审查未完成，最终报告／review JSON／完整 QA 尚未交付。所有执行计数为 0，未修改实现或 main。无本目标后台驱动或未结束的远端调用。五文件只读约束已按用户关闭要求[显式释放](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-channel-local-review-r1-guards-released.json)，不持有更广泛 source／entry／environment 约束，不产生后继执行授权。

## 6. 未解决问题

继续分析：Receive 异常穿过旧 Simulator::Run 时，ProcessOneEvent 的 Invoke 后 Unref 被跳过，事件及其持有的 channel／ledger 可能泄漏；不要推断夹具必然崩溃，也不能宣称 Destroy 完整回收。还需核 Enter／history／open 分配及 Schedule／动画异常的原子性、失去 session owner 后的绑定、既有设备／channel 循环、绑定前默认事件的遗漏，以及默认分支和 include guard 去除后精确恢复父源的独立核验。

真实 switch、shared-control、完成回调／savedRX、history、G1、两代网络正反例与 V0／双侧效果／成本仍必做，不属于本次已完成内容。

## 7. 后续推荐动作

恢复时先读项目远程工作流，再用本 checkpoint 核计划、HEAD、五份 WIP 工作哈希。若主对话在释放后改了源码，必须使用新冻结计划核新字节，不沿用旧审查结论。然后先补 C2／C3 的 PacketTagList 调用锚点，完成异常与生命周期分析、默认恢复检查、最小修复和测试建议，交付最终本地报告／JSON／QA。**不要启动 SSH、编译或夹具。**

## 8. 与其他工作流的关系

本存档只保存当前审查进度，不整合或改写主状态，不归档未完成工作为已闭环；不启动 Ofan、WS-29、旧控制器或矩阵，不重复已验测试。用户关闭 Codex 不取消当前目标及全部后继验收。已有完成节点及 raw 保持原位置和身份。

## 9. CONTEXT SNAPSHOT

当前为 8cd 上五份未提交 channel WIP 的本地审查，用户要求关闭前存档。五份字节和 15 份父源证据已复制，总 23 项，checkpoint JSON 含完整哈希、已读来源、三个源码发现及待续分析。最终 review 未完成，所有执行为 0，五文件只读约束已显式释放。恢复先验新旧字节，再继续静态审查；若源码变更，用新计划。本次不授权任何执行，真实网络接线与效果验证仍由主承担。
