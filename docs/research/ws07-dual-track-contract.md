# WS-07 双轨契约与 MixTax 判据

日期：2026-09-25。技术验证与实验结果须回查各实验 ID 的 `metadata.json`、`config/traffic_trace.txt`、`raw/*/*_out_fct.txt` 和 `raw/*/config.log`；本文不以四流最小运行作性能结论。

## 输入、选路和传输契约

- 六列 trace 的 `tag=1` 是背景类，`tag=2` 是 MoE 类；五列旧输入缺省 `tag=0`。tag 是 ns-3 `PacketTag`，不增加线上头长，也不自动表示接收端能力。
- `dualtrack` (`LB_MODE=12`) 对 UDP 数据的 `tag=2` 在每个有多个等价下一跳的交换机以五元组加 UDP `seq` 做确定性逐包 ECMP；`tag=1` 和 `tag=0` 走原流 ECMP。单下一跳自然退化。ACK/NACK/PFC 等控制流仍按原分派。`fecmp` 作为全流对照。
- 两模式均使用同一 DCQCN、PFC=1、IRN=0、400/100G 拓扑参数、seed=1 与原 RNIC 序号/NACK/重传逻辑；没有引入 MixHash 的目的端重排、额外头字段或传输改动。RNIC 对乱序数据当前产生 NACK，逐包完成可能伴随额外重传与 CNP；这是共享传输模型下的实际代价，须在结果中单列，不能称为“零代价乱序能力”。若它导致大规模无法完成，停止性能比较并先修正共同接收语义。
- 导入拓扑为四个不连通 rail，现有四份 MoE trace 只使用 rail 0。MoE 16,384 条 8 KiB 流在 2.000s 同启；文件名 `8round` 没有轮次字段。背景 0/64/128/192 条 8 MiB 流增加总字节。只在同一 trace、同一拓扑和相同公共配置下做算法配对；跨背景档位标注为“加背景”，不称固定总负载混合比例效应。

## 独立的 MoE 分析口径

`scripts/analyze_moe_tags.py <实验ID>` 以该实验 `config/traffic_trace.txt` 为输入分母，检查其哈希与元数据一致，按照 scratch 中从 10000/100 起逐源/逐目的分配的端口号，把原始 FCT 行一一匹配到输入流。按 tag 报告输入、完成、未完成、完成率、完成流 FCT 均值/P50/P95/P99。只有全类输入流完成时才给出该类**合成批次完成时间**，即最迟完成的绝对时间减 trace 最早起点；另给完整源的批次 P99 与完整源数量。部分完成时批次指标为 `null`，不以已完成流的最大值代替。没有轮次 ID，不报告已观测的“八轮 job CCT”。旧 `scripts/analyze_result.py` 与 `fctAnalysis.py` 的 2.005s baseline 窗口及结果保持原样。

## 分阶段实验与预先判据

1. **正确性门槛：**32 主机 tag=1 单类、tag=2 单类及双类样本；核对源 ToR 计数与输入、每类完成率 100%、无异常未标记包，并确认 tag=2 触及多下一跳。按流单类应与相同 trace 的 `fecmp` 原始 FCT 逐行相同。然后在导入 1280 拓扑用版本化四流 trace 重复双类检查。此门槛只验证路径和完成，不比较优劣。
2. **资源 pilot：**先对原始 0/64 文件做静态事件与字节预算，检查服务器负载、内存和已有 ns-3 进程；以一个固定 SHA 和一个小的、保持同一 MoE 子 trace 的配对 trace 试运行，按 `-j2` 编译且同一时刻只跑一个仿真。记录墙钟、峰值 RSS、原始记录数、未完成数、NACK/CNP/PFC、队列与 uplink 采样。若完成率低于 100% 或资源逼近工作流上限，保留失败 ID 并缩小规模，不扩大到完整 64 背景。
3. **双向 MixTax 诊断：**同一 MoE 子 trace，四格为 `MoE=packet/flow × 背景=0/64`。MoE 侧主观察量为合成批次完成时间交互：`(packet,64 − packet,0) − (flow,64 − flow,0)`；背景侧为同一 64 背景 trace 的背景 FCT `packet − flow`。报告完成率、P99、逐包重传/CNP/PFC 与链路利用率。单个 trace seed 的流不是独立重复，不能从流数得到统计置信度。
4. **固定总负载主实验准备：**独立于仿真 seed 指定 trace seed，生成并保存每个 seed 的不可变 trace、生成脚本版本、拓扑与 trace SHA；在每个 seed 内固定总提供字节、目标 MoE 子 trace、发送时刻、端点/rail 约束，用替换式背景组合改变类别构成。各算法复用同一 seed 的字节级相同 trace。正式重复数及固定字节预算须在 pilot 的资源结果后冻结，不能基于一次 P99 结果挑选。

`scripts/make_ws07_pilot_traces.py` 已为 seed 20260925 生成 256 条同一 MoE 子 trace 的 0/64 背景资源样本，哈希见 `ws07-pilot-manifest.json`。`scripts/make_ws07_fixed_load_traces.py` 另生成 0/2/4 背景替换式**设计样本**：目标 MoE 256 条不变，竞争字节固定为 32 MiB，总提供字节均为 35,651,584 B，哈希见 `ws07-fixed-load-manifest.json`。后者的 tag=2 还包含随背景数变化的填充 MoE 流；正式分析使用 `analyze_moe_tags.py --target-trace config/<manifest 的 target_file>` 按固定目标集合另算 MoE 指标，不能把全部 tag=2 批次当作同一个目标集合。两套生成资产均尚未验证大规模仿真可承受。

**Go / no-go：**进入 WS-08 前，至少三个独立 trace seed 的同向交互应达到预先冻结的实际意义门槛，且 MoE 改善不能仅以背景 FCT/完成率明显恶化为代价；同时需确认损害不是由未完成流或不对称传输配置伪造。当前暂定实际意义门槛为合成批次完成时间差异 ≥5%，背景 P99 恶化不得超过 5% 且两类完成率均为 100%；pilot 后、正式运行前只可基于精度与资源约束调整并留痕。若无稳定损害或逐包流不能可靠完成，WS-08 保持条件状态。ConWeave 若进入导入混合延迟拓扑的比较，须先审计其统一 `one_hop_delay` 推导的 ToR 时序值；当前不把它作为此双轨实验的对照。
