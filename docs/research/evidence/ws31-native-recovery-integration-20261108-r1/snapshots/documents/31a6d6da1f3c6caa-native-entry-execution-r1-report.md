# WS-31 原生入口执行 R1：完整构建失败

## 1. 实际结果

**新 ID 的唯一完整构建失败，20 案均未运行。** declarations 头缺少 Waf 导出项，未生成案例准入请求、gate、目标 ELF 或已链接项目库。本 ID 保留失败，不改源、不重试；主须用新固定源和新 ID 继续，工程验收仍未完成。

实验 ID：`20261108-122127-ws31-native-entry-r1`。源码为个人 fork 分支 `experiment/ws31-native-entry-r1`，commit `cf54734ced37d1754bfa840bf1c52596b57522f1`。该有限工程失败不关闭 G2 科学义务。

## 2. 前置与实际命令

本机独核正确的 source-fixed-git-bytes.tar.gz：全部 4,870 个普通文件匹配 Git blob、长度、SHA-256 与可执行位，未误用首份 CRLF 失败包。两份 D1／D2、seed 5310001 旧声明的字节、长度、头部和家族均匹配，input_binding_sha256 为 `8c5a25c2c12a702c047715ae78b1e8b25b1afd23a3798c3a3059ac3f3247cfde`。

新 worker 哈希、Python 3.5 语法及继承准入函数逐字一致性已独核；18 项本机纯控制检查收据已审读，它们不计 C++ 案例。远端新路径此前不存在，实际提取仅普通文件／目录，源码与输入再次逐项核验；未触及共享 cache／worker 或同步部署。

启动前重新观察全部用户／PID 祖先、CPU 增量、资源和维护候选，无其他活跃用户作业。孤立调试器和 hg 查询按当前状态、start ticks、无子进程与零 CPU 增量归为被动进程；系统 dockerd 活动单列，不沿用旧 PID 假设。load1＝0，可用内存约 122.52 GiB，磁盘约 2,287.61 GiB。实际启动使用 env -u PYTHONOPTIMIZE python3 -B，优化关闭，未带科学环境变量。

| 实际直接子命令 | PID | 退出码 | 耗时 |
| --- | ---: | ---: | ---: |
| g++ --version | 326960 | 0 | 0.006 s |
| ./waf configure --build-profile=optimized | 326961 | 0 | 3.828 s |
| ./waf -j2 | 327200 | 1 | 22.643 s |

实际编译器为 Ubuntu GCC 5.4.0。仅执行 3 个直接子命令，configure 和完整 build 各一次；ldd＝0、案例进程＝0、网络运行＝0，无超时或重试。原预算 24 个直接子命令的剩余部分未执行。

worker PID 为 326959。失败收据生成于 **2026 年 11 月 8 日 12:28:29.803984（北京时间）**，原值 2026-11-08T04:28:29.803984Z；不是本报告生成时刻。命令收据保留各自 started_epoch_s 和 elapsed_s，不补造 OS exec／退出精确时刻。worker 最终 OS 退出码未单独捕获；FAIL 收据及进程已退出有观察，build 子进程退出 1 有直接记录。

## 3. 失败证据与修复入口

[原始 build.stderr 第 753 行](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/native-entry-execution-r1-raw/remote-result/execution/build.stderr:753)记录：

```text
./ns3/ws31-v2-native-entry.h:13:45: fatal error: ns3/ws31-v2-native-declarations.h: No such file or directory
```

实际链为 network-load-balance.cc → applications-module.h → 新 Entry 头。新头被安装不等于其内容已编译通过；最后的 749／1,484 是混合构建任务进度，也不是 749 个 C++ 验收项通过。

固定源中 declarations 头存在，但 [point-to-point 导出列表](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/native-entry-execution-r1-raw/diagnosis/point-to-point-wscript.cf547.txt:59)未列 model/ws31-v2-native-declarations.h；Session 头已在第 69 行导出。[Entry 固定原像第 13 行](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/native-entry-execution-r1-raw/diagnosis/Entry-header.cf547.txt:13)通过 ns3/ 前缀引用 declarations 头。

主的最小修复入口是 src/point-to-point/wscript 的 declarations 头导出。此处未修改源码，也不推断修后必无其他编译错误。前轮静态 include／API 检查漏识别了生成导出头边界；本次真实构建结果修正了可构建性判断。

完整 configure／build stdout／stderr、build/config.log 与 c4che 配置已回传。实际 g++ 行保留 -O3、-g、-std=gnu++11、-march=native、strict-aliasing、pthread 等参数，不只保存错误摘录。

## 4. 准入与保护

worker 在 BUILD 阶段写 FAIL，completed_cases＝[]；未生成 case-admission-request、post-build-resource-gate、case-admission 或成功 receipt。没有预放行、刷新或复用 gate。20 个注册案例全部未执行，pending／ENTRY_FAILURE_DRAIN、终态 P2、实际 QP／Packet 与诊断验收均待后继；旧 R4、控制检查和 configure 不替代它们。

北京时间 12:31:04 的终态观察确认 worker 已退出，无该 run 残余进程或编译器。远端 4,870 个源文件和权限、两份实际输入均未变，目标 ELF 未产生，未观察到已链接项目库；这些不是可用二进制证据。

北京时间 12:33:20 的本机终检通过：发布 checkout 的 4,870 个原字节文件、原 WIP 的 4,868 个 tracked／untracked 文件、两边 HEAD／branch／index／status 和 12 份绑定工件保持，包括旧失败归档、输入、控制和计划。只写本次指定 report／evidence／raw 前缀，guard 保持待主验收。

## 5. 原始回传与节点边界

[完整 raw](E:/研/毕业论文/workspace/LarryBUPT-conweave-ns3/docs/research/ws31/independent/native-entry-execution-r1-raw)含前置及资源观察、上传／启动记录、完整失败日志、控制／输入副本、正确源码包、全树终态身份、配置与独立校验。结果包只含 25 个普通文件，拒绝链接和路径穿越；24 个清单成员及清单自身哈希均匹配。

结果归档 SHA-256：`9afb159c480f57d4d44afe19c99b8421976206d8d763c7cde0d2875cbdd71707`；远端 transfer-inventory.json：`4f4d86ce9ecd155628352c241b5a102169de4a341d0394386b04ed4dd49a69aa`。原远端 ID 与失败收据保留。

已复核候选 README／reading-log 入口，本问题是 Waf 导出缺失，无适用的新论文机制借鉴；此前请求、QP 与完成的边界保持，入口哈希见 raw/reference-node-review.json。未报告任何新的成本、网络、完成、代际或科学收益结论。

主独立验收失败 raw 后，最小修复、准确发布新固定源，再另立新 ID 的完整构建／postbuild gate／20 案计划。OS2／framing、完成／共享协议／真实超时／两代、V0、消融、双侧效果与实际成本等 G2 义务继续保持未完成。
