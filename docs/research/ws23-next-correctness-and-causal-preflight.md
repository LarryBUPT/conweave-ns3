# WS-23 下一批正确性与跨类因果预飞行

日期：2026-10-01。状态：**本地输入、候选源码、验收规则已冻结；新源码未远程构建，以下五格均未运行。** WS-24 正使用共享远端 `remote_worker.py` 部署与运行入口；本页不授权在其在途作业中部署或启动 WS-23。执行前须重新协调 worker 版本、远端 ID 空闲、其他作业和资源，并按[远程工作流](../REMOTE_EXPERIMENT_WORKFLOW.md)实际切入 Luna High 监督。终态 raw 回传后实际切回 Sol High 核验。两个固定仿真 SHA 的 `scripts/remote_worker.py` Git 内容相同，SHA-256 均为 `8bcb695221a4c2918ee471c4df7c0f6bd8b9cc9d38e5a272c2987f49a3be10c6`；共享入口释放后核对远端已部署文件，不一致时才由协调任务部署本分支 worker。观察器通过每格独立结果目录启动，不触碰共享 worker。

## 已有原始证据与证据边界

- 仿真源码 `70bf890d1ceba58c5ebd26b17e492295b34c99ca` 的无损暂停 `20260930-201500-ws23-lossless-pause` 为 1/1 完成，源端主机 0、PG 3 在 `2006001203` 至 `2007801203 ns` 真实暂停 1.8 ms，无丢失或误恢复。
- 同 SHA 压力 `20260930-201600-ws23-loss-recovery` 和资源补验 `20260930-213100-ws23-loss-recovery-r2` 均为 16/16、两类各 8/8、161 次出口准入丢包与 3 次超时恢复；两份 FCT SHA-256 同为 `97feb0e118544f07e006da9e9bc2ead2566a10b91ad2201e0e83ced89279b18a`。资源补验在仿真前启动观察器，实际运行 PID `138011` 的 10 个采样均有正 RSS，峰值 204.012 MiB、可用内存最低 122.824 GiB、磁盘最低 5664.202 GiB。第一份压力格的零 RSS 终态采样不能当运行峰值。机器摘要见[两格证据](evidence/ws23-two-cell-correctness-20261001.json)，原始数据在独立执行副本的 `results/<实验ID>/`。
- 两格都没有 `WS23_IRN_PFC_TIMEOUT_DEFERRED`，所以“暂停期间计时器到期后推迟恢复”目前只有单测，没有端到端动态覆盖。压力格流 14（源主机 14、PG 3）最后一次准入丢包在 `2007015639 ns`，原恢复在 `2007524560 ns`、RTO 为 `320000 ns`；该主机旧的自然 PFC 最后恢复在 `2007041797 ns`。下面的注入时段选在已发生丢包之后、旧恢复之前，属于基于原始记录预先选定的技术探针，不能假定干预后的事件时刻仍相同。
- 旧 PFC=0 常规格没有证明两类流共享可改道瓶颈；本批先建立受控合成场景的因果前提。它不提供正式隔离收益或真实业务 SLO。

## A. 超时延期动态覆盖：一格

固定仿真源码为已通过 optimized 构建、单测和两格正确性复核的 `70bf890d1ceba58c5ebd26b17e492295b34c99ca`。预留新 ID 为 `20261001-090000-ws23-rto-pause`，执行前须核对本地和远端均未占用。输入为 Git 内容 SHA-256 `bc2db1513cbde20f12eea6efa4e2265cf74954be4fa45f2a147ff0ce84b33985` 的 `config/ws09_drop_probe_16x1MiB.txt`；拓扑 SHA-256 `dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad`。seed=1，ECMP、DCQCN、100G、1 MiB buffer、IRN=1、PFC=1、`simul_time=0.01`、`netload=10`、`--factorial-pilot --factorial-drop-diag`、并发 1。**仅新增**对源主机 14、PG 3 的真实 PFC：相对 2 s 窗口 `7200000 ns` 注入 2500 µs pause，`8800000 ns` 显式 resume。

