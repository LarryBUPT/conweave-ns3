# WS-24 合成多 NIC v0：实现工作记录（ACTIVE）

2026-09-30。从干净且已推送的 `feature/ws23-validation@b2af87983ab7218d00cfff02bddc618f15d87df6` 建独立工作树 `workspace/ws24-multinic-validation` 与 `feature/ws24-multinic-validation`；该父提交包含 WS-23 修复源码 `70bf890d1ceba58c5ebd26b17e492295b34c99ca`。WS-23 的仿真从独立固定源码工作树执行。本记录是实现中状态，**尚无 C++ 构建、ns-3 运行、实验 ID、旧 baseline 回归或效果结论**；不能据此关闭 [必做清单](../project-state/WS23_WS24_VALIDATION_PLAN.md)。

## 来源与假设

`maplerime/conweave-ns3@470c58026ec3933eabb6667bf3124b6b9bd401be` 的 `config/gen_moe_topology.py` 与导入 OS1 拓扑 3,840 链路逐边吻合。生成器把每 server 的四个 port node 接到四个 rail。这是合成生成规则，不是实际物理部署或 job placement 记录。`scripts/make_ws24_inputs.py` 将 1,280 个原端点按 `host=endpoint//4`、`rail=endpoint%4` 折叠为 320 个多 NIC Node；交换机 ID 减 960，四个 fabric 组件继续禁止经主机转发。两个主机的四 rail 极小拓扑单独生成。两套 NIC 文件逐行给出 `(host, rail, IP, peer switch, interface, legacy endpoint)`，不是依赖隐含邻接猜测。

新模式通过 `--ws24-multi-nic 1 --ws24-nic-file config/<文件>` 显式启用，当前仅使用 `fecmp`。新流文件每行恰好 12 列：

```text
flow_id job_id src_rank dst_rank src_host dst_host src_rail dst_rail pg bytes demand_ns workload_tag
```

第一行是流数。输入按 `(demand_ns,flow_id)` 排序，同一 job/rank 的 host 放置在一次运行内固定。缺 NIC、源/目的跨 rail、重复 flow ID、无效 host/PG、非单调时刻均拒绝。`config/ws24_synthetic_2host_crossrail_reject.txt` 明示不同源/目标 rail 以供动态拒错验证。旧五/六列输入继续进入旧解析分支；其真实回归尚待运行。

四臂固定逻辑需求都是 10 条、2,408,448 B，固定/可变放置交换 rank 1 与 2，单 rail 使用 rail 0，多 rail 使用 flow ID 对四取模。热对 0→1 的最短 fabric 跳数随放置从 4 变 6。这个小输入只用于工程正确性和机制 pilot；没有真实 job 需求、GPU/CPU/PCIe 争用或 collective 语义，不支持实际训练性能主张。目标拓扑、NIC、流文件的内容哈希在 `config/ws24_synthetic_manifest.json`。

## 源码接入与待验证点

- 一个物理 host Node 安装四个 Qbb NIC、四个独立 11.x IP，`RdmaDriver/RdmaHw` 在 host 上只创建一套；NIC/接口关系在链路安装时与显式文件逐条核对。`Settings::hostIp2IdMap` 将四个 IP 解析回同一 host。
- 路由以**目标 NIC IP**为键，在该 NIC 直连交换机所在组件内反向遍历；其它主机不作中转，源 host 只对同 rail NIC 安装出口。每 `(src host,dst host,rail)` 分别计算 RTT、带宽、BDP。旧 Node 级路由留给旧模式。
- 新模式 TX/RX QP 使用两端 IP、两端端口和 PG 的键。数据从源 NIC 走目标 rail；ACK/NACK（含随带的 CNP 标志）从目的 NIC 的 IP 沿同 rail 返回源 NIC。`QbbNetDevice` 在终点检查真实入接口与目标 IP/rail 一致。独立 CNP 包路径在旧代码中仍会退出，未被此模式声称支持。
- 新原始 `*_out_ws24.txt` 对每条已完成流记录 job/rank/host/rail、两端 IP、端口、逻辑字节、需求/放行/完成时刻、接收连续唯一字节、发送 payload、发送序号。结束时强制检查输入/完成数与唯一字节守恒；允许重传导致发送 payload 超过逻辑字节，并将其单独记录。
- `scripts/remote_worker.py` 在新模式下固定 NIC 文件哈希并回传快照，检查身份收据的完成行数。`scripts/verify_ws24_result.py` 计划从终态 raw、trace、NIC 文件、FCT、日志逐流核对正反路径。运行结果前，该脚本仅是待验证的验收器。

