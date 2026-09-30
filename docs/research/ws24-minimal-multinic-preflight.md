# WS-24 两主机四 rail 最小端到端预飞行（待执行）

冻结日期：2026-09-30。阶段：**仅冻结协议，尚未构建或仿真**。候选源码 SHA `71982b18e508739748dc8e0198e4d520bec9450b`，个人 fork 分支 `feature/ws24-multinic-validation`；该分支从 WS-23 的 `b2af87983ab7218d00cfff02bddc618f15d87df6` 分出，包含其传输修复。文档提交后的 HEAD 不等于候选仿真源码；构建须显式指定上述 SHA。若编译或正确性失败，保存该 ID 的构建/原始日志，修复后以新 SHA 和独立 ID 重验。

## 输入、参数与预留 ID

候选正例 build+run ID：`20260930-224500-ws24-minimal-v0`；候选异 rail 拒错 ID：`20260930-224600-ws24-crossrail-reject-v0`（均未创建；执行前检查远端不存在）。唯一源为个人 fork 的固定 SHA，新运行须使用隔离源码副本，不触碰 WS-23 固定执行副本。

| 项目 | 冻结值 |
| --- | --- |
| 拓扑 | `config/ws24_synthetic_2host_4nic_topology.txt`；SHA-256 `cb7a9ef2589140967f9499c731a71126ef1dec9f007bb4a91e622c22c63c2b8a` |
| NIC 映射 | `config/ws24_synthetic_2host_4nic_nics.txt`；SHA-256 `25054d303698f8f79440b9533244dd7ee54bda13eecba6bf71b071cf87b26b53` |
| 流 | `config/ws24_synthetic_2host_4nic_flows.txt`；SHA-256 `ff975567be775416aee70f241c6712e2237e077de4a0a36555e1b3bda1fc0d86`；四条各 8,192 B，合计 32,768 B，分别走 rail 0/1/2/3 |
| 拒错流 | `config/ws24_synthetic_2host_crossrail_reject.txt`；SHA-256 `2fd3e459a531750eacc15a1697019952f150b4e378fc3e6a309e6e1b0bf09a8c`；源 rail 0、目标 rail 1，必须在输入阶段拒绝 |
| 传输/模式 | `fecmp`；DCQCN，PFC=0、IRN=1、400 Gbps、9 MiB switch buffer、固定 seed=1；显式 `--ws24-multi-nic 1` |
| 时间/资源 | demand=2.0 s，`--simul-time 0.01`，`--netload 10` 仅满足运行器参数，显式 trace 决定实际负载；optimized build `-j2`，最小格并发上限 1 |

运行前必须核对服务器无其它用户作业、WS-23 在途实验及当前资源；WS-23 已在独立固定源码工作树中进行压力格构建。WS-24 不得为部署更新版共享 `remote_worker.py` 而改变 WS-23 正在使用的运行入口；待其完成且协调确认后再部署并核验 worker 版本。固定旧 worker 若支持安全隔离 build，也仍不得在模型切换之前启动远程构建或仿真。

## 必须同时满足的验收

1. 构建无错误；`metadata.json` 的 `git_commit`、拓扑、流、NIC 哈希与上表一致；raw/config 三份输入快照及运行参数完整。
2. 真实运行有 2 个 host Node，各四个 Qbb NIC 与唯一 IP，四个 switch fabric 组件没有跨 rail 转发。`WS24_ROUTE_SUMMARY` 目标数为 8，源对/rail 路由数为 8；不能用主机 Node 的单路由合并四个 rail。
3. 四个输入 flow ID 各有唯一 TX QP、首次 RX DATA、首次 RX ACK 身份事件；host/rank、两端 IP、源与返回 NIC 接口均对应同一 rail。非法异 rail 流须在独立负例 ID 中被拒绝，不能进入仿真并产生成功 FCT。
4. `*_out_ws24.txt` 与 FCT 各 4 条，四条全部完成；逻辑输入、连续唯一接收与确认序号各 32,768 B。逐 QP `rx_unique_bytes=snd_una=size`，发送 payload `>=size`，超出部分仅在可解释重传下接受。需求≤放行≤完成；FCT 端点、端口和字节与身份收据一一对应。
5. ACK/NACK 与随带 CNP flag 的返回路径以反向两端 IP、目标源 NIC 及实际入接口验证。此无拥塞最小格可能没有 NACK/CNP flag，零事件只说明该动态分支未触发；后续需单独设计可触发的正确性格，不以零事件宣称 CNP 已验证。

`python scripts/verify_ws24_result.py <实验ID> --source-sha 71982b18e508739748dc8e0198e4d520bec9450b` 为终态 raw 核验入口，实际使用前还须审查其与首份 raw 格式一致。远程 worker 的非空 FCT 门槛只是一层防漏，不能替代此逐流验收。

若编译失败、路由/身份断言、未完成、哈希不符或资源异常，立即停止后续格并保留该 ID 的日志和 raw；定位修复后用新源码 SHA 与新 ID 再验证。最小格成功后才启动目标 320 host 拓扑及旧五/六列四 baseline 回归。效果小样四臂与后续正式验证仍受 [必做清单](../project-state/WS23_WS24_VALIDATION_PLAN.md) 约束，不因技术 pilot 结束而取消。

根据 [远程工作流](../REMOTE_EXPERIMENT_WORKFLOW.md)，进入后台实验监督前须实际切到 GPT-6 Luna High；终态 raw 回传后实际切回 GPT-6 Sol High 分析。**目前没有模型切换、远程 build、实验 ID 或 raw。**
