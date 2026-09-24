# Handoff 07：ANT 项目经验与机制筛选

来源：Codex 任务 `01a0d48c-8a70-73b0-bffa-67678d61b059`「ANT项目经验」，两轮对话均已完成。交接日期：2026-09-25（中国时间）。本 Handoff 汇入 WS-02 Research Discovery，记录研究选择与静态输入证据；不构成新机制实现或性能结论。

## 1. 本对话目标

先按聊天日期梳理 `E:\研\毕业论文\screenshot\` 中 9 张 ANT 项目长截图，并与只读 `maplerime/conweave-ns3` 的提交演化对照。随后用户明确：聊天背景与本项目一致，应借鉴流量分析和机制迭代以减少冗余试错；研究中心仍是在相同背景下实现另一负载均衡机制，须从仓库已有方案中筛选，并以 baseline 审计为前提。

## 2. 已确认的项目事实

- 论文项目 `docs/research/11-screenshot-research-iteration-analysis.md` 展示的是讨论、源码提交与阶段报告的迭代；当时的性能表格未在本项目按原始数据独立复算。其反复修正的变量包括流量对象与时序、拓扑、IRN/inflight 窗口、PFC 阈值和统计口径。
- 论文项目 `docs/research/evidence/moe-static-profile.json` 由 `scripts/profile_moe_trace.py` 从个人 fork 的导入文件生成：拓扑有 4 个互不连通的 rail，而四份 MoE/背景 trace 均只使用 rail 0；MoE 为同时在 `2.000s` 启动的 16,384 条 8 KiB 流，文件名中的 `8round` 不提供轮次字段；背景流为额外的 0/64/128/192 条 8 MiB 流，总提供字节随档位上升。MoE 与背景主机集合不交叠，部分 ToR 集合交叠。
- 旧 `run.py` 的 FCT 分析从 `2.005s` 起筛选，本机 `scripts/analyze_result.py` 也用同一开始窗口；它们会排除这四份 `2.000s` 启动的目标流。原始 FCT 非空不保证默认汇总有效。
- WS-06 只证明五/六列输入与 tag 到源 ToR 的技术通路；完整 MoE、双轨及新机制实验尚未完成。四种旧 baseline 的最小运行不能用于性能排序。

## 3. 已完成工作

用户决定研究范围与筛选依据；以下取证、静态分析和文档由该任务执行。第一轮写出论文项目 `docs/research/11-screenshot-research-iteration-analysis.md`，按 2026-03-18 至 2026-06-04 的聊天日期复原“异常观察—修正场景与口径—排查传输混杂—简化选路—仿真原型”的过程。第二轮写出 `docs/research/12-screenshot-lessons-and-mechanism-selection.md`、画像脚本及 JSON，并修正旧 `11-mixhash-inspired-lb-only-discovery.md` 对个人 fork 仍只支持五列的过期说法。

2026-09-25 集成核对：个人 fork `feature/ws06-flow-tags` 本地与 `origin` 均为 `0a8d28ce89e8886b597e220cc3ff308523dc3c28`，工作树干净；重跑静态画像脚本后 JSON SHA-256 仍为 `373310A75C36B67E2F08A84A4336380D170E0E82C1C9EDED5C3A737D35F2D344`。源码再次核对了 `run.py` 和 `scripts/analyze_result.py` 的 `2.005s` 起始窗口。这些是静态证据和分析链路检查，未启动远程仿真。

## 4. 已形成的设计决策

**Decision：**保留 HarmGate 的跨类损害问题，以 GuardHash 的本地双候选规则作为唯一优先、**有条件**的机制原型；先测“背景增加是否额外伤害 MoE”，同时报告背景侧代价。详见 [ADR-006](../decisions/ADR-006-conditional-guardhash-selection.md)。**Rationale：**截图最先追问 MoE 小流受背景影响，而旧 GuardHash 草案主要把背景长流写成受害者；统一的双侧指标比预设单一受害方向更可证伪。**Alternatives：**Inflex 多跳 probe、PhaseSalt、BorrowHash 和完整 MixHash 传输/重排改造暂缓；AnchorHash 留作简单基线或消融。该选择不是用户批准立即实现，也不是效果已测得。

## 5. 当前状态

ANT 对话的截图复盘、已有候选筛选和静态画像已交付；对话内没有尚待回答的请求。报告 12 是当前机制筛选入口，旧报告 11 保留历史方案和近邻风险。论文项目根目录未纳入 Git；本 Handoff 与 ADR 在个人 fork 中保留可版本化的结论索引，根目录完整研究材料仍由本地路径提供。正式代码实现、完整 MoE 运行和机制性能比较均尚未发生，属于后续 WS-07/WS-08。

## 6. 未解决问题

- WS-07 必须先建立两类共同的传输/PFC/乱序语义、MoE 专用的按 tag 输入/完成/未完成与同步批次指标，再验证单类及双类正确性。没有轮次 ID，不能把合成批次完成时间称作已观测的“八轮 job CCT”。
- 当前四份 trace 的背景字节数增加，不能单独归因于混合比例；主实验需固定总提供字节、不可变 trace 和独立 trace seed。若使用导入混合延迟拓扑比较 ConWeave，须先核查其统一 `one_hop_delay` 假设。
- GuardHash v0 的 per-port、per-tag 排队字节信号尚未实现或校验守恒；类别信号是否优于普通短队列二选一完全待实验。硬件实现成本、重排内存与真实 RNIC 行为不在当前证据范围。

## 7. 后续推荐动作

WS-07 先补 MoE 分组分析入口并冻结共同传输语义；用 32 主机和导入拓扑四流检查，再评估完整 64 背景 trace 的资源 pilot。在相同 MoE 子 trace 下，配对比较 packet/flow × 背景 0/64，对 MoE 和背景两侧分别量化损害。只有跨类损害稳定、可解释且统计口径正确，WS-08 才实现 GuardHash v0，并与普通本地短队列二选一及其他强基线比较；无损害或无类别信号增量即停止机制主张。

## 8. 与其他工作流的关系

本交接补充 WS-02 的研究方向，依赖 WS-05 的 baseline 证据边界和 WS-06 的输入/tag 底座，为 WS-07 的诊断与 WS-08 的条件门槛提供取舍依据。它不改变已完成的 WS-06 代码，也不让旧截图中的仿真数字成为本论文的结果。ANT 任务可在集成后归档；归档不代表 WS-07/WS-08 已完成。

## 9. CONTEXT SNAPSHOT

最新筛选：HarmGate 问题 + GuardHash 本地双候选 v0，条件启动，首看背景对 MoE 的额外伤害并同时报告背景代价。静态输入事实：四 rail 只用 rail 0、MoE 16,384 条流同刻启动、背景 0/64/128/192 条增加总字节、无轮次字段。默认 FCT `2.005s` 窗口会漏掉 `2.000s` 目标流。尚无完整 MoE 或新机制性能实验；下一步为 WS-07 的共同语义、分组观测和双向 MixTax 诊断。
