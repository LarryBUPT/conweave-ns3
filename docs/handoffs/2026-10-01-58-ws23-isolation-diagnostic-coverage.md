# Handoff 58：WS-23 预飞行观测覆盖失败与 v2 本地冻结

日期：2026-10-01。执行任务 `01a0f15f-58c7-7532-84bd-9acaaaa14525`；分支 `feature/ws23-validation-execution`，工作区 `E:\研\毕业论文\workspace\ws23-execution-70bf890`。证据等级：v1 四格为固定合成输入的技术预飞行；v2 为本地修复准备，尚无远端验证或候选效果结论。

## 1. 本对话目标

继续 WS-23 隔离候选验证：先用同一旧混合输入核验 ECMP、`shortq2`、`guardhash` 的诊断开关、完整流和资源，再决定能否进入三组独立合成需求的 18 格双侧对照。原清单与双侧判据不变。v1 在第四格发现观测缺口，本阶段定位、修正并固定全新预飞行入口。

## 2. 已确认的项目事实

- v1 源码固定为 `e263579aeaf970bb64a27d3c41c0ab0ba850022b`；输入快照 SHA-256 为 `379e0c87cb0c26690d438287468dbc9159054f82445e6be46d0324165d639863`，拓扑为 `dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad`，ns-3 seed=1。远端 worker 当时与本地 WS-23 脚本 SHA-256 同为 `9e1b4e144d5584e8999d2c560bf4577b249ca73421d9aac6c53e5a96a798766e`。
- v1 前四个 ID `20261001-174000/174001-ws23-pilot-fecmp-off/on`、`20261001-174002/174003-ws23-pilot-shortq2-off/on` 均为 `SUCCEEDED`、4/4 完成、正 RSS 收据有效，峰值约 203.9–204.2 MiB。ECMP pair 原始 FCT SHA-256 同为 `4c415e30d3a25529f12b7c9af54a2c29f000ee7b0412c12cce494cb4ceb4dfdd`，与旧同输入锚点一致；`shortq2` pair 同为 `2a8e209b50c2e7fa117cda2fe65e385ef60e2ecdda6771a557bb9bcc9d007d9a`。
- ECMP 开诊断格有 20 条 `WS23_CROSSCLASS_HOP` 与一条 `unpaired=0` 的 `WS23_CROSSCLASS_INFLIGHT`；`shortq2` 开诊断格两类记录均为零。`python scripts/verify_ws23_isolation_preflight.py --source-sha e263579aeaf970bb64a27d3c41c0ab0ba850022b` 在该格按原判据报 `diagnostic pairing` 失败。`run.py` 将 `shortq2`、`guardhash` 分别映射为模式 13、14；旧 `Ws23CrossClassDiagnosticEnabled()` 只接受模式 0。四格原始结果在本地 `results/<ID>/` 和远端同 ID 目录，未覆盖或删除。
- `20261001-174004/174005-ws23-pilot-guardhash-off/on` 没有启动，三组需求的 18 格也没有构建或运行。此前四格只回答预飞行正确性，不能用于新方案效果判断。

## 3. 已完成工作

1. 现场核对个人 fork、24 个 v1 预留 ID、共享 worker、无其他用户作业、资源和旧 Mercurial 进程归属；按既有授权保留旧进程。部署本分支 worker、同步个人 fork，并对前四格分别从固定源码作独立 `optimized -j2` 构建。第一格旁的独立测试副本完成 `devices-point-to-point` 单测，最终日志为 `PASS`；测试 helper 恢复前后 SHA 相同，仿真源码未改。
2. 四格均先取得资源观察器 `READY` 再运行，终态收正 RSS 收据、取回 raw。ECMP pair 及 `shortq2` 关闭格的逐格检查通过；第四格的诊断记录缺失触发原预飞行验收失败，随即停止新增格。失败格本身的 FCT 与同模式关闭格一致，不能代替缺失的观测。
3. 本地仅将小拓扑跨类观测开关扩展到模式 0、13、14，未改 GuardHash/shortq2 选路评分；验收脚本保留 v1 默认编号，增加 `--revision 2` 指向六个新 ID。Python 语法、v1 失败复现、v2 ID 生成、Git 输入字节哈希与 `git diff --check` 已检查。代码与验收入口已提交并推送个人 fork，固定 SHA `eff40eaac291a86c1d42afa6042ab1d583c8a373`。新 C++ 尚未远端构建或运行。

