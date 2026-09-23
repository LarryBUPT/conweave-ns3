---
name: conweave-project-state
description: Maintain this ConWeave research project's cross-conversation handoffs, current state, decisions, and workstream coordination. Use when asked for a checkpoint, project integration, state update, or next-workstream handoff; ordinary code or experiment tasks do not need it.
---

# ConWeave project state

This skill belongs to the `LarryBUPT/conweave-ns3` personal fork. It organizes project memory; it does not authorize changes to reference repositories, remote experiments, or thread management by itself.

## Bootstrap

1. Follow `AGENTS.md`: read `docs/REMOTE_EXPERIMENT_WORKFLOW.md` first. For baseline, source-path, or metric claims, then read `docs/research/10-baseline-fidelity-and-dataflow-audit.md`.
2. Read `docs/project-state/CURRENT_STATE.md` and the relevant rows in `WORKSTREAMS.md`; open only the ADRs and Handoffs needed for the task. Treat state files as an index that may be stale. Verify Git refs, source code, experiment metadata and raw data before repeating time-sensitive claims.

## Choose the operation

- **Checkpoint a workstream:** record a compact Handoff using [the nine-section schema](references/handoff-schema.md). Distinguish user decisions, assistant/tool actions, observed results, plans and unverified claims. Include source task ID/title and concrete file, SHA or experiment ID evidence. Do not modify algorithm code merely to produce a checkpoint.
- **Integrate handoffs:** compare new Handoffs with current Git/data and existing state. Deduplicate conclusions; record contradictions, outdated assumptions and dependencies in `CONFLICTS.md`. Update `CURRENT_STATE.md`, `WORKSTREAMS.md` and `ROADMAP.md` to reflect only verified or explicitly labelled planned work. Add an ADR only for a consequential decision that future work might otherwise reopen.
- **Start or resume a workstream:** identify its current predecessor and go/no-go gate from `WORKSTREAMS.md` and `ROADMAP.md`; provide the new task with a short context snapshot and links. Keep implementation and experiments in that workstream. Return a Handoff when its stage ends.
- **Close a task:** integrate its Handoff before treating the task as frozen. Archive or create Codex tasks only when requested by the user; archiving a conversation never marks its research question complete.

## Evidence and update rules

- Actual source plus experiment-ID raw data outrank chat summaries. A successful smoke/fidelity run is not a formal performance comparison. ConWeave VOQ is not MMU physical queue occupancy.
- Keep one current status for each workstream; use `COMPLETE FOR ...`, `ACTIVE`, `PLANNED`, `CONDITIONAL`, or `BLOCKED` with a clear scope and dependency. Avoid timeless claims such as “current HEAD is ...” without an observation date.
- Keep stable behavior and safety constraints in `AGENTS.md`/the remote workflow, current stage in `CURRENT_STATE.md`, task dependencies in `WORKSTREAMS.md`, durable rationale in ADRs, and temporary detail in Handoffs. Do not paste conversation transcripts into the state files.
- The paper-project root is not a Git repository. These canonical state artifacts are versioned in the personal fork; `E:\研\毕业论文\AGENTS.md` links to them. Never write to the two read-only reference remotes.

## Finish

Check internal links, document dates, Git status and the claims affected by the update. Report which files changed, what evidence was verified, and which questions remain open. The loop is **Bootstrap → Work → Checkpoint → Integrate → next workstream**.
