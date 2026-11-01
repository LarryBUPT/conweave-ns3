# WS-31 第十二节点：适配器边界整合

日期：2026 年 11 月 1 日。来源为“WS-31 主对话：类别感知新机制构思与论证”（`01a19322-95a5-76e3-a4f5-1f1e9dde81ce`）的[节点交接副本](../research/evidence/ws31-adapter-boundary-integration-20261101-r1/snapshots/main/adapter-boundary-node12-handoff.md)。本次只在本地核验、整合并推送个人 fork，不接管实验。

## 1. 本对话目标

确认固定 1f 源的一次构建及 17 个适配器条件确有原始证据，将旧“构建前停止、r2 待验”更新为工程通过，同时保留网络验收与后续科学验证的实际范围。WS-26～WS-28 的[归档交接](2026-11-01-ws26-ws28-archive.md)和平台收据已存在，本次不重复归档。

## 2. 已确认的项目事实

实现源为 `1f917f44fcfb88e61f3ad22c5cc75fa3a06b6c0e`，父源为 `1ec5eedc24cd863a289b7493e8b3865c70592ab5`。本地隔离克隆 `feature/ws31-candidates` 干净，HEAD 与个人 origin tracking ref 一致。42 个固定 Git 对象及 4,843 项树与交付匹配；未改源码或运行二进制。

新工程 ID 为 `20261101-150000-ws31-adapter-preflight-r2`。独立 index SHA-256 为 `9b103d83c461e4c93138e1a0d7650b1d21150b85503949168ae81064a3bd4f8b`，QA 为 `513898a3ae98b08013ddf385b81a9400586c9852cbb6f7fbc174a4607f68c8fa`。主聚合验收与这两份文件相互关联，完整模型重放保留主验身份。

## 3. 已完成工作

Integration 的[本地验收](../research/evidence/ws31-adapter-boundary-integration-20261101-r1/verification.json)核对 33 文档、4 依赖、28 原 r1 文件、15 支持、47 结果和 4 参考。一次 optimized `-j2` 构建完成 1,468 项、用时 5m59.118s，随后三个命令按 C1 → C2 → C3 直接运行。两个 ELF 二进制和 36 个 ns-3 库均按实际字节核验；ldd 在指定 LD_LIBRARY_PATH 下解析的路径一致，未将其写成内核采样的运行时映射。

| 范围 | 从原日志另核的动作与结论 |
| --- | --- |
| C1，五例 | 20 包、8 次首次选择、3 次真实清理。真实出口队列增加 5,000 B 后保持路径；重复、空洞及重叠的有效载荷、预测压力、精确到期、容量／区间／32 位序号回退与重建计数匹配 |
| C2，十例 | Stop／Dispose 的提前、同刻两种事件顺序、放行后和零等待均有日志；十需求／81,920 B，四次取消、六次交付替身。独立按固定四元组哈希算出 376 ns，原需求时刻及字节账一致，真实 QP 与完成为 0 |
| C3，两例 | 九包、三次真实清理。借用与归属类别激活、20,199／20,200／20,201 ns 的只读活动边界、20,202 ns 迟到续期，以及一个残留包／156 B 均匹配；未知首包身份在清理前保持 |

完整 C1 预算账和 C3 活动／归属模型由主独立重放，主预备脚本哈希未变。八种真实日志副本损坏的拒绝收据已核身份，Integration 未重做这些负例或重跑夹具。夹具显式时间戳格式的开销为 56 B，不与旧网络格的 48 B 开销混加。

原 r1 的 28 文件与恢复前后索引一致，其中 27 份还与既有 Integration 快照逐字比较；旧快照未保存的 .gitignore 如实单列。原未知 PID 297502 的归属继续未知。此次本地复制曾遇到 Windows 过长目标路径，旧快照覆盖数也曾被本地脚本错误假定为 28；两份旧脚本及纠正记录保留，未发生实验数据不一致、源码改动或远端重跑。

## 4. 已形成的设计决策

