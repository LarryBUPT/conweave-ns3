# WS-23 两格端到端正确性预飞行协议

日期：2026-09-30。执行分支 `feature/ws23-validation`。本协议只验证 IRN+PFC 恢复正确性，不比较性能。旧修复 `12dea54d421243ddb98c83437b929944ab6d128c` 的 optimized build `20260930-175600-ws23-recovery-build` 和隔离 `devices-point-to-point` 单测已通过；下面的**新增诊断与验收源码**尚未构建或仿真。

## 冻结资产与两格

仿真/运行器源码均固定为 `70bf890d1ceba58c5ebd26b17e492295b34c99ca`。后续纯文档提交只移动分支 HEAD，不改变这份源码。共同使用 `fat_k4_100G_OS2`，Git 内容 SHA-256 `dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad`；ECMP、DCQCN、IRN=1、PFC=1、100 Gbps、`simul_time=0.01`、`netload=10`、seed=1、`--factorial-pilot --factorial-drop-diag`。每格独立源码和结果目录，`--max-concurrent 1`。

| 预留 ID | 目的与唯一差异 | Git 内容 SHA-256 | 必过门槛 |
| --- | --- | --- | --- |
| `20260930-201500-ws23-lossless-pause` | `config/ws23_pause_probe_1x1MiB.txt`，主机 0→24、PG 3、一条 1 MiB 流在 2.006 s 启动；9 MiB buffer。源侧相邻交换机于 2.006000200 s 发送 2500 µs PFC pause，于 2.007800200 s 显式 resume；两时刻相对 2.000 s 流量窗口为 6,000,200 / 7,800,200 ns。 | `4f10f678000f7b380cc272e121db7926ca320a581c72b47909545f31f2a312f8` | pause/resume 真到主机 0、PG 3，持续超过最长 1350 µs RTO 且处于流传输中；若发生 RTO 延期则为正时长（无损流可能已收到全部 ACK，故不要求必有延期）；1/1 完成、QP `snd_una=snd_nxt=tx_payload_bytes=size`，无超时恢复、无数据/ACK 准入丢弃、队列拒绝或链路丢失。 |
| `20260930-201600-ws23-loss-recovery` | 旧 `config/ws09_drop_probe_16x1MiB.txt`，16 条各 1 MiB，1 MiB buffer，不注入 PFC。 | `bc2db1513cbde20f12eea6efa4e2265cf74954be4fa45f2a147ff0ce84b33985` | 两类各 8/8、合计 16/16 完成；16 个唯一 QP 的 `snd_una=snd_nxt=size`、发送 payload 不少于 size；复现真实数据准入丢失并发生超时恢复；恢复均在对应源 PG 非暂停期，延期事件为正时长未来事件。 |

两格使用 `scripts/verify_ws23_recovery.py --scenario pause|pressure --source-sha 70bf890d1ceba58c5ebd26b17e492295b34c99ca <实验ID>` 核对元数据、trace/拓扑快照、FCT、QP、PFC 和丢包原始记录。验收脚本已经拒绝旧 `20260927-215700-irnpfcstress-11`（旧源码且只有 13/16）。旧格的 `SUCCEEDED` 仅代表 FCT 非空，不能代替完成门槛。运行后还要人工核对验收摘要、配置快照、原始文件哈希、worker 状态和资源收据。

## 执行顺序与资源停止条件

