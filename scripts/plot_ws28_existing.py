#!/usr/bin/env python3
"""Draw the WS-28 paired seed evidence from verified WS-27 raw data."""
import json
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/research/evidence/ws28-existing-raw-analysis.json"
STEM = ROOT / "docs/research/figures/ws28-classreserve-paired-seeds"
sys.path.insert(0, str(Path.home() / ".codex/skills/nature-figure/scripts"))
from audit_panel_alignment import require_matplotlib_panel_alignment  # noqa: E402


def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = data["paired_seeds"]
    assert len(rows) == 24 and [r["seed"] for r in rows] == list(range(20262721, 20262745))
    mpl.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans", "sans-serif"],
        "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
        "legend.fontsize": 7, "axes.spines.right": False, "axes.spines.top": False,
        "axes.linewidth": 0.8, "svg.fonttype": "none", "pdf.fonttype": 42,
    })
    fig, ax = plt.subplots(figsize=(183 / 25.4, 82 / 25.4), dpi=600)
    x = list(range(len(rows)))
    batch = [r["moe_batch_change_pct"] for r in rows]
    single_p95 = [r["moe_single_flow_p95_change_pct"] for r in rows]
    ax.axhline(0, color="#525A61", lw=0.8, zorder=1)
    ax.scatter([v - 0.12 for v in x], batch, s=21, marker="o", color="#17639A",
               label="MoE batch completion", zorder=3)
    ax.scatter([v + 0.12 for v in x], single_p95, s=23, marker="^", color="#C4772E",
               label="Within-seed MoE flow FCT P95", zorder=3)
    ax.set_xticks(x, [str(r["seed"])[-2:] for r in rows])
    ax.set_xlim(-0.7, 23.7)
    ax.set_ylabel("Paired change vs ECMP (%)")
    ax.set_xlabel("Demand seed (202627xx)")
    ax.grid(axis="y", lw=0.45, color="#D9DEE3", zorder=0)
    fig.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.53, 0.995))
    fig.subplots_adjust(left=0.09, right=0.985, top=0.87, bottom=0.17)
    fig.canvas.draw()
    STEM.parent.mkdir(parents=True, exist_ok=True)
    require_matplotlib_panel_alignment(fig, json_out=str(STEM) + ".alignment.json",
                                       overlay_svg=str(STEM) + ".alignment.svg", strict=True)
    fig.savefig(str(STEM) + ".pdf")
    fig.savefig(str(STEM) + ".svg")
    svg = Path(str(STEM) + ".svg")
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n",
                   encoding="utf-8")
    fig.savefig(str(STEM) + ".tiff", dpi=600)
    plt.close(fig)


if __name__ == "__main__":
    main()
