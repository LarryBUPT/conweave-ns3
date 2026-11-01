# C2 决策标签接口技术验收

日期：2026 年 11 月 1 日。固定源码 `50603927fc09a68d9f2e038129aaee3a3d021081` 的修改核心及五格全部通过。默认行为恢复已验 c4 C2，移除标签恢复 QueuePin，交换标签改变等待资格，未知标签保持立即放行。原业务身份、字节及需求时刻均保留。主已从 raw [独立验收](../main/evidence/c2-label-pilot-main-acceptance-r1.json)。

## 1. 冻结计划与环境暂停

唯一执行计划 SHA-256 为 `96f81afe9eca873ab79faca540a14416c2421a420fc9eb81c96d1a0d0fbc3e46`，已按派发版本核对。五格 ID 使用前缀 `20261101-074000-ws31-c2tag-r1-`，后缀依次为 default、remove、swap、unknown-q12、unknown-c2。

attempt1 在任何核心、构建或仿真启动前暂停。远端 GitHub 获取超时后，既有 guarded bundle 成功同步固定提交；新鲜资源门随后发现两个源码缓存目录内的 `git-remote-http` 进程，拒绝继续。两进程后来均已自然退出，未发送终止信号。暂停不是 C2 正确性失败。

主明确恢复条件后，原收据、驱动、错误、同步和资源日志共 9 份按原字节封存。attempt2 独立记录全部后续状态与日志。恢复前再次确认五个 ID 的 runs/results 均未创建、旧 driver/monitor 不活动，以及缓存 realpath、个人 origin、clean、固定 commit 和 origin 分支包含关系。资源门通过后复用已同步缓存，没有再次 fetch、放宽保护或覆盖实验 ID。见[暂停历史](c2-label-validation-r1-evidence/attempt1/manifest.json)和[缓存恢复核验](c2-label-validation-r1-attempt2-cache-prerequisite.json)。

## 2. 构建与核心

五个新的 guarded optimized `-j2` 构建分为 3＋2 两波，总并行编译任务不超过 6。全部构建和源码／产物核验通过后，才用第一格固定源码编译并执行修改过的 `tests/ws31_start_test.cc`。编译参数为 `-std=c++11 -O2 -Wall -Wextra -pedantic`，没有 `-DNDEBUG`；二进制包含 `__assert_fail`。

核心输出 `WS31_START_TEST PASS bounds/determinism/controls/fallback/demand-time/policy-tag`，编译和运行退出码均为 0。核心二进制 SHA-256 为 `2592280229337566ea98bd6218a19523143ae521b5fbb9b69dcb529ba3c31238`。源文件、头文件、命令、原始日志和二进制均保留，见[核心收据](c2-label-validation-r1-attempt2-core-receipt.json)。未重跑 C1、C3 或 Ofan 核心。

全部构建结束后才执行核心，核心通过后才串行运行五格。远端 metadata 及核心收据时间确认没有构建／仿真重叠，见[阶段时序](c2-label-validation-r1-attempt2-phase-order.json)。公共设置仍为 100 Gbps、buffer 9 MiB、DCQCN、PFC=0、IRN=1、seed 1、观测级别 2，等待上限保持 500 ns。

## 3. 五格结果

| 格 | 完成请求 | 完成载荷／B | 正等待请求 | 最大等待／ns | 规定配对及标签检查 |
| --- | ---: | ---: | ---: | ---: | --- |
| default | 104 | 201,981,952 | 80 | 497 | 恢复 c4 C2 |
| remove | 104 | 201,981,952 | 0 | 0 | 恢复 Q12；单核 tag 0 |
| swap | 104 | 201,981,952 | 24 | 467 | 原身份保持；资格交换 |
| unknown-q12 | 6 | 28,278 | — | — | 建立配对参考 |
| unknown-c2 | 6 | 28,278 | 0 | 0 | FCT 与路径等于新 Q12 |

四个 C2 格共 318 条请求，需求、放行、完成三套日志逐一对应。每条需求日志的原业务 `tag`、`policy_tag`、`tag_transform` 均符合冻结干预。按原四元组独立重算 uint32 哈希及模 501 等待，所有记录精确相符；FCT 从原需求起算并包含等待。所有 C2 终态均无 pending、cancelled、unfinished 或字节失衡。

三个主输入格始终保留原 tag 1 的 24 条请求／201,326,592 B，以及原 tag 2 的 80 条请求／655,360 B。交换后按原业务身份核验，未用策略标签重新分组。默认总等待为 18,002 ns，交换总等待为 5,771 ns；这里只核机制执行，不作收益比较。

默认格完整 FCT 与已验 c4 C2 逐字节相同，有序 CHOICE、ROUTE 及合并流只去 uid 后相同。移除格完整 FCT 与已验 Q12 相同；路径仅额外移除有意变化的 tag 字段，三类有序流均相同，同时单独确认每个实际包 tag 均为 0。

未知输入含 0、7、99 各两条请求，每类 9,426 B。两格共用同一原输入，包标签保持原值；未知 C2 的策略标签也保持原值，六条等待全为 0。完整 FCT、有序 CHOICE、ROUTE 和合并流仅去 uid 后均与新未知 Q12 相同。

各主输入格均有 312 条 CHOICE、606,168 条 ROUTE；未知输入各为 18 条和 99 条。`WS30_CHOICE` 的 tag 为固定 0，实际包标签仅从 `WS30_ROUTE` 核对。每个数据包的实际标签按原四元组核对，全部路径无 QP 内换口、拒绝或观测溢出。队列入出字节相等，丢弃、拒绝、终态在队字节和账本违规均为 0。

## 4. 证据与资源

完整 raw、配置、metadata、日志、采样及核心产物位于 `c2-label-validation-r1-evidence/attempt2/<实验 ID>/results/`。共 120 份结果文件已按远端清单核长度和 SHA-256；每格在运行前和回传后核对 35 份关键源对象／输入，全部匹配固定提交。完整 4,836 项 Git 树清单及每格网络二进制哈希已保存。旧参考 FCT 和路径原始日志另核完整性，未修改旧数据。

编译每 5 秒采样，共 159 次；最多观测到 3 个构建、6 个 cc1plus。最大采样负载 6.24，最小采样可用内存约 120.798 GiB，最大采样构建进程树 RSS 为 1,938,684 KiB。未观察到其他用户或未知项目作业。运行每 2 秒采样，全部保留；这些数值不是精确峰值。三个既有 strict-aliasing 警告在每个构建中保留，未改源码或屏蔽。

## 5. 结论与承接

本轮完成决策可见标签接口的技术验收。参考借鉴复核阅读了 DiffFlow 固定 arXiv v1 的技术分析与核验：分类依据、决策可见标签和应用业务身份需要分开。DiffFlow 的分类广告与分路粒度不同于当前 C2 启动等待；其简化传输结果不能外推成本项目收益，见[复核记录](c2-label-validation-r1-attempt2-reference-review.json)。本轮没有新增基线或 Ofan/RR 工作。

三候选其余匹配控制、错误／延迟标签、完整生命周期、独立 C1 V0 以及双侧效果和开销仍必做。主独验已通过，等待下一单目标；没有预设或筛选性能方向。

[attempt2 总收据](c2-label-validation-r1-attempt2-receipt.json) · [交付索引](c2-label-validation-r1-attempt2-index.json) · [九节交接](c2-label-validation-r1-attempt2-handoff.md)
