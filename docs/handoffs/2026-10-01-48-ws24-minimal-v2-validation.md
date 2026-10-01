# Handoff 48：WS-24 v2 最小多 NIC 正反例验收

## 1. 本对话目标

WS-24 在上一轮 v1 断言失败修复后，用固定仿真源码完成两主机四 rail 最小正确性正例与异 rail 拒错负例，回传原始数据并按协议验收。只交接本阶段证据，不关闭 WS-24 全部必做验证。

## 2. 已确认的项目事实

- 独立 checkout：`workspace/ws24-multinic-validation`；个人 fork 分支 `feature/ws24-multinic-validation`。
- 两格仿真固定源码 SHA：`824e3fa0c4c06dd9894474a81e729931d59a3108`；正例和负例均由隔离 optimized `-j2` build 生成。后来验收器修正提交 `bd05747b52451923726939797f5ad24c245bf4df` 不属于该实验源码 SHA。
- 运行前 worker SHA `0be12e21ce37655f52a19803824f2b8d24a9a2c84ba0cd58124eb6fb96de62eb` 和观察器 SHA `cbe3e3317a0eca93e607485c7ec63516b888b5d4f909715664d3e0ca508606f5` 与冻结记录相符。
- 输入源自明确的合成 fixture；不代表真实服务器/NIC 或 job placement。

## 3. 已完成工作

- 用户授权按固定 v2 协议运行；运行前两 ID 均空，服务器无其他登录用户/构建/仿真作业。负载和资源远低于停止门槛。
- 正例 `20261001-100000-ws24-minimal-v2` / raw `559237678`：`SUCCEEDED`。运行日志报告 8 个 rail-specific 目标、8 条 host pair/rail 路由、max RTT 440 ns、max BDP 22,000 B，IRN BDP 亦为 22,000 B。四条 8,192 B 流分别走 rail 0–3；TX QP、首个 RX DATA、首个 RX ACK 身份全覆盖，FCT 与身份输出各 4 行，unique receive、ACK sequence 和 TX payload 每流均为 8,192 B，总完成 32,768 B。修正后的 `verify_ws24_result.py` 全项通过，输出 `feedback_identity_verified=true`。
- 负例 `20261001-100100-ws24-crossrail-reject-v2` / raw `208672100`：optimized build 成功；运行状态 `FAILED` 是事前预期。raw `config.log` 在解析第二行报 `WS24 invalid flow row 2`，没有 FLOW_START，FCT 0 B，WS24 输出无完成行。
- 资源观察器覆盖两格 build/run；正例 99 点、RSS 峰值 661.840 MiB、最低可用内存 122.387 GiB、最低空闲盘 5661.411 GiB；负例 75 点、703.465 MiB、122.350 GiB、5660.381 GiB。终态 raw 与摘要已 fetch 到本地。
- 验收器首轮失败源自读取 launcher 日志而非 raw ns-3 日志；事件打印的 IPv4 字符串也遵循仓库仅输出两个 octet 的 `Ipv4Address::Print`。提交 `bd05747b52451923726939797f5ad24c245bf4df` 修正日志来源、格式比较并增加 RTT/BDP 断言；原正例 raw 重跑通过。

## 4. 已形成的设计决策

- 合成最小拓扑证明指定合成输入下的多 NIC/rail/QP/ACK 工程路径与跨 rail 输入拒错；不把零 CNP flag 解读为动态 CNP 接收已验证。
- v2 最小正确性通过仅开放下一步本地审查和协议冻结；不据此关闭旧格式回归、目标拓扑、CNP 动态格或四臂比较。
- 下一远程批次不自动部署 worker、不自动启动；先等 WS-23 冻结完成并执行其五格批次，释放共享入口后再协调。

## 5. 当前状态

WS-24 仍为 ACTIVE。仿真源码 SHA `824e3fa0c4c06dd9894474a81e729931d59a3108` 的最小正例与拒错负例终态证据已回传。验收器修正已提交推送。远端入口已释放。当前阶段按 Integration 指令在 Luna High 监督、Sol High 收束边界交接；不是 WS-24 任务闭环。

## 6. 未解决问题

- 旧五/六列四 baseline 的固定输入/源码回归未执行。
- 320-host 目标拓扑尚无端到端运行；其 RTT/BDP 目前只有本地静态推导 600 ns/30,000 B。
- CNP flag 在最小格为 0；须设计可触发的 ACK/NACK 携带 flag 往返正确性格。
- 固定逻辑需求与总字节下单/多 rail、固定/可变放置四臂对照未执行，效果证据不存在。
- 真实部署 host/NIC/job 映射仍无来源；合成结果不支持部署主张。

## 7. 后续推荐动作

1. 仅在此独立 WS-24 checkout 内审查和冻结旧格式四 baseline、目标拓扑正确性、动态 CNP 正确性、四臂输入/参数/验收与资源门槛。
2. 下一批先由 WS-23 执行其已冻结的五格，并明确释放共享运行入口。
3. 此后重新核验服务器、worker/observer SHA、ID、资源，再协调下一远程批次；正例不通过不得启动负例。所有新修复使用新源码 SHA 与独立 ID。

## 8. 与其他工作流的关系

WS-23 与 WS-24 共用远程 worker/服务器入口；本批两格已终态、fetch，入口释放。WS-24 后续只本地工作，不改 WS-23 checkout 或目录，不与 WS-23 竞争远程入口。实验输入与结果在 WS-24 checkout 的忽略目录 `results/20261001-100000-ws24-minimal-v2/`、`results/20261001-100100-ws24-crossrail-reject-v2/`。

## 9. CONTEXT SNAPSHOT

WS-24 的 v2 两主机四 rail 合成正确性批次已完成：固定仿真 SHA `824e3fa0c4c06dd9894474a81e729931d59a3108`；正例 4/4 flow、32,768 B 守恒且 RTT/IRN BDP=440 ns/22,000 B；跨 rail 负例按 parser 契约拒绝且无 FCT。两格 raw 与资源摘要均已回传，修正验收器提交为 `bd05747b52451923726939797f5ad24c245bf4df`。WS-24 仍 ACTIVE。远端入口已释放，下一批不自动部署/启动；独立 WS-24 checkout 继续冻结旧格式四 baseline、320-host 目标、动态 CNP 和四臂对照，本轮后优先由 WS-23 执行五格再协调。完整证据见 [v2 预飞行收据](../research/ws24-minimal-multinic-preflight.md) 与 [必做验证清单](../project-state/WS23_WS24_VALIDATION_PLAN.md)。
