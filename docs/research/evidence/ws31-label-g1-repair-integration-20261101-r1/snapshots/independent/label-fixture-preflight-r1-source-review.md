# 新标签夹具源码独立审查

日期：2026 年 11 月 1 日。固定源 `4605fa32af440998f4280b641e5c2de2195ea4c3`，父提交 `50603927fc09a68d9f2e038129aaee3a3d021081`。结论：**发现一项执行门缺口，按冻结停止规则结束本次预检。**

## 1. G1：C++ 隔离门缺少契约要求的实际配置

修订二契约第 6 节要求，标签夹具启用时使用共同传输条件，并拒绝旧故障／诊断配置。Python 的 [worker 校验](E:/研/毕业论文/workspace/ws31-candidates-implementation/scripts/remote_worker.py:791) 检查 PFC=0、IRN=1、指定拓扑、ws31 输入和旧配置冲突。

C++ 的 [ValidateLabelProfile](E:/研/毕业论文/workspace/ws31-candidates-implementation/src/point-to-point/model/ws31-label-fixture.h:28) 只接收 profile、模式、旧 transform、composition、lifecycle、lifeProfile 和 observe。[主程序调用](E:/研/毕业论文/workspace/ws31-candidates-implementation/scratch/network-load-balance.cc:1604) 也没有传入传输条件或旧故障／诊断状态。这个入口因而不能独立拒绝它们。

一个可按源码直接判断的反例是：`WS31_LABEL_PROFILE=1`、`WS30_OBSERVE=2`、模式 36，旧 transform／composition／lifecycle／lifeProfile 都为 0，同时 `WS25_DIAG=1`。C++ 标签门实际收到 `(1,36,0,0,0,0,2)`，其拒绝条件为假；worker 对应的 `ws25_diag=1` 则会拒绝。相同缺口适用于不合要求的 PFC／IRN 配置，因为这两项根本没有进入 C++ 标签门。**这是静态调用链反例，本轮没有执行这个组合，也没有声称完整仿真已运行。**

新增 [C++ 核心测试](E:/研/毕业论文/workspace/ws31-candidates-implementation/tests/ws31_label_test.cc:41) 将上述七个参数的正常组合列为通过例，只测试这七项的错误值；[Python mock 的冲突例](E:/研/毕业论文/workspace/ws31-candidates-implementation/tests/ws31_label_runner_test.py:48) 无法补充 C++ 入口本身缺少的检查。

必须在后继源码中，将实际解析的传输条件、输入资格及冲突状态送入 C++ 启动校验，或提供等效的明确启动检查。新增核心应包含对应的直接拒绝例，并核对主程序传入真实配置。profile 0 的既有行为、500 ns、哈希桶和三模式算法保持原样。若主选择将契约限定为仅受管 worker 入口，须先明确修订契约；本副不自行放宽当前停止线。

## 2. 其余已完成的静态核对

- 计划哈希、父提交及 10 个变更对象全部匹配。完整 Git 树为 4,839 项。
- SwitchNode、C1 预算核心、C3 配额核心、StartHash／StartDelay、QP 业务真值字段和 run.py 的固定对象均与父提交相同。
- LabelAt 使用原需求时钟及当前构包时刻。profile 1 区分缺失与显式 0，profile 2 保留未知类别，profile 3 使用固定 StartHash 的桶 0。
- C2 仍只在需求时采样一次，QP 的原业务标签保持。构包日志有 uid／flow_id，逐跳日志另外读取实际 PacketTag 的 present／value，支持后续关联核验。
- CLI 参数、worker 元数据和显式环境覆盖均已读到。profile 0 保留旧 transform 的标签值及存在性语义；网络回归尚未运行。
- generation=0 的标签子阶段没有新增清理或重建机制，与修订二的范围一致。完整生命周期仍待后继夹具。

这些结论均为源审查，不代表新核心、mock 或网络格通过。

## 3. 执行状态与约束释放

同步、部署、远端审计、完整构建、新核心、Python mock、旧核心及网络运行均为 0。资源门在源码门失败后没有启动；本轮未检查或创建远端实验 ID，不作远端 ID 是否存在的判断。

本副没有在途预检命令。当前目标随停止释放实现及入口／环境兼容约束，供主修源；**未建立实验源码副本，不能称“源码复制完成”。** 修复后由主冻结后继 SHA 和计划，再另行派发执行。

固定对象、调用链反例和未执行项见[收据](label-fixture-preflight-r1-receipt.json)，完整交接见[九节交接](label-fixture-preflight-r1-handoff.md)。
