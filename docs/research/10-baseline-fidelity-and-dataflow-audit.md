# ConWeave 研究入口：Baseline Fidelity Check 与实验数据流审计

记录日期：2026-09-23；后续状态同步：2026-09-26（WS-10 交接）。审计源码：个人 fork `LarryBUPT/conweave-ns3` 的 `a8d2db5f057172ce89730b4f6344c531e34a9302`。第 1–4 节仅核对当时的四个基线、运行输入和既有观测链路，不把最小运行结果解释为性能结论。后续工作流的证据与路线见第 5 节；它们不改写这组基线的固定 SHA、参数或原始结果。

## 1. 实验契约与可复现输入

四次实验均使用 `leaf_spine_128_100G_OS2`、`AliStorage2019`、`--netload 10`、`--simul-time 0.01`、`--cc dcqcn`、`--pfc 1`、`--irn 0`、`--bw 100`、`--buffer 9`、`--sw_monitoring_interval 10000`。`run.py` 从 OS2 算出每主机生成负载 5%，流量区间 `[2.000, 2.010] s`；`RANDOM_SEED 1` 经配置进入 ns-3 的 `srand` 和 `SeedManager::SetSeed`。四次仅 `LB_MODE` 与算法专属、对其他模式无效的 ConWeave 参数不同。

重要约束：`traffic_gen/traffic_gen.py` 调用 Python `random`，但没有设置生成器 seed；ns-3 的 `RANDOM_SEED` **不控制 trace 生成**。本轮复用 smoke 实验 `20260923-165542-smoke-fecmp` 的同一个输入文件 `L_5.00_CDF_AliStorage2019_N_128_T_10ms_B_100_flow.txt`（首行 19,388，SHA-256 `abebc3170428aa22ebb13b15246243b806cb4f749bf4c9e6a80fb0a4a694a3cf`）。所用拓扑文本 SHA-256 为 `0dddc4f3ae673139b895ff2f875befe82b234cc48e325bd8a164d9cddedc12e2`。该拓扑是仓库中预置的 `config/leaf_spine_128_100G_OS2.txt`，运行时**读取而非生成**。`config/fat_topology_gen.py` 可生成 fat-tree 文本，但不是这组实验的步骤。

远程根目录 `/home/fnl/lzy`；每个 `<实验ID>` 的源码在 `runs/<实验ID>/source`，原始结果在 `results/<实验ID>/raw/<数字ID>/`，元数据在 `results/<实验ID>/metadata.json`，配置快照在 `results/<实验ID>/config/`，下载后本地在个人 fork 的 `results/<实验ID>/`。`remote_worker.py` 为每次实验创建固定 SHA 的独立构建，以 `-j2` 编译，只允许一个仿真同时运行；`run.py` 为每次运行随机生成数字原始目录 ID。`metadata.json` 保存 Git 仓库、commit、分支、服务器、参数、seed、命令、开始/结束时间、状态和原始目录 ID。

### 最小运行记录

| Baseline | `LB_MODE` | 实验 ID / raw ID | 运行与选择逻辑证据 | 结果位置 |
| --- | ---: | --- | --- | --- |
| ECMP (`fecmp`) | 0 | `20260923-180001-fidelity-fecmp` / `655853737` | `SUCCEEDED`；`LB_MODE 0`，FCT 19,388 行、uplink 65,984 行；源代码路径为 `GetOutDev → DoLbFlowECMP` | `results/20260923-180001-fidelity-fecmp/` |
| CONGA | 3 | `20260923-180002-fidelity-conga` / `340182156` | `SUCCEEDED`；CONGA history 记录 flowlet timeout **51**，证实动态分支被触发；FCT 19,388 行 | `results/20260923-180002-fidelity-conga/` |
| LetFlow | 6 | `20260923-180003-fidelity-letflow` / `92340389` | `SUCCEEDED`；Letflow history 记录 flowlet timeout **50**；FCT 19,388 行 | `results/20260923-180003-fidelity-letflow/` |
| ConWeave | 9 | `20260923-180004-fidelity-conweave` / `547586311` | `SUCCEEDED`；rerouting **376**、OoO 入 VOQ **23,502** 包、VOQ flush **330**；VOQ 采样 8,328 行 | `results/20260923-180004-fidelity-conweave/` |