```powershell
python scripts/remote_experiment.py build --repo-local . --source-sha 70bf890d1ceba58c5ebd26b17e492295b34c99ca --id 20261001-090000-ws23-rto-pause
python scripts/ws23_start_resource_watch.py 20261001-090000-ws23-rto-pause --source-sha 70bf890d1ceba58c5ebd26b17e492295b34c99ca
python scripts/remote_experiment.py run 20261001-090000-ws23-rto-pause --lb fecmp --pfc 1 --irn 1 --simul-time 0.01 --netload 10 --bw 100 --buffer 1 --topo fat_k4_100G_OS2 --cdf AliStorage2019 --flow-file config/ws09_drop_probe_16x1MiB.txt --factorial-pilot --factorial-drop-diag --ws23-pfc-probe-host 14 --ws23-pfc-probe-pg 3 --ws23-pfc-probe-start-ns 7200000 --ws23-pfc-probe-end-ns 8800000 --ws23-pause-time-us 2500 --max-concurrent 1
python scripts/remote_experiment.py status 20261001-090000-ws23-rto-pause
python scripts/ws23_start_resource_watch.py 20261001-090000-ws23-rto-pause --source-sha 70bf890d1ceba58c5ebd26b17e492295b34c99ca --wait
python scripts/remote_experiment.py fetch 20261001-090000-ws23-rto-pause
python scripts/verify_ws23_recovery.py --scenario deferral --source-sha 70bf890d1ceba58c5ebd26b17e492295b34c99ca 20261001-090000-ws23-rto-pause
```

逐行按门槛执行：`build` 成功后用一条本地命令把快速观察器安装到该 ID 的独立 `logs/` 并启动，看到 `READY` 才可 `run`；`status` 显示终态后才用 `--wait` 读取正 RSS 资源收据，随后 `fetch`。观察器不修改共享 worker，且不依赖旧 `70bf890…` 源码目录中存在新观察器。若构建、启动观察器、运行或收据失败，停止新格，保留该 ID 的远端记录和 raw；终态 `FAILED` 仍可 `fetch`。验收器要求：输入/拓扑/参数一致；源主机确实收 pause/resume；流 14 在暂停前已有真实准入丢包；流 14 至少一次暂停中延期、一次恢复后完整 RTO 观察期延期，延期均为正时长；源 PG 暂停期无超时恢复，恢复不早于最近一次 resume 后完整 RTO；两类各 8/8、QP 序号与字节守恒。若干预改变丢包或 ACK 时序而未触发目标分支，**保留此 ID 与 raw，判为技术探针未覆盖**；定位后另冻新方案、SHA/ID，不能降低断言。

## B. 共享可改道出口因果技术小样：四格

候选仿真源码为 `154f537ec345df75fbb404a1674436535f92735b`，**仅完成本地 Python 语法与 `git diff --check`；C++ optimized 构建、单测、端到端均待做**。它在 `fecmp`、32 主机小拓扑、显式 `--ws13-diag 1` 时汇总 tag 1/2 的逐流交换机出口、排队前设备队列字节、准入后 MMU 物理出口占用、等待时间及活动时间窗；诊断默认关闭。这里的 MMU 数是端口已预留字节，设备队列数是入队前字节，两者不能混称。逐格要求观测 `WS23_CROSSCLASS_INFLIGHT unpaired=0`，并以同输入诊断开/关的 FCT 字节哈希相等证明观测未改变业务时序。没有通过该技术门槛前，不解释排队或因果结果。

共同拓扑仍为 `fat_k4_100G_OS2@dcca23ca…`。背景 `config/ws23_crossclass_bg_1x8MiB.txt@8b11ba4bbc5fac248b1983e4070e818cb3ad3658ebaae6d9eb878b3999b76b83`：`0→24`、PG 3、tag 1、8 MiB、2.006 s。混合 `config/ws23_crossclass_bg_plus_3x4MiB.txt@379e0c87cb0c26690d438287468dbc9159054f82445e6be46d0324165d639863`：完全相同的背景首行，再加 `1→25`、`2→26`、`3→27` 三条 tag 2、各 4 MiB、同一时刻。静态拓扑中四源同接 ToR 32、四目的同接 ToR 38，各目的有不同最终下行；ToR 32 对远端有两条聚合上联。**这只说明可争用与可选路的结构，不证明本输入实际共用出口。**

