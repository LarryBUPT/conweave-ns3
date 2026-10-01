# Handoff 59：WS-23 v2 预飞行参数漏传与 revision 3 重跑

日期：2026-10-01。执行工作区 `E:\研\毕业论文\workspace\ws23-execution-70bf890`，分支 `feature/ws23-validation-execution`。本交接记录执行错误和恢复入口，不构成隔离效果结论。

## 本轮发现与处理

- 监督任务通过实际线程调度将本轮设为 GPT-6 Luna High 后，继续 revision 2。`20261001-151502-ws23-pilot2-shortq2-off` 原先构建完成；本轮取得 READY 后运行并回传 raw，状态为 `SUCCEEDED`，输入 SHA-256 `379e0c87cb0c26690d438287468dbc9159054f82445e6be46d0324165d639863`，拓扑 SHA-256 `dcca23ca6992b9b81e5b71127a3698264441390455f3dd29b459e33db29915ad`，峰值进程树 RSS 203.988 MiB。
- `20261001-151503-ws23-pilot2-shortq2-on` 以源码 `eff40eaac291a86c1d42afa6042ab1d583c8a373` 独立 `optimized -j2` 构建；观察器 READY 后运行并回传 raw，状态为 `SUCCEEDED`，同一输入和拓扑哈希，开启 `ws13_diag=1`，峰值进程树 RSS 204.129 MiB。
- 上述 `shortq2` 两格启动时漏传 `--factorial-pilot --factorial-drop-diag`。因此元数据没有记录输入、完成和未完成流数；尽管状态为 `SUCCEEDED` 且 FCT 非空，不能通过冻结验收。两格和 raw 保留为失败编号，不复用。v2 `guardhash` 两格未启动。
- 本机 `remote_worker.py` 与服务器执行器 SHA-256 均为 `9e1b4e144d5584e8999d2c560bf4577b249ca73421d9aac6c53e5a96a798766e`，所以不是执行器版本不同步。revision 2 验收器在 `shortq2` 检查处因缺少完成数证据失败。
- revision 2 的 ECMP 诊断开/关两格均带有上述 factorial 参数，记录 4/4 完成；但它们不能与失败的 `shortq2` 格拼成通过的六格门槛。

## 恢复方案

未修改路由评分、输入、拓扑、seed、停止规则或探索性双侧条件。验收脚本新增 revision 3 编号映射，协议追加漏传参数与失败记录，验证清单同步当前状态。该文档和验收入口变更提交后，以新固定提交及以下全新 ID 重新运行完整六格；运行前逐一检查本地及远端 `results/`、`runs/` 均空闲：

| 模式 | 诊断关闭 | 诊断开启 |
| --- | --- | --- |
| `fecmp` | `20261001-190100-ws23-pilot3-fecmp-off` | `20261001-190101-ws23-pilot3-fecmp-on` |
| `shortq2` | `20261001-190102-ws23-pilot3-shortq2-off` | `20261001-190103-ws23-pilot3-shortq2-on` |
| `guardhash` | `20261001-190104-ws23-pilot3-guardhash-off` | `20261001-190105-ws23-pilot3-guardhash-on` |

所有格均显式使用 `--factorial-pilot --factorial-drop-diag`；仅 `--ws13-diag` 按配对取 0 或 1。其余冻结参数保持一致。每格仍独立 `optimized -j2` 构建、资源观察器先 READY、并发 1；终态读取有效正 RSS 收据并回传 raw。完成后运行 revision 3 验收器。任何格失败即停止扩格；六格全通过才允许运行预注册 18 格。

## 当前边界

源代码修复仍未得到六格预飞行完整验收；不得进入 18 格，不报告隔离候选效果。v1/v2 失败 raw 全部保留。后续仍须全部完成六格验收、18 格双侧验证及逐格 raw 独立复核；真实业务适用范围仍缺真实部署来源和可信 SLO。