本表的通过标准：状态 `SUCCEEDED` 且 FCT 非空；四个 `FLOW_FILE` 的哈希相同、拓扑哈希相同、公共配置相同；原始日志存在对应算法的入口或统计证据；FCT、VOQ（仅 ConWeave）、uplink 的原始文件与分析输出逐项核验。即使通过，也只说明此输入下路径可运行；不能推出算法优劣或所有分支均被覆盖。

四份结果均已由 `fetch` 下载至个人 fork 的忽略目录 `results/<实验ID>/`，远程相同 ID 位于 `/home/fnl/lzy/results/<实验ID>/`。每份 `config/` 含 `config.txt`、`topology.txt`、`traffic_trace.txt`；每份 `metadata.json` 记录 `a8d2db5f057172ce89730b4f6344c531e34a9302`、分支、seed、参数、原始目录 ID 与开始/结束时间。远程核对了四个实际 `source/config/..._flow.txt` 的哈希，均与快照一致，且 `simulation.log` 均记录缓存 trace 已存在。`scripts/verify_baseline_fidelity.py` 独立比对了公共配置和两个输入哈希，结果为 `common_config_equal: true`，机器可读摘要见本论文项目 `results/baseline_fidelity_20260923.json`。四份 FCT SHA-256 各不相同，结合源码分派和专属非零计数，支持四个模式在此次输入下并非同一输出路径。

本机 `scripts/analyze_result.py` 对每份均产生 `fct_summary.json`、`fct_percentiles.csv`、`fct_slowdown.svg`；每份 raw 中原有 `fctAnalysis.py` 的 summary 与 CDF 均非空。四份按同一窗口选出 9,708 条已完成流；P99 FCT 分别为 ECMP 161.446、CONGA 161.994、LetFlow 173.309、ConWeave 138.323 µs，**仅作分析链路数值校验，不作性能排序**。ConWeave 的 `queueAnalysis.py` 生成两个 VOQ CDF，8,328 条 VOQ 采样中 256 条非零，样本最大 3 个 VOQ、280 个排队包。四份 PFC 事件文件均为空，说明这个低负载最小实验未实际触发 PFC；不能据此验证 PFC 阈值分支。

原有 `analysis/plot_uplink.py` 在远程 Python 3.5 环境因已安装的 `cycler` 使用较新类型注解语法而无法导入。保持源码与仿真不变，在本机 `tmp/uplink-venv`（Python 3.12、Matplotlib）用四份 raw 与对应 `.history` 记录成功运行原脚本，诊断图为 `results/baseline_fidelity_uplink_20260923.pdf`。另由 raw 累计字节检查了每份 64 个 ToR uplink 在 `[2.005,2.010] s` 的单调计数及正速率；远程绘图环境仍需在后续工作中处理，但原始 uplink 与脚本计算链路已核实。

## 2. 一次真实运行的数据流

```text
固定源码 SHA + 参数
  → run.py：计算 hostload、查找/生成 traffic_gen trace、写 mix/output/<数字ID>/config.txt
  → ./waf --run 'scratch/network-load-balance <config.txt>'
  → 读 TOPOLOGY_FILE/FLOW_FILE；创建主机、交换机、Qbb 链路和 RDMA 应用
  → QbbNetDevice::Receive → SwitchNode::SwitchReceiveFromDevice
  → SwitchNode::SendToDev / GetOutDev → ECMP / CONGA / LetFlow / ConWeave
  → ConWeave RxToR 可进入 ConWeaveVOQ → SwitchNode::SendToDevContinue / DoSwitchSend
  → SwitchMmu 准入、PFC、ECN → QbbNetDevice 队列、发送
  → 目标主机 RdmaHw::ReceiveUdp / ReceiverCheckSeq → ACK/NACK、CNP、DCQCN
  → qp_finish 与 periodic_monitoring 写 raw
  → fctAnalysis.py / queueAnalysis.py / analysis/plot_uplink.py
  → 本机 scripts/analyze_result.py 按实验 ID 写 processed 与 figures
```

