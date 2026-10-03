# Handoff 68：WS-25 diag CLI 参数修复与 r4 计划

1. **目标：** 按失败停线规则处理 r3 的 seed07 ClassReserve diag 控制格启动失败，保存失败身份，修正 runner 参数并冻结恢复计划。
2. **已通过的主格：** seed20262507 的 ECMP、ConWeave、LetFlow、DRILL、CONGA、ClassReserve 六个主格均已 SUCCEEDED 并通过逐格 verifier（6/28）。每格 MoE 16,384/16,384、背景 192/192 完成；最大树 RSS `4562.313 MiB`。这些 ID/raw 保持原样，不重跑。
3. **失败 ID 与证据：** `20261003-100000-ws25-v1fix-cal07-classreserve-diag` 远端 metadata 仍是 `BUILT`，其 `run` CLI 在 ns-3 启动前因参数错误拒绝：runner 只传了 `--ws25-diag`，而 `remote_experiment.py`/`run.py` 定义要求 `--ws25-diag {0,1}`。该 ID 没有仿真 raw，状态与 ID 永久保留、不复用。不是算法、正确性或仿真效果失败。
4. **修复：** runner 参数改为 `--ws25-diag 1`；错误 ID 从恢复计划排除，seed07 diag 更换为 `20261003-110000-ws25-v1fix-cal07-classreserve-diag`。R4 保留 r3 中六个已成功主格和其余所有未尝试 ID，仅替换这一项；源码固定 SHA、trace、拓扑、统计定义和其余 27 个 ID 均不变。
5. **冻结计划与检查：** 版本化[r4 计划](../research/evidence/ws25-v1fix-calibration-plan-r4.json)含 28 个唯一 ID；与 r3 对照只有上述一个 diag ID 被替换。`py_compile`、`plan`、ID 唯一性/替换检查、CLI help 的 `--ws25-diag {0,1}` 口径及 `git diff --check` 通过。远端最近审计 load 1m=`0.0`、无活动仿真、可用内存 `122.95 GiB`、空闲盘 `5520.6 GiB`。
6. **当前状态：** r4 尚未推送/启动；当前实际模型 GPT-6 Luna High。推送后确认工作树干净和远端空闲，立即运行 `python scripts/run_ws25_v1fix_calibration.py run`。runner 会先从本地已回传 raw 验证 r3 六个成功主格，然后以新 ID 执行 seed07 diag 和剩余未尝试格；保持 cap=2、逐格 trace SHA 预检和约 30 分钟监督。任一新失败仍停新格并保留 ID/raw。
7. **未完成：** diag 控制及剩余 21 个主格、矩阵验收、Sol High 校准分析、0/64/128 档约束、正式双侧阈值/样本量/最终 ID、正式矩阵及小论文均待办。WS-25 仍 ACTIVE；校准不作正式收益或 NO-GO 结论。
8. **边界：** r1 是固定 SHA 未含 trace，r2 是远端 Git 缓存未同步固定 SHA，r3 diag 是命令行参数缺值；前两者和本次均为执行身份/调度问题，不是候选机制失败。仅 r3 六个主臂是当前可报告的新校准数据，单个 seed 尚不允许性能分析结论。WS-21、WS-23、WS-24 和历史 WS-10/11/12 判断不重写。
9. **CONTEXT SNAPSHOT：** seed07 六个主臂 6/28 逐格通过，diag ID 已 BUILT 但 CLI 拒绝启动；r4 用一个替代 ID 修正，27 个既有身份保持不变。当前模型 Luna High，材料验证完成待推送，随后自动恢复远程执行；全部校准格终态后实际切 Sol High 分析。
