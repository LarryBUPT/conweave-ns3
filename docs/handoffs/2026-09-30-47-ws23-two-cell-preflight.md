# Handoff 47：WS-23 两格正确性预飞行冻结，待远程执行

1. **本对话目标：** WS-23 恢复任务 `01a0f15f-58c7-7532-84bd-9acaaaa14525` 继续执行用户重新开放的全部预设验收项。本阶段将本地实现、真实暂停输入、两格验收器和远程协议做成可执行状态；根据 [工作流](../REMOTE_EXPERIMENT_WORKFLOW.md)停在实际 Luna High 切换边界，不能称任务闭环。

2. **已核验原始事实：** 旧 `20260927-215700-irnpfcstress-11` 仅 13/16 完成，旧元数据 `SUCCEEDED` 只代表 FCT 非空；定向 `20260927-223000-irnpfcdrop-11` 记录 161 次出口准入丢失，未完成流的未确认序号有先前丢包。旧修复 `12dea54d…` 的隔离 optimized build 和 point-to-point 单测通过，但没有新仿真。输入和拓扑固定 Git 内容哈希及旧证据见[恢复契约](../research/ws23-irn-pfc-recovery-contract.md)。

3. **本阶段已做：** 从已推送的 WS-24 输入分支建立 `feature/ws23-validation`，保留本地既有改动，补齐 `run.py`、远端控制器/worker、scratch 与 Qbb 设备的真实源 PG PFC 注入和接收/丢弃诊断；新增 0→24、PG 3、一条 1 MiB 的无损输入；`verify_ws23_recovery.py` 分别对旧压力反例和真实 pause/resume 格检查完成数、QP 字节/序号、恢复、暂停事件与丢包。发现原注入相对窗口起点会在目标流启动前发生，于是将协议时刻改为流开始后 200 ns，显式恢复前暂停 1800 µs，超过最长 1350 µs RTO。

4. **冻结决策：** 新源码 SHA `f8f6afdb2d93c693e32c60bb80cc5e5cf46a5c6b`。旧压力 trace SHA-256 `bc2db1513cbde20f12eea6efa4e2265cf74954be4fa45f2a147ff0ce84b33985`，新无损 trace SHA-256 `4f10f678000f7b380cc272e121db7926ca320a581c72b47909545f31f2a312f8`，共同拓扑 SHA-256 `dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad`。seed=1、各格独立 ID、资源/停止条件、命令和断言见[两格预飞行协议](../research/ws23-two-cell-preflight.md)。后续文档提交不改变仿真源码 SHA。

5. **核验与当前状态：** `python -m py_compile` 覆盖四个改动 Python 文件通过；`git diff --check` 通过；构造的 PFC pause/延期日志由解析器正确解析；旧压力 ID 被新源码 SHA 门槛拒绝。Git 内容哈希与协议一致。**本 SHA 尚无 C++ build、单测、仿真 ID 或新 raw**；上面均是本地静态或解析检查，不能证明修复有效。

6. **未完成验收项：** 新 SHA 隔离 optimized build 与 `devices-point-to-point`；无损暂停 1/1、实际源端 pause/resume、超时延期、无丢失/重传/误恢复；旧压力 16/16、两类 8/8、唯一 QP、序号与 payload 守恒、真实丢包后恢复且暂停期无恢复；全部原始数据/资源收据回传复核。任一失败需保留 raw、修复、重新固定 SHA 与新 ID。原拥塞流隔离的跨类阻塞因果前提和最小对照仍需实测；现有 PFC=0 常规格不能证明它。

7. **下一执行入口：** 监督任务须先实际切到 GPT-6 Luna High，核对个人 origin、远端 ID 空闲、他人作业和资源，再按协议部署 worker、同步固定 SHA、隔离构建/单测、无损格、压力格；后台静默、约半小时精简监督。全部终态 raw 回传后实际切回 GPT-6 Sol High 验收并按结果继续修复或形成结论。当前尚未发生模型切换，不能以本文字代替。WS-24 在此分支源码提交并推送且工作树干净后可使用共享工作树；远端两个固定副本不会要求长期占用本地工作树。

8. **与其他工作流关系：** WS-24 只读准备不改写 WS-23 输入/代码；WS-25 继续跟踪[必做清单](../project-state/WS23_WS24_VALIDATION_PLAN.md)，不能把此 Handoff、构建通过或性能 NO-GO 当闭环。WS-10/11/12 等历史效果 no-go 和 WS-13 原始 ID 不重判。

9. **CONTEXT SNAPSHOT：** WS-23 新源码及两格协议已本地冻结，实验仍未运行。先切 Luna High，再新 SHA build/单测和无损、压力格；终态 raw 回传后切 Sol High 分析。正确性完成前 WS-23 ACTIVE，隔离性能矩阵关闭；若失败必须在新 SHA/ID 下持续修复复验。