### 2.1 拓扑、trace 与参数映射

`run.py` 的 `lb_modes` 把 `fecmp/conga/letflow/conweave` 映射为 `0/3/6/9`。配置模板把 `--topo` 写成 `TOPOLOGY_FILE config/<topo>.txt`，把生成的流量文件写成 `FLOW_FILE config/<flow>.txt`，并写 `LB_MODE`、`CC_MODE`、PFC/IRN、缓冲区、监控时间和输出路径。默认 DCQCN 的拥塞参数也在 `run.py` 中写入。`--simul_time` 是**流量生成时长**；实际事件从 2 s 开始，仿真会继续处理未完成流。

`traffic_gen/traffic_gen.py` 从 `traffic_gen/AliStorage2019.txt` 采样流大小，用 Poisson 到达生成 `src dst pg size start_time`，第一行为流数量。`run.py` 按文件名缓存 trace；存在即直接复用。`scratch/network-load-balance.cc::main` 读取两个文本的首行并建立 `SwitchNode`、链路、IP、`RdmaDriver/RdmaHw`，随后 `ReadFlowInput` 与 `ScheduleFlowInputs` 把每条 trace 行变成 RDMA client/QP。`CalculateRoutes` / `SetRoutingEntries` 创建 ECMP next-hop 表；后续遍历 next-hop 建立 CONGA、LetFlow、ConWeave 路径表，`Settings::hostIp2SwitchId` 负责源/目的 ToR 关联。

`scratch` 读取 `RANDOM_SEED` 后执行 `srand(seed)` 和 `SeedManager::SetSeed(seed)`。`run.py` 的随机数字输出 ID 使用本机时间播种，但仅用于目录名，不是 ns-3 路由 seed。可复现契约必须同时保留**trace 文件哈希与配置 seed**。

### 2.2 交换机分派与四个 baseline

收到交换机数据包时，`QbbNetDevice::Receive` 添加入端口 `FlowIdTag`，调用 `SwitchNode::SwitchReceiveFromDevice`。`SendToDev` 对 CONGA (`3`) 和 ConWeave (`9`) 直接调用各自的 `RouteInput`，由其回调 `DoSwitchSend` 或 `SendToDevContinue`；其余模式走 `GetOutDev`。`GetOutDev` 中 ECMP (`0`) 及控制包通过 `DoLbFlowECMP`，LetFlow (`6`) 调 `DoLbLetflow → LetflowRouting::RouteInput`。`DoLbConga`、`DoLbConWeave` 虽标记为 dummy ECMP，但服务于控制包/退化路径；正常跨 ToR UDP 数据已在 `SendToDev` 前置分派，不能据 dummy 函数认定 CONGA/ConWeave 未生效。

| 模式 | 入口与实际选路 | 核心状态 | 运行证据口径 |
| --- | --- | --- | --- |
| ECMP | `SwitchNode::GetOutDev → DoLbFlowECMP`，按源/目的 IP、端口与 `m_ecmpSeed` 哈希选 next-hop | `m_rtTable`、`m_ecmpSeed` | `LB_MODE 0`、非空 FCT/uplink；代码入口核验；无专属动态计数器 |
| CONGA | `SendToDev → CongaRouting::RouteInput → GetBestPath`，flowlet 选路并传递路径/拥塞反馈 tag | `m_flowletTable`、`m_DreMap`、`m_congaToLeafTable`、`m_congaFromLeafTable`、路径表 | `LB_MODE 3`、CONGA history/flowlet timeout、与 ECMP 不同的 uplink/FCT 指纹；计数为 0 时只证明入口可达 |
| LetFlow | `GetOutDev → DoLbLetflow → LetflowRouting::RouteInput → GetRandomPath`，100 µs flowlet 间隔后重选路径 | `m_flowletTable`、`m_letflowRoutingTable`、`LetflowTag` | `LB_MODE 6`、LetFlow history/flowlet timeout、uplink/FCT 指纹 |
| ConWeave | `SendToDev → ConWeaveRouting::RouteInput`，TxToR 的 epoch/phase/路径状态与 RxToR 的乱序缓存 | `m_conweaveTxTable`、`m_conweaveRxTable`、`m_conweavePathTable`、`m_voqMap`、Data/Reply/Notify tag | `LB_MODE 9`、ConWeave history 的 reroute/VOQ/OoO 计数、VOQ 原始采样 |

