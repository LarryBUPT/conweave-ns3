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

2026-09-30 14:05 UTC 的只读预检：远端 `ns3host` 的 `load1m=0.0`，无活动 ns-3 仿真，可用内存 122.98 GiB，工作区空闲 5664.2 GiB；进程清单没有在途 Waf/GCC/ns-3 作业。两个预留 ID 在 `runs/` 与 `results/` 均为空，本地和 `origin/feature/ws24-multinic-validation` 均为 `03f0924f392fea3585e2e50d99f2f89a3b288386`，候选 `71982b18e508739748dc8e0198e4d520bec9450b` 是其祖先。10 个输入文件逐一与 manifest 哈希相符，manifest SHA-256 为 `816da98d6cefa5e90ab3476cab0c924717cc1f732fc1a6ea67b9c0b0797d84c1`。这些是瞬时收据，不能代替启动前复查。

WS-23 已释放共享运行入口；远端现有 worker SHA-256 为 `b2454dda0b2f8a1e49f70a956b39a75fcd8bda9a661198cc6bd04f31615ce6c1`，不含 `ws24_multi_nic`，本地新版为 `0be12e21ce37655f52a19803824f2b8d24a9a2c84ba0cd58124eb6fb96de62eb`。实际切至 Luna High 后、构建之前才部署新版，共享路径仅 `/home/fnl/lzy/.research-workflow/remote_worker.py`；部署后复核 SHA、`audit`、无在途作业，固定源码的隔离副本不触碰 WS-23 结果。当前不部署、不 `sync`、不远程构建或仿真。

## 启动门槛、顺序和停止条件

1. 每次启动前记录 UTC 时间、登录用户与其他用户作业、活动 ns-3/Waf/GCC 进程、CPU/load、`MemAvailable`、工作区空闲盘、worker SHA 和两个 ID 的占用状态。没有他人作业、`load1m ≤10`、可用内存 ≥32 GiB、空闲盘 ≥100 GiB，且无 WS-23 或未知实验进程时才启动。若任何条件失效，暂停新格并重新取收据。
2. Luna High 实际生效后，先部署并验证 worker，再 `sync` 固定源码；用正例 ID 建隔离 optimized `-j2` 构建。构建完成核对 `metadata.json` 的 SHA、`BUILT`、`build.log` 和源码副本，才运行正例，`--max-concurrent 1`。正例终态先回传并用 raw 验收；全部通过后，才用另一独立 ID 构建并运行跨 rail 拒错格。负例必须在输入解析阶段报 `WS24 invalid flow row`、状态失败、无成功 FCT；其失败日志和 raw 均保留。禁止把预留 ID 复用为修复格。
3. 为每个运行 ID 保存资源逐点收据与终态摘要（可用 `scripts/ws11_resource_watch.py`，间隔 5 秒），核对后台 PID 与独立 `source`、`mix/output`、日志、raw 路径。构建超过 20 分钟或任一仿真超过 10 分钟，就停止启动后续格并诊断现有格，不覆盖其结果。出现他人作业、`load1m >20`、进程树 RSS >8 GiB、可用内存 <16 GiB、空闲盘 <100 GiB、单份文本日志 >50 MiB、资源收据缺失、隔离失效或运行失败时，停止新格并保留原始文件；对仍运行的异常进程先记录 PID 和状态，再安全终止该独立格。正常后台格静默运行，约半小时读一次精简状态；短格终态及时处理。
4. 正例与拒错格均核对固定 SHA、输入快照和哈希、seed=1、参数、退出状态及原始日志。正例需独立检查 `WS24_ROUTE_SUMMARY targets=8 host_pairs=8`、四条 `WS24_FLOW_START`、真实入接口运行时断言没有触发，再运行逐流验收器。当前验收器只统计 CNP flag 生成，不能以零事件证明动态 CNP 接收路径；另建可触发的独立正确性格并验证发送端收到随 ACK/NACK 的 flag。修复或补充动态观测需新源码 SHA 和独立 ID。

冻结的远程命令参数如下；它们尚未执行。先执行正例的 build/run/status/fetch/验收，再执行负例的 build/run/status/fetch 和拒错日志验收；`run` 的预期非零退出或 `FAILED` 不能误判为基础设施失败。

