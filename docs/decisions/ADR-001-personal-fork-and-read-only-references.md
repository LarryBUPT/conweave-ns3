# ADR-001：个人 fork 承载科研代码

状态：Accepted。日期：2026-09-23。

## Decision

以 `conweave-project/conweave-ns3` 建立 `LarryBUPT/conweave-ns3` 个人 fork。只在个人 fork 的研究分支提交和推送科研改动；上游与 `maplerime/conweave-ns3` 只读。远程实验从个人 fork 的固定 SHA 建立独立副本。

## Rationale

原始 ConWeave 同时提供 ECMP、CONGA、LetFlow、ConWeave 四个可独立核验的基线。以它为起点可清楚区分自己的改动与 maplerime 的研究型改造。用户确认了这一 fork 选择及第三方仓库只读边界。

## Alternatives considered

- 直接以 maplerime fork 为个人起点：已有 MixHash/MoE 修改较多，基线和新增机制的归因更复杂。
- 在远程现有工作树直接改代码：会造成本地与服务器版本分叉，且已有未提交修改。
- 向参考仓库推送或提交 PR：不符合本项目授权范围。

## Consequences

源码版本以个人 fork commit 为准；原始数据按实验 ID 与 SHA 保存，不纳入 Git。工作流及保护机制见 `docs/REMOTE_EXPERIMENT_WORKFLOW.md`。本 ADR 不授权对参考仓库写入。
