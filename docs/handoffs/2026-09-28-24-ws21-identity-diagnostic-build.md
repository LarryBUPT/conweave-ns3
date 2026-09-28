# Handoff 24 — WS-21 路径身份诊断源码与隔离编译

## 1. 本轮目标

用户要求继续 WS-21 的下一步，并用自然语言交代流程与结论。本轮只推进首版复审指出的路径身份子门槛和反馈工程契约；完整技术 pilot 与效果矩阵没有获准解锁。

## 2. 已核验前提

按项目 `AGENTS.md` 先读 `docs/REMOTE_EXPERIMENT_WORKFLOW.md`，再读 baseline 审计、项目状态 Skill、WS-21 复审与实际源码。起点为个人 fork `feature/ws21-downstream-feedback@4465f37c79c17b0bc9b8d8682656d6ec728174ab`，工作树干净。旧 WS-19 六格静态预算脚本 `python scripts/audit_ws21_static_budget.py --verify` 通过；它仍只说明旧输入的 13.29 ms 最大背景尾部、候选 key 与报告上界预算，不能提供 WS-21 动态证据。

## 3. 本轮实际工作

在模式 20 加默认关闭的 `WS21_IDENTITY`：初始化时遍历最短路径 DAG，检查目的入端口到源首口反推是否有冲突；源 ToR 记录实际首口，目的 ToR 在最终主机出口 ECN 标记前记录实入端口反推首口及上游 CE。按 QP 四元组汇总包数和首次/末次 ns，结束时写独立 raw 文件。新增 `scripts/verify_ws21_identity.py`，用同 ID WS18 时序、拓扑和身份文件逐 QP 核查。运行器已透传诊断开关，诊断状态不供源端选路。

在[工程契约](../research/ws21-identity-diagnostic-contract.md)中列明完整尾部端口事件流和真实反馈报文的字段、订阅/停发、乱序/丢失、年龄、状态与线上成本要求，并明确这些**尚未实现**。

## 4. 检查与构建

`python -m py_compile`、`git diff --check` 通过；核验器成功解析固定拓扑的 1,280 个主机 ToR 归属及一份 WS-19 旧 `_out_ws18.txt` 的 16,384 条时序行，仅作格式检查。源码提交 `382b6dfe98ff6da28aea9c737d56a55206ef344e` 已由受保护脚本推送至个人 fork 并在远端同步。远端检查时 `active_simulation_pids` 为空、1 分钟负载 0.0、可用内存 123.01 GiB、磁盘 5,715.6 GiB。独立实验源码构建 ID `20260928-232758-ws21-identity-build` 返回 `build complete`。**本轮没有运行仿真，也没有新 raw。**

## 5. 结论

路径身份诊断已有可编译的工程入口，静态歧义将使初始化失败，且目标入包观测不改变选路；但“逐 QP 一致”“开/关 FCT 相同”和“上游 CE 足以区分候选”都仍是待验命题。WS-21 完整技术 pilot **NOT READY**，效果矩阵 **NO-GO**。旧 WS-19/20 与 WS-10/11/12 判定不变。

## 6. 未完成与限制

尚缺同 SHA 40 流开/关技术 pair 的原始结果和资源收据；没有共享出口全尾流事件、QP 传输转折、显式反馈消息、订阅停发或线上字节/延迟。旧 64 µs 桶仍不足，当前代码没有声称修复它。隔离编译不等于运行时映射成功；旧 WS-19 raw 不能充作新 pair。

## 7. 下一动作

先按[契约](../research/ws21-identity-diagnostic-contract.md)用固定 40 流和拓扑在**同一新 SHA** 建开/关两份独立结果，核对 FCT/WS18 哈希、40/40 与 33,849,344 B 守恒、身份文件零歧义和资源差额。若失败先修源码、换新 SHA/ID；若通过，也只关闭身份子门槛。随后再实现可覆盖完整背景尾部的流式端口事件和可计费真实反馈消息，审查后才可能讨论反馈技术 pilot。

## 8. 与其他工作流关系

WS-22/23/24 的条件未改变，WS-25 只整合实际静态/技术/效果证据。无业务 SLO、硬件或新独立需求效果数据。

## 9. CONTEXT SNAPSHOT

个人 fork 分支 `feature/ws21-downstream-feedback`；诊断源码 SHA `382b6dfe98ff6da28aea9c737d56a55206ef344e`，隔离构建 ID `20260928-232758-ws21-identity-build` 成功。输入候选是 `config/ws18_1280_correctness.txt` SHA `4e7d0e6a68e3230e8960a174e570a0a788c191fa0b44922408867b02c25782cc`，拓扑 SHA `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。未运行新格；完整技术 pilot 与效果矩阵继续关闭。
