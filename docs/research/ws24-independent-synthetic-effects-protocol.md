# WS-24 独立合成 job 需求四臂效果协议

日期：2026-10-02。状态：**本地输入与分析契约已冻结；远程 pilot 和矩阵尚未运行；WS-24 ACTIVE**。用户已明确决定“不要真实主机数据，仅NS3模拟”，见 [ADR-009](../decisions/ADR-009-ws24-ns3-only-scope.md)。本文只支持 ns-3 合成模型内的结论，不表示真实服务器多 NIC 或真实 job 性能。

## 目标与实验单位

目标是在已通过正确性验收的 320-host × 4-NIC 合成拓扑中，检验相同逻辑 job 需求下多 rail 相对单 rail 的完成跨度差，以及固定/可变 rank 放置的条件差异。**独立单位为一份由独立生成 key 产生的 job 需求块，共 12 块**；每块的四臂属于同一配对块，30 条流不是 30 个独立样本，四臂也不是四个独立 job。它们都是合成模型，不来自物理集群或采集到的业务 trace。先前 `b1184d6…` 的 14 格 raw 已从原始数据验收；其中 D 的一组 10 流 seed pilot 只作前置正确性与资源依据，不并入本矩阵样本。

固定源码提交：`166ca6709e2b6ea8b60978bf80778fee636937e5`，分支 `feature/ws24-multinic-validation`，个人 origin `LarryBUPT/conweave-ns3`。源码、48 个输入和验收脚本都在该提交；后续文档 HEAD 不改变本批实验身份。`config/ws24_independent_manifest.json` 的 Git/工作树 SHA-256 为 `e94251d3717f368b8f7c1bd1de5788d524559f8dc65c5b788aeb874ccbc2977d`。manifest 含 12 个生成 key、48 个 flow 文件 SHA-256、每 job 逻辑需求哈希/host 放置/总字节、48 个唯一实验 ID 和随机化执行顺序。目标 topology SHA-256 `e82f742a1f07749de63706c94c29b3275ec908c61a967f6336988526213bf6fa`；NIC 清单 SHA-256 `4a4bc61466efd15983bf6a6e7a3e69e153cb00760f909a98311d1f9c17481202`。输入文件均由 Git 字节哈希核对；旧 14 格输入/raw 不改。

## 需求生成与四臂配对

`scripts/make_ws24_independent_inputs.py` 用 SHA-256 PRF 的 master seed `20261002` 和 12 个不同 key `20261002|1` 至 `20261002|12` 固定生成过程。每块从预定 16 个合成 host 候选中选 4 个不同 host；可变放置只交换 rank 1/2 的 host。每块 30 条流，包括所有 rank 有向对、另外 12 条独立抽样有向对和 6 条指向该块热点 rank 的流；流大小从 8 KiB 至 1 MiB 的冻结离散集合独立抽取，三个到达波次各有独立 jitter。不同块的逻辑需求哈希及固定放置均不同，字节范围为 2,695,168–10,928,128 B。四臂内的 flow_id、job/rank 两端、PG、大小、到达时间和 tag 逐项相同；只有 rank→host 放置与 rail 策略改变。单 rail 全部使用 rail 0，多 rail 为 flow_id mod 4。ns-3 `RANDOM_SEED=1` 在四臂和所有块保持固定，它不代替需求生成 key。

四臂为 `fixed_single`、`fixed_multi`、`variable_single`、`variable_multi`。文件名、Git 字节 SHA-256 与实验 ID 逐项见 manifest，不以相同 trace 的行序置换充当独立样本。`python scripts/make_ws24_independent_inputs.py --check` 与 `python scripts/verify_ws24_independent_inputs.py` 在本地通过：48/48 文件逐字节再生成一致、12 个逻辑哈希互异、四臂配对/host/NIC/同 rail 可达/输入字节通过。旧 14 格 `verify_ws24_matrix.py` 重跑仍为 14/14。**这只是离线门槛，尚未证明新 30 流动态仿真正确性。**

## 运行身份、顺序与资源 pilot

每格使用 manifest 中唯一 `20261002-180000-ws24-ind-jNN-{fs,fm,vs,vm}` ID，`--source-sha` 指定上述共同提交。参数：`fecmp`、`ws24_multi_nic=1`、目标 topology/NIC、`--bw 400 --buffer 9 --pfc 0 --irn 1 --simul-time 0.01 --netload 10`，显式 flow 文件按 manifest；`run.py`/ns-3 seed=1。每格独立源码、raw、日志、metadata 和资源收据；失败 ID 不复用，修复后新 SHA/ID，并复核需要重跑的同条件对照。

