# 整合构建与 C2 生命周期预检九节交接

日期：2026 年 11 月 1 日。来源副对话 `01a19323-2201-7b23-a0f1-905c71496d38`；接收主对话 `01a19322-95a5-76e3-a4f5-1f1e9dde81ce`。

## 1. 本对话目标

原目标是整合源码完整构建、Ofan 核心测试及 C2 非网络取消测试。构建在途时，用户明确暂缓 Ofan，并要求新增基线只接受已核实发表于 CCF A/B 类会议或期刊的机制。修订目标为完成在途整合构建及 C2 Stop/Dispose 测试；尚未启动的 Ofan 专门测试、动态覆盖和 RR 对照取消。

已从主对话核到直接用户消息，turn 为 `01a1940b-da42-7d93-ac39-164e1a614ffb`，消息为 `01a1940c-3b71-7db2-bb38-0c11dedf679b`。见[范围变更收据](ofan-preflight-r1-scope-change.json)及主的[新增基线政策](../main/baseline-admission-policy-r2.md)。这是用户调整范围，不是正确性失败。

## 2. 已确认的项目事实

固定个人 fork 提交为 `c4b6039beb47e667e6954b56ec770cb6038082fa`，分支为 `feature/ws31-candidates`。本地只读来源为 `E:/研/毕业论文/workspace/ws31-candidates-implementation`，开始时干净、已推送且参考 remote 禁止推送保护有效。相对上一版 `bc4de1e943866f7630545ce5665cb3525084dda2`，worker 只增加 Ofan/RR 的模式 choices，未改锁、资源门、构建和并发规则。

## 3. 已完成工作

新鲜资源门通过：无其他普通用户作业、编译或仿真进程，无登录会话；40 个逻辑 CPU，1 分钟负载 0.01，可用内存 122.524 GiB、空闲盘 2382.689 GiB。deploy、sync、build 均返回 0，部署 worker 哈希一致。固定远端副本建立后已通知主。

独立 ID 为 `20261101-061544-ws31-ofan-preflight-r1`；源为 `/home/fnl/lzy/runs/20261101-061544-ws31-ofan-preflight-r1/source`，结果为 `/home/fnl/lzy/results/20261101-061544-ws31-ofan-preflight-r1/`。optimized `-j2` 构建完成 1463 项任务，用时 354.785 秒，metadata 为 `BUILT`。

随后只执行 `./waf -j2 --run ws31-start-lifecycle-test`，退出码为 0，原始日志同时出现 `WS31_C2_LIFECYCLE PASS kind=stop` 和 `WS31_C2_LIFECYCLE PASS kind=dispose`。夹具没有 RDMA 驱动或网络，仅验证等待事件取消、请求／字节守恒及 Destroy 后不重复取消。未重复 C1/C2/C3 核心测试。

## 4. 已形成的设计决策

接受固定源码完整构建及 C2 非网络取消两项检查。对照固定 Git 对象核验 33 份变更文件，全部哈希一致；三份固定流量输入及测试源码的哈希在[总收据](ofan-preflight-r1-receipt.json)和[测试核验](ofan-preflight-r1-tests.json)中。测试无需外部流量输入，代码内固定请求为 8192 B；这些流量文件本轮没有被网络程序使用。

Ofan 核心编译／执行均在启动前取消，原准备脚本保留为未执行记录；实际使用的是 lifecycle-only 驱动。没有启动 Ofan 动态覆盖、RR 对照或任何网络格。历史文件名和实验 ID 中的 Ofan 字样保留，不代表 Ofan 已验证或获准进入基线。

## 5. 当前状态

状态为 `COMPLETE FOR REVISED TECHNICAL PREFLIGHT ONLY`。完整构建原始日志为 208360 B；C2 生命周期原始日志为 301 B，均已回传并逐字节核验哈希。远端固定源工作树干净，`raw/` 为空。

生命周期可执行文件 SHA-256 为 `14df5096b1ce67c8e859c94e1599bbad8c71ee31fa4535316555764ebdf9ff7a`。network-load-balance 虽由完整构建生成，但没有执行；其哈希及相关共享库哈希见测试核验文件。测试后可用内存 122.514 GiB、空闲盘 2380.811 GiB、1 分钟负载 1.43；只记录前后快照，没有测量资源峰值。

## 6. 未解决问题

构建保留 3 条 `-Wstrict-aliasing` 警告，位于 `scratch/network-load-balance.cc` 的 2083、2113、2148 行。相同 `pathId` 指针转换已存在于上一版 2032、2062、2097 行；本副没有修改或屏蔽。

C1/C2/C3 的网络零控制回归、标签与动态覆盖、C2 原需求计时、C3 借用及残留、独立需求双侧效果仍未完成。Ofan/RR 专门验证因用户决定取消，不列为本次遗留必做项，也不把未执行写成失败。新增基线的正式发表及 CCF A/B 资格由后续单目标核验，本轮没有准入任何新增机制。

## 7. 后续推荐动作

主独立核验[完整构建日志](ofan-preflight-r1-build-remote.log)、[C2 原始日志](ofan-preflight-r1-c2-lifecycle-remote.log)、收据与来源哈希。后续 C1/C2/C3 网络 pilot 需另派固定输入及验收协议；本次不启动下一格。Ofan 暂缓，新增加的基线需先通过用户规定的发表资格门和机制必要性审查。

## 8. 与其他工作流的关系

本副只写 independent 下 `ofan-preflight-r1*` 独占文件，未编辑主代码、共享分支、权威状态或论文，未提交／推送，未访问后置入口或恢复旧控制器。远端只部署已审 worker、同步缓存并在新 ID 下构建和运行指定非网络夹具。

本轮是工程预检验收，没有新文献或效果结论；旧基线建议保留历史身份，Ofan 优先实现建议已被用户新决定覆盖。主继续按 C1→C2→C3 推进。

## 9. CONTEXT SNAPSHOT

固定 `c4b6039b…` 的整合源码完整构建通过，ID `20261101-061544-ws31-ofan-preflight-r1`，1463 项任务、354.785 秒。C2 非网络 Stop/Dispose 两项均 PASS；33 份变更文件、输入、二进制及原始日志哈希已核。Ofan 专门测试尚未开始即按用户新指令取消，未推进 RR 对照，网络格启动数为 0。本修订单目标完成，等待主核验及下一单目标。
