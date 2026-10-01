# Handoff 51：WS-24 同 SHA point-to-point 单测收据

日期：2026-10-02。工作流：WS-24 单测补验。执行对话：`01a0f1da-f1e2-7870-9361-24b4d626fd76`。本文件记录当时的收据交接；后续实际 Sol High 独立复核见 [Handoff 52](2026-10-02-52-ws24-sol-review.md)。WS-24 仍 ACTIVE。

## 做了什么

先前两个尝试保留在各自 ID 中。`20261002-140000-ws24-point-to-point-unit` 的监督脚本在 configure 前失败，C++ 测试没有运行；`20261002-141000-ws24-point-to-point-unit-r1` 在测试构建 715/1636 处遇到既有 core test helper 编译错误，suite 没有运行。修复仅用于隔离副本的新尝试 `20261002-142000-ws24-point-to-point-unit-r2` 成功。

r2 的远程 metadata、隔离源码 HEAD 和本次测试摘要共同记录固定仿真 SHA `b1184d6a7bd38577b235b7f119f920973308774f`。本地 `feature/ws24-multinic-validation` HEAD 与个人 origin 同名分支均为 `3f04f32ebe87aa6226091a0d24ac69e3c6b8e016`。configure 与显式启用测试的构建命令均返回 0。

原始错误是 `CommandLineTestCaseBase::Parse` 收到 const `CommandLine` 参数，函数内又调用非 const 的 `CommandLine::Parse`。它不是声明与定义互相不一致。隔离测试源码将两个 `const CommandLine &cmd` 临时改为 `CommandLine &cmd`，构建和测试后恢复。改前/恢复后 Git blob `03c247e660386a48b793bae460512eccfa6e7eea`、SHA-256 `b7285686202442d47d339fd5817e9001c47bfc23377c8a8f5f596ba694373881` 完全一致；临时版本 SHA-256 为 `3c474633f4545bc10c3fede9e8fbaddd83e5526bd19597ed19be509a4537cd99`。隔离源码最终 tracked diff 为空，只有预期未跟踪构建输出目录。

## 证据与结论

实际 runner 为 `build-ws24-tests/utils/ns3.19-test-runner-optimized`；suite 列表含 `devices-point-to-point`。suite 运行命令退出码为 0，原始 stdout 记录 5 条 PASS、没有 FAIL：suite 总项、PointToPoint、IRN timeout/PFC pause-resume grace、WS-21 feedback header、WS-21 heartbeat header。summary 的 `runner_list_exit_code` 是 null，因为 driver 没有赋值该字段；driver 源码显示列表进程非零会抛错并停止，本次随后执行 suite 且成功，因此 runner-list 通过由控制流证据支持，不能说 summary 有显式退出码。

资源收据有 193 个样本：峰值进程树 RSS 727.96 MiB，最低可用内存 122.27 GiB，最低空闲盘 5596.79 GiB，最大 load1m 为 2.16。终态 `SUCCEEDED` / `PASSED`。fetch 回传的 16 个文件逐个计算 SHA-256，校验清单在 `results/20261002-142000-ws24-point-to-point-unit-r2/FETCHED_SHA256SUMS.txt`；测试日志、suite 列表、resource samples/summary、metadata 与驱动摘要均在该结果目录。

此单测证明共同源码中的 point-to-point suite 通过，不独立证明 WS-24 多 NIC 身份、路由、动态 CNP 或性能。WS-24 14 格 raw 和分析没有修改。单测清单已勾选；整个 WS-24 不归档，真实部署映射仍缺可信来源，四臂数据仍是单 seed 合成描述性 pilot。

## 尚待完成

本收据交接形成时当前执行环境没有模型切换工具，故当时未声称已切至 GPT-6 Sol High。监督方随后实际切换，完成独立复核并写入 [Handoff 52](2026-10-02-52-ws24-sol-review.md)。此前两个失败 ID 与所有 raw 继续保留；真实映射和独立需求效果仍待验证，WS-24 保持 ACTIVE。
