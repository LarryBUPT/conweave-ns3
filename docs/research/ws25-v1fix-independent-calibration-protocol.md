# WS-25 ClassReserve v1 修正版独立校准协议

状态：2026-10-03，r3 身份已冻结，**只含独立校准，不是正式效果矩阵**。r1 前两格因构建 SHA 不含新 trace 而在 ns-3 启动前失败，见[Handoff 63](../handoffs/2026-10-03-63-ws25-calibration-r1-input-source-mismatch.md)；r2 前两格的 build 请求因远端尚未同步包含 SHA 的提交而无法解析 Git object，没有生成远端实验目录。该提交已通过工作流 `sync` 同步；为严格遵守失败 ID 不复用规则，r3 的 28 格全部使用全新 ID，详见[Handoff 64](../handoffs/2026-10-03-64-ws25-calibration-r2-sync-and-r3-freeze.md)。r3 使用包含全部 trace 的 Git SHA `a656104d05c681f9b3a998b5ef4ce3e644558d02`。前置正确性与同 seed 修正诊断见[11 格分析](ws25-v1fix-correctness-analysis.md)。修正参考过 seed01–04 的结果，因此本轮不复用这些需求；新校准需求为 20262505–20262508。最终验证需求池 20262521–20262544 保持未读取、未运行。

## 问题与估计单位

检查 ClassReserve v1 修正版在未看过的同分布需求上，能否重现“MoE 批次和背景 P99 的双侧候选信号”，并估计需求 seed 间差异，为后续数值门槛、样本量与 0/64/128 档约束设计提供校准数据。独立重复单位是 **需求 seed**（4 个）；每个 seed 的 ECMP、DRILL、CONGA、LetFlow、ConWeave、ClassReserve 六臂配对。流、QP、交换机、包及同 seed 诊断复跑都不是独立样本。校准只作描述性评估，不能作正式显著性、收益或 NO-GO 判决。

## 固定条件与输入

- 仿真源码/输入快照 `feature/ws25-first-paper@a656104d05c681f9b3a998b5ef4ce3e644558d02`；该提交相对算法修正版 SHA `c84108b24c94a5068861e5bb090c5aa387245ee1` 只增加已冻结输入/工作流材料，`src/`、`scratch/` 与 `run.py` 无差异。拓扑 `topo_1280_400G_400G_OS1`，SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。
- 六臂使用同一源码、拓扑及参数：NS-3 seed 1、PFC=0、IRN=1、DCQCN、400 Gbps、buffer=9 MiB、`--simul-time 0.01 --netload 10`。主性能格 `ws25_diag=0`。
- 新 trace 由 `scripts/make_ws25_demand.py` 生成；每 seed 的 192 背景主档含 16,384 个 8 KiB/tag2 MoE 流及 192 个 8 MiB/tag1 背景流，同步从 2.000 s 开始，共 16,576 流、1,744,830,464 offered bytes。全部四档输入及哈希见[manifest](evidence/ws25-v1fix-calibration-inputs.json)。
- 主档六臂 ID 每 seed 配对如下。完整确定性运行顺序见版本化[校准计划](evidence/ws25-v1fix-calibration-plan-r3.json)；执行器也会在忽略目录生成 `results/ws25-v1fix-calibration-plan-r3.json` 并逐字节检查计划未变。

| 需求 seed | flow-file | SHA-256 | ECMP | DRILL | CONGA | LetFlow | ConWeave | ClassReserve |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20262505 | `ws25_seed20262505_b192.txt` | `038d7cf09f21a56ae8e1d13164cc57e816bd14cf62631d7ff9efa59b8c1d9272` | `20261003-102000-ws25-v1fix-cal05-fecmp` | `…-cal05-drill` | `…-cal05-conga` | `…-cal05-letflow` | `…-cal05-conweave` | `…-cal05-classreserve` |
| 20262506 | `ws25_seed20262506_b192.txt` | `fe94e381938538ab7c2376614f6d8c27600b2e351c2d5e10a2b62fd14d2a8ed5` | `20261003-103000-ws25-v1fix-cal06-fecmp` | `…-cal06-drill` | `…-cal06-conga` | `…-cal06-letflow` | `…-cal06-conweave` | `…-cal06-classreserve` |
| 20262507 | `ws25_seed20262507_b192.txt` | `01b24bc1bd76d4932dd6c6e4e7ce159ff9d73824de2540ba4b09cd62e6ff83b7` | `20261003-100000-ws25-v1fix-cal07-fecmp` | `…-cal07-drill` | `…-cal07-conga` | `…-cal07-letflow` | `…-cal07-conweave` | `…-cal07-classreserve` |
| 20262508 | `ws25_seed20262508_b192.txt` | `e68616fd2de70e466f6193d7584ae77a1eb1a437efbf90c8619930dd814ded4a` | `20261003-101000-ws25-v1fix-cal08-fecmp` | `…-cal08-drill` | `…-cal08-conga` | `…-cal08-letflow` | `…-cal08-conweave` | `…-cal08-classreserve` |

