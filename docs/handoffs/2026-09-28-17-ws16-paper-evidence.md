# Handoff 17：WS-16 论文证据与复现收束

日期：2026-09-28。来源任务：`WS-16 论文证据与复现收束`（由 ConWeave Research · Integration 的交接启动；本任务 ID 未在本地工作材料中记录）。状态：**证据索引和论文边界材料完成；待导师确认论文范围**。

## 1. 本对话目标

承接 WS-15 门槛 no-go，以既有固定源码和原始实验 ID 整理 WS-10/11/12 各自正式负结果、WS-13 诊断与不完整压力格、WS-14 单输入停止、WS-15 未开矩阵；提供主张—源码—输入—raw—分析—图表的复现入口，并对照开题报告检查未验证部分。用户要求原则上不扩大仿真。

## 2. 已确认的项目事实

起点个人 fork `feature/ws15-gate-review@53b56b3d3f271356c98afdcad8779183a3fff528`，本地/`origin` 均包含该提交且工作树干净。新分支 `feature/ws16-paper-evidence` 从此 SHA 建立。工作规则与 baseline 审计先行读取；WS-15 Handoff 16 和门槛报告已对照。WS-10/11/12 固定仿真源码分别为 `aa778ac523bc0319999395dd3cf8085b41e73a98`、`208fcee4c541da9b24ed26792b32ae681a30977f`、`adae7956e3fc874d9237e62a6ea8e32b26d5def1`。WS-14 为 `73401ce3ac0a5c27bf0e3e0636c9337056d9355e`。真实证据等级详见[总报告](../research/ws16-paper-evidence-and-reproduction.md)。

## 3. 已完成工作

助手/工具在本地重新执行 `verify_ws10_formal.py`、`verify_ws11_formal.py`、`verify_ws12_formal.py`、`run_ws14_small.py verify` 和 `analyze_ws13_calibration.py`，退出码均为 0，分别返回正式 30/40/120 格、WS-14 七格与三条独立需求六格的既有结论。新增[`build_ws16_evidence_index.py`](../../scripts/build_ws16_evidence_index.py)逐一读取 216 个实验 ID 的元数据及 trace/拓扑/FCT 原始文件并验证 SHA，产出[CSV](../research/evidence/ws16-experiment-index.csv)。新增[论文证据与复现报告](../research/ws16-paper-evidence-and-reproduction.md)，记录主张映射、图表和原始数据回取步骤，核对开题报告原文 SHA。没有 SSH 或远程仿真，没有更改算法或历史结果。

## 4. 已形成的设计决策

**决定：以现有正式 no-go 和证据缺口完成论文材料，不为叙事补跑仿真。**理由是 WS-15 未有合格的新单机制，旧实验各自冻结且已有足够原始数据解释条件性双侧结果。事后补格、重判 5% 或把校准/顺序置换升级为独立验证均会改变证据含义。替代的前瞻性新机制实验仅能在独立问题、观测、双侧小样与正式契约事前冻结后另立工作流。

## 5. 当前状态

WS-16 的索引、论文口径、复现步骤和范围差异已写入 fork；机器索引共 216 个唯一 ID，WS-15 没有新 ID。WS-13 压力 11 格旧 `SUCCEEDED` 元数据与 13/16 实际完成数的冲突已明确，不作为正式性能格。当前分支为 `feature/ws16-paper-evidence`；最终提交/远端 SHA 以本交接后的 Git 核验为准。

## 6. 未解决问题

需导师决定论文创新点是否以交换机侧原型和双侧负结果重述；开题报告的发送端 QP/DSCP/长度自动分类、端侧逐包→flowlet 降级、INT/Δq 反馈、接收协同重排、硬件/线上部署均无本阶段验证。用户暂无可核验业务 SLO 和真实 MoE job 轮次；物理 MMU 总占用、可靠独立逐 QP timeout、逐包 ECN 与即时 RNIC 速率仍缺。独立需求上的候选机制效果未知。

## 7. 后续推荐动作

先请导师确认结果主线、题目/创新点与是否必须补端侧/硬件范围，再据此写论文结果和局限章节；如需新效果主张，另立前瞻性契约与新实验，不重判 WS-10/11/12。若仅复现已有结果，按总报告下载同 ID 原始目录并运行核验脚本。

## 8. 与其他工作流的关系

WS-10 固定总字节主档 no-go、WS-11 全量输入复合 no-go、WS-12 四策略双侧 no-go 均保持原判。WS-13 是诊断/校准/技术 pilot，WS-14 是单输入停止小样，WS-15 是未开矩阵的门槛决定；三者均不转成正式机制收益。旧四模式 fidelity 最小运行不参加性能排名。

## 9. CONTEXT SNAPSHOT

WS-16 在 `feature/ws16-paper-evidence` 建立可重算的 216 ID 原始证据 CSV 和[总报告](../research/ws16-paper-evidence-and-reproduction.md)。WS-10/11/12 的 30/40/120 正式格各自按预注册 no-go；WS-13 压力 IRN+PFC 11 格实际 13/16，不可作正式性能格；WS-14 GuardHash 单输入 0/192 七格触发停止；WS-15 无新实验 ID、确认性矩阵关闭。原始数据位于 Git 忽略的 `results/<ID>/`。开题目标中的端侧分类/降级、INT Δq、接收协同重排及硬件/业务 SLO 尚未验证。下一步是导师确认论文范围，再写正文，不事后重判旧门槛。
