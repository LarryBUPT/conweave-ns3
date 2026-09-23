# Workstream Handoff schema

Use this when the user requests a checkpoint or when a completed workstream is handed to project integration. Keep it concise enough for a fresh task to use without the original conversation.

1. **本对话目标：** original goal, changes in scope, workstream ID.
2. **已确认的项目事实：** repository/environment/mechanism facts with source paths, SHAs or experiment IDs; separate unverified claims.
3. **已完成工作：** ordered changes, reason and observed verification. Attribute user decisions separately from assistant/tool execution.
4. **已形成的设计决策：** Decision, Rationale, Alternatives considered and why rejected; link an ADR if durable.
5. **当前状态：** completed, partial, not started, blockers, repository branch and working tree at a dated observation.
6. **未解决问题：** must solve, can defer, research-only possibilities.
7. **后续推荐动作：** dependency order and go/no-go conditions; do not start the next workstream as part of a handoff-only request.
8. **与其他工作流的关系：** shared code/data, branch conflicts, conclusions that remain local.
9. **CONTEXT SNAPSHOT：** a short, standalone version of confirmed state, constraints, open work and key paths; no chat narrative.

For experimental claims, state whether evidence is a design, technical verification, pilot, or formal comparison. Do not turn an expected result into a measured effect.
