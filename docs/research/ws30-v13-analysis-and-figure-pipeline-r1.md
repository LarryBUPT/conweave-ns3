# WS-30 v13 待运行矩阵的本地分析与图表管线

日期：2026 年 10 月 26 日。本节点完成读取未来 raw 的分析和绘图入口，实际上下文为 GPT-6.1 Sol / Medium。没有远端访问、推送、部署、授权收据或仿真。主稿、论文版本和回复文件未改。

[分析契约](evidence/ws30-v13-analysis-contract-r1.json)绑定原关闭的执行契约、200 个性能格、4 个观测资格格及历史来源索引；[准备收据](evidence/ws30-v13-analysis-pipeline-preparation-r1.json)记录实际本地验证。现有目标 raw 全部缺失，因此本节点没有生成正式估计、置信区间或结果图。

## 1. 统计单位与直接配对

| 组别 | 固定单位 | 分析口径 |
| --- | --- | --- |
| 新建 QP 五臂补充比较 | 24 份已揭盲独立需求，每份五臂，120 格 | 每需求直接配对；不是新的盲确认 |
| 历史 DRILL 补跑 A/B | 两组各 24 份历史需求，共 48 格 | 各自与同需求历史 ECMP 配对；先核全部 48 格与原 DRILL FCT 哈希一致 |
| 持续负载 pilot | 2 个独立需求 seed × 2 种时序 × 8 方法，32 格 | 分时序给逐 seed 结果；8 轮与两时序均为同需求内重复 |
| ConWeave 观测资格 | 两对 off/on，共 4 格 | 两对 FCT 一致后，才开放持续负载性能配对 |

同输入的方法变化定义为 `100 × (candidate / reference − 1)`，先逐需求计算再取需求中位数，不使用合并流分母或总体均值之比。五臂预设 Q12/R12/U12/DRILL 对 ECMP，以及 R12/U12/DRILL 对 Q12；持续负载另包含 CONGA、LetFlow、ConWeave 对 ECMP 和 ConWeave 对 Q12。全部预设比较均输出，不按结果筛选。

完整的 24 需求比较沿用固定 seed 20,263,003 的 10,000 次需求级 bootstrap，输出中位变化的名义 95% 百分位区间。两侧指标和各比较使用相同的重采样索引。区间未经多重比较调整，不输出 p 值、星号或自动“通过”判定。任一配对需求缺失时仍保留全部预设行，且不生成该比较的推断区间。两需求 pilot 只给全部点、中位数与范围，不计算推断区间，也不将四种 seed/时序条件或 16 个轮次当独立样本。

## 2. 身份、字节和缺失处理

[分析脚本](../../scripts/analyze_ws30_v13_pending.py)先匹配源/目的、源/目的端口、尺寸和原始需求时刻，额外保留 trace 的标签和优先级。每条 FCT 仅允许与一个输入身份匹配，时间容差为 1 ns；检查每条完成、总完成数和 payload 总字节，记录输入身份指纹及 metadata/config/trace/topology/FCT/log 哈希。新格还调用已有严格验收器，核对各自固定 SHA、算法、schema 3、模拟/需求 seed、公共参数、观测和资源收据。

MISSING、LOCAL_PARTIAL、BUILDING、RUNNING、FAILED、BUILD_FAILED、INVALID 等状态逐格保留。失败格有可读取的匹配 raw 时记录已完成身份/字节及完成比例；读不到时标明原因，不补零。不以已完成流的尾部替代完整输入指标，不用超时时间填补 FCT。缺失格与资格未通过的比较均保留原因，不能悄悄剔除后形成“完整”样本。

历史 ECMP 与原 DRILL 的来源从冻结索引解析，保留原 ID、源码、输入、FCT、metadata 和 config 哈希。只有相应新补跑出现后才读取其历史 ECMP anchor；现有历史 raw 不会单独生成新的实验结果。两组历史样本与新建 QP 的 24 份需求不合并。旧 46 格也不会进入这些正式统计组。

当前快照明确列出性能格 200/200 MISSING、观测资格 4/4 MISSING；260 条预设逐需求比较分别为 168 条成员缺失、48 条历史哈希资格未完成、44 条观测资格未完成。`source-map.json` 包含 200 个目标、96 个历史参照及 4 个资格格的 300 条来源定位；它是来源清单，不是 300 个新样本。

## 3. 批次、原/新批尾及逐输入分布

主结果为消息从原始需求到完整完成的跨度和全部背景 FCT 的线性插值 P99。持续负载还逐轮使用该轮自己的需求原点，并保留八轮整体跨度。32 条背景的全部身份配对值、P50/P95/P99、最大值和完成比例都输出；有限的 P99 分辨率不被隐藏。

设同需求的消息完成值为 R、C，原参照批尾为 i。管线逐条核对：

```text
max(C) − max(R) = [C(i) − R(i)] + [max(C) − C(i)]
```

前项为候选在原批尾身份上的变化，后项为替换批尾造成的非负 gap。原/新身份、全部最大值并列身份、两种方法在两身份上的值均落盘；并列时用确定性的身份顺序选代表。该等式是 max 的代数分解，不是因果中介。持续负载同时输出各轮与整体的分解。

ECMP 固定 top-k 使用参照 ECMP 的 FCT 排序，k=1/4/16/64/256，之后比较同一组流身份，不用候选结果重新选样本。逐输入分布来自每条相同身份的 FCT 变化，另外单列两方法的边际分位数，不把两条排序曲线的差当作逐流配对效果。全部标签 1/2 的逐流配对以 gzip CSV 保存；其余标签仍参与完整输入守恒。