## 4. 已形成的设计决策

保留 v1 四格 raw 与失败判据，不重用任何已运行 ID。用新的源码 SHA 和六个新 ID 重跑完整预飞行；不能沿用旧 ECMP pair 充当新 SHA 的回归。选择只扩大显式诊断开关的模式范围，因为源码检查已定位到该限制，且改路由评分或删掉观测验收都不能修复证据缺口。双侧效果、竞争流代价和全部三组需求仍按[原协议及 v2 修订](../research/ws23-isolation-paired-pilot-prereg-v1.md)报告。

## 5. 当前状态

修复候选源码 `eff40eaac291a86c1d42afa6042ab1d583c8a373` 已推送个人 fork；文档提交后分支 HEAD 将继续移动，仿真仍须明确选用该源码 SHA。v2 六个 ID 在本地和远端结果/运行目录的初次检查中均未占用：`20261001-151500/151501-ws23-pilot2-fecmp-off/on`、`20261001-151502/151503-ws23-pilot2-shortq2-off/on`、`20261001-151504/151505-ws23-pilot2-guardhash-off/on`。**v2 0/6，18 格 0/18；WS-23 ACTIVE。**

## 6. 未解决问题

新 SHA 的优化构建、隔离单测、六格观测与配对等价、18 格同输入双侧结果、原始数据独立复核和真实业务适用范围均未完成。三组需求属于同一小拓扑下的独立合成变化，没有真实 host/NIC/job 身份或可核验业务 SLO。v1 失败没有证明隔离效果为正或负。

## 7. 后续推荐动作

在监督任务实际切至 GPT-6 Luna High 后，重新确认共享入口、worker SHA、无其他作业、固定源码祖先、六个 ID 与 18 个矩阵 ID 空闲。每格从 `eff40ea…` 建独立源码和 `optimized -j2` 构建；首格另用隔离测试副本重新运行 `devices-point-to-point` 单测，不沿用 v1 收据。运行前固定输入 `379e0c87…`、拓扑 `dcca23ca…`、seed=1，PFC=0、IRN=1、100G、9 MiB buffer、`simul_time=0.01`、`netload=10`、并发 1。每格观察器先 `READY`，终态核对正 RSS、取回 raw；运行 `scripts/verify_ws23_isolation_preflight.py --revision 2 --source-sha eff40eaac291a86c1d42afa6042ab1d583c8a373`。六格全部满足 4/4 完成、诊断开关配对 FCT 哈希一致、ECMP 旧锚点相同、诊断 `unpaired=0`、新模式双候选/评分计数为正、队列守恒及资源门槛，才开放 18 格。

准入线仍为无人作业、load1m ≤10、可用内存 ≥32 GiB、磁盘 ≥100 GiB；出现他人作业、load1m >20、单格进程树 RSS >8 GiB、内存 <16 GiB、磁盘 <100 GiB、日志 >50 MiB、构建 >20 分钟、单格 >10 分钟或收据缺失时停新格并保留 raw。18 格完成后实际切至 GPT-6 Sol High，从全部原始数据独立核对双侧结果；结论与源码、输入和每格 ID 逐项对应后才能检查任务闭环。

## 8. 与其他工作流的关系

远端 worker 与 WS-24 共享；本阶段不再部署、构建或启动新格，入口由 Integration 协调后交给监督任务。WS-24 的单测缺口及既有 14 格结果不因本修复改变。旧 WS-14 负向结论、WS-23 恢复正确性和四格共享出口发现也不由本技术失败改判。

## 9. CONTEXT SNAPSHOT

WS-23 v1 四格固定合成预飞行在 `shortq2` 开诊断格被原验收器拒收：仿真 4/4 完成且 FCT 与关闭格相同，但跨类观测为零；源码只让 ECMP 开启该观测。四格 raw 均保留，原后两格和 18 格未启动。修复源码/验收入口 `eff40eaac291a86c1d42afa6042ab1d583c8a373` 已推送，六个全新 v2 ID 与不变的输入/拓扑/seed/门槛见[协议修订](../research/ws23-isolation-paired-pilot-prereg-v1.md)。新源码未编译或运行；先实际切 Luna High，再现场复查并跑完整六格，全部通过才进入 18 格。终态 raw 后切 Sol High 独立分析。WS-23 ACTIVE。