### 2.3 ConWeave 与 VOQ；MMU/PFC；RNIC

ConWeave 的 TxToR 按 flow key 保存 epoch、phase、当前路径、reply/notify 等状态，选好 pathId 后给数据包加 `ConWeaveDataTag`。中间交换机按 tag 的 pathId/hopCount 转发。RxToR 比较 packet 与本地 epoch/phase；当 phase 1 包先于前一 phase 的尾部到达，建立每流 `ConWeaveVOQ` 并入队，同时估计 flush deadline。phase 0/TAIL 到来可重设期限；定时器触发 `FlushAllImmediately`，先经 `CallbackByVOQFlush` 更新 Rx 状态，再按 FIFO 释放到 `SendToDevContinue`，最后删 VOQ。RxToR 可发 Reply/Notify，反馈影响 TxToR 后续路径。VOQ 不是交换机 MMU 的 egress queue。

`SwitchNode::DoSwitchSend` 对普通数据调用 `SwitchMmu::CheckEgressAdmission` 和 `CheckIngressAdmission`，更新占用，可能丢包并通过 `CheckAndSendPfc` 暂停；出队 `SwitchNotifyDequeue` 释放占用、决定 ECN 标记和 PFC resume。`SwitchMmu::ShouldSendCN` 用 egress shared queue 的 `kmin/kmax/pmax`；`QbbNetDevice` 承载真实发送队列/PFC 帧。这一路可改变排队、暂停、丢包、ECN，进而改变 FCT、P99 与 uplink。此轮 PFC=1、IRN=0、DCQCN=1，保持四模式一致。

目标 RNIC 的 `RdmaHw::Receive → ReceiveUdp → ReceiverCheckSeq` 检查序号，乱序时生成 NACK，必要时随 ACK/NACK 携带 CNP 标志；`ReceiveAck` 处理 NACK、重传与 CNP，DCQCN 的 `cnp_received_mlx` / rate decrease 调整发送速率。IRN 分支使用 SACK，但此轮关闭。独立 `ReceiveCnp` 当前会直接报错退出；本实验中的拥塞反馈走 ACK/NACK 的 CNP flag。ConWeave VOQ 在目标 RNIC 前处理部分路径切换乱序，未被 VOQ 掩盖的乱序仍会影响 RNIC 的 NACK/CNP 与 FCT。

### 2.4 原始数据与指标口径

| 指标 | 原始数据与生产点 | 现有分析入口 | 口径/限制 |
| --- | --- | --- | --- |
| FCT、P99 FCT | `<数字ID>_out_fct.txt`，`qp_finish` 每完成 QP 写 `src dst sport dport size start_ns fct_ns standalone_ns` | `fctAnalysis.py`；本机 `scripts/analyze_result.py` | `start_ns > 2.005e9` 且 `start_ns+fct_ns < 2.060e9`；P99 是该窗口内**已完成流**的 FCT 第 99 百分位，不是全部输入流；slowdown=`max(1,FCT/standalone)` |
| ConWeave VOQ usage | `<数字ID>_out_voq.txt` 与 `_out_voq_per_dst.txt`，`periodic_monitoring` 采样 `(time,ToR,#VOQ,#packets)` / `(time,dstIP,#VOQ,#packets)` | `queueAnalysis.py` 产 CDF | 仅 ConWeave 打开文件；是重排 VOQ 状态，不是 MMU 物理 buffer occupancy |
| MMU 物理 queue usage | `<数字ID>_out_qlen.txt` 的配置项存在，但 `monitor_buffer` 位于 `#if (false)` | 当前链路无有效统计 | **本轮不可报告物理队列占用**；空文件不能视为 0 占用 |
| Uplink utilization / imbalance | `<数字ID>_out_uplink.txt`，`periodic_monitoring` 写 `(time,ToR,outDev,cumulative_tx_bytes)`；字节计数来自 `SwitchNode::SwitchNotifyDequeue` | `analysis/plot_uplink.py` 对各端口相邻采样求差，再算每 ToR 的 `(max−min)/avg` CDF | 原始值是累计发送字节，不是百分比；利用率需除以采样间隔与 100 Gbps 端口速率；短窗口须注明选取时间 |
| PFC/CNP 诊断 | `_out_pfc.txt` 的 pause/resume 事件，`_out_cnp.txt` 的 ECN/OoO CNP 计数 | 原始日志/独立核对 | 可辅助解释 FCT/队列差异，不直接代表路由逻辑有效 |

