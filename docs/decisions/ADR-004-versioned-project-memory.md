# ADR-004：把跨对话状态放进版本化项目文件

状态：Accepted。日期：2026-09-24。

## Decision

个人 fork 的 `docs/project-state/CURRENT_STATE.md` 是跨对话状态入口，`WORKSTREAMS.md` 记录任务与依赖，`docs/decisions/ADR-*` 留存关键取舍，`docs/handoffs/` 保存阶段交接。项目 Skill 规定 Bootstrap → Work → Checkpoint → Integrate；`AGENTS.md` 仅存稳定规则与入口。

## Rationale

五个对话分别掌握部分历史，单靠聊天上下文会在分叉、压缩和归档后丢失项目状态。论文项目根目录尚未纳入 Git；将这组文件放在个人 fork，才能随 Git 版本化并供新的工作流读取。

## Alternatives considered

- 把所有状态塞进 `AGENTS.md`：阶段事实会频繁变化，导致稳定规则膨胀并过期。
- 把五个对话全文复制到新对话：重复、矛盾与过期决策难以识别。
- 只在未版本化的论文项目根目录维护状态：无法随个人 fork 保存和同步。

## Consequences

状态文件是导航和审计索引，实际源码与对应实验 ID 的原始数据仍是最终证据。每次集成先对照实时 Git、文件和数据，再更新状态；不能因 Handoff 的叙述覆盖更强的实测证据。原对话保留供追溯，不再充当唯一状态来源。
