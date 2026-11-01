# 适配器边界预检源审查与门控停止报告

日期：2026 年 11 月 1 日。固定 `1f917f44fcfb88e61f3ad22c5cc75fa3a06b6c0e` 的独立静态源审查通过。新构建前的未知作业门检出了缓存内 `git-remote-http` PID 297502，驱动按计划停止。构建、17 例夹具、核心和网络执行均为 0；本次没有适配器运行通过结论。

## 1. 已完成的源码审查

已逐项核五文件差异及固定哈希。移除新增 DispatchRequest 提取和两处友元声明后，三个生产文件逐字节恢复父源。SwitchNode 生产适配器及预算／等待／配额核心未改，见[独立源审记录](adapter-boundary-preflight-r1-source-review.json)。

实际 PPP 为 14 B、IPv4 为 20 B、UDP 为 8 B；INT mode 1 的 SeqTs 为 14 B，合计 56 B 包头。仓库 UDP 写实际剩余长度，完整 CustomHeader 减去 22 B 的 UDP／SeqTs／INT 后得到原载荷。八个 QbbNetDevice 均连接实际 BEgressQueue，负载读取真实队列，5,000 B 入队在实际容量内。

C1 重复、空洞和部分重叠的唯一账，19,999／20,000／20,001 ns 到期边界，以及容量／区间／序号跨界回退的预期与生产方法一致；观测会检查 Pressure 是否额外清理漏掉的到期。C3 借用、首次类别缓存、20,199／20,200／20,201 ns 只读快照和 20,202 ns 真调用续期逻辑一致，生产清理前后新表和历史计数分开检查。

C2 子类通过 CreateObject 设置 TypeId 并继承属性；只替换生产计时计数后的虚拟传输入口。原需求 10 ns、同刻两种 event uid 顺序、Stop／Dispose 与重复控制、零等待同步交付均有实际生产入口和优化构建有效的 NS_FATAL_ERROR 检查。上述为静态审查，尚未通过构建或执行验证。

## 2. 实际执行与停止依据

本地旧驱动门、干净已推送个人 fork、新 ID、worker 与初始资源门通过。仅执行一次 guarded sync，将缓存引用更新到固定 SHA；worker 与 controller 原始字节、规范化 LF 对象保持既有来源，未部署。

同步后 cache origin／分支／树／clean 与新 ID 均通过。紧接的新构建前门在 `2026-11-01T06:42:04.334661Z` 记录 PID 297502，cwd 为 `/home/fnl/lzy/code/conweave-ns3`。无计算进程、无其他用户进程，一分钟负载 0.24，可用内存约 122.513 GiB、磁盘约 2,298.321 GiB。停止由未知项目进程触发，不是资源不足或源码失败。

随后只读诊断在 `2026-11-01T06:44:24.066161Z` 已看不到该 PID，因此无法再取其父链；不将它推断成其他用户作业，也不确定归属到本次 sync。未发送信号、绕过门控或自动续跑。见[停止前资源收据](adapter-boundary-preflight-r1-evidence/20261101-143000-ws31-adapter-preflight-r1/resources-before-build.json)及[进程诊断](adapter-boundary-preflight-r1-process-diagnosis.json)。

## 3. 保全与后继

42 个本地固定 Git 对象、4,843 项完整树、冻结计划／契约、差异、源码审查、sync 日志和门控收据已保全，见[索引](adapter-boundary-preflight-r1-index.json)。新 ID 在最后 cache 门仍不存在，未建立构建源副本，也没有 raw、测试二进制或动态库产物。本副未改主源码、worker、controller、环境或既有证据，未提交／推送。

构建及 C1→C2→C3 的 17 例实际验收继续待办，需主核本次门控记录后安排新的实时门与接续。源码／入口／环境约束尚未释放，不能由缓存同步推定为副本建立。新源默认网络回归、真实端点 generation／drain／reuse、独立 C1 V0 和双侧效果／成本仍未完成。

已从候选 README／reading-log 复核 DiffFlow v1 的生效顺序与回收缺口，仅借鉴检查问题，不外推其 SDN 喷洒或平均 FCT；见[参考复核](adapter-boundary-preflight-r1-reference-review.json)。本副停止新增执行，等待主处理。
