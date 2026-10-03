# WS-25 16/18 并发容量试跑协议

日期：2026-10-03。此试跑只选定安全且有吞吐收益的远端并发度；重复 seed05–08 的旧输入，不增加研究独立样本，也不进入算法收益判断。

固定仿真 SHA `a656104d05c681f9b3a998b5ef4ce3e644558d02`，拓扑和四个 b192 trace 的 SHA 见[冻结计划](evidence/ws25-resource-capacity-plan.json)。34 格均有全新实验 ID；16 格先行，通过后最多再跑 18 格。六个算法仅作同输入确定性回放；OS1/400G、PFC0/IRN1、`netload=10`、`simul_time=0.01`、buffer 9 MiB 和无 WS-25 诊断均固定。每格独立源码、`mix/output`、日志、元数据、资源样本和结果目录。

远端 worker 的 16/18 准入只对上述固定 SHA、trace 哈希、拓扑哈希和参数开放。互斥启动锁内拒绝其他普通用户活动进程、未知 ns-3、其他工作负载混跑、1 分钟 load 大于 20、空闲盘小于 100 GiB。按既有单格树 RSS 峰值约 4.6 GiB，以每个未达峰格及新格各 5 GiB 预留，再要求 `MemAvailable` 至少剩余 32 GiB。通用工作负载仍使用原有 1/2/4/8/12 档。

16 档结果必须全部成功、原始结果逐格核对且吞吐比 12 档的 98.41 格/小时提高超过 5%，才准继续 18 档。运行中若出现其他用户作业、未知仿真、load 超 20、可用内存低于 32 GiB、空闲盘低于 100 GiB 或任一格失败，停止开启新格、保留 ID 和原始数据，并安全降载。18 档完成后按吞吐与资源余量选择正式矩阵上限；吞吐提升不足 5% 时采用上一个通过档。18 档也未达 CPU 饱和时，先分析实际 CPU 使用率与整批吞吐，不能仅凭内存余量继续增加进程。

每格完成后运行 WS-25 原始 verifier，并与相应 r4 校准格核对 FCT SHA；最终从原始资源样本独立复算墙钟时间、峰值负载与最低可用内存。远端仿真阶段按工作流以 Luna High 静默监督，终态由 Sol High 做分析。入口为 `python scripts/run_ws25_resource_capacity.py plan|prebuild|run|verify`；收据落在本机忽略目录 `results/ws25-resource-capacity-receipts.jsonl`，摘要落在 `results/ws25-resource-capacity-summary.json`。
