#!/usr/bin/env python3
"""Plot the terminal-packet queue timelines for three WS-28 counterexamples."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from audit_panel_alignment import require_matplotlib_panel_alignment


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/research/evidence/ws28-tail-analysis.json"
OUTDIR = ROOT / "docs/research/figures"
SEEDS = (20262725, 20262729, 20262739)
MODES = (("fecmp", "ECMP", "#666666"),
         ("classreserve", "ClassReserve", "#15618A"))


def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = {(row.get("seed"), row.get("mode")): row
            for row in data["analyzed_cells"] if row["diag"]}
    if len(data["analyzed_cells"]) != 12 or len(rows) != 6:
        raise ValueError("Expected twelve verified diagnostic cells")
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
        "svg.fonttype": "none", "pdf.fonttype": 42, "font.size": 7,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": .7,
    })
    OUTDIR.mkdir(parents=True, exist_ok=True)
    for seed in SEEDS:
        fig, ax = plt.subplots(figsize=(7.2, 3.3))
        fig.subplots_adjust(left=.27, right=.98, bottom=.2, top=.81)
        labels = []
        for target_idx, target_name in enumerate(("ECMP tail flow", "ClassReserve tail flow")):
            for mode_idx, (mode, mode_name, color) in enumerate(MODES):
                row = rows[(seed, mode)]
                target = row["targets"][target_idx]
                if target["target"] != 2 * SEEDS.index(seed) + target_idx:
                    raise ValueError("Unexpected target order for seed " + str(seed))
                paths = target["max_seq_paths"]
                if len(paths) != 1:
                    raise ValueError("Expected one terminal-packet UID per target")
                y = 3 - 2 * target_idx - mode_idx
                hops = paths[0]["hops"]
                for hop_idx, hop in enumerate(hops):
                    start = (hop["enqueue_ns"] - 2_000_000_000) / 1000
                    end = (hop["end_ns"] - 2_000_000_000) / 1000
                    if hop["event"] != "DEQUEUE" or end < start:
                        raise ValueError("Unexpected terminal-packet event")
                    if hop_idx:
                        previous = (hops[hop_idx - 1]["end_ns"] - 2_000_000_000) / 1000
                        ax.plot([previous, start], [y, y], color=color,
                                alpha=.5, linewidth=.65, zorder=1)
                    ax.plot([start, end], [y, y], color=color,
                            linewidth=4.0, solid_capstyle="round", zorder=2)
                    ax.scatter([start], [y], marker="|", s=55,
                               color=color, linewidths=.9, zorder=3)
                src, dst, sport, dport = target["flow"]
                labels.append((y, "{}: {}:{}→{}:{}".format(
                    mode_name, src, sport, dst, dport)))
        ax.set_yticks([y for y, _ in labels])
        ax.set_yticklabels([label for _, label in labels])
        ax.set_ylim(-.5, 3.5)
        ax.set_xlim(9.5, 20.5)
        ax.set_xticks([10, 12, 14, 16, 18, 20])
        ax.set_xlabel("Simulation time after 2.000 s (μs)")
        ax.set_title("Seed {}: terminal-packet queue timeline".format(seed),
                     loc="left", fontsize=9, pad=12)
        ax.axhline(1.5, color="#D6D6D6", linewidth=.7)
        ax.grid(axis="x", color="#E6E6E6", linewidth=.5)
        ax.set_axisbelow(True)
        ax.tick_params(axis="both", length=2.5, width=.6)
        fig.text(.27, .06,
                 "Thick: switch queue wait; thin: between observed hops; ticks: enqueue.",
                 fontsize=7, ha="left")
        out = OUTDIR / "ws28-tail-timeline-s{}".format(seed)
        require_matplotlib_panel_alignment(
            fig, axes=[ax], panel_ids=["a"],
            json_out=str(out) + ".alignment.json",
            overlay_svg=str(out) + ".alignment.svg", strict=True)
        svg = Path(str(out) + ".svg")
        fig.savefig(svg)
        svg.write_text("\n".join(line.rstrip() for line in
                                 svg.read_text(encoding="utf-8").splitlines()) + "\n",
                       encoding="utf-8")
        fig.savefig(str(out) + ".pdf")
        fig.savefig(str(out) + ".tiff", dpi=600)
        plt.close(fig)
        print(out)


if __name__ == "__main__":
    main()
