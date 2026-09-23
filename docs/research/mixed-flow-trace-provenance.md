# MixHash 参考仓库 MoE / 背景流输入资产

本分支只迁移实验输入，不迁移 MixHash 的负载均衡、重排、拥塞控制或传输代码。来源是只读参考仓库 [`maplerime/conweave-ns3`](https://github.com/maplerime/conweave-ns3) 的 `main`，提交 `470c58026ec3933eabb6667bf3124b6b9bd401be`。下面六个文件均从其 `config/` 原样复制，并逐文件以 SHA-256 确认字节一致。

| 文件 | 声明流数 | MoE 8 KiB（tag=2） | 背景 8 MiB（tag=1） | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `moe_1280group_256to8_8round_8KB.txt` | 16384 | 16384 | 0 | `9E00BAA5C79AB45B107B82B4C18D43CBB9A1073101BF14123AEDD2D90D2E89FD` |
| `moe_1280group_256to8_8round_8KB_hybrid_64fecmp.txt` | 16448 | 16384 | 64 | `83D0B2FF46D683D243BCD1D4B2FC4C2FEFA330324062D13DCFB878AF5ABDD7DC` |
| `moe_1280group_256to8_8round_8KB_hybrid_128fecmp.txt` | 16512 | 16384 | 128 | `D1DD382FB7CEFC368CBFE10AD5A7DB21566AA417E16248172559A7BD9283F5C5` |
| `moe_1280group_256to8_8round_8KB_hybrid_192fecmp.txt` | 16576 | 16384 | 192 | `BF1A1960651B2D5BD27CD1304433D489363727A7C02D08C5C05DF2B2415D9C8A` |

配套拓扑 `topo_1280_400G_400G_OS1.txt` 的 SHA-256 是 `74A6F7154CA10C3CD6DFD45046C4F8ABF0CE27FAA8AD11446B6A52920B83AFBA`；生成脚本 `gen_moe_flow_1280.py` 的 SHA-256 是 `1853787AAFBCF8576CF680141D63C1968AE94029C3A55FB6E7A7FD2D2B77C5B1`。拓扑首行 `1856 576 3840`，对应 1280 台主机、576 台交换机。四份流量的每条记录都是 `src dst pg bytes start_s tag` 六列，当前全部 `pg=3`、`start_s=2.000000000`。

注意：

1. 本 fork 目前的 `scratch/network-load-balance.cc` 只读取**五列**流记录，且 `run.py` 不接收任意现成流文件作为 `--flow_file`；这些文件**已迁移，但尚不能直接用于本 fork 的仿真**。必须先实现六列解析、tag 端到端传播和显式流文件选择，并验证旧五列基线不变。
2. 两种 `tag` 是工作负载标签，不自动代表“允许乱序”和“必须有序”。源仓库 MixHash 的 `lb_mode=16` 对两类数据都使用带计数器的哈希；不能把该 trace 本身称为“包/流混合负载均衡机制”。
3. 原文件随背景流数从 0 增到 192 而**增加总提供字节数**，所以跨文件比较不能单独归因于“混合比例”；各算法须使用同一文件、相同 seed 配对比较。后续因果实验还需制作固定总负载的替换式 trace。
4. 源仓库的 `moe_1280group_256to8_8round_8KB_bg_conflict50_64fecmp.txt` 与普通 `64fecmp` 文件 SHA-256 完全相同；未迁入，不可当作独立冲突场景。生成脚本虽有 `--conflict` 参数，当前脚本未据此改变生成的流内容。
5. 本文件只记录资产与格式，不构成任何性能复现或创新性证据；正式运行须遵循本仓库 `docs/REMOTE_EXPERIMENT_WORKFLOW.md`，记录固定提交 SHA、实验 ID 与原始结果。
