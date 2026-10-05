#!/usr/bin/env python3
"""Render all 24 formal seeds with six comparable absolute-value arms."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "docs/research/evidence/ws25-v1fix-formal-cell-metrics.csv"
PAIRS = ROOT / "docs/research/evidence/ws25-v1fix-formal-seed-pairs.csv"
UPLINK = ROOT / "docs/research/evidence/ws25-v1fix-formal-uplink-metrics.csv"
OUT = ROOT / "docs/research/figures/ws25-v1fix-formal-seed-overview"
MODES = ("fecmp", "drill", "conga", "letflow", "conweave", "classreserve")
LABELS = ("ECMP", "DRILL", "CONGA", "LetFlow", "ConWeave", "ClassReserve")
COLORS = ("#4b5563", "#2563eb", "#16a34a", "#9333ea", "#d97706", "#dc2626")
METRICS = (("moe_batch_us", "MoE 合成批次完成时间"),
           ("background_p99_fct_us", "背景流 P99 完成时间"))


def esc(value):
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def render(rows, background, metric, title, unit="微秒", note="越低越好"):
    selected = [row for row in rows if int(row["background_flows"]) == background]
    if len(selected) != 24 * 6:
        raise RuntimeError("Missing seed/mode rows for background " + str(background))
    cells = {(int(row["seed"]), row["mode"]): row for row in selected}
    values = [float(row[metric]) for row in selected]
    minimum, maximum = min(values), max(values)
    margin = max((maximum - minimum) * 0.12, 0.1)
    low, high = max(0, minimum - margin), maximum + margin
    left, top, width, height = 82, 104, 1300, 470
    def yp(value):
        return top + height * (high - value) / (high - low)
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1480" height="720" viewBox="0 0 1480 720">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,"Microsoft YaHei","Noto Sans CJK SC",sans-serif;fill:#1f2937}.title{font-size:23px;font-weight:700}.sub{font-size:14px;fill:#4b5563}.axis{font-size:12px}.grid{stroke:#e5e7eb;stroke-width:1}</style>',
        '<text class="title" x="30" y="38">%s：24 个需求 seed × 六种机制</text>' % esc(title),
        '<text class="sub" x="30" y="64">背景流 %d 条 · seed 20262521–20262544（横轴标末两位）· 同 seed 六臂配对 · %s</text>' % (background, esc(note)),
    ]
    for index in range(6):
        value = low + (high - low) * index / 5
        y = yp(value)
        lines.append('<line class="grid" x1="%d" y1="%.2f" x2="%d" y2="%.2f"/>' %
                     (left, y, left + width, y))
        lines.append('<text class="axis" text-anchor="end" x="%d" y="%.2f">%.1f</text>' %
                     (left - 9, y + 4, value))
    for seed_index, seed in enumerate(range(20262521, 20262545)):
        center = left + width * (seed_index + 0.5) / 24
        lines.append('<text class="axis" text-anchor="middle" x="%.2f" y="%d">%d</text>' %
                     (center, top + height + 20, seed % 100))
        for mode_index, mode in enumerate(MODES):
            row = cells[seed, mode]
            x = center + (mode_index - 2.5) * 6.2
            y = yp(float(row[metric]))
            lines.append('<circle cx="%.2f" cy="%.2f" r="3.5" fill="%s"><title>%s | %s | %.6f %s | %s</title></circle>' %
                         (x, y, COLORS[mode_index], seed, LABELS[mode_index], float(row[metric]), esc(unit), esc(row["id"])))
    lines.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="#374151"/>' %
                 (left, top, width, height))
    lines.append('<text class="sub" text-anchor="middle" x="730" y="%d">需求 seed（同一 seed 内六机制共享输入）</text>' %
                 (top + height + 49))
    lines.append('<text class="axis" transform="translate(27 340) rotate(-90)" text-anchor="middle">%s（%s）</text>' % (esc(title), esc(unit)))
    for index, (mode, label) in enumerate(zip(MODES, LABELS)):
        x = 95 + index * 211
        lines.append('<circle cx="%d" cy="662" r="5" fill="%s"/>' % (x, COLORS[index]))
        lines.append('<text class="sub" x="%d" y="667">%s</text>' % (x + 12, label))
    lines.append('<text class="sub" x="1450" y="702" text-anchor="end">原始 ID、trace/FCT SHA 与准确值见逐格指标 CSV；源码 ce699dffe2845dc8…</text>')
    lines.append('</svg>')
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / ("b%03d-%s.svg" % (background, metric))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def render_pair_changes(pairs, background, metric, title):
    chosen = [row for row in pairs if (int(row["background_flows"]) == background and
              row["baseline"] == "fecmp" and row["metric"] == metric)]
    if len(chosen) != 24 or len({row["seed"] for row in chosen}) != 24:
        raise RuntimeError("Incomplete ECMP pair rows")
    by_seed = {int(row["seed"]): row for row in chosen}
    values = [float(row["change_pct"]) for row in chosen]
    low, high = min(min(values), -5, 0), max(max(values), -5, 0)
    margin = max((high - low) * 0.1, 1)
    low -= margin
    high += margin
    left, top, width, height = 85, 95, 1280, 445
    def yp(value):
        return top + height * (high - value) / (high - low)
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1460" height="670" viewBox="0 0 1460 670">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,"Microsoft YaHei","Noto Sans CJK SC",sans-serif;fill:#1f2937}.title{font-size:23px;font-weight:700}.sub{font-size:14px;fill:#4b5563}.axis{font-size:12px}.grid{stroke:#e5e7eb;stroke-width:1}</style>',
        '<text class="title" x="30" y="38">%s：ClassReserve 相对 ECMP 的逐 seed 变化</text>' % esc(title),
        '<text class="sub" x="30" y="64">背景流 %d 条 · seed 20262521–20262544（横轴标末两位）· 负值表示 ClassReserve 较快</text>' % background,
    ]
    for index in range(6):
        value = low + (high - low) * index / 5
        y = yp(value)
        lines.append('<line class="grid" x1="%d" y1="%.2f" x2="%d" y2="%.2f"/>' %
                     (left, y, left + width, y))
        lines.append('<text class="axis" text-anchor="end" x="%d" y="%.2f">%.1f%%</text>' %
                     (left - 8, y + 4, value))
    for value, color, dash in ((0, "#374151", ""), (-5, "#a16207", ' stroke-dasharray="6 4"')):
        y = yp(value)
        lines.append('<line x1="%d" y1="%.2f" x2="%d" y2="%.2f" stroke="%s" stroke-width="1.5"%s/>' %
                     (left, y, left + width, y, color, dash))
    for index, seed in enumerate(range(20262521, 20262545)):
        row = by_seed[seed]
        value = float(row["change_pct"])
        x = left + width * (index + 0.5) / 24
        color = "#15803d" if value < 0 else "#dc2626"
        lines.append('<circle cx="%.2f" cy="%.2f" r="5" fill="%s"><title>seed %d | %.6f%% | %s | %s</title></circle>' %
                     (x, yp(value), color, seed, value, esc(row["classreserve_id"]), esc(row["baseline_id"])))
        lines.append('<text class="axis" text-anchor="middle" x="%.2f" y="%d">%d</text>' %
                     (x, top + height + 20, seed % 100))
    lines.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="#374151"/>' %
                 (left, top, width, height))
    lines.append('<text class="sub" text-anchor="middle" x="720" y="%d">需求 seed</text>' % (top + height + 50))
    lines.append('<text class="sub" x="30" y="625">水平实线：0%；虚线：−5% 工程幅度线。单个点越线不等于 24 seed 中位数通过正式门槛。</text>')
    lines.append('</svg>')
    path = OUT / ("b%03d-%s-vs-ecmp.svg" % (background, metric))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main():
    with TABLE.open("r", encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if len(rows) != 576:
        raise RuntimeError("Incomplete formal table")
    paths = []
    with PAIRS.open("r", encoding="utf-8", newline="") as source:
        pairs = list(csv.DictReader(source))
    if len(pairs) != 840:
        raise RuntimeError("Incomplete formal pair table")
    for background in (0, 64, 128, 192):
        for metric, title in METRICS:
            if background == 0 and metric.startswith("background"):
                continue
            paths.append(render(rows, background, metric, title))
            pair_metric = "background_p99_fct_us" if metric.startswith("background") else metric
            paths.append(render_pair_changes(pairs, background, pair_metric, title))
    with UPLINK.open("r", encoding="utf-8", newline="") as source:
        uplink_rows = list(csv.DictReader(source))
    if len(uplink_rows) != 576:
        raise RuntimeError("Incomplete uplink table")
    for background in (0, 64, 128, 192):
        paths.append(render(uplink_rows, background, "mean_active_port_utilization_pct",
                            "活跃上联端口平均计数器等效率", "% of 400 Gbps",
                            "仅表示原始字节计数/时间窗，不等于物理实时利用率"))
        paths.append(render(uplink_rows, background, "mean_active_tor_port_imbalance",
                            "活跃 ToR 上联端口平均不均衡", "无量纲",
                            "全局分布描述，不能代替尾流的逐跳排队"))
    print("seed_overview_figures=%d" % len(paths))


if __name__ == "__main__":
    main()
