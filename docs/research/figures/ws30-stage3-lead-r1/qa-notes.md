# WS-30 先占节点图表与统计核对

日期：2026 年 10 月 25 日。用于内部研究节点报告，尚未指定投稿期刊。

## 数据与统计

三张图均由 Python/Matplotlib 绘制。数据来自[分析 JSON](../../evidence/ws30-stage3-lead-analysis-r1.json)、[逐格 CSV](../../evidence/ws30-stage3-lead-paired-r1.csv)和[对比 CSV](../../evidence/ws30-stage3-lead-contrasts-r1.csv)。每个系列保留 24 个需求，无删点或插值。同步与先占是同需求内的相关条件，两种业务指标也在同一需求内配对。

`moe-effects` 和 `background-effects` 的小点表示逐需求百分比变化；黑色菱形表示中位数，横线表示 10,000 次需求层 bootstrap 的名义双侧 95% 区间。随机 seed 固定为 `20263003`，所有对比共用同一份重采样索引。没有显著性标签。背景 +3% 线仅是候选/E 的预设工程参考，不是非劣效或等效性检验。

`lead-joint-effects` 的每种标记为 24 个需求，横纵坐标属于同一需求。它展示 MoE 与背景代价的共同分布，不为两个系列增加独立样本量。

同步配对中位数与原主矩阵完全一致。统一重采样索引后，名义区间端点与旧分析的最大差异为 0.136109 个百分点。旧文件保留，本节点报告与图统一采用本节点重算区间。逐项对应见分析 JSON 的 `synchronous_regression`。

## 渲染核对

三张图分别导出可编辑 PDF、SVG 和 600 dpi PNG。全部 PDF 文本审计最小字号为 8 pt，没有低于 5 pt 的文字。三份 `*.pdf.collision.json` 均为 0 FAIL、0 WARN。每张图只有一个轴，多面板对齐记录为不适用，没有声称执行多面板比较。`figure-contract.json` 记录图的研究问题、数据单位、导出用途和零排除规则。

已逐张目视检查完整图：轴标签、各组配对方向、全部点的取值范围、置信区间、+3% 线与图例均可辨认；没有文字相互覆盖或数据裁切。统计点和区间的重叠是预定编码。没有对原始结果图像做裁剪、局部增强或图像合成。

静态预检为 20 PASS、1 WARN、0 FAIL。WARN 是 PNG 预览存在而没有 TIFF。该节点使用 PDF/SVG 向量图和内部预览，不声明完成任何期刊的最终投稿格式检查。

## 复现与文字检查

分析与绘图入口分别为 `scripts/analyze_ws30_stage3_lead.py` 和 `scripts/plot_ws30_stage3_lead.py`。软件版本、脚本和数据文件哈希见[分析出处收据](../../evidence/ws30-stage3-lead-analysis-provenance-r1.json)。原始 FCT、输入、元数据和配置未修改。

中文报告在写作前从[阮一峰规范 README](https://github.com/ruanyf/document-style-guide)进入，读取标题、文本、段落、数值、标点符号、文档体系六章原文。成稿再次检查层级、空行、中文与英文及数字间距、数值范围、单位、标点和相对变化分母。正文中的绝对分布统计、配对变化中位数和条件对数比差分别标明。