每 seed 另有一格诊断控制，使用相同 ClassReserve、flow-file、SHA 与其主格 ID 时间前缀，但标签后缀为 `-classreserve-diag`，`ws25_diag=1`：

| seed | 诊断控制 ID |
| --- | --- |
| 20262505 | `20261003-102000-ws25-v1fix-cal05-classreserve-diag` |
| 20262506 | `20261003-103000-ws25-v1fix-cal06-classreserve-diag` |
| 20262507 | `20261003-100000-ws25-v1fix-cal07-classreserve-diag` |
| 20262508 | `20261003-101000-ws25-v1fix-cal08-classreserve-diag` |

共 28 个实验 ID：24 个主校准格 + 4 个诊断控制格。各 seed 是 blocking unit；seed block 顺序为 20262507、08、05、06；同 block 的七种执行条件由固定随机化种子 20262509 与 seed 派生的随机顺序排列，每两个 cell 同时运行，最多并发 2。诊断控制与同 seed ClassReserve 主格为重复测量/指纹对照，不增加 n。

## 指标及验收

- **共同主指标：** MoE synthetic batch completion time（全部 16,384 个 MoE flow 最晚完成绝对时间减 2.000 s）；背景 P99 FCT（192 个背景 flow 的完成 FCT 线性插值 P99）。若任一输入 flow 未完成，则该格指标标缺失并停止新格，不对完成者截尾计算。
- **正确性门槛：** metadata 源码/拓扑/输入哈希及参数一致；tag 输入数 192/16,384；16,576/16,576 完成；raw FCT/CNP/PFC/uplink 与 config/resource 收据齐全。ClassReserve `queue_violations=0`、入队=出队、queued drop=0、终态 current=0；MoE 与背景按流缓存均有新建和复用命中。CNP 的 ECN 与 OoO 字段分开报告；PFC=0 下空 PFC raw 视为配置预期。
- **诊断解释：** 诊断格须产生 16,576 个逐 QP 观测、tag 数正确，并记录 MoE 双选队列样本、背景出口逐跳统计及路径计数。每 seed 诊断格 FCT SHA 必须与主校准中同 seed ClassReserve SHA 一致，才将诊断解释数据标为非扰动；如不一致，仅禁用该 seed 的诊断结论，主矩阵 `ws25_diag=0` raw 不覆盖、不替代。
- **解释指标：** ClassReserve 候选两路选择/改选、flow cache 新建/复用、类别队列守恒；CNP 的 ECN/OoO、PFC、uplink 累计字节及链路不均衡。缺失指标不得填零；模拟 queue counters 不代表 MMU 物理 buffer。baseline 动态分支只有日志确实触发时才报告覆盖，入口可达不算触发。

## 资源、失败处理与后续边界

服务器开格前检查无其他用户实验/未知 ns-3/worker、worker 锁空闲、SSH/磁盘/内存健康。cap=2 已由相同 SHA 的 seed01 b192 correctness 实测，树 RSS 峰值约 4.56 GiB；本轮固定 cap=2，不再升档。每格 build 超过 30 分钟、仿真超过 4 小时、树 RSS 超过 32 GiB、1 分钟 load>20、可用内存<32 GiB、磁盘<100 GiB、哈希/完成率/守恒不符、远端未知作业或 SSH/系统异常时，停止启动新格，保留已运行与失败 ID/raw，用修复后的新 ID 重验。全部格保留独立源码、raw、metadata、日志、资源收据及 FCT 指纹。

本轮不预注册性能通过阈值，不把四个 seed 当最终样本。全部终态后由 Sol High 逐 seed 配对分析；再按工作清单处理 0/64/128 档约束与机制观测，随后依据 pilot 变异使用 statistical-power 方法确定正式最终样本量，冻结双侧数值门槛、比较方法和最终 seed/ID。正式矩阵在这些门槛冻结前关闭。远程执行前主对话须实际将本任务切到 Luna High；r3 协议、计划和 16 个新 trace 已冻结，切换生效后执行器入口为 `python scripts/run_ws25_v1fix_calibration.py run`。长时运行按约 30 分钟间隔进行精简状态检查。验收入口为 `python scripts/run_ws25_v1fix_calibration.py verify`。