1. 在真实 Luna High 监督任务中先核对个人 `origin` 与本地分支、固定源码 SHA、两预留 ID 在本地/远端未占用，再 `deploy` 更新远端 worker、`sync` 固定源码。先隔离构建 ID `20260930-201400-ws23-gate-build`，对 **`70bf890…`** 做 optimized build 及启用测试的 `devices-point-to-point` suite。若仍遇仓库既有 core 测试 helper const 问题，仅在该隔离源码副本修正、测试后恢复并核对源码；不可让测试 workaround 进入仿真 SHA。构建或单测失败则保留 ID 与日志，修复后重新提交并冻结新 SHA/ID。
2. 只读核对服务器登录用户、其他作业、ns-3/构建进程、CPU、load、内存、工作区磁盘：没有他人作业，load1m ≤10，可用内存 ≥32 GiB、磁盘 ≥100 GiB 才启动。两格分别从固定 SHA 以 `-j2` 独立构建；先无损暂停格作资源与注入 pilot，通过其原始验收后才启动压力格。每格 `max-concurrent=1`，运行资源观察器并保存逐点及终态收据。构建若超过 20 分钟、单格仿真若超过 10 分钟，停止启动后续格并诊断，不复用该 ID。
3. 观察器或资源出现异常即停止新格并保留已有 raw：任何他人作业、load1m >20、进程树 RSS >8 GiB、可用内存 <16 GiB、磁盘 <100 GiB、文本日志 >50 MiB、资源收据缺失、隔离不成立或运行状态失败。正常后台仿真静默运行，约半小时只读一次完成数与资源摘要；短格终态及时处理，不重复轮询或输出逐包日志。
4. 每格完成后先 `status`，再 `fetch` 到本地唯一 ID，运行相应验收器。任何断言失败都保留 raw、定位问题、修复并固定新源码 SHA 与独立新 ID；不能覆盖旧结果，也不能因为压力格或性能 gate 负向而跳过另一项正确性验证。两格终态原始结果回传后实际切回 Sol High，逐项核对源码、效果、限制并更新清单。未完成前 WS-23 保持 ACTIVE。

冻结命令参数如下；在执行前按上面的资源、ID 和模型门槛检查，不直接把这些命令视为已运行：

```powershell
python scripts/remote_experiment.py run 20260930-201500-ws23-lossless-pause --lb fecmp --pfc 1 --irn 1 --simul-time 0.01 --netload 10 --bw 100 --buffer 9 --topo fat_k4_100G_OS2 --cdf AliStorage2019 --flow-file config/ws23_pause_probe_1x1MiB.txt --factorial-pilot --factorial-drop-diag --ws23-pfc-probe-host 0 --ws23-pfc-probe-pg 3 --ws23-pfc-probe-start-ns 6000200 --ws23-pfc-probe-end-ns 7800200 --ws23-pause-time-us 2500 --max-concurrent 1
python scripts/remote_experiment.py run 20260930-201600-ws23-loss-recovery --lb fecmp --pfc 1 --irn 1 --simul-time 0.01 --netload 10 --bw 100 --buffer 1 --topo fat_k4_100G_OS2 --cdf AliStorage2019 --flow-file config/ws09_drop_probe_16x1MiB.txt --factorial-pilot --factorial-drop-diag --max-concurrent 1
```

## 原隔离目标的可证伪前置条件

旧 PFC=0 常规格虽然 320/320 完成，但没有真实 PFC 动作，也没有证明两类流在同一个可控瓶颈上互相阻塞。修复恢复逻辑后，仍需单独构造固定背景需求与可变拥塞需求：明确两类共用的交换机出口、实际入队等待/准入丢弃/完成时刻，保持背景流和总配置不变，仅改变拥塞流的出现或强度。先证明背景受影响且来源于该共享出口，再比较隔离候选与同输入 ECMP，并同时报告拥塞类收益与背景类代价。目的主机的唯一最终出口无法靠上游选路隔离；若目标声称可缓解该出口阻塞，必须有可作用于该出口的机制和对应观测。当前物理队列和逐类等待证据不足，需先补非扰动观测和最小因果对照；此缺口不取消上面两格传输正确性验证，也不把旧技术格当作隔离收益。

**当前状态：**只完成本地源码、静态输入/解析检查与本协议冻结；本 SHA 尚无 C++ build、端到端仿真或新的 raw。两格结果均待实际运行。
