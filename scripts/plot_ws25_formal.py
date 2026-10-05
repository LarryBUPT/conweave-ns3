#!/usr/bin/env python3
"""Render the frozen WS-25 formal 192-flow paired-effect forest plot as SVG."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/research/evidence/ws25-v1fix-formal-analysis.json"
OUTPUT = ROOT / "docs/research/figures/ws25-v1fix-formal-192-effects.svg"

BASELINES = (("fecmp", "ECMP"), ("drill", "DRILL"),
             ("conga", "CONGA"), ("letflow", "LetFlow"),
             ("conweave", "ConWeave"))
METRICS = (("moe_batch_us", "MoE batch completion time"),
           ("background_p99_us", "Background-flow P99 FCT"))


def esc(value):
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def render():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    width, height = 1000, 620
    x0, x1 = 230, 960
    xmin, xmax = -25.0, 25.0
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#17212b}.title{font-size:19px;font-weight:700}.panel{font-size:15px;font-weight:700}.axis{font-size:12px}.row{font-size:13px}.note{font-size:12px;fill:#45515c}.main{stroke:#9a3412;stroke-width:3}.other{stroke:#527a9b;stroke-width:2}.main-dot{fill:#c2410c}.other-dot{fill:#527a9b}.zero{stroke:#273746;stroke-width:1.4}.gate{stroke:#a16207;stroke-width:1.4;stroke-dasharray:6 4}.grid{stroke:#d8dee4;stroke-width:1}</style>',
        '<text class="title" x="24" y="30">ClassReserve v1: paired effects at 192 background flows</text>',
    ]
    panel_top = (78, 326)
    panel_height = 170
    row_gap = 28
    for panel_index, (metric, label) in enumerate(METRICS):
        top = panel_top[panel_index]
        bottom = top + panel_height
        def xp(value):
            return x0 + (value - xmin) * (x1 - x0) / (xmax - xmin)

        lines.append(f'<text class="panel" x="24" y="{top - 24}">{esc(label)}</text>')
        lines.append(f'<line class="grid" x1="{x0}" y1="{top}" x2="{x1}" y2="{top}"/>')
        lines.append(f'<line class="zero" x1="{xp(0):.2f}" y1="{top}" x2="{xp(0):.2f}" y2="{bottom}"/>')
        lines.append(f'<line class="gate" x1="{xp(-5):.2f}" y1="{top}" x2="{xp(-5):.2f}" y2="{bottom}"/>')
        for tick in (-20, -10, -5, 0, 10, 20):
            x = xp(tick)
            lines.append(f'<line class="grid" x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{bottom}"/>')
            lines.append(f'<text class="axis" text-anchor="middle" x="{x:.2f}" y="{bottom + 19}">{tick}</text>')
        for index, (baseline, name) in enumerate(BASELINES):
            y = top + 20 + index * row_gap
            stats = data["paired_changes"]["192"][baseline][metric]
            median = stats["median_change_pct"]
            low, high = stats["bootstrap_95pct_median_ci"]
            main = baseline == "fecmp"
            cls = "main" if main else "other"
            dot_cls = "main-dot" if main else "other-dot"
            lines.append(f'<text class="row" text-anchor="end" x="{x0 - 12}" y="{y + 4}">{esc(name)}</text>')
            lines.append(f'<line class="{cls}" x1="{xp(low):.2f}" y1="{y}" x2="{xp(high):.2f}" y2="{y}"/>')
            lines.append(f'<line class="{cls}" x1="{xp(low):.2f}" y1="{y - 5}" x2="{xp(low):.2f}" y2="{y + 5}"/>')
            lines.append(f'<line class="{cls}" x1="{xp(high):.2f}" y1="{y - 5}" x2="{xp(high):.2f}" y2="{y + 5}"/>')
            lines.append(f'<circle class="{dot_cls}" cx="{xp(median):.2f}" cy="{y}" r="5"/>')
        lines.append(f'<text class="axis" text-anchor="middle" x="{(x0 + x1) / 2}" y="{bottom + 42}">Paired change (%) — lower is better</text>')
    lines.append('<line class="gate" x1="24" y1="564" x2="54" y2="564"/><text class="note" x="61" y="568">−5% engineering magnitude threshold</text>')
    lines.append('<line class="zero" x1="360" y1="564" x2="390" y2="564"/><text class="note" x="397" y="568">0% no change</text>')
    lines.append('<text class="note" x="1000" y="589" text-anchor="end">Points: paired median; bars: 95% bootstrap CI, 24 demand seeds. Negative favors ClassReserve.</text>')
    lines.append('<text class="note" x="1000" y="608" text-anchor="end">Formal ID prefix: 20261004-070000-ws25-formal-; source SHA: ce699dffe2845dc83e2171a1c309c6d96b96d2b3</text>')
    lines.append('</svg>')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    render()
