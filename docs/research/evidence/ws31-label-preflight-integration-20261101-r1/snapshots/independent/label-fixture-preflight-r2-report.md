# 标签夹具 r2 预检报告

日期：2026 年 11 月 1 日。固定 `2ed7d342d0713a5667f43c7730ca5bc5a6a67150` 的源码门、单份完整构建、新标签核心和本地 mock 均通过。网络仿真为 0，默认回归与动态标签网络覆盖仍未完成。

## 1. 来源与修订范围

冻结计划 SHA-256 为 `7defac33294806d0369febbc79932e10263ac10112162642d0327eeb01366e3b`，实验 ID 为 `20261101-121000-ws31-label-preflight-r2`。G1 的五文件修订和相对 506 的完整标签差异已独立阅读并核哈希。C++ 从实际配置构造 LabelRunContext，检查位于配置解析后、随机种子和网络初始化前。C1／C2／C3 算法、500 ns、StartHash 和桶规则不变，见[源审查](label-fixture-preflight-r2-source-review.json)。

## 2. 实际执行

新 ID 的 runs／results 均在本次启动前核为空，旧 r1 ID 没有被复用或据此推断不存在。缓存真实路径、个人 origin／推送引用、树与干净状态核对后，同步新 SHA；无其他用户／未知作业时部署新 worker。部署字节哈希与本地工作树一致，按 CRLF→LF 规范化后的内容与固定 Git 对象一致。

只运行一次 guarded optimized `-j2` 完整构建，最终任务数为 1,464，日志用时为 5m52.659s。未运行 run.py 或网络 run。构建后只编译／运行新增 ws31_label_test.cc，显式 `-UNDEBUG`，二进制含 `__assert_fail`，输出完整 context PASS。二进制和日志均在该 ID 结果目录，位于 source 之外。

新增 Python runner mock 只执行一次，5 个方法全部通过。远程入口在测试中被替换为 mock。日志原始字节哈希与驱动按文本解码后的哈希分别保留，见[日志完整性](label-fixture-preflight-r2-local-mock-log-integrity.json)。旧核心、旧取消夹具和网络格均未重复。

两个 Python 工作树文件使用 CRLF，Git 对象使用 LF。交付器首次直接比较字节而失败，旧脚本及修正记录均保留；逐文件证明只有换行差异，源码、测试日志和二进制未改，也未重跑。见[规范化等价证明](label-fixture-preflight-r2-local-source-canonical-equivalence.json)。

## 3. 证据与资源

9 份结果逐文件核大小及 SHA-256；38 个固定源对象、模拟二进制、新核心二进制和 4,839 项 Git 树均匹配。构建元数据保持 BUILT，核心与 mock 分别有独立 PASS 收据，见[完整性记录](label-fixture-preflight-r2-integrity.json)。

构建每 5 秒采样，共 72 次。最高采样负载 2.22，最大编译前端数 2，最低采样可用内存约 121.916 GiB，磁盘余量约 2,323.609 GiB。未采到其他用户或未知项目作业；采样值不称精确峰值。全部警告保留在索引与日志。

## 4. 结论与后继

本次完成新标签源码的工程预检，主核网络证据仍需后续计划。真实 GetNxtPacket 到每跳 ROUTE 的默认 0 回归、profiles 1／2／3、重传时刻关联、完整适配器生命周期及 generation 边界均未验。独立 V0、双侧效果和成本仍必做，新组合基线未形成。

节点参考复核从候选 README／reading-log 进入，保留 DiffFlow v1 关于分类可见性与生效位置的区分；作者结果不能替代本次源和测试证据，见[复核记录](label-fixture-preflight-r2-reference-review.json)。固定副本已核，全部预检命令终态，兼容约束已释放。本副停止新增执行，等待下一单目标。
