# ConWeave 本地开发与远程实验

更新：2026-09-23。日常操作从本机 `workspace/LarryBUPT-conweave-ns3`（个人 fork 克隆）执行。源码进 Git，原始实验数据进独立结果目录。

## 1. 三处职责与当前状态

| 位置 | 用途 | 当前状态 |
| --- | --- | --- |
| Windows 本机 `workspace/LarryBUPT-conweave-ns3` | 阅读、改代码、提交、轻量检查、分析和画图 | Git `origin` 是个人 fork |
| `LarryBUPT/conweave-ns3` | 个人源码版本中心 | 已从 `conweave-project/conweave-ns3` fork；个人分支承载实验代码 |
| `fnl@10.112.14.167:/home/fnl/lzy` | 编译、仿真、原始数据 | Ubuntu 16.04.7；项目写入仅限此目录 |

`conweave-project/conweave-ns3` 和 `maplerime/conweave-ns3` 均为**只读参考**。不向它们 push、建 PR 或修改远程状态。前者是原始 ConWeave 基线，后者是从前者分出的研究型改造；后者 `main` 相对前者基线有 36 个独有提交、122 个文件差异，重点为 MoE、混合负载、MixHash、重排与统计，其大量新增行是生成流量数据。选择前者建立个人 fork，便于保持 ECMP（代码中 `fecmp`）、CONGA、LetFlow、ConWeave 可独立对照。详细差异见 `docs/research/09-maplerime-conweave-fork-evolution-report.md`（位于本论文项目根目录）。

个人克隆的 remote 固定为：

```text
origin                https://github.com/LarryBUPT/conweave-ns3.git         可写
upstream              https://github.com/conweave-project/conweave-ns3.git  只读
reference-maplerime   https://github.com/maplerime/conweave-ns3.git         只读
```

两个只读 remote 的本地 `pushurl` 都设为 `no-push://read-only-reference`，且 `push.default=nothing`。版本化的 `.githooks/pre-push` 只允许向个人仓库的 `origin` 推送，也会拦截直接指定第三方 URL 的推送；项目脚本在 push、同步和编译前再次检查 `origin` 所属者及个人开发分支。现有两份参考克隆还在各自 `.git/hooks/pre-push` 中设置了无条件拒绝钩子。人为关闭 Git hook 可以绕过保护，仍须遵守只读规则。

## 2. 一次性配置

在个人克隆内操作：

```powershell
cd E:\研\毕业论文\workspace\LarryBUPT-conweave-ns3
Copy-Item .project\remote.env.example .project\remote.env
# 只在本机把 REMOTE_HOST 填为 10.112.14.167（或已有 SSH Host alias）
python scripts\remote_experiment.py protect-fork --repo-local .
python scripts\remote_experiment.py deploy
python scripts\remote_experiment.py check
```

本机 `.project/remote.env` 被 Git 忽略，只含主机、用户和工作区路径；不放密码、Token 或私钥。SSH 使用现有 `~/.ssh` 凭据，不复制进项目。`deploy` 只向 `/home/fnl/lzy/.research-workflow/remote_worker.py` 写项目脚本；会检查真实根路径。

服务器已有 Docker 客户端，但 `fnl` 无权访问 Docker socket，因此目前采用工作区内的原生 Waf 编译。不能为 Docker 修改用户组或 daemon。默认编译 `-j2`，一次只运行一个仿真，保留 CPU 和内存给服务器其他任务。远程 Python 3.5 和 GCC 5.4 较旧；原始基线的 Waf `configure` 和完整编译已在隔离目录通过。新代码仍要逐次编译验证。

只读审计摘要：本机 Windows（12 个逻辑处理器），Git 2.54、OpenSSH 9.5、Python 3.12；本机没有 `rsync`，结果下载采用 `scp`。服务器报告 40 个逻辑 CPU（项目仍按 20 核预算）、125 GiB 内存、无 swap、约 5.9 TiB 可用磁盘；GCC/G++ 5.4、Python 2.7/3.5、Git 2.7、Make 4.1、CMake 3.17、NumPy 1.11，`tmux`、`screen`、`nohup`、`rsync` 已有。Waf 报告 GTK2、GSL、部分 Boost/OpenFlow 和 Python 绑定等可选功能未启用；原始基线编译不需要它们。若个人 idea 引入更新的 C++、Python 或可选库依赖，优先在 `~/lzy` 内建立用户级工具链；确实需要系统级安装时先停下说明影响。

## 3. 日常流程

### 本地改代码并推送个人 fork

```powershell
git switch -c feature/my-routing
# 修改代码，做轻量检查
git add <明确的文件路径>
git commit -m "Add routing idea"
python scripts\remote_experiment.py push --repo-local .
```

只在 `feature/*`、`experiment/*`、`idea/*`、`research/*` 上进行科研改动。`main` 保持稳定；基线对照始终使用固定 commit 与相同实验参数。脚本要求本地工作树干净，且同步时确认当前 commit 已在个人 fork 同名分支上。

### 同步、编译、仿真

