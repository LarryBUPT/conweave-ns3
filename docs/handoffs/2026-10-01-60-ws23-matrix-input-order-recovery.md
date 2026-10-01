# Handoff 60：WS-23 矩阵输入排序修复与全新 18 格冻结

日期：2026-10-01。执行工作区 `E:\研\毕业论文\workspace\ws23-execution-70bf890`，分支 `feature/ws23-validation-execution`。证据等级：revision 3 为技术预飞行；旧矩阵仅三个背景格成功，混合格失败；新矩阵已通过一格输入解析门槛，双侧效果数据尚未完成。

## 1. 本对话目标

接续 WS-23，分析 revision 3 后首批隔离矩阵的失败，保留原始证据，修复可定位的输入问题，并冻结不混用旧 SHA 的新矩阵入口。用户要求持续完成原必做验证；本 Handoff 只是阶段交接，WS-23 不闭环。

## 2. 已确认的项目事实

- `docs/REMOTE_EXPERIMENT_WORKFLOW.md` 要求失败 ID/raw 保留、修复后用新固定 SHA/独立 ID 验证。源码 `scratch/network-load-balance.cc::ReadFlowInput` 要求流开始时间非递减。
- revision 3 六格在 `b3d8d30826dd4550f5667d4cab2a3b4004c3cf22` 下通过：每格 4/4、诊断关/开 FCT 字节相同、资源收据有效；仅证明旧混合输入的预飞行门槛。
- 原矩阵 `20261001-180000/180001/180002-ws23-s2301-bg-*` 均 1/1，旧输入哈希 `c3ea8ff…`，峰值 RSS 约 204 MiB；它们只能作旧 SHA 历史证据。`20261001-180003-ws23-s2301-mix-fecmp` 的 `metadata.json` 为 `FAILED`，FCT 为空，`raw/672934038/config.log` 报 `FLOW_INPUT_ERROR line 3`，其资源收据峰值约 203.871 MiB。失败格原输入第 2、3 行到达时间分别为 2.006091550、2.006083307 秒。`180004/180005` 已构建未运行，其余旧 ID 未创建。
- 失败格在配置快照前退出，原 `results/<ID>/config/` 不含输入/拓扑。远端独立源码副本的两份法证下载已保存在该 ID 的 `forensic/`，未覆盖 raw；该输入、拓扑哈希分别为 `f0566d10d33ab63bf5ba8b123bc09136d86fb8bf2f3331104d03f1459575283d` 和 `dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad`。

## 3. 已完成工作

把 `scripts/make_ws23_isolation_demands.py` 的 trace 输出改为按原 `arrival_offset_ns` 排序，manifest 继续按背景优先记录语义流。重新生成三份混合输入和 manifest；三份背景输入未变。新增 `scripts/verify_ws23_demand_reorder.py`，从旧 Git 提交逐条比对六列记录多重集合、到达时间、唯一性、哈希及 manifest 除哈希以外的内容，收据为 `docs/research/evidence/ws23-isolation-reorder-audit.json`。三份混合新 SHA 依次为 `44c511ec97322bbb6ff0755ea20cc5782ce213f16f8e52099dff90852c23d7af`、`3940065ae39880cf418b46de8b3155d7329a3b7d52d85eeca88a007d0bf29fbd`、`123dadf0a18165cf0e023c4095b8bedee55ebb9e76ac8bb5615e3c9baa080750`。新 manifest SHA 为 `5d7cb60ab271bc60c940c316b0323ab3d98a109dafb0ca9c239639cbe247a464`。

`scripts/verify_ws23_isolation_pilot.py` 新增矩阵 `--revision 2` 编号，保留旧 `--revision 1` 映射；读取结果前独立检查流数、六列、manifest 对应和到达时间排序。生成器 `--check`、排序审计、Python 编译和 18 个唯一新 ID 的本地生成检查已通过。2026-10-01 本地 `results/` 与远端 `results/`、`runs/` 的新 ID 首次检查均为空；运行前还须复查。

## 4. 已形成的设计决策

决定只改输入文件的行序，因为源码解析器明确要求排序，逐条比对证明需求内容可保持不变。没有调整候选评分、三组需求、原双侧方向、竞争流代价或资源停止线。旧背景三格即使输入字节不变，也不与新 SHA 的九个背景格混用；所有 18 格重新从同一新固定 SHA 运行。先用新排序混合输入的 ECMP 格做解析门槛，通过后才扩展其余 17 格。

## 5. 当前状态

WS-23 **ACTIVE**。排序修复固定源码 SHA `3db2685a3540895bf49e25302bd00465bc0921e2`。解析门槛格 `20261001-200003-ws23-s2301-mix-fecmp` 已独立构建、运行并通过：`SUCCEEDED`，4/4 流完成，FCT SHA-256 `d4ac5917d3d8bbd10f7ac4a1d963fc1a60e60aa036ad7e953acc7471861be301`，输入 SHA `44c511ec97322bbb6ff0755ea20cc5782ce213f16f8e52099dff90852c23d7af`，拓扑 SHA `dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad`，峰值进程树 RSS 203.844 MiB，最大采样 load1m 1.17；[解析门槛收据](../research/evidence/ws23-isolation-parse-gate.json)逐项核验通过。矩阵 1/18，其余 17 格尚未运行，没有隔离收益结论。

## 6. 未解决问题

新 SHA 对新排序输入的端到端解析、18 格逐格完成与资源收据、同输入双侧效果、竞争流代价、原始数据独立复核均未完成。三组仍属同一小拓扑的合成需求；没有真实部署身份或可信业务 SLO，实际适用范围只能据此标明证据缺口。

## 7. 后续推荐动作

解析门槛已经通过。继续现场复查 worker、作业、资源和剩余 17 个 ID 空闲；每格独立构建并在观察器 READY 后运行，仿真并发 1。构建采用每格 `-j2`、最多四格一批（8 个编译任务），起始 load1m ≤10、可用内存 ≥32 GiB、磁盘 ≥100 GiB，运行中越过停止线则停止新增格。所有格按 revision 2 验收并保留 raw；全部终态回传后实际切 GPT-6 Sol High，以 `--revision 2 --source-sha 3db2685a3540895bf49e25302bd00465bc0921e2` 重算原始双侧结果并作独立复核，再逐项核对必做清单决定闭环。

## 8. 与其他工作流的关系

旧 WS-14/19 等结论及其停止规则不因本修复改变。WS-24 的合成多 NIC 结果与本隔离实验不是同一输入或同一主张。共享远程入口和资源仍须与 Integration 协调；不触及两个只读参考仓库。

## 9. CONTEXT SNAPSHOT

WS-23 revision 3 六格预飞行通过，旧 18 格在第四格因混合 trace 时间倒序失败并停止。已保留旧 ID/raw，修复只排序三份混合 trace，六列流记录与 manifest 语义内容不变；排序审计收据可从旧 Git 提交重算。新完整 SHA `3db2685a3540895bf49e25302bd00465bc0921e2` 的新混合 ECMP 解析门槛格通过，矩阵 1/18；剩余 17 格按 `--revision 2` 编号运行。WS-23 ACTIVE，解析门槛与 Handoff 均不能代替双侧效果验证。
