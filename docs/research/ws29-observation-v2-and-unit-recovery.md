# WS-29 观测修补与单测恢复协议

2026 年 10 月 22 日。状态：本地材料已固定，等待主对话审核和远端恢复 GO。当前阶段未使用 SSH，未启动仿真。

## 1. 固定版本与 ID

观测版仿真源码固定为 `3e68b3604e93cf34a4d938ebb48f1b1e0cfc988f`，前版为 `526802e6b25635435aba960d821e8e5561ebb50a`。本次只补充证据与验收，不修改候选评分、候选盐、QP 决策粒度、需求时序、故障安排、STATE/HB 间隔或 TTL。候选仍为 v1；按主对话决定，本次不消耗机制修正名额。

新 [27 格计划](evidence/ws29-engineering-plan-observation-v2.json) 的 SHA-256 为 `5db623e7b38109a43ef0c37e0203e29713c896fe61e4d44581fd9512b551e8fd`。ID 前缀为 `20261022-180000-ws29-obs2-`，与旧计划的 27 格全部分离。新计划保留原输入、拓扑、seed、臂、故障和验收门槛，另明确记录每格须传入的控制开关与间隔。

单测恢复使用此前拟定但尚未执行的独立 ID `20261022-173000-ws29-eng-unit-compat-r1`。[新兼容契约](evidence/ws29-unit-compat-observation-v2.json) 将 source SHA 改为上述观测版，并保留旧 SHA 与首个失败 ID。远端 ID 空闲性须在实际切换至执行模型、收到恢复 GO 后核验。本地未发现这些新 ID 的既有结果。

## 2. 首次失败的事实

`20261022-150000-ws29-eng-unit` 对旧版固定源码完成了常规 optimized 构建，耗时 5 分 46.264 秒。启用测试的独立构建在 1,489/1,636 个目标处被既有 core 测试辅助函数阻断：`Parse(const CommandLine&, ...)` 调用了非 const 的 `CommandLine::Parse`。`devices-point-to-point` suite 未启动，终态为 `UNIT_FAILED`。

该 ID 的原始日志、元数据和资源收据已保留并回传，五个文件的本地与远端 SHA-256 均匹配。167 个资源样本记录峰值进程树 RSS 901.5 MiB、最低可用内存 121.81 GiB、最低磁盘 3,847.01 GiB、最大 1 分钟负载 2.15。该失败 ID 不复用。

## 3. 五类验收补强

| 验收项 | 本地实现与证据要求 |
| --- | --- |
| 参数与实际运行配置 | 逐格核对 metadata 与最终 config 的 arm、fault、ToR、port、起止时间、identity、STATE/HB 开关和间隔、seed、PFC/IRN；新增 `WS29_SETTINGS` 回显实际参数和 20,000 ns TTL。 |
| 联合控制成本 | 按交换机、端口、报文类型分别累计 enqueue/dequeue/queued drop 的包数和实际字节，拒绝空账本冒充正常 K4；与 `WS29_COUNT`、事件行数、STATE/HB 全局计数对账。准入拒绝与未生成的 ACK 单列；未生成报文的线上字节为 0。C0 禁止任何控制事件或计数，STATE-only 禁止 HB。 |
| 自然资格与真实缓存 | 按生产 ToR、源 ToR、候选、session、sequence、时间窗、CE 和样本数，把实际 SEND、CACHE 和决策连接起来。自然合格决策必须使用此前最新且未被 session/link 事件清除的缓存，并有当前活动 epoch 的新鲜 ACK。仅 fault 10、15、16、17 的显式合成缓存单列豁免 SEND 来源；ACK 注入格和 rollover 格仍要求真实 SEND。 |
| ACK 与生命周期 | `WS29_ACK_CHECK` 记录接收处理前后的 lastAck、missed、outstanding、epoch 及接受/拒绝原因；注入记录另保存无效报文前后快照。重复例先验收唯一有效 ACK，再验收重复报文不改状态。旧 timer 按 scheduled/current epoch 或 session 逐条核对；重启须恢复实际有效 ACK。rollover 须有旧生产会话、递增会话的 sequence=1 SEND 及匹配 CACHE；拒旧另由 fault 10 的实际拒收记录覆盖。 |
| 历史 reference | 重算旧 metadata、config、trace、topology、FCT 的固定哈希，并比对旧 metadata 的 SHA、seed 和完整参数；新 C0 仍须完成逐字节 FCT 回归。 |

