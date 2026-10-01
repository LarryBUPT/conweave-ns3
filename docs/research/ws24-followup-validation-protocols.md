# WS-24 后续本地冻结协议

日期：2026-10-01；本地冻结一致性复核：2026-10-01。范围：旧输入四 baseline 回归、320-host 目标拓扑正确性、动态 CNP 正确性、固定逻辑需求的 rail × placement 四臂验证。协议、输入与观测源码已冻结；**此共同 SHA 尚未远端构建或运行 14 格仿真**。WS-24 仍为 ACTIVE。

## 公共边界与证据等级

- 导入 OS1 拓扑来源可追至只读参考仓库 maplerime/conweave-ns3@470c58026ec3933eabb6667bf3124b6b9bd401be 的合成生成器，逐边结构相符；它不是物理服务器/NIC 或真实 job placement 证据。320-host、NIC、流与 placement 都明确是合成 fixture。
- 四类后续仿真由 Integration 在共享入口空闲、WS-23 无在途远程 build/sim 或 worker 切换时协调。WS-23 正确性验证优先级仍保留；五格全部成功不是独立 WS-24 回归的机械前置条件。启动前须重新核对服务器用户/作业、活动 build/sim、worker、资源与全部 ID。监督阶段须实际切 Luna High；终态 raw 回传后实际切回 Sol High。2026-10-01 续作只读审计确认当时无登录用户/运行中结果、资源达标、14 个 ID 均未占用；检测到 worker SHA 与固定提交版本不同后，已部署并核对 worker SHA `0be12e21ce37655f52a19803824f2b8d24a9a2c84ba0cd58124eb6fb96de62eb`。源码缓存已通过 workspace Git bundle 同步到分支提交 `dc6477e5f469434f42c2b888ac0e18c50341b422`，其中包含共同实验 SHA `b1184d6a7bd38577b235b7f119f920973308774f`。此后尚未 build/run；本轮监督模型未实际切到 Luna High 前不启动实验。
- **A/B/C/D 共同仿真源码 SHA 固定为 `b1184d6a7bd38577b235b7f119f920973308774f`**，分支 `feature/ws24-multinic-validation` 已推送至 LarryBUPT 个人 origin 且远端同名分支曾核对为该 SHA。2026-10-01 从此提交的 Git blob 逐一核对 11 份合成输入、manifest、旧五/六列输入与 OS2 拓扑、CNP 四类观测事件及验收器；11/11 文件哈希等于 manifest，manifest SHA-256 为 `55997be83ecf7e43accc2f6bc546b97185943657cdc64da0d5c89ef91a52b127`。此前 v2 最小格仍归属 `824e3fa0c4c06dd9894474a81e729931d59a3108`，不能并入新批次。后续文档提交只移动分支 HEAD；若无源码或输入改动，14 格仍显式指定 `b1184d6…` 构建。新实验 ID 启动前必须检查 `/home/fnl/lzy/runs/`、`results/` 未占用；下列 ID 仍只是本地预留。
- 默认 seed=1。simul-time=0.01、netload=10 是现有 runner 的兼容参数；显式 trace 决定实际流量。每个 raw 都须保留 metadata、配置快照、trace/NIC/topology 和资源收据。失败 ID/raw 不覆盖、不复用。
- 本文的 SUCCEEDED 只是 runner 状态；每项还需逐流身份、输入/完成/字节守恒和原始日志证据。空日志/计数不等于零事件或分支通过。任何错误先定位，修复后固定新 SHA 并使用新 ID。

固定提交中的输入对应关系：A 的 8 个 ID 使用 `ws06_legacy_baseline.txt` 或 `ws06_small_six_column.txt`（各四模式）及 OS2 拓扑，其完整 Git 字节哈希见 A 表；B 使用 manifest 中目标拓扑、目标 NIC 与 `ws24_synthetic_fixed_multi_flows.txt`；C 使用相同目标拓扑/NIC 与 `ws24_synthetic_cnp_incast_flows.txt`；D 四个 ID 分别使用相同目标拓扑/NIC 与四份 `fixed/variable × single/multi` flow 文件，其完整哈希见 D 表。manifest 的其余四份 `2host` 文件属于已完成的 v2 最小格/拒错输入，仍随固定提交保留，不冒充 14 格的新运行。协议列出的 14 个预留 ID 与 `scripts/verify_ws24_matrix.py::DEFAULT_IDS` 已逐一核对一致。

