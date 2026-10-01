# WS-23 延期探针 v2：双格预飞行

日期：2026-10-01。状态：**本地源码与验收器已冻结；C++ 未构建，两格未运行。** 本协议只处理 IRN×PFC 动态延期的端到端正确性。跨类共享出口四格按[原预飞行](ws23-next-correctness-and-causal-preflight.md#b-共享可改道出口因果技术小样四格)自身门槛独立推进，不以本探针通过为前置；两者均不能替代后续隔离候选的双侧验证。

## 固定输入与预留身份

仿真源码及验收器提交：`94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1`；分支 `feature/ws23-validation-execution`。输入 `config/ws09_drop_probe_16x1MiB.txt` 的 Git 内容 SHA-256 为 `bc2db1513cbde20f12eea6efa4e2265cf74954be4fa45f2a147ff0ce84b33985`，拓扑 `config/fat_k4_100G_OS2.txt` 为 `dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad`。两格固定 seed=1、ECMP、100G、1 MiB buffer、PFC=1、IRN=1、`simul_time=0.01`、`netload=10`、`--factorial-pilot --factorial-drop-diag`、并发 1；常规全网 `PAUSE_TIME=5 µs`。

预留两个**全新** ID：无探针对照 `20261001-150000-ws23-rto-v2-control`，定向探针 `20261001-150100-ws23-rto-v2-probe`。首版文档的预留 ID 缺少运行器要求的六位时间段，本次在任何构建或运行之前修正；本地 `remote_experiment.py`、`remote_worker.py` 和资源观察器的 ID 校验均接受新值。本地现时未见同名结果；远程执行时还须重新确认本地和远端均空闲。旧失败 ID `20261001-090000-ws23-rto-pause` 永不复用。

探针只给源主机 14 的 PG 3 注入 2500 µs 暂停帧：相对流量起点 2 s 的 `7200000 ns` 触发，`8800000 ns` 显式恢复，每 `1000 ns` 刷新暂停帧。注入时必须已记录源 14 的真实准入丢包且目标 QP 有未确认数据，否则仿真明确失败。正常 PFC 帧继续使用 5 µs。延后提前结束检查直至显式恢复后再经过 1.35 ms，供完整 RTO 观察。该设计有本地源码审查，**能否形成预期动态事件仍须 raw 验证**。

## 顺序执行与逐格验收

先按[远程实验工作流](../REMOTE_EXPERIMENT_WORKFLOW.md)确认个人 fork 同名分支已推送固定 SHA、共享 `remote_worker.py` 与 WS-24 的使用边界、远端在途作业、资源和两个 ID。若共享入口仍被占用，保持本地冻结并协调，不部署或启动。本地和远端 worker 版本必须对应；只在协调后部署。后台监督开始前须**实际**切换至 GPT-6 Luna High；终态 raw 回传后须实际切回 GPT-6 Sol High。提示文字不算切换。

1. 先从固定 SHA 隔离构建 `control`，核对 optimized build；按已有资源观察器流程在该 ID 的独立 `logs/` 启动并确认 `READY`，再运行下列无探针命令。终态核对正 RSS 收据，回传 raw，执行 `pressure` 验收。还须核对 16/16 完成、161 次准入丢包、源 14 在探针起点前的 36 次丢包，以及 FCT SHA-256 `97feb0e118544f07e006da9e9bc2ead2566a10b91ad2201e0e83ced89279b18a`。任一不符即停，不启动探针。
2. 同 SHA 隔离构建 `probe`，同样观察器先 `READY`、后运行。终态收资源收据并回传 raw，用 `deferral-v2` 双格验收器逐项核对。验收器要求探针前丢包日志与对照逐条相同，目标真实丢包并携未确认数据进入暂停；暂停中正时长延期、显式恢复后宽限期延期、最近一次恢复后完整 RTO 才超时恢复；源 PG 暂停期无恢复，两类各 8/8、16 个 QP 序号与字节守恒。刷新收据必须为 1599 次，暂停/恢复需抵达源主机，仿真必须持续到显式恢复后的观察窗口。

```powershell
python scripts/remote_experiment.py build --repo-local . --source-sha 94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1 --id 20261001-150000-ws23-rto-v2-control
python scripts/ws23_start_resource_watch.py 20261001-150000-ws23-rto-v2-control --source-sha 94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1
python scripts/remote_experiment.py run 20261001-150000-ws23-rto-v2-control --lb fecmp --pfc 1 --irn 1 --simul-time 0.01 --netload 10 --bw 100 --buffer 1 --topo fat_k4_100G_OS2 --cdf AliStorage2019 --flow-file config/ws09_drop_probe_16x1MiB.txt --factorial-pilot --factorial-drop-diag --max-concurrent 1
python scripts/remote_experiment.py status 20261001-150000-ws23-rto-v2-control
python scripts/ws23_start_resource_watch.py 20261001-150000-ws23-rto-v2-control --source-sha 94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1 --wait
python scripts/remote_experiment.py fetch 20261001-150000-ws23-rto-v2-control
python scripts/verify_ws23_recovery.py --scenario pressure --source-sha 94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1 20261001-150000-ws23-rto-v2-control

python scripts/remote_experiment.py build --repo-local . --source-sha 94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1 --id 20261001-150100-ws23-rto-v2-probe
python scripts/ws23_start_resource_watch.py 20261001-150100-ws23-rto-v2-probe --source-sha 94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1
python scripts/remote_experiment.py run 20261001-150100-ws23-rto-v2-probe --lb fecmp --pfc 1 --irn 1 --simul-time 0.01 --netload 10 --bw 100 --buffer 1 --topo fat_k4_100G_OS2 --cdf AliStorage2019 --flow-file config/ws09_drop_probe_16x1MiB.txt --factorial-pilot --factorial-drop-diag --ws23-pfc-probe-host 14 --ws23-pfc-probe-pg 3 --ws23-pfc-probe-start-ns 7200000 --ws23-pfc-probe-end-ns 8800000 --ws23-pause-time-us 2500 --ws23-pfc-probe-drop-gated --ws23-pfc-probe-refresh-ns 1000 --max-concurrent 1
python scripts/remote_experiment.py status 20261001-150100-ws23-rto-v2-probe
python scripts/ws23_start_resource_watch.py 20261001-150100-ws23-rto-v2-probe --source-sha 94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1 --wait
python scripts/remote_experiment.py fetch 20261001-150100-ws23-rto-v2-probe
python scripts/verify_ws23_recovery.py --scenario deferral-v2 --source-sha 94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1 --control-id 20261001-150000-ws23-rto-v2-control 20261001-150100-ws23-rto-v2-probe
```

上列命令**逐步执行**：每次 `build` 后核对构建与必要单测，每次观察器见 `READY` 才 `run`，每次 `status` 到终态后才收收据和 `fetch`。失败格的 ID、远端记录和 raw 保留；若旧设计假设失效，定位后另冻 SHA/ID，不改弱断言来接收结果。资源准入及停止阈值沿用[上一预飞行](ws23-next-correctness-and-causal-preflight.md#资源隔离与停止)：无人作业、load1m ≤10、可用内存 ≥32 GiB、磁盘 ≥100 GiB；构建 >20 分钟、单格 >10 分钟、他人作业、load1m >20、RSS >8 GiB、内存 <16 GiB、磁盘 <100 GiB、日志 >50 MiB、收据缺失或隔离失败均停止新格。

本地只做了 Python 语法、配置占位符、参数拒错、`git diff --check` 和旧 raw 拒收等轻量检查。Windows 没有本项目可用的 C++ 编译环境；optimized 构建、单测、对照重现及动态延期均**未验证**。WS-23 保持 ACTIVE。跨类四格的 PFC=0 条件与本探针不同，可按独立资源与源码门槛推进；其 C++ 仍待构建、四格仍待运行。两项正确性和因果门槛即使通过，后续隔离候选双侧对照、结果归因与最终源码/效果/结论一致性核验仍属必做。
