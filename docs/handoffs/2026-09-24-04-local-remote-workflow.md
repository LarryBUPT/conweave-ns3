# Handoff 04：搭建本地-远程工作链路

来源：Codex 对话 `01a0cd67-6078-7fc0-adad-fd68edfb1881`，标题「搭建本地-远程工作链路」。由集成任务整理。日期：2026-09-24。

## 1. 本对话目标

建立本机开发、Git 版本管理、远程隔离编译/仿真、原始数据保存、回传与本机分析的安全科研链路。用户要求第三方仓库只读，服务器项目写入仅限指定工作区，不做系统级环境修改。

## 2. 已确认的项目事实

个人 fork `LarryBUPT/conweave-ns3` 由原始 ConWeave fork 而来；本机个人克隆的 `origin` 是唯一可写 GitHub remote。服务器为 Ubuntu 16.04，Docker 客户端存在但当前用户无 daemon 权限；原始基线可在服务器工作区内用 Waf 原生编译。远程已有的另一份 ConWeave 工作树存在 `mix/.history` 未提交修改，应保留。

## 3. 已完成工作

建立个人 fork、只读 remote 和拒绝推送 hook，版本化远程控制脚本、worker、FCT 本机分析脚本与工作流文档。`20260923-165542-smoke-fecmp` 在固定 `edd2b72` 上完成隔离编译、后台运行、结果回传和本机分析，状态 `SUCCEEDED`；这只验证链路。用户后续得到本地 commit→个人 fork→远程缓存→独立实验副本的命令说明。

## 4. 已形成的设计决策

**Decision：**个人 fork commit 是源码版本依据，原始结果按实验 ID 独立保存。**Rationale：**避免本地与远程手改两套代码、结果覆盖和参考仓库误推送。**Alternatives：**直接用远程现有工作树、为 Docker 修改权限、运行上游批量脚本；均不符合隔离/资源边界。详见 `docs/decisions/ADR-001-personal-fork-and-read-only-references.md`。

## 5. 当前状态

最小完整链路可用。个人 fork 当前研究分支和远程缓存的实时 SHA 应以 `docs/project-state/CURRENT_STATE.md` 的核验记录及执行时 Git 命令为准；不要把本对话完成时的 `a8d2db5` 当永久 HEAD。大规模并发与新算法编译兼容性尚未验证。

## 6. 未解决问题

必须解决：每项新源码改动需重新编译并按固定 SHA 建实验。可延后：远程绘图依赖和更大规模资源 pilot。研究方向保留：工作流不定义任何新负载均衡算法。

## 7. 后续推荐动作

按 `docs/REMOTE_EXPERIMENT_WORKFLOW.md` 从干净的个人研究分支推送、同步、构建、运行、检查状态、回传和分析。每次保留实验 ID、SHA、输入哈希；不触碰既有结果或远程原工作树。

## 8. 与其他工作流的关系

为 baseline 审计和后续 WS-06–08 提供执行底座。研究文档可提出实验设计，但不能绕过工作流的只读仓库与资源约束。

## 9. CONTEXT SNAPSHOT

本地开发、个人 fork 版本管理、远程固定 SHA 独立实验、结果回传和本机分析链路已由一次 `fecmp` smoke 验证。参考仓库只读，服务器只在项目工作区写入。当前实时分支需每次重新核验。
