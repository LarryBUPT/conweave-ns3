# WS-25 v2 同输入非扰动诊断

状态：2026-10-06，远程 build/run 前冻结；性质仅为已见小输入的正确性和观测核验，不计独立收益样本。

- 唯一新 ID：`20261006-123000-ws25-v2-diag-mixed8`。模式 `destspread`（22），仿真源码 SHA `87bb136ba85126c8c6c883814c7fa10cdcd74fda`。
- 输入 `ws25_v1fix_mixed8.txt` SHA-256 `29ebe2dcf38c0e4d29326947c4bc4e111f6b56fe378c020c30ee788fbaa5effb`；拓扑 `topo_1280_400G_400G_OS1` SHA-256 `74a6f7154ca10c3cd6dfd45046c4f8abf0ce27faa8ad11446b6a52920b83afba`。
- 与已验收的 `20261006-070000-ws25-v2-pre-mixed8` 唯一运行参数差异为 `ws25_diag=1`；其他参数为 ns-3 seed=1、400 Gbps、9 MiB、DCQCN、PFC=0、IRN=1、`simul_time=0.01`、`netload=10`、cap=1。
- 两格必须分别通过 metadata、trace/拓扑、8/8 完成、逐流身份、类别队列守恒和逐运行资源验收，且原始 FCT 文件 SHA-256 完全相同。关闭诊断格的 FCT SHA 为 `d689d88a6d6d187be45c723d9d44319d46718a87288c3186bb354dc37d3a1bbf`。若不同，诊断有扰动，保留该 ID 并停止将日志解释成非扰动观测。
- 检查诊断原始记录是否包含 tag1/tag2 的逐 QP 乱序、NACK/CNP、重复发送与超时，以及源 ToR 端口选择计数。缺失字段不能填零；即使全零也只适用于此 8 流小输入，不代表全量需求无乱序风险。
- 启动前现场确认其他用户作业、未知 ns-3/worker、锁、load≤20、每 worker 预留 5 GiB 后 MemAvailable≥32 GiB、空盘≥100 GiB；watcher 先于 run，RSS≤32 GiB。SSH 超时不当作失败重启；先读原 ID、PID、raw 再恢复。诊断通过后使用与 v1 完全不重合的新需求 seed 作独立筛选和资源 pilot，正式实验另冻。
