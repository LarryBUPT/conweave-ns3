# WS-25 DestSpread v2 独立需求探索筛选

状态：2026-10-06，任何筛选格构建或运行前冻结。本阶段只决定是否进入另组 seed 的校准 pilot，不产生正式收益结论；v1 的 576 格主 NO-GO 保持不变。

## 估计单位和身份

- 独立单位为需求 seed `20262545–48`，与 v1 筛选/校准 `20262501–08` 和 v1 正式 `20262521–44` 不重合。四 seed 只作探索性筛选；另预留 `20262549–52` 作校准和资源 pilot、`20262553–76` 作未见正式池，后两组此时不读取仿真结果。
- 用原 `scripts/make_ws25_demand.py` 按种子生成同分布需求，固定 16,384 条 8 KiB MoE 与 192 条 8 MiB 背景流，均从 2.000 s 开始。每 seed 的六主臂复用逐字节相同的 trace；四组输入及 SHA 在[输入清单](evidence/ws25-v2-screen-inputs.json)。行顺序和同 seed 多个模式不是新的独立样本。
- 六主臂为 ECMP、DRILL、CONGA、LetFlow、ConWeave、DestSpread；每 seed 增加一格 `destspread` 且 `ws25_diag=1` 的同输入非扰动诊断，共 4×7=28 个唯一 ID。固定构建提交 `7aa09f5ab8e9cd7ef852db3c3fab6aa551ca8ecb`；其 `src/`、`scratch/`、`run.py` 与已过小输入正确性的仿真提交 `87bb136ba85126c8c6c883814c7fa10cdcd74fda` 完全相同。拓扑 SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。
- 运行条件为 ns-3 seed=1、400 Gbps、9 MiB、DCQCN、PFC=0、IRN=1、`simul_time=0.01`、`netload=10`；六主臂 `ws25_diag=0`。按[冻结计划](evidence/ws25-v2-screen-plan.json)的 `2026100614` 随机顺序运行配对块，先完成 seed45 的七格并逐格验收，再扩到其余三组。控制器修改和重试不改计划、输入、原 ID 或仿真源码；失败 ID 不复用、不覆盖 raw。

## 正确性、观测和筛选口径

每格核对 metadata、构建 SHA、trace/拓扑 SHA、参数、输入流身份和字节、FCT 与类别全完成率、候选队列守恒，以及原始日志和资源收据。任一格失败暂停新格；若正确性代码需修复，v2 至多一次诊断修正，另固定 SHA/ID 并重验受影响比较。诊断格需与同 seed 候选主格的完整 FCT 原始 SHA 相同，逐 QP 记录 16,576 条，tag1/tag2 数量正确，并有背景逐跳和未配对计数。缺失观测不能填零；诊断有扰动则保留其 raw，不将日志解释为非扰动机制证据。

两项探索性结果都从完整 raw 配对计算：MoE 合成批次为最后一个 MoE 流完成绝对时刻减 2.000 s；背景 P99 为 192 条背景流 FCT 的线性插值第 99 百分位。对每 seed 报告 `100×(DestSpread/ECMP−1)`，并同时列出与其他四基线的两项绝对值、变化和反例。只在 28/28 全部通过后作方向筛选：相对 ECMP，两项各自四 seed 中位变化均≤−5%，且各至少 3/4 seed 严格改善，才进入另组 seed 的校准 pilot；否则完整报告并用诊断判断 v2 一次修正或第三候选，不从这四 seed 作正式 NO-GO 或正向主张。此筛选线仅管理迭代，正式 24 seed 的共同主判据仍需在未见最终池运行前另冻，不能借用筛选结果冒充确认性统计。

## 资源和恢复

首块 cap=1，以全量需求实测资源；其余块只有在首块逐格通过且新准入检查通过后尝试 cap=4。每批前核无其他用户作业、未知 ns-3/worker、启动锁、load≤20、每 worker 预留 5 GiB 后 MemAvailable≥32 GiB、空盘≥100 GiB；每格 watcher 先于 run，进程树 RSS≤32 GiB。出现争用、资源异常或吞吐下降则降载或暂停新格。构建、SSH 或 fetch 超时先按原 ID 查 metadata/PID/raw 和本地收据，绝不双重启动或覆盖。小输入校准/诊断、此次筛选及后续资源 pilot 都不算正式收益证据；两类业务仍共同重要，模型仅是两类 RDMA QP，不能称真实控制消息与 TCP/UDP 混跑。
