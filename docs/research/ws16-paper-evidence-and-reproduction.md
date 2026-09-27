# WS-16 论文证据与复现收束

日期：2026-09-28。本文是可供论文写作与导师讨论的**证据边界和复现入口**，不改变 WS-10/11/12 的预注册判据或结论。本次复用本地原始实验结果，没有启动远程仿真。逐格机器索引为 [`ws16-experiment-index.csv`](evidence/ws16-experiment-index.csv)，生成与快照 SHA 核验入口为 [`build_ws16_evidence_index.py`](../../scripts/build_ws16_evidence_index.py)。索引含 216 个**不同实验 ID**：WS-10/11/12 正式格 30/40/120、WS-13 反馈探针 4、校准 6、IRN×PFC 常规/压力 8、定向丢包探针 1、WS-14 小样 7。它不是 216 次独立需求重复；WS-15 没有新实验 ID。原始数据保存在 Git 忽略的 `results/<ID>/`，远端同 ID 在 `/home/fnl/lzy/results/<ID>/`；CSV 保存相对路径、固定源码 SHA、seed、输入和拓扑哈希、原始 FCT 哈希及分析入口。索引收录不等于效果证据等级相同。

## 论文可写的主张与证据链

| 主张和等级 | 固定仿真源码、输入与原始证据 | 分析与图表入口 | 允许的结论 |
| --- | --- | --- | --- |
| **WS-10 预注册正式现象 no-go** | `aa778ac523bc0319999395dd3cf8085b41e73a98`；五条独立生成 seed `20261001–20261005`，每 seed 的 0/2/4 档 × `fecmp/dualtrack` 共 30 ID；每格 trace SHA 见 CSV，拓扑 SHA `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。完整原始索引见[30 格摘要](ws10-fixed-load-formal-summary.json) | [`verify_ws10_formal.py`](../../scripts/verify_ws10_formal.py)、[预注册](ws10-fixed-load-prereg-v1.md)、[报告及逐 seed 表](ws10-fixed-load-formal-report.md) | 30/30 两类流完成；固定总字节主 4 档交互仅 1/5 为正、归一化中位数 −1.3947%，不达事前现象门槛。2 档五 seed 正向但非主判据；背景安全 10/10 通过仅限各格 2 或 4 条背景流。 |
| **WS-11 预注册正式复合 no-go** | `208fcee4c541da9b24ed26792b32ae681a30977f`；完整 16,384 MoE 加 0/64/128/192 背景、原始加四组相同流多重集的顺序置换，40 ID。原始组 192 trace SHA `bf1a1960651b2d5bd27cd1304433d489363727a7c02d08c5c05df2b2415d9c8a`；其余逐格见 CSV 与[40 格摘要](ws11-full-moe-formal-summary.json) | [`verify_ws11_formal.py`](../../scripts/verify_ws11_formal.py)、[输入审计](ws11-input-audit.json)、[预注册](ws11-full-moe-prereg-v1.md)、[报告主表](ws11-full-moe-formal-report.md) | 40/40 全完成；主 192 档交互 5/5 正向、中位 +35.9057%，但原始组背景 P99 从 1411.822 到 1505.747 µs，+6.6527% 超过历史预注册 5% 线，故复合 no-go。五组是顺序敏感性，不是五条独立需求。 |
| **WS-12 四策略各自正式双侧 no-go** | `adae7956e3fc874d9237e62a6ea8e32b26d5def1`；与 WS-11 同流记录及五组顺序、六模式 × 四档 = 120 ID；旧 `fecmp/dualtrack` 对应 40 格 FCT SHA 与 WS-11 逐格一致。逐格哈希及 raw 路径见 CSV 与[120 格摘要](ws12-packet-strategies-formal-summary.json) | [`verify_ws12_formal.py`](../../scripts/verify_ws12_formal.py)、[预注册](ws12-packet-strategies-prereg-v1.md)、[报告主表](ws12-packet-strategies-formal-report.md)、[逐流权衡图](evidence/ws13-tradeoff.svg) | RR/随机/自适应/DRILL 在主档相对既有逐包哈希的 MoE 批次中位缩短 16.116%/18.406%/21.056%/22.549%，但各有背景 P99 预定越线格，均不满足复合判据。相对哈希改善、相对 ECMP 的绝对差、追加背景交互必须分列。 |
| **WS-13 尾部相关性诊断和校准** | 逐流诊断复用 WS-12 原始格；四个只加观测的反馈 ID 固定 `a985798ef78a95f502cf8eb56982c6e3a3b1168d`，FCT SHA 与对应 WS-12 格相同；六格三条独立需求校准固定 `6a1de1d9c8c9ea3ac41921230e05d87ccda93b9d`。逐格 trace/拓扑/FCT 见 CSV | [`diagnose_ws13_tails.py`](../../scripts/diagnose_ws13_tails.py)、[`analyze_ws13_feedback_probe.py`](../../scripts/analyze_ws13_feedback_probe.py)、[`analyze_ws13_calibration.py`](../../scripts/analyze_ws13_calibration.py)、[1600 行逐流 CSV](evidence/ws13-tail-paired-flows.csv)、[反馈摘要](evidence/ws13-feedback-probe-analysis.json)、[校准摘要](evidence/ws13-calibration-summary.json)、[报告](ws13-tail-diagnosis-and-experiment-contract.md) | 慢背景 QP 与目的 ToR 出口微秒级等待、CNP 同时出现；选定 QP 无 SACK。只能定位相关链条，不能推出因果或新通用安全线。三个独立需求仅作校准，不回填正式验证。 |
| **WS-13 IRN×PFC 技术 pilot，压力 11 格不完整** | 常规四格和压力四格固定 `babd1b90d7c027cd09ac8c7d67380511a92883a6`；压力 trace SHA `bc2db1513cbde20f12eea6efa4e2265cf74954be4fa45f2a147ff0ce84b33985`、拓扑 SHA `dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad`。11 定向探针 `20260927-223000-irnpfcdrop-11@7af917af2743529882c3d8524d08114e4677b3ed`，原始 FCT 与旧 11 格逐字节相同 | [`analyze_irn_pfc_factorial.py`](../../scripts/analyze_irn_pfc_factorial.py)、[`analyze_irn_pfc_drop_probe.py`](../../scripts/analyze_irn_pfc_drop_probe.py)、[常规](evidence/ws13-irn-pfc-factorial-pilot.json)/[压力](evidence/ws13-irn-pfc-factorial-stress.json)/[丢包](evidence/ws13-irn-pfc-drop-probe.json)收据、[报告表](ws13-irn-pfc-factorial-pilot-report.md) | 常规输入 PFC 零事件；压力 00/01/10 为 16/16，11 仅 13/16。探针记录 161 次出口准入拒绝，并把三条未完成流的关键序号丢包与后续超时抑制逐一对应。旧 `metadata.status=SUCCEEDED` 仅代表非空 FCT，不能当作全部完成；11 格不参与性能排名。 |
| **WS-14 事前停止的单输入小样** | `73401ce3ac0a5c27bf0e3e0636c9337056d9355e`；0 档 trace SHA `9e00baa5c79ab45b107b82b4c18d43cbb9a1073101bf14123aedd2d90d2e89fd`、192 档 SHA `bf1a1960651b2d5bd27cd1304433d489363727a7c02d08c5c05df2b2415d9c8a`，7 个 `20260927-233000-ws14-*` ID | [`run_ws14_small.py verify`](../../scripts/run_ws14_small.py)、[`analyze_ws14_small.py`](../../scripts/analyze_ws14_small.py)、[事前契约](ws14-single-mechanism-prereg-v1.md)、[逐格 JSON](evidence/ws14-small-analysis.json)、[报告表](ws14-guardhash-single-mechanism-pilot-report.md) | 7/7 全完成。192 档 GuardHash 背景 P99 1431.183 µs，低于普通双候选 1552.660 µs；MoE 批次 19.651 µs，慢于普通双候选 19.099 和 ECMP 18.920 µs，背景尾流转移。按双侧停止规则不跑 64/128；没有完整剂量曲线或普遍效果。 |
| **WS-15 正式矩阵 gate no-go（设计决定）** | 无新仿真 SHA、无新实验 ID；复核 WS-14 七格和 WS-13 六格校准原始结果 | [门槛报告](ws15-independent-demand-gate-review.md)、[Handoff 16](../handoffs/2026-09-28-16-ws15-gate-review.md) | 未找到同时具有独立理由、可观测链条及事前双侧小样条件的新单机制；确认性矩阵未启动。“未测”不能写作性能零效应。 |

上述表的 WS-10/11/12 5% 是**各自历史预注册研究保护线**，不是业务 SLA 或普遍适用的网络阈值。WS-10 通过五个独立生成 trace seed 测固定总字节输入；WS-11/12 的五组共享流多重集，只改变顺序与端口分配，且追加背景使总字节由 128 增至 1664 MiB。它们不能合并为一个样本集或一条“纯混合比例”剂量曲线。WS-12 的模式改变信息预算，亦非等信息消融。[既有三场负结果解释](ws12-ws10-ws11-negative-evidence.md)保留更多逐组数值。

## 图表索引与复现顺序

1. [WS-10 报告逐 seed 交互表](ws10-fixed-load-formal-report.md)来自 `verify_ws10_formal.py` 与 30 格原始 FCT；图题须注明固定总字节、五个独立 trace seed、主档 4 条背景。
2. [WS-11 报告五顺序组主表](ws11-full-moe-formal-report.md)来自 `verify_ws11_formal.py`；图题须注明同一需求的顺序置换、追加背景与原始组 P99 越线。
3. [WS-12 报告六策略主表](ws12-packet-strategies-formal-report.md)来自 `verify_ws12_formal.py`；绝对批次、相对哈希缩短和背景安全三列不能互换。
4. [WS-13 连续 MoE—背景权衡 SVG](evidence/ws13-tradeoff.svg)及[其逐流 CSV](evidence/ws13-tail-paired-flows.csv)由 `python scripts/diagnose_ws13_tails.py` 从 WS-12 原始格重建；横轴为背景 P99 相对同档 ECMP 的差，纵轴为 ECMP 批次减候选批次。64→128→192 的连接线只表示离散追加负载，不是插值或独立样本置信带。
5. [WS-13 IRN×PFC 表](ws13-irn-pfc-factorial-pilot-report.md)和[WS-14 极端格表](ws14-guardhash-single-mechanism-pilot-report.md)只作技术诊断与单输入 pilot 图表；不得混入正式效果图。

在个人 fork 根目录运行以下命令。第一步只核对索引所列 216 个本地实验的元数据、trace/拓扑快照及 FCT 原始文件 SHA；`--check` 也比较重建 CSV 是否与提交版相同。正式判据须再运行各自预注册分析脚本，因为原始哈希一致本身不证明完成率或效果门槛。

```powershell
python scripts/build_ws16_evidence_index.py --check
python scripts/verify_ws10_formal.py > $null
python scripts/verify_ws11_formal.py
python scripts/verify_ws12_formal.py
python scripts/run_ws14_small.py verify
python scripts/analyze_ws13_calibration.py
```

`results/` 被 Git 忽略，故源码仓库单独克隆后不能仅凭提交版 CSV 重算原始结果。需按[远程工作流](../REMOTE_EXPERIMENT_WORKFLOW.md)从 `/home/fnl/lzy/results/<ID>/` 取回**同 ID 的完整目录**，保留 `metadata.json`、`config/`、`raw/`、`logs/resource-*`；下载不得覆盖已有 ID。WS-10 首次控制器诊断格 `20260926-070414-ws10-20261002-b4-p` 和 WS-11 缺资源收据旧格 `20260926-144756-ws11-02-b192-f` 不计正式矩阵，替代 ID 见各报告。WS-13 压力 11 的旧成功状态不表示全流完成，需以 trace 16 条与 FCT 13 条核对。

## 开题目标与现有实现的范围差异

对照原始《开题报告 罗臻宇.docx》（本机 `E:\研\毕业论文\开题报告\`；SHA-256 `532b7739eed80cf2143f3c3a2ee3deb22c175d74b94f4a6930337e002725093a`）的“二、研究内容和目标”“三、研究方案设计及可行性分析”“四、本研究课题可能的创新之处”：原计划包括发送端依据 QP/DSCP/长度实时分类、端侧逐包→flowlet 单向降级与逐 RTT 恢复、INT/ECN 带回多路径队列差 Δq、路径时延感知的乱序控制，以及接收端协同重排。当前六列 trace 的 tag 是**预先写入的输入类别**，`WorkloadTag` 让源 ToR 的交换机选路按 tag 分支；`SwitchNode::DoLbDualTrack`、`DoLbPacketStrategy`、`DoLbGuardHash` 在交换机转发路径工作。已有 ConWeave VOQ 与 IRN/接收代码属于基线/共同传输条件，不能改称本课题已实现的端侧协同重排。WS-13 的本地出口队列探针也不是端侧 INT Δq 闭环。

因此论文可称“**在 ns-3 中实现并验证带预置类别标签的交换机侧混合粒度/候选选路原型，并在指定输入与共同传输条件下完成双侧负结果研究**”。目前不能称已实现开题报告的端侧自动分类、端侧降级状态机、INT/Δq 路径控制、动态接收缓存算法，也不能称完成 SmartNIC、交换芯片、线上业务或训练 job CCT 验证。现有 MoE 指标是同启流的合成批次终点，不含真实训练轮次依赖；背景 P99 是已完成流在本输入下的分位。物理 MMU 总队列监控、可靠独立逐 QP NACK/timeout、逐包 ECN 与即时 RNIC 速率仍缺，空文件不等于零。共同 DCQCN/PFC=0/IRN=1 的 WS-10/11/12 与早期 PFC=1/IRN=0 的 4 ms RTO 诊断不能混称同一传输效应。

## 论文负结果叙事与待导师确认

建议以“**条件性负结果揭示双侧代价**”组织结果：先冻结输入和重复单位，再展示 WS-10 固定字节非单调性；随后展示 WS-11 全量输入的 MoE 正向交互与背景安全越线；再展示 WS-12 改变逐包策略后相对哈希的收益及相对 ECMP 的背景代价；最后用 WS-13 的逐流相关诊断、WS-14 事前停止和 WS-15 未开矩阵说明为什么当前证据不足以宣布新机制有效。每张图写明源码 SHA、输入/拓扑 SHA、实验 ID 范围、单位、比较基准、完成数与证据等级。不要对不同场景的百分比取合并平均、把单输入 pilot 当独立验证、把未运行格填零或在看见结果后重选 5% 线。

需请导师确认：（1）论文题目/创新点是否调整为**交换机侧原型与双侧负结果**，或另定补齐端侧和接收机制的明确范围与时间；（2）真实 MoE/背景业务是否有可核验 SLO、真实任务轮次或 trace，若无则保持合成批次与连续权衡的研究口径；（3）正文是否以 WS-10/11/12 三套各自正式 no-go 为结果主线，并将 WS-13/14/15 明标诊断、pilot、门槛决定；（4）是否需要独立需求、拓扑/负载敏感性或硬件验证作为新的前瞻性课题。任何新效果比较须另行事前冻结输入、对照、判据和完成门禁，不改写这些旧结果。
