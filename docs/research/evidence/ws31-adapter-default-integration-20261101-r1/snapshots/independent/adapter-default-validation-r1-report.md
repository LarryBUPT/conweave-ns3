# 新交付入口默认网络兼容报告

日期：2026 年 11 月 1 日。固定 `1f917f44fcfb88e61f3ad22c5cc75fa3a06b6c0e` 的 Q12／C2 两格默认兼容均 PASS，共 208 条完成、403,963,904 B。完整 FCT、有序 CHOICE／ROUTE 只去 uid 后恢复各自固定参考；C2 的全部 DEMAND／LAUNCH／FINISH／STATE 字节流也精确恢复。主原始数据独验待完成。

## 1. 授权与来源

冻结计划 SHA-256 为 `01665606c32d7422b92f4202d23e8e571500321631ca376b5924ed67f5e7eb68`。原条件状态未改，实际执行以[独立授权收据](adapter-default-validation-r1-execution-authorization.json)和本轮新门为依据。17 例适配器主验、明确约束释放和唯一副 idle 已满足。源 SHA 改变即失效的规则保持，未替换源。

每格 104 请求、201,981,952 B，共用 correctness r1 输入和 OS2 100 Gbps 拓扑，DCQCN、PFC 0、IRN 1、buffer 9 MiB、seed 1、0.01 s、netload 10、观测 2。新 label profile 和旧干预／故障关闭。

新 Q12 `20261101-153000-ws31-adapterdef-r1-q12` 对照 c4 的 `20261101-062753-ws31-zr1-q12`；新 C2 `20261101-153000-ws31-adapterdef-r1-c2` 对照 2ed 的 `20261101-124500-ws31-labeldef-r1-c2`。两份主参考收据、完整 FCT／log、元数据及两个输入共 12 份只读文件在执行前后及封装时哈希相同。

## 2. 实际执行与完整回归

新本地进程、全部远程进程及 Git 助手、缓存 origin／引用／对象／树／clean、worker、新 ID 与实时资源门通过。复用已匹配的缓存与 worker，sync／deploy 为 0。两个新隔离 optimized `-j2` 全构建各 1,468 项通过后，才按 Q12→C2 串行网络运行，没有构建与仿真交叠，见[顺序证据](adapter-default-validation-r1-phase-order.json)。

每格全部原请求身份、字节和需求起点均检查，没有筛选完成时间窗。实际包标签按原请求保持。有序 CHOICE／ROUTE 比较保留时间、四元组、候选、队列、tag 和端口，仅删除 uid；完整 FCT 按原始字节比较。没有新标签或适配器夹具观测。

C2 的 104 条 demand／launch／finish 按原四元组及流索引核对，冻结 StartHash 决定是否和等待多久，原需求 FCT 包含等待。三个事件表和一条终态账全部精确匹配参考，等待、launch／finish 与原起点再次核对。Q12 没有 C2 专属事件。两格队列字节守恒，丢弃、拒收、账本违规、观察溢出和 QP 内端口变化均为 0。

## 3. 来源完整性与资源

52 份结果逐文件核大小及 SHA-256，22 份支持文件、每格 42 个固定 Git 对象及 4,843 项完整树已核。构建前／运行后源映射和实际 network-load-balance 二进制匹配，配置、输入及 raw 保留。完整入口见[索引](adapter-default-validation-r1-index.json)与[完整性记录](adapter-default-validation-r1-integrity.json)。

构建每 5 秒采样，共 79 次，最大采样编译前端 4、并行构建 2，最高负载 4.07，最低可用内存约 121.403 GiB、磁盘约 2,292.241 GiB。未采到其他用户或未知作业。仿真每 2 秒采样且串行，数字均为采样界值。模型没有执行或声称切换。

旧参考、核心、17 例夹具、Ofan/RR、旧控制器与矩阵均未重跑，成功 ID 未覆盖。两个源码副本及网络调用终态核验后，源码／入口／环境约束已明确释放，见[释放收据](adapter-default-validation-r1-guards-released.json)。

## 4. 结论与后继

本次验证默认虚拟交付入口提取在 Q12 公共路径与 C2 等待路径、本固定输入上保持兼容。它不建立新效果或新组合基线。真实端点退出、旧包排空、跨代 generation／drain／reuse、独立 C1 V0 和三个候选双侧业务效果／状态／运行成本继续由主总计划承接。

已从候选 README／reading-log 复核 DiffFlow v1 技术与核验记录，保留业务身份和控制生效位置的区分；其分类广告与喷洒及作者效果不代替本轮 default dispatch raw，见[参考复核](adapter-default-validation-r1-reference-review.json)。本副停止新增执行，等待主独核与下一单目标。
