# WS-24：多 rail 与作业放置可表示性本地审计

日期：2026-09-30。分支 `feature/ws24-multirail-input`，父提交 `7dfacee3a968073c5c80d5bb3c315a6557b980e3`。本阶段只读源码、拓扑与既有证据，并运行本地结构检查；没有远程仿真、新实验 ID、性能数据或模型切换需求。目标是判断现有 OS1 资产能否表达同一物理服务器的多 NIC、流的 rail 绑定及 job placement。前置门槛为这些身份及连通的可核验输入。停止条件是任何一个身份、绑定、路由或 placement 不可证明，或静态检查发现跨 rail 不可达。

## 证据与结论

固定拓扑 `config/topo_1280_400G_400G_OS1.txt` 的 SHA-256 是 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。[`scripts/audit_ws24_multirail.py`](../../scripts/audit_ws24_multirail.py) 逐边解析得到 1,856 节点、576 交换机、3,840 链路；四个互不连通组件各 464 节点、320 个度为 1 的主机端点。端点 `ID mod 4` 与组件一致。`scripts/make_ws17_demand.py::HOSTS` 只取 `range(0,1280,4)`。这些是**网络端点与输入限制**，没有物理服务器身份或真实作业映射证据。仓库内 `config/fat_topology_gen.py` 生成普通 fat-tree 文本，不能作为此导入 OS1 文件的主机/NIC 来源说明。

源码审计表：

| 层 | 当前表示 | WS-24 缺口 |
| --- | --- | --- |
| topology/scratch 创建 | `scratch/network-load-balance.cc` 按每个非交换机 ID 建一个 `Node`，按链路建 `QbbNetDevice`；每节点算一个 `serverAddress[i]`，主机链路把该地址加到接口 1 | 没有 `physical_host_id → 多 NIC Node` 的导入字段；四个相邻 ID 实际创建四个独立 Node |
| IP/route | `SetRoutingEntries` 用目的 `GetAddress(1,0)` 建表，`Settings::hostId2IpMap`/`hostIp2IdMap` 与 `hostIp2SwitchId` 按单端点 IP 管理。最短路 BFS 不经主机作中转 | 没有跨组件网络路径；多接口时固定接口 1 不是可接受的目的地址选择契约 |
| RDMA endpoint | 每个 host Node 独立创建一对 `RdmaDriver`/`RdmaHw`。底层 `RdmaHw::m_nic` 是 vector，`RdmaDriver::Init` 枚举该 Node 的设备，`GetNicIdxOfQp` 按目的 IP 路由候选选择 NIC | 底层有多 NIC 容器，但当前 OS1 每 Node 仅一个 Qbb 端点；没有经测试的显式源 NIC/目的 NIC 绑定，也没有共享物理主机的资源/队列语义 |
| flow/job | `ReadFlowInput` 接受 `src dst pg bytes start_s [tag]`；`ScheduleFlowInputs` 把 `src/dst` 当 Node ID，以对应单地址建 QP | trace 没有 job、rank、physical host、src/dst NIC、rail、轮次或 placement；`tag` 是 workload 类别，不是 rail |

因此，当前拓扑下**同一 rail 的两个端点可存在网络路径**；不同 rail 的任意两个端点无 fabric 路径。若将四个端点只在外部 sidecar 中标成同一物理主机，仍只是一个**待证假设**：模拟器运行时它们是四个独立 Node/RDMA Hw，不能据此报告多 NIC 主机的吞吐、共享资源或放置收益。底层 vector 也不足以证明当前 scratch 的多 NIC 路径可运行。

## 必须先冻结的数据契约

建议将物理/作业身份保存在与既有 trace 同 SHA 配对的 sidecar，保持旧五/六列格式及四 baseline 不变。sidecar 至少需要：

1. **拓扑与来源**：拓扑 SHA、原始拓扑/集群配置的来源、物理主机 ID、该主机每个 rail 的 NIC ID、`endpoint_node_id`、端口/速率/ToR、IP，以及这些映射的原始证据。`node_id // 4` 只能作合成 fixture，不能自行变成真实物理映射。
2. **作业放置**：`job_id`、不可重复 `rank_id`、其 `physical_host_id`、放置策略和约束、独立需求 seed/原始记录来源。不同 placement 对照须冻结同一逻辑通信需求和总字节，并明示被改变的 rank→host 映射。
3. **每条逻辑流**：稳定 `flow_id`、job/源目的 rank、源和目的 NIC/rail、字节、PG、workload tag、需求时刻、轮次/依赖（若声称 job CCT）；解析后记录源/目的 endpoint Node、IP 和 QP 身份。默认 rail 内通信必须有 `src_rail == dst_rail`；若允许异 rail，需显式互联链路或可解释的主机侧转发与计时，不可凭 sidecar 标签假造连通。
4. **可审计守恒**：映射一对一且每物理 host 的四 NIC 落在四个不同 rail 组件；每 job/rank 的 placement 唯一；每流两端存在且可达，QP 记录 rail/NIC/host/job；输入流数、字节、放行与完成数守恒。任一失败立即拒绝生成或运行。

实现次序：先取得可信映射与需求 provenance；再改拓扑导入，使一个物理 host 对应一个 `Node` 与多 `QbbNetDevice`，每 NIC 有唯一 IP/rail，构建目的 IP 与源接口的显式路由；核验 RDMA QP 的源/目的 NIC 绑定、ACK/CNP 返回路径及共享资源语义；然后做两主机四 rail 的最小正确性测试和 placement/流身份收据。正式效果比较另需固定 placement 与可变 placement、固定单 rail 与多 rail 等双侧强对照，并由独立 job 需求与业务/研究判据支撑。

## 本地结构测试及边界

运行 `python scripts/audit_ws24_multirail.py` 通过。脚本以**显式 synthetic fixture** 把每四个相邻端点假设为一组，验证 320 组均覆盖四个不同组件；给两个假设 host 分配一个假设 job 的两个 rank，四条同 rail 流分别解析成 `(0,16)`、`(1,17)`、`(2,18)`、`(3,19)`，并拒绝重复 host/rail endpoint、未知 rank 及异 rail 源/目的绑定。它还直接检查 `0` 与 `17` 位于不同组件。该测试只证明可写出可拒错的**输入 sidecar 结构**和拓扑内连通判断；没有把 sidecar 接入 ns-3，没有证明四端点真的共处一台机器，也没有测 QP 多 NIC、job CCT 或性能。

成熟系统的抽象提供对照而非本仓库实现证据：[NCCL 官方文档](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/env.html#nccl-cross-nic) 明确区分同 NIC rail 与跨 NIC 通信策略，并以 `NCCL_IB_HCA` 的 rail/plane 字段和 `NCCL_NETDEVS_POLICY` 的 GPU→网络设备分配表达设备身份。其做法说明 rail、NIC 与计算 rank/设备映射必须是独立可识别对象；不能由四个断开的交换网络自动推出物理主机多 NIC 或通信收益。本审计不声称 NCCL 策略可直接移植到本 ns-3/RDMA 模型。

**门槛结果：WS-24 本地结构审计完成；remote simulation NO-GO。** 当前缺可信物理 host/NIC 映射、job placement/独立需求，以及 scratch 多 NIC 端到端正确性。四组件不能当作已验证的 multi-rail 收益。WS-23 另保持：固定修复 SHA `12dea54d421243ddb98c83437b929944ab6d128c` 仅 optimized build 与 `devices-point-to-point` 单测通过；没有修复版端到端仿真，传输恢复正确性待验证，隔离性能实验 NO-GO。