## A. 旧五列、六列输入的四 baseline 回归

**目的：**在开启 WS-24 代码的源码上，确认旧输入入口、旧 OS2 1000 ns 拓扑约束和四种 LB 原路径均保持可运行；五列缺省 tag=0，六列显式 tag 仍可到达路由入口但不改变旧 baseline 的 tag 无关语义。

| 输入 | 精确版本库字节 SHA-256 | 拓扑 | 预期输入 |
| --- | --- | --- | --- |
| config/ws06_legacy_baseline.txt | abebc3170428aa22ebb13b15246243b806cb4f749bf4c9e6a80fb0a4a694a3cf（Linux/Git blob LF；Windows 工作树 CRLF 哈希 2be597a61bb279a6fea49ef6be2095f672dcbdc9499124d6a00e6b4ecc995f57） | leaf_spine_128_100G_OS2，0dddc4f3ae673139b895ff2f875befe82b234cc48e325bd8a164d9cddedc12e2 | 19,388 行，五列，缺省 tag=0 |
| config/ws06_small_six_column.txt | be78b4cb5afbcceb51f42ee10594c32b8a4322bc3e069ed0413554e41ba75748（Linux/Git blob LF；Windows 工作树 CRLF 哈希 fbaff41e14dea900f40a72ee6d6906a3e199e562cacb4345eb240c6376499032） | 同上 | 4 行，六列，tag=2 两条、tag=1 两条 |

共同运行参数：--bw 100 --buffer 9 --pfc 1 --irn 0 --simul-time 0.01 --netload 10，拓扑固定 OS2；DCQCN 为当前 run.py 默认，seed=1 为 worker/source 固定值。远程控制器不接受 --cc 或 --seed 覆盖。算法依次 fecmp/conga/letflow/conweave（LB_MODE=0/3/6/9）。8 个本地预留 ID：

- 20261002-100000-ws24-legacy5-fecmp
- 20261002-100100-ws24-legacy5-conga
- 20261002-100200-ws24-legacy5-letflow
- 20261002-100300-ws24-legacy5-conweave
- 20261002-101000-ws24-legacy6-fecmp
- 20261002-101100-ws24-legacy6-conga
- 20261002-101200-ws24-legacy6-letflow
- 20261002-101300-ws24-legacy6-conweave

**逐格验收：**metadata/source SHA 和输入快照匹配；OS2 的老链路 1000 ns 断言通过；FCT 行数恰为输入数（五列 19,388，六列 4）；五列日志显示 19,388 个 tag=0，六列输入与路由计数能分别核对 tag=1/2 为 2/2 且缺失计数为 0；FCT 与 uplink 可解析非空，ConWeave 的 VOQ 输出可解析；四种 LB_MODE 确认对应。六列小格若 flowlet、reroute 等动态计数为 0，只报告未触发，不能作为该动态机制已覆盖证据。

历史锚点：WS-06 Handoff 06 的 `887f55ef91b0b02455bad1cce5be864d1f4fd02c` 已完成四次五列回归。2026-10-01 从个人 fork 的 `results/20260924-211000-ws06-legacy-fecmp`、`20260924-211500-ws06-legacy-conga`、`20260924-212200-ws06-legacy-letflow`、`20260924-212900-ws06-legacy-conweave` 四份历史 raw **只读重算**：metadata 均 `SUCCEEDED` 且同 SHA、trace/拓扑快照哈希与 metadata/上表一致、各 FCT 恰 19,388 行；完整 FCT SHA-256 分别存于[参考哈希 JSON](evidence/ws24-legacy-reference-fct-sha.json)。历史 raw 位于个人 fork checkout 而非本 WS-24 checkout，后续矩阵入口用 JSON 强制逐字节比较。历史成功只作输入兼容锚点，不代替新共同 SHA 上的回归，也不作性能比较。

