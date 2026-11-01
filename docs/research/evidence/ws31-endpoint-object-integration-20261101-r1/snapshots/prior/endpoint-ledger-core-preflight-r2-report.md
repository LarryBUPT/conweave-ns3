# WS-31 端点证据核心 r2 独立工程预检

日期：2026 年 11 月 1 日。状态：COMPLETE FOR PORTABLE CORE PREFLIGHT；WS-31 真实端点与业务验证继续 ACTIVE。本次按[冻结计划](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/main/endpoint-ledger-core-preflight-r2.json)完成独立审源、新门、一次同步、隔离来源核验、一次编译、一次运行和原始证据回传。

## 1. 结论

固定源 `20bc2d9f7c7c435bf832ba2fcaf0e07df00cf5da` 的可移植端点证据核心预检通过。两代请求均完成 Launch、精确累计 ACK、退役、排空与清理的账本流程，共闭合 6 个 token，旧代身份和原需求／放行／完成时间保留。实测记录为编译退出 0、运行退出 0、stdout 与冻结预期逐字节一致、stderr 为空。

该结果验证手工快照下的证据逻辑。真实端点快照为 0，网络运行、全量 NS-3 构建、worker 部署和旧测试重跑均为 0；实际对象、队列、事件、完成历史清理及双代网络正反例仍须接线验证。

## 2. 来源和静态审查

源分支为 `feature/ws31-candidates`，父源 `1f917f44fcfb88e61f3ad22c5cc75fa3a06b6c0e`。本地工作树前后干净；个人 origin 的实际分支通过 `git ls-remote` 核到新 SHA。相对父源仅新增以下两文件，未修改运行路径、Waf 注册或候选策略。

| 编译输入 | SHA-256 |
| --- | --- |
| `src/point-to-point/model/ws31-endpoint-ledger.h` | `105b7ced338b85e12ddb87f0235ab9bfff1ac0444a34584a9127cb6cbe944524` |
| `tests/ws31_endpoint_ledger_test.cc` | `da24c329cff2c8e118fe19653e9b76a1926fd9a295b55009a11b4b7a0765ba49` |

完整 Git 树共 4845 项，`git ls-tree -r` 原始输出 SHA-256 为 `3da8acbcc1809389aac24adc1936d22874821077e40ddd397723fa7d977e0e64`。隔离副本逐文件校验 Git blob 和实际字节，共 284,683,832 B；运行后全部文件 SHA-256 再核不变。[来源清单](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-raw/remote-results/provenance/source-files.json)和[静态审查](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-raw/local-static-review.json)保留核验过程；[固定核心输入](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-raw/frozen-source)保存两份实际编译输入副本。

审源未发现阻止本轮核心编译的材料或源码问题。r1 的事项逐项对应如下。

| 事项 | r2 已核实现／政策 | 本轮证据范围 |
| --- | --- | --- |
| R1 实际资源别名 | 节点与 packed TX／RX 键、交换机四元组分别登记所有者，跨 tuple 别名在登记前拒绝 | 测试核 dport 100／103 的 packed 别名及仅 PG 不同的交换机域冲突；键表达式是固定源镜像，后续须与真实函数对照 |
| R2 队列组完成位 | 契约采用保留已完成旧 QP、追加新 QP；生产 Clear 未修改 | 本轮没有操作生产 QP 组或证明真实 finished 位分支；接线后仍须覆盖 |
| R3 快照与复用 | 绑定 flow_id、tuple、generation、观察时间、八类字段及资源所有者；合法 false 观察推进时钟；检查历史、交换机状态和最终旧代新快照 | 测试覆盖身份／时刻／字段拒绝、非零设备／队列、RX 复活、历史与表项残留；ALL 是调用方声明 |
| R4 闭合来源 | serial、UID、flow_id、四字段定向链路、kind 与合法 reason 同时校验 | 测试错误接口、身份、serial、类别、原因和重复闭合；held 明确是未入网副本丢弃 |

当前合同限定为清理后到达的新需求及完成型请求，不支持先到需求排队或取消终态；原需求不后移。token 的独立 serial 区分同 UID、同链路重复发送、下一跳发送及 held copy。来源与结论符合[r2 契约](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/main/endpoint-lifecycle-design-r2.md)。

## 3. 新门、同步与隔离

新 ID 为 `20261101-163000-ws31-endpoint-core-r2`。首次及同步前均确认 runs/results 中没有该 ID；回传目标也在传输前确认不存在。远端缓存 origin 为个人 fork，工作树干净，初始没有新提交，因此执行一次已部署 worker 的合规 sync，退出 0，无重试或 bundle 回退。worker 字节经换行归一化与固定源一致，未部署新 worker。缓存工作树 HEAD 保持 `236a801a00e35de9078635e04acae2f701c21ded`，仅取得新 Git 对象和分支引用。

进程门保留所有用户的 `/proc` 与 ps 快照，核对父进程、命令、可读 cwd、UID 和开始标记。未发现其他普通用户作业、活动项目驱动、Git HTTP helper、仿真或编译。旧 driver 22440 不存在。长期休眠的 OpenDebugAD7 和 PID 377959 的 hg 位于本项目之外，其 UID、父进程、cwd 与此前默认回归收据相符；本轮重新检查其休眠状态，无信号或进程终止动作。Windows 仅有已知 ElectricBillMonitor 的 pythonw 进程，无遗留 SSH／scp／项目驱动。