`run.py` 调用 `fctAnalysis.py` 处理全部模式，只对 ConWeave 调用 `queueAnalysis.py`；这两个 `os.system` 的退出码未检查且 stdout/stderr 被隐藏，故必须检查生成文件是否存在、非空且可解析。`analysis/plot_uplink.py` 依赖 `mix/.history` 与固定输出布局，更适合批量论文图；本轮最小检查直接从单次 raw 的累计字节序列计算窗口内端口速率与 imbalance，保留原始文件供既有脚本复核。

## 3. 研究机制 → 可修改面

| 研究机制 | 对应类/函数 | packet path 位置 | 输入参数 | 内部状态 | 影响的实验指标 | 可使用的 baseline |
| --- | --- | --- | --- | --- | --- | --- |
| 固定流哈希选路 | `SwitchNode::DoLbFlowECMP` | 每跳 `GetOutDev` | `LB_MODE 0`、seed、拓扑 next-hop | `m_rtTable`、`m_ecmpSeed` | FCT/P99、uplink、PFC | ECMP；其他模式控制包回退 |
| 拥塞反馈的 flowlet 路径 | `CongaRouting::RouteInput/GetBestPath` | TxToR、中间交换机、RxToR | `LB_MODE 3`、DRE/aging/flowlet 常量 | flowlet、DRE、本地/远端反馈表 | FCT/P99、uplink、CNP/PFC | CONGA |
| 随机 flowlet 路径 | `LetflowRouting::RouteInput/GetRandomPath` | TxToR 选路，中间交换机按 tag 转发 | `LB_MODE 6`、flowlet timeout | flowlet 表、路径表 | FCT/P99、uplink、RNIC OoO | LetFlow |
| epoch/phase 路径切换 | `ConWeaveRouting::RouteInput` | TxToR 决策、RxToR 反馈 | `LB_MODE 9`、reply/expiry/path pause | Tx/Rx 表、路径表、tags | FCT/P99、uplink、VOQ、CNP | ConWeave |
| 接收端重排 | `ConWeaveRouting` + `ConWeaveVOQ` | RxToR 到目标主机前 | VOQ flush/default waiting | `m_voqMap`、FIFO、计时器 | VOQ usage、FCT/P99、RNIC OoO | ConWeave |
| 缓冲、PFC、ECN | `SwitchNode::DoSwitchSend/SwitchNotifyDequeue` + `SwitchMmu` | 出端口准入与出队 | buffer、PFC、kmin/kmax/pmax | ingress/egress bytes、pause、ECN 阈值 | FCT/P99、PFC、uplink | 四模式共享 |
| RNIC 乱序与拥塞控制 | `RdmaHw::ReceiverCheckSeq/ReceiveAck/cnp_received_mlx` | 终端接收及发送 QP | CC、IRN、ACK/NACK/CNP | QP、seq、SACK、rate、alpha | FCT/P99、CNP | 四模式共享 |

