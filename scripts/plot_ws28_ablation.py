#!/usr/bin/env python3
"""Plot paired WS-28 factorial contrasts from the verified raw analysis."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from audit_panel_alignment import require_matplotlib_panel_alignment


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/research/evidence/ws28-ablation-analysis.json"
OUT = ROOT / "docs/research/figures/ws28-component-effects"
CONTRASTS = ["A_when_B0", "A_when_B1", "B_when_A0", "B_when_A1", "A_by_B_interaction"]
LABELS = ["A | B=0", "A | B=1", "B | A=0", "B | A=1", "A × B"]
COLORS = ["#22668B", "#22668B", "#B76B3F", "#B76B3F", "#454545"]


def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    if data["verified_cells"] != 120 or data["independent_units"] != 24:
        raise ValueError("Expected 120 verified cells and 24 independent seeds")
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
        "svg.fonttype": "none", "pdf.fonttype": 42, "font.size": 7,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": .7,
    })
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.45), sharey=True)
    fig.subplots_adjust(left=.16, right=.98, bottom=.22, top=.83, wspace=.11)
    specs = [
        ("moe_batch_pct", "MoE batch completion", (-11, 12)),
        ("background_p99_pct", "Background P99 FCT", (-12, 12)),
    ]
    for panel, (ax, (metric, title, xlim)) in enumerate(zip(axes, specs)):
        ax.axvline(0, color="#777777", linewidth=.7, zorder=0)
        ax.set_xlim(*xlim)
        ax.set_ylim(-.5, len(CONTRASTS)-.5)
        ax.invert_yaxis()
        for idx, key in enumerate(CONTRASTS):
            values = [row["contrasts"][key][metric] for row in data["paired_seeds"]]
            if len(values) != 24:
                raise ValueError("Incomplete paired seeds for " + key)
            offsets = [((row["seed"] * 7) % 17 - 8) * .014
                       for row in data["paired_seeds"]]
            color = COLORS[idx]
            ax.scatter(values, [idx + offset for offset in offsets], s=7,
                       color=color, alpha=.34, linewidths=0, zorder=2)
            summary = data["component_effects"][key][metric]
            low, high = summary["bootstrap_95pct"]
            ax.plot([low, high], [idx, idx], color=color, linewidth=2.5,
                    solid_capstyle="round", zorder=3)
            ax.scatter([summary["median_pct"]], [idx], marker="D", s=26,
                       color=color, edgecolor="white", linewidth=.5, zorder=4)
        ax.set_yticks(range(len(CONTRASTS)))
        ax.set_yticklabels(LABELS)
        ax.set_xlabel("Paired change (%)")
        ax.set_title(title, loc="left", fontsize=9, pad=13)
        ax.text(-.07, 1.05, "ab"[panel], transform=ax.transAxes,
                ha="right", va="bottom", fontsize=9, fontweight="bold")
        ax.grid(axis="x", color="#E6E6E6", linewidth=.5)
        ax.set_axisbelow(True)
        ax.tick_params(axis="both", length=2.5, width=.6)
    axes[1].tick_params(axis="y", labelleft=False, left=False)
    fig.text(.16, .07,
             "Points: 24 paired seeds; diamonds: medians; bars: seed-bootstrap 95% intervals (10,000 resamples).",
             fontsize=7, ha="left")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    require_matplotlib_panel_alignment(
        fig, axes=axes, panel_ids=["a", "b"], row_groups=[["a", "b"]],
        json_out=str(OUT) + ".alignment.json",
        overlay_svg=str(OUT) + ".alignment.svg", strict=True)
    svg = Path(str(OUT) + ".svg")
    fig.savefig(svg)
    svg.write_text("\n".join(line.rstrip() for line in
                             svg.read_text(encoding="utf-8").splitlines()) + "\n",
                   encoding="utf-8")
    fig.savefig(str(OUT) + ".pdf")
    fig.savefig(str(OUT) + ".tiff", dpi=600)
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
