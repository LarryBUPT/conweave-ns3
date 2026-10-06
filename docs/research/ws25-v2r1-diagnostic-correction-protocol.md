# WS-25 DestSpread v2 唯一诊断修正预检

状态：2026-10-06，首个新格远程 build/run 前冻结；本协议只验证 v2 修正的正确性与非扰动观测，不产生效果结论。v1 576 格正式 NO-GO 与 v2 原版 28 格探索筛选均保留。

## 变更与固定身份

- 第一课题候选台账 v1=1/3、v2=2/3；本修正消耗 **v2 唯一一次诊断修正额度**。不改变背景流的首次本地最短队列、目的地址平局轮转和逐流缓存。MoE 从每包调用 DRILL 改为每 QP 首包调用 DRILL、后续在当前交换机复用相同出口；控制包、未知标签、单下一跳语义不变。理由和反例见[四 seed 诊断](ws25-v2-independent-screen-analysis.md)。
- 固定仿真源码提交 `206888df97e2fd5fd37656d51deda5fb6a4e96c1`，分支 `feature/ws25-first-paper`，已推送个人 fork。相对原 v2 筛选提交 `7aa09f5…`，`src/`、`scratch/`、`run.py` 中仅 `switch-node.{cc,h}` 改动；新诊断计数 `moe_new + moe_reused = moe_packets`。模式仍为 `destspread`（22），原 v2 ID 不复用。
- 旧正确性输入仅作预检：`mixed8`、背景单类 4、MoE 单类 4、tag0 八流和旧五列八流。其 SHA 见[原 v2 预检协议](ws25-v2-destspread-correctness-protocol.md)。OS1/400 Gbps 拓扑 SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`；ns-3 seed=1、DCQCN、PFC=0、IRN=1、9 MiB、`simul_time=0.01`、`netload=10`。所有格独立源码/metadata/raw/资源收据。

## 新 ID 与顺序

| 顺序 | 原 ID 后缀（统一前缀 `20261006-1700`） | 模式/输入 | 诊断 |
| ---: | --- | --- | ---: |
| 1–5 | `00-ws25-v2r1-pre-mixed8`、`01-ws25-v2r1-pre-background4`、`02-ws25-v2r1-pre-moe4`、`03-ws25-v2r1-pre-unclassified8`、`04-ws25-v2r1-pre-legacy5` | destspread / 同名旧输入 | 0 |
| 6–10 | `05–09-ws25-v2r1-pre-{fecmp,drill,conga,letflow,conweave}` | 五旧模式 / mixed8 | 0 |
| 11–12 | `10-ws25-v2r1-pre-unclassified-ecmp`、`11-ws25-v2r1-pre-legacy-ecmp` | ECMP / 对应回退输入 | 0 |
| 13 | `12-ws25-v2r1-pre-mixed8-diag` | destspread / mixed8 | 1 |

准确完整 ID 由[`verify_ws25_v2r1_correctness.py`](../../scripts/verify_ws25_v2r1_correctness.py)的冻结 `CELLS` 给出；若协议和脚本不一致，停止新格并修正控制文件，绝不改已运行 ID。先单独构建、运行、验收首格，然后最多四格一批继续；最后开诊断，要求与首格完整 FCT 原始 SHA 相同。

## 逐格验收及后续门

1. 逐格对源码、输入/拓扑哈希、参数、流身份、字节、全完成率、原始文件唯一性和资源收据；候选类别队列守恒、违规零。MoE 新建/复用计数各非零且两者之和等于 MoE 包数；背景首次/复用各非零。小输入零乱序不证明全量需求安全。
2. tag0/旧五列候选回退格的完整 FCT 指纹分别与同 SHA ECMP 一致；五旧模式 mixed8 完整 FCT 指纹与既有已验收同输入运行一致。诊断格须有 8 条逐 QP 记录，tag1/tag2 各 4，乱序、SACK/CNP、重复发送与超时字段齐全；缺失字段不填零。
3. 任一格身份、正确性、资源或非扰动失败，保留原 ID/raw 并停止扩格。由于 v2 修正额度已用，后续若仍须改仿真源码，须进入第三候选或如实收束负结果，不再次修 v2。
4. 13/13 正确性验收后，才可启动使用全新需求 seed `20262577–80` 的独立探索筛选；它们不与 v1、v2 原筛选、预留 `20262549–52` 校准 pilot 或 `20262553–76` 最终池重合。筛选另有冻结计划，不用小输入、校准或本预检写收益。

## 安全恢复

首格 cap=1；后续最多 cap=4。每组前核其他用户作业、未知 ns-3/worker、锁、load≤20、每 worker 预留 5 GiB 后 MemAvailable≥32 GiB、空盘≥100 GiB，逐格 watcher 先于仿真、进程树 RSS≤32 GiB。SSH/build/fetch 超时先查原 ID metadata/PID/raw 和本地收据，不以超时推断未执行或双重启动；已验收 raw 不覆盖。长时运行期间使用 Luna High 静默监督，终态 raw 回传后实际切 Sol High 分析。
