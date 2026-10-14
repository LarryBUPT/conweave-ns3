#!/usr/bin/env python3
"""Plot paired WS-28 native-mode effects and their background constraint."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from audit_panel_alignment import require_matplotlib_panel_alignment


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/research/evidence/ws28-native-analysis.json"
OUT = ROOT / "docs/research/figures/ws28-native-comparison"
MODES = ["drill", "classreserve", "letflow", "conweave", "fecmp", "conga"]
LABELS = {"drill": "DRILL", "classreserve": "ClassReserve v1",
          "letflow": "LetFlow", "conweave": "ConWeave",
          "fecmp": "ECMP", "conga": "CONGA"}
COLORS = {"drill": "#C65B45", "classreserve": "#145A88",
          "letflow": "#678599", "conweave": "#8296A4",
          "fecmp": "#555555", "conga": "#9DABAF"}


def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    if data["verified_raw_cells"] != 144:
        raise ValueError("Expected all 144 raw cells")
    effects = {row["mode"]: row for row in data["effects"]}
    rows = {(row["seed"], row["mode"]): row for row in data["paired_seeds"]}
    seeds = range(20262721, 20262745)
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
        "svg.fonttype": "none", "pdf.fonttype": 42, "font.size": 7,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": .7,
    })
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.35), sharey=True)
    fig.subplots_adjust(left=.16, right=.98, bottom=.19, top=.84, wspace=.08)
    specs = [
        ("moe_batch_change_vs_ecmp_pct", "moe_batch_median_change_vs_ecmp_pct",
         "moe_batch_bootstrap_95pct", "MoE batch completion", (-28, 16)),
        ("background_p99_change_vs_ecmp_pct", "background_p99_median_change_vs_ecmp_pct",
         "background_p99_bootstrap_95pct", "Background flow P99 FCT", (-9, 19)),
    ]
    for panel, (ax, spec) in enumerate(zip(axes, specs)):
        value_key, median_key, interval_key, title, limits = spec
        ax.set_xlim(*limits)
        ax.set_ylim(-.6, len(MODES) - .4)
        ax.invert_yaxis()
        ax.axvline(0, color="#696969", linewidth=.7, zorder=0)
        if panel == 1:
            ax.axvline(3, color="#B24C3E", linewidth=.9, linestyle="--", zorder=0)
        for index, mode in enumerate(MODES):
            color = COLORS[mode]
            if mode != "fecmp":
                values = [rows[(seed, mode)][value_key] for seed in seeds]
                offsets = [((seed * 7) % 17 - 8) * .012 for seed in seeds]
                ax.scatter(values, [index + offset for offset in offsets], s=7,
                           color=color, alpha=.42, linewidths=0, zorder=2)
                low, high = effects[mode][interval_key]
                ax.plot([low, high], [index, index], color=color, linewidth=2.2,
                        solid_capstyle="round", zorder=3)
            ax.scatter([effects[mode][median_key]], [index], marker="D", s=24,
                       facecolor=color, edgecolor="white", linewidth=.5, zorder=4)
        ax.set_yticks(range(len(MODES)))
        ax.set_yticklabels([LABELS[mode] for mode in MODES])
        ax.set_xlabel("Paired change vs ECMP (%)")
        ax.set_title(title, loc="left", fontsize=9, pad=13)
        ax.text(-.07, 1.05, "ab"[panel], transform=ax.transAxes,
                ha="right", va="bottom", fontsize=9, fontweight="bold")
        ax.grid(axis="x", color="#E5E5E5", linewidth=.5)
        ax.set_axisbelow(True)
        ax.tick_params(axis="both", length=2.5, width=.6)
    axes[1].tick_params(axis="y", labelleft=False, left=False)
    fig.text(.16, .05, "Points: 24 matched seeds; diamonds: medians; bars: bootstrap 95% intervals; dashed line: +3% background gate.",
             fontsize=7, ha="left")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    require_matplotlib_panel_alignment(
        fig, axes=axes, panel_ids=["a", "b"], row_groups=[["a", "b"]],
        json_out=str(OUT) + ".alignment.json",
        overlay_svg=str(OUT) + ".alignment.svg", strict=True)
    fig.savefig(str(OUT) + ".svg")
    fig.savefig(str(OUT) + ".pdf")
    fig.savefig(str(OUT) + ".tiff", dpi=600)
    plt.close(fig)
    print(str(OUT))


if __name__ == "__main__":
    main()
