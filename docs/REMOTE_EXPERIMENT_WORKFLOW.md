# ConWeave 本地开发与远程实验

更新：2026-09-27。日常操作从本机 `workspace/LarryBUPT-conweave-ns3`（个人 fork 克隆）执行。源码进 Git，原始实验数据进独立结果目录。

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

服务器已有 Docker 客户端，但 `fnl` 无权访问 Docker socket，因此目前采用工作区内的原生 Waf 编译。不能为 Docker 修改用户组或 daemon。`remote_worker.py` 每份独立源码仍以 `-j2` 编译；WS-11 已把原单仿真限制改为互斥锁保护、上限 1/2/4/8/12 的并发启动，并以 18 个共享 CPU 令牌完成全量矩阵。该实测配置不是永久资源上限。启动前核对其他用户/任务、系统负载、CPU、可用内存、磁盘、现有 ns-3 进程及运维状态。确认没有其他用户作业、系统健康且每格隔离安全后，按资源 pilot 与吞吐实测逐级提高编译加仿真的总调度量；可继续验证 19–20 个物理核等效令牌，目标是尽可能利用 20C/40 逻辑 CPU 的空闲算力，而非只追求最高并发进程数。保持系统及 SSH/存储可用，出现其他用户作业、争用、负载异常、内存/磁盘压力或吞吐下降时降低并发或暂停新格。不同实验 ID 的源码、`mix/output`、日志、元数据和结果必须独立；提高运行器上限时先审计锁、资源阈值与失败恢复，不绕过保护。远程 Python 3.5 和 GCC 5.4 较旧；原始基线的 Waf `configure` 和完整编译已在隔离目录通过。新代码仍要逐次编译验证。

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

`sync` 只接受已推送到个人 fork 的 SHA；服务器访问 GitHub 失败时，先诊断并静默运行一次 `~/lzy/login.sh` 后重试，再从本机通过 SSH 传送 Git bundle，仍保持相同 SHA。也可直接使用 `python scripts\remote_experiment.py sync-bundle --repo-local .`。`build` 从缓存复制一个**全新、固定 commit** 的实验源码目录，Waf `optimized` 模式每份以 2 个任务编译；它从不切换服务器现有的 `/home/fnl/lzy/conweave-ns3` 工作树。`run` 使用独立后台进程，SSH 断开仍继续；默认并发上限为 1，经资源核验可显式提高。`status` 返回 PID、状态、SHA、参数和时间。默认小实验只接受 0.005–0.1 秒仿真时间及 1–50 的负载；扩大规模前先检查资源并修改项目安全上限，不直接运行 `autorun.sh`。

### 结果和分析

```text
远程代码缓存  /home/fnl/lzy/code/conweave-ns3
远程实验源码  /home/fnl/lzy/runs/<实验ID>/source
远程结果      /home/fnl/lzy/results/<实验ID>/
              config/ raw/ processed/ figures/ logs/ metadata.txt metadata.json
本地结果      个人 fork 克隆内的 results/<实验ID>/（Git 忽略）
```

每个结果记录 Git 仓库、SHA、分支、拓扑、负载、算法、种子（当前原始 `run.py` 固定为 1）、编译模式、服务器、启动命令、开始与结束时间、状态、PID。`run.py` 的 `mix/output` 在单次实验副本中指向该实验的 `raw/`，不会覆盖另一组。`fetch` 先检查远程结果没有符号链接，再下载到本机临时目录；已有同 ID 结果时拒绝覆盖。`analyze_result.py` 在本机读取 FCT 原始数据，生成 `processed/fct_summary.json`、`processed/fct_percentiles.csv` 和 `figures/fct_slowdown.svg`，无需额外 Python 包；重复运行时不会覆盖已生成文件。论文图表记录实验 ID 和 SHA。大规模原始数据不提交 Git。

### 任务闭环与持续验证准则（2026-09-30，用户明确要求）

每个 WS 必须在开始及恢复时列出全部预设任务与验收项，并逐项记录实现、实验、原始证据、验证结果和未完成动作。执行“实验 → 修改 → 验证 → 再修改”的循环，直至全部预设任务完成，最终代码、实际效果与结论逐项对应。正确性失败先定位修复，再用新固定 SHA/独立实验 ID 验证；效果为负应完整保留并按预设判据分析，不为获得正收益而放宽门槛或无限调参。完成全部约定验证后，负结果也可形成有证据的结论。

阶段 Handoff、编译/单测通过、本地审计和性能 NO-GO 都不能替代任务闭环。性能实验的停止条件不能自动取消正确性验证或修复工作。发现输入或模型缺口时，继续修复可解决部分，明确受阻项、来源和下一动作；真实部署证据不足与明示合成模型的工程/机制验证分别处理，不把合成数据冒充真实数据，也不默认禁止可复现的合成正确性验证。

不得把未完成验证改写为“以后看论文是否需要”，不得静默删除、缩小或转移用户预设任务。确实需要变更任务范围或放弃某项时，提出具体依据并取得用户明确决定；在此之前保持未完成状态。归档前核对全部验收项和原始数据对应关系，确保未完成项均有具体承接任务与执行入口；若仍有必做未完成项，只能记录阶段交接，不能称本任务闭环或按“闭环完成”归档。Handoff 必须列出未完成验收项，防止仅凭摘要或 COMPLETE FOR 标签提前收束。

