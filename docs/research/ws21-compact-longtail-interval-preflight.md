# WS-21 v2 长尾反馈间隔技术矩阵预飞行表

原计划日期：2026-09-29（Sol High 分析阶段）；执行及复核完成：2026-09-30。此表保留当时预注册的**反馈传输成本**矩阵及后续执行记录，不是选路效果实验。原有“条件性 GO、尚不可启动”均为启动前历史条件，实际五格已完成；终态见文末及[长尾报告](ws21-compact-longtail-interval-report.md)。前置分析见 [40 流 Sol 报告](ws21-compact-40pair-sol-report.md)。执行以 `docs/REMOTE_EXPERIMENT_WORKFLOW.md` 为准。

## 固定版本、输入与实验臂

- 个人分支：`feature/ws21-downstream-feedback`。旧 40 流小样源码为 `91f43c70bbb515ae35b3161d4d1e40d30ff90992`，其单测收据 `20260929-192700-ws21c-v2-unitfix` 的 `devices-point-to-point` 已 PASS；但该 SHA 的部分协议边界保护仅在断言中，优化构建不能据此放行长尾。五格须统一固定为**修正源码 SHA `2c14d3b4c952a9cece89a9de14216709b604706f`**，优化模式、每格独立源码构建 `-j2`，不得混用旧 SHA 或后续文档 HEAD。
- 长尾 trace：`config/ws19_ws17_seed20261701_tor_hotspot_b192.txt`，SHA-256 `9996372ea22158ca995937c727b6fef20559e0ce910b22e77529d9a8061b0cc3`；16,576 条流、1,744,830,464 B。拓扑：`config/topo_1280_400G_400G_OS1.txt`，SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。两份文件在本地重算并与旧原始 metadata 对照；远端 build 后须再从结果快照核对。ns-3 seed 固定 1；不得重新生成 trace。
- 公共命令参数：`--lb ws18 --simul-time 0.01 --netload 10 --bw 400 --buffer 9 --topo topo_1280_400G_400G_OS1 --cdf AliStorage2019 --flow-file ws19_ws17_seed20261701_tor_hotspot_b192.txt --pfc 0 --irn 1 --ws13-diag 1 --ws18-admission 0 --ws18-path 0 --ws18-admission-rate-gbps 400 --ws21-identity 1 --ws21-port-events 0 --max-concurrent 1`。其余保持脚本默认值；每格仅改 `--ws21-feedback` 和 `--ws21-feedback-interval-ns`。

| 次序 | 预留 ID | 反馈 | 聚合间隔 | 目的 |
| ---: | --- | ---: | ---: | --- |
| 1 | `20260929-221000-ws21c-v2-tail-off` | 0 | 10 µs（关闭时无效） | 新源码同输入基准；先核对旧 v1 off 指纹 |
| 2 | `20260929-221100-ws21c-v2-tail-10us` | 1 | 10 µs | 新头长尾传输与资源 pilot；异常即停 |
| 3 | `20260929-221200-ws21c-v2-tail-20us` | 1 | 20 µs | 降低更新频率的开销与陈旧度 |
| 4 | `20260929-221300-ws21c-v2-tail-40us` | 1 | 40 µs | 更低通信开销候选 |
| 5 | `20260929-221400-ws21c-v2-tail-5us` | 1 | 5 µs | 报文最密集的资源压力格，最后运行 |

这些 ID 在计划时本地 `results/` 均不存在；**远端空闲性尚未核对**，不得凭表中时间戳假定实际启动时间。每格独立 build/run、metadata、raw、资源 watcher 和下载目录；任何已有 ID 均停下另立新表，不覆盖。`build` 必须传 `--source-sha 2c14d3b4c952a9cece89a9de14216709b604706f`；文档提交不会改变仿真源码。

## 启动前与运行中的安全门槛

