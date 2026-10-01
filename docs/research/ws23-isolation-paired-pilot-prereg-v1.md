# WS-23 隔离候选同输入双侧探索协议 v1

冻结日期：2026-10-01。v1 候选源码、生成器和验收脚本的固定提交为 `e263579aeaf970bb64a27d3c41c0ab0ba850022b`。本节保留事前冻结的合成需求、候选机制、对照和判据。后续预飞行及矩阵失败、修复与新 ID 见文末执行修订；原双侧判据不变。个人 fork 同分支同步、远端 ID 空闲及 worker/资源现场收据仍须在启动前核对。

## 要检验的主张

四格原始复核已确认一个合成场景的共享出口影响，但没有测试隔离。候选沿用源码中 `guardhash`（模式 14，`lambda=1, tau=0`）：tag=1 背景流和控制包走流 ECMP；tag=2 竞争流在两个固定候选出口间，按总队列字节加背景类别队列字节评分。机制消融 `shortq2`（模式 13）使用相同双候选、去掉背景类别项；普通 `fecmp`（模式 0）提供绝对对照。三个模式必须在**同一源码 SHA、同一份需求输入、同一 ns-3 seed** 下配对。当前源码仅增加 `class_nonzero`、`class_changed_choice` 两个路由计数，用来证明类别项在动态决策中出现并实际改变选择；不改变路由评分。WS-14 在另一组全量场景已按旧停止规则负向结束，本小样无论结果如何均不改写它。

## 独立需求与矩阵

生成器 `scripts/make_ws23_isolation_demands.py` 使用三个独立 Python 随机种子 2301/2302/2303，事前固定各组源/目的映射和到达时间。每组四个源主机 0–3 到四个目的主机 24–27，均跨源 ToR 32 至目的 ToR 38；一条 tag=1 背景流 8 MiB，三条 tag=2 竞争流各 4 MiB，总量 20 MiB。到达时间在 2.006 s 后 0–100 µs 内；背景单独输入是混合输入的相同首流。场景仍是**明示的合成需求**，三组虽改变映射与到达，却共享同一小拓扑和负载家族，不能当作真实部署样本。

六份输入及每份的字节哈希、流身份、生成种子在[清单](evidence/ws23-isolation-demand-manifest.json)。输入在 Git 中按原字节保存；执行前同时核对 Git blob 和远端 `config/traffic_trace.txt` 快照的 SHA-256，不能用 Windows 工作树哈希代替远端快照。三个 seed **全部报告**，不因是否碰巧共用出口、方向好坏或动态计数大小筛选。旧四格是机制发现输入，不混入三组独立需求统计。

每个 seed 分别运行背景单独/混合 × `fecmp`/`shortq2`/`guardhash`，共 18 个独立 ID；ID 由 `scripts/verify_ws23_isolation_pilot.py` 中 `experiment_id` 固定。共同配置：`fat_k4_100G_OS2` 拓扑、DCQCN、100G、9 MiB buffer、PFC=0、IRN=1、ns-3 seed=1、`simul_time=0.01`、`netload=10`、`--factorial-pilot --factorial-drop-diag`、诊断关闭、每格 optimized `-j2`、仿真并发 1。先用已复核的旧四格输入做新 SHA 的诊断开/关与三模式正确性最小门槛；通过后才启动 18 格，不复用旧 SHA 的 FCT 当作新 SHA 回归。

## 逐格验收、双侧判据与停止

新 SHA 的最小预飞行为旧混合输入上三模式各跑诊断关/开一对，共六格。预留 ID 为 `20261001-174000-ws23-pilot-fecmp-off`、`174001-...-fecmp-on`、`174002/174003-...-shortq2-off/on`、`174004/174005-...-guardhash-off/on`；完整字符串由 `scripts/verify_ws23_isolation_preflight.py` 的 `pilot_id` 固定。六格同输入、同配置（仅模式与诊断开关不同），要求 4/4 全完成、每对 FCT 原始字节哈希相同、ECMP 与旧同输入 FCT 哈希相同、新模式双候选和评分计数为正、诊断开启时 `unpaired=0`、队列守恒及资源门槛通过。运行 `scripts/verify_ws23_isolation_preflight.py --source-sha <冻结完整 SHA>` 验收；失败停在六格，不进入 18 格。

