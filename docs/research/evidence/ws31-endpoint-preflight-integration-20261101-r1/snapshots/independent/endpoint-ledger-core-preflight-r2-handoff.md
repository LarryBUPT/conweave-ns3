# WS-31 端点证据核心 r2 九节交接

日期：2026 年 11 月 1 日。来源聊天：`01a19323-2201-7b23-a0f1-905c71496d38`；委派主聊天：`01a19322-95a5-76e3-a4f5-1f1e9dde81ce`。证据等级：独立静态审查及单次可移植核心工程验证。

## 1. 本对话目标

按[新单目标计划](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/main/endpoint-ledger-core-preflight-r2.json)，独立审查固定新核心；通过新进程／资源／ID 门后，至多一次同步、一次新 ID 源码复制、一次 C++11／DNDEBUG 编译和一次新二进制运行。失败即停止后继。全部产物位于 independent 的 `endpoint-ledger-core-preflight-r2*` 范围。

## 2. 已确认的项目事实

新源 `20bc2d9f7c7c435bf832ba2fcaf0e07df00cf5da`，父源 `1f917f44fcfb88e61f3ad22c5cc75fa3a06b6c0e`，个人分支 `feature/ws31-candidates`；新实际远端引用已核。差异仅新增头文件和独立测试，未被 Waf 或运行路径引用。完整源树 4845 项、284,683,832 B，Git 树输出 SHA-256 为 `3da8acbcc1809389aac24adc1936d22874821077e40ddd397723fa7d977e0e64`。本地实现树保持干净，旧审查和封存 WIP 共 5 项哈希未变。

## 3. 已完成工作

主对话决定并冻结 r2 设计、输入和判据；本副对话执行只读审源、来源核验、新门、单次同步和隔离预检。新 ID `20261101-163000-ws31-endpoint-core-r2` 的编译、运行均退出 0；stdout 精确符合预期，stderr 为空。两代完整账本流程及 6 个闭合 token 通过运行时检查。回传 41 项原始文件，逐项校验日志、环境、完整树、二进制、工具链、5 项运行库与资源收据。详见[报告](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-report.md)及[索引](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-index.json)。

## 4. 已形成的设计决策

资源所有者按节点与实际 TX／RX 键、交换机四元组登记，跨 tuple 别名永久拒绝；避免借用无关排空证书。token 校验精确 serial、UID、flow_id、源／目的节点和接口、类别与原因；held 只表示未入网副本。快照绑定身份、时刻和字段声明，合法 false 观察推进时钟，最终创建再次要求旧代新快照。当前合同仅接清理后新需求和完成型请求，不后移原需求。

R2 延续主契约：保留已完成旧 QP、追加新 QP，避免生产 Clear 残留完成位。未修改或测试生产位图。ALL 手工标记与实际测量分开；未采用用等待时长、清零 token、启用旧控制器或修改基线键的替代方案。

## 5. 当前状态

COMPLETE FOR PORTABLE CORE PREFLIGHT；WS-31 仍 ACTIVE。远端 g++ 5.4.0，以冻结参数编译一次并运行一次；二进制 SHA-256 `15ed3dd0a023e59da058535e29797d7c67787912a619203ad2ee96e108dac86b`。真实端点快照 0、网络 0、全量 NS-3 构建 0、部署 0、旧核心／夹具重跑 0。来源、编译和运行进程均终态，本地无遗留项目驱动；[源码／入口／环境约束已显式释放](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-guards-released.json)。本任务不授权下一项执行。

## 6. 未解决问题

必做：真实快照适配器与标签缺失拒绝，原交付事件的 post-Receive token 闭合，保留追加 QP 与旧 finished 位真实分支，完成历史和交换机清理前后收据，新上下文 G1 及双代网络正例／拒绝例。随后仍有独立 C1 V0、三候选双侧效果及状态／运行成本验证。没有当前核心预检阻塞；上述任务仍未实现／验收，不改为可选。

## 7. 后续推荐动作

主对话先从 index 与 raw 独立重放本轮哈希、argv、环境、退出与 stdout；再将本核心与真实接口表结合实现默认关闭接线，独立审源后另冻 SHA、输入、ID 和资源门，取得网络授权后验证。不要以本轮 PASS 代替真实排空证书或复跑旧格。本副对话到本目标交付停止。

## 8. 与其他工作流的关系

父源 1f 的默认兼容验收保持原证据，不转移为 20 源的新端点能力证明。未改主材料或科学源码，未开展 Ofan 专门工作、WS-29、旧控制器、旧矩阵或新基线。候选参考借鉴复核使用 DiffFlow v1 的顺序思想，缺少结束与回收协议的论文不能背书 RDMA 复用；不产生业务效果结论，见[复核记录](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/endpoint-ledger-core-preflight-r2-reference-review.json)。全项目闭环仍由主对话集成和推进。

## 9. CONTEXT SNAPSHOT

固定 `20bc2d9f` 的可移植证据核心已通过独立审源、新门、单同步、隔离源逐文件核验、1 编译和 1 运行；计划 SHA-256 `57ee56f60e6406dfaeab8e317910423e53fdb87e46982be6bf730dd4823fae47`。ID `20261101-163000-ws31-endpoint-core-r2`；原始结果在远端 `/home/fnl/lzy/results/20261101-163000-ws31-endpoint-core-r2`，本地 raw/remote-results 下有 41 项经核验文件及清单。二进制哈希 `15ed3dd0a023e59da058535e29797d7c67787912a619203ad2ee96e108dac86b`；唯一 stdout 表示 requests=2、completed_generations=2、closed_tokens=6、real_endpoint_snapshots=0、network_runs=0。保护已明确释放，主实现树干净，r1 原始字节未变。下一步为主对话验收并实现真实接线；本轮没有全构建或网络授权。