新 SHA 的独立 optimized 构建与单测 ID `20260929-222000-ws21c-v2-guard-unit` 已保留，但第一次测试构建漏传 `--enable-tests`，生成的 runner 没有测试可执行；其测试日志为空，因此**不算测试通过，也不复用此 ID**。修正后的完整构建/单测使用新 ID `20260929-222500-ws21c-v2-guard-unitretry`，只用于构建、`devices-point-to-point` 单测和日志/资源收据，不启动仿真；随后单测通过才运行 40 流回归：首次 off ID `20260929-223000-ws21c-v2-guard-off40` 保留为无资源收据的 SUCCEEDED 结果，不复用；新的 off retry ID 为 `20260929-223200-ws21c-v2-guard-off40-r1`，on ID 为 `20260929-223100-ws21c-v2-guard-on40`。retry ID 的本地和远端 runs/results 均检查为空闲。启动 watcher 时使用该格隔离源码内的 `runs/<ID>/source/scripts/ws11_resource_watch.py`，并确认生成 resource-samples 与 resource-summary 后才继续。retry ID 在本地与远端结果目录、已版本化记录中均未发现占用；远端其他预留 ID 仍须在 Luna High 启动前逐一确认。`build --id` 对 retry 与两个回归格均显式传 `--source-sha 2c14d3b4c952a9cece89a9de14216709b604706f`。单测使用独立测试输出目录，并执行 `./waf configure --enable-tests --build-profile=optimized --out=build-ws21-tests` 与 `./waf --out=build-ws21-tests -j2`，随后直接运行测试 runner 的 `devices-point-to-point` suite 并保存 verbose 日志；若遇既有 core 测试 const 问题，只在该隔离副本临时同时修正声明和定义，测试后恢复并校验固定源码。off/on 两格沿用[旧 40 流预飞行表](ws21-compact-40flow-preflight.md)的同一 trace、拓扑、seed、命令参数和资源采样，仅更换固定源码 SHA；不得复用旧格结果。

若测试构建、运行器或单测失败，保留该 ID、源码副本和日志，不启动 off/on；诊断后先在本表登记新的未占用 unit ID，再以新隔离副本重试，绝不覆盖或复用失败 ID。本次 `222000` 因测试模块未启用而保留，retry `222500` 通过；首次 `223000` 因资源观察器未启动而保留，使用新的 `223200` off retry。若修复需要修改受版本控制的仿真源码，则先提交并固定新 SHA，同时重新登记 unit、off/on 与后续长尾格 ID，旧 SHA 的所有预留格不得继续使用。远端任一预留 ID 已占用时同样先修订本表，再启动对应格。

Luna High 实际生效后，先只读核对服务器健康、他人作业和三个前置 ID 的远端空闲性；通过后对新固定源码做隔离 optimized 构建与 `devices-point-to-point` 单测，再以**同一 SHA**重跑 40 流 off/on 最小回归：两格均 40/40 完成、字节守恒、跨 ToR 身份正确；开启格报告全送达、逐跳守恒且无非法生成/解码，关闭格无报告。逐流 FCT 和 WS18 与旧 40 流 pair 配对列出变化；若变化，先解释并暂停长尾，不把旧 SHA 的结果直接当新 SHA 门槛。必要时加短包拒收定向验证；未覆盖时在最终报告标明。上述收据填入本表后，再次只读核对服务器登录/他人作业、现有 ns-3 和 `run.py`、CPU、load 1/5/15 分钟、可用内存及磁盘，逐个确认远端 ID 不存在。预检要求无他人作业、1 分钟负载 ≤10、可用内存 ≥32 GiB、工作区磁盘 ≥100 GiB。固定源码须已同步、个人 origin 与本地文档 HEAD 一致、工作树干净且服务器健康。编译和仿真串行，`max-concurrent=1`；第一、二格作为长尾资源 pilot，后续不自动提并发。

每格启动立即保存 PID、UTC 开始时间、固定 SHA/输入哈希和预期首次检查时间（+10 分钟），启动 `scripts/ws11_resource_watch.py <ID> --interval 2` 静默采集 `resource-samples.jsonl` 与 `resource-summary.json`，两文件不得预先存在。正常长时运行约每 30 分钟精简监督一次；若先完成或失败，及时处理。运行中出现他人作业、load1m >20、可用内存 <16 GiB、空闲磁盘 <100 GiB、进程树 RSS >8 GiB、任一文本日志 >50 MiB、资源收据缺失或构建/仿真失败，停止启动后续格并保留原始数据；先诊断，不复用失败 ID。

## Luna 阶段执行记录（2026-09-29）