24 个预留 ID（六格预飞行和 18 格需求对照） 在本地冻结检查时均未占用；远端仍须在运行前现场查重。ID 从 `20261001-180000-ws23-s2301-bg-fecmp` 到 `20261001-180017-ws23-s2303-mix-guardhash`，完整映射以固定提交中的验收脚本为准。

逐格先核对源码/输入/拓扑哈希、参数、完整流身份及 payload、1/1 或 4/4 完成、无 PFC/准入丢包/队列拒绝/超时，两个新模式 `WS09_QUEUE_CHECK violations=0`，运行中正 RSS 资源收据与停止线。背景单独三模式 FCT 字节哈希必须相同，因为此时没有 tag=2 竞争流；不相同先定位回归。任何错误保留该 ID 和 raw，停止新增格；修复后另用新 SHA/ID，不能覆盖旧记录。

对每个 seed 都计算：背景流的“混合 FCT − 本模式背景单独 FCT”，三条竞争流的逐流 FCT 与最大 FCT；列出相对 ECMP 和 shortq2 的正负差。`guardhash` 的 `two_candidates`、`scored`、`class_nonzero`、`class_changed_choice` 都须为正，才称这一组需求实际触发类别决策。类别项可能有改善、无变化或损害，均如实保留。

**探索性正向条件**预先设为：三个 seed 各自都实际触发类别决策；各自背景干扰量严格低于 ECMP 和 shortq2；各自竞争流最大 FCT 不高于这两个对照。任一组不满足即报告该探索性条件未通过，逐组展示损害与收益，不按结果调权、删 seed 或转称普遍有效。三组正向也只支持这个合成负载家族的探索性结果，不是统计确认、真实业务安全阈值或正式性能收益。没有可信 SLO，不能据此创造通用百分比安全线。

资源规则沿用 WS-23：执行前确认共享 worker 归属、无他人作业或在途任务、load1m ≤10、可用内存 ≥32 GiB、磁盘 ≥100 GiB；运行中他人作业、load1m >20、进程树 RSS >8 GiB、可用内存 <16 GiB、磁盘 <100 GiB、日志 >50 MiB、构建 >20 分钟、单格仿真 >10 分钟或收据缺失时停止新格。每格先 `READY`，终态读取状态、正 RSS 收据并取回 raw。进入后台实验时实际切至 Luna High，约半小时精简监督；全部终态与 raw 回传后实际切回 Sol High 独立分析。共享入口目前由 Integration 协调，本协议形成不表示已获该入口。

## 验证出口

`scripts/verify_ws23_isolation_pilot.py --source-sha <冻结完整 SHA>` 从 18 份原始结果产生逐 seed 机器摘要；运行前还需在执行 Handoff 固定 SHA、核对全部 ID 空闲、确认脚本与生成器的版本，并完成新 SHA 的 optimized 构建、单测和旧输入诊断等价最小门槛。若结果为负，保留完整双侧数据并据此作负结论；WS-23 的“验证隔离候选”项在完成这轮预设验证与独立复核后才能判断是否闭环。真实业务适用范围始终另列证据缺口。

## v2 执行修订：观测覆盖修复后重新预飞行

