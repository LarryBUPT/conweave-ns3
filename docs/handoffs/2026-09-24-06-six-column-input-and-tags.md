# Handoff 06：六列输入与 tag 通路

来源：WS-06「六列输入与 tag 通路」，由协调任务 `01a0cfac-3176-7590-bf34-c0f176a45118` 派发。日期：2026-09-24（中国时间）。本文件是技术验证交接，不是性能结论。权威运行规则见 [远程工作流](../REMOTE_EXPERIMENT_WORKFLOW.md)。

## 1. 本对话目标

在个人 fork 分支实现显式选择现有流文件、旧五列和新六列兼容、工作负载 tag 从输入到交换机选路入口的可见通路，以及可核验计数；保持 ECMP、CONGA、LetFlow、ConWeave 原行为。按小拓扑、旧 trace 四基线、导入拓扑轻量探测顺序验证。WS-07 双轨语义与 MixTax、WS-08 新算法不在本轮。

## 2. 已确认的项目事实

- 用户指定参考 maplerime 的解析方法。其 `scratch/network-load-balance.cc::ReadFlowInput` 支持六列和五列缺省 tag=0；本轮采用相同兼容语义，并严格校验记录数、列数、主机范围与时间顺序，避免坏的第六列被吞掉。
- 导入的 `topo_1280_400G_400G_OS1.txt` 有 1280 主机、576 交换机、3840 链路，链路延迟同时有 10ns 与 100ns。运行时从链路实际算得 `maxRtt=600ns`、`maxBdp=30000B`；maplerime 手填的 18000B 与该文件不符。见 [ADR-005](../decisions/ADR-005-imported-topology-bdp.md)。
- 四份迁入 MoE trace 静态核对无坏行：声明/实际流数分别为 16384/16448/16512/16576，tag=2 恒为 16384，tag=1 为 0/64/128/192。它们未做全量仿真。
- `core.autocrlf=true` 曾使 Git blob 的换行不同于 Windows 参考字节；现在六份导入资产在 [.gitattributes](../../.gitattributes) 中设 `-text`，版本库字节与 [溯源表](../research/mixed-flow-trace-provenance.md) 一致。旧实验的哈希以各自配置快照为准。

## 3. 已完成工作

用户决定：保留原四基线、参考 maplerime 解析方法；不赋予 tag 乱序能力，也不在 WS-06 引入 MixHash/GuardHash。以下实施、命令与记录由本任务执行。

1. 从干净的 `feature/mixed-flow-traces@30734578e7468a8cf156588de0aded5f96095e43` 创建 `feature/ws06-flow-tags`。`run.py` 和远程控制器支持 `--flow-file`（现有 `config/*.txt`），远程还可选 `--bw 400`；每次记录配置、trace/拓扑哈希并回传原始快照。
2. `scratch/network-load-balance.cc` 逐行读取五/六列；五列默认 tag=0。tag 经 `RdmaClient → RdmaDriver → RdmaHw/QP → WorkloadTag(PacketTag) → SwitchNode::SendToDev` 到达选路前入口。日志输出 `WS06_INPUT_TAG` 与源 ToR 的 `WS06_ROUTING_TAG`。四种 LB 分派规则未改。
3. 加入 32 主机 `fat_k4_100G_OS2` 小拓扑支持、四流六列样本以及旧 fidelity trace 的原样五列快照；导入 1280 拓扑支持 400G 与混合链路延迟，以实际 30000B BDP 保留断言。失败实验 ID 均保留：`20260924-205157-ws06-compile`（小拓扑 BDP 未登记）、`20260924-214000-ws06-1280-probe`（统一延迟断言）、`20260924-215000-ws06-1280-delay`（手填 18000B 与实际 30000B 不符）。

验证记录（均为远程固定 SHA 独立构建、`-j2`、单仿真；PFC=1、IRN=0、DCQCN、seed=1、`--simul-time 0.01`、`--netload 10`；原始数据已 `fetch` 至本机忽略目录 `results/<实验ID>/`）：

| 检查 | 实验 ID / raw ID | 源码 SHA | 输入与结果 |
| --- | --- | --- | --- |
| 32 主机六列 ECMP | `20260924-210116-ws06-small-six` / `549119844` | `887f55ef91b0b02455bad1cce5be864d1f4fd02c` | trace `be78b4cb…ba75748`；tag=1/2 各 2 流，入口包 132/18、缺失 0；4 条流完成 |
| 旧五列 ECMP | `20260924-211000-ws06-legacy-fecmp` / `406472895` | 同上 | trace `abebc317…94a3cf`；19,388 条完成；FCT SHA `d712e769…54eb976` 与旧 ECMP 相同 |
| 旧五列 CONGA | `20260924-211500-ws06-legacy-conga` / `406831809` | 同上 | 19,388 条完成；FCT SHA `0c041fd0…c7667d3` 与旧 CONGA 相同 |
| 旧五列 LetFlow | `20260924-212200-ws06-legacy-letflow` / `297017927` | 同上 | 19,388 条完成；FCT SHA `abb659fe…eee0f` 与旧 LetFlow 相同 |
| 旧五列 ConWeave | `20260924-212900-ws06-legacy-conweave` / `182482077` | 同上 | 19,388 条完成；FCT SHA `b2334230…701255` 与旧 ConWeave 相同 |
| 导入 1280 拓扑四流 ECMP | `20260924-221000-ws06-byte-exact` / `409519521` | `dba99face4b026443220e4b73e655a86aecc1aca` | 400G；同一四流六列 trace；拓扑 SHA `74a6f715…15ad` 与参考一致；tag=1/2 各 2 流、入口包 132/18、缺失 0；4 条流完成 |

