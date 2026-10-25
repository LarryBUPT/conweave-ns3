"""Python figures for the WS-30 paired condition comparison; no data exclusion."""
import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / 'docs/research/evidence'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--qa-tools-dir', type=Path, default=Path.home() / '.codex/skills/nature-figure/scripts')
    args = parser.parse_args()
    sys.path.insert(0, str(args.qa_tools_dir))
    from audit_panel_alignment import require_matplotlib_panel_alignment
    data = json.loads((EV / 'ws30-stage3-lead-analysis-r1.json').read_text(encoding='utf-8'))
    out = ROOT / 'docs/research/figures/ws30-stage3-lead-r1'
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'DejaVu Sans'],
                         'font.size': 8, 'axes.labelsize': 9, 'xtick.labelsize': 8, 'ytick.labelsize': 8,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.linewidth': .7, 'svg.fonttype': 'none', 'pdf.fonttype': 42,
                         'legend.frameon': False, 'savefig.dpi': 600})
    colors = {'synchronous': '#88939B', 'lead20us': '#397A9B'}
    labels = {'synchronous': 'Sync', 'lead20us': 'Lead 20 us'}
    comparisons = {(x['condition'], x['contrast']): x for x in data['comparisons']}

    def export(fig, name):
        base = out / name
        fig.canvas.draw()
        require_matplotlib_panel_alignment(fig, json_out=str(base) + '.alignment.json', strict=True)
        fig.savefig(str(base) + '.svg')
        svg = base.with_suffix('.svg')
        svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines()) + '\n', encoding='utf-8')
        fig.savefig(str(base) + '.pdf')
        fig.savefig(str(base) + '.png', dpi=600)
        plt.close(fig)

    # Question: does the 20-us lead separate class weighting from shared queue selection?
    # Each of 24 demand-seed effects is retained; black marks are median and nominal CI.
    for metric, axis_label, name in [('moe_batch', 'Paired MoE batch-time change (%)', 'moe-effects'),
                                      ('background_p99', 'Paired background P99 FCT change (%)', 'background-effects')]:
        fig, ax = plt.subplots(figsize=(7.2, 3.6))
        fig.subplots_adjust(left=.23, right=.97, bottom=.18, top=.96)
        ticks, ticklabels = [], []
        for group, contrast in enumerate(('Q16/E', 'C16/E', 'C16/Q16')):
            for j, condition in enumerate(('synchronous', 'lead20us')):
                y = 5 - group * 2 - j * .72
                stat = comparisons[(condition, contrast)][metric]
                points = list(stat['per_seed'].values())
                jitter = np.linspace(-.15, .15, len(points))
                ax.scatter(points, y + jitter, s=14, color=colors[condition], alpha=.65, linewidths=0, zorder=2)
                low, high = stat['bootstrap_95pct']
                ax.errorbar(stat['median'], y, xerr=[[stat['median']-low], [high-stat['median']]],
                            fmt='D', color='#17242D', markersize=4, capsize=3, linewidth=1.2, zorder=4)
                ticks.append(y); ticklabels.append(contrast + '  |  ' + labels[condition])
        ax.axvline(0, color='#687078', linewidth=.7, zorder=0)
        if metric == 'background_p99':
            ax.axvline(3, color='#A66D40', linestyle='--', linewidth=.8, zorder=0)
        ax.set(yticks=ticks, yticklabels=ticklabels, xlabel=axis_label, ylim=(-.2, 5.5))
        ax.tick_params(axis='y', length=0)
        export(fig, name)

    # Question: which individual demands pay background-tail cost for a lower MoE batch time?
    fig, ax = plt.subplots(figsize=(5.5, 4.1))
    fig.subplots_adjust(left=.17, right=.97, bottom=.17, top=.88)
    for candidate, color, marker in [('Q16', '#397A9B', 'o'), ('C16', '#B4774A', '^')]:
        c = comparisons[('lead20us', candidate + '/E')]
        seeds = data['independent_demand_seeds']
        x = [c['moe_batch']['per_seed'][str(s)] for s in seeds]
        y = [c['background_p99']['per_seed'][str(s)] for s in seeds]
        ax.scatter(x, y, s=25, color=color, marker=marker, alpha=.85, label=candidate + ' / E', linewidths=.3, edgecolors='white')
    ax.axhline(0, color='#88939B', linewidth=.7, zorder=0)
    ax.axvline(0, color='#88939B', linewidth=.7, zorder=0)
    ax.axhline(3, color='#A66D40', linestyle='--', linewidth=.8, zorder=0)
    ax.set(xlabel='Paired MoE batch-time change (%)', ylabel='Paired background P99 FCT change (%)',
           xlim=(-16, 1), ylim=(-9, 9))
    ax.legend(loc='lower left', bbox_to_anchor=(0, 1.015), ncols=2, borderaxespad=0, fontsize=8)
    export(fig, 'lead-joint-effects')
    contract = {'backend': 'Python / matplotlib', 'source_data': '../../evidence/ws30-stage3-lead-analysis-r1.json',
                'archetype': 'single-panel quantitative plots', 'excluded_observations': 0,
                'n': '24 independent demand seeds; conditions and two metrics are paired within seed',
                'uncertainty': 'black diamond = median; horizontal bar = nominal two-sided demand-bootstrap 95% interval; no significance labels',
                'point_definition': 'one demand-seed paired percent change; all 24 points retained per series',
                'engineering_line': '+3% background line applies to candidate/E comparisons; not a noninferiority test',
                'question': 'Does fixed 20-us background precedence reveal an incremental class-weighting benefit over common queue selection?',
                'role': {'moe-effects': 'MoE relative effects and demand heterogeneity', 'background-effects': 'background cost and adverse cases', 'lead-joint-effects': 'within-demand joint outcomes'},
                'exports': ['PDF editable text', 'SVG editable text', 'PNG 600 dpi preview'], 'journal': 'internal research node report; no journal submission claim'}
    (out / 'figure-contract.json').write_text(json.dumps(contract, indent=2) + '\n', encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