| 预留 ID | 输入 | 诊断 |
| --- | --- | --- |
| `20261001-091000-ws23-bg-off` | 背景 1 流 | 关 |
| `20261001-091100-ws23-bg-on` | 背景 1 流 | `--ws13-diag 1` |
| `20261001-091200-ws23-mix-off` | 背景 + 3 竞争流 | 关 |
| `20261001-091300-ws23-mix-on` | 背景 + 3 竞争流 | `--ws13-diag 1` |

四格固定 seed=1、ECMP、DCQCN、100G、9 MiB buffer、PFC=0、IRN=1、`simul_time=0.01`、`netload=10`、`--factorial-pilot --factorial-drop-diag`、并发 1，均为独立构建、源码、输出和结果目录；执行前逐 ID 核查空闲。先新 SHA optimized 构建与 `devices-point-to-point` 单测，再背景关/开确认诊断不扰动，再混合关/开。四格终态后使用 `scripts/verify_ws23_crossclass.py --source-sha 154f537ec345df75fbb404a1674436535f92735b <四个 ID，按表顺序>`；脚本要求每流完成、背景首行身份一致、两组各自诊断开/关 FCT 哈希一致、无背景准入丢包或超时，也没有任何队列拒绝/额外丢弃警告；ToR 32 同一实际出口上两类流活动时段重叠，且混合格背景 FCT、该出口平均排队等待和 MMU 端口占用均高于背景单独格。任一方向不成立，只能报告**该合成输入未建立预定因果前提**；保存 raw，重新设计需新输入 SHA/ID，不从结果事后挑端点或改判据。四格即使通过，也只确认该受控输入的共享出口影响；隔离候选与同输入 ECMP 的双侧比较、独立需求和实际业务界限仍是后续必做项。

在已确认远端入口空闲、候选 SHA 已推送并同步后，逐格执行以下命令。每个 `build` 完成后先核对 optimized 构建结果；第一格构建后还须通过 `devices-point-to-point` 单测，再启动该格。每个 `run` 前让快速资源观察器对相应 ID 写出 `READY`，终态后 `status → fetch`，核验元数据、raw 与资源收据，才进入下一格。诊断开关之外，同组两格参数完全相同。

