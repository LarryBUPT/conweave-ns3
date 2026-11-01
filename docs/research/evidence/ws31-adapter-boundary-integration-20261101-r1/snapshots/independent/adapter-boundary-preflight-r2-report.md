# 适配器边界 r2 工程预检报告

日期：2026 年 11 月 1 日。固定 `1f917f44fcfb88e61f3ad22c5cc75fa3a06b6c0e` 的一次 optimized `-j2` 完整构建及新增 17 个适配器条件全部通过：C1 五例、C2 十例、C3 两例。主从回传原日志独立验收仍待完成。网络、核心、同步和部署次数均为 0。

## 1. 原停止保全与新门

恢复计划 SHA-256 为 `e09f0883fe8839f5e77ee2797ebbf75aeb88e0fa9959b7b7ddf84b5acb328061`，新 ID 为 `20261101-150000-ws31-adapter-preflight-r2`。原 r1 的 28 份文件前后字节相同，停止交付没有回写成功。复核原静态审查、42 个固定源对象和 4,843 项完整树后，源码和 17 例判据保持。

重新读取全部进程，Git 助手及相关祖先链单列；初始和构建前均无 Git 助手、其他用户或未知项目作业。原 PID 的历史消失不作当前门依据。缓存个人 origin、分支引用、固定对象／树／clean、worker、原保留 ID 和新 ID 均核对。旧、新 ID 在恢复门均不存在。本轮没有 sync、deploy 或缓存修补；见[只读缓存门](adapter-boundary-preflight-r2-cache-read-only.json)。

## 2. 实际构建和三个直接命令

新隔离副本完成一次全量 optimized `-j2` 构建，任务数 1,468，原日志用时 5m59.118s。随后直接执行新 `ws31-switch-boundary-test --candidate=c1`、`ws31-start-boundary-test`、`ws31-switch-boundary-test --candidate=c3`，不使用 `waf --run`。

环境由白名单重新构造：观测 2，label／transform／lifecycle／life profile／composition 均为 0，诊断与 preload 等继承项不进入进程。`LD_LIBRARY_PATH` 只包含该隔离 build。两个二进制及实际解析的 36 份 ns-3 动态库均在运行前核路径／哈希并保留副本，ldd 没有缺库。完整 argv、环境、PID、时刻、退出码和 stdout／stderr 在[技术收据](adapter-boundary-preflight-r2-evidence/20261101-150000-ws31-adapter-preflight-r2/results/technical/adapter-boundary/receipt.json)与索引。

## 3. 原始行为验收

C1 五例共 20 次真实包调用。PPP／IPv4／UDP／SeqTs 和 INT mode 1 完整解析，实际包头为 56 B；八个 Qbb 设备连接 BEgressQueue。重复、空洞和部分重叠的唯一扣减依次为 100、100、200、400、500 B，真实选中队列填入 5,000 B 后标签和队列变化均不迁移原路径。到期前、恰好到期、迟到无重登记、容量／区间／序号跨界回退及真实清表重建均核对。Pressure 观测没有替生产入口执行漏掉的到期。

C2 的 Stop／Dispose 各五例：放行前、同刻控制先、同刻放行先、放行后和零等待。实际 demand 共 10、launch 共 6、cancel 共 4；每例 8,192 B，原需求时刻 10 ns，等待按四元组哈希重算。同刻 uid 的两个大小顺序都成立，零等待同步交付。重复控制／Dispose 不二次计数。替身只替换计时和计数之后的传输交付，真实 QP 和完成数均为 0。

C3 两例共九次真实包调用。首先达到真实类别 1 借用类别 2 所有权端口，再激活归属类别，记录一个残留包／156 B。后续改标签及缺失标签保持首次类别和端口。20,199／20,200／20,201 ns 只读快照分别对应活动双真、类别 2 到期、两类到期，保留固定条目和惰性租约；20,202 ns 真调用执行到期并续期。真实 reset 清借用账，未知首次策略保持至显式清理后重新准入。全部逐包、空闲、清表记录见[原始重放结果](adapter-boundary-preflight-r2-raw-acceptance.json)。

## 4. 完整性与资源

47 份远程结果逐文件核大小和 SHA-256；42 个固定源对象及 4,843 项完整树匹配，两个测试二进制、36 个动态库、构建／夹具日志及完整 receipt 均由 manifest 保全。元数据保持 BUILT，网络 raw 为空。原 r1 保全文件前后相同，见[索引](adapter-boundary-preflight-r2-index.json)及[完整性记录](adapter-boundary-preflight-r2-integrity.json)。

构建每 5 秒采样，共 74 次；最大采样编译前端 2，最高负载 2.00，最低可用内存约 121.806 GiB，磁盘约 2,296.350 GiB。未采到其他用户或未知项目作业。夹具前后另有资源快照和各直接子进程的 rusage；采样界值不称精确系统峰值。当前没有可用模型切换接口，未执行或声称模型切换。

## 5. 结论与承接

本次完成新增适配器工程预检，源码副本与三个调用均终态，r1 延续的源码／入口／环境约束已明确释放，见[释放收据](adapter-boundary-preflight-r2-guards-released.json)。本副停止新增执行，等待主独核与下一单目标。

工程通过不代表真实端点退出、旧包排空、跨代 generation／drain／reuse 或默认网络兼容。DispatchRequest 提取后的必要网络回归、真实端点生命周期、独立 C1 V0 及三个候选双侧业务效果／状态／运行成本仍由总计划承接。新组合基线尚未形成。

从候选 README／reading-log 复核 DiffFlow v1 技术和核验记录，保留生效顺序、缓存身份与显式状态移除的区分；其抽样广告、喷洒和平均 FCT 不能代替本轮真实适配器或端点证据，见[参考复核](adapter-boundary-preflight-r2-reference-review.json)。
