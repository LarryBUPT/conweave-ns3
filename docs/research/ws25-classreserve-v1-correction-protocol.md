# WS-25 ClassReserve v1 唯一诊断修正：正确性预飞行

状态：2026-10-03，远程仿真前冻结。上一轮 D1 在四个诊断格全数通过：ClassReserve/DRILL 的诊断开关 FCT SHA 各自相同；ClassReserve 的 MoE 逐包双选同时出现 8,324 个接收端乱序包和 8,023 个序号范围内重复发送包，DRILL 对应为 1,675 和 1,761。D1 同一输入下 ClassReserve 的 MoE 批次较 DRILL 慢 29.389%，背景 P99 好 5.397%；该 seed 来自已查看的校准池，只作为修正理由，不是独立效果样本。

本轮消耗 ClassReserve v1 **唯一一次诊断修正额度**。候选从逐包 MoE 双选改为每个 MoE flow 在每个交换机第一次抵达时用同一双候选队列分数选端口，后续该 flow 在该交换机固定复用。背景长流原有首次双选及按流固定保持不变。修正移除流内逐包换路，不增加 flowlet timeout 参数。未改变 ECMP、DRILL、CONGA、LetFlow、ConWeave 模式分支、拓扑、传输契约或流量分布。此轮仅做 correctness / fallback / byte-conservation / resource check；不作性能结论，不开放正式矩阵。

## 固定身份与输入

仿真源码固定为 `feature/ws25-first-paper@c84108b24c94a5068861e5bb090c5aa387245ee1`；NS-3 seed 1，400 Gbps、9 MiB、PFC=0、IRN=1、DCQCN、`--simul-time 0.01 --netload 10`。拓扑 `topo_1280_400G_400G_OS1` SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。

| trace | 用途 | SHA-256 | 流数 |
| --- | --- | --- | ---: |
| `ws25_v1fix_mixed8.txt` | 五基线与 ClassReserve 同输入回归；4 背景+4 MoE | `29ebe2dcf38c0e4d29326947c4bc4e111f6b56fe378c020c30ee788fbaa5effb` | 8 |
| `ws25_v1fix_background4.txt` | ClassReserve 背景单类路径 | `e1259a4dbb17fe70e15a72881cbc3faaeac637123ba18ac29596b4f4f2743015` | 4 |
| `ws25_v1fix_moe4.txt` | ClassReserve MoE 单类稳定选路 | `8acfe14d19d7ef7822bfd9a78334b830ce581456003e132d6557a44d1e41ea60` | 4 |
| `ws25_v1fix_unclassified8.txt` | 显式 tag 0 回退 | `73704cadbdb95708c5ba26126af43b2758af688e332a80fdad46e7bc42c66dd3` | 8 |
| `ws25_v1fix_legacy5.txt` | 旧五列无 workload tag 回退 | `cc80f3a1eb23dcf936a8b371bf5b63763acac283923361efe9bcd3ebb1ae6c94` | 8 |
| `ws25_seed20262501_b192.txt` | 完整流数/类别/队列守恒correctness格；此 seed 已见，不计独立样本 | `9791006f71843ea74b044396f6ae112ea8340aa9781cf0d267876e0940b02f48` | 16,576 |

所有输入由 `scripts/make_ws25_v1fix_correctness.py` 从已冻结 preflight trace 确定性生成。五模式 baseline 为 `fecmp / drill / conga / letflow / conweave`，候选为 `classreserve`。每个实验独立构建、源码与结果目录，`ws25_diag=0`。

## 冻结 ID

| ID | 模式 | 输入 |
| --- | --- | --- |
| `20261003-180000-ws25-v1fix-pre-fecmp` | fecmp | mixed8 |
| `20261003-180001-ws25-v1fix-pre-drill` | drill | mixed8 |
| `20261003-180002-ws25-v1fix-pre-conga` | conga | mixed8 |
| `20261003-180003-ws25-v1fix-pre-letflow` | letflow | mixed8 |
| `20261003-180004-ws25-v1fix-pre-conweave` | conweave | mixed8 |
| `20261003-180005-ws25-v1fix-pre-classreserve` | classreserve | mixed8 |
| `20261003-180010-ws25-v1fix-pre-background` | classreserve | background4 |
| `20261003-180011-ws25-v1fix-pre-moe` | classreserve | moe4 |
| `20261003-180012-ws25-v1fix-pre-unclassified` | classreserve | unclassified8 |
| `20261003-180013-ws25-v1fix-pre-legacy5` | classreserve | legacy5 |
| `20261003-180014-ws25-v1fix-pre-b192` | classreserve | seed01 b192 |

## 验收和资源停止线

- mixed8 六臂须在同一 SHA、输入/拓扑哈希和共同传输参数下构建成功；每格输入分母内流全完成、字节守恒、类别计数正确。目标与类别单类、tag0 与五列 fallback 格也须全流完成；fallback 格 `fallback_packets>0`，单类格只包含对应标签流。
- ClassReserve 所有格 `queue_violations=0`；mixed8 与 b192 必须出现新增 MoE flow cache 与复用计数，背景 cache 也须有命中；b192 为 16,576/16,576，背景/MoE 分别 192/16,384。
- 每格保留 metadata、trace/topology SHA、FCT/CNP/PFC/uplink raw、config.log、资源收据。baseline 旧模式回归仅要求正确性与输入/输出守恒，不借小样排序。
- 启动前检查服务器无人作业、无未知 ns-3/worker、1 分钟 load ≤20、内存 ≥32 GiB、磁盘 ≥100 GiB。先单格 build/run，确认运行器和 map 状态；逐级提升并发，最多 cap=4。单格 build >30 min、simulation >4 h、树 RSS >32 GiB、单格新增磁盘 >10 GiB、load/内存/磁盘越线、哈希/完成率/守恒失败时立即停止新格、保留证据并以新 SHA/ID 修复重验。
- 一个 correctness 格失败即停止后续格；修复后旧 ID 不复用。全部正确性通过仍需独立校准，不足以进入正式矩阵。

Correctness 终态回传后，在 Sol High 分析逐格证据和旧模式回归。若正确性通过，另行冻结 corrected-candidate 校准契约：使用未见筛选池及预留校准需求，六臂相同 SHA/逐 seed 配对；不得将 D1/seed01 当独立验证。只有独立需求上的候选信号和完整 0/64/128 输入后，才冻结正式双侧门槛、最终样本量和全部正式 ID。仿真前由主对话实际切 Luna High，终态 raw 后实际切回 Sol High；人工无需重复授权。