```powershell
python scripts/remote_experiment.py deploy
python scripts/remote_experiment.py check
python scripts/remote_experiment.py sync --repo-local .
python scripts/remote_experiment.py build --repo-local . --source-sha 71982b18e508739748dc8e0198e4d520bec9450b --id 20260930-224500-ws24-minimal-v0
python scripts/remote_experiment.py run 20260930-224500-ws24-minimal-v0 --lb fecmp --pfc 0 --irn 1 --simul-time 0.01 --netload 10 --bw 400 --buffer 9 --topo ws24_synthetic_2host_4nic_topology --flow-file config/ws24_synthetic_2host_4nic_flows.txt --ws24-multi-nic 1 --ws24-nic-file config/ws24_synthetic_2host_4nic_nics.txt --max-concurrent 1
python scripts/remote_experiment.py build --repo-local . --source-sha 71982b18e508739748dc8e0198e4d520bec9450b --id 20260930-224600-ws24-crossrail-reject-v0
python scripts/remote_experiment.py run 20260930-224600-ws24-crossrail-reject-v0 --lb fecmp --pfc 0 --irn 1 --simul-time 0.01 --netload 10 --bw 400 --buffer 9 --topo ws24_synthetic_2host_4nic_topology --flow-file config/ws24_synthetic_2host_crossrail_reject.txt --ws24-multi-nic 1 --ws24-nic-file config/ws24_synthetic_2host_4nic_nics.txt --max-concurrent 1
```

## 必须同时满足的验收

1. 构建无错误；`metadata.json` 的 `git_commit`、拓扑、流、NIC 哈希与上表一致；raw/config 三份输入快照及运行参数完整。
2. 真实运行有 2 个 host Node，各四个 Qbb NIC 与唯一 IP，四个 switch fabric 组件没有跨 rail 转发。`WS24_ROUTE_SUMMARY` 目标数为 8，源对/rail 路由数为 8；不能用主机 Node 的单路由合并四个 rail。
3. 四个输入 flow ID 各有唯一 TX QP、首次 RX DATA、首次 RX ACK 身份事件；host/rank、两端 IP、源与返回 NIC 接口均对应同一 rail。非法异 rail 流须在独立负例 ID 中被拒绝，不能进入仿真并产生成功 FCT。
4. `*_out_ws24.txt` 与 FCT 各 4 条，四条全部完成；逻辑输入、连续唯一接收与确认序号各 32,768 B。逐 QP `rx_unique_bytes=snd_una=size`，发送 payload `>=size`，超出部分仅在可解释重传下接受。需求≤放行≤完成；FCT 端点、端口和字节与身份收据一一对应。
5. ACK/NACK 与随带 CNP flag 的返回路径以反向两端 IP、目标源 NIC 及实际入接口验证。此无拥塞最小格可能没有 NACK/CNP flag，零事件只说明该动态分支未触发；后续需单独设计可触发的正确性格，不以零事件宣称 CNP 已验证。

`python scripts/verify_ws24_result.py <实验ID> --source-sha 71982b18e508739748dc8e0198e4d520bec9450b` 为终态 raw 核验入口，实际使用前还须审查其与首份 raw 格式一致。远程 worker 的非空 FCT 门槛只是一层防漏，不能替代此逐流验收。

若编译失败、路由/身份断言、未完成、哈希不符或资源异常，立即停止后续格并保留该 ID 的日志和 raw；定位修复后用新源码 SHA 与新 ID 再验证。最小格成功后才启动目标 320 host 拓扑及旧五/六列四 baseline 回归。效果小样四臂与后续正式验证仍受 [必做清单](../project-state/WS23_WS24_VALIDATION_PLAN.md) 约束，不因技术 pilot 结束而取消。

根据 [远程工作流](../REMOTE_EXPERIMENT_WORKFLOW.md)，进入后台实验监督前须实际切到 GPT-6 Luna High；终态 raw 回传后实际切回 GPT-6 Sol High 分析。**目前没有模型切换、远程 build、实验 ID 或 raw。**
