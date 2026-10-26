# WS-30 v13 模型门槛修复与正式执行准备

日期：2026 年 10 月 26 日。本节点纠正上一版把通用工作流的 High 默认套用于 WS-30 的配置回归。用户对本 WS 的具体要求优先：Luna Medium 监督，GPT-6.1 Sol Medium 分析。已修改实际代码、示例和测试，没有访问远端、推送或启动仿真，也没有创建实际授权收据。

## 1. 实际模型门槛

[执行器](../../scripts/run_ws30_v14.py)的 `MODEL_POLICY` 明确绑定 `gpt-6-luna / medium` 和 `gpt-6.1-sol / medium`。`authorize` 读取真实会话检查监督模型，并核对收据中的监督和分析模型；High、普通 GPT-6 Sol 或收据中不一致的策略均拒绝。`verify-local` 也通过真实会话检查指定分析模型，使用时须传 `--session-file`。`inspect` 保持默认本地只读。

[示例](evidence/ws30-v14-execution-authorization.example.json)仍为 `approved=false`、空阶段列表，仅更新模型字段和控制文件哈希。新的授权策略测试使用内存 mock，不创建假授权文件。本地实际分析上下文已核验为 GPT-6.1 Sol / Medium，见[离线收据 r2](evidence/ws30-v14-executor-offline-audit-r2.json)。运行器不负责切换实际模型，后续仍须由主对话使相应设置生效。

## 2. 旧源正式格的实际命令链

[命令审计](evidence/ws30-v13-formal-command-compatibility-r1.json)保存全部 168 格的 source SHA、实际 controller 参数、worker RPC 参数和最终 `run.py` argv。审计在本地调用真实 controller 和 worker 的参数解析，拦截 RPC/start 边界；随后只执行 worker 中构造 argv 和环境的 AST 片段，不执行 `execute()`、目录创建或 `run.py`。

全部正式格仍为 `2c9f3a50bafad0740b461496ba24fa81941a9bc7`。当前 worker 与该固定源 worker 对每格构造的 `run.py` argv 完全相同，固定旧 `run.py` parser 全部接受。两个环境字典只差新增的 `WS30_LIFE_PROFILE=0`；固定旧 `run.py`、scratch 和生命周期头文件均没有读取此变量。原有 OBSERVE/LIFECYCLE/TAG_TRANSFORM 等环境值保持一致。模拟 seed 继续由旧源配置中的 `RANDOM_SEED 1` 决定。

首格为 `20261026-120000-w30v14-m-s20263021-e`，实际构造如下；这是审计记录，未执行：

```text
python3 run.py --lb fecmp --pfc 0 --irn 1 --simul_time 0.01 --netload 10 --bw 400 --buffer 9 --topo topo_1280_400G_400G_OS1 --cdf AliStorage2019 --flow-file config/ws25_seed20263021_b192.txt
```

| 新字段 | controller/worker 协议 | 固定旧源行为 |
| --- | --- | --- |
| simulation_seed=1 | 显式传入，记录 schema 3，运行后核对实际配置 | 不新增 run.py 参数；继续使用原 `RANDOM_SEED 1` |
| demand_seed | 从固定 trace 来源传入/核对，写元数据 | 不传入 run.py，不重生 trace |
| life_profile=0 | 传入 worker，并写环境变量 | 旧源不读取；生命周期模式仍为 0 |

负例确认：旧 `run.py` parser 拒绝泄漏的 `--simulation-seed`；worker parser 拒绝模拟 seed 2；正式模式 lifecycle=0 下传 profile=1 会在 start 前拒绝。19 项离线测试均通过，[静态审计 r6](evidence/ws30-v14-static-audit-r6.json)也通过。此证据确认本地命令协议兼容，真实部署 worker 的哈希握手、隔离构建与新 schema 首批验收仍待执行。

## 3. 准备状态与顺序

主对话已接受 formal lane 与持久补验的科学依赖解耦，拟优先 formal-first → formal-rest，再进行新源技术/生命周期和 W5。本节点记录该顺序，没有将它当作运行授权。阶段数、固定源码、输入和关闭的 r2 契约均未变：正式 4＋164，工程 48，W5 36；新执行为 0。

仍需实际外部同步授权、配套部署和 worker 哈希匹配、新鲜主机与 ID 冲突门槛，以及 formal-first 四格的 schema/身份/字节/资源验收。新源随后从单格和 cap 4 资格开始，不能继承旧源 cap 8。原生构建、动态观测不干扰与真实 pair/state 触发均未完成。静态兼容不替代这些门槛。

## 4. 已有数据的独立素材

[论文与回复素材](ws30-v13-existing46-paper-response-material-r1.md)单独整理了现有 46 格的标签干预、Q12 首次选择规则、持久对象/累计序号/缓存清理，以及技术输入中的两类流与恢复代价。五臂表格从原分析 JSON 直接生成；原始分析重新运行后与 r2 完全一致，202,020 条完成记录不变。素材明确区分单输入技术验证、资源重复与尚未运行的正式比较，没有改主稿或现有回复，也没有虚构审稿意见或稿件修改位置。

本次为配置与命令兼容的窄修复，未改变研究机制。文献边界沿用[执行节点参考复核](evidence/ws30-v14-executor-reference-review-r1.json)的 IRN 正式版和 SeqBalance v1；请求内部恢复、完成边界排空及 QP/WQE 的区分均未扩大。WS-30 保持 ACTIVE。