四次旧五列运行的拓扑 SHA 均为 `0dddc4f3ae673139b895ff2f875befe82b234cc48e325bd8a164d9cddedc12e2`，输入 SHA 均为 `abebc3170428aa22ebb13b15246243b806cb4f749bf4c9e6a80fb0a4a694a3cf`，日志均为 `tag=0 flows=19388`、源 ToR `tag=0 packets=842602`、`missing=0`。FCT 哈希逐模式匹配原 fidelity 实验，证明该固定条件下原四模式完成流输出未变；不构成性能排序。

## 4. 已形成的设计决策

- **Decision：**五列默认 `tag=0`，tag 是工作负载标签，作为 PacketTag 送到选路入口。**Rationale：**旧输入无须重写，后续模式可读取标签；当前四基线不按标签改变路径。**Alternatives：**直接将 tag=1/2 定义为可乱序/不可乱序或引入 MixHash；会提前决定 WS-07 的传输语义，故未采用。
- **Decision：**显式流文件限于版本化 `config/*.txt`；远程按提交 SHA 构建并快照输入。**Rationale：**避免每次暗中重新随机生成 trace，防止路径越界与结果不可复核。
- **Decision：**导入拓扑的 BDP 采用源码从真实链路计算的 30000B，保留校验；导入资产保留原字节。**Rationale：**避免手填值、换行差异造成可复现性矛盾。见 ADR-005 与溯源表。

## 5. 当前状态

WS-06 的输入兼容与轻量技术验证完成。代码和输入资产版本为 `feature/ws06-flow-tags@dba99face4b026443220e4b73e655a86aecc1aca`；本 Handoff 后续文档提交不改变该源码内容。2026-09-24 中国时间 22:17 核对，六列小/导入拓扑轻量探测与四基线均 `SUCCEEDED`，原始结果在远程 `/home/fnl/lzy/results/<实验ID>/` 和本机个人 fork 的忽略目录；未碰两份只读参考仓库或服务器既存工作树。

## 6. 未解决问题

- 必须在 WS-07 解决：tag 与逐包/按流选路的关系、两类共同的传输/PFC/接收重排语义、分类 FCT/重传等指标的原始记录。当前的源 ToR packet tag 计数只证明标签可见，不证明双轨运行或乱序能力。
- 四份完整 1280 节点 MoE trace 仅做格式静态核对；尚未做全量仿真或资源 pilot。现有四份总字节数不同，不能直接用作“只改变混合比例”的因果比较。
- 在导入混合延迟拓扑上，ConWeave 某些 ToR 间时序估计仍使用原统一 `one_hop_delay`；若 WS-07 用此拓扑做多算法对照，须先审计/修正，不可把本轮 ECMP 四流探测外推给所有模式。

## 7. 后续推荐动作

先由项目集成工作流依据本 Handoff、Git 和实验原始数据更新 `CURRENT_STATE.md`、`WORKSTREAMS.md`、`ROADMAP.md`、`CONFLICTS.md`。WS-07 再冻结两类流的选路、传输与重排契约，补按 tag 的完成流与异常计数，先做单类退化和双类共存的小测试；之后制作固定总负载、可重生且带独立 trace seed 的配对输入，才做 MixTax pilot。若无法保证逐包流正确完成及公平对照，应缩小研究主张；没有可重复跨类损害则不启动 WS-08 机制主线。

## 8. 与其他工作流的关系

继承 WS-04 的隔离远程实验链路与 WS-05 的四基线同 trace 锚点。四基线旧五列回归沿用其输入与指标边界；其短运行不能用于论文性能结论。本轮向 WS-07 交付稳定的输入标签通路、显式 trace 和可追溯实验，未交付 packet/flow 双轨选路、MixTax 或新算法。两个参考仓库只读。

## 9. CONTEXT SNAPSHOT

个人 fork `feature/ws06-flow-tags` 的代码/资产固定在 `dba99fa`；五/六列兼容，五列 tag=0，`--flow-file` 选择版本化 `config/*.txt`，PacketTag 可在源 ToR 选路入口读取并计数。32 主机六列与导入 1280 拓扑四流均完成 4/4；四种旧基线 19,388/19,388 完成，FCT 原始哈希各与原 fidelity 实验相同。完整 MoE 输入尚未全量运行；tag 不代表乱序能力；WS-07 须先定义公平的双轨及传输/重排语义，再谈 MixTax。