| idea（待下一阶段形成可证伪假设） | code location | packet path | parameter | baseline | metric |
| --- | --- | --- | --- | --- | --- |
| 选路规则这一类可修改面 | `switch-node.{h,cc}` 分派 + 新的 `*-routing.{h,cc}`；注册在 `src/point-to-point/wscript` | TxToR 或每跳 | `run.py` 模式号 → scratch `LB_MODE` / `Settings::lb_mode` | ECMP、CONGA、LetFlow、ConWeave | FCT/P99、uplink |
| 路径反馈/状态这一类可修改面 | 对应 routing 实现与 header/tag；scratch 的路径表初始化 | TxToR ↔ RxToR | `run.py` 配置模板 → scratch 解析/`SetConstants` | CONGA 或 ConWeave | FCT/P99、uplink、CNP |
| 重排这一类可修改面 | `conweave-routing.{h,cc}` + `conweave-voq.{h,cc}` | RxToR | VOQ deadline/expiry 参数链 | ConWeave | VOQ、FCT/P99、RNIC OoO |
| 观测定义这一类可修改面 | scratch raw writer + `fctAnalysis.py` / `queueAnalysis.py` / `analysis/plot_uplink.py` | 完成回调/周期采样后 | 分析窗口、采样间隔、BDP | 四模式 | 指标口径本身 |

最小新增 LB idea 的文件集合取决于落点：新路由模式需在 `run.py` 加模式映射与参数输出，在 `scratch/network-load-balance.cc` 解析、初始化路径表和常量，在 `switch-node.{h,cc}` 增加选择入口，在 `src/point-to-point/model` 放对应 routing 实现并更新 `src/point-to-point/wscript`。若采用现有 routing 对象持有方式，还需在 `switch-mmu.h` 增加成员并绑定 callback。若需要新的 per-switch 状态，应确认其生命周期和路径表注入位置；若要比较新指标，还须加 raw writer 与分析脚本。保持四个原 baseline 分支原样，使用新模式号和相同 trace/seed 作对照。

## 4. 本轮界限与下一阶段前的核验点

- 最小仿真仅核实可运行、数据流和既有分析，不进行显著性或性能排名。P99 来自极短时间窗，仅能作为链路存活检查。
- trace 生成未播种是跨运行可比性的主要陷阱；以后必须继续共享不可变 trace 或先独立记录生成 seed 与文件哈希。
- `queueAnalysis.py` 的 queue 语义限于 ConWeave VOQ。若下一阶段假设涉及 MMU 物理占用，应先建立单独观测口径，再做最小实验。
- 若算法专属计数器为 0，须把“模式被选中”与“关键动态分支被触发”分开报告，不推断算法全部行为已验证。

## 5. 后续证据与研究路线同步（2026-09-26，WS-10 闭环）

本文件第 1–4 节是 **2026-09-23 四模式 fidelity 的历史审计**。后续 WS-06 至 WS-09 使用新增六列输入、`dualtrack`、GuardHash/HarmGate 原型和不同接收契约，不能把它们的数字并入上表做同条件排名。跨对话的实时状态与任务边界以个人 fork 的 [CURRENT_STATE](../project-state/CURRENT_STATE.md)、[WORKSTREAMS](../project-state/WORKSTREAMS.md) 和 [ROADMAP](../project-state/ROADMAP.md) 为入口，运行时仍以源码、实验 ID 的元数据和原始数据为准。