2026-10-01，v1 前四格在固定源码 `e263579aeaf970bb64a27d3c41c0ab0ba850022b` 下完成并回传 raw。ECMP 诊断关/开配对的 FCT 哈希相同，且与旧输入锚点一致；`shortq2` 的关/开配对 FCT 也相同，但开启格 `20261001-174003-ws23-pilot-shortq2-on` 没有预设的 `WS23_CROSSCLASS_HOP` 与 `WS23_CROSSCLASS_INFLIGHT` 记录。v1 验收器按原判据报 `diagnostic pairing` 失败。源码原因是跨类观测开关仅允许 ECMP 模式。四份已运行 raw 保留，v1 后两格和 18 格均未启动；详见[Handoff 58](../handoffs/2026-10-01-58-ws23-isolation-diagnostic-coverage.md)。

修复候选固定源码与 v2 验收入口为 `eff40eaac291a86c1d42afa6042ab1d583c8a373`，已推送个人 fork 同名分支。修复只让显式诊断开关在 32 主机小拓扑的 ECMP、`shortq2`、`guardhash` 三模式记录同一组跨类观测；不改路由评分、候选路径、输入或双侧通过门槛。`scripts/verify_ws23_isolation_preflight.py --revision 2 --source-sha eff40eaac291a86c1d42afa6042ab1d583c8a373` 使用以下六个全新 ID；不覆盖 v1。原脚本默认 `--revision 1`，仍可复现 v1 失败。

| 模式 | 诊断关闭 | 诊断开启 |
| --- | --- | --- |
| `fecmp` | `20261001-151500-ws23-pilot2-fecmp-off` | `20261001-151501-ws23-pilot2-fecmp-on` |
| `shortq2` | `20261001-151502-ws23-pilot2-shortq2-off` | `20261001-151503-ws23-pilot2-shortq2-on` |
| `guardhash` | `20261001-151504-ws23-pilot2-guardhash-off` | `20261001-151505-ws23-pilot2-guardhash-on` |

六格仍使用同一旧混合输入 `config/ws23_crossclass_bg_plus_3x4MiB.txt`，Git 字节 SHA-256 `379e0c87cb0c26690d438287468dbc9159054f82445e6be46d0324165d639863`；拓扑 `config/fat_k4_100G_OS2.txt` 的 SHA-256 为 `dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad`。ns-3 seed=1，其余配置、逐格验收、配对哈希、路由与队列守恒、资源停止线和六格通过后才开放 18 格的规则，均沿用上文。v2 六个 ID 在本地与远端结果/运行目录的初次检查中未占用；执行前还要现场复查。仿真源码的远程优化构建、单测和预飞行仍以实际收据为准。

## v3 执行修订：纠正预飞行启动参数并重新冻结编号

2026-10-01，v2 已运行并回传 ECMP 两格及 `shortq2` 两格。ECMP 两格启用了 `--factorial-pilot --factorial-drop-diag`，验收元数据记录 4/4；`shortq2` 两格启动时漏传这两个冻结参数，虽然仿真状态均为 `SUCCEEDED` 且 FCT 输出非空，但没有 `input_flows/completed_flows/unfinished_flows` 元数据，不能满足预飞行验收。`shortq2` 两格及 raw 保留并按失败编号处理；`guardhash` 两格未启动。revision 2 验收在 `shortq2` 检查处因完成数证据缺失而失败。未改变 C++ 选路、输入、拓扑或通过判据。

为遵守失败 ID 不复用与固定 SHA 规则，执行入口加入 revision 3，新固定提交包含验收编号映射与本次流程记录，不修改仿真行为或既有验收条件。revision 3 使用六个全新编号：`20261001-190100-ws23-pilot3-fecmp-off`、`190101-...-fecmp-on`、`190102/190103-...-shortq2-off/on`、`190104/190105-...-guardhash-off/on`。运行前须再次确认本地、远端 `results/` 与 `runs/` 均无这些编号。

revision 3 六格继续使用 v2 所列同一输入、拓扑、seed、源码树（C++ 行为未变）和全部验收判据。每一格必须显式带 `--factorial-pilot --factorial-drop-diag`；仅 `--ws13-diag` 随配对为 0/1，模式按冻结表映射。全部六格均以各自独立源码目录 `optimized -j2` 构建，启动前资源观察器须 `READY`。验证命令为 `python scripts/verify_ws23_isolation_preflight.py --revision 3 --source-sha <revision-3 完整 SHA>`。任一格失败仍停止扩展；六格全部通过后才开放原预注册的 18 格。

