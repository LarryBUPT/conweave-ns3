# Handoff 53：WS-23 延期 v2 对照格启动失败

日期：2026-10-01。证据类别：构建/执行故障诊断；没有形成压力对照结果或机制效果证据。

## 1. 本对话目标

继续 WS-23 延期 v2 双格端到端验证：先以无探针对照重现固定压力输入，再在对照通过后运行定向暂停探针。跨类 PFC=0 四因果格仍为独立必做项，不由本双格替代。目标与验收边界见[预飞行协议](../research/ws23-deferral-v2-preflight.md)及[WS-23/24 必做清单](../project-state/WS23_WS24_VALIDATION_PLAN.md)。

## 2. 已确认的项目事实

- 仿真源码与验收器固定在 `94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1`，分支 `feature/ws23-validation-execution`。输入 `config/ws09_drop_probe_16x1MiB.txt` SHA-256 为 `bc2db1513cbde20f12eea6efa4e2265cf74954be4fa45f2a147ff0ce84b33985`；拓扑 SHA-256 为 `dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad`。
- 首个对照 ID `20261001-150000-ws23-rto-v2-control` 在 optimized 构建后启动失败，状态为 `FAILED`，远端 PID `161782`，raw ID `194251116`。失败实验的远端/本地结果均保留，不复用；未运行的旧 probe ID `20261001-150100-ws23-rto-v2-probe` 也不再复用。
- 失败格的 `config.log` 显示 Waf 尝试编译 `src/core/test/command-line-test-suite.cc`，因 `const ns3::CommandLine` 调用非 const `Parse` 而失败。之前的单测准备污染了该实验默认 Waf 测试配置；这不是压力输入上的仿真结果。独立 `devices-point-to-point` 测试记录为 1/1 通过，测试 helper 与默认配置恢复后，文件 SHA 分别为 `b7285686202442d47d339fd5817e9001c47bfc23377c8a8f5f596ba694373881` 和 `4218823aba16383072f2cdc3d574d4ea60cf992e8361069e41f9e16b2f3fab87`。
- 失败格的资源收据有 6 个运行采样；进程树峰值 RSS 235.28 MiB，可用内存最低 122.79 GiB，空闲磁盘最低 5657.99 GiB，最高 1 分钟负载 0.1。原始资源文件位于忽略目录 `results/20261001-150000-ws23-rto-v2-control/logs/`，仿真错误位于 `results/20261001-150000-ws23-rto-v2-control/raw/194251116/config.log`。
- 2026-10-01 08:56（北京时间）远端只读复查：0 登录用户，无仿真/编译进程，load average `0.00/0.13/0.31`，可用内存约 122 GiB、空闲盘约 5.6 TiB。共享 worker SHA-256 为 `9e1b4e144d5584e8999d2c560bf4577b249ca73421d9aac6c53e5a96a798766e`，包含 `--ws23-pfc-probe-drop-gated` 参数。长期 `hg outgoing -q` PID `377959` 仍为 0 CPU、工作目录已删除；依据此前用户确认予以保留。
- 新 control/probe ID `20261001-151000-ws23-rto-v2-control-r2` 与 `20261001-151100-ws23-rto-v2-probe-r2` 经远端状态检查均无结果目录。它们仍须在启动前再次检查。

## 3. 已完成工作

- 用户要求继续 WS-23；按项目要求重新读取远程工作流、baseline/dataflow 审计与项目状态技能。
- 核查本地五份状态/协议文档的未提交差异，确认固定 SHA、输入哈希与双格先后门槛未变，只替换重试身份并记录首格故障。
- 读取首格 metadata、构建/仿真/单测日志与资源收据，核实失败类别、PID、raw ID、构建模式和资源数字；未将其计作仿真验证。
- 检查远端资源、登录用户、实验进程、共享 worker 能力及两个新 ID；未发现会阻止重试的资源或 ID 冲突。
- 本地 `git diff --check` 通过。当前状态文件、路线图、工作流表、必做清单和预飞行协议已补充失败记录并改用 r2 ID。

## 4. 已形成的设计决策