| 阶段 | 已核验事实 | 证据等级与边界 |
| --- | --- | --- |
| WS-06 输入兼容 | 显式 flow file、五/六列解析和 tag 通路；旧五列四 baseline 的 FCT 哈希与此前同输入运行一致 | [Handoff 06](../handoffs/2026-09-24-06-six-column-input-and-tags.md)：输入与回归核验，不是双轨性能证据 |
| WS-07 最小双轨 | `dualtrack` 中 `tag=2` UDP 数据逐包哈希、`tag=1/0` 按流 ECMP；单类/双类与跨 ToR 正确性通过。PFC=1、IRN=0 的单 seed 四格中，逐包无背景批次为 4002.653 µs，背景交互仅 +2.038 µs | [Handoff 08](../handoffs/2026-09-25-08-ws07-dual-track-mixtax.md)、[四格摘要](../research/ws07-pilot-summary.json)：技术 pilot；4 ms 尾部不能归因于背景 |
| WS-08 接收诊断 | 只加日志的复跑把四条约 4 ms 尾流逐一对应到最后 192 B 未确认后的 4 ms RTO；共同 PFC=0、IRN=1 的四格全部完成，MoE 交互为 −0.053 µs（−3.7456%），背景 P99 差为 0 | [Handoff 09](../handoffs/2026-09-25-09-ws08-receiver-gate.md)、[诊断](../research/ws08-receiver-preflight.md)：另一套传输条件的单 seed pilot；不证明其他条件无跨类损害 |
| WS-09 工程原型 | `shortq2/guardhash/guardhashgate`（模式 13/14/15）与真实出口 per-port/per-tag 计数已实现；十个终态 ID 的完成数、trace/拓扑哈希、队列守恒和同输入配对复核通过。三格单 seed MoE 合成批次为 1.421/1.415/1.490 µs，背景 P99 相同；门控激活 39 次、退出 9 次 | [Handoff 10](../handoffs/2026-09-26-10-ws09-guardhash-prototype.md)、[冻结规格](../research/ws09-guardhash-v0-spec.md)、[十格摘要](../research/ws09-validation-summary.json)：正确性与技术 pilot；门控格在此输入下较无门控格慢，不能宣称机制收益 |
| WS-10 固定总字节正式复核 | 统一 `aa778ac523bc0319999395dd3cf8085b41e73a98`，资源 pilot 6/6、五 seed × 六格正式 30/30；全类 100% 完成，主 4 档交互 1/5 正向、归一化中位数 −1.3947%，背景安全 10/10 通过；2 档均正而 4 档多数负 | [Handoff 11](../handoffs/2026-09-26-11-ws10-fixed-load-formal.md)、[预注册](../research/ws10-fixed-load-prereg-v1.md)、[报告](../research/ws10-fixed-load-formal-report.md)、[30 格原始索引与摘要](../research/ws10-fixed-load-formal-summary.json)：正式现象 **no-go**；不证明 GuardHash 效果，也不推断其他负载普遍无损害 |

**当前决策：**WS-08 的单 seed 结果未达到正向损害门槛；WS-09 已按工程范围完成；WS-10 的正式五 seed 场景也未达到主 4 档正向方向与幅度门槛，故 WS-11 的 GuardHash/HarmGate 效果主张目前不启动。[ADR-007](../decisions/ADR-007-guardhash-prototype-before-efficacy.md)允许先实现和技术验证，同时保留 [ADR-006](../decisions/ADR-006-conditional-guardhash-selection.md)的正式效果判据。ADR 是 Architecture Decision Record（架构决策记录），用于保存会影响后续实验的决策及理由，不是性能结果。WS-09 已冻结：HarmGate 是按本地总队列字节激活类别评分的门控，GuardHash 是同一双候选上的 `q+b` 评分；二者不是两套独立协议。WS-09 的队列字节来自真实 BEgressQueue，**不回填**为本文件旧四模式的 MMU 队列观测。

**后续顺序：**WS-10 已按事前固定的场景、目标/总字节、五独立 trace seed、判据和资源预算完成；主判据 no-go，不能事后把 2 档正向趋势替换成 4 档成功结论。WS-11 已明确设立**全量输入现象验证阶段**：完整 16,384 条同步 MoE 与原始 0/64/128/192 背景档从未正式仿真，先独立预注册问题、热点与双侧指标、判据和资源 pilot。原始档位的总字节随背景增加，须并列设置负载归因控制，不得将总体负载上升直接写成包流混合损害。新场景与 WS-10 的 30 格分开报告；仅当新的现象门槛通过，才进行 GuardHash/HarmGate 等信息强对照、消融与双侧效果判断。远程仿真按[工作流](../REMOTE_EXPERIMENT_WORKFLOW.md)静默运行；确认服务器无人、隔离与资源 pilot 通过后逐级提高并行度。WS-12 可先整理当前负结果、非单调性和传输/接收边界。旧 `2.005s` FCT 窗口排除 `2.000s` 同启 MoE，本轮使用独立按 tag 的输入分母、完成率、FCT 和合成批次指标；无轮次字段，不称“八轮 job CCT”。ConWeave VOQ 仍不等于 MMU 物理队列。
