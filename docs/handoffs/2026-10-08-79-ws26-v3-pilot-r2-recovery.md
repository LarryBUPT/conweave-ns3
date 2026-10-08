# Handoff 79：WS-26 独立需求 pilot v2 修复与重启

## 1. 本对话目标

继续 WS-26 独立需求 pilot。目标是修复 ConWeave 在 OS1、PFC=1、IRN=1 下的参数入口，并用全新源码 SHA 与实验 ID 重新执行筛选 pilot。

## 2. 已确认的项目事实

- 个人 fork 分支为 `feature/ws26-classmix-validation`。修复提交为 `593038416fa16f4982b600d256b563260f9106a8`，已推送至 `origin`。
- 旧 pilot 固定于 `d6fdc5efe9a9aa77a90d24ab3aee931f721b607f`。高档 28 格中 6 格终态成功；第 7 格 `20261008-070000-ws26v3-p90-b192-conweave` 在仿真开始前失败，错误为 `Unsupported ConWeave Parameter Setup`。
- 旧成功格与失败格均不得并入修复版数据。旧 ID 和 raw 仍在本机结果目录中；旧计划副本为 `docs/research/evidence/ws26-v3-pilot-plan-v1-stopped.json`。
- 修复代码在 `run.py` 中为 OS1、PFC=1、IRN=1 明确设置 flush=16、waiting=300、expiry=1000。这是工程比较配置，并非原版官方校准。
- 修复版计划含 52 个新 ID：高档 28 格、低档 24 格。拓扑与 16 份 trace 哈希不变；新计划文件为 `docs/research/evidence/ws26-v3-pilot-plan.json`。

## 3. 已完成工作

- 在 `run.py` 增加明确参数分支，做 `python -m py_compile run.py` 和 `git diff --check`，均通过。
- 提交并推送修复 SHA。计划生成器和逐格验收器已更新为新 SHA 与新 ID 命名。
- 生成 52 个新 ID，执行计划结构、唯一性和 Python 编译检查，均通过。
- 阅读阮一峰《中文技术文档的写作规范》README 及标题、文本、段落、数值、标点符号和文档体系章节；据此更新协议和项目状态用语。

## 4. 已形成的设计决策

**决策：**保持 OS1、PFC=1、IRN=1 和原计划中的 ConWeave 参数 16/300/1000；重新冻结所有高档和低档 pilot ID。

**理由：**旧源码把目标组合判定为不支持，导致 ConWeave 格尚未启动。修改后的参数满足用户明确要求，并让整个修复版 pilot 使用同一 SHA。

**限制：**该组合是工程比较配置，不能描述为原版 ConWeave 的官方校准。v1 的 6 个成功格只能作为旧批次历史数据。

## 5. 当前状态

WS-26 仍为 ACTIVE。修复源码已提交和推送；本地计划结构检查通过。新 SHA 尚未在服务器构建，也尚无 v2 运行格。高档与低档资源收据均未产生。工作区位于 `E:\研\毕业论文\workspace\ws26-classmix-validation`，分支 `feature/ws26-classmix-validation`。

## 6. 未解决问题

必须完成新 SHA 的远端编译和 ConWeave 参数/全流正确性检查；随后重跑高档 28 格并逐格核验原始数据与资源收据。高档双侧效果门和机制覆盖门通过后，才运行低档 24 格。最终结果还需由 GPT-6 Sol High 分析。正式矩阵尚未获准或启动。

## 7. 后续推荐动作

1. 将更新后的生成器、验收器、协议、停止批次计划和项目状态提交推送。
2. 核对服务器无其他用户作业、系统健康、锁和唯一 runner；在新 SHA 下构建。
3. 用独立 v2 ID 验证 ConWeave 的配置快照、完整流完成及资源收据。
4. 串行启动并核验 v2 高档 28 格。任一正确性或资源验收失败时停止新格并保留证据。
5. 只有双侧筛选和机制门同时通过时，才启动低档 24 格。

## 8. 与其他工作流的关系

此 pilot 属于 WS-26 第一课题后续机制验证，不更改 WS-25 正式 NO-GO，不进入投稿后的第二课题。v1 结果不得与 v2 合并或配对。低档和正式矩阵均保持未启动。

## 9. CONTEXT SNAPSHOT

WS-26 pilot v1 使用旧 SHA `d6fdc5e…`，高档 6/28 成功后在 ConWeave 仿真前失败；旧 ID/raw 被保留并排除。OS1、PFC=1、IRN=1 的 ConWeave 参数入口已在 `run.py` 修复为 flush=16、waiting=300、expiry=1000，固定修复 SHA `593038416fa16f4982b600d256b563260f9106a8`。新计划有全新 52 个 ID（高档 28、低档 24），尚未远端构建或运行。继续遵守 `docs/REMOTE_EXPERIMENT_WORKFLOW.md` 的资源门、串行起步、逐格收据和持续验证要求。

