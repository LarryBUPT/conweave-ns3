# Handoff 49：WS-24 后续验证本地冻结

日期：2026-10-01（中国时间）。来源任务：Codex 对话 01a0f1da-f1e2-7870-9361-24b4d626fd76，WS-24 多 NIC 验证。

## 1. 本对话目标

在 v2 两格最小正确性验收后，在独立 checkout 内完成旧五/六列四 baseline、320-host 目标拓扑、动态 CNP 和 rail×placement 四臂验证的本地审查与协议冻结。用户指令明确禁止自动部署 worker、同步代码或启动下一批仿真；共享入口应先由 WS-23 五格使用，完成后再协调。

## 2. 已确认的项目事实

- v2 仿真固定源码 SHA 824e3fa0c4c06dd9894474a81e729931d59a3108。正例 20261001-100000-ws24-minimal-v2 已完成 4/4 flow、32,768 B 守恒；跨 rail 负例 20261001-100100-ws24-crossrail-reject-v2 在 flow parser 按预期拒绝、无 FLOW_START/FCT。
- 导入 OS1 图和 WS-24 多 NIC/placement 输入均为显式 synthetic fixture，不代表物理部署或真实 job trace。
- 五列 OS2 trace 的 Git blob SHA-256 为 abebc3170428aa22ebb13b15246243b806cb4f749bf4c9e6a80fb0a4a694a3cf，19,388 flows；六列小 trace 为 be78b4cb5afbcceb51f42ee10594c32b8a4322bc3e069ed0413554e41ba75748，4 flows，tag=1/2 各 2 条。Windows CRLF 与 LF blob 哈希分开记载。
- 新 incast fixture 为 4 个源 host 在 rail 0 同时发往 host 1 的 rail 0，各 1 MiB，总量 4,194,304 B。文件 SHA-256 fd621d8ea2db69549874193fc79c1ae9d7159aef3c45105401fdd128b5a00ce7；11 项 manifest SHA-256 55997be83ecf7e43accc2f6bc546b97185943657cdc64da0d5c89ef91a52b127。
- 远端最后只读复核为 2026-09-30T19:16:43Z：0 个登录用户，未发现 Waf/GCC/network-load-balance/run.py 进程，load 约 0.02、MemAvailable 约 122 GiB、工作区空闲约 5.6 TiB。旧 v2 两个 ID 均为终态，入口释放；随后已停止远程操作。

## 3. 已完成工作

- 将后续工作拆为 A 旧格式 × 四 baseline 8 格、B 320-host correctness 1 格、C CNP correctness 1 格和 D rail×placement pilot 4 格，并冻结输入、验收、预留 ID、资源门槛和执行顺序，详见后续协议。
- 修改 make_ws24_inputs.py 生成受控 CNP incast；verify_ws24_inputs.py 现在核验 host/NIC/rail 可达、同一目标 rail、rank 身份及流量守恒。新增 .gitattributes 规则以保留生成输入的原始字节。
- 更新 CURRENT_STATE、WORKSTREAMS、ROADMAP 与 WS23_WS24_VALIDATION_PLAN；写入 Handoff 48、Handoff 49 和 v2 结果记录。所有新增 ID 均仅本地预留。
- 本地运行 make_ws24_inputs.py、verify_ws24_inputs.py 和 py_compile；11 项输入哈希通过，四个 rail×placement 臂各为 10 flows/2,408,448 B；目标拓扑离线 RTT/BDP 为 600 ns/30,000 B；incast fixture 为 4 flows/4,194,304 B。
- 本地 Markdown 链接审查发现一个已有未命中链接：CURRENT_STATE.md 中 ../../results/ws19-pilot-receipts.jsonl 在本 checkout 不存在；本轮未改其指向。

## 4. 已形成的设计决策

- **Decision:** 所有后续试验输入都用版本化 synthetic fixture，并由 manifest 固定哈希。**Rationale:** 本项目没有真实 NIC/job placement 来源，合成工程机制验证必须与真实部署主张区分。**Alternative rejected:** 把端点号相邻解释成共处一台物理机。
- **Decision:** 四类后续格共用一个最终固定仿真 SHA；当前 SHA 尚未固定。先实现并审核限量 CNP 生成、接收和 DCQCN rate-decrease 观测，再包含 fixture/manifest 后一起冻结。**Rationale:** 当前只记录接收端 flag 和每 QP 首个 ACK，不足以证明源端收到带 CNP 的 ACK/NACK 或 QP 状态改变。**Alternative rejected:** 把 CNP=0 的最小格当作动态覆盖，或让对照臂混用源码 SHA。
- **Decision:** 4 臂结果只作为一个合成 seed 的描述性 pilot。**Rationale:** 当前逻辑需求/placement 输入不是独立真实 job 样本。统计确认需要新的独立需求与事前判据。

## 5. 当前状态

WS-24 保持 ACTIVE；本地协议和 incast 输入已提交。checkout：workspace/ws24-multinic-validation，branch feature/ws24-multinic-validation，工作树干净。最终共同仿真 SHA 仍未固定，CNP 观测实现/构建/运行均未完成。本地 commit 未推送；没有 deploy、sync、build 或 run。

## 6. 未解决问题

- 8 个五/六列 × 四 baseline 回归未运行；历史 FCT 完整哈希/raw 不在此 checkout，未来先从既有结果只读取 reference。
- 320-host correctness 未运行；离线 RTT/BDP 预测不能代替运行时 route/IRN 日志和逐流 raw。
- 新 CNP incast 尚未触发 ECN/CNP；接收端 flag、源 NIC identity、源 QP pending state 与 DCQCN rate decrease 观测改动未实现或编译。
- 四臂未运行；其结果不支持真实训练性能或统计确认。
- CNP 使用随 ACK/NACK 携带的 flag；独立 ReceiveCnp 包仍不支持。

## 7. 后续推荐动作

1. 先实现受限 CNP 收发/DCQCN 状态观测并做本地审查，更新输入/源码哈希，冻结 A/B/C/D 共同 SHA。
2. 等 WS-23 完成五格并释放共享入口；之后重新核对服务器用户、作业、worker、资源和全部预留 ID。
3. 在实际 Luna High 下按 A→B→C→D 执行；遇到异常保留 raw，以新 SHA/ID 修复验证。所有终态 raw 回传后实际切回 Sol High 分析。
4. 在全部预设格验收、代码/数据/结论一致之前，不关闭或归档 WS-24。

## 8. 与其他工作流的关系

WS-23 优先占用共享远程执行入口并负责传输恢复五格；WS-24 不与其并行切换共享 worker。WS-25 只整理实际完成的证据，不替代 A/B/C/D 执行。WS-24 所有新增模型输入为 synthetic；不得外推为真实部署映射或收益。

## 9. CONTEXT SNAPSHOT

v2 最小多 NIC 正例/跨 rail 拒绝负例已在 SHA 824e3fa 下终态并验收。本地协议提交未推送；新增四源同 rail 4 MiB incast 与 manifest 已验证；后续 A/B/C/D 的本地预留 ID、输入、验收和顺序见 docs/research/ws24-followup-validation-protocols.md。远端最后检查为空闲，此后已停止远程操作。WS-24 仍 ACTIVE：旧 baseline、320-host、动态 CNP、四臂均未运行；CNP 观测器与统一实验 SHA 尚待实现/冻结。先完成 WS-23，再重新协调远端实验与模型切换。