### 重要节点后的参考借鉴复核（2026-10-10，用户明确要求）

每个完整的重要工作节点结束后，进行一次参考借鉴复核。重要节点包括诊断收束、候选机制冻结、pilot 双侧分析和正式矩阵分析；逐格验收、例行心跳和仍在后台运行的阶段不重复触发。先从论文项目根目录的 `参考文献/候选/README.md` 与 `reading-log.md` 查找相关候选，再核对对应论文版本、技术分析和核验记录。

节点记录需说明具体借鉴点、适用条件、与现有机制的区别，以及论文条件或证据不足导致的不可外推之处。把论文提出的机制、作者报告的效果与本项目原始数据分别标明。候选身份不等于最终引用、算法准入或本项目收益证据；新机制仍须先完成失败原因分析、事前设计和既定验收。若节点没有适用的新借鉴，也记录检索范围与原因，不为满足复核要求而改动实验或放宽门槛。

## 4. 失败与恢复

| 情况 | 日常处理 |
| --- | --- |
| SSH 断开 | 重新连接后运行 `status <实验ID>`；结果和日志仍在 `results/<实验ID>`。|
| GitHub / 下载失败 | 先区分 DNS、TLS、认证和外网；远程 `sync` 失败时在同轮最多静默执行一次 `~/lzy/login.sh` 并重试，不输出脚本内容。仍失败则自动使用本机已验证的个人 fork 提交制作 Git bundle，经 SSH 传入 `~/lzy`；其他依赖下载若仍失败则停下排查，不改系统网络。|
| 编译失败 | 看 `results/<实验ID>/logs/build.log`；该 ID 保留失败记录，修复个人分支后创建新 ID。|
| 仿真失败 | 看 `status`、`logs/worker.log`、`logs/simulation.log`。`run.py` 可能吞掉子命令退出码，工具额外要求 FCT 输出非空才标成功。|
| 结果同步失败 | `fetch` 保留本机 `.incoming-<实验ID>-<PID>` 临时目录；核对后重新下载，不自动覆盖正式结果。|

### 长时矩阵运行准则

仿真与批量编译在后台静默进行，结果及资源收据落盘；不把逐格日志、重复状态或完整 JSON 持续送入对话。正常运行时约每 30 分钟监督一次，只核对完成数与资源/异常摘要，不做冗余 SSH 轮询或反复唤醒；完成、失败、资源异常或需要用户决定时及时处理。报告使用实验 ID、完成数、失败数、资源峰值及下一动作的简表。矩阵可并行但每格必须保持固定源码 SHA、输入哈希、seed、独立目录与可恢复状态；中断后从已核验收据继续，不覆盖既有原始结果。远程实验进入后台静默监督阶段时，Codex 切换到 GPT-6 Luna（`gpt-6-luna`）、High 推理强度；实验完成后切回 GPT-6 Sol（`gpt-6-sol`）、High 推理强度，进行结果分析与任务收束。

**每个新 WS 分支任务均执行此准则。**任务开始时在对应工作流记录中写清目标、前置门槛、分支、固定源码/输入、观测指标和停止条件；先完成本地审计、最小正确性与资源 pilot，确认服务器无人作业及系统健康后再运行必要的远程仿真。长时仿真启动前保存实验 ID、SHA、输入哈希、后台进程与预计检查时间，并将任务切至 Luna High 监督；正常状态约每 30 分钟读取一次精简收据，禁止为了进度反复 SSH、打印逐格日志或重跑已完成格。完成、失败或资源异常立即处理，安全降载优先于并发目标。所有终态格回传并核对原始数据后切回 Sol High，做逐格核验、双侧分析、反例与证据等级判定。交接 Handoff 及任务最终说明须另用自然语言说明**做了什么、哪些实验数据支持、得到什么结论、仍有哪些限制**，先讲实际意义再给必要术语与文件/实验 ID；未运行、未完成和技术 pilot 不能写成正式收益。模型切换须由实际任务/编排工具确认生效，单靠文档或提示文字不算完成；若当前工具无法自动切换，应说明实际模型并由能切换的线程操作完成，不能假称已切换。

不执行仓库自带 `cleanup.sh`：它包含 `rm -rf ./mix/output/*` 和删除分析 PDF。远程现有工作树的 `mix/.history` 已有未提交修改，保持原状。任何系统级安装、Docker 权限变更、已有结果删除和强制 Git 操作仍须先由开发者明确确认。用户已授权在确认服务器无人、隔离与资源 pilot 通过后尽可能调度空闲资源运行研究矩阵；不需为这一授权重复询问，但须记录并发度、资源依据与降载条件。

## 5. 首次最小验证记录

`20260923-165542-smoke-fecmp` 使用个人 fork 的 `edd2b72e52c4d01fd5b86e22ee1173c03f821f92`，在隔离目录以 `-j2` 完整编译，执行 `fecmp`、`leaf_spine_128_100G_OS2`、10% 负载、0.01 秒模拟，状态为 `SUCCEEDED`。FCT 原始文件和元数据已通过 `scp` 回到本机；本机摘要从 19,388 条原始记录中按原项目时间窗选出 9,708 条完成流，成功生成 JSON、CSV 与 SVG。数据只证明工作链路可用，不代表论文性能结论。
