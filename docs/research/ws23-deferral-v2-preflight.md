# WS-23 延期探针 v2：双格预飞行

日期：2026-10-01。状态：**v2 control/probe 两格已运行，原始验收器通过；终态 Sol High 复核尚待具备模型切换能力的任务完成。** 本协议只处理 IRN×PFC 动态延期的端到端正确性，不构成性能收益结论。跨类共享出口四格按[原预飞行](ws23-next-correctness-and-causal-preflight.md#b-共享可改道出口因果技术小样四格)自身门槛独立推进，不以本探针通过为前置；两者均不能替代后续隔离候选的双侧验证。

## 固定输入与预留身份

仿真源码及验收器提交：`94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1`；分支 `feature/ws23-validation-execution`。输入 `config/ws09_drop_probe_16x1MiB.txt` 的 Git 内容 SHA-256 为 `bc2db1513cbde20f12eea6efa4e2265cf74954be4fa45f2a147ff0ce84b33985`，拓扑 `config/fat_k4_100G_OS2.txt` 为 `dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad`。两格固定 seed=1、ECMP、100G、1 MiB buffer、PFC=1、IRN=1、`simul_time=0.01`、`netload=10`、`--factorial-pilot --factorial-drop-diag`、并发 1；常规全网 `PAUSE_TIME=5 µs`。

实际使用的独立 ID：无探针对照 `20261001-151000-ws23-rto-v2-control-r2`，定向探针 `20261001-151100-ws23-rto-v2-probe-r2`。前一组格式合法的 `20261001-150000-ws23-rto-v2-control` 在 2026-10-01 第一次远程启动后失败并保留：optimized 构建成功，但单测准备误把测试开关写入默认构建目录；恢复默认 lock 后，Waf 又尝试编译已知有 const 缺陷的测试 helper，导致仿真前失败。其 raw、错误日志和正 RSS 收据已回传；不得复用该 ID。对应未运行的 `20261001-150100-ws23-rto-v2-probe` 也不复用。失败分析见[Handoff 53](../handoffs/2026-10-01-53-ws23-rto-v2-control-build-failure.md)，本次双格结果见[Handoff 54](../handoffs/2026-10-01-54-ws23-rto-v2-correctness-results.md)及[机器证据](evidence/ws23-deferral-v2-20261001.json)。

同固定源码 SHA `94f08c6e…` 的 `devices-point-to-point` 套件已在隔离测试配置中通过 1/1；临时测试 helper 与默认配置均已从固定 Git 源码/备份恢复并校验。两次 r2 simulation 均从固定 SHA 新建干净 optimized 副本，未在 simulation 默认输出目录开启单测。

探针只给源主机 14 的 PG 3 注入 2500 µs 暂停帧：相对流量起点 2 s 的 `7200000 ns` 触发，`8800000 ns` 显式恢复，每 `1000 ns` 刷新暂停帧。注入时必须已记录源 14 的真实准入丢包且目标 QP 有未确认数据，否则仿真明确失败。正常 PFC 帧继续使用 5 µs。延后提前结束检查直至显式恢复后再经过 1.35 ms，供完整 RTO 观察。实际 raw 已核实唯一触发、暂停与恢复到达源端、暂停期与恢复宽限期均延期、完整 RTO 后恢复，以及所有 QP 字节/序号守恒；仅对本固定合成输入成立。

## 顺序执行与逐格验收

先按[远程实验工作流](../REMOTE_EXPERIMENT_WORKFLOW.md)确认个人 fork 同名分支已推送固定 SHA、共享 `remote_worker.py` 与 WS-24 的使用边界、远端在途作业、资源和两个 ID。若共享入口仍被占用，保持本地冻结并协调，不部署或启动。本地和远端 worker 版本必须对应；只在协调后部署。后台监督开始前须**实际**切换至 GPT-6 Luna High；终态 raw 回传后须实际切回 GPT-6 Sol High。提示文字不算切换。本轮 Luna High 监督已按集成线程记录生效；当前任务工具没有 Sol High 切换接口，故机器验收已完成，终态复核仍待具备模型切换能力的任务完成。

1. 先从固定 SHA 隔离构建 `control`，核对 optimized build；按已有资源观察器流程在该 ID 的独立 `logs/` 启动并确认 `READY`，再运行下列无探针命令。终态核对正 RSS 收据，回传 raw，执行 `pressure` 验收。还须核对 16/16 完成、161 次准入丢包、源 14 在探针起点前的 36 次丢包，以及 FCT SHA-256 `97feb0e118544f07e006da9e9bc2ead2566a10b91ad2201e0e83ced89279b18a`。任一不符即停，不启动探针。
2. 同 SHA 隔离构建 `probe`，同样观察器先 `READY`、后运行。终态收资源收据并回传 raw，用 `deferral-v2` 双格验收器逐项核对。验收器要求探针前丢包日志与对照逐条相同，目标真实丢包并携未确认数据进入暂停；暂停中正时长延期、显式恢复后宽限期延期、最近一次恢复后完整 RTO 才超时恢复；源 PG 暂停期无恢复，两类各 8/8、16 个 QP 序号与字节守恒。刷新收据必须为 1599 次，暂停/恢复需抵达源主机，仿真必须持续到显式恢复后的观察窗口。

```powershell
python scripts/remote_experiment.py build --repo-local . --source-sha 94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1 --id 20261001-151000-ws23-rto-v2-control-r2
python scripts/ws23_start_resource_watch.py 20261001-151000-ws23-rto-v2-control-r2 --source-sha 94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1
python scripts/remote_experiment.py run 20261001-151000-ws23-rto-v2-control-r2 --lb fecmp --pfc 1 --irn 1 --simul-time 0.01 --netload 10 --bw 100 --buffer 1 --topo fat_k4_100G_OS2 --cdf AliStorage2019 --flow-file config/ws09_drop_probe_16x1MiB.txt --factorial-pilot --factorial-drop-diag --max-concurrent 1
python scripts/remote_experiment.py status 20261001-151000-ws23-rto-v2-control-r2
python scripts/ws23_start_resource_watch.py 20261001-151000-ws23-rto-v2-control-r2 --source-sha 94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1 --wait
python scripts/remote_experiment.py fetch 20261001-151000-ws23-rto-v2-control-r2
python scripts/verify_ws23_recovery.py --scenario pressure --source-sha 94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1 20261001-151000-ws23-rto-v2-control-r2

python scripts/remote_experiment.py build --repo-local . --source-sha 94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1 --id 20261001-151100-ws23-rto-v2-probe-r2
python scripts/ws23_start_resource_watch.py 20261001-151100-ws23-rto-v2-probe-r2 --source-sha 94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1
python scripts/remote_experiment.py run 20261001-151100-ws23-rto-v2-probe-r2 --lb fecmp --pfc 1 --irn 1 --simul-time 0.01 --netload 10 --bw 100 --buffer 1 --topo fat_k4_100G_OS2 --cdf AliStorage2019 --flow-file config/ws09_drop_probe_16x1MiB.txt --factorial-pilot --factorial-drop-diag --ws23-pfc-probe-host 14 --ws23-pfc-probe-pg 3 --ws23-pfc-probe-start-ns 7200000 --ws23-pfc-probe-end-ns 8800000 --ws23-pause-time-us 2500 --ws23-pfc-probe-drop-gated --ws23-pfc-probe-refresh-ns 1000 --max-concurrent 1
python scripts/remote_experiment.py status 20261001-151100-ws23-rto-v2-probe-r2
python scripts/ws23_start_resource_watch.py 20261001-151100-ws23-rto-v2-probe-r2 --source-sha 94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1 --wait
python scripts/remote_experiment.py fetch 20261001-151100-ws23-rto-v2-probe-r2
python scripts/verify_ws23_recovery.py --scenario deferral-v2 --source-sha 94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1 --control-id 20261001-151000-ws23-rto-v2-control-r2 20261001-151100-ws23-rto-v2-probe-r2
```

上列命令**逐步执行**：每次 `build` 后核对构建与必要单测，每次观察器见 `READY` 才 `run`，每次 `status` 到终态后才收收据和 `fetch`。失败格的 ID、远端记录和 raw 保留；若旧设计假设失效，定位后另冻 SHA/ID，不改弱断言来接收结果。资源准入及停止阈值沿用[上一预飞行](ws23-next-correctness-and-causal-preflight.md#资源隔离与停止)：无人作业、load1m ≤10、可用内存 ≥32 GiB、磁盘 ≥100 GiB；构建 >20 分钟、单格 >10 分钟、他人作业、load1m >20、RSS >8 GiB、内存 <16 GiB、磁盘 <100 GiB、日志 >50 MiB、收据缺失或隔离失败均停止新格。

本机只做静态检查；两次 optimized 构建、单测收据复用、对照和探针均已在远端按固定 SHA 执行并回传 raw。验收脚本通过不代替 Sol High 对原始数据的独立复核。WS-23 保持 ACTIVE：跨类四格 PFC=0 的 C++ 和仿真仍待执行；隔离候选双侧对照、结果归因与最终源码/效果/结论一致性核验仍属必做。

## 双格运行结果（2026-10-01）

两格使用同一固定源码、trace、拓扑、seed 和公共配置。control `20261001-151000-ws23-rto-v2-control-r2` 与 probe `20261001-151100-ws23-rto-v2-probe-r2` 均 `SUCCEEDED`、16/16 完成；pressure 和 deferral-v2 验收器均以退出码 0 通过。对照重现 161 次准入丢包、源 14 的 36 次目标丢包及预期 FCT SHA-256 `97feb0e118544f07e006da9e9bc2ead2566a10b91ad2201e0e83ced89279b18a`。探针前丢包逐行与对照一致；唯一门控触发时目标 QP 有未确认数据；主机 14/PG 3 的 pause/resume 到达源端，刷新 1599 次；验收器记录暂停期间 4 次延期、恢复宽限期间 1 次延期，完整 320 µs RTO 后于 `2009121003 ns` 恢复；仿真持续至 `2017100000 ns`。两类各 8/8 完成，16 个 QP 序号与字节守恒，无其他队列/链路丢包。

control/probe 进程树峰值 RSS 分别为 204.26/204.39 MiB；最低可用内存为 122.82/122.82 GiB，最低空闲磁盘为 5656.93/5655.88 GiB，最高采样负载为 1.44/1.60。原始文件和逐项结果见机器证据索引。结论只支持**此固定合成压力输入下动态延期与恢复契约按设计执行**；不支持性能提升、普遍无损、跨类隔离或真实部署结论。WS-23 仍 ACTIVE：跨类因果四格和隔离候选双侧验证仍未完成，Sol High 原始数据复核待实际模型切换后完成。