同一持续需求跨两时序的响应另输出配对对数比之差，形成每 seed 的时间条件交互描述。它仍只有两个独立 seed，不增加统计重复数。

## 4. 状态与恢复开销

逐标签保留 gap、低于期望序号、带/不带 SACK 的反馈、CNP、实际重传包与 payload 字节、超时。重传比例的分母为对应标签的原始 payload 字节，不是全链路 wire 字节；gap 不等于丢包，全部 0xFD 不等于恢复 NACK，CNP 也不能单独证明真实 ECN 拥塞。缺少观测字段为未知，已观测到的 0 才保留为 0。

缓存逐交换机输出当前/峰值条目、命中与 miss，不把条目数写成字节内存。图中若汇总各交换机的峰值，会明确它不是同一时刻的网络峰值。ConWeave 单列原生 reroute/入 VOQ/flush 计数、被动阶段事件、实际公共端口变化、反馈年龄、单 VOQ 的已观测最大包数及日志字节。VOQ 包数不当作 MMU 物理占用，日志量不当作协议线上开销。

年龄按事件解释：reply_rx 为匹配请求 RTT，rx_mark/rx_buffer 为源时间戳年龄，flush 为首次缓冲至释放的等待。未匹配年龄保留不可用数量，不填 0；各事件样本数、P50/P99 和最大值独立输出。没有新的状态传播或硬件成本结论。

## 5. 图表入口与论文呈现

[Python 绘图脚本](../../scripts/plot_ws30_v13_pending.py)消费分析输出，生成双侧变化散点、逐需求内配对流分布、原/替换批尾分解、实际重传代价、可用缓存条目和持续负载逐轮轨迹。图内只用 ECMP、DRILL、CONGA、LetFlow、ConWeave 和描述性的双候选方法名称，不出现工作流编号；原实验 ID 和内部方法键保留在配套来源文件中。

散点每点对应一份配对需求。分布图竖线为同一需求内逐流变化的第 10～90 百分位，点为中位数，不是需求级置信区间；这一说明保存在每图的 notes/source 中，后续稿件图注必须带上。持续负载的轮次轨迹明确 n=2。默认拒绝不完整组绘图；显式选择 partial descriptive 后才可画，并标记实际/预期 n。

正式图同时导出可编辑 SVG、PDF、PNG 预览及点源 JSON，并调用 Python 的 PDF 字号与碰撞检查。单面板 alignment 标为不适用；自动检查后仍保留最终尺寸人工视觉复核为 PENDING。当前无目标 raw，未画占位效果图、未对旧技术格画正式图，也未声称渲染 QA 已通过。Python matplotlib 3.11.2 和 PyMuPDF 可用。

## 6. 使用入口与输出

以下命令均为本地处理示例，`SESSION_JSONL` 需换为真实 GPT-6.1 Sol Medium 分析会话文件，`FIGURE_QA_SCRIPTS` 为已安装的图表 QA 工具目录。

```text
python scripts/analyze_ws30_v13_pending.py analyze --out results/analysis-snapshot-NEW --session-file SESSION_JSONL
python scripts/plot_ws30_v13_pending.py results/analysis-snapshot-NEW --out results/figures-snapshot-NEW --session-file SESSION_JSONL --qa-tools FIGURE_QA_SCRIPTS
```

每次输出必须是工作树内的新目录，已有目录拒绝覆盖。回传新 raw 后重跑到新目录；本地 MISSING 只表示该快照未见本地结果，不推断远端状态。

| 输出 | 内容 |
| --- | --- |
| cell-status / qualification-status | 全部预设 ID 与失败、缺失、资格状态 |
| source-map / run-provenance | 来源定位、源码/输入/raw 哈希、分析脚本版本 |
| cell-metrics / paired-endpoints / summary | 逐输入指标、两侧直接配对与需求级汇总 |
| paired-flows.csv.gz / per-input-distributions | 全身份配对点和逐需求分布 |
| tail-decomposition / fixed-ecmp-topk | 原/新批尾及固定 ECMP 身份分析 |
| all-background-pairs / round-pairs / timing-interactions | 全部背景点、各轮和同 seed 的时序响应 |
| costs / recovery-costs / cache-state-entries / conweave-event-ages | 观测可用性、状态与恢复代价 |
| figure-manifest 与逐图 source / QA | 论文显示名、点源、自动 QA 和待完成视觉复核 |

## 7. 本节点验证和剩余工作

只使用五个已有技术 raw 核对解析，共 840 条 FCT；身份/字节、主指标和恢复计数与冻结独立分析一致，并在同一技术输入上检查批尾分解恒等式。四份持续 trace 只核对结构：每份 8 轮、每轮 2,048 条消息，两时序的身份和总字节一致。旧技术格没有被算作正式独立需求，也没有生成新性能结果。

目标空快照端到端输出了缺失状态、空推断区间和 0 张图，未触发任何远端调用。后续仍须取得并验收新 raw、通过观测资格与历史回归，检查实际运行数据下的解析/统计结果，并完成真实图形的自动 QA、最终尺寸视觉检查和主稿整合。管线准备完成不代表这些事项完成。

节点参考复核从候选 README/reading-log 进入，沿用 IRN 正式版对 gap/SACK/实际重传的区分，以及 SeqBalance v1 对完整请求和 QP 生命周期的区分；只借鉴计量边界，没有迁移作者机制、性能或硬件结论。[复核记录](evidence/ws30-v13-analysis-reference-review-r1.json)保存版本和文件哈希。WS-30 仍为 ACTIVE，拟先正式首四格 → 余 164 格，再新源技术/生命周期和 W5；本节点没有执行放行。
