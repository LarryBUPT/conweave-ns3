# WS-09 GuardHash/HarmGate v0 冻结规格

冻结日期：2026-09-26，开始机制代码前。起点为已推送的 `feature/ws08-guardhash-gate@c45d41d42157dd3589e37ebe1953c75a68d5b6c2`。本规格是可关闭的工程原型，不改变 WS-08 的单 seed 效果 no-go。

## 模式和输入

| LB_MODE | 名称 | tag=2 UDP 数据 | tag=1/0 与控制包 |
| ---: | --- | --- | --- |
| 0 | `fecmp` | 原四元组 ECMP | 原分派 |
| 12 | `dualtrack` | 原逐包单哈希 | 原分派 |
| 13 | `shortq2` | 普通短队列双候选，始终比较总出口排队字节 | 原分派 |
| 14 | `guardhash` | 类别感知双候选，HarmGate 关闭（始终评分） | 原分派 |
| 15 | `guardhashgate` | 同一类别感知评分，HarmGate 开启 | 原分派 |

三种新模式只作用于 `tag=2` 的 UDP 数据；无标签、`tag=0/1`、ACK/NACK/PFC/QCN 保留原流 ECMP。候选 1 使用现有 `dualtrack` 的 `sip,dip,UDP sport/dport,seq` 与交换机 ECMP seed；候选 2 对**同一键**使用固定异或盐 `0x9e3779b9` 后再调用同一哈希。候选相同或仅一个下一跳时直接选候选 1，不读取门控。两个候选及其顺序在三模式完全相同。

## 观测、评分和门控

`q_j` 为出口设备真实 BEgressQueue 中**所有优先级**当前排队字节；`b_j` 为其中 `WorkloadTag=1` 的字节。计数取路由决策时的瞬时快照，当前待发包尚未入队，不含正在链路发送的包。仅 `tag=2` 读取这些量。普通模式分数 `q_j`；类别模式分数 `q_j + λ b_j`，`λ=1`。仅当候选 2 分数严格小于候选 1 时改路；相等选候选 1。`τ=0` 字节，等价于严格小于，三个模式共用。权重和门槛为预设工程常数，不根据 FCT 调整。

HarmGate 是类别评分的激活条件，不是第二套选路协议。按交换机、无序候选端口对保存一个布尔状态：两端 `max(q_1,q_2) ≥ 8192 B` 时激活；激活后直到两端 `max(q_1,q_2) ≤ 4096 B` 才退出。未激活时固定选候选 1；模式 14 始终评分。门控只用总队列字节，类别信息仅进入评分。记录激活、退出、已评分、主候选、改路等计数；不声称该局部门槛能预测下游竞争。

## 队列守恒与停机

在 BEgressQueue 真正接受包后按出口端口和 tag 计 `enqueued_bytes`；出队前按原 tag 计 `dequeued_bytes`；MMU 准入失败或 BEgressQueue 拒绝时计 `dropped_bytes`，但不增加队列余额；链路下线清空已排队包时同时冲减余额并计丢弃。对每个 `(switch,port,tag)` 要满足 `enqueued - dequeued - queued_drop = current`；各 tag 的 `current` 之和必须等于同一出口 BEgressQueue 的 `GetNBytesTotal()`。日志给出逐端口、逐 tag 的原始计数与全局违规数；任一违规或类别观测不可用时停止效果 pilot。`admission_drop` 与 `queued_drop` 分开记录，避免把未入队的包当成队列流失。

## 比较边界

共同 `DCQCN, PFC=0, IRN=1`。所有算法配对复用固定源码 SHA、同一个不可变 trace、拓扑、seed、运行参数和独立实验 ID。先做 32 主机单类/双类、导入 1280 拓扑跨 ToR 四流、旧 `fecmp/dualtrack` 退化/回归、有限资源 pilot。pilot 仅检验可运行、守恒与等输入可比性；WS-10/11 才判断损害可重复和类别信号的效果增量。