## 矩阵第二版：修正输入行序并重新冻结完整 18 格

2026-10-01，revision 3 六格在固定源码 `b3d8d30826dd4550f5667d4cab2a3b4004c3cf22` 全部通过：每格 4/4，诊断关/开 FCT 配对相同，资源收据有效。这只证明旧混合输入的正确性门槛。随后的原矩阵在第四格 `20261001-180003-ws23-s2301-mix-fecmp` 失败后停止。该格 `metadata.json` 为 `FAILED`，FCT 为空，`raw/672934038/config.log` 报 `FLOW_INPUT_ERROR line 3`。源码 `scratch/network-load-balance.cc::ReadFlowInput` 要求到达时间不递减，旧混合文件先写背景流、后写竞争流，三组均存在倒序。前三个 `s2301-bg` 格均 1/1 完成且 FCT 哈希相同，但属于旧固定 SHA，不能填充新矩阵。两个后续旧 ID 已构建未运行，其余旧矩阵编号未创建；全部已生成的 ID/raw 保留。

生成器现在只在写六列 trace 时按原有到达偏移排序；背景优先的 manifest 语义顺序、三组流身份、tag、字节量、到达时间和全部双侧判据不变。[逐条等价收据](evidence/ws23-isolation-reorder-audit.json)以旧 Git 提交的输入为基准，确认三份背景文件逐字节相同，三份混合文件仅行序变化，六份均无重复到达时间且时间不递减。新的三份混合文件 SHA-256 分别为 seed 2301 `44c511ec97322bbb6ff0755ea20cc5782ce213f16f8e52099dff90852c23d7af`、2302 `3940065ae39880cf418b46de8b3155d7329a3b7d52d85eeca88a007d0bf29fbd`、2303 `123dadf0a18165cf0e023c4095b8bedee55ebb9e76ac8bb5615e3c9baa080750`；新 manifest SHA-256 `5d7cb60ab271bc60c940c316b0323ab3d98a109dafb0ca9c239639cbe247a464`。

新矩阵仍为三个 seed × 背景单独/混合 × 三模式的完整 18 格，使用 `scripts/verify_ws23_isolation_pilot.py --revision 2 --source-sha <本次冻结完整 SHA>` 验收；`--revision 1` 保留旧编号入口。新 ID 从 `20261001-200000-ws23-s2301-bg-fecmp` 连续至 `20261001-200017-ws23-s2303-mix-guardhash`，按 seed、场景、模式顺序在验收器中确定。2026-10-01 本地 `results/` 与远端 `results/`、`runs/` 首次检查这 18 个 ID 均空闲，启动前仍须现场复查。所有 9 个背景格和 9 个混合格都使用同一个新完整提交 SHA 重跑，不能借用旧背景结果。

**新增启动门槛：**先运行生成器 `--check` 和逐条等价审计，并由验收器在读取任一结果前检查六列 trace 的流数、manifest 中的全部流身份及非递减、无重复的到达时间。新 SHA 仍需一格混合 ECMP 解析正确性预飞行：同一新 SHA、新排序混合输入、全部冻结运行参数，要求 4/4 完成、无输入解析错误、输入/拓扑快照哈希匹配、正 RSS 和资源停止线通过；此格占新矩阵的 `200003` 编号，成功后才扩展到其余 17 格。原 revision 3 六格是同一 C++ 模拟器代码树的历史预飞行，不能替代新输入解析门槛。运行前复查共享入口、worker、他人作业与资源；仿真阶段实际切 Luna High，失败立即停新格，终态 raw 回传后实际切 Sol High 独立逐格和双侧分析。WS-23 继续 ACTIVE，未得到隔离效果结论。
