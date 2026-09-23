# Handoff 02：Research Discovery

来源：Codex 对话 `01a0ca49-1841-7952-bdaf-b16daa10f5d8`，标题「Research Discovery」。由集成任务结合对话及当前研究文档整理。日期：2026-09-24。

## 1. 本对话目标

初始目标是从开题报告、论文和 ConWeave 代码中筛出可证伪、可在 NS-3 验证的小论文 idea。用户随后明确：**负载均衡机制是研究中心，包级与流级共存是应用场景**。后续又要求借鉴 MixHash 的选路骨架，并迁入相关流量输入资产。

## 2. 已确认的项目事实

初轮完成 15 篇相关本地论文的矩阵、8 个 idea 与反向检索。FAMG、APS、FLB 等工作压缩了“按类别选粒度/隔离路径”的独立新颖性。maplerime `main@470c580` 的 MixHash 模式对两类数据均做包级哈希；tag 不代表现成双轨选路。四份迁入流量文件为六列，个人 fork 当前只读五列且未提供显式 flow file 参数。原文件增加背景流时总字节数也增加。

## 3. 已完成工作

研究记录位于论文项目 `docs/research/01`–`08` 和 `11-mixhash-inspired-lb-only-discovery.md`，含候选、近邻、审稿挑战、实验设计和否证门槛。个人 fork 的 `feature/mixed-flow-traces@ccdbd78` 已迁入四份 MoE/背景流文件、拓扑与生成脚本，逐文件哈希记录在 `docs/research/mixed-flow-trace-provenance.md`；未迁入 MixHash 机制，未运行混合性能实验。

## 4. 已形成的设计决策

**Decision：**先测 MixTax，再有条件评估 HarmGate/GuardHash。**Rationale：**须证明混合场景造成独特损害，且新规则优于强基线。**Alternatives：**直接实现开题的分类与阈值切换，因近邻重合降级；PartialWeave 作为偏离主线的独立备选；AnchorHash、BorrowHash 保留次选/储备，PhaseSalt 更适合消融。详见 `docs/decisions/ADR-002-mixed-granularity-research-question.md`。

## 5. 当前状态

文献发现与算法草案已成文；输入资产已迁入并推送到个人 fork。六列读取、标签传播、真正双轨模式、固定总负载 trace、MixTax 和 GuardHash 性能实验均未完成。没有论文性能结论。

## 6. 未解决问题

必须解决：tag 与传输/乱序语义的明确契约；同轨迹、同总负载的跨类损害能否复现；强基线是否已有同等效果。可延后：反馈延迟、错标、路径不对称等边界实验。研究方向保留：PartialWeave、FreshRoute、BoundaryShare 等独立备选。

## 7. 后续推荐动作

先做六列输入及 tag 通路、旧基线回归，再做双轨基线与 MixTax；仅在 go 门槛通过后实现 GuardHash。对应任务见 `docs/project-state/ROADMAP.md`。

## 8. 与其他工作流的关系

依赖参考仓库审计确定代码事实，依赖远程实验链路与 baseline 审计保证可复现；混合分支应从个人 fork 继续。旧初轮排序已被用户明确的新研究中心修订，不能混用成同时有效的首选。

## 9. CONTEXT SNAPSHOT

研究中心＝包/流共存下的负载均衡。MixTax 是先决现象实验，GuardHash/HarmGate 是有条件机制草案。个人 fork 已迁入六列输入但尚不能运行；无新算法或正式性能结果。先完成输入与双轨语义，再判断跨类损害和强基线差异。
