#!/usr/bin/env python3
"""Render all 24 formal seeds with six comparable absolute-value arms."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "docs/research/evidence/ws25-v1fix-formal-cell-metrics.csv"
OUT = ROOT / "docs/research/figures/ws25-v1fix-formal-seed-overview"
MODES = ("fecmp", "drill", "conga", "letflow", "conweave", "classreserve")
LABELS = ("ECMP", "DRILL", "CONGA", "LetFlow", "ConWeave", "ClassReserve")
COLORS = ("#4b5563", "#2563eb", "#16a34a", "#9333ea", "#d97706", "#dc2626")
METRICS = (("moe_batch_us", "MoE 合成批次完成时间"),
           ("background_p99_fct_us", "背景流 P99 完成时间"))


def esc(value):
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def render(rows, background, metric, title):
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
        '<text class="sub" x="30" y="64">背景流 %d 条 · 每个点是一格独立原始结果 · 横向分组按 seed 配对 · 越低越好</text>' % background,
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
                     (center, top + height + 20, seed))
        for mode_index, mode in enumerate(MODES):
            row = cells[seed, mode]
            x = center + (mode_index - 2.5) * 6.2
            y = yp(float(row[metric]))
            lines.append('<circle cx="%.2f" cy="%.2f" r="3.5" fill="%s"><title>%s | %s | %.6f 微秒 | %s</title></circle>' %
                         (x, y, COLORS[mode_index], seed, LABELS[mode_index], float(row[metric]), esc(row["id"])))
    lines.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="#374151"/>' %
                 (left, top, width, height))
    lines.append('<text class="sub" text-anchor="middle" x="730" y="%d">需求 seed（同一 seed 内六机制共享输入）</text>' %
                 (top + height + 49))
    lines.append('<text class="axis" transform="translate(27 340) rotate(-90)" text-anchor="middle">%s（微秒）</text>' % esc(title))
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


def main():
    with TABLE.open("r", encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if len(rows) != 576:
        raise RuntimeError("Incomplete formal table")
    paths = []
    for background in (0, 64, 128, 192):
        for metric, title in METRICS:
            if background == 0 and metric.startswith("background"):
                continue
            paths.append(render(rows, background, metric, title))
    print("seed_overview_figures=%d" % len(paths))


if __name__ == "__main__":
    main()
