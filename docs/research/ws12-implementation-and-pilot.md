# WS-12 实现、正确性与资源 pilot

日期：2026-09-27。WS-12 [预注册](ws12-packet-strategies-prereg-v1.md)在策略代码前以提交 `7675d86` 冻结；本页只记录其前置核验。六模式源码固定 `adae7956e3fc874d9237e62a6ea8e32b26d5def1`，其后的控制器、分析和本报告提交不改仿真源码。两个参考仓库只读；参考 `hybrid-as/ss` 及本 fork DRILL 的有效路径与额外状态见预注册。

新模式映射：`packet-rr=16`、`packet-random=17`、`packet-adaptive=18`、`packet-drill=19`；旧 `fecmp=0`、`dualtrack=12` 保留。四个新模式均只对 `WorkloadTag=2` 的 UDP 数据作逐包选择，背景 tag=1/0 和控制包沿原 `DoLbFlowECMP`；每个分支都使用相同的 `m_rtTable` 下一跳集合。RR 状态存于每交换机的目的 IP→下一索引表，交换机新建时复位；DRILL 复用已有两个随机候选、本地出口队列和目的端上次最佳缓存；随机喷洒与自适应喷洒分别采用参考代码的均匀抽样及无 probe 时 `1/(local_queue+8193)` 权重。参考 `hybrid-as` 的远端 probe 只在 Inflex 模式启动，本阶段不引入其未激活控制流；接收端始终是本 fork 的共同 IRN 实现。

| 前置核验 | 实验 ID / 结果 |
| --- | --- |
| 1280 节点跨 ToR，六模式共用四流、同 trace SHA `2d55bb4d...18b6`、PFC=0/IRN=1 | `20260927-023500-ws12-small-f/h/s/a/d` 与 `20260927-022600-ws12-build`；均 4/4 完成。新模式在源 ToR 的多下一跳 MoE 包为 RR 23、随机 21、自适应 26、DRILL 18；实际使用端口数分别 8/7/8/2，背景源包均记 132。`scripts/verify_ws12_small.py` 重算通过。 |
| 32 主机单类/双类 | `20260927-031000-ws12-32-flow/packet/dual`，RR 下各 4/4 完成。全背景流格 MoE 入口为 0、背景入口 150；全 MoE 格多下一跳入口 156；双类格 MoE 31、背景 132。全背景流格原始 FCT SHA 与 WS-08 `20260925-213355-ws08-irn-small-flow` 完全相同。 |
| 旧模式同源码退化 | 上述跨 ToR `dualtrack` 原始 FCT SHA `3a12b4a9...ab79353f` 与 WS-08 `20260925-214621-ws08-irn-cross-four` 一致。全量 192 背景资源 pilot 中，新源码 `fecmp` 与 `dualtrack` 的原始 FCT SHA 分别为 `9d600f05...5038e1`、`e76888a2...d3e311`，均与 WS-11 原始输入同模式完全一致。 |
| 六模式全量 192 背景资源 pilot | `20260927-030000-ws12-pilot-f/h/r/s/a/d`；控制器 `results/ws12-pilot-plan.json` 和 `results/ws12-pilot-receipts.jsonl`（Git 忽略）记录每格源码、trace、完成率、PFC、资源收据与恢复状态。六格 MoE 16,384/16,384、背景 192/192 均完成，PFC 文件均空。峰值进程树 RSS 最大 4540.47 MiB；四格并发最低可用内存 105.42 GiB、最低空闲盘 5897.33 GiB。 |

小样和 pilot 只证明当前输入下的分派、完成与资源可行性；pilot 性能数字不用于挑选策略或改变正式门槛。全量正式矩阵独立 120 格，由 `scripts/run_ws12_matrix.py` 锁定同一仿真 SHA、输入哈希与资源采样，完成后由 `scripts/verify_ws12_formal.py` 从每格原始文件重新计算双侧判据。若正式格未完整，报告“未完成”，不以 pilot 或部分格作正式排序。