初始采样的 1 分钟负载为 0.08，可用内存约 122.5 GiB，磁盘约 2292.1 GiB，满足负载不超过 4、内存至少 64 GiB、磁盘至少 100 GiB 的门槛。隔离副本使用新 ID 的 source 目录，输出在 source 之外。来源建立、编译前及运行后均重新核门；这些是离散采样收据，不宣称连续系统峰值。

## 4. 唯一编译和运行

工作目录为 `/home/fnl/lzy/runs/20261101-163000-ws31-endpoint-core-r2/source`，完整环境见[精确环境](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-raw/remote-results/provenance/exact-compile-run-environment.json)。编译器为 `g++ (Ubuntu 5.4.0-6ubuntu1~16.04.12) 5.4.0 20160609`，实际编译命令如下。

```text
g++ -std=c++11 -O2 -Wall -Wextra -pedantic -DNDEBUG tests/ws31_endpoint_ledger_test.cc -o /home/fnl/lzy/results/20261101-163000-ws31-endpoint-core-r2/artifacts/ws31_endpoint_ledger_test
```

运行命令仅为上述新二进制的绝对路径，运行一次。标准 assert 关闭，测试依靠 Require 与异常检查。原始 stdout 为：

```text
WS31_ENDPOINT_LEDGER PASS requests=2 completed_generations=2 closed_tokens=6 real_endpoint_snapshots=0 network_runs=0
```

| 操作 | 次数 | 退出码 | stdout／stderr | wait4 子进程最大 RSS |
| --- | ---: | ---: | --- | ---: |
| 新核心编译 | 1 | 0 | 均为空，无警告 | 122,944 KiB |
| 新核心运行 | 1 | 0 | stdout 精确符合冻结值；stderr 为空 | 10,232 KiB |

编译发生于 UTC 08:15:56～08:15:57，运行于 UTC 08:15:57；本地时间为 16:15。资源数值只描述本次工程预检，不作为候选算法运行成本或性能结论。编译器版本、目标、cc1plus、汇编器、链接器及其指纹见[工具链](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-raw/remote-results/provenance/toolchain.json)；5 项实际运行库及加载器路径与哈希见[运行库](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-raw/remote-results/provenance/runtime-libraries.json)。版本和库查询不执行测试主体，不计为第二次编译或核心运行。

编译器二进制 SHA-256：`a98ee2dd501beee05b3d10d5acd6deb3a75471c5be2b5c92a94f9fd24808ff62`。新测试二进制共 50,520 B，运行前后及回传后 SHA-256 均为 `15ed3dd0a023e59da058535e29797d7c67787912a619203ad2ee96e108dac86b`。[编译收据](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-raw/remote-results/provenance/compile-result.json)、[运行收据](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-raw/remote-results/provenance/run-result.json)含完整 argv、cwd、环境、时间、退出状态、日志哈希和资源使用。原始[stdout](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-raw/remote-results/logs/run.stdout)与[stderr](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-raw/remote-results/logs/run.stderr)均已回传。

## 5. 完整性与约束释放

回传清单的 41 项文件逐一核验大小与 SHA-256，完整 Git 树与本地冻结树逐字节相同。[回传完整性](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-raw/fetched-integrity.json)确认没有本地二进制执行或覆盖已有目标。r1 的三份独立交付与两份封存 WIP 共 5 项原字节未变；新实现 HEAD、两份输入及计划哈希前后不变。

最终门确认来源进程 307479、执行驱动 307553、编译进程 307587 和测试进程 307592 均不存在；全部同步、来源建立、编译／运行、回传和最终 SSH 调用已经终态。[显式释放收据](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-guards-released.json)已释放本目标源码、入口和环境约束，没有遗留后台驱动或下一项执行授权。

## 6. 参考借鉴复核与后继

本重要节点从候选 README 和 reading-log 定位 DiffFlow，复核 arXiv:1604.05107v1 的技术附件与核验记录。借鉴点是前置状态完成后才启用后续行为的顺序约束，适用于本账本分开记录完成、退役、排空、清理和复用。该文缺少充分的安装确认、结束检测和回收协议，不能证明本核心或真实 RDMA 复用正确。其分类喷洒、简化传输和独立队列与本项目端点证据机制不同，平均 FCT 不外推为 MoE 批次或背景 P99 收益。本轮未新增机制或对照；详细范围见[参考复核](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-reference-review.json)。

后继仍由主对话承担：真实端点／设备／队列／事件快照与标签检查、默认关闭且在 Receive 返回后闭合的原事件 token、旧 QP 保留追加及 finished 位真实分支、实际历史与交换机清理收据，以及另行冻结的 G1 和双代网络正例／拒绝例。独立 C1 V0、三候选双侧效果及状态／运行成本继续必做。Ofan 专门工作、WS-29、旧控制器和旧矩阵均未开展。

[索引](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-index.json)提供完整证据指纹，[QA](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-qa.json)记录本轮验收，[九节交接](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-handoff.md)供主对话继续集成。本节点的核心预检完成不替代 WS-31 全部任务闭环。
