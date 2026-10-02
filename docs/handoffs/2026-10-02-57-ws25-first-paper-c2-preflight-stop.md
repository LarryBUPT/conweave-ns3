# Handoff 57：WS-25 C2 兼容修复后的正确性暂停点

日期：2026-10-02。WS-25 继续 ACTIVE；本交接记录 C2 远程正确性阶段的安全暂停点，不是 pilot 或正式效果结论。

## 做了什么

- C1 `1d876a03629dcc0834e001d02e891957608a9f6c` 的 ConWeave 八流格 `20261002-220004-ws25-pre-conweave` 在 `run.py` 配置生成阶段失败。日志为 `Unsupported ConWeave Parameter Setup`；原因是 OS1 拓扑名没有进入既有 ConWeave IRN 参数分支。该失败 metadata、worker/simulation/build 日志和资源摘要已回传，原 ID 未覆盖。
- C2 只修正 `run.py` 的拓扑兼容条件：`topo_1280_400G_400G_OS1` 在 `PFC=0, IRN=1` 下复用已有三阶段 IRN 参数（flush 16、waiting 300、expiry 1000）。C2 源码 SHA 为 `bb10309261b7c5be350fcaab75b4fdb8db95ddca`，修复 diff 仅为该条件分支。
- 因源码变化，C1 IDs 不复用；C2 的 12 个 v2 ID 已写入协议和冻结计划。C2 源码已推送并由服务器 `sync` 成功确认。

## C2 原始证据

| ID | 状态 | 完成/守恒 | FCT SHA | 资源摘要 |
| --- | --- | --- | --- | --- |
| `20261002-223000-ws25-v2-pre-fecmp` | `SUCCEEDED`，已验证 | 8/8；tag1 `33,554,432 B`，tag2 `32,768 B` | `e3fa403b4768239fdd0e916f333117ecd84177c3d0553eefc923a76cb249fdbc` | peak RSS `4543.96 MiB`；min mem `118.57 GiB`；min disk `5558.61 GiB` |
| `20261002-223001-ws25-v2-pre-drill` | `SUCCEEDED`，已验证 | 8/8；tag1 `33,554,432 B`，tag2 `32,768 B` | `1d4b790ebf475bdb21646356acb921a5ac35b41667abbe7e6472de0c0f6fe15f` | peak RSS `4544.32 MiB`；min mem `118.58 GiB`；min disk `5557.92 GiB` |

两格均核对 C2 source SHA、trace SHA `29ebe2dcf38c0e4d29326947c4bc4e111f6b56fe378c020c30ee788fbaa5effb`、topology SHA `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`、模式入口与资源收据。C2 收据位于 `results/ws25-preflight-receipts-v2.jsonl`，逐格验证摘要位于各 ID 的 `processed/ws25_preflight_verification.json`。

## 暂停与未完成项

主对话要求在已启动的 C2 DRILL 格终态后停止新增格；该格已完成并核验。服务器当前无活动 ns-3 进程，负载 `0.0`，可用内存约 `122.98 GiB`，可用磁盘约 `5557.9 GiB`。没有启动 C2 CONGA、LetFlow、ConWeave、ClassReserve，也没有启动任何 192 档 calibration 或正式矩阵。

仍未完成：C2 六臂 correctness 的其余四格；C2 ClassReserve correctness；六臂 calibration；正式双侧门槛、最终 seed/ID 冻结和正式验证；逐格论文分析与成稿。C1 的 ECMP、DRILL、CONGA、LetFlow 通过结果只属于旧 SHA，不能与 C2 合并为同 SHA 六臂证据。

## 下一动作

由主对话在实际 Sol High 下复核 C1 失败证据、C2 修复边界、C2 两格 raw/资源收据及 ID 不复用；复核完成后再实际切 Luna High，继续 C2 correctness。继续时从 `results/ws25-preflight-receipts-v2.jsonl` 和已完成 C2 IDs 恢复，不覆盖旧 raw，不启动 calibration 直到六格 correctness 全部通过。