实现入口为 `scripts/verify_ws29_engineering.py` 与 `scripts/ws29_evidence_checks.py`。缺日志即拒收，不由决策自报的 valid、注入计数或 rollover 计数替代。字段定义见 [观测 schema](evidence/ws29-observation-schema-v2.json)。原 500,000 条 WS29 事件、20,000 条 HB 事件、50 MiB 文本日志门槛保持不变；任何溢出或越界均拒收。

## 4. 测试兼容修补与恢复

仅在新 ID 的隔离源码副本中，临时修改 `src/core/test/command-line-test-suite.cc` 的声明与定义两处签名：`Parse (const CommandLine &cmd, int n, ...)` 改为 `Parse (CommandLine &cmd, int n, ...)`。精确差异见 [patch](evidence/ws29-unit-compat-observation-v2.patch)。

原始与恢复后的文件 SHA-256 必须为 `b7285686202442d47d339fd5817e9001c47bfc23377c8a8f5f596ba694373881`；临时修补后的文件必须为 `3c474633f4545bc10c3fede9e8fbaddd83e5526bd19597ed19be509a4537cd99`。观测版 core 原始 blob 与前版相同。

runner 先完成未修补源码的常规 optimized 构建，再归档原始字节和精确 diff，应用两行修补，以 `--enable-tests --build-profile=optimized --out=build-ws29-tests` 配置并以 `-j2` 构建。随后记录 suite 列表，执行完整 `devices-point-to-point --verbose`；除 suite 总体 PASS 外，PointToPoint、IRN 超时、反馈头及心跳头四项均须有 PASS 记录，反馈头用例包含 v2/v3 与边界检查。

异常与正常返回均经 `finally` 恢复原始字节，记录恢复哈希和 tracked diff。只有恢复成功且 suite 全部通过才能标记 `TESTED`。测试二进制包含已披露的两行兼容编辑；恢复源码不会改变已编译二进制，不能声称该二进制完全来自未修改源码。正式仿真必须另建无修补的固定 SHA 源码副本。

恢复 GO 后的预定命令如下，当前尚未执行：

```powershell
python scripts/remote_experiment.py build --repo-local . --id 20261022-173000-ws29-eng-unit-compat-r1 --source-sha 3e68b3604e93cf34a4d938ebb48f1b1e0cfc988f --unit-suite devices-point-to-point --unit-compat
```

## 5. 本地核验与参考复核

12 项证据拒收测试、Python 语法检查与差异格式检查通过。3 组历史 reference 的元数据、配置、输入及 FCT 哈希已实际重核通过。`ChooseWs29Feedback` 与 `DoLbClassReserve` 函数体和前版逐字一致，config 输入文件无差异。上述结果与参考复核见 [静态审计](evidence/ws29-observation-static-audit.json)。观测版尚未完成 C++ 构建、单测或任一仿真格。

本节点重新从候选 README、reading-log 进入，核对 SGLB SIGCOMM 2025 的固定 20 页版及 CONGA SIGCOMM 2014 的固定 12 页会议版技术分析与核验记录。SGLB 的版本化状态和故障/恢复分层适用于本轮证据身份检查；本项目没有 GLB ASIC、EDK、BGP 或 SyncMesh 实现。CONGA 的源/目的叶与候选反馈映射适用于 SEND/CACHE 关联；本项目仍使用 QP 固定的双候选 ClassReserve 与全路径 CE 比例，没有改为 DRE/flowlet。两篇论文的硬件成本、故障时延和性能收益均不外推到本项目。

全部 27 格、A07-C0 新版回归和后续效果门槛仍为未完成项。单测恢复 GO 只开放构建/单测，不自动开放 27 格或独立 pilot。