## 本地检查与远程边界

截至本记录，本地 `python scripts/make_ws24_inputs.py` 与 `python scripts/verify_ws24_inputs.py` 通过：最小 8 NIC/4 流、目标 1,280 NIC、四臂各 10 流/2,408,448 B。Python 文件 `py_compile` 与 `git diff --check` 通过。`run.py --help` 用 bundled Python 可启动；原系统 Python 缺 NumPy，原 `random.seed(datetime.now())` 在新版 Python 不接受 datetime，现改为时间戳，仅用于随机原始输出目录 ID，trace 仍须固定哈希。

后续不能跳过的步骤：先静态审查并提交源码，在独立固定 SHA 下远程 optimized build；失败则定位修复、改 SHA 重建。再运行两主机四 rail 的端到端正确性和同源/异 NIC 反例，核对数据、ACK/NACK/CNP 标志及逐 QP 守恒；旧五/六列四 baseline 回归；再运行目标拓扑四臂小样和必要效果对照。每次仿真前冻结具体 SHA、文件哈希、seed、实验 ID、资源和停止条件。按项目工作流，进入后台远程实验监督前须**实际切换到 GPT-6 Luna High**，终态 raw 回传后实际切回 GPT-6 Sol High；未切换不得以文档文字代替。

## 2026-10-01 构建失败与修复检查点

首次远程构建 `20260930-224500-ws24-minimal-v0` 固定源码 `71982b18e508739748dc8e0198e4d520bec9450b`，元数据终态 `BUILD_FAILED`。Waf 编译 `scratch/network-load-balance.cc` 到 1198/1453 时，在 `InstallWs24Routes()` 的路由 BFS 循环遇到误置的活跃 QP 计数代码，引用未声明的 `rdmaHw`、`nActiveQP`。失败来源由 `git blame` 定位为 `5e78ea2`。没有启动该 ID 的仿真，也没有启动预留的 v0 跨 rail 拒错格。

失败目录及证据已从远端回传：`results/20260930-224500-ws24-minimal-v0/logs/build.log` SHA-256 `1aa7aaf1f69e11c25cc2ca7f7388c9f6c3e3c0f2094e9b4686bc68d0f8875a3f`；36 条资源采样 SHA-256 `a656744cc8f9b9081a136377f595db64dd19c5f28c6a2e8c3ed37ac45e29d8c7`；资源摘要 SHA-256 `ae6b04133e68318c270742da2a33377a9f5be02a934517122856778b88da91fd`。最大进程树 RSS 517.48 MiB，可用内存最低 122.527 GiB，空闲盘最低 5663.47 GiB；失败由代码编译错误造成，未触及资源停止阈值。

修复提交 `1d52cbe765d1077ccd8c3afe994b2fb491e4735a` 将活跃 QP 计数放回 `periodic_monitoring()`，WS-24 统计 `m_ws24QpMap`、旧格式统计 `m_qpMap`，并从路由 BFS 移除该代码。修复已推送，`git diff --check`、Python 脚本语法检查及离线输入验收通过。新冻结协议见 [最小多 NIC 预飞行](ws24-minimal-multinic-preflight.md)：正例新 ID `20261001-011500-ws24-minimal-v1`，跨 rail 负例新 ID `20261001-011600-ws24-crossrail-reject-v1`，二者固定新 SHA。**修复候选尚未远程构建或仿真**；下一步须在实际切至 Luna High 后重新检查资源/ID，并只运行新正例，正例全部通过后才执行负例。旧格式回归、目标拓扑、动态 CNP 触发与四臂对照仍待完成。
