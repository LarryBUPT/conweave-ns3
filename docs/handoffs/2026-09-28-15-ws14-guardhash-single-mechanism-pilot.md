# Handoff 15：WS-14 GuardHash 单机制研究小样

日期：2026-09-28。来源任务 ID：`01a0e380-6362-71f0-a95b-9b14d8ce8765`，标题：`WS-14 单机制研究小样验证`。状态：**按事前停止规则完成 0/192 极端格 pilot；不进入 64/128 格或 WS-15。**

## 1. 本对话目标

核验 WS-13 交接后的当前项目状态，另立 WS-14 分支，冻结一个单机制可证伪假说、相同传输契约、基线和强对照、连续损害曲线、观测缺口及停止条件，然后运行正确性与极端格小样并留原始证据。

## 2. 已确认的项目事实

- 进入时 fork HEAD 为 `feature/ws13-tail-diagnosis@de6db9eea529f9a60a974f22e4229a4c1106a52c`，工作树干净；该分支已包含 WS-13 交接。WS-13 的 IRN+PFC 压力 11 格仅 13/16 完成，不用于本轮性能比较。
- 新分支为 `feature/ws14-single-mechanism`。实验仿真固定 SHA：`73401ce3ac0a5c27bf0e3e0636c9337056d9355e`。之后分析器提交为 `049ab1afb7e0e9d0cdbcf49174012ef9574c10eb`，仅新增本地分析代码；所有格仍从固定仿真 SHA 独立构建。
- 预注册契约：[研究契约](../research/ws14-single-mechanism-prereg-v1.md)，原始分析：[JSON](../research/evidence/ws14-small-analysis.json)，结果报告：[pilot 报告](../research/ws14-guardhash-single-mechanism-pilot-report.md)。
- 7 格实验 ID：`20260927-233000-ws14-{0-q,0-g,192-f,192-h,192-q,192-d,192-g}`。共同条件为 1280 主机 400G、DCQCN、PFC=0、IRN=1、seed=1、9 MiB buffer；192 输入 trace SHA `bf1a1960651b2d5bd27cd1304433d489363727a7c02d08c5c05df2b2415d9c8a`，拓扑 SHA `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。
- 7/7 格 SUCCEEDED，所有输入流完成；两类 GuardHash/shortq2 队列字节守恒检查为 0 violation，逐目的出口与 QP 探针可配对，192 格 PFC 文件为空。资源收据齐全，峰值进程树 RSS 约 4540.59 MiB，最低可用内存 114.16 GiB、磁盘 5777.26 GiB；实验后无活动仿真。

## 3. 已完成工作

- 阅读并遵循项目远程实验工作流、baseline/dataflow 审计与 `conweave-project-state` 技能；核验个人 fork 分支和 WS-13 的实际交接文件。
- 以 GuardHash 模式 14 的背景队列字节评分惩罚为唯一候选机制（`lambda=1,tau=0`），对比普通双候选模式 13；另设 ECMP、逐包哈希和 DRILL 对照。保持已有传输参数不变，不启动 IRN+PFC。
- 0 背景 shortq2/GuardHash 的 FCT SHA 完全相同；192 档所有五模式完成，复算出绝对 MoE 批次、背景 P99/最大值、逐流尾部和 QP CNP/目的出口队列等待。具体数值见报告。
- 一次分析脚本未提交导致 runner 拒绝后续新构建；已提交后按原 SHA 恢复。此前完成格与原始结果未变，成功恢复全部 7 格。旧失败尝试只留本地 receipt，不改实验元数据。
- 双侧停止规则被触发：GuardHash 相对普通双候选背景 P99 低 121.477 µs，但 MoE 批次慢 0.552 µs；相对 ECMP MoE 批次慢 0.731 µs。最慢背景 QP 转移至新流，队列等待对原尾流不一致下降。故中档格未运行，WS-15 不启动。

## 4. 已形成的设计决策

GuardHash 本次仅有一个单输入 pilot 的背景 P99 改善，同时 MoE 相对 ECMP/普通双候选变慢，且背景最大 FCT与尾流迁移不支持双侧通过。依契约停止机制扩展。此决定不是通用业务安全结论，也不修改 WS-10/11/12 的历史 no-go；没有新增百分比线。

## 5. 当前状态

2026-09-28 独立交接核验：分支 `feature/ws14-single-mechanism` 本地与 origin 同为 `735e0b3c3ea7f13d0797f802eef9bbf698e6971a`、工作树干净；固定实验 SHA 仍为 `73401ce3ac0a5c27bf0e3e0636c9337056d9355e`。重跑 `run_ws14_small.py verify` 通过 7/7 格；`analyze_ws14_small.py` 从原始数据再生的机器摘要 SHA-256 与已提交文件同为 `dbce7a845c8e18bd4f4ef95b6164ba2bfa8d54adf7fefd20ae2731ade07dacda`。本次文档集成会移动分支 HEAD，不改变实验 SHA。pilot 按预注册极端格和停止规则范围闭环；结果只支持单输入描述，不支持正式效果、业务安全或因果主张。

## 6. 未解决问题

- 极端格 stop gate 后没有中档连续曲线，也没有多个独立需求重复。
- 目标 QP 的 CNP、出口排队和 FCT 配对不等于因果分解；仍缺物理 MMU 全队列、逐包 ECN、即时 RNIC 速率与可靠的逐 QP timeout 观测。
- 没有可核验业务 SLO，不能判定 19.360 µs 背景 P99 差是否可接受。

## 7. 后续推荐动作

按当前证据结束 WS-14 pilot，转向 WS-16 负结果与复现材料收束。用户要求创建 WS-15 对话时，先做门槛复核与新机制研究理由评估；本轮 GuardHash 未通过双侧门槛，不能直接运行 WS-15 确认性矩阵。若提出新的机制研究问题，应重新冻结假说、输入、完整观测和双侧规则；不得把本轮单 trace 加入确认性重复。

## 8. 与其他工作流的关系

WS-10/11/12 原预注册及 no-go 原样保留。WS-13 三条校准需求 trace 未作本轮输入，亦不作 WS-15 确认性数据。IRN×PFC 不完整压力 11 格不进入任何本轮比较。GuardHash/HarmGate 工程原型存在，不等于已证明机制有效。

## 9. CONTEXT SNAPSHOT

WS-14 在 `feature/ws14-single-mechanism` 上冻结 GuardHash 背景队列评分机制，固定仿真 SHA `73401ce3ac0a5c27bf0e3e0636c9337056d9355e`。七格 0/192 极端小样全部完成，0 背景 GuardHash 与 shortq2 的 FCT 完全相同。192 档 GuardHash 背景 P99 低于普通双候选，但 MoE 批次慢于普通双候选 0.552 µs、慢于 ECMP 0.731 µs；旧背景尾流有所缓解但新的最慢流出现，出口最大等待也没有一致下降。按冻结门槛停止，不跑 64/128，不启动 WS-15，不设置业务安全线。详见 `docs/research/ws14-guardhash-single-mechanism-pilot-report.md` 和 `docs/research/evidence/ws14-small-analysis.json`。