```powershell
python scripts\remote_experiment.py sync --repo-local .
python scripts\remote_experiment.py build --repo-local . --label conweave-baseline
# 记下输出的实验 ID，例如 20260923-170000-conweave-baseline
python scripts\remote_experiment.py run 20260923-170000-conweave-baseline --lb conweave --simul-time 0.01 --netload 10
python scripts\remote_experiment.py status 20260923-170000-conweave-baseline
python scripts\remote_experiment.py fetch 20260923-170000-conweave-baseline
python scripts\analyze_result.py 20260923-170000-conweave-baseline
```

`sync` 只从个人 fork 获取已推送的 SHA。`build` 从缓存复制一个**全新、固定 commit** 的实验源码目录，Waf `optimized` 模式以 2 个任务编译；它从不切换服务器现有的 `/home/fnl/lzy/conweave-ns3` 工作树。`run` 使用独立后台进程，SSH 断开仍继续。`status` 返回 PID、状态、SHA、参数和时间。默认小实验只接受 0.005–0.1 秒仿真时间及 1–50 的负载；扩大规模前先检查资源并修改项目安全上限，不直接运行 `autorun.sh`。

### 结果和分析

```text
远程代码缓存  /home/fnl/lzy/code/conweave-ns3
远程实验源码  /home/fnl/lzy/runs/<实验ID>/source
远程结果      /home/fnl/lzy/results/<实验ID>/
              config/ raw/ processed/ figures/ logs/ metadata.txt metadata.json
本地结果      个人 fork 克隆内的 results/<实验ID>/（Git 忽略）
```

每个结果记录 Git 仓库、SHA、分支、拓扑、负载、算法、种子（当前原始 `run.py` 固定为 1）、编译模式、服务器、启动命令、开始与结束时间、状态、PID。`run.py` 的 `mix/output` 在单次实验副本中指向该实验的 `raw/`，不会覆盖另一组。`fetch` 先检查远程结果没有符号链接，再下载到本机临时目录；已有同 ID 结果时拒绝覆盖。`analyze_result.py` 在本机读取 FCT 原始数据，生成 `processed/fct_summary.json`、`processed/fct_percentiles.csv` 和 `figures/fct_slowdown.svg`，无需额外 Python 包；重复运行时不会覆盖已生成文件。论文图表记录实验 ID 和 SHA。大规模原始数据不提交 Git。

## 4. 失败与恢复

| 情况 | 日常处理 |
| --- | --- |
| SSH 断开 | 重新连接后运行 `status <实验ID>`；结果和日志仍在 `results/<实验ID>`。|
| GitHub / 下载失败 | 先区分 DNS、TLS、认证和外网；远程 `sync` 失败时在同轮最多静默执行一次 `~/lzy/login.sh` 并重试，不输出脚本内容。仍失败则停下排查，不改系统网络。|
| 编译失败 | 看 `results/<实验ID>/logs/build.log`；该 ID 保留失败记录，修复个人分支后创建新 ID。|
| 仿真失败 | 看 `status`、`logs/worker.log`、`logs/simulation.log`。`run.py` 可能吞掉子命令退出码，工具额外要求 FCT 输出非空才标成功。|
| 结果同步失败 | `fetch` 保留本机 `.incoming-<实验ID>-<PID>` 临时目录；核对后重新下载，不自动覆盖正式结果。|

不执行仓库自带 `cleanup.sh`：它包含 `rm -rf ./mix/output/*` 和删除分析 PDF。远程现有工作树的 `mix/.history` 已有未提交修改，保持原状。任何系统级安装、Docker 权限变更、已有结果删除、强制 Git 操作和接近全部 CPU 的长时间实验，仍须先由开发者明确确认。

## 5. 首次最小验证记录

`20260923-165542-smoke-fecmp` 使用个人 fork 的 `edd2b72e52c4d01fd5b86e22ee1173c03f821f92`，在隔离目录以 `-j2` 完整编译，执行 `fecmp`、`leaf_spine_128_100G_OS2`、10% 负载、0.01 秒模拟，状态为 `SUCCEEDED`。FCT 原始文件和元数据已通过 `scp` 回到本机；本机摘要从 19,388 条原始记录中按原项目时间窗选出 9,708 条完成流，成功生成 JSON、CSV 与 SVG。数据只证明工作链路可用，不代表论文性能结论。

## 6. 下一步研究入口

先在个人分支重跑同一拓扑、负载和随机种子的 `fecmp`、`conga`、`letflow`、`conweave`，确认输出与分析链路。入口为 `run.py`（参数、流量生成与配置）→ `scratch/network-load-balance.cc`（拓扑、节点、应用、统计）→ `src/point-to-point/model/switch-node.cc`（按 LB 模式分发）→ `conga-routing.cc`、`letflow-routing.cc`、`conweave-routing.cc` 与 `conweave-voq.cc`（选路及重排）；`switch-mmu.cc` 管理队列/PFC，`rdma-hw.cc` 管理 RNIC/拥塞控制，`settings.cc` 承载全局配置。优先加新策略和参数，在相同输入 trace 上做独立对照，保留四种原始 baseline。
