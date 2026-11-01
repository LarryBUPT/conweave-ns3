# WS-31 第十五节点：端点核心预检整合

日期：2026 年 11 月 1 日。来源为“WS-31 主对话：类别感知新机制构思与论证”（`01a19322-95a5-76e3-a4f5-1f1e9dde81ce`）的[节点交接](../research/evidence/ws31-endpoint-preflight-integration-20261101-r1/snapshots/main/endpoint-core-node15-handoff.md)。本轮只核本地原证据、Git 内容并更新状态，不执行 C++、模拟器或远端动作。

## 1. 本对话目标

确认可移植端点证据核心的一次编译和一次运行确有完整来源，随后单列实际对象探针草稿。核心手工快照与网络验收分别记录，不增加现有 43 格技术网络或 17 例非网络适配器条件。

## 2. 已确认的项目事实

固定源为 `20bc2d9f7c7c435bf832ba2fcaf0e07df00cf5da`，ID 为 `20261101-163000-ws31-endpoint-core-r2`，冻结计划哈希 `57ee56f60e6406dfaeab8e317910423e53fdb87e46982be6bf730dd4823fae47`。index SHA-256 为 `5c8fd34433da0d8d5d317f5c2d4b545e8e2a6657834af67b856a7d778a194b68`，QA 为 `16a64faf700cfecdd14e6a10a4cfd90698cc7b3c2094f2af1394f76ce81e7ce4`，与主收据相互关联。

实际仅一次同步、一次核心编译、一次新二进制运行。编译采用 C++11、-O2、-Wall、-Wextra、-pedantic、-DNDEBUG；核心的检查使用运行时异常。全量 NS-3 构建、部署、网络和旧测试重跑均为 0。

## 3. 已完成工作

Integration 的[独立收据](../research/evidence/ws31-endpoint-preflight-integration-20261101-r1/verification.json)核对 90 项索引文件、41 项 raw、5 项旧审查／WIP 和 4 项文献来源。对完整 Git 树的 4,845 条文件路径逐条比较模式、blob ID、大小和 SHA-256，合计 284,683,832 B。这里是路径计数，不称为唯一对象数；大规模源码内容只从固定 Git 对象流式读取，没有复制进新证据目录。

两份实际编译输入与固定源一致。50,520 B 本地 ELF 的 SHA-256 为 `15ed3dd0a023e59da058535e29797d7c67787912a619203ad2ee96e108dac86b`。编译、运行的 argv、cwd、环境、顺序、退出码及 stdout／stderr 哈希一致。stdout 精确报告两代手工流程完成、6 token 闭合、真实端点快照 0、网络 0；编译和运行 stderr 均为空。Integration 未再次执行该二进制。

五项库证据仅为保存的 ldd 解析及远端大小／哈希收据，未在本地重新核库文件字节，也不是内核运行时映射。编译和运行的子进程 rusage 最大 RSS 分别记录 122,944 KiB、10,232 KiB，不当作全系统峰值。

原主 checker 的相对根路径错误已澄清。旧脚本哈希与修正收据一致，新脚本只增加绝对路径解析，并化简一个无效果的字符串替换；源码、raw 和验收判据不改，没有重编译或重跑核心。旧收据按原字节保留。

## 4. 已形成的设计决策

可移植核心工程预检通过范围为手工快照下的身份、顺序、资源别名、观察时钟、token 及最终复用门。它没有操作真实传输 QP、生产 finished 位图、channel 或完成回调，不替代真实两代网络验收。

后续快照读取避免调用 `RdmaQueuePair::GetBytesLeft()`：其 IRN 分支会在相应条件下推进 snd_nxt 并丢弃 SACK，RdmaEgressQueue::GetNBytes 又委托该方法。首版探针按字段计算保守待发送载荷，与物理队列字节分列；当前只核静态调用方式，实际只读纯度仍须前后状态夹具验证。

## 5. 当前状态

全部核心调用终态后于 08:19:32 UTC 明确释放源码／入口／环境约束；释放记录确认无持久驱动，副 idle cursor 98 后才转入下一目标。Integration 主快照为 idle cursor `f7a3a118-6bff-483e-a32e-333396ead68d:22`，副 active99 为主交接状态，不直接重复派发。

实现树 HEAD 和个人 origin tracking ref 仍为 20bc，原核心两输入不变。当前 `qbb-net-device.h` 仅多窄 friend／注释，`ws31-endpoint-probe.h` 为未跟踪 WIP，字节与主收据及新计划一致。新探针未编译、注册、包含或调用；它故意不置 SWITCH_STATE 覆盖位，不能独自通过 ALL 认证，不继承核心验收为测量证明。

权威仓库分支仍为 `feature/ws23-ws24-evidence-integration`，本节点整合前 HEAD 为 `53002c2574ee38845a530f9bddb23a20dfdb984b`。本轮仅提交五份权威状态、本交接和 Integration 新证据；主、副源目录不整体暂存。

## 6. 未解决问题

探针接口可编译性、真实对象只读纯度、字段及设备覆盖尚未验证。交换机读取、默认关闭的原交付事件 channel token、Receive 返回后闭合、RX 对象保存、历史清理和旧完成 QP 保留／新 QP 追加接线仍待完成。

实际上下文 G1、真实两代网络正例及拒绝例、独立 C1 V0、三候选业务批次／背景尾部双侧效果和状态／运行成本继续必做。43 格网络、17 例适配器和本核心预检分别计数，没有新组合基线，WS-31 不闭环、不归档。

## 7. 后续推荐动作

唯一副已按[探针只读计划](../research/evidence/ws31-endpoint-preflight-integration-20261101-r1/snapshots/main/endpoint-probe-local-review-r1.json)审查两文件，计划哈希 `fd8e63b3692967d6f938d409945ee9dad12b5401772c2a07e9b56062c51482ee`。当前无编译、测试、远端或修改主源码权限，两文件保持原字节直至审查返回。

主据审查补齐必要接口，再为真实对象编译与纯度夹具冻结独立源码和工程门。随后完成交换机、原事件 channel、G1 及真实两代网络正反例；不得以 getter 代码存在代替测量，也不调用会改变 IRN／SACK 的读取方法来证明静默。

## 8. 与其他工作流的关系

Integration 维护状态和本地独立证据，主实现并验收，唯一副沿固定目标审查或执行。Ofan 暂缓，WS-29 不读取、唤醒或归档，旧矩阵不恢复，QueuePin 投稿稿不改。新增正式方法仍按 CCF A/B、必要性、成本及忠实性门审查。

节点参考复核从候选 README、reading-log 进入，核对 DiffFlow arXiv:1604.05107v1 的技术和核验记录。借鉴的是前置状态完成后再启用后继行为的顺序约束；其结束检测及回收描述不足，不能支撑本项目排空或复用正确性。分类喷洒、简化传输和独立队列下的平均结果不外推为 RDMA、批次或背景 P99 收益。

## 9. CONTEXT SNAPSHOT

20bc 单次核心编译／运行及完整交付已主验和 Integration 独核：两代手工流程、6 token、真实端点／网络 0；90 项索引、41 raw、完整 4,845 条 Git 文件路径及实际 ELF 均匹配。旧约束明确释放后进入探针 WIP 本地只读审查，原核心不改，新探针无运行证明且缺交换机覆盖位。43 网络／17 适配器不变，真实接线、G1／两代网络和 V0／效果／成本仍待完成。