```powershell
python scripts/remote_experiment.py build --repo-local . --source-sha 154f537ec345df75fbb404a1674436535f92735b --id 20261001-091000-ws23-bg-off
python scripts/ws23_start_resource_watch.py 20261001-091000-ws23-bg-off --source-sha 154f537ec345df75fbb404a1674436535f92735b
python scripts/remote_experiment.py run 20261001-091000-ws23-bg-off --lb fecmp --pfc 0 --irn 1 --simul-time 0.01 --netload 10 --bw 100 --buffer 9 --topo fat_k4_100G_OS2 --cdf AliStorage2019 --flow-file config/ws23_crossclass_bg_1x8MiB.txt --factorial-pilot --factorial-drop-diag --max-concurrent 1
python scripts/remote_experiment.py build --repo-local . --source-sha 154f537ec345df75fbb404a1674436535f92735b --id 20261001-091100-ws23-bg-on
python scripts/ws23_start_resource_watch.py 20261001-091100-ws23-bg-on --source-sha 154f537ec345df75fbb404a1674436535f92735b
python scripts/remote_experiment.py run 20261001-091100-ws23-bg-on --lb fecmp --pfc 0 --irn 1 --simul-time 0.01 --netload 10 --bw 100 --buffer 9 --topo fat_k4_100G_OS2 --cdf AliStorage2019 --flow-file config/ws23_crossclass_bg_1x8MiB.txt --ws13-diag 1 --factorial-pilot --factorial-drop-diag --max-concurrent 1
python scripts/verify_ws23_crossclass.py --source-sha 154f537ec345df75fbb404a1674436535f92735b --pair background 20261001-091000-ws23-bg-off 20261001-091100-ws23-bg-on
python scripts/remote_experiment.py build --repo-local . --source-sha 154f537ec345df75fbb404a1674436535f92735b --id 20261001-091200-ws23-mix-off
python scripts/ws23_start_resource_watch.py 20261001-091200-ws23-mix-off --source-sha 154f537ec345df75fbb404a1674436535f92735b
python scripts/remote_experiment.py run 20261001-091200-ws23-mix-off --lb fecmp --pfc 0 --irn 1 --simul-time 0.01 --netload 10 --bw 100 --buffer 9 --topo fat_k4_100G_OS2 --cdf AliStorage2019 --flow-file config/ws23_crossclass_bg_plus_3x4MiB.txt --factorial-pilot --factorial-drop-diag --max-concurrent 1
python scripts/remote_experiment.py build --repo-local . --source-sha 154f537ec345df75fbb404a1674436535f92735b --id 20261001-091300-ws23-mix-on
python scripts/ws23_start_resource_watch.py 20261001-091300-ws23-mix-on --source-sha 154f537ec345df75fbb404a1674436535f92735b
python scripts/remote_experiment.py run 20261001-091300-ws23-mix-on --lb fecmp --pfc 0 --irn 1 --simul-time 0.01 --netload 10 --bw 100 --buffer 9 --topo fat_k4_100G_OS2 --cdf AliStorage2019 --flow-file config/ws23_crossclass_bg_plus_3x4MiB.txt --ws13-diag 1 --factorial-pilot --factorial-drop-diag --max-concurrent 1
python scripts/verify_ws23_crossclass.py --source-sha 154f537ec345df75fbb404a1674436535f92735b --pair mixed 20261001-091200-ws23-mix-off 20261001-091300-ws23-mix-on
python scripts/verify_ws23_crossclass.py --source-sha 154f537ec345df75fbb404a1674436535f92735b 20261001-091000-ws23-bg-off 20261001-091100-ws23-bg-on 20261001-091200-ws23-mix-off 20261001-091300-ws23-mix-on
```

上面的四格命令是**逐格执行**，不是一次性粘贴连续启动。每次 `run` 后先 `status <该 ID>` 确认终态，再用 `python scripts/ws23_start_resource_watch.py <该 ID> --source-sha 154f537ec345df75fbb404a1674436535f92735b --wait` 确认运行中正 RSS 收据并检查资源阈值，随后 `fetch <该 ID>` 和逐格元数据/raw 核验。背景开关配对两格的 FCT 字节哈希须先一致，才进入混合两格；四格终态且 raw 全数回传后才运行跨类验收器。任一失败保留 ID、远端 raw 与本地已回传内容，停止后续格并定位；不重跑或覆盖旧 ID。

## 资源、隔离与停止

运行前核对独立副本在 `feature/ws23-validation-execution`、工作树干净、本地 HEAD 与个人 fork 同分支一致；两个固定仿真 SHA 都是该 HEAD 的祖先，三份输入与拓扑的 **Git 内容**哈希仍等于上文冻结值。再确认五个 ID 在本地和远端均未占用、共享 worker 已协调、没有其他用户作业或现有 ns-3/构建进程，load1m ≤10、可用内存 ≥32 GiB、磁盘 ≥100 GiB；每格 `-j2` 构建、单仿真并发上限 1。构建超过 20 分钟、单格仿真超过 10 分钟、他人作业出现、load1m >20、进程树 RSS >8 GiB、可用内存 <16 GiB、磁盘 <100 GiB、文本日志 >50 MiB、资源收据缺失、身份/隔离不成立或状态失败时停止新格，保留已有结果并诊断。资源观察器在仿真开始前就绪，`--wait` 会核对运行中正 RSS 采样及资源停止阈值；短格终态及时 `status → 资源收据 → fetch → 验收`，不覆盖旧 raw。

**执行边界：**WS-24 当前独占共享 `remote_worker.py`。本页的 SHA/ID/输入是本地冻结，不表示远端已同步、构建或执行；远程前由监督任务再次检查 worker 版本、两任务在途作业及模型切换。WS-23 保持 ACTIVE，不能用本技术小样替代原隔离目标或提前归档。