远端现有共享 worker SHA-256 为 `9e1b4e…`，只读检查未找到 WS-24 参数入口；不得覆盖它。控制器新增显式 `--worker-name ws24_worker.py`，仅把本分支 worker 部署到 `/home/fnl/lzy/.research-workflow/ws24_worker.py`，该路径预飞行时不存在；默认 worker 路径仍不变。部署后须核对其 SHA-256 等于本分支 `scripts/remote_worker.py` 的 `0be12e21ce37655f52a19803824f2b8d24a9a2c84ba0cd58124eb6fb96de62eb`。所有 `deploy/check/sync/build/run/status/fetch` 命令须在子命令前带 `--worker-name ws24_worker.py`；不得触碰 WS-23 checkout 或共享 worker。

入口只读采样（2026-10-02 本地时间约 01:49）：0 登录用户、load1m 0.00、MemAvailable 约 122 GiB、工作区空闲约 5,597 GiB、无 waf/cc1plus/ns-3/run.py 作业；48 个预留 ID 的 runs/results 路径均未发现。该采样不是未来启动许可。**远程运行前必须由监督方实际切换本任务至 GPT-6 Luna High**，重新核对无人/未知或 WS-23 作业、worker 隔离、ID 空闲、load1m ≤10、MemAvailable ≥32 GiB、空闲盘 ≥100 GiB，再部署独立 worker、同步固定 SHA 并启动。

先按 `j01` 四臂做动态正确性和资源 pilot，按 manifest 的四个 ID 各自 build/run/fetch/逐流验收。旧 D 四格历史每格 46 个资源样本、峰值进程树 RSS 约 7,258 MiB、最低 MemAvailable 约 115.9 GiB；它们只支持新 pilot 的初始单格并发上限 1，不代表新 30 流成本已验证。pilot 中确认 30/30 输入流完成、逐流 NIC/IP/rail/job/rank 和收发字节守恒、目标图运行时 600 ns/30,000 B、资源采样完整；四臂同一逻辑需求及总字节一致。若任一失败，保留该 ID/raw，停止扩格并诊断；不得依据效果方向调整输入。pilot 通过后按 manifest `run_order` 去掉 j01 四臂的顺序完成余下 44 格，先用 2 个 CPU 令牌的单格编译/仿真，再在同一批实测资源允许时逐级提高并发，记录令牌、峰值和降载依据。

每格沿用安全门槛：构建 ≤20 分钟、仿真 ≤10 分钟、每 5 秒资源采样；运行中 load1m >20、单格进程树 RSS >8 GiB、MemAvailable <16 GiB、空闲盘 <100 GiB、单文本日志 >50 MiB、采样缺失、其他用户/未知作业或命令失败即停止后续新格，保留 raw 和日志。后台正常约半小时只读一次完成数/失败数/资源峰值摘要；资源异常立即降载或暂停。旧 14 格和失败单测 ID 均不重写。

## 事前分析与双侧判据

每格以 `scripts/verify_ws24_result.py --profile independent --fixture jNN_<arm>` 核对 metadata/source SHA、输入快照哈希、运行时路由/BDP、30/30 完成、FCT/WS24 逐流身份、唯一接收/ACK/发送字节和资源收据。全矩阵用 `scripts/verify_ws24_independent_matrix.py --source-sha <固定SHA>` 从 48 份 raw 独立重算，并对同一 job 四臂按 flow_id 配对；任何缺格、哈希不符、未完成或资源收据越界均使矩阵不通过。

每 job×arm 的完成跨度为 `max(finish_ns)−min(demand_ns)`。主指标对每个独立 job 计算 `r_j = 0.5×[log(span_fixed_multi/span_fixed_single)+log(span_variable_multi/span_variable_single)]`，即多/单 rail 完成跨度比例在两种放置上的平均对数值；报告 12 个 job 的中位百分比差及不低于 95% 覆盖的精确次序统计量中位数区间。双侧精确符号检验以 job 为单位，排除恰为零的差值，`p≤0.05` 才称本合成生成分布内有方向证据；正负方向均按原判据报告。固定/可变放置各自差及其交互、逐流 FCT、源端准入等待、CNP/PFC/重传作为描述性机制/限制指标，不用 30 条流伪扩大样本数，不凭事后挑臂宣布显著。没有外部业务 SLO，不把统计方向自动称为实际收益。

矩阵不因中期效果大小或方向提前停机；正确性或资源失败先定位/修复，保留失败格并以新固定 SHA/独立 ID 验证。全部 48 个终态原始结果回传核对后，监督方**实际切回 GPT-6 Sol High**，复核双侧结论、反例与证据等级并更新 WS-24 状态。届时无论结果正负，均只在 ns-3 合成模型内解释；未验收前 WS-24 保持 ACTIVE，不归档。
