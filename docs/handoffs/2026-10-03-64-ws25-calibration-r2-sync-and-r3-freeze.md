# Handoff 64：WS-25 远端 SHA 同步修复与 r3 计划冻结

1. **本阶段目标：** 延续 WS-25 的用户授权自动流程，在 r2 首格 build 请求遇到远端 Git 缓存缺少固定对象后修复同步路径，并按失败 ID 不复用规则冻结全新校准计划。
2. **r2 尝试与边界：** r2 首对 `20261003-083000-ws25-v1fix-cal07-fecmp` / `20261003-083000-ws25-v1fix-cal07-conweave` 在执行 `remote_worker.py build` 时失败，远端 `git cat-file -e a656104…^{commit}` 报对象不存在。远端查询确认两 ID 均无 `metadata.json`/实验目录；没有构建或仿真。尽管如此，两 ID 作为失败的 build 尝试永久保留，不重用。
3. **根因与修复：** 本地 HEAD `35a0eb86cce14577c5e7d18d9c62b275756328fb` 已推送到个人 fork，且包含固定输入 SHA `a656104d05c681f9b3a998b5ef4ce3e644558d02` 的祖先对象，但远端源码缓存未同步到该提交。已运行项目工作流 `python scripts/remote_experiment.py sync --repo-local .`，远端确认同步 fork commit `35a0eb86…`。实验仍严格固定在 `a656104…`，不因仅文档/runner 后续提交而漂移。
4. **r3 冻结计划：** 对四个需求 seed `20262505–20262508` 的 b192 输入，六个模式配对主格与四个 ClassReserve diag-on 控制格，共 28 格全新 ID；输入 SHA、拓扑 SHA、参数、顺序与所有 ID 见版本化[r3 计划](../research/evidence/ws25-v1fix-calibration-plan-r3.json)。runner 使用独立 `results/*-r3` 计划、收据及验证文件名；远端每个新格开跑前会核对 trace 普通文件身份与 SHA-256。旧 r1/r2 ID 均不在 r3 计划中。
5. **执行器修订和检查：** runner 的运行态轮询已改为约 30 分钟一次精简状态读取，不再每五分钟多做一次 SSH 资源审计；seed block 前后仍按计划做资源与并发门槛检查，远端 watcher 持续采集每格资源样本。`py_compile`、`scripts/run_ws25_v1fix_calibration.py plan`、28 ID 唯一性与 `git diff --check` 均需在提交前再次确认。
6. **当前状态：** r3 尚未 build 或仿真。r2 同步已成功；实际监督模型 GPT-6 Luna High，固定 cap=2。启动前再次运行远端 `check`/审计，确认无活动仿真、负载/内存/磁盘达标后，执行 `python scripts/run_ws25_v1fix_calibration.py run`。控制器遇到任意格错误即停后续新格并保留身份。
7. **未完成项：** r3 28 格的 build、仿真、raw 回传和逐格验收，校准分析，0/64/128 档约束，正式样本量和双侧数值门槛冻结，最终矩阵与论文稿均待办。校准只描述四个独立需求 seed 的配对差，不作正式收益或 NO-GO 结论；WS-25 保持 ACTIVE。
8. **研究关系：** ClassReserve v1 修正版仍是同一候选版本和同一算法 SHA `c84108b…`；r1 的 trace 包装错误和 r2 的远端同步错误都是执行身份/环境问题，不是机制失效。修正参考已看过的 seed01–04，因此校准只用 seed05–08。WS-21 状态反馈/心跳仍在第一篇投稿后第二课题门槛，历史 WS-10/11/12 NO-GO 不变。
9. **CONTEXT SNAPSHOT：** correctness raw 11/11；r1 两格在仿真启动前因源 SHA 不含 trace 失败；r2 首两格 build 请求因远端对象缺失失败且无远端实验目录。远端现已同步到包含 `a656104…` 的推送提交 `35a0eb8…`。r3 28 个 ID、哈希和执行顺序已冻结，runner 已采用半小时监督。当前模型 Luna High；远端预检通过并推送后自动启动，28 格全部终态回传后切 Sol High 复核分析。
