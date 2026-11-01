# 动态标签恢复与十格合并验收报告

日期：2026 年 11 月 1 日。原冻结十格在本副的完整技术验收为 10/10 PASS，共 150 条完成记录、2,457,600 B。本次仅运行原来 BUILT、从未启动的 C3 p2／p3 两格，各运行一次；前八格只做离线重验。主对话已独验前八格，新增两格待主独验。

## 1. 检查器修正与旧证据保全

恢复计划 SHA-256 为 `d1dce31271e4756e4c90084bc01006e9c4a670de830d24414260a71faacd9599`，固定源码 `1ec5eedc24cd863a289b7493e8b3865c70592ab5`、原输入、500 ns、模板和配额均保持。原停止由本副给 C3 加入通用 CHOICE 总数及 combined hash 等价要求引起。原 checker、driver、finalizer、stop index、QA、日志和 raw 共 268 份文件逐字节保持，旧停止交付没有回写。

新文件检查器 SHA-256 为 `6ce22a20fe87e8ce6e90c9ef4e7d3da7a97cc4eeaf742d1201bcc13da2b5ba7c`，见[修订差异](label-dynamic-recovery-r2-checker.patch)。C3 p1 按原合同比较完整 FCT、仅去 uid／tag 的有序 ROUTE 及 15 条首次源投影；30 条通用 CHOICE＋15 条专属首次准入与 Q12 的 45 条通用 CHOICE 分开验收。总 switch QP 均为 45，不因日志分类不同丢弃决策。C2 的完整 CHOICE、ROUTE 及 combined 比较保持。

八份旧 raw 用新检查器离线通过；改坏 ROUTE 哈希、首次源投影及 C2 完整 combined 哈希的三个内存副本均被拒绝，见[负例检查](label-dynamic-recovery-r2-offline-negative-examples.json)。历史 C3 p1 的 raw_preserved 标记保留，新记录明确实际 raw 存在，完整身份／UID／时钟／存在性／状态已验。

## 2. 两个未运行格的实际恢复

新本地旧进程、个人 fork、cache origin／引用／树／clean、worker、作业与资源门通过。两个远程元数据与原 BUILT 快照的对象和原始哈希完全一致，raw 为空且没有 worker／simulation 日志。40 项固定源码、输入和二进制与原十构建证明一致后，仅按 p2→p3 串行 guarded run；见[启动前门](label-dynamic-recovery-r2-pending-built-source-cache-gate.json)。未构建、同步、部署、执行核心或重跑前八格，结果写入新的恢复目录。

| Profile | 首次准入 | 限制 | 借用 | 残留包 | 残留 B | 结果 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 2 | 15 | 6 | 1 | 16 | 16,152 | PASS |
| 3 | 15 | 11 | 0 | 0 | 0 | PASS |

p2 的 15 请求均有真实阈值前后构包，首次类别保持原标签；后期互换没有迁移已有策略或路径。p3 的错误源仍恰为 1／7，其他已知类别每类各五个正确，未知 0／7／99 保持。两个已知策略类别和限制准入均覆盖。所有活动、借用和残留计数按实际逐包状态重放，零值保留。

## 3. 合并十格的实际行为

九个标签格共 2,295 次构包，逐 UID 对应 6,885 条标签路由；含新 Q12 的十格合计 7,650 条 ROUTE。六个 profiles 1／2 格的 90 个请求实例均有首次 elapsed＜500 ns 和后续 elapsed≥500 ns 的真实构包。缺失 0 与显式 0 分开检查，原业务真值、需求起点及字节保持。

C1 按首次真实包值选择模板，完整重放两候选、饱和 Q＋R、区间扣减、访问时到期和保留预测项；后变标签没有重新登记。C2 在原需求时刻采样一次，p1 全立即，p2 六次总计 1,588 ns／最大 413 ns，p3 六次总计 1,457 ns／最大 409 ns。FCT 包含原等待。C3 缓存首次类别，按 20,000 ns 活动窗口重放新准入、所有权、借用与残留，已有 QP 固定路径。

C2／C3 p1 的完整 FCT 与本轮 Q12 一致；ROUTE 仅去 uid／tag 后一致，C3 的 15 条首次源投影一致，C2 额外保持完整通用选择事件比较。原身份、完成和队列账守恒，丢弃、拒收、账本违规和 QP 内换路为 0。

## 4. 完整性与资源

最终十格共 193 份结果、83 份原始及恢复支持文件逐项哈希；400 项来源映射、40 个唯一 Git 对象及 4,841 项完整树匹配。原 r1 的 268 份文件前后不变；完整入口见[索引](label-dynamic-recovery-r2-index.json)及[完整性记录](label-dynamic-recovery-r2-integrity.json)。新两格的回传 manifest、输入、配置、binary 和 raw 分别核对，未覆盖旧 BUILT／stop 快照。

主验反馈后，确认初稿 JSON 的实际 UTF-8 字节与转义有效，但本机默认 CP936 解码会把中文字节后的反斜杠读入双字节字符，导致 JSON 解析失败。恢复 JSON 现采用 ASCII 转义序列化，原 UTF-8 索引、QA 和 receipt 以 `.bin` 保留供追溯；按字节、显式 UTF-8 和默认编码三种读取均核对。记录见[编码诊断](label-dynamic-recovery-r2-json-encoding-diagnostic.json)。原 r1 不变。

新增仿真每 2 秒采样且串行，最高采样负载 0.08，最低可用内存约 122.460 GiB；无其他用户或未知作业。原十构建的资源收据保持，新增构建数为 0。以上为采样值。实际模型未切换，未声称切换。

## 5. 节点结论与承接

本副已完成原十格小输入合成标签正确性目标，generation 为 0。全部十源码副本保持，两次新调用终态核验后入口／环境约束已明确释放，见[释放收据](label-dynamic-recovery-r2-guards-released.json)。主对话继续独立验收新增两格及最终交付；本报告不代替主验。

已从候选 README／reading-log 复核 DiffFlow v1 技术与核验记录，保留分类可见性、生效位置与原业务真值的区分，见[参考复核](label-dynamic-recovery-r2-reference-review.json)。本次不估计真实分类错误率，不证明适配器完整生命周期或同四元组重建隔离。SwitchNode／RdmaClient 异常、cleanup／generation／drain、同刻事件、独立 C1 V0、三候选双侧业务效果与状态／运行成本继续由总计划承接；新组合基线尚未形成。本副停止新增执行，等待下一单目标。