服务器预检通过：`ns3host` 上无登录用户、无 active simulation PID；可用内存约 123 GiB、工作区可用磁盘约 5.7 TiB；预留 ID 逐项核对为空闲。遗留 VS Code 调试辅助进程及 `hg outgoing` 均为数月龄、0.0% CPU，不是运行中的仿真或构建。

`20260929-222000-ws21c-v2-guard-unit`：固定 SHA `2c14d3b4c952a9cece89a9de14216709b604706f` 的 optimized build 为 `BUILT`。第一次独立测试输出目录漏加 `--enable-tests`，runner 没有注册 suite、测试日志为空；此格保留，不作为测试通过证据，也不重用。`20260929-222500-ws21c-v2-guard-unitretry`：显式 `--enable-tests` 重建后，runner 列表包含 `devices-point-to-point`，verbose 运行返回码 0，输出 `PASS devices-point-to-point`、`PASS PointToPoint` 和 `PASS WS-21 feedback header serialization and validation`。临时 `CommandLine` const 兼容改动已恢复，源文件 SHA-256 与原值一致，隔离源码树干净。资源采样 259 点，进程树峰值 730.8 MiB、最低可用内存 122.32 GiB、最低磁盘 5,685.46 GiB、最大 load1m 2.1；收据在远端 `results/20260929-222500-ws21c-v2-guard-unitretry/logs/`。

`20260929-223000-ws21c-v2-guard-off40`：固定 SHA、trace SHA `4e7d0e6a…` 和拓扑 SHA `74a6f715…` 的 off 仿真为 `SUCCEEDED`，结果已 fetch 至本机。资源观察器启动时误用了代码缓存目录中的脚本路径，日志明确记录脚本不存在；因此没有 `resource-samples.jsonl`/`resource-summary.json`，该格违反资源收据门槛并保留。

`20260929-223200-ws21c-v2-guard-off40-r1`：正确启动隔离源码内的 watcher 后 `SUCCEEDED` 并已 fetch。独立核验得到 40/40 FCT 与 WS18 记录、33,849,344 B 守恒、40/40 跨 ToR 身份正确，资源收据 86 点、峰值进程树 RSS 4,544.34 MiB、最低可用内存 118.59 GiB、最低磁盘 5,684.40 GiB。与旧 SHA 40 流 off 的 FCT/WS18 SHA-256 完全相同（`0f8fd036…` / `bc7004a6…`），确认边界保护修复未改动本次 off 行为。

`20260929-223100-ws21c-v2-guard-on40`：同一 SHA、trace、拓扑、seed 和公共参数，仅开反馈；`SUCCEEDED` 并已 fetch。off/on 均 40/40 流、33,849,344 B 守恒、40/40 跨 ToR 身份正确，FCT 与 WS18 SHA 分别相同。开启格 223/223 报告送达，拒收/过期/逐跳拒绝/序号缺口为 0，逐跳入队/出队各 446、逐跳字节 26,760 B、最大样本年龄 9.838 µs、缓存峰值 8；资源 82 点、峰值进程树 RSS 4,544.10 MiB、最低可用内存 118.57 GiB、最低磁盘 5,683.40 GiB。双格机器核验摘要见[40 流 guard pair](evidence/ws21-compact-guard-40pair-verification.json)。新 SHA 40 流门槛通过，可进入长尾 off 与 10 µs pilot；效果矩阵仍不开放。

## 逐格核验与停止规则

所有格须 `SUCCEEDED`，同 SHA、trace、拓扑、seed 和公共参数；按 16,576 条输入逐 ID 全完成、1,744,830,464 B 守恒、WS18 需求/释放/完成时序和 16,205 条旧观察到的跨 ToR QP 路径身份无错。关闭格不应生成反馈；开启格要求 `generated>0`、`delivered≤generated`，逐跳入队/出队计数与字节守恒，样本时间、生成时间、送达时间可解析且非未来，缓存峰值 ≤16,384。只要出现解码/路径归属/守恒错误、资源收据缺项或报告计数无法解释即停止后续格。若出现丢失、过期或序号缺口，先记录为传输事实并暂停后续格，查明是否被明确计数和安全退回；不能把无报告当成零拥塞，也不能直接宣称整个研究机制不合理。