## B. 320-host × 4 NIC 目标拓扑正确性

固定输入：config/ws24_synthetic_320host_4nic_topology.txt、config/ws24_synthetic_320host_4nic_nics.txt、config/ws24_synthetic_fixed_multi_flows.txt。config/ws24_synthetic_manifest.json SHA-256 为 55997be83ecf7e43accc2f6bc546b97185943657cdc64da0d5c89ef91a52b127；逐文件哈希以该 manifest 为准，来源 OS1 topology SHA 为 74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba。目标图含 320 个合成 host Node、1,280 个 NIC、576 switches、3,840 links；固定流文件 10 条/2,408,448 B，覆盖 rail 0–3。

本地预留 ID：20261002-110000-ws24-target-320host-correctness。参数：fecmp、WS-24 multi-NIC、--bw 400 --buffer 9 --pfc 0 --irn 1 --simul-time 0.01 --netload 10 --seed 1，固定上述拓扑/NIC/flow 文件。

**逐项验收：**raw 运行日志报告 targets=1280、路由覆盖实际目标 IP/NIC、所有四 rail 路由 RTT/带宽均从已安装 channel 推导，max_rtt_ns=600、max_bdp_bytes=30000，且 IRN BDP=30,000 B；配置/原始快照保留 10 条输入；10/10 完成，逐流 rail 与 NIC/IP 身份正确，唯一接收字节、累计确认、完成字节符合输入，合计 2,408,448 B；FCT、WS24 identity、uplink 等原始数据可解析。对 OS1 10 ns/100 ns 混合链路的保持由目标图逐边输入哈希与运行时 RTT/BDP 共同核验；不能只靠离线 600/30000 预测通过。

该格只证明合成图正确性，不代表真实部署规模上的性能。

## C. 可触发动态 CNP 正确性格

### 输入和触发设计

新增 config/ws24_synthetic_cnp_incast_flows.txt，四条 1 MiB 流（合计 4,194,304 B），分别由合成 host 0, 8, 64, 72 的 rail 0 同时发往 host 1 的 rail 0；PG=3、seed=1。它是明确标注的受控 incast fixture，不是实际训练流。四条流在目标 host NIC 的汇聚出口制造真实排队机会，保留默认 ECN/QCN 阈值；是否产生 ECN/CNP 必须由 raw 证实，不预设通过。

此输入已加入 generator/manifest；当前 manifest SHA-256 55997be83ecf7e43accc2f6bc546b97185943657cdc64da0d5c89ef91a52b127，文件 SHA 在 manifest。新增 .gitattributes 规则保留 ws24_synthetic_* 的原始字节，避免 Windows 换行转换破坏 manifest 核验。离线验收确认四条 flow、同 rail、独立源 rank、同目的 rank、1 MiB/流、总量 4 MiB。目标图四组件结构确保同 rail 可达；未来仿真仍须验证真实路由路径。

本地预留 ID：20261002-120000-ws24-cnp-incast-correctness。使用目标 320-host topology/NIC 清单、该 incast 输入；参数同 B（fecmp、400 Gbps、PFC=0、IRN=1、DCQCN、buffer=9 MiB、seed=1）。

### 运行观测要求与验收

原有 WS24_CNP_FLAG 只记接收端生成 flag；WS24_RX_ACK 只记每 QP 首个 ACK，不能证明后续带 CNP 的 ACK/NACK 到达源 NIC 或 DCQCN 实际改变 QP 状态。固定源码 `b1184d6…` 已在 `RdmaHw` 添加仅 WS-24 开启的收发观测：生成、接收与实际降速各 QP 最多 32 条；**尚未远端编译或以该 SHA 运行**。事件字段和执行后验收要求为：