- **决定：**失败 control ID 及未运行的配套旧 probe ID 都保留，不重用；换一组唯一 r2 ID。
- **理由：**首格已生成失败元数据、日志和资源收据；沿用会混淆实际尝试和结果。问题出在测试准备对默认 Waf 配置的影响，不能由该失败推断 v2 机制对错。
- **构建约束：**新 control 必须从固定 SHA 建立全新隔离 optimized 副本，沿用同 SHA 独立测试通过证据；不得在 simulation 默认输出目录重新开启单测。
- **顺序约束：**control 先运行并逐项通过 16/16 完成、总准入丢包 161、源主机 14 丢包 36 次和固定 FCT 哈希后，才允许运行 probe。

## 5. 当前状态

- 本次观察时分支 `feature/ws23-validation-execution` 的 HEAD 为 `5721627ab03dfbd367d8af32881d7094fdf2fea6`，工作树含五份未提交文档修改及本 Handoff。
- control 构建曾成功，但首格在仿真前失败；没有有效 FCT 可供压力验收。r2 两格尚未构建或运行。
- WS-23 仍为 ACTIVE；跨类 PFC=0 四格、隔离候选双侧验证和最终源码/效果/结论核验仍未完成。
- 后台监督模型已在本次接续前由集成线程实际切至 GPT-6 Luna High；终态数据回传后须实际切回 GPT-6 Sol High 做原始数据验收。

## 6. 未解决问题

- 必须在 r2 control 的独立干净副本上完成 optimized 构建、启动前资源观察器和无探针对照，并核对全部固定验收断言。
- 只有 control 全部通过才可运行 probe；还须核验丢包门控、暂停中延期、显式恢复后的宽限和完整 RTO、最终恢复、1599 次刷新、16 个 QP 序号与字节守恒。
- 两格技术正确性通过不代表隔离效果或性能收益；跨类因果四格、隔离候选双侧对照仍是独立工作。

## 7. 后续动作

1. 将本 Handoff 与五份状态/协议文档修改提交并推送个人 fork，确保固定仿真 SHA 仍可由远端同步。
2. 启动前重新核对共享 worker、WS-24 执行边界、远端用户/进程/资源及两个 r2 ID；资源观察器先显示 `READY`，再运行。
3. 从 `94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1` 独立构建 `20261001-151000-ws23-rto-v2-control-r2`。终态先收正 RSS 收据、取回 raw 并运行 pressure 验收；任一门槛失败就保留并停止后续格。
4. control 通过后才构建并运行 `20261001-151100-ws23-rto-v2-probe-r2`，随后取回原始数据并运行 deferral-v2 双格验收。
5. 完成终态回传后实际切至 Sol High，复核日志、元数据、输入/拓扑哈希、FCT 指纹、资源收据和逐条动态事件；继续追踪 WS-23 其余必做项。

## 8. 与其他工作流的关系

本记录只涉及 WS-23 延期恢复正确性双格。共享远端 worker 同时服务 WS-24，因此每个构建/运行前仍需确认共享入口没有冲突。WS-24 的多 NIC 源码和验收协议保持其自身固定 SHA 与执行边界；本双格既不替代也不阻塞其独立前置门槛。既有性能 no-go 与本次构建故障结论均不重判。

## 9. CONTEXT SNAPSHOT

WS-23 v2 固定源码 `94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1`；输入/拓扑哈希见第 2 节。首次 control `20261001-150000-ws23-rto-v2-control` optimized 构建后，在仿真开始前因默认 Waf 测试目录尝试编译已知 `CommandLine::Parse` const 缺陷而失败；失败日志、raw 和 6 点正 RSS 收据已回传，ID 不复用。独立 point-to-point 单测 1/1 通过，恢复文件哈希已记录。远端 worker SHA `9e1b4e…` 支持 v2 参数；2026-10-01 08:56 检查无用户/构建/仿真作业，资源充足，长期 hg 进程按用户先前确认保留。新 ID `20261001-151000-ws23-rto-v2-control-r2` 先跑；只有通过 16/16、161/源 14 的 36 次丢包及 FCT SHA `97feb0e118544f07e006da9e9bc2ead2566a10b91ad2201e0e83ced89279b18a` 才运行 `20261001-151100-ws23-rto-v2-probe-r2`。新格尚未构建/运行；跨类四格及隔离双侧验证仍为必做。主协议：`docs/research/ws23-deferral-v2-preflight.md`；执行清单：`docs/project-state/WS23_WS24_VALIDATION_PLAN.md`。
