#!/usr/bin/env python3
"""Plot six-mode FCT CDFs for every formal demand seed and background level."""
import csv
import hashlib
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "docs/research/evidence/ws25-v1fix-formal-cell-metrics.csv"
FIGURES = ROOT / "docs/research/figures/ws25-v1fix-formal-cdf"
INDEX = ROOT / "docs/research/evidence/ws25-v1fix-formal-cdf-index.csv"
MODES = ("fecmp", "drill", "conga", "letflow", "conweave", "classreserve")
LABELS = {"fecmp": "ECMP", "drill": "DRILL", "conga": "CONGA",
          "letflow": "LetFlow", "conweave": "ConWeave", "classreserve": "ClassReserve"}
COLORS = {"fecmp": "#4b5563", "drill": "#2563eb", "conga": "#16a34a",
          "letflow": "#9333ea", "conweave": "#d97706", "classreserve": "#dc2626"}


def esc(value):
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fct_values(row, size):
    path = ROOT / row["raw_fct_path"]
    if not path.is_file() or path.is_symlink() or sha(path) != row["fct_sha256"]:
        raise RuntimeError("Raw FCT fingerprint mismatch: " + row["id"])
    values = []
    with path.open("r", encoding="ascii") as source:
        for line in source:
            data = line.split()
            if len(data) != 8:
                raise RuntimeError("Malformed FCT row: " + row["id"])
            if int(data[4]) == size:
                value = int(data[6]) / 1000
                if value <= 0:
                    raise RuntimeError("Nonpositive FCT: " + row["id"])
                values.append(value)
    expected = 16384 if size == 8192 else int(row["background_flows"])
    if len(values) != expected:
        raise RuntimeError("CDF flow count mismatch: " + row["id"])
    return sorted(values)


def polyline(values, xmin, xmax):
    left, top, width, height = 95, 95, 770, 415
    indices = {0, len(values) - 1}
    indices.update(round(i * (len(values) - 1) / 400) for i in range(401))
    for pct in (90, 95, 99, 99.9, 99.99):
        indices.add(round((len(values) - 1) * pct / 100))
    xlow, xhigh = math.log10(xmin), math.log10(xmax)
    points = []
    for index in sorted(indices):
        x = left + width * (math.log10(values[index]) - xlow) / (xhigh - xlow)
        y = top + height * (1 - (index + 1) / len(values))
        points.append("%.2f,%.2f" % (x, y))
    return " ".join(points)


def render(rows, seed, background, kind):
    size = 8192 if kind == "moe" else 8388608
    series = {mode: fct_values(rows[mode], size) for mode in MODES}
    xmin = min(values[0] for values in series.values())
    xmax = max(values[-1] for values in series.values())
    xmin = 10 ** (math.floor(math.log10(xmin) * 2) / 2)
    xmax = 10 ** (math.ceil(math.log10(xmax) * 2) / 2)
    if xmax <= xmin:
        xmax = xmin * 10
    left, top, width, height = 95, 95, 770, 415
    title = ("MoE 流" if kind == "moe" else "背景流") + "完成时间累计分布"
    filename = "seed%d-b%03d-%s-fct-cdf.svg" % (seed, background, kind)
    path = FIGURES / filename
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="970" height="640" viewBox="0 0 970 640">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,"Microsoft YaHei","Noto Sans CJK SC",sans-serif;fill:#1f2937}.title{font-size:22px;font-weight:700}.sub{font-size:13px;fill:#4b5563}.axis{font-size:13px}.grid{stroke:#e5e7eb;stroke-width:1}</style>',
        '<text class="title" x="30" y="37">%s</text>' % esc(title),
        '<text class="sub" x="30" y="60">需求 seed %d · 背景流 %d 条 · 六种机制使用相同输入 · 横轴为对数刻度</text>' % (seed, background),
    ]
    xlow, xhigh = math.log10(xmin), math.log10(xmax)
    for exponent in range(math.ceil(xlow), math.floor(xhigh) + 1):
        value = 10 ** exponent
        x = left + width * (exponent - xlow) / (xhigh - xlow)
        lines.append('<line class="grid" x1="%.2f" y1="%d" x2="%.2f" y2="%d"/>' % (x, top, x, top + height))
        lines.append('<text class="axis" text-anchor="middle" x="%.2f" y="%d">%g</text>' % (x, top + height + 24, value))
    for pct in (0, 25, 50, 75, 90, 100):
        y = top + height * (1 - pct / 100)
        lines.append('<line class="grid" x1="%d" y1="%.2f" x2="%d" y2="%.2f"/>' % (left, y, left + width, y))
        lines.append('<text class="axis" text-anchor="end" x="%d" y="%.2f">%d%%</text>' % (left - 9, y + 4, pct))
    lines.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="#374151"/>' % (left, top, width, height))
    for mode in MODES:
        lines.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.1"/>' %
                     (polyline(series[mode], xmin, xmax), COLORS[mode]))
    for index, mode in enumerate(MODES):
        x = 80 + (index % 3) * 270
        y = 568 + (index // 3) * 23
        lines.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="3"/>' %
                     (x, y, x + 25, y, COLORS[mode]))
        lines.append('<text class="axis" x="%d" y="%d">%s (n=%d)</text>' %
                     (x + 33, y + 4, LABELS[mode], len(series[mode])))
    lines.append('<text class="axis" text-anchor="middle" x="480" y="552">单流完成时间（微秒，log10）</text>')
    lines.append('<text class="sub" x="945" y="627" text-anchor="end">原始 ID 与 SHA 见配套 CDF 索引；仿真 SHA ce699dffe2845dc8…</text>')
    lines.append('</svg>')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path, series


def main():
    with TABLE.open("r", encoding="utf-8", newline="") as source:
        cells = list(csv.DictReader(source))
    if len(cells) != 576:
        raise RuntimeError("Incomplete formal cell table")
    by_key = {(int(row["seed"]), int(row["background_flows"]), row["mode"]): row for row in cells}
    if len(by_key) != 576:
        raise RuntimeError("Duplicate formal cell table key")
    FIGURES.mkdir(parents=True, exist_ok=True)
    index = []
    for seed in range(20262521, 20262545):
        for background in (0, 64, 128, 192):
            rows = {mode: by_key[seed, background, mode] for mode in MODES}
            if len({row["trace_sha256"] for row in rows.values()}) != 1:
                raise RuntimeError("Six modes do not share input")
            for kind in (("moe",) if background == 0 else ("moe", "background")):
                path, series = render(rows, seed, background, kind)
                for mode in MODES:
                    index.append({"seed": seed, "background_flows": background, "class": kind,
                                  "figure": str(path.relative_to(ROOT)).replace("\\", "/"),
                                  "mode": mode, "id": rows[mode]["id"],
                                  "trace_sha256": rows[mode]["trace_sha256"],
                                  "fct_sha256": rows[mode]["fct_sha256"],
                                  "cdf_sample_count": len(series[mode])})
    with INDEX.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(index[0]))
        writer.writeheader()
        writer.writerows(index)
    print("figures=%d index_rows=%d" % (len(index) // 6, len(index)))


if __name__ == "__main__":
    main()