1. `WS24_CNP_FLAG` 在接收 host 记录时间、flow/QP 五元身份、两端数值 IP、rail、真实 NIC interface、ACK/NACK 类型、序号和 CNP bit。
2. `WS24_CNP_RX` 在源 host 命中双 IP QP 后记录相同身份、真实源 NIC/interface、ACK/NACK 类型、序号、QP rate 与 alpha/pending 前态；`WS24_CNP_STATE` 记录 DCQCN 处理后的 pending/rate/alpha。生成和接收分别逐 QP 最多记 32 条，因此若日志截断导致无法事件配对，应保留 raw 并核验/调整观测上限，不能硬判通过。
3. `WS24_CNP_RATE` 在 `CheckRateDecreaseMlx` 的 CNP pending 分支、实际写入 `q->m_rate` 后记录同一 QP 的 rate/目标速率前后值、alpha 与时间；默认 RateOnFirstCnp=1 时首个 CNP 到达只安排后续 4 µs 回调，必须看到活动 QP 在完成前真正降速。

**通过条件：**至少一条接收端生成的 CNP flag 按反向 rail 返回预期源 NIC；源端以同 flow、两端 IP、端口/PG 命中唯一 WS-24 QP；日志明确 ACK/NACK 中的 CNP bit；该 QP 的 DCQCN CNP pending 状态生效，并观察到按源码逻辑安排的 rate-decrease 状态转变（不能只数 flag 或输出 cnp=1）。四条输入流仍需完成与字节守恒；若有丢包、未完成或只发生接收标志而源端无状态变化，格不通过，保留 raw 并定位。独立 ReceiveCnp 包仍不支持，本格只测随 ACK/NACK 携带的标志路径。若默认 ECN 触发没有事件，不得修改门槛后重复同 ID；先据 raw 调整受控输入或观测、固定新输入 SHA/新 ID。

A、B、C、D 全部格须使用 `b1184d6…` 的同一源码与固定输入；若编译/正确性失败而修改源码或输入，须重新冻结共同 SHA、修订协议与独立 ID，再判定哪些格需要重跑。不能让 A/B/D 跑在旧 `824e3fa…`，把 CNP 单独跑在另一 SHA 却称同一冻结批次。

## D. 相同逻辑需求与总字节的 rail × placement 四臂

| 臂 | 输入文件 | 含义 | SHA-256 |
| --- | --- | --- | --- |
| 固定放置 × 单 rail | ws24_synthetic_fixed_single_flows.txt | 所有 10 条逻辑流使用 rail 0，rank→host 为固定映射 | 04a486ea8c3b974e322b883103ff5e87df36d08191c5296c53bf3134ad90b46c |
| 固定放置 × 多 rail | ws24_synthetic_fixed_multi_flows.txt | 相同需求按 flow_id % 4 分到四 rail | c708f5046f4e9efe79ebbb5c200507bac7d31fb0ad0984bfaca6361c8cfdf541 |
| 可变放置 × 单 rail | ws24_synthetic_variable_single_flows.txt | 相同逻辑需求；rank 1/2 的 host 映射互换，所有流走 rail 0 | 6c6845ec68febff594cbd018971eb39fbe19524ca70e52b2eabf28bcf9430257 |
| 可变放置 × 多 rail | ws24_synthetic_variable_multi_flows.txt | 同一可变放置并按 flow_id % 4 分 rail | 8ce8d8d7b6582d902960fb3463435a25e6d3ae4e3da677827ea8beea6c73f77a |

四臂共同使用 B 的目标 topology/NIC 文件，manifest SHA 同为 55997be…a52b127；每臂 10 条流和 2,408,448 B，flow_id、job/rank 需求属性、时间、PG、tag、大小配对。仅 rail 分配和 rank→host 放置按契约变化。四个本地预留 ID：

- 20261002-130000-ws24-fixed-single
- 20261002-130100-ws24-fixed-multi
- 20261002-130200-ws24-variable-single
- 20261002-130300-ws24-variable-multi