17 例只完成生产适配器边界。C2 交付替身不创建 QP，交换机清理不证明端点及链路已排空，三个候选的效果和成本仍须独立验证。本节点网络运行、旧核心重复、同步及部署均为 0，累计网络仍为 41 格，最新网络已验源仍为 1ec。

约 181 MB 的结果中含 38 个 ELF；它们留在原本地结果目录，Git 只保存哈希、来源与较小证据副本。文件位置及是否冻结见[来源清单](../research/evidence/ws31-adapter-boundary-integration-20261101-r1/source-manifest.json)，不为文档整合重复提交大型构建产物。

## 5. 当前状态

三调用终态后，原源码／入口／环境约束已于 07:05:47 UTC 明确释放。主核旧驱动 43152 不存在和唯一副 idle cursor 90 后另派默认两格；Integration 主快照至 cursor `f7a3a118-6bff-483e-a32e-333396ead68d:19`，主为 idle，未重复派发或直接唤醒副。

权威仓库分支仍为 `feature/ws23-ws24-evidence-integration`，本节点提交前 HEAD 为 `cd2caf2bb3aa65caa65dbb5eee76194db97e9c60`。主、副自有 `docs/research/ws31/` 未跟踪材料不整体纳入暂存。本轮只提交五份权威状态、本交接和 Integration 新证据目录。

## 6. 未解决问题

默认 Q12／C2 两格的新结果尚未在本节点验收。真实端点退出、排空、代际观测和同四元组复用只有[设计草案](../research/evidence/ws31-adapter-boundary-integration-20261101-r1/snapshots/main/endpoint-lifecycle-design-r1.md)，尚无实现或执行证据。独立 C1 V0、三候选的业务批次／背景尾部效果及状态／运行成本仍必做。新组合基线未形成，WS-31 不闭环、不归档。

## 7. 后续推荐动作

主已另行授权[两格计划](../research/evidence/ws31-adapter-boundary-integration-20261101-r1/snapshots/main/adapter-default-validation-r1.json)，哈希 `01665606c32d7422b92f4202d23e8e571500321631ca376b5924ed67f5e7eb68`。[解禁收据](../research/evidence/ws31-adapter-boundary-integration-20261101-r1/snapshots/main/evidence/adapter-default-execution-authorization-r1.json)关联本节点主验及原约束释放。

新 ID 为 `20261101-153000-ws31-adapterdef-r1-q12` 和 `20261101-153000-ws31-adapterdef-r1-c2`。先过新源码、ID、缓存、进程和资源门；两个隔离构建最多共 4 个编译任务，全部构建后串行 Q12 → C2，参考 raw 只读，旧参考、17 例及核心不重跑。新源码／入口／环境约束保持至明确释放。之后按实际调用链完成端点设计、实现和独立最小验证，再推进 V0 与双侧效果成本。

## 8. 与其他工作流的关系

Integration 只做本地验收与基线整合，主独核日志，唯一副独占远端。WS-26 保持暂停且科学范围未完成，WS-27／28 归档范围不变；QueuePin 投稿稿不改，WS-29 不读取、唤醒或归档，Ofan 暂缓。

重要节点参考复核从候选 README 与 reading-log 进入，核对 DiffFlow arXiv:1604.05107v1 的技术与核验记录。借鉴的是区分控制生效、保留身份及实际状态退出的验证方法。其 SDN 规则传播和长流喷洒与本地首包缓存不同，回收细节也不充分；不外推其收益或视为新增正式基线。当前结论仍以固定 1f 源及本节点原日志为证据。

## 9. CONTEXT SNAPSHOT

1f 的一次全构建和 17 个适配器条件已主验并经 Integration 核对来源、实际 ELF、日志边界和下一目标解禁链。原 r1 停止与 28 文件保持，原约束明确释放，新默认 Q12／C2 两格已派且有独立约束，结果未在本节点验收。网络累计仍 41／最新已验源 1ec；端点草案、独立 V0 与双侧效果成本未完，没有新基线，WS-31 继续 ACTIVE。