第一格先与旧 v1 同输入 off `20260929-170600-ws21-feedback-longtail` 比对 FCT/WS18 指纹；若不同，分析源码差异，不启动后续。第二格确认 v2 报文字节、生成/送达、年龄、日志与 RSS 后再进入其余间隔。`ws13-diag=1` 与旧长尾 pair 相同，但无新端口事件原始日志；无须把旧 v1 29,388 份报告当作新版本的预期值。旧版同报告数下 v2 逐跳成本 6,355,440 B 只是静态算式，不能代替新实测。

每格回传后按相同 QP 键配对 off，列出改善/变差/不变数、全部与 8 KiB/8 MiB 分组 P50/P90/P99、MoE 8 轮完成均值/最大、192 条背景流 P99/最大；同时列实际报告数、每份仿真包字节、交付/逐跳总字节、逐跳字节/应用输入字节、报告传输年龄和样本年龄、资源峰值/最低余量、墙钟与日志大小。FCT 或 WS18 哈希变化是需解释的业务扰动，不自动构成技术错误，也不能写成反馈选路收益。统计单位只有一个固定需求 trace，不把 16,576 条流视为独立重复；业务 SLO 尚未给出。

收束时只报告新鲜度、业务扰动、通信与资源的 Pareto 非劣集合，不宣布唯一最优间隔。即便技术格通过，缓存尚未用于决策，仍缺候选质量区分、决策时可用率及 `adopted/fallback` 计数，**效果矩阵继续 NO-GO**。局部 HELLO/ACK 是另一独立阶段，先小拓扑故障注入再合并，不把心跳字节计入 STATE 压缩收益。所有终态 raw 和资源收据核验后实际切回 GPT-6 Sol High 分析。

## 矩阵执行与门槛复核（2026-09-30）

长尾关闭格 `20260929-221000-ws21c-v2-tail-off` 与旧版同输入关闭格 `20260929-170600-ws21-feedback-longtail` 的 FCT/WS18 SHA-256 完全相同：`964b7f757f93397d56f2ab1434aa4647dfc4b23d083ecd08ef6486fac7f0e18f` / `e12ab3388a27f2ccec9b85acf1d590680816e7b7d91a9e22b90e2a9e58e5fbab`。新版本关闭行为一致，允许进入间隔 pilot。

随后固定 SHA `2c14d3b4c952a9cece89a9de14216709b604706f` 依次完成 10 µs、20 µs、40 µs、5 µs 四格，ID 分别为 `20260929-221100-ws21c-v2-tail-10us`、`20260929-221200-ws21c-v2-tail-20us`、`20260929-221300-ws21c-v2-tail-40us`、`20260929-221400-ws21c-v2-tail-5us`。四格均 16,576/16,576 全完成、1,744,830,464 B 守恒、16,205/16,205 跨 ToR 路径身份通过，资源观察器收据与全部 raw 均已回传；峰值进程树 RSS 约 4,544 MiB，最低可用内存约 118.58 GiB，最低磁盘余量约 5,678 GiB。关闭格与开启格的需求和放行时刻一致，但 13,357–13,990 条流完成时刻有变化，属于共享队列通信扰动，不是选路收益。

5 µs 格生成 46,784 份报告，46,769 份在 10 µs 有效期内更新缓存，15 份超过年龄门槛而被明确计为过期并在缓存更新前丢弃；生成量等于送达量加过期量。无解码/路径拒收、逐跳拒收或序号缺口，逐跳收发守恒。该情况出现在矩阵最后一格，故不再启动其它间隔。它不证明缓存用于路由时的安全回退，因为路由选择仍未消费该缓存。

完整原始数据和 Sol 配对复核见[WS-21 精简反馈长尾间隔报告](ws21-compact-longtail-interval-report.md)及[机器摘要](evidence/ws21-compact-longtail-interval-analysis.json)。5 µs 因存在过期报告而不满足零过期条件；10/20/40 µs 为零过期候选，但控制字节和窗口末样本年龄各有取舍。严格要求最大样本年龄 ≤20.000 µs 且零过期时，本次最低成本档为 10 µs（6,452,040 逐跳字节）；若仅举例允许 ≤20.5 µs，才是 20 µs（4,534,680 逐跳字节）。这两个年龄上限都不是已核验业务 SLO，不能宣布唯一最优。反馈选路效果矩阵仍 NO-GO，缓存决策接入、采用/回退计数、业务 SLO 和局部 HELLO/ACK 心跳均未实现或测试。