**逐臂验收：**拓扑/NIC/flow 哈希一致；10/10 流完成，输入/完成数与 2,408,448 B 唯一接收/确认字节守恒；每流 rail/NIC/IP、rank placement、demand/release/finish 身份可配对；四臂无混用输入或重复 ID。记录逐 flow finish_ns-demand_ns、最大完成时间跨度 max(finish_ns)-min(demand_ns)、源端准入/实际放行等待（若非零）及 rail 使用计数。先在固定、可变 placement 各自配对比较多 rail 对单 rail，再比较 placement 的差异；这是一个合成 seed 的描述性四臂 pilot，不能称为普遍性能收益或真实训练 job 改善。后续若要作统计确认，须另行冻结独立 job-demand/seed 和双侧判据，不能把四个臂或同一需求的行顺序置换当独立样本。

## 顺序、资源与停止规则

1. 当前阶段完成输入/来源、观测源码与共同 SHA 的本地冻结，14 格尚未运行。续作已核实 WS-23 无在途远程作业、共享 worker 无冲突、服务器资源健康、14 个 ID 未占用；已部署并核验固定 worker，且把源码缓存同步到 `dc6477e5f469434f42c2b888ac0e18c50341b422`（实验仍须构建 `b1184d6…`）。不以 WS-23 五格全部成功作为独立 WS-24 回归的静态条件。后续 build/run 前仍须由实际 Luna High 线程监督，并复核入口/ID 状态；每格使用独立目录和资源收据。
2. 允许的未来顺序：A 旧输入回归；B 320-host correctness；C CNP 输入/观测的本地触发门槛后执行；D 四臂 pilot。每项失败先保留 raw 并诊断，修复后新 SHA/new ID；不得越过 correctness 直接解释 D 的效果。
3. 适用已冻结的服务器门槛：load1m ≤10、MemAvailable ≥32 GiB、空闲盘 ≥100 GiB、无他人/WS-23/未知 build 或仿真作业；build 单格 20 分钟、仿真单格 10 分钟上限；资源收据每 5 秒记录，远程后台监督静默、约半小时一次精简状态。出现工作流定义的任一异常就停止后续格并按原始数据恢复流程处理。
4. 所有终态 raw 回传并核验后，再实际切回 Sol High 分析。上述 8+1+1+4 格构成 WS-24 仍未完成的必做执行任务，不因本文冻结而视作运行、效果结论或工作流闭环。

## 本地验收入口与当前阶段边界

- `python scripts/verify_ws24_inputs.py` 核对 11 文件 manifest、目标图与四臂逻辑输入；已在本地重跑通过。
- `python scripts/verify_ws24_legacy.py <实验ID> --source-sha <共同SHA> --flow-kind legacy5|legacy6 --lb fecmp|conga|letflow|conweave` 核对 A 单格的状态、输入快照、旧 1000 ns 拓扑、LB_MODE、输入 tag 计数、FCT 身份/数量与 uplink；旧五列的历史 FCT 完整哈希还须在矩阵入口与参考 raw 核对。
- `python scripts/verify_ws24_result.py <实验ID> --source-sha <共同SHA> --profile target|cnp|arm [--fixture fixed_single|fixed_multi|variable_single|variable_multi]` 核对 B/C/D 单格的精确 fixture、1280 目标路由、600 ns/30,000 B、20 列逐流收据、FCT、字节守恒；C 进一步关联同一 QP/序号的 flag、源端接收、pending 和完成前实际降速。旧最小格可用默认 `minimal` profile 复核。
- `python scripts/verify_ws24_matrix.py --source-sha <共同SHA> --reference-fct-sha-json docs/research/evidence/ws24-legacy-reference-fct-sha.json [--id-map <替换ID映射JSON>]` 汇总 14 格并要求旧五列 FCT 与历史原始哈希逐字节相同；四臂再按同一 flow_id 比较逻辑需求、placement/rail 和完成跨度。失败或重跑使用新的实验 ID，经 `--id-map` 明确替换，绝不覆盖旧 raw。
- 本轮仅有 Python 语法、静态输入与既有最小格的本地回归。Windows checkout 无可用 C++ 构建环境，`b1184d6…` 新增 CNP 日志的编译和动态验收仍待共享远程入口协调；当前不能报告 14 格通过。
