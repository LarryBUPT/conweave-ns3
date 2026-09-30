# Handoff 43：WS-23 构建/单测门槛与 WS-24 多 rail 拓扑审查启动

1. **本对话目标：** 来源 task “ConWeave Research · Integration” (`01a0cfac-3176-7590-bf34-c0f176a45118`)；按用户要求收束 WS-23 当前可验证阶段，并推进 WS-24。WS-23 本地修复、构建和单测门槛已核验；不把尚未运行的正确性仿真记为完成。

2. **已确认的项目事实：** WS-23 修复代码固定于 `feature/ws23-irn-pfc-recovery` 的 `12dea54d421243ddb98c83437b929944ab6d128c`；Handoff 42 已记录契约和后续最小正确性格。隔离 optimized build ID `20260930-175600-ws23-recovery-build` 对该 SHA 构建成功。完整测试构建首次被仓库既有 `CommandLineTestCaseBase::Parse` const 不一致阻断；参照 Handoff 30，仅在该隔离源码副本临时去掉测试辅助函数参数 const 后续编译，执行 `devices-point-to-point` 得到 `PASS devices-point-to-point 0.000 s`。临时变更恢复后文件 SHA-256 为 `b7285686202442d47d339fd5817e9001c47bfc23377c8a8f5f596ba694373881`，与原文件相同；固定源码 SHA 未变。无新仿真、raw 或性能结论。

3. **已完成工作：** 先通过远端资源收据确认无活动仿真（40 logical CPU、load 1m 0.0、可用内存约 122.99 GiB、空闲磁盘约 5670.2 GiB），同步个人 fork 后创建独立 build ID，`optimized -j2` 构建成功。测试 build 输出隔离于 `build-ws23-tests`；编译 workaround 仅触及 `src/core/test/command-line-test-suite.cc` 中既有测试 helper 签名，执行后逐字节恢复并校验。没有删除或覆盖任何既有实验结果。

4. **已形成的设计决策：** 将 WS-23 关闭范围限定为“本地恢复契约/补丁及 optimized build + point-to-point suite 已完成”；端到端传输正确性仍待冻结并执行两个最小正确性格。无条件删除 PFC 超时抑制并未被采用；补丁按源 PG 的实际暂停状态延期 RTO，在 resume 后等待完整 RTO。此验证不开放拥塞流隔离性能实验，因为 PFC=0 跨类阻塞因果前提仍未证。

5. **当前状态：** 集成前分支 `feature/ws23-irn-pfc-recovery`，源码提交已推送到个人 fork；本地树在文档集成前干净。WS-23 修复通过 optimized build 与 `devices-point-to-point` 单测，但没有修复版仿真 ID，不能声称故障已在仿真中修复。WS-24 仍为本地可行性审查，不进入仿真。

6. **未解决问题：** WS-23 固定 16×1 MiB 压力格 16/16 完成、QP 序号/字节守恒、暂停期无恢复以及无损真实 pause/resume 格仍未由新仿真验证。WS-24 既有 400G OS1 拓扑 `topo_1280_400G_400G_OS1.txt`（SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`）静态遍历得到 4 个互不连通分量；每分量 464 节点、320 个主机端点，主机 ID 各自固定于单一 `ID mod 4` 组且度为 1。WS-17 生成器只选 rail 0。尚未证明四个端点对应同一物理服务器的四个 NIC，也未发现共享主机、作业 placement 或跨 rail 连接表示；据此暂不能把既有节点当成真实 multi-rail 主机。

7. **后续推荐动作：** WS-24 新任务先审计拓扑生成、scratch host/NIC/RDMA endpoint 模型、IP 与 route 初始化，明确现有四组件的 rail 语义和物理 host 映射；形成显式 placement/NIC/流量数据契约并验证可表示性。若要扩展模型，先用本地结构测试验证共享主机/多 NIC 身份、流到 rail 映射和组件连通；不能表示或缺少可核验物理映射则维持 NO-GO，不运行多 rail 仿真。WS-23 若以后继续，先冻结端到端正确性协议，并遵守工作流所需的 Luna 监督和终态 Sol 分析。

8. **与其他工作流的关系：** WS-23 只修传输恢复正确性，不重判 WS-13 旧四格、WS-10/11/12/19/20/21 no-go，也不把旧压力格作性能排名。WS-24 是独立的输入/拓扑/放置问题；四个断开的 rail 组件不能提供同服务器多 NIC 或跨 rail 任务协同的证据。WS-25 的证据收束和导师确认范围不变。

9. **CONTEXT SNAPSHOT：** WS-23 修复 SHA `12dea54d…` optimized build 与 point-to-point 单测通过；单测曾因无关的 core 测试 helper const 缺陷失败，隔离修正后通过且恢复源码 SHA。没有修复版仿真，故端到端正确性仍未验证；隔离性能矩阵继续 NO-GO。WS-24 拓扑有四个互不连通分量，每个 320 个 rail 单归属端点，当前没有同一物理 server 的多 NIC / placement 映射。下一步只做本地拓扑与代码可表示性审计，必要时提出可核验输入契约；没有满足门槛前不仿真。项目状态见 `docs/project-state/CURRENT_STATE.md`、`WORKSTREAMS.md` 和 `ROADMAP.md`。
