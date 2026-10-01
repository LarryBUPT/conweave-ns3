# WS-24 同 SHA point-to-point 单测补验协议

日期：2026-10-01。状态：**已冻结，未执行；WS-24 ACTIVE**。本协议只补齐 `devices-point-to-point` 的编译与运行收据。已经完成的 A/B/C/D 14 格仿真、输入、原始数据和单 seed 合成结论保持原样。

## 证据缺口与固定身份

- 仿真源码 SHA 为 `b1184d6a7bd38577b235b7f119f920973308774f`。14 格的 `metadata.json` 均记录该 SHA，`build.log` 是独立 optimized 仿真构建。v0/v1/v2 使用更早 SHA。本地 18 个 WS-24 结果目录、远端 WS-24 结果日志与测试构建目录的只读检索，未发现 `--enable-tests`、`--suite=devices-point-to-point`、`PASS devices-point-to-point` 或测试 runner 收据；当前不能声称共同 SHA 的单测通过。
- 新测试 ID：`20261002-140000-ws24-point-to-point-unit`。冻结时本地 `results/<ID>` 与远端 `/home/fnl/lzy/{runs,results}/<ID>` 均不存在；执行前重查，已占用则另定 ID。
- 分支 `feature/ws24-multinic-validation`，个人 `origin` 为 `LarryBUPT/conweave-ns3`。只从固定 SHA 创建独立 `/home/fnl/lzy/runs/<ID>/source`，使用单独 `build-ws24-tests` 输出目录；不接触 14 格源码/raw 或 WS-23 checkout。
- `src/point-to-point/test/point-to-point-test.cc` 注册的 suite 包含 PointToPoint、IRN/PFC timeout、WS-21 feedback 与 heartbeat 测试。该 suite 是共同源码的 point-to-point 回归门槛，**单测本身不证明 WS-24 多 NIC 身份、路由或 CNP**；这些机制由 14 格 raw 验收支持。

## 执行与资源规则

1. 集成工作流协调共享远端入口，确认执行任务**实际切至 GPT-6 Luna High** 后，重核个人 origin/固定 SHA、worker、ID 空闲、无他人或未知/WS-23 build/仿真作业、load1m ≤10、MemAvailable ≥32 GiB、工作区空闲盘 ≥100 GiB。未满足则停止。
2. 在 WS-24 独立 checkout 执行 `python scripts/remote_experiment.py build --repo-local . --id 20261002-140000-ws24-point-to-point-unit --source-sha b1184d6a7bd38577b235b7f119f920973308774f`，核对新 `metadata.json.git_commit` 与隔离源码 `git rev-parse HEAD` 均为固定 SHA，optimized build 成功且无仿真 raw。失败保留 ID/log；修复后使用新 SHA/ID。
3. 仅在隔离源码中运行 `./waf configure --enable-tests --build-profile=optimized --out=build-ws24-tests`，再运行 `./waf --out=build-ws24-tests -j2`。将完整命令、UTC 起止、退出码和 stdout/stderr 分别保存在新 ID 的 `logs/unit-configure.log`、`logs/unit-build.log`；测试构建超过 20 分钟就记录状态并诊断。
4. 若编译遇仓库既有 `CommandLineTestCaseBase::Parse` const 声明/定义不一致，仅在此隔离副本的 `src/core/test/command-line-test-suite.cc` 同时暂时修正声明与定义。改前记录 Git blob `03c247e660386a48b793bae460512eccfa6e7eea` 和 SHA-256；测试后恢复并验证 Git blob、SHA-256 与改前相同，`git status --porcelain` 为空。其他编译错误不得泛用此修正；临时改动不进入 Git 或仿真源码。
5. 保存 runner 的 suite 列表，确认包含 `devices-point-to-point`。用隔离库路径执行 `LD_LIBRARY_PATH=build-ws24-tests ./build-ws24-tests/utils/ns3.19-test-runner-optimized --suite=devices-point-to-point --verbose`。若实际 runner 文件名不同，先只读列出构建目录并记录真实路径。保存完整 `logs/unit-suite.log`、命令、退出码、runner 路径、实际测试条目及通过/失败数。空日志、未注册 suite、只编译不执行或旧 SHA 的 PASS 均判失败。
6. 为该 ID 的构建/测试进程树每 5 秒保存资源采样和终态摘要到 `logs/resource-samples.jsonl`、`logs/resource-summary.json`，记录峰值 RSS、最低 MemAvailable/空闲盘、最大 load1m、样本数和状态；文件须在启动前不存在。出现他人作业、load1m >20、进程树 RSS >8 GiB、MemAvailable <16 GiB、空闲盘 <100 GiB、任一文本日志 >50 MiB、采样缺失或命令失败时停止后续步骤，保留原始文件。单测超过 20 分钟，先记录 PID/状态再安全终止隔离任务。后台阶段静默，正常约 30 分钟读取一次精简状态。
7. 回传该 ID 的 metadata、原始测试日志、suite 列表、资源收据、源码恢复哈希与 Git 状态收据至本地新 `results/<ID>/`，逐文件核对 SHA-256，不覆盖已有目录。终态核验后实际切回 GPT-6 Sol High 分析，更新清单、状态及 Handoff。

## 通过判据

必须同时核实：固定 SHA 与个人 origin、隔离源码、metadata 一致；显式启用测试的构建退出码为 0；runner 列表含 suite；suite 实际执行且退出码 0，完整日志含 `PASS devices-point-to-point`，所有实际条目通过且失败数为 0；core helper 若曾暂改已逐字节恢复；资源收据完整且没有越界。记录实际条目数，不预填数量。失败保留 ID 与原始收据，修复后新 SHA/ID 重验。补验通过且全部收据回传核对前，WS-24 保持 ACTIVE，不归档。
