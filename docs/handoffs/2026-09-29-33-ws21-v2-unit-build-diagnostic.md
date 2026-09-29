# Handoff 33 — WS-21 v2 单测构建诊断

## 1. 本对话目标

按 Luna High 监督，继续 WS-21 精简反馈第一道工程门槛：隔离构建、反馈头单测和固定 40 流 off/on pair。当前仅进行预检、优化构建和单测构建诊断，40 流尚未启动。

## 2. 已确认的项目事实

固定开发 SHA `91f43c70bbb515ae35b3161d4d1e40d30ff90992`，分支 `feature/ws21-downstream-feedback`。40 流 trace SHA-256 `4e7d0e6a68e3230e8960a174e570a0a788c191fa0b44922408867b02c25782cc`、拓扑 SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。服务器首轮预检 `ns3host`：40 逻辑 CPU、无登录用户、无活动仿真、load1m 0、可用内存 122.99 GiB、空闲磁盘 5,694.3 GiB；冻结 ID 均未占用。

## 3. 已完成工作

个人 fork 通过 SSH Git bundle 同步；直接 fetch GitHub 超时，工作流已静默尝试一次 `login.sh` 后按规则恢复。隔离 ID `20260929-185100-ws21c-v2-unit` 的 optimized `-j2` 构建 `BUILT`，结束时间 `2026-09-29T11:13:54Z`。另建 `build-ws21-tests` 后在 1,522/1,633 步遇到已知无关错误：`CommandLineTestCaseBase::Parse` 声明去 const、定义仍有 const。WS-21 报文测试没有执行。

临时测试更改已经恢复；远端 Git 状态的 tracked 文件干净，只留这个隔离 ID 下的未跟踪测试 build 目录。失败编译日志和 248 个资源点保留；摘要 `results/20260929-185100-ws21c-v2-unit/logs/unit-attempt-summary.json` 给出进程树峰值 809.7 MiB、最低可用内存 122.25 GiB、最低空闲磁盘 5,692.74 GiB、最大 load1m 2.14。wrapper 因把预期 build 目录误当源码污染而在恢复后退出，诊断日志明确编译错误，不影响 tracked 源码恢复。

## 4. 已形成的设计决策

失败 ID 保留，不重用、不覆盖。40 流 off/on 暂停。预飞行表增加单独 unit 修复 ID `20260929-192700-ws21c-v2-unitfix`，在**新隔离副本**中临时同时修正声明和定义，跑 `devices-point-to-point` 后逐字节恢复；若通过再进入已有 off/on ID。这个暂时性构建修复不进入论文代码 SHA。

## 5. 当前状态

模型处于用户要求的 GPT-6 Luna High 实验阶段。远端首 ID优化构建通过、单测构建失败；还没有报文单测 PASS、新 40 流实验、raw 或业务结论。本地预飞行文档已增加失败记录和新 ID，待提交/推送后，runner 源码 SHA `91f43c70…` 仍为待测固定祖先。

## 6. 未解决问题

必须确认新 ID 未占用、确认 worker/源 SHA、再为单测 ID 做干净隔离优化构建和完整测试编译。修复后必须核对测试日志、逐字节恢复的源文件哈希与无 tracked 源码改动。若再次失败，保存该 ID 并停止，不启动 40 流。

## 7. 后续推荐动作

先提交并推送更新后的预飞行记录；重新检查工作区和新 ID `20260929-192700-ws21c-v2-unitfix` 不存在，再执行固定 SHA `91f43c70bbb515ae35b3161d4d1e40d30ff90992` 的独立 build 与修正后的单测。单测通过后重新检查资源/ID，再依序跑 `20260929-185200-ws21c-v2-off40` 和 `20260929-185300-ws21c-v2-on40`，每格保存 2 秒资源采样、PID、输入哈希、开始时间和 +10 分钟首次检查时间。任一技术或资源门槛失败即停。所有 raw 回传核验后停在 Sol High 分析边界。

## 8. 与其他工作流的关系

旧 WS-21 反馈长尾 pair 的时序扰动和资源缺项仍归属旧 SHA；本次单测编译失败不更改旧数据或 WS-10/11/12/19/20 no-go。Handoff 与实验预飞行表是不同材料；实际试验状态以每个 ID 的 metadata、日志、资源样本和 raw 为准。

## 9. CONTEXT SNAPSHOT

WS-21 v2 源码 SHA `91f43c70bbb515ae35b3161d4d1e40d30ff90992` 的优化构建 ID `20260929-185100-ws21c-v2-unit` 为 `BUILT`；测试构建在 1522/1633 因仓库既有 `Parse` 声明/定义 const 不一致失败，反馈单测未执行。源文件已恢复，tracked 状态干净，失败日志与资源收据保留。修正预飞行表增加新单测 ID `20260929-192700-ws21c-v2-unitfix`。40 流 off/on 暂缓，只有新单测 PASS 才可继续。模型现为 Luna High，全部终态回传后切 Sol High 分析。
