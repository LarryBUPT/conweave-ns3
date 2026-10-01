# Handoff 52：WS-23 v2 远端启动前核验

1. **本对话目标：**按用户继续执行指示启动延期 v2 双格；固定源码、输入、先对照后探针和验收门槛不变。本轮停在正式远程构建前的监督模型与孤立进程确认边界。

2. **已确认的项目事实：**本地分支 `feature/ws23-validation-execution` 的 `HEAD` 与个人 fork 同步为 `c76da735cee70edd4e245e61a6f0d3a6cbce9196`；仿真源码固定祖先为 `94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1`，两份输入/拓扑 hash 沿用[预飞行协议](../research/ws23-deferral-v2-preflight.md)。新 ID `20261001-150000-ws23-rto-v2-control` 与 `20261001-150100-ws23-rto-v2-probe` 通过本地 `remote_experiment.py`、`remote_worker.py`、资源观察器的格式校验，本地和远端均未见同名结果。

3. **已完成工作：**只读运行远端 `check` 与 SSH 进程/目录检查。主机 `ns3host`：load1m 0.0、可用内存 122.99 GiB、`/home/fnl/lzy` 可用磁盘 5659.3 GiB；运行器识别的仿真 PID 为空，`waf build`、`network-load-balance`、远程 worker build/run/execute 无进程，`who` 无登录会话。已安装 worker SHA-256 为 `b2454dda0b2f8a1e49f70a956b39a75fcd8bda9a661198cc6bd04f31615ce6c1`，不含 `--ws23-pfc-probe-drop-gated` 与 `--ws23-pfc-probe-refresh-ns`，不能承接冻结的探针命令。

4. **需协调的远端状态：**完整进程列表另有 `fnl` 用户 PID `377959`：`/usr/bin/python /usr/bin/hg outgoing -q`，运行约 277 天，当前工作目录 `/home/fnl/ntlpy/ns-3-win2 (deleted)`，CPU 占用为 0。它不是仿真或构建进程，但所属任务未知；未终止，也未替换共享 worker。已请用户确认该进程是否为已知遗留项并可原样保留。远端 worker 更新仅在确认 WS-24 不使用共享入口及上述进程状态可接受后进行。

5. **当前状态：**本轮没有部署、构建、单测或仿真。当前工具列表没有切换本任务模型的接口；项目工作流要求后台实验实际使用 GPT-6 Luna High。已请用户在 Codex 中切换监督任务并回复后继续，尚未把文字提示当成切换证明。

6. **未解决问题：**需确认孤立 `hg outgoing` 进程归属，并在模型实际切换为 Luna High 后，确认共享 worker 可安全更新、运行冻结源码的 optimized 构建与必要单测。远端资源和两个 ID 当前检查通过，但实际实验启动时仍须重核。动态延期与同 SHA 对照均没有新 raw。

7. **后续推荐动作：**收到用户对孤立进程的处理意见且监督线程切至 Luna High 后，再确认 worker 更新边界；部署固定源码中的 worker 到 `/home/fnl/lzy/.research-workflow/remote_worker.py`，复核 SHA 与参数支持；按[预飞行](../research/ws23-deferral-v2-preflight.md)构建 control、READY 观察、运行、收正 RSS 收据并回传 raw。只有 control 满足原有输入、161 次准入丢包、源 14 的 36 次丢包和固定 FCT SHA 后，才启动 probe。任何失败保留记录并停止后续格。

8. **与其他工作流的关系：**远端实验根目录仍仅限 `/home/fnl/lzy`，个人 fork 是唯一可写 remote。WS-24 没有启动下一批 14 格的说法来自当前任务交接，但本轮仍须以共享入口使用协调和远端实际状态为准。跨类 PFC=0 四因果格保持独立必做项，本轮不自动启动。

9. **CONTEXT SNAPSHOT：**延期 v2 固定源码 `94f08c6e83fcef7f5374c6e0e5e4286f0cdbc6a1` 已推送；新合法 ID 为 `20261001-150000-ws23-rto-v2-control`、`20261001-150100-ws23-rto-v2-probe`。远端只读资源检查通过，未见仿真/构建，两个 ID 空闲；现有 worker `b2454d…` 缺两项 probe 参数，启动前需在协调后更新。还发现长期孤立的 `hg outgoing -q`（PID 377959、删除目录、0 CPU），等待用户确认。当前工具不能切本任务模型，Luna High 监督切换等待用户操作。没有远程修改或新实验；WS-23 ACTIVE。
