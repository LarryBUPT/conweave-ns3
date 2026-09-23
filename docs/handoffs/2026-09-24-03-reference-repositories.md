# Handoff 03：对比mixhash与conweave

来源：Codex 对话 `01a0cb67-1645-77b1-89c2-7285ddd1e6d4`，标题「对比mixhash与conweave」。由集成任务整理。日期：2026-09-24。

## 1. 本对话目标

先在论文项目内独立克隆原始 ConWeave，随后按修改时间分析 maplerime fork 相比上游的机制演化、端到端调用链和研发工作流。用户明确限制：克隆上游时只克隆，不在该对话改源码或论文材料。

## 2. 已确认的项目事实

原始参考克隆位于论文项目 `workspace/conweave-ns3`，当前 `main@236a801`；maplerime 参考克隆在 `workspace/maplerime-conweave-ns3`，当前 `main@470c580`。两者本地工作树干净、push URL 被拒绝。maplerime `main` 相对原始基线有 36 个独有提交；报告还统计了多分支的研究演化，不能把实验分支能力都算进 `main`。

## 3. 已完成工作

原始 ConWeave 已独立克隆。论文项目 `docs/research/09-maplerime-conweave-fork-evolution-report.md` 梳理了 Hybrid/FlowSlice、MoE、Inflex、NECMP、MixHash、重排缓存与 ToR-BDP 的时间线、分支合并状态和 trace→报文→选路→重排→分析链路。报告为静态源码取证，未在此对话复现性能。

## 4. 已形成的设计决策

**Decision：**把两个仓库都作为只读参考；以提交和实际代码路径区分主线与分支原型。**Rationale：**文档/注释可能滞后，分支未合并的能力不能当作当前 `main` 功能。**Alternatives：**只看 `main` 或只按 README 归纳，都会漏掉研究迭代和版本漂移。

## 5. 当前状态

克隆和分析报告已完成；未修改两份参考源码，也未向它们写远程状态。个人 fork 的创建与实验链路属于另一工作流。

## 6. 未解决问题

必须解决：若移植某项 MixHash 机制，先固定精确来源 commit 并核实报文头、序号和重排边界。可延后：逐分支的动态复现。研究方向保留：报告指出的正确性风险需在实际采用该代码时逐项核验。

## 7. 后续推荐动作

新实现只在个人 fork 进行，优先移植或重写最小必要的输入/选路部分；不要把 maplerime 的重排与传输改动隐式绑定到新算法。

## 8. 与其他工作流的关系

为 Research Discovery 和输入资产迁入提供来源证据；与 baseline 工作流之间保持“参考实现”和“个人实验基线”的边界。

## 9. CONTEXT SNAPSHOT

两个参考仓库已克隆且只读；maplerime 演化报告已完成。其 `main`、未合并分支和论文/注释不能混称。此对话没有性能复现或参考仓库写入。
